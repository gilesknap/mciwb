"""
functions to allow interactive copy and paste of regions of a minecraft map
"""
import re
from threading import Thread
from time import sleep

from mcipc.rcon.enumerations import Item
from mcipc.rcon.je import Client, client
from mcwb.types import Vec3

from mciwb.player import Player

sign_text = re.compile(r"""Text1: '{"text":"([^"]*)"}'}""")
zero = Vec3(0, 0, 0)


class Copy:
    def __init__(self, client: Client, player_name: str):
        self.client = client
        self.player_name = player_name
        self.player = Player(client, player_name)
        self.start_vec = zero
        self.stop_vec = zero
        self.paste_vec = zero

        # create our own client for the new thread
        self.polling = True
        self.poll_client = Client(
            self.client.host, self.client.port, passwd=self.client.passwd
        )
        self.poll_client.connect(True)
        self.poll_thread = Thread(target=self._poller)
        self.poll_thread.start()

        self.get_signs()

    def __del__(self):
        self.polling = False

    def get_signs(self):
        entity = (
            """minecraft:oak_sign{{BlockEntityTag:{{Text1:'{{"text":"{0}"}}'}},"""
            """display:{{Name:'{{"text":"{0}"}}'}}}}"""
        )
        self.client.give(self.player_name, entity.format("start"))
        self.client.give(self.player_name, entity.format("stop"))
        self.client.give(self.player_name, entity.format("paste"))

    def _set_pos_relative(self, x, y, z, relative):
        offset = Vec3(x, y, z)
        if relative:
            pos = self.player.pos()
            return pos.with_ints() + offset
        else:
            return offset

    def set_start(self, x=0, y=0, z=0, relative=True):
        """
        Set the start point of the paste buffer relative
        to the current player position
        """
        self.start_vec = self._set_pos_relative(x, y, z, relative)
        # default paste back to same location (for use with paste offsets)
        self.paste_vec = self.start_vec

    def set_stop(self, x=0, y=0, z=0, relative=True):
        """
        Set the start point of the paste buffer relative
        to the current player position
        """
        self.stop_vec = self._set_pos_relative(x, y, z, relative)

    def set_paste(self, x=0, y=0, z=0, relative=True):
        """
        Set the paste point of the paste buffer relative
        to the current player position
        """
        self.paste_vec = self._set_pos_relative(x, y, z, relative)
        # adjust so the paste corner matches the start paste buffer
        size = self.stop_vec - self.start_vec
        if size.x < 0:
            self.paste_vec += Vec3(size.x, 0, 0)
        if size.z < 0:
            self.paste_vec += Vec3(0, 0, size.z)

    def paste(self, x=0, y=0, z=0):
        """
        Copy the contents of past buffer to paste point + offsets x,y,z
        """
        dest = self.paste_vec + Vec3(x, y, z)
        result = self.client.clone(self.start_vec, self.stop_vec, dest)
        print(result)

    def _poller(self):
        # check if a sign has been placed in front of the player
        # one - three blocks away

        while self.polling:
            dir = self.player.dir(self.poll_client)
            for distance in range(1, 4):
                pos = self.player.current_pos + dir.value * distance
                ipos = pos.with_ints()
                data = self.poll_client.data.get(block=ipos)
                match = sign_text.search(data)
                if match:
                    text = match.group(1)
                    self._function(text, ipos + dir.value, ipos)
            sleep(0.5)

    def _function(self, func: str, pos: Vec3, sign_pos: Vec3):
        if func == "start":
            client.setblock(self.poll_client, sign_pos, Item.AIR)
            self.start_vec = pos
            # reset copy buffer to 1 block
            self.stop_vec = pos
            # default paste back to same location (for use with paste offsets)
            self.paste_vec = pos
        elif func == "stop":
            client.setblock(self.poll_client, sign_pos, Item.AIR)
            self.stop_vec = pos
        elif func == "paste":
            client.setblock(self.poll_client, sign_pos, Item.AIR)
            self.set_paste(*pos, relative=False)
            self.paste()
