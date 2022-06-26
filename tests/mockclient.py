"""
A mock client for testing functions that call the minecraft server.
This mocks a world of 100 blocks square with origin in the middle.
"""
from math import floor

import numpy as np
from mcipc.rcon.enumerations import CloneMode, Item, MaskMode
from mcwb.types import Items, Vec3


class MockClient:
    """
    A mock version of the RCON client for unit testing.
    """

    def __init__(self, host, port, passwd=None):
        # create an empty mock world full of air
        self.world = np.full((100, 100, 100), Item.AIR, dtype=Item)
        # note that numpy will wrap around indexes so this world has
        # ability to index from -50 to 50 in each dimension
        self.host = host
        self.port = port
        self.passwd = passwd

        self.connected = False

    ###########################################################################
    # the following are mock versions of the original Client Functions ########
    ###########################################################################

    def connect(self, retry=True):
        self.connected = True

    def setblock(self, pos: Vec3, block: Item):
        """set the block at position in the world"""
        self.world[pos.x, pos.y, pos.z] = block

    def fill(self, start: Vec3, end: Vec3, block: Item):
        block = Item(block)  # ensure enum
        end -= 1
        self.world[
            floor(start.x) : floor(end.x),
            floor(start.y) : floor(end.y),
            floor(start.z) : floor(end.z),
        ] = block

    def clone(
        self,
        start_corner: Vec3,
        stop_corner: Vec3,
        dest: Vec3,
        mask_mode: MaskMode,
        clone_mode: CloneMode,
    ):
        """clone the contents of the world from a range to another position"""
        begin = []
        end = []

        # using slicing for the clone requires that all the start coords are
        # less than the stop coords (and stop coords are +1
        # (iteration may have been easier but expensive for large clones)
        for start_dim, stop_dim in zip(start_corner, stop_corner):
            if start_dim <= stop_dim:
                begin.append(start_dim)
                end.append(stop_dim + 1)
            else:
                begin.append(stop_dim)
                end.append(start_dim + 1)

        start = Vec3(*begin)
        stop = Vec3(*end)
        d_stop = dest + stop - start
        self.world[
            dest.x : d_stop.x, dest.y : d_stop.y, dest.z : d_stop.z
        ] = self.world[
            start.x : stop.x,
            start.y : stop.y,
            start.z : stop.z,
        ]
        return f"cloned {start} : {stop} to {dest}"

    @property
    def loot(self):
        """
        Support the 'grab' command which looks like this:
        == client.loot.spawn(dump).mine(vol.start + Vec3(*idx)) ==
        It is the convoluted way to find what block is at a coordinate.

        TODO: review this weird way to provide sub commands!
        """
        parent = self

        class spawn_cls:
            def spawn(self, dump):
                class mine_cls:
                    def mine(self, pos: Vec3):
                        return str(parent.getblock(pos))

                return mine_cls()

        return spawn_cls()

    ###########################################################################
    # the following are additional functions for use in tests #################
    ###########################################################################

    def getblock(self, pos: Vec3) -> Item:
        """return the block at position in the world"""
        return self.world[int(pos.x), int(pos.y), int(pos.z)]

    def compare(self, pos: Vec3, cube: Items):
        """verify that the contents of the world at pos matches cube"""
        n_cube = np.array(cube)
        upper = pos + Vec3(*(n_cube.shape))
        world_slice = self.world[pos.x : upper.x, pos.y : upper.y, pos.z : upper.z]

        return np.array_equal(world_slice, n_cube)
