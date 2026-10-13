import gzip
from pathlib import Path

import numpy as np
import pytest

from mciwb.builders import DATA_VERSION, BlockState, Schematic
from mciwb.builders.nbtfile import (
    Byte,
    ByteArray,
    Double,
    Float,
    Int,
    IntArray,
    Long,
    LongArray,
    Short,
    TagList,
    load_nbt,
    read_nbt,
    save_nbt,
    write_nbt,
)
from mciwb.builders.schematic import _read_varints, _write_varints
from mciwb.imports import Item, Vec3, Volume
from tests.mockclient import MockClient

STAIRS = "minecraft:oak_stairs[facing=north,half=bottom,shape=straight]"


# NBT #########################################################################


def test_nbt_round_trip(tmp_path: Path):
    value = {
        "byte": Byte(-3),
        "short": Short(300),
        "int": Int(70000),
        "plain int": 5,
        "long": Long(2**40),
        "float": Float(0.5),
        "double": Double(0.25),
        "plain float": 1.5,
        "bytes": ByteArray(b"\x00\xff"),
        "ints": IntArray([1, -2, 3]),
        "longs": LongArray([2**40, -1]),
        "string": "café \U0001f600 nul\x00",
        "list": TagList([Short(1), Short(2)]),
        "empty list": TagList([], 10),
        "compound": {"nested": TagList([{"a": "b"}])},
    }
    data = write_nbt(value, "root")
    assert data[:2] == b"\x1f\x8b"  # gzip
    name, result = read_nbt(data)
    assert name == "root"
    assert result == value
    # the tag types are kept
    assert isinstance(result["short"], Short)
    assert isinstance(result["plain int"], Int)
    assert isinstance(result["plain float"], Double)
    assert result["empty list"].tag_type == 10
    # write it again, byte for byte the same
    assert write_nbt(result, "root") == data

    file = tmp_path / "test.nbt"
    save_nbt(file, value)
    assert load_nbt(file) == ("", value)


def test_nbt_format():
    # the example in https://minecraft.wiki/w/NBT_format: a compound named
    # "hello world" holding a string "name" = "Bananrama"
    expected = b"\x0a\x00\x0bhello world\x08\x00\x04name\x00\x09Bananrama\x00"
    assert write_nbt({"name": "Bananrama"}, "hello world", compress=False) == (expected)
    assert read_nbt(expected) == ("hello world", {"name": "Bananrama"})
    # Java's modified UTF-8 encodes NUL as two bytes
    assert write_nbt({"": "\x00"}, compress=False)[-4:-1] == b"\x02\xc0\x80"


def test_nbt_errors():
    with pytest.raises(ValueError, match="compound"):
        read_nbt(b"\x08\x00\x00")
    with pytest.raises(ValueError, match="end"):
        read_nbt(b"\x0a\x00\x00\x08")
    with pytest.raises(TypeError):
        write_nbt({"bad": object()})


def test_varints():
    values = [0, 1, 127, 128, 300, 2**21]
    data = _write_varints(values)
    assert data[:5] == b"\x00\x01\x7f\x80\x01"
    assert _read_varints(data, len(values)) == values
    with pytest.raises(ValueError):
        _read_varints(data, 3)


# Schematic ###################################################################


def make_schematic() -> Schematic:
    """2 wide (x), 3 high (y), 4 long (z), a different block at each corner"""
    blocks = np.full((2, 3, 4), BlockState("minecraft:air"), dtype=object)
    blocks[0, 0, 0] = BlockState.parse("stone")
    blocks[1, 0, 0] = BlockState.parse(STAIRS)
    blocks[0, 0, 3] = BlockState.parse("oak_log[axis=x]")
    blocks[0, 2, 0] = BlockState.parse("glass")
    return Schematic(blocks)


def test_schematic_save_load(tmp_path: Path):
    schematic = make_schematic()
    schematic.metadata = {"Name": "test"}
    schematic.block_entities = [{"Pos": IntArray([0, 0, 0]), "Id": "minecraft:sign"}]
    file = tmp_path / "test.schem"
    schematic.save(file)

    _, root = load_nbt(file)
    data = root["Schematic"]
    assert data["Version"] == 3
    assert data["DataVersion"] == DATA_VERSION
    assert (data["Width"], data["Height"], data["Length"]) == (2, 3, 4)
    assert data["Metadata"] == {"Name": "test"}
    palette = data["Blocks"]["Palette"]
    assert len(palette) == 5
    # index = x + z * width + y * width * length
    indices = _read_varints(data["Blocks"]["Data"], 24)
    assert indices[0] == palette["minecraft:stone"]
    assert indices[1] == palette[STAIRS]
    assert indices[0 + 3 * 2] == palette["minecraft:oak_log[axis=x]"]
    assert indices[2 * 2 * 4] == palette["minecraft:glass"]

    loaded = Schematic.load(file)
    assert (loaded.blocks == schematic.blocks).all()
    assert loaded.size == Vec3(2, 3, 4)
    assert loaded.metadata == {"Name": "test"}
    assert loaded.block_entities == schematic.block_entities
    assert repr(loaded) == "<Schematic 2x3x4, 5 block states>"


def test_schematic_load_version_2(tmp_path: Path):
    file = tmp_path / "v2.schem"
    # a version 2 file is not nested, and keeps its blocks in BlockData
    v2 = {
        "Version": Int(2),
        "DataVersion": Int(3465),
        "Width": Short(2),
        "Height": Short(1),
        "Length": Short(1),
        "Palette": {"minecraft:stone": Int(1), "minecraft:dirt": Int(0)},
        "BlockData": ByteArray(b"\x01\x00"),
    }
    save_nbt(file, v2, "Schematic")
    loaded = Schematic.load(file)
    assert loaded.data_version == 3465
    assert loaded.blocks[0, 0, 0] == BlockState("minecraft:stone")
    assert loaded.blocks[1, 0, 0] == BlockState("minecraft:dirt")

    save_nbt(file, {"Version": Int(1)}, "Schematic")
    with pytest.raises(ValueError, match="version"):
        Schematic.load(file)


def test_schematic_large_dimensions(tmp_path: Path):
    # sizes above 32767 are stored as negative (signed) shorts
    blocks = np.full((40000, 1, 1), BlockState("minecraft:stone"), dtype=object)
    file = tmp_path / "long.schem"
    Schematic(blocks).save(file)
    _, root = read_nbt(gzip.decompress(file.read_bytes()))
    assert root["Schematic"]["Width"] == 40000 - 65536
    assert Schematic.load(file).size == Vec3(40000, 1, 1)
    with pytest.raises(ValueError):
        Schematic(np.empty((0, 1, 1), dtype=object))


def test_schematic_cuboid():
    cuboid = [[[Item.STONE, Item.AIR]], [[Item.DIRT, Item.GLASS]]]
    schematic = Schematic.from_cuboid(cuboid)
    assert schematic.size == Vec3(2, 1, 2)
    assert schematic.blocks[1, 0, 1] == BlockState("minecraft:glass")
    assert schematic.to_cuboid() == cuboid
    with pytest.raises(ValueError):
        Schematic.from_cuboid([Item.STONE])


def test_schematic_rotate():
    schematic = make_schematic()
    turned = schematic.rotate(1)
    # clockwise from above: the 2 (x) by 4 (z) footprint becomes 4 by 2,
    # and the north west corner goes to the north east
    assert turned.size == Vec3(4, 3, 2)
    assert turned.blocks[3, 0, 0] == BlockState("minecraft:stone")
    # the stairs at the north east corner go to the south east, facing east
    assert str(turned.blocks[3, 0, 1]) == (
        "minecraft:oak_stairs[facing=east,half=bottom,shape=straight]"
    )
    # the log at the south west goes to the north west, along z
    assert str(turned.blocks[0, 0, 0]) == "minecraft:oak_log[axis=z]"
    assert (schematic.rotate(4).blocks == schematic.blocks).all()
    assert (turned.rotate(3).blocks == schematic.blocks).all()


def test_schematic_mirror():
    schematic = make_schematic()
    schematic.block_entities = [{"Pos": IntArray([1, 0, 0]), "Id": "minecraft:sign"}]
    flipped = schematic.mirror("x")
    assert flipped.blocks[1, 0, 0] == BlockState("minecraft:stone")
    assert flipped.blocks[0, 0, 0] == BlockState.parse(STAIRS)
    assert list(flipped.block_entities[0]["Pos"]) == [0, 0, 0]
    flipped = schematic.mirror("z")
    assert flipped.blocks[0, 0, 3] == BlockState("minecraft:stone")
    assert str(flipped.blocks[1, 0, 3]) == (
        "minecraft:oak_stairs[facing=south,half=bottom,shape=straight]"
    )
    assert list(flipped.block_entities[0]["Pos"]) == [1, 0, 3]
    with pytest.raises(ValueError):
        schematic.mirror("y")


def test_schematic_world(mock_client: MockClient):
    mock_client.setblock(Vec3(0, 0, 0), STAIRS.replace("north", "west"))
    mock_client.setblock(Vec3(1, 0, 0), "minecraft:oak_slab[type=top]")
    mock_client.setblock(Vec3(0, 1, 0), "minecraft:oak_log[axis=z]")
    mock_client.setblock(Vec3(1, 1, 0), Item.STONE)

    schematic = Schematic.from_world(Volume.from_corners(Vec3(0, 0, 0), Vec3(1, 1, 0)))
    assert [str(b) for b in schematic.blocks.ravel()] == [
        "minecraft:oak_stairs[facing=west,half=bottom,shape=straight]",
        "minecraft:oak_log[axis=z]",
        "minecraft:oak_slab[type=top]",
        "minecraft:stone",
    ]
    plain = Schematic.from_world(
        Volume.from_corners(Vec3(0, 0, 0), Vec3(1, 1, 0)), states=False
    )
    assert str(plain.blocks[0, 0, 0]) == "minecraft:oak_stairs"

    mock_client.block_commands.clear()
    volume = schematic.paste(Vec3(10, 0, 0))
    assert (volume.start, volume.end) == (Vec3(10, 0, 0), Vec3(11, 1, 0))
    assert mock_client.state_at(Vec3(11, 0, 0)) == "minecraft:oak_slab[type=top]"
    assert mock_client.state_at(Vec3(10, 1, 0)) == "minecraft:oak_log[axis=z]"
    assert len(mock_client.block_commands) == 4

    # air is skipped, unless asked for
    mock_client.setblock(Vec3(20, 0, 0), Item.DIRT)
    mock_client.block_commands.clear()
    holes = Schematic.from_cuboid([[[Item.AIR]], [[Item.STONE]]])
    holes.paste(Vec3(20, 0, 0))
    assert mock_client.block_commands == ["setblock 21 0 0 minecraft:stone"]
    assert mock_client.getblock(Vec3(20, 0, 0)) == Item.DIRT
    holes.paste(Vec3(20, 0, 0), air=True)
    assert mock_client.getblock(Vec3(20, 0, 0)) == Item.AIR


def test_schematic_paste_merges_fills(mock_client: MockClient):
    cube = np.full((3, 2, 3), BlockState("minecraft:stone"), dtype=object)
    cube[1, 1, 1] = BlockState("minecraft:glass")
    Schematic(cube).paste(Vec3(0, 0, 0))
    assert mock_client.block_commands[0] == "fill 0 0 0 2 0 2 minecraft:stone"
    # one fill for the bottom layer, a ring of 4 fills around the glass
    assert len(mock_client.block_commands) == 1 + 4 + 1
