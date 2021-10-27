"""
functions to allow interactive copy and paste of regions of a minecraft map
"""
from enum import Enum
import re
from threading import Thread
from time import sleep

from mcipc.rcon.enumerations import Item
from mcipc.rcon.je import Client, client
from mcwb.types import Vec3

from mciwb.player import Player

sign_text = re.compile(r"""Text1: '{"text":"([^"]*)"}'}""")
zero = Vec3(0, 0, 0)


class Commands(Enum):
    start = 0
    stop = 1
    paste = 2
    floorpaste = 3
    clear = 4


class Copy:
    def __init__(self, client: Client, player_name: str):
        self.client = client
        self.player_name = player_name
        self.player = Player(client, player_name)
        self.start_vec: Vec3 = None
        self.stop_vec: Vec3  = None
        self.paste_vec: Vec3  = None
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

        self.give_signs()

    def __del__(self):
        # terminate the poll thread
        self.polling = False

    def __repr__(self) -> str:
        report = (
            "Minecraft copy tool status:\n"
            "  player: {o.player_name} at {o.player.current_pos}\n"
            "  copy buffer start: {o.start_vec}\n"
            "  copy buffer stop: {o.stop_vec}\n"
            "  copy buffer size: {o.size}\n"
            "  paste point: {o.paste_vec}\n"
        )
        return report.format(o=self)

    def give_signs(self):
        entity = (
            """minecraft:oak_sign{{BlockEntityTag:{{Text1:'{{"text":"{0}"}}'}},"""
            """display:{{Name:'{{"text":"{0}"}}'}}}}"""
        )
        for command in Commands:
            self.client.give(self.player_name, entity.format(command.name))

    def _set_pos(self, x, y, z, player_relative):
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
        self.start_vec = self._set_pos(x, y, z, player_relative)
        self.set_paste(*self.start_vec, player_relative=player_relative)

    def set_stop(self, x=0, y=0, z=0, player_relative=False):
        """
        Set the start point of the copy buffer
        """
        self.stop_vec = self._set_pos(x, y, z, player_relative)
        self.size = self.stop_vec - self.start_vec
        self.set_paste(*self.start_vec, player_relative=player_relative)

    def set_paste(self, x=0, y=0, z=0, player_relative=False):
        """
        Set the paste point relative to the current player position
        """
        self.paste_vec = self._set_pos(x, y, z, player_relative)
        # adjust clone dest so the paste corner matches the start paste buffer
        self.clone_dest = self.paste_vec
        size = self.stop_vec - self.start_vec
        if size.x < 0:
            self.clone_dest += Vec3(size.x, 0, 0)
        if size.z < 0:
            self.clone_dest += Vec3(0, 0, size.z)

    def paste(self, x=0, y=0, z=0):
        """
        Copy the contents of past buffer to paste point plus offset x y z
        """
        offset = Vec3(x, y, z)
        result = self.client.clone(
            self.start_vec, self.stop_vec, self.clone_dest + offset
        )
        print(result)

    def shift(self, x=0, y=0, z=0):
        """
        shift the position of the copy buffer
        """
        offset = Vec3(x, y, z)
        self.set_start(*(self.start_vec + offset))
        self.set_stop(*(self.stop_vec + offset))

    def fill(self, item: Item = None, x=0, y=0, z=0):
        """
        fill the paste buffer offset by x y z with Air or a specified block
        """
        item = item or Item.AIR
        offset = Vec3(x, y, z)
        size = self.stop_vec - self.start_vec
        end = self.paste_vec + size + offset
        result = self.client.fill(self.paste_vec + offset, end, item.value)
        print(result)

    def expand(self, x=0, y=0, z=0):
        """
        expand one or more of the dimensions of the copy buffer
        """
        expander = Vec3(x, y, z)
        # use mutable start and stop here to make the code more readable
        start = self.start_vec._asdict()
        stop = self.stop_vec._asdict()

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

    def _poller(self):
        """
        continually check if a sign has been placed in front of the player
        one to three blocks away and take action based on sign text
        """
        while self.polling:
            dir = self.player.dir(self.poll_client)
            for height in range(-1, 3):
                for distance in range(1, 4):
                    pos = self.player.current_pos + dir.value * distance
                    ipos = pos.with_ints() + Vec3(0, height, 0)
                    data = self.poll_client.data.get(block=ipos)
                    match = sign_text.search(data)
                    if match:
                        text = match.group(1)
                        self._function(text, ipos + dir.value, ipos)
            sleep(0.5)

    def _function(self, func: str, pos: Vec3, sign_pos: Vec3):
        """
        performs the functions available by placing signs in front of player
        """
        try:
            client.setblock(self.poll_client, sign_pos, Item.AIR)
            if func == Commands.start.name:
                self.set_start(*pos)
            elif func == Commands.stop.name:
                self.set_stop(*pos)
            elif func == Commands.paste.name:
                self.set_paste(*pos)
                self.paste()
            elif func == Commands.floorpaste.name:
                pos -= Vec3(0, 1, 0)
                self.shift(y=-1)
                self.set_paste(*pos)
                self.paste()
                self.shift(y=1)
            elif func == Commands.clear.name:
                self.fill()
        except BaseException as e:
            self.client.tell(player=self.player_name, message=f"ERROR: {e}")
