"""
System tests for the Copy class
"""

import logging

from mcipc.rcon.item import Item
from mcwb.types import Anchor3, Vec3

from mciwb.copier import CopyPaste
from mciwb.threads import set_client
from tests.cube import SampleCube
from tests.mockclient import MockClient

# TODO unit test version of this
# def test_world_reporting(mciwb_world: Iwb):
#     """
#     verify printing of the world object
#     """

#     assert f"player: {ENTITY_NAME}" in mciwb_world.__repr__()


def test_copy_anchors():
    client = MockClient("localhost", 20400, "pass")
    set_client(client)  # type: ignore
    copy_anchors()


def copy_anchors():
    """
    Test copy and paste of the same cube using all possible opposite corners
    for a total of 8 pairs of opposite corner pairs (with ordering significant)

    Because the start corner is the anchor for the paste, every paste will
    place the cube offset in a different direction
    """

    copier = CopyPaste()

    t = SampleCube()
    source = Vec3(2, 5, 2)
    t.create(source)

    dest = Vec3(10, 5, 2)

    # try anchoring to each of the 8 corners of the cube
    corner_pairs = (
        ((2, 5, 2), (4, 7, 4), Anchor3.BOTTOM_NW),
        ((4, 5, 2), (2, 7, 4), Anchor3.BOTTOM_NE),
        ((2, 7, 2), (4, 5, 4), Anchor3.TOP_NW),
        ((2, 5, 4), (4, 7, 2), Anchor3.BOTTOM_SW),
        ((4, 7, 2), (2, 5, 4), Anchor3.TOP_NE),
        ((2, 7, 4), (4, 5, 2), Anchor3.TOP_SW),
        ((4, 5, 4), (2, 7, 2), Anchor3.BOTTOM_SE),
        ((4, 7, 4), (2, 5, 2), Anchor3.TOP_SE),
    )
    try:

        for start, stop, anchor in corner_pairs:
            logging.info("copy anchors test: %s, %s, %s", start, stop, anchor)
            copier.select(Vec3(*stop))
            copier.select(Vec3(*start))

            copier.paste_safe(Vec3(*dest))

            try:
                t.test(dest, anchor)
            finally:
                t.clear(dest, anchor)
    finally:
        t.clear(source)


def test_expand():
    client = MockClient("localhost", 20400, "pass")
    set_client(client)  # type: ignore

    copier = CopyPaste()

    start = Vec3(0, 0, 0)
    stop = Vec3(5, 5, 5)
    copier.select(stop)
    copier.select(start)

    copier.expand(x=1, z=2)
    assert copier.start_b == Vec3(0, 0, 0)
    assert copier.stop_b == Vec3(6, 5, 7)

    copier.expand(x=-1, y=-2)
    assert copier.start_b == Vec3(-1, -2, 0)
    assert copier.stop_b == Vec3(6, 5, 7)

    exp = Vec3(0, 20, 20)
    copier.expand_to(exp)
    assert copier.start_b == Vec3(-1, -2, 0)
    assert copier.stop_b == Vec3(6, 20, 20)

    exp = Vec3(-20, -20, -20)
    copier.expand_to(exp)
    assert copier.start_b == Vec3(-20, -20, -20)
    assert copier.stop_b == Vec3(6, 20, 20)


def test_clear():
    client = MockClient("localhost", 20400, "pass")
    set_client(client)  # type: ignore

    copier = CopyPaste()

    client.setblock(Vec3(0, 0, 0), Item.STONE)
    copier.select(Vec3(1, 1, 1))
    copier.select(Vec3(0, 0, 0))

    copier.clear()

    assert client.getblock(Vec3(0, 0, 0)) == Item.AIR
