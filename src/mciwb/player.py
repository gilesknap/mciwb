"""
Represent a player in the world and provide functions for monitoring their
state
"""

import math
import re
from re import Match, Pattern
from time import sleep

from mcipc.rcon.types import Rotation
from mcwb.types import Direction, Vec3
from mcwb.volume import Volume

from mciwb.logging import log
from mciwb.threads import get_client

regex_coord = re.compile(r"\[(-?\d+.?\d*)d, *(-?\d+.?\d*)d, *(-?\d+.?\d*)d\]")
float_reg = r"(-?\ *[0-9]+\.?[0-9]*(?:[Ee]\ *-?\ *[0-9]+)?)f"
regex_angle = re.compile(float_reg)
regex_rot = re.compile(r"\[(-?\d+.?\d*)f, *(-?\d+.?\d*)f\]")


class PlayerNotInWorldError(Exception):
    """The player (or named entity) could not be found in the world."""


class Player:
    """
    Represent a player in the world and provide functions for monitoring their
    position and direction they are facing.

    Creating a Player only reads from the world. Call `setup` to make the
    player an operator in creative mode (`Iwb.add_player` does this).

    :param name: the name of the player, or the CustomName of any other entity
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def setup(self) -> None:
        """
        Make the player an operator in creative mode, so that they can use
        command signs and build freely.
        """
        client = get_client()
        client.op(self.name)
        client.gamemode("creative", self.name)

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

        raise PlayerNotInWorldError(f"player {self.name} left")

    @property
    def inventory(self) -> list[str]:
        """
        Get the player's inventory
        """
        # TODO long term this should return a list of Item objects
        # TODO and Item should be extended to allow properties
        return get_client().data.get(entity=self.name, path="Inventory")

    @property
    def pos_f(self) -> Vec3:
        """
        Return the player's precise position
        """
        match = self._get_entity_data("Pos", regex_coord)
        return Vec3(float(match.group(1)), float(match.group(2)), float(match.group(3)))

    @property
    def pos(self) -> Vec3:
        """
        Return the player's block position
        """
        return self.pos_f.with_ints()

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
        angle = float(match.group(1))

        index = int(((math.floor(angle) + 45) % 360) / 90)
        return Direction.cardinals()[index]

    @property
    def rotation(self) -> Rotation:
        """
        Get the player's rotation in degrees
        """
        match = self._get_entity_data("Rotation", regex_rot)
        # TODO how to coerce this?
        return float(match.group(1)), float(match.group(2))  # type: ignore

    def player_in(self, volume: Volume) -> bool:
        """
        Check if the player is inside the Volume

        :param volume: the volume of blocks to check
        """
        return volume.inside(self.pos)

    @classmethod
    def players_in(cls, volume: Volume) -> list[str]:
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
            except PlayerNotInWorldError:
                pass  # players are sometimes missing temporarily
        return players
