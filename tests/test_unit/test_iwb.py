"""
Unit tests for the Iwb world object, connected to a MockClient
"""

from pathlib import Path

import pytest
from mcipc.rcon.exceptions import NoPlayerFound

import mciwb.iwb
from mciwb.imports import (
    Anchor3,
    Direction,
    Item,
    Iwb,
    Vec3,
    Volume,
    WallMaker,
    get_world,
)
from tests.conftest import ENTITY_NAME
from tests.mockclient import MockClient


@pytest.fixture()
def world(mock_client: MockClient, monkeypatch: pytest.MonkeyPatch):
    # Iwb makes its own client, make it a MockClient on the same mock server
    monkeypatch.setattr(mciwb.iwb, "Client", MockClient)
    world = Iwb(mock_client.host, mock_client.port, "pass")
    yield world
    world.stop()


def test_connect(world: Iwb, mock_client: MockClient):
    assert get_world() is world
    assert mock_client.gamerules["send_command_feedback"] is False
    assert "no players" in repr(world)


def test_set_get_block(world: Iwb, mock_client: MockClient):
    pos = Vec3(1, 2, 3)
    assert world.set_block(pos, Item.GOLD_BLOCK)
    assert world.get_block(pos) == Item.GOLD_BLOCK
    assert mock_client.getblock(pos) == Item.GOLD_BLOCK


def test_set_block_does_not_change_nbt(world: Iwb, mock_client: MockClient):
    nbt = ["half=bottom"]
    for x in range(3):
        world.set_block(Vec3(x, 0, 0), Item.OAK_STAIRS, Direction.EAST, nbt=nbt)

    assert nbt == ["half=bottom"]
    assert mock_client.states[(2, 0, 0)] == "half=bottom,facing=east"


def test_set_block_failure(world: Iwb, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        MockClient, "setblock", lambda *args, **kwargs: "Unknown block type"
    )
    assert not world.set_block(Vec3(0, 0, 0), "minecraft:not_a_block")  # type: ignore


def test_place_door(world: Iwb, mock_client: MockClient):
    world.place_door(Vec3(0, 0, 0), Item.OAK_DOOR, Direction.SOUTH, right_hinge=True)

    assert mock_client.getblock(Vec3(0, 0, 0)) == Item.OAK_DOOR
    assert mock_client.getblock(Vec3(0, 1, 0)) == Item.OAK_DOOR
    assert mock_client.states[(0, 1, 0)] == (
        "half=upper,hinge=right,open=false,facing=south"
    )
    with pytest.raises(ValueError):
        world.place_door(Vec3(0, 0, 0), Item.STONE)


def test_cmd(world: Iwb, mock_client: MockClient):
    world.cmd("time set day")
    assert mock_client.commands[-1] == "time set day"


def test_add_player(world: Iwb, mock_client: MockClient):
    world.add_player(ENTITY_NAME)

    assert world.players == [ENTITY_NAME]
    assert world.player is world.get_player(ENTITY_NAME)
    assert world.copier is world.signs.copy
    # the player was given the command signs
    assert {target for target, _ in mock_client.given} == {ENTITY_NAME}
    assert f"player: {ENTITY_NAME}" in repr(world)
    assert "position: Vec3(x=0, y=-60, z=0)" in repr(world)


def test_add_player_not_a_real_player(
    world: Iwb, mock_client: MockClient, monkeypatch: pytest.MonkeyPatch
):
    """
    a named entity standing in for a player cannot be given items, but is
    still monitored for sign commands
    """

    def give(target: str, item: str):
        raise NoPlayerFound("No player was found")

    monkeypatch.setattr(mock_client, "give", give)
    world.add_player(ENTITY_NAME)

    assert world.players == [ENTITY_NAME]
    assert world.player is world.get_player(ENTITY_NAME)


def test_save_load(world: Iwb, mock_client: MockClient, tmp_path: Path):
    file = tmp_path / "blocks.json"
    mock_client.setblock(Vec3(0, 0, 0), Item.STONE)
    mock_client.setblock(Vec3(1, 1, 1), Item.GLASS)
    world.save(file, Volume.from_corners(Vec3(0, 0, 0), Vec3(1, 1, 1)))

    world.add_player(ENTITY_NAME)
    world.load(file, Vec3(10, 0, 0), Anchor3.BOTTOM_NW)

    assert mock_client.getblock(Vec3(10, 0, 0)) == Item.STONE
    assert mock_client.getblock(Vec3(11, 1, 1)) == Item.GLASS
    # the copy buffer is now the loaded blocks
    vol = world.copier.to_volume()
    assert vol.start == Vec3(10, 0, 0)
    assert vol.end == Vec3(11, 1, 1)
    assert world.copier.paste_pos == Vec3(10, 0, 0)


def test_save_load_need_copy_buffer(world: Iwb, tmp_path: Path):
    with pytest.raises(ValueError, match="copy buffer"):
        world.save(tmp_path / "blocks.json")
    with pytest.raises(ValueError, match="copy buffer"):
        world.load(tmp_path / "blocks.json")


def test_wall_maker(world: Iwb, mock_client: MockClient):
    world.add_player(ENTITY_NAME)
    maker = WallMaker()

    assert {WallMaker.start, WallMaker.end} <= set(world.signs.signs)
    world.signs.do_action(WallMaker.start, Vec3(0, 0, 0), Vec3(0, 5, 0))
    world.signs.do_action(WallMaker.end, Vec3(2, 0, 0), Vec3(0, 5, 0))
    assert mock_client.getblock(Vec3(2, 3, 0)) == Item.STONE

    maker.remove()
    assert WallMaker.start not in world.signs.signs
