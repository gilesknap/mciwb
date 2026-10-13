"""
A mock client for testing functions that call the minecraft server.
This mocks a world of 100 blocks square with origin in the middle.
"""

import itertools
import re
from math import floor
from typing import Any

import numpy as np
from mcipc.rcon.enumerations import CloneMode, FillMode, MaskMode
from mcwb.types import Items

from mciwb.imports import Item, Player, Vec3, Volume


class MockClient:
    """
    A mock version of the RCON client for unit testing.
    """

    # the state of each mock server, keyed by (host, port). Every MockClient
    # connected to the same server shares it, just like real RCON clients
    # share one Minecraft world. This lets Monitor threads, which make their
    # own client, see the world that the test set up.
    _servers: dict[tuple[str, int], dict[str, Any]] = {}

    def __init__(self, host, port, passwd=None, timeout=None):
        self.host = host
        self.port = port
        self.passwd = passwd
        self.connected = False

        state = self._servers.setdefault((host, port), {})
        if not state:
            # create an empty mock world full of air
            # note that numpy will wrap around indexes so this world has
            # ability to index from -50 to 50 in each dimension
            state["world"] = np.full((100, 100, 100), Item.AIR, dtype=Item)
            # the block states (e.g. "powered=true") of blocks, keyed by position
            state["states"] = {}
            # the text of signs in the mock world, keyed by block position
            state["signs"] = {}
            # the rotation of the mock player 'georgeTest' (yaw, pitch)
            state["rotation"] = (0.0, 0.0)
            # record of all items given to players
            state["given"] = []
            state["gamerules"] = {}
            # record of all commands sent with run(), say(), save_*() etc.
            state["commands"] = []
            # record of all setblock and fill commands, as Minecraft commands
            state["block_commands"] = []
            # positions of the marker entities summoned, keyed by tag
            state["markers"] = {}
        self._state = state

    @classmethod
    def reset(cls):
        """Forget the state of every mock server"""
        cls._servers.clear()

    world = property(lambda self: self._state["world"])
    states = property(lambda self: self._state["states"])
    signs = property(lambda self: self._state["signs"])
    given = property(lambda self: self._state["given"])
    gamerules = property(lambda self: self._state["gamerules"])
    commands = property(lambda self: self._state["commands"])
    block_commands = property(lambda self: self._state["block_commands"])
    markers = property(lambda self: self._state["markers"])

    @property
    def rotation(self) -> tuple[float, float]:
        return self._state["rotation"]

    @rotation.setter
    def rotation(self, value: tuple[float, float]):
        self._state["rotation"] = value

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

    def close(self):
        self.connected = False

    def gamerule(self, rule: str, value: bool | int):
        self.gamerules[rule] = value
        return f"Game rule {rule} is now set to {str(value).lower()}"

    def give(self, target: str, item: str):
        self.given.append((target, item))
        return f"Gave 1 [{item}] to {target}"

    def setblock(self, pos: Vec3, block: Item | str, mode=None):
        """set the block at position in the world"""
        key = (int(pos.x), int(pos.y), int(pos.z))
        self.block_commands.append(f"setblock {key[0]} {key[1]} {key[2]} {block}")
        self._set(key, str(block))
        return f"Changed the block at {key[0]}, {key[1]}, {key[2]}"

    def _set(self, key: tuple[int, ...], block: str):
        # split e.g. 'minecraft:oak_door[half=lower]' into item and state
        name, _, state = block.partition("[")
        name = name.split("{")[0]
        self.world[key] = Item(name)
        if state:
            self.states[key] = state.rstrip("]")
        else:
            self.states.pop(key, None)

    def fill(
        self,
        start: Vec3,
        end: Vec3,
        block: Item | str,
        mode: FillMode | None = None,
        filter: str | None = None,
    ):
        """
        fill a volume, including both corners, like the Minecraft command.
        Supports block states, and the keep and replace (with a filter) modes
        """
        lo = [floor(min(a, b)) for a, b in zip(start, end, strict=True)]
        hi = [floor(max(a, b)) for a, b in zip(start, end, strict=True)]
        command = f"fill {' '.join(map(str, lo))} {' '.join(map(str, hi))} {block}"
        if mode is not None:
            command += f" {FillMode(mode).value}"
            if filter is not None:
                command += f" {filter}"
        self.block_commands.append(command)

        keys = itertools.product(
            *(range(a, b + 1) for a, b in zip(lo, hi, strict=True))
        )
        simple = mode in (None, FillMode.REPLACE) and filter is None
        if simple and "[" not in block and min(lo) >= 0:
            # the common case, quickly (slices do not wrap negative indexes)
            self.world[lo[0] : hi[0] + 1, lo[1] : hi[1] + 1, lo[2] : hi[2] + 1] = Item(
                block
            )
            for key in [
                k for k in self.states if all(lo[i] <= k[i] <= hi[i] for i in range(3))
            ]:
                del self.states[key]
            count = int(np.prod(np.subtract(hi, lo) + 1))
        else:
            count = 0
            for key in keys:
                if mode == FillMode.KEEP and self.world[key] != Item.AIR:
                    continue
                if filter is not None and not self.matches(Vec3(*key), filter):
                    continue
                self._set(key, str(block))
                count += 1
        if count == 0:
            return "No blocks were filled"
        return f"Successfully filled {count} block(s)"

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
                return Run(parent.matches(pos, str(block)))

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

    def matches(self, pos: Vec3, block: str) -> bool:
        """
        Test the block at pos as 'execute if block' does. Supports the
        #minecraft:wall_signs tag and block states e.g. lever[powered=true]
        """
        actual = str(self.getblock(pos))
        if block == "#minecraft:wall_signs":
            return actual.endswith("_wall_sign")
        name, _, state = block.partition("[")
        if actual != str(Item(name)):
            return False
        key = (int(pos.x), int(pos.y), int(pos.z))
        actual_states = dict(
            s.split("=")
            for s in self.states.get(key, "").replace(" ", "").split(",")
            if s
        )
        for wanted in state.rstrip("]").replace(" ", "").split(","):
            if wanted:
                prop, value = wanted.split("=")
                # treat states that were not set as false e.g. powered=false
                if actual_states.get(prop, "false") != value:
                    return False
        return True

    def say(self, message: str) -> str:
        self.commands.append(f"say {message}")
        return ""

    def save_off(self) -> str:
        self.commands.append("save-off")
        return "Automatic saving is now disabled"

    def save_all(self, flush: bool = False) -> str:
        self.commands.append("save-all flush" if flush else "save-all")
        return "Saved the game"

    def save_on(self) -> str:
        self.commands.append("save-on")
        return "Automatic saving is now enabled"

    def run(self, command: str, *args: str) -> str:
        command = " ".join((command, *args))
        self.commands.append(command)
        if match := re.match(
            r"summon minecraft:marker (\S+) (\S+) (\S+) .*\"(\w+)\"", command
        ):
            self.markers[match.group(4)] = tuple(map(float, match.groups()[:3]))
            return "Summoned new Marker"
        if match := re.match(
            r"execute positioned (\S+) 0 (\S+) positioned over \w+ run tp "
            r"@e\[type=minecraft:marker,tag=(\w+),limit=1\] ~ ~ ~",
            command,
        ):
            x, z = int(match.group(1)), int(match.group(2))
            # the mock heightmap: the first block above the highest solid one
            y = self.height(x, z)
            self.markers[match.group(3)] = (x + 0.5, y, z + 0.5)
            return f"Teleported Marker to {x + 0.5:f}, {y:f}, {z + 0.5:f}"
        if match := re.match(r"kill @e\[type=minecraft:marker,tag=(\w+)\]", command):
            if self.markers.pop(match.group(1), None) is None:
                return "No entity was found"
            return "Killed Marker"
        return f"ran {command}"

    def height(self, x: int, z: int) -> int:
        """
        The mock world's heightmap at x, z: one above the highest block that
        is not air, or the bottom of the mock world (-50)
        """
        for y in range(49, -51, -1):
            if self.world[x, y, z] != Item.AIR:
                return y + 1
        return -50

    def state_at(self, pos: Vec3) -> str:
        """the block state at pos, as a string e.g. 'minecraft:stone'"""
        key = (int(pos.x), int(pos.y), int(pos.z))
        state = self.states.get(key)
        block = str(self.getblock(pos))
        return f"{block}[{state}]" if state else block

    def getblock(self, pos: Vec3) -> Item:
        """return the block at position in the world"""
        return self.world[int(pos.x), int(pos.y), int(pos.z)]

    def compare(self, pos: Vec3, cube: Items):
        """verify that the contents of the world at pos matches cube"""
        n_cube = np.array(cube, dtype=Item)
        upper = pos + Vec3(*(n_cube.shape))
        world_slice = self.world[pos.x : upper.x, pos.y : upper.y, pos.z : upper.z]

        return np.array_equal(world_slice, n_cube)
