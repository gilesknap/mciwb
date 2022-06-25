"""
System tests for the Copy class
"""

import logging

from mcipc.rcon.je import Client
from mcwb.types import Anchor3, Vec3

from mciwb.copier import CopyPaste
from mciwb.iwb import Iwb, Monitor
from mciwb.player import Player
from tests.conftest import ENTITY_NAME
from tests.cube import SampleCube


def test_session_fixtures(mciwb_world: Iwb, minecraft_player: Player):
    """
    verify that the global session fixtures that create a minecraft server,
    RCON client and mciwb.Player are working
    """
    assert isinstance(mciwb_world.player, Player)
    assert mciwb_world.player.pos == minecraft_player._pos()


def test_world_reporting(mciwb_world: Iwb):
    """
    verify printing of the world object
    """

    assert f"player: {ENTITY_NAME}" in mciwb_world.__repr__()


def test_copy_anchors(mciwb_world: Iwb, minecraft_client: Client):
    """
    Test copy and paste of the same cube using all possible opposite corners
    for a total of 8 pairs of opposite corner pairs (with ordering significant)

    Because the start corner is the anchor for the paste, every paste will
    place the cube offset in a different direction
    """
    assert isinstance(mciwb_world.copier, CopyPaste)

    t = SampleCube(mciwb_world.sign_monitor.poll_client)
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
            mciwb_world.copier.select(Vec3(*stop))
            mciwb_world.copier.select(Vec3(*start))

            # stop polling to avoid the issue below
            Monitor.stop_all()
            # use the Monitor poller thread to avoid race conditions with
            # the sign polling - this does not work and sometimes the
            # call to the server never returns
            mciwb_world.copier.paste_safe(
                Vec3(*dest), mciwb_world.sign_monitor.poll_client
            )

            try:
                assert t.test(dest, anchor)
            finally:
                t.clear(dest, anchor)
    finally:
        t.clear(source)