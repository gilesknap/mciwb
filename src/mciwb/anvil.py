"""
Read blocks straight from the region (.mca) files of a Minecraft world.

This is much faster than asking the server for one block at a time over RCON
(see `mciwb.blockgrid.grab_blocks`): it needs the world folder to be on this
machine, as it is for the server that ``mciwb start`` runs. A running server
keeps recent changes in memory, so ask it to write them out first with
``save-all flush`` (`mciwb.render.scan` does this for you).

The readers here are small, read-only and use numpy for the bulky parts. They
support the chunk format of Minecraft 1.18 and later, including the
``dimensions/<namespace>/<name>`` world layout of Minecraft 26.1 and later.
See https://minecraft.wiki/w/Region_file_format and
https://minecraft.wiki/w/Chunk_format.
"""

from __future__ import annotations

import gzip
import struct
import zlib
from pathlib import Path
from time import monotonic
from typing import Any

import numpy as np
from mcwb import Volume

from mciwb.blockgrid import AIR, BlockGrid, block_name
from mciwb.logging import log

# the folders that hold each dimension's region files, newest layout first
_DIMENSION_FOLDERS = {
    "overworld": ("dimensions/minecraft/overworld", "."),
    "the_nether": ("dimensions/minecraft/the_nether", "DIM-1"),
    "the_end": ("dimensions/minecraft/the_end", "DIM1"),
}

SECTOR = 4096
SECTION_BLOCKS = 16 * 16 * 16


# ----------------------------------------------------------------------------
# NBT: https://minecraft.wiki/w/NBT_format


class _NbtReader:
    """Decode one uncompressed binary NBT document"""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def _unpack(self, fmt: str) -> Any:
        value = struct.unpack_from(fmt, self.data, self.pos)[0]
        self.pos += struct.calcsize(fmt)
        return value

    def _string(self) -> str:
        length = self._unpack(">H")
        raw = self.data[self.pos : self.pos + length]
        self.pos += length
        # NBT strings are Java's modified UTF-8: plain UTF-8 for block names
        return raw.decode("utf-8", errors="replace")

    def _array(self, dtype: str) -> np.ndarray:
        count = self._unpack(">i")
        array = np.frombuffer(self.data, dtype=dtype, count=count, offset=self.pos)
        self.pos += array.nbytes
        return array

    def _payload(self, tag: int) -> Any:
        match tag:
            case 1:
                return self._unpack(">b")
            case 2:
                return self._unpack(">h")
            case 3:
                return self._unpack(">i")
            case 4:
                return self._unpack(">q")
            case 5:
                return self._unpack(">f")
            case 6:
                return self._unpack(">d")
            case 7:
                return self._array(">i1")
            case 8:
                return self._string()
            case 9:
                item_tag = self._unpack(">b")
                length = self._unpack(">i")
                return [self._payload(item_tag) for _ in range(length)]
            case 10:
                compound = {}
                while (item_tag := self._unpack(">b")) != 0:
                    name = self._string()
                    compound[name] = self._payload(item_tag)
                return compound
            case 11:
                return self._array(">i4")
            case 12:
                return self._array(">i8")
            case _:
                raise ValueError(f"unknown NBT tag {tag} at byte {self.pos}")

    def read(self) -> dict[str, Any]:
        tag = self._unpack(">b")
        if tag != 10:
            raise ValueError(f"NBT document must be a compound, not tag {tag}")
        self._string()  # the root's name, usually empty
        return self._payload(tag)


def read_nbt(data: bytes) -> dict[str, Any]:
    """
    Decode binary NBT (uncompressed) into Python objects: compounds become
    dicts, lists become lists and arrays become numpy arrays.
    """
    return _NbtReader(data).read()


# ----------------------------------------------------------------------------
# region files


class RegionFile:
    """
    One region (.mca) file: the chunks of a 32 x 32 chunk area.

    :param path: the path of the file, ``r.<region x>.<region z>.mca``
    """

    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes() if path.exists() else b""

    def chunk(self, cx: int, cz: int) -> dict[str, Any] | None:
        """
        Read a chunk's NBT, or None if the chunk has not been generated

        :param cx: the chunk's x coordinate (block x // 16)
        :param cz: the chunk's z coordinate (block z // 16)
        """
        if len(self.data) < 2 * SECTOR:
            return None
        entry = 4 * ((cx & 31) + (cz & 31) * 32)
        location = int.from_bytes(self.data[entry : entry + 3], "big")
        if location == 0:
            return None
        start = location * SECTOR
        length, compression = struct.unpack_from(">iB", self.data, start)
        if compression & 0x80:
            # chunks larger than 1MiB are stored in a file of their own
            payload = (self.path.parent / f"c.{cx}.{cz}.mcc").read_bytes()
        else:
            payload = self.data[start + 5 : start + 4 + length]
        return read_nbt(_decompress(payload, compression & 0x7F, self.path))


def _decompress(payload: bytes, compression: int, path: Path) -> bytes:
    match compression:
        case 1:
            return gzip.decompress(payload)
        case 2:
            return zlib.decompress(payload)
        case 3:
            return payload
        case _:
            # 4 is LZ4, chosen with region-file-compression=lz4 in
            # server.properties. Its Java stream format has no pure Python
            # reader, so ask for the default instead
            raise ValueError(
                f"{path} uses chunk compression type {compression}: set "
                "region-file-compression=deflate in server.properties"
            )


def region_folder(world_folder: Path, dimension: str = "overworld") -> Path:
    """
    Find the folder of a dimension's region files in a world folder

    :param world_folder: the world folder (containing level.dat)
    :param dimension: overworld, the_nether or the_end

    :raises ValueError: if there is no such folder
    """
    world_folder = Path(world_folder)
    try:
        candidates = _DIMENSION_FOLDERS[dimension]
    except KeyError:
        raise ValueError(
            f"unknown dimension {dimension}, use one of {', '.join(_DIMENSION_FOLDERS)}"
        ) from None
    for candidate in candidates:
        folder = world_folder / candidate / "region"
        if folder.is_dir():
            return folder
    raise ValueError(f"no {dimension} region files in {world_folder}")


def _unpack_indices(data: np.ndarray | None, palette_size: int) -> np.ndarray:
    """
    Unpack the palette indices of a chunk section's 4096 blocks, ordered
    y, z, x. Each 64 bit long holds as many whole indices as fit, lowest bits
    first, and the indices use at least 4 bits.
    """
    if data is None or palette_size == 1:
        return np.zeros(SECTION_BLOCKS, dtype=np.int64)
    bits = max(4, (palette_size - 1).bit_length())
    per_long = 64 // bits
    longs = data.astype(">i8").view(">u8").astype(np.uint64)
    shifts = np.arange(per_long, dtype=np.uint64) * np.uint64(bits)
    values = (longs[:, np.newaxis] >> shifts) & np.uint64((1 << bits) - 1)
    values = values.ravel()
    if values.size < SECTION_BLOCKS:
        raise ValueError(f"chunk section has {values.size} blocks, not 4096")
    return values[:SECTION_BLOCKS].astype(np.int64)


def _palette_name(entry: Any) -> str:
    """
    The block name of a block state palette entry: a compound with a Name
    (and Properties), or a block state string such as
    ``minecraft:oak_stairs[facing=east]``
    """
    if isinstance(entry, dict) and "Name" in entry:
        return block_name(entry["Name"])
    if isinstance(entry, str):
        return block_name(entry)
    raise ValueError(f"unexpected block palette entry {entry!r}")


def read_world_blocks(
    world_folder: Path, vol: Volume, dimension: str = "overworld"
) -> BlockGrid:
    """
    Read a region of a world from its region files.

    Chunks that have not been generated read as air. Block states (e.g. which
    way stairs face) are not read, just the block names.

    :param world_folder: the world folder (containing level.dat)
    :param vol: the region to read
    :param dimension: overworld, the_nether or the_end

    :raises ValueError: if the world folder has no region files, or they are
        in a format that this reader does not support
    """
    begin = monotonic()
    folder = region_folder(world_folder, dimension)
    lx, ly, lz = vol.start.i_tuple
    hx, hy, hz = vol.end.i_tuple

    index = {AIR: 0}
    # 2 bytes per block: there are far fewer than 65536 kinds of block
    ids = np.zeros(vol.size.i_tuple, dtype=np.uint16)
    regions: dict[tuple[int, int], RegionFile] = {}
    missing = 0

    for cx in range(lx >> 4, (hx >> 4) + 1):
        for cz in range(lz >> 4, (hz >> 4) + 1):
            key = (cx >> 5, cz >> 5)
            if key not in regions:
                regions[key] = RegionFile(folder / f"r.{key[0]}.{key[1]}.mca")
            chunk = regions[key].chunk(cx, cz)
            if chunk is None:
                missing += 1
                continue
            if "sections" not in chunk:
                raise ValueError(
                    f"chunk {cx}, {cz} in {folder} is from before Minecraft "
                    "1.18: open the world with a newer server to upgrade it"
                )
            # the part of the region that this chunk covers, in world coords
            x0, x1 = max(lx, cx * 16), min(hx, cx * 16 + 15)
            z0, z1 = max(lz, cz * 16), min(hz, cz * 16 + 15)
            for section in chunk["sections"]:
                states = section.get("block_states")
                sy = section["Y"]
                y0, y1 = max(ly, sy * 16), min(hy, sy * 16 + 15)
                if states is None or y0 > y1:
                    continue
                palette = [
                    index.setdefault(_palette_name(entry), len(index))
                    for entry in states["palette"]
                ]
                local = _unpack_indices(states.get("data"), len(palette))
                # [y][z][x] -> [x][y][z]
                blocks = np.asarray(palette)[local].reshape(16, 16, 16)
                blocks = blocks.transpose(2, 0, 1)
                ids[
                    x0 - lx : x1 - lx + 1,
                    y0 - ly : y1 - ly + 1,
                    z0 - lz : z1 - lz + 1,
                ] = blocks[
                    x0 - cx * 16 : x1 - cx * 16 + 1,
                    y0 - sy * 16 : y1 - sy * 16 + 1,
                    z0 - cz * 16 : z1 - cz * 16 + 1,
                ]

    if missing:
        log.warning(f"{missing} chunks in {vol.start} to {vol.end} not generated")
    elapsed = monotonic() - begin
    log.debug(f"read {vol.size.volume} blocks from {folder} in {elapsed:.2f}s")
    return BlockGrid(vol.start, ids, list(index))
