"""
System tests for the Copy class
"""

from tests.conftest import ENTITY_NAME

from mcipc.rcon.je import Client

from mciwb.copy import Copy
from mciwb.player import Player


def test_session_fixtures(minecraft_server: Client, minecraft_player: Player):
    # verify that the global session fixtures that create a minecraft server,
    # RCON client and mciwb.Player are working
    cp = Copy(minecraft_server, ENTITY_NAME)
    assert cp.player.pos() == minecraft_player.pos()
    cp.polling = False


def test_copy_reporting(minecraft_server: Client):
    cp = Copy(minecraft_server, ENTITY_NAME)
    assert "player: george at Vec3(x=0.5, y=4.0, z=0.5)" in cp.__repr__()
    cp.polling = False
