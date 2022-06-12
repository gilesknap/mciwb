import sys
from typing import Dict

from mcipc.rcon.je import Client

from mciwb.copyblock import Copy
from mciwb.player import Player

sys.tracebacklimit = 0

cmd = None


class Iwb:
    """
    Interactive World Builder class. Provides a very simple interface for
    interactive functions. Intended to be a singleton in an Ipython session
    accessed through the global 'cmd'
    """

    def __init__(self, server: str, port: int, passwd: str) -> None:
        global cmd
        if cmd is not None:
            raise RuntimeError("Iwb object cmd already created")
        self._server = server
        self._port = port
        self._passwd = passwd

        cmd = self._client = self.connect(server, port, passwd)

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
