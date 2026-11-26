"""
The Foundry (dome 4) of The Drowned Station: the first fight. Its build
stage (``dome_4_inside``), its datapack functions (``dome/4/...``) and its
live check (``foundry``).

**The fight.** Hold the room while a machine charges. A lever on the mast
in the middle of the dome, the MAIN SWITCH, starts it: the accumulator (the
mast: twelve cells of four lamps, and a bossbar) charges while all three
breakers are closed, and the Foundry casts automatons from its two moulds
and the rivet loft to stop it. As the charge passes each quarter a breaker
trips (its lever thrown back, its lamp out, its label red) and the charge
stands still until someone closes it by hand; the three breakers are on
three levels (the casting floor, the gallery, the top deck), so somebody
always has to go somewhere. The twelfth cell ends it: every automaton
drops, the bus bar in the floor lights to the exit, and the pump runs.
Nothing depends on a kill, and nothing ends the run.

- *Solo:* one breaker trips at each quarter: A (floor), B (gallery), C
  (top deck), so the fight climbs the room.
- *Duo:* two trip at once, on two levels: A and B, B and C, C and A; and
  the waves and the cap of automatons alive are the two-player ones.
  Neither breaker needs holding, so one player can always close both.

**The two rules** (game.py). *Leaving is a checkpoint*: when the dome
empties in the fight (3 s after the last player went) the automatons go,
the charge falls back to the last quarter reached, the breakers stay as
they were left (leaving answers no trip), the switch stays thrown, and the
fight goes on 5 s after someone walks in, at the level then in force
(``checkpoint``, ``resume``). A death costs a cell of charge, never more
than the quarter in progress. *A change of form waits*: ``solo`` and
``duo`` only record the form; it takes force at the next trip and the next
wave, and nothing a player is using is touched. The one thing ``solo``
does at once is a kindness: if two breakers are out, the second closes
itself.

**Real inputs, datapack brain.** The switch and the breakers are real
levers on brass, each with a sign; the functions read them and do the
rest. The automatons, their kit, the deaths, the team and the reading of
Peaceful are the core's (automatons.py, game.py): this module only says
where and how many.

**State** (scores in ``st``, all ``#fdy.<name>``): ``state`` 0 idle, 1
fighting, 2 charged; ``charge`` 0 to ``FULL`` (a cell is ``CELL``);
``stage`` the trips done, 0 to 3, and ``floor`` the charge at the last
of them; ``b0`` ``b1`` ``b2`` each breaker as read (1 closed) and
``closed`` how many; ``form`` 1 solo, 2 duo; ``wait`` ticks until a fight
left and come back to goes on; ``next`` ticks to the next wave; ``bus``
the bus bar's lamps as they light; ``live`` 1 once the room has been set
up for those in it. From the level in force when the room is set up
(``scaled``): ``rate`` (charge a step), ``gap`` (ticks between waves),
``pen`` (what a death costs).

**Functions** (the core calls the hooks, see game.py):

- ``enter``: the first into an unsolved, idle room sets it up anew
  (``arm``: ``reset``, with the level's values); into a fight left at a
  checkpoint, the countdown to ``resume``; into a solved room,
  ``restored``;
- ``tick``: the ladle; the waves' clock (``warn`` 2 s before ``cast``);
  and every ``STEP`` ticks ``step``: ``switch`` -> ``breakers`` ->
  ``charge`` (which calls ``trip_stage`` and ``done``) -> ``show``, then
  the leash and the sweep. ``done`` is the one caller of
  ``station:dome/4/solved``;
- ``solo`` / ``duo``: the form recorded (and the relief relay);
- ``died``: a cell of charge lost, not below the last quarter;
- ``empty``: ``checkpoint`` in a fight, ``reset`` of an idle room;
- ``reset``: everything as built.

There is no ``leave`` hook: the room lends nothing (the Foundry's kit is
the core's, given on entering), and what a player's going changes is the
form, which the core tells by ``solo``.

**Places.** Everything is placed in the dome's own frame (``Frame``:
forward from the entrance, right, up from the floor); nothing here is a
world coordinate. ``room_problems`` runs the shared checks of the plan
(rooms.py, fittings.py) and the build refuses a plan that fails one.

**The foundry** (``dressing_blocks``: what makes the room a place). A
black casting floor with glowing channels; the dais and the mast, its
crown chained to the top of the glass; a gallery of copper grating six up,
a horseshoe from the west ladder round the north and east to above the
entrance (the south-west is open: the way to the exit, and where the
ladle pours), reached by two stairs; a gantry twelve up, a bridge through
the mast with the tuning deck round it, reached by two ladders from the
gallery; two black moulds big enough to walk into, the cupola furnace with
the rivet loft on top, two chimneys. Machinery that works by itself:

- the *stamp battery* on the north mould's roof, behind bars: the shared
  torch clock (``fittings.torch_clock``), real redstone, always running:
  two plain pistons strike a die bar in turn, and its four lamps blink in
  the mould's roof;
- the *ladle crane*: four block displays that travel a rail under the
  roof and pour a thread of fire on the pouring floor, moved by the
  function ``crane`` while anyone is in the dome, twice as fast in the
  fight; ``rest`` parks it (``reset``, ``empty``).

Neither has a lever, button or plate, and no function of the fight reads
either. Every input is on brass (gold) with a sign; nothing else is.
"""

from __future__ import annotations

import math
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
from domes import AIR, Cell, middle
from fittings import Frame, frame, label_text, snbt

if TYPE_CHECKING:
    from station_layout import Dome

INDEX = 4  # the Foundry's place in the ring
OBJ = game.OBJ

STEP = 10  # ticks between steps of the state machine
CELLS = 12  # the mast's cells
CELL = 2000  # charge a cell
FULL = CELL * CELLS
QUARTER = FULL // 4  # a breaker trips at each
TRIPS = 3
# at level 5, scaled by the core's percentages (``scaled``)
RATE = 75  # charge a step: 160 s to full with no breaker out
GAP = 400  # ticks between waves
PENALTY = CELL  # what a death costs
LAST_GAP = (3, 4)  # the gap in the last quarter, as a fraction
WARN = 40  # ticks of warning before a wave
FIRST = 100  # ticks from the switch (or a fight going on again) to a wave
RESUME = 100  # ticks from someone walking in to a left fight going on
FOLLOW = 48  # an automaton's follow range: the dome, on any level
#: a wave by the dome's form: (solo, duo, more for each player beyond two),
#: put through the core's ``mob/count``
CAP = (6, 10, 2)  # automatons alive
STOKERS = (2, 3, 1)  # a wave, from the first
RIVETERS = (1, 2, 0)  # a wave, from the second quarter
RIVETER_CAP = (2, 3, 0)  # Riveters alive
HUSKS = (1, 2, 0)  # a wave, from the third quarter
#: the most automatons the waves' functions can cast in one go
MOST = 24
#: which breakers trip at each stage, by form
TRIP = {
    1: {1: (0,), 2: (1,), 3: (2,)},
    2: {1: (0, 1), 2: (1, 2), 3: (2, 0)},
}
#: the breaker that closes itself when a pair is out and one player goes
RELIEF = {stage: pair[1] for stage, pair in TRIP[2].items()}

BRASS = fittings.BRASS
COPPER = "minecraft:waxed_copper_block"
CUT = fittings.CUT
CHISELED = fittings.CHISELED
EXPOSED = "minecraft:waxed_exposed_copper"
WEATHERED = "minecraft:waxed_weathered_copper"
BULB = "minecraft:waxed_copper_bulb"
GRATE = "minecraft:waxed_copper_grate"
BARS = "minecraft:iron_bars"
ROD = "minecraft:waxed_lightning_rod"
CHAIN = "minecraft:iron_chain"
STAIRS = "minecraft:waxed_cut_copper_stairs"
SLAB = "minecraft:waxed_cut_copper_slab"
BLACK = "minecraft:polished_blackstone"
BRICKS = "minecraft:polished_blackstone_bricks"
TIMBER = "minecraft:dark_oak_planks"
HOT = "minecraft:shroomlight"  # metal that glows
COOL = "minecraft:orange_terracotta"  # metal that has set
LADDER = "minecraft:ladder"
ENTITY_TAG = "st.d4"  # everything this module summons (no reset kills it)
LADLE_TAG = "st.d4.ladle"
SWITCH_TAG = "st.d4.switch"


# ---------------------------------------------------------------- the room
# where things are, in the frame: (forward, right)

DAIS = 4  # the dais reaches this far each way from the middle
MAST_BASE = (2, 4)  # the mast's foot, from and to this height
MAST_H = 5  # its first cell; the twelfth is at MAST_H + 11
PLAQUE = (-15, 3)
LECTERN = (-15, 6)
RECALL = (-19, 3, -1)  # the recall post: f, r, the side its button is on
#: the gallery: a ring this far from the middle, a kerb each side of it
RING = (13.5, 16.5)
DECK_H = 6  # its deck; feet are a block above
GANTRY_H = 12  # the bridge and the tuning deck
LADDER_R = 16  # the ladders, right and left of the mast
TUNING = 3  # the tuning deck reaches this far each way
#: the stairs to the gallery: (f of its two rows, r of its foot, the way
#: it climbs along r)
STAIRWAYS = (((-9, -8), 7, 1), ((8, 9), -7, -1))
#: (the top tread level with the deck: no full block's step onto it)
TREADS = DECK_H
COLUMNS = ((6, 14), (14, 6), (6, -14), (14, -6), (-6, 14), (-14, 6))
HANGERS = ((16, 6), (6, 16), (-6, 16), (-16, 6), (16, -6), (6, -16))
#: lit lamps set in the gallery's inner edge, to light it above and below
RING_LAMPS = ((13, 0), (0, 13), (9, 9), (9, -9), (-13, 3))
#: the moulds: the middle of each one's open front, and the way in
MOULDS = {"north": ((18, 0), (1, 0)), "east": ((0, 18), (0, 1))}
MOULD_DEPTH, MOULD_HALF, MOULD_ROOF = 5, 3, 4
CUPOLA = (13, 13)  # the cupola furnace's middle; the loft is on top
CHIMNEYS = ((17, -6), (17, 6))
CHIMNEY_TOP = 12
CRANE = (-7, 17)  # the crane rail: its f and its height
CRANE_R = (-12, 12)
LADLE_R = (11, -10)  # the ladle's ends: east (parked) and west (pouring)
LADLE_H = 14
POUR = tuple((f, r) for f in (-9, -7, -5) for r in (-12, -10, -8))
BUS_R = (-5, -20)  # the bus bar, from the dais to the exit
#: the breakers: name, level, the post's (f, r, h), the way its lever faces
#: (a step of the frame)
BREAKERS = (
    ("A", "floor", (12, -18, 1), (0, 1)),
    ("B", "gallery", (-12, 12, DECK_H + 1), (0, -1)),
    ("C", "top deck", (3, 3, GANTRY_H + 1), (0, -1)),
)
# the ladle's loop, in ticks
TRAVEL = (LADLE_R[0] - LADLE_R[1]) * 8  # an eighth of a block a tick
PAUSE = 60
PERIOD = 2 * (TRAVEL + PAUSE)


@dataclass(frozen=True)
class Breaker:
    """a breaker: a lever on a brass post, a lamp on top, a label over it"""

    index: int
    name: str
    level: str
    post: fittings.Post
    lever: Cell
    lamp: Cell
    stand: Cell  # where a player stands to work it
    facing: str
    label: tuple[float, float, float]

    @property
    def tag(self) -> str:
        return f"st.d4.brk{self.index}"

    @property
    def score(self) -> str:
        return f"#fdy.b{self.index}"

    def block(self, closed: bool) -> str:
        return fittings.lever(self.facing, closed)


@dataclass(frozen=True)
class Room:
    """where the Foundry's working parts are"""

    frame: Frame
    switch: Cell  # the main switch's lever
    switch_on: Cell  # the brass it is on
    switch_facing: str
    switch_stand: Cell
    mast: tuple[tuple[Cell, ...], ...]  # four columns of lamps, lowest first
    mast_faces: tuple[tuple[Cell, ...], ...]  # the cell in front of each lamp
    breakers: tuple[Breaker, Breaker, Breaker]
    bus: tuple[Cell, ...]  # the bus bar's lamps, nearest the mast first
    telltales: tuple[Cell, ...]  # the moulds' lamps: lit when a wave is near
    stokers: tuple[Cell, Cell]  # where each kind is cast
    husks: tuple[Cell]
    riveters: tuple[Cell]
    lectern: Cell
    recall: tuple[int, int, int]
    crown: Cell  # where the crown crackles
    # the machinery (no part of the fight)
    machine: fittings.Machine  # the stamp battery
    ladle: tuple[Cell, Cell]  # its ends: east (parked), west (pouring)
    pour: tuple[Cell, ...]  # the pouring floor's moulds
    smoke: tuple[Cell, ...]  # the chimneys' tops


def mould_cell(fr: Frame, name: str, depth: int, across: int, h: int) -> Cell:
    """a cell of a mould: ``depth`` in from its open front (0 the
    threshold), ``across`` it (-3 .. 3), ``h`` above the floor"""
    (f, r), (df, dr) = MOULDS[name]
    return fr.at(f + depth * df - across * dr, r + depth * dr + across * df, h)


def battery_frame(fr: Frame) -> Frame:
    """the frame the stamp battery is laid out in: its clock runs across
    the north mould's roof, so its forward is the room's right"""
    return Frame(fr.origin, fr.right, (-fr.forward[0], -fr.forward[1]))


@cache
def room(dome: Dome) -> Room:
    fr = frame(dome)
    back = fr.facing(-1, 0)
    breakers = []
    for i, (name, level, (f, r, h), (df, dr)) in enumerate(BREAKERS):
        facing = fr.facing(df, dr)
        post = fittings.input_post(
            fr.at(f, r, h),
            facing,
            fittings.lever(facing, True),
            (f"BREAKER {name}", "Lamp out?", "Throw the", "lever."),
        )
        x, y, z = fr.at(f, r, h + 3)
        breakers.append(
            Breaker(
                i,
                name,
                level,
                post,
                post.input,
                (x, y, z),
                fr.at(f + df, r + dr, h),
                facing,
                (x + 0.5, y + 1.3, z + 0.5),
            )
        )
    faces = ((-1, 0), (0, -1), (0, 1), (1, 0))
    mast = tuple(
        tuple(fr.at(df, dr, MAST_H + k) for k in range(CELLS)) for df, dr in faces
    )
    mast_faces = tuple(
        tuple(fr.at(2 * df, 2 * dr, MAST_H + k) for k in range(CELLS))
        for df, dr in faces
    )
    lights = domes.light_cells(dome)[0]
    bus = tuple(
        cell
        for r in range(BUS_R[0], BUS_R[1] - 1, -1)
        if (cell := fr.at(0, r, 0)) not in lights
    )
    telltales = tuple(
        mould_cell(fr, name, 0, side * MOULD_HALF, 3)
        for name in MOULDS
        for side in (-1, 1)
    )
    cf, ch = CRANE
    # the stamp battery: on the north mould's roof, its pistons to the front
    (mf, _), _ = MOULDS["north"]
    machine = fittings.torch_clock(
        battery_frame(fr), 0, -(mf + 2), MOULD_ROOF + 1, 1, lamps=True, pistons=True
    )
    return Room(
        frame=fr,
        switch=fr.at(-2, 0, 3),
        switch_on=fr.at(-1, 0, 3),
        switch_facing=back,
        switch_stand=fr.at(-3, 0, 2),
        mast=mast,
        mast_faces=mast_faces,
        breakers=(breakers[0], breakers[1], breakers[2]),
        bus=bus,
        telltales=telltales,
        stokers=(mould_cell(fr, "north", 2, -1, 1), mould_cell(fr, "east", 2, 0, 1)),
        husks=(mould_cell(fr, "north", 2, 1, 1),),
        riveters=(fr.at(*CUPOLA, DECK_H + 1),),
        lectern=fr.at(*LECTERN, 1),
        recall=RECALL,
        crown=fr.at(0, 0, MAST_H + CELLS + 1),
        machine=machine,
        ladle=(fr.at(cf, LADLE_R[0], LADLE_H), fr.at(cf, LADLE_R[1], LADLE_H)),
        pour=tuple(fr.at(f, r, 0) for f, r in POUR),
        smoke=tuple(fr.at(f, r, CHIMNEY_TOP + 2) for f, r in CHIMNEYS),
    )


def scaled(level: int) -> dict[str, int]:
    """the room's values at a level, as the function ``scale`` works them
    out: at a low level the mast charges faster, the waves come further
    apart and a death costs less"""
    core = game.scaled(level)
    t = core["#diff.timer"] + 100
    return {
        "rate": RATE * t // 200,
        "gap": GAP * t // 200,
        "pen": PENALTY * core["#diff.damage"] // 100,
    }


def count(level: int, players: int, numbers: tuple[int, int, int]) -> int:
    """the core's ``mob/count`` in Python: ``numbers`` (solo, duo, more a
    player beyond two) by how many are in the dome, scaled by the level"""
    solo, duo, more = numbers
    n = duo if players >= 2 else solo
    n += max(0, (players - 2) * more)
    return max(1, n * game.scaled(level)["#diff.count"] // 100)


def wave(level: int, players: int, stage: int) -> dict[str, int]:
    """what a wave asks for with ``stage`` trips done (the quarter of the
    charge), and the caps it is cast under: of all the automatons alive,
    of the Stokers and of the Riveters"""
    cap, riveter_cap = count(level, players, CAP), count(level, players, RIVETER_CAP)
    husks = count(level, players, HUSKS)
    return {
        "cap": cap,
        "stoker": count(level, players, STOKERS),
        # (the Stokers leave room for the Riveters' cap and a wave of Husks)
        "stoker_cap": cap - riveter_cap - husks,
        "riveter": count(level, players, RIVETERS) if stage >= 1 else 0,
        "riveter_cap": riveter_cap,
        "husk": husks if stage >= 2 else 0,
    }


def last_quarter(charge: int) -> int:
    """the charge a fight that is left falls back to"""
    return charge // QUARTER * QUARTER


def seconds(level: int) -> int:
    """how long the mast takes to charge with no breaker out"""
    return math.ceil(FULL / scaled(level)["rate"]) * STEP // 20


SWITCH_SIGN = ("MAIN SWITCH", "Throw to", "charge the", "accumulator.")
PLAQUE_SIGNS = (
    ("FOUNDRY No. 4", "Pump No. 4", "", "Hold the floor."),
    ("Throw the", "main switch", "on the mast."),
    ("Keep all three", "breakers closed", "until the mast", "is charged."),
)
LOG_TITLE, LOG_AUTHOR = "Foundry log", "O. Finch"
LOG_PAGES = [
    "Foundry log\nO. Finch, Chief Engineer\n\nNobody has given this shop an "
    "order in nine days. It is casting anyway.\n\nNot pipe. Not plate. "
    "Stokers, with legs.",
    "I counted forty off the north mould before I stopped counting. They "
    "walk to the Engine's door and stand there, like a shift coming on.\n\n"
    "The Engine is not broken. It is hiring.\n\nSomebody showed it what a "
    "man looks like.",
    "Pump No. 4 runs off the accumulator, the mast in the middle. Throw the "
    "main switch and she charges.\n\nThe shop will cast against you until "
    "she is full. A breaker out, and the charge stands still. Red light: "
    "go and close it.",
    "They go for the breakers: floor, gallery, top deck. With a mate they "
    "pull two at a time, so split up.\n\nThey are bad at ladders.\n\nI am "
    "going on to the Signal Room. Something in there is sending, and it is "
    "not us.\n\nO.F.",
]


def logbook(fr: Frame) -> str:
    return fittings.lectern_with_book(
        fr.facing(-1, 0), LOG_TITLE, LOG_AUTHOR, LOG_PAGES
    )


def label(breaker: Breaker, closed: bool) -> str:
    """the text of a breaker's label: gold, or red when it is out"""
    if closed:
        return label_text(f"BREAKER {breaker.name}")
    return label_text(f"BREAKER {breaker.name} OUT", "red", bold="true")


@dataclass
class Blocks:
    """every block the room is made of, as built and as ``reset`` leaves it"""

    floor: dict[Cell, str] = field(default_factory=dict)  # relaid floor
    solid: dict[Cell, str] = field(default_factory=dict)
    attached: dict[Cell, str] = field(default_factory=dict)  # need a support
    #: redstone that must go in last, in this order (the battery's clock)
    late: dict[Cell, str] = field(default_factory=dict)
    clear: set[Cell] = field(default_factory=set)  # air, to be kept so
    #: cells whose block's state changes by itself (the clock's dust, its
    #: repeaters, its lamps, its pistons): the same block always
    moving: set[Cell] = field(default_factory=set)
    #: cells a moving part passes through (a piston's head)
    swept: set[Cell] = field(default_factory=set)

    def above(self) -> dict[Cell, str]:
        """everything above the floor"""
        return {**self.solid, **self.attached, **self.late}

    def everything(self) -> dict[Cell, str]:
        return {**self.floor, **self.above()}

    def put(self, part: dict[Cell, str], cell: Cell, block: str) -> None:
        """a block in one of the parts; no cell may be given twice"""
        parts = (self.floor, self.solid, self.attached, self.late)
        if any(cell in p for p in (*parts, self.clear, self.swept)):
            raise ValueError(f"cell given two blocks: {cell} ({block})")
        part[cell] = block

    def add(self, other: Blocks) -> None:
        """take in another set of blocks; no cell may be given twice"""
        mine, theirs = self.everything(), other.everything()
        if both := (set(mine) | self.clear | self.swept) & set(theirs):
            raise ValueError(f"cells given two blocks: {sorted(both)[:5]}")
        self.floor |= other.floor
        self.solid |= other.solid
        self.attached |= other.attached
        self.late |= other.late
        self.clear |= other.clear
        self.moving |= other.moving
        self.swept |= other.swept


def room_blocks(dome: Dome) -> Blocks:
    """the Foundry's blocks, the fight's and the foundry's. They are the
    same in the solo and the duo form: the form changes what trips and
    what is cast, not what is built"""
    b = puzzle_blocks(dome)
    b.add(dressing_blocks(dome))
    return b


def ring_part(f: int, r: int) -> str:
    """what the gallery has in a column: its ``deck``, a ``kerb`` (which
    carries the rail), or nothing. A horseshoe: the south-west quarter is
    left out, with a kerb across each cut end"""
    if f < -2 and r < -2:
        return ""
    d = math.hypot(f, r)
    lo, hi = RING
    if not lo - 1 <= d < hi + 1:
        return ""
    if (f == -2 and r <= -2) or (r == -2 and f <= -2):
        return "kerb"
    return "deck" if lo <= d < hi else "kerb"


def stair_treads(fr: Frame) -> dict[Cell, str]:
    """the two stairs' treads: cell -> the stair block"""
    treads = {}
    for rows, foot, way in STAIRWAYS:
        for i in range(TREADS):
            for f in rows:
                treads[fr.at(f, foot + way * i, 1 + i)] = (
                    f"{STAIRS}[facing={fr.facing(0, way)},half=bottom]"
                )
    return treads


def stair_wells() -> set[tuple[int, int]]:
    """the columns of the gallery left open over the stairs' upper treads,
    so that a head clears the deck on the way up"""
    return {
        (f, foot + way * i)
        for rows, foot, way in STAIRWAYS
        for i in range(TREADS)
        for f in rows
        if 1 + i + 3 >= DECK_H
    }


def cupola_columns() -> set[tuple[int, int]]:
    """the columns of the cupola furnace: a round tower five across"""
    cf, cr = CUPOLA
    return {
        (cf + df, cr + dr)
        for df in range(-2, 3)
        for dr in range(-2, 3)
        if abs(df) + abs(dr) < 4
    }


def puzzle_blocks(dome: Dome) -> Blocks:
    """the blocks of the fight itself and of the room's fittings, as
    ``reset`` leaves them: the mast and its switch, the breakers, the bus
    bar, the moulds' lamps, the plaque, the logbook, the recall post"""
    place = room(dome)
    fr = place.frame
    back = fr.facing(-1, 0)
    b = Blocks()

    # the plaque, the logbook, the recall button
    solid, attached = fittings.plaque_blocks(fr, *PLAQUE, signs=PLAQUE_SIGNS)
    b.solid |= solid
    b.attached |= attached
    b.put(b.solid, place.lectern, logbook(fr))
    solid, attached = fittings.recall_post_blocks(fr, *place.recall)
    for cell, block in solid.items():
        b.put(b.solid, cell, block)
    for cell, block in attached.items():
        b.put(b.attached, cell, block)

    # the mast: a foot of three blocks with the main switch on brass in its
    # south face, then twelve cells of four lamps. (No lamp touches the
    # switch's brass: a thrown lever powers its block, and that block every
    # bulb beside it.)
    lamps = {cell for column in place.mast for cell in column}
    for h in range(MAST_BASE[0], MAST_H + CELLS):
        for df in (-1, 0, 1):
            for dr in (-1, 0, 1):
                cell = fr.at(df, dr, h)
                if cell in lamps:
                    block = f"{BULB}[lit=false]"
                elif df and dr:
                    block = CUT
                elif h == MAST_BASE[1]:
                    block = CHISELED
                else:
                    block = COPPER
                b.put(b.solid, cell, block)
    b.solid[place.switch_on] = BRASS
    b.put(b.attached, place.switch, fittings.lever(place.switch_facing))
    x, y, z = place.switch
    b.put(b.attached, (x, y + 1, z), fittings.wall_sign(back, *SWITCH_SIGN))

    # the breakers: a lever on a brass post, closed as built, its lamp lit
    for breaker in place.breakers:
        for cell, block in breaker.post.solid.items():
            b.put(b.solid, cell, block)
        for cell, block in breaker.post.attached.items():
            b.put(b.attached, cell, block)
        b.put(b.solid, breaker.lamp, f"{BULB}[lit=true]")

    # the bus bar: lamps in the floor from the dais to the exit, dark
    for cell in place.bus:
        b.put(b.floor, cell, f"{BULB}[lit=false]")
    # the moulds' lamps, in the posts of their fronts
    for cell in place.telltales:
        b.put(b.solid, cell, f"{BULB}[lit=false]")
    return b


def dressing_blocks(dome: Dome) -> Blocks:
    """the foundry round the fight (see the module docstring): built once
    and left alone by ``reset``, but for the pouring floor, which it
    cools"""
    place = room(dome)
    fr = place.frame
    cells = domes.dome_cells(dome)
    lights = domes.light_cells(dome)[0]
    left, right = fr.facing(0, -1), fr.facing(0, 1)
    fight = puzzle_blocks(dome)
    used = set(fight.everything())
    d = Blocks()

    def rod(way: str = "up") -> str:
        return f"{ROD}[facing={way}]"

    def hang(f: int, r: int, h: int) -> None:
        """a chain from here up to the glass"""
        while (cell := fr.at(f, r, h)) in cells.interior:
            d.put(d.solid, cell, CHAIN)
            h += 1

    # -- the casting floor: black, with glowing channels from the dais to
    # each mould, and the pouring floor's nine moulds, cool
    reach = RING[1] + 4
    channel = {(f, 0) for f in range(DAIS + 1, MOULDS["north"][0][0])}
    channel |= {(0, r) for r in range(DAIS + 1, MOULDS["east"][0][1])}
    for f in range(-dome.radius, dome.radius + 1):
        for r in range(-dome.radius, dome.radius + 1):
            cell = fr.at(f, r, 0)
            if cell in lights or cell in used or cell not in cells.floor:
                continue
            if cell in place.pour:
                d.floor[cell] = COOL
            elif (f, r) in channel:
                d.floor[cell] = HOT if (f + r) % 3 == 0 else COOL
            elif math.hypot(f, r) < reach:
                d.floor[cell] = BLACK

    # -- the dais: nine by nine and a block high, a skirt of stairs
    for f in range(-DAIS, DAIS + 1):
        for r in range(-DAIS, DAIS + 1):
            if abs(f) == DAIS and abs(r) == DAIS:
                block = f"{SLAB}[type=bottom]"
            elif abs(f) == DAIS:
                block = f"{STAIRS}[facing={fr.facing(-f // DAIS, 0)},half=bottom]"
            elif abs(r) == DAIS:
                block = f"{STAIRS}[facing={fr.facing(0, -r // DAIS)},half=bottom]"
            else:
                block = CUT
            d.put(d.solid, fr.at(f, r, 1), block)
    # the mast's crown: rods, four arms, a chain to the top of the glass
    top = MAST_H + CELLS
    for h in range(top, top + 3):
        d.put(d.solid, fr.at(0, 0, h), rod())
    for df, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        d.put(d.solid, fr.at(df, dr, top), rod(fr.facing(df, dr)))
    hang(0, 0, top + 3)

    # -- the moulds: black boxes open at the front, glowing inside
    for name in MOULDS:
        for depth in range(MOULD_DEPTH):
            for across in range(-MOULD_HALF, MOULD_HALF + 1):
                d.put(d.solid, mould_cell(fr, name, depth, across, MOULD_ROOF), BRICKS)
                wall = abs(across) == MOULD_HALF or depth == MOULD_DEPTH - 1
                for h in range(1, MOULD_ROOF):
                    cell = mould_cell(fr, name, depth, across, h)
                    if not wall or cell in used:
                        continue
                    glow = depth == MOULD_DEPTH - 1 and h == 2 and abs(across) < 2
                    d.put(d.solid, cell, HOT if glow else BLACK)
                if not wall:
                    under = mould_cell(fr, name, depth, across, 0)
                    if under not in lights:
                        d.floor[under] = HOT if (depth + across) % 2 else COOL

    # -- the stamp battery on the north mould's roof: the shared torch
    # clock, its two pistons striking a die bar, in a cage of bars
    machine = place.machine
    d.solid |= machine.bed  # (the roof under it, and the four lamps)
    for cell, block in machine.solid.items():
        d.put(d.solid, cell, block)
    for cell, block in machine.attached.items():
        d.put(d.late, cell, block)
    d.moving |= machine.moving & (set(d.solid) | set(d.late))
    d.swept |= machine.moving - set(d.solid) - set(d.late)
    die = MOULD_ROOF + 3
    for across in (-1, 0, 1, 2):
        d.put(d.solid, mould_cell(fr, "north", 1, across, die), CHISELED)
    for across in (-1, 2):
        for h in (MOULD_ROOF + 1, MOULD_ROOF + 2):
            d.put(d.solid, mould_cell(fr, "north", 1, across, h), BARS)
    for depth in range(MOULD_DEPTH):
        for across in range(-MOULD_HALF, MOULD_HALF + 1):
            rim = abs(across) == MOULD_HALF or depth in (0, MOULD_DEPTH - 1)
            if rim:
                for h in (MOULD_ROOF + 1, MOULD_ROOF + 2):
                    d.put(d.solid, mould_cell(fr, "north", depth, across, h), BARS)
            # a lid of grating level with the die bar: a player who hops the
            # gallery's rail walks on it, and cannot drop into the cage
            if across not in (-1, 0, 1, 2) or depth != 1:
                d.put(d.solid, mould_cell(fr, "north", depth, across, die), GRATE)
    # the east mould's roof: two tanks and the pipe between them
    for across in (-2, 1):
        for da in (0, 1):
            for depth in (1, 2):
                cell = mould_cell(fr, "east", depth, across + da, MOULD_ROOF + 1)
                d.put(d.solid, cell, CUT)
                x, y, z = cell
                d.put(d.solid, (x, y + 1, z), WEATHERED)
                d.put(d.solid, (x, y + 2, z), f"{SLAB}[type=bottom]")
    d.put(d.solid, mould_cell(fr, "east", 1, 0, MOULD_ROOF + 2), rod(fr.facing(1, 0)))
    d.put(d.solid, mould_cell(fr, "east", 3, 0, MOULD_ROOF + 1), rod())

    # -- the cupola furnace, a round tower, and the rivet loft on top of
    # it: railed on the far side, roofed, open to the gallery
    tower = cupola_columns()
    cf, cr = CUPOLA
    for f, r in tower:
        for h in range(1, DECK_H + 1):
            band = h in (1, DECK_H) or (f - cf and r - cr)
            d.put(d.solid, fr.at(f, r, h), CUT if band else EXPOSED)
        booth = abs(f - cf) < 2 and abs(r - cr) < 2
        if not booth and math.hypot(f, r) >= RING[1] + 1:
            for h in (DECK_H + 1, DECK_H + 2):
                d.put(d.solid, fr.at(f, r, h), BARS)
        if booth or math.hypot(f, r) >= RING[1] + 1:
            d.put(d.solid, fr.at(f, r, DECK_H + 3), f"{SLAB}[type=bottom]")
    d.solid[fr.at(cf, cr - 2, 2)] = HOT  # the furnace's mouth, towards the mast
    d.solid[fr.at(cf - 2, cr, 2)] = HOT

    # -- the chimneys, a campfire smoking on each
    for f, r in CHIMNEYS:
        for h in range(1, CHIMNEY_TOP + 1):
            d.put(d.solid, fr.at(f, r, h), BRICKS if h % 4 else CHISELED)
        d.put(d.attached, fr.at(f, r, CHIMNEY_TOP + 1), "minecraft:campfire[lit=true]")

    # -- the stairs to the gallery: open flights, so that the foot of the
    # mast is seen through them
    for cell, block in stair_treads(fr).items():
        d.put(d.solid, cell, block)

    # -- the gallery: a horseshoe of grating, its two edges (the kerbs)
    # railed, on columns and on chains from the glass. Grating throughout,
    # so that the mast and the lamps are seen through it from any level
    wells = stair_wells()
    for f in range(-dome.radius, dome.radius + 1):
        for r in range(-dome.radius, dome.radius + 1):
            part = ring_part(f, r)
            if not part or (f, r) in wells or (f, r) in tower:
                continue
            lamp = f"{BULB}[lit=true]" if (f, r) in RING_LAMPS else GRATE
            d.put(d.solid, fr.at(f, r, DECK_H), lamp)
            rail = fr.at(f, r, DECK_H + 1)
            if part == "kerb" and rail not in used and (f, r) not in HANGERS:
                if abs(r) != LADDER_R + 1 or f:
                    d.put(d.solid, rail, BARS)
    for f, r in COLUMNS:
        for h in range(1, DECK_H):
            d.put(d.solid, fr.at(f, r, h), rod())
    for f, r in HANGERS:
        hang(f, r, DECK_H + 1)

    # -- the gantry: a bridge of grating through the mast with the tuning
    # deck round it, a rail along every edge, and a ladder at each end
    # from the gallery, on a back of copper
    end = LADDER_R + 1
    for f in range(-TUNING - 1, TUNING + 2):
        for r in range(-end, end + 1):
            cell = fr.at(f, r, GANTRY_H)
            if cell in used or (f == 0 and abs(r) >= LADDER_R):
                continue
            edge = max(abs(f), abs(r)) == TUNING + 1 and abs(f) > 1
            if abs(r) > TUNING + 1 and abs(f) > 2:
                continue
            lamp = abs(f) == TUNING + 1 and r == 0
            d.put(d.solid, cell, f"{BULB}[lit=true]" if lamp else GRATE)
            if edge or (abs(r) > TUNING + 1 and abs(f) == 2) or abs(r) == end:
                d.put(d.solid, fr.at(f, r, GANTRY_H + 1), BARS)
    for side in (-1, 1):
        for h in range(DECK_H + 1, GANTRY_H + 2):
            d.put(d.solid, fr.at(0, side * end, h), COPPER)
        for h in range(DECK_H + 1, GANTRY_H + 1):
            d.put(
                d.attached,
                fr.at(0, side * LADDER_R, h),
                f"{LADDER}[facing={left if side > 0 else right}]",
            )
        # the way up the ladder and off its head stays clear
        d.clear.add(fr.at(0, side * LADDER_R, GANTRY_H + 1))
        d.clear.add(fr.at(0, side * LADDER_R, GANTRY_H + 2))

    # -- the crane rail under the roof, hung from the glass; the ladle on
    # it is four displays (``summons``)
    cf, ch = CRANE
    for r in range(CRANE_R[0], CRANE_R[1] + 1):
        d.put(d.solid, fr.at(cf, r, ch), TIMBER)
    for r in (CRANE_R[0], 0, CRANE_R[1]):
        hang(cf, r, ch + 1)
    return d


def summons(dome: Dome) -> list[str]:
    """the commands that summon the room's entities: the recall button's
    interaction, the labels over the breakers and the switch, the ladle"""
    place = room(dome)
    fr = place.frame
    out = [fittings.summon_recall(fr, *place.recall, tags=(ENTITY_TAG,))]
    for breaker in place.breakers:
        out.append(
            fittings.display(
                (ENTITY_TAG, breaker.tag),
                breaker.label,
                0,
                label(breaker, True),
                0.8,
                "center",
            )
        )
    x, y, z = place.switch
    out.append(
        fittings.display(
            (ENTITY_TAG, SWITCH_TAG),
            (x + 0.5, y + 2.2, z + 0.5),
            0,
            label_text("MAIN SWITCH"),
            0.8,
            "center",
        )
    )
    return out + ladle_summons(place)


def ladle_summons(place: Room) -> list[str]:
    """the ladle, parked at the east end of its rail: a bucket two blocks
    across with the glow of the metal in it, on two chains. Displays: they
    stop nobody and cannot be clicked"""
    fr = place.frame
    ax, az = fr.right
    parts = [
        ("minecraft:cauldron", (-1.0, 0.0, -1.0), (2.0, 2.0, 2.0)),
        (HOT, (-0.7, 1.45, -0.7), (1.4, 0.4, 1.4)),
    ]
    parts += [
        (CHAIN, (-0.5 + side * 0.6 * ax, 2.0, -0.5 + side * 0.6 * az), (1.0, 1.0, 1.0))
        for side in (-1, 1)
    ]
    identity = "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]"
    return [
        f"summon minecraft:block_display {middle(place.ladle[0])} "
        f'{{Tags:["{ENTITY_TAG}","{LADLE_TAG}"],teleport_duration:1,'
        f'brightness:{{sky:15,block:15}},block_state:{{Name:"{block}"}},'
        f"transformation:{{translation:[{tx}f,{ty}f,{tz}f],"
        f"scale:[{sx}f,{sy}f,{sz}f],{identity}}}}}"
        for block, (tx, ty, tz), (sx, sy, sz) in parts
    ]


def fr_of(fr: Frame, cell: Cell) -> tuple[int, int, int]:
    """a cell's place in a frame: forward, right, and above the floor"""
    dx, dz = cell[0] - fr.origin[0], cell[2] - fr.origin[2]
    return (
        dx * fr.forward[0] + dz * fr.forward[1],
        dx * fr.right[0] + dz * fr.right[1],
        cell[1] - fr.origin[1],
    )


# ----------------------------------------------------------- the plan's checks

#: what stands on or hangs from a block and is still in the way
IN_THE_WAY = ("minecraft:campfire",)


def inputs(dome: Dome) -> set[Cell]:
    """every lever and button of the room: the main switch, the three
    breakers, the recall button"""
    place = room(dome)
    f, r, side = place.recall
    return {
        place.switch,
        *(b.lever for b in place.breakers),
        place.frame.at(f, r + side, 2),
    }


def ladder_heads(dome: Dome) -> dict[str, Cell]:
    """where a player steps off each ladder onto the gantry"""
    fr = room(dome).frame
    return {
        name: fr.at(0, side * (LADDER_R - 1), GANTRY_H + 1)
        for name, side in (("west", -1), ("east", 1))
    }


def walks(dome: Dome) -> dict[str, Cell]:
    """where a player must be able to walk to from the entrance, by name:
    the cell their feet are in. The gantry is reached by the ladders
    (``gantry_walks``)"""
    place = room(dome)
    fr = place.frame
    tunnel = layout.TUNNELS[dome.index]
    ux, uz = domes.outward(dome, tunnel)
    ox, oy, oz = dome.floor_centre
    mouth = dome.radius - 3
    lf, lr = LECTERN
    rf, rr, side = place.recall
    targets = {
        "the way out": (ox + ux * mouth, oy + 1, oz + uz * mouth),
        "the plaque": fr.at(PLAQUE[0] - 2, PLAQUE[1], 1),
        "the logbook": fr.at(lf - 1, lr, 1),
        "the recall button": fr.at(rf, rr + 2 * side, 1),
        "the main switch": place.switch_stand,
        "the north mould": place.stokers[0],
        "the east mould": place.stokers[1],
        "the rivet loft": place.riveters[0],
    }
    for breaker in place.breakers[:2]:
        targets[f"breaker {breaker.name}"] = breaker.stand
    for rows, foot, way in STAIRWAYS:
        name = "east" if way > 0 else "west"
        targets[f"the {name} stair's head"] = fr.at(
            rows[0], foot + way * TREADS, DECK_H + 1
        )
    for name, side in (("west", -1), ("east", 1)):
        targets[f"the {name} ladder's foot"] = fr.at(0, side * LADDER_R, DECK_H + 1)
    return targets


def gantry_walks(dome: Dome) -> dict[str, Cell]:
    """where a player must be able to walk to on the gantry, from the head
    of either ladder"""
    place = room(dome)
    return {
        "breaker C": place.breakers[2].stand,
        **{f"the {n} ladder's head": c for n, c in ladder_heads(dome).items()},
    }


def pits(dome: Dome, solid, ladders: set[Cell], blocked=()) -> set[Cell]:
    """
    The cells a player can get to from the entrance but not back: a search
    like ``rooms.reach`` (a step up of one block, rail tops counted as
    something to stand on), with falls of any height and ladders climbed
    both ways, then the same moves taken backwards from the entrance.
    """
    cells = domes.dome_cells(dome)
    full = set(solid) | set(blocked)
    ground = set(cells.floor) | set(solid)

    def free(cell: Cell) -> bool:
        return cell in cells.interior and cell not in full

    def held(cell: Cell) -> bool:
        x, y, z = cell
        return (x, y - 1, z) in ground or cell in ladders

    def stands(cell: Cell) -> bool:
        x, y, z = cell
        return free(cell) and free((x, y + 1, z)) and held(cell)

    def moves(cell: Cell) -> set[Cell]:
        x, y, z = cell
        out = set()
        if cell in ladders:
            out |= {c for c in ((x, y + 1, z), (x, y - 1, z)) if stands(c)}
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            to = (x + dx, y, z + dz)
            up = (x + dx, y + 1, z + dz)
            if stands(up) and free((x, y + 2, z)):
                out.add(up)
            if not (free(to) and free((to[0], y + 1, to[2]))):
                continue
            while not held(to) and free((to[0], to[1] - 1, to[2])):
                to = (to[0], to[1] - 1, to[2])
            if stands(to):
                out.add(to)
        return out

    start = domes.entrance(dome)[:3]
    seen, edge, back = {start}, [start], {}
    while edge:
        cell = edge.pop()
        for to in moves(cell):
            back.setdefault(to, set()).add(cell)
            if to not in seen:
                seen.add(to)
                edge.append(to)
    home, edge = {start}, [start]
    while edge:
        for came in back.get(edge.pop(), ()):
            if came not in home:
                home.add(came)
                edge.append(came)
    return seen - home


def walk_problems(dome: Dome) -> list[str]:
    """
    Every place of ``walks`` can be walked to from the entrance, and every
    place of ``gantry_walks`` from the head of each ladder, at foot and
    head height (``rooms.walk_problems``); each ladder is whole, from the
    gallery's deck to the gantry's, with nothing in its way; and there is
    no pit (``pits``): nowhere a player can climb or fall into and not get
    out of. The room is built the same in both forms, so one pass serves
    both.
    """
    place = room(dome)
    fr = place.frame
    b = room_blocks(dome)
    blocked = b.swept | {
        c for c, block in b.attached.items() if rooms.name(block) in IN_THE_WAY
    }
    problems = rooms.walk_problems(dome, b.solid, walks(dome), blocked)
    ladders = {c for c, block in b.attached.items() if rooms.name(block) == LADDER}
    if stuck := pits(dome, b.solid, ladders, blocked):
        problems.append(f"{len(stuck)} cells with no way out, as {min(stuck)}")
    for name, head in ladder_heads(dome).items():
        found = rooms.walk_problems(dome, b.solid, gantry_walks(dome), blocked, head)
        problems += [p.replace("the entrance", f"the {name} ladder") for p in found]
    for name, side in (("west", -1), ("east", 1)):
        rungs = [fr.at(0, side * LADDER_R, h) for h in range(DECK_H + 1, GANTRY_H + 1)]
        above = [fr.at(0, side * LADDER_R, GANTRY_H + h) for h in (1, 2)]
        if any(rooms.name(b.attached.get(c, "")) != LADDER for c in rungs):
            problems.append(f"the {name} ladder is not whole")
        if any(c in b.above() for c in above):
            problems.append(f"the {name} ladder's head is not clear")
    return problems


def sights(dome: Dome) -> list[tuple[str, Cell, str, tuple[Cell, ...]]]:
    """what the fight depends on seeing: (where, the cell stood in, what,
    cells: seen if any one of them is). The mast is the progress bar:
    its first and its last cell from the entrance, the switch and where
    each breaker is worked. A breaker's lamp is found from where the fight
    starts or from the level below it."""
    place = room(dome)
    a, b, c = place.breakers
    eyes = {
        "the entrance": domes.entrance(dome)[:3],
        "the main switch": place.switch_stand,
        **{f"breaker {x.name}": x.stand for x in place.breakers},
    }
    out = []
    for where, eye in eyes.items():
        for k in (0, CELLS - 1):
            # (a lamp is seen if the cell in front of its face is: a line
            # to the lamp's own middle from below runs up inside the mast)
            faces = tuple(column[k] for column in place.mast_faces)
            out.append((where, eye, f"cell {k + 1} of the mast", faces))
    out += [
        ("the entrance", eyes["the entrance"], "breaker A's lamp", (a.lamp,)),
        ("the entrance", eyes["the entrance"], "breaker B's lamp", (b.lamp,)),
        ("the main switch", eyes["the main switch"], "breaker B's lamp", (b.lamp,)),
        ("breaker B", b.stand, "breaker C's lamp", (c.lamp,)),
    ]
    out += [
        (f"the {name} ladder's head", head, "breaker C's lamp", (c.lamp,))
        for name, head in ladder_heads(dome).items()
    ]
    return out


def sight_problems(dome: Dome) -> list[str]:
    """each of ``sights`` is in sight: nothing but glass, grating, bars,
    chains and pipes on the line from the eye to one of its cells
    (``rooms.hidden``); and the outgoing door's window from the entrance
    (``rooms.window_problems``)"""
    b = room_blocks(dome)
    solid = rooms.opaque(b.solid)
    problems = []
    for where, eye, what, cells in sights(dome):
        ways = [rooms.hidden(eye, cell, solid - {cell}) for cell in cells]
        if all(ways):
            first = min(min(way) for way in ways)
            problems.append(f"{what} is hidden from {where} by {first}")
    return problems + rooms.window_problems(dome, b.above())


def room_problems(dome: Dome) -> list[str]:
    """the room's plan against the dome and the rules for a room: every
    cell inside the dome and off the cells the tunnels reserve, the floor
    in the floor and its lanterns left, nothing waterlogged; every input
    listed, on brass, with a sign, and nothing beside its brass that
    redstone would work; nothing of the dressing an input; the walks
    clear and the sights in sight"""
    try:
        b = room_blocks(dome)
    except ValueError as e:
        return [str(e)]
    place = room(dome)
    more = b.clear | b.swept | set(place.ladle) | set(place.smoke) | {place.crown}
    more |= {*place.stokers, *place.husks, *place.riveters}
    more |= {(x, y + up, z) for x, y, z in place.ladle for up in (1, 2)}
    problems = rooms.room_problems(dome, b.above(), b.floor, more)
    problems += fittings.placement_problems(dome, set(b.above()) | more)
    if lost := set(b.floor) & domes.light_cells(dome)[0]:
        problems.append(f"{len(lost)} of the floor's lanterns relaid: {min(lost)}")
    problems += rooms.input_problems(b.above(), inputs(dome), floor=b.floor)
    dress = dressing_blocks(dome).everything()
    problems += [
        f"an input in the dressing at {cell}"
        for cell, block in sorted(dress.items())
        if rooms.is_input(block)
    ]
    return problems + walk_problems(dome) + sight_problems(dome)


# --------------------------------------------------------------- the build


def build(ctx: Any) -> str:
    """the Foundry inside its shell; takes the stub's BYPASS post away,
    wipes what was inside but the pump engine, and leaves the room as
    ``reset`` does"""
    dome = ctx.layout.DOMES[INDEX]
    if problems := room_problems(dome):
        raise RuntimeError("the Foundry: " + "; ".join(problems))
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    engine = set(tunnels.engine_cells(ctx.layout.TUNNELS[INDEX]).values())
    for command in game.clear_stub_commands(dome):
        ctx.cmd(command)
    ctx.cmd(f"kill @e[tag={ENTITY_TAG}]")
    ctx.fill_boxes(cells.interior - engine, AIR)
    # the big parts a box at a time (which also joins the bars); what has
    # NBT, and what needs a support, a block at a time
    for part in (b.floor, b.solid):
        plain = {c: block for c, block in part.items() if "{" not in block}
        for block, where in sorted(domes.by_block(plain).items()):
            ctx.fill_boxes(where, block)
        for cell, block in sorted(part.items()):
            if cell not in plain:
                ctx.setblock(cell, block)
    for cell, block in sorted(b.attached.items()):
        ctx.setblock(cell, block)
    # the battery's clock last, in the order that starts it
    for cell, block in b.late.items():
        ctx.setblock(cell, block)
    for command in summons(dome):
        ctx.cmd(command)
    # the pack's own idea of the room, if the pack is installed
    ctx.function(f"dome/{INDEX}/reset")
    ctx.advance(10)
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    return (
        f"{dome.name}: {len(b.everything())} blocks: plaque, logbook, recall "
        "button, the mast and its switch, 3 breakers, the bus bar; the "
        "foundry: casting floor, dais, gallery and 2 stairs, gantry and 2 "
        "ladders, 2 moulds, cupola and loft, 2 chimneys, the stamp battery, "
        "the crane rail and its ladle"
    )


# ----------------------------------------------------------- the functions


def _s(name: str) -> str:
    return f"#fdy.{name} {OBJ}"


def _set(name: str, value: int) -> str:
    return f"scoreboard players set {_s(name)} {value}"


def _op(name: str, op: str, other: str) -> str:
    return f"scoreboard players operation {_s(name)} {op} {other} {OBJ}"


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


def _setblock(cell: Cell, block: str) -> str:
    return f"setblock {_xyz(cell)} {block}"


def _if_block(cell: Cell, block: str) -> str:
    return f"if block {_xyz(cell)} {block}"


def wave_points(place: Room) -> dict[automatons.Kind, tuple[Cell, ...]]:
    """where each kind is cast: Stokers in the two moulds in turn, Riveters
    in the loft, Slag Husks in the north mould"""
    return {
        automatons.RIVETER: place.riveters,
        automatons.SLAG_HUSK: place.husks,
        automatons.STOKER: place.stokers,
    }


def functions(pack: dp.Pack) -> None:
    """the Foundry's functions (see the module docstring)"""
    dome = layout.DOMES[INDEX]
    place = room(dome)
    fr = place.frame
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    open_dome = f"#d{INDEX} {OBJ}"
    mobs = automatons.selector(INDEX)
    pack.objectives({OBJ: "dummy"})
    pack.constants(OBJ, 100, 200, CELL, QUARTER, *LAST_GAP)
    lit, dark = f"{BULB}[lit=true]", f"{BULB}[lit=false]"
    switch_on = fittings.lever(place.switch_facing, True)
    switch_off = fittings.lever(place.switch_facing)

    def fid(name: str) -> str:
        return pack.id(f"{base}/{name}")

    def call(name: str) -> str:
        return f"function {fid(name)}"

    def state(value: str) -> str:
        return f"if score {_s('state')} matches {value}"

    def sound(name: str, cell: Cell, volume: float = 1, pitch: float = 1) -> str:
        return f"playsound minecraft:{name} block {here} {_xyz(cell)} {volume} {pitch}"

    def say(text: str, colour: str = "yellow") -> str:
        return f'tellraw {here} {{text:{snbt(text)},color:"{colour}"}}'

    def title(text: str, sub: str, colour: str = "gold") -> list[str]:
        return [
            f"title {here} times 5 50 10",
            f'title {here} subtitle {{text:{snbt(sub)},color:"yellow"}}',
            f'title {here} title {{text:{snbt(text)},color:"{colour}"}}',
        ]

    def fx(
        name: str, at: str, spread: str = "0.2 0.2 0.2", speed: float = 0.01, n: int = 4
    ) -> str:
        """a particle by way of the macro function ``fx``: a particle's
        name is checked when a function loads, and a macro line only when
        it runs, so a name this version does not know costs one effect,
        not the function it is in and every function that calls that"""
        return (
            f'{call("fx")} {{p:"minecraft:{name}",at:"{at}",'
            f'd:"{spread}",s:"{speed:g}",n:{n}}}'
        )

    pack.function(f"{base}/fx", ["$particle $(p) $(at) $(d) $(s) $(n)"])
    bar = automatons.bar(pack, INDEX, "Accumulator", FULL, "yellow", "notched_12")
    hint_switch = fittings.hint(
        pack,
        INDEX,
        "switch",
        "Nothing happens until someone throws the main switch on the mast.",
        60,
    )
    hint_breaker = fittings.hint(
        pack, INDEX, "breaker", "A breaker is out. Find the red light.", 20
    )

    # -- the values of the level in force
    pack.function(
        f"{base}/scale",
        [
            _op("t", "=", "#diff.timer"),
            f"scoreboard players add {_s('t')} 100",
            _set("rate", RATE),
            _op("rate", "*=", "#fdy.t"),
            _op("rate", "/=", "#200"),
            _set("gap", GAP),
            _op("gap", "*=", "#fdy.t"),
            _op("gap", "/=", "#200"),
            _set("pen", PENALTY),
            _op("pen", "*=", "#diff.damage"),
            _op("pen", "/=", "#100"),
        ],
    )

    # -- the main switch: thrown, it starts the fight, and stays thrown
    pack.function(
        f"{base}/switch",
        [
            f"execute {state('0')} {_if_block(place.switch, 'minecraft:lever[powered=true]')} "
            f"run {call('start')}",
            fittings.lever_hold_line(place.switch, switch_on, state("1..")),
        ],
    )
    flare = [_setblock(cell, lit) for cell in place.telltales]
    unflare = [_setblock(cell, dark) for cell in place.telltales]
    pack.function(
        f"{base}/start",
        [
            # the core's reading of the game's difficulty: on Peaceful the
            # game takes every automaton as it is cast
            f"function {pack.id('fight/difficulty')}",
            f"execute if score #difficulty {OBJ} matches 0 run {call('refuse')}",
            f"execute if score #difficulty {OBJ} matches 0 run return 0",
            _set("state", 1),
            _set("wait", 0),
            _set("next", FIRST),
            *title("THE FOUNDRY WAKES", "Keep all three breakers closed", "red"),
            sound("block.beacon.activate", place.switch, 2, 0.6),
            sound("block.anvil.land", place.stokers[0], 2, 0.5),
            *flare,
            bar.value_line(_s("charge")),
            bar.show,
        ],
    )
    pack.function(
        f"{base}/refuse",
        [
            *fittings.lever_put_lines(place.switch, switch_off),
            say("The Foundry will not wake while the world is Peaceful.", "gray"),
        ],
    )

    # -- the breakers: each lever read, its lamp and its label to match
    breakers = []
    for b in place.breakers:
        v, shown = f"{b.score} {OBJ}", _s(f"s{b.index}")
        mark = fittings.display_selector(b.tag)
        pack.function(
            f"{base}/breaker/{b.index}",
            [
                f"execute if score {v} matches 1 run {_setblock(b.lamp, lit)}",
                f"execute if score {v} matches 1 run "
                + fittings.text_line(b.tag, label(b, True)),
                f"execute if score {v} matches 1 "
                f"run data merge entity {mark} {{see_through:0b}}",
                f"execute if score {v} matches 1 if score {shown} matches 0 run "
                + sound("block.iron_door.close", b.lever, 1, 1.4),
                f"execute if score {v} matches 0 run {_setblock(b.lamp, dark)}",
                f"execute if score {v} matches 0 run "
                + fittings.text_line(b.tag, label(b, False)),
                # a red label that shows through the machinery
                f"execute if score {v} matches 0 "
                f"run data merge entity {mark} {{see_through:1b}}",
                f"scoreboard players operation {shown} = {v}",
            ],
        )
        breakers += [
            # (a lever that is gone would be a breaker nobody could close)
            f"execute unless block {_xyz(b.lever)} minecraft:lever "
            f"run {_setblock(b.lever, b.block(False))}",
            f"scoreboard players set {v} 0",
            f"execute {_if_block(b.lever, 'minecraft:lever[powered=true]')} "
            f"run scoreboard players set {v} 1",
            f"execute unless score {v} = {shown} run {call(f'breaker/{b.index}')}",
        ]
        # tripped: the lever taken out and put back open, so that whatever
        # is beside it is told
        pack.function(
            f"{base}/trip/{b.index}",
            [
                *fittings.lever_put_lines(b.lever, b.block(False)),
                sound("entity.lightning_bolt.thunder", b.lever, 3, 1.3),
                fx("electric_spark", middle(b.lamp, 0.5), "0.4 0.4 0.4", 0.3, 30),
            ],
        )
    breakers += [
        _set("closed", 0),
        *(_op("closed", "+=", b.score) for b in place.breakers),
    ]
    pack.function(f"{base}/breakers", breakers)
    # all three closed and showing it, whatever they were
    pack.function(
        f"{base}/close",
        [
            *(_setblock(b.lever, b.block(True)) for b in place.breakers),
            call("breakers"),
        ],
    )

    # -- the charge: up while all three are closed; a trip at each quarter
    fighting = f"{state('1')} if score {_s('wait')} matches 0"
    trips = [
        f"scoreboard players add {_s('stage')} 1",
        _op("charge", "=", "#fdy.stage"),
        _op("charge", "*=", f"#{QUARTER}"),
        _op("floor", "=", "#fdy.charge"),
    ]
    for form, by_stage in TRIP.items():
        for stage, which in by_stage.items():
            when = (
                f"execute if score {_s('form')} matches {form} "
                f"if score {_s('stage')} matches {stage} run"
            )
            trips += [f"{when} {call(f'trip/{i}')}" for i in which]
            # one title naming every breaker of the stage (a second title
            # in the same tick would replace the first)
            out = [place.breakers[i] for i in which]
            names = " AND ".join(x.name for x in out)
            levels = " and ".join(x.level for x in out)
            many = "S" if len(out) > 1 else ""
            trips += [
                f"{when} {line}"
                for line in title(
                    f"BREAKER{many} {names} TRIPPED",
                    f"On the {levels}",
                    "red",
                )
            ]
    trips += [call("breakers"), hint_breaker.arm]
    pack.function(f"{base}/trip_stage", trips)
    pack.function(
        f"{base}/charge",
        [
            f"execute unless score {_s('state')} matches 1 run return 0",
            f"execute if score {_s('wait')} matches 1.. run return 0",
            f"execute if score {_s('closed')} matches 3 run {_op('charge', '+=', '#fdy.rate')}",
            f"execute if score {_s('closed')} matches 3 run {hint_breaker.progress}",
            *(
                f"execute if score {_s('stage')} matches {stage} "
                f"if score {_s('charge')} matches {(stage + 1) * QUARTER}.. "
                f"run {call('trip_stage')}"
                for stage in reversed(range(TRIPS))
            ),
            f"execute if score {_s('charge')} matches {FULL}.. run {call('done')}",
        ],
    )

    # -- the mast and the bossbar, drawn when the charge changes
    mast = [
        f"execute if score {_s('n')} > {_s('n.shown')} run "
        + sound("block.note_block.bell", place.switch, 2, 0.8),
    ]
    for column in place.mast:
        mast += fittings.gauge_lines(column, _s("n"), 1, lit, dark)
    pack.function(f"{base}/mast", [*mast, _op("n.shown", "=", "#fdy.n")])
    pack.function(
        f"{base}/show",
        [
            _op("n", "=", "#fdy.charge"),
            _op("n", "/=", f"#{CELL}"),
            f"execute unless score {_s('n')} = {_s('n.shown')} run {call('mast')}",
            bar.value_line(_s("charge")),
        ],
    )

    # -- the waves: the core's, cast by the dome's form and the quarter
    points = wave_points(place)
    cast = {
        kind: automatons.waves(
            pack,
            INDEX,
            where,
            kinds=(kind,),
            base=f"{base}/wave/{kind.key}",
            cap=MOST,
            near=2 * dome.radius + 2,
        ).cast
        for kind, where in points.items()
    }

    def want(numbers: tuple[int, int, int], score: str) -> list[str]:
        solo, duo, more = numbers
        return [
            f"function {pack.id('mob/count')} "
            f"{{dome:{INDEX},solo:{solo},duo:{duo},more:{more}}}",
            f"scoreboard players operation {score} {OBJ} = #mob.n {OBJ}",
        ]

    riveters = f"#wave{INDEX}.{automatons.RIVETER.key}"
    husks = f"#wave{INDEX}.{automatons.SLAG_HUSK.key}"
    stokers = f"#wave{INDEX}.{automatons.STOKER.key}"

    def room_for(kind: automatons.Kind, cap: str, asked: str) -> list[str]:
        """no more of a kind asked for than its cap leaves room for"""
        return [
            f"execute store result score {_s('t')} "
            f"if entity {automatons.selector(INDEX, f'tag={kind.tag}')}",
            _op(cap, "-=", "#fdy.t"),
            f"execute if score {_s(cap)} matches ..-1 run {_set(cap, 0)}",
            f"scoreboard players operation {asked} {OBJ} < {_s(cap)}",
        ]

    pack.function(
        f"{base}/temper",
        [
            # they find a player on any level, and the sun through the top
            # of the glass does not burn them
            f"execute as {mobs} run attribute @s minecraft:follow_range base set {FOLLOW}",
            f"effect give {mobs} minecraft:fire_resistance 3600 0 true",
        ],
    )
    num, den = LAST_GAP
    pack.function(
        f"{base}/cast",
        [
            *want(CAP, f"#wave{INDEX}.cap"),
            *want(STOKERS, stokers),
            *want(RIVETERS, riveters),
            *want(HUSKS, husks),
            *want(RIVETER_CAP, "#fdy.rcap"),
            # the Stokers leave room for the others (the Riveters' cap and
            # a wave of Slag Husks), so that a room full of Stokers nobody
            # has killed still gets its archers
            _op("scap", "=", f"#wave{INDEX}.cap"),
            _op("scap", "-=", "#fdy.rcap"),
            f"scoreboard players operation {_s('scap')} -= {husks} {OBJ}",
            *room_for(automatons.STOKER, "scap", stokers),
            # never more Riveters alive than their own cap
            *room_for(automatons.RIVETER, "rcap", riveters),
            # Riveters from the second quarter, Slag Husks from the third
            f"execute unless score {_s('stage')} matches 1.. "
            f"run scoreboard players set {riveters} {OBJ} 0",
            f"execute unless score {_s('stage')} matches 2.. "
            f"run scoreboard players set {husks} {OBJ} 0",
            *cast.values(),
            call("temper"),
            *unflare,
            *(
                fx("large_smoke", middle(cell, 1), "0.8 0.5 0.8", 0.02, 20)
                for cell in (*place.stokers, *place.riveters)
            ),
            sound("block.anvil.land", place.stokers[0], 2, 0.6),
            sound("block.anvil.land", place.stokers[1], 2, 0.7),
            # the next wave: sooner in the last quarter
            _op("next", "=", "#fdy.gap"),
            f"execute if score {_s('stage')} matches {TRIPS} "
            f"run {_op('next', '*=', f'#{num}')}",
            f"execute if score {_s('stage')} matches {TRIPS} "
            f"run {_op('next', '/=', f'#{den}')}",
        ],
    )
    pack.function(
        f"{base}/warn",
        [
            *flare,
            sound("block.bell.use", place.stokers[0], 2, 0.7),
            sound("block.bell.use", place.stokers[1], 2, 0.7),
            *(
                fx("flame", middle(cell, 1), "0.8 0.6 0.8", 0.02, 12)
                for cell in place.stokers
            ),
        ],
    )
    pack.function(
        f"{base}/wave/clock",
        [
            f"scoreboard players remove {_s('next')} 1",
            f"execute if score {_s('next')} matches {WARN} run {call('warn')}",
            f"execute if score {_s('next')} matches ..0 run {call('cast')}",
        ],
    )
    # an automaton that has left the dome goes back to where it was cast
    pack.function(
        f"{base}/leash",
        [
            f"execute as "
            f"{automatons.selector(INDEX, f'tag={kind.tag},tag={automatons.home_tag(i)}')} "
            f"unless entity @s[{domes.sphere(dome)}] run tp @s {middle(point)}"
            for kind, where in points.items()
            for i, point in enumerate(where)
        ],
    )

    # -- the end
    pack.function(
        f"{base}/done",
        [
            _set("state", 2),
            _set("bus", 0),
            f"execute at {mobs} run particle minecraft:cloud ~ ~1 ~ 0.3 0.6 0.3 0.02 12",
            automatons.remove_line(INDEX),
            sound("entity.lightning_bolt.thunder", place.crown, 4, 0.7),
            fx("electric_spark", middle(place.crown, 1), "0.8 1.5 0.8", 0.6, 120),
            call("steady"),
            f"function {pack.id(f'dome/{INDEX}/solved')}",
        ],
    )
    # the room once charged: steady, and nothing left to work
    pack.function(
        f"{base}/steady",
        [
            _set("state", 2),
            _set("wait", 0),
            _set("charge", FULL),
            _set("n", CELLS),
            call("mast"),
            call("close"),
            fittings.lever_hold_line(place.switch, switch_on),
            *unflare,
            bar.hide,
        ],
    )
    bus_lit = len(place.bus) * 3
    bus = fittings.gauge_lines(place.bus, _s("bus"), 3, lit, dark)
    pack.function(f"{base}/bus", [f"scoreboard players add {_s('bus')} 1", *bus])
    pack.function(f"{base}/bus/draw", bus)
    pack.function(
        f"{base}/restored", [call("steady"), _set("bus", bus_lit), call("bus/draw")]
    )

    # -- leaving in the fight is a checkpoint; coming back takes it up
    pack.function(
        f"{base}/checkpoint",
        [
            # (the core has just removed the automatons)
            _op("charge", "=", "#fdy.floor"),
            _set("wait", RESUME),
            # (the breakers are left as they are: leaving answers no trip)
            _op("n", "=", "#fdy.charge"),
            _op("n", "/=", f"#{CELL}"),
            _op("n.shown", "=", "#fdy.n"),
            call("mast"),
            *unflare,
            bar.hide,
        ],
    )
    pack.function(
        f"{base}/waiting",
        [
            f"scoreboard players remove {_s('wait')} 1",
            f"execute if score {_s('wait')} matches ..0 run {call('resume')}",
        ],
    )
    pack.function(
        f"{base}/resume",
        [
            # (a safe point: a level voted while the dome was left is taken)
            call("scale"),
            _set("wait", 0),
            _set("next", FIRST),
            *title("THE FOUNDRY WAKES", "The charge is where you left it", "red"),
            sound("block.beacon.activate", place.switch, 2, 0.6),
            bar.value_line(_s("charge")),
            bar.show,
        ],
    )

    # -- the machinery (no part of the fight: nothing above reads it)
    ax, az = fr.right
    step = 1 / 8
    east, west = (middle(cell) for cell in place.ladle)
    ladle = f"@e[type=minecraft:block_display,tag={LADLE_TAG}]"
    crane = _s("crane")

    def move(way: int) -> str:
        dx, dz = (f"~{v:g}" if v else "~" for v in (way * step * ax, way * step * az))
        return f"execute as {ladle} at @s run tp @s {dx} ~ {dz}"

    pour = (f"{place.ladle[1][0] + 0.5} {place.ladle[1][1] - 0.2} ") + (
        f"{place.ladle[1][2] + 0.5}"
    )
    pack.function(
        f"{base}/crane",
        [
            f"scoreboard players add {crane} 1",
            f"execute if score {crane} matches 1..{TRAVEL} run {move(-1)}",
            f"execute if score {crane} matches {TRAVEL + 1} run tp {ladle} {west}",
            f"execute if score {crane} matches {TRAVEL + 1}..{TRAVEL + PAUSE} "
            f"run {call('crane/pour')}",
            f"execute if score {crane} matches {TRAVEL + 20} run {call('crane/hot')}",
            f"execute if score {crane} matches {TRAVEL + PAUSE + 1}.."
            f"{2 * TRAVEL + PAUSE} run {move(1)}",
            f"execute if score {crane} matches {2 * TRAVEL + PAUSE + 1} "
            f"run {call('crane/cool')}",
            f"execute if score {crane} matches {PERIOD}.. run {call('crane/park')}",
        ],
    )
    pack.function(
        f"{base}/crane/pour",
        [
            fx("falling_lava", pour, "0.15 0 0.15", 0, 3),
            fx("lava", middle(place.pour[4], 1.1), "1.5 0 1.5", 0, 1),
        ],
    )
    pack.function(
        f"{base}/crane/hot",
        [
            *(_setblock(cell, HOT) for cell in place.pour),
            sound("block.lava.extinguish", place.pour[4], 1, 0.6),
        ],
    )
    pack.function(f"{base}/crane/cool", [_setblock(c, COOL) for c in place.pour])
    pack.function(f"{base}/crane/park", [_set("crane", 0), f"tp {ladle} {east}"])
    pack.function(f"{base}/rest", [call("crane/park"), call("crane/cool")])
    smoke = [
        f"particle minecraft:campfire_cosy_smoke {middle(cell)} 0.2 0.5 0.2 0.01 1"
        for cell in place.smoke
    ]

    # -- a step, and the hooks
    pack.function(f"{base}/book", [_setblock(place.lectern, logbook(fr))])
    pack.function(
        f"{base}/step",
        [
            # a room never set up has no values: a rate of nothing
            f"execute unless score {_s('rate')} matches 1.. run {call('arm')}",
            call("switch"),
            call("breakers"),
            call("charge"),
            call("show"),
            f"execute {state('1')} run {call('leash')}",
            *(
                f"execute {state('1')} run {line}"
                for line in automatons.sweep_lines(dome)
            ),
            f"execute {_if_block(place.lectern, 'minecraft:lectern[has_book=false]')} "
            f"run {call('book')}",
        ],
    )
    pack.function(
        f"{base}/tick",
        [
            # the machinery, whether or not there is a fight: the ladle
            # (twice as fast in the fight), smoke, the bus bar lighting
            call("crane"),
            f"execute {fighting} run {call('crane')}",
            f"scoreboard players add {_s('tick')} 1",
            *(f"execute if score {_s('tick')} matches {STEP} run {s}" for s in smoke),
            f"execute {state('2')} if score {_s('bus')} matches ..{bus_lit - 1} "
            f"run {call('bus')}",
            f"execute if score {_s('tick')} matches {STEP}.. {state('2')} "
            f"{_if_block(place.lectern, 'minecraft:lectern[has_book=false]')} "
            f"run {call('book')}",
            f"execute if score {_s('tick')} matches {STEP}.. "
            f"unless score {open_dome} matches 1 run {_set('tick', 0)}",
            f"execute unless score {open_dome} matches 1 run return 0",
            f"execute {state('0')} run {hint_switch.tick}",
            f"execute {state('1')} if score {_s('wait')} matches 1.. "
            f"run {call('waiting')}",
            f"execute {fighting} run {call('wave/clock')}",
            f"execute {fighting} if score {_s('closed')} matches ..2 "
            f"run {hint_breaker.tick}",
            f"execute unless score {_s('tick')} matches {STEP}.. run return 0",
            _set("tick", 0),
            call("step"),
        ],
    )
    first = f"if score {open_dome} matches 1 if score #first {OBJ} matches 1"
    # (a score that was never set matches nothing: idle is "not started")
    idle = f"unless score {_s('state')} matches 1.."
    pack.function(
        f"{base}/enter",
        [
            # the core's signal: the first into an empty room
            f"execute {first} {idle} run {call('arm')}",
            f"execute {first} {state('1')} run tellraw @s "
            '{text:"The Foundry is waiting: the charge is where the last '
            'quarter left it.",color:"gray",italic:true}',
            f"execute if score {open_dome} matches 1 {idle} run tellraw @s "
            '{text:"The Foundry is cold. The brass plaque says what to do.",'
            'color:"gray",italic:true}',
            f"execute if score {open_dome} matches 2 run {call('restored')}",
        ],
    )
    pack.function(
        f"{base}/arm",
        [call("reset"), call("scale"), _set("live", 1), hint_switch.arm],
    )
    pack.function(
        f"{base}/empty",
        [
            call("rest"),
            f"execute if score {open_dome} matches 1 {state('1')} "
            f"run {call('checkpoint')}",
            f"execute if score {open_dome} matches 1 {idle} run {call('reset')}",
            f"execute if score {open_dome} matches 2 run {call('restored')}",
            _set("live", 0),
        ],
    )
    # the form: recorded, to take force at the next trip and the next wave
    pack.function(
        f"{base}/relief",
        [
            *(
                f"execute if score {_s('stage')} matches {stage} "
                f"run {_setblock(place.breakers[i].lever, place.breakers[i].block(True))}"
                for stage, i in RELIEF.items()
            ),
            call("breakers"),
            say("Relief relay: one engineer, one breaker. The other has closed."),
        ],
    )
    pack.function(
        f"{base}/solo",
        [
            f"execute if score {_s('form')} matches 2 {state('1')} "
            f"if score {_s('stage')} matches 1.. "
            f"if score {_s('closed')} matches ..1 run {call('relief')}",
            _set("form", 1),
        ],
    )
    pack.function(
        f"{base}/duo",
        [
            f"execute if score {_s('form')} matches 1 {state('0..1')} run "
            + say("Two engineers: the breakers will trip two at a time."),
            _set("form", 2),
        ],
    )
    # a death: a cell of charge, never more than the quarter in progress
    pack.function(
        f"{base}/died",
        [
            f"execute unless score {_s('state')} matches 1 run return 0",
            _op("charge", "-=", "#fdy.pen"),
            _op("charge", ">", "#fdy.floor"),
            say("An engineer is down: the accumulator loses charge.", "red"),
            sound("block.beacon.deactivate", place.switch, 2, 0.8),
        ],
    )
    zeroed = ("state", "charge", "stage", "floor", "wait", "next", "bus", "tick")
    zeroed += ("live", "n", "n.shown", "closed", "rcap", "scap", "t")
    pack.function(
        f"{base}/reset",
        [
            call("scale"),
            *(_set(name, 0) for name in zeroed),
            # (the form is the core's to say: a reset with two in the room
            # leaves it duo)
            _set("form", 1),
            f"execute if score #form{INDEX} {OBJ} matches 2 run {_set('form', 2)}",
            automatons.remove_line(INDEX),
            *fittings.lever_put_lines(place.switch, switch_off),
            *(
                line
                for b in place.breakers
                for line in fittings.lever_put_lines(b.lever, b.block(True))
            ),
            # (the levers read, and each lamp and label made to match)
            *(f"scoreboard players set {_s(f's{b.index}')} -1" for b in place.breakers),
            call("breakers"),
            call("mast"),
            call("bus/draw"),
            *unflare,
            bar.hide,
            call("rest"),
            f"execute {_if_block(place.lectern, 'minecraft:lectern[has_book=false]')} "
            f"run {call('book')}",
        ],
    )


# --------------------------------------------------------------- the check

S1, S2 = "st.fd1", "st.fd2"


def check(ctx: Any) -> list[str]:
    """
    Work the Foundry in place over RCON. A player is stood in for by an
    armour stand that the core counts (``game.STANDIN``): it is put at the
    entrance to come in and in the tunnel to go out; a lever is thrown by
    setting the block as a hand would leave it; a death is the stand-in's
    ``st.died`` set by hand; the charge is moved on by setting its score
    (a whole fight is some minutes of ticks) and a wave is brought on by
    setting its clock. Leaves the room and its tunnel reset, the scores it
    changed as it found them and no stand-in or automaton behind. It
    resets this dome and its tunnel only, never the game.

    What stand-ins cannot prove (all in the play-test list): that an
    automaton notices, reaches or hurts a player on any level (a zombie
    ignores an armour stand: here they only stand about), climbs a stair
    or is stopped by a ladder; that the fight is fair; a real death, the
    respawn, the Resistance and the kit (aimed at ``@a``, and the core's);
    a hand on a lever, and a trip seen in front of you; the titles,
    sounds, particles and the bossbar as shown (only that the bar is on);
    a label's red text through the machinery (``see_through`` is read
    back, not seen); the ladle as a thing seen moving (its position is
    read); the recall button (the core answers it: only its entity is
    counted here). Peaceful is tried by changing the world's difficulty
    for a moment with nobody online; it is put back whatever happens, and
    so is the level (``game_checks.save_level``).
    """
    game_checks.no_run(ctx)
    saved_level = game_checks.save_level(ctx)
    try:
        return _check(ctx)
    finally:
        game_checks.restore_level(ctx, saved_level)
        ctx.function("difficulty/apply")


def _check(ctx: Any) -> list[str]:
    dome = ctx.layout.DOMES[INDEX]
    tunnel = ctx.layout.TUNNELS[INDEX]
    place = room(dome)
    fr = place.frame
    problems: list[str] = []
    scan = game_checks.SCAN
    base = f"dome/{INDEX}"
    a, b, c = place.breakers
    mobs = automatons.selector(INDEX)
    lit, dark = f"{BULB}[lit=true]", f"{BULB}[lit=false]"
    switch_on = fittings.lever(place.switch_facing, True)
    switch_off = fittings.lever(place.switch_facing)

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def get(name: str) -> int:
        return ctx.score(f"#fdy.{name}") or 0

    def put(name: str, value: int) -> None:
        ctx.set_score(f"#fdy.{name}", value)

    outside = middle(tunnels.at(ctx.layout.TUNNELS[INDEX - 1], 8, 0, 1))
    entrance = middle(domes.entrance(dome)[:3])

    def come_in(tag: str = S1) -> None:
        """a stand-in out of the dome and in again: a new entry"""
        game_checks.stand_at(ctx, tag, outside)
        ctx.advance(game_checks.EMPTY)  # (a dome is empty 3 s after its last player)
        game_checks.stand_at(ctx, tag, entrance)

    def throw(breaker: Breaker, closed: bool) -> None:
        ctx.setblock(breaker.lever, breaker.block(closed))

    def levers() -> list[bool]:
        return [ctx.is_block(x.lever, x.block(True)) for x in place.breakers]

    def alive(kind: automatons.Kind | None = None) -> int:
        more = f"tag={kind.tag}" if kind else ""
        return ctx.count(automatons.selector(INDEX, more))

    def mast_lit() -> int:
        return sum(ctx.is_block(cell, lit) for column in place.mast for cell in column)

    def bar_shown() -> bool:
        reply = ctx.cmd(f"bossbar get {automatons.bar_id(INDEX)} visible", "currently")
        return "visible" in reply

    def cast_now() -> None:
        """the next wave, now"""
        put("next", 1)
        ctx.advance(3)

    def label_of(breaker: Breaker, what: str = "text") -> str:
        return ctx.data(f"entity {fittings.display_selector(breaker.tag)} {what}")

    def ladle_at() -> str:
        """where the ladle is: ``east`` (parked), ``west`` or ``between``"""
        pos = ctx.data(f"entity @e[tag={LADLE_TAG},limit=1] Pos")
        try:
            x, _, z = (float(v.strip().rstrip("d")) for v in pos.strip("[]").split(","))
        except ValueError:
            return f"not read ({pos!r})"
        for name, cell in zip(("east", "west"), place.ladle, strict=True):
            if abs(x - cell[0] - 0.5) + abs(z - cell[2] - 0.5) < 0.2:
                return name
        return "between"

    def as_built(what: str, parked: bool = True) -> None:
        """every block of the room is as ``reset`` leaves it (a block of
        the battery's clock: the same block, in whatever state), the
        scores are nil, every breaker reads closed and its label is the
        plain one, nothing is left of a fight, and (``parked``: with
        nobody in the dome to keep it travelling) the ladle is parked"""
        blocks = room_blocks(dome)
        # (with someone in the dome the ladle pours: the pouring floor may
        # be glowing by the time it is read)
        pouring = set() if parked else set(place.pour)
        wrong = [
            cell
            for cell, block in blocks.everything().items()
            if cell not in pouring
            and not ctx.is_block(
                cell,
                rooms.name(block) if cell in blocks.moving else block.partition("{")[0],
            )
            # (a piston caught in mid stroke)
            and not (
                cell in blocks.moving and ctx.is_block(cell, "minecraft:moving_piston")
            )
        ]
        wrong += [cell for cell in blocks.clear if not ctx.is_block(cell, AIR)]
        if wrong:
            problems.append(f"{what}: {len(wrong)} blocks not as built: {wrong[:6]}")
        names = ("state", "charge", "stage", "wait", "bus", "live")
        got = {n: get(n) for n in names}
        expect(f"{what}: the scores", got, dict.fromkeys(names, 0))
        expect(f"{what}: the breakers read closed", get("closed"), 3)
        for x in place.breakers:
            text = label_of(x)
            if "OUT" in text or f"BREAKER {x.name}" not in text:
                problems.append(f"{what}: breaker {x.name}'s label reads {text!r}")
        expect(f"{what}: automatons", alive(), 0)
        expect(f"{what}: the bossbar shown", bar_shown(), False)
        if parked:
            expect(f"{what}: the ladle", ladle_at(), "east")

    def battery_runs(what: str) -> None:
        """the stamp battery, which nothing starts or stops: each of its
        four lamps seen lit and dark and both pistons out and in, in 6 s"""
        machine = place.machine
        lamps: list[set[bool]] = [set() for _ in machine.lamps]
        heads: list[set[bool]] = [set() for _ in machine.pistons]
        for _ in range(40):
            ctx.advance(3)
            for cell, seen in zip(machine.lamps, lamps, strict=True):
                seen.add(ctx.is_block(cell, lit))
            for cell, seen in zip(machine.pistons, heads, strict=True):
                seen.add(ctx.is_block(cell, "minecraft:piston[extended=true]"))
        if lamps != [{True, False}] * 4 or heads != [{True, False}] * 2:
            problems.append(f"{what}: the battery's lamps {lamps}, pistons {heads}")

    def unsolve() -> None:
        """the room and its tunnel put back, the dome open and unsolved"""
        ctx.function(f"tunnel/{INDEX}/reset")
        ctx.function(f"{base}/reset")
        ctx.set_score(f"#d{INDEX}", 1)
        ctx.set_score(f"#d{INDEX + 1}", saved[f"#d{INDEX + 1}"] or 0)
        ctx.set_score("#solved", saved["#solved"] or 0)

    def start_fight() -> None:
        ctx.setblock(place.switch, switch_on)
        ctx.advance(STEP + 2)

    # ---- before: nobody about, the room and its tunnel reset, the dome open
    names = (f"#d{INDEX}", f"#d{INDEX + 1}", "#solved")
    saved = game_checks.scores(ctx, *names)
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan)
    if (others := ctx.score("#players")) or ctx.score(f"#form{INDEX}"):
        return [f"{others} players or stand-ins of another check are in the game"]
    unsolve()
    ctx.advance(scan)
    as_built("built")
    got = {
        "recall": ctx.count(f"@e[type=minecraft:interaction,tag={ENTITY_TAG}]"),
        "labels": ctx.count(f"@e[type=minecraft:text_display,tag={ENTITY_TAG}]"),
        "ladle": ctx.count(f"@e[type=minecraft:block_display,tag={LADLE_TAG}]"),
    }
    expect("the room's entities", got, {"recall": 1, "labels": 4, "ladle": 4})
    if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("the logbook is not on the lectern")
    battery_runs("nobody in")
    expect("the ladle with nobody in", ladle_at(), "east")

    # ---- solo: in, the room armed and quiet; the ladle travels
    game_checks.stand_at(ctx, S1, entrance)
    got = {n: get(n) for n in ("live", "form", "state")}
    expect("solo, entered", got, {"live": 1, "form": 1, "state": 0})
    level = ctx.score("#active") or game.DEFAULT_LEVEL
    rate, pen = scaled(level)["rate"], scaled(level)["pen"]
    expect("the level's values", {n: get(n) for n in scaled(level)}, scaled(level))
    ctx.advance(40)
    expect("the ladle with someone in", ladle_at(), "between")
    ctx.advance(FIRST + GAP // 4)
    expect("idle: nothing cast, no charge", (alive(), get("charge")), (0, 0))
    # Peaceful: the switch is thrown back and nothing starts
    found = ctx.cmd("difficulty", "difficulty").split()[-1].lower()
    if found not in ("peaceful", "easy", "normal", "hard"):
        found = "easy"
    try:
        ctx.cmd("difficulty peaceful")
        start_fight()
        got = (get("state"), ctx.is_block(place.switch, switch_off))
        expect("Peaceful: the fight not started, the switch back", got, (0, True))
    finally:
        ctx.cmd(f"difficulty {found}")
        ctx.function("fight/difficulty")

    # ---- the switch: the fight, the warning, the first wave, the charge
    start_fight()
    expect("the switch thrown: the fight", get("state"), 1)
    expect("the switch thrown: the bossbar shown", bar_shown(), True)
    expect("the first wave is on its way", 0 < get("next") <= FIRST, True)
    ctx.setblock(place.switch, switch_off)
    ctx.advance(STEP + 2)
    expect("the switch held over", ctx.is_block(place.switch, switch_on), True)
    expect("nothing cast yet", alive(), 0)
    put("next", WARN + 2)
    ctx.advance(4)
    flared = [ctx.is_block(cell, lit) for cell in place.telltales]
    expect("the moulds' lamps, 2 s before a wave", flared, [True] * len(flared))
    ctx.advance(WARN + STEP)
    one = wave(level, 1, 0)
    got = {k.key: alive(k) for k in automatons.KINDS}
    expect("the first wave", got, {"stoker": one["stoker"], "riveter": 0, "husk": 0})
    flared = [ctx.is_block(cell, dark) for cell in place.telltales]
    expect("the moulds' lamps after it", flared, [True] * len(flared))
    expect("none left undressed", ctx.count(f"{mobs[:-1]},tag={automatons.NEW}]"), 0)
    homes = [
        alive() and ctx.count(f"{mobs[:-1]},tag={automatons.home_tag(i)}]")
        for i in (0, 1)
    ]
    expect("cast in both moulds in turn", all(homes) or one["stoker"] < 2, True)
    reply = ctx.cmd(
        f"attribute {mobs[:-1]},limit=1] minecraft:follow_range base get", "is "
    )
    expect(f"an automaton's follow range ({reply!r})", f"{FOLLOW}" in reply, True)
    before = get("charge")
    ctx.advance(4 * STEP)
    expect("the charge climbs", get("charge") > before > 0, True)
    # a breaker opened by hand: the charge stands, its lamp and label show it
    throw(a, False)
    ctx.advance(2 * STEP)
    stood = get("charge")
    ctx.advance(10 * STEP)
    got = {
        "closed": get("closed"),
        "moved": get("charge") - stood,
        "lamp": ctx.is_block(a.lamp, dark),
        "label": "OUT" in label_of(a),
    }
    want = {"closed": 2, "moved": 0, "lamp": True, "label": True}
    expect("breaker A opened by hand, 5 s", got, want)
    throw(a, True)
    ctx.advance(3 * STEP)
    if get("charge") <= stood or not ctx.is_block(a.lamp, lit):
        problems.append("breaker A closed again: the charge did not go on")

    # ---- the first quarter: breaker A trips, the charge stands, Riveters
    put("charge", QUARTER - rate)
    ctx.advance(2 * STEP)
    got = {"stage": get("stage"), "charge": get("charge"), "levers": levers()}
    want = {"stage": 1, "charge": QUARTER, "levers": [False, True, True]}
    expect("solo, the first quarter: A trips", got, want)
    expect("the tripped breaker's label is out", "OUT" in label_of(a), True)
    expect("and set to show through", label_of(a, "see_through"), "1b")
    ctx.advance(6 * STEP)
    expect("a breaker out: the charge stands", get("charge"), QUARTER)
    throw(a, True)
    ctx.advance(2 * STEP)
    expect("A closed: the charge goes on", get("charge") > QUARTER, True)
    # the waves: Riveters from the second quarter, never beyond the caps
    ctx.cmd(automatons.remove_line(INDEX))
    most = {"all": 0, "stoker": 0, "riveter": 0}
    for _ in range(8):
        cast_now()
        now = {"all": alive(), "stoker": alive(automatons.STOKER)}
        now["riveter"] = alive(automatons.RIVETER)
        most = {k: max(most[k], now[k]) for k in most}
        put("charge", QUARTER + CELL)  # (the charge held where it is)
    two = wave(level, 1, 1)
    want = {"stoker": two["stoker_cap"], "riveter": two["riveter_cap"]}
    want["all"] = want["stoker"] + want["riveter"]
    expect("eight waves, nothing killed: the most alive", most, want)
    expect("the most alive within the cap", most["all"] <= two["cap"], True)
    ctx.cmd(automatons.remove_line(INDEX))
    cast_now()
    got = {k.key: alive(k) for k in automatons.KINDS}
    want = {"stoker": two["stoker"], "riveter": two["riveter"], "husk": 0}
    expect("all removed, the next wave", got, want)
    # the leash: one taken into the tunnel is back in the dome within a step
    ctx.cmd(f"tp {mobs[:-1]},limit=1] {outside}")
    ctx.advance(STEP + 2)
    inside = ctx.count(f"{mobs[:-1]},{domes.sphere(dome)}]")
    expect("automatons in the dome after one was taken out", inside, alive())

    # ---- a death (the stand-in's score set by hand): a cell, and never
    # below the last quarter
    put("charge", QUARTER + 3 * CELL)
    ctx.cmd(f"scoreboard players set @e[tag={S1}] st.died 1")
    ctx.advance(3)
    lost = QUARTER + 3 * CELL - get("charge")
    if not pen - 3 * rate <= lost <= pen:
        problems.append(f"a death cost {lost} of charge, expected {pen}")
    expect("the death answered", ctx.score(f"@e[tag={S1},limit=1]", "st.died"), 0)
    put("charge", QUARTER + 10)
    ctx.cmd(f"scoreboard players set @e[tag={S1}] st.died 1")
    ctx.advance(3)
    if not QUARTER <= get("charge") <= QUARTER + 10 + 3 * rate:
        problems.append(f"a death just over a quarter left {get('charge')}")

    # ---- duo: a second player; the next wave and the next trip are a pair's
    game_checks.stand_at(ctx, S2, entrance)
    ctx.advance(scan)
    expect("two in: the form", (ctx.score(f"#form{INDEX}"), get("form")), (2, 2))
    expect("two in: nothing tripped by it", levers(), [True, True, True])
    cast_now()
    cap = ctx.score(f"#wave{INDEX}.cap")
    expect("two in: the cap of the next wave", cap, wave(level, 2, 1)["cap"])
    put("charge", 2 * QUARTER - rate)
    ctx.advance(2 * STEP)
    got = {"stage": get("stage"), "charge": get("charge"), "levers": levers()}
    want = {"stage": 2, "charge": 2 * QUARTER, "levers": [True, False, False]}
    expect("duo, the second quarter: B and C trip", got, want)
    ctx.cmd(automatons.remove_line(INDEX))
    cast_now()
    three = wave(level, 2, 2)
    got = {k.key: alive(k) for k in automatons.KINDS}
    want = {"stoker": three["stoker"], "riveter": three["riveter"]}
    want["husk"] = three["husk"]
    expect("duo, a wave in the third quarter: Slag Husks too", got, want)
    # one leaves: solo within a few seconds, and the second closes itself
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan)
    expect("one left: the form", (ctx.score(f"#form{INDEX}"), get("form")), (1, 1))
    expect("one left: the relief relay", levers(), [True, False, True])
    expect("one left: the fight goes on", (get("state"), get("stage")), (1, 2))
    throw(b, True)
    ctx.advance(2 * STEP)
    expect("B closed: the charge goes on", get("charge") > 2 * QUARTER, True)

    # ---- leaving is a checkpoint: back to the last quarter, and on again
    put("charge", 2 * QUARTER + 2 * CELL)
    cast_now()
    throw(a, False)
    ctx.advance(STEP)
    game_checks.stand_at(ctx, S1, outside)  # a step out of the dome: under 3 s
    got = {
        "state": get("state"),
        "kept": get("charge") > 2 * QUARTER,
        "automatons": alive() > 0,
    }
    expect("out for a second", got, {"state": 1, "kept": True, "automatons": True})
    ctx.advance(game_checks.EMPTY)
    got = {
        "state": get("state"),
        "charge": get("charge"),
        "stage": get("stage"),
        "wait": get("wait"),
        "levers": levers(),
        "switch": ctx.is_block(place.switch, switch_on),
        "automatons": alive(),
        "bar": bar_shown(),
        "mast": mast_lit(),
    }
    want = {
        "state": 1,
        "charge": 2 * QUARTER,
        "stage": 2,
        "wait": RESUME,
        "levers": [False, True, True],
        "switch": True,
        "automatons": 0,
        "bar": False,
        "mast": 4 * (2 * QUARTER // CELL),
    }
    expect("the dome left in the fight: a checkpoint", got, want)
    # (a level voted while the dome was left: taken when the fight goes on)
    low = game.LEVELS[0]
    ctx.set_score("#level", low)
    game_checks.stand_at(ctx, S1, entrance)
    expect("back in: the charge kept", get("charge"), 2 * QUARTER)
    ctx.advance(RESUME + 2 * STEP)
    got = {
        "wait": get("wait"),
        "stood": get("charge") == 2 * QUARTER,
        "bar": bar_shown(),
        "values": {n: get(n) for n in scaled(low)},
    }
    want = {"wait": 0, "stood": True, "bar": True, "values": scaled(low)}
    expect("5 s after coming back, A still out", got, want)
    throw(a, True)
    ctx.advance(2 * STEP)
    expect("A closed: on again", get("charge") > 2 * QUARTER, True)
    ctx.set_score("#level", level)
    ctx.function("difficulty/apply")
    ctx.function(f"{base}/scale")
    ctx.advance(FIRST)
    expect("and a wave after that", alive() > 0, True)

    # ---- the end: the twelfth cell
    put("stage", TRIPS)
    put("floor", TRIPS * QUARTER)
    put("charge", FULL - rate)
    ctx.advance(2 * STEP)
    got = {
        "state": get("state"),
        "dome": ctx.score(f"#d{INDEX}"),
        "automatons": alive(),
        "mast": mast_lit(),
        "bar": bar_shown(),
    }
    want = {"state": 2, "dome": 2, "automatons": 0, "mast": 4 * CELLS, "bar": False}
    expect("charged", got, want)
    problems.extend(game_checks.pull_pump(ctx, INDEX))
    expect("tunnel 4 at the end", ctx.score(f"#t{INDEX}") in (1, 2), True)
    ctx.advance(len(place.bus) * 3 + STEP)
    bus = sum(ctx.is_block(x, lit) for x in place.bus)
    expect("the bus bar lit", bus, len(place.bus))
    ctx.advance(tunnels.event_ticks(tunnel) + 60)
    got = game_checks.scores(ctx, f"#t{INDEX}", f"#d{INDEX + 1}")
    expect("tunnel 4 open, dome 5 open", got, {f"#t{INDEX}": 2, f"#d{INDEX + 1}": 1})
    doors = [x for d in tunnels.ends(tunnel) for _, x in domes.door_cells(d, tunnel)]
    expect("door cells open", sum(ctx.is_block(x, AIR) for x in doors), len(doors))
    problems += [f"tunnel open: {p}" for p in domes.check_shell(ctx, dome, False)]
    # a second entry into the charged room: steady, and nothing is cast
    come_in()
    ctx.advance(FIRST + GAP // 2)
    got = {
        "state": get("state"),
        "automatons": alive(),
        "mast": mast_lit(),
        "switch": ctx.is_block(place.switch, switch_on),
    }
    want = {"state": 2, "automatons": 0, "mast": 4 * CELLS, "switch": True}
    expect("charged, entered again", got, want)

    # ---- an idle room left is put back; the level's values on a new entry
    unsolve()
    come_in()
    throw(c, False)
    game_checks.stand_at(ctx, S1, outside)
    ctx.advance(game_checks.EMPTY)
    expect("an idle room left: put back", (get("live"), levers()), (0, [True] * 3))
    for new in (game.LEVELS[0], game.LEVELS[-1]):
        ctx.set_score("#level", new)
        come_in()
        want = scaled(new)
        expect(f"level {new}: the values", {n: get(n) for n in want}, want)
    ctx.set_score("#level", level)
    ctx.function("difficulty/apply")

    # ---- reset, from a scrambled state: a duo fight past the first trip
    come_in()
    game_checks.stand_at(ctx, S2, entrance)
    start_fight()
    put("charge", QUARTER - 1)
    ctx.advance(2 * STEP)
    cast_now()
    put("charge", QUARTER + 2 * CELL + 1)
    ctx.setblock(place.lectern, f"minecraft:lectern[facing={fr.facing(-1, 0)}]")
    ctx.advance(2 * STEP)
    if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("a logbook taken from the lectern was not put back")
    got = (get("state"), get("stage"), levers(), alive() > 0, mast_lit() > 0)
    want = (1, 1, [False, False, True], True, True)
    expect("scrambled before the reset", got, want)
    ctx.function(f"{base}/reset")
    ctx.set_score(f"#d{INDEX}", 0)  # locked, so that nothing of the fight runs
    ctx.advance(STEP)
    # (the stand-ins are still in the dome, so the ladle is on its way again)
    as_built("reset from a scrambled state", parked=False)

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
    battery_runs("left")
    got, want = tunnels.counts(ctx, tunnel), tunnels.expected(tunnel, 0)
    expect("tunnel 4 left shut and flooded", got, want)
    problems += [f"left: {p}" for p in domes.check_shell(ctx, dome, False)]
    left = ctx.count(f"@e[tag={S1}]") + ctx.count(f"@e[tag={S2}]") + alive()
    expect("stand-ins and automatons left behind", left, 0)
    return problems


MODULE = game.Module(
    "foundry",
    stages={f"dome_{INDEX}_inside": build},
    functions=functions,
    checks={"foundry": check},
)
