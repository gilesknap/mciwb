from typing import List

from mcwb.types import Vec3
from mcwb.volume import Volume

from mciwb import Direction
from tests.conftest import ENTITY_NAME
from tests.mockclient import MockClient


class MockPlayer:
    def __init__(self, client: MockClient, name: str) -> None:
        self.name = ENTITY_NAME

    @property
    def pos(self) -> Vec3:
        return Vec3(0, 0, 0)

    @property
    def facing(self) -> Vec3:
        return Direction.SOUTH

    def _pos(self, client=None) -> Vec3:
        return self._pos()

    def _facing(self, client=None) -> Vec3:
        return self._facing()

    def player_in(self, volume: Volume) -> bool:
        """
        Check if the player is in the volume
        """
        return volume.inside(self.pos)

    @classmethod
    def players_in(cls, volume: Volume) -> List["MockPlayer"]:
        """
        return a list of player names whose position is inside the volume
        """
        return []
