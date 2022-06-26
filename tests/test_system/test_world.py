"""
System tests for the Copy class
"""


from mciwb import Iwb
from mciwb.player import Player
from tests.conftest import ENTITY_NAME


def test_session_fixtures(mciwb_world: Iwb, minecraft_player: Player):
    """
    verify that the global session fixtures that create a minecraft server,
    RCON client and mciwb.Player are working
    """
    assert mciwb_world.player.pos == minecraft_player.pos


def test_world_reporting(mciwb_world: Iwb):
    """
    verify printing of the world object
    """

    # TODO craft the unit test version with mocked client and player

    assert f"player: {ENTITY_NAME}" in mciwb_world.__repr__()
