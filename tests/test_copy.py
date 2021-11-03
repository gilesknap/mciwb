"""
System tests for the Copy class
"""

from mcipc.rcon.je import Client
from mcwb.itemlists import grab
from mcwb.types import Anchor3, Cuboid, Vec3
from mcwb.volume import Volume

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
    """

    # TODO only handles one pair currently
    t = TestCube(minecraft_server)
    source = Vec3(2, 5, 2)
    t.create(source)

    start = source
    stop = start + t.size
    dest = Vec3(10, 5, 2)
    minecraft_copy.set_start(*start)
    minecraft_copy.set_stop(*stop)

    minecraft_copy.set_paste(*dest)
    minecraft_copy.paste()

    assert t.test(dest)
