"""
Unit tests for the thread helpers and the thread safe RCON Client
"""

import threading
from time import sleep

import pytest
from mcipc.rcon.enumerations import CloneMode, FillMode, MaskMode, SetblockMode
from mcipc.rcon.exceptions import InvalidArgument
from mcipc.rcon.je.client import Client as McipcClient
from mcwb import Item, Vec3
from mcwb.api import get_block
from rcon.source import Client as SourceClient

from mciwb.threads import RCON_ATTEMPTS, Client


def test_client_runs_one_command_at_a_time(monkeypatch: pytest.MonkeyPatch):
    """
    the server shares one output buffer between RCON connections, so commands
    from clients on different threads must not overlap
    """
    running = 0
    overlapped = False

    def run(self, command: str, *arguments: str) -> str:
        nonlocal running, overlapped
        running += 1
        overlapped |= running > 1
        sleep(0.01)
        running -= 1
        return command

    monkeypatch.setattr(McipcClient, "run", run)
    clients = [Client("localhost", 20400, passwd="pass") for _ in range(4)]
    results: list[str] = []

    def use(client: Client):
        for i in range(5):
            results.append(client.run(f"say {i}"))

    threads = [threading.Thread(target=use, args=(c,)) for c in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not overlapped
    assert len(results) == 20


class FakeServer:
    """
    Stands in for the RCON connection of `Client`: each command gets the next
    of a list of replies, as from a server whose replies another RCON client
    garbles (gilesknap/mciwb#166)
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *replies: str):
        self.replies = list(replies)
        self.sent: list[str] = []

        def run(client, command: str, *arguments: str) -> str:
            self.sent.append(" ".join((command, *arguments)))
            return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]

        # the RCON transport, under mcipc's argument formatting and checks
        monkeypatch.setattr(SourceClient, "run", run)


@pytest.fixture
def client() -> Client:
    return Client("localhost", 20400, passwd="pass")


def test_lost_reply_is_retried(monkeypatch: pytest.MonkeyPatch, client: Client):
    server = FakeServer(monkeypatch, "", "Changed the block at 1, -2, 3")
    assert client.setblock(Vec3(1, -2, 3), "minecraft:stone") == (
        "Changed the block at 1, -2, 3"
    )
    assert server.sent == ["setblock 1 -2 3 minecraft:stone"] * 2

    # but commands such as summon and give may not be safe to send twice
    server.replies = [""]
    assert client.run("summon minecraft:pig 0 0 0") == ""
    assert client.run("give", "georgeTest", "minecraft:stone") == ""
    assert len(server.sent) == 4


def test_polluted_reply_gives_own_output(
    monkeypatch: pytest.MonkeyPatch, client: Client
):
    """the output of another client's command is removed from the reply"""
    polluted = (
        "There are 0 of a max of 20 players online: \nSuccessfully filled 8 block(s)"
    )
    server = FakeServer(monkeypatch, polluted)
    reply = client.fill(Vec3(0, 0, 0), Vec3(1, 1, 1), "minecraft:stone")
    assert reply == "Successfully filled 8 block(s)"
    assert len(server.sent) == 1


def test_other_clients_setblock_reply_is_retried(
    monkeypatch: pytest.MonkeyPatch, client: Client
):
    server = FakeServer(
        monkeypatch, "Changed the block at 9, 9, 9", "Changed the block at 1, 2, 3"
    )
    assert client.setblock(Vec3(1, 2, 3), "minecraft:stone").endswith("1, 2, 3")
    assert len(server.sent) == 2
    # ours, after another client's
    server.replies = ["Changed the block at 9, 9, 9\nChanged the block at 1, 2, 3"]
    assert client.setblock(Vec3(1, 2, 3), "minecraft:stone") == (
        "Changed the block at 1, 2, 3"
    )
    assert len(server.sent) == 3


def test_block_reads_are_retried(monkeypatch: pytest.MonkeyPatch, client: Client):
    """mcwb.get_block reads blocks with loot spawn, through this client"""
    FakeServer(
        monkeypatch,
        "",
        "There are 0 of a max of 20 players online: "
        "Dropped 1 [Stone] from loot table minecraft:blocks/stone",
        "Block Air has no loot table",
    )
    assert get_block(client, Vec3(1, 2, 3)) == Item.STONE
    assert get_block(client, Vec3(1, 2, 4)) == Item.AIR


def test_real_errors_are_not_retried_for_long(
    monkeypatch: pytest.MonkeyPatch, client: Client
):
    """the same reply twice is the server's real reply, not a garbled one"""
    server = FakeServer(monkeypatch, "That position is not loaded")
    assert client.setblock(Vec3(1, 2, 3), "minecraft:stone") == (
        "That position is not loaded"
    )
    assert len(server.sent) == 2


def test_retries_are_bounded(monkeypatch: pytest.MonkeyPatch, client: Client):
    server = FakeServer(monkeypatch, "")
    assert client.fill(Vec3(0, 0, 0), Vec3(1, 1, 1), "minecraft:stone") == ""
    assert len(server.sent) == RCON_ATTEMPTS


def test_harmful_repeats_are_not_retried(
    monkeypatch: pytest.MonkeyPatch, client: Client
):
    """
    destroy mode would destroy what the first send placed, and clone may move
    blocks or overlap its source: these are sent once, whatever the reply
    """
    server = FakeServer(monkeypatch, "")
    stone = "minecraft:stone"
    assert client.setblock(Vec3(1, 2, 3), stone, SetblockMode.DESTROY) == ""
    assert client.fill(Vec3(0, 0, 0), Vec3(1, 1, 1), stone, FillMode.DESTROY) == ""
    a, b, dest = Vec3(0, 0, 0), Vec3(4, 4, 4), Vec3(2, 0, 0)
    for mode in CloneMode:
        assert (
            client.clone(a, b, dest, mask_mode=MaskMode.REPLACE, clone_mode=mode) == ""
        )
    assert len(server.sent) == 2 + len(CloneMode)
    assert server.sent[0] == "setblock 1 2 3 minecraft:stone destroy"
    assert server.sent[1] == "fill 0 0 0 1 1 1 minecraft:stone destroy"
    # other modes are retried
    client.fill(Vec3(0, 0, 0), Vec3(1, 1, 1), stone, FillMode.KEEP)
    assert len(server.sent) == 2 + len(CloneMode) + RCON_ATTEMPTS


def test_appended_output_is_not_merged(monkeypatch: pytest.MonkeyPatch, client: Client):
    """output appended to ours, with no separator, makes the reply retried"""
    FakeServer(
        monkeypatch,
        "Changed the block at 1, 2, 35 players",
        "Changed the block at 1, 2, 3",
    )
    assert client.setblock(Vec3(1, 2, 3), "minecraft:stone") == (
        "Changed the block at 1, 2, 3"
    )
    FakeServer(
        monkeypatch,
        "Dropped 1 [Stone] from loot table minecraft:blocks/stoneThere are 0",
        "Dropped 1 [Stone] from loot table minecraft:blocks/stone\nThere are 0",
    )
    assert get_block(client, Vec3(1, 2, 3)) == Item.STONE


def test_run_raw_returns_errors(monkeypatch: pytest.MonkeyPatch, client: Client):
    """mcipc raises an exception for some errors, run_raw returns them"""
    error = "Incorrect argument for command...ghtCycle<--[HERE]"
    FakeServer(monkeypatch, error)
    with pytest.raises(InvalidArgument):
        client.run("gamerule doDaylightCycle")
    assert client.run_raw("gamerule doDaylightCycle") == error
