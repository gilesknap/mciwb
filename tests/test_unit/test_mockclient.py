"""
Check that the MockClient behaves like the Minecraft commands it fakes
"""

import pytest

from mciwb.imports import FillMode, Item, Vec3
from tests.mockclient import MockClient


@pytest.mark.parametrize(
    "mode, centre, count",
    [
        (FillMode.HOLLOW, Item.AIR, 27),
        (FillMode.OUTLINE, Item.GOLD_BLOCK, 26),
        (FillMode.KEEP, Item.GOLD_BLOCK, 26),
        (FillMode.REPLACE, Item.STONE, 27),
        (FillMode.DESTROY, Item.STONE, 27),
    ],
)
def test_fill_modes(mock_client: MockClient, mode: FillMode, centre: Item, count):
    """fill a 3x3x3 box around a gold block"""
    mock_client.setblock(Vec3(2, 2, 2), Item.GOLD_BLOCK)

    result = mock_client.fill(Vec3(1, 1, 1), Vec3(3, 3, 3), Item.STONE, mode)

    assert result == f"Successfully filled {count} block(s)"
    assert mock_client.getblock(Vec3(2, 2, 2)) == centre
    assert mock_client.getblock(Vec3(1, 1, 1)) == Item.STONE
    assert mock_client.getblock(Vec3(3, 2, 2)) == Item.STONE
    assert mock_client.getblock(Vec3(4, 2, 2)) == Item.AIR


def test_door_breaks_without_its_top(mock_client: MockClient):
    """a lower door half breaks when the block above it changes"""
    mock_client.setblock(Vec3(1, 1, 1), "minecraft:oak_door[half=lower]")
    mock_client.setblock(Vec3(1, 2, 1), "minecraft:oak_door[half=upper]")
    mock_client.setblock(Vec3(1, 2, 1), Item.STONE)

    assert mock_client.getblock(Vec3(1, 1, 1)) == Item.AIR
