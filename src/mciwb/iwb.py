"""
The Interactive World Builder: the main entry point for building in a
Minecraft world
"""

from collections.abc import Sequence
from pathlib import Path

from mcipc.rcon.exceptions import NoPlayerFound
from mcwb import Anchor3, Blocks, Direction, Item, Vec3, Volume
from mcwb.itemlists import grab, load_items, save_items
from rcon.exceptions import SessionTimeout

from mciwb.backup import Backup
from mciwb.blockgrid import BlockGrid
from mciwb.copier import CopyPaste
from mciwb.logging import init_logging, log
from mciwb.monitor import Monitor
from mciwb.player import Player
from mciwb.render import render, scan
from mciwb.server import (
    HOST,
    backup_folder_default,
    def_pass,
    def_port,
    default_server_folder,
)
from mciwb.signs import Signs
from mciwb.threads import Client, get_client, set_client


def get_world() -> "Iwb":
    """
    Return the current `Iwb` world object, i.e. the most recently created one.
    """
    return Iwb.the_world


class Iwb:
    """
    Interactive World Builder class. Provides a very simple interface for
    interactive functions for use in an IPython shell, or in scripts.

    Connect to the server started by ``mciwb start`` with::

        world = Iwb()

    Call `stop` when finished to stop any background monitoring threads.

    :ivar player: The default `Player` object.
    :ivar copier: `CopyPaste` object for the above player.
    :ivar signs: The `Signs` object for the above player.
    :ivar world_folder: The server's world folder, if it is on this machine.
        `scan` and `render` read blocks from its files, which is much faster
        than over RCON. Set for the default server of ``mciwb start``.
    """

    the_world: "Iwb" = None  # type: ignore

    def __init__(
        self, server: str = HOST, port: int = def_port, passwd: str = def_pass
    ) -> None:
        """
        Initialise the world object.

        :param server: the server address, defaults to the local server
            started by ``mciwb start``
        :param port: the server's RCON port
        :param passwd: the server's RCON password

        :raises SessionTimeout: if the connection to the server fails

        """
        Iwb.the_world = self

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
        self._backup: Backup | None = None
        self.world_folder: Path | None = None
        if server == HOST and port == def_port:
            world_folder = default_server_folder / "world"
            if (world_folder / "level.dat").exists():
                self._backup = Backup(world_folder, backup_folder_default)
                self.world_folder = world_folder
            else:
                # e.g. the server's folder is elsewhere, or not yet saved
                log.warning(
                    f"backups disabled: {world_folder} does not look like "
                    "a minecraft world"
                )

    def debug(self, enable: bool = True):
        """
        Enable/disable debug log. Enabling this will also enable
        full Traceback log.

        :param enable: True to enable debug log, False to disable
        """
        init_logging(debug=enable)

    def backup(self, name: str | None = None) -> None:
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
        client.gamerule("send_command_feedback", False)

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

    def add_player(self, name: str, me: bool = True, setup: bool = True):
        """
        Add a player to the world object. This provides monitoring of the
        player's position and handles the player's placing of action signs.
        The player is also given a set of the action signs.

        If me is True then the player will be set as the current default
        player. The default player is available using::

            Iwb.the_world.player

        All players are available using::

            Iwb.the_world._players

        :param name: the name of the player
        :param me: if True, set this player as the default player
        :param setup: if True, make the player an operator in creative mode
        """
        player = Player(name)
        self._players[name] = player
        signs = Signs(player)
        Monitor(signs.poll, name=name)
        self._copiers[name] = signs.copy

        if me or self.player is None:
            self.player = player
            self.copier = signs.copy
            self.signs = signs

        try:
            if setup:
                player.setup()
            signs.give_signs()
        except NoPlayerFound:
            # e.g. a misspelt player name, or a named entity standing in for
            # a player (as in the tests), which cannot be given items.
            # NoPlayerFound has no message of its own, so supply one
            log.warning(
                "could not set up or give signs to %s, player not found in the world",
                name,
            )
        except SessionTimeout:
            log.warning(
                "could not set up or give signs to %s, the server did not respond",
                name,
            )
        else:
            log.info(f"Monitoring player {name} enabled for sign commands")

    def stop(self):
        """
        Stop all background monitoring threads. Call this when finished with
        the world, e.g. at the end of a script.
        """
        Monitor.stop_all()

    def set_block(
        self,
        pos: Vec3,
        block: Item,
        facing: Vec3 | None = None,
        nbt: list[str] | None = None,
    ) -> bool:
        """
        Places a block in the world

        :param pos: the position to place the block
        :param block: the type of block
        :param facing: the direction the block should face (if applicable)
        :param nbt: a list of block states to apply to the block

        nbt examples:

        Placing a top half of a door, open, with hinge on the left:

        nbt=["half=upper", "hinge=left", "open=true"]

        :returns: True if the block is now in place. False if the server
            rejected the command (the server's response is logged as an error)
        """
        # TODO at present the nbt are free form strings. In the spirit of mcwb
        # we should provide a set of types that represent the block states and
        # provide a way to convert them to strings (but that is a large task)
        client = get_client()

        pos = Vec3(*pos)
        int_pos = pos.with_ints()
        # copy, so that the caller's list is not changed
        nbt = list(nbt or [])

        if facing:
            nbt.append(f"""facing={Direction.name(facing)}""")
        block_str = f"""{block}[{",".join(nbt)}]"""

        result = client.setblock(int_pos, block_str)
        log.debug("setblock: " + result)

        # 'Could not set the block' is not an error - it means it was already set
        if not any(
            x in result for x in ["Changed the block", "Could not set the block"]
        ):
            log.error(result)
            return False
        return True

    def place_door(
        self,
        pos: Vec3,
        door_type: Item,
        facing: Vec3 = Direction.NORTH,
        open: bool = False,
        right_hinge: bool = False,
    ) -> None:
        """
        Place a door in the world (doors are 2 blocks high)

        :param pos: the position of the bottom half of the door
        :param door_type: the type of door to place e.g. Item.OAK_DOOR
        :param facing: the direction the door should face
        :param open: whether the door should be open or closed
        :param right_hinge: True for a hinge on the right, False for the left
        """
        if not str(door_type).upper().endswith("_DOOR"):
            raise ValueError("door_type must be a door")

        hinge = "right" if right_hinge else "left"
        open_str = "true" if open else "false"
        common = [f"hinge={hinge}", f"open={open_str}"]

        # doors wont replace doors with different states so need to clear first
        self.set_block(pos, Item.AIR)
        self.set_block(pos, door_type, facing=facing, nbt=["half=lower", *common])
        top = pos + Direction.UP
        self.set_block(top, Item.AIR)
        self.set_block(top, door_type, facing=facing, nbt=["half=upper", *common])

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

    def save(self, filename: str | Path, vol: Volume | None = None):
        """
        Save a Volume of blocks to a file. The volume can be specified in
        the *vol* parameter or alternatively defaults to the current copy buffer.

        The file is saved in the mcwb format which is a JSON file containing
        a 3d array of Item objects.

        The file can be loaded into a world using the `load` method.

        :param filename: the name of the file to save to
        :param vol: the volume to save

        :raises ValueError: if no *vol* is given and there is no copy buffer
        """
        if not vol:
            if self.copier is None or self.copier.start_pos is None:
                raise ValueError(
                    "no vol given and no copy buffer selected "
                    "(add a player and use the select sign, or pass vol)"
                )
            vol = self.copier.to_volume()

        blocks = grab(get_client(), vol)
        save_items(blocks, Path(filename))

    def load(
        self,
        filename: str | Path,
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

        :raises ValueError: if no *position* is given and there is no copy buffer
        """
        if not position:
            if self.copier is None or self.copier.start_pos is None:
                raise ValueError(
                    "no position given and no copy buffer selected "
                    "(add a player and use the select sign, or pass position)"
                )
            position = self.copier.start_pos

        # load a 3d array of Item from the file
        items = load_items(Path(filename), dimensions=3)
        # convert the items into a Blocks object which renders them in the world
        blocks = Blocks(get_client(), position, items, anchor=anchor)

        if self.copier:
            self.copier.apply_volume(blocks.volume)

    def scan(self, start: Vec3, end: Vec3) -> BlockGrid:
        """
        Read the blocks between two opposite corners of a region, from the
        world's files if `world_folder` is set, otherwise over RCON.

        :param start: a corner of the region
        :param end: the opposite corner of the region

        :returns: the blocks, e.g. ``world.scan(a, b).counts()`` counts them
        """
        vol = Volume.from_corners(Vec3(*start), Vec3(*end))
        return scan(vol, self.world_folder, get_client())

    def render(
        self,
        start: Vec3,
        end: Vec3,
        file: str | Path = "render.png",
        views: Sequence[str] = ("top", "iso"),
        scale: int | None = None,
        labels: bool = True,
    ) -> BlockGrid:
        """
        Render the region between two opposite corners to a PNG image, to
        see what a build looks like. See `mciwb.render` for the views.

        :param start: a corner of the region
        :param end: the opposite corner of the region
        :param file: the image file to write
        :param views: the views to draw: top, iso, north, south, east, west,
            iso_ne, iso_nw or iso_sw
        :param scale: pixels per block, chosen automatically by default
        :param labels: add titles and world coordinate labels

        :returns: the blocks that were rendered, see `scan`
        """
        grid = self.scan(start, end)
        render(grid, views, scale, labels).save(file)
        log.info(f"rendered {', '.join(views)} to {file}")
        return grid

    def cmd(self, cmd: str) -> str:
        """
        Run any arbitrary Minecraft console command on the server.

        :param cmd: the command to run, without the leading slash
            e.g. "time set day"

        :returns: the server's response
        """
        return get_client().run(cmd)
