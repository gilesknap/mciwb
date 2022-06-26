"""
System tests for the Copy class
"""

import logging

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
