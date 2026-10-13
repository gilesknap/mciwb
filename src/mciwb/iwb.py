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
from mciwb.builders.schematic import Schematic
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
from mciwb.threads import (
    Client,
    get_client,
    reply_matches,
    retry_command,
    set_client,
)


def _rcon_port(server_folder: Path) -> int | None:
    """The RCON port in a server folder's server.properties, if there is one"""
    try:
        lines = (server_folder / "server.properties").read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        key, _, value = line.partition("=")
        if key.strip() == "rcon.port":
            try:
                return int(value)
            except ValueError:
                return None
    return None


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
        ``scan`` and ``render`` read blocks from its files, which is much faster
        than over RCON. Set for the server of ``mciwb start`` when it uses
        the default ``--folder``: for another folder, set it yourself, e.g.
        ``world.world_folder = Path("/my/server/world")``.
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

        # if we are using the server created by mciwb start (with its default
        # folder) then we know where the folders are for doing backups
        self._backup: Backup | None = None
        self.world_folder: Path | None = None
        if server == HOST and (
            port == def_port or _rcon_port(default_server_folder) == port
        ):
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

        # doors wont replace doors with different states so need to clear first.
        # Clear both halves before placing either: a lower half breaks if the
        # block above it changes to anything but its upper half (e.g. when
        # clearing a doorway in a wall)
        top = pos + Direction.UP
        self.set_block(pos, Item.AIR)
        self.set_block(top, Item.AIR)
        self.set_block(pos, door_type, facing=facing, nbt=["half=lower", *common])
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
        a 3d array of Item objects. If the filename ends in ``.schem`` it is
        saved as a Sponge schematic instead, with the block states of stairs,
        slabs and logs (see `mciwb.builders.Schematic.from_world`), which
        other Minecraft tools such as WorldEdit can load.

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

        if Path(filename).suffix == ".schem":
            Schematic.from_world(vol).save(filename)
            return
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
        JSON file containing a 3d array of Item objects, or from a Sponge
        schematic if the filename ends in ``.schem`` (see
        `mciwb.builders.Schematic`).

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

        if Path(filename).suffix == ".schem":
            schematic = Schematic.load(filename)
            volume = Volume.from_anchor(position, schematic.size, anchor)
            schematic.paste(volume.start)
        else:
            # load a 3d array of Item from the file
            items = load_items(Path(filename), dimensions=3)
            # convert the items into a Blocks object which renders them
            volume = Blocks(get_client(), position, items, anchor=anchor).volume

        if self.copier:
            self.copier.apply_volume(volume)

    def scan(self, start: Vec3, end: Vec3) -> BlockGrid:
        """
        Read the blocks between two opposite corners of a region, from the
        world's files if ``world_folder`` is set, otherwise over RCON.

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
        see what a build looks like. See `render_howto` for the views.

        :param start: a corner of the region
        :param end: the opposite corner of the region
        :param file: the image file to write
        :param views: the views to draw: top, iso, north, south, east, west,
            iso_ne, iso_nw or iso_sw; a list, or the name of one view
        :param scale: pixels per block, chosen automatically by default
        :param labels: add titles and world coordinate labels

        :returns: the blocks that were rendered, see `scan`
        """
        if isinstance(views, str):
            views = [views]
        grid = self.scan(start, end)
        render(grid, views, scale, labels).save(file)
        log.info(f"rendered {', '.join(views)} to {file}")
        return grid

    def cmd(self, cmd: str, expect: str | None = None) -> str:
        """
        Run any arbitrary Minecraft console command on the server.

        The server's reply is returned as it is, including error messages
        such as ``Incorrect argument for command...<--[HERE]``. (On Minecraft
        26.x, for example, game rules have snake case names, so
        ``gamerule doDaylightCycle`` is an error: use
        ``gamerule advance_time``. And ``time query daytime`` is an error
        too: use ``time query day`` for the ticks into the current day, and
        ``time query day repetition`` for the number of days.)

        Changed: before mciwb#166 the errors that mcipc recognises were
        raised as mcipc exceptions (e.g. ``InvalidArgument``); now they are
        returned as text like any other reply.

        Another RCON client of the server (e.g. a dashboard) can, rarely,
        garble the reply: empty it or add its own output to it. Pass
        *expect* to check the reply and send the command again if needed.
        Only do that for a command that is safe to send twice (e.g.
        ``setblock``, ``tp`` to a fixed place, ``gamerule ...``, but not
        ``give`` or ``summon``).

        :param cmd: the command to run, without the leading slash
            e.g. "time set day"
        :param expect: a regular expression that the reply must contain,
            e.g. ``r"Game rule \\S+ is currently set to \\S+"``

        :returns: the server's response. With *expect*, just the part of it
            that matched, or the whole response if it never matched
        """
        client = get_client()
        if expect is None:
            return client.run_raw(cmd)
        return retry_command(lambda: client.run_raw(cmd), reply_matches(expect), cmd)
