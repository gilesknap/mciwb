"""
A fake RCON client for station builds, which answers every command
plausibly without a server (`Recorder`), and the simulated blocks of a box
(`World`). build_station.py runs the whole build against it
(``offline_build``), so the unit test and the offline checks need no
server, and two builds can be compared by their commands and blocks.

What it simulates: ``setblock`` and ``fill`` (with fill's modes and a block
filter, which may be one of the block tags in ``TAGS``), ``execute if
block``, ``forceload`` (add, remove and query, with the server's limit of
256 chunks a command), ``list``, and a game clock that only ``tick sprint``
moves (``time query gametime``, ``tick query``). A block command outside the forceloaded
chunks is refused as the server refuses it, so a stage that builds outside
the loaded site fails offline too.

Of the datapack it simulates only the loading: given the world's
``datapacks`` folder, ``reload`` runs the functions of each pack's load tag
(not recorded as commands), and ``data modify storage ... set value`` and
``data get storage`` keep and give back a value, which is how the
datapack's install sees that its pack loaded. Nothing ticks, and
``function`` is only recorded.

A cell nothing has set reads as air: there is no sea and no sea bed here,
so this checks the build's logic, not the terrain.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from mcipc.rcon.enumerations import FillMode

AIR = "minecraft:air"
NOT_LOADED = "That position is not loaded"
FORCELOAD_LIMIT = 256  # chunks a forceload command, the server's limit
#: the block tags a fill's filter may name, as far as the fake world can
#: hold them: it has no plants and no lava
TAGS = {"#minecraft:replaceable": {AIR, "minecraft:water"}}


def _ints(v) -> tuple[int, int, int]:
    return int(v[0]), int(v[1]), int(v[2])


def _name(block: str) -> str:
    """a block without its states and NBT, with its namespace"""
    name = block.partition("[")[0].partition("{")[0]
    return name if ":" in name else f"minecraft:{name}"


class World:
    """the blocks inside a box, as names with states; outside it, nothing"""

    def __init__(self, lo: tuple[int, int, int], hi: tuple[int, int, int]):
        self.lo = np.array(lo)
        self.shape = tuple(int(h - lo_ + 1) for lo_, h in zip(lo, hi, strict=True))
        self.blocks = np.full(self.shape, "", dtype=object)  # "" = untouched

    def _box(self, a, b):
        a, b = np.array(_ints(a)), np.array(_ints(b))
        lo = np.minimum(a, b) - self.lo
        hi = np.maximum(a, b) - self.lo + 1
        lo = np.maximum(lo, 0)
        hi = np.minimum(hi, self.shape)
        if (hi <= lo).any():
            return None
        return tuple(slice(int(s), int(e)) for s, e in zip(lo, hi, strict=True))

    def setblock(self, pos, block: str) -> None:
        box = self._box(pos, pos)
        if box is not None:
            self.blocks[box] = block

    def fill(self, a, b, block: str, mode=None, filter=None) -> None:
        box = self._box(a, b)
        if box is None:
            return
        view = self.blocks[box]
        mode = FillMode(mode) if mode is not None else FillMode.REPLACE
        if mode == FillMode.KEEP:
            view[(view == "") | (view == AIR)] = block
        elif mode in (FillMode.HOLLOW, FillMode.OUTLINE):
            # (the outline of the whole box, clipped to the world)
            inner = np.zeros(view.shape, bool)
            if all(s > 2 for s in view.shape):
                inner[1:-1, 1:-1, 1:-1] = True
            if mode == FillMode.HOLLOW:
                view[inner] = AIR
            view[~inner] = block
        elif filter:
            if filter.startswith("#") and filter not in TAGS:
                raise ValueError(f"the fake world does not know the tag {filter}")
            wanted = TAGS.get(filter, {_name(filter)})
            names = np.vectorize(lambda s: _name(s) if s else AIR, otypes=[object])(
                view
            )
            view[np.isin(names, list(wanted))] = block
        else:
            view[...] = block

    def at(self, pos) -> str:
        """the block placed at pos ("" if none, or outside the box)"""
        box = self._box(pos, pos)
        return "" if box is None else self.blocks[box][0, 0, 0]

    def name_at(self, pos) -> str:
        """the block at pos without its states; air where nothing was set"""
        block = self.at(pos)
        return _name(block) if block else AIR

    def grid(self, lo=None, hi=None):
        """the blocks (without their states) as a BlockGrid, to render"""
        from mcwb import Vec3

        from mciwb.blockgrid import BlockGrid

        box = self._box(lo, hi) if lo is not None else (slice(None),) * 3
        assert box is not None
        names = np.vectorize(lambda s: _name(s) if s else AIR)(self.blocks[box])
        origin = [int(b.start or 0) + int(o) for b, o in zip(box, self.lo, strict=True)]
        return BlockGrid.from_blocks(names, Vec3(*origin))

    def dump(self) -> list[str]:
        """every cell that was set, as sorted "x y z block" lines"""
        out = []
        for idx in zip(*np.nonzero(self.blocks != ""), strict=True):
            x, y, z = (int(i + o) for i, o in zip(idx, self.lo, strict=True))
            out.append(f"{x} {y} {z} {self.blocks[idx]}")
        return sorted(out)


class Recorder:
    """
    A fake RCON client: records every command and answers it plausibly.

    ``players`` are the names ``list`` reports. ``forceloaded`` is the set
    of (chunk x, chunk z) that ``forceload`` has marked; with
    ``everything_loaded`` block commands work anywhere (for trying one
    build function by itself). ``datapacks_dir`` is the fake world's
    datapacks folder, read on ``reload``.
    """

    def __init__(
        self,
        world: World,
        players: tuple[str, ...] = (),
        everything_loaded: bool = False,
        datapacks_dir: Path | str | None = None,
    ):
        self.world = world
        self.players = list(players)
        self.everything_loaded = everything_loaded
        self.commands: list[str] = []
        self.replies: list[str] = []  # the reply to each of ``commands``
        self.forceloaded: set[tuple[int, int]] = set()
        self.datapacks_dir = Path(datapacks_dir) if datapacks_dir else None
        self.storage: dict[tuple[str, str], str] = {}  # (storage, path) -> SNBT
        self.gametime = 0  # moved only by ``tick sprint``
        self.host, self.port, self.passwd = "fake", 0, ""

    def connect(self, retry=True) -> None:
        pass

    def loaded(self, a, b=None) -> bool:
        """are all the chunks of a box (or of a position) loaded?"""
        if self.everything_loaded:
            return True
        a = _ints(a)
        b = _ints(b) if b is not None else a
        cx1, cx2 = sorted((a[0] // 16, b[0] // 16))
        cz1, cz2 = sorted((a[2] // 16, b[2] // 16))
        return all(
            (cx, cz) in self.forceloaded
            for cx in range(cx1, cx2 + 1)
            for cz in range(cz1, cz2 + 1)
        )

    # the two commands that mcwb and mciwb's Placer send by method
    def setblock(self, pos, block, mode=None) -> str:
        x, y, z = _ints(pos)
        self.commands.append(f"setblock {x} {y} {z} {block}")
        self.replies.append(self._setblock((x, y, z), str(block)))
        return self.replies[-1]

    def fill(self, a, b, block, mode=None, filter=None) -> str:
        a, b = _ints(a), _ints(b)
        extra = f" {FillMode(mode).value}" if mode is not None else ""
        extra += f" {filter}" if filter else ""
        self.commands.append(f"fill {' '.join(map(str, a + b))} {block}{extra}")
        self.replies.append(self._fill(a, b, str(block), mode, filter))
        return self.replies[-1]

    def _setblock(self, pos, block: str) -> str:
        if not self.loaded(pos):
            return NOT_LOADED
        self.world.setblock(pos, block)
        return f"Changed the block at {pos[0]}, {pos[1]}, {pos[2]}"

    def _fill(self, a, b, block: str, mode=None, filter=None) -> str:
        if not self.loaded(a, b):
            return NOT_LOADED
        self.world.fill(a, b, block, mode, filter)
        return "Successfully filled 1 block(s)"

    def run(self, command: str, *args: str) -> str:
        command = " ".join((command, *args))
        self.commands.append(command)
        self.replies.append(self._answer(command))
        return self.replies[-1]

    def _answer(self, command: str) -> str:
        word = command.split(" ", 1)[0]
        if word == "list":
            names = ", ".join(self.players)
            return (
                f"There are {len(self.players)} of a max of 20 players online: {names}"
            )
        if word == "forceload":
            return self._forceload(command.split()[1:])
        if m := re.match(r"setblock (\S+) (\S+) (\S+) (.+)", command):
            return self._setblock(_ints(m.groups()[:3]), m.group(4))
        if m := re.match(
            r"fill((?: -?\d+){6}) (\S+)"
            r"(?: (destroy|hollow|keep|outline|replace)(?: (\S+))?)?$",
            command,
        ):
            c = [int(v) for v in m.group(1).split()]
            return self._fill(c[:3], c[3:], m.group(2), m.group(3), m.group(4))
        if m := re.match(r"execute if block (\S+) (\S+) (\S+) (\S+)$", command):
            pos = _ints(m.groups()[:3])
            if not self.loaded(pos):
                return NOT_LOADED
            same = self.world.name_at(pos) == _name(m.group(4))
            return "Test passed" if same else "Test failed"
        if m := re.match(r"data modify storage (\S+) (\S+) set value (.+)", command):
            self.storage[m.group(1), m.group(2)] = m.group(3)
            return f"Modified storage {m.group(1)}"
        if m := re.match(r"data get storage (\S+) (\S+)$", command):
            if m.groups() not in self.storage:
                return f"Found no elements matching {m.group(2)}"
            value = self.storage[m.group(1), m.group(2)]
            return f"Storage {m.group(1)} has the following contents: {value}"
        if word == "reload":
            self._load_packs()
            return "Reloading!"
        if m := re.match(r"tick sprint (\d+)$", command):
            self.gametime += int(m.group(1))
            return f"Sprinting {m.group(1)} ticks"
        if command == "tick query":
            return "The game is running normally"
        if command == "time query gametime":
            return f"The game time is {self.gametime} tick(s)"
        if word == "gamerule":
            return (
                f"Game rule {command.split()[1]} is now set to: {command.split()[-1]}"
            )
        return ""

    def _load_packs(self) -> None:
        """run the functions of every pack's load tag, as a reload does"""
        if self.datapacks_dir is None:
            return
        for tag in sorted(
            self.datapacks_dir.glob("*/data/minecraft/tags/function/load.json")
        ):
            pack = tag.parents[4]
            for name in json.loads(tag.read_text())["values"]:
                namespace, _, path = name.partition(":")
                file = pack / "data" / namespace / "function" / f"{path}.mcfunction"
                for line in file.read_text().splitlines():
                    if line and not line.startswith("#"):
                        self._answer(line)

    def _forceload(self, args: list[str]) -> str:
        """``forceload add|remove x1 z1 [x2 z2]`` and ``forceload remove all``"""
        if args == ["query"]:
            chunks = ", ".join(f"[{x}, {z}]" for x, z in sorted(self.forceloaded))
            n = len(self.forceloaded)
            if n == 0:
                return "No force loaded chunks were found in minecraft:overworld"
            if n == 1:
                return f"A force loaded chunk was found in minecraft:overworld at: {chunks}"
            return f"{n} force loaded chunks were found in minecraft:overworld at: {chunks}"
        if args[:2] == ["remove", "all"]:
            self.forceloaded.clear()
            return "Unmarked all force loaded chunks in minecraft:overworld"
        if args[0] not in ("add", "remove") or len(args) not in (3, 5):
            return ""
        x1, z1 = int(args[1]), int(args[2])
        x2, z2 = (int(args[3]), int(args[4])) if len(args) == 5 else (x1, z1)
        chunks = {
            (cx, cz)
            for cx in range(min(x1, x2) // 16, max(x1, x2) // 16 + 1)
            for cz in range(min(z1, z2) // 16, max(z1, z2) // 16 + 1)
        }
        if len(chunks) > FORCELOAD_LIMIT:
            return (
                "Too many chunks in the specified area "
                f"(maximum {FORCELOAD_LIMIT}, specified {len(chunks)})"
            )
        if args[0] == "add":
            self.forceloaded |= chunks
            return (
                f"Marked {len(chunks)} chunks in minecraft:overworld to be force loaded"
            )
        self.forceloaded -= chunks
        return f"Unmarked {len(chunks)} chunks in minecraft:overworld for force loading"
