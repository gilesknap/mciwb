import importlib
import sys
from typing import Dict

from mcipc.rcon.je import Client
from mcwb import Vec3

from mciwb.copyblock import Copy
from mciwb.player import Player

sys.tracebacklimit = 0


class Iwb:
    """
    Interactive World Builder class. Provides a very simple interface for
    interactive functions.
    """

    def __init__(self, server: str, port: int, passwd: str) -> None:
        self._server = server
        self._port = port
        self._passwd = passwd

        self._client = self.connect(server, port, passwd)

        self.players: Dict[str, Player] = {}
        self.player: Player
        self.copiers: Dict[str, Copy] = {}

    def connect(self, server: str, port: int, passwd: str):
        c = Client(server, int(port), passwd=passwd)
        c.connect(True)
        print(f"Connected to {server} on {port}")
        # don't announce every rcon command
        c.gamerule("sendCommandFeedback", False)

        return c

    def reload_code(self, module):
        module = importlib.reload(module)

    def add_player(self, name: str, me=True):
        player = Player(self._client, name)
        self.players[name] = player
        if me:
            self.player = player
        self.copiers[name] = Copy(self._client, player)
        print(f"Monitoring player {name} enabled for sign commands")

    def stop(self):
        for copier in self.copiers.values():
            copier.stop()

    @property
    def select_pos(self) -> Vec3:
        return self.copiers[self.player.name].start_b
