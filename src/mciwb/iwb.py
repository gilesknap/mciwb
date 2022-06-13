import importlib
import sys
from typing import Dict, Optional

from mcipc.rcon.enumerations import SetblockMode
from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Direction, Vec3

from mciwb.copyblock import Copy
from mciwb.player import Player

sys.tracebacklimit = 0


class Iwb:
    """
    Interactive World Builder class. Provides a very simple interface for
    interactive functions for use in an IPython shell.
    """

    def __init__(self, server: str, port: int, passwd: str) -> None:
        self._server = server
        self._port = port
        self._passwd = passwd

        self._client = self.connect()

        self.players: Dict[str, Player] = {}
        self.player: Player
        self.copiers: Dict[str, Copy] = {}

    def connect(self):
        c = Client(self._server, int(self._port), passwd=self._passwd)
        c.connect(True)
        print(f"Connected to {self._server} on {self._port}")
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
        print("Stopped monitoring all players for sign commands")

    @property
    def select_pos(self) -> Vec3:
        return self.copiers[self.player.name].start_b

    def set_block(self, pos: Vec3, block: Item, facing: Optional[Vec3] = None):
        int_pos = pos.with_ints()
        nbt = []

        if facing:
            nbt.append(f"""facing={Direction.name(facing)}""")
        block_str = f"""{block.value}[{",".join(nbt)}]"""

        block_str = block.value
        result = self._client.setblock(int_pos, block_str, SetblockMode.REPLACE)

        # 'Could not set the block' is no error - means it was already set
        if not any(
            x in result for x in ["Changed the block", "Could not set the block"]
        ):
            print(result)
