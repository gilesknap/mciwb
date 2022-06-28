from mcwb.types import Vec3
from mcwb.volume import Volume

from mciwb.player import Player
from tests.conftest import ENTITY_NAME


def test_players_in(mock_client):
    """
    verify that the players_in function returns a list of players
    """
    v = Volume.from_corners(Vec3(-10, -60, -10), Vec3(10, -60, 10))
    players = Player.players_in(v)
    assert len(players) == 1
    assert players[0] == ENTITY_NAME

    v = Volume.from_corners(Vec3(3, 3, 3), Vec3(10, 10, 10))
    players = Player.players_in(v)
    assert len(players) == 0


def test_player_in(mock_client, minecraft_player: Player):
    """
    verify that the player_in function returns True if the player is in the volume
    """
    v = Volume.from_corners(Vec3(-10, -1, -10), Vec3(10, -60, 10))
    assert minecraft_player.player_in(v)

    v = Volume.from_corners(Vec3(3, 3, 3), Vec3(10, -60, 10))
    assert not minecraft_player.player_in(v)
