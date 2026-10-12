"""
A compact 3D array of the blocks in a cuboid region of a Minecraft world.

`BlockGrid` is what the readers return (`read_world_blocks` reads the world's
region files, `grab_blocks` asks the server over RCON) and what
`mciwb.render` draws.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from time import monotonic

import numpy as np
from mcwb import Vec3, Volume
from mcwb.itemlists import grab

from mciwb.logging import log
from mciwb.threads import Client

AIR = "minecraft:air"


def block_name(name: object) -> str:
    """
    Normalise a block name to its namespaced id, e.g. ``Item.STONE``,
    ``"stone"`` and ``"minecraft:stone[axis=y]"`` all give ``"minecraft:stone"``
    """
    text = str(name).split("[", 1)[0].split("{", 1)[0].strip()
    return text if ":" in text else f"minecraft:{text}"


@dataclass
class BlockGrid:
    """
    The blocks of a cuboid region of the world.

    Each block is stored as an index into a list of block names, which keeps
    large regions small and makes per-block lookups (e.g. colours) cheap.

    :ivar origin: the world position of the block at index [0, 0, 0], the
        lowest (north west bottom) corner of the region
    :ivar ids: integer array of shape (size x, size y, size z), indexed
        ``ids[x][y][z]`` like a ``mcwb.Cuboid``
    :ivar names: the namespaced block id for each index in *ids*, e.g.
        ``"minecraft:stone"``
    """

    origin: Vec3
    ids: np.ndarray
    names: list[str]

    def __post_init__(self):
        self.origin = Vec3(*self.origin).with_ints()
        if self.ids.ndim != 3:
            raise ValueError(f"ids must be 3 dimensional, not {self.ids.shape}")

    @classmethod
    def from_blocks(cls, blocks: Iterable, origin: Vec3) -> BlockGrid:
        """
        Make a grid from a 3D array of block names or ``mcwb.Item``, indexed
        ``[x][y][z]``, such as the ``mcwb.Cuboid`` returned by ``grab``

        :param blocks: a nested list or numpy array of blocks
        :param origin: the world position of blocks[0][0][0]
        """
        array = np.array(blocks, dtype=object)
        if array.ndim != 3:
            raise ValueError(f"blocks must be a 3D array, not shape {array.shape}")
        index: dict[str, int] = {}
        ids = np.empty(array.shape, dtype=np.int32)
        for pos, block in np.ndenumerate(array):
            ids[pos] = index.setdefault(block_name(block), len(index))
        return cls(origin, ids, list(index))

    @property
    def size(self) -> Vec3:
        """the size of the region in blocks (x, y, z)"""
        return Vec3(*self.ids.shape)

    @property
    def end(self) -> Vec3:
        """the world position of the highest (south east top) corner block"""
        return self.origin + self.size - 1

    @property
    def volume(self) -> Volume:
        """the region as a ``mcwb.Volume``"""
        return Volume.from_corners(self.origin, self.end)

    def __getitem__(self, pos: Vec3) -> str:
        """the name of the block at a world position, e.g. grid[Vec3(1, 2, 3)]"""
        local = Vec3(*pos).with_ints() - self.origin
        if not all(0 <= c < s for c, s in zip(local, self.ids.shape, strict=True)):
            raise IndexError(f"{pos} is outside {self.origin} to {self.end}")
        return self.names[self.ids[local.i_tuple]]

    def counts(self, include_air: bool = False) -> dict[str, int]:
        """
        Count the blocks of each type, most common first. A quick way to
        check that a build contains what it should.

        :param include_air: also count air (and cave air and void air)
        """
        totals = np.bincount(self.ids.ravel(), minlength=len(self.names))
        counter = Counter(
            {
                name: int(total)
                for name, total in zip(self.names, totals, strict=True)
                if total and (include_air or not name.endswith("air"))
            }
        )
        return dict(counter.most_common())

    def to_names(self) -> np.ndarray:
        """a 3D numpy array of block names, indexed [x][y][z]"""
        return np.array(self.names, dtype=object)[self.ids]


def grab_blocks(client: Client, vol: Volume) -> BlockGrid:
    """
    Read a region of the world one block at a time over RCON.

    This works with any server, local or remote, but makes one RCON command
    per block: use `mciwb.anvil.read_world_blocks` for regions of more than a
    few thousand blocks when the world's files are on this machine.

    :param client: an RCON client for the current thread
    :param vol: the region to read
    """
    start = monotonic()
    grid = BlockGrid.from_blocks(grab(client, vol), vol.start)
    elapsed = monotonic() - start
    log.debug(f"read {vol.size.volume} blocks over RCON in {elapsed:.1f}s")
    return grid
