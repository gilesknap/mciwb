"""
functions to allow interactive copy and paste of regions of a minecraft map

TODO: refactor required ?
  extract the player monitoring to a class
  extract the copy paste functions to a class
  create a framework for hooking signs to function and provide a default
    mapping for copy/paste signs
"""
import re
from enum import Enum
from threading import Thread
from time import sleep
from typing import Optional

from mcipc.rcon.enumerations import CloneMode, Item, MaskMode
from mcipc.rcon.je import Client
from mcwb.types import Number, Vec3

from mciwb.backup import Backup
from mciwb.player import Player


class Commands(Enum):
    select = 0
    expand = 1
    paste = 2
    clear = 3
    paste_safe = 4
    backup = 5


class Copy:
    """
    Provides an interactive way to use copy and paste commands within a
    Minecraft world.

    Gives the player a set of command signs and spawns a thread to watch
    for those signs being dropped in the world.
    """

    # TODO does this need to use poll_client in the functions called from
    # _functions? It feels like using a socket created in a different thread
    # could be bad (and see the comment on test_copy_anchors)

    def __init__(self, client: Client, player: Player, backup: Optional[Backup] = None):
        self.client = client
        self.backup: Optional[Backup] = backup
        self.player = player
        self.player_name = player.name
        self.start_b: Vec3 = self.player.pos()
        self.stop_b: Vec3 = self.start_b
        self.paste_b: Vec3 = self.start_b
        self.clone_dest = zero
        self.size = zero

        # create our own client for the new thread
        self.polling = True
        self.poll_client = Client(
            self.client.host, self.client.port, passwd=self.client.passwd
        )
        self.poll_client.connect(True)
        self.poll_thread = Thread(target=self._poller)
        self.poll_thread.start()

    def __del__(self):
        self.stop()

    def stop(self):
        # terminate the poll thread
        self.polling = False

    def __repr__(self) -> str:
        report = (
            "Minecraft copy tool status:\n"
            "  player: {o.player_name} at {o.player.current_pos}\n"
            "  copy buffer start: {o.start_b}\n"
            "  copy buffer stop: {o.stop_b}\n"
            "  copy buffer size: {o.size}\n"
            "  paste point: {o.paste_b}\n"
        )
        return report.format(o=self)

    def give_signs(self):
        """
        Give player one of each command sign
        """
        entity = (
            """minecraft:oak_sign{{BlockEntityTag:{{Text1:'{{"text":"{0}"}}'}},"""
            """display:{{Name:'{{"text":"{0}"}}'}}}}"""
        )
        for command in Commands:
            self.client.give(self.player_name, entity.format(command.name))

    def set_start(
        self, x: Number = 0, y: Number = 0, z: Number = 0, player_relative=False
    ):
        """
        Set the start point of the copy buffer
        """
        self.start_b = self._calc_pos(x, y, z, player_relative)
        self.size = self.stop_b - self.start_b
        self.set_paste(
            self.start_b.x,
            self.start_b.y,
            self.start_b.z,
            player_relative=player_relative,
        )

    def set_stop(
        self, x: Number = 0, y: Number = 0, z: Number = 0, player_relative=False
    ):
        """
        Set the start point of the copy buffer
        """
        self.stop_b = self._calc_pos(x, y, z, player_relative)
        self.size = self.stop_b - self.start_b

    def set_paste(
        self, x: Number = 0, y: Number = 0, z: Number = 0, player_relative=False
    ):
        """
        Set the paste point relative to the current player position
        """
        self.paste_b = self._calc_pos(x, y, z, player_relative)
        # adjust clone dest so the paste corner matches the start paste buffer
        self.clone_dest = self.paste_b
        x_off = self.size.x if self.size.x < 0 else 0
        y_off = self.size.y if self.size.y < 0 else 0
        z_off = self.size.z if self.size.z < 0 else 0
        self.clone_dest += Vec3(x_off, y_off, z_off)

    def paste(self, x=0, y=0, z=0, force=False):
        """
        Copy the contents of past buffer to paste point plus offset x y z
        """
        offset = Vec3(x, y, z)
        mode = CloneMode.FORCE if force else CloneMode.NORMAL
        result = self.client.clone(
            self.start_b,
            self.stop_b,
            self.clone_dest + offset,
            mask_mode=MaskMode.REPLACE,
            clone_mode=mode,
        )
        print(result)

    def shift(self, x=0, y=0, z=0):
        """
        shift the position of the copy buffer
        """
        offset = Vec3(x, y, z)
        self.set_start(*(self.start_b + offset))
        self.set_stop(*(self.stop_b + offset))

    def fill(self, item: Item = Item.AIR, x=0, y=0, z=0):
        """
        fill the paste buffer offset by x y z with Air or a specified block
        """
        item = item or Item.AIR
        offset = Vec3(x, y, z)
        end = self.paste_b + self.size + offset
        result = self.client.fill(self.paste_b + offset, end, str(item))
        print(result)

    def expand(self, x=0, y=0, z=0):
        """
        expand one or more of the dimensions of the copy buffer by relative
        amounts
        """
        expander = Vec3(x, y, z)
        # use mutable start and stop here to make the code more readable
        start = self.start_b._asdict()
        stop = self.stop_b._asdict()

        for dim in ["x", "y", "z"]:
            if expander[dim] > 0:
                if start[dim] > stop[dim]:
                    start[dim] += expander[dim]
                else:
                    stop[dim] += expander[dim]
            elif expander[dim] < 0:
                if start[dim] < stop[dim]:
                    start[dim] += expander[dim]
                else:
                    stop[dim] += expander[dim]

        self.set_start(**start)
        self.set_stop(**stop)

    def expand_to(self, x: Number = 0, y: Number = 0, z: Number = 0):
        """
        expand one or more of the dimensions of the copy buffer by moving
        the faces outwards to the specified point
        """
        expander = Vec3(x, y, z)
        # use mutable start and stop here to make the code more readable
        start = self.start_b._asdict()
        stop = self.stop_b._asdict()

        for dim in ["x", "y", "z"]:
            if start[dim] <= stop[dim]:
                if expander[dim] > stop[dim]:
                    stop[dim] = expander[dim]
                elif expander[dim] < start[dim]:
                    start[dim] = expander[dim]
            elif start[dim] >= stop[dim]:
                if expander[dim] < stop[dim]:
                    stop[dim] = expander[dim]
                elif expander[dim] > start[dim]:
                    start[dim] = expander[dim]

        self.set_start(**start)
        self.set_stop(**stop)

    dump = Vec3(0, 0, 0)
    extract_item = re.compile(r".*minecraft\:(?:blocks\/)?(.+)$")

    def _function(self, func: str, pos: Vec3):
        """
        performs the functions available by placing signs in front of player
        """
        if func == Commands.select.name:
            self.set_stop(*self.start_b)
            self.set_start(*pos)
        elif func == Commands.paste_safe.name:
            self.set_paste(*pos)
            self.paste()
        elif func == Commands.paste.name:
            self.set_paste(*pos)
            self.paste(force=True)
        elif func == Commands.clear.name:
            self.fill()
        elif func == Commands.backup.name:
            if self.backup is not None:
                self.backup.backup()
        elif func == Commands.expand.name:
            self.expand_to(*pos)
