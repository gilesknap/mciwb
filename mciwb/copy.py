"""
functions to allow interactive copy and paste of regions of a minecraft map
"""
from threading import Thread

from mcipc.rcon.enumerations import Item
from mcipc.rcon.je import Client
from mcwb.types import Vec3

from mciwb.player import Player


class Copy:
    # command blocks to place in the world
    # TODO: use some tags to make these unique
    copy_start_block = Item.RED_CONCRETE  # mark the paste buffer start corner
    copy_stop_block = Item.GREEN_CONCRETE  # mark paste buffer opposite corner
    copy_paste_block = Item.BLUE_CONCRETE  # copy paste buffer to here

    def __init__(self, client: Client, player_name: str):
        self.client = client
        self.player_name = player_name
        self.player = Player(client, player_name)
        self.start_vec = Vec3(0, 0, 0)
        self.stop_vec = Vec3(0, 0, 0)

    def _set_pos(self, x, y, z):
        offset = Vec3(x, y, z)
        pos = self.player.pos()
        return pos.with_ints() + offset

    def set_start(self, x=0, y=0, z=0):
        """
        Set the start point of the paste buffer relative
        to the current player position
        """
        self.start_vec = self._set_pos(x, y, z)
        # default paste back to same location (for use with paste offsets)
        self.paste_vec = self.start_vec

    def set_stop(self, x=0, y=0, z=0):
        """
        Set the start point of the paste buffer relative
        to the current player position
        """
        self.stop_vec = self._set_pos(x, y, z)

    def set_paste(self, x=0, y=0, z=0):
        """
        Set the paste point of the paste buffer relative
        to the current player position
        """
        self.paste_vec = self._set_pos(x, y, z)

    def paste(self, x=0, y=0, z=0):
        """
        Copy the contents of past buffer to paste point + offsets x,y,z
        """
        dest = self.paste_vec + Vec3(x, y, z)
        self.client.clone(self.stop_vec, self.start_vec, dest)
