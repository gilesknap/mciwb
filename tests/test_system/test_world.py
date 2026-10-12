"""
System tests for the Iwb world object
"""

from mcwb import Vec3, Volume

from mciwb.imports import Direction, Item, Iwb, Player, get_client
from mciwb.signs import Signs
from tests.conftest import ENTITY_NAME
from tests.test_system.helpers import is_block, wait_until


def test_session_fixtures(mciwb_world: Iwb, minecraft_player: Player):
    """
    verify that the global session fixtures that create a minecraft server,
    RCON client and mciwb.Player are working
    """
    assert mciwb_world.player.pos == minecraft_player.pos


def test_world_reporting(mciwb_world: Iwb):
    """
    verify printing of the world object
    """
    assert f"player: {ENTITY_NAME}" in mciwb_world.__repr__()


def test_set_get_block(mciwb_world: Iwb):
    pos = Vec3(5, -60, 5)
    try:
        assert mciwb_world.set_block(pos, Item.OAK_STAIRS, facing=Direction.EAST)
        assert mciwb_world.get_block(pos) == Item.OAK_STAIRS
        assert is_block(pos, "minecraft:oak_stairs[facing=east]")
        assert "Changed" in mciwb_world.cmd(f"setblock {pos.x} {pos.y} {pos.z} air")
    finally:
        mciwb_world.set_block(pos, Item.AIR)


def test_world_player_signs(mciwb_world: Iwb, minecraft_player: Player):
    """
    verify that placing select/expand/paste signs copies blocks
    """

    client = get_client()
    p = minecraft_player.pos

    def place_sign(pos: Vec3, text: str):
        """place a command sign and wait for the world's monitor to use it"""
        client.setblock(pos, Signs.sign_block(text))
        assert wait_until(lambda: is_block(pos, Item.AIR)), f"{text} sign not used"

    try:
        # the player faces south, standing signs target the block below them
        # select the grass below the sign as both corners of the copy buffer
        place_sign(p + Direction.SOUTH * 3, "select")
        # expand the buffer to the grass below this sign
        place_sign(p + Direction.SOUTH, "expand")
        # paste the 3 grass blocks one block up, starting at the paste sign
        place_sign(p + Direction.SOUTH * 2 + Direction.UP, "paste")

        # the paste happens just after the sign is removed
        target = p + Direction.SOUTH * 2
        assert wait_until(lambda: is_block(target, Item.GRASS_BLOCK))
    finally:
        # clear everything above the ground in front of the player
        Volume.from_corners(
            p + Direction.SOUTH, p + Direction.SOUTH * 4 + Direction.UP * 2
        ).fill(client, Item.AIR)
