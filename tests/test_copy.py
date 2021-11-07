"""
System tests for the Copy class
"""

from mcipc.rcon.je import Client
from mcwb.types import Anchor3, Vec3

from mciwb.copy import Copy
from mciwb.player import Player
from tests.conftest import ENTITY_NAME
from tests.cube import TestCube


def test_session_fixtures(minecraft_copy: Copy, minecraft_player: Player):
    """
    verify that the global session fixtures that create a minecraft server,
    RCON client and mciwb.Player are working
    """
    assert minecraft_copy.player.pos() == minecraft_player.pos()


def test_copy_reporting(minecraft_copy: Copy):
    """
    verify printing of the Copy object
    """
    assert (
        f"player: {ENTITY_NAME} at Vec3(x=0.5, y=4.0, z=0.5)"
        in minecraft_copy.__repr__()
    )


def test_copy_anchors(minecraft_copy: Copy, minecraft_server: Client):
    """
    Test copy and paste of the same cube using all possible opposite corners
    for a total of 8 pairs of opposite corner pairs (with ordering significant)

    Because the start corner is the anchor for the paste, every paste will
    place the cube offset in a different direction
    """

    # When running under github actions the poller and main thread seem to
    # mix up each others responses so turn off polling for this test.
    minecraft_copy.polling = False

    t = TestCube(minecraft_server)
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
            print(start, stop)
            minecraft_copy.set_start(*start)
            minecraft_copy.set_stop(*stop)

            minecraft_copy.set_paste(*dest)
            minecraft_copy.paste()

            try:
                assert t.test(dest, anchor)
            finally:
                t.clear(dest, anchor)
    finally:
        t.clear(source)
