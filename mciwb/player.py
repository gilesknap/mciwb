import re

from mcipc.rcon.je import Client
from mcwb import Vec3, Volume
from mcwb.types import Direction

regex_coord = re.compile(r"\[(-?\d+.?\d*)d, *(-?\d+.?\d*)d, *(-?\d+.?\d*)d\]")


class Player:
    def __init__(self, client: Client, name: str) -> None:
        # todo might make a player with threaded monitoring if needed ?
        self.client = client
        self.running = False
        self.name = name
        self.current_pos = Vec3(0, 0, 0)
        self.current_dir = Direction.NORTH
        self.dir()

    def pos(self) -> Vec3:
        data = self.client.data.get(entity=self.name, path="Pos")
        match = regex_coord.search(data)
        if match:
            self.current_pos = Vec3(
                float(match.group(1)), float(match.group(2)), float(match.group(3))
            )
            return self.current_pos

        raise ValueError(f"player {self.name} does not exist")

    def dir(self, client: Client = None) -> Direction:
        # if called in a thread then use the thread's client object
        client = client or self.client
        start = -45
        for dir in [Direction.SOUTH, Direction.WEST, Direction.NORTH, Direction.EAST]:
            stop = start + 90
            entity = f"@p[y_rotation={start}..{stop},name={self.name}]"
            data = client.data.get(entity=entity, path="Pos")
            match = regex_coord.search(data)
            if match:
                self.current_pos = Vec3(
                    float(match.group(1)), float(match.group(2)), float(match.group(3))
                )
                self.current_dir = dir
                return dir
            start += 90

        raise ValueError(f"player {self.name} does not exist")

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
