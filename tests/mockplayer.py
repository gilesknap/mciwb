from mcwb.types import Vec3

from mciwb import Direction
from tests.mockclient import MockClient


class MockPlayer:
    def __init__(self, client: MockClient, name: str) -> None:
        pass

    @property
    def pos(self) -> Vec3:
        return Vec3(0, 0, 0)

    @property
    def facing(self) -> Vec3:
        return Direction.NORTH

    def _pos(self, client=None) -> Vec3:
        return self._pos()

    def _facing(self, client=None) -> Vec3:
        return self._facing()
