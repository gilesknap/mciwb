"""
A mock client for testing functions that call the minecraft server.
This mocks a world of 100 blocks square with origin in the middle.
"""
from math import floor

import numpy as np
from mcipc.rcon.enumerations import Item
from mcwb.types import Items, Vec3


class MockClient:
    def __init__(self, host, port, passwd=None):
        """create an empty mock world"""
        self.world = np.full((100, 100, 100), Item.AIR, dtype=Item)
        self.offset = Vec3(50, 50, 50)
        self.host = host
        self.port = port
        self.passwd = passwd

        self.connected = False

    # the following are mock versions of the original Client Functions
    def connect(self, retry=True):
        self.connected = True

    def setblock(self, position: Vec3, block: Item):
        """set the block at position in the world"""
        pos = position - self.offset
        self.world[pos.x, pos.y, pos.z] = block

    def fill(self, start: Vec3, end: Vec3, block: Item):
        block = Item(block)  # ensure enum
        start -= self.offset
        end -= self.offset - 1
        self.world[
            floor(start.x) : floor(end.x),
            floor(start.y) : floor(end.y),
            floor(start.z) : floor(end.z),
        ] = block

    # the following are additional functions for use in tests

    def getblock(self, position: Vec3) -> Item:
        """return the block at position in the world"""
        pos = position - self.offset
        return self.world[int(pos.x), int(pos.y), int(pos.z)]

    def compare(self, position: Vec3, cube: Items):
        """verify that the contents of the world at pos matches cube"""
        n_cube = np.array(cube)
        pos = position - self.offset
        upper = pos + Vec3(*(n_cube.shape))
        world_slice = self.world[pos.x : upper.x, pos.y : upper.y, pos.z : upper.z]

        return np.array_equal(world_slice, n_cube)
