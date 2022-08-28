"""
Represent a player in the world and provide functions for monitoring their
state
"""
import math
import re
from time import sleep
from typing import List, Match, Pattern

from mcwb.types import Direction, Vec3
from mcwb.volume import Volume

from mciwb.logging import log
from mciwb.threads import get_client

regex_coord = re.compile(r"\[(-?\d+.?\d*)d, *(-?\d+.?\d*)d, *(-?\d+.?\d*)d\]")
regex_angle = re.compile(r"-?\ *[0-9]+\.?[0-9]*(?:[Ee]\ *-?\ *[0-9]+)?")


class PlayerNotInWorld(Exception):
    pass


class Player:
    """
    Represent a player in the world and provide functions for monitoring their
    position and direction they are facing.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def _get_entity_data(self, path: str, regex: Pattern[str]) -> Match[str]:
        """
        Get entity data with retries - the remote function sometimes fails to find
        an entity that does exist
        """
        client = get_client()
        for _ in range(5):
            # entity=self.name would not work for the dummy stand used for testing
            data = client.data.get(entity=f"@e[name={self.name},limit=1]", path=path)
            match = regex.search(data)
            if match:
                return match
            else:
                log.debug(f"{self.name} not found: {data}")
            sleep(0.1)

        raise PlayerNotInWorld(f"player {self.name} left")

    @property
    def inventory(self) -> List[str]:
        """
        Get the player's inventory
        """
        # TODO long term this should return a list of Item objects
        # TODO and Item should be extended to allow properties
        return get_client().data.get(entity=self.name, path="Inventory")

    @property
    def pos(self) -> Vec3:
        """
        Return the player's position
        """
        match = self._get_entity_data("Pos", regex_coord)
        pos = Vec3(
            float(match.group(1)), float(match.group(2)), float(match.group(3))
        ).with_ints()
        return pos

    @property
    def facing(self) -> Vec3:
        """
        Return the player's facing direction

        :return: a Vec3 representing the direction the player is facing
            NORTH = Vec3(0, 0, -1)
            SOUTH = Vec3(0, 0, 1)
            EAST = Vec3(1, 0, 0)
            WEST = Vec3(-1, 0, 0)
        """
        match = self._get_entity_data("Rotation", regex_angle)
        angle = float(match.group(0))

        index = int(((math.floor(angle) + 45) % 360) / 90)
        return Direction.cardinals[index]

    def player_in(self, volume: Volume) -> bool:
        """
        Check if the player is inside the Volume

        :param volume: the volume of blocks to check
        """
        return volume.inside(self.pos)

    @classmethod
    def players_in(cls, volume: Volume) -> List["Player"]:
        """
        return a list of player names whose position is inside the Volume
        """

        client = get_client()
        players = []

        names = [p.name for p in client.players.players]
        for name in names:
            try:
                pos = Player(name).pos
                if volume.inside(pos, 2):
                    players.append(name)
            except ValueError:
                pass  # players are sometimes missing temporarily
        return players
