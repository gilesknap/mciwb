import logging
from pathlib import Path
from typing import Dict, Optional

from mcipc.rcon.exceptions import NoPlayerFound
from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Anchor3, Blocks, Direction, Vec3, Volume
from mcwb.itemlists import grab, load_items, save_items
from rcon.exceptions import SessionTimeout

from mciwb.backup import Backup
from mciwb.copier import CopyPaste
from mciwb.monitor import Monitor
from mciwb.player import Player, PlayerNotInWorld
from mciwb.server import HOST, def_port
from mciwb.signs import Signs
from mciwb.threads import get_client, set_client

world: "Iwb" = None  # type: ignore


def get_world():
    return Iwb.the_world


class Iwb:
    """
    Interactive World Builder class. Provides a very simple interface for
    interactive functions for use in an IPython shell.
    """

    the_world: "Iwb" = None  # type: ignore

    def __init__(self, server: str, port: int, passwd: str, client=None) -> None:
        if self.the_world is not None:
            raise RuntimeError("only one world can be created")

        Iwb.the_world = self

        self._server = server
        self._port = port
        self._passwd = passwd

        client = client or self.connect()

        self.player: Player = None  # type: ignore
        self.copier: CopyPaste = None  # type: ignore
        self.signs: Signs = None  # type: ignore

        self._players: Dict[str, Player] = {}
        self._copiers: Dict[str, CopyPaste] = {}

        # if we are using the default server created by mciwb then we know
        # where the folders are for doing backups
        if server == HOST and port == def_port:
            self._backup: Optional[Backup] = Backup()
        else:
            self._backup = None

    def backup(self, name=None) -> None:
        if self._backup is None:
            logging.warning("no backup available")
        else:
            self._backup.backup(name=name)

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
        try:
            player = Player(name)
            self._players[name] = player

            self.signs = Signs(player)
            Monitor(self.signs.poll, name=name)
            self._copiers[name] = self.signs.copy

            if me:
                self.player = player
                self.copier = self.signs.copy

            self.signs.give_signs()
        except (PlayerNotInWorld, SessionTimeout, NoPlayerFound) as e:
            # during tests this will fail as there is no real player
            logging.error("failed to give signs to player, %s", e)

        logging.info(f"Monitoring player {name} enabled for sign commands")

    def stop(self):
        Monitor.stop_all()

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

    def get_block(self, pos: Vec3) -> Item:
        """
        Gets a block in the world
        """
        client = get_client()

        int_pos = Vec3(*pos).with_ints()

        grab_volume = Volume.from_corners(int_pos, int_pos)
        blocks = grab(client, grab_volume)

        return blocks[0][0][0]

    def __repr__(self) -> str:
        report = "Minecraft Interactive World Builder status:\n"
        if self.copier is not None:
            report += (
                "  copy buffer start: {o.copier.start_pos}\n"
                "  copy buffer stop: {o.copier.stop_pos}\n"
                "  copy buffer size: {o.copier.size}\n"
                "  paste point: {o.copier.paste_pos}\n"
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

    def save(self, filename: str, vol: Optional[Volume] = None):
        """
        Save the Volume of blocks represented by the copy buffer or provided
        volumne to a file
        """
        if not vol:
            vol = self.copier.to_volume()

        blocks = grab(get_client(), vol)
        save_items(blocks, Path(filename))

    def load(
        self,
        filename: str,
        position: Optional[Vec3] = None,
        anchor: Anchor3 = Anchor3.BOTTOM_SW,
    ):
        """
        Load a saved set of blocks into a location indicated by copy buffer or
        passed as an argument
        """
        if not position:
            position = self.copier.start_pos

        # load a 3d array of Item from the file
        items = load_items(Path(filename), dimensions=3)
        # convert the items into a Blocks object which renders them in the world
        blocks = Blocks(get_client(), position, items, anchor=Anchor3.BOTTOM_SW)

        if self.copier:
            self.copier.apply_volume(blocks.volume)
