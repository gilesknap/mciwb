"""
The sea floor round The Drowned Station, dressed so that the sea can be
seen from inside the domes: lights in the sand, coral reefs, sea pickles
and seagrass, and lighter water. Two build stages, both after the tunnels:

- ``seabed``: the blocks (``plan()``). It first takes away what an earlier
  run of the stage left (``clear_boxes``), so a rerun, or a run after the
  plan was retuned, leaves exactly the plan.
- ``seabed_water``: the biome of the station's box set to ``BIOME`` from
  the lowest floor up to the sea's surface (``biome_boxes``). A warm
  ocean's water is a light turquoise where this sea's is a dark blue, so
  the same light shows much more through the glass; tropical fish spawn in
  it too. ``fillbiome`` sets what is there already again without harm.

**What is placed** (all of it a pure function of the layout, the survey
and ``SEED``):

- ``LANTERN`` set flush in the sea floor (it takes the floor block's
  place): a loose ring close round each dome and a thinner one further
  out, a row down each side of every tunnel, and a scatter over the rest;
- reefs: mounds of living coral block one to four high that follow the
  ground, with corals, coral fans and sea pickles on top, wall fans on
  their sides and a fringe of corals, fans and seagrass on the sand round
  them. Each reef has two main colours of the five, so the colours read
  as patches;
- sea pickles, three or four to a block (light 12 or 15), in small
  clusters round the domes and on the reefs;
- tufts of seagrass.

**Where.** Only in columns of the station's box that are ``MARGIN`` clear
blocks or more from every dome's shell and every tunnel's glass, measured
level (``protected``): so never on, under or over a dome, a tunnel, a
pier, the dock or the lift, whatever the height. Only where the survey
(``site_survey.npz``, the sea floor before the station was built) has
water over a floor between ``FLOOR_LOW`` and ``FLOOR_HIGH``: not down the
ravines, not on the bubble column. Everything stands on the surveyed
floor, or on the reef's own coral.

**Coral stays alive** only while it touches water. Every coral, fan and
pickle is waterlogged; every living coral block has water (or one of
those) on one of its six faces, by the survey: a block of a mound that
would have none is ``CORE`` (it is buried, and cannot be seen).
``problems()`` checks all of this, and the margins, offline.

The build cannot read the ground, so it trusts the survey: a column whose
floor has changed since gets its dressing at the surveyed height all the
same. The live check (``check``) reads a sample of the plan back and looks
for coral that has died.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import datapack as dp
import domes
import numpy as np
import station_layout as layout
import tunnels
from domes import Cell

# ------------------------------------------------------------------- settings

SEED = 20261126
#: clear blocks between the dressing and a dome's shell or a tunnel's glass
MARGIN = 3
#: the sea floor that is dressed: not the ravines, and nothing near the top
FLOOR_LOW = min(d.floor_y for d in layout.DOMES) - 2
FLOOR_HIGH = layout.SEA_LEVEL - 12
MOUND_MAX = 4  # the most coral blocks in a column
#: the water's biome (None: leave the sea as it is)
BIOME: str | None = "minecraft:warm_ocean"
BIOME_LIMIT = 32768  # blocks a fillbiome command

LANTERN = "minecraft:sea_lantern"
#: the buried middle of a mound (a kind that is in no sea floor, so a
#: rerun can take it away again)
CORE = "minecraft:dead_horn_coral_block"
SAND = "minecraft:sand"  # what a lantern taken away leaves
WATER = "minecraft:water"
SEAGRASS = "minecraft:seagrass"
PICKLE = "minecraft:sea_pickle"
COLOURS = ("tube", "brain", "bubble", "fire", "horn")
FACING = {(0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west"}
#: what a rerun takes away first: (what a fill replaces, with what)
CLEAR = (
    ("#minecraft:wall_corals", WATER),
    ("#minecraft:corals", WATER),
    (PICKLE, WATER),
    ("#minecraft:coral_blocks", WATER),
    (CORE, WATER),
    (LANTERN, SAND),
)

# how much of everything (tuned by eye on render_seabed.py's picture)
RING_GAP = 7  # blocks between the lanterns of a dome's near ring
OUTER_GAP = 13  # ... and of its far ring
TUNNEL_GAP = 7  # blocks between the lanterns beside a tunnel
FIELD_GRID = 13  # one lantern a square of this side over the rest
LANTERN_APART = 5  # no two lanterns nearer than this
REEF_GRID = 15  # one reef (or none) a square of this side
REEF_CHANCE = 0.8
REEFS_BY_DOME = 5  # reefs set round each dome besides
PICKLES_BY_DOME = 7  # clusters of pickles round each dome
GRASS_GRID = 11  # one tuft of seagrass (or none) a square of this side


def coral_block(colour: str) -> str:
    return f"minecraft:{colour}_coral_block"


def coral(colour: str) -> str:
    return f"minecraft:{colour}_coral[waterlogged=true]"


def fan(colour: str) -> str:
    return f"minecraft:{colour}_coral_fan[waterlogged=true]"


def wall_fan(colour: str, facing: str) -> str:
    return f"minecraft:{colour}_coral_wall_fan[facing={facing},waterlogged=true]"


def pickles(count: int) -> str:
    return f"{PICKLE}[pickles={count},waterlogged=true]"


def name(block: str) -> str:
    return block.partition("[")[0]


def is_coral_block(block: str) -> bool:
    """a living coral block"""
    return block.endswith("_coral_block") and block != CORE


def is_solid(block: str) -> bool:
    """a full block of the plan (the rest hold water)"""
    return is_coral_block(block) or block in (CORE, LANTERN)


# ------------------------------------------------------------------- the site


@dataclass(frozen=True)
class Site:
    """the surveyed sea floor of the station's box, by column"""

    x0: int
    z0: int
    floor: np.ndarray  #: [x - x0, z - z0] -> the y of the top block of ground
    free: np.ndarray  #: may this column be dressed? (see the module docstring)

    def inside(self, x: int, z: int) -> bool:
        return 0 <= x - self.x0 < self.floor.shape[0] and (
            0 <= z - self.z0 < self.floor.shape[1]
        )

    def floor_at(self, x: int, z: int) -> int:
        return int(self.floor[x - self.x0, z - self.z0])

    def is_free(self, x: int, z: int) -> bool:
        return self.inside(x, z) and bool(self.free[x - self.x0, z - self.z0])


def protected() -> np.ndarray:
    """the columns of the station's box (as ``Site.floor``) that are
    within ``MARGIN`` clear blocks of a dome or a tunnel, measured level"""
    (x1, _, z1), (x2, _, z2) = layout.BOUNDS
    xs = np.arange(x1, x2 + 1)[:, None]
    zs = np.arange(z1, z2 + 1)[None, :]
    out = np.zeros((x2 - x1 + 1, z2 - z1 + 1), bool)
    for d in layout.DOMES:
        reach = d.radius + 0.5 + MARGIN + 1
        out |= (xs - d.centre[0]) ** 2 + (zs - d.centre[1]) ** 2 < reach**2
    half = tunnels.DOOR_HALF_WIDTH + 1 + MARGIN  # the glass, and the margin
    for t in layout.TUNNELS:
        lo_x, hi_x = sorted((t.a[0], t.b[0]))
        lo_z, hi_z = sorted((t.a[2], t.b[2]))
        ax, az = domes.across(t.step)
        out |= (
            (xs >= lo_x - abs(ax) * half)
            & (xs <= hi_x + abs(ax) * half)
            & (zs >= lo_z - abs(az) * half)
            & (zs <= hi_z + abs(az) * half)
        )
    return out


@cache
def site(survey_path: str | None = None) -> Site:
    """
    The sea floor of the station's box from the survey file (by default
    ``layout.SURVEY_FILE`` beside this module).

    :raises FileNotFoundError: if there is no survey
    :raises ValueError: if the survey does not cover the station's box
    """
    path = (
        Path(survey_path)
        if survey_path
        else Path(__file__).with_name(layout.SURVEY_FILE)
    )
    data = np.load(path)
    sx, sz = (int(v) for v in data["origin"])
    (x1, _, z1), (x2, _, z2) = layout.BOUNDS
    whole = data["floor"]
    if x1 < sx or z1 < sz or x2 - sx >= whole.shape[0] or z2 - sz >= whole.shape[1]:
        raise ValueError("the survey does not cover the station's box")
    cut = np.s_[x1 - sx : x2 + 1 - sx, z1 - sz : z2 + 1 - sz]
    floor = whole[cut].astype(int)
    free = (data["wet"][cut] == 1) & (floor >= FLOOR_LOW) & (floor <= FLOOR_HIGH)
    free &= ~protected()
    # (a block's neighbours are looked at: keep off the box's edge)
    free[0, :] = free[-1, :] = free[:, 0] = free[:, -1] = False
    return Site(x1, z1, floor, free)


# ------------------------------------------------------------------- the plan


class _Plan:
    """the plan as it is made: the blocks, and the columns that are used"""

    def __init__(self, where: Site):
        self.site = where
        self.rng = random.Random(SEED)
        self.blocks: dict[Cell, str] = {}
        self.columns: set[tuple[int, int]] = set()
        self.lanterns: list[tuple[int, int]] = []

    def open(self, x: int, z: int) -> bool:
        """a free column nothing stands in yet"""
        return self.site.is_free(x, z) and (x, z) not in self.columns

    def flat(self, x: int, z: int, drop: int = 2) -> bool:
        """is the ground about level here (a reef does not hang on a cliff)"""
        y = self.site.floor_at(x, z)
        return all(
            abs(self.site.floor_at(x + i, z + j) - y) <= drop
            for i, j in FACING
            if self.site.inside(x + i, z + j)
        )

    def lantern(self, x: float, z: float, apart: int = LANTERN_APART) -> None:
        x, z = round(x), round(z)
        if not self.open(x, z):
            return
        if any(abs(x - i) + abs(z - j) < apart for i, j in self.lanterns):
            return
        self.blocks[x, self.site.floor_at(x, z), z] = LANTERN
        self.columns.add((x, z))
        self.lanterns.append((x, z))

    def stand(self, x: int, z: int, block: str) -> None:
        """a plant on the sea floor of an open column"""
        if self.open(x, z):
            self.blocks[x, self.site.floor_at(x, z) + 1, z] = block
            self.columns.add((x, z))

    # -- the lights --------------------------------------------------------

    def lanterns_round(self, dome: layout.Dome, away: int, gap: int) -> None:
        """a loose ring of lanterns ``away`` to ``away + 3`` from a shell"""
        rng, (cx, cz) = self.rng, dome.centre
        angle = rng.uniform(0, math.tau)
        end = angle + math.tau
        while angle < end:
            r = dome.radius + away + rng.uniform(0, 3)
            self.lantern(cx + r * math.cos(angle), cz + r * math.sin(angle))
            angle += gap * rng.uniform(0.7, 1.3) / r

    def lanterns_beside(self, tunnel: layout.Tunnel) -> None:
        """a row of lanterns down each side of a tunnel"""
        rng = self.rng
        (sx, sz), (ax, az) = tunnel.step, domes.across(tunnel.step)
        near = tunnels.DOOR_HALF_WIDTH + 1 + MARGIN + 1
        for side in (-1, 1):
            s = rng.uniform(0, TUNNEL_GAP)
            while s < tunnel.length:
                w = side * (near + rng.randint(0, 2))
                self.lantern(
                    tunnel.a[0] + s * sx + w * ax, tunnel.a[2] + s * sz + w * az
                )
                s += TUNNEL_GAP * rng.uniform(0.7, 1.3)

    def lanterns_over(self) -> None:
        """a scatter of lanterns over the rest of the box"""
        for x, z in self.squares(FIELD_GRID):
            self.lantern(
                x + self.rng.randrange(FIELD_GRID),
                z + self.rng.randrange(FIELD_GRID),
                apart=FIELD_GRID - 4,
            )

    def squares(self, side: int) -> list[tuple[int, int]]:
        """the low corners of the squares of a grid over the box"""
        shape = self.site.floor.shape
        return [
            (self.site.x0 + i, self.site.z0 + j)
            for i in range(0, shape[0], side)
            for j in range(0, shape[1], side)
        ]

    # -- the reefs ---------------------------------------------------------

    def top(self, colour: str) -> str | None:
        """what stands on a block of a reef"""
        roll = self.rng.random()
        if roll < 0.42:
            return coral(colour)
        if roll < 0.66:
            return fan(colour)
        if roll < 0.76:
            return pickles(self.rng.choice((3, 4)))
        return None

    def reef(self, x: int, z: int) -> None:
        """a mound of coral about a column, if the ground is free there"""
        rng = self.rng
        if not (self.open(x, z) and self.flat(x, z)):
            return
        main, second = rng.sample(COLOURS, 2)
        size = rng.choice((2.4, 3.2, 3.2, 4.2, 4.2, 6.0))
        rx, rz = size * rng.uniform(0.75, 1.25), size * rng.uniform(0.75, 1.25)
        peak = rng.choice((1.2, 1.8, 2.4, 3.2, 4.2))
        reach = math.ceil(max(rx, rz)) + 1
        for i in range(-reach, reach + 1):
            for j in range(-reach, reach + 1):
                far = math.hypot(i / rx, j / rz) + rng.uniform(-0.18, 0.18)
                roll = rng.random()
                colour = (
                    main
                    if roll < 0.72
                    else second
                    if roll < 0.95
                    else rng.choice(COLOURS)
                )
                high = min(int((1 - far) * peak + rng.random() * 0.8), MOUND_MAX)
                fringe = rng.random()
                decked = self.top(colour)
                if far > 1.25 or not self.open(x + i, z + j):
                    continue
                if not self.flat(x + i, z + j, drop=3):
                    continue
                y = self.site.floor_at(x + i, z + j)
                if far > 1 or high < 1:
                    # the fringe: something on the sand, or nothing
                    if fringe < 0.22:
                        self.stand(x + i, z + j, decked or SEAGRASS)
                    elif fringe < 0.36:
                        self.stand(x + i, z + j, SEAGRASS)
                    continue
                self.columns.add((x + i, z + j))
                for up in range(1, high + 1):
                    self.blocks[x + i, y + up, z + j] = coral_block(colour)
                if decked:
                    self.blocks[x + i, y + high + 1, z + j] = decked

    def reefs_round(self, dome: layout.Dome) -> None:
        rng, (cx, cz) = self.rng, dome.centre
        for _ in range(REEFS_BY_DOME):
            angle = rng.uniform(0, math.tau)
            r = dome.radius + MARGIN + rng.uniform(6, 13)
            self.reef(round(cx + r * math.cos(angle)), round(cz + r * math.sin(angle)))

    def pickles_round(self, dome: layout.Dome) -> None:
        """small clusters of sea pickles close to a dome's glass"""
        rng, (cx, cz) = self.rng, dome.centre
        for _ in range(PICKLES_BY_DOME):
            angle = rng.uniform(0, math.tau)
            r = dome.radius + MARGIN + rng.uniform(2, 8)
            x, z = round(cx + r * math.cos(angle)), round(cz + r * math.sin(angle))
            for _ in range(rng.randint(2, 4)):
                self.stand(
                    x + rng.randint(-1, 1),
                    z + rng.randint(-1, 1),
                    pickles(rng.choice((3, 4, 4))),
                )

    def grass(self) -> None:
        """tufts of seagrass over the box"""
        rng = self.rng
        for x, z in self.squares(GRASS_GRID):
            x, z = x + rng.randrange(GRASS_GRID), z + rng.randrange(GRASS_GRID)
            blades = rng.randint(3, 8)
            if rng.random() < 0.55:
                for _ in range(blades):
                    self.stand(x + rng.randint(-2, 2), z + rng.randint(-2, 2), SEAGRASS)

    def wall_fans(self) -> None:
        """coral fans on the sides of the mounds, where there is water"""
        rng = self.rng
        for (x, y, z), block in sorted(self.blocks.items()):
            if not is_coral_block(block):
                continue
            colour = name(block).removeprefix("minecraft:").removesuffix("_coral_block")
            for (i, j), facing in FACING.items():
                beside = (x + i, y, z + j)
                roll = rng.random()
                if (
                    roll < 0.16
                    and beside not in self.blocks
                    and self.site.is_free(x + i, z + j)
                    and y > self.site.floor_at(x + i, z + j)
                ):
                    self.blocks[beside] = wall_fan(colour, facing)

    def bury(self) -> None:
        """a coral block with no water on any face would die: make it
        ``CORE`` (which nobody can see)"""
        for cell in [c for c, b in self.blocks.items() if is_coral_block(b)]:
            if not touches_water(self.site, self.blocks, cell):
                self.blocks[cell] = CORE


def touches_water(where: Site, blocks: dict[Cell, str], cell: Cell) -> bool:
    """has a cell water, or a waterlogged block of the plan, on a face?
    (By the survey: water is what is above the surveyed floor)"""
    x, y, z = cell
    for i, j, k in ((0, 1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
        beside = (x + i, y + j, z + k)
        if beside in blocks:
            if not is_solid(blocks[beside]):
                return True
        elif where.inside(x + i, z + k) and beside[1] > where.floor_at(x + i, z + k):
            return True
    return False


@cache
def plan() -> dict[Cell, str]:
    """
    Every block of the dressing: cell -> block. The same every time (the
    layout, the survey and ``SEED`` decide it).

    :raises FileNotFoundError: if there is no survey of the site
    """
    p = _Plan(site())
    # the lights first: the reefs leave their columns alone
    for dome in layout.DOMES:
        p.lanterns_round(dome, MARGIN + 1, RING_GAP)
    for tunnel in layout.TUNNELS:
        p.lanterns_beside(tunnel)
    for dome in layout.DOMES:
        p.lanterns_round(dome, MARGIN + 10, OUTER_GAP)
    p.lanterns_over()
    for dome in layout.DOMES:
        p.reefs_round(dome)
        p.pickles_round(dome)
    for x, z in p.squares(REEF_GRID):
        at = (x + p.rng.randrange(REEF_GRID), z + p.rng.randrange(REEF_GRID))
        if p.rng.random() < REEF_CHANCE:
            p.reef(*at)
    p.grass()
    p.wall_fans()
    p.bury()
    return dict(sorted(p.blocks.items()))


def census(blocks: dict[Cell, str] | None = None) -> dict[str, int]:
    """how many of each kind of thing the plan holds"""
    blocks = plan() if blocks is None else blocks
    out: dict[str, int] = dict.fromkeys(
        (
            "lanterns",
            "coral blocks",
            "corals",
            "fans",
            "wall fans",
            "pickles",
            "seagrass",
            "core",
        ),
        0,
    )
    for block in blocks.values():
        kind = name(block)
        if kind == LANTERN:
            out["lanterns"] += 1
        elif kind == CORE:
            out["core"] += 1  # (before the coral blocks: it ends as they do)
        elif kind == SEAGRASS:
            out["seagrass"] += 1
        elif kind == PICKLE:
            out["pickles"] += 1
        elif kind.endswith("_coral_block"):
            out["coral blocks"] += 1
        elif kind.endswith("_wall_fan"):
            out["wall fans"] += 1
        elif kind.endswith("_fan"):
            out["fans"] += 1
        else:
            out["corals"] += 1
    return out


# ---------------------------------------------------------------------- checks


def structure_cells() -> frozenset[Cell]:
    """every cell of the domes and the tunnels"""
    cells: set[Cell] = set()
    for d in layout.DOMES:
        cells |= domes.dome_cells(d).all
    for t in layout.TUNNELS:
        c = tunnels.tunnel_cells(t)
        cells |= c.ring | c.floor | c.inside | set(c.stairs)
    return frozenset(cells)


def near(cell: Cell, cells, reach: int = 2) -> bool:
    """is any of ``cells`` within ``reach`` of a cell, on every axis?"""
    x, y, z = cell
    span = range(-reach, reach + 1)
    return any((x + i, y + j, z + k) in cells for i in span for j in span for k in span)


def problems(blocks: dict[Cell, str] | None = None) -> list[str]:
    """
    The plan against its rules, without a server: inside the station's
    box, in free columns, two clear blocks or more from every dome and
    tunnel, everything standing on the surveyed floor or on the reef,
    every living coral block touching water, the fills inside what the
    game takes.

    :returns: the problems found, one line each; empty if there are none
    """
    try:
        where = site()
    except FileNotFoundError:
        return []  # (no survey: the stage places nothing)
    blocks = plan() if blocks is None else blocks
    found: list[str] = []
    taken = structure_cells()
    for cell, block in blocks.items():
        x, y, z = cell
        if not layout.in_station(*cell):
            found.append(f"{block} at {cell} is outside the station's box")
            continue
        if not where.is_free(x, z):
            found.append(f"{block} at {cell} is in a column that is not free")
            continue
        if near(cell, taken):
            found.append(f"{block} at {cell} is within 2 of a dome or a tunnel")
        floor = where.floor_at(x, z)
        below = blocks.get((x, y - 1, z), "")
        if block == LANTERN:
            if y != floor:
                found.append(f"the lantern at {cell} is not in the floor (y {floor})")
        elif "_wall_fan" in block:
            facing = block.partition("facing=")[2].partition(",")[0]
            (i, j) = next(step for step, way in FACING.items() if way == facing)
            if not is_coral_block(blocks.get((x - i, y, z - j), "")) or y <= floor:
                found.append(f"the wall fan at {cell} has no coral block behind it")
        elif not (y == floor + 1 or (y > floor and is_solid(below))):
            found.append(f"{block} at {cell} stands on nothing (floor y {floor})")
        if y >= layout.SEA_LEVEL - 3:
            found.append(f"{block} at {cell} is at the sea's surface")
        if "coral" in block or PICKLE in block:
            if "_block" not in block and "waterlogged=true" not in block:
                found.append(f"{block} at {cell} is not waterlogged")
        if is_coral_block(block) and not touches_water(where, blocks, cell):
            found.append(f"the coral block at {cell} touches no water")
    for a, b, _ in biome_boxes():
        if not (layout.in_station(*a) and layout.in_station(*b)):
            found.append(f"fillbiome {a} {b} leaves the station's box")
        if biome_volume(a, b) > BIOME_LIMIT:
            found.append(f"fillbiome {a} {b} is more than {BIOME_LIMIT} blocks")
    return found


# ----------------------------------------------------------------------- build


def clear_boxes() -> list[tuple[Cell, Cell]]:
    """the free columns, from the lowest dressed floor to the highest
    thing a plan could put on the highest, as boxes a fill takes"""
    where = site()
    low, high = FLOOR_LOW, FLOOR_HIGH + MOUND_MAX + 1
    xs, zs = np.nonzero(where.free)
    columns = {
        (int(x) + where.x0, 0, int(z) + where.z0) for x, z in zip(xs, zs, strict=True)
    }
    out = []
    for a, b in domes.boxes(columns):
        area = (b[0] - a[0] + 1) * (b[2] - a[2] + 1)
        layers = max(1, dp.MAX_FILL // area)
        for y in range(low, high + 1, layers):
            out.append(((a[0], y, a[2]), (b[0], min(y + layers - 1, high), b[2])))
    return out


def build(ctx: Any) -> str:
    """the ``seabed`` stage: what an earlier run left taken away, then the
    plan placed"""
    try:
        blocks = plan()
    except FileNotFoundError:
        return f"no {layout.SURVEY_FILE}: the sea floor is not known, nothing placed"
    for a, b in clear_boxes():
        for what, with_ in CLEAR:
            ctx.fill(a, b, with_, f"replace {what}")
    count = 0
    # the solid blocks first, so that what stands on them has its footing
    by_block = domes.by_block(blocks)
    for block in sorted(by_block, key=lambda b: (not is_solid(b), b)):
        for a, b in domes.boxes(by_block[block]):
            ctx.fill(a, b, block)
            count += 1
    ctx.advance(10)
    told = ", ".join(f"{n} {what}" for what, n in census(blocks).items())
    return f"{len(blocks)} blocks in {count} fills: {told}"


def biome_volume(a: Cell, b: Cell) -> int:
    """the blocks a fillbiome of a box counts: the game widens the box to
    whole cells of 4 x 4 x 4 first"""
    return math.prod((hi // 4 - lo // 4 + 1) * 4 for lo, hi in zip(a, b, strict=True))


def biome_boxes() -> list[tuple[Cell, Cell, str]]:
    """the station's box, from its bottom to the top layer of the sea, as
    boxes a fillbiome command takes, each with the biome"""
    if BIOME is None:
        return []
    (x1, y1, z1), (x2, _, z2) = layout.BOUNDS
    y2 = layout.SEA_LEVEL - 1
    high = (y2 // 4 - y1 // 4 + 1) * 4
    # (a side of n blocks may be widened to n + 3, at most)
    side = max(4, math.isqrt(BIOME_LIMIT // high) // 4 * 4 - 4)
    return [
        ((x, y1, z), (min(x + side - 1, x2), y2, min(z + side - 1, z2)), BIOME)
        for x in range(x1, x2 + 1, side)
        for z in range(z1, z2 + 1, side)
    ]


def build_water(ctx: Any) -> str:
    """the ``seabed_water`` stage: the water's biome (``BIOME``)"""
    boxes = biome_boxes()
    if not boxes:
        return "the sea's biome left as it is"
    for a, b, biome in boxes:
        command = f"fillbiome {' '.join(map(str, a + b))} {biome}"
        reply = ctx.cmd(command)
        if "not loaded" in reply or "Too many" in reply or "Unknown" in reply:
            raise RuntimeError(f"{command}: {reply!r}")
    return f"{BIOME} in {len(boxes)} boxes, from y {boxes[0][0][1]} to {boxes[0][1][1]}"


# ------------------------------------------------------------------ live check

SAMPLE = 150  # blocks of the plan the live check reads back


def check(ctx: Any) -> list[str]:
    """
    Live: a sample of the plan read back (all the lanterns' and the coral
    blocks' kinds are in it), and the biome at the corners of its box. A
    coral block that reads as its dead kind has no water on it: the
    survey was wrong there.
    """
    blocks = plan()
    found = []
    cells = sorted(blocks)
    for cell in random.Random(SEED).sample(cells, min(SAMPLE, len(cells))):
        block = name(blocks[cell])
        if ctx.is_block(cell, block):
            continue
        dead = block.replace("minecraft:", "minecraft:dead_")
        died = "coral" in block and block != CORE and ctx.is_block(cell, dead)
        found.append(f"{'dead coral' if died else 'no ' + block} at {cell}")
    boxes = biome_boxes()
    for a, b, biome in (boxes[0], boxes[-1]) if boxes else ():
        for x, y, z in (a, b):
            if not ctx.test(f"execute if biome {x} {y} {z} {biome}"):
                found.append(f"the biome at {(x, y, z)} is not {biome}")
    return found[:20]


if __name__ == "__main__":
    for what, n in census().items():
        print(f"{n:6} {what}")
    print("\n".join(problems()) or "seabed OK")
