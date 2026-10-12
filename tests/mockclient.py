"""
A mock client for testing functions that call the minecraft server.
This mocks a world of 100 blocks square with origin in the middle.
"""

from math import floor

import numpy as np
from mcipc.rcon.enumerations import CloneMode, MaskMode
from mcwb.types import Items

from mciwb.imports import Item, Player, Vec3, Volume


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
        # the text of signs in the mock world, keyed by block position
        self.signs: dict[tuple[int, int, int], str] = {}
        # the rotation of the mock player 'georgeTest' (yaw, pitch)
        self.rotation = (0.0, 0.0)
        # record of all items given to players
        self.given: list[tuple[str, str]] = []
        self.gamerules: dict[str, bool | int] = {}

    # The responses below mimic those of a Minecraft 26.3 server

    ###########################################################################
    # the following are mock versions of the original Client Functions ########
    ###########################################################################

    def op(self, name):
        """set user as operator"""

    def gamemode(self, mode, user):
        """set user gamemode"""

    def connect(self, retry=True):
        self.connected = True

    def gamerule(self, rule: str, value: bool | int):
        self.gamerules[rule] = value
        return f"Game rule {rule} is now set to {str(value).lower()}"

    def give(self, target: str, item: str):
        self.given.append((target, item))
        return f"Gave 1 [{item}] to {target}"

    def setblock(self, pos: Vec3, block: Item):
        """set the block at position in the world"""
        self.world[int(pos.x), int(pos.y), int(pos.z)] = block

    def fill(self, start: Vec3, end: Vec3, block: Item):
        block = Item(block)  # ensure enum
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

        # use Volume to normalize the corners for use in slicing
        vol = Volume.from_corners(start_corner, stop_corner)

        v_start = vol.start
        v_stop = v_start + vol.size
        d_stop = dest + vol.size

        self.world[dest.x : d_stop.x, dest.y : d_stop.y, dest.z : d_stop.z] = (
            self.world[
                v_start.x : v_stop.x,
                v_start.y : v_stop.y,
                v_start.z : v_stop.z,
            ]
        )
        return f"cloned {v_start} : {v_stop} to {dest}"

    @property
    def loot(self):
        """
        Support the 'grab' command which looks like this:
        == client.loot.spawn(dump).mine(vol.start + Vec3(*idx)) ==
        It is the convoluted way to find what block is at a coordinate.
        """
        parent = self

        class SpawnCls:
            def spawn(self, dump):
                class MineCls:
                    def mine(self, pos: Vec3):
                        return str(parent.getblock(pos))

                return MineCls()

        return SpawnCls()

    def kill(self, targets: str):
        return "No entity was found"

    def summon(self, entity_type, pos: Vec3, properties):
        """
        summon an entity at position with properties
        """
        # for simplicity, assume 'georgeTest' was summoned at 0,-16,-60, rotation=0
        # the data property below will deliver these values

    @property
    def players(self):
        class PlayersCls:
            @property
            def players(self):
                return [Player("georgeTest")]

        return PlayersCls()

    @property
    def data(self):
        parent = self

        class GetCls:
            def get(
                self,
                block: Vec3 | None = None,
                entity: str | None = None,
                path: str | None = None,
            ):
                if block is not None:
                    key = (int(block.x), int(block.y), int(block.z))
                    if key not in parent.signs:
                        return "The target block is not a block entity"
                    text = parent.signs[key]
                    pos = f"{key[0]}, {key[1]}, {key[2]}"
                    if path == "front_text.messages[0]":
                        return f'{pos} has the following block data: "{text}"'
                    return (
                        f"{pos} has the following block data: {{back_text: "
                        '{has_glowing_text: 0b, color: "black", '
                        'messages: ["", "", "", ""]}, id: "minecraft:sign", '
                        'front_text: {has_glowing_text: 0b, color: "black", '
                        f'messages: ["{text}", "", "", ""]}}}}'
                    )
                # summon puts the armor stand 'georgeTest' at the block centre
                if path == "Pos":
                    data = "[0.5d, -60.0d, 0.5d]"
                elif path == "Rotation":
                    data = f"[{parent.rotation[0]}f, {parent.rotation[1]}f]"
                elif path == "Inventory":
                    data = "[]"
                else:
                    return f"Found no elements matching {path}"
                return f"georgeTest has the following entity data: {data}"

        return GetCls()

    @property
    def execute(self):
        """
        Support 'execute if block <pos> <block> run seed'
        """
        parent = self

        class Run:
            def __init__(self, passed: bool):
                self.passed = passed

            def run(self, command: str):
                return "Seed: [0]" if self.passed else ""

        class If:
            def block(self, pos: Vec3, block: str):
                return Run(str(parent.getblock(pos)) == str(block))

        class Execute:
            if_ = If()

        return Execute()

    ###########################################################################
    # the following are additional functions for use in tests #################
    ###########################################################################

    def place_sign(self, pos: Vec3, text: str, block: Item = Item.OAK_SIGN):
        """place a sign with text on its front at position in the world"""
        self.setblock(pos, block)
        self.signs[(int(pos.x), int(pos.y), int(pos.z))] = text

    def getblock(self, pos: Vec3) -> Item:
        """return the block at position in the world"""
        return self.world[int(pos.x), int(pos.y), int(pos.z)]

    def compare(self, pos: Vec3, cube: Items):
        """verify that the contents of the world at pos matches cube"""
        n_cube = np.array(cube, dtype=Item)
        upper = pos + Vec3(*(n_cube.shape))
        world_slice = self.world[pos.x : upper.x, pos.y : upper.y, pos.z : upper.z]

        return np.array_equal(world_slice, n_cube)
