"""
functions to allow interactive copy and paste of regions of a minecraft map
"""
import re
from enum import Enum
from threading import Thread
from time import sleep

from mcipc.rcon.enumerations import CloneMode, Item, MaskMode
from mcipc.rcon.je import Client, client
from mcwb.types import Direction, Vec3

from mciwb.backup import Backup
from mciwb.player import Player

sign_text = re.compile(r"""Text1: '{"text":"([^"]*)"}'}""")
zero = Vec3(0, 0, 0)


class Commands(Enum):
    select = 0
    expand = 1
    paste = 2
    pasteforce = 3
    clear = 4
    backup = 5


class Copy:
    """
    Provides an interactive way to use copy and paste commands within a
    Minecraft world.

    Gives the player a set of command signs and spawns a thread to watch
    for those signs being dropped in the world.
    """

    def __init__(self, client: Client, player_name: str, backup: Backup = None):
        self.client = client
        self.player_name = player_name
        self.backup: Backup = backup or Backup("", "", "", client)
        self.player = Player(client, player_name)
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

    def _calc_pos(self, x, y, z, player_relative):
        offset = Vec3(x, y, z)
        if player_relative:
            pos = self.player.pos()
            return pos.with_ints() + offset
        else:
            return offset

    def set_start(self, x=0, y=0, z=0, player_relative=False):
        """
        Set the start point of the copy buffer
        """
        self.start_b = self._calc_pos(x, y, z, player_relative)
        self.size = self.stop_b - self.start_b
        self.set_paste(*self.start_b, player_relative=player_relative)

    def set_stop(self, x=0, y=0, z=0, player_relative=False):
        """
        Set the start point of the copy buffer
        """
        self.stop_b = self._calc_pos(x, y, z, player_relative)
        self.size = self.stop_b - self.start_b

    def set_paste(self, x=0, y=0, z=0, player_relative=False):
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
        print(mode)
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

    def fill(self, item: Item = None, x=0, y=0, z=0):
        """
        fill the paste buffer offset by x y z with Air or a specified block
        """
        item = item or Item.AIR
        offset = Vec3(x, y, z)
        end = self.paste_b + self.size + offset
        result = self.client.fill(self.paste_b + offset, end, item.value)
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

    def expand_to(self, x=0, y=0, z=0):
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

    def get_target_block(self, pos: Vec3, dir: Direction):
        """
        determine the target block that the sign at pos indicates
        """
        # use 'execute if' with a benign command like seed
        result = self.client.execute.if_.block(pos, "minecraft:oak_wall_sign").run(
            "seed"
        )

        if "Seed" in result:
            # wall signs target the block behind them
            pos += dir.value
        else:
            # standing signs target the block below them
            pos += Vec3(0, -1, 0)

        return pos

    def _poller(self):
        """
        continually check if a sign has been placed in front of the player
        one to three blocks away and take action based on sign text
        """
        while self.polling:
            try:
                dir = self.player.dir(self.poll_client)
                for height in range(-1, 3):
                    for distance in range(1, 4):
                        pos = self.player.current_pos + dir.value * distance
                        ipos = pos.with_ints() + Vec3(0, height, 0)
                        data = self.poll_client.data.get(block=ipos)
                        match = sign_text.search(data)
                        if match:
                            text = match.group(1)
                            target = self.get_target_block(ipos, dir)
                            print(text, target)
                            client.setblock(self.poll_client, ipos, Item.AIR)
                            self._function(text, target)
            except BrokenPipeError:
                print("Connection to Minecraft Server lost, polling terminated")
                self.polling = False
            except BaseException as e:
                print(e)
            sleep(0.5)

    def _function(self, func: str, pos: Vec3):
        """
        performs the functions available by placing signs in front of player
        """
        if func == Commands.select.name:
            self.set_stop(*self.start_b)
            self.set_start(*pos)
        elif func == Commands.paste.name:
            self.set_paste(*pos)
            self.paste()
        elif func == Commands.pasteforce.name:
            self.set_paste(*pos)
            self.paste(force=True)
        elif func == Commands.clear.name:
            self.fill()
        elif func == Commands.backup.name:
            self.backup.backup()
        elif func == Commands.expand.name:
            self.expand_to(*pos)
