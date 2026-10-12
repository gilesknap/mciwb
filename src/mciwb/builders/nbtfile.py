"""
Read and write binary NBT, the format of Minecraft's data files (and of
schematics). See https://minecraft.wiki/w/NBT_format

Tags map to Python types as follows. Reading always gives the typed wrappers,
so that a file that is read and written again keeps its tag types.

=============  ===============================================
NBT tag        Python
=============  ===============================================
Byte           `Byte` (an int)
Short          `Short` (an int)
Int            `Int`, or a plain int when writing
Long           `Long` (an int)
Float          `Float` (a float)
Double         `Double`, or a plain float when writing
Byte Array     `ByteArray`, or bytes when writing
String         str
List           `TagList` (a list), or a plain list when writing
Compound       dict
Int Array      `IntArray` (a list of int)
Long Array     `LongArray` (a list of int)
=============  ===============================================
"""

from __future__ import annotations

import gzip
import struct
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

__all__ = [
    "Byte",
    "ByteArray",
    "Double",
    "Float",
    "Int",
    "IntArray",
    "Long",
    "LongArray",
    "Short",
    "TagList",
    "load_nbt",
    "read_nbt",
    "save_nbt",
    "write_nbt",
]


class Byte(int):
    """An NBT Byte"""


class Short(int):
    """An NBT Short"""


class Int(int):
    """An NBT Int"""


class Long(int):
    """An NBT Long"""


class Float(float):
    """An NBT Float"""


class Double(float):
    """An NBT Double"""


class ByteArray(bytes):
    """An NBT Byte Array"""


class IntArray(list):
    """An NBT Int Array"""


class LongArray(list):
    """An NBT Long Array"""


class TagList(list):
    """
    An NBT List. *tag_type* is the type id of the items, kept so that an
    empty list is written back with the type it was read with
    """

    def __init__(self, items=(), tag_type: int | None = None):
        super().__init__(items)
        self.tag_type = tag_type


_END, _COMPOUND, _LIST = 0, 10, 9
_SCALARS: dict[int, tuple[type, str]] = {
    1: (Byte, ">b"),
    2: (Short, ">h"),
    3: (Int, ">i"),
    4: (Long, ">q"),
    5: (Float, ">f"),
    6: (Double, ">d"),
}
_ARRAYS: dict[int, tuple[type, str, int]] = {
    7: (ByteArray, ">b", 1),
    11: (IntArray, ">i", 4),
    12: (LongArray, ">q", 8),
}
_STRING = 8


def _tag_type(value: Any) -> int:
    for tag, (cls, _) in _SCALARS.items():
        if isinstance(value, cls):
            return tag
    for tag, (cls, _, _) in _ARRAYS.items():
        if isinstance(value, cls):
            return tag
    if isinstance(value, bool | int):
        return 3  # Int
    if isinstance(value, float):
        return 6  # Double
    if isinstance(value, bytes):
        return 7
    if isinstance(value, str):
        return _STRING
    if isinstance(value, list):
        return _LIST
    if isinstance(value, dict):
        return _COMPOUND
    raise TypeError(f"cannot write {type(value).__name__} as NBT")


def _encode_string(text: str) -> bytes:
    """Java's modified UTF-8: NUL is two bytes, and astral characters are
    encoded as a pair of surrogates"""
    data = bytearray()
    for char in text:
        code = ord(char)
        if code == 0:
            data += b"\xc0\x80"
        elif code > 0xFFFF:
            pair = char.encode("utf-16-be")
            for i in (0, 2):
                surrogate = int.from_bytes(pair[i : i + 2], "big")
                data += chr(surrogate).encode("utf-8", "surrogatepass")
        else:
            data += char.encode("utf-8", "surrogatepass")
    return bytes(data)


def _decode_string(data: bytes) -> str:
    text = data.replace(b"\xc0\x80", b"\x00").decode("utf-8", "surrogatepass")
    # join surrogate pairs into single characters
    return text.encode("utf-16-be", "surrogatepass").decode("utf-16-be")


class _Reader:
    def __init__(self, stream: BinaryIO):
        self.stream = stream

    def read(self, size: int) -> bytes:
        data = self.stream.read(size)
        if len(data) != size:
            raise ValueError("unexpected end of NBT data")
        return data

    def unpack(self, fmt: str) -> Any:
        return struct.unpack(fmt, self.read(struct.calcsize(fmt)))[0]

    def string(self) -> str:
        return _decode_string(self.read(self.unpack(">H")))

    def payload(self, tag: int) -> Any:
        if tag in _SCALARS:
            cls, fmt = _SCALARS[tag]
            return cls(self.unpack(fmt))
        if tag in _ARRAYS:
            cls, fmt, size = _ARRAYS[tag]
            count = self.unpack(">i")
            if cls is ByteArray:
                return ByteArray(self.read(count))
            return cls(struct.unpack(f">{count}{fmt[1]}", self.read(count * size)))
        if tag == _STRING:
            return self.string()
        if tag == _LIST:
            item_tag = self.unpack(">b")
            count = self.unpack(">i")
            return TagList((self.payload(item_tag) for _ in range(count)), item_tag)
        if tag == _COMPOUND:
            result = {}
            while (child := self.unpack(">b")) != _END:
                name = self.string()
                result[name] = self.payload(child)
            return result
        raise ValueError(f"unknown NBT tag type {tag}")


class _Writer:
    def __init__(self, stream: BinaryIO):
        self.stream = stream

    def pack(self, fmt: str, value: Any) -> None:
        self.stream.write(struct.pack(fmt, value))

    def string(self, text: str) -> None:
        data = _encode_string(text)
        self.pack(">H", len(data))
        self.stream.write(data)

    def payload(self, tag: int, value: Any) -> None:
        if tag in _SCALARS:
            self.pack(_SCALARS[tag][1], value)
        elif tag in _ARRAYS:
            fmt = _ARRAYS[tag][1]
            self.pack(">i", len(value))
            if tag == 7:
                self.stream.write(bytes(value))
            else:
                self.stream.write(struct.pack(f">{len(value)}{fmt[1]}", *value))
        elif tag == _STRING:
            self.string(value)
        elif tag == _LIST:
            item_tag = getattr(value, "tag_type", None)
            if value:
                item_tag = _tag_type(value[0])
            elif item_tag is None:
                item_tag = _END
            self.pack(">b", item_tag)
            self.pack(">i", len(value))
            for item in value:
                self.payload(item_tag, item)
        elif tag == _COMPOUND:
            for name, child in value.items():
                child_tag = _tag_type(child)
                self.pack(">b", child_tag)
                self.string(name)
                self.payload(child_tag, child)
            self.pack(">b", _END)


def read_nbt(data: bytes) -> tuple[str, dict]:
    """
    Read NBT data (gzip compressed or not) holding a root compound tag.

    :returns: (name, value): the name of the root tag, and its value
    """
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    reader = _Reader(BytesIO(data))
    if reader.unpack(">b") != _COMPOUND:
        raise ValueError("NBT data must start with a compound tag")
    name = reader.string()
    return name, reader.payload(_COMPOUND)


def write_nbt(value: dict, name: str = "", compress: bool = True) -> bytes:
    """
    Write a root compound tag as NBT data, gzip compressed by default.
    """
    stream = BytesIO()
    writer = _Writer(stream)
    writer.pack(">b", _COMPOUND)
    writer.string(name)
    writer.payload(_COMPOUND, value)
    data = stream.getvalue()
    return gzip.compress(data, mtime=0) if compress else data


def load_nbt(filename: Path | str) -> tuple[str, dict]:
    """Read an NBT file, see `read_nbt`"""
    return read_nbt(Path(filename).read_bytes())


def save_nbt(filename: Path | str, value: dict, name: str = "") -> None:
    """Write a gzip compressed NBT file, see `write_nbt`"""
    Path(filename).write_bytes(write_nbt(value, name))
