"""
Sponge schematic (``.schem``) files: the format that WorldEdit, Litematica
and most other Minecraft tools exchange structures in.

A `Schematic` holds a box of block states in memory, indexed
``blocks[x][y][z]`` from its bottom north west corner, like the cuboids of
``mcwb.Item`` that ``grab`` returns and ``Blocks`` renders. It can be grabbed from
the world, pasted into it, converted to and from those cuboids, rotated and
mirrored, and loaded from and saved to files.

The specification of the format is at
https://github.com/SpongePowered/Schematic-Specification. Files are written
in version 3, versions 2 and 3 can be read.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from mcwb import Vec3, Volume
from mcwb.api import get_block

from mciwb.builders.blockstate import BlockState
from mciwb.builders.nbtfile import (
    ByteArray,
    Int,
    IntArray,
    Short,
    TagList,
    load_nbt,
    save_nbt,
)
from mciwb.builders.placer import Placer
from mciwb.logging import log
from mciwb.threads import get_client

__all__ = ["DATA_VERSION", "Schematic"]

DATA_VERSION = 5023
"""The data version of Minecraft 26.3, written in saved schematics"""

AIR = BlockState("minecraft:air")
ORIGIN = Vec3(0, 0, 0)

# the block state properties that from_world reads back for some families
# of blocks, with their possible values (most common first)
_STAIRS = [
    ("facing", ["north", "south", "east", "west"]),
    ("half", ["bottom", "top"]),
    ("shape", ["straight", "outer_left", "outer_right", "inner_left", "inner_right"]),
]
_SLAB = [("type", ["bottom", "top", "double"])]
_AXIS = [("axis", ["y", "x", "z"])]
_AXIS_SUFFIXES = ("_log", "_wood", "_stem", "_hyphae", "_pillar", "_chain")
_AXIS_BLOCKS = {
    "bamboo_block",
    "basalt",
    "bone_block",
    "creaking_heart",
    "deepslate",
    "hay_block",
    "infested_deepslate",
    "muddy_mangrove_roots",
    "ochre_froglight",
    "pearlescent_froglight",
    "polished_basalt",
    "stripped_bamboo_block",
    "verdant_froglight",
}


def _probed_properties(name: str) -> list[tuple[str, list[str]]]:
    short = name.removeprefix("minecraft:")
    if short.endswith("_stairs"):
        return _STAIRS
    if short.endswith("_slab"):
        return _SLAB
    if short.endswith(_AXIS_SUFFIXES) or short in _AXIS_BLOCKS:
        return _AXIS
    return []


def _read_varints(data: bytes, count: int) -> list[int]:
    values: list[int] = []
    value = shift = 0
    for byte in data:
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
        else:
            values.append(value)
            value = shift = 0
    if len(values) != count:
        raise ValueError(f"schematic has {len(values)} blocks, expected {count}")
    return values


def _write_varints(values: list[int]) -> bytes:
    data = bytearray()
    for value in values:
        while value >= 0x80:
            data.append(value & 0x7F | 0x80)
            value >>= 7
        data.append(value)
    return bytes(data)


def _unsigned_short(value: int) -> int:
    return value & 0xFFFF


def _signed_short(value: int) -> Short:
    if not 0 < value <= 0xFFFF:
        raise ValueError(f"schematic dimension {value} is out of range")
    return Short(value - 0x10000 if value >= 0x8000 else value)


class Schematic:
    """
    A box of blocks with their block states, e.g. to save to, or load from,
    a Sponge schematic ``.schem`` file.

    For example, copy a building with its stairs and slabs facing the right
    way, turned a quarter turn clockwise::

        house = Schematic.from_world(Volume.from_corners(corner1, corner2))
        house.save("house.schem")
        Schematic.load("house.schem").rotate(1).paste(Vec3(100, 64, 0))

    :ivar blocks: a 3D numpy array of `BlockState`, indexed ``[x][y][z]``
    :ivar block_entities: the block entities (chests, signs ...) from a
        file, as Sponge BlockEntity compounds (``Pos``, ``Id``, ``Data``).
        These are kept when saving, but not pasted into the world
    :ivar offset: the Sponge ``Offset`` of the file, kept when saving, but
        not used when pasting
    :ivar metadata: the Sponge ``Metadata`` compound (``Name``, ``Author``...)
    :ivar data_version: the Minecraft data version that the blocks are from
    """

    def __init__(
        self,
        blocks: np.ndarray,
        *,
        block_entities: list[dict[str, Any]] | None = None,
        offset: Vec3 = ORIGIN,
        metadata: dict[str, Any] | None = None,
        data_version: int = DATA_VERSION,
    ) -> None:
        if blocks.ndim != 3 or 0 in blocks.shape:
            raise ValueError("blocks must be a 3D array with no empty sides")
        self.blocks = blocks
        self.block_entities = block_entities or []
        self.offset = offset
        self.metadata = metadata or {}
        self.data_version = data_version

    @property
    def size(self) -> Vec3:
        """The size of the schematic, as (width x, height y, length z)"""
        return Vec3(*self.blocks.shape)

    def __repr__(self) -> str:
        size = "x".join(str(n) for n in self.blocks.shape)
        return f"<Schematic {size}, {len(self.palette)} block states>"

    @property
    def palette(self) -> list[BlockState]:
        """The different block states in the schematic"""
        return list(dict.fromkeys(self.blocks.ravel()))

    # conversions #############################################################

    @classmethod
    def from_cuboid(cls, cuboid: Sequence[Any] | np.ndarray) -> Schematic:
        """
        Make a schematic from a 3D list (or numpy array) of blocks indexed
        ``[x][y][z]``, e.g. from ``grab`` or ``load_items``. The blocks may be
        ``Item``, block state strings or `BlockState`.
        """
        items = np.array(cuboid, dtype=object)
        if items.ndim != 3:
            raise ValueError("cuboid must be 3 dimensional")
        return cls(np.vectorize(BlockState.parse, otypes=[object])(items))

    def to_cuboid(self) -> list:
        """
        The blocks as a 3D list of ``Item`` indexed ``[x][y][z]``, for use with
        ``Blocks`` or ``save_items``. This loses the block states.

        :raises ValueError: if a block is not in ``Item`` e.g. a modded block
        """
        return np.vectorize(lambda state: state.item, otypes=[object])(
            self.blocks
        ).tolist()

    @classmethod
    def from_world(cls, volume: Volume, states: bool = True) -> Schematic:
        """
        Read the blocks in a Volume of the world.

        Reading is slow: one RCON command for each block, and when *states*
        is True a few more for each stairs, slab and log-like block, to find
        its ``facing``, ``half``, ``shape``, ``type`` or ``axis``. Other block
        states (e.g. the facing of a door or a furnace) can not be read
        back, and those blocks take their default state. Block entity data
        (e.g. chest contents) is not read either. Some blocks read back as
        a related block, e.g. a wall torch as a torch, see ``get_block``.

        :param volume: the box of the world to read
        :param states: read the block states of stairs, slabs and logs
        """
        client = get_client()
        blocks = np.empty(volume.size.i_tuple, dtype=object)
        for idx in np.ndindex(blocks.shape):
            pos = volume.start + Vec3(*idx)
            item = get_block(client, pos)
            state = BlockState(item.value)
            if states:
                for prop, values in _probed_properties(state.name):
                    found = values[-1]
                    for value in values[:-1]:
                        test = f"{state.name}[{prop}={value}]"
                        result = client.execute.if_.block(pos, test).run("seed")
                        if "Seed" in result:
                            found = value
                            break
                    state = state.with_props(**{prop: found})
            blocks[idx] = state
        return cls(blocks)

    def paste(self, position: Vec3, air: bool = False) -> Volume:
        """
        Place the blocks in the world, with the schematic's bottom north west
        corner (``blocks[0][0][0]``) at *position*. Uses one ``fill`` for
        each rectangle of the same block state in each layer, bottom layer
        first.

        :param position: where to put the bottom north west corner
        :param air: if True, also place the air blocks, clearing whatever is
            in the box. If False, leave the world unchanged where the
            schematic has air
        :returns: the box that the schematic covers in the world
        """
        position = Vec3(*position).with_ints()
        if self.block_entities:
            log.warning(
                f"the block entity data of {len(self.block_entities)} blocks "
                "is not pasted"
            )
        placer = Placer()
        for y in range(self.blocks.shape[1]):
            layer = {}
            for x, z in np.ndindex(self.blocks.shape[0], self.blocks.shape[2]):
                state: BlockState = self.blocks[x, y, z]
                if air or not state.is_air:
                    layer[(int(position.x) + x, int(position.z) + z)] = state
            placer.layer(int(position.y) + y, layer)
        return Volume.from_corners(position, position + self.size - 1)

    # transforms ##############################################################

    def _transformed(
        self,
        blocks: np.ndarray,
        state_map: Callable[[BlockState], BlockState],
        pos_map: Callable[[Vec3], Vec3],
    ) -> Schematic:
        """A new schematic with the blocks moved and their states changed"""
        cache: dict[BlockState, BlockState] = {}

        def change(state: BlockState) -> BlockState:
            if state not in cache:
                cache[state] = state_map(state)
            return cache[state]

        entities = []
        for entity in self.block_entities:
            moved = dict(entity)
            moved["Pos"] = IntArray(pos_map(Vec3(*entity["Pos"])))
            entities.append(moved)
        return Schematic(
            np.vectorize(change, otypes=[object])(blocks),
            block_entities=entities,
            offset=self.offset,
            metadata=dict(self.metadata),
            data_version=self.data_version,
        )

    def rotate(self, steps: int = 1) -> Schematic:
        """
        A copy of the schematic turned about the Y axis by *steps* quarter
        turns clockwise, viewed from above (so a stairs block facing north
        faces east after one step). See `BlockState.rotate` for the block
        states that turn with it.
        """
        steps %= 4
        result = self
        for _ in range(steps):
            width, _, length = result.blocks.shape
            # clockwise: (x, z) moves to (length - 1 - z, x)
            turned = np.transpose(result.blocks, (2, 1, 0))[::-1, :, :]
            result = result._transformed(
                turned,
                lambda state: state.rotate(1),
                lambda pos, length=length: Vec3(length - 1 - pos.z, pos.y, pos.x),
            )
        return result

    def mirror(self, axis: str) -> Schematic:
        """
        A mirror image copy of the schematic: ``"x"`` swaps east and west,
        ``"z"`` swaps north and south. See `BlockState.mirror`.
        """
        if axis not in ("x", "z"):
            raise ValueError("axis must be 'x' or 'z'")
        width, _, length = self.blocks.shape
        if axis == "x":
            flipped = self.blocks[::-1, :, :]

            def pos_map(pos: Vec3) -> Vec3:
                return Vec3(width - 1 - pos.x, pos.y, pos.z)
        else:
            flipped = self.blocks[:, :, ::-1]

            def pos_map(pos: Vec3) -> Vec3:
                return Vec3(pos.x, pos.y, length - 1 - pos.z)

        return self._transformed(flipped, lambda state: state.mirror(axis), pos_map)

    # files ###################################################################

    @classmethod
    def load(cls, filename: Path | str) -> Schematic:
        """
        Load a Sponge schematic file (version 2 or 3).
        """
        _, root = load_nbt(filename)
        if "Schematic" in root:  # version 3 nests everything in 'Schematic'
            root = root["Schematic"]
        version = int(root.get("Version", 0))
        if version == 3:
            container = root.get("Blocks", {})
            palette, data = container.get("Palette", {}), container.get("Data", b"")
            entities = container.get("BlockEntities", [])
        elif version == 2:
            palette, data = root.get("Palette", {}), root.get("BlockData", b"")
            entities = root.get("BlockEntities", [])
        else:
            raise ValueError(f"{filename} is not a Sponge schematic version 2 or 3")

        size = tuple(
            _unsigned_short(root[key]) for key in ("Width", "Height", "Length")
        )
        width, height, length = size
        by_index = {
            int(index): BlockState.parse(state) for state, index in palette.items()
        }
        if not by_index:
            by_index = {0: AIR}
        indices = _read_varints(bytes(data), width * height * length)
        # the data is ordered x fastest, then z, then y
        ordered = np.array([by_index[i] for i in indices], dtype=object)
        blocks = ordered.reshape((height, length, width)).transpose(2, 0, 1)
        return cls(
            np.ascontiguousarray(blocks),
            block_entities=list(entities),
            offset=Vec3(*root.get("Offset", [0, 0, 0])),
            metadata=dict(root.get("Metadata", {})),
            data_version=int(root.get("DataVersion", DATA_VERSION)),
        )

    def save(self, filename: Path | str) -> None:
        """
        Save as a Sponge schematic version 3 file (``.schem``).
        """
        palette: dict[BlockState, int] = {}
        ordered = self.blocks.transpose(1, 2, 0).ravel()
        indices = [palette.setdefault(state, len(palette)) for state in ordered]
        width, height, length = self.blocks.shape
        blocks: dict[str, Any] = {
            "Palette": {str(state): Int(index) for state, index in palette.items()},
            "Data": ByteArray(_write_varints(indices)),
        }
        if self.block_entities:
            blocks["BlockEntities"] = TagList(self.block_entities)
        schematic: dict[str, Any] = {
            "Version": Int(3),
            "DataVersion": Int(self.data_version),
        }
        if self.metadata:
            schematic["Metadata"] = self.metadata
        schematic.update(
            {
                "Width": _signed_short(width),
                "Height": _signed_short(height),
                "Length": _signed_short(length),
                "Offset": IntArray(int(n) for n in self.offset),
                "Blocks": blocks,
            }
        )
        save_nbt(filename, {"Schematic": schematic})
