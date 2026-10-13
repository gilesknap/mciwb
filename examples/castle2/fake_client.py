"""
A fake RCON client for castle builds, which answers every command
plausibly without a server (`Recorder`), and the simulated blocks of a box
(`World`). The builds and checks use it at run time to learn what their
stages do: `summon_counts` (what a stage summons: castle2_layout.SUMMONED)
and `dry_run` (e.g. which seats a build places). record_build.py uses it to
record and render a whole build offline.

The ground is a gentle deterministic slope (`ground`).
"""

from __future__ import annotations

import re

import numpy as np
from mcipc.rcon.enumerations import FillMode
from mcwb import Vec3


def ground(x: int, z: int) -> int:
    """the fake world's top ground block at (x, z)"""
    return 62 + (x * 7 + z * 3) // 50 % 6


def _ints(v) -> tuple[int, int, int]:
    return int(v[0]), int(v[1]), int(v[2])


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
            air = (view == "") | (view == "minecraft:air")
            view[air] = block
        elif mode in (FillMode.HOLLOW, FillMode.OUTLINE):
            # (the outline of the whole box, clipped to the world)
            inner = np.zeros(view.shape, bool)
            if all(s > 2 for s in view.shape):
                inner[1:-1, 1:-1, 1:-1] = True
            if mode == FillMode.HOLLOW:
                view[inner] = "minecraft:air"
            view[~inner] = block
        elif filter:
            view[self._matches(view, filter)] = block
        else:
            view[...] = block

    @staticmethod
    def _matches(view, filter: str):
        names = np.vectorize(lambda s: s.partition("[")[0] or "minecraft:air")(view)
        if filter.startswith("#"):
            tag = filter.split(":", 1)[1]
            words = {"sand": "sand", "logs": "_log"}.get(tag, tag)
            return np.vectorize(lambda n: words in n)(names)
        return names == filter.partition("[")[0]

    def grid(self, lo=None, hi=None):
        """the blocks (without their states) as a BlockGrid, to render"""
        from mciwb.blockgrid import BlockGrid

        box = self._box(lo, hi) if lo is not None else (slice(None),) * 3
        assert box is not None
        names = np.vectorize(lambda s: s.partition("[")[0].partition("{")[0])(
            self.blocks[box]
        )
        names[names == ""] = "minecraft:air"
        origin = [int(b.start or 0) + int(o) for b, o in zip(box, self.lo, strict=True)]
        return BlockGrid.from_blocks(names, Vec3(*origin))

    def at(self, pos) -> str:
        """the block placed at pos ("" if none, or outside the box)"""
        box = self._box(pos, pos)
        return "" if box is None else self.blocks[box][0, 0, 0]

    def dump(self) -> list[str]:
        out = []
        for idx in zip(*np.nonzero(self.blocks != ""), strict=True):
            x, y, z = (int(i + o) for i, o in zip(idx, self.lo, strict=True))
            out.append(f"{x} {y} {z} {self.blocks[idx]}")
        return sorted(out)


class Recorder:
    """a fake RCON client: records every command, answers it plausibly"""

    def __init__(self, world: World):
        self.world = world
        self.commands: list[str] = []
        self.host, self.port, self.passwd = "fake", 0, ""
        # the entities summoned and not killed since: (type, tags)
        self.entities: list[tuple[str, set[str]]] = []

    def setblock(self, pos, block, mode=None) -> str:
        x, y, z = _ints(pos)
        self.commands.append(f"setblock {x} {y} {z} {block}")
        self.world.setblock((x, y, z), str(block))
        return f"Changed the block at {x}, {y}, {z}"

    def fill(self, a, b, block, mode=None, filter=None) -> str:
        a, b = _ints(a), _ints(b)
        extra = f" {FillMode(mode).value}" if mode is not None else ""
        extra += f" {filter}" if filter else ""
        self.commands.append(f"fill {' '.join(map(str, a + b))} {block}{extra}")
        self.world.fill(a, b, str(block), mode, filter)
        return "Successfully filled 1 block(s)"

    def run(self, command: str, *args: str) -> str:
        command = " ".join((command, *args))
        # the ground readings' marker tags are random
        self.commands.append(re.sub(r"mciwb_[0-9a-f]{8}", "mciwb_TAG", command))
        if command.startswith("summon"):
            kinds = [command.split()[1].split(":")[-1]]
            kinds += re.findall(r'Passengers:\[\{id:"minecraft:(\w+)"', command)
            tags = set(
                re.findall(
                    r'"([^"]+)"',
                    (re.search(r"Tags:\[([^\]]*)\]", command) or ["", " "])[1],
                )
            )
            for kind in kinds:
                self.entities.append((kind, tags))
            return "Summoned new entity"
        if m := re.match(r"execute positioned (\S+) 0 (\S+) positioned over", command):
            x, z = int(float(m.group(1))), int(float(m.group(2)))
            if " run tp " in command:
                return f"Teleported Marker to {x}.0, {ground(x, z) + 1}.0, {z}.0"
            return "Test failed"
        if m := re.match(r"setblock (\S+) (\S+) (\S+) (.*)", command):
            self.world.setblock(_ints([m.group(1), m.group(2), m.group(3)]), m.group(4))
            return "Changed the block"
        if command.startswith("execute if entity"):
            n = len(self._selected(command))
            return f"Test passed. Count: {n}" if n else "Test failed"
        if command.startswith("execute if block"):
            # air is everywhere the build asks; nothing else is
            return "Test passed" if command.endswith("minecraft:air") else "Test failed"
        if command == "list":
            return "There are 0 of a max of 20 players online: "
        if command.startswith("kill"):
            gone = self._selected(command)
            self.entities = [e for e in self.entities if e not in gone]
            return f"Killed {len(gone)} entities" if gone else "No entity was found"
        return ""

    def _selected(self, command: str) -> list[tuple[str, set[str]]]:
        """the summoned entities an @e[...] selector picks, by its type= and
        tag= (a box or other filter is taken to include them all)"""
        sel = re.search(r"@e\[([^\]]*)\]", command)
        if not sel:
            return []
        want_type = re.search(r"type=minecraft:(\w+)", sel.group(1))
        tags = re.findall(r"tag=([^,\]]+)", sel.group(1))
        out = []
        for e in self.entities:
            kind, etags = e
            if want_type and kind != want_type.group(1):
                continue
            if any(t.startswith("!") and t[1:] in etags for t in tags):
                continue
            if any(not t.startswith("!") and t not in etags for t in tags):
                continue
            out.append(e)
        return out

    def connect(self, retry=True) -> None:
        pass


def dry_run(*funcs, box: tuple | None = None) -> Recorder:
    """
    Run build functions against a fake client, without touching the world,
    and give back the recorder (its ``commands``). Used by the checks to
    learn what a build places, e.g. ``castle_lib.SEATS``. The thread's real
    client is put back afterwards. Give a ``box`` (two corners) to simulate
    the blocks placed in it (``recorder.world.blocks``).
    """
    from mciwb.threads import get_client, set_client

    try:
        real = get_client()
    except AttributeError:
        real = None
    lo, hi = box if box is not None else ((0, 0, 0), (0, 0, 0))
    rec = Recorder(World(_ints(lo), _ints(hi)))
    set_client(rec)  # type: ignore[arg-type]
    try:
        for func in funcs:
            func()
    finally:
        if real is not None:
            set_client(real)
    return rec


def summon_counts(*funcs) -> dict[str, int]:
    """what build functions summon, by entity type (riders included),
    learnt by running them against a fake client"""
    counts: dict[str, int] = {}
    for command in dry_run(*funcs).commands:
        if command.startswith("summon minecraft:"):
            kinds = [command.split()[1].split(":")[1]]
            kinds += re.findall(r'Passengers:\[\{id:"minecraft:(\w+)"', command)
            for kind in kinds:
                counts[kind] = counts.get(kind, 0) + 1
    return counts
