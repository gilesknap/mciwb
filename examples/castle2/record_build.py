"""
Record what a castle build would do, without a server: run a castle
directory's ``build_castle.py`` (or castle2's ``build_castle2.py``) against a
fake RCON client that answers every command plausibly, and write

- ``OUT.commands``: every command the build sent, in order;
- ``OUT.blocks``: the final block of every cell it set inside the site box
  (simulating setblock and fill, with fill's modes and filters), sorted.

Two builds of the same castle can then be compared with ``diff``: the
refactor of phase 0 must leave castle's blocks exactly as they were::

    python record_build.py ../castle /tmp/before            # castle
    python record_build.py . /tmp/c2 build_castle2          # castle2

The ground is a gentle deterministic slope (``ground``); nothing is read
from a real world, so this checks the build's logic, not the terrain.
The environment (ORIGIN, BAILEY_DEPTH ...) is passed through.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import numpy as np
from mcipc.rcon.enumerations import FillMode


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
            return "Summoned new entity"
        if m := re.match(r"execute positioned (\S+) 0 (\S+) positioned over", command):
            x, z = int(float(m.group(1))), int(float(m.group(2)))
            if " run tp " in command:
                return f"Teleported Marker to {x}.5, {ground(x, z) + 1}.0, {z}.5"
            return "Test failed"
        if m := re.match(r"setblock (\S+) (\S+) (\S+) (.*)", command):
            self.world.setblock(_ints([m.group(1), m.group(2), m.group(3)]), m.group(4))
            return "Changed the block"
        if command.startswith("execute if entity"):
            return "Test passed, count: 1000"
        if command.startswith("execute if block"):
            # air is everywhere the build asks; nothing else is
            return "Test passed" if command.endswith("minecraft:air") else "Test failed"
        if command == "list":
            return "There are 0 of a max of 20 players online: "
        if command.startswith("kill"):
            return "No entity was found"
        return ""

    def connect(self, retry=True) -> None:
        pass


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    folder, out = Path(sys.argv[1]).resolve(), sys.argv[2]
    script = sys.argv[3] if len(sys.argv) > 3 else "build_castle"
    sys.path.insert(0, str(folder))
    sys.path.insert(1, str(Path(__file__).parent.parent / "castle"))
    import castle_layout

    from mciwb.threads import set_client

    a, b = castle_layout.site_box()
    world = World(_ints(a), _ints(b))
    rec = Recorder(world)
    set_client(rec)  # type: ignore[arg-type]
    time.sleep = lambda _s: None
    os.environ.setdefault("FORCE", "1")
    module = __import__(script)
    module.main()
    Path(f"{out}.commands").write_text("\n".join(rec.commands) + "\n")
    Path(f"{out}.blocks").write_text("\n".join(world.dump()) + "\n")
    print(f"{len(rec.commands)} commands, site {a}..{b}")


if __name__ == "__main__":
    main()
