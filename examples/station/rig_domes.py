"""
The rig's second round: the mechanics the six later domes' designs rest
on, each worked on the live server (Minecraft Java 26.3) with nobody
online, in the air over the rig's ocean, far from the station::

    STATION_DATAPACKS_DIR=/path/to/world/datapacks mciwb run rig_domes.py

WHICH=2,3 runs some of the experiments (numbered as in the designs'
review; 1 is the hand bench, below). Each builds what it needs on its own
plot, works it over RCON and through the rig's own pack (``station_rig2``),
and judges by what it reads back. At the end every plot is cleared, the
rig's entities, scores, team and pack are removed and its chunks released.

2.  the Flooded Dome's basin: a body of sources with fittings in it,
    stepped down a layer at a time and drawn back from every level
3.  the Clockwork Maze's gate: a two-leaf sticky piston door worked by a
    block of redstone, 1000 strokes, short pulses, rewrites in mid stroke
4.  the Engine's pair: a ravager with a vindicator on it, and with a husk
5.  daylight under glass with a block of water over it
6.  the Signal Room's contact, the button beside a bulb, ``random``
7.  fights: ``difficulty`` read into a score, a zombie's way over grate,
    stairs and ladders, ``damage`` in a function
8.  block displays turned and posed
9.  the Maze's lift: a platform stepped up under a shutter
10. the Gearworks' small things
11. machinery: the tapped torch clock, comparators out of copper bulbs

**The hand bench** (``BENCH=build``, ``BENCH=remove``) is not an
experiment: it is a small deck joined to the station's dock, with a bay
for each thing only a player in adventure mode can try, and it stays. Its
functions are a pack of their own (``station_bench``), so the station's
pack and its reset know nothing of it. See ``bench_*`` below.
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import datapack as dp  # noqa: E402

NS = "station_rig2"
OBJ = "rig2"
STORE = f"{NS}:rig"
TAG = "rig2"  # on every entity the rig summons
TEAM = "rig2"
AIR = "minecraft:air"
WATER = "minecraft:water"
SOURCE = "minecraft:water[level=0]"
STONE = "minecraft:smooth_stone"
GLASS = "minecraft:glass"
REDSTONE = "minecraft:redstone_block"
BULB = "minecraft:waxed_copper_bulb"

Cell = tuple[int, int, int]
Box = tuple[Cell, Cell]


def add(name: str) -> str:
    return f"run scoreboard players add {name} {OBJ} 1"


def at(c: Cell) -> str:
    return f"{c[0]} {c[1]} {c[2]}"


def middle(c: Cell, dy: float = 0.0) -> str:
    """the middle of a cell's floor (not ``f"{x}.5"``: wrong when negative)"""
    return f"{c[0] + 0.5} {c[1] + dy} {c[2] + 0.5}"


def setblock(c: Cell, block: str) -> str:
    return f"setblock {at(c)} {block}"


def cells(a: Cell, b: Cell) -> list[Cell]:
    return [
        (x, y, z)
        for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1)
        for z in range(min(a[2], b[2]), max(a[2], b[2]) + 1)
        for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1)
    ]


class Bench:
    """the server, the rig's pack, the checks' results, and what to clear"""

    def __init__(self, world, datapacks_dir: Path) -> None:
        self.world = world
        self.dir = datapacks_dir
        self.results: list[tuple[str, bool]] = []
        x, y, z = (int(v) for v in os.environ.get("RIG", "2440,42,1544").split(","))
        # the chunks the rig works in (those of the first round), and the
        # level its plots stand at, well over the sea
        self.load_box = (x - 88, z - 24, x + 39, z + 103)
        self.o: Cell = (x - 84, 100, z - 20)
        self.plots: list[Box] = []
        self.pack = dp.Pack(NS, NS, "The Drowned Station: rig, second round")
        self.pack.objectives({OBJ: "dummy"})
        self.ticking: list[str] = []
        self.tick_lines: list[str] = []

    # -- talking to the server ---------------------------------------------

    def cmd(self, command: str, expect: str | None = None) -> str:
        if expect is None:
            return self.world.cmd(command)
        return self.world.cmd(command, f"(?s).*(?:{expect}).*")

    def check(self, name: str, ok: object, detail: object = "") -> bool:
        self.results.append((name, bool(ok)))
        tail = f"  [{detail}]" if detail != "" else ""
        print(("PASS " if ok else "FAIL ") + name + tail, flush=True)
        return bool(ok)

    def note(self, text: str) -> None:
        print("     " + text, flush=True)

    def gametime(self) -> int:
        r = self.cmd("time query gametime", r"\d+ tick")
        m = re.search(r"(\d+) tick", r)
        return int(m.group(1)) if m else 0

    def tick(self, ticks: int, chunk: int = 150) -> None:
        """let the game run at least ``ticks`` ticks, sprinted"""
        end = self.gametime() + ticks
        left = ticks
        stop = time.time() + 60 + ticks / 20
        while left > 0:
            if time.time() > stop:
                raise RuntimeError(f"the game did not advance {ticks} ticks")
            self.cmd(f"tick sprint {min(left, chunk)}")
            deadline = time.time() + 30
            while time.time() < deadline:
                time.sleep(0.05)
                if "sprinting" not in self.cmd("tick query", "game is"):
                    break
            left = end - self.gametime()

    def score(self, name: str) -> int | None:
        r = self.cmd(
            f"scoreboard players get {name} {OBJ}", r"has -?\d+|Can't get|Unknown"
        )
        m = re.search(r"has (-?\d+)", r)
        return int(m.group(1)) if m else None

    def set_score(self, name: str, value: int) -> None:
        self.cmd(f"scoreboard players set {name} {OBJ} {value}", "Set ")

    def is_block(self, c: Cell, block: str) -> bool:
        r = self.cmd(f"execute if block {at(c)} {block}", "Test ")
        return "Test passed" in r

    def what(self, c: Cell, names: list[str]) -> str:
        """which of ``names`` the block at a cell is"""
        for name in names:
            if self.is_block(c, name):
                return name.removeprefix("minecraft:")
        return "?"

    def count(self, selector: str) -> int:
        r = self.cmd(f"execute if entity {selector}", r"Test (passed|failed)")
        m = re.search(r"Count: (\d+)", r)
        return int(m.group(1)) if m else (1 if "passed" in r else 0)

    def data(self, selector: str, path: str) -> str:
        """an entity's data at a path, as the game prints it ('' if none)"""
        r = self.cmd(
            f"data get entity {selector} {path}",
            "entity data|No entity|Found no|Only one",
        )
        return r.split("entity data: ", 1)[1] if "entity data: " in r else ""

    def number(self, selector: str, path: str) -> float | None:
        m = re.match(r"(-?[\d.]+(?:E-?\d+)?)", self.data(selector, path))
        return float(m.group(1)) if m else None

    def pos(self, selector: str) -> tuple[float, float, float] | None:
        got = re.findall(r"(-?[\d.]+(?:E-?\d+)?)d", self.data(selector, "Pos"))
        return (float(got[0]), float(got[1]), float(got[2])) if len(got) == 3 else None

    def fill(self, a: Cell, b: Cell, block: str, how: str = "") -> str:
        """fill a box of any size, in slabs under the game's limit"""
        lo = (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]))
        hi = (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))
        per = (hi[0] - lo[0] + 1) * (hi[2] - lo[2] + 1)
        step = max(1, dp.MAX_FILL // per)
        r = ""
        for y in range(lo[1], hi[1] + 1, step):
            top = min(hi[1], y + step - 1)
            r = self.cmd(
                dp.fill((lo[0], y, lo[2]), (hi[0], top, hi[2]), block, how),
                "fill|Fill|No blocks|not loaded",
            )
        return r

    def put(self, blocks: dict[Cell, str]) -> None:
        for c, block in blocks.items():
            self.cmd(setblock(c, block), "Changed|Could not|not loaded")

    def plot(self, a: Cell, b: Cell) -> None:
        """claim a box: cleared to air now and at the end"""
        self.plots.append((a, b))
        self.fill(a, b, AIR)

    def function(self, path: str, lines: list[str], **how: bool) -> str:
        return self.pack.function(path, lines, **how)

    def every(self, flag: str, path: str) -> None:
        """run a function every tick while a score of the rig's is 1"""
        self.tick_lines.append(
            f"execute if score {flag} {OBJ} matches 1 run function {NS}:{path}"
        )
        self.ticking.append(flag)

    def run(self, path: str) -> str:
        return self.cmd(f"function {NS}:{path}")

    def summon(self, kind: str, c: Cell, nbt: str, tag: str, dy: float = 0.0) -> None:
        """summon an entity in the middle of a cell, tagged for the rig"""
        inner = nbt.strip()[1:-1]
        tags = f'Tags:["{TAG}","{tag}"]'
        self.cmd(
            f"summon {kind} {middle(c, dy)} {{{tags}{',' if inner else ''}{inner}}}"
        )

    # -- running and cleaning up ----------------------------------------------

    def forceload(self, on: bool) -> None:
        x1, z1, x2, z2 = self.load_box
        print(self.cmd(f"forceload {'add' if on else 'remove'} {x1} {z1} {x2} {z2}"))
        if on:
            deadline = time.time() + 60
            for x, z in ((x1, z1), (x2, z2), (x1, z2), (x2, z1)):
                while "not loaded" in self.cmd(f"execute if block {x} 0 {z} {AIR}"):
                    if time.time() > deadline:
                        raise RuntimeError(f"chunk at {x}, {z} did not load")
                    time.sleep(0.5)
            time.sleep(2)
            self.tick(20)

    def kill_all(self) -> None:
        # twice: a rider is left standing when its mount goes
        for _ in range(2):
            self.cmd(f"kill @e[tag={TAG}]")
            self.tick(2)
        x1, z1, x2, z2 = self.load_box
        box = f"x={x1},y=90,z={z1},dx={x2 - x1},dy={150},dz={z2 - z1}"
        self.cmd(f"kill @e[type=minecraft:item,{box}]")
        self.cmd(f"kill @e[type=minecraft:experience_orb,{box}]")

    def cleanup(self) -> None:
        if os.environ.get("KEEP"):  # to look at a failure by hand: run again to clear
            print("-- KEEP set: nothing cleaned up", flush=True)
            return
        print("-- cleaning up", flush=True)
        for path in self.pack.functions:
            self.cmd(f"schedule clear {NS}:{path}")
        for name in self.ticking:
            self.cmd(f"scoreboard players set {name} {OBJ} 0")
        self.kill_all()
        for a, b in self.plots:
            self.fill(a, b, AIR)
        self.tick(5)
        for a, b in self.plots:  # again: what a first pass let fall or flow
            self.fill(a, b, AIR)
        self.kill_all()
        left = self.count(f"@e[tag={TAG}]")
        self.check("no rig entity left", left == 0, left)
        self.cmd(f"team remove {TEAM}")
        self.cmd(f"data remove storage {STORE} v")
        dp.uninstall(self.world, self.pack, self.dir)
        self.forceload(False)
        packs = self.cmd("datapack list")
        self.check("the rig's pack is gone", NS not in packs, packs)
        print(f"datapacks folder: {sorted(p.name for p in self.dir.iterdir())}")


# == 2: the Flooded Dome's basin ============================================

BASIN = (35, 47, 12)  # inside: across x, across z, layers of water
STAIR = "minecraft:waxed_cut_copper_stairs[facing=east,waterlogged={}]"
LADDER = "minecraft:ladder[facing=east,waterlogged={}]"
BARS = "minecraft:iron_bars[waterlogged={}]"
BARS_SET = "minecraft:iron_bars[north=true,south=true,waterlogged={}]"
LEVER = "minecraft:lever[face=floor,facing=north]"


class Basin:
    """the basin's cells: i across x, j across z, k up (the floor is k 0,
    the water layers k 1 to 12, then two of air and a roof)"""

    def __init__(self, b: Bench) -> None:
        ox, oy, oz = b.o
        self.o = (ox + 1, oy, oz + 1)
        ni, nj, nk = BASIN
        self.layers = nk
        self.top = nk + 3  # the roof
        self.outer = (b.o, (ox + ni + 1, oy + self.top, oz + nj + 1))
        self.solid: dict[tuple[int, int, int], str] = {}
        self.fit: dict[tuple[int, int, int], str] = {}  # block with {} for the state
        for k in range(1, nk + 1):
            self.fit[(18 + k, 10, k)] = STAIR
            self.solid[(25, 30, k)] = "minecraft:polished_deepslate"
            self.fit[(26, 30, k)] = LADDER
            for j in range(25, 36):
                self.solid[(10, j, k)] = "minecraft:waxed_copper_block"
            self.solid[(30, 40, k)] = "minecraft:gold_block"
            if k <= 8:
                self.solid[(30, 20, k)] = "minecraft:gold_block"
        self.bars = [(10, j, k) for j in (29, 30) for k in (3, 4)]
        for c in self.bars:
            del self.solid[c]
            self.fit[c] = BARS
        for i in range(3, 13):
            for j in range(5, 15):
                self.solid[(i, j, 8)] = "minecraft:waxed_cut_copper"
        self.lever_a = (30, 40, nk + 1)  # always over the water
        self.lever_b = (30, 20, 9)  # on a pedestal whose top is layer 8
        self.lantern = (17, 23, 0)

    def cell(self, ijk: tuple[int, int, int]) -> Cell:
        return (self.o[0] + ijk[0], self.o[1] + ijk[2], self.o[2] + ijk[1])

    def layer(self, k: int) -> Box:
        ni, nj, _ = BASIN
        return (self.cell((0, 0, k)), self.cell((ni - 1, nj - 1, k)))

    def open_cells(self, k: int) -> list[tuple[int, int, int]]:
        ni, nj, _ = BASIN
        return [
            (i, j, k)
            for j in range(nj)
            for i in range(ni)
            if (i, j, k) not in self.solid
            and (i, j, k) not in self.fit
            and (i, j, k) not in (self.lever_a, self.lever_b)
        ]

    def fittings(self, k: int) -> list[tuple[tuple[int, int, int], str]]:
        return [(c, s) for c, s in sorted(self.fit.items()) if c[2] == k]


def x2_pack(b: Bench) -> Basin:
    bs = Basin(b)
    n = bs.layers
    lever_b = bs.cell(bs.lever_b)
    for k in range(1, n + 1):
        lo, hi = bs.layer(k)
        fits = bs.fittings(k)
        b.function(
            f"basin/dry_{k}",
            [setblock(bs.cell(c), s.format("false")) for c, s in fits]
            + [dp.fill(lo, hi, AIR, f"replace {WATER}")],
        )
        b.function(
            f"basin/wet_{k}",
            [
                dp.fill(lo, hi, WATER, f"replace {WATER}"),
                dp.fill(lo, hi, WATER, f"replace {AIR}"),
            ]
            + [setblock(bs.cell(c), s.format("true")) for c, s in fits],
        )
        for wet in (True, False):
            lines = []
            for c in bs.open_cells(k):
                p = at(bs.cell(c))
                if wet:
                    lines += [
                        f"execute unless block {p} {SOURCE} {add('#b_open')}",
                        f"execute if block {p} {WATER} unless block {p} {SOURCE} "
                        f"{add('#b_flow')}",
                    ]
                else:
                    lines += [
                        f"execute unless block {p} {AIR} {add('#b_open')}",
                        f"execute if block {p} {WATER} {add('#b_flow')}",
                    ]
            for c, s in fits:
                state = (BARS_SET if s == BARS else s).format(str(wet).lower())
                lines.append(
                    f"execute unless block {at(bs.cell(c))} {state} {add('#b_fit')}"
                )
            for c, block in sorted(bs.solid.items()):
                if c[2] == k:
                    lines.append(
                        f"execute unless block {at(bs.cell(c))} {block} "
                        f"{add('#b_solid')}"
                    )
            lines.append(f"scoreboard players add #b_ran {OBJ} 1")
            b.function(f"basin/chk_{'wet' if wet else 'dry'}_{k}", lines)
    # the two layers of air over the basin
    lines = []
    for k in (n + 1, n + 2):
        for c in bs.open_cells(k):
            lines.append(
                f"execute unless block {at(bs.cell(c))} {AIR} {add('#b_open')}"
            )
    lines.append(f"scoreboard players add #b_ran {OBJ} 1")
    b.function("basin/chk_over", lines)
    names = ("#b_open", "#b_flow", "#b_fit", "#b_solid", "#b_ran")
    for w in range(n + 1):
        b.function(
            f"basin/chk_{w}",
            [f"scoreboard players set {name} {OBJ} 0" for name in names]
            + [
                f"function {NS}:basin/chk_{'wet' if k <= w else 'dry'}_{k}"
                for k in range(1, n + 1)
            ]
            + [f"function {NS}:basin/chk_over"],
        )
        # the whole basin from nothing but the level: levers out first, the
        # layers, then the lever of a deck the water has left
        lines = [f"scoreboard players set #b_w {OBJ} {w}"]
        if w >= bs.lever_b[2]:
            lines.append(
                f"fill {at(lever_b)} {at(lever_b)} {AIR} replace minecraft:lever"
            )
        lines += [
            f"function {NS}:basin/{'wet' if k <= w else 'dry'}_{k}"
            for k in range(1, n + 1)
        ]
        if w < bs.lever_b[2]:
            lines.append(
                f"execute unless block {at(lever_b)} minecraft:lever "
                f"run {setblock(lever_b, LEVER)}"
            )
        b.function(f"basin/level_{w}", lines)
    return bs


def x2_run(b: Bench, bs: Basin) -> None:
    print("-- 2 the Flooded Dome's basin", flush=True)
    n = bs.layers
    a, z = bs.outer
    b.plot(a, z)
    ni, nj, _ = BASIN
    # a stone box (no daylight in it), the roof two clear layers over the water
    b.fill(a, z, STONE)
    b.fill(bs.cell((0, 0, 1)), bs.cell((ni - 1, nj - 1, bs.top - 1)), AIR)
    b.put({bs.cell(c): block for c, block in bs.solid.items()})
    b.put({bs.cell(c): s.format("false") for c, s in bs.fit.items()})
    b.put({bs.cell(bs.lantern): "minecraft:sea_lantern"})
    b.put({bs.cell(bs.lever_a): LEVER})
    box = (
        f"x={a[0]},y={a[1]},z={a[2]},dx={z[0] - a[0]},dy={z[1] - a[1]},dz={z[2] - a[2]}"
    )

    def items() -> int:
        return b.count(f"@e[type=minecraft:item,{box}]")

    def read(w: int) -> dict[str, int | None]:
        b.run(f"basin/chk_{w}")
        return {k: b.score(f"#b_{k}") for k in ("open", "flow", "fit", "solid", "ran")}

    def good(c: dict[str, int | None]) -> bool:
        return c == {"open": 0, "flow": 0, "fit": 0, "solid": 0, "ran": n + 1}

    def layers_wrong(w: int) -> str:
        """which layers a failed count lies in (for the log)"""
        out = []
        kinds = [AIR, SOURCE, WATER, STONE]
        for k in [*range(1, n + 1), 0]:
            name = f"chk_{'wet' if k <= w else 'dry'}_{k}" if k else "chk_over"
            for s_ in ("#b_open", "#b_flow", "#b_fit"):
                b.set_score(s_, 0)
            b.run(f"basin/{name}")
            got = [b.score(s_) for s_ in ("#b_open", "#b_flow", "#b_fit")]
            if any(got):
                kk = k or n + 1
                sample = [b.what(bs.cell((i, 20, kk)), kinds) for i in (0, 16, 34)]
                out.append(f"{name} {got} e.g. {sample}")
        return "; ".join(out)

    lever_a, lever_b = bs.cell(bs.lever_a), bs.cell(bs.lever_b)
    b.run(f"basin/level_{n}")
    b.tick(5)
    first = read(n)
    b.tick(200)
    c = read(n)
    cells_ = sum(len(bs.open_cells(k)) for k in range(1, n + 1))
    b.check(
        f"2a basin {ni} x {nj} x {n} drawn full: {cells_} open cells all sources, "
        f"{len(bs.fit)} fittings waterlogged, the same 200 ticks on",
        good(first) and good(c),
        f"{first} then {c}",
    )
    if not good(c):
        b.note(layers_wrong(n))
    if os.environ.get("STOP"):
        return

    # the designer's belief: a fitting set not waterlogged among sources stays dry
    probes = {
        "stair": ((18 + 5, 10, 5), STAIR),
        "ladder": ((26, 30, 5), LADDER),
        "bars": (bs.bars[0], BARS),
    }
    for c_, s in probes.values():
        b.cmd(setblock(bs.cell(c_), s.format("false")))
    b.tick(200)
    stays = {
        name: not b.is_block(
            bs.cell(c_), s.format("true").split("[")[0] + "[waterlogged=true]"
        )
        for name, (c_, s) in probes.items()
    }
    c = read(n)
    b.check(
        "2b a fitting set waterlogged=false among sources is waterlogged by the "
        "game within 200 ticks (so none may be left to the game: draw sets each)",
        not any(stays.values()),
        f"stayed not waterlogged: {stays}; the basin's count then: {c}",
    )
    b.run(f"basin/level_{n}")
    b.tick(5)

    # stepping down as the design's drain does: only the top layer written
    bad = []
    for k in range(n, 0, -1):
        b.run(f"basin/dry_{k}")
        w = k - 1
        if w == bs.lever_b[2] - 1:
            b.cmd(setblock(lever_b, LEVER))  # the deck's lever, once uncovered
        b.tick(2)
        soon = read(w)
        b.tick(200 if k > n - 4 else 40)
        late = read(w)
        line = f"water to layer {w}: at 2 ticks {soon}"
        if late != soon:
            line += f", later {late}"
        b.note(line)
        if not (good(soon) and good(late)):
            bad.append(w)
    b.check(
        f"2c stepped down {n} layers, the top one written each time (fittings "
        "dry, then fill air replace water): below all sources, above all air, "
        "nothing flowing, 200 ticks on for the first four and 40 for the rest",
        not bad,
        f"levels not as they should be: {bad}",
    )
    b.check(
        "2d the lever over the surface and the lever on the uncovered deck "
        "are still there, and no item lies in the basin",
        b.is_block(lever_a, "minecraft:lever")
        and b.is_block(lever_b, "minecraft:lever")
        and items() == 0,
        f"items {items()}",
    )

    # draw: any level from any other, then back to full
    bad = []
    order = [n, 0, 7, 3, n, 8, 11, 2, 9, 4, 10, 1, 6, 5, 0, n]
    for w in order:
        b.run(f"basin/level_{w}")
        b.tick(20)
        c = read(w)
        want_b = w < bs.lever_b[2]
        if not good(c) or b.is_block(lever_b, "minecraft:lever") != want_b:
            bad.append((w, c))
    b.tick(200)
    c = read(n)
    b.check(
        f"2e drawn whole from the level alone, {len(order)} jumps (every level "
        "visited), ending full: each right 20 ticks on, the last 200 ticks on",
        not bad and good(c),
        f"wrong: {bad}; at the end {c}",
    )
    b.check(
        "2f after all of it: the lever over the surface stands, no item "
        "(the deck's lever is taken out by draw before its layer is wet)",
        b.is_block(lever_a, "minecraft:lever") and items() == 0,
        f"items {items()}",
    )

    # what happens to a lever left in when its layer is written wet
    b.run("basin/level_8")
    b.tick(5)
    b.run("basin/wet_9")
    b.tick(40)
    washed = not b.is_block(lever_b, "minecraft:lever")
    b.note(
        f"a lever left standing while its layer is made wet: washed off {washed}, "
        f"items dropped {items()}"
    )
    b.cmd(f"kill @e[type=minecraft:item,{box}]")
    b.run(f"basin/level_{n}")
    b.tick(10)

    # the bars as a gate: opened (water) and shut (bars) under water, and dry
    lo, hi = bs.cell(bs.bars[0]), bs.cell(bs.bars[-1])
    res = []
    for w in (n, 0):
        b.run(f"basin/level_{w}")
        b.tick(10)
        wet = "true" if w else "false"
        b.cmd(dp.fill(lo, hi, WATER if w else AIR))
        b.tick(40)
        opened = all(b.is_block(bs.cell(c_), SOURCE if w else AIR) for c_ in bs.bars)
        b.run(f"basin/chk_{w}")
        flow = b.score("#b_flow")
        b.cmd(dp.fill(lo, hi, BARS.format(wet)))
        b.tick(40)
        c = read(w)
        res.append((w, opened, flow, c))
    b.check(
        "2g the 2 x 2 of bars opened by fill (water under water, air when dry) "
        "and shut again by fill iron_bars[waterlogged=...]: joined up, nothing flows",
        all(o and f == 0 and good(c) for _, o, f, c in res),
        res,
    )

    # light from one sea lantern in the floor, at head height, wet and dry
    li, lj, _ = bs.lantern
    reach = {}
    for w in (n, 0):
        b.run(f"basin/level_{w}")
        b.tick(10)
        far = -1
        for d in range(0, 12):
            p = at(bs.cell((li + d, lj, 2)))
            r = b.cmd(
                f"execute positioned {p} if predicate "
                '{type:"minecraft:location_check",predicate:{light:{light:{min:8}}}}',
                "Test ",
            )
            if "passed" not in r:
                break
            far = d
        reach["wet" if w else "dry"] = far
    b.check(
        "2h light of 8 or more at head height (2 over the floor) from a sea "
        "lantern in the floor, in a dark box: the same reach wet and dry",
        reach["wet"] == reach["dry"] and reach["wet"] >= 3,
        f"blocks sideways from over the lantern with light >= 8: {reach}",
    )
    b.run(f"basin/level_{n}")
    b.tick(5)


# == 3: the Clockwork Maze's gate ============================================

LEAF = "minecraft:waxed_chiseled_copper"
PISTON = "minecraft:sticky_piston"
STROKE = 80  # ticks from one shutting to the next
DIRS = {"east": (1, 0), "south": (0, 1), "west": (-1, 0), "north": (0, -1)}


class Gate:
    """one gate: along a wall line the doorway, the parked leaves, the
    pistons (facing the doorway), and the slot behind them or beside them"""

    def __init__(self, base: Cell, along: str, slot: str) -> None:
        dx, dz = DIRS[along]
        x, y, z = base
        self.facing = {v: k for k, v in DIRS.items()}[(-dx, -dz)]
        col = [(x + dx * n, z + dz * n) for n in range(4)]
        self.door = [(col[0][0], y + h, col[0][1]) for h in (0, 1)]
        self.leaf = [(col[1][0], y + h, col[1][1]) for h in (0, 1)]
        self.piston = [(col[2][0], y + h, col[2][1]) for h in (0, 1)]
        if slot == "behind":
            sx, sz = col[3]
        else:  # round the corner of the post: beside the pistons
            sx, sz = col[2][0] - dz, col[2][1] + dx
        self.slot = [(sx, y + h, sz) for h in (0, 1)]
        self.jamb = (x - dx, y, z - dz)
        # the wall over all of it, and the lintel's bulb
        self.over = [(cx, y + 2, cz) for cx, cz in col] + [(sx, y + 2, sz)]
        self.lamp = (x, y + 3, z)
        # a bulb diagonal to the slot (a block along and a block aside)
        self.diagonal = (sx + dx - dz, y, sz + dz + dx)
        self.name = f"{along}, slot {slot}"

    def open_lines(self) -> list[str]:
        """the whole gate written open, as a repair would"""
        lines = [f"fill {at(self.slot[0])} {at(self.slot[1])} {AIR}"]
        lines += [
            setblock(c, f"{PISTON}[facing={self.facing},extended=false]")
            for c in self.piston
        ]
        lines += [setblock(c, LEAF) for c in self.leaf]
        lines += [setblock(c, AIR) for c in self.door]
        return lines

    def expect(self, shut: bool) -> dict[Cell, str]:
        f = self.facing
        if shut:
            head = f"minecraft:piston_head[facing={f},type=sticky]"
            want = dict.fromkeys(self.door, LEAF)
            want |= dict.fromkeys(self.leaf, head)
            want |= dict.fromkeys(self.piston, f"{PISTON}[facing={f},extended=true]")
        else:
            want = dict.fromkeys(self.door, AIR)
            want |= dict.fromkeys(self.leaf, LEAF)
            want |= dict.fromkeys(self.piston, f"{PISTON}[facing={f},extended=false]")
        return want


def x3_gates(b: Bench) -> list[Gate]:
    ox, oy, oz = b.o
    x, y, z = ox + 44, oy + 1, oz + 4
    return [
        Gate((x, y, z), "east", "behind"),
        Gate((x + 12, y, z), "south", "behind"),
        Gate((x, y, z + 12), "west", "beside"),
        Gate((x + 12, y, z + 12), "north", "beside"),
    ]


def x3_pack(b: Bench) -> list[Gate]:
    gates = x3_gates(b)
    shut = [f"fill {at(g.slot[0])} {at(g.slot[1])} {REDSTONE}" for g in gates]
    open_ = [f"fill {at(g.slot[0])} {at(g.slot[1])} {AIR}" for g in gates]
    b.function("gate/shut", shut)
    b.function("gate/open", open_)
    b.function("gate/write_open", [line for g in gates for line in g.open_lines()])
    # the mend, for every tick: a gate whose pistons stand at rest has its
    # leaves where they belong, whatever a short pulse or a rewrite left.
    # It reads the pistons and never writes them: a piston written while
    # the game has a stroke of it in hand is what loses a leaf
    lines = []
    for g in gates:
        head = f"minecraft:piston_head[facing={g.facing}]"
        for d, c, p in zip(g.door, g.leaf, g.piston, strict=True):
            rest = f"execute if block {at(p)} {PISTON}[extended=false]"
            out = f"execute if block {at(p)} {PISTON}[extended=true] if block {at(c)} {head}"
            lines += [
                f"{rest} unless block {at(c)} {LEAF} run {setblock(c, LEAF)}",
                f"{rest} unless block {at(d)} {AIR} run {setblock(d, AIR)}",
                f"{out} unless block {at(d)} {LEAF} run {setblock(d, LEAF)}",
            ]
    b.function("gate/mend", lines)
    for state in ("open", "shut"):
        lines = [f"scoreboard players set #g_{n} {OBJ} 0" for n in range(len(gates))]
        for n, g in enumerate(gates):
            for c, block in g.expect(state == "shut").items():
                lines.append(f"execute unless block {at(c)} {block} {add(f'#g_{n}')}")
        lines.append(f"scoreboard players set #g_bad {OBJ} 0")
        lines += [
            f"scoreboard players operation #g_bad {OBJ} += #g_{n} {OBJ}"
            for n in range(len(gates))
        ]
        lines += [
            f"execute if score #g_bad {OBJ} matches 1.. {add('#g_faults')}",
            f"execute if score #g_bad {OBJ} matches 1.. unless score #g_first {OBJ} "
            f"matches 1.. run scoreboard players operation #g_first {OBJ} = "
            f"#g_strokes {OBJ}",
            f"scoreboard players add #g_ran {OBJ} 1",
        ]
        b.function(f"gate/chk_{state}", lines)
    half = STROKE // 2
    b.function(
        "gate/cycle",
        [
            f"scoreboard players add #g_phase {OBJ} 1",
            f"execute if score #g_phase {OBJ} matches 1 run function {NS}:gate/shut",
            f"execute if score #g_phase {OBJ} matches {half - 1} "
            f"run function {NS}:gate/chk_shut",
            f"execute if score #g_phase {OBJ} matches {half} run function {NS}:gate/open",
            f"execute if score #g_phase {OBJ} matches {STROKE - 1} "
            f"run function {NS}:gate/chk_open",
            f"execute if score #g_phase {OBJ} matches {STROKE - 1} {add('#g_strokes')}",
            f"execute if score #g_phase {OBJ} matches {STROKE}.. "
            f"run scoreboard players set #g_phase {OBJ} 0",
        ],
    )
    b.every("#g_on", "gate/cycle")
    b.every("#g_mend", "gate/mend")
    for n in range(1, 9):
        b.function(
            f"gate/pulse_{n}",
            [f"function {NS}:gate/shut", f"schedule function {NS}:gate/open {n}t"],
        )
        b.function(
            f"gate/gap_{n}",
            [f"function {NS}:gate/open", f"schedule function {NS}:gate/shut {n}t"],
        )
        b.function(
            f"gate/rewrite_shutting_{n}",
            [
                f"function {NS}:gate/shut",
                f"schedule function {NS}:gate/write_open {n}t",
            ],
        )
        b.function(
            f"gate/rewrite_opening_{n}",
            [
                f"function {NS}:gate/open",
                f"schedule function {NS}:gate/write_open {n}t",
            ],
        )
    return gates


def x3_run(b: Bench, gates: list[Gate]) -> None:
    print("-- 3 the Clockwork Maze's gate", flush=True)
    ox, oy, oz = b.o
    a, z = (ox + 38, oy, oz), (ox + 66, oy + 6, oz + 24)
    b.plot(a, z)
    b.fill(a, (z[0], a[1], z[2]), STONE)
    box = (
        f"x={a[0]},y={a[1]},z={a[2]},dx={z[0] - a[0]},dy={z[1] - a[1]},dz={z[2] - a[2]}"
    )
    for g in gates:
        b.put(dict.fromkeys([g.jamb, *g.over], STONE))
        b.put({g.lamp: f"{BULB}[lit=true]", g.diagonal: f"{BULB}[lit=true]"})
    b.run("gate/write_open")
    b.tick(5)
    names = [g.name for g in gates]

    def faults(state: str) -> list[int | None]:
        b.run(f"gate/chk_{state}")
        return [b.score(f"#g_{n}") for n in range(len(gates))]

    def describe(g: Gate) -> str:
        kinds = [AIR, LEAF, PISTON, "minecraft:piston_head", "minecraft:moving_piston"]
        return "/".join(
            b.what(c, kinds) for c in (*g.door, *g.leaf, *g.piston)
        ).replace("waxed_chiseled_copper", "leaf")

    def lamps() -> list[tuple[bool, bool]]:
        lit = f"{BULB}[lit=true,powered=false]"
        return [(b.is_block(g.lamp, lit), b.is_block(g.diagonal, lit)) for g in gates]

    # one stroke, watched
    b.run("gate/shut")
    b.tick(10)
    shut = faults("shut")
    b.run("gate/open")
    b.tick(10)
    opened = faults("open")
    b.check(
        "3a one stroke: slot filled with redstone_block from a function, both "
        "leaves in the doorway 10 ticks on; slot cleared, both parked 10 ticks on "
        f"(gates: {names})",
        shut == [0] * len(gates) and opened == [0] * len(gates),
        f"cells wrong shut {shut}, open {opened}",
    )

    # 1000 strokes, counted and checked by the pack itself
    for name in ("#g_phase", "#g_strokes", "#g_faults", "#g_first", "#g_ran"):
        b.set_score(name, 0)
    b.set_score("#g_on", 1)
    t = time.time()
    while (b.score("#g_strokes") or 0) < 1000:
        b.tick(4000, chunk=2000)
        if time.time() - t > 900:
            break
    b.set_score("#g_on", 0)
    b.tick(STROKE)
    strokes, ran = b.score("#g_strokes"), b.score("#g_ran")
    wrong, first = b.score("#g_faults"), b.score("#g_first")
    b.run("gate/open")
    b.tick(20)
    end = faults("open")
    b.check(
        f"3b 1000 strokes {STROKE} ticks apart, each read shut and read open by "
        "the pack: never a cell out of place",
        (strokes or 0) >= 1000 and wrong == 0 and end == [0] * len(gates),
        f"{strokes} strokes, {ran} reads, {wrong} with a fault (first at stroke "
        f"{first}), at the end {end}, {time.time() - t:.0f} s",
    )
    lit = lamps()
    b.check(
        "3c a lit bulb on the lintel and one diagonal to the slot are still "
        "lit and unpowered after them",
        all(x and y for x, y in lit),
        lit,
    )

    none = [0] * len(gates)

    def rest_open(mend: bool) -> None:
        """every gate open and whole, by the slot and the mend alone"""
        b.set_score("#g_mend", 1)
        b.run("gate/open")
        b.tick(12)
        b.set_score("#g_mend", 1 if mend else 0)
        if faults("open") != none:
            raise RuntimeError(
                "the gates could not be put right: " + describe(gates[0])
            )

    def states() -> str:
        return "; ".join(describe(g) for g in gates)

    # short pulses: the slot cleared n ticks after it was filled
    raw, mended = {}, {}
    for mend in (False, True):
        for n in range(1, 9):
            rest_open(mend)
            b.run(f"gate/pulse_{n}")
            b.tick(40)
            ok = faults("open") == none
            (mended if mend else raw)[n] = ok
            if not ok:
                b.note(
                    f"pulse of {n} ticks{' with the mend' if mend else ''}, 40 ticks "
                    f"on (door/door/leaf/leaf/piston/piston): {states()}"
                )
    b.check(
        "3d short pulses (slot cleared 1 to 8 ticks after it was filled), "
        "nothing else done: all end open with the leaves parked",
        all(raw.values()),
        f"clean: {raw}",
    )
    b.check(
        "3e the same with the mend run every tick: all end open and whole",
        all(mended.values()),
        f"clean: {mended}",
    )
    raw, mended = {}, {}
    for mend in (False, True):
        for n in range(1, 9):
            rest_open(mend)
            b.run("gate/shut")
            b.tick(20)
            b.run(f"gate/gap_{n}")
            b.tick(40)
            ok = faults("shut") == none
            (mended if mend else raw)[n] = ok
            if not ok:
                b.note(
                    f"shut gate opened and shut again {n} ticks later"
                    f"{' with the mend' if mend else ''}, 40 ticks on: {states()}"
                )
    b.check(
        "3f a shut gate opened and shut again 1 to 8 ticks later ends shut "
        "(nothing else done)",
        all(raw.values()),
        f"clean: {raw}",
    )
    b.check("3g the same with the mend run every tick", all(mended.values()), mended)

    # the whole gate rewritten (slot, pistons, leaves, doorway) in mid stroke
    res, after = {}, {}
    for kind in ("shutting", "opening"):
        for n in (1, 2, 3, 4):
            rest_open(False)
            if kind == "opening":
                b.run("gate/shut")
                b.tick(20)
            b.run(f"gate/rewrite_{kind}_{n}")
            b.tick(40)
            res[f"{kind} +{n}"] = faults("open") == none
            if not res[f"{kind} +{n}"]:
                b.note(f"rewritten {n} ticks into {kind}, 40 ticks on: {states()}")
            b.set_score("#g_mend", 1)
            b.tick(5)
            after[f"{kind} +{n}"] = faults("open") == none
    rest_open(False)
    b.run("gate/shut")
    b.tick(20)
    b.run("gate/write_open")
    b.tick(40)
    res["shut, at rest"] = faults("open") == none
    if not res["shut, at rest"]:
        b.note(f"a shut gate at rest rewritten open, 40 ticks on: {states()}")
    b.set_score("#g_mend", 1)
    b.tick(5)
    after["shut, at rest"] = faults("open") == none
    n_items = b.count(f"@e[type=minecraft:item,{box}]")
    b.check(
        "3h the whole gate rewritten open by setblock (slot, pistons, leaves, "
        "doorway) while shut or in mid stroke: ends open and whole",
        all(res.values()),
        f"{res}; items {n_items}",
    )
    b.check(
        "3i whatever a rewrite left, 5 ticks of the mend put right (so a "
        "reset is: clear the slots, and the mend)",
        all(after.values()) and n_items == 0,
        after,
    )
    rest_open(False)
    # a bulb face to face with a slot, for contrast
    g = gates[0]
    dx, dz = DIRS["east"]
    beside = (g.slot[0][0] + dx, g.slot[0][1], g.slot[0][2] + dz)
    b.put({beside: f"{BULB}[lit=true]"})
    b.tick(5)
    b.run("gate/shut")
    b.tick(10)
    flipped = b.is_block(beside, f"{BULB}[lit=false]")
    b.run("gate/open")
    b.tick(10)
    b.note(
        f"a lit bulb face to face with the slot went dark when it was filled: {flipped}"
    )


# == shared: pens and prey ==================================================

PREY = (
    '{NoAI:1b,PersistenceRequired:1b,attributes:[{id:"minecraft:max_health",'
    "base:1000d}],Health:1000f}"
)


def off(b: Bench, dx: int, dy: int, dz: int) -> Cell:
    return (b.o[0] + dx, b.o[1] + dy, b.o[2] + dz)


def box_sel(a: Cell, z: Cell) -> str:
    return dp.box_selector(a, z)


def pen(b: Bench, corner: Cell, nx: int, nz: int, high: int, roof: bool) -> Cell:
    """a stone pen, inside ``nx`` by ``nz`` and ``high`` tall, on a stone
    floor; with a roof it is dark inside. Gives the inside's low corner"""
    x, y, z = corner
    top = y + high + (1 if roof else 0)
    b.fill(corner, (x + nx + 1, top, z + nz + 1), STONE)
    b.fill((x + 1, y + 1, z + 1), (x + nx, y + high, z + nz), AIR)
    return (x + 1, y + 1, z + 1)


def stair_pen(b: Bench, corner: Cell, wide: int, high: int, roof: bool) -> Cell:
    """a pen 9 by 16 with a platform 4 up at its far end, reached by a
    flight of stairs ``wide`` across between stone walls"""
    c = pen(b, corner, 9, 16, high, roof)
    x, y, z = c
    b.fill((x, y, z + 10), (x + 8, y + 3, z + 15), STONE)
    b.fill((x, y, z + 6), (x + 8, y + high - 1, z + 9), STONE)
    x1 = x + 4 - wide // 2
    for n in range(4):
        zz = z + 6 + n
        b.fill((x1, y + n, zz), (x1 + wide - 1, y + high - 1, zz), AIR)
        b.fill(
            (x1, y + n, zz),
            (x1 + wide - 1, y + n, zz),
            "minecraft:stone_stairs[facing=south]",
        )
    return c


# == 4: the Engine's pair ====================================================


def x4_pack(b: Bench) -> None:
    return None


def x4_run(b: Bench, _: None) -> None:
    print("-- 4 the Engine's pair", flush=True)
    a, z = off(b, 40, 0, 30), off(b, 112, 8, 49)
    b.plot(a, z)
    grief = b.cmd("gamerule mob_griefing")
    hard = b.cmd("difficulty")
    axe = 'equipment:{mainhand:{id:"minecraft:iron_axe",count:1}}'
    none = 'attributes:[{id:"minecraft:attack_damage",base:0d}]'
    pens = {
        "bite": ("vindicator", none, "", "flat"),  # the rider's blow does nothing
        "blow": ("vindicator", "", none, "flat"),  # the ravager's bite does nothing
        "husk": ("husk", "", "", "flat"),
        "stair1": ("vindicator", "", "", 1),
        "stair2": ("vindicator", "", "", 2),
        "stair3": ("vindicator", "", "", 3),
    }
    where: dict[str, Cell] = {}
    for n, (name, (rider, rider_nbt, mount_nbt, kind)) in enumerate(pens.items()):
        corner = (a[0] + 12 * n, a[1], a[2])
        if kind == "flat":
            c = pen(b, corner, 9, 16, 6, False)
            prey = (c[0] + 4, c[1], c[2] + 13)
        else:
            c = stair_pen(b, corner, int(kind), 7, False)
            prey = (c[0] + 4, c[1] + 4, c[2] + 13)
        where[name] = c
        if name == "bite":
            # a deck across the pen, 5 over the floor, to pass under
            b.fill((c[0], c[1] + 4, c[2] + 7), (c[0] + 8, c[1] + 4, c[2] + 8), STONE)
            b.summon(
                "minecraft:zombie",
                (c[0], c[1], c[2] + 8),
                "{NoAI:1b,IsBaby:0b,PersistenceRequired:1b}",
                "x4_mate",
            )
        b.summon("minecraft:iron_golem", prey, PREY, f"x4_prey_{name}")
        extra = f"{axe}," if rider == "vindicator" else "IsBaby:0b,"
        inner = f'id:"minecraft:{rider}",Tags:["{TAG}","x4_rider_{name}"],' + extra
        inner += f"PersistenceRequired:1b{',' if rider_nbt else ''}{rider_nbt}"
        mount = f"{{PersistenceRequired:1b,{mount_nbt}{',' if mount_nbt else ''}"
        mount += f"Passengers:[{{{inner}}}]}}"
        b.summon(
            "minecraft:ravager", (c[0] + 4, c[1], c[2] + 2), mount, f"x4_mount_{name}"
        )
    b.tick(2)
    b.cmd(f"team join {TEAM} @e[tag={TAG}]")
    start = {n: b.pos(f"@e[tag=x4_mount_{n},limit=1]") for n in pens}
    health: dict[str, list[float | None]] = {n: [] for n in pens}
    high: dict[str, float] = dict.fromkeys(pens, 0.0)
    for _step in range(6):
        b.tick(100)
        for n in pens:
            health[n].append(b.number(f"@e[tag=x4_prey_{n},limit=1]", "Health"))
            p = b.pos(f"@e[tag=x4_mount_{n},limit=1]")
            if p:
                high[n] = max(high[n], p[1] - where[n][1])
    end = {n: b.pos(f"@e[tag=x4_mount_{n},limit=1]") for n in pens}

    def moved(n: str) -> float:
        p, q = start[n], end[n]
        return (
            round(((p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2) ** 0.5, 1)
            if p and q
            else -1
        )

    def lost(n: str) -> float:
        h = health[n][-1]
        return round(1000 - h, 1) if h is not None else -1

    b.note(
        f"{grief}; {hard}; the prey is an iron golem that cannot move, 11 blocks off"
    )
    b.note(f"prey's health each 100 ticks: {health}")
    b.check(
        "4a a ravager with a vindicator on it (the rider's blow set to 0) goes "
        "for the prey by itself and bites, passing under a deck 5 over the floor",
        lost("bite") > 0 and moved("bite") > 6,
        f"prey lost {lost('bite')}, ravager went {moved('bite')} blocks",
    )
    b.check(
        "4b the rider strikes from its back (the ravager's bite set to 0)",
        lost("blow") > 0,
        f"prey lost {lost('blow')}",
    )
    riding = b.count("@e[tag=x4_rider_bite,nbt={PersistenceRequired:1b}]") + b.count(
        "@e[tag=x4_mount_bite,nbt={PersistenceRequired:1b}]"
    )
    b.cmd(
        f"execute as @e[tag=x4_rider_bite] on vehicle if entity @s[tag=x4_mount_bite] "
        f"run scoreboard players set #x4_rides {OBJ} 1"
    )
    mate = b.number("@e[tag=x4_mate,limit=1]", "Health")
    b.check(
        "4c after 600 ticks both are there, persistent, the rider still up, and "
        "the zombie of their team beside them unhurt",
        riding == 2 and b.score("#x4_rides") == 1 and mate == 20,
        f"persistent {riding} of 2, riding {b.score('#x4_rides')}, zombie's health {mate}",
    )
    b.check(
        "4d with a husk on its back the ravager only carries: it does not go "
        "for the prey or bite",
        lost("husk") == 0 and 0 <= moved("husk") < 3,
        f"prey lost {lost('husk')}, ravager went {moved('husk')} blocks",
    )
    climbs = {
        n: (lost(n) > 0, round(high[n], 1)) for n in ("stair1", "stair2", "stair3")
    }
    b.check(
        "4e the pair climbs a stair 3 wide between walls to prey 4 up, and "
        "does not climb one 1 wide",
        climbs["stair3"][0] and not climbs["stair1"][0],
        f"(prey bitten, highest the ravager stood over the floor) {climbs}",
    )
    b.note(f"a stair 2 wide between walls: climbed {climbs['stair2'][0]}")


# == 5: daylight ==============================================================


def x5_pack(b: Bench) -> None:
    return None


def x5_run(b: Bench, _: None) -> None:
    print("-- 5 daylight under glass and a block of sea", flush=True)
    a, z = off(b, 70, 0, 0), off(b, 94, 6, 6)
    b.plot(a, z)
    helmet = (
        'equipment:{head:{id:"minecraft:copper_helmet",count:1,'
        'components:{"minecraft:unbreakable":{}}}},'
    )
    cases = {
        "zombie, open sky": ("zombie", "", "open"),
        "zombie in a helmet, open sky": ("zombie", helmet, "open"),
        "zombie, glass": ("zombie", "", "glass"),
        "zombie, glass and water": ("zombie", "", "water"),
        "skeleton, glass and water": ("skeleton", "", "water"),
        "zombie in a helmet, glass and water": ("zombie", helmet, "water"),
        "skeleton in a helmet, glass and water": ("skeleton", helmet, "water"),
    }
    cells: dict[str, Cell] = {}

    def put_mob(name: str) -> None:
        kind, nbt, _roof = cases[name]
        baby = "IsBaby:0b," if kind == "zombie" else ""
        b.summon(
            f"minecraft:{kind}",
            cells[name],
            f"{{{baby}{nbt}PersistenceRequired:1b}}",
            f"x5_{list(cases).index(name)}",
        )

    for n, (name, (_kind, _nbt, roof)) in enumerate(cases.items()):
        x, y, zz = a[0] + 3 * n, a[1], a[2] + 1
        b.fill((x, y, zz), (x + 2, y, zz + 2), STONE)
        b.fill((x, y + 1, zz), (x + 2, y + 2, zz + 2), GLASS)
        b.fill((x + 1, y + 1, zz + 1), (x + 1, y + 2, zz + 1), AIR)
        if roof != "open":
            b.fill((x, y + 3, zz), (x + 2, y + 3, zz + 2), GLASS)
        if roof == "water":
            b.fill((x, y + 4, zz), (x + 2, y + 4, zz + 2), GLASS)
            b.cmd(setblock((x + 1, y + 4, zz + 1), WATER))
        cells[name] = (x + 1, y + 1, zz + 1)
        put_mob(name)
    control = "@e[tag=x5_0,limit=1]"
    burning = False
    for _try in range(24):
        b.tick(100)
        fire = b.number(control, "Fire")
        if fire is None or fire > 0:
            burning = True
            break
        b.tick(1000, chunk=1000)  # wait for the sun
    if not burning:
        b.check("5 the sun came out in 26,000 ticks (a bare zombie burnt)", False)
        return
    # the control burns: put a fresh one in, and give them all the same sun
    b.cmd("kill @e[tag=x5_0]")
    b.tick(2)
    b.cmd(f"kill @e[type=minecraft:item,{box_sel(a, z)}]")
    put_mob("zombie, open sky")
    seen: dict[str, list[tuple[float | None, float | None]]] = {n: [] for n in cases}
    for _step in range(3):
        b.tick(60)
        for n, name in enumerate(cases):
            sel = f"@e[tag=x5_{n},limit=1]"
            seen[name].append((b.number(sel, "Fire"), b.number(sel, "Health")))

    def burnt(name: str) -> bool:
        return any(f is None or f > 0 or h is None or h < 20 for f, h in seen[name])

    day = b.cmd("time query day")
    b.note(f"{day}; (Fire, Health) at 60, 120 and 180 ticks: {seen}")
    b.check(
        "5a the controls: a bare zombie under the open sky burns, and under "
        "one layer of glass burns too",
        burnt("zombie, open sky") and burnt("zombie, glass"),
        {n: burnt(n) for n in ("zombie, open sky", "zombie, glass")},
    )
    under = [n for n in cases if n.endswith("glass and water")]
    b.check(
        "5b under one layer of glass with one block of water over it, in the "
        "same sun, nobody burns: zombie and skeleton, bare and helmeted",
        not any(burnt(n) for n in under),
        {n: burnt(n) for n in under},
    )
    b.note(
        "a zombie in an unbreakable copper helmet under the open sky burnt: "
        f"{burnt('zombie in a helmet, open sky')}"
    )


# == 6: the Signal Room's contact =============================================

LAMP = "minecraft:redstone_lamp"
COPPER = "minecraft:waxed_copper_block"
STONE_BUTTON = "minecraft:stone_button[face=floor,facing=north,powered={}]"


class Signal:
    def __init__(self, b: Bench) -> None:
        self.a, self.z = off(b, 96, 0, 0), off(b, 112, 5, 12)
        x, y, z = self.a
        self.hub = (x + 3, y + 1, z + 3)
        hx, hy, hz = self.hub
        self.lamps = [
            (hx + 1, hy, hz),
            (hx - 1, hy, hz),
            (hx, hy, hz + 1),
            (hx, hy, hz - 1),
        ]
        self.note = (x + 9, y + 2, z + 3)
        self.contact = (x + 10, y + 2, z + 3)
        self.sensor = (x + 9, y + 1, z + 7)
        # a desk: gold with a button on it, a bulb and a lamp beside the gold
        self.desk = (x + 3, y + 1, z + 9)
        self.button = (x + 3, y + 2, z + 9)
        self.desk_bulb = (x + 4, y + 1, z + 9)
        self.desk_lamp = (x + 2, y + 1, z + 9)
        self.desk2 = (x + 10, y + 1, z + 9)
        self.button2 = (x + 10, y + 2, z + 9)
        self.desk2_bulb = (x + 11, y + 1, z + 9)


def x6_pack(b: Bench) -> Signal:
    s = Signal(b)
    lit = [f"execute if block {at(c)} {LAMP}[lit=true] {add('{}')}" for c in s.lamps]
    b.function(
        "sig/on",
        [setblock(s.hub, REDSTONE), f"scoreboard players set #s_lit {OBJ} 0"]
        + [line.format("#s_lit") for line in lit],
    )
    b.function(
        "sig/note",
        [
            setblock(s.contact, REDSTONE),
            f"execute store success score #s_note {OBJ} "
            f"if block {at(s.note)} minecraft:note_block[powered=true]",
        ],
    )
    for n in range(1, 7):
        b.function(
            f"sig/sample_{n}",
            [f"scoreboard players set #s_{n} {OBJ} 0"]
            + [line.format(f"#s_{n}") for line in lit],
        )
    b.function(
        "sig/off",
        [setblock(s.hub, COPPER), setblock(s.contact, COPPER)]
        + [f"schedule function {NS}:sig/sample_{n} {n}t" for n in range(1, 7)],
    )
    b.function(
        "sig/hit",
        [
            f"scoreboard players add #s_presses {OBJ} 1",
            setblock(s.button, STONE_BUTTON.format("false")),
        ],
    )
    b.function(
        "sig/keys",
        [
            f"execute if block {at(s.button)} minecraft:stone_button[powered=true] "
            f"run function {NS}:sig/hit"
        ],
    )
    b.every("#s_keys", "sig/keys")
    lines = [f"scoreboard players set #r_{k} {OBJ} 0" for k in range(0, 6)]
    for _ in range(400):
        lines.append(f"execute store result score #r {OBJ} run random value 1..4")
        lines += [
            f"execute if score #r {OBJ} matches {k} {add(f'#r_{k}')}"
            for k in (1, 2, 3, 4)
        ]
        lines.append(f"execute unless score #r {OBJ} matches 1..4 {add('#r_0')}")
    b.function("sig/random", lines)
    return s


def x6_run(b: Bench, s: Signal) -> None:
    print("-- 6 the Signal Room's contact", flush=True)
    b.plot(s.a, s.z)
    x, y, z = s.a
    b.fill(s.a, (s.z[0], y, s.z[2]), STONE)
    b.put({s.hub: COPPER} | dict.fromkeys(s.lamps, f"{LAMP}[lit=false]"))
    below = (s.note[0], s.note[1] - 1, s.note[2])
    b.put({below: "minecraft:gold_block", s.note: "minecraft:note_block"})
    b.put({(s.contact[0], s.contact[1] - 1, s.contact[2]): STONE, s.contact: COPPER})
    b.put({s.sensor: "minecraft:sculk_sensor"})
    b.put(
        {
            s.desk: "minecraft:gold_block",
            s.button: STONE_BUTTON.format("false"),
            s.desk_bulb: f"{BULB}[lit=false]",
            s.desk_lamp: f"{LAMP}[lit=false]",
            s.desk2: "minecraft:gold_block",
            s.button2: "minecraft:oak_button[face=floor,facing=north,powered=false]",
            s.desk2_bulb: f"{BULB}[lit=false]",
        }
    )
    b.tick(60)
    active = "minecraft:sculk_sensor[sculk_sensor_phase=active]"

    b.run("sig/on")
    same_tick = b.score("#s_lit")
    b.tick(4)
    heard_contact = b.is_block(s.sensor, active)
    b.tick(80)
    b.run("sig/note")
    powered = b.score("#s_note")
    b.tick(4)
    heard_note = b.is_block(s.sensor, active)
    b.check(
        "6a a redstone_block set among four redstone lamps from a function: "
        "all four read lit=true in the same function",
        same_tick == 4,
        f"lamps lit in the function that set the block: {same_tick}",
    )
    b.check(
        "6b a redstone_block set beside a note block (gold under it, air over "
        "it): powered=true in the same function, and it sounds (a sculk sensor "
        "8 blocks off wakes, which the lamps' contact alone did not do)",
        powered == 1 and heard_note and not heard_contact,
        f"powered {powered}, sensor woke for the note {heard_note}, "
        f"for the lamps' contact alone {heard_contact}",
    )
    b.tick(80)
    b.run("sig/off")
    b.tick(10)
    dark = [b.score(f"#s_{n}") for n in range(1, 7)]
    b.check(
        "6c the contact swapped back for copper: the lamps are dark within 4 ticks",
        dark[3] == 0,
        f"lamps lit 1 to 6 ticks after: {dark}",
    )

    # a button set by command: what it tells, and the pack letting it go
    b.cmd(setblock(s.button, STONE_BUTTON.format("true")))
    b.tick(4)
    by_cmd = (
        b.is_block(s.desk_bulb, f"{BULB}[lit=true]"),
        b.is_block(s.desk_lamp, f"{LAMP}[lit=true]"),
    )
    b.cmd(setblock(s.button, STONE_BUTTON.format("false")))
    b.put({s.desk_bulb: f"{BULB}[lit=false]", s.desk_lamp: f"{LAMP}[lit=false]"})
    b.tick(4)
    b.set_score("#s_presses", 0)
    b.set_score("#s_keys", 1)
    for _ in range(5):
        b.cmd(setblock(s.button, STONE_BUTTON.format("true")))
        b.tick(3)
    presses = b.score("#s_presses")
    b.set_score("#s_keys", 0)
    b.check(
        "6d a stone button on a desk set powered=true by command five times, "
        "read by the pack each tick and set back in the tick it is read: five "
        "presses counted, the button up again",
        presses == 5 and b.is_block(s.button, STONE_BUTTON.format("false")),
        f"presses {presses}",
    )
    # a real press (an arrow on a wooden button) beside a bulb
    b.cmd(
        f"summon minecraft:arrow {middle(s.button2, 0.8)} "
        f'{{Tags:["{TAG}","x6_arrow"],Motion:[0d,-0.5d,0d]}}'
    )
    b.tick(6)
    pressed = b.is_block(s.button2, "minecraft:oak_button[powered=true]")
    flipped = b.is_block(s.desk2_bulb, f"{BULB}[lit=true]")
    b.cmd("kill @e[tag=x6_arrow]")
    b.check(
        "6e a button really pressed on a block flips a copper bulb that "
        "touches that block (so no bulb or lamp may touch a desk)",
        pressed and flipped,
        f"pressed by an arrow {pressed}, the bulb lit {flipped}; the same with a "
        f"stone button set by command: (bulb lit, lamp lit) {by_cmd}",
    )
    b.run("sig/random")
    got = [b.score(f"#r_{k}") for k in range(0, 5)]
    b.check(
        "6f execute store result score ... run random value 1..4, 400 times in "
        "a function: every value 1 to 4 comes up, nothing else",
        got[0] == 0
        and sum(v or 0 for v in got[1:]) == 400
        and min(v or 0 for v in got[1:]) > 50,
        f"outside 1..4: {got[0]}; counts of 1, 2, 3, 4: {got[1:]}",
    )


# == 7: fights =================================================================

GRATE = "minecraft:waxed_copper_grate"


class Fights:
    def __init__(self, b: Bench) -> None:
        self.a, self.z = off(b, 0, 0, 55), off(b, 60, 12, 75)
        self.cell = off(b, 52, 1, 58)  # a dark cell for the hurt tests


def x7_pack(b: Bench) -> Fights:
    f = Fights(b)
    b.function(
        "fight/difficulty", [f"execute store result score #diff {OBJ} run difficulty"]
    )
    b.function(
        "fight/hurt",
        ["execute as @e[tag=x7_hurt] run damage @s 2 minecraft:generic"],
    )
    b.function(
        "fight/set_on",
        [
            "execute as @e[tag=x7_angry] run damage @s 0.01 minecraft:mob_attack "
            "by @e[tag=x7_victim,limit=1]"
        ],
    )
    b.function(
        "fight/up",
        [
            "execute as @e[tag=x7_climber] run damage @s 0.01 minecraft:mob_attack "
            "by @e[tag=x7_prey_ladder,limit=1]"
        ],
    )
    return f


def x7_run(b: Bench, f: Fights) -> None:
    print("-- 7 fights", flush=True)
    b.plot(f.a, f.z)
    b.run("fight/difficulty")
    hard = b.cmd("difficulty")
    b.check(
        "7a execute store result score ... run difficulty gives the level's "
        "number (1 on Easy; Peaceful would be 0, not tried: the world's "
        "difficulty is not the rig's to change)",
        b.score("#diff") == 1 and "Easy" in hard,
        f"score {b.score('#diff')}; {hard}",
    )
    zombie = "{IsBaby:0b,PersistenceRequired:1b,CanPickUpLoot:0b}"
    x, y, z = f.a
    floors: dict[str, int] = {}

    # a deck of copper grate with nothing under it
    c = pen(b, (x, y, z), 3, 12, 8, True)
    b.fill((c[0], c[1] + 2, c[2]), (c[0] + 2, c[1] + 2, c[2] + 11), GRATE)
    b.summon("minecraft:zombie", (c[0] + 1, c[1] + 3, c[2]), zombie, "x7_z_grate")
    b.summon(
        "minecraft:iron_golem", (c[0] + 1, c[1] + 3, c[2] + 10), PREY, "x7_prey_grate"
    )
    floors["grate"] = c[1] + 3
    # a stair two wide
    c = stair_pen(b, (x + 6, y, z), 2, 7, True)
    b.summon("minecraft:zombie", (c[0] + 4, c[1], c[2] + 1), zombie, "x7_z_stair")
    b.summon(
        "minecraft:iron_golem", (c[0] + 4, c[1] + 4, c[2] + 13), PREY, "x7_prey_stair"
    )
    floors["stair"] = c[1] + 4
    # a deck with a ladder hole in the straight way to the prey
    c = pen(b, (x + 18, y, z), 3, 12, 9, True)
    b.fill((c[0], c[1] + 3, c[2]), (c[0] + 2, c[1] + 3, c[2] + 11), STONE)
    b.fill((c[0] + 1, c[1], c[2] + 5), (c[0] + 1, c[1] + 2, c[2] + 5), STONE)
    b.fill(
        (c[0] + 1, c[1], c[2] + 6),
        (c[0] + 1, c[1] + 3, c[2] + 6),
        "minecraft:ladder[facing=south]",
    )
    b.summon("minecraft:zombie", (c[0] + 1, c[1] + 4, c[2]), zombie, "x7_z_hole")
    b.summon(
        "minecraft:iron_golem", (c[0] + 1, c[1] + 4, c[2] + 10), PREY, "x7_prey_hole"
    )
    floors["hole"] = c[1] + 4
    # a shaft one block square with a ladder, the prey by its mouth 5 up
    c = pen(b, (x + 24, y, z), 5, 5, 9, True)
    b.fill((c[0], c[1], c[2]), (c[0] + 4, c[1] + 4, c[2] + 4), STONE)
    b.fill(
        (c[0] + 1, c[1], c[2] + 1),
        (c[0] + 1, c[1] + 4, c[2] + 1),
        "minecraft:ladder[facing=south]",
    )
    b.summon("minecraft:zombie", (c[0] + 1, c[1], c[2] + 1), zombie, "x7_climber")
    b.summon(
        "minecraft:iron_golem", (c[0] + 3, c[1] + 5, c[2] + 3), PREY, "x7_prey_ladder"
    )
    floors["ladder"] = c[1]
    b.tick(2)
    seen: dict[str, list[float]] = {"ladder": []}
    for _step in range(5):
        b.run("fight/up")
        b.tick(80)
        p = b.pos("@e[tag=x7_climber,limit=1]")
        seen["ladder"].append(round(p[1] - floors["ladder"], 1) if p else -1)
    res = {}
    for name in ("grate", "stair", "hole"):
        p = b.pos(f"@e[tag=x7_z_{name},limit=1]")
        h = b.number(f"@e[tag=x7_prey_{name},limit=1]", "Health")
        res[name] = (
            h is not None and h < 1000,
            round(p[1] - floors[name], 1) if p else None,
        )
    b.check(
        "7b a zombie crosses 10 blocks of copper grate deck (nothing under "
        "it) to its prey",
        res["grate"] == (True, 0.0),
        f"(prey hit, zombie's height over the deck) {res['grate']}",
    )
    b.check(
        "7c a zombie climbs a stair two wide between walls to prey 4 up",
        res["stair"][0],
        f"(prey hit, zombie's height over the platform) {res['stair']}",
    )
    b.check(
        "7d a zombie passes a ladder hole in the straight way to its prey "
        "without going down it",
        res["hole"] == (True, 0.0),
        f"(prey hit, zombie's height over the deck) {res['hole']}",
    )
    b.check(
        "7e a zombie at the foot of a ladder in a shaft one block square, set "
        "on prey at the top (damage ... by), climbs it: ladders do not keep "
        "automatons down",
        max(seen["ladder"]) >= 4,
        f"height over the shaft's floor each 80 ticks: {seen['ladder']}",
    )

    # damage in a function; and one mob set on another by damage ... by
    c = pen(b, (f.cell[0] - 1, f.cell[1] - 1, f.cell[2] - 1), 5, 5, 3, True)
    still = "{NoAI:1b,IsBaby:0b,PersistenceRequired:1b}"
    b.summon("minecraft:husk", (c[0], c[1], c[2]), still, "x7_hurt")
    b.summon("minecraft:husk", (c[0] + 4, c[1], c[2]), still, "x7_hurt")
    b.summon("minecraft:zombie", (c[0], c[1], c[2] + 4), zombie, "x7_angry")
    b.summon("minecraft:zombie", (c[0] + 4, c[1], c[2] + 4), still, "x7_victim")
    b.tick(100)
    calm = b.number("@e[tag=x7_victim,limit=1]", "Health")
    many = b.cmd("damage @e[tag=x7_hurt] 2 minecraft:generic")
    b.run("fight/hurt")
    b.tick(2)
    b.cmd(
        f"execute as @e[tag=x7_hurt] store result score @s {OBJ} "
        "run data get entity @s Health"
    )
    left = b.count(f"@e[tag=x7_hurt,scores={{{OBJ}=18}}]")
    b.check(
        "7f damage from a function: execute as <each> run damage @s 2 "
        "minecraft:generic takes 2 from each of two husks (damage takes one "
        "target: given two it is refused)",
        left == 2 and "Only one entity" in many,
        f"husks at 18 health: {left}; with two targets: {many[:60]}",
    )
    b.run("fight/set_on")
    b.tick(200)
    after = b.number("@e[tag=x7_victim,limit=1]", "Health")
    b.check(
        "7g damage <mob> 0.01 minecraft:mob_attack by <other> sets the mob on "
        "the other (a zombie left another alone for 100 ticks, then went for it)",
        calm == 20 and (after is None or after < 20),
        f"the other's health before {calm}, 200 ticks after {after}",
    )


# == 8: displays ==============================================================


def x8_pack(b: Bench) -> None:
    b.function("disp/turn", ["execute as @e[tag=x8_turn] at @s run tp @s ~ ~ ~ ~9 ~"])
    b.every("#d_turn", "disp/turn")


def x8_run(b: Bench, _: None) -> None:
    print("-- 8 displays", flush=True)
    c = off(b, 42, 2, 78)
    b.plot(off(b, 40, 0, 76), off(b, 46, 5, 82))
    state = 'block_state:{Name:"minecraft:waxed_copper_block"}'
    b.summon(
        "minecraft:block_display", c, f"{{{state},teleport_duration:1}}", "x8_turn"
    )
    b.summon(
        "minecraft:block_display", (c[0] + 3, c[1], c[2]), f"{{{state}}}", "x8_pose"
    )
    b.tick(2)
    for _n in range(10):
        b.run("disp/turn")
    ten = b.data("@e[tag=x8_turn,limit=1]", "Rotation")
    t0 = b.score("#ticks") or 0
    b.set_score("#d_turn", 1)
    b.tick(30)
    b.set_score("#d_turn", 0)
    b.tick(2)
    turns = (b.score("#ticks") or 0) - t0
    yaw = b.number("@e[tag=x8_turn,limit=1]", "Rotation[0]")
    want = ((90 + 9 * turns + 180) % 360) - 180
    near = (
        yaw is not None
        and min(abs(yaw - want - 9 * k) for k in (-2, -1, 0, 1, 2)) < 0.01
    )
    b.check(
        "8a a block display turned by tp @s ~ ~ ~ ~9 ~ with teleport_duration:1: "
        "90 degrees after ten, and on by 9 a tick from a tick function",
        "[90.0f" in ten and near,
        f"after ten: {ten}; after about {turns} more ticks: {yaw}",
    )
    pose = (
        "{start_interpolation:0,interpolation_duration:20,transformation:{"
        "left_rotation:{axis:[0f,1f,0f],angle:1.5708f},translation:[0f,1f,0f],"
        "scale:[1f,2f,1f],right_rotation:[0f,0f,0f,1f]}}"
    )
    r = b.cmd(f"data merge entity @e[tag=x8_pose,limit=1] {pose}")
    b.tick(25)
    got = b.data("@e[tag=x8_pose,limit=1]", "transformation")
    dur = b.data("@e[tag=x8_pose,limit=1]", "interpolation_duration")
    b.check(
        "8b a block display posed by data merge with start_interpolation:0, "
        "interpolation_duration:20: the new transformation reads back",
        "Modified" in r
        and "translation: [0.0f, 1.0f, 0.0f]" in got
        and "0.70710" in got
        and dur.startswith("20"),
        f"{got}; duration {dur}",
    )


# == 9: the Maze's lift =======================================================

TRAPDOOR = "minecraft:iron_trapdoor[half=top,open=false]"
RISE, STEP = 6, 3  # blocks of travel, ticks a block


class Lift:
    def __init__(self, b: Bench) -> None:
        self.a, self.z = off(b, 50, 0, 76), off(b, 58, 12, 84)
        x, y, z = self.a
        self.lo, self.hi = (x + 3, z + 3), (x + 5, z + 5)  # the 3 x 3, in x and z
        self.y0 = y + 1  # the platform's blocks at the bottom
        self.top = self.y0 + RISE  # and at the top: the shutter's layer

    def layer(self, y: int) -> Box:
        return ((self.lo[0], y, self.lo[1]), (self.hi[0], y, self.hi[1]))


def x9_pack(b: Bench) -> Lift:
    lf = Lift(b)
    for h in range(1, RISE + 1):
        new, old = lf.layer(lf.y0 + h), lf.layer(lf.y0 + h - 1)
        sel = dp.box_selector(
            (lf.lo[0], lf.y0 + h, lf.lo[1]), (lf.hi[0], lf.top + 2, lf.hi[1])
        )
        lines = []
        if h == RISE - 3:
            lines.append(dp.fill(*lf.layer(lf.top), AIR))  # the shutter opens
        lines += [
            f"execute as @e[tag={TAG},{sel}] at @s run tp @s ~ ~1 ~",
            dp.fill(*new, COPPER),
            dp.fill(*old, AIR),
            f"scoreboard players set #l_h {OBJ} {h}",
        ]
        b.function(f"lift/at_{h}", lines)
    b.function(
        "lift/tick",
        [f"scoreboard players add #l_t {OBJ} 1"]
        + [
            f"execute if score #l_t {OBJ} matches {STEP * h} "
            f"run function {NS}:lift/at_{h}"
            for h in range(1, RISE + 1)
        ]
        + [
            f"execute if score #l_t {OBJ} matches {STEP * RISE}.. "
            f"run scoreboard players set #l_on {OBJ} 0"
        ],
    )
    b.every("#l_on", "lift/tick")
    return lf


def x9_run(b: Bench, lf: Lift) -> None:
    print("-- 9 the Maze's lift step", flush=True)
    b.plot(lf.a, lf.z)
    x, y, z = lf.a
    b.fill(lf.a, (lf.z[0], y, lf.z[2]), STONE)
    b.fill((x + 1, lf.top, z + 1), (x + 7, lf.top, z + 7), STONE)  # the upper deck
    b.fill(*lf.layer(lf.top), TRAPDOOR)
    b.fill(*lf.layer(lf.y0), COPPER)
    mid = (lf.lo[0] + 1, lf.y0 + 1, lf.lo[1] + 1)
    b.summon("minecraft:armor_stand", mid, "{}", "x9_rider")
    b.summon(
        "minecraft:armor_stand", (lf.lo[0], lf.top + 1, lf.lo[1]), "{}", "x9_above"
    )
    b.tick(10)
    before = (b.pos("@e[tag=x9_rider,limit=1]"), b.pos("@e[tag=x9_above,limit=1]"))
    b.set_score("#l_t", 0)
    b.set_score("#l_on", 1)
    b.tick(STEP * RISE + 20)
    rider, above = b.pos("@e[tag=x9_rider,limit=1]"), b.pos("@e[tag=x9_above,limit=1]")
    want = lf.top + 1
    whole = all(b.is_block(c, COPPER) for c in cells(*lf.layer(lf.top)))
    b.check(
        f"9a a stand on a 3 x 3 platform stepped up {RISE} blocks at {STEP} ticks "
        "a block (riders moved up, the new layer set, the old cleared), the "
        "shutter of iron trapdoors cleared when it is 3 below: it ends "
        "standing on the platform, level with the upper deck",
        rider is not None
        and abs(rider[1] - want) < 0.01
        and whole
        and b.score("#l_h") == RISE,
        f"from {before[0]} to {rider}; the platform's top at y {want}",
    )
    b.check(
        "9b a stand standing on the shutter when it opens ends on the platform too",
        above is not None
        and abs(above[1] - want) < 0.01
        and lf.lo[0] <= above[0] <= lf.hi[0] + 1,
        f"from {before[1]} to {above}",
    )


# == 10: the Gearworks' small things ============================================

PIPE = "minecraft:waxed_exposed_copper_bulb"


class Gear:
    def __init__(self, b: Bench) -> None:
        self.a, self.z = off(b, 64, 0, 88), off(b, 92, 8, 112)
        x, y, z = self.a
        self.hub = (x + 16, y + 3, z + 12)
        hx, hy, hz = self.hub
        self.disc = [
            (hx + f, hy, hz + r)
            for f in range(-5, 6)
            for r in range(-5, 6)
            if f * f + r * r <= 30
        ]


def rows(cs: list[Cell]) -> list[Box]:
    """cells of one layer as rows along x"""
    out: list[Box] = []
    for c in sorted(cs, key=lambda c: (c[1], c[2], c[0])):
        if out and out[-1][1] == (c[0] - 1, c[1], c[2]):
            out[-1] = (out[-1][0], c)
        else:
            out.append((c, c))
    return out


def x10_pack(b: Bench) -> Gear:
    g = Gear(b)
    for name, block in (
        ("a", "minecraft:waxed_cut_copper"),
        ("b", "minecraft:waxed_exposed_cut_copper"),
    ):
        b.function(f"gear/{name}", [dp.fill(lo, hi, block) for lo, hi in rows(g.disc)])
    b.function(
        "gear/turn",
        [
            f"scoreboard players add #gear_t {OBJ} 1",
            f"scoreboard players operation #gear_p {OBJ} = #gear_t {OBJ}",
            f"scoreboard players operation #gear_p {OBJ} %= #2 {OBJ}",
            f"execute if score #gear_p {OBJ} matches 0 run function {NS}:gear/a",
            f"execute if score #gear_p {OBJ} matches 1 run function {NS}:gear/b",
        ],
    )
    b.pack.constants(OBJ, 2)
    b.every("#gear_on", "gear/turn")
    b.function(
        "gear/items",
        [
            f"execute as @e[tag=x10_item] store result score #i_pipe {OBJ} "
            f"if items entity @s contents {PIPE}",
            f"execute as @e[tag=x10_item] store result score #i_data {OBJ} "
            "if items entity @s contents *[minecraft:custom_data~{st_gear:1b}]",
            f"execute as @e[tag=x10_item] store result score #i_gold {OBJ} "
            "if items entity @s contents minecraft:gold_block",
        ],
    )
    return g


def x10_run(b: Bench, g: Gear) -> None:
    print("-- 10 the Gearworks' small things", flush=True)
    b.plot(g.a, g.z)
    x, y, z = g.a
    b.fill(g.a, (g.a[0] + 8, y, g.a[2] + 10), STONE)
    box = box_sel(g.a, g.z)

    # a lit bulb with a bulb put beside it, and a block of redstone two off
    one, two = (x + 3, y + 1, z + 2), (x + 4, y + 1, z + 2)
    b.put({one: f"{PIPE}[lit=true]"})
    b.tick(5)
    b.put({two: f"{PIPE}[lit=false]"})
    b.tick(20)
    kept = b.is_block(one, f"{PIPE}[lit=true,powered=false]") and b.is_block(
        two, f"{PIPE}[lit=false,powered=false]"
    )
    b.put({(x + 1, y + 1, z + 2): REDSTONE})
    b.tick(20)
    kept2 = b.is_block(one, f"{PIPE}[lit=true,powered=false]")
    b.put({(x + 1, y + 1, z + 2): AIR, one: f"{PIPE}[lit=false]"})
    b.tick(20)
    kept3 = b.is_block(one, f"{PIPE}[lit=false]") and b.is_block(
        two, f"{PIPE}[lit=false]"
    )
    b.check(
        "10a a bulb set lit=true stays lit and its new neighbour dark when a "
        "bulb is set beside it; a block of redstone two blocks off changes "
        "nothing; set dark again it stays dark",
        kept and kept2 and kept3,
        (kept, kept2, kept3),
    )
    states = ["lit=false,powered=false", "lit=true,powered=false"]
    states += ["lit=false,powered=true", "lit=true,powered=true"]
    line = [(x + 1 + 2 * n, y + 1, z + 5) for n in range(4)]
    b.put({c: f"{PIPE}[{s}]" for c, s in zip(line, states, strict=True)})
    r = b.cmd(dp.fill(line[0], line[-1], AIR, f"replace {PIPE}"))
    b.check(
        "10b fill ... air replace minecraft:waxed_exposed_copper_bulb takes a "
        "bulb in each of its four states",
        "filled 4 " in r,
        r,
    )

    # items: an item entity read by `if items`, and clear by custom_data
    b.cmd(
        f"summon minecraft:item {middle((x + 3, y + 1, z + 8))} "
        f'{{Tags:["{TAG}","x10_item"],NoGravity:1b,PickupDelay:32767,Item:{{id:"{PIPE}",'
        'count:3,components:{"minecraft:custom_data":{st_gear:1b}}}}'
    )
    b.tick(2)
    b.run("gear/items")
    got = [b.score(f"#i_{k}") for k in ("pipe", "data", "gold")]
    clear = b.cmd("clear @a[gamemode=adventure] *[minecraft:custom_data~{st_gear:1b}]")
    count = b.cmd(
        "clear @a[gamemode=adventure] *[minecraft:custom_data~{st_gear:1b}] 0"
    )
    b.check(
        "10c execute as <item entity> if items entity @s contents <item>: 3 "
        "for the bulb, 3 by its custom_data, 0 for another item; clear by "
        "custom_data parses (nobody to clear)",
        got == [3, 3, 0] and "No player" in clear and "No player" in count,
        f"counts {got}; clear: {clear}",
    )
    b.cmd("kill @e[tag=x10_item]")

    # the Great Gear's 97 cells swapped under a stand, every tick
    b.run("gear/a")
    hub = g.hub
    b.summon("minecraft:armor_stand", (hub[0], hub[1] + 1, hub[2]), "{}", "x10_stand")
    b.summon(
        "minecraft:armor_stand", (hub[0] + 4, hub[1] + 1, hub[2] + 3), "{}", "x10_stand"
    )
    b.tick(10)
    b.set_score("#gear_t", 0)
    b.set_score("#gear_on", 1)
    b.tick(60)
    b.set_score("#gear_on", 0)
    b.tick(2)
    b.cmd(
        f"execute as @e[tag=x10_stand] store result score @s {OBJ} "
        "run data get entity @s Pos[1] 100"
    )
    stood = b.count(f"@e[tag=x10_stand,scores={{{OBJ}={(hub[1] + 1) * 100}}}]")
    b.check(
        f"10d the gear's {len(g.disc)} cells swapped for another full block "
        "every tick for 60 ticks (nothing under the disc): two stands on it "
        "do not fall",
        stood == 2 and (b.score("#gear_t") or 0) >= 60,
        f"stands still at y {hub[1] + 1}: {stood} of 2; swaps {b.score('#gear_t')}",
    )

    # the rule for block drops, read and (briefly) turned off
    rule = b.cmd("gamerule block_drops")
    old = b.cmd("gamerule doTileDrops")
    spot = (x + 6, y + 1, z + 8)

    def broken() -> int:
        b.put({spot: f"{PIPE}[lit=false]"})
        b.cmd(f"setblock {at(spot)} {AIR} destroy")
        b.tick(3)
        n = b.count(f"@e[type=minecraft:item,{box}]")
        b.cmd(f"kill @e[type=minecraft:item,{box}]")
        return n

    was = "true" in rule
    on = off_ = -1
    try:
        b.cmd("gamerule block_drops true")
        on = broken()
        b.cmd("gamerule block_drops false")
        off_ = broken()
    finally:
        back = b.cmd(f"gamerule block_drops {'true' if was else 'false'}")
    now = b.cmd("gamerule block_drops")
    b.check(
        "10e the rule is block_drops (doTileDrops is refused): on, a bulb "
        "broken by setblock ... destroy drops one item; off, none. The rule "
        "is put back as it was",
        on == 1 and off_ == 0 and "currently set" not in old and now == rule,
        f"was: {rule}; items with it on {on}, off {off_}; {back}; now: {now}",
    )


# == 11: machinery =============================================================


class Machine:
    def __init__(self, b: Bench) -> None:
        self.a, self.z = off(b, 96, 0, 80), off(b, 120, 5, 104)
        x, y, z = self.a
        self.c = (x + 8, y + 1, z + 18)  # the clock's block
        cx, cy, cz = self.c
        self.pistons = [(cx + 4 + 2 * k, cy + 1, cz) for k in range(3)]
        self.bulbs = [(cx + 2, cy, cz - 3 - 2 * k) for k in range(6)]
        self.tap = (cx + 2, cy, cz - 2)

    def blocks(self) -> dict[Cell, str]:
        cx, cy, cz = self.c
        wire = "minecraft:redstone_wire"
        out: dict[Cell, str] = {self.c: COPPER}
        for dx, dz in ((2, 0), (2, -1), (1, -1), (-1, -1), (-2, -1), (-2, 0)):
            out[(cx + dx, cy, cz + dz)] = wire
        # a repeater's facing names the side its input is on
        out[(cx, cy, cz - 1)] = "minecraft:repeater[facing=east,delay=4]"
        out[(cx - 1, cy, cz)] = "minecraft:repeater[facing=west,delay=4]"
        # the tappets: a repeater, a block with a piston on it and a lamp
        # beside it, three times over
        for k, p in enumerate(self.pistons):
            out[(cx + 3 + 2 * k, cy, cz)] = "minecraft:repeater[facing=west,delay=4]"
            out[(p[0], cy, cz)] = COPPER
            out[p] = "minecraft:piston[facing=up]"
            out[(p[0], cy, cz + 1)] = f"{LAMP}[lit=false]"
        # the tally: a repeater into the first bulb, a comparator between
        # each bulb and the next
        out[self.tap] = "minecraft:repeater[facing=south,delay=1]"
        for k, c in enumerate(self.bulbs):
            out[c] = f"{BULB}[lit=false]"
            if k:
                out[(c[0], c[1], c[2] + 1)] = "minecraft:comparator[facing=south]"
        return out


def x11_pack(b: Bench) -> Machine:
    m = Machine(b)
    lines = [f"scoreboard players add #m_t {OBJ} 1"]
    for k, p in enumerate(m.pistons, 1):
        out = f"if block {at(p)} minecraft:piston[extended=true]"
        b.function(
            f"mach/rise_{k}",
            [
                f"scoreboard players add #m_rises_{k} {OBJ} 1",
                f"execute unless score #m_first_{k} {OBJ} matches 1.. run "
                f"scoreboard players operation #m_first_{k} {OBJ} = #m_t {OBJ}",
            ],
        )
        lines += [
            f"execute {out} unless score #m_was_{k} {OBJ} matches 1 "
            f"run function {NS}:mach/rise_{k}",
            f"execute store success score #m_was_{k} {OBJ} {out}",
        ]
    for k, c in enumerate(m.bulbs, 1):
        lines += [
            f"execute store success score #m_now_{k} {OBJ} "
            f"if block {at(c)} {BULB}[lit=true]",
            f"execute unless score #m_now_{k} {OBJ} = #m_lit_{k} {OBJ} "
            f"{add(f'#m_tog_{k}')}",
            f"scoreboard players operation #m_lit_{k} {OBJ} = #m_now_{k} {OBJ}",
        ]
    b.function("mach/tick", lines)
    b.every("#m_on", "mach/tick")
    return m


def x11_run(b: Bench, m: Machine) -> None:
    print("-- 11 machinery", flush=True)
    b.plot(m.a, m.z)
    b.fill(m.a, (m.z[0], m.a[1], m.z[2]), STONE)
    b.put(m.blocks())
    for k in range(1, 7):
        for name in ("m_lit", "m_tog", "m_rises", "m_first", "m_was"):
            b.set_score(f"#{name}_{k}", 0)
    b.set_score("#m_t", 0)
    b.set_score("#m_on", 1)
    # the torch last: the clock starts when it is set
    cx, cy, cz = m.c
    b.cmd(setblock((cx + 1, cy, cz), "minecraft:redstone_wall_torch[facing=east]"))
    b.tick(2400, chunk=600)
    b.set_score("#m_on", 0)
    t = b.score("#m_t") or 0
    rises = [b.score(f"#m_rises_{k}") or 0 for k in (1, 2, 3)]
    first = [b.score(f"#m_first_{k}") or 0 for k in (1, 2, 3)]
    period = round(t / rises[0], 1) if rises[0] else 0
    b.check(
        "11a the torch clock (a torch on a block, dust, two repeaters of 4) "
        "set by setblock starts by itself, and three plain pistons tapped off "
        "it through repeaters rise in turn, once a turn",
        rises[0] > 10
        and max(rises) - min(rises) <= 1
        and first[0] < first[1] < first[2],
        f"in {t} ticks each rose {rises} times: a turn is {period} ticks "
        f"({period / 20:.2f} s); first rises at ticks {first}",
    )
    tog = [b.score(f"#m_tog_{k}") or 0 for k in range(1, 7)]
    want = [tog[0] // 2**k for k in range(6)]
    b.check(
        "11b six waxed copper bulbs in a row with a comparator out of each "
        "into the next count in binary: each changes half as often as the one "
        "before",
        tog[0] > 10 and all(abs(a - w) <= 1 for a, w in zip(tog, want, strict=True)),
        f"changes of each bulb in {t} ticks: {tog} (wanted about {want})",
    )
    b.cmd(setblock((cx + 1, cy, cz), AIR))
    b.tick(60)
    stopped = [b.score(f"#m_was_{k}") for k in (1, 2, 3)]
    b.note(f"the torch taken out: 60 ticks on the pistons are {stopped} (0 is down)")


# == running ================================================================

Experiment = tuple[Callable[[Bench], object], Callable[..., None]]
EXPERIMENTS: dict[str, Experiment] = {
    "2": (x2_pack, x2_run),
    "3": (x3_pack, x3_run),
    "4": (x4_pack, x4_run),
    "5": (x5_pack, x5_run),
    "6": (x6_pack, x6_run),
    "7": (x7_pack, x7_run),
    "8": (x8_pack, x8_run),
    "9": (x9_pack, x9_run),
    "10": (x10_pack, x10_run),
    "11": (x11_pack, x11_run),
}


def run(world, datapacks_dir: Path) -> None:
    b = Bench(world, datapacks_dir)
    which = os.environ.get("WHICH", ",".join(EXPERIMENTS)).split(",")
    made = {key: EXPERIMENTS[key][0](b) for key in which}
    b.function(
        "tick", [f"scoreboard players add #ticks {OBJ} 1", *b.tick_lines], tick=True
    )
    try:
        b.forceload(True)
        dp.install(world, b.pack, datapacks_dir)
        b.cmd(f"team add {TEAM}")
        b.cmd(f"team modify {TEAM} friendlyFire false")
        for key in which:
            try:
                EXPERIMENTS[key][1](b, made[key])
            except Exception as e:  # one broken experiment must not stop the rest
                b.check(f"experiment {key} ran to its end", False, repr(e))
    finally:
        b.cleanup()
    failed = [name for name, ok in b.results if not ok]
    print(
        f"{len(b.results) - len(failed)} passed, {len(failed)} failed"
        + "".join(f"\n  FAILED {name}" for name in failed),
        flush=True,
    )


def main(world) -> None:
    online = world.cmd("list", r"There are \d+ of a max.*")
    if not re.search(r"There are 0 ", online):
        print(f"a player is online ({online}): the rig sprints time, so not run")
        return
    where = os.environ.get(dp.DATAPACKS_ENV)
    if where is None and getattr(world, "world_folder", None):
        where = str(world.world_folder / "datapacks")
    if where is None:
        print(f"set {dp.DATAPACKS_ENV} to the world's datapacks folder")
        return
    run(world, Path(where))


if __name__ == "__main__":
    main(globals()["world"])  # `world` is given by `mciwb run`
