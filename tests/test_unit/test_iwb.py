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
from mciwb.monitor import Monitor
from tests.anvil_writer import write_world
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

    def give(self, target: str, item: str):
        raise NoPlayerFound()

    # patch the class, as Iwb uses its own MockClient
    monkeypatch.setattr(MockClient, "give", give)
    world.add_player(ENTITY_NAME)

    assert world.players == [ENTITY_NAME]
    assert world.player is world.get_player(ENTITY_NAME)


def test_add_player_not_found_warning(
    world: Iwb,
    mock_client: MockClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """mcipc's NoPlayerFound has no message, so the warning supplies a reason"""

    def give(self, target: str, item: str):
        raise NoPlayerFound()

    # patch the class, as Iwb uses its own MockClient
    monkeypatch.setattr(MockClient, "give", give)
    world.add_player("bob", setup=False)

    assert (
        "could not set up or give signs to bob, player not found in the world"
        in caplog.text
    )


@pytest.fixture()
def default_world(
    mock_client: MockClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """An Iwb that thinks it is connected to the default mciwb server"""
    monkeypatch.setattr(mciwb.iwb, "Client", MockClient)
    monkeypatch.setattr(mciwb.iwb, "def_port", mock_client.port)
    monkeypatch.setattr(mciwb.iwb, "default_server_folder", tmp_path / "server")
    monkeypatch.setattr(mciwb.iwb, "backup_folder_default", tmp_path / "backups")

    def make() -> Iwb:
        return Iwb(mock_client.host, mock_client.port, "pass")

    yield make
    Monitor.stop_all()


def test_backup_no_world(default_world, caplog: pytest.LogCaptureFixture):
    """With no world in the default server folder, backups are disabled"""
    world = default_world()
    assert "backups disabled" in caplog.text

    caplog.clear()
    world.backup()
    assert "no backup available" in caplog.text


def test_backup_default_server(default_world, tmp_path: Path):
    world_folder = tmp_path / "server" / "world"
    world_folder.mkdir(parents=True)
    (world_folder / "level.dat").write_text("level")

    world = default_world()
    world.backup(name="saved")

    assert (tmp_path / "backups" / "saved.zip").exists()


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


def test_scan_and_render_rcon(world: Iwb, mock_client: MockClient, tmp_path: Path):
    """with no world folder, blocks are read over RCON"""
    mock_client.setblock(Vec3(1, 1, 1), Item.GOLD_BLOCK)
    assert world.world_folder is None

    grid = world.scan(Vec3(0, 0, 0), Vec3(2, 2, 2))
    assert grid.counts() == {"minecraft:gold_block": 1}

    file = tmp_path / "render.png"
    grid = world.render(Vec3(2, 2, 2), Vec3(0, 0, 0), file, views=["top"])
    assert grid.origin == Vec3(0, 0, 0)
    assert file.exists()


def test_scan_default_server(default_world, mock_client: MockClient, tmp_path: Path):
    """the default server's world is read from its files"""
    world_folder = write_world(
        tmp_path / "server" / "world", {(1, 2, 3): "minecraft:gold_block"}
    )
    world = default_world()
    assert world.world_folder == world_folder

    grid = world.scan(Vec3(0, 2, 3), Vec3(2, 2, 3))

    assert grid[Vec3(1, 2, 3)] == "minecraft:gold_block"
    assert "save-all flush" in mock_client.commands


def test_scan_mciwb_server_other_port(
    default_world, mock_client: MockClient, monkeypatch: pytest.MonkeyPatch, tmp_path
):
    """mciwb start --port N still uses the default folder: find it by its port"""
    monkeypatch.setattr(mciwb.iwb, "def_port", mock_client.port + 100)
    world_folder = write_world(
        tmp_path / "server" / "world", {(1, 2, 3): "minecraft:gold_block"}
    )
    assert default_world().world_folder is None

    properties = tmp_path / "server" / "server.properties"
    properties.write_text(f"motd=hi\nrcon.port={mock_client.port}\n")
    world = default_world()
    assert world.world_folder == world_folder

    grid = world.scan(Vec3(0, 2, 3), Vec3(2, 2, 3))
    assert grid[Vec3(1, 2, 3)] == "minecraft:gold_block"
    assert "save-all flush" in mock_client.commands
