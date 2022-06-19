from typing import Dict, Optional

from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Direction, Vec3

from mciwb.copier import CopyPaste
from mciwb.monitor import Monitor
from mciwb.player import Player
from mciwb.signs import Signs

world: "Iwb" = None  # type: ignore


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
        self.copiers: Dict[str, CopyPaste] = {}
        self.copier: CopyPaste

        self.sign_monitor = Monitor(self._client)

    def connect(self):
        """
        Makes a connection to the Minecraft Server. Can be called again
        if the connection is lost e.g. due to server reboot.

        Advanced NOTE:
        This class is intended to be a singleton and will be called from the
        Ipython interactive thread. As such it maintains its own
        mcipc.rcon.je.Client for making server calls on this main thread
        """

        c = Client(self._server, int(self._port), passwd=self._passwd)
        c.connect(True)
        print(f"Connected to {self._server} on {self._port}")
        # don't announce every rcon command
        c.gamerule("sendCommandFeedback", False)

        return c

    def add_player(self, name: str, me=True):
        player = Player(self._client, name)
        self.players[name] = player

        sign = Signs(player, self.sign_monitor.poll_client)
        self.sign_monitor.add_poller_func(sign.poll)
        self.copiers[name] = sign.copy

        if me:
            self.player = player
            self.copier = sign.copy

        print(f"Monitoring player {name} enabled for sign commands")

    def stop(self):
        Monitor.stop_all()

    @property
    def selected_position(self) -> Vec3:
        """
        Get the most recent block position on which the player placed a
        'select' sign
        """
        return self.copiers[self.player.name].start_b

    def set_block(self, pos: Vec3, block: Item, facing: Optional[Vec3] = None):
        """
        Sets a block in the world
        """
        pos = Vec3(*pos)
        int_pos = pos.with_ints()
        nbt = []

        if facing:
            nbt.append(f"""facing={Direction.name(facing)}""")
        block_str = f"""{block}[{",".join(nbt)}]"""

        result = self._client.setblock(int_pos, block_str)

        # 'Could not set the block' is not an error - it means it was already set
        if not any(
            x in result for x in ["Changed the block", "Could not set the block"]
        ):
            print("ERROR:", result)

    # TODO FIX THIS
    def __repr__(self) -> str:
        report = (
            "Minecraft Interactive World Builder status:\n"
            "  player: {o.player.name} at {o.player.current_pos}\n"
            "  copy buffer start: {o.copier.start_b}\n"
            "  copy buffer stop: {o.copier.stop_b}\n"
            "  copy buffer size: {o.copier.size}\n"
            "  paste point: {o.copier.paste_b}\n"
        )
        return report.format(o=self)
