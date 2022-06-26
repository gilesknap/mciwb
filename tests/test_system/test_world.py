"""
System tests for the Copy class
"""


from mciwb import Iwb
from mciwb.player import Player
from tests.conftest import ENTITY_NAME
from tests.test_unit.test_world import copy_anchors


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

    # TODO craft the unit test version with mocked client and player

    assert f"player: {ENTITY_NAME}" in mciwb_world.__repr__()


def test_copy_anchors(minecraft_client):
    """
    Runs the unit test copy_anchors() but uses a real client so tests
    against a real minecraft server instead of a mock one.
    """
    copy_anchors()
