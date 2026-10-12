import logging
from pathlib import Path

import numpy as np
import pytest

from mciwb.anvil import RegionFile, read_nbt, read_world_blocks, region_folder
from mciwb.imports import Vec3, Volume
from tests.anvil_writer import chunk_nbt, write_nbt, write_region, write_world

# blocks either side of chunk and region boundaries, at negative coordinates
BLOCKS = {
    (-1, -61, -1): "minecraft:gold_block",
    (0, -61, 0): "minecraft:stone",
    (511, 70, 3): "minecraft:red_wool",
    (512, 70, 3): "minecraft:blue_wool",
    (-513, 319, -2): "minecraft:glass",
    (3, -64, 600): "minecraft:bedrock",
}


def read(world: Path, start, end, **kwargs):
    return read_world_blocks(world, Volume.from_corners(start, end), **kwargs)


def test_read_nbt_types():
    doc = {
        "byte": np.int8(-3),
        "short": np.int16(300),
        "int": 70000,
        "long": np.int64(-(2**40)),
        "float": np.float32(1.5),
        "double": 2.25,
        "bytes": np.array([1, -2], dtype=np.int8),
        "ints": np.array([1, -2], dtype=np.int32),
        "longs": np.array([2**62, -1], dtype=np.int64),
        "string": "minecraft:stone",
        "list": [{"a": 1}, {"b": "x"}],
        "empty": [],
        "nested": {"inner": {"deep": [1, 2, 3]}},
    }
    result = read_nbt(write_nbt(doc))

    assert result["byte"] == -3
    assert result["short"] == 300
    assert result["int"] == 70000
    assert result["long"] == -(2**40)
    assert result["float"] == 1.5
    assert result["double"] == 2.25
    assert list(result["bytes"]) == [1, -2]
    assert list(result["ints"]) == [1, -2]
    assert list(result["longs"]) == [2**62, -1]
    assert result["string"] == "minecraft:stone"
    assert result["list"] == [{"a": 1}, {"b": "x"}]
    assert result["empty"] == []
    assert result["nested"] == {"inner": {"deep": [1, 2, 3]}}


def test_read_nbt_errors():
    with pytest.raises(ValueError, match="must be a compound"):
        read_nbt(b"\x08\x00\x00")
    with pytest.raises(ValueError, match="unknown NBT tag 13"):
        read_nbt(b"\x0a\x00\x00\x0d\x00\x01a")


@pytest.mark.parametrize("layout", ["dimensions/minecraft/overworld/region", "region"])
def test_read_blocks(tmp_path: Path, layout: str):
    world = write_world(tmp_path / "world", BLOCKS, layout)

    for pos, name in BLOCKS.items():
        grid = read(world, Vec3(*pos), Vec3(*pos))
        assert grid[Vec3(*pos)] == name

    grid = read(world, Vec3(-2, -62, -2), Vec3(1, -60, 1))
    assert grid.size == Vec3(4, 3, 4)
    assert grid.origin == Vec3(-2, -62, -2)
    assert grid.counts() == {"minecraft:gold_block": 1, "minecraft:stone": 1}
    assert grid[Vec3(-1, -61, -1)] == "minecraft:gold_block"
    assert grid[Vec3(0, -61, 0)] == "minecraft:stone"
    assert grid[Vec3(0, -61, -1)] == "minecraft:air"

    # across a region boundary
    grid = read(world, Vec3(510, 70, 3), Vec3(513, 70, 3))
    assert [grid[Vec3(x, 70, 3)] for x in range(510, 514)] == [
        "minecraft:air",
        "minecraft:red_wool",
        "minecraft:blue_wool",
        "minecraft:air",
    ]


def test_read_many_block_types(tmp_path: Path):
    """palettes of more than 16 blocks need more than 4 bits per block"""
    names = [f"minecraft:{c}_wool" for c in range(40)]
    blocks = {(i % 16, i // 16, 5): name for i, name in enumerate(names)}
    blocks[(15, 15, 15)] = "minecraft:stone"
    world = write_world(tmp_path / "world", blocks)

    grid = read(world, Vec3(0, 0, 0), Vec3(15, 15, 15))
    for (x, y, z), name in blocks.items():
        assert grid[Vec3(x, y, z)] == name
    assert sum(grid.counts().values()) == len(blocks)


@pytest.mark.parametrize("compression", [1, 2, 3, 2 + 128])
def test_compression(tmp_path: Path, compression: int):
    world = write_world(tmp_path / "world", BLOCKS, compression=compression)
    grid = read(world, Vec3(0, -61, 0), Vec3(0, -61, 0))
    assert grid[Vec3(0, -61, 0)] == "minecraft:stone"


def test_lz4_unsupported(tmp_path: Path):
    world = write_world(tmp_path / "world", BLOCKS, compression=4)
    with pytest.raises(ValueError, match="region-file-compression=deflate"):
        read(world, Vec3(0, -61, 0), Vec3(0, -61, 0))


def test_missing_chunks(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    world = write_world(tmp_path / "world", BLOCKS)
    caplog.set_level(logging.WARNING)

    # chunk 1, 0 is not generated, and region 5, 5 does not exist
    grid = read(world, Vec3(16, 0, 0), Vec3(17, 0, 0))
    assert grid.counts(include_air=True) == {"minecraft:air": 2}
    grid = read(world, Vec3(2600, 0, 2600), Vec3(2600, 0, 2600))
    assert grid.counts(include_air=True) == {"minecraft:air": 1}
    assert "1 chunks" in caplog.text


def test_old_chunk_format(tmp_path: Path):
    folder = tmp_path / "world" / "region"
    folder.mkdir(parents=True)
    write_region(folder / "r.0.0.mca", {(0, 0): {"Level": {"Sections": []}}})
    with pytest.raises(ValueError, match="before Minecraft 1.18"):
        read(tmp_path / "world", Vec3(0, 0, 0), Vec3(1, 1, 1))


def test_region_folder(tmp_path: Path):
    world = tmp_path / "world"
    with pytest.raises(ValueError, match="no overworld region files"):
        region_folder(world)
    with pytest.raises(ValueError, match="unknown dimension"):
        region_folder(world, "moon")

    (world / "DIM-1" / "region").mkdir(parents=True)
    assert region_folder(world, "the_nether") == world / "DIM-1" / "region"
    new = world / "dimensions" / "minecraft" / "the_nether" / "region"
    new.mkdir(parents=True)
    assert region_folder(world, "the_nether") == new


def test_nether(tmp_path: Path):
    world = write_world(
        tmp_path / "world",
        {(1, 2, 3): "minecraft:netherrack"},
        "dimensions/minecraft/the_nether/region",
    )
    grid = read(world, Vec3(1, 2, 3), Vec3(1, 2, 3), dimension="the_nether")
    assert grid[Vec3(1, 2, 3)] == "minecraft:netherrack"


@pytest.mark.parametrize(
    "entry",
    [
        # Minecraft 26.3 and later
        {"id": "minecraft:oak_stairs", "properties": {"facing": "east"}},
        {"id": "minecraft:oak_stairs"},
        {"": "minecraft:oak_stairs"},
        "minecraft:oak_stairs",
        "minecraft:oak_stairs[facing=east]",
        "oak_stairs",
        # before 26.3
        {"Name": "minecraft:oak_stairs", "Properties": {"facing": "east"}},
        {"Name": "minecraft:oak_stairs"},
    ],
)
def test_palette_entries(tmp_path: Path, entry):
    """palette entries may be compounds in each format, or block state strings"""
    nbt = chunk_nbt(0, 0, {(1, 1, 1): "minecraft:stone"})
    air = "minecraft:air" if isinstance(entry, str) else {"id": "minecraft:air"}
    nbt["sections"][-1]["block_states"]["palette"] = [air, entry]
    folder = tmp_path / "world" / "region"
    folder.mkdir(parents=True)
    write_region(folder / "r.0.0.mca", {(0, 0): nbt})

    grid = read(tmp_path / "world", Vec3(1, 1, 1), Vec3(1, 1, 1))
    assert grid[Vec3(1, 1, 1)] == "minecraft:oak_stairs"


def test_block_states(tmp_path: Path):
    """a section with blocks in non default states has a compound palette"""
    blocks = {
        (1, 1, 1): "minecraft:oak_stairs[facing=east]",
        (2, 1, 1): "minecraft:oak_log[axis=x]",
        (3, 1, 1): "minecraft:stone",
        (1, 2, 1): "minecraft:oak_door[facing=south,half=upper]",
    }
    world = write_world(tmp_path / "world", blocks)
    nbt = RegionFile(region_folder(world) / "r.0.0.mca").chunk(0, 0)
    assert nbt is not None
    palette = nbt["sections"][-1]["block_states"]["palette"]
    assert {"id": "minecraft:oak_stairs", "properties": {"facing": "east"}} in palette
    assert {"id": "minecraft:stone"} in palette

    grid = read(world, Vec3(1, 1, 1), Vec3(3, 2, 1))
    assert grid[Vec3(1, 1, 1)] == "minecraft:oak_stairs"
    assert grid[Vec3(2, 1, 1)] == "minecraft:oak_log"
    assert grid[Vec3(3, 1, 1)] == "minecraft:stone"
    assert grid[Vec3(1, 2, 1)] == "minecraft:oak_door"


@pytest.mark.parametrize(
    "entry, match",
    [(7, "7"), ({"properties": {"facing": "east"}}, "{'properties'")],
)
def test_bad_palette_entry(tmp_path: Path, entry, match: str):
    nbt = chunk_nbt(0, 0, {(1, 1, 1): "minecraft:stone"})
    nbt["sections"][-1]["block_states"]["palette"] = [entry, entry]
    folder = tmp_path / "world" / "region"
    folder.mkdir(parents=True)
    write_region(folder / "r.0.0.mca", {(0, 0): nbt})

    with pytest.raises(ValueError, match=f"unexpected block palette entry {match}"):
        read(tmp_path / "world", Vec3(1, 1, 1), Vec3(1, 1, 1))


def test_chunk_without_block_states(tmp_path: Path):
    """sections with only biomes (e.g. above the world) read as air"""
    nbt = chunk_nbt(0, 0, {(1, 1, 1): "minecraft:stone"})
    nbt["sections"].append({"Y": np.int8(5), "biomes": {"palette": []}})
    folder = tmp_path / "world" / "region"
    folder.mkdir(parents=True)
    write_region(folder / "r.0.0.mca", {(0, 0): nbt})

    grid = read(tmp_path / "world", Vec3(0, 0, 0), Vec3(2, 90, 2))
    assert grid.counts() == {"minecraft:stone": 1}
