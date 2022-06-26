import logging
from typing import Dict, Optional

from mcipc.rcon.exceptions import NoPlayerFound
from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Direction, Vec3
from rcon.exceptions import SessionTimeout

from mciwb.copier import CopyPaste
from mciwb.monitor import Monitor
from mciwb.player import Player
from mciwb.signs import Signs
from mciwb.threads import get_client, set_client

world: "Iwb" = None  # type: ignore


class Iwb:
    """
    Interactive World Builder class. Provides a very simple interface for
    interactive functions for use in an IPython shell.
    """

    def __init__(self, server: str, port: int, passwd: str, client=None) -> None:
        self._server = server
        self._port = port
        self._passwd = passwd

        client = client or self.connect()

        self.players: Dict[str, Player] = {}
        self.player: Player = None  # type: ignore
        self.copiers: Dict[str, CopyPaste] = {}
        self.copier: CopyPaste = None  # type: ignore

        self.sign_monitor = Monitor()

    def connect(self) -> Client:
        """
        Makes a connection to the Minecraft Server. Can be called again
        if the connection is lost e.g. due to server reboot.
        """

        client = Client(self._server, int(self._port), passwd=self._passwd)
        client.connect(True)

        # store the client for the main thread
        set_client(client)

        logging.info(f"Connected to {self._server} on {self._port}")
        # don't announce every rcon command
        client.gamerule("sendCommandFeedback", False)

        return client

    def add_player(self, name: str, me=True):
        player = Player(name)
        self.players[name] = player

        sign = Signs(player)
        self.sign_monitor.add_poller_func(sign.poll)
        self.copiers[name] = sign.copy

        if me:
            self.player = player
            self.copier = sign.copy

        try:
            sign.give_signs()
        except (NoPlayerFound, SessionTimeout) as e:
            # during tests this will fail as there is no real player
            logging.warning("failed to give signs to player, %s", e)

        logging.info(f"Monitoring player {name} enabled for sign commands")

    def stop(self):
        Monitor.stop_all()

    @property
    def selected_position(self) -> Vec3:
        """
        Get the most recent block position on which the player placed a
        'select' sign
        """
        if self.player is None:
            raise RuntimeError("No player selected")
        return self.copiers[self.player.name].start_b

    def set_block(self, pos: Vec3, block: Item, facing: Optional[Vec3] = None):
        """
        Sets a block in the world
        """
        client = get_client()

        pos = Vec3(*pos)
        int_pos = pos.with_ints()
        nbt = []

        if facing:
            nbt.append(f"""facing={Direction.name(facing)}""")
        block_str = f"""{block}[{",".join(nbt)}]"""

        result = client.setblock(int_pos, block_str)
        logging.debug("setblock: " + result)

        # 'Could not set the block' is not an error - it means it was already set
        if not any(
            x in result for x in ["Changed the block", "Could not set the block", ""]
        ):
            logging.error(result)

    def __repr__(self) -> str:
        report = "Minecraft Interactive World Builder status:\n"
        if self.copier is not None:
            report += (
                "  copy buffer start: {o.copier.start_b}\n"
                "  copy buffer stop: {o.copier.stop_b}\n"
                "  copy buffer size: {o.copier.size}\n"
                "  paste point: {o.copier.paste_b}\n"
            )
        if self.player is not None:
            report += (
                "  player: {o.player.name}\n"
                "  player position: {o.player.pos}\n"
                "  player facing: {o.player.facing}\n"
            )
        else:
            report += "  no player selected\n"

        return report.format(o=self)
