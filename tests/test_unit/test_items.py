"""Unit tests for the mcwb dependency surface that mciwb relies on."""

from mciwb.imports import Direction, Item
from mciwb.wall import Wall


def test_modern_items():
    # mcwb.Item covers blocks added after mcipc's enum (Minecraft 1.16)
    assert Item("deepslate") is Item.DEEPSLATE
    assert Item.PALE_OAK_LOG == "minecraft:pale_oak_log"
    assert str(Item.CHERRY_PLANKS) == "minecraft:cherry_planks"


def test_wall_rotation():
    # Direction.cardinals became a method (classmethod properties were removed
    # in Python 3.13)
    wall = Wall(profile=[Item.STONE])
    assert wall._rot_left(Direction.NORTH) == Direction.WEST
    assert wall._rot_right(Direction.NORTH) == Direction.EAST
    assert wall._rot_right(Direction.EAST) == Direction.SOUTH
