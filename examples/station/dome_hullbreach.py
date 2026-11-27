"""
Hull Breach of The Drowned Station: a battle against the water. Its build
stage (``dome_<n>_inside``), its datapack functions (``dome/<n>/...``), its
live check (``hull_breach``) and a rig for the Breacher
(``hull_breach_rig``, run only when named). ``n`` is the dome's place in
the ring (``INDEX``); everything is placed in the dome's own frame
(fittings.py: f forward from the entrance, r right, h up from the floor),
so nothing here is a world coordinate.

**The room.** You come out of the tunnel into a dry entry hall behind a
glass dam and look down into a round pressure chamber: a copper test
column in the middle with a red band nine up (the *flood line*, painted on
both dams too), a ring walk round the chamber one block over that line, a
gantry across the top with two caged perches and the caged compressor on
the column's head, and round the walls twelve iron frames, each holding a
square of copper plate. Three levels for players: the floor, three ledges
(deck ``LEDGE_H``) under the middle breaches, and the ring walk (deck
``WALK_H``), which is always dry; the gantry (``GANTRY_H``) above. Two
stairs and seven ladders climb out of the water at every level. The exit
hall beyond the far dam is roofed with glass at the walk's height, and
opens only by the dam door after the solve.

**The one rule** (the plaque): water rises while any breach is open;
rivet plates stick only to the iron frames; keep above the red line.

- **TEST VALVE** (a lever on brass on the landing over the entry hall)
  starts the test, refused on Peaceful.
- A **stage** bursts its breaches one after another (``stag`` apart) in a
  fixed order (``ORDERS``) that pulls the players across the room and up
  and down; a burst breaks the four plates of a 2 x 2 hole out of its
  frame (``raw_iron_block``: a frame means "build here"), hangs a red
  BREACH label over it and casts a Breacher in front of it. With two
  players a stage has one more breach, and the first two burst together.
- Every step each open breach adds to ``flow``; at ``per`` a layer of
  water rises (the layer functions of the Flooded Dome, run upwards),
  never above ``MAX`` (the line). At the line with a breach open the
  room warns and counts ``hold``: seal in time and the stage goes on; if
  not the stage fails: the automatons go, the stage's breaches are made
  sound again (never on a body in a hole), the pumps take the water down,
  and the stage starts again. Stages held before are kept.
- **Rivet plates** (``waxed_exposed_chiseled_copper``, placeable only on
  the frames) are lent on entering, topped up when gone, taken back on
  leaving; four in a hole seal it. Plates put anywhere else round a frame
  are cleared (``strays``).
- When a stage's last breach is sealed: the stage holds, the automatons
  are flushed out, the pumps (the compressor working on the gantry) take
  the water down, a breather, the next. After the third: the dome is
  solved and the dam door opens.

**The mobs** (automatons.py): Breachers (``automatons.BREACHER``, a
drowned with a trident; the fallbacks are one switch, ``BREACHER_MODE``)
cast at the breaches, up to a cap, and every ``CAST_GAP`` ticks at any
open breach with a player near; Riveters fenced to the gantry. A halls
fence sends any automaton found in either hall home, so the entry hall is
always a safe place to respawn. Tridents stuck in blocks are swept.
Nothing depends on a kill. Water Breathing for everyone in the test at
levels 1 to 3.

**State** (scores in ``st``, all ``#hb.<name>``): ``state`` 0 idle, 1
testing, 2 solved; ``stage`` stages held (0 to 3); ``phase`` 0 breather,
1 bursting, 2 at the line, 3 pumping down; ``w`` the top wet layer (the
only record of the water); ``flow``; ``open``; ``b1`` .. ``b9`` each
breach open (1) or sound; ``due`` bursts to come, ``idx`` the next in the
order, ``next`` ticks to it; ``hold``; ``t`` ticks in the phase; ``form``
and ``want``; ``live``; ``wait`` (a test left: -1, or ticks to resume);
``again`` the live stage failed before; from the level (``scaled``): ``per``,
``stag``, ``hold0``, ``n1`` ``n2`` ``n3``, ``bcap``, ``rcap``, ``wb``.

**Functions** (the core calls the hooks, see game.py): ``enter``,
``tick`` (every ``STEP`` ticks ``step``: ``valve`` -> ``read`` ->
``bursts`` -> ``water`` -> ``cast`` -> ``show``, and every half second
``slow``: ``strays``, ``fence``, the sweep, the spray), ``solo``/``duo``
(recorded; ``solo`` mid-stage strikes off the extra bursts), ``died``,
``leave``, ``empty`` (``checkpoint`` in a test), ``reset``; and ``guard``
(every tick): while the outgoing tunnel's pump waits, runs or is open,
the basin is dry.

**The offline proofs** (``room_problems``, which the build runs):
the basin is closed (water has nowhere to go but the basin, the halls
and mouths hold none of it); the headroom at every level of the water
(every wet cell of the top layer is within two cells of one with air
over it); an escape at every level, with every breach open and with
every breach sound (from every place a player can get to, air within
``MAX_DIVE`` moves, and from every place with air, a way to the entry
hall that never goes under); no pits; every hole cell touching two frame
blocks; no input, plate or sign in the basin.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from functools import cache
from typing import TYPE_CHECKING, Any

import automatons
import datapack as dp
import domes
import fittings
import game
import game_checks
import rooms
import station_layout as layout
import tunnels
from dome_flooded import Shape, reach
from dome_foundry import pits
from domes import AIR, Cell, middle
from fittings import Frame, frame, label_text, snbt

if TYPE_CHECKING:
    from station_layout import Dome

INDEX = layout.index_of("hullbreach")
OBJ = game.OBJ

STEP = 2  # ticks between steps of the state machine
SLOW = 10  # ticks between the slower jobs (strays, fences, spray)
MAX = 9  # the flood line: the highest layer water ever stands at
WALK_H, LEDGE_H, GANTRY_H = 10, 5, 16  # the decks
WALK_IN, WALK_OUT = 17.0, 19.5  # the ring walk's band, from the middle
ENTRY_F, EXIT_F = -17, 17  # the two dams; the basin is between them
HALL_FS = ((-23, -18), (18, 23))
# at level 5, scaled by the core's ``#diff.timer`` (``scaled``)
PER_TICKS = 280  # a layer, for one breach open
STAGGER = 300  # between bursts
HOLD = 200  # at the line
CAST_GAP = 400  # Breachers cast again at the open breaches
RIVETER_GAP = 600  # a new Riveter after one has gone
BREATHER = 200  # between stages
PUMP_TICKS = 20  # a layer down
RESUME = 100  # from someone coming back to a left test going on
NEAR = 16  # a breach casts again only with a player this near
MAX_DIVE = 14  # moves under water a way out may ask for (the Flooded Dome's)
DECO_PHASES = 6
#: breaches a stage, solo, by level (duo: one more each)
BURSTS = {
    1: (1, 2, 2),
    2: (2, 2, 2),
    3: (2, 2, 2),
    4: (2, 2, 3),
    5: (2, 2, 3),
    6: (2, 3, 3),
    7: (2, 3, 3),
    8: (3, 3, 3),
    9: (3, 3, 4),
    10: (3, 4, 4),
}
#: Breachers alive, solo and duo, by level
BREACHER_CAP = {
    1: (1, 2),
    2: (2, 3),
    3: (2, 3),
    4: (2, 4),
    5: (3, 5),
    6: (3, 5),
    7: (3, 6),
    8: (4, 6),
    9: (4, 7),
    10: (4, 8),
}
#: Riveters alive, solo and duo, by level
RIVETER_CAP = {
    1: (1, 1),
    2: (1, 1),
    3: (1, 2),
    4: (1, 2),
    5: (1, 2),
    6: (1, 2),
    7: (2, 3),
    8: (2, 3),
    9: (2, 3),
    10: (2, 3),
}
WATER_BREATHING = range(1, 4)  # the levels that give it
#: the order each stage bursts its breaches in; the first two are on two
#: levels and two sides, and burst together with two players
ORDERS = ((1, 4, 7, 5, 3), (8, 2, 5, 3, 6), (6, 3, 9, 2, 7))

#: The Breacher, and its fallbacks if the rig finds it wrong: ``trident``
#: (the design), ``melee`` (a drowned with no trident) or ``none`` (no
#: Breachers: the Riveters alone)
BREACHER_MODE = "trident"
BREACHER_MELEE = automatons.Kind(
    "breacher",
    "minecraft:drowned",
    "Breacher",
    (("head", automatons.COPPER["head"]),),
    20,
    30,
)

WATER = "minecraft:water"
GLASS = "minecraft:glass"
BRASS = fittings.BRASS
COPPER = "minecraft:waxed_copper_block"
EXPOSED = "minecraft:waxed_exposed_copper"
WEATHERED = "minecraft:waxed_weathered_copper"
OXIDIZED = "minecraft:waxed_oxidized_copper"
CUT = fittings.CUT
EXPOSED_CUT = "minecraft:waxed_exposed_cut_copper"
WEATHERED_CUT = "minecraft:waxed_weathered_cut_copper"
CHISELED = fittings.CHISELED
GRATE = "minecraft:waxed_copper_grate"
BULB = "minecraft:waxed_copper_bulb"
TANK_BULB = "minecraft:waxed_weathered_copper_bulb"
RED = "minecraft:red_concrete"
LANTERN = "minecraft:sea_lantern"
TILES = "minecraft:deepslate_tiles"
BARS = "minecraft:iron_bars"
CHAIN = "minecraft:iron_chain"
HANGING = "minecraft:lantern[hanging=true]"
LADDER = "minecraft:ladder"
STAIRS = "minecraft:waxed_cut_copper_stairs"
TORCH = "minecraft:redstone_wall_torch"
#: the two blocks that mean something here and nowhere else
FRAME = "minecraft:raw_iron_block"
PLATE = "minecraft:waxed_exposed_chiseled_copper"
#: a frame that is only dressing: finished iron, which no plate sticks to
DRESS_FRAME = "minecraft:iron_block"
DRESS_PLATE = "minecraft:waxed_weathered_copper"
DRY, WET = "waterlogged=false", "waterlogged=true"
ENTITY_TAG = "st.hb"  # everything this module summons
STAGE_TAG = "st.hb.stage"
KEY = "plate"  # the lent plates' key (with the dome's index)
PLATES = 16  # lent at a time

#: the breaches: number, level, f of the hole's first column, side (1
#: right, -1 left); each is on a side wall, its hole two wide along f
SPECS = (
    (1, "low", -6, 1),
    (2, "low", 6, -1),
    (3, "low", -12, -1),
    (4, "mid", -2, -1),
    (5, "mid", 8, 1),
    (6, "mid", -10, 1),
    (7, "high", 4, -1),
    (8, "high", -6, 1),
    (9, "high", 12, -1),
)
#: the frames that are only dressing, in the same terms
DRESS_SPECS = (("low", 12, 1), ("mid", 3, -1), ("high", 3, 1))
HOLE_H = {"low": 2, "mid": 6, "high": 12}  # the hole's lower row
LEVEL_NAMES = {"low": "floor", "mid": "ledge", "high": "ring walk"}

# where things are, in the frame: (forward, right[, height])
STAIR_RS = ((13, 14), (-13, -14))  # the two basin stairs, right and left
TANKS = ((7, 9), (-7, -9))  # the ballast tanks' middles
VENTS = ((4, 5), (-5, 4), (5, -6), (-4, -5))
LANDING = ((-19, -18), (-1, 2))  # the valve landing, deck at WALK_H
HALL_STAIR = ((-19, -18), 12, 3)  # its places across, the foot's r, the top's r
VALVE = (-18, 0)  # the valve's post, on the landing
PLAQUE = (-6, -20)  # the plaque: r of its wall, f of its middle sign
LECTERN = (-21, -3)
RECALL = (-19, -3, 1)  # the recall post: f, r, the side its button is on
BOARD_R = -4  # the dam's gauge column (the test board)
STAGE_LAMPS = ((-1, 6), (0, 6), (1, 6))  # r, h on the entry dam
COLUMN = 1  # the test column's half width
LADDER_R = 17  # the gantry's ladders, from the walk
PERCH = ((-5, -3), (9, 11))  # a Riveter's perch: f, and r on each side
COMPRESSOR = (4, 0)  # the compressor's frame, on the gantry
PILLARS = (30, 60, 120, 150, 210, 240, 300, 330)  # bearings under the walk
FLOOR_RINGS = (6.5, 12.5)  # copper rings in the floor
RIB_EVERY = 20  # degrees between the hull's ribs

rooms.mean(FRAME, INDEX)
rooms.mean(PLATE, INDEX)
domes.allow(
    INDEX,
    "the test column",
    "a copper column in the middle of the chamber, the gauge and the gantry's "
    "hub: it stands between the entrance and the outgoing door's window, which "
    "is behind the exit dam anyway",
)


def fr_of(fr: Frame, cell: Cell) -> tuple[int, int, int]:
    """a cell's place in a frame: forward, right, height above the floor"""
    dx, dz = cell[0] - fr.origin[0], cell[2] - fr.origin[2]
    return (
        dx * fr.forward[0] + dz * fr.forward[1],
        dx * fr.right[0] + dz * fr.right[1],
        cell[1] - fr.origin[1],
    )


def _name(block: str) -> str:
    return block.partition("[")[0].partition("{")[0]


def wet(block: str, is_wet: bool = True) -> str:
    """a fitting of the basin as it stands in a wet layer, or a dry one"""
    return block.replace(DRY, WET) if is_wet else block


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


@cache
def basin(dome: Dome) -> frozenset[Cell]:
    """the cells that may hold water: all of the dome's inside between the
    dams, up to the flood line"""
    fr = frame(dome)
    out = set()
    for c in domes.dome_cells(dome).interior:
        f, _, h = fr_of(fr, c)
        if ENTRY_F < f < EXIT_F and 1 <= h <= MAX:
            out.add(c)
    return frozenset(out)


domes.add_wet(INDEX, basin(layout.DOMES[INDEX]))


# ---------------------------------------------------------------- the room


@dataclass(frozen=True)
class Breach:
    """a frame round a hole of 2 x 2 in a side wall (``number`` 0 for one
    that is only dressing)"""

    number: int
    level: str
    side: int  # 1 the right wall, -1 the left
    f0: int  # the hole's first column
    h0: int  # its lower row
    depth: int  # how far out the frame's plane is, |r|
    holes: tuple[Cell, ...]  # the lower row first
    frame: tuple[Cell, ...]
    backing: frozenset[Cell]  # glass behind, out to the shell
    front: frozenset[Cell]  # the cells in front of the hole
    bay: frozenset[Cell]  # where a stray plate is cleared (not the holes)
    spawn: Cell  # a Breacher's feet, in front of the hole
    label: tuple[float, float, float]  # where its BREACH label floats

    @property
    def tag(self) -> str:
        return f"{ENTITY_TAG}.b{self.number}"

    @property
    def name(self) -> str:
        return f"breach {self.number}"


@dataclass(frozen=True)
class Room:
    """where Hull Breach's working parts are"""

    frame: Frame
    breaches: tuple[Breach, ...]
    dressing: tuple[Breach, ...]
    gauge: tuple[Cell, ...]  # on the column's face, lowest first
    board: tuple[Cell, ...]  # the same on the entry dam
    stage_lamps: tuple[Cell, ...]
    door: tuple[Cell, ...]  # the dam door
    valve: fittings.Post
    valve_on: str
    valve_off: str
    lectern: Cell
    recall: tuple[int, int, int]
    compressor: fittings.Machine
    torch: Cell  # the compressor runs while its torch is here
    perches: tuple[Cell, Cell]  # where the Riveters are cast (feet)
    tank_lamps: tuple[Cell, ...]
    vents: tuple[Cell, ...]
    halls: tuple[tuple[Cell, Cell], tuple[Cell, Cell]]  # boxes: entry, exit
    gantry: tuple[Cell, Cell]  # the Riveters' fence

    def breach(self, number: int) -> Breach:
        return self.breaches[number - 1]

    @property
    def points(self) -> tuple[Cell, ...]:
        """the automatons' homes, by ``automatons.home_tag``: the
        breaches' spawn cells, then the two perches"""
        return (*(b.spawn for b in self.breaches), *self.perches)


def _box(a: Cell, b: Cell) -> set[Cell]:
    return {
        (x, y, z)
        for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1)
        for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1)
        for z in range(min(a[2], b[2]), max(a[2], b[2]) + 1)
    }


def _breach(dome: Dome, number: int, level: str, f0: int, side: int) -> Breach:
    """a frame placed as far out as the dome's curve lets it, against the
    shell, filled in behind with glass"""
    fr = frame(dome)
    inside = domes.dome_cells(dome).interior
    reserved = tunnels.reserved_cells(dome)
    h0 = HOLE_H[level]
    fs, hs = range(f0 - 1, f0 + 3), range(h0 - 1, h0 + 3)
    for depth in range(dome.radius, 8, -1):
        cells = [fr.at(f, side * depth, h) for f in fs for h in hs]
        cells += [fr.at(f, side * (depth - 1), h) for f in fs for h in hs]
        if all(c in inside and c not in reserved for c in cells):
            break
    else:
        raise ValueError(f"no room for breach {number} in {dome.name}")
    holes = tuple(fr.at(f, side * depth, h) for h in (h0, h0 + 1) for f in (f0, f0 + 1))
    ring = tuple(
        fr.at(f, side * depth, h)
        for h in hs
        for f in fs
        if fr.at(f, side * depth, h) not in holes
    )
    backing = {
        fr.at(f, side * d, h)
        for f in fs
        for h in hs
        for d in range(depth + 1, dome.radius + 1)
        if fr.at(f, side * d, h) in inside
    }
    front = frozenset(fr.at(f, side * (depth - 1), h) for f in fs for h in hs)
    bay = {
        fr.at(f, side * d, h)
        for f in range(f0 - 2, f0 + 4)
        for h in range(h0 - 2, h0 + 4)
        for d in (depth - 1, depth)
        if fr.at(f, side * d, h) in inside
    } - set(holes)
    x, y, z = fr.at(f0, side * (depth - 1), h0 + 2)
    # between the hole's two columns, half a block out from the frame
    ax, az = fr.forward
    nx, nz = fr.right[0] * side, fr.right[1] * side
    label = (x + 0.5 + ax * 0.5 + nx * 0.2, y + 0.2, z + 0.5 + az * 0.5 + nz * 0.2)
    spawn_h = {"low": 1, "mid": LEDGE_H + 1, "high": WALK_H + 1}[level]
    return Breach(
        number,
        level,
        side,
        f0,
        h0,
        depth,
        holes,
        ring,
        frozenset(backing),
        front,
        frozenset(bay),
        fr.at(f0, side * (depth - 1), spawn_h),
        label,
    )


@cache
def room(dome: Dome) -> Room:
    fr = frame(dome)
    at = fr.at
    back = fr.facing(-1, 0)
    breaches = tuple(_breach(dome, *spec) for spec in SPECS)
    dressing = tuple(_breach(dome, 0, *spec) for spec in DRESS_SPECS)
    vf, vr = VALVE
    valve_on = fittings.lever(back, True)
    valve_off = fittings.lever(back)
    valve = fittings.input_post(
        at(vf, vr, WALK_H + 1),
        back,
        valve_off,
        VALVE_SIGN,
        "TEST VALVE",
        (ENTITY_TAG,),
    )
    # the compressor's own frame: along the gantry (the dome's r)
    cf = Frame(at(COMPRESSOR[0], COMPRESSOR[1], 0), fr.right, domes.across(fr.right))
    compressor = fittings.torch_clock(
        cf, 0, 0, GANTRY_H + 1, 1, lamps=True, pistons=True, block=COPPER, bed=CUT
    )
    torch = cf.at(1, 0, GANTRY_H + 1)
    tank_lamps = []
    for tf, tr in TANKS:
        for h in (2, 3):
            tank_lamps += [
                at(tf - 1, tr, h),
                at(tf, tr + 1, h),
                at(tf + 1, tr, h),
                at(tf, tr - 1, h),
            ]
    pf, pr = PERCH
    perches = (at(sum(pf) // 2, -sum(pr) // 2, GANTRY_H + 1),) + (
        at(sum(pf) // 2, sum(pr) // 2, GANTRY_H + 1),
    )
    r = dome.radius
    halls = (
        (at(HALL_FS[0][0], -r, 1), at(HALL_FS[0][1], r, WALK_H + 4)),
        (at(HALL_FS[1][0], -r, 1), at(HALL_FS[1][1], r, WALK_H - 1)),
    )
    return Room(
        frame=fr,
        breaches=breaches,
        dressing=dressing,
        gauge=tuple(at(-COLUMN, 0, h) for h in range(1, MAX + 1)),
        board=tuple(at(ENTRY_F, BOARD_R, h) for h in range(1, MAX + 1)),
        stage_lamps=tuple(at(ENTRY_F, sr, sh) for sr, sh in STAGE_LAMPS),
        door=tuple(at(EXIT_F, rr, h) for rr in (-1, 0, 1) for h in (1, 2, 3)),
        valve=valve,
        valve_on=valve_on,
        valve_off=valve_off,
        lectern=at(*LECTERN, 1),
        recall=RECALL,
        compressor=compressor,
        torch=torch,
        perches=perches,
        tank_lamps=tuple(tank_lamps),
        vents=tuple(at(vf_, vr_, 1) for vf_, vr_ in VENTS),
        halls=halls,
        gantry=(at(-6, -LADDER_R, GANTRY_H + 1), at(6, LADDER_R, GANTRY_H + 3)),
    )


# ----------------------------------------------------------- the levels


def scaled(level: int) -> dict[str, int]:
    """the room's values at a level, as the function ``scaled`` works them
    out (``per`` in steps: a layer for one breach open)"""
    timer = game.scaled(level)["#diff.timer"]
    n1, n2, n3 = BURSTS[level]
    b_solo, b_duo = BREACHER_CAP[level]
    r_solo, r_duo = RIVETER_CAP[level]
    return {
        "per": PER_TICKS // STEP * timer // 100,
        "stag": STAGGER * timer // 100,
        "hold0": HOLD * timer // 100,
        "n1": n1,
        "n2": n2,
        "n3": n3,
        "bsolo": b_solo,
        "bduo": b_duo,
        "rsolo": r_solo,
        "rduo": r_duo,
        "wb": int(level in WATER_BREATHING),
    }


# ----------------------------------------------------------- the words

VALVE_SIGN = ("TEST VALVE", "Open it to", "start the", "hull test.")
PLAQUE_SIGNS = (
    ("HULL TEST", "Chamber", f"No. {INDEX}"),
    ("Open the valve.", "Rivet every", "breach: plates", "stick to iron."),
    ("Water rises", "while a breach", "is open. Keep", "above the red."),
)
LOG_TITLE, LOG_AUTHOR = "Hull Test log", "O. Finch"
LOG_PAGES = [
    "Hull Test log\nO. Finch, Chief Engineer\n\nThis chamber proves the hull "
    "before the line to the Signal Room is opened. Raise the pressure in three "
    "stages. Every plate must hold.\n\nLast month every plate held.",
    "Tonight the plates on the outer ring are loose. Not sheared: the rivets "
    "drawn, one at a time, by a careful hand.\n\nI know that hand. I taught "
    "it.\n\nMarsh was here before me.",
    "To pass the test:\n1. Open the TEST VALVE.\n2. Plates will blow. Rivet "
    "new ones into each hole. They hold only in the iron frames.\n3. Hold all "
    "three stages. The pumps do the rest.",
    "Keep above the red line. Things came in with the sea, and they hunt in "
    "the water.\n\nTwo of you? One rivets, one keeps the gantry quiet.\n\nThe "
    "Signal Room is next. Something in there is sending, and it is not us.",
]
PLATE_LORE = ("Sticks only to the", "iron frame of a breach.")


def logbook(fr: Frame, pages=LOG_PAGES) -> str:
    return fittings.lectern_with_book(fr.facing(-1, 0), LOG_TITLE, LOG_AUTHOR, pages)


# ------------------------------------------------------------- the plan


@dataclass
class Blocks:
    """the room's blocks that no state of the test moves"""

    floor: dict[Cell, str] = field(default_factory=dict)  # relaid floor
    solid: dict[Cell, str] = field(default_factory=dict)  # full blocks
    #: blocks that do not fill their cell: stairs, ladders, bars, chains,
    #: pistons, the lectern. Those in the basin are its fittings
    parts: dict[Cell, str] = field(default_factory=dict)
    attached: dict[Cell, str] = field(default_factory=dict)  # need a support
    clear: set[Cell] = field(default_factory=set)  # air, to be kept so
    moving: set[Cell] = field(default_factory=set)  # state changes by itself
    swept: set[Cell] = field(default_factory=set)  # a moving part passes

    def above(self) -> dict[Cell, str]:
        return {**self.solid, **self.parts, **self.attached}

    def everything(self) -> dict[Cell, str]:
        return {**self.floor, **self.above()}

    def add(self, other: Blocks) -> None:
        """take in another set of blocks; no cell may be given twice"""
        mine, theirs = self.everything(), other.everything()
        if both := (set(mine) | self.clear | self.swept) & set(theirs):
            raise ValueError(f"cells given two blocks: {sorted(both)[:5]}")
        self.floor |= other.floor
        self.solid |= other.solid
        self.parts |= other.parts
        self.attached |= other.attached
        self.clear |= other.clear
        self.moving |= other.moving
        self.swept |= other.swept


def ladder(facing: str) -> str:
    return f"{LADDER}[facing={facing},{DRY}]"


def stairs(facing: str) -> str:
    return f"{STAIRS}[facing={facing},half=bottom,shape=straight,{DRY}]"


def _bearing(fr: Frame, deg: float, d: float) -> tuple[int, int]:
    """the place at a bearing (0 forward, 90 right) and a distance"""
    a = math.radians(deg)
    return (round(d * math.cos(a)), round(d * math.sin(a)))


@cache
def walk_places(dome: Dome) -> frozenset[tuple[int, int]]:
    """the ring walk's places (f, r): a band round the chamber between the
    dams, the dams' crests and the exit hall's roof, which it crosses"""
    fr = frame(dome)
    inside = domes.dome_cells(dome).interior
    out = set()
    for f in range(-dome.radius, dome.radius + 1):
        for r in range(-dome.radius, dome.radius + 1):
            if fr.at(f, r, WALK_H) not in inside:
                continue
            if ENTRY_F < f < EXIT_F and WALK_IN <= math.hypot(f, r) <= WALK_OUT:
                out.add((f, r))
            elif f in (ENTRY_F, EXIT_F) or f > EXIT_F:
                out.add((f, r))
    return frozenset(out)


def towers(dome: Dome) -> list[tuple[Cell, str, Cell]]:
    """the ladders from the floor to the ring walk: (the foot's cell, its
    facing, the post it is on). One beside each low breach's frame and one
    up through each ledge, each on a post that carries the walk"""
    place = room(dome)
    fr = place.frame
    out = []
    for b in place.breaches:
        if b.level == "low":
            f, d = b.f0 + 3, round(math.sqrt(18.4**2 - (b.f0 + 3) ** 2))
            post = (f + 1, d)
            face = fr.facing(-1, 0)
        elif b.level == "mid":
            f, d = b.f0 + 1, b.depth - 3
            post = (f + 1, d)
            face = fr.facing(-1, 0)
        else:
            continue
        out.append((fr.at(f, b.side * d, 1), face, fr.at(post[0], b.side * post[1], 1)))
    return out


def structure(dome: Dome) -> Blocks:
    """the chamber: dams, halls, column, walk, ledges, stairs, ladders,
    gantry, perches, the breaches' frames (plates in the holes are the
    state's: ``fixed_blocks``)"""
    place = room(dome)
    fr = place.frame
    at = fr.at
    cells = domes.dome_cells(dome)
    inside = cells.interior
    reserved = tunnels.reserved_cells(dome)
    b = Blocks()
    usable = inside - reserved

    def put(part: dict[Cell, str], cell: Cell, block: str) -> None:
        if cell in usable and cell not in b.everything():
            part[cell] = block

    # -- the floor: dark tiles in the chamber, a lantern every fifth place
    lights = domes.light_cells(dome)[0]
    for c in cells.floor:
        f, r, _ = fr_of(fr, c)
        if c in lights or not ENTRY_F < f < EXIT_F:
            continue
        d = math.hypot(f, r)
        lit = f % 5 == 0 and r % 5 == 0 and d > 3
        ring = any(abs(d - ring_d) < 0.5 for ring_d in FLOOR_RINGS)
        b.floor[c] = LANTERN if lit else CUT if ring else TILES

    # -- the dams: glass, copper ribs every fifth place, the red band at
    # the line, the crest at the walk's height; the board and the stage
    # lamps in the entry dam; the dam door in the exit dam
    for f in (ENTRY_F, EXIT_F):
        for r in range(-dome.radius, dome.radius + 1):
            for h in range(1, WALK_H + 1):
                c = at(f, r, h)
                if c not in inside:
                    continue
                block = COPPER if r % 5 == 0 else GLASS
                if h == MAX:
                    block = RED
                if h == WALK_H:
                    block = CUT
                b.solid[c] = block
    for c in place.door:
        del b.solid[c]
    for h in range(1, WALK_H):
        for r in (BOARD_R - 1, BOARD_R + 1):
            b.solid[at(ENTRY_F, r, h)] = RED if h == MAX else EXPOSED
    for c in place.board:
        b.solid[c] = f"{BULB}[lit=false]"
        b.moving.add(c)
    for c in place.stage_lamps:
        b.solid[c] = f"{BULB}[lit=false]"
        b.moving.add(c)
    # buttresses where the dams meet the shell, under the walk: no pocket
    # of water roofed by the shell, the crest and the walk
    for f in (ENTRY_F + 1, ENTRY_F + 2, EXIT_F - 2, EXIT_F - 1):
        for r in range(-dome.radius, dome.radius + 1):
            if math.hypot(f, r) < WALK_IN:
                continue
            for h in range(1, WALK_H + 1):
                c = at(f, r, h)
                if c in usable:
                    b.solid[c] = CHISELED if h in (3, 7) else WEATHERED_CUT
    # the exit hall's glass roof, which the walk crosses
    for c in inside:
        f, _, h = fr_of(fr, c)
        if f > EXIT_F and h == WALK_H:
            b.solid[c] = GLASS

    # -- the entry hall: the stair up the dam to the valve landing
    fs, foot, top = HALL_STAIR
    for f in fs:
        for r in range(top, foot + 1):
            h = 1 + foot - r
            b.parts[at(f, r, h)] = stairs(fr.facing(0, -1)).replace(f",{DRY}", "")
            for under in range(1, h):
                b.solid[at(f, r, under)] = COPPER if under % 3 else EXPOSED_CUT
    (lf0, lf1), (lr0, lr1) = LANDING
    for f in range(lf0, lf1 + 1):
        for r in range(lr0, lr1 + 1):
            b.solid[at(f, r, WALK_H)] = CUT

    # -- the test column, the gauge on its face, the red band
    for f in range(-COLUMN, COLUMN + 1):
        for r in range(-COLUMN, COLUMN + 1):
            for h in range(1, GANTRY_H):
                block = COPPER
                if h in (4, 13):
                    block = CHISELED
                elif h in (1, 15):
                    block = CUT
                if h == MAX and (f, r) != (0, 0):
                    block = RED
                b.solid[at(f, r, h)] = block
    for c in place.gauge:
        b.solid[c] = f"{BULB}[lit=false]"
        b.moving.add(c)
    # its ladder, on the left face, up to the gantry
    for h in range(1, GANTRY_H + 1):
        b.parts[at(0, -COLUMN - 1, h)] = ladder(fr.facing(0, -1))

    # -- the ring walk: a grating band, the crests, the roof; rails on
    # both edges where it is open (``rails``)
    for f, r in walk_places(dome):
        c = at(f, r, WALK_H)
        if c not in b.solid:
            b.solid[c] = GRATE

    # -- the two stairs from the floor to the walk, in the basin
    for (r0, r1), way in zip(STAIR_RS, (1, -1), strict=True):
        for r in (r0, r1):
            for k in range(WALK_H):
                f, h = way * k, k + 1
                b.parts[at(f, r, h)] = stairs(fr.facing(way, 0))
                for under in range(1, h):
                    b.solid[at(f, r, under)] = WEATHERED if under % 4 else CHISELED
            # a landing from the top tread to the walk
            for k in range(WALK_H, WALK_H + 3):
                c = at(way * k, r, WALK_H)
                if (way * k, r) in walk_places(dome):
                    break
                b.solid[c] = GRATE

    # -- the ladders to the walk, each on a post that carries it
    for foot_, face, post in towers(dome):
        for h in range(1, WALK_H + 1):
            lc = (foot_[0], foot_[1] + h - 1, foot_[2])
            pc = (post[0], post[1] + h - 1, post[2])
            b.solid.pop(lc, None)
            b.parts[lc] = ladder(face)
            if pc not in b.solid or h == WALK_H:
                b.solid[pc] = (
                    LANTERN if h == 7 else GRATE if h == WALK_H else WEATHERED_CUT
                )

    # -- the breaches' frames, their backing; the ledges under the middle
    # ones, decks in front of the high ones
    for br in (*place.breaches, *place.dressing):
        frame_block = FRAME if br.number else DRESS_FRAME
        for c in br.frame:
            b.solid[c] = frame_block
        for c in br.backing:
            b.solid.setdefault(c, GLASS)
        if br.level == "mid":
            # nothing under the frame and its backing for water to stand
            # in with no air over it
            for f in range(br.f0 - 1, br.f0 + 3):
                for d in range(br.depth, dome.radius + 1):
                    for h in (*range(1, br.h0 - 1), *range(br.h0 + 3, MAX + 1)):
                        c = at(f, br.side * d, h)
                        if c in usable and (h < br.h0 or d > br.depth):
                            b.solid.setdefault(c, EXPOSED)
        if not br.number:
            for c in br.holes:
                b.solid[c] = DRESS_PLATE
        if br.level == "mid":
            for f in range(br.f0 - 1, br.f0 + 2):
                for d in range(br.depth - 3, br.depth):
                    c = at(f, br.side * d, LEDGE_H)
                    if c not in b.parts:
                        put(b.solid, c, CUT)
        if br.level == "high":
            for f in range(br.f0 - 1, br.f0 + 3):
                for d in (br.depth - 1, br.depth):
                    c = at(f, br.side * d, WALK_H)
                    b.solid[c] = GRATE

    # -- the ballast tanks, their lamps blinked by the pack
    for tf, tr in TANKS:
        for f in range(tf - 1, tf + 2):
            for r in range(tr - 1, tr + 2):
                for h in range(1, 5):
                    block = WEATHERED if h < 4 else EXPOSED_CUT
                    b.solid[at(f, r, h)] = block
    for c in place.tank_lamps:
        b.solid[c] = f"{TANK_BULB}[lit=false]"
        b.moving.add(c)

    # -- pillars under the walk, lit, where nothing else stands
    for deg in PILLARS:
        f, r = _bearing(fr, deg, 18)
        column = [at(f, r, h) for h in range(1, WALK_H)]
        near = [
            at(f + df, r + dr, h)
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            for h in range(1, WALK_H)
        ]
        if all(c in usable and c not in b.everything() for c in near):
            for h, c in enumerate(column, 1):
                b.solid[c] = LANTERN if h == 6 else OXIDIZED if h % 4 else CHISELED

    # -- the hull's ribs: copper up the inside of the glass, floor to top,
    # wherever nothing else stands against it
    for deg in range(0, 360, RIB_EVERY):
        a = math.radians(deg + RIB_EVERY / 2)
        rib = []
        for h in range(1, dome.radius):
            out = None
            for k in range(dome.radius, 0, -1):
                c = at(round(k * math.cos(a)), round(k * math.sin(a)), h)
                if c in inside:
                    out = c
                    break
            if out is None:
                break
            rib.append(out)
        if all(c in usable and c not in b.everything() for c in rib):
            for c in rib:
                f_, _, h_ = fr_of(fr, c)
                if not ENTRY_F < f_ < EXIT_F and h_ <= WALK_H:
                    continue  # (the halls: their walls are their own)
                b.solid[c] = EXPOSED if fr_of(fr, c)[2] % 6 else LANTERN

    # -- the gantry: a bridge through the hub on the column's head, rails,
    # ladders up from the walk, two perches, the compressor's platform
    for f in range(-2, 3):
        for r in range(-16, 17):
            hub = abs(f) <= COLUMN and abs(r) <= COLUMN
            b.solid[at(f, r, GANTRY_H)] = CHISELED if hub else GRATE
    b.solid.pop(at(0, -COLUMN - 1, GANTRY_H))  # the column's ladder
    for side in (1, -1):
        for h in range(WALK_H + 1, GANTRY_H + 1):
            b.parts[at(0, side * LADDER_R, h)] = ladder(fr.facing(0, -side))
            post = at(0, side * (LADDER_R + 1), h)
            if post in usable and post not in b.everything():
                b.solid[post] = WEATHERED_CUT
        (pf0, pf1), (pr0, pr1) = PERCH
        for f in range(pf0 - 1, pf1 + 1):
            for r in range(pr0 - 1, pr1 + 2):
                rr = side * r
                b.solid.setdefault(at(f, rr, GANTRY_H), CUT)
                b.solid[at(f, rr, GANTRY_H + 3)] = EXPOSED_CUT
                wall = f == pf0 - 1 or r in (pr0 - 1, pr1 + 1)
                for h in (GANTRY_H + 1, GANTRY_H + 2):
                    if wall:
                        b.parts[at(f, rr, h)] = BARS
        # an anvil in each perch, for the riveting's clink
        b.solid[at(pf0, side * pr0, GANTRY_H + 1)] = "minecraft:anvil"
    # the compressor's platform and its cage, lidded
    for f in range(3, 7):
        for r in range(-3, 4):
            b.solid.setdefault(at(f, r, GANTRY_H), CUT)
    for f in range(2, 7):
        for r in range(-3, 4):
            b.solid[at(f, r, GANTRY_H + 3)] = EXPOSED_CUT
            if f in (2, 6) or abs(r) == 3:
                for h in (GANTRY_H + 1, GANTRY_H + 2):
                    b.parts[at(f, r, h)] = BARS
    # the bridge's rails, with a way into each perch and to each ladder
    for f in (-2, 2):
        for r in range(-16, 17):
            perch = f == -2 and PERCH[1][0] <= abs(r) <= PERCH[1][1]
            c = at(f, r, GANTRY_H + 1)
            if not perch and c not in b.parts:
                b.parts[c] = BARS
    for r in (-16, 16):
        for f in (-2, -1, 1, 2):
            put(b.parts, at(f, r + (1 if r > 0 else -1), GANTRY_H + 1), BARS)
    # chains and lanterns under the gantry
    for r in (-12, -6, 6, 12):
        for f in (-2, 2):
            for h in range(GANTRY_H - 3, GANTRY_H):
                b.parts[at(f, r, h)] = CHAIN
            b.parts[at(f, r, GANTRY_H - 4)] = HANGING
    # the valve's post
    b.solid |= place.valve.solid
    b.attached |= {
        c: block for c, block in place.valve.attached.items() if "lever" not in block
    }
    b.attached[place.valve.input] = place.valve_off
    return b


def rails(dome: Dome, b: Blocks) -> dict[Cell, str]:
    """iron bars along every open edge of the walk, the landing and the
    crests, one up, but where a stair or a ladder comes up"""
    fr = frame(dome)
    at = fr.at
    inside = domes.dome_cells(dome).interior
    reserved = tunnels.reserved_cells(dome)
    deck = {
        (f, r)
        for c in b.solid
        for f, r, h in [fr_of(fr, c)]
        if h == WALK_H and _name(b.solid[c]) != GLASS or h == WALK_H and f > EXIT_F
    }
    keep_open = set()
    for c, block in b.parts.items():
        f, r, h = fr_of(fr, c)
        if ("stairs" in block or "ladder" in block) and h <= WALK_H + 1:
            keep_open |= {(f + df, r + dr) for df in (-1, 0, 1) for dr in (-1, 0, 1)}
    out = {}
    for f, r in deck:
        for df, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = (f + df, r + dr)
            if p in deck or p in keep_open:
                continue
            c, under = at(*p, WALK_H + 1), at(*p, WALK_H)
            if c not in inside or c in reserved or c in b.everything():
                continue
            if under in b.everything():
                continue
            out[c] = BARS
    return out


def dressing(dome: Dome) -> Blocks:
    """the compressor (real redstone, run by the pack) and pipes"""
    place = room(dome)
    m = place.compressor
    b = Blocks(solid=dict(m.bed) | dict(m.solid), moving=set(m.moving))
    for cell, block in m.attached.items():
        if cell == place.torch:
            b.clear.add(cell)
        else:
            b.attached[cell] = block
    for cell in m.pistons:
        b.parts[cell] = b.solid.pop(cell)
        b.swept.add((cell[0], cell[1] + 1, cell[2]))
    return b


@cache
def _room_blocks(dome: Dome) -> Blocks:
    b = structure(dome)
    extra = dressing(dome)
    # the compressor's bed is laid in the gantry's deck
    for cell in set(extra.solid) & set(b.solid):
        del b.solid[cell]
    b.add(extra)
    b.add(hall_blocks(dome))
    b.parts |= rails(dome, b)
    return b


def room_blocks(dome: Dome) -> Blocks:
    """Hull Breach's blocks that no state of the test moves (lamps dark,
    the basin's fittings dry, no plate in any hole)"""
    return _room_blocks(dome)


def holds_water(block: str) -> bool:
    """is this block one of the basin's fittings: one water can stand in?"""
    return any(w in block for w in ("stairs", "ladder"))


WATERLOGGABLE = ("slab", "grate", "trapdoor", "fence", "_wall", "pane", "chain")
WATERLOGGABLE += ("stairs", "ladder", "bars", "lightning_rod", "sign", "_door")
WATERLOGGABLE += ("lantern[", "lever", "button", "pressure_plate", "rail", "anvil")


@dataclass(frozen=True)
class Layer:
    """one layer of the basin: the cells that are water or air (the holes'
    among them: a plate is left alone by the fills) and its fittings (cell
    -> block when dry)"""

    h: int
    open: frozenset[Cell]
    fittings: dict[Cell, str]


@cache
def layers(dome: Dome) -> dict[int, Layer]:
    """the basin by height, 1 to ``MAX``"""
    b = room_blocks(dome)
    fr = frame(dome)
    out = {}
    for h in range(1, MAX + 1):
        level = {c for c in basin(dome) if fr_of(fr, c)[2] == h}
        fit = {c: block for c, block in b.parts.items() if c in level}
        out[h] = Layer(h, frozenset(level - set(b.solid) - set(fit)), fit)
    return out


def layer_lines(dome: Dome, h: int, is_wet: bool) -> list[str]:
    """the commands that make a layer of the basin wet, or dry: the rig's
    two forms. Wet: its cells made sources (flowing water too), then its
    fittings waterlogged. Dry: its fittings first, then its water away"""
    layer = layers(dome)[h]
    boxes = domes.boxes(layer.open)
    fit = [
        f"setblock {_xyz(c)} {wet(block, is_wet)}"
        for c, block in sorted(layer.fittings.items())
    ]
    if is_wet:
        lines = []
        for a, z in boxes:
            lines += [
                dp.fill(a, z, WATER, f"replace {WATER}"),
                dp.fill(a, z, WATER, f"replace {AIR}"),
            ]
        return lines + fit
    return fit + [dp.fill(a, z, AIR, f"replace {WATER}") for a, z in boxes]


# ------------------------------------------------------------ the states


@dataclass(frozen=True)
class State:
    """what the scores say of the room: enough to know every block of it"""

    w: int = 0
    stage: int = 0
    open: frozenset[int] = frozenset()  # the breaches open
    lit: int = 0  # the column's gauge (the water)

    @property
    def solved(self) -> bool:
        return self.stage >= 3


START = State()
SOLVED = State(stage=3)
ALL_OPEN = frozenset(range(1, len(SPECS) + 1))


def hole_block(cell_h: int, state: State, is_open: bool) -> str:
    if not is_open:
        return PLATE
    return WATER if cell_h <= state.w else AIR


def fixed_blocks(dome: Dome, state: State = START) -> dict[Cell, str]:
    """
    Every block of the room in a state, but the water and air of the
    basin's open cells (``fluid_blocks``): what stands still, the basin's
    fittings wet or dry, the plates in the holes, the gauges, the stage
    lamps, the dam door. (Not the compressor's torch, which is there while
    the pumps run.)
    """
    place = room(dome)
    b = room_blocks(dome)
    fr = place.frame
    out = b.everything()
    for h, layer in layers(dome).items():
        for cell, block in layer.fittings.items():
            out[cell] = wet(block, h <= state.w)
    for column in (place.gauge, place.board):
        for h, cell in enumerate(column, 1):
            out[cell] = f"{BULB}[lit={'true' if h <= state.w else 'false'}]"
    for k, cell in enumerate(place.stage_lamps, 1):
        out[cell] = f"{BULB}[lit={'true' if k <= state.stage else 'false'}]"
    for br in place.breaches:
        for cell in br.holes:
            h = fr_of(fr, cell)[2]
            out[cell] = hole_block(h, state, br.number in state.open)
    for cell in place.door:
        out[cell] = AIR if state.solved else CHISELED
    if state.solved:
        out[place.valve.input] = place.valve_on
    return out


def fluid_blocks(dome: Dome, state: State = START) -> dict[Cell, str]:
    """the basin's open cells in a state (the holes are ``fixed_blocks``'s):
    water up to its level, air over it"""
    holes = {c for br in room(dome).breaches for c in br.holes}
    out = {}
    for h, layer in layers(dome).items():
        for cell in layer.open - holes:
            out[cell] = WATER if h <= state.w else AIR
    return out


def plan(dome: Dome) -> dict[Cell, str]:
    """the room as built (dry, every breach sound): for the checks of what
    stands where"""
    out = fixed_blocks(dome, START)
    b = room_blocks(dome)
    return {c: block for c, block in out.items() if c not in b.floor and block != AIR}


def inputs(dome: Dome) -> set[Cell]:
    """the valve and the recall post's button"""
    place = room(dome)
    f, r, side = place.recall
    return {place.valve.input, place.frame.at(f, r + side, 2)}


def recall_blocks(dome: Dome) -> tuple[dict[Cell, str], dict[Cell, str]]:
    place = room(dome)
    return fittings.recall_post_blocks(place.frame, *place.recall)


def hall_blocks(dome: Dome) -> Blocks:
    """the entry hall's fittings: the plaque, the lectern, the recall post"""
    place = room(dome)
    fr = place.frame
    side = Frame(fr.origin, (-fr.right[0], -fr.right[1]), fr.forward)
    pr, pf = PLAQUE
    solid, signs = fittings.plaque_blocks(side, -pr, pf, PLAQUE_SIGNS)
    rs, ra = recall_blocks(dome)
    b = Blocks(solid=solid | rs, attached=signs | ra)
    b.parts[place.lectern] = logbook(fr)
    return b


# ------------------------------------------------- walking, climbing, swimming


@cache
def _still(dome: Dome) -> tuple[frozenset[Cell], frozenset[Cell], frozenset[Cell]]:
    """what does not change with the state: blocks to stand on, cells a
    body cannot be in, ladders"""
    b = room_blocks(dome)
    engine = {
        c: block
        for c, block in engine_blocks(dome).items()
        if block != AIR and "rod" not in block
    }
    ground = set(b.solid) | {c for c, block in b.parts.items() if "stairs" in block}
    ground |= set(engine)
    ladders = {c for c, block in b.parts.items() if "ladder" in block}
    full = ground | (set(b.parts) - ladders) | set(b.attached) | b.swept | b.clear
    full |= {c for c, block in engine_blocks(dome).items() if block != AIR}
    return frozenset(ground), frozenset(full), frozenset(ladders)


@cache
def engine_blocks(dome: Dome) -> dict[Cell, str]:
    """the outgoing tunnel's pump engine, in the exit hall (the core's)"""
    cells = tunnels.engine_cells(layout.TUNNELS[dome.index])
    return {cell: tunnels.ENGINE[key] for key, cell in cells.items()}


def shape(dome: Dome, state: State) -> Shape:
    """the room in a state, for a body"""
    place = room(dome)
    cells = domes.dome_cells(dome)
    ground, full, ladders = _still(dome)
    plates = {
        c for br in place.breaches if br.number not in state.open for c in br.holes
    }
    door = set(place.door) if not state.solved else set()
    fr = place.frame
    return Shape(
        inside=cells.interior,
        ground=ground | plates | door,
        floor=cells.floor,
        full=full | plates | door,
        ladders=ladders,
        water=frozenset(c for c in basin(dome) if fr_of(fr, c)[2] <= state.w),
    )


def under(sh: Shape, c: Cell) -> bool:
    """is a body here under water: in water with no air for its head"""
    x, y, z = c
    head = (x, y + 1, z)
    return c in sh.water and (head in sh.water or not sh.free(head))


def checked_states() -> list[State]:
    """the states the routes are proved in: every level of the water, every
    breach open and every breach sound, and the room solved"""
    return [
        *(State(w=w, open=o) for w in range(MAX + 1) for o in (frozenset(), ALL_OPEN)),
        SOLVED,
    ]


def escape_problems(dome: Dome) -> list[str]:
    """
    Nobody drowns and nobody is stranded, in every state of
    ``checked_states``: from every place a player can get to (any fall
    taken), air is within ``MAX_DIVE`` moves, and there is a way back to
    the entry hall that is never more than ``MAX_DIVE`` moves under water
    in a row (a swim under the walk's deck, a dive to a hole).
    """
    entrance = domes.entrance(dome)[:3]
    fr = frame(dome)
    problems = []
    for state in checked_states():
        sh = shape(dome, state)
        places = reach(sh, entrance)
        back: dict[Cell, list[Cell]] = {}
        for c in places:
            for to in sh.moves(c):
                back.setdefault(to, []).append(c)
        # air within MAX_DIVE moves of every place under water
        deep = {c for c in places if under(sh, c)}
        dist = {c: 0 for c in places if c not in deep}
        edge = list(dist)
        while edge:
            nxt = []
            for c in edge:
                for came in back.get(c, ()):
                    if came in deep and came not in dist:
                        dist[came] = dist[c] + 1
                        nxt.append(came)
            edge = nxt
        what = f"the water at {state.w}, {len(state.open)} breaches open"
        if state.solved:
            what = "the room solved"
        if drown := {c for c in deep if dist.get(c, MAX_DIVE + 1) > MAX_DIVE}:
            problems.append(
                f"{what}: {len(drown)} places more than {MAX_DIVE} moves from air, "
                f"e.g. (f, r, h) {fr_of(fr, min(drown))}"
            )
        # home: ``spare`` is how many more moves under water a body there
        # may already have taken and still get home (a place's own move
        # under counted); worked out from the entrance, the most first
        spare = {entrance: MAX_DIVE}
        buckets: list[list[Cell]] = [[] for _ in range(MAX_DIVE + 1)]
        buckets[MAX_DIVE].append(entrance)
        for left in range(MAX_DIVE, -1, -1):
            while buckets[left]:
                c = buckets[left].pop()
                if spare[c] != left:
                    continue
                for came in back.get(c, ()):
                    can = left - 1 if c in deep else MAX_DIVE
                    if can > spare.get(came, -1):
                        spare[came] = can
                        buckets[can].append(came)
        if lost := set(places) - set(spare):
            problems.append(
                f"{what}: no way back to the entrance from {len(lost)} places "
                f"with at most {MAX_DIVE} moves under water in a row, e.g. "
                f"(f, r, h) {fr_of(fr, min(lost))}"
            )
    return problems


def headroom_problems(dome: Dome) -> list[str]:
    """every wet cell of the top layer is within two cells (along the
    layer) of a wet cell with air over it, at every level of the water"""
    sh = shape(dome, State(w=MAX))
    fr = frame(dome)
    problems = []
    for w in range(1, MAX + 1):
        top = set(layers(dome)[w].open) | set(layers(dome)[w].fittings)
        aired = {c for c in top if sh.free((c[0], c[1] + 1, c[2]))}
        bad = []
        for x, y, z in top:
            if not any(
                (x + dx, y, z + dz) in aired
                for dx in range(-2, 3)
                for dz in range(-2, 3)
                if abs(dx) + abs(dz) <= 2
            ):
                bad.append((x, y, z))
        if bad:
            problems.append(
                f"the water at {w}: {len(bad)} cells with no air within two, "
                f"e.g. (f, r, h) {fr_of(fr, min(bad))}"
            )
    return problems


def basin_problems(dome: Dome) -> list[str]:
    """
    The basin is closed: every cell of it that is water (or a hole's) or a
    fitting has, on each side and below, another such cell or a full block
    that holds no water (the room's, the shell, the floor, the dam door),
    so water has nowhere to run; the halls and the mouths' ways in hold no
    basin cell; every fitting says whether it is waterlogged; no lever,
    button, plate, sign or other waterloggable block stands in the basin
    but the fittings.
    """
    cells = domes.dome_cells(dome)
    b = room_blocks(dome)
    place = room(dome)
    fr = place.frame
    holes = {c for br in place.breaches for c in br.holes}
    full = {c for c, block in b.solid.items() if not _waterloggable(block)}
    full |= cells.shell | cells.floor | set(place.door)
    problems = []
    for h, layer in layers(dome).items():
        mine = layer.open | set(layer.fittings)
        below = set()
        if h > 1:
            lower = layers(dome)[h - 1]
            below = lower.open | set(lower.fittings)
        for x, y, z in mine:
            for dx, dz in domes.COMPASS:
                if (side := (x + dx, y, z + dz)) not in mine and side not in full:
                    problems.append(f"the basin leaks sideways at {fr_of(fr, side)}")
            if (down := (x, y - 1, z)) not in below and down not in full:
                problems.append(f"the basin leaks down at {fr_of(fr, down)}")
        for cell, block in layer.fittings.items():
            if not holds_water(block) or DRY not in block:
                problems.append(f"{block} at {fr_of(fr, cell)} is no fitting")
    for cell, block in b.everything().items():
        if cell in basin(dome) and cell not in b.floor:
            if _waterloggable(block) and not holds_water(block):
                problems.append(
                    f"{_name(block)} at {fr_of(fr, cell)}: in the basin, and not "
                    "written by its layer"
                )
            if rooms.is_input(block) or "sign" in block:
                problems.append(f"{_name(block)} at {fr_of(fr, cell)} in the basin")
    if not holes <= basin(dome) | {
        c for br in place.breaches if br.level == "high" for c in br.holes
    }:
        problems.append("a low or middle hole is not in the basin")
    halls = set()
    for lo, hi in place.halls:
        halls |= _box(lo, hi)
    if taken := basin(dome) & (halls | tunnels.reserved_cells(dome)):
        problems.append(f"{len(taken)} cells of the basin in a hall or a way in")
    return problems[:12]


def _waterloggable(block: str) -> bool:
    return any(w in block for w in WATERLOGGABLE)


def breach_problems(dome: Dome) -> list[str]:
    """every hole cell touches two frame blocks and has glass or the shell
    behind it; every bay holds no other breach's hole, no input and no
    sign; a Breacher is cast in the room, in front of its hole"""
    place = room(dome)
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    problems = []
    holes = {c for br in place.breaches for c in br.holes}
    sh = shape(dome, State(open=ALL_OPEN))
    for br in place.breaches:
        frames = set(br.frame)
        for x, y, z in br.holes:
            touching = sum(
                (x + dx, y + dy, z + dz) in frames for dx, dy, dz in rooms.FACES
            )
            if touching != 2:
                problems.append(
                    f"{br.name}: a hole cell touches {touching} frame blocks"
                )
            fr = place.frame
            nx, nz = fr.right[0] * br.side, fr.right[1] * br.side
            behind = (x + nx, y, z + nz)
            if behind not in cells.shell and b.solid.get(behind) != GLASS:
                problems.append(f"{br.name}: no glass behind a hole cell")
        if other := (br.bay & holes) - set(br.holes):
            problems.append(f"{br.name}: another hole in its bay at {min(other)}")
        for c in br.bay:
            block = b.everything().get(c, "")
            if rooms.is_input(block) or "sign" in block:
                problems.append(f"{br.name}: {_name(block)} in its bay")
        if br.spawn in br.holes or not sh.stands(br.spawn):
            problems.append(f"{br.name}: its Breacher is not cast on its feet")
    return problems


def walks(dome: Dome) -> dict[str, Cell]:
    """where a player must be able to get to from the entrance, by any
    way, in the room as built (dry, the dam door shut)"""
    place = room(dome)
    at = place.frame.at
    out = {
        "the valve": at(VALVE[0] - 1, VALVE[1] + 1, WALK_H + 1),
        "the logbook": at(LECTERN[0] - 1, LECTERN[1], 1),
        "the recall post": at(RECALL[0], RECALL[1] + 2 * RECALL[2], 1),
        "the gantry": at(0, 8, GANTRY_H + 1),
        "a perch": place.perches[0],
    }
    for br in place.breaches:
        out[br.name] = br.spawn
    return out


def walk_problems(dome: Dome) -> list[str]:
    """
    Every place of ``walks`` can be got to (by foot, ladder and stair)
    from the entrance in the room as built; the way out (through the dam
    door to the outgoing tunnel's pump lever) once solved; and there is no
    pit: nowhere a player can get to and not get back from, as dry
    (``dome_foundry.pits``: falls of any height, ladders both ways, rails
    stood on)
    """
    place = room(dome)
    problems = []
    entrance = domes.entrance(dome)[:3]
    built = reach(shape(dome, START), entrance)
    problems += [
        f"no way from the entrance to {name}"
        for name, cell in walks(dome).items()
        if cell not in built
    ]
    out = layout.TUNNELS[dome.index]
    ux, uz = domes.outward(dome, out)
    lx, ly, lz = tunnels.lever_cell(out)
    by_lever = (lx - ux, ly - 1, lz - uz)
    solved = reach(shape(dome, SOLVED), entrance)
    ox, oy, oz = dome.floor_centre
    mouth = (ox + ux * (dome.radius - 3), oy + 1, oz + uz * (dome.radius - 3))
    for name, cell in (("the pump lever", by_lever), ("the way out", mouth)):
        if cell not in solved:
            problems.append(f"solved: no way from the entrance to {name}")
    if set(built) & _box(*place.halls[1]):
        problems.append("the exit hall can be got into before the solve")
    b = room_blocks(dome)
    ground, full, ladders = _still(dome)
    plates = {c for br in place.breaches for c in br.holes}
    door = set(place.door)
    stand = (
        set(ground)
        | plates
        | door
        | {c for c, block in b.parts.items() if "bars" in block}
    )
    blocked = (set(full) | plates | door) - stand
    if stuck := pits(dome, stand, set(ladders), blocked):
        f_ = fr_of(place.frame, min(stuck))
        problems.append(f"{len(stuck)} cells with no way out, as (f, r, h) {f_}")
    return problems


@cache
def _room_problems(dome: Dome) -> tuple[str, ...]:
    try:
        b = room_blocks(dome)
    except ValueError as e:
        return (str(e),)
    place = room(dome)
    used = set(b.above()) | b.clear | b.swept | set(place.door)
    used |= {c for br in place.breaches for c in br.holes}
    problems = fittings.placement_problems(dome, used)
    more = (b.clear | b.swept) - set(b.above())
    blocks = plan(dome)
    problems += rooms.room_problems(dome, blocks, b.floor, more)
    problems += rooms.input_problems(blocks, inputs(dome), floor=b.floor)
    if set(b.floor) & domes.light_cells(dome)[0]:
        problems.append("the relaid floor covers one of the dome's lanterns")
    problems += rooms.window_problems(dome, plan(dome))
    problems += basin_problems(dome)
    problems += breach_problems(dome)
    problems += headroom_problems(dome)
    problems += walk_problems(dome)
    problems += escape_problems(dome)
    return tuple(problems)


def forget() -> None:
    """drop what is remembered of the plan (for a test that changes it)"""
    for remembered in (_room_blocks, layers, _still, _room_problems):
        remembered.cache_clear()


def room_problems(dome: Dome) -> list[str]:
    """the room's plan against its dome and against itself (see the
    module docstring): none, or the build refuses to run"""
    return list(_room_problems(dome))


# --------------------------------------------------------------- the build


def plate_base() -> str:
    """a rivet plate before it is marked lent"""
    return fittings.restricted(
        PLATE, place_on=FRAME, name="Rivet plate", lore=PLATE_LORE
    )


def labels(dome: Dome) -> list[str]:
    """the commands that summon the room's text displays: a BREACH label
    over each breach (empty while it is sound), the valve's label, the
    test board's"""
    place = room(dome)
    fr = place.frame
    out = list(place.valve.summons)
    for br in place.breaches:
        out.append(
            fittings.display(
                (ENTITY_TAG, br.tag), br.label, 0, label_text(""), 1.0, "center"
            )
        )
    yaw = {"south": 0, "west": 90, "north": 180, "east": -90}[fr.facing(-1, 0)]
    x, y, z = fr.at(ENTRY_F - 1, 0, STAGE_LAMPS[0][1] + 1)
    ax, az = fr.forward
    out.append(
        fittings.display(
            (ENTITY_TAG, STAGE_TAG),
            (x + 0.5 + ax * 0.45, y + 0.1, z + 0.5 + az * 0.45),
            yaw,
            label_text("STAGE  1  2  3"),
            0.6,
        )
    )
    x, y, z = fr.at(ENTRY_F - 1, BOARD_R, MAX)
    out.append(
        fittings.display(
            (ENTITY_TAG,),
            (x + 0.5 + ax * 0.45, y + 0.25, z + 0.5 + az * 0.45),
            yaw,
            label_text("FLOOD LINE", "red", bold="true"),
            0.5,
        )
    )
    return out


def book_commands(dome: Dome) -> list[str]:
    """the logbook on its lectern, a page a command: RCON takes a short
    command only"""
    place = room(dome)
    at = _xyz(place.lectern)
    return [
        f"setblock {at} {AIR}",
        f"setblock {at} {logbook(place.frame, LOG_PAGES[:1])}",
        *(
            f"data modify block {at} {fittings.BOOK_PAGES} append value {snbt(page)}"
            for page in LOG_PAGES[1:]
        ),
    ]


def build(ctx: Any) -> str:
    """Hull Breach inside its shell: drains and wipes what was inside but
    the pump engine, builds the room dry with every breach sound, and
    leaves it as ``reset`` does. Run it after the tunnels' stages"""
    dome = ctx.layout.DOMES[INDEX]
    if problems := room_problems(dome):
        raise RuntimeError("Hull Breach: " + "; ".join(problems))
    place = room(dome)
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    engine = set(engine_blocks(dome))
    ctx.cmd(f"kill @e[tag={ENTITY_TAG}]")
    ctx.cmd(automatons.remove_line(INDEX))
    for command in game.clear_stub_commands(dome):
        ctx.cmd(command)
    # an old flood goes from the top, so nothing runs
    for h in range(MAX, 0, -1):
        for line in layer_lines(dome, h, False):
            ctx.cmd(line)
    ctx.fill_boxes(cells.interior - engine, AIR)
    for part in (b.floor, b.solid, b.parts, b.attached):
        for block, where in sorted(domes.by_block(part).items()):
            if "{" not in block and TORCH not in block:
                ctx.fill_boxes(where, block)
        for cell, block in sorted(part.items()):
            if "{" in block and cell != place.lectern:
                ctx.setblock(cell, block)  # (signs; the book is below)
    for br in place.breaches:
        for cell in br.holes:
            ctx.setblock(cell, PLATE)
    ctx.fill_boxes(set(place.door), CHISELED)
    for command in book_commands(dome):
        ctx.cmd(command)
    for command in labels(dome):
        ctx.cmd(command)
    ctx.cmd(fittings.summon_recall(place.frame, *place.recall, tags=(ENTITY_TAG,)))
    # the pack's own idea of the room, if the pack is installed
    ctx.function(f"dome/{INDEX}/reset")
    ctx.advance(10)
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    return (
        f"{dome.name}: {len(b.everything())} blocks: the entry hall (stair, valve "
        "landing, plaque, logbook, recall post, test board), two glass dams, "
        "the test column and its gauge, the ring walk, three ledges, two stairs "
        "and seven ladders, nine breaches and three dressing frames, the gantry "
        "with two perches and the compressor, the ballast tanks"
    )


# ----------------------------------------------------------- the functions


def _s(name: str) -> str:
    return f"#hb.{name} {OBJ}"


def _set(name: str, value: int) -> str:
    return f"scoreboard players set {_s(name)} {value}"


def _op(name: str, op: str, other: str) -> str:
    return f"scoreboard players operation {_s(name)} {op} {other} {OBJ}"


def _is(name: str, what: int | str) -> str:
    return f"if score {_s(name)} matches {what}"


def _not(name: str, what: int | str) -> str:
    return f"unless score {_s(name)} matches {what}"


def _setblock(cell: Cell, block: str) -> str:
    return f"setblock {_xyz(cell)} {block}"


def _if_block(cell: Cell, block: str) -> str:
    return f"if block {_xyz(cell)} {block}"


def breacher_kind() -> automatons.Kind | None:
    """the Breacher as ``BREACHER_MODE`` has it (None: no Breachers)"""
    return {
        "trident": automatons.BREACHER,
        "melee": BREACHER_MELEE,
        "none": None,
    }[BREACHER_MODE]


#: the scores a new game has, all 0 (``b<i>`` too)
ZEROED = (
    "state", "stage", "phase", "w", "flow", "open", "due", "idx", "next",
    "hold", "t", "wait", "again", "cast", "rclk", "klax", "slow", "wbt",
    "deco", "deco.t", "tick",
)  # fmt: skip


def functions(pack: dp.Pack) -> None:
    """Hull Breach's functions (see the module docstring)"""
    dome = layout.DOMES[INDEX]
    place = room(dome)
    fr = place.frame
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    open_dome = f"#d{INDEX} {OBJ}"
    mobs = automatons.selector(INDEX)
    kind = breacher_kind()
    riveter = automatons.RIVETER
    pack.objectives({OBJ: "dummy", domes.CHECK_OBJECTIVE: "dummy"})
    pack.constants(OBJ, 100)
    lit, dark = f"{BULB}[lit=true]", f"{BULB}[lit=false]"
    key = f"{KEY}{INDEX}"
    column = place.gauge[MAX // 2]

    def fid(name: str) -> str:
        return pack.id(f"{base}/{name}")

    def call(name: str) -> str:
        return f"function {fid(name)}"

    def sound(name: str, cell: Cell, volume: float = 1, pitch: float = 1) -> str:
        return (
            f"playsound minecraft:{name} block {here} {middle(cell)} {volume} {pitch}"
        )

    def say(text: str, colour: str = "yellow") -> str:
        return f'tellraw {here} {{text:{snbt(text)},color:"{colour}"}}'

    def title(text: str, sub: str, colour: str = "gold") -> list[str]:
        return [
            f"title {here} times 5 50 10",
            f'title {here} subtitle {{text:{snbt(sub)},color:"yellow"}}',
            f'title {here} title {{text:{snbt(text)},color:"{colour}"}}',
        ]

    def fx(name: str, at: str, spread: str, speed: float, n: int) -> str:
        """a particle through the macro ``fx``: a name this version does
        not know costs one effect, not the function (the Foundry's way)"""
        return (
            f'{call("fx")} {{p:"minecraft:{name}",at:"{at}",'
            f'd:"{spread}",s:"{speed:g}",n:{n}}}'
        )

    pack.function(f"{base}/fx", ["$particle $(p) $(at) $(d) $(s) $(n)"])
    bar = automatons.bar(pack, INDEX, "Hull test", MAX, "blue", "notched_10")

    # -- the values of the level in force, and the caps of the form
    scale = [
        _op("k", "=", "#diff.timer"),
        _set("per", PER_TICKS // STEP),
        _op("per", "*=", "#hb.k"),
        _op("per", "/=", "#100"),
        _set("stag", STAGGER),
        _op("stag", "*=", "#hb.k"),
        _op("stag", "/=", "#100"),
        _set("hold0", HOLD),
        _op("hold0", "*=", "#hb.k"),
        _op("hold0", "/=", "#100"),
        _set("cgap", CAST_GAP),
        _op("cgap", "*=", "#hb.k"),
        _op("cgap", "/=", "#100"),
    ]
    for level in game.LEVELS:
        values = scaled(level)
        when = f"execute if score #active {OBJ} matches {level} run"
        scale += [
            f"{when} {_set(name, values[name])}"
            for name in ("n1", "n2", "n3", "bsolo", "bduo", "rsolo", "rduo", "wb")
        ]
    pack.function(f"{base}/scaled", [*scale, call("caps")])
    pack.function(
        f"{base}/caps",
        [
            _op("bcap", "=", "#hb.bsolo"),
            _op("rcap", "=", "#hb.rsolo"),
            f"execute {_is('form', 2)} run {_op('bcap', '=', '#hb.bduo')}",
            f"execute {_is('form', 2)} run {_op('rcap', '=', '#hb.rduo')}",
        ],
    )

    # -- the water: a layer wet, a layer dry; a layer up, a layer down
    for h in range(1, MAX + 1):
        pack.function(f"{base}/layer_{h}/wet", layer_lines(dome, h, True))
        pack.function(f"{base}/layer_{h}/dry", layer_lines(dome, h, False))
    pack.function(
        f"{base}/rise",
        [
            *(
                f"execute {_is('w', h - 1)} run {call(f'layer_{h}/wet')}"
                for h in range(1, MAX + 1)
            ),
            f"scoreboard players add {_s('w')} 1",
            _op("flow", "-=", "#hb.per"),
            call("gauge"),
            sound("block.bubble_column.upwards_inside", column, 2, 0.6),
            sound("block.fire.extinguish", column, 0.5, 0.5),
        ],
    )
    pack.function(
        f"{base}/fall",
        [
            *(
                f"execute {_is('w', h)} run {call(f'layer_{h}/dry')}"
                for h in range(1, MAX + 1)
            ),
            f"scoreboard players remove {_s('w')} 1",
            call("gauge"),
            sound("block.bubble_column.whirlpool_inside", column, 2, 0.8),
        ],
    )

    # -- the breaches: open (by its layer), shut (plates), the labels
    for br in place.breaches:
        i = br.number
        open_lines, burst_lines = [], []
        for cell in br.holes:
            h = fr_of(fr, cell)[2]
            if h > MAX:
                open_lines.append(_setblock(cell, AIR))
                burst_lines.append(f"{_setblock(cell, AIR)} destroy")
                continue
            for wet_, block in ((True, WATER), (False, AIR)):
                when = _is("w", f"{h}..") if wet_ else _not("w", f"{h}..")
                open_lines.append(f"execute {when} run {_setblock(cell, block)}")
                burst_lines.append(
                    f"execute {when} run {_setblock(cell, block)} destroy"
                )
        pack.function(f"{base}/hole/{i}/open", open_lines)
        pack.function(
            f"{base}/hole/{i}/shut", [_setblock(cell, PLATE) for cell in br.holes]
        )
        mark = fittings.display_selector(br.tag)
        pack.function(
            f"{base}/label/{i}/on",
            [
                fittings.text_line(br.tag, label_text("BREACH", "red", bold="true")),
                f"data merge entity {mark} {{see_through:1b}}",
            ],
        )
        pack.function(
            f"{base}/label/{i}/off",
            [
                fittings.text_line(br.tag, label_text("")),
                f"data merge entity {mark} {{see_through:0b}}",
            ],
        )
        x, y, z = br.holes[2]
        top = f"{x + 0.5} {y + 1.1} {z + 0.5}"
        pack.function(
            f"{base}/burst/{i}",
            [
                f"execute {_is(f'b{i}', 1)} run return 0",
                _set(f"b{i}", 1),
                *burst_lines,
                call(f"label/{i}/on"),
                sound("block.glass.break", br.holes[0], 2, 0.6),
                sound("entity.generic.explode", br.holes[0], 0.6, 1.4),
                sound("block.anvil.land", br.holes[0], 1, 0.5),
                fx("splash", top, "0.6 0.4 0.6", 0.3, 40),
                f"execute {_is('phase', '1..2')} run {call(f'cast_at/{i}')}",
                *title(
                    "BREACH",
                    f"On the {LEVEL_NAMES[br.level]}, the "
                    f"{'right' if br.side > 0 else 'left'} wall",
                    "red",
                ),
            ],
        )
        bodies = dp.box_selector(min(br.holes), max(br.holes))
        pack.function(
            f"{base}/seal/{i}",
            [
                _set(f"b{i}", 0),
                call(f"label/{i}/off"),
                sound("block.anvil.use", br.holes[0], 1.5, 1.2),
                sound("block.note_block.bell", br.holes[0], 1.5, 1.4),
                fx("wax_on", top, "0.6 0.6 0.6", 0.5, 12),
            ],
        )
        # made sound again, never on a body in the hole (it waits)
        pack.function(
            f"{base}/plug/{i}",
            [
                f"execute if entity @e[tag=st.in,{bodies}] run return 0",
                f"execute if entity {automatons.selector(INDEX, bodies)} run return 0",
                call(f"hole/{i}/shut"),
                _set(f"b{i}", 0),
                call(f"label/{i}/off"),
            ],
        )
    pack.function(
        f"{base}/holes",
        [
            line
            for br in place.breaches
            for line in (
                f"execute {_is(f'b{br.number}', 1)} run {call(f'hole/{br.number}/open')}",
                f"execute {_not(f'b{br.number}', 1)} run {call(f'hole/{br.number}/shut')}",
                f"execute {_is(f'b{br.number}', 1)} run {call(f'label/{br.number}/on')}",
                f"execute {_not(f'b{br.number}', 1)} run "
                + call(f"label/{br.number}/off"),
            )
        ],
    )
    pack.function(
        f"{base}/restore_stage",
        [
            f"execute {_is(f'b{br.number}', 1)} run {call(f'plug/{br.number}')}"
            for br in place.breaches
        ],
    )

    # -- what the room shows: the gauges, the stage lamps, the door
    gauge = []
    for cells_ in (place.gauge, place.board):
        gauge += fittings.gauge_lines(cells_, _s("w"), 1, lit, dark)
    gauge += fittings.gauge_lines(place.stage_lamps, _s("stage"), 1, lit, dark)
    gauge.append(bar.value_line(_s("w")))
    pack.function(f"{base}/gauge", gauge)
    door = []
    for a, z in domes.boxes(set(place.door)):
        door += [
            f"execute {_is('state', 2)} run {dp.fill(a, z, AIR)}",
            f"execute {_not('state', 2)} run {dp.fill(a, z, CHISELED)}",
        ]
    pack.function(f"{base}/door", door)
    # the whole room from the scores: the reset and the repair
    draw = []
    for h in range(1, MAX + 1):
        draw += [
            f"execute {_is('w', f'{h}..')} run {call(f'layer_{h}/wet')}",
            f"execute {_not('w', f'{h}..')} run {call(f'layer_{h}/dry')}",
        ]
    draw += [call("holes"), call("gauge"), call("door")]
    pack.function(f"{base}/draw", draw)

    # -- the compressor: it runs while a torch is in its clock
    torch = place.compressor.attached[place.torch]
    pack.function(
        f"{base}/pumps_on",
        [
            f"execute unless block {_xyz(place.torch)} {TORCH} "
            f"run {_setblock(place.torch, torch)}"
        ],
    )
    pack.function(
        f"{base}/pumps_off",
        [f"execute {_if_block(place.torch, TORCH)} run {_setblock(place.torch, AIR)}"],
    )

    # -- the valve: thrown, it starts the test, and stays thrown
    pack.function(
        f"{base}/valve",
        [
            f"execute {_is('state', 0)} "
            f"{_if_block(place.valve.input, 'minecraft:lever[powered=true]')} "
            f"run {call('start')}",
            fittings.lever_hold_line(
                place.valve.input, place.valve_on, _is("state", "1..")
            ),
        ],
    )
    pack.function(
        f"{base}/start",
        [
            # on Peaceful the game takes every automaton as it is cast
            f"function {pack.id('fight/difficulty')}",
            f"execute if score #difficulty {OBJ} matches 0 run {call('refuse')}",
            f"execute if score #difficulty {OBJ} matches 0 run return 0",
            _set("state", 1),
            _set("stage", 0),
            _set("again", 0),
            _set("wait", 0),
            sound("block.iron_door.open", place.valve.input, 2, 0.5),
            sound("block.beacon.activate", column, 3, 0.5),
            bar.show,
            call("start_stage"),
        ],
    )
    pack.function(
        f"{base}/refuse",
        [
            *fittings.lever_put_lines(place.valve.input, place.valve_off),
            say("The hull test will not run while the world is Peaceful.", "gray"),
        ],
    )

    # -- a stage: its bursts, the first at once (two with two players)
    pack.function(
        f"{base}/start_stage",
        [
            f"execute {_not('state', 1)} run return 0",
            _op("form", "=", "#hb.want"),
            call("scaled"),
            *(
                f"execute {_is('stage', s)} run {_op('due', '=', f'#hb.n{s + 1}')}"
                for s in range(3)
            ),
            f"execute {_is('form', 2)} run scoreboard players add {_s('due')} 1",
            *(_set(name, 0) for name in ("idx", "flow", "hold", "t", "klax", "wait")),
            _set("phase", 1),
            *(
                f"execute {_is('stage', s)} run "
                + bar.name_line(f'"Hull test: stage {s + 1} of 3"')
                for s in range(3)
            ),
            *(
                f"execute {_is('stage', s)} {_is('again', 0)} run {line}"
                for s in range(3)
                for line in title(
                    f"STAGE {s + 1}", "Rivet every breach. Keep above the red line."
                )
            ),
            *(
                f"execute {_is('stage', s)} {_is('again', 1)} run {line}"
                for s in range(3)
                for line in title(f"STAGE {s + 1}: AGAIN", "The pumps are clear.")
            ),
            _set("again", 0),
            sound("block.bell.use", column, 2, 0.6),
            call("burst_next"),
            f"execute {_is('form', 2)} run {call('burst_next')}",
            _op("next", "=", "#hb.stag"),
            _op("cast", "=", "#hb.cgap"),
            _set("rclk", 0),
            call("riveters"),
            call("riveters"),
            call("gauge"),
        ],
    )
    nexts = [
        f"execute {_is('stage', s)} {_is('idx', j)} run {call(f'burst/{i}')}"
        for s, order in enumerate(ORDERS)
        for j, i in enumerate(order)
    ]
    pack.function(
        f"{base}/burst_next",
        [
            f"execute {_is('due', '..0')} run return 0",
            *nexts,
            f"scoreboard players add {_s('idx')} 1",
            f"scoreboard players remove {_s('due')} 1",
        ],
    )
    pack.function(
        f"{base}/bursts",
        [
            f"scoreboard players remove {_s('next')} {STEP}",
            f"execute {_is('next', '..0')} {_is('due', '1..')} run {call('burst_next')}",
            f"execute {_is('next', '..0')} run {_op('next', '=', '#hb.stag')}",
        ],
    )

    # -- reading the holes: four plates seal one
    read = [_set("open", 0)]
    for br in place.breaches:
        i = br.number
        plated = " ".join(_if_block(c, PLATE) for c in br.holes)
        read += [
            f"execute {_is(f'b{i}', 1)} {plated} run {call(f'seal/{i}')}",
            f"execute {_is(f'b{i}', 1)} run scoreboard players add {_s('open')} 1",
        ]
    read.append(
        f"execute {_is('phase', '1..2')} {_is('open', 0)} {_is('due', '..0')} "
        f"run {call('held')}"
    )
    pack.function(f"{base}/read", read)

    # -- the water's logic
    pack.function(
        f"{base}/water",
        [
            # one phase a step: a phase that ends starts the next one's
            # work only at the next step
            f"execute {_is('phase', 1)} run return run {call('water/rising')}",
            f"execute {_is('phase', 2)} run return run {call('water/line')}",
            f"execute {_is('phase', 3)} run return run {call('water/pumping')}",
            f"execute {_is('phase', 0)} run return run {call('water/breather')}",
        ],
    )
    pack.function(
        f"{base}/water/rising",
        [
            _op("flow", "+=", "#hb.open"),
            f"execute {_not('w', f'{MAX}..')} if score {_s('flow')} >= {_s('per')} "
            f"run {call('rise')}",
            f"execute {_is('w', f'{MAX}..')} run {_set('flow', 0)}",
            f"execute {_is('w', f'{MAX}..')} {_is('open', '1..')} run {call('warn')}",
        ],
    )
    pack.function(
        f"{base}/warn",
        [
            _set("phase", 2),
            _op("hold", "=", "#hb.hold0"),
            _set("klax", 0),
            *title("HULL FAILING", "Seal the breaches!", "red"),
            "bossbar set " + bar.id + " color red",
        ],
    )
    pack.function(
        f"{base}/water/line",
        [
            f"execute {_is('open', 0)} run {_set('phase', 1)}",
            f"execute {_is('open', 0)} run bossbar set {bar.id} color blue",
            f"execute {_is('open', 0)} run return 0",
            f"scoreboard players remove {_s('hold')} {STEP}",
            f"scoreboard players add {_s('klax')} {STEP}",
            f"execute {_is('klax', '20..')} run {call('klaxon')}",
            f"execute {_is('hold', '..0')} run {call('fail')}",
        ],
    )
    pack.function(
        f"{base}/klaxon",
        [
            _set("klax", 0),
            sound("block.bell.use", column, 3, 0.5),
            sound("block.note_block.bass", column, 3, 0.5),
            f'title {here} actionbar {{text:"HULL FAILING",color:"red",bold:true}}',
        ],
    )
    pack.function(
        f"{base}/water/pumping",
        [
            call("restore_stage"),
            f"scoreboard players add {_s('t')} {STEP}",
            f"execute {_is('t', f'{PUMP_TICKS}..')} {_is('w', '1..')} run {call('fall')}",
            f"execute {_is('t', f'{PUMP_TICKS}..')} run {_set('t', 0)}",
            f"execute {_is('w', '..0')} run {call('pumped')}",
        ],
    )
    pack.function(
        f"{base}/water/breather",
        [
            f"scoreboard players remove {_s('t')} {STEP}",
            f"execute {_is('t', '..0')} run {call('start_stage')}",
        ],
    )
    pack.function(
        f"{base}/held",
        [
            f"scoreboard players add {_s('stage')} 1",
            *(
                f"execute {_is('stage', s + 1)} run {line}"
                for s in range(3)
                for line in title(f"STAGE {s + 1} HOLDS", "The pumps are clearing it.")
            ),
            f"execute at {mobs} run particle minecraft:bubble_pop ~ ~1 ~ 0.3 0.6 0.3 0.05 20",
            automatons.remove_line(INDEX),
            sound("block.note_block.bell", column, 3, 0.8),
            sound("block.beacon.power_select", column, 2, 0.8),
            call("pumping"),
        ],
    )
    pack.function(
        f"{base}/fail",
        [
            *title("BLOW THE BALLAST", "The stage is put back. Try again.", "red"),
            f"execute at {mobs} run particle minecraft:bubble_pop ~ ~1 ~ 0.3 0.6 0.3 0.05 20",
            automatons.remove_line(INDEX),
            _set("again", 1),
            _set("due", 0),
            sound("block.beacon.deactivate", column, 3, 0.6),
            call("pumping"),
            call("restore_stage"),
        ],
    )
    pack.function(
        f"{base}/pumping",
        [
            _set("phase", 3),
            _set("t", 0),
            _set("flow", 0),
            call("pumps_on"),
            f"bossbar set {bar.id} color blue",
            call("gauge"),
        ],
    )
    pack.function(
        f"{base}/pumped",
        [
            call("pumps_off"),
            f"execute {_is('stage', '3..')} run return run {call('done')}",
            _set("phase", 0),
            _set("t", BREATHER),
            say("The chamber is clear. A breath, then the next stage."),
        ],
    )
    pack.function(
        f"{base}/done",
        [f"function {pack.id(f'dome/{INDEX}/solved')}", call("restored")],
    )
    # the room once solved: dry, sound, the dam door open, nothing lent
    pack.function(
        f"{base}/restored",
        [
            _set("state", 2),
            _set("stage", 3),
            *(_set(n, 0) for n in ("phase", "w", "flow", "due", "wait", "hold")),
            *(_set(f"b{br.number}", 0) for br in place.breaches),
            automatons.remove_line(INDEX),
            call("pumps_off"),
            call("draw"),
            fittings.lever_hold_line(place.valve.input, place.valve_on),
            fittings.take_back_line(key, here),
            f"effect clear {here} minecraft:water_breathing",
            bar.hide,
        ],
    )

    # -- the automatons
    pack.function(
        f"{base}/temper",
        [
            f"execute as {mobs} run attribute @s minecraft:follow_range base set 40",
            f"effect give {mobs} minecraft:fire_resistance 3600 0 true",
        ],
    )
    count = (
        f"execute store result score {_s('alive')} if entity "
        + automatons.selector(INDEX, f"tag={automatons.BREACHER.tag}")
    )
    for k, br in enumerate(place.breaches):
        i = br.number
        if kind is None:
            pack.function(f"{base}/cast_at/{i}", ["return 0"])
            continue
        pack.function(
            f"{base}/cast_one/{i}",
            [
                count,
                f"execute if score {_s('alive')} >= {_s('bcap')} run return 0",
                automatons.summon_kind(
                    kind, middle(br.spawn), INDEX, (automatons.home_tag(k), ENTITY_TAG)
                ),
                automatons.dress_kind_line(INDEX, kind),
                call("temper"),
                fx("bubble_column_up", middle(br.spawn, 0.5), "0.4 0.8 0.4", 0.1, 30),
            ],
        )
        pack.function(
            f"{base}/cast_at/{i}",
            [
                call(f"cast_one/{i}"),
                f"execute {_is('form', 2)} run {call(f'cast_one/{i}')}",
            ],
        )
    near = {
        br.number: f"x={middle(br.spawn).split()[0]},y={br.spawn[1]},"
        f"z={middle(br.spawn).split()[2]},distance=..{NEAR}"
        for br in place.breaches
    }
    pack.function(
        f"{base}/cast/again",
        [
            _op("cast", "=", "#hb.cgap"),
            *(
                f"execute {_is(f'b{i}', 1)} if entity @e[tag=st.in,{sel}] "
                f"run {call(f'cast_one/{i}')}"
                for i, sel in near.items()
            ),
        ],
    )
    perch_tags = [automatons.home_tag(len(place.breaches) + k) for k in (0, 1)]
    rivs = automatons.selector(INDEX, f"tag={riveter.tag}")
    pack.function(
        f"{base}/riveters",
        [
            f"execute store result score {_s('ralive')} if entity {rivs}",
            f"execute if score {_s('ralive')} >= {_s('rcap')} run return 0",
            *(
                f"execute unless entity {automatons.selector(INDEX, f'tag={tag}')} "
                f"run return run {call(f'perch/{k}')}"
                for k, tag in enumerate(perch_tags)
            ),
            call("perch/0"),
        ],
    )
    for k, (cell, tag) in enumerate(zip(place.perches, perch_tags, strict=True)):
        pack.function(
            f"{base}/perch/{k}",
            [
                automatons.summon_kind(riveter, middle(cell), INDEX, (tag, ENTITY_TAG)),
                automatons.dress_kind_line(INDEX, riveter),
                call("temper"),
                sound("block.anvil.place", cell, 1, 0.8),
            ],
        )
    pack.function(
        f"{base}/cast",
        [
            f"scoreboard players remove {_s('cast')} {STEP}",
            f"execute {_is('cast', '..0')} run {call('cast/again')}",
            f"execute store result score {_s('ralive')} if entity {rivs}",
            f"execute if score {_s('ralive')} < {_s('rcap')} "
            f"run scoreboard players add {_s('rclk')} {STEP}",
            f"execute {_is('rclk', f'{RIVETER_GAP}..')} run {_set('rclk', 0)}",
            f"execute {_is('rclk', 0)} if score {_s('ralive')} < {_s('rcap')} "
            f"run {call('riveters')}",
        ],
    )
    # the leash (the dome), the gantry for the Riveters, and the halls:
    # an automaton found in either hall goes home
    fence = automatons.leash_lines(INDEX, place.points, domes.sphere(dome))
    lo, hi = place.gantry
    for k, tag in enumerate(perch_tags):
        fence.append(
            f"execute as {automatons.selector(INDEX, f'tag={tag}')} "
            f"unless entity @s[{dp.box_selector(lo, hi)}] "
            f"run tp @s {middle(place.perches[k])}"
        )
    for a, z in place.halls:
        hall = dp.box_selector(a, z)
        fence += [
            f"execute as {automatons.selector(INDEX, f'tag={automatons.home_tag(k)}')} "
            f"if entity @s[{hall}] run tp @s {middle(point)}"
            for k, point in enumerate(place.points)
        ]
    pack.function(f"{base}/fence", fence)

    # -- stray plates round a frame cleared: to water or air by the layer
    strays = []
    for br in place.breaches:
        rows: dict[int, set[Cell]] = {}
        for c in br.bay:
            rows.setdefault(fr_of(fr, c)[2], set()).add(c)
        for h, row in sorted(rows.items()):
            for a, z in domes.boxes(row):
                if h > MAX:
                    strays.append(dp.fill(a, z, AIR, f"replace {PLATE}"))
                    continue
                strays += [
                    f"execute {_is('w', f'{h}..')} run "
                    + dp.fill(a, z, WATER, f"replace {PLATE}"),
                    f"execute {_not('w', f'{h}..')} run "
                    + dp.fill(a, z, AIR, f"replace {PLATE}"),
                ]
    pack.function(f"{base}/strays", strays)
    sphere = domes.sphere(dome)
    lent_items = (
        f"kill @e[type=minecraft:item,{sphere},"
        f'nbt={{Item:{{components:{{"minecraft:custom_data":{{{fittings.LENT}:"{key}"}}}}}}}}]'
    )
    tridents = f"kill @e[type=minecraft:trident,{sphere}]"
    pack.function(
        f"{base}/sweep",
        [
            f"kill @e[type=minecraft:trident,nbt={{inGround:1b}},{sphere}]",
            *automatons.sweep_lines(dome),
        ],
    )
    # the spray over each open breach: falling water while its layer is
    # dry, bubbles while it is wet, and a hiss
    spray = []
    for br in place.breaches:
        i = br.number
        x, y, z = br.holes[2]
        top = f"{x + 0.5} {y + 0.9} {z + 0.5}"
        h = fr_of(fr, br.holes[2])[2]
        is_open = _is(f"b{i}", 1)
        spray += [
            f"execute {is_open} {_not('w', f'{h}..')} run "
            + fx("falling_water", top, "0.5 0.2 0.5", 0, 8),
            f"execute {is_open} {_not('w', f'{h}..')} run "
            + fx("splash", top, "0.5 0.3 0.5", 0.2, 10),
            f"execute {is_open} {_is('w', f'{h}..')} run "
            + fx("bubble", top, "0.5 0.5 0.5", 0.2, 12),
            f"execute {is_open} run {sound('block.fire.extinguish', br.holes[2], 0.4, 1.6)}",
        ]
    pack.function(f"{base}/spray", spray)
    pack.function(
        f"{base}/slow",
        [
            _set("slow", 0),
            f"execute if score {open_dome} matches 1 run "
            + fittings.lend_again_line(INDEX, plate_base(), key, PLATES),
            call("strays"),
            call("fence"),
            call("sweep"),
            call("spray"),
            f"scoreboard players add {_s('wbt')} {SLOW}",
            f"execute {_is('wbt', '100..')} {_is('wb', 1)} {_is('state', 1)} run "
            f"effect give {here} minecraft:water_breathing 10 0 true",
            f"execute {_is('wbt', '100..')} run {_set('wbt', 0)}",
        ],
    )

    # -- the machinery that only ticks: the tanks' lamps, the vents, the
    # perches' clink
    for k in range(DECO_PHASES):
        pack.function(
            f"{base}/deco/p{k}",
            [
                _setblock(
                    cell,
                    f"{TANK_BULB}[lit={'true' if (j + k) % DECO_PHASES < 2 else 'false'}]",
                )
                for j, cell in enumerate(place.tank_lamps)
            ],
        )
    turn = [
        _set("deco.t", 0),
        f"scoreboard players add {_s('deco')} 1",
        f"execute {_is('deco', f'{DECO_PHASES}..')} run {_set('deco', 0)}",
        *(
            f"execute {_is('deco', k)} run {call(f'deco/p{k}')}"
            for k in range(DECO_PHASES)
        ),
        f"execute {_is('deco', 0)} run "
        + sound("block.anvil.use", place.perches[0], 0.3, 1.6),
        f"execute {_is('deco', 3)} run "
        + sound("block.anvil.use", place.perches[1], 0.3, 1.5),
    ]
    for cell in place.vents:
        turn += [
            f"execute {_is('w', '1..')} run particle minecraft:bubble_column_up "
            f"{middle(cell, 0.2)} 0.2 0.6 0.2 0.02 10",
            f"execute {_not('w', '1..')} run particle minecraft:cloud "
            f"{middle(cell, 0.2)} 0.3 0.1 0.3 0.01 2",
        ]
    pack.function(f"{base}/deco/turn", turn)
    pack.function(
        f"{base}/deco",
        [
            f"scoreboard players add {_s('deco.t')} 1",
            f"execute {_is('deco.t', '5..')} run {call('deco/turn')}",
            # a log taken from the lectern is put back
            f"execute {_if_block(place.lectern, 'minecraft:lectern[has_book=false]')} "
            f"run {call('book')}",
        ],
    )
    pack.function(f"{base}/book", [_setblock(place.lectern, logbook(fr))])

    # -- a step, and the hooks
    fighting = f"{_is('state', 1)} {_is('wait', 0)}"
    pack.function(
        f"{base}/step",
        [
            call("valve"),
            f"execute {fighting} run {call('read')}",
            f"execute {fighting} {_is('phase', '1..2')} run {call('bursts')}",
            f"execute {fighting} run {call('water')}",
            f"execute {fighting} {_is('phase', '1..2')} run {call('cast')}",
            f"scoreboard players add {_s('slow')} {STEP}",
            f"execute {_is('slow', f'{SLOW}..')} run {call('slow')}",
        ],
    )
    pack.function(
        f"{base}/tick",
        [
            f"scoreboard players add {_s('tick')} 1",
            f"execute {_not('tick', f'{STEP}..')} run return 0",
            _set("tick", 0),
            call("deco"),
            f"execute unless score {open_dome} matches 1 run return 0",
            # a room never set up (the pack reloaded)
            f"execute {_not('live', 1)} run {call('arm')}",
            # found solved by the guard while its tunnel is pumping or open:
            # solved; dried by a tunnel's check that has since reset the
            # tunnel: set up anew
            f"execute {_is('state', 2)} if score {tunnels.score(INDEX)} "
            f"matches 1.. run return run {call('done')}",
            f"execute {_is('state', 2)} run return run {call('reset')}",
            f"execute {_is('state', 1)} {_is('wait', '1..')} run {call('waiting')}",
            call("step"),
        ],
    )
    pack.function(
        f"{base}/waiting",
        [
            f"scoreboard players remove {_s('wait')} {STEP}",
            f"execute {_is('wait', '..0')} run {call('resume')}",
        ],
    )
    pack.function(
        f"{base}/resume",
        [
            # (a safe point: a level voted meanwhile is taken)
            _set("wait", 0),
            bar.show,
            call("start_stage"),
        ],
    )
    first = f"if score #first {OBJ} matches 1"
    is_open = f"if score {open_dome} matches 1"
    idle = _not("state", "1..")
    pack.function(
        f"{base}/enter",
        [
            fittings.take_back_line(key),
            f"execute {is_open} run " + fittings.lend_line(plate_base(), key, PLATES),
            f"execute {is_open} {first} {idle} run {call('arm')}",
            f"execute {is_open} {first} {_is('state', 1)} run {_set('wait', RESUME)}",
            f"execute {is_open} {idle} run tellraw @s "
            '{text:"A pressure chamber, dry for now. The brass plaque says how the '
            'test runs. You are given rivet plates.",color:"gray",italic:true}',
            f"execute {is_open} {_is('state', 1)} run tellraw @s "
            '{text:"The hull test is waiting: the stage starts again in a moment.",'
            'color:"gray",italic:true}',
            f"execute if score {open_dome} matches 2 {first} run {call('restored')}",
        ],
    )
    pack.function(
        f"{base}/zero",
        [
            *(_set(name, 0) for name in ZEROED),
            *(_set(f"b{br.number}", 0) for br in place.breaches),
            _set("form", 1),
            _set("want", 1),
            f"execute if score #form{INDEX} {OBJ} matches 2 run {_set('want', 2)}",
            f"execute if score #form{INDEX} {OBJ} matches 2 run {_set('form', 2)}",
        ],
    )
    pack.function(
        f"{base}/arm",
        [call("reset"), _set("live", 1)],
    )
    pack.function(
        f"{base}/checkpoint",
        [
            # (the core has just removed the automatons; nobody is in)
            *(call(f"hole/{br.number}/shut") for br in place.breaches),
            *(_set(f"b{br.number}", 0) for br in place.breaches),
            *(_set(n, 0) for n in ("w", "flow", "due", "phase", "hold", "t")),
            _set("wait", -1),
            call("pumps_off"),
            call("draw"),
            bar.hide,
        ],
    )
    pack.function(
        f"{base}/empty",
        [
            f"execute {_is('state', 1)} run {call('checkpoint')}",
            lent_items,
            tridents,
        ],
    )
    pack.function(f"{base}/duo", [_set("want", 2)])
    # one of two gone mid-stage: bursts beyond the solo count struck off
    pack.function(
        f"{base}/solo",
        [
            _set("want", 1),
            f"execute {_is('state', 1)} {_is('form', 2)} {_is('phase', '1..2')} "
            f"run {call('strike')}",
        ],
    )
    pack.function(
        f"{base}/strike",
        [
            *(
                f"execute {_is('stage', s)} run {_op('k', '=', f'#hb.n{s + 1}')}"
                for s in range(3)
            ),
            _op("k", "-=", "#hb.idx"),
            f"execute if score {_s('k')} matches ..-1 run {_set('k', 0)}",
            _op("due", "<", "#hb.k"),
            _set("form", 1),
            call("caps"),
            say("One engineer now: the rest of this stage's breaches hold."),
        ],
    )
    pack.function(f"{base}/died", [say("The water does not wait.", "red")])
    pack.function(
        f"{base}/leave",
        [
            fittings.take_back_line(key),
            "effect clear @s minecraft:water_breathing",
        ],
    )
    # whoever opens the outgoing tunnel, the basin is dry first
    pack.function(
        f"{base}/guard",
        [
            f"execute if score {tunnels.score(INDEX)} matches 1.. {_is('w', '1..')} "
            f"run {call('restored')}",
            f"execute if score {tunnels.score(INDEX, '.ready')} matches 1 "
            f"{_is('w', '1..')} run {call('restored')}",
        ],
        tick=True,
    )
    pack.function(
        f"{base}/reset",
        [
            call("zero"),
            call("scaled"),
            automatons.remove_line(INDEX),
            *(call(f"hole/{br.number}/shut") for br in place.breaches),
            call("pumps_off"),
            call("draw"),
            call("strays"),
            *fittings.lever_put_lines(place.valve.input, place.valve_off),
            lent_items,
            tridents,
            fittings.take_back_line(key, game.PLAYERS),
            bar.hide,
            f"bossbar set {bar.id} color blue",
            call("book"),
        ],
    )

    # -- the check's counts, a function a layer
    ran = f"scoreboard players add #ran {domes.CHECK_OBJECTIVE} 1"
    for h, layer in layers(dome).items():
        lines = domes.row_lines(pack, layer.open, "hbasin")
        lines += domes.row_lines(pack, set(layer.fittings), "hbasinfit")
        pack.function(f"check/dome/{INDEX}/layer_{h}", [*lines, ran])


#: what ``station:check/dome/<n>/layer_<h>`` counts (``#hb_<name>`` in the
#: checks' objective): open cells that are water, sources, air, air with
#: water over it, plates (in the holes); fittings that are wet
COUNTS = ("water", "source", "air", "under", "plate", "fit")


def _count(name: str) -> str:
    return f"run scoreboard players add #hb_{name} {domes.CHECK_OBJECTIVE} 1"


domes.ROW_FAMILIES["hbasin"] = (
    f"execute if block ~%k ~ ~ {WATER} {_count('water')}",
    f"execute if block ~%k ~ ~ {WATER}[level=0] {_count('source')}",
    f"execute if block ~%k ~ ~ {AIR} {_count('air')}",
    f"execute if block ~%k ~ ~ {AIR} if block ~%k ~1 ~ {WATER} {_count('under')}",
    f"execute if block ~%k ~ ~ {PLATE} {_count('plate')}",
)
domes.ROW_FAMILIES["hbasinfit"] = (
    f"execute positioned ~%k ~ ~ if predicate {domes.WET} {_count('fit')}",
)


def expected(dome: Dome, state: State = START) -> dict[str, int]:
    """what the basin's count reads in a state"""
    place = room(dome)
    fr = place.frame
    sound_holes = {
        c for br in place.breaches if br.number not in state.open for c in br.holes
    }
    out: dict[str, int] = dict.fromkeys(COUNTS, 0)
    for h, layer in layers(dome).items():
        for c in layer.open:
            if c in sound_holes:
                out["plate"] += 1
            elif h <= state.w:
                out["water"] += 1
                out["source"] += 1
            else:
                out["air"] += 1
        if h <= state.w:
            out["fit"] += len(layer.fittings)
    del fr
    return out


# --------------------------------------------------------------- the check

S1, S2 = "st.hb1", "st.hb2"


def falling_trident(at: str, tag: str) -> str:
    """a trident dropped half a block over the floor: it lands and sticks
    as a thrown one does (one summoned ``inGround`` off a block is loosed
    the next tick)"""
    return f'summon minecraft:trident {at} {{Motion:[0.0,-1.0,0.0],Tags:["{tag}"]}}'


def counts(ctx: Any) -> dict[str, int | None]:
    """the basin counted in the world (``COUNTS``); ``ran`` is how many of
    the layers' functions ran whole"""
    obj = domes.CHECK_OBJECTIVE
    for name in COUNTS:
        ctx.set_score(f"#hb_{name}", 0, obj)
    ctx.set_score("#ran", 0, obj)
    for h in range(1, MAX + 1):
        ctx.function(f"check/dome/{INDEX}/layer_{h}")
    got = {name: ctx.score(f"#hb_{name}", obj) for name in COUNTS}
    got["ran"] = ctx.score("#ran", obj)
    return got


def check(ctx: Any) -> list[str]:
    """
    Work Hull Breach in place over RCON, nobody online (``hull_breach``).
    It refuses while a run is in progress (``game_checks.no_run``); the
    level is put back (``save_level``) and the stand-ins and automatons
    killed whatever happens. A player is stood in for by an armour stand
    that the core counts (``game.STANDIN``); the valve is thrown and plates
    are riveted by setting the blocks as a hand would leave them. Leaves
    the room and its outgoing tunnel reset, and the dome's and the next
    dome's scores, ``#solved`` and the level as it found them.

    What stand-ins and block reads cannot prove, and so is not claimed: a
    hand placing a plate (``can_place_on`` in an adventure hand: the
    owner's bench); any walk, climb or swim (``escape_problems`` and
    ``walk_problems``, on the plan alone); that a Breacher fights, throws
    its trident or targets anyone (the rig, ``hull_breach_rig``); Water
    Breathing on a player; anything aimed at players: titles, chat,
    sounds, particles, the bossbar as seen.
    """
    game_checks.no_run(ctx)
    saved_level = game_checks.save_level(ctx)
    try:
        return _check(ctx)
    finally:
        ctx.cmd(f"kill @e[tag={S1}]")
        ctx.cmd(f"kill @e[tag={S2}]")
        ctx.cmd(automatons.remove_line(INDEX))
        game_checks.restore_level(ctx, saved_level)
        ctx.function("difficulty/apply")


def _check(ctx: Any) -> list[str]:
    dome = ctx.layout.DOMES[INDEX]
    place = room(dome)
    b = room_blocks(dome)
    fr = place.frame
    problems: list[str] = []
    base = f"dome/{INDEX}"
    scan = game_checks.SCAN
    fall_back = game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan
    kind = breacher_kind()

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def get(name: str) -> int:
        return ctx.score(f"#hb.{name}") or 0

    def opened() -> frozenset[int]:
        return frozenset(br.number for br in place.breaches if get(f"b{br.number}"))

    def state() -> State:
        return State(w=get("w"), stage=get("stage"), open=opened())

    outside = middle(tunnels.at(ctx.layout.TUNNELS[INDEX - 1], 8, 0, 1))
    entrance = middle(domes.entrance(dome)[:3])

    def come_in(tag: str = S1) -> None:
        """a stand-in out of the dome and in again: a new entry"""
        game_checks.stand_at(ctx, tag, outside)
        ctx.advance(game_checks.EMPTY)
        game_checks.stand_at(ctx, tag, entrance)

    def as_state(what: str, want: State | None = None) -> None:
        """every block of the room as the state has it (a lamp or a moving
        part: the same block in whatever state), and the basin by count"""
        want = want or state()
        # (the valve is thrown while the test runs)
        moving = b.moving | {place.valve.input}
        wrong = [
            cell
            for cell, block in fixed_blocks(dome, want).items()
            if not ctx.is_block(
                cell, _name(block) if cell in moving else block.partition("{")[0]
            )
            and not (cell in moving and ctx.is_block(cell, "minecraft:moving_piston"))
        ]
        if wrong:
            problems.append(f"{what}: {len(wrong)} blocks not as planned: {wrong[:6]}")
        expect(
            f"{what}: the basin's count",
            counts(ctx),
            expected(dome, want) | {"ran": MAX},
        )

    def plate(number: int) -> None:
        for cell in place.breach(number).holes:
            ctx.setblock(cell, PLATE)

    def until(test, ticks: int, step: int = STEP) -> bool:
        waited = 0
        while not test() and waited < ticks:
            ctx.advance(step)
            waited += step
        return test()

    def breachers(more: str = "") -> int:
        tag = automatons.BREACHER.tag
        return ctx.count(
            automatons.selector(INDEX, f"tag={tag}{',' + more if more else ''}")
        )

    def riveters() -> int:
        return ctx.count(automatons.selector(INDEX, f"tag={automatons.RIVETER.tag}"))

    def near(cell: Cell, reach: float = 2.5) -> str:
        x, y, z = cell
        return f"x={x + 0.5},y={y},z={z + 0.5},distance=..{reach}"

    # ---- before: nobody about, the room and its tunnel reset, the dome open
    names = (f"#d{INDEX}", f"#d{INDEX + 1}", "#solved")
    saved = game_checks.scores(ctx, *names)
    others = [
        f"#d{d.index}" for d in ctx.layout.DOMES if d.index not in (INDEX, INDEX + 1)
    ]
    others += [f"#t{t.index}" for t in ctx.layout.TUNNELS if t.index != INDEX]
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(fall_back)
    if (n := ctx.score("#players")) or ctx.score(f"#form{INDEX}"):
        return [f"{n} players or stand-ins of another check are in the game"]
    before = game_checks.scores(ctx, *others)

    def unsolve() -> None:
        ctx.function(f"tunnel/{INDEX}/reset")
        ctx.function(f"{base}/reset")
        ctx.set_score(f"#d{INDEX}", 1)
        ctx.set_score(f"#d{INDEX + 1}", saved[f"#d{INDEX + 1}"] or 0)
        ctx.set_score("#solved", saved["#solved"] or 0)
        ctx.advance(4)

    unsolve()
    ctx.set_score("#level", game.DEFAULT_LEVEL)
    as_state("built", START)
    problems += [f"built: {p}" for p in domes.check_shell(ctx, dome, False)]
    expect(
        "the labels",
        ctx.count(f"@e[type=minecraft:text_display,tag={ENTITY_TAG}]"),
        len(labels(dome)),
    )
    recall = (
        f"@e[type=minecraft:interaction,tag={ENTITY_TAG},tag={fittings.RECALL_TAG}]"
    )
    expect("the recall post's interaction entity", ctx.count(recall), 1)
    if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("the logbook is not on the lectern")
    still = all(
        not ctx.is_block(c, "minecraft:piston[extended=true]")
        for c in place.compressor.pistons
    )
    expect("the compressor still with nobody in", still, True)

    # ---- arming: a stand-in comes in; the level's values
    come_in()
    values = {
        k: get(k)
        for k in ("per", "stag", "hold0", "n1", "n2", "n3", "bcap", "rcap", "wb")
    }
    want = scaled(game.DEFAULT_LEVEL)
    want_values = {k: want[k] for k in ("per", "stag", "hold0", "n1", "n2", "n3", "wb")}
    want_values |= {"bcap": want["bsolo"], "rcap": want["rsolo"]}
    expect("armed: the level's values", values, want_values)
    expect("armed: idle, live", (get("state"), get("live")), (0, 1))

    # ---- the valve: the test starts, the first breach bursts
    first = ORDERS[0][0]
    ctx.setblock(place.valve.input, place.valve_on)
    ctx.advance(2 * STEP)
    expect(
        "the valve thrown: state, stage, phase",
        (get("state"), get("stage"), get("phase")),
        (1, 0, 1),
    )
    expect("the first burst", opened(), frozenset({first}))
    br1 = place.breach(first)
    expect("its holes open", all(ctx.is_block(c, AIR) for c in br1.holes), True)
    text = ctx.data(f"entity {fittings.display_selector(br1.tag)} text")
    expect("its label reads BREACH", "BREACH" in text, True)
    if kind is not None:
        expect("a Breacher cast in front of it", breachers(near(br1.spawn)), 1)
        mob = automatons.selector(INDEX, f"tag={automatons.BREACHER.tag},limit=1")
        got = {
            k: ctx.data(f"entity {mob} {k}").rstrip("bf")
            for k in ("IsBaby", "CanPickUpLoot", "PersistenceRequired")
        }
        expect(
            "the Breacher dressed",
            got,
            {"IsBaby": "0", "CanPickUpLoot": "0", "PersistenceRequired": "1"},
        )
        if kind is automatons.BREACHER:
            expect(
                "its trident",
                "trident" in ctx.data(f"entity {mob} equipment.mainhand.id"),
                True,
            )
    expect("a Riveter at a perch", riveters(), get("rcap"))
    ctx.setblock(place.valve.input, place.valve_off)
    ctx.advance(2 * STEP)
    expect("the valve held over", ctx.is_block(place.valve.input, place.valve_on), True)

    # ---- the water rising: a layer every ``per`` steps with one breach open
    # (the next burst held off: the game runs on between the reads)
    ctx.set_score("#hb.next", 10**6)
    per = get("per") * STEP
    ctx.advance(per + 2 * STEP)
    expect("a layer up after per", get("w"), 1)
    as_state("the water at 1")
    # strays: a plate in front of the frame, dry; one in the hole stays
    front = max(br1.front, key=lambda c: c[1])  # above the water
    ctx.setblock(front, PLATE)
    ctx.setblock(br1.holes[0], PLATE)
    ctx.advance(SLOW + STEP)
    expect("a stray plate cleared to air", ctx.is_block(front, AIR), True)
    expect("a plate in the hole kept", ctx.is_block(br1.holes[0], PLATE), True)
    # the breach still open with three of four
    expect("three plates of four: still open", get(f"b{first}"), 1)

    # ---- the line: every breach open, the water held at MAX, the hold
    for br in place.breaches:
        ctx.function(f"{base}/burst/{br.number}")
    ctx.set_score("#hb.w", MAX - 1)
    ctx.function(f"{base}/draw")
    if not until(lambda: get("phase") == 2, 3 * per):
        problems.append(
            f"at the line with breaches open: phase {get('phase')}, w {get('w')}"
        )
    expect("the water at the line", get("w"), MAX)
    hold = get("hold")
    ctx.advance(20)
    # (20 or a few more: the game runs on between the reads)
    expect("the hold counting", 20 <= hold - get("hold") <= 30, True)
    as_state("at the line, every breach open")
    problems += [f"at the line: {p}" for p in domes.check_shell(ctx, dome, False)]
    # saved in time: every hole plated, the stage goes on (a burst still
    # to come, so that it is not held)
    ctx.set_score("#hb.due", 1)
    for br in place.breaches:
        plate(br.number)
    ctx.advance(2 * STEP)
    expect("sealed in time: no breach open", opened(), frozenset())
    # ---- the failure: one open, the hold run out, a body in a hole
    low = next(br for br in place.breaches if br.level == "low")
    ctx.set_score("#hb.due", 1)
    ctx.set_score("#hb.phase", 1)
    ctx.function(f"{base}/burst/{low.number}")
    # (half up: a marker's hitbox is a point, and one on the box's floor
    # is not in it)
    game_checks.stand_at(ctx, S1, middle(low.holes[0], 0.5))
    if not until(lambda: get("phase") == 3, get("hold0") + 4 * per):
        problems.append(f"the hold run out: phase {get('phase')}")
    expect("failed: automatons gone", ctx.count(automatons.selector(INDEX)), 0)
    expect("the hole with a body in it waits", get(f"b{low.number}"), 1)
    expect("the pumps running", ctx.is_block(place.torch, TORCH), True)
    game_checks.stand_at(ctx, S1, entrance)
    ctx.advance(2 * STEP)
    expect("plated the step after it is empty", get(f"b{low.number}"), 0)
    if not until(lambda: get("w") == 0, (MAX + 2) * PUMP_TICKS):
        problems.append(f"the pumps did not empty the room: w {get('w')}")
    ctx.advance(2 * STEP)
    expect("the breather", (get("phase"), get("stage")), (0, 0))
    as_state("pumped dry")
    if not until(lambda: get("phase") == 1, BREATHER + 4 * STEP):
        problems.append("the stage did not start again after the breather")
    expect(
        "stage 1 again, its first breach",
        (get("stage"), opened()),
        (0, frozenset({first})),
    )

    # ---- the mobs: the cap over a while; the fences; the trident sweep
    if kind is not None:
        for br in place.breaches:
            ctx.function(f"{base}/burst/{br.number}")
        for _ in range(6):
            ctx.set_score("#hb.cast", 1)
            ctx.advance(2 * STEP)
        expect("the Breachers' cap held", breachers() <= get("bcap"), True)
        mob = automatons.selector(INDEX, f"tag={automatons.BREACHER.tag},limit=1")
        hall = middle(fr.at(-20, 6, 1))
        ctx.cmd(f"tp {mob} {hall}")
        ctx.advance(SLOW + STEP)
        expect(
            "a Breacher in the hall sent home",
            ctx.count(automatons.selector(INDEX, near(fr.at(-20, 6, 1), 2))),
            0,
        )
    rmob = automatons.selector(INDEX, f"tag={automatons.RIVETER.tag},limit=1")
    ctx.cmd(f"tp {rmob} {middle(fr.at(0, 8, 1))}")
    ctx.advance(SLOW + STEP)
    on_gantry = automatons.selector(
        INDEX, f"tag={automatons.RIVETER.tag},{dp.box_selector(*place.gantry)}"
    )
    expect("a Riveter off the gantry put back", ctx.count(on_gantry), riveters())
    ctx.cmd(falling_trident(middle(fr.at(3, 3, 1), 0.5), S2))
    ctx.advance(2 * SLOW + STEP)
    expect("a trident stuck in the floor swept", ctx.count(f"@e[tag={S2}]"), 0)

    # ---- the checkpoint: everyone out mid-stage, back in
    for br in place.breaches:
        plate(br.number)
    ctx.advance(2 * STEP)
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.advance(game_checks.EMPTY)
    got = (
        get("state"),
        get("wait"),
        get("w"),
        opened(),
        ctx.count(automatons.selector(INDEX)),
    )
    expect("left: waiting, dry, sound, no automatons", got, (1, -1, 0, frozenset(), 0))
    expect(
        "the valve still thrown", ctx.is_block(place.valve.input, place.valve_on), True
    )
    # back, two of them: the stage starts again 5 s later, duo
    game_checks.stand_at(ctx, S1, entrance)
    game_checks.stand_at(ctx, S2, entrance)
    ctx.advance(RESUME + 4 * STEP)
    expect("back: the stage going on", (get("wait"), get("phase")), (0, 1))
    expect("duo: two burst together", opened(), frozenset(ORDERS[0][:2]))
    expect("duo: the caps", (get("bcap"), get("rcap")), (want["bduo"], want["rduo"]))
    due = get("due")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(fall_back)
    expect(
        "one gone: solo, the extra burst struck off",
        (get("form"), get("due")),
        (1, max(0, min(due, want["n1"] - 2))),
    )

    # ---- the end: every stage held
    for stage in range(3):
        ctx.set_score("#hb.stage", stage)
        ctx.set_score("#hb.due", 0)
        ctx.set_score("#hb.phase", 1)
        for number in opened():
            plate(number)
        ctx.advance(2 * STEP)
        if not until(
            lambda s=stage: get("stage") > s and get("phase") != 3,
            (MAX + 2) * PUMP_TICKS + 4 * STEP,
        ):
            problems.append(f"stage {stage + 1} not held: phase {get('phase')}")
        if stage < 2:
            ctx.set_score("#hb.t", 1)
            ctx.advance(2 * STEP)
            for br in place.breaches:
                plate(br.number)
            ctx.advance(2 * STEP)
    expect("solved", (ctx.score(f"#d{INDEX}"), get("state")), (2, 2))
    problems += game_checks.pull_pump(ctx, INDEX)
    as_state("solved", SOLVED)
    second = ctx.count(automatons.selector(INDEX))
    come_in()
    expect(
        "a second entry casts nothing", ctx.count(automatons.selector(INDEX)), second
    )
    # the guard: water while the tunnel's pump runs is taken away at once
    ctx.set_score("#hb.w", 3)
    ctx.function(f"{base}/draw")
    ctx.advance(2)
    expect("the guard dried it", get("w"), 0)

    # ---- the levels' values
    for level in (1, 10):
        ctx.set_score("#level", level)
        ctx.function("difficulty/apply")
        ctx.function(f"{base}/scaled")
        got = {k: get(k) for k in ("per", "stag", "hold0", "n1", "n2", "n3", "wb")}
        want_l = scaled(level)
        expect(f"level {level}'s values", got, {k: want_l[k] for k in got})
    ctx.set_score("#level", game.DEFAULT_LEVEL)
    ctx.function("difficulty/apply")

    # ---- reset from a scrambled room
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.function(f"tunnel/{INDEX}/reset")
    unsolve()
    come_in()
    ctx.setblock(place.valve.input, place.valve_on)
    ctx.advance(2 * STEP)
    for number in (2, 5, 9):
        ctx.function(f"{base}/burst/{number}")
    ctx.set_score("#hb.w", 7)
    ctx.function(f"{base}/draw")
    ctx.setblock(sorted(br1.front)[0], PLATE)
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.function(f"{base}/reset")
    ctx.advance(4)
    as_state("reset", START)
    for what in ("item", "trident"):
        expect(
            f"reset: {what} entities in the dome",
            ctx.count(f"@e[type=minecraft:{what},{domes.sphere(dome)}]"),
            0,
        )
    expect("reset: automatons", ctx.count(automatons.selector(INDEX)), 0)
    expect(
        "reset: the other domes' and tunnels' scores",
        game_checks.scores(ctx, *others),
        before,
    )

    # ---- after: as found
    ctx.function(f"tunnel/{INDEX}/reset")
    for name in names:
        ctx.set_score(name, saved[name] or 0)
    ctx.advance(fall_back)
    ctx.function(f"{base}/reset")
    expect(
        "stand-ins left behind",
        ctx.count(f"@e[tag={S1}]") + ctx.count(f"@e[tag={S2}]"),
        0,
    )
    return problems


# ----------------------------------------------------------------- the rig

RIG = "st.hbrig"


def rig(ctx: Any) -> list[str]:
    """
    The Breacher's rig (``CHECKS=hull_breach_rig``; it is a check only
    when named), for the live integrator, before the room is trusted. In
    the check cell (``fittings.check_cell``: glass under the open sea, in
    the middle of the ring; built here and the sea put back after), half
    dry and half a pool of sources behind a glass sill, with nobody
    online and the time of day left as it is (``time query day``
    printed):

    1. a Breacher summoned and dressed as the room does
       (``automatons.BREACHER``), with no fire resistance;
    2. two prey, iron golems that cannot move (``NoAI``, 1000 health, off
       the team): one standing in the pool, one on the dry floor;
    3. 600 ticks, then read: is it burning (``Fire`` above 0, ever); the
       health each prey lost; how many tridents were thrown and their
       ``pickup`` (0: nobody may pick one up); trident items lying about;
       the sweep's line removes a trident stuck in a block.

    What to do with each outcome (``BREACHER_MODE`` in this module):

    - it burns: nothing (the room's ``temper`` gives every automaton fire
      resistance) but note it;
    - a thrown trident can be picked up (``pickup`` 1) or a trident item
      drops: ``BREACHER_MODE = "melee"`` (a drowned with no trident);
    - it goes for neither prey in 600 ticks, by day and by night: set
      ``"none"`` (the Riveters alone); if it goes only for the prey in the
      water by day, that is the design's rule ("in the water, mind the
      Breachers") and nothing changes; if for both, nothing changes but
      the plaque's advice is only true at night: tell the owner;
    - the summon is refused or it is a baby, picks things up or keeps no
      helmet: a fault in ``automatons.summon`` to fix before the room.

    Its problems name the outcomes that need ``BREACHER_MODE`` changed;
    the rest is printed. It is to be run once by day and once by night
    (the game's time is never set by the station).
    """
    cell = fittings.check_cell()
    if problems := fittings.build_cell(ctx):
        return problems
    try:
        return _rig(ctx, cell)
    finally:
        ctx.cmd(f"kill @e[tag={RIG}]")
        fittings.remove_cell(ctx)


def _rig(ctx: Any, cell: Any) -> list[str]:
    import re

    n = fittings.CHECK_INDEX
    fr = cell.fr
    lf, lr = fittings.CELL_HALF
    problems: list[str] = []
    report: list[str] = []
    daytime = ctx.cmd("time query day", r"\d+ tick")
    report.append(f"time of day: {daytime.strip()} (night is 13000 to 23000)")
    # the pool: the cell's far half, two deep, behind a glass sill
    ctx.fill(fr.at(0, -lr, 1), fr.at(0, lr, 2), GLASS)
    ctx.fill(fr.at(1, -lr, 1), fr.at(lf, lr, 2), WATER)
    kind = automatons.BREACHER
    ctx.cmd(automatons.summon_kind(kind, middle(fr.at(-1, 0, 1)), n, (RIG,)))
    ctx.cmd(automatons.dress_kind_line(n, kind))
    mob = automatons.selector(n, f"tag={RIG},limit=1")
    if not ctx.count(mob):
        return ["the Breacher was not summoned"]
    got = {
        k: ctx.data(f"entity {mob} {k}").rstrip("bf")
        for k in ("IsBaby", "CanPickUpLoot")
    }
    report.append(
        f"dressed: {got}, helmet {ctx.data(f'entity {mob} equipment.head.id')}"
    )
    if got != {"IsBaby": "0", "CanPickUpLoot": "0"}:
        problems.append(
            f"the Breacher is not dressed as the core's automatons are: {got}"
        )
    golem = (
        '{NoAI:1b,PersistenceRequired:1b,Health:1000f,Tags:["%s","%s"],'
        'attributes:[{id:"minecraft:max_health",base:1000d}]}'
    )
    wet_prey, dry_prey = f"{RIG}.wet", f"{RIG}.dry"
    ctx.cmd(
        f"summon minecraft:iron_golem {middle(fr.at(lf - 1, 0, 1))} {golem % (RIG, wet_prey)}"
    )
    ctx.cmd(
        f"summon minecraft:iron_golem {middle(fr.at(-lf + 1, 0, 1))} {golem % (RIG, dry_prey)}"
    )
    burnt = 0
    for _ in range(20):
        ctx.advance(30)
        fire = ctx.data(f"entity {mob} Fire").rstrip("s")
        if fire.lstrip("-").isdigit() and int(fire) > 0:
            burnt += 1
    lost = {}
    for name, tag in (("in the water", wet_prey), ("on the dry floor", dry_prey)):
        health = ctx.data(f"entity @e[tag={tag},limit=1] Health").rstrip("f")
        try:
            lost[name] = round(1000 - float(health))
        except ValueError:
            lost[name] = None
    report.append(f"burning in {burnt} of 20 looks; prey's health lost: {lost}")
    tridents = f"@e[type=minecraft:trident,{cell.selector}]"
    thrown = ctx.count(tridents)
    pickups = re.findall(
        r"\d+",
        ctx.data(f"entity @e[type=minecraft:trident,{cell.selector},limit=1] pickup"),
    )
    items = ctx.count(
        f'@e[type=minecraft:item,{cell.selector},nbt={{Item:{{id:"minecraft:trident"}}}}]'
    )
    report.append(
        f"tridents thrown and lying: {thrown}, pickup {pickups}, trident items {items}"
    )
    ctx.cmd(falling_trident(middle(fr.at(-3, 1, 1), 0.5), RIG))
    ctx.advance(4)
    stuck = f"@e[type=minecraft:trident,tag={RIG},nbt={{inGround:1b}}]"
    report.append(f"a trident dropped on the floor stuck: {ctx.count(stuck)}")
    ctx.cmd(f"kill @e[type=minecraft:trident,nbt={{inGround:1b}},{cell.selector}]")
    report.append(f"the sweep's line left {ctx.count(tridents)} tridents")
    ctx.cmd(f"kill {mob}")
    ctx.advance(20)
    items = ctx.count(
        f'@e[type=minecraft:item,{cell.selector},nbt={{Item:{{id:"minecraft:trident"}}}}]'
    )
    report.append(f"killed: trident items dropped {items}")
    for line in report:
        print(f"     rig: {line}", flush=True)
    if burnt:
        print("     rig: it burnt: the room's fire resistance covers it (note it)")
    if items or any(p != "0" for p in pickups):
        problems.append('a trident can be had: set BREACHER_MODE = "melee"')
    if not any(lost.values()):
        problems.append(
            "it went for neither prey in 600 ticks: run it at the other time of "
            'day; if neither, set BREACHER_MODE = "none"'
        )
    return problems


_checks: dict[str, Any] = {"hull_breach": check}
if "hull_breach_rig" in os.environ.get("CHECKS", "").split(","):
    _checks["hull_breach_rig"] = rig

MODULE = game.Module(
    "hullbreach",
    stages={f"dome_{INDEX}_inside": build},
    functions=functions,
    checks=_checks,
)
