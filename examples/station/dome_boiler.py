"""
The Boiler Room (dome 1) of The Drowned Station: the first puzzle and the
tutorial. Its build stage (``dome_1_inside``), its datapack functions
(``dome/1/...``) and its live check (``boiler_room``).

**The puzzle.** Raise steam and hold it. Coal comes from the bunker (a
button, a dropper); it goes into the chute (a hopper) on each of two
boilers and lights its fire; with both steam valves open the pressure
climbs the gauge, a column of ten lamps in the middle of the dome, and
with a valve shut it leaks away. Held in the green lamps (the band), the
pressure charges the main: five lamps in the floor come on towards the
next tunnel, and at the fifth the room is solved. Left to climb to the
tenth lamp, the safety valve blows: the pressure is dumped, the main is
lost and the valves slam shut. Left alone, the fires burn out and the
pressure falls. Either way the players start the main again; nothing ends
the run, and coal never runs out.

- *Solo:* each valve has a lever, which stays as it is put.
- *Duo:* each valve has a plate, which a player must stand on: two
  players, two valves far apart, held at once. A plate takes a living
  thing, so an item dropped on one does not hold it.

**Real inputs, datapack brain.** The button and the dropper are real
redstone; so are the hoppers (a dropped coal is drawn in), the levers and
the plates. The functions read their states and do the rest. The room's
machine to watch is the feed pump: a redstone torch clock through two
repeaters that works two pistons, running while a fire burns. Nothing
reads it.

**State** (scores in ``st``, all ``#boil.<name>``): ``p`` the pressure, 0
to ``P_MAX`` (a lamp is ``LAMP``); ``hold`` the steps held in the band;
``f0``, ``f1`` the steps of fire left in each boiler; ``lit`` how many
burn; ``v0``, ``v1``, ``open`` the valves; ``form`` 1 solo, 2 duo;
``live`` 1 once the room has been set up for those in it (a record:
the signal to set it up is the core's ``#first``); ``blows`` the
times the safety valve has blown. From the level in force when the room
is first entered (``scaled``): ``lo`` the bottom of the band, ``leak``,
``need`` (steps to hold), ``fuel`` (steps a coal burns).

**Functions** (the core calls the hooks, see game.py):

- ``enter``: the first to come into an unsolved room sets it up anew
  (``arm``: ``reset``, with the level's values);
- ``tick``: the recall button, and every ``STEP`` ticks ``step``: the
  state machine ``fires`` -> ``valves`` -> ``pressure`` -> ``show`` ->
  ``hold``, which calls ``done`` (``station:dome/1/solved``, then the
  room left steady by ``restored``);
- ``solo`` / ``duo``: the valves' levers or plates, whatever the pressure;
- ``empty``: the pump stopped, and an unsolved room put back;
- ``reset``: everything as built.

**Places.** Everything is placed in the dome's own frame (``Frame``:
forward from the entrance, right, up from the floor), so nothing here is
a world coordinate, and ``room_problems`` checks that every cell is
inside the dome and off the cells the tunnels reserve.

The frame, the signs, the plaque, the lectern and the recall post are the
core's (fittings.py).

**The boiler house** (``dressing_blocks``: what makes the room a room, and
no part of the puzzle). The boilers are tall riveted vessels with domed
tops, their flues rising to a header under the roof that the gauge's
standpipe hangs from. A stoker's gantry of copper grating crosses the
firing aisle five blocks up, reached by stairs at its north end, feed
pipes slung under it; the bunker is a timbered bin; the main is a pipe
run set in the floor from the gauge to the pump engine; a feed tank
stands by the feed pump and two receivers by the east wall. Machinery
that works by itself:

- the *lamp chaser* at the gantry's south end, behind bars: a torch clock
  with copper bulbs under its dust, real redstone, always running;
- the *governor* by the north receiver, behind bars: two pistons worked
  in turn by the function ``govern``, faster the higher the pressure,
  still when it is nil, a slow beat once the room is solved;
- the *bell* under the header, rung (a redstone block put over it) as
  each lamp of the main comes on;
- steam from the header, the stack and the receivers, more of it the
  higher the pressure.

``dress`` runs these every ``STEP`` ticks while anyone is in the dome,
solved or not; ``rest`` stills them (``reset``, ``empty``). None has a
lever, button or plate, and no function of the puzzle reads one.
``walk_problems`` and ``sight_problems`` check, with no server, that
every walk the puzzle needs is clear at foot and head height in both
forms and that the gauge can be seen from where it is worked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from typing import TYPE_CHECKING, Any

import datapack as dp
import domes
import game
import game_checks
import rooms
import station_layout as layout
import tunnels
from domes import AIR, Cell, middle
from fittings import (
    Frame,
    frame,
    lectern_with_book,
    placement_problems,
    plaque_blocks,
    recall_functions,
    recall_post_blocks,
    sign_text,
    snbt,
    standing_sign,
    summon_recall,
    wall_sign,
)

if TYPE_CHECKING:
    from station_layout import Dome

INDEX = 1  # the Boiler Room's place in the ring
OBJ = game.OBJ

STEP = 5  # ticks between steps of the state machine
LAMP = 1000  # pressure a lamp of the gauge
LAMPS = 10
P_MAX = LAMP * LAMPS  # the safety valve blows here
BAND_TOP = 8  # the top lamp of the band; the band is ``lo`` up to ``BAND_HI``
BAND_HI = (BAND_TOP + 1) * LAMP
P_AFTER_BLOW = 2 * LAMP
RISE = 40  # pressure a step for each fire, valves open
MAIN_LAMPS = 5
# at level 5, scaled by the core's percentages (``scaled``)
LEAK = 30  # pressure a step, valves shut or fires out
HOLD_STEPS = 60  # 15 s in the band
FUEL_STEPS = 120  # a coal burns 30 s
HOLD_LOSS = 2  # steps of hold lost a step out of the band

BRASS = "minecraft:gold_block"
COPPER = "minecraft:waxed_copper_block"
CUT = "minecraft:waxed_cut_copper"
CHISELED = "minecraft:waxed_chiseled_copper"
BULB = "minecraft:waxed_copper_bulb"
BAND_BULB = "minecraft:waxed_oxidized_copper_bulb"  # the green lamps
PLATE = "minecraft:polished_blackstone_pressure_plate"
PISTON = "minecraft:piston[facing=up]"
EXPOSED = "minecraft:waxed_exposed_copper"
WEATHERED = "minecraft:waxed_weathered_copper"
GRATE = "minecraft:waxed_copper_grate"
BARS = "minecraft:iron_bars"
ROD = "minecraft:waxed_lightning_rod"
STAIRS = "minecraft:waxed_cut_copper_stairs"
SLAB = "minecraft:waxed_cut_copper_slab"
TIMBER = "minecraft:dark_oak_planks"
STONE = "minecraft:polished_blackstone"
POWER = "minecraft:redstone_block"
GOV_AT = 16  # the governor strokes when its count reaches this
GOV_SOLVED = 2  # what a solved room adds to the count a step (a lamp adds 1)
BELL_STEPS = 2  # steps the bell's power stays on
#: blocks a player sees the gauge through
CLEAR_NAMES = ("grate", "bars", "lightning_rod", "glass", "chain")
SIGN = "minecraft:bamboo"
COAL = "minecraft:coal"
#: what a player would have to hold to open a locked block: nobody does
LOCK = '{lock:{items:"minecraft:barrier"}}'
ENTITY_TAG = "st.d1"  # everything this module summons
RECALL_TAG = "st.recall1"


# ---------------------------------------------------------------- the room


@dataclass(frozen=True)
class Boiler:
    name: str
    furnace: Cell
    hopper: Cell
    vent: Cell  # where its smoke rises
    score: str  # the steps of fire left


@dataclass(frozen=True)
class Valve:
    name: str
    lever: Cell
    plate: Cell
    lamp: Cell
    sign: Cell
    facing: str  # the way its lever and sign face
    score: str


@dataclass(frozen=True)
class Room:
    """where the Boiler Room's working parts are"""

    frame: Frame
    boilers: tuple[Boiler, Boiler]
    valves: tuple[Valve, Valve]
    gauge: tuple[Cell, ...]  # the pressure lamps, lowest first
    main: tuple[Cell, ...]  # the main's lamps, nearest the gauge first
    dropper: Cell
    coal_button: Cell
    coal_out: Cell  # where a coal lands
    lectern: Cell
    torch: Cell  # the feed pump's clock runs while a torch is here
    pistons: tuple[Cell, Cell]
    recall: tuple[int, int, int]  # the recall post: f, r, side
    # the boiler house's machinery (no part of the puzzle)
    chaser: tuple[Cell, ...]  # the lamp chaser's bulbs
    governor: tuple[Cell, Cell]  # its pistons
    gov_power: tuple[Cell, Cell]  # the floor under them: power or not
    gov_lamp: Cell
    bell: Cell
    bell_power: Cell  # the header's block over the bell
    steam: tuple[tuple[int, Cell], ...]  # (lamps of pressure it shows at, where)


# where things are, in the frame: (forward, right)
PLAQUE = (-7, 0)
LECTERN = (-7, 2)
RECALL = (-11, 3, -1)
BUNKER = (-7, -8)  # the dropper
BOILER_R = 7  # the boilers' middles, right and left of the gauge
VALVE = (7, 10)  # the valves, right and left
MAIN_F = (3, 5, 7, 9, 11)
PUMP = (-6, 10)  # the block the clock's torch is on
# the boiler house
BOILER_TOP = 7  # the height of a boiler's shell; its dome is above
HEADER_H = 12  # the header, across the dome over both boilers and the gauge
DECK_H = 5  # the gantry's deck; feet are a block above
DECK_F = (-6, -3)  # the deck from west to east; the walk is the middle two
DECK_R = (-6, 10)  # from the head of the stairs to the south end
CHASER_R = 6  # the south end of the deck from here is the lamp chaser's
GOVERNOR = (10, -5)  # the governor's middle
BELL_R = 3  # the bell hangs under the header this far right of the gauge
TANKS = ((10, -9), (10, 8))  # the receivers' low corners (2 by 2)
FEED_TANK = (-10, 9)


@cache
def room(dome: Dome) -> Room:
    fr = frame(dome)
    boilers = tuple(
        Boiler(
            name,
            fr.at(-2, side * BOILER_R, 1),
            fr.at(-2, side * BOILER_R, 2),
            fr.at(0, side * BOILER_R, HEADER_H + 1),
            f"#boil.f{i}",
        )
        for i, (name, side) in enumerate((("A", -1), ("B", 1)))
    )
    f, r = VALVE
    valves = tuple(
        Valve(
            name,
            fr.at(f, side * (r - 1), 2),
            fr.at(f, side * (r - 2), 1),
            fr.at(f, side * r, 3),
            fr.at(f, side * (r - 1), 1),
            fr.facing(0, -side),
            f"#boil.v{i}",
        )
        for i, (name, side) in enumerate((("A", -1), ("B", 1)))
    )
    bf, br = BUNKER
    pf, pr = PUMP
    gf, gr = GOVERNOR
    walk = (DECK_F[0] + 1, DECK_F[1] - 1)
    steam = [(1, fr.at(0, 0, HEADER_H + 3)), (9, fr.at(0, 0, HEADER_H + 3))]
    steam += [(3, fr.at(0, side * 4, HEADER_H + 1)) for side in (-1, 1)]
    steam += [(5, fr.at(tf, tr, 6)) for tf, tr in TANKS]
    steam += [(7, fr.at(0, side * BOILER_R, BOILER_TOP + 3)) for side in (-1, 1)]
    return Room(
        frame=fr,
        boilers=(boilers[0], boilers[1]),
        valves=(valves[0], valves[1]),
        gauge=tuple(fr.at(0, 0, 1 + k) for k in range(1, LAMPS + 1)),
        main=tuple(fr.at(f, 0, 0) for f in MAIN_F),
        dropper=fr.at(bf, br, 2),
        coal_button=fr.at(bf + 1, br + 1, 2),
        coal_out=fr.at(bf, br + 1, 1),
        lectern=fr.at(*LECTERN, 1),
        torch=fr.at(pf + 1, pr, 1),
        pistons=(fr.at(pf + 1, pr + 1, 1), fr.at(pf, pr + 1, 1)),
        recall=RECALL,
        chaser=tuple(fr.at(f, r, DECK_H) for r in (CHASER_R, DECK_R[1]) for f in walk),
        governor=(fr.at(gf, gr - 1, 1), fr.at(gf, gr + 1, 1)),
        gov_power=(fr.at(gf, gr - 1, 0), fr.at(gf, gr + 1, 0)),
        gov_lamp=fr.at(gf, gr, 2),
        bell=fr.at(0, BELL_R, HEADER_H - 1),
        bell_power=fr.at(0, BELL_R, HEADER_H),
        steam=tuple(steam),
    )


def scaled(level: int) -> dict[str, int]:
    """the room's values at a level, as the function ``scale`` works them
    out: a wider band, a slower leak, a shorter hold and longer-burning
    coal at low levels"""
    core = game.scaled(level)
    width = (2 * core["#diff.timer"] + 50) // 100  # lamps: 3, 2 or 1
    return {
        "lo": (BAND_TOP + 1 - width) * LAMP,
        "leak": LEAK * core["#diff.damage"] // 100,
        "need": HOLD_STEPS * core["#diff.count"] // 100,
        "fuel": FUEL_STEPS * core["#diff.timer"] // 100,
    }


def gauge_bulb(k: int, lo: int) -> str:
    """the kind of the gauge's lamp k (1 the lowest): green in the band"""
    return BAND_BULB if lo <= k * LAMP < BAND_HI else BULB


def lever(valve: Valve, on: bool = False) -> str:
    return (
        f"minecraft:lever[face=wall,facing={valve.facing},"
        f"powered={'true' if on else 'false'}]"
    )


def furnace(fr: Frame, lit: bool = False) -> str:
    return (
        f"minecraft:furnace[facing={fr.facing(-1, 0)},"
        f"lit={'true' if lit else 'false'}]{LOCK}"
    )


def valve_sign(valve: Valve, form: int) -> tuple[str, ...]:
    """what a valve's sign says in the solo and the duo form"""
    how = (
        ("Pull the lever", "to open.")
        if form == 1
        else (
            "Stand on the",
            "plate to hold",
            "it open.",
        )
    )
    return (f"STEAM VALVE {valve.name}", *how)


LOG_TITLE, LOG_AUTHOR = "Boiler Room log", "T. Marsh"
LOG_PAGES = [
    "Boiler Room log\nT. Marsh, engineer\n\nThe Engine has stopped answering "
    "us. The tunnels are flooding one by one.\n\nWhoever reads this: Pump "
    "No. 1 still works, if you can raise steam.",
    "To raise steam:\n\n1. Coal from the bunker. Press the button.\n\n"
    "2. Coal into the chute on each boiler.\n\n3. Open BOTH steam valves.\n\n"
    "4. Shut a valve when the gauge is in the green. Open it before she "
    "falls out.",
    "Hold her in the green and the main fills, lamp by lamp. Five lamps and "
    "the pump runs.\n\nToo high and the safety valve blows: you start the "
    "main again.\n\nWith a mate, the valves must be held: one each.",
]


def logbook(fr: Frame) -> str:
    return lectern_with_book(fr.facing(-1, 0), LOG_TITLE, LOG_AUTHOR, LOG_PAGES)


@dataclass
class Blocks:
    """every block the room is made of, as built and as ``reset`` leaves it"""

    floor: dict[Cell, str] = field(default_factory=dict)  # relaid floor
    solid: dict[Cell, str] = field(default_factory=dict)
    attached: dict[Cell, str] = field(default_factory=dict)  # need a support
    clear: set[Cell] = field(default_factory=set)  # air, to be kept so
    #: cells whose block's state changes by itself (a clock's dust, its
    #: repeaters, its lamps): the same block always, in whatever state
    moving: set[Cell] = field(default_factory=set)
    #: cells a moving part passes through (a piston's head)
    swept: set[Cell] = field(default_factory=set)

    def everything(self) -> dict[Cell, str]:
        return {**self.floor, **self.solid, **self.attached}

    def add(self, other: Blocks) -> None:
        """take in another set of blocks; no cell may be given twice"""
        mine, theirs = self.everything(), other.everything()
        if both := (set(mine) | self.clear | self.swept) & set(theirs):
            raise ValueError(f"cells given two blocks: {sorted(both)[:5]}")
        self.floor |= other.floor
        self.solid |= other.solid
        self.attached |= other.attached
        self.clear |= other.clear
        self.moving |= other.moving
        self.swept |= other.swept


def room_blocks(dome: Dome, lo: int | None = None, form: int = 1) -> Blocks:
    """the Boiler Room's blocks, the puzzle's and the boiler house's
    (``lo``: the bottom of the band, for the gauge's green lamps, the
    default level's if not given; ``form``: 1 the valves' levers, 2 their
    plates)"""
    b = puzzle_blocks(dome, lo)
    if form == 2:
        for valve in room(dome).valves:
            del b.attached[valve.lever]
            b.clear.discard(valve.plate)
            b.attached[valve.plate] = PLATE
            b.clear.add(valve.lever)
    b.add(dressing_blocks(dome))
    return b


def puzzle_blocks(dome: Dome, lo: int | None = None) -> Blocks:
    """the blocks of the puzzle itself and of the room's fittings, as
    ``reset`` leaves them"""
    lo = scaled(game.DEFAULT_LEVEL)["lo"] if lo is None else lo
    place = room(dome)
    fr = place.frame
    back, ahead = fr.facing(-1, 0), fr.facing(1, 0)
    right = fr.facing(0, 1)
    left = fr.facing(0, -1)
    b = Blocks()

    # the plaque, the logbook, the recall button
    solid, attached = plaque_blocks(
        fr,
        *PLAQUE,
        signs=(
            ("BOILER ROOM", "Pump No. 1", "", "Raise steam."),
            ("Feed the fires.", "Open both", "steam valves."),
            ("Hold the gauge", "in the green", "till the main", "is charged."),
        ),
    )
    b.solid |= solid
    b.attached |= attached
    b.solid[place.lectern] = logbook(fr)
    solid, attached = recall_post_blocks(fr, *place.recall)
    b.solid |= solid
    b.attached |= attached

    # the coal bunker: a heap of coal, the dropper, its button beside it
    f, r = BUNKER
    for df in (-1, 0, 1):
        for h in (1, 2):
            b.solid[fr.at(f + df, r - 1, h)] = "minecraft:coal_block"
    b.solid[fr.at(f - 1, r, 1)] = b.solid[fr.at(f - 1, r, 2)] = "minecraft:coal_block"
    b.solid[fr.at(f, r, 1)] = "minecraft:coal_block"
    # a timbered bin round the heap: a back row, an end wall, a lintel
    for df in (-1, 0, 1):
        b.solid[fr.at(f + df, r - 1, 3)] = "minecraft:coal_block"
        b.solid[fr.at(f + df, r, 3)] = TIMBER
        for h in (1, 2, 3):
            b.solid[fr.at(f + df, r - 2, h)] = "minecraft:coal_block"
    for dr in (-2, -1, 0):
        for h in (1, 2, 3):
            b.solid[fr.at(f - 2, r + dr, h)] = TIMBER
    b.solid[place.dropper] = f"minecraft:dropper[facing={right}]{LOCK}"
    b.solid[fr.at(f + 1, r, 1)] = CUT
    b.solid[fr.at(f + 1, r, 2)] = BRASS
    b.attached[place.coal_button] = f"minecraft:stone_button[face=wall,facing={right}]"
    b.attached[fr.at(f - 1, r + 1, 2)] = wall_sign(right, "COAL", "Press the", "button")

    # the boilers: tall riveted vessels, a firebox and a coal chute at the
    # foot of each (the dome, the flue and the header are the dressing's)
    for boiler, side in zip(place.boilers, (-1, 1), strict=True):
        mid = side * BOILER_R
        for h in range(1, BOILER_TOP + 1):
            for df in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    b.solid[fr.at(df, mid + dr, h)] = boiler_plate(df, dr, h)
        b.solid[boiler.furnace] = furnace(fr)
        b.solid[boiler.hopper] = f"minecraft:hopper[facing={ahead}]"
        b.attached[fr.at(-2, mid, 3)] = wall_sign(
            back, f"BOILER {boiler.name}", "Coal in", "the chute", "below"
        )

    # the gauge
    b.solid[fr.at(0, 0, 1)] = CHISELED
    for k, cell in enumerate(place.gauge, 1):
        b.solid[cell] = f"{gauge_bulb(k, lo)}[lit=false]"
    b.attached[fr.at(-1, 0, 1)] = wall_sign(back, "PRESSURE", "Hold it in", "the green")

    # the valves: a lever (solo) or a plate (duo), a lamp that shows it open
    f, r = VALVE
    for valve, side in zip(place.valves, (-1, 1), strict=True):
        b.solid[fr.at(f, side * r, 1)] = CUT
        b.solid[fr.at(f, side * r, 2)] = BRASS
        b.solid[valve.lamp] = f"{BULB}[lit=false]"
        b.floor[fr.at(f, side * (r - 2), 0)] = BRASS
        b.attached[valve.lever] = lever(valve)
        b.attached[valve.sign] = wall_sign(valve.facing, *valve_sign(valve, 1))
        b.clear.add(valve.plate)

    # the main: lamps in the floor towards the next tunnel
    for cell in place.main:
        b.floor[cell] = f"{BULB}[lit=false]"

    # the feed pump: a torch on a block, its light led round through two
    # repeaters to put the torch out, and two pistons that follow it
    f, r = PUMP
    for df in range(-2, 4):
        for dr in (-1, 0, 1):
            b.floor[fr.at(f + df, r + dr, 0)] = CUT
    b.solid[fr.at(f, r, 1)] = COPPER
    # (plain pistons with nothing on them: a sticky one drops its load when
    # the clock is stopped and started within a stroke)
    for cell in place.pistons:
        b.solid[cell] = PISTON
    for df, dr in ((2, 0), (2, -1), (1, -1), (-1, -1), (-2, -1), (-2, 0)):
        b.attached[fr.at(f + df, r + dr, 1)] = "minecraft:redstone_wire"
    # a repeater's facing names the side its input is on
    b.attached[fr.at(f, r - 1, 1)] = f"minecraft:repeater[facing={ahead},delay=4]"
    b.attached[fr.at(f - 1, r, 1)] = f"minecraft:repeater[facing={back},delay=4]"
    b.attached[fr.at(f + 3, r, 1)] = standing_sign(
        left, "FEED PUMP", "runs while", "a fire burns"
    )
    b.clear.add(place.torch)
    return b


def boiler_plate(df: int, dr: int, h: int) -> str:
    """a boiler's shell: cut copper straps at the corners, the foot and
    the top, a riveted band half way up, plates of two ages between"""
    if (df and dr) or h in (1, BOILER_TOP):
        return CUT
    if h == (BOILER_TOP + 1) // 2:
        return CHISELED
    return COPPER if h % 2 == 0 else EXPOSED


def dressing_blocks(dome: Dome) -> Blocks:
    """the boiler house round the puzzle (see the module docstring): built
    once, and left alone by ``reset`` but for the governor and the bell,
    which it stills"""
    place = room(dome)
    fr = place.frame
    back, ahead = fr.facing(-1, 0), fr.facing(1, 0)
    left, right = fr.facing(0, -1), fr.facing(0, 1)
    d = Blocks()

    def rod(way: str) -> str:
        return f"{ROD}[facing={way}]"

    # -- the boilers' domed tops, their flues, the header and its stack
    for side in (-1, 1):
        mid = side * BOILER_R
        top = BOILER_TOP + 1
        d.solid[fr.at(0, mid, top)] = COPPER
        for df, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            d.solid[fr.at(df, mid + dr, top)] = (
                f"{STAIRS}[facing={fr.facing(-df, -dr)},half=bottom]"
            )
        for df in (-1, 1):
            for dr in (-1, 1):
                d.solid[fr.at(df, mid + dr, top)] = f"{SLAB}[type=bottom]"
        d.solid[fr.at(0, mid, top + 1)] = CHISELED
        for h in range(top + 2, HEADER_H):
            d.solid[fr.at(0, mid, h)] = CUT
    for r in range(-BOILER_R, BOILER_R + 1):
        joint = r == 0 or abs(r) == BOILER_R
        d.solid[fr.at(0, r, HEADER_H)] = CHISELED if joint else COPPER
    d.solid[fr.at(0, 0, HEADER_H + 1)] = CUT
    d.solid[fr.at(0, 0, HEADER_H + 2)] = GRATE
    # the bell, out of reach under the header
    d.attached[place.bell] = f"minecraft:bell[attachment=ceiling,facing={back}]"
    d.moving.add(place.bell)

    # -- the stoker's gantry: a deck of grating over the firing aisle, a
    # rail each side, stairs at the north end, posts under its west edge
    f0, f1 = DECK_F
    r0, r1 = DECK_R
    walk = (f0 + 1, f1 - 1)
    for r in range(r0, r1 + 1):
        for f in range(f0, f1 + 1):
            d.solid[fr.at(f, r, DECK_H)] = GRATE if r < CHASER_R else CUT
        for f in (f0, f1):
            d.solid[fr.at(f, r, DECK_H + 1)] = BARS
    for i in range(DECK_H):  # the stairs, down to the floor going north
        for f in walk:
            d.solid[fr.at(f, r0 - 1 - i, DECK_H - i)] = (
                f"{STAIRS}[facing={right},half=bottom]"
            )
    for r in (r0 + 1, 0, CHASER_R - 1, PUMP[1] - 2):
        for h in range(1, DECK_H):
            d.solid[fr.at(f0, r, h)] = rod("up")
    for r in (-3, 3):
        d.attached[fr.at(walk[0], r, DECK_H - 1)] = "minecraft:lantern[hanging=true]"
    # the feed pipe slung under the east edge, a riser from the feed pump,
    # a branch into each boiler over its chute
    pf, pr = PUMP
    for h in range(1, DECK_H - 1):
        d.solid[fr.at(f1, pr - 1, h)] = rod("up")
    for r in range(-BOILER_R, pr):
        d.solid[fr.at(f1, r, DECK_H - 1)] = rod(right)
    for side in (-1, 1):
        d.solid[fr.at(f1 + 1, side * BOILER_R, DECK_H - 1)] = rod(ahead)

    # -- the lamp chaser, on the south end of the deck behind bars: the
    # feed pump's clock again (a torch on a block, dust, two repeaters),
    # with copper bulbs under four of its dust
    mid = (CHASER_R + r1) // 2
    east, west = walk[1], walk[0]
    for f in walk:
        for h in (1, 2):
            d.solid[fr.at(f, CHASER_R - 1, DECK_H + h)] = BARS
    for cell in place.chaser:
        d.solid[cell] = f"{BULB}[lit=false]"
    d.solid[fr.at(east, mid, DECK_H + 1)] = COPPER
    d.attached[fr.at(east, mid + 1, DECK_H + 1)] = (
        f"minecraft:redstone_wall_torch[facing={right}]"
    )
    wire = [(east, mid + 2), (west, mid + 2), (west, mid + 1)]
    wire += [(west, mid - 1), (west, mid - 2), (east, mid - 2)]
    for f, r in wire:
        d.attached[fr.at(f, r, DECK_H + 1)] = "minecraft:redstone_wire"
    d.attached[fr.at(west, mid, DECK_H + 1)] = (
        f"minecraft:repeater[facing={right},delay=4]"
    )
    d.attached[fr.at(east, mid - 1, DECK_H + 1)] = (
        f"minecraft:repeater[facing={left},delay=4]"
    )
    d.moving |= set(place.chaser)
    d.moving |= {fr.at(f, r, DECK_H + 1) for f in walk for r in range(mid - 2, mid + 3)}
    d.moving.discard(fr.at(east, mid, DECK_H + 1))

    # -- the main: a pipe run set in the floor from the gauge to the pump
    # engine, the puzzle's five lamps in it
    lights = domes.light_cells(dome)[0]
    engine = tunnels.engine_cells(layout.TUNNELS[dome.index])
    ef, er = fr_of(fr, engine[1, 0])
    run = [(f, 0) for f in range(1, ef)]
    run += [(ef - 1, r) for r in range(0, er, 1 if er > 0 else -1)][1:]
    for f, r in run:
        cell = fr.at(f, r, 0)
        if cell not in place.main and cell not in lights:
            d.floor[cell] = CUT
        for dr in (-1, 1):
            edge = fr.at(f, r + dr, 0) if r == 0 else fr.at(f + dr, r, 0)
            if (f, r + dr) not in run and edge not in lights:
                d.floor.setdefault(edge, STONE)
    # the firing aisle's floor
    for r in range(-BOILER_R - 2, BOILER_R + 2):
        for f in (f1 - 1, f1):
            if fr.at(f, r, 0) not in lights:
                d.floor[fr.at(f, r, 0)] = STONE

    # -- the receivers by the east wall and the feed tank by the feed pump
    for (tf, tr), high in ((TANKS[0], 5), (TANKS[1], 5), (FEED_TANK, 4)):
        for df in (0, 1):
            for dr in (0, 1):
                d.solid[fr.at(tf + df, tr + dr, 1)] = CUT
                for h in range(2, high):
                    d.solid[fr.at(tf + df, tr + dr, h)] = WEATHERED
                d.solid[fr.at(tf + df, tr + dr, high)] = f"{SLAB}[type=bottom]"
    # the south receiver's pipe: a stub, then under the floor to the main
    tf, tr = TANKS[1]
    d.solid[fr.at(tf, tr - 1, 1)] = rod(left)
    for r in range(2, tr - 1):
        d.floor.setdefault(fr.at(tf, r, 0), CUT)

    # -- the governor, between the north receiver and the main, behind
    # bars: two pistons (plain, carrying nothing: a sticky one drops its
    # load when it is stilled within a stroke), a lamp between them. The
    # floor under each piston is its power (a redstone block) or not
    gf, gr = GOVERNOR
    for piston, power in zip(place.governor, place.gov_power, strict=True):
        d.solid[piston] = PISTON
        d.swept.add((piston[0], piston[1] + 1, piston[2]))
        d.floor[power] = CUT
    d.solid[fr.at(gf, gr, 1)] = COPPER
    d.solid[place.gov_lamp] = f"{BULB}[lit=false]"
    d.solid[fr.at(gf, gr, 3)] = rod("up")
    for r in range(TANKS[0][1] + 2, gr - 1):
        d.solid[fr.at(gf, r, 1)] = rod(right)
    for dr in (-1, 0, 1):
        for df in (-1, 1):
            d.solid[fr.at(gf + df, gr + dr, 1)] = BARS
    d.solid[fr.at(gf, gr + 2, 1)] = BARS
    for r in range(gr + 3, 0):
        d.floor.setdefault(fr.at(gf, r, 0), CUT)
    return d


def fr_of(fr: Frame, cell: Cell) -> tuple[int, int]:
    """a cell's place in a frame: forward and right of the middle"""
    dx, dz = cell[0] - fr.origin[0], cell[2] - fr.origin[2]
    return (
        dx * fr.forward[0] + dz * fr.forward[1],
        dx * fr.right[0] + dz * fr.right[1],
    )


def torch(fr: Frame) -> str:
    return f"minecraft:redstone_wall_torch[facing={fr.facing(1, 0)}]"


def _name(block: str) -> str:
    return block.partition("[")[0].partition("{")[0]


#: what stands on or hangs from a block and is still in the way
IN_THE_WAY = ("minecraft:lantern", "minecraft:bell")


def walks(dome: Dome) -> dict[str, Cell]:
    """where a player must be able to walk to from the entrance, by name:
    the cell their feet are in"""
    place = room(dome)
    fr = place.frame
    out = layout.TUNNELS[dome.index]
    ux, uz = domes.outward(dome, out)
    ox, oy, oz = dome.floor_centre
    mouth = dome.radius - 3
    bx, by, bz = place.coal_button
    lf, lr = LECTERN
    targets = {
        "the way out": (ox + ux * mouth, oy + 1, oz + uz * mouth),
        "the bunker's button": (bx, by - 1, bz),
        "where the coal lands": place.coal_out,
        "the logbook": fr.at(lf - 1, lr, 1),
        "the plaque": fr.at(PLAQUE[0] - 2, PLAQUE[1], 1),
        "the gauge": fr.at(2, 1, 1),
        "the gantry": fr.at(DECK_F[0] + 1, 0, DECK_H + 1),
        "the feed pump": fr.at(PUMP[0] + 3, PUMP[1] - 2, 1),
        "the governor": fr.at(GOVERNOR[0] - 2, GOVERNOR[1], 1),
    }
    for boiler in place.boilers:
        x, y, z = boiler.furnace
        bf, br = fr_of(fr, boiler.furnace)
        targets[f"boiler {boiler.name}'s chute"] = fr.at(bf - 1, br, 1)
    for valve in place.valves:
        targets[f"valve {valve.name}"] = valve.plate
    return targets


def walk_problems(dome: Dome) -> list[str]:
    """
    Every place of ``walks`` can be walked to from the entrance, in the
    solo and the duo form: a player's feet and head are in free cells
    with something to stand on, and a step is to a cell beside, level or
    one up or down (a stair), with room for the head on the way up.
    """
    problems = []
    for form in (1, 2):
        b = room_blocks(dome, form=form)
        blocked = set(b.solid) | b.swept
        blocked |= {c for c, block in b.attached.items() if _name(block) in IN_THE_WAY}
        seen = rooms.reach(dome, domes.entrance(dome)[:3], b.solid, blocked)
        problems += [
            f"form {form}: no walk from the entrance to {name} at {cell}"
            for name, cell in walks(dome).items()
            if cell not in seen
        ]
    return problems


def sight_problems(dome: Dome) -> list[str]:
    """
    The gauge can be read from where the puzzle is worked: from each
    valve and each chute every lamp, and from the entrance and the bunker
    the lamps of the band at every level. A lamp is seen if nothing but
    grating, bars and pipes is on the line from the eye to its middle.
    """
    place = room(dome)
    b = room_blocks(dome)
    solid = {
        cell
        for cell, block in b.solid.items()
        if not any(word in block for word in CLEAR_NAMES)
    } - set(place.gauge)
    spots = walks(dome)
    x, y, z, _ = domes.entrance(dome)
    band = range(min(scaled(lv)["lo"] for lv in game.LEVELS) // LAMP, BAND_TOP + 1)
    every = range(1, LAMPS + 1)
    eyes = {
        "the entrance": ((x, y, z), band),
        "the bunker": (spots["where the coal lands"], band),
    }
    for name, cell in spots.items():
        if name.startswith(("valve", "boiler")):
            eyes[name] = (cell, every)
    problems = []
    for name, (cell, lamps) in eyes.items():
        for k in lamps:
            lamp = place.gauge[k - 1]
            hidden = rooms.hidden(cell, lamp, solid)
            if hidden:
                problems.append(
                    f"lamp {k} of the gauge is hidden from {name} by {min(hidden)}"
                )
    return problems


def room_problems(dome: Dome) -> list[str]:
    """the room's cells against the dome's: all inside it, none on a cell
    the tunnels reserve, the relaid floor in the floor and off its outer
    ring's lanterns; the walks clear and the gauge in sight"""
    cells = domes.dome_cells(dome)
    try:
        b = room_blocks(dome)
    except ValueError as e:
        return [str(e)]
    place = room(dome)
    above = {**b.solid, **b.attached}
    inside = set(above) | b.clear | b.swept | {place.coal_out}
    inside |= {x.vent for x in place.boilers} | {cell for _, cell in place.steam}
    # the feed pump's pistons' heads rise a block
    inside |= {(x, y + 1, z) for x, y, z in place.pistons}
    problems = placement_problems(dome, inside)
    if stray := set(b.floor) - cells.floor:
        problems.append(f"{len(stray)} floor cells are not in the floor")
    if set(b.floor) & set(above) or set(b.solid) & set(b.attached):
        problems.append("a cell is given two blocks")
    if "waterlogged=true" in "".join(b.everything().values()):
        problems.append("a block is waterlogged")
    return problems + walk_problems(dome) + sight_problems(dome)


# --------------------------------------------------------------- the build


def build(ctx: Any) -> str:
    """the Boiler Room inside its shell; wipes what was inside but the
    pump engine, and leaves the room as ``reset`` does"""
    dome = ctx.layout.DOMES[INDEX]
    if problems := room_problems(dome):
        raise RuntimeError("the Boiler Room: " + "; ".join(problems))
    place = room(dome)
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    engine = set(tunnels.engine_cells(ctx.layout.TUNNELS[INDEX]).values())
    ctx.cmd(f"kill @e[tag={ENTITY_TAG}]")
    ctx.fill_boxes(cells.interior - engine, AIR)
    for part in (b.floor, b.solid, b.attached):
        for cell, block in sorted(part.items()):
            ctx.setblock(cell, block)
    ctx.cmd(summon_recall(place.frame, *place.recall, tags=(ENTITY_TAG, RECALL_TAG)))
    x, y, z = place.dropper
    ctx.cmd(f"item replace block {x} {y} {z} container.0 with {COAL} 64")
    # the pack's own idea of the room, if the pack is installed
    ctx.function(f"dome/{INDEX}/reset")
    ctx.advance(10)
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    return (
        f"{dome.name}: {len(b.everything())} blocks: plaque, logbook, recall "
        "button, coal bunker, 2 boilers, 2 valves, the gauge, the main, the "
        "feed pump; the boiler house: flues and header, gantry and stairs, "
        "pipes, 3 tanks, lamp chaser, governor, bell"
    )


# ----------------------------------------------------------- the functions


def _s(name: str) -> str:
    return f"#boil.{name} {OBJ}"


def _set(name: str, value: int) -> str:
    return f"scoreboard players set {_s(name)} {value}"


def _op(name: str, op: str, other: str) -> str:
    return f"scoreboard players operation {_s(name)} {op} {other} {OBJ}"


def _setblock(cell: Cell, block: str) -> str:
    return f"setblock {cell[0]} {cell[1]} {cell[2]} {block}"


def _if_block(cell: Cell, block: str) -> str:
    return f"if block {cell[0]} {cell[1]} {cell[2]} {block}"


def _unless_block(cell: Cell, block: str) -> str:
    return f"unless block {cell[0]} {cell[1]} {cell[2]} {block}"


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


def functions(pack: dp.Pack) -> None:
    """the Boiler Room's functions (see the module docstring)"""
    dome = layout.DOMES[INDEX]
    place = room(dome)
    fr = place.frame
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    open_dome = f"#d{INDEX} {OBJ}"
    pack.constants(OBJ, MAIN_LAMPS, 100, LAMP)

    def fid(name: str) -> str:
        return pack.id(f"{base}/{name}")

    def sound(name: str, cell: Cell, volume: float = 1, pitch: float = 1) -> str:
        return f"playsound minecraft:{name} block {here} {_xyz(cell)} {volume} {pitch}"

    def say(text: str, colour: str = "yellow") -> str:
        return f'tellraw {here} {{text:{snbt(text)},color:"{colour}"}}'

    top = place.gauge[-1]

    # -- the values of the level in force
    pack.function(
        f"{base}/scale",
        [
            _set("leak", LEAK),
            _op("leak", "*=", "#diff.damage"),
            _op("leak", "/=", "#100"),
            _set("need", HOLD_STEPS),
            _op("need", "*=", "#diff.count"),
            _op("need", "/=", "#100"),
            _set("fuel", FUEL_STEPS),
            _op("fuel", "*=", "#diff.timer"),
            _op("fuel", "/=", "#100"),
            # the band's width in lamps, then its bottom
            _op("t", "=", "#diff.timer"),
            _op("t", "+=", "#diff.timer"),
            f"scoreboard players add {_s('t')} 50",
            _op("t", "/=", "#100"),
            _set("lo", BAND_TOP + 1),
            _op("lo", "-=", "#boil.t"),
            _op("lo", "*=", f"#{LAMP}"),
        ],
    )

    # -- the fires: a coal from the chute when a fire is out
    coal_gone = '{type:"minecraft:set_count",count:-1,add:true}'
    fires = []
    for i, boiler in enumerate(place.boilers):
        fire = f"{boiler.score} {OBJ}"
        chute = _xyz(boiler.hopper)
        pack.function(
            f"{base}/stoke_{i}",
            [
                _set("got", 0),
                *(
                    f"execute if score {_s('got')} matches 0 "
                    f"if items block {chute} container.{slot} {COAL} "
                    f"store success score {_s('got')} "
                    f"run item modify block {chute} container.{slot} {coal_gone}"
                    for slot in range(5)
                ),
                f"execute if score {_s('got')} matches 1 "
                f"run scoreboard players operation {fire} = {_s('fuel')}",
            ],
        )
        pack.function(
            f"{base}/light_{i}",
            [
                _setblock(boiler.furnace, furnace(fr, True)),
                sound("item.firecharge.use", boiler.furnace),
            ],
        )
        fires += [
            f"execute if score {fire} matches 1.. "
            f"run scoreboard players remove {fire} 1",
            f"execute if score {fire} matches ..0 run function {fid(f'stoke_{i}')}",
            f"execute if score {fire} matches 1.. "
            f"{_if_block(boiler.furnace, 'minecraft:furnace[lit=false]')} "
            f"run function {fid(f'light_{i}')}",
            f"execute if score {fire} matches ..0 "
            f"{_if_block(boiler.furnace, 'minecraft:furnace[lit=true]')} "
            f"run {_setblock(boiler.furnace, furnace(fr))}",
            f"execute if score {fire} matches 1.. run particle "
            f"minecraft:campfire_cosy_smoke {middle(boiler.vent)} 0.2 0.5 0.2 0.01 2",
        ]
    lit = _s("lit")
    fires += [
        _set("lit", 0),
        *(
            f"execute if score {b.score} {OBJ} matches 1.. "
            f"run scoreboard players add {lit} 1"
            for b in place.boilers
        ),
        f"execute if score {lit} matches 1.. run function {fid('pump_on')}",
        f"execute if score {lit} matches 0 run function {fid('pump_off')}",
    ]
    pack.function(f"{base}/fires", fires)
    a_torch = "minecraft:redstone_wall_torch"
    pack.function(
        f"{base}/pump_on",
        [
            f"execute {_unless_block(place.torch, a_torch)} "
            f"run {_setblock(place.torch, torch(fr))}"
        ],
    )
    pack.function(
        f"{base}/pump_off",
        [
            f"execute {_if_block(place.torch, a_torch)} run {_setblock(place.torch, AIR)}"
        ],
    )

    # -- the valves: a lever thrown or a plate stood on
    valves = [_op("was", "=", "#boil.open")]
    for valve in place.valves:
        v = f"{valve.score} {OBJ}"
        valves += [
            f"scoreboard players set {v} 0",
            f"execute {_if_block(valve.lever, 'minecraft:lever[powered=true]')} "
            f"run scoreboard players set {v} 1",
            f"execute {_if_block(valve.plate, f'{PLATE}[powered=true]')} "
            f"run scoreboard players set {v} 1",
            f"execute if score {v} matches 1 "
            f"{_if_block(valve.lamp, f'{BULB}[lit=false]')} "
            f"run {_setblock(valve.lamp, f'{BULB}[lit=true]')}",
            f"execute if score {v} matches 0 "
            f"{_if_block(valve.lamp, f'{BULB}[lit=true]')} "
            f"run {_setblock(valve.lamp, f'{BULB}[lit=false]')}",
        ]
    both = " ".join(f"if score {v.score} {OBJ} matches 1" for v in place.valves)
    is_open = f"if score {_s('open')} matches 1"
    valves += [
        _set("open", 0),
        f"execute {both} run {_set('open', 1)}",
        f"execute {is_open} if score {_s('was')} matches 0 run "
        + sound("block.fire.extinguish", top, 1, 1.6),
        f"execute {is_open} if score {lit} matches 0 "
        f"if score {_s('hint.cold')} matches 0 run function {fid('hint_cold')}",
    ]
    pack.function(f"{base}/valves", valves)
    pack.function(
        f"{base}/hint_cold",
        [
            _set("hint.cold", 1),
            say("The valves are open, but the fires are out: no steam."),
        ],
    )

    # -- the pressure: up with steam through both valves, else leaking away
    flowing = f"{is_open} if score {lit} matches 1.."
    pressure = [
        _set("flow", 0),
        f"execute {flowing} run {_set('flow', 1)}",
        _op("t", "=", "#boil.lit"),
        _op("t", "*=", "#boil.rise"),
        f"execute if score {_s('flow')} matches 1 run {_op('p', '+=', '#boil.t')}",
        f"execute if score {_s('flow')} matches 0 run {_op('p', '-=', '#boil.leak')}",
        f"execute if score {_s('p')} matches ..-1 run {_set('p', 0)}",
        f"execute if score {_s('p')} matches {P_MAX}.. run function {fid('safety')}",
    ]
    pack.function(f"{base}/pressure", pressure)
    pack.function(
        f"{base}/safety",
        [
            _set("p", P_AFTER_BLOW),
            _set("hold", 0),
            f"scoreboard players add {_s('blows')} 1",
            *(
                f"execute {_if_block(v.lever, 'minecraft:lever[powered=true]')} "
                f"run {_setblock(v.lever, lever(v))}"
                for v in place.valves
            ),
            f"title {here} times 5 50 10",
            f'title {here} subtitle {{text:"Too much steam: keep it in the green",'
            'color:"yellow"}',
            f'title {here} title {{text:"Safety valve!",color:"red"}}',
            sound("entity.generic.explode", top, 0.7, 1.4),
            sound("block.fire.extinguish", top, 2, 0.6),
            f"particle minecraft:cloud {middle(top, 2)} 0.6 1.5 0.6 0.08 120",
        ],
    )

    # -- the gauge and the main, drawn when they change
    band_bottoms = sorted({scaled(level)["lo"] for level in game.LEVELS})
    gauge = []
    for k, cell in enumerate(place.gauge, 1):
        on = f"if score {_s('n')} matches {k}.."
        off = f"unless score {_s('n')} matches {k}.."
        if len({gauge_bulb(k, lo) for lo in band_bottoms}) == 1:  # at every level
            kinds = [("", gauge_bulb(k, band_bottoms[0]))]
        else:
            kinds = [
                (f"if score {_s('lo')} matches ..{k * LAMP} ", BAND_BULB),
                (f"unless score {_s('lo')} matches ..{k * LAMP} ", BULB),
            ]
        for when, bulb in kinds:
            gauge += [
                f"execute {when}{on} run {_setblock(cell, f'{bulb}[lit=true]')}",
                f"execute {when}{off} run {_setblock(cell, f'{bulb}[lit=false]')}",
            ]
    pack.function(f"{base}/gauge", [*gauge, _op("n.shown", "=", "#boil.n")])
    main = [
        f"execute if score {_s('m')} > {_s('m.shown')} run "
        + sound("block.note_block.bell", place.main[0], 2, 1.2),
        f"execute if score {_s('m')} > {_s('m.shown')} run function {fid('ring')}",
    ]
    for j, cell in enumerate(place.main, 1):
        main += [
            f"execute if score {_s('m')} matches {j}.. "
            f"run {_setblock(cell, f'{BULB}[lit=true]')}",
            f"execute unless score {_s('m')} matches {j}.. "
            f"run {_setblock(cell, f'{BULB}[lit=false]')}",
        ]
    pack.function(f"{base}/main", [*main, _op("m.shown", "=", "#boil.m")])
    pack.function(
        f"{base}/show",
        [
            _op("n", "=", "#boil.p"),
            _op("n", "/=", f"#{LAMP}"),
            f"execute unless score {_s('n')} = {_s('n.shown')} "
            f"run function {fid('gauge')}",
            _op("m", "=", "#boil.hold"),
            _op("m", "*=", f"#{MAIN_LAMPS}"),
            _op("m", "/=", "#boil.need"),
            f"execute if score {_s('m')} matches {MAIN_LAMPS + 1}.. "
            f"run {_set('m', MAIN_LAMPS)}",
            f"execute unless score {_s('m')} = {_s('m.shown')} "
            f"run function {fid('main')}",
        ],
    )

    # -- the hold: in the band the main charges, out of it the charge goes
    in_band = f"if score {_s('band')} matches 1"
    pack.function(
        f"{base}/hold",
        [
            _set("band", 0),
            f"execute if score {_s('p')} >= {_s('lo')} "
            f"if score {_s('p')} matches ..{BAND_HI - 1} run {_set('band', 1)}",
            f"execute {in_band} run scoreboard players add {_s('hold')} 1",
            f"execute unless score {_s('band')} matches 1 "
            f"run scoreboard players remove {_s('hold')} {HOLD_LOSS}",
            f"execute if score {_s('hold')} matches ..-1 run {_set('hold', 0)}",
            f"execute {in_band} if score {_s('hint.band')} matches 0 "
            f"run function {fid('hint_band')}",
            f"execute if score {_s('hold')} >= {_s('need')} run function {fid('done')}",
        ],
    )
    pack.function(
        f"{base}/hint_band",
        [
            _set("hint.band", 1),
            say("In the green. Hold her there: the main is charging.", "green"),
        ],
    )
    pack.function(
        f"{base}/done",
        [
            f"function {pack.id(f'dome/{INDEX}/solved')}",
            f"function {fid('restored')}",
        ],
    )
    # the room once solved: steady, and nothing left to work
    pack.function(
        f"{base}/restored",
        [
            _set("hold", 0),
            _set("n", BAND_TOP),
            f"function {fid('gauge')}",
            _set("m", MAIN_LAMPS),
            _op("m.shown", "=", "#boil.m"),
            f"function {fid('main')}",
            *(_setblock(b.furnace, furnace(fr, True)) for b in place.boilers),
            *(_setblock(v.plate, AIR) for v in place.valves),
            *(_setblock(v.lever, lever(v, True)) for v in place.valves),
            *(_setblock(v.lamp, f"{BULB}[lit=true]") for v in place.valves),
            f"function {fid('pump_on')}",
        ],
    )

    # -- the boiler house's machinery (no part of the puzzle: nothing
    # above reads any of it)
    gov, phase = _s("gov"), _s("gov.phase")
    up, down = place.gov_power
    lamp = place.gov_lamp
    head = (place.governor[0][0], place.governor[0][1] + 2, place.governor[0][2])
    puff = "minecraft:cloud"

    def stroke(a: Cell, b: Cell, lit: str) -> list[str]:
        return [
            _setblock(b, CUT),
            _setblock(a, POWER),
            _setblock(lamp, f"{BULB}[{lit}]"),
        ]

    pack.function(
        f"{base}/govern",
        [
            f"scoreboard players remove {gov} {GOV_AT}",
            f"scoreboard players add {_s('strokes')} 1",
            _set("gov.out", 1),
            f"scoreboard players add {phase} 1",
            f"execute if score {phase} matches 2.. run {_set('gov.phase', 0)}",
            *(
                f"execute if score {phase} matches 1 run {line}"
                for line in stroke(up, down, "lit=true")
            ),
            *(
                f"execute if score {phase} matches 0 run {line}"
                for line in stroke(down, up, "lit=false")
            ),
            f"particle {puff} {middle(head)} 0.3 0.2 0.3 0.01 3",
        ],
    )
    pack.function(
        f"{base}/rest",
        [
            _set("gov", 0),
            _set("gov.phase", 0),
            _set("gov.out", 0),
            _set("bell", 0),
            _setblock(up, CUT),
            _setblock(down, CUT),
            _setblock(lamp, f"{BULB}[lit=false]"),
            _setblock(place.bell_power, COPPER),
        ],
    )
    pack.function(
        f"{base}/ring",
        [
            _set("bell", BELL_STEPS),
            f"scoreboard players add {_s('rings')} 1",
            _setblock(place.bell_power, POWER),
        ],
    )
    solved_dome = f"if score {open_dome} matches 2"
    lamps_up = f"score {_s('n')} matches"
    dress = [
        # the bell's power, off again
        f"execute if score {_s('bell')} matches 1.. "
        f"run scoreboard players remove {_s('bell')} 1",
        f"execute if score {_s('bell')} matches 0 "
        f"{_if_block(place.bell_power, POWER)} "
        f"run {_setblock(place.bell_power, COPPER)}",
        # the governor: a lamp of pressure is a count a step, and a solved
        # room keeps a slow beat; cold and unsolved it stands still
        f"execute {solved_dome} run scoreboard players add {gov} {GOV_SOLVED}",
        f"execute unless score {open_dome} matches 2 if {lamps_up} 1.. "
        f"run {_op('gov', '+=', '#boil.n')}",
        f"execute unless score {open_dome} matches 2 unless {lamps_up} 1.. "
        f"if score {_s('gov.out')} matches 1 run function {fid('rest')}",
        f"execute if score {gov} matches {GOV_AT}.. run function {fid('govern')}",
    ]
    # steam: more places the higher the pressure
    for lamps, cell in place.steam:
        count = 6 if lamps >= BAND_TOP + 1 else 1
        dress.append(
            f"execute if {lamps_up} {lamps}.. run particle {puff} "
            f"{middle(cell, 0.5)} 0.2 0.3 0.2 0.02 {count}"
        )
    pack.function(f"{base}/dress", dress)

    # -- a step, and the hooks
    x, y, z = place.dropper
    pack.function(
        f"{base}/stock",
        [
            f"item replace block {x} {y} {z} container.0 with {COAL} 64",
            f"execute {_if_block(place.lectern, 'minecraft:lectern[has_book=false]')} "
            f"run function {fid('book')}",
        ],
    )
    pack.function(f"{base}/book", [_setblock(place.lectern, logbook(fr))])
    pack.function(
        f"{base}/step",
        [
            *(
                f"function {fid(name)}"
                for name in ("fires", "valves", "pressure", "show", "stock", "hold")
            ),
        ],
    )
    recall = recall_functions(pack, f"{base}/recall", RECALL_TAG)
    pack.function(
        f"{base}/tick",
        [
            recall,
            f"scoreboard players add {_s('tick')} 1",
            f"execute unless score {_s('tick')} matches {STEP}.. run return 0",
            _set("tick", 0),
            # the boiler house's machinery, whether or not there is a puzzle
            f"function {fid('dress')}",
            f"execute unless score {open_dome} matches 1 run return 0",
            # a room never set up has no values: a hold of no steps is held
            f"execute unless score {_s('need')} matches 1.. run function {fid('arm')}",
            f"function {fid('step')}",
        ],
    )
    pack.function(
        f"{base}/enter",
        [
            # the core's signal: the first into an empty room
            f"execute if score {open_dome} matches 1 "
            f"if score #first {OBJ} matches 1 run function {fid('arm')}",
            f"execute if score {open_dome} matches 1 run tellraw @s "
            '{text:"The fires are out. The brass plaque says what to do.",'
            'color:"gray",italic:true}',
            f"execute if score {open_dome} matches 2 run function {fid('pump_on')}",
        ],
    )
    pack.function(f"{base}/arm", [f"function {fid('reset')}", _set("live", 1)])
    pack.function(
        f"{base}/empty",
        [
            f"function {fid('pump_off')}",
            f"function {fid('rest')}",
            f"execute if score {open_dome} matches 1 run function {fid('reset')}",
            _set("live", 0),
        ],
    )

    def valve_signs(form: int) -> list[str]:
        return [
            f"data merge block {_xyz(v.sign)} {{{sign_text(valve_sign(v, form))}}}"
            for v in place.valves
        ]

    is_lever = "minecraft:lever"
    pack.function(
        f"{base}/solo",
        [
            *(_setblock(v.plate, AIR) for v in place.valves),
            *(
                f"execute {_unless_block(v.lever, is_lever)} "
                f"run {_setblock(v.lever, lever(v))}"
                for v in place.valves
            ),
            *valve_signs(1),
            f"execute if score {_s('form')} matches 2 run "
            + say("One engineer now: the valves latch. Use the levers."),
            _set("form", 1),
        ],
    )
    pack.function(
        f"{base}/duo",
        [
            *(_setblock(v.lever, AIR) for v in place.valves),
            *(
                f"execute {_unless_block(v.plate, PLATE)} "
                f"run {_setblock(v.plate, PLATE)}"
                for v in place.valves
            ),
            *valve_signs(2),
            say("Two engineers: each valve must be held. Stand on a plate each."),
            _set("form", 2),
        ],
    )
    zeroed = ("p", "hold", "lit", "open", "was", "flow", "tick", "live", "blows")
    zeroed += ("hint.cold", "hint.band", "n", "m", "m.shown", "got", "band")
    pack.function(
        f"{base}/reset",
        [
            f"function {fid('scale')}",
            _set("rise", RISE),
            *(_set(name, 0) for name in zeroed),
            *(f"scoreboard players set {b.score} {OBJ} 0" for b in place.boilers),
            *(f"scoreboard players set {v.score} {OBJ} 0" for v in place.valves),
            *(_setblock(b.furnace, furnace(fr)) for b in place.boilers),
            *(f"data merge block {_xyz(b.hopper)} {{Items:[]}}" for b in place.boilers),
            *(_setblock(v.lamp, f"{BULB}[lit=false]") for v in place.valves),
            *(_setblock(v.plate, AIR) for v in place.valves),
            *(_setblock(v.lever, lever(v)) for v in place.valves),
            *valve_signs(1),
            _set("form", 1),
            f"function {fid('gauge')}",
            f"function {fid('main')}",
            f"function {fid('pump_off')}",
            f"function {fid('rest')}",
            f"function {fid('stock')}",
            f"kill @e[type=minecraft:item,{domes.sphere(dome)}]",
        ],
    )


# --------------------------------------------------------------- the check

S1, S2 = "st.b1", "st.b2"


def check(ctx: Any) -> list[str]:
    """
    Work the Boiler Room in place over RCON (see ``PROGRESS.md`` for what
    this does not prove). A player is stood in for by an armour stand that
    the core counts (``game.STANDIN``): it is put at the entrance to come
    in, and on a valve's plate to hold it; a lever is thrown, the bunker's
    button pressed and the recall button clicked by setting the block or
    the entity as a hand would leave it. Leaves the room and its tunnel
    reset, dome 1 locked again and no stand-in behind.
    """
    game_checks.no_run(ctx)
    dome = ctx.layout.DOMES[INDEX]
    tunnel = ctx.layout.TUNNELS[INDEX]
    place = room(dome)
    fr = place.frame
    problems: list[str] = []
    scan = game_checks.SCAN
    base = f"dome/{INDEX}"

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def get(name: str) -> int:
        return ctx.score(f"#boil.{name}") or 0

    outside = middle(tunnels.at(ctx.layout.TUNNELS[INDEX - 1], 8, 0, 1))
    entrance = middle(domes.entrance(dome)[:3])

    def stand(tag: str, where: str) -> None:
        """a stand-in with a body and a weight, which presses a plate"""
        game_checks.stand_at(ctx, tag, where, gravity=True)

    def come_in(tag: str = S1) -> None:
        """a stand-in out of the dome and in again: a new entry"""
        stand(tag, outside)
        ctx.advance(game_checks.EMPTY)  # (a dome is empty 3 s after its last player)
        stand(tag, entrance)

    def throw(valve: Valve, on: bool) -> None:
        ctx.setblock(valve.lever, lever(valve, on))

    def feed(coals: int = 8) -> None:
        for boiler in place.boilers:
            ctx.cmd(
                f"item replace block {_xyz(boiler.hopper)} container.0 "
                f"with {COAL} {coals}"
            )

    def lamps_lit(cells: tuple[Cell, ...]) -> int:
        return sum(
            ctx.is_block(c, f"{BULB}[lit=true]")
            or ctx.is_block(c, f"{BAND_BULB}[lit=true]")
            for c in cells
        )

    def as_built(what: str) -> None:
        """every block of the room is as ``reset`` leaves it (a block of a
        clock that runs by itself: the same block, in whatever state)"""
        b = room_blocks(dome, get("lo"))
        wrong = [
            cell
            for cell, block in b.everything().items()
            if not ctx.is_block(
                cell, _name(block) if cell in b.moving else block.partition("{")[0]
            )
        ]
        wrong += [cell for cell in b.clear | b.swept if not ctx.is_block(cell, AIR)]
        if wrong:
            problems.append(f"{what}: {len(wrong)} blocks not as built: {wrong[:6]}")
        names = ("p", "hold", "f0", "f1", "lit", "open", "live", "n", "m")
        got = {n: get(n) for n in names}
        expect(f"{what}: the scores", got, dict.fromkeys(names, 0))
        for boiler in place.boilers:
            if ctx.data(f"block {_xyz(boiler.hopper)} Items") not in ("", "[]"):
                problems.append(f"{what}: boiler {boiler.name}'s chute is not empty")
        if not ctx.test(
            f"execute if items block {_xyz(place.dropper)} container.0 {COAL}"
        ):
            problems.append(f"{what}: the bunker's dropper has no coal")

    def chaser_runs(what: str) -> None:
        """the lamp chaser, which nothing starts or stops: each of its
        four lamps seen lit and unlit over 6 s"""
        seen: list[set[bool]] = [set() for _ in place.chaser]
        for _ in range(30):
            ctx.advance(4)
            for cell, states in zip(place.chaser, seen, strict=True):
                states.add(ctx.is_block(cell, f"{BULB}[lit=true]"))
        if any(states != {True, False} for states in seen):
            problems.append(f"{what}: the lamp chaser's lamps, lit or not: {seen}")

    def strokes(ticks: int) -> tuple[int, set[bool]]:
        """the governor over some ticks: how many strokes it made, and
        whether its first piston was seen out, in or both"""
        before, seen = get("strokes"), set()
        for _ in range(ticks // 4):
            ctx.advance(4)
            seen.add(ctx.is_block(place.governor[0], "minecraft:piston[extended=true]"))
        return get("strokes") - before, seen

    def work(valves: Any, until: Any, limit: int = 4000) -> bool:
        """keep the pressure in the band as a player would, opening and
        shutting with ``valves(on)``, until ``until()`` or ``limit`` ticks"""
        lo = get("lo")
        low, high = lo + (BAND_HI - lo) // 3, BAND_HI - (BAND_HI - lo) // 3
        is_on = None
        for _ in range(limit // STEP):
            if until():
                return True
            p = get("p")
            want = True if p < low else False if p > high else is_on
            if want is not None and want != is_on:
                valves(want)
                is_on = want
            ctx.advance(STEP)
        return until()

    def levers(on: bool) -> None:
        # the far valve stays open; the near one is worked
        throw(place.valves[0], True)
        throw(place.valves[1], on)

    def plates(on: bool) -> None:
        stand(S2, middle(place.valves[1].plate if on else place.coal_out))

    def solved() -> bool:
        return ctx.score(f"#d{INDEX}") == 2

    def unsolve() -> None:
        """the room and its tunnel put back, the dome open and unsolved"""
        ctx.function(f"tunnel/{INDEX}/reset")
        ctx.function(f"{base}/reset")
        ctx.set_score(f"#d{INDEX}", 1)
        ctx.set_score(f"#d{INDEX + 1}", saved[f"#d{INDEX + 1}"] or 0)
        ctx.set_score("#solved", saved["#solved"] or 0)

    # ---- before: nobody about, the room and its tunnel reset, the dome open
    names = (f"#d{INDEX}", f"#d{INDEX + 1}", "#solved", "#level")
    saved = game_checks.scores(ctx, *names)
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan)
    if (others := ctx.score("#players")) or ctx.score(f"#form{INDEX}"):
        return [f"{others} players or stand-ins of another check are in the game"]
    ctx.function(f"{base}/reset")
    unsolve()
    ctx.advance(scan)
    as_built("built")
    chaser_runs("nobody in")
    expect("the governor with nobody in", strokes(40), (0, {False}))
    if ctx.count(f"@e[type=minecraft:interaction,tag={RECALL_TAG}]") != 1:
        problems.append("not one recall button's interaction entity")
    if "Marsh" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("the logbook is not on the lectern")

    # ---- solo, the success path: in, coal, fires, valves, the band held
    stand(S1, entrance)
    got = {n: get(n) for n in ("live", "form")}
    expect("solo, entered", got, {"live": 1, "form": 1})
    level = ctx.score("#active") or game.DEFAULT_LEVEL
    expect("the level's values", {n: get(n) for n in scaled(level)}, scaled(level))
    # the bunker: the button pressed, a coal out of the dropper
    # (a button set pressed tells only its own neighbours; a hand's press
    # tells the block it is on as well, so the dropper is told here)
    button = room_blocks(dome).attached[place.coal_button]
    above = (place.dropper[0], place.dropper[1] + 1, place.dropper[2])
    lintel = room_blocks(dome).solid[above]
    for pressed, ticks in ((button.replace("]", ",powered=true]"), 12), (button, 4)):
        ctx.setblock(place.coal_button, pressed)
        ctx.setblock(above, "minecraft:stone")
        ctx.setblock(above, lintel)
        ctx.advance(ticks)
    x, y, z = place.coal_out
    coal = f'@e[type=minecraft:item,nbt={{Item:{{id:"{COAL}"}}}}'
    near = f"{coal},x={x},y={y},z={z},distance=..6]"
    expect("coal out of the bunker at a press", ctx.count(near), 1)
    # dropped on boiler A's chute, the hopper draws it in; B's is put in
    a, b = place.boilers
    ctx.cmd(f"tp {near[:-1]},limit=1] {middle(a.hopper, 1.1)}")
    ctx.cmd(f"item replace block {_xyz(b.hopper)} container.3 with {COAL} 8")
    ctx.advance(30)
    if not (get("f0") and get("f1") and get("lit") == 2):
        got = {n: get(n) for n in ("f0", "f1", "lit")}
        problems.append(f"the fires after coal in both chutes: {got}")
    for boiler in place.boilers:
        if not ctx.is_block(boiler.furnace, "minecraft:furnace[lit=true]"):
            problems.append(f"boiler {boiler.name}'s furnace is not lit")
    ctx.cmd(f"item replace block {_xyz(a.hopper)} container.1 with {COAL} 8")
    # the feed pump runs: each piston seen out and in
    seen: tuple[set[bool], set[bool]] = (set(), set())
    for _ in range(30):
        ctx.advance(4)
        for piston, states in zip(place.pistons, seen, strict=True):
            states.add(ctx.is_block(piston, "minecraft:piston[extended=true]"))
    if seen != ({True, False}, {True, False}):
        problems.append(f"the feed pump's pistons, out or in over 6 s: {seen}")
    # no valve, then one valve: no pressure
    expect("fires lit, valves shut: pressure", get("p"), 0)
    expect("the governor, fires lit and no pressure", strokes(40), (0, {False}))
    throw(place.valves[0], True)
    ctx.advance(4 * STEP)
    got = {n: get(n) for n in ("v0", "v1", "open", "p")}
    expect("one valve open", got, {"v0": 1, "v1": 0, "open": 0, "p": 0})
    lamps = [ctx.is_block(v.lamp, f"{BULB}[lit=true]") for v in place.valves]
    expect("the valves' lamps, one open", lamps, [True, False])
    # both: it climbs, the gauge follows it, and held in the band it solves
    throw(place.valves[1], True)
    ctx.advance(6 * STEP)
    if get("p") <= 0:
        problems.append("both valves open, fires lit: the pressure did not rise")
    most = 0
    rung, swung, rings = set(), set(), get("rings")
    beat, pumped = get("strokes"), set()

    def watch() -> bool:
        nonlocal most
        most = max(most, get("m"))
        rung.add(ctx.is_block(place.bell_power, POWER))
        swung.add(ctx.is_block(place.bell, "minecraft:bell[powered=true]"))
        for piston in place.governor:
            pumped.add(ctx.is_block(piston, "minecraft:piston[extended=true]"))
        return solved()

    if not work(levers, watch):
        got = {n: get(n) for n in ("p", "hold", "need", "lit")}
        problems.append(f"solo: not solved by holding the band: {got}")
    expect("the main's lamps seen lit before it was solved", most >= 3, True)
    expect("the safety valve in the solo run", get("blows"), 0)
    # the machinery followed it: the bell at the main's lamps, the governor
    if get("rings") - rings < MAIN_LAMPS - 1 or rung != swung or rung != {True, False}:
        problems.append(
            f"the bell in the solo run: rung {get('rings') - rings} times, its "
            f"power seen on or off: {rung}, the bell powered or not: {swung}"
        )
    if get("strokes") - beat < 10 or pumped != {True, False}:
        problems.append(
            f"the governor in the solo run: {get('strokes') - beat} strokes, "
            f"its pistons seen out or in: {pumped}"
        )
    # solved: the tunnel's pump event, the next dome open, the room steady
    expect("tunnel 1 at the solve", ctx.score(f"#t{INDEX}") in (1, 2), True)
    wait = tunnels.event_ticks(tunnel) + 60
    ctx.advance(wait)
    got = game_checks.scores(ctx, f"#t{INDEX}", f"#d{INDEX + 1}")
    expect("tunnel 1 open, dome 2 open", got, {f"#t{INDEX}": 2, f"#d{INDEX + 1}": 1})
    doors = [c for d in tunnels.ends(tunnel) for _, c in domes.door_cells(d, tunnel)]
    expect("door cells open", sum(ctx.is_block(c, AIR) for c in doors), len(doors))
    expect("solved: the gauge", lamps_lit(place.gauge), BAND_TOP)
    expect("solved: the main", lamps_lit(place.main), MAIN_LAMPS)
    problems += [f"tunnel open: {p}" for p in domes.check_shell(ctx, dome, False)]
    # a second entry leaves a solved room solved and steady
    come_in()
    ctx.advance(4 * STEP)
    expect("solved, entered again: the dome", ctx.score(f"#d{INDEX}"), 2)
    expect("solved, entered again: the gauge", lamps_lit(place.gauge), BAND_TOP)
    expect("solved, entered again: the main", lamps_lit(place.main), MAIN_LAMPS)
    expect("solved, entered again: set up anew", get("live"), 0)
    lit = [ctx.is_block(x.furnace, "minecraft:furnace[lit=true]") for x in (a, b)]
    expect("solved, entered again: the furnaces still lit", lit, [True, True])
    # the solved room's slow beat while someone is in it, and none after
    made, seen_out = strokes(80)
    want = 80 // STEP * GOV_SOLVED // GOV_AT
    if not want - 1 <= made <= want + 1 or seen_out != {True, False}:
        problems.append(f"solved: the governor made {made} strokes in 4 s: {seen_out}")
    stand(S1, outside)
    ctx.advance(game_checks.EMPTY)  # (a dome is empty 3 s after its last player)
    expect("solved, nobody in: the governor", strokes(40), (0, {False}))
    expect(
        "solved, nobody in: the bell's power",
        ctx.is_block(place.bell_power, COPPER),
        True,
    )

    # ---- solo, the failure paths, and getting back from each
    unsolve()
    come_in()
    expect("unsolved, entered again: set up anew", get("live"), 1)
    expect("unsolved, entered again: the gauge", lamps_lit(place.gauge), 0)
    # too much steam: the safety valve
    feed()
    levers(True)
    for _ in range(120):
        if get("blows"):
            break
        ctx.advance(2 * STEP)
    got = {n: get(n) for n in ("blows", "hold")}
    expect("valves left open: the safety valve", got, {"blows": 1, "hold": 0})
    if not 0 < get("p") < scaled(level)["lo"]:
        problems.append(f"the pressure after the safety valve: {get('p')}")
    on = [ctx.is_block(v.lever, lever(v, True)) for v in place.valves]
    expect("the levers after the safety valve", on, [False, False])
    expect("the dome after the safety valve", ctx.score(f"#d{INDEX}"), 1)
    # the governor follows the pressure: slow at 2 lamps, fast at 8 (the
    # pressure set, the valves shut, 4 s each)
    levers(False)
    rates = []
    for lamps in (2, BAND_TOP):
        ctx.set_score("#boil.p", lamps * LAMP + LAMP - 1)
        ctx.advance(2 * STEP)
        rates.append(strokes(80)[0])
    if not 0 < rates[0] < rates[1]:
        problems.append(f"the governor's strokes in 4 s at 2 and 8 lamps: {rates}")
    ctx.set_score("#boil.p", P_AFTER_BLOW)
    ctx.set_score("#boil.hold", 0)
    # neglect: the fires burn out, the pump stops, the pressure falls
    for boiler in place.boilers:
        ctx.cmd(f"data merge block {_xyz(boiler.hopper)} {{Items:[]}}")
        ctx.set_score(boiler.score, 2)
    levers(True)
    ctx.advance(10 * STEP)
    before = get("p")
    ctx.advance(10 * STEP)
    expect("the fires burnt out", get("lit"), 0)
    if not 0 < get("p") < before:
        problems.append(f"fires out: the pressure went {before} to {get('p')}")
    unlit = [ctx.is_block(x.furnace, "minecraft:furnace[lit=false]") for x in (a, b)]
    expect("the furnaces, burnt out", unlit, [True, True])
    expect("the feed pump's torch, fires out", ctx.is_block(place.torch, AIR), True)
    expect("the dome, fires out", ctx.score(f"#d{INDEX}"), 1)
    # back from both: coal again, and the band held charges the main
    feed()
    if not work(levers, lambda: get("hold") >= 5, 1500):
        problems.append(f"after a failure the main did not charge: {get('p')}")
    # out of the band (the pressure put just under it) the charge goes
    levers(False)
    ctx.set_score("#boil.p", get("lo") - 300)
    ctx.advance(8 * STEP)
    expect("out of the band for 2 s: the charge", get("hold"), 0)
    expect("the dome, the charge lost", ctx.score(f"#d{INDEX}"), 1)

    # ---- duo: two valves held at once
    come_in()
    stand(S2, entrance)
    ctx.advance(scan)
    expect("two in: the dome's form", ctx.score(f"#form{INDEX}"), 2)
    expect("two in: the form", get("form"), 2)
    shape = [
        (ctx.is_block(v.plate, PLATE), ctx.is_block(v.lever, AIR)) for v in place.valves
    ]
    expect("duo: plates down, levers gone", shape, [(True, True)] * 2)
    feed()
    ctx.advance(4 * STEP)
    stand(S1, middle(place.valves[0].plate))
    ctx.advance(12 * STEP)
    got = {n: get(n) for n in ("v0", "v1", "open", "p", "hold")}
    want = {"v0": 1, "v1": 0, "open": 0, "p": 0, "hold": 0}
    expect("duo: one valve held for 3 s", got, want)
    expect("duo: one valve held does not solve it", solved(), False)
    # a coal on the other plate does not hold it
    x, y, z = place.valves[1].plate
    ctx.cmd(
        f"summon minecraft:item {middle(place.valves[1].plate, 0.2)} "
        f'{{Item:{{id:"{COAL}",count:1}}}}'
    )
    ctx.advance(6 * STEP)
    expect("duo: a coal on the other plate", get("v1"), 0)
    ctx.cmd(f"kill {coal},x={x},y={y},z={z},distance=..2]")
    if not work(plates, solved):
        got = {n: get(n) for n in ("p", "hold", "need", "lit", "v0", "v1")}
        problems.append(f"duo: not solved with both valves held: {got}")
    expect("duo solved: tunnel 1", ctx.score(f"#t{INDEX}") in (1, 2), True)

    # ---- duo, and one leaves in the middle: solo, and not stuck
    unsolve()
    stand(S2, outside)
    come_in()
    stand(S2, entrance)
    ctx.advance(scan)
    expect("two in again: the form", get("form"), 2)
    feed()
    stand(S1, middle(place.valves[0].plate))
    stand(S2, middle(place.valves[1].plate))
    for _ in range(60):
        if get("p") >= 3 * LAMP:
            break
        ctx.advance(2 * STEP)
    part = get("p")
    if part < 3 * LAMP:
        problems.append(f"duo: both valves held, the pressure only reached {part}")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan)
    expect("one left: the dome's form", ctx.score(f"#form{INDEX}"), 1)
    expect("one left: the form", get("form"), 1)
    shape = [
        (ctx.is_block(v.plate, AIR), ctx.is_block(v.lever, lever(v)))
        for v in place.valves
    ]
    expect("one left: plates gone, levers back and shut", shape, [(True, True)] * 2)
    expect("one left: the room not set up anew", get("live"), 1)
    if not 0 < get("p") <= part + 20 * RISE:
        problems.append(f"one left: the pressure went from {part} to {get('p')}")
    if not work(levers, solved):
        got = {n: get(n) for n in ("p", "hold", "need", "lit")}
        problems.append(f"after one left: not solved solo: {got}")

    # ---- the recall button: a click on it is taken up
    click = f"@e[type=minecraft:interaction,tag={RECALL_TAG},limit=1]"
    ctx.cmd(
        f"data modify entity {click} interaction set value "
        "{player:[I;1,2,3,4],timestamp:0L}"
    )
    ctx.advance(4)
    left = ctx.data(f"entity {click} interaction")
    expect("the recall button's click, 4 ticks on", left, "")

    # ---- difficulty: the values of the level, on a new entry
    unsolve()
    for new in (game.LEVELS[0], game.LEVELS[-1]):
        ctx.set_score("#level", new)
        come_in()
        want = scaled(new)
        expect(f"level {new}: the values", {n: get(n) for n in want}, want)
        kinds = [
            ctx.is_block(c, gauge_bulb(k, want["lo"]))
            for k, c in enumerate(place.gauge, 1)
        ]
        expect(f"level {new}: the gauge's green lamps", all(kinds), True)
    ctx.set_score("#level", saved["#level"] or game.DEFAULT_LEVEL)
    ctx.function("difficulty/apply")

    # ---- reset, from a scrambled state
    feed()
    ctx.cmd(f"item replace block {_xyz(a.hopper)} container.4 with minecraft:arrow 3")
    ctx.function(f"{base}/duo")
    stand(S1, middle(place.valves[1].plate))
    for name, value in (("p", 7777), ("hold", 20), ("blows", 3), ("f0", 500)):
        ctx.set_score(f"#boil.{name}", value)
    ctx.setblock(place.lectern, f"minecraft:lectern[facing={fr.facing(-1, 0)}]")
    ctx.advance(3 * STEP)
    if "Marsh" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("a logbook taken from the lectern was not put back")
    ctx.function(f"{base}/ring")
    governor_out = strokes(40)
    if (
        lamps_lit(place.gauge) < 6
        or not ctx.is_block(place.torch, "minecraft:redstone_wall_torch")
        or governor_out[0] < 1
    ):
        problems.append("the room was not scrambled before the reset")
    ctx.function(f"{base}/ring")
    ctx.function(f"{base}/reset")
    ctx.set_score(f"#d{INDEX}", 0)  # locked, so that nothing runs after it
    ctx.advance(STEP)  # a piston takes a tick or two to come in
    as_built("reset from a scrambled state")

    # ---- after: nobody, the tunnel shut and flooded, the dome dry
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.function(f"tunnel/{INDEX}/reset")
    for name in names:
        ctx.set_score(name, saved[name] or 0)
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan)
    ctx.function(f"{base}/reset")
    ctx.advance(100)
    as_built("left")
    chaser_runs("left")
    expect("the governor, left", strokes(40), (0, {False}))
    got, want = tunnels.counts(ctx, tunnel), tunnels.expected(tunnel, 0)
    expect("tunnel 1 left shut and flooded", got, want)
    problems += [f"left: {p}" for p in domes.check_shell(ctx, dome, False)]
    expect(
        "stand-ins left behind",
        ctx.count(f"@e[tag={S1}]") + ctx.count(f"@e[tag={S2}]"),
        0,
    )
    return problems


MODULE = game.Module(
    "boiler",
    stages={f"dome_{INDEX}_inside": build},
    functions=functions,
    checks={"boiler_room": check},
)
