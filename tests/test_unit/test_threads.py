"""
Unit tests for the thread helpers and the thread safe RCON Client
"""

import threading
from time import sleep

import pytest
from mcipc.rcon.je.client import Client as McipcClient

from mciwb.threads import Client


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
