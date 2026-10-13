"""
Write minimal Minecraft worlds for testing mciwb.anvil: just enough NBT and
region file structure for the reader, in the same formats as the game.

NBT types are chosen from the Python types: dict is a compound, list a list,
str a string, int an int, float a double, numpy scalars int8/int16/int64/
float32 a byte/short/long/float, numpy int8/int32/int64 arrays a byte/int/
long array.
"""

import gzip
import struct
import zlib
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from mciwb.anvil import SECTOR

AIR = "minecraft:air"


_SCALARS = {np.int8: 1, np.int16: 2, np.int64: 4, np.float32: 5}
_ARRAYS = {np.dtype(np.int8): 7, np.dtype(np.int32): 11, np.dtype(np.int64): 12}
_PYTHON = {bool: 3, int: 3, float: 6, str: 8, list: 9, dict: 10}


def _tag(value: Any) -> int:
    if isinstance(value, np.ndarray):
        return _ARRAYS[value.dtype]
    for kind, tag in (*_SCALARS.items(), *_PYTHON.items()):
        if isinstance(value, kind):
            return tag
    raise TypeError(f"no NBT type for {value!r}")


def _payload(value: Any) -> bytes:
    tag = _tag(value)
    match tag:
        case 1 | 2 | 3 | 4 | 5 | 6:
            fmt = {1: ">b", 2: ">h", 3: ">i", 4: ">q", 5: ">f", 6: ">d"}[tag]
            return struct.pack(fmt, value)
        case 7 | 11 | 12:
            big = value.astype(value.dtype.newbyteorder(">"))
            return struct.pack(">i", len(value)) + big.tobytes()
        case 8:
            raw = value.encode()
            return struct.pack(">H", len(raw)) + raw
        case 9:
            item_tag = _tag(value[0]) if value else 0
            items = b"".join(_payload(v) for v in value)
            return struct.pack(">bi", item_tag, len(value)) + items
        case _:
            return (
                b"".join(
                    struct.pack(">b", _tag(v)) + _payload(k) + _payload(v)
                    for k, v in value.items()
                )
                + b"\0"
            )


def write_nbt(value: dict) -> bytes:
    """encode a dict as an uncompressed NBT document with an empty root name"""
    return b"\x0a" + _payload("") + _payload(value)


def pack_indices(indices: np.ndarray, palette_size: int) -> np.ndarray:
    """pack 4096 palette indices into longs, as the game does"""
    bits = max(4, (palette_size - 1).bit_length())
    per_long = 64 // bits
    longs = []
    flat = [int(i) for i in indices.ravel()]
    for start in range(0, len(flat), per_long):
        value = 0
        for n, index in enumerate(flat[start : start + per_long]):
            value |= index << (n * bits)
        longs.append(value)
    return np.array(longs, dtype=np.uint64).view(np.int64)


def palette_entry(state: str) -> dict:
    """
    The palette compound of a block state string such as
    ``minecraft:oak_stairs[facing=east,half=top]``, as Minecraft 26.3 writes it
    """
    name, _, props = state.partition("[")
    if not props:
        return {"id": name}
    pairs = (prop.split("=") for prop in props.rstrip("]").split(","))
    return {"id": name, "properties": dict(pairs)}


def section(sy: int, blocks: dict[tuple[int, int, int], str]) -> dict:
    """
    A chunk section with blocks keyed by (x, y, z) within the section. Blocks
    are block state strings, with or without properties. Like Minecraft 26.3,
    the palette is a list of strings when every block has its default state
    (written here as no properties), otherwise a list of compounds
    """
    palette = [AIR] + sorted(set(blocks.values()) - {AIR})
    indices = np.zeros((16, 16, 16), dtype=np.int64)  # [y][z][x]
    for (x, y, z), name in blocks.items():
        indices[y, z, x] = palette.index(name)
    if any("[" in state for state in palette):
        entries: list = [palette_entry(state) for state in palette]
    else:
        entries = palette
    states: dict[str, Any] = {"palette": entries}
    if len(palette) > 1:
        states["data"] = pack_indices(indices, len(palette))
    return {
        "Y": np.int8(sy),
        "block_states": states,
        "biomes": {"palette": ["minecraft:plains"]},
    }


def chunk_nbt(cx: int, cz: int, blocks: dict[tuple[int, int, int], str]) -> dict:
    """a chunk with blocks keyed by world (x, y, z), plus an empty section"""
    sections: dict[int, dict] = defaultdict(dict)
    for (x, y, z), name in blocks.items():
        sections[y >> 4][(x & 15, y & 15, z & 15)] = name
    empty = min(sections, default=0) - 1
    sections.setdefault(empty, {})
    return {
        "DataVersion": 4000,
        "xPos": cx,
        "zPos": cz,
        "yPos": -4,
        "Status": "minecraft:full",
        "LastUpdate": np.int64(1),
        "sections": [section(sy, b) for sy, b in sorted(sections.items())],
        "Heightmaps": {"WORLD_SURFACE": np.zeros(37, dtype=np.int64)},
        "block_entities": [],
    }


def _compress(data: bytes, compression: int) -> bytes:
    match compression:
        case 1:
            return gzip.compress(data)
        case 2:
            return zlib.compress(data)
        case _:
            return data


def write_region(
    path: Path, chunks: dict[tuple[int, int], dict], compression: int = 2
) -> None:
    """
    Write chunks keyed by chunk (x, z) to a region file. Compression 1 is
    gzip, 2 zlib, 3 none, 4 lz4 (not really compressed, for errors only),
    and adding 128 stores the chunk in an external .mcc file
    """
    header = bytearray(2 * SECTOR)
    body = bytearray()
    for (cx, cz), nbt in chunks.items():
        data = _compress(write_nbt(nbt), compression & 0x7F)
        if compression & 0x80:
            (path.parent / f"c.{cx}.{cz}.mcc").write_bytes(data)
            data = b""
        record = struct.pack(">iB", len(data) + 1, compression) + data
        record += bytes(-len(record) % SECTOR)
        sector = 2 + len(body) // SECTOR
        entry = 4 * ((cx & 31) + (cz & 31) * 32)
        header[entry : entry + 4] = struct.pack(
            ">I", sector << 8 | len(record) // SECTOR
        )
        body += record
    path.write_bytes(bytes(header) + bytes(body))


def write_world(
    world: Path,
    blocks: dict[tuple[int, int, int], str],
    region_folder: str = "dimensions/minecraft/overworld/region",
    compression: int = 2,
) -> Path:
    """
    Write a world folder containing blocks keyed by world (x, y, z). Only
    the chunks that contain blocks are generated

    :returns: the world folder
    """
    folder = world / region_folder
    folder.mkdir(parents=True, exist_ok=True)
    (world / "level.dat").write_bytes(gzip.compress(write_nbt({"Data": {}})))
    chunks: dict[tuple[int, int], dict] = defaultdict(dict)
    for (x, y, z), name in blocks.items():
        chunks[(x >> 4, z >> 4)][(x, y, z)] = name
    regions: dict[tuple[int, int], dict] = defaultdict(dict)
    for (cx, cz), chunk_blocks in chunks.items():
        regions[(cx >> 5, cz >> 5)][(cx, cz)] = chunk_nbt(cx, cz, chunk_blocks)
    for (rx, rz), region_chunks in regions.items():
        write_region(folder / f"r.{rx}.{rz}.mca", region_chunks, compression)
    return world
