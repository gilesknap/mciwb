from mcwb import Item, Volume
from mcwb.api import polygon
from mcwb.itemlists import grab
from mcwb.types import Direction, Vec3

from mciwb.threads import get_client
from tests.test_system.helpers import is_block


def test_poly():
    client = get_client()
    # away from the test entity, inside the chunks forceloaded for tests
    center = Vec3(x=20, y=-60, z=20)
    height = 3
    corner = Vec3(-7, 0, -7)
    area = Volume.from_corners(center + corner, center - corner + Vec3(0, height, 0))

    def layer(y: int) -> list[Item]:
        start = center + corner + Direction.UP * y
        blocks = grab(client, Volume.from_corners(start, start - corner * 2))
        return [item for plane in blocks for row in plane for item in row]

    try:
        polygon(
            client,
            center=center,
            sides=6,
            height=height,
            diameter=9,
            item=Item.GOLD_BLOCK,
            direction=Direction.UP,
        )

        # the bottom and top layers are a hollow ring of gold
        for y in (0, height - 1):
            blocks = layer(y)
            assert set(blocks) == {Item.GOLD_BLOCK, Item.AIR}
            assert blocks.count(Item.GOLD_BLOCK) >= 6
            assert is_block(center + Direction.UP * y, Item.AIR)
        # and nothing is built above the top layer
        assert set(layer(height)) == {Item.AIR}
    finally:
        area.fill(client, Item.AIR)
