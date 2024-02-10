from pathlib import Path

from mcipc.rcon.exceptions import NoPlayerFound
from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Anchor3, Blocks, Direction, Vec3, Volume
from mcwb.itemlists import grab, load_items, save_items
from rcon.exceptions import SessionTimeout
from rcon.source.proto import Packet

from mciwb.backup import Backup
from mciwb.copier import CopyPaste
from mciwb.logging import init_logging, log
from mciwb.monitor import Monitor
from mciwb.player import Player, PlayerNotInWorld
from mciwb.server import HOST, def_port
from mciwb.signs import Signs
from mciwb.threads import get_client, set_client
from mciwb.utils import Utils

world: "Iwb" = None  # type: ignore


def get_world():
    return Iwb.the_world


class Iwb:
    """
    Interactive World Builder class. Provides a very simple interface for
    interactive functions for use in an IPython shell.

    :ivar player: The default `Player` object.
    :ivar copier: `CopyPaste` object for the above player.
    :ivar signs: The `Signs` object for the above player.
    """

    the_world: "Iwb" = None  # type: ignore

    def __init__(self, server: str, port: int, passwd: str) -> None:
        """
        Initialise the world object.

        :param server: the server address
        :param port: the server port
        :param passwd: the server password

        :raises SessionTimeout: if the connection to the server fails

        """
        Iwb.the_world = self
        self.utils = Utils(self)

        self._server: str = server
        self._port: int = port
        self._passwd: str = passwd

        self.connect()

        self.player: Player = None  # type: ignore
        self.copier: CopyPaste = None  # type: ignore
        self.signs: Signs = None  # type: ignore

        self._players: dict[str, Player] = {}
        self._copiers: dict[str, CopyPaste] = {}

        # if we are using the default server created by mciwb then we know
        # where the folders are for doing backups
        if server == HOST and port == def_port:
            self._backup: Backup | None = Backup()
        else:
            self._backup = None

    def debug(self, enable: bool = True):
        """
        Enable/disable debug log. Enabling this will also enable
        full Traceback log.

        :param enable: True to enable debug log, False to disable
        """
        init_logging(debug=enable)

    def backup(self, name=None) -> None:
        """
        Backup the Minecraft world to a file. If no name is given then the
        backup will be named using the current date and time.

        :param name: the name of the backup file
        """
        if self._backup is None:
            log.warning("no backup available")
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

        log.info(f"Connected to {self._server} on {self._port}")
        # don't announce every rcon command
        client.gamerule("sendCommandFeedback", False)

        return client

    def get_player(self, name: str) -> Player:
        """
        Get the player object for the given player name.

        :param name: the name of the player
        """
        return self._players[name]

    @property
    def players(self) -> list[str]:
        """
        Get a list of the names of players being monitored.
        """
        return list(self._players.keys())

    def add_player(self, name: str, me=True):
        """
        Add a player to the world object. This provides monitoring of the
        player's position and handles the player's placing of action signs.

        If me is True then the player will be set as the current default
        player. The default player is available using::

            Iwb.the_world.player

        All players are available using::

            Iwb.the_world._players

        :param name: the name of the player
        :param me: if True, set this player as the default player
        """
        try:
            player = Player(name)
            self._players[name] = player

            self.signs = Signs(player)
            Monitor(self.signs._poll, name=name)
            self._copiers[name] = self.signs.copy

            if me:
                self.player = player
                self.copier = self.signs.copy

            self.signs.give_signs()
        except (PlayerNotInWorld, SessionTimeout, NoPlayerFound) as e:
            # during tests this will fail as there is no real player
            log.error("failed to give signs to player, %s", e)

        log.info(f"Monitoring player {name} enabled for sign commands")

    def stop(self):
        Monitor.stop_all()

    def set_block(
        self,
        pos: Vec3,
        block: Item,
        facing: Vec3 | None = None,
        nbt: list[str] | None = None,
    ):
        """
        Places a block in the world

        :param pos: the position to place the block
        :param block: the type of block
        :param facing: the direction the block should face (if applicable)
        :param nbt: a list of NBT tags to apply to the block

        nbt examples:

        Placing a top half of a door, open, with hinge on the left:

        nbt=["half=upper", "hinge=left", "open=true"]

        TODO at present the nbt are free form strings. In the spirit of mcwb
        we should provide a set of types that represent the NBT tags and
        provide a way to convert them to strings (but that is a large task)
        """
        client = get_client()

        pos = Vec3(*pos)
        int_pos = pos.with_ints()
        nbt = nbt or []

        if facing:
            nbt.append(f"""facing={Direction.name(facing)}""")
        block_str = f"""{block}[{",".join(nbt)}]"""

        result = client.setblock(int_pos, block_str)
        log.debug("setblock: " + result)

        # 'Could not set the block' is not an error - it means it was already set
        if not any(
            x in result for x in ["Changed the block", "Could not set the block", ""]
        ):
            log.error(result)

    def get_block(self, pos: Vec3) -> Item:
        """
        Gets a block in the world

        :param pos: the position to get the block from
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
        for name, player in self._players.items():
            report += (
                f"  player: {name}\n"
                f"    position: {player.pos}\n"
                f"    facing: {player.facing}\n"
            )
        if len(self._players.items()) == 0:
            report += "  no players\n"

        return report.format(o=self)

    def save(self, filename: str, vol: Volume | None = None):
        """
        Save a Volume of blocks to a file. The volume can be specified in
        the *vol* parameter or alternatively defaults to the current copy buffer.

        The file is saved in the mcwb format which is a JSON file containing
        a 3d array of Item objects.

        The file can be loaded into a world using the `load` method.

        :param filename: the name of the file to save to
        :param vol: the volume to save
        """
        if not vol:
            vol = self.copier.to_volume()

        blocks = grab(get_client(), vol)
        save_items(blocks, Path(filename))

    def load(
        self,
        filename: str,
        position: Vec3 | None = None,
        anchor: Anchor3 = Anchor3.BOTTOM_SW,
    ):
        """
        Load a saved set of blocks into a location. The location can be
        specified in argument *position* or alternatively defaults
        to the copy buffer start position.

        The blocks are loaded from a file in the mcwb format which is a
        JSON file containing a 3d array of Item objects.

        The blocks are loaded into the world using the Blocks class.

        :param filename: the name of the file to load from
        :param position: the position to load the blocks to
        :param anchor: the anchor point for the blocks
        """
        if not position:
            position = self.copier.start_pos

        # load a 3d array of Item from the file
        items = load_items(Path(filename), dimensions=3)
        # convert the items into a Blocks object which renders them in the world
        blocks = Blocks(get_client(), position, items, anchor=anchor)

        if self.copier:
            self.copier.apply_volume(blocks.volume)

    def cmd(self, cmd: str) -> str:
        """
        Run any arbitrary Minecraft console command on the server.

        :param cmd: the command to run
        """
        encoding = "utf-8"
        client = get_client()
        request = Packet.make_command(cmd, encoding=encoding)

        response = client.communicate(request)
        if response.id != request.id:
            raise SessionTimeout()

        return response.payload.decode(encoding)
