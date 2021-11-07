import math
import re
from typing import Match, Pattern

from mcipc.rcon.je import Client
from mcwb import Vec3, Volume
from mcwb.types import Direction

regex_coord = re.compile(r"\[(-?\d+.?\d*)d, *(-?\d+.?\d*)d, *(-?\d+.?\d*)d\]")
regex_angle = re.compile(r"-?\ *[0-9]+\.?[0-9]*(?:[Ee]\ *-?\ *[0-9]+)?")


class Player:
    def __init__(self, client: Client, name: str) -> None:
        # todo might make a player with threaded monitoring if needed ?
        self.client = client
        self.running = False
        self.name = name
        self.current_pos = Vec3(0, 0, 0)
        self.current_dir = Direction.NORTH
        self.dir()

    def _get_entity_data(
        self, client: Client, path: str, regex: Pattern[str]
    ) -> Match[str]:
        """
        Get entity data with retries - the remote function sometimes fails to find
        an entity that does exist
        """
        for retry in range(5):
            data = client.data.get(entity=f"@e[name={self.name},limit=1]", path=path)
            match = regex.search(data)
            if match:
                return match

        raise ValueError(f"player {self.name} not in the world")

    def pos(self, client: Client = None) -> Vec3:
        # if called in a thread then use the thread's client object
        client = client or self.client
        match = self._get_entity_data(client, "Pos", regex_coord)
        self.current_pos = Vec3(
            float(match.group(1)), float(match.group(2)), float(match.group(3))
        )
        return self.current_pos

    def dir(self, client: Client = None) -> Direction:
        # if called in a thread then use the thread's client object
        client = client or self.client
        self.pos(client)
        match = self._get_entity_data(client, "Rotation", regex_angle)
        angle = float(match.group(0))

        dirs = [Direction.SOUTH, Direction.WEST, Direction.NORTH, Direction.EAST]
        index = int(((math.floor(angle) + 45) % 360) / 90)
        return dirs[index]

    @classmethod
    def players_in(cls, client: Client, volume: Volume):
        """return a list of player names whose position is inside the volume"""
        players = []

        names = [p.name for p in client.players.players]
        for name in names:
            try:
                pos = Player(client, name).pos()
                if volume.inside(pos, 2):
                    players.append(name)
            except ValueError:
                pass  # players are sometimes missing temporarily
        return players
