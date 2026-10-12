import pytest

from mciwb.imports import Direction, Item, Vec3, Wall
from tests.mockclient import MockClient


def test_wall_needs_height_or_profile():
    with pytest.raises(ValueError):
        Wall()


def test_plain_wall(mock_client: MockClient):
    wall = Wall(height=3, item=Item.STONE)
    wall.set_start(Vec3(0, 0, 0))
    wall.draw(Vec3(4, 0, 0))

    # walls are built on top of the start and end blocks
    for x in range(5):
        for y in range(1, 4):
            assert mock_client.getblock(Vec3(x, y, 0)) == Item.STONE
        assert mock_client.getblock(Vec3(x, 4, 0)) == Item.AIR
    assert mock_client.getblock(Vec3(5, 1, 0)) == Item.AIR


def test_profile_wall(mock_client: MockClient):
    # two alternating columns, listed from the top down. The second column
    # is 2 blocks thick at the bottom
    profile = [
        [Item.STONE, Item.STONE],
        [Item.AIR, [Item.OAK_PLANKS, Item.GLASS]],
    ]
    wall = Wall(profile=profile)
    wall.set_start(Vec3(0, 0, 0))
    wall.draw(Vec3(0, 0, 3))  # draw south

    assert mock_client.getblock(Vec3(0, 1, 0)) == Item.STONE
    assert mock_client.getblock(Vec3(0, 2, 0)) == Item.STONE
    assert mock_client.getblock(Vec3(0, 1, 1)) == Item.OAK_PLANKS
    assert mock_client.getblock(Vec3(0, 2, 1)) == Item.AIR
    # thickness extends to the right of the drawing direction (west of south)
    assert mock_client.getblock(Vec3(-1, 1, 1)) == Item.GLASS
    assert mock_client.getblock(Vec3(0, 1, 2)) == Item.STONE


def test_connected_walls(mock_client: MockClient):
    wall = Wall(height=1)
    wall.set_start(Vec3(0, 0, 0))
    wall.draw(Vec3(2, 0, 0))
    wall.draw(Vec3(2, 0, 2))

    corner = Vec3(2, 1, 0)
    assert mock_client.getblock(corner) == Item.STONE
    assert mock_client.getblock(corner + Direction.SOUTH * 2) == Item.STONE


def test_draw_needs_start(mock_client: MockClient):
    with pytest.raises(ValueError):
        Wall(height=1).draw(Vec3(1, 0, 0))
