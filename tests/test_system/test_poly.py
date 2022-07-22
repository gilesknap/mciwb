from mcipc.rcon.enumerations import Item
from mcwb.api import polygon
from mcwb.types import Direction, Vec3

# def test_make_line_xz(minecraft_client):
#     start = Vec3(x=0, y=-60, z=0)

#     left = start + Direction.WEST * 5
#     right = start + Direction.SOUTH * 15
#     make_line_xz(minecraft_client, left, right, Item.STONE)
#     make_line_xz(minecraft_client, right, left, Item.GOLD_BLOCK)
#     make_line_xz(minecraft_client, left, right, Item.AIR)
#     make_line_xz(minecraft_client, right, left, Item.AIR)


def test_poly(minecraft_client):
    center = Vec3(x=0, y=-60, z=0)
    sides = 6
    diameter = 50
    offset = None
    offset = -30
    height = 10
    direction = Direction.NORTH

    item = Item.AIR
    item = Item.GOLD_BLOCK
    polygon(
        minecraft_client,
        center=center,
        sides=sides,
        height=height,
        diameter=diameter,
        item=item,
        offset=offset,
        direction=direction,
    )
