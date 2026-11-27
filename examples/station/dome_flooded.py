"""
The Flooded Dome (dome ``INDEX``) of The Drowned Station: half under water, and
drained a deck at a time. Its build stage (``dome_<n>_inside``), its datapack
functions (``dome/<n>/...``) and its live check (``flooded_dome``).

**The room.** A dam of glass crosses the dome a few steps in from the
door and holds a basin of water ``TOP`` layers deep: the entry hall
behind it is always dry. Out of the flood rises a copper standpipe with a
gauge of lamps up its face, one lamp a layer of water. Stairs climb
beside the dam to a high walk over the water; from it bridges lead to a
balcony round the standpipe, to the crown on top of it and to a platform
in the east. Under the water are a machine deck, a lower deck and the
floor, with the airlock to the next tunnel and its pump engine at the
very bottom. *The water is the floor plan*: each pump takes a few layers
away and uncovers the next deck, the next pump and the next way down.

**The puzzle**, the same three times (``Sluice``: A, B, C). A pump moves
water only while its sluice is open, and the sluice's handle is never
where the pump is. Each stage has a *sluice control* on a brass post, a
*pump lever* on brass in a pump house, and a *gate* of iron bars in the
way to it. While the control is active the gate is open and, once the
pump lever has been thrown, the water falls a layer at a time; when the
control stops, the gate shuts and the water rests where it is. It never
comes back up, and a pump once thrown stays thrown.

- *Solo:* the control is a lever on a spring: thrown, it holds the gate
  open for a time (a line of eight lamps counts it down), then throws
  itself back. Throw it and run, or swim, for the pump.
- *Duo:* the control is a plate: the gate is open and the pump runs only
  while one player stands on it, and the other goes through.

A gate is open whenever anyone is on its inner side, and never shuts on
a cell with a player in it: nobody is ever shut in. Stage A is all in the
dry; B is through a culvert under the machine deck; C is a dive to a
gate at the foot of a cabin's plinth. Nothing here hurts but the air
meter.

**Two rules** (game.py). *Leaving* costs nothing here: ``empty`` puts the
control back and shuts the gate, and the water level and every pump
thrown are kept until the game's reset. *A change of form* never shuts a
gate early: solo to duo waits until the spring's clock has run out; duo
to solo is at once, and the lever appears thrown with a full clock if the
plate was held within the last few seconds (``GRACE``).

**The water** is written by the functions and by nothing else. The basin
(``basin``: everything east of the dam up to layer ``TOP``) is registered
with ``domes.add_wet``, so the core's wet check leaves it to this
module's own count (``station:check/dome/<n>/layer_<h>``, ``counts``).
``#fl.w`` is the top wet layer and the only record of the water;
``draw`` writes the whole room from the scores, so it is the reset and
the repair. Two rules from the rig, kept exactly:

- every cell of the basin that can hold water in itself (a stair, a
  ladder, a pipe, the bars of a gate, the pump engine's lightning rod) is
  written by ``draw`` and by its layer's function, waterlogged while its
  layer is wet and not when it is dry: none is left to the game;
- levers, plates and signs are taken out before any layer is made wet,
  and put back only where their stage has been uncovered.

**State** (scores in ``st``, all ``#fl.<name>``): ``w`` the top wet
layer; ``stage`` pumps finished, 0 to 3; ``form`` the form drawn (1 solo,
2 duo) and ``want`` the form the core asks for; ``live`` 1 once set up
for those in it; ``ctl`` the live control active; ``t`` steps left on the
spring; ``pump`` the live pump lever thrown; ``in`` players on the inner
side of the live gate, ``g`` in its own cells; ``gate`` the live gate
drawn open; ``d`` ticks to the next layer; ``rel`` steps since the plate
was last held; ``tgt`` and ``tt`` the live stage's target layer and full
clock; from the level (``scaled``): ``per`` ticks a layer, ``ta`` ``tb``
``tc`` the clocks in steps.

**Functions** (the core calls the hooks, see game.py):

- ``enter``: the first into an unsolved room sets it up (``arm``: the
  level's values, then ``draw``); the first into a solved one puts it
  right (``restored``);
- ``tick``: the machinery (``deco``), the hints, and every ``STEP`` ticks
  ``step``: ``swap`` (a form change at a safe point) -> ``read`` ->
  ``gate`` -> ``drain`` -> ``line``;
- ``drain`` runs ``layer_<h>/dry`` as each layer goes, and at the
  stage's target ``stage_done``, which at the third calls ``done``
  (``station:dome/<n>/solved``, then ``restored``);
- ``solo`` / ``duo``: only say what the room should become (``want``);
- ``empty``: the control back, the gate shut, the engine still; the
  water and the pumps kept;
- ``reset``: all of that, and the basin full again;
- ``guard`` (every tick, whoever is or is not in the dome): if its tunnel
  is pumping or open, or its pump waits for its lever (which stands in
  the basin), while the basin is wet, the room is made dry at once
  (``restored``). The room's own ``done`` never needs it; the core's
  checks call ``dome/<n>/solved`` and ``tunnel/<n>/open`` themselves, and the
  tunnel's doors must never open onto the flood. A room found dry by a
  player is solved if the tunnel is pumping or open, and flooded again
  (``reset``) if a tunnel's check has since shut it (``tick``).

**Machinery that only ticks** (``dressing``; nothing reads any of it,
none has a lever, button or plate, and everything a player can work
stands on brass with a sign): the *beam engine* on the crown (a torch
clock with a lamp chase and two plain pistons, real redstone, running
only while water is falling: the pack puts its torch in and takes it
out); the *tide clock* in a cage in the entry hall (the same clock,
running for ever, never wet, touched by no reset); the *drowned lamps*
(copper bulbs in two boilers on the machine deck and in the floor round
the standpipe's foot, blinked in turn by ``deco``, with bubbles from
vents in the floor, since redstone cannot live under water).

Everything is placed in the dome's own frame (fittings.py), so nothing
here is a world coordinate. The plan is pure data shared by the build,
the pack and the checks, and ``room_problems`` refuses a room that is
outside the dome or on reserved cells, that leaks, whose inputs are not
on brass, whose walks or sight lines are blocked, or in which a player
could be stranded at any level of the water (``lock_problems``).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cache
from typing import TYPE_CHECKING, Any

import datapack as dp
import domes
import fittings
import game
import game_checks
import rooms
import station_layout as layout
import tunnels
from domes import AIR, Cell, middle
from fittings import Frame, frame, snbt, wall_sign

if TYPE_CHECKING:
    from station_layout import Dome

INDEX = layout.index_of("flooded")  # the Flooded Dome's place in the ring
OBJ = game.OBJ

STEP = 2  # ticks between steps of the state machine
TOP = 11  # the top wet layer at the start (height above the floor)
#: the layer the water stands at before each stage, and after it
STARTS = (11, 7, 3)
TARGETS = (7, 3, 0)
# at level 5, scaled by the core's ``#diff.timer`` (``scaled``)
LAYER_TICKS = 30  # ticks between layers going
CLOCK_SECONDS = (22, 32, 28)  # the solo spring's time for A, B, C
HINT_SECONDS = 60
GRACE = 50  # steps after a plate was let go in which duo to solo throws the lever
LINE = 8  # lamps in a sluice line
NEVER = 1000  # ``rel`` when no plate has been held
DECO_STEPS = 10  # steps between the drowned lamps' turns
DECO_PHASES = 7

WATER = "minecraft:water"
GLASS = "minecraft:glass"
BRASS = "minecraft:gold_block"
COPPER = "minecraft:waxed_copper_block"
EXPOSED = "minecraft:waxed_exposed_copper"
WEATHERED = "minecraft:waxed_weathered_copper"
OXIDIZED = "minecraft:waxed_oxidized_copper"
CUT = "minecraft:waxed_cut_copper"
EXPOSED_CUT = "minecraft:waxed_exposed_cut_copper"
WEATHERED_CUT = "minecraft:waxed_weathered_cut_copper"
OXIDIZED_CUT = "minecraft:waxed_oxidized_cut_copper"
CHISELED = "minecraft:waxed_chiseled_copper"
BULB = "minecraft:waxed_copper_bulb"
DROWNED_BULB = "minecraft:waxed_weathered_copper_bulb"
LANTERN = "minecraft:sea_lantern"
BARS = "minecraft:iron_bars"
ROD = "minecraft:waxed_lightning_rod"
LADDER = "minecraft:ladder"
TIMBER = "minecraft:dark_oak_log"
PLATE = "minecraft:polished_blackstone_pressure_plate"
LEVER = "minecraft:lever"
TORCH = "minecraft:redstone_wall_torch"
DRY, WET = "waterlogged=false", "waterlogged=true"
# The st.dN tags are names, not ring indices (st.d3 is the Flooded Dome, now dome 4,
# and so on): they keep their old numbers so the re-site clears the old entities.
ENTITY_TAG = "st.d3"  # everything this module summons

# where things are, in the frame: (forward, right[, height])
DAM_F = -12  # the dam's plane; the basin is everything beyond it
DAM_RIBS = (3, 8, 13, 18)
DOOR = ((-16, -15), 3)  # the dam door: its places across, its height
STAIR_F = (-14, -13)  # the hall's stair, two wide against the dam
STAIR_FOOT, STAIR_STEPS = 14, 12  # its first step, and how many (going left)
LANDING = (0, 1, 2)
PLAQUE = (-15, -4)
LECTERN = (-15, -7)
RECALL = (-19, 3, -1)
TIDE = (-15, -10)  # the tide clock's block
PIPE = 2  # the standpipe's half width
PIPE_TOP = 15
WALK_H, CROWN_H, MID_H, LOW_H = 12, 16, 8, 4  # the decks' heights
ENGINE = (0, -2)  # the beam engine's block, on the crown
BOILERS = ((4, 13), (8, 12))  # the drowned boilers' middles, on the machine deck
CABIN_B = ((-8, -3), (9, 14))  # pump house B: forward and right, walls included
CABIN_C = ((-9, -4), (-13, -8))
HOUSE_A = ((13, 16), (-2, 2))
CULVERT = ((-8, 0), (10, 13))  # walls included; its floor is the lower deck's height
WELL = ((-2, -1), (11, 12))
HATCH_B = ((-7, -6), (11, 12))
HATCH_C = ((-8, -7), (-11, -10))
VENTS = ((-6, -4), (5, -6), (7, 6), (-5, 6))  # where bubbles rise from the floor
FOOT_LAMPS = ((-4, -3), (0, -5), (4, -3), (4, 3), (0, 5), (-4, 3))

domes.allow(
    INDEX,
    "the dam",
    "a wall of glass across the dome between the entrance and the outgoing "
    "door's window: it is what holds the flood, and the room's first sight",
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


@cache
def basin(dome: Dome) -> frozenset[Cell]:
    """the cells that hold water on purpose: all of the dome's inside
    beyond the dam, up to layer ``TOP``"""
    fr = frame(dome)
    return frozenset(
        c
        for c in domes.dome_cells(dome).interior
        if fr_of(fr, c)[0] > DAM_F and fr_of(fr, c)[2] <= TOP
    )


domes.add_wet(INDEX, basin(layout.DOMES[INDEX]))


# ---------------------------------------------------------------- the room


@dataclass(frozen=True)
class Sluice:
    """one stage: a sluice control, a gate, a pump lever behind it"""

    key: str  # a, b, c
    name: str
    post: Cell  # the control's brass post, its lowest block
    facing: str  # the side of the post the control is on
    lever: Cell  # the control in the solo form
    plate: Cell  # and in the duo form: where its holder stands
    sign: Cell
    pump_brass: Cell  # the brass block in the pump house's wall
    pump: Cell  # the pump lever
    pump_sign: Cell
    pump_facing: str
    stand: Cell  # where the pump lever is worked from (the feet)
    gate: tuple[Cell, ...]
    inner: tuple[tuple[Cell, Cell], ...]  # boxes: the gate's inner side
    line: tuple[Cell, ...]  # the sluice line's lamps, the gate's end first
    start: int  # the water's layer when the stage is uncovered
    target: int  # and when it is done


@dataclass(frozen=True)
class Room:
    """where the Flooded Dome's working parts are"""

    frame: Frame
    sluices: tuple[Sluice, Sluice, Sluice]
    gauge: tuple[tuple[Cell, ...], tuple[Cell, ...]]  # two columns, lowest first
    door: tuple[Cell, ...]  # the dam door
    lectern: Cell
    recall: tuple[int, int, int]  # the recall post: f, r, side
    engine: fittings.Machine  # the beam engine on the crown
    engine_torch: Cell  # it runs while a torch is here
    tide: fittings.Machine  # the tide clock in the hall
    lamps: tuple[Cell, ...]  # the drowned lamps
    vents: tuple[Cell, ...]


def _box(fr: Frame, fs: tuple[int, int], rs: tuple[int, int], hs: tuple[int, int]):
    return (fr.at(fs[0], rs[0], hs[0]), fr.at(fs[1], rs[1], hs[1]))


@cache
def room(dome: Dome) -> Room:
    fr = frame(dome)
    at = fr.at
    back = fr.facing(-1, 0)

    def sluice(
        key: str,
        post: tuple[int, int, int],
        way: tuple[int, int],
        brass: tuple[int, int, int],
        stand: tuple[int, int, int],
        gate: list[tuple[int, int, int]],
        inner: list[tuple[Cell, Cell]],
        line: list[tuple[int, int, int]],
    ) -> Sluice:
        i = "abc".index(key)
        f, r, h = post
        bf, br, bh = brass
        front = (f + way[0], r + way[1])
        return Sluice(
            key=key,
            name=key.upper(),
            post=at(f, r, h),
            facing=fr.facing(*way),
            lever=at(*front, h + 1),
            plate=at(*front, h),
            sign=at(*front, h + 2),
            pump_brass=at(bf, br, bh),
            # every pump lever is on the back face of its house's far wall
            pump=at(bf - 1, br, bh),
            pump_sign=at(bf - 1, br, bh + 1),
            pump_facing=back,
            stand=at(*stand),
            gate=tuple(at(*c) for c in gate),
            inner=tuple(inner),
            line=tuple(at(*c) for c in line),
            start=STARTS[i],
            target=TARGETS[i],
        )

    walk, crown, mid, low = WALK_H, CROWN_H, MID_H, LOW_H
    a = sluice(
        "a",
        (-3, 3, crown + 1),
        (1, 0),
        (16, 0, walk + 2),
        (14, 0, walk + 1),
        [(13, 0, walk + 1), (13, 0, walk + 2)],
        [_box(fr, (14, 15), (-1, 1), (walk + 1, walk + 2))],
        [(f, 1, crown) for f in range(4, -4, -1)],
    )
    b = sluice(
        "b",
        (-3, 2, mid + 1),
        (0, 1),
        (CABIN_B[0][1], 10, mid + 2),
        (-5, 10, mid + 1),
        [(-4, r, h) for h in (low + 1, low + 2) for r in HATCH_B[1]],
        [
            _box(fr, (-7, -5), HATCH_B[1], (low + 1, mid)),
            _box(fr, (-7, -4), (10, 13), (mid + 1, mid + 3)),
        ],
        [(-1, 10, mid), *((-2, r, mid) for r in range(10, 3, -1))],
    )
    c = sluice(
        "c",
        (6, -13, low + 1),
        (0, 1),
        (CABIN_C[0][1], -9, low + 2),
        (-6, -9, low + 1),
        [(-4, r, h) for h in (1, 2) for r in HATCH_C[1]],
        [_box(fr, (-8, -5), (-12, -9), (1, low + 3))],
        [(f, -11, 0) for f in range(-3, 5)],
    )
    ef, er = ENGINE
    engine = fittings.torch_clock(
        fr, ef, er, crown + 1, side=-1, lamps=True, pistons=True
    )
    tf, tr = TIDE
    tide = fittings.torch_clock(fr, tf, tr, 2, side=1, lamps=True, pistons=True)
    lamps = [at(f, r, 0) for f, r in FOOT_LAMPS]
    for f, r in BOILERS:
        lamps += [at(f + df, r + dr, mid + 2) for df, dr in domes.COMPASS]
    west, east = (tuple(at(f, 0, h) for h in range(1, TOP + 1)) for f in (-PIPE, PIPE))
    return Room(
        frame=fr,
        sluices=(a, b, c),
        gauge=(west, east),
        door=tuple(at(DAM_F, r, h) for r in DOOR[0] for h in range(1, DOOR[1] + 1)),
        lectern=at(*LECTERN, 1),
        recall=RECALL,
        engine=engine,
        engine_torch=at(ef + 1, er, crown + 1),
        tide=tide,
        lamps=tuple(lamps),
        vents=tuple(at(f, r, 1) for f, r in VENTS),
    )


def scaled(level: int) -> dict[str, int]:
    """the room's values at a level, as the function ``scale`` works them
    out: at a low level the water falls faster and the spring holds
    longer"""
    timer = game.scaled(level)["#diff.timer"]
    out = {"per": LAYER_TICKS * (200 - timer) // 100}
    for key, seconds in zip("abc", CLOCK_SECONDS, strict=True):
        out[f"t{key}"] = seconds * (20 // STEP) * timer // 100
    return out


@dataclass(frozen=True)
class State:
    """what the scores say of the room: enough to know every block of it"""

    w: int = TOP
    stage: int = 0
    form: int = 1
    ctl: int = 0
    pump: int = 0
    gate: int = 0  # the live gate drawn open
    lit: int = 0  # lamps of the live sluice line


START = State()
SOLVED = State(w=0, stage=3)


def lever(facing: str, on: bool = False) -> str:
    return fittings.lever(facing, bool(on))


def sluice_sign(s: Sluice, how: str) -> tuple[str, ...]:
    """what a control's sign says: ``solo``, ``duo`` or ``done``"""
    text = {
        "solo": ("Throw it, then", "run for the", "pump."),
        # (the holder's job is dull three times running: nothing enforces
        # the swap)
        "duo": ("Hold here.", "Swap next", "time."),
        "done": ("Open.",),
    }[how]
    return (f"SLUICE {s.name}", *text)


def pump_sign(s: Sluice) -> tuple[str, ...]:
    return (f"PUMP {s.name}", "Throw it while", "the sluice", "is open.")


def fixtures(dome: Dome, state: State) -> dict[Cell, str]:
    """
    The levers, plates and signs that stand in a state of the room, as the
    function ``fixtures`` leaves them: none for a stage still under water;
    a finished stage's levers thrown; the live stage's control a lever
    (solo) or a plate (duo).
    """
    out = {}
    for i, s in enumerate(room(dome).sluices):
        if state.stage < i or state.w > s.start:
            continue
        done = state.stage > i
        if done or state.form == 1:
            out[s.lever] = lever(s.facing, done or bool(state.ctl))
            how = "done" if done else "solo"
        else:
            out[s.plate] = PLATE
            how = "duo"
        out[s.sign] = wall_sign(s.facing, *sluice_sign(s, how))
        out[s.pump] = lever(s.pump_facing, done or bool(state.pump))
        out[s.pump_sign] = wall_sign(s.pump_facing, *pump_sign(s))
    return out


def fixture_cells(dome: Dome) -> set[Cell]:
    """every cell a lever, a plate or one of their signs may stand in"""
    return {
        c
        for s in room(dome).sluices
        for c in (s.lever, s.plate, s.sign, s.pump, s.pump_sign)
    }


LOG_TITLE, LOG_AUTHOR = "Flooded Dome log", "O. Finch"
LOG_PAGES = [
    "Flooded Dome log\nO. Finch, Chief Engineer\n\nThe Engine opened the sea "
    "cocks here itself. I stood on the dam and watched the water come up the "
    "stairs one step at a time. It was in no hurry.",
    "Three pumps will clear it: A, B and C, top to bottom. Each sits behind a "
    "sluice gate.\n\nOpen the sluice, then throw the pump. A pump moves water "
    "only while its sluice is open.",
    "It has learned.\n\nIt moved every sluice handle away from its gate and "
    "put it on a spring. It knows I am one engineer. If two of you come, it "
    "will change the handles for plates.\n\nSo: throw the handle and run.",
    "B is under the machine deck: down the well, through the pipe. C is under "
    "its own floor. Hold your breath.\n\nThe lift came down again last night. "
    "Nobody got out of it that I saw.\n\nNext is the Foundry. I hear "
    "hammering.",
]


def logbook(fr: Frame, pages=LOG_PAGES) -> str:
    return fittings.lectern_with_book(fr.facing(-1, 0), LOG_TITLE, LOG_AUTHOR, pages)


# ------------------------------------------------------------- the plan


@dataclass
class Blocks:
    """the room's blocks that no state of the puzzle moves"""

    floor: dict[Cell, str] = field(default_factory=dict)  # relaid floor
    solid: dict[Cell, str] = field(default_factory=dict)  # full blocks
    #: blocks that do not fill their cell: stairs, ladders, bars, pipes,
    #: pistons, the lectern. Those in the basin are its fittings
    parts: dict[Cell, str] = field(default_factory=dict)
    attached: dict[Cell, str] = field(default_factory=dict)  # need a support
    clear: set[Cell] = field(default_factory=set)  # air, to be kept so
    #: cells whose block's state changes by itself or by the pack (a
    #: clock's dust, a lamp): the same block always, in whatever state
    moving: set[Cell] = field(default_factory=set)
    #: cells a moving part passes through (a piston's head)
    swept: set[Cell] = field(default_factory=set)

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


def ring(n: int) -> set[tuple[int, int]]:
    """the places n out from the middle, square"""
    return {
        (f, r)
        for f in range(-n, n + 1)
        for r in range(-n, n + 1)
        if max(abs(f), abs(r)) == n
    }


def span(fs: tuple[int, int], rs: tuple[int, int]) -> set[tuple[int, int]]:
    return {(f, r) for f in range(fs[0], fs[1] + 1) for r in range(rs[0], rs[1] + 1)}


def edge(fs: tuple[int, int], rs: tuple[int, int]) -> set[tuple[int, int]]:
    """the outline of a rectangle of places"""
    return {(f, r) for f, r in span(fs, rs) if f in fs or r in rs}


def outline(places: set[tuple[int, int]], joined=()) -> set[tuple[int, int]]:
    """the places with a side on none of ``places`` or ``joined``"""
    whole = places | set(joined)
    return {
        (f, r)
        for f, r in places
        if any((f + df, r + dr) not in whole for df, dr in domes.COMPASS)
    }


def high_walk() -> set[tuple[int, int]]:
    """the high walk's deck, always dry: a strip out from the dam's crest,
    a bridge to the balcony round the standpipe, a bridge on to the east
    platform, a spur to a look-out over the airlock"""
    places = span((DAM_F + 1, DAM_F + 2), (-12, 12))
    places |= span((DAM_F + 3, -6), (-2, 2))
    places |= ring(3) | ring(4) | ring(5)
    places |= span((6, 11), (-2, 2)) | span((12, 17), (-5, 5))
    places |= span((-2, 2), (-12, -6)) | span((-3, 3), (-16, -13))
    return places - WALK_HOLES


#: where the two long ladders come up through the high walk
PIPE_LADDER, DAM_LADDER = (0, -PIPE - 1), (DAM_F + 1, 8)
WALK_HOLES = {PIPE_LADDER, DAM_LADDER}
#: gaps in the high walk's rails: where flight 1 leaves it, and three
#: diving boards
RAIL_GAPS = {(0, 5), (1, 5), (-7, 2), (0, -16), (14, 5)}


def crown() -> set[tuple[int, int]]:
    """the deck on the standpipe's top, a corner cut out for its stair"""
    return span((-4, 4), (-4, 4)) - span((1, 4), (2, 4))


def machine_deck() -> set[tuple[int, int]]:
    return {(f, r) for f, r in span((-9, 12), (8, 17)) if f * f + r * r <= 18 * 18}


def mid_ring() -> set[tuple[int, int]]:
    """the walk round the standpipe at the machine deck's height, and its
    gangway to the deck"""
    return (ring(3) - {PIPE_LADDER}) | span((-2, -2), (4, 7))


def lower_deck() -> set[tuple[int, int]]:
    return {
        (f, r)
        for f, r in span((5, 19), (-16, 4))
        if 10 * 10 <= f * f + r * r <= 19 * 19
    }


def pipe_block(f: int, r: int, h: int) -> str:
    """the standpipe: greener towards its foot, a band of cut copper at
    each deck's height"""
    age = min((h - 1) // 4, 3)
    if h % 4 == 0 or h == PIPE_TOP:
        return (OXIDIZED_CUT, WEATHERED_CUT, EXPOSED_CUT, CUT)[age]
    return (OXIDIZED, WEATHERED, EXPOSED, COPPER)[age]


def stairs(kind: str, facing: str, basin_fitting: bool = False) -> str:
    """a stair that rises towards ``facing``; one of the basin's says
    whether it is waterlogged"""
    state = f"facing={facing},half=bottom" + (f",{DRY}" if basin_fitting else "")
    return f"{kind}_stairs[{state}]"


def structure(dome: Dome) -> Blocks:
    """the room itself: the dam and the hall, the standpipe, the decks and
    their stairs and ladders, the three pump houses, the culvert, the
    brass every input stands on, the gauge and the sluice lines"""
    place = room(dome)
    fr = place.frame
    at = fr.at
    inside = domes.dome_cells(dome).interior
    ahead, back = fr.facing(1, 0), fr.facing(-1, 0)
    left, right = fr.facing(0, -1), fr.facing(0, 1)
    b = Blocks()

    # -- the dam: glass from shell to shell, ribbed, with a crest; the
    # door's cells are the puzzle's (``place.door``)
    for r in range(-dome.radius, dome.radius + 1):
        for h in range(1, WALK_H + 1):
            cell = at(DAM_F, r, h)
            if cell in inside and cell not in place.door:
                rib = WEATHERED_CUT if abs(r) in DAM_RIBS else GLASS
                b.solid[cell] = CUT if h == WALK_H else rib
    # a rail along the crest, open where the stair's landing meets it
    for r in range(-12, 13):
        if r not in LANDING:
            b.parts[at(DAM_F, r, WALK_H + 1)] = BARS

    # -- the entry hall: the stair up the dam, the plaque, the log, the recall
    for i in range(STAIR_STEPS):
        for f in STAIR_F:
            b.parts[at(f, STAIR_FOOT - i, 1 + i)] = stairs(CUT, left)
    for f in STAIR_F:
        for r in LANDING:
            b.solid[at(f, r, WALK_H)] = CUT
    solid, attached = fittings.plaque_blocks(
        fr,
        *PLAQUE,
        signs=(
            ("FLOODED DOME", "Pumps A, B, C", "Work only what", "stands on brass"),
            ("Open the sluice,", "then throw", "the pump."),
            ("A pump runs", "only while its", "sluice is open."),
        ),
    )
    b.solid |= solid
    b.attached |= attached
    b.parts[place.lectern] = logbook(fr)
    solid, attached = fittings.recall_post_blocks(fr, *place.recall)
    b.solid |= solid
    b.attached |= attached

    # -- the standpipe, the gauge up two of its faces
    for f in range(-PIPE, PIPE + 1):
        for r in range(-PIPE, PIPE + 1):
            for h in range(1, PIPE_TOP + 1):
                b.solid[at(f, r, h)] = pipe_block(f, r, h)
    for column in place.gauge:
        for cell in column:
            b.solid[cell] = f"{BULB}[lit=false]"
            b.moving.add(cell)

    # -- the decks, a lantern set in each every fifth block
    def deck(places: set[tuple[int, int]], h: int, block: str) -> None:
        for f, r in places:
            lamp = f % 5 == 0 and r % 5 == 0
            b.solid[at(f, r, h)] = LANTERN if lamp else block

    walk = high_walk()
    deck(walk, WALK_H, CUT)
    deck(crown(), CROWN_H, CUT)
    deck(machine_deck() | mid_ring(), MID_H, EXPOSED_CUT)
    deck(lower_deck(), LOW_H, WEATHERED_CUT)
    # (glass in the walk round the standpipe where it passes the gauge)
    for f in (-PIPE - 1, PIPE + 1):
        b.solid[at(f, 0, MID_H)] = GLASS
    # rails: round the bridges, the balcony, the platform and the look-out
    # (not the strip by the dam: the water side is open), and the crown
    pipe = span((-PIPE, PIPE), (-PIPE, PIPE))
    strip = span((DAM_F + 1, DAM_F + 2), (-12, 12))
    for f, r in outline(walk - strip, strip | pipe | WALK_HOLES) - RAIL_GAPS:
        b.parts[at(f, r, WALK_H + 1)] = BARS
    for f, r in outline(crown()) - {(0, 3)}:  # (the head of the crown's stair)
        b.parts[at(f, r, CROWN_H + 1)] = BARS

    # -- the ways between the decks. Two ladders that are always there
    for (f, r), way in ((PIPE_LADDER, left), (DAM_LADDER, ahead)):
        for h in range(1, WALK_H + 1):
            b.parts[at(f, r, h)] = f"{LADDER}[facing={way},{DRY}]"
    # the crown's stair, up the standpipe's right face from the balcony
    for i, f in enumerate((3, 2, 1)):
        b.parts[at(f, PIPE + 1, WALK_H + 1 + i)] = stairs(CUT, back)
    # flight 1, the high walk down to the machine deck; flight 2, on down
    # to the lower deck; flight 3, down to the floor
    for i in range(3):
        for f in (0, 1):
            b.parts[at(f, 6 + i, WALK_H - 1 - i)] = stairs(CUT, left, True)
        for f in (11, 12):
            b.parts[at(f, 7 - i, MID_H - 1 - i)] = stairs(EXPOSED_CUT, right, True)
        for r in (-16, -15):
            b.parts[at(4 - i, r, LOW_H - 1 - i)] = stairs(WEATHERED_CUT, ahead, True)

    # -- pump house A, on the east platform: its doorway is gate A
    (f0, f1), (r0, r1) = HOUSE_A
    for f, r in edge(*HOUSE_A):
        window = r in (r0, r1) and f0 < f < f1
        for h in (WALK_H + 1, WALK_H + 2, WALK_H + 3):
            b.solid[at(f, r, h)] = GLASS if window else COPPER
    for f, r in span(*HOUSE_A):
        b.solid[at(f, r, WALK_H + 4)] = CUT

    # -- the culvert under the machine deck: a floor, walls (glass on the
    # side the sluice control looks down from), a roof; open at the intake
    # well and under pump house B's hatch
    holes = span(*WELL) | span(*HATCH_B)
    for f, r in span(*CULVERT):
        b.solid[at(f, r, LOW_H)] = WEATHERED_CUT
        if (f, r) in holes:
            del b.solid[at(f, r, MID_H)]
        else:
            b.solid[at(f, r, MID_H - 1)] = EXPOSED
    for f, r in edge(*CULVERT):
        for h in (LOW_H + 1, LOW_H + 2):
            b.solid[at(f, r, h)] = GLASS if r == CULVERT[1][0] else EXPOSED
    # a ladder up the well, and one up to the hatch
    for (f, r), way in (((-1, 11), back), ((-7, 11), ahead)):
        for h in range(LOW_H + 1, MID_H + 1):
            b.parts[at(f, r, h)] = f"{LADDER}[facing={way},{DRY}]"

    # -- pump house B, a closed cabin on the machine deck: no door, the
    # only way in is up through its floor
    (f0, f1), (r0, r1) = CABIN_B
    for f, r in edge(*CABIN_B):
        window = (r == r0 or f == f0) and (f, r) not in ((f0, r0), (f1, r0), (f0, r1))
        for h in range(MID_H + 1, MID_H + 4):
            b.solid[at(f, r, h)] = GLASS if window else EXPOSED
    for f, r in span(*CABIN_B):
        b.solid[at(f, r, MID_H + 4)] = EXPOSED_CUT

    # -- pump house C: a cabin on a walled plinth, entered from below
    # through gate C in the plinth's wall and a hatch in the cabin's floor
    (f0, f1), (r0, r1) = CABIN_C
    for f, r in edge(*CABIN_C):
        window = (r == r1 or f == f1) and (f, r) not in ((f1, r0), (f0, r1), (f1, r1))
        for h in range(1, LOW_H):
            b.solid[at(f, r, h)] = WEATHERED
        for h in range(LOW_H + 1, LOW_H + 4):
            b.solid[at(f, r, h)] = GLASS if window else WEATHERED
    for f, r in span(*CABIN_C):
        if (f, r) not in span(*HATCH_C):
            b.solid[at(f, r, LOW_H)] = WEATHERED_CUT
        b.solid[at(f, r, LOW_H + 4)] = WEATHERED_CUT
    for h in range(1, LOW_H + 1):
        b.parts[at(HATCH_C[0][0], HATCH_C[1][0], h)] = f"{LADDER}[facing={ahead},{DRY}]"

    # -- the brass: each control's post, the block under its plate, the
    # block its pump lever is on (and plain copper over that, for the sign)
    for s in place.sluices:
        post = fittings.input_post(
            s.post, s.facing, lever(s.facing), sluice_sign(s, "solo")
        )
        b.solid |= post.solid
        x, y, z = s.plate
        if (x, y - 1, z) not in b.solid:
            raise ValueError(f"sluice {s.name}'s plate stands on nothing")
        b.solid[x, y - 1, z] = BRASS
        b.solid[s.pump_brass] = BRASS
        x, y, z = s.pump_brass
        b.solid[x, y + 1, z] = b.solid[x, y - 1, z] = COPPER
        for cell in s.gate:
            b.solid.pop(cell, None)
        # the sluice line: lamps set in the deck (or the floor) towards the gate
        for cell in s.line:
            if cell in domes.dome_cells(dome).floor:
                b.floor[cell] = f"{BULB}[lit=false]"
            else:
                b.solid[cell] = f"{BULB}[lit=false]"
            b.moving.add(cell)
    b.clear |= fixture_cells(dome)
    return b


def dressing(dome: Dome) -> Blocks:
    """what makes the room busy and is no part of the puzzle (see the
    module docstring): built once, and touched by no reset but for the
    beam engine's torch and the drowned lamps"""
    place = room(dome)
    fr = place.frame
    at = fr.at
    ahead, back = fr.facing(1, 0), fr.facing(-1, 0)
    lights = domes.light_cells(dome)[0]
    d = Blocks()

    def machine(m: fittings.Machine, bed: dict[Cell, str]) -> None:
        bed |= m.bed
        for cell, block in m.solid.items():
            (d.parts if "piston" in block else d.solid)[cell] = block
        d.attached |= m.attached
        d.moving |= m.moving & (set(m.bed) | set(m.solid) | set(m.attached))
        d.swept |= m.moving - set(m.bed) - set(m.solid) - set(m.attached)

    # -- the tide clock, caged in the hall against the dam: it runs for ever
    machine(place.tide, d.solid)
    f, r = TIDE
    cage = edge((f - 3, DAM_F), (r - 2, r + 2)) - span((DAM_F, DAM_F), (r - 2, r + 2))
    for cf, cr in cage:
        for h in (1, 2, 3):
            d.parts[at(cf, cr, h)] = BARS
    # two posts under the hall's stair
    for i in (4, 8):
        for h in range(1, 1 + i):
            d.parts[at(STAIR_F[0], STAIR_FOOT - i, h)] = f"{ROD}[facing=up]"

    # -- the beam engine on the crown, behind bars, under a timber frame:
    # its bed is the crown's own deck. It is built still: the pack puts its
    # torch in while water is falling
    bed: dict[Cell, str] = {}
    machine(place.engine, bed)
    d.solid |= bed
    del d.attached[place.engine_torch]
    d.clear.add(place.engine_torch)
    d.moving.discard(place.engine_torch)
    f, r = ENGINE
    for bf in range(-3, 4):
        for h in (1, 2):
            d.parts[at(bf, 0, CROWN_H + h)] = BARS
    for bf in (f - 2, f + 3):
        for h in (1, 2, 3):
            d.solid[at(bf, r - 1, CROWN_H + h)] = TIMBER
    for bf in range(f - 2, f + 4):
        d.solid[at(bf, r - 1, CROWN_H + 4)] = "minecraft:dark_oak_planks"

    # -- the drowned boilers on the machine deck, a lamp in each face, a
    # stub of flue on top; and the lamps in the floor round the standpipe
    for bf, br in BOILERS:
        for df in (-1, 0, 1):
            for dr in (-1, 0, 1):
                for h in (1, 2, 3):
                    corner = df and dr
                    d.solid[at(bf + df, br + dr, MID_H + h)] = (
                        EXPOSED_CUT if corner or h != 2 else EXPOSED
                    )
        for h in (4, 5, 6):
            d.parts[at(bf, br, MID_H + h)] = f"{ROD}[facing=up]"
    for cell in place.lamps:
        (d.floor if cell[1] == dome.floor_y else d.solid)[cell] = (
            f"{DROWNED_BULB}[lit=false]"
        )
        d.moving.add(cell)
    # a foot plate of old copper in the floor round the standpipe
    for f, r in ring(PIPE + 1):
        cell = at(f, r, 0)
        if cell not in lights and cell not in d.floor:
            d.floor[cell] = OXIDIZED_CUT

    # -- pipework: the mains slung under the two bridges, from the dam to
    # the standpipe and on to pump house A. In the top layer of the flood,
    # so they are fittings of the basin
    for f in (*range(DAM_F + 1, -PIPE), *range(PIPE + 1, HOUSE_A[0][0])):
        way = ahead if f > 0 else back
        d.parts[at(f, -2, WALK_H - 1)] = f"{ROD}[facing={way},{DRY}]"
    return d


@cache
def _room_blocks(dome: Dome) -> Blocks:
    b = structure(dome)
    extra = dressing(dome)
    # the beam engine's bed is laid in the crown's deck, the tide clock's
    # stands on the floor: the dressing's blocks take the deck's places
    for cell in set(extra.solid) & set(b.solid):
        if cell in room(dome).engine.bed:
            del b.solid[cell]
    b.add(extra)
    return b


def room_blocks(dome: Dome) -> Blocks:
    """the Flooded Dome's blocks that no state of the puzzle moves: the
    room's and its dressing's (lamps as they are when dark, the basin's
    fittings as they are when dry)"""
    return _room_blocks(dome)


@cache
def engine_blocks(dome: Dome) -> dict[Cell, str]:
    """the outgoing tunnel's pump engine, which stands in the basin: the
    core builds it, and the water is written round it. Its cells that can
    hold water (two that are air, the lightning rod) are written by
    ``draw`` like the room's own"""
    cells = tunnels.engine_cells(layout.TUNNELS[dome.index])
    return {cell: tunnels.ENGINE[key] for key, cell in cells.items()}


#: blocks water can stand in that the basin must not hold as plain blocks
WATERLOGGABLE = ("slab", "grate", "trapdoor", "fence", "_wall", "pane", "chain")
WATERLOGGABLE += ("stairs", "ladder", "bars", "lightning_rod", "sign", "_door")


def holds_water(block: str) -> bool:
    """is this block of the basin one of its fittings: a block that water
    can stand in?"""
    return any(w in block for w in ("stairs", "ladder", "bars", "lightning_rod"))


@dataclass(frozen=True)
class Layer:
    """one layer of the basin: the cells that are water or air, and the
    fittings (cell -> block when dry)"""

    h: int
    open: frozenset[Cell]
    fittings: dict[Cell, str]
    gates: frozenset[Cell]


@cache
def layers(dome: Dome) -> dict[int, Layer]:
    """the basin by height, 1 to ``TOP``"""
    b = room_blocks(dome)
    place = room(dome)
    fr = place.frame
    engine = engine_blocks(dome)
    gates = {c for s in place.sluices for c in s.gate}
    taken = set(b.solid) | {c for c, block in engine.items() if block != AIR}
    out = {}
    for h in range(1, TOP + 1):
        level = {c for c in basin(dome) if fr_of(fr, c)[2] == h}
        fit = {c: block for c, block in b.parts.items() if c in level}
        for c, block in engine.items():
            if c in level and "lightning_rod" in block:
                fit[c] = f"{ROD}[{DRY}]"
        out[h] = Layer(
            h,
            frozenset(level - taken - set(fit) - gates),
            fit,
            frozenset(level & gates),
        )
    return out


def layer_lines(dome: Dome, h: int, is_wet: bool) -> list[str]:
    """the commands that make a layer of the basin wet, or dry: the rig's
    two forms. Wet: its cells made sources (flowing water too), then its
    fittings waterlogged. Dry: its fittings first, then its water away.
    The gates' cells are the function ``gates``'s"""
    layer = layers(dome)[h]
    boxes = domes.boxes(layer.open)
    fit = [
        f"setblock {_xyz(c)} {wet(block, is_wet)}"
        for c, block in sorted(layer.fittings.items())
    ]
    if is_wet:
        lines = []
        for a, b in boxes:
            lines += [
                dp.fill(a, b, WATER, f"replace {WATER}"),  # flowing -> source
                dp.fill(a, b, WATER, f"replace {AIR}"),
            ]
        return lines + fit
    return fit + [dp.fill(a, b, AIR, f"replace {WATER}") for a, b in boxes]


def gate_rows(s: Sluice) -> list[tuple[int, Cell, Cell]]:
    """a gate's cells as rows for ``fill`` (which joins the bars up): the
    height above the floor of each, and its two ends"""
    rows: dict[int, list[Cell]] = {}
    for cell in s.gate:
        rows.setdefault(cell[1], []).append(cell)
    floor_y = layout.DOMES[INDEX].floor_y
    return [(y - floor_y, min(cs), max(cs)) for y, cs in sorted(rows.items())]


def gate_block(is_open: bool, is_wet: bool) -> str:
    if is_open:
        return WATER if is_wet else AIR
    return f"{BARS}[{WET if is_wet else DRY}]"


def gate_open(state: State, index: int) -> bool:
    """is a stage's gate drawn open? A finished stage's always, a later
    one's never"""
    return state.stage > index or (state.stage == index and bool(state.gate))


def fixed_blocks(dome: Dome, state: State = START) -> dict[Cell, str]:
    """
    Every block of the room in a state, but the water and air of the
    basin's open cells (``fluid_blocks``): what stands still, the basin's
    fittings wet or dry, the gauge, the sluice lines, the gates, the dam
    door, the levers, plates and signs. (Not the beam engine's torch,
    which is there while water is falling.)
    """
    place = room(dome)
    b = room_blocks(dome)
    out = b.everything()
    for h, layer in layers(dome).items():
        for cell, block in layer.fittings.items():
            out[cell] = wet(block, h <= state.w)
    for column in place.gauge:
        for h, cell in enumerate(column, 1):
            out[cell] = f"{BULB}[lit={'true' if h <= state.w else 'false'}]"
    for i, s in enumerate(place.sluices):
        lit = LINE if state.stage > i else state.lit if state.stage == i else 0
        for k, cell in enumerate(s.line, 1):
            out[cell] = f"{BULB}[lit={'true' if k <= lit else 'false'}]"
        for cell in s.gate:
            is_wet = cell[1] - dome.floor_y <= state.w
            out[cell] = gate_block(gate_open(state, i), is_wet)
    for cell in place.door:
        out[cell] = AIR if state.stage >= 3 else CHISELED
    # where no lever, plate or sign stands there is air, or (in the basin)
    # whatever the water's level makes it: ``fluid_blocks``
    out |= dict.fromkeys(fixture_cells(dome) - basin(dome), AIR)
    out |= fixtures(dome, state)
    return out


def fluid_blocks(dome: Dome, state: State = START) -> dict[Cell, str]:
    """the basin's open cells in a state: water up to its level, air over
    it (a lever, a plate or a sign stands in some: ``fixed_blocks``)"""
    out = {}
    for h, layer in layers(dome).items():
        for cell in layer.open:
            out[cell] = WATER if h <= state.w else AIR
    return out


def plan(dome: Dome, form: int = 1) -> dict[Cell, str]:
    """the room dry, with every input it ever has in one form: for the
    checks of what stands where (``rooms.room_problems``,
    ``input_problems``)"""
    out = fixed_blocks(dome, State(w=0, stage=0, form=form))
    for i, s in enumerate(room(dome).sluices):
        live = fixtures(dome, State(w=0, stage=i, form=form))
        mine = (s.lever, s.plate, s.sign, s.pump, s.pump_sign)
        out |= {c: block for c, block in live.items() if c in mine}
    b = room_blocks(dome)
    skip = set(b.floor) | set(engine_blocks(dome))  # (the engine is the core's)
    return {c: block for c, block in out.items() if c not in skip and block != AIR}


def inputs(dome: Dome, form: int = 1) -> set[Cell]:
    """the levers and plates of a form, and the recall post's button"""
    place = room(dome)
    f, r, side = place.recall
    return {place.frame.at(f, r + side, 2)} | {
        cell
        for s in place.sluices
        for cell in (s.lever if form == 1 else s.plate, s.pump)
    }


# ------------------------------------------------- walking, climbing, swimming


@dataclass(frozen=True)
class Shape:
    """
    The room as a body meets it in one state: where it can be, stand,
    climb and swim. A place is the cell of the feet.
    """

    inside: frozenset[Cell]
    ground: frozenset[Cell]  # blocks with a top to stand on (not the floor)
    floor: frozenset[Cell]
    full: frozenset[Cell]  # cells a body cannot be in
    ladders: frozenset[Cell]
    water: frozenset[Cell]  # the basin's cells that are wet

    def free(self, c: Cell) -> bool:
        return c in self.inside and c not in self.full

    def floats(self, c: Cell) -> bool:
        """in water or on a ladder: held up with nothing underfoot"""
        return self.free(c) and (c in self.ladders or c in self.water)

    def stands(self, c: Cell) -> bool:
        x, y, z = c
        under = (x, y - 1, z)
        return (
            self.free(c)
            and self.free((x, y + 1, z))
            and (under in self.ground or under in self.floor)
        )

    def at_rest(self, c: Cell) -> bool:
        return self.floats(c) or self.stands(c)

    def moves(self, c: Cell, falls: bool = True) -> Iterator[Cell]:
        """
        Where a body at ``c`` can get to in one move. On foot: a step to
        the side, level or one up or down, with room for the head (as
        ``rooms.reach``), into water or onto a ladder too; with ``falls``,
        off an edge and down to whatever is below. In water or on a
        ladder: any way to more of the same, and out sideways onto a
        surface level with it or one up (the top of a ladder, a deck
        level with the water: not one a block above it).
        """
        x, y, z = c
        if self.floats(c):
            for dx, dy, dz in rooms.FACES:
                to = (x + dx, y + dy, z + dz)
                if self.floats(to):
                    yield to
            if self.stands((x, y - 1, z)):
                yield (x, y - 1, z)
            for dx, dz in domes.COMPASS:
                if self.stands((x + dx, y, z + dz)):
                    yield (x + dx, y, z + dz)
                up = (x + dx, y + 1, z + dz)
                if self.stands(up) and self.free((x, y + 1, z)):
                    yield up
        if not self.stands(c):
            return
        for dx, dz in domes.COMPASS:
            for dy in (0, 1, -1):
                to = (x + dx, y + dy, z + dz)
                head = (x, y + 2, z) if dy == 1 else (to[0], to[1] + 2, to[2])
                if self.at_rest(to) and (not dy or self.free(head)):
                    yield to
            side = (x + dx, y, z + dz)
            if (
                not falls
                or not self.free(side)
                or not self.free((x + dx, y + 1, z + dz))
            ):
                continue
            for down in range(1, y):
                to = (x + dx, y - down, z + dz)
                if not self.free(to):
                    break
                if self.at_rest(to):
                    if down > 1:
                        yield to
                    break


@cache
def _still(dome: Dome) -> tuple[frozenset[Cell], frozenset[Cell], frozenset[Cell]]:
    """what does not change with the state: blocks to stand on, cells a
    body cannot be in, ladders"""
    b = room_blocks(dome)
    engine = engine_blocks(dome)
    ground = set(b.solid) | {c for c, block in b.parts.items() if "stairs" in block}
    ground |= {c for c, block in engine.items() if block != AIR and "rod" not in block}
    ladders = {c for c, block in b.parts.items() if "ladder" in block}
    full = ground | (set(b.parts) - ladders) | set(b.attached) | b.swept
    full |= {c for c, block in engine.items() if block != AIR}
    return frozenset(ground), frozenset(full), frozenset(ladders)


def shape(dome: Dome, state: State) -> Shape:
    """the room in a state, for a body (``state.gate``: the live gate
    open)"""
    place = room(dome)
    cells = domes.dome_cells(dome)
    ground, full, ladders = _still(dome)
    shut = {
        c
        for i, s in enumerate(place.sluices)
        if not gate_open(state, i)
        for c in s.gate
    }
    door = set(place.door) if state.stage < 3 else set()
    fr = place.frame
    return Shape(
        inside=cells.interior,
        ground=ground | door,
        floor=cells.floor,
        full=full | shut | door,
        ladders=ladders,
        water=frozenset(c for c in basin(dome) if fr_of(fr, c)[2] <= state.w),
    )


def reach(sh: Shape, start: Cell, falls: bool = True) -> dict[Cell, Cell | None]:
    """every place a body can get to from ``start``, each with the place
    it was reached from (the shortest way, in moves)"""
    seen: dict[Cell, Cell | None] = {start: None}
    edge_, i = [start], 0
    while i < len(edge_):
        c = edge_[i]
        i += 1
        for to in sh.moves(c, falls):
            if to not in seen:
                seen[to] = c
                edge_.append(to)
    return seen


def way(seen: dict[Cell, Cell | None], to: Cell) -> list[Cell]:
    """the way ``reach`` found to a place, from the start"""
    out: list[Cell] = []
    at: Cell | None = to
    while at is not None:
        out.append(at)
        at = seen[at]
    return out[::-1]


def stage_states(stage: int) -> list[State]:
    """the water's levels while a stage is the live one (after the last:
    the dry room)"""
    if stage >= 3:
        return [SOLVED]
    return [State(w=w, stage=stage) for w in range(STARTS[stage], TARGETS[stage], -1)]


def inner_cells(dome: Dome, s: Sluice) -> set[Cell]:
    """a gate's inner side, and its own cells"""
    out = set(s.gate)
    for a, b in s.inner:
        out |= {
            (x, y, z)
            for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1)
            for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1)
            for z in range(min(a[2], b[2]), max(a[2], b[2]) + 1)
        }
    return out


def dive(sh: Shape, path: list[Cell]) -> int:
    """the longest run of a way that is under water with no air over it"""
    longest = run = 0
    for x, y, z in path:
        under = (x, y, z) in sh.water and (
            (x, y + 1, z) in sh.water or not sh.free((x, y + 1, z))
        )
        run = run + 1 if under else 0
        longest = max(longest, run)
    return longest


MAX_DIVE = 14  # cells under water in a row that a route may ask for


def route_problems(dome: Dome) -> list[str]:
    """
    The routes the puzzle asks for, by foot, ladder and water, at every
    level of each stage: from the entrance to the stage's control (never
    by a fall onto anything but water); and, with its gate open and the
    water at the stage's first level, from the control to the pump lever
    and back, never long under water.
    """
    place = room(dome)
    problems = []
    entrance = domes.entrance(dome)[:3]
    for i, s in enumerate(place.sluices):
        for state in stage_states(i):
            seen = _wet_reach(dome, state, entrance)
            if s.plate not in seen:
                problems.append(
                    f"no way from the entrance to sluice {s.name}'s control "
                    f"with the water at {state.w}"
                )
        sh = shape(dome, State(w=s.start, stage=i, gate=1))
        for a, b, what in (
            (s.plate, s.stand, f"sluice {s.name}'s control to pump {s.name}"),
            (s.stand, s.plate, f"pump {s.name} back to its sluice's control"),
        ):
            seen = _wet_only(sh, a)
            if b not in seen:
                problems.append(f"no way from {what}, its gate open")
            elif (deep := dive(sh, way(seen, b))) > MAX_DIVE:
                problems.append(f"{what}: {deep} cells under water in a row")
        shut = _wet_only(shape(dome, State(w=s.start, stage=i)), s.plate)
        if s.stand in shut:
            problems.append(f"pump {s.name} can be reached with its gate shut")
    # the dry room: from the door through the dam's door to the way out
    seen = _wet_reach(dome, SOLVED, entrance)
    for name, cell in dry_walks(dome).items():
        if cell not in seen:
            problems.append(f"the room dry: no way from the entrance to {name}")
    return problems


def _wet_only(sh: Shape, start: Cell) -> dict[Cell, Cell | None]:
    """``reach`` with no fall but into water"""
    seen: dict[Cell, Cell | None] = {start: None}
    edge_, i = [start], 0
    while i < len(edge_):
        c = edge_[i]
        i += 1
        for to in sh.moves(c, True):
            drop = c[1] - to[1] > 1
            if to not in seen and not (drop and to not in sh.water):
                seen[to] = c
                edge_.append(to)
    return seen


def _wet_reach(dome: Dome, state: State, start: Cell) -> dict[Cell, Cell | None]:
    return _wet_only(shape(dome, state), start)


def lock_problems(dome: Dome) -> list[str]:
    """
    Nobody can be stranded. For each stage and each level of its water:
    from every place a player can get to (the live gate open, any fall
    taken), there is a way back to the entrance with the live gate shut
    and nobody holding it; and, for a place on the gate's inner side,
    with the gate open, as it is whenever anyone is there. So at every
    level something that can be climbed pierces the surface.
    """
    place = room(dome)
    entrance = domes.entrance(dome)[:3]
    problems = []
    for stage in range(4):
        live = place.sluices[stage] if stage < 3 else None
        inner = inner_cells(dome, live) if live else set()
        for state in stage_states(stage):
            opened = shape(dome, State(w=state.w, stage=stage, gate=1))
            shut = shape(dome, state)
            places = reach(opened, entrance)
            back: dict[Cell, list[Cell]] = {}
            for c in places:
                for to in (opened if c in inner else shut).moves(c):
                    back.setdefault(to, []).append(c)
            home, edge_ = {entrance}, [entrance]
            while edge_:
                for c in back.get(edge_.pop(), ()):
                    if c not in home:
                        home.add(c)
                        edge_.append(c)
            if lost := set(places) - home:
                where = fr_of(place.frame, min(lost))
                problems.append(
                    f"stage {stage}, the water at {state.w}: no way back to the "
                    f"entrance from {len(lost)} places, e.g. (f, r, h) {where}"
                )
    return problems


def walks(dome: Dome) -> dict[str, Cell]:
    """where a player must be able to walk to from the entrance when the
    room is as built, flooded: the cell the feet are in"""
    place = room(dome)
    at = place.frame.at
    a = place.sluices[0]
    lf, lr = LECTERN
    return {
        "the plaque": at(PLAQUE[0] - 2, PLAQUE[1], 1),
        "the logbook": at(lf - 1, lr, 1),
        "the recall post": at(RECALL[0], RECALL[1] + 2 * RECALL[2], 1),
        "the dam door": at(DAM_F - 1, DOOR[0][0], 1),
        "the tide clock": at(TIDE[0] - 4, TIDE[1], 1),
        "the foot of the stair": at(STAIR_F[0], STAIR_FOOT + 1, 1),
        "the dam's crest": at(DAM_F, LANDING[1], WALK_H + 1),
        "the balcony": at(-4, 0, WALK_H + 1),
        "the look-out": at(0, -14, WALK_H + 1),
        "sluice A's control": a.plate,
        "the beam engine": at(-2, 1, CROWN_H + 1),
        "pump house A's door": at(HOUSE_A[0][0] - 1, 0, WALK_H + 1),
        "the head of flight 1": at(0, 5, WALK_H + 1),
    }


def dry_walks(dome: Dome) -> dict[str, Cell]:
    """and when it is dry and solved, as well: every deck, both the lower
    controls, the floor, and the way out by the dam door"""
    place = room(dome)
    at = place.frame.at
    out = layout.TUNNELS[dome.index]
    ux, uz = domes.outward(dome, out)
    ox, oy, oz = dome.floor_centre
    mouth = dome.radius - 3
    _, b, c = place.sluices
    return {
        "the way out": (ox + ux * mouth, oy + 1, oz + uz * mouth),
        "the basin's side of the dam door": at(DAM_F + 1, DOOR[0][0], 1),
        "pump A": place.sluices[0].stand,
        "the machine deck": at(2, 10, MID_H + 1),
        "sluice B's control": b.plate,
        "the intake well": at(0, 10, MID_H + 1),
        "the lower deck": at(12, 0, LOW_H + 1),
        "sluice C's control": c.plate,
        "the standpipe's foot": at(-PIPE - 2, 0, 1),
        "gate C": at(CABIN_C[0][1] + 1, HATCH_C[1][0], 1),
        "the pump engine": at(5, -20, 1),
    }


def walk_problems(dome: Dome) -> list[str]:
    """
    The walks of ``walks`` (the room flooded, gate A shut) and of
    ``dry_walks`` (dry, every gate and the dam door open) by
    ``rooms.walk_problems``: on foot only, feet and head in free cells, a
    step level or one up or down. The ways that need a ladder or a swim
    are ``route_problems``'s.
    """
    problems = []
    for state, targets in (
        (START, walks(dome)),
        (SOLVED, walks(dome) | dry_walks(dome)),
    ):
        sh = shape(dome, state)
        blocked = sh.full - sh.ground
        found = rooms.walk_problems(dome, sh.ground, targets, blocked)
        problems += [f"the water at {state.w}: {p}" for p in found]
    return problems


def sight_problems(dome: Dome) -> list[str]:
    """
    What the puzzle depends on seeing: every lamp of the gauge from the
    entrance, through the dam; from each sluice control (where its holder
    stands) its own gate, so that one player watches the other go through.
    Glass, bars, pipes and ladders are seen through.
    """
    place = room(dome)
    blocks = {
        c: b for c, b in plan(dome, 2).items() if "ladder" not in b and "lever" not in b
    }
    blocks |= {c: b for c, b in engine_blocks(dome).items() if b != AIR}
    gauge = {f"lamp {h} of the gauge": cell for h, cell in enumerate(place.gauge[0], 1)}
    eye = {"the entrance": domes.entrance(dome)[:3]}
    problems = rooms.sight_problems(blocks, eye, gauge)
    solid = rooms.opaque(blocks)
    for s in place.sluices:
        if all(rooms.hidden(s.plate, cell, solid) for cell in s.gate):
            problems.append(f"gate {s.name} is hidden from its sluice control")
    return problems


def basin_problems(dome: Dome) -> list[str]:
    """
    The basin holds: every cell of it that is water, a fitting or a gate
    has, on each side and below, another such cell or a full block (the
    room's, the shell, the floor, the tunnel's door or engine), so water
    has nowhere to run; every fitting says whether it is waterlogged; and
    no lever, plate or sign stands in a layer that is wet while it is
    there.
    """
    cells = domes.dome_cells(dome)
    b = room_blocks(dome)
    place = room(dome)
    fr = place.frame
    engine = engine_blocks(dome)
    full = set(b.solid) | cells.shell | cells.floor | set(place.door)
    full |= {c for c, block in engine.items() if block != AIR and "rod" not in block}
    problems = []
    for h, layer in layers(dome).items():
        mine = layer.open | set(layer.fittings) | layer.gates
        below = set()
        if h > 1:
            lower = layers(dome)[h - 1]
            below = lower.open | set(lower.fittings) | lower.gates
        for x, y, z in mine:
            for dx, dz in domes.COMPASS:
                if (side := (x + dx, y, z + dz)) not in mine and side not in full:
                    problems.append(f"the basin leaks sideways at {side}")
            if (under := (x, y - 1, z)) not in below and under not in full:
                problems.append(f"the basin leaks down at {under}")
        for cell, block in layer.fittings.items():
            if not holds_water(block) or DRY not in block:
                problems.append(f"{block} at {cell} is no fitting for the basin")
        for cell, block in b.attached.items():
            if cell in mine:
                problems.append(f"{_name(block)} at {cell} would be washed off")
    for cell, block in b.solid.items():
        if cell in basin(dome) and any(w in _name(block) for w in WATERLOGGABLE):
            problems.append(f"{_name(block)} at {cell}: water stands in it, unwritten")
    for s in place.sluices:
        for cell in (s.lever, s.plate, s.sign, s.pump, s.pump_sign):
            if fr_of(fr, cell)[2] <= s.start:
                problems.append(f"sluice {s.name}: {cell} is wet when it is uncovered")
        if any(cell not in basin(dome) for cell in s.gate) != (s.start >= TOP):
            problems.append(f"gate {s.name} is half in the basin")
    return problems[:12]


@cache
def _room_problems(dome: Dome) -> tuple[str, ...]:
    cells = domes.dome_cells(dome)
    try:
        b = room_blocks(dome)
    except ValueError as e:
        return (str(e),)
    place = room(dome)
    used = set(b.above()) | b.clear | b.swept | set(place.door)
    used |= {c for s in place.sluices for c in s.gate}
    problems = fittings.placement_problems(dome, used | set(place.vents))
    more = (b.clear | b.swept | set(place.vents)) - set(b.above())
    for form in (1, 2):
        blocks = plan(dome, form)
        problems += rooms.room_problems(dome, blocks, b.floor, more)
        problems += rooms.input_problems(blocks, inputs(dome, form), floor=b.floor)
    if set(b.floor) & (domes.light_cells(dome)[0] - set(place.lamps)):
        problems.append("the relaid floor covers one of the dome's lanterns")
    if set(b.solid) & set(b.parts) or (set(b.solid) | set(b.parts)) & set(b.attached):
        problems.append("a cell is given two blocks")
    if not cells.interior >= basin(dome):
        problems.append("the basin is not inside the dome")
    problems += rooms.window_problems(dome, plan(dome))
    problems += basin_problems(dome)
    problems += walk_problems(dome) + sight_problems(dome)
    problems += route_problems(dome) + lock_problems(dome)
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


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


def labels(dome: Dome) -> list[str]:
    """the commands that summon the glowing labels: one over each control
    and each pump lever (text displays: water does them no harm)"""
    out = []
    for s in room(dome).sluices:
        post = fittings.input_post(
            s.post,
            s.facing,
            lever(s.facing),
            sluice_sign(s, "solo"),
            f"SLUICE {s.name}",
            (ENTITY_TAG,),
        )
        out += post.summons
        x, y, z = s.pump
        out.append(
            fittings.display(
                (ENTITY_TAG,),
                (x + 0.5, y + 1.6, z + 0.5),
                0,
                fittings.label_text(f"PUMP {s.name}"),
                0.8,
                "center",
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
    """the Flooded Dome inside its shell: drains and wipes what was
    inside but the pump engine, builds the room dry, then floods it, and
    leaves it as ``reset`` does. Run it after the tunnels' stages (which
    rebuild the pump engine dry: after them, ``function
    station:dome/<n>/draw``)"""
    dome = ctx.layout.DOMES[INDEX]
    if problems := room_problems(dome):
        raise RuntimeError("the Flooded Dome: " + "; ".join(problems))
    place = room(dome)
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    engine = set(engine_blocks(dome))
    ctx.cmd(f"kill @e[tag={ENTITY_TAG}]")
    for command in game.clear_stub_commands(dome):
        ctx.cmd(command)
    # an old flood goes as the pumps take it, from the top, so nothing
    # runs: in each layer the bars of the gates and the fittings dry first
    for h in range(TOP, 0, -1):
        for s in place.sluices:
            for at, a, z in gate_rows(s):
                if at == h:
                    ctx.fill(a, z, gate_block(False, False))
        for line in layer_lines(dome, h, False):
            ctx.cmd(line)
    ctx.fill_boxes(cells.interior - engine, AIR)
    torches = {c: block for c, block in b.attached.items() if TORCH in block}
    for part in (b.floor, b.solid, b.parts, b.attached):
        for block, where in sorted(domes.by_block(part).items()):
            if "{" not in block and TORCH not in block:
                ctx.fill_boxes(where, block)
        for cell, block in sorted(part.items()):
            if "{" in block and cell != place.lectern:
                ctx.setblock(cell, block)  # (signs; the book is below)
    for cell, block in sorted(torches.items()):
        ctx.setblock(cell, block)  # a clock's torch last: it starts by itself
    for command in book_commands(dome):
        ctx.cmd(command)
    for command in labels(dome):
        ctx.cmd(command)
    ctx.cmd(fittings.summon_recall(place.frame, *place.recall, tags=(ENTITY_TAG,)))
    # the flood, from the floor up, as ``draw`` writes it; then the gates,
    # the dam door, the gauge and stage A's control and pump lever
    for h in range(1, TOP + 1):
        for line in layer_lines(dome, h, True):
            ctx.cmd(line)
    for s in place.sluices:
        for h, a, z in gate_rows(s):
            ctx.fill(a, z, gate_block(False, h <= TOP))
    ctx.fill_boxes(set(place.door), CHISELED)
    start = fixed_blocks(dome, START)
    for cell in (c for column in place.gauge for c in column):
        ctx.setblock(cell, start[cell])
    for cell, block in sorted(fixtures(dome, START).items()):
        ctx.setblock(cell, block)
    # the pack's own idea of the room, if the pack is installed
    ctx.function(f"dome/{INDEX}/reset")
    ctx.advance(10)
    # (water that ran while an older room was being wiped, if the game ticked)
    ctx.fill_boxes(cells.interior - basin(dome), AIR, f"replace {WATER}")
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    water = sum(len(layer.open) for layer in layers(dome).values())
    return (
        f"{dome.name}: {len(b.everything())} blocks and {water} of water: the dam "
        "and the hall (stair, plaque, logbook, recall post, tide clock), the "
        "standpipe and its gauge, the high walk, the crown and its beam engine, "
        "the machine deck, the lower deck, three pump houses, the culvert, "
        "three sluice controls"
    )


# ----------------------------------------------------------- the functions


def _s(name: str) -> str:
    return f"#fl.{name} {OBJ}"


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


#: what ``station:check/dome/<n>/layer_<h>`` counts (``#f3_<name>`` in the
#: checks' objective): open cells that are water, sources, air, air with
#: water over it; fittings and gate cells that are wet
COUNTS = ("water", "source", "air", "under", "fit")


def _count(name: str) -> str:
    return f"run scoreboard players add #f3_{name} {domes.CHECK_OBJECTIVE} 1"


domes.ROW_FAMILIES["basin"] = (
    f"execute if block ~%k ~ ~ {WATER} {_count('water')}",
    f"execute if block ~%k ~ ~ {WATER}[level=0] {_count('source')}",
    f"execute if block ~%k ~ ~ {AIR} {_count('air')}",
    f"execute if block ~%k ~ ~ {AIR} if block ~%k ~1 ~ {WATER} {_count('under')}",
)
domes.ROW_FAMILIES["basinfit"] = (
    f"execute positioned ~%k ~ ~ if predicate {domes.WET} {_count('fit')}",
)


def expected(dome: Dome, state: State = START) -> dict[str, int]:
    """what the basin's count reads in a state: every open cell up to the
    water's level a source, every one above it air but those a lever, a
    plate or a sign stands in, no air under water; every fitting and gate
    cell up to the level wet, none above"""
    by_h = layers(dome)
    wet_cells = sum(len(by_h[h].open) for h in by_h if h <= state.w)
    dry_cells = sum(len(by_h[h].open) for h in by_h if h > state.w)
    standing = set(fixtures(dome, state)) & {c for h in by_h for c in by_h[h].open}
    fit = sum(len(by_h[h].fittings) + len(by_h[h].gates) for h in by_h if h <= state.w)
    return {
        "water": wet_cells,
        "source": wet_cells,
        "air": dry_cells - len(standing),
        "under": 0,
        "fit": fit,
    }


def functions(pack: dp.Pack) -> None:
    """the Flooded Dome's functions (see the module docstring)"""
    dome = layout.DOMES[INDEX]
    place = room(dome)
    fr = place.frame
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    open_dome = f"#d{INDEX} {OBJ}"
    pack.objectives({OBJ: "dummy", domes.CHECK_OBJECTIVE: "dummy"})
    pack.constants(OBJ, 100, LINE)
    sluices = place.sluices

    def fid(name: str) -> str:
        return pack.id(f"{base}/{name}")

    def call(name: str) -> str:
        return f"function {fid(name)}"

    def sound(name: str, cell: Cell, volume: float = 1, pitch: float = 1) -> str:
        return f"playsound minecraft:{name} block {here} {_xyz(cell)} {volume} {pitch}"

    def say(text: str, colour: str = "yellow") -> str:
        return f'tellraw {here} {{text:{snbt(text)},color:"{colour}"}}'

    def live(i: int) -> str:
        """the clauses that are true while stage i is the live one"""
        return _is("stage", i)

    top = place.gauge[0][-1]

    # -- the values of the level in force
    scale = [
        _set("k", 200),
        _op("k", "-=", "#diff.timer"),
        _set("per", LAYER_TICKS),
        _op("per", "*=", "#fl.k"),
        _op("per", "/=", "#100"),
    ]
    for s, seconds in zip(sluices, CLOCK_SECONDS, strict=True):
        scale += [
            _set(f"t{s.key}", seconds * (20 // STEP)),
            _op(f"t{s.key}", "*=", "#diff.timer"),
            _op(f"t{s.key}", "/=", "#100"),
        ]
    pack.function(f"{base}/scale", scale)
    # the live stage's target layer and its spring's full clock
    target = []
    for i, s in enumerate(sluices):
        when = f"execute {_is('stage', i if i < 2 else '2..')} run"
        target += [
            f"{when} {_set('tgt', s.target)}",
            f"{when} {_op('tt', '=', f'#fl.t{s.key}')}",
        ]
    pack.function(f"{base}/target", target)

    # -- the water: a layer wet, a layer dry
    for h in range(1, TOP + 1):
        pack.function(f"{base}/layer_{h}/wet", layer_lines(dome, h, True))
        pack.function(f"{base}/layer_{h}/dry", layer_lines(dome, h, False))

    # -- the gates: every one written from the scores, bars or none, wet
    # or dry with its layer (``fill`` joins the bars up)
    for s in sluices:
        for name, is_open in (("open", True), ("shut", False)):
            lines = []
            for h, a, z in gate_rows(s):
                if h > TOP:
                    lines.append(dp.fill(a, z, gate_block(is_open, False)))
                    continue
                lines += [
                    f"execute {_is('w', f'{h}..')} run "
                    + dp.fill(a, z, gate_block(is_open, True)),
                    f"execute {_not('w', f'{h}..')} run "
                    + dp.fill(a, z, gate_block(is_open, False)),
                ]
            pack.function(f"{base}/gate_{s.key}/{name}", lines)
    gates = []
    for i, s in enumerate(sluices):
        is_open, is_shut = call(f"gate_{s.key}/open"), call(f"gate_{s.key}/shut")
        gates += [
            f"execute {_is('stage', f'{i + 1}..')} run {is_open}",
            f"execute {live(i)} {_is('gate', 1)} run {is_open}",
            f"execute {live(i)} {_not('gate', 1)} run {is_shut}",
        ]
        if i:
            gates.append(f"execute {_is('stage', f'..{i - 1}')} run {is_shut}")
    pack.function(f"{base}/gates", gates)

    # -- the levers, plates and signs. ``fixtures_clear``: all of them out,
    # before ``draw`` writes any water. ``fixtures``: those of the stages
    # uncovered, taken out and put back as the scores say; a stage still
    # under water is left alone (to clear a cell there would make a hole
    # in the water)
    pack.function(
        f"{base}/fixtures_clear",
        [_setblock(cell, AIR) for cell in sorted(fixture_cells(dome))],
    )
    fix = []
    for i, s in enumerate(sluices):
        dry = f" {_is('w', f'..{s.start}')}" if i else ""
        reached = f"execute {_is('stage', f'{i}..')}{dry} run"
        done = f"execute {_is('stage', f'{i + 1}..')}{dry} run"
        now = f"execute {live(i)}{dry}"

        def sign(cell: Cell, facing: str, text: tuple[str, ...]) -> str:
            return _setblock(cell, wall_sign(facing, *text))

        fix += [
            *(
                f"{reached} {_setblock(cell, AIR)}"
                for cell in (s.lever, s.plate, s.sign, s.pump, s.pump_sign)
            ),
            f"{done} {_setblock(s.lever, lever(s.facing, True))}",
            f"{done} {sign(s.sign, s.facing, sluice_sign(s, 'done'))}",
            f"{done} {_setblock(s.pump, lever(s.pump_facing, True))}",
            f"{now} {_is('form', 1)} {_is('ctl', 0)} run "
            + _setblock(s.lever, lever(s.facing)),
            f"{now} {_is('form', 1)} {_is('ctl', 1)} run "
            + _setblock(s.lever, lever(s.facing, True)),
            f"{now} {_is('form', 1)} run "
            + sign(s.sign, s.facing, sluice_sign(s, "solo")),
            f"{now} {_is('form', 2)} run {_setblock(s.plate, PLATE)}",
            f"{now} {_is('form', 2)} run "
            + sign(s.sign, s.facing, sluice_sign(s, "duo")),
            f"{now} {_is('pump', 0)} run {_setblock(s.pump, lever(s.pump_facing))}",
            f"{now} {_is('pump', 1)} run "
            + _setblock(s.pump, lever(s.pump_facing, True)),
            f"{reached} {sign(s.pump_sign, s.pump_facing, pump_sign(s))}",
        ]
    pack.function(f"{base}/fixtures", fix)

    # -- the gauge on the standpipe, a lamp a layer; the sluice lines
    lit, dark = f"{BULB}[lit=true]", f"{BULB}[lit=false]"
    gauge = []
    for column in place.gauge:
        gauge += fittings.gauge_lines(column, _s("w"), 1, lit, dark)
    pack.function(f"{base}/gauge", gauge)
    for s in sluices:
        pack.function(
            f"{base}/line_{s.key}",
            fittings.gauge_lines(s.line, _s("ln"), 1, lit, dark),
        )
    line = [
        _set("ln", 0),
        # solo: the lamps left are the spring's time left; duo: all, while held
        f"execute {_is('form', 1)} {_is('ctl', 1)} run {call('line_left')}",
        f"execute {_is('form', 2)} {_is('ctl', 1)} run {_set('ln', LINE)}",
        *(
            f"execute {live(i)} run {call(f'line_{s.key}')}"
            for i, s in enumerate(sluices)
        ),
    ]
    pack.function(f"{base}/line", line)
    pack.function(
        f"{base}/line_left",
        [
            _op("ln", "=", "#fl.t"),
            _op("ln", "*=", f"#{LINE}"),
            _op("ln", "/=", "#fl.tt"),
            f"scoreboard players add {_s('ln')} 1",
            f"execute {_is('ln', f'{LINE + 1}..')} run {_set('ln', LINE)}",
        ],
    )
    # a finished stage's line stays lit, one not reached is dark
    lines_rest = []
    for i, s in enumerate(sluices):
        for cell in s.line:
            lines_rest.append(
                f"execute {_is('stage', f'{i + 1}..')} run {_setblock(cell, lit)}"
            )
            if i:
                lines_rest.append(
                    f"execute {_is('stage', f'..{i - 1}')} run {_setblock(cell, dark)}"
                )
    pack.function(f"{base}/lines_rest", [*lines_rest, call("line")])

    # -- the dam door: shut until the last pump has run
    door = []
    for a, z in domes.boxes(set(place.door)):
        door += [
            f"execute {_is('stage', '3..')} run {dp.fill(a, z, AIR)}",
            f"execute {_not('stage', '3..')} run {dp.fill(a, z, CHISELED)}",
        ]
    pack.function(f"{base}/door", door)

    # -- the whole room from the scores: the reset and the repair
    # its tunnel's pump lever stands in the basin, by the airlock: out
    # before any layer is made wet (it is there only once the room is dry)
    lx, ly, lz = tunnels.lever_cell(layout.TUNNELS[INDEX])
    draw = [
        call("fixtures_clear"),
        f"execute {_is('w', '1..')} run setblock {lx} {ly} {lz} {AIR}",
    ]
    for h in range(1, TOP + 1):
        draw += [
            f"execute {_is('w', f'{h}..')} run {call(f'layer_{h}/wet')}",
            f"execute {_not('w', f'{h}..')} run {call(f'layer_{h}/dry')}",
        ]
    draw += [call(n) for n in ("door", "gates", "fixtures", "gauge", "lines_rest")]
    pack.function(f"{base}/draw", draw)

    # -- the beam engine: it runs while a torch is in its clock
    torch = place.engine.attached[place.engine_torch]
    pack.function(
        f"{base}/engine_on",
        [
            f"execute unless block {_xyz(place.engine_torch)} {TORCH} "
            f"run {_setblock(place.engine_torch, torch)}"
        ],
    )
    pack.function(
        f"{base}/engine_off",
        [
            f"execute {_if_block(place.engine_torch, TORCH)} "
            f"run {_setblock(place.engine_torch, AIR)}"
        ],
    )

    # -- hints, one a stage: a line of chat after a while with no progress
    hints = [
        fittings.hint(pack, INDEX, s.key, text, HINT_SECONDS)
        for s, text in zip(
            sluices,
            (
                "The sluice handle is on top of the standpipe. Pump A is over "
                "the east bridge, behind the bars.",
                "Sluice B is on the walk round the standpipe. Pump B's cabin "
                "has no door: go down the well beside it.",
                "Sluice C is at the far end of the lower deck. Pump C is under "
                "its own floor: dive to the bars at the foot of its cabin.",
            ),
            strict=True,
        )
    ]
    pack.function(
        f"{base}/hint_arm",
        [f"execute {live(i)} run {h.arm}" for i, h in enumerate(hints)],
    )

    # -- reading the room: who is beyond the live gate, the pump lever,
    # the control
    read = [_set("in", 0), _set("g", 0)]
    for i, s in enumerate(sluices):
        for a, z in s.inner:
            who = f"@e[tag=st.in,{dp.box_selector(a, z)}]"
            read += [
                f"execute {live(i)} store result score {_s('n')} if entity {who}",
                f"execute {live(i)} run {_op('in', '+=', '#fl.n')}",
            ]
        who = f"@e[tag=st.in,{dp.box_selector(min(s.gate), max(s.gate))}]"
        read.append(f"execute {live(i)} store result score {_s('g')} if entity {who}")
        thrown = _if_block(s.pump, f"{LEVER}[powered=true]")
        read += [
            f"execute {live(i)} {_is('pump', 0)} {thrown} run {call('pump_on')}",
            # a pump once thrown stays thrown
            fittings.lever_hold_line(
                s.pump, lever(s.pump_facing, True), f"{live(i)} {_is('pump', 1)}"
            ),
        ]
    read += [
        f"execute {_is('form', 1)} run {call('read_solo')}",
        f"execute {_is('form', 2)} run {call('read_duo')}",
    ]
    pack.function(f"{base}/read", read)
    pack.function(
        f"{base}/pump_on",
        [
            _set("pump", 1),
            _op("d", "=", "#fl.per"),
            sound("block.piston.extend", top, 2, 0.6),
            *(h.progress for h in hints),
        ],
    )
    solo = []
    for i, s in enumerate(sluices):
        thrown = _if_block(s.lever, f"{LEVER}[powered=true]")
        solo.append(f"execute {live(i)} {_is('ctl', 0)} {thrown} run {call('throw')}")
    solo += [
        f"execute {_is('ctl', 1)} run scoreboard players remove {_s('t')} 1",
        f"execute {_is('ctl', 1)} {_is('t', '..0')} run {call('spring')}",
    ]
    # while its clock runs the lever is held over
    solo += [
        fittings.lever_hold_line(
            s.lever, lever(s.facing, True), f"{live(i)} {_is('ctl', 1)}"
        )
        for i, s in enumerate(sluices)
    ]
    pack.function(f"{base}/read_solo", solo)
    pack.function(
        f"{base}/throw",
        [
            _set("ctl", 1),
            _op("t", "=", "#fl.tt"),
            sound("block.iron_trapdoor.open", top, 2, 0.7),
        ],
    )
    pack.function(
        f"{base}/spring",
        [
            _set("ctl", 0),
            _set("t", 0),
            *(
                f"execute {live(i)} run {_setblock(s.lever, lever(s.facing))}"
                for i, s in enumerate(sluices)
            ),
            sound("block.iron_trapdoor.close", top, 2, 0.6),
        ],
    )
    duo = [_set("held", 0)]
    duo += [
        f"execute {live(i)} {fittings.plate_held(s.plate)} run {_set('held', 1)}"
        for i, s in enumerate(sluices)
    ]
    duo += [
        f"execute {_is('held', 1)} run {_set('rel', 0)}",
        f"execute {_is('held', 0)} {_is('rel', f'..{NEVER - 1}')} "
        f"run scoreboard players add {_s('rel')} 1",
        _op("ctl", "=", "#fl.held"),
    ]
    pack.function(f"{base}/read_duo", duo)

    # -- a change of form, at a safe point. Solo to duo: not while the
    # spring's clock runs. Duo to solo: at once, and if the plate was held
    # a moment ago the lever comes thrown, with a full clock
    pack.function(
        f"{base}/swap",
        [
            f"execute {_is('want', 2)} {_is('form', 1)} {_is('ctl', 0)} "
            f"run {call('to_duo')}",
            f"execute {_is('want', 1)} {_is('form', 2)} run {call('to_solo')}",
        ],
    )
    pack.function(
        f"{base}/to_duo",
        [
            _set("form", 2),
            _set("ctl", 0),
            _set("t", 0),
            _set("rel", NEVER),
            call("fixtures"),
            say(
                "Two engineers: the sluice handle is a plate now. One holds "
                "it, the other goes through."
            ),
        ],
    )
    pack.function(
        f"{base}/to_solo",
        [
            _set("form", 1),
            _set("ctl", 0),
            _set("t", 0),
            f"execute {_is('rel', f'..{GRACE}')} run {call('throw')}",
            _set("rel", NEVER),
            call("fixtures"),
            say("One engineer now: the sluice handle is a lever on a spring."),
        ],
    )

    # -- the live gate: open while the control is active or anyone is
    # beyond it, and never shut on a cell with a player in it
    pack.function(
        f"{base}/gate",
        [
            _set("open", 0),
            f"execute {_is('ctl', 1)} run {_set('open', 1)}",
            f"execute {_is('in', '1..')} run {_set('open', 1)}",
            f"execute {_is('gate', 1)} {_is('g', '1..')} run {_set('open', 1)}",
            f"execute unless score {_s('open')} = {_s('gate')} run {call('gate_move')}",
        ],
    )
    pack.function(
        f"{base}/gate_move",
        [
            _op("gate", "=", "#fl.open"),
            call("gates"),
            f"execute {_is('gate', 1)} run "
            + sound("block.iron_door.open", top, 2, 0.8),
            f"execute {_is('gate', 0)} run "
            + sound("block.iron_door.close", top, 2, 0.8),
        ],
    )

    # -- the pump: a layer goes every ``per`` ticks while the control is
    # active and the pump lever thrown
    pack.function(
        f"{base}/drain",
        [
            _set("run", 0),
            f"execute {_is('ctl', 1)} {_is('pump', 1)} run {_set('run', 1)}",
            f"execute unless score {_s('w')} > {_s('tgt')} run {_set('run', 0)}",
            f"execute {_is('run', 1)} run {call('engine_on')}",
            f"execute {_is('run', 0)} run {call('engine_off')}",
            f"execute {_is('run', 1)} run {call('pumping')}",
        ],
    )
    pack.function(
        f"{base}/pumping",
        [
            f"scoreboard players remove {_s('d')} {STEP}",
            f"execute {_is('d', '..0')} run {call('layer_down')}",
            f"execute unless score {_s('w')} > {_s('tgt')} run {call('stage_done')}",
        ],
    )
    pack.function(
        f"{base}/layer_down",
        [
            *(
                f"execute {_is('w', h)} run {call(f'layer_{h}/dry')}"
                for h in range(1, TOP + 1)
            ),
            f"scoreboard players remove {_s('w')} 1",
            _op("d", "=", "#fl.per"),
            call("gates"),
            call("gauge"),
            sound("block.bubble_column.whirlpool_ambient", top, 2, 0.7),
            *(h.progress for h in hints),
        ],
    )
    pack.function(
        f"{base}/stage_done",
        [
            f"scoreboard players add {_s('stage')} 1",
            *(_set(name, 0) for name in ("ctl", "t", "pump", "gate", "run")),
            _set("rel", NEVER),
            call("target"),
            call("engine_off"),
            call("draw"),
            call("hint_arm"),
            f"title {here} times 5 40 10",
            f'title {here} subtitle {{text:"The water rests. Find the next sluice.",'
            'color:"aqua"}',
            f'title {here} title {{text:"Pump clear",color:"gold"}}',
            sound("block.note_block.bell", top, 3, 0.8),
            f"execute {_is('stage', '3..')} run {call('done')}",
        ],
    )
    pack.function(
        f"{base}/done",
        [f"function {pack.id(f'dome/{INDEX}/solved')}", call("restored")],
    )
    # the room once solved: dry, every gate and the dam door open
    pack.function(
        f"{base}/restored",
        [
            _set("w", 0),
            _set("stage", 3),
            *(_set(name, 0) for name in ("ctl", "t", "pump", "gate", "in", "g")),
            call("engine_off"),
            call("draw"),
        ],
    )

    # -- the machinery that only ticks: the drowned lamps, in turn, and
    # bubbles from the floor (a wisp of mist, once it is dry)
    for k in range(DECO_PHASES):
        pack.function(
            f"{base}/deco/p{k}",
            [
                _setblock(
                    cell,
                    f"{DROWNED_BULB}[lit="
                    f"{'true' if (i + k) % DECO_PHASES < 2 else 'false'}]",
                )
                for i, cell in enumerate(place.lamps)
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
            f"execute {_is('deco.t', f'{DECO_STEPS}..')} run {call('deco/turn')}",
            # a log taken from the lectern is put back
            f"execute {_if_block(place.lectern, 'minecraft:lectern[has_book=false]')} "
            f"run {call('book')}",
        ],
    )
    pack.function(f"{base}/book", [_setblock(place.lectern, logbook(fr))])

    # -- a step, and the hooks
    pack.function(
        f"{base}/step",
        [call(name) for name in ("swap", "read", "gate", "drain", "line")],
    )
    is_open = f"if score {open_dome} matches 1"
    pack.function(
        f"{base}/tick",
        [
            *(
                f"execute {is_open} {_is('live', 1)} {live(i)} run {h.tick}"
                for i, h in enumerate(hints)
            ),
            f"scoreboard players add {_s('tick')} 1",
            f"execute {_not('tick', f'{STEP}..')} run return 0",
            _set("tick", 0),
            # the machinery, whether or not there is a puzzle
            call("deco"),
            f"execute unless score {open_dome} matches 1 run return 0",
            # a room never set up for those in it (the pack reloaded)
            f"execute {_not('live', 1)} run {call('arm')}",
            # a room found dry (``guard``) is a room solved while its tunnel
            # is pumping or open; dried by a tunnel's check that has since
            # reset the tunnel, it is flooded again (the next step arms it)
            f"execute {_is('stage', '3..')} if score {tunnels.score(INDEX)} "
            f"matches 1.. run {call('done')}",
            f"execute {_is('stage', '3..')} if score {tunnels.score(INDEX)} "
            f"matches 0 run return run {call('reset')}",
            call("step"),
        ],
    )
    first = f"if score #first {OBJ} matches 1"
    pack.function(
        f"{base}/enter",
        [
            # the core's signal: the first into an empty room
            f"execute {is_open} {first} run {call('arm')}",
            f"execute {is_open} run tellraw @s "
            '{text:"The dome is flooded. The brass plaque says how to pump it out.",'
            'color:"gray",italic:true}',
            f"execute if score {open_dome} matches 2 {first} run {call('restored')}",
        ],
    )
    # the scores as a new game has them
    zeroed = ("ctl", "t", "pump", "gate", "in", "g", "run", "held", "open", "ln")
    pack.function(
        f"{base}/zero",
        [
            _set("w", TOP),
            _set("stage", 0),
            _set("form", 1),
            _set("want", 1),
            _set("live", 0),
            _set("rel", NEVER),
            *(_set(name, 0) for name in (*zeroed, "tick", "deco", "deco.t")),
        ],
    )
    # set up for those who have come in: the level's values, the control
    # at rest, the room drawn from the scores. The water and the pumps
    # are as they were left
    pack.function(
        f"{base}/arm",
        [
            f"execute {_not('w', '0..')} run {call('zero')}",
            call("scale"),
            call("target"),
            *(_set(name, 0) for name in zeroed if name != "pump"),
            _set("rel", NEVER),
            _op("d", "=", "#fl.per"),
            _set("live", 1),
            call("engine_off"),
            call("draw"),
            call("hint_arm"),
        ],
    )
    # everyone has gone: the control back, the gate shut, the engine
    # still. The water's level and the pumps thrown are kept
    pack.function(
        f"{base}/empty",
        [
            *(_set(name, 0) for name in zeroed if name != "pump"),
            _set("rel", NEVER),
            _set("live", 0),
            call("engine_off"),
            call("fixtures"),
            call("gates"),
            call("lines_rest"),
        ],
    )
    # whoever opens its tunnel (this room's ``done``, the core's checks, which
    # call ``solved`` or the tunnel's ``open`` themselves), the flood must
    # be gone before the tunnel's doors are: looked at every tick, with
    # anyone in the dome or nobody
    pack.function(
        f"{base}/guard",
        [
            f"execute if score {tunnels.score(INDEX)} matches 1.. {_is('w', '1..')} "
            f"run {call('restored')}",
            # its pump waiting for its lever (the lever is in the basin)
            f"execute if score {tunnels.score(INDEX, '.ready')} matches 1 "
            f"{_is('w', '1..')} run {call('restored')}",
        ],
        tick=True,
    )
    pack.function(f"{base}/solo", [_set("want", 1)])
    pack.function(f"{base}/duo", [_set("want", 2)])
    pack.function(
        f"{base}/reset",
        [
            call("zero"),
            call("scale"),
            call("target"),
            _op("d", "=", "#fl.per"),
            call("engine_off"),
            call("draw"),
            call("book"),
            f"kill @e[type=minecraft:item,{domes.sphere(dome)}]",
            # once more a second on: the tunnel's reset may have left a
            # piston of the pump engine on its way in, and its cell empty
            f"schedule function {fid('draw')} 20t",
        ],
    )

    # -- the check's counts, a function a layer (each well inside the
    # game's limit of commands a function)
    ran = f"scoreboard players add #ran {domes.CHECK_OBJECTIVE} 1"
    for h, layer in layers(dome).items():
        lines = domes.row_lines(pack, layer.open, "basin")
        lines += domes.row_lines(pack, set(layer.fittings) | layer.gates, "basinfit")
        pack.function(f"check/dome/{INDEX}/layer_{h}", [*lines, ran])


# --------------------------------------------------------------- the check

S1, S2 = "st.fl1", "st.fl2"


def counts(ctx: Any) -> dict[str, int | None]:
    """the basin counted in the world (``COUNTS``); ``ran`` is how many of
    the layers' functions ran whole"""
    obj = domes.CHECK_OBJECTIVE
    for name in COUNTS:
        ctx.set_score(f"#f3_{name}", 0, obj)
    ctx.set_score("#ran", 0, obj)
    for h in range(1, TOP + 1):
        ctx.function(f"check/dome/{INDEX}/layer_{h}")
    got = {name: ctx.score(f"#f3_{name}", obj) for name in COUNTS}
    got["ran"] = ctx.score("#ran", obj)
    return got


def check(ctx: Any) -> list[str]:
    """
    Work the Flooded Dome in place over RCON, nobody online. It refuses
    while a run is in progress (``game_checks.no_run``); the level is put
    back (``save_level``) and the stand-ins killed whatever happens. A player is
    stood in for by an armour stand that the core counts
    (``game.STANDIN``), with a body and a weight so that it presses a
    plate: put at the entrance to come in, on a control's plate to hold
    it, beyond a gate to be "inside". A lever is thrown by setting the
    block as a hand would leave it. The room's blocks are read whole only
    when nothing is running (a server that has just been sprinted ticks on
    between the reads). Leaves the room and its tunnel reset (``#t<n>`` 0,
    whatever it was), this dome's and the next's scores, ``#solved`` and the level as
    it found them, and no stand-in behind.

    What stand-ins and block reads cannot prove, and so is not claimed: a
    hand on a lever, or a player's own weight on a plate; any walk, climb
    or swim (that the routes exist is ``route_problems`` and
    ``lock_problems``, on the plan alone; that a player has the breath
    for them, or can get out of the water at a ladder, is not); what a
    body in the water does as its layer goes; that a gate does not shut
    on a real player (the stand-in shows the function's logic only);
    anything aimed at players: titles, chat, sounds, particles; what is
    seen through the dam and the water; light, beyond the nine places
    read; that nothing spawns in the basin.
    """
    game_checks.no_run(ctx)
    saved_level = game_checks.save_level(ctx)
    try:
        return _check(ctx)
    finally:
        ctx.cmd(f"kill @e[tag={S1}]")
        ctx.cmd(f"kill @e[tag={S2}]")
        game_checks.restore_level(ctx, saved_level)
        ctx.function("difficulty/apply")


def _check(ctx: Any) -> list[str]:
    dome = ctx.layout.DOMES[INDEX]
    tunnel = ctx.layout.TUNNELS[INDEX]
    place = room(dome)
    b = room_blocks(dome)
    a_, b_, c_ = place.sluices
    problems: list[str] = []
    scan = game_checks.SCAN
    base = f"dome/{INDEX}"
    fall_back = game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def get(name: str) -> int:
        return ctx.score(f"#fl.{name}") or 0

    def state(**more: int) -> State:
        """the room's state as the scores have it"""
        names = ("w", "stage", "form", "ctl", "pump", "gate")
        return State(**({n: get(n) for n in names} | {"lit": get("ln")} | more))

    outside = middle(tunnels.at(ctx.layout.TUNNELS[INDEX - 1], 8, 0, 1))
    entrance = middle(domes.entrance(dome)[:3])

    def stand(tag: str, where: str) -> None:
        game_checks.stand_at(ctx, tag, where, gravity=True)

    def come_in(tag: str = S1) -> None:
        """a stand-in out of the dome and in again: a new entry"""
        stand(tag, outside)
        ctx.advance(game_checks.EMPTY)
        stand(tag, entrance)

    def throw(cell: Cell, facing: str, on: bool = True) -> None:
        ctx.setblock(cell, lever(facing, on))

    def as_state(what: str, want: State | None = None) -> None:
        """every block of the room is as the state has it (a block that
        changes by itself: the same block, in whatever state), and the
        basin's water is right by count: all sources up to the level,
        air above, nothing flowing, no air under water"""
        want = want or state()
        moving = b.moving - {c for col in place.gauge for c in col}
        moving -= {c for s in place.sluices for c in s.line}
        # (a piston caught in mid stroke reads as a ``moving_piston``)
        wrong = [
            cell
            for cell, block in fixed_blocks(dome, want).items()
            if not ctx.is_block(
                cell, _name(block) if cell in moving else block.partition("{")[0]
            )
            and not (cell in moving and ctx.is_block(cell, "minecraft:moving_piston"))
        ]
        # (the beam engine is still whenever this is asked; the tide clock
        # never is, and its pistons' heads come and go)
        still = b.swept - place.tide.moving
        wrong += [c for c in still if not ctx.is_block(c, AIR)]
        if wrong:
            problems.append(f"{what}: {len(wrong)} blocks not as planned: {wrong[:6]}")
        got = counts(ctx)
        expect(f"{what}: the basin's count", got, expected(dome, want) | {"ran": TOP})

    def falls(to: int, what: str) -> None:
        """the water falls to a layer, one layer at a time, each within
        ``per`` ticks of the last, the gauge with it"""
        per = get("per")
        while (w0 := get("w")) > to:
            waited = 0
            while get("w") == w0 and waited <= per + 4 * STEP:
                ctx.advance(STEP)
                waited += STEP
            lamps = sum(ctx.is_block(c, f"{BULB}[lit=true]") for c in place.gauge[0])
            expect(
                f"{what}: a layer gone from {w0}", (get("w"), lamps), (w0 - 1, w0 - 1)
            )
            if get("w") == w0:
                break

    def solved() -> bool:
        return ctx.score(f"#d{INDEX}") == 2

    def unsolve() -> None:
        """the room and its tunnel put back, the dome open and unsolved"""
        ctx.function(f"tunnel/{INDEX}/reset")
        ctx.function(f"{base}/reset")
        ctx.set_score(f"#d{INDEX}", 1)
        ctx.set_score(f"#d{INDEX + 1}", saved[f"#d{INDEX + 1}"] or 0)
        ctx.set_score("#solved", saved["#solved"] or 0)
        ctx.advance(25)  # (the reset draws once more a second on)

    def set_stage(stage: int, **more: int) -> None:
        """a stage reached by the scores and ``draw``, as the game leaves
        it: any state of the water can follow any other"""
        for name, value in ({"stage": stage, "w": STARTS[stage]} | more).items():
            ctx.set_score(f"#fl.{name}", value)
        for name in ("ctl", "t", "gate"):
            ctx.set_score(f"#fl.{name}", 0)
        ctx.function(f"{base}/target")
        ctx.function(f"{base}/draw")
        ctx.advance(2 * STEP)

    def engine_seen(ticks: int) -> list[set[bool]]:
        """the beam engine's two pistons over some ticks: out, in or both"""
        seen: list[set[bool]] = [set(), set()]
        for _ in range(ticks // 3):
            ctx.advance(3)
            for piston, states in zip(place.engine.pistons, seen, strict=True):
                states.add(ctx.is_block(piston, "minecraft:piston[extended=true]"))
        return seen

    def bars(s: Sluice) -> int:
        return sum(ctx.is_block(c, BARS) for c in s.gate)

    # ---- before: nobody about, the room and its tunnel reset, the dome open
    names = (f"#d{INDEX}", f"#d{INDEX + 1}", "#solved", "#level")
    saved = game_checks.scores(ctx, *names)
    others = [f"#d{d.index}" for d in ctx.layout.DOMES if d.index != INDEX]
    others += [f"#t{t.index}" for t in ctx.layout.TUNNELS]
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(fall_back)
    if (n := ctx.score("#players")) or ctx.score(f"#form{INDEX}"):
        return [f"{n} players or stand-ins of another check are in the game"]
    unsolve()
    as_state("built", START)
    problems += [f"built: {p}" for p in domes.check_shell(ctx, dome, False)]
    ctx.advance(200)
    expect("the flood, 200 ticks on", counts(ctx), expected(dome) | {"ran": TOP})
    problems += [f"200 ticks on: {p}" for p in domes.check_shell(ctx, dome, False)]
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
    # light at head height: in the hall, on the crest, the balcony and the
    # platform (the decks under water are read when the room is dry)
    at = place.frame.at
    lit_places = {
        "the hall": at(-17, 0, 2),
        "the dam's crest": at(DAM_F + 1, 0, WALK_H + 2),
        "the balcony": at(-4, 0, WALK_H + 2),
        "the crown": at(-1, 2, CROWN_H + 2),
        "the east platform": at(12, 0, WALK_H + 2),
    }
    light = '{type:"minecraft:location_check",predicate:{light:{light:{min:8}}}}'

    def dark(places: dict[str, Cell]) -> list[str]:
        return [
            name
            for name, cell in places.items()
            if not ctx.test(f"execute positioned {_xyz(cell)} if predicate {light}")
        ]

    expect("places with light under 8, the room flooded", dark(lit_places), [])
    # the tide clock, which nothing starts or stops: each lamp seen lit and
    # unlit, each piston out and in, over 10 s
    tide: list[set[bool]] = [set() for _ in (*place.tide.lamps, *place.tide.pistons)]
    for _ in range(50):
        ctx.advance(4)
        for cell, states in zip(place.tide.lamps, tide, strict=False):
            states.add(ctx.is_block(cell, f"{BULB}[lit=true]"))
        for cell, states in zip(place.tide.pistons, tide[4:], strict=True):
            states.add(ctx.is_block(cell, "minecraft:piston[extended=true]"))
    if any(states != {True, False} for states in tide):
        problems.append(f"the tide clock's lamps and pistons, on or off: {tide}")
    expect("the beam engine with nobody in", engine_seen(30), [{False}, {False}])

    # ---- solo, straight through
    stand(S1, entrance)
    ctx.advance(2 * STEP)
    expect("solo, entered", (get("live"), get("form")), (1, 1))
    level = ctx.score("#active") or game.DEFAULT_LEVEL
    expect("the level's values", {n: get(n) for n in scaled(level)}, scaled(level))
    absent = [
        ctx.is_block(c, AIR) or ctx.is_block(c, WATER) for c in (b_.lever, b_.pump)
    ]
    expect("stage B's levers before pump A has run", absent, [True, True])
    # the control thrown: the gate opens, the line lights; left alone, the
    # spring throws it back after the level's clock and the bars are back
    expect("gate A shut", bars(a_), len(a_.gate))
    throw(a_.lever, a_.facing)
    ctx.advance(3 * STEP)
    lamps = sum(ctx.is_block(c, f"{BULB}[lit=true]") for c in a_.line)
    expect("control A thrown", (get("ctl"), bars(a_), lamps), (1, 0, LINE))
    expect("no pump thrown: the water", get("w"), TOP)
    ctx.advance(get("ta") * STEP // 2)
    lamps = sum(ctx.is_block(c, f"{BULB}[lit=true]") for c in a_.line)
    if not 0 < lamps < LINE or get("ctl") != 1:
        problems.append(f"half the clock on: {lamps} lamps of the line lit")
    ctx.advance(get("ta") * STEP // 2 + 4 * STEP)
    got = (get("ctl"), bars(a_), ctx.is_block(a_.lever, lever(a_.facing)))
    expect("the clock run out: control, bars, lever back", got, (0, len(a_.gate), True))
    # again, and the pump: a layer every ``per`` ticks, the engine working
    throw(a_.lever, a_.facing)
    ctx.advance(2 * STEP)
    throw(a_.pump, a_.pump_facing)
    ctx.advance(2 * STEP)
    expect("pump A thrown", get("pump"), 1)
    falls(TOP - 1, "stage A")
    expect(
        "the beam engine's torch while pumping",
        ctx.is_block(place.engine_torch, TORCH),
        True,
    )
    seen = engine_seen(40)  # (the clock's half period is about 10 ticks)
    if seen != [{True, False}, {True, False}]:
        problems.append(f"the beam engine's pistons while pumping: {seen}")
    falls(TARGETS[0], "stage A, on")
    ctx.advance(2 * STEP)
    expect("stage A done", (get("stage"), get("w"), get("pump")), (1, STARTS[1], 0))
    ctx.advance(30)  # (the clock's last stroke, after its torch has gone)
    expect("the beam engine, the stage done", engine_seen(12), [{False}, {False}])
    expect("its torch, the stage done", ctx.is_block(place.engine_torch, AIR), True)
    as_state("stage B uncovered")
    shown = [ctx.is_block(c, LEVER) for c in (b_.lever, b_.pump)]
    expect("stage B's levers, uncovered", shown, [True, True])
    # B: the water rests part way when the spring runs out, for as long as
    # it is left, and goes on when the control is thrown again
    throw(b_.lever, b_.facing)
    ctx.advance(2 * STEP)
    throw(b_.pump, b_.pump_facing)
    falls(STARTS[1] - 2, "stage B")
    ctx.set_score("#fl.t", 1)
    ctx.advance(3 * STEP)
    expect("the spring run out mid-stage", (get("ctl"), get("pump")), (0, 1))
    part = get("w")
    ctx.advance(200)
    expect("the water at rest, 200 ticks on", get("w"), part)
    as_state("stage B, at rest part way")
    throw(b_.lever, b_.facing)
    falls(TARGETS[1], "stage B, on")
    ctx.advance(2 * STEP)
    expect("stage B done", (get("stage"), get("w")), (2, STARTS[2]))
    ctx.advance(30)  # (the beam engine's last stroke)
    as_state("stage C uncovered")
    # C, and the dome solved, once
    throw(c_.lever, c_.facing)
    ctx.advance(2 * STEP)
    throw(c_.pump, c_.pump_facing)
    falls(TARGETS[2], "stage C")
    ctx.advance(2 * STEP)
    expect("solved", (solved(), get("stage"), get("w")), (True, 3, 0))
    problems.extend(game_checks.pull_pump(ctx, INDEX))
    expect("its tunnel at the solve", ctx.score(f"#t{INDEX}") in (1, 2), True)
    expect("places with light under 8, the room dry", dark(lit_places), [])
    low = {
        "the machine deck": at(2, 10, MID_H + 2),
        "the lower deck": at(12, 0, LOW_H + 2),
        "the floor": at(-6, 5, 2),
        "under the lower deck": at(12, -4, 2),
    }
    expect("places with light under 8 on the lower decks", dark(low), [])
    ctx.advance(tunnels.event_ticks(tunnel) + 60)
    got = game_checks.scores(ctx, f"#t{INDEX}", f"#d{INDEX + 1}")
    expect(
        "its tunnel open, the next dome open",
        got,
        {f"#t{INDEX}": 2, f"#d{INDEX + 1}": 1},
    )
    doors = [c for d in tunnels.ends(tunnel) for _, c in domes.door_cells(d, tunnel)]
    expect("door cells open", sum(ctx.is_block(c, AIR) for c in doors), len(doors))
    expect("the dam door open", sum(ctx.is_block(c, AIR) for c in place.door), 6)
    as_state("solved, the tunnel open", SOLVED)
    problems += [f"tunnel open: {p}" for p in domes.check_shell(ctx, dome, False)]
    # a second entry leaves a solved room solved
    come_in()
    ctx.advance(4 * STEP)
    expect("solved, entered again", (solved(), get("w"), get("live")), (True, 0, 0))
    as_state("solved, entered again", SOLVED)

    # ---- nobody is shut in: a gate is open while anyone is beyond it,
    # and does not shut on its own cells while anyone is in them
    unsolve()
    come_in()
    stand(S1, middle(a_.stand))
    ctx.advance(3 * STEP)
    expect("one beyond gate A, the control off", (get("in"), bars(a_)), (1, 0))
    stand(S1, middle(a_.gate[0]))
    ctx.advance(3 * STEP)
    expect("one in gate A's own cells", (get("in"), get("g"), bars(a_)), (0, 1, 0))
    stand(S1, middle(place.frame.at(HOUSE_A[0][0] - 1, 0, WALK_H + 1)))
    ctx.advance(3 * STEP)
    expect("out again: gate A", (get("gate"), bars(a_)), (0, len(a_.gate)))
    # the same of gate B, under water (a stand-in sinks to the culvert's floor)
    set_stage(1)
    stand(S1, middle(at(-5, HATCH_B[1][0], LOW_H + 1)))
    ctx.advance(3 * STEP)
    expect("one beyond gate B, under water", (get("in"), bars(b_)), (1, 0))
    as_state("gate B open, under water")
    stand(S1, entrance)
    ctx.advance(3 * STEP)
    expect("out again: gate B", bars(b_), len(b_.gate))
    as_state("gate B shut again, under water")
    # gates B and C, a stand-in at the pump lever and in the gate's own
    # cells (under water: it sinks to their foot)
    for i, s in ((1, b_), (2, c_)):
        set_stage(i)
        n = s.key.upper()
        stand(S1, middle(s.stand))
        ctx.advance(3 * STEP)
        expect(f"one at pump {n}, the control off", (get("in"), bars(s)), (1, 0))
        stand(S1, middle(s.gate[0]))
        ctx.advance(3 * STEP)
        got = (get("in"), get("g"), bars(s))
        expect(f"one in gate {n}'s own cells", got, (0, 1, 0))
        stand(S1, entrance)
        ctx.advance(3 * STEP)
        expect(f"out again: gate {n}", bars(s), len(s.gate))

    # ---- the dome solved from outside (as the core's checks do), nobody
    # in it and the basin full: the flood is gone at once, long before the
    # tunnel's doors open (the pump engine's pistons are working, so the
    # air is not counted here)
    stand(S1, outside)
    ctx.advance(game_checks.EMPTY)
    unsolve()
    ctx.function(f"dome/{INDEX}/solved")
    ctx.advance(4)
    got = counts(ctx)
    expect(
        "solved from outside: the water",
        (get("w"), got["water"], got["fit"]),
        (0, 0, 0),
    )
    expect(
        "solved from outside: the dam door open",
        bars(c_) + sum(not ctx.is_block(c, AIR) for c in place.door),
        0,
    )
    shut = sum(not ctx.is_block(c, AIR) for c in doors)
    expect("solved from outside: the tunnel's doors still shut", shut, len(doors))

    # ---- duo: the control is a plate, held by a living weight only
    unsolve()
    come_in()
    stand(S2, entrance)
    ctx.advance(scan + 2 * STEP)
    expect("two in: the dome's form", ctx.score(f"#form{INDEX}"), 2)
    expect("two in: the form", (get("want"), get("form")), (2, 2))
    shape_ = (ctx.is_block(a_.plate, PLATE), ctx.is_block(a_.lever, AIR))
    expect("duo: plate down, lever gone", shape_, (True, True))
    as_state("duo")
    throw(a_.pump, a_.pump_facing)
    ctx.advance(get("per") + 4 * STEP)
    expect("duo: pump thrown, nobody on the plate", (get("pump"), get("w")), (1, TOP))
    ctx.cmd(
        f"summon minecraft:item {middle(a_.plate, 0.2)} "
        '{Item:{id:"minecraft:coal",count:1}}'
    )
    ctx.advance(30)
    expect("duo: an item on the plate", (get("ctl"), bars(a_)), (0, len(a_.gate)))
    ctx.cmd(f"kill @e[type=minecraft:item,{dp.box_selector(a_.plate, a_.plate)}]")
    stand(S1, middle(a_.plate))
    ctx.advance(20)
    expect("duo: one on the plate", (get("ctl"), bars(a_)), (1, 0))
    falls(TOP - 2, "duo, the plate held")
    stand(S1, entrance)
    ctx.advance(40)  # (a plate comes up within 2 s of the weight going)
    part = get("w")
    expect("duo: the plate let go", (get("ctl"), bars(a_)), (0, len(a_.gate)))
    ctx.advance(100)
    expect("duo: the water at rest", get("w"), part)
    stand(S1, middle(a_.plate))
    ctx.advance(20)
    falls(TARGETS[0], "duo, the plate held again")
    ctx.advance(2 * STEP)
    expect("duo: stage A done", (get("stage"), get("form")), (1, 2))
    ctx.advance(30)  # (the beam engine's last stroke)
    as_state("duo, stage B uncovered")

    # ---- a change of form in the middle of a stage, both ways
    # duo to solo with the plate held: the lever comes thrown, clock full
    part = get("w")
    stand(S1, middle(b_.plate))
    ctx.advance(20)
    expect("duo: plate B held", get("ctl"), 1)
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(fall_back + 2 * STEP)
    expect("one left: the dome's form", ctx.score(f"#form{INDEX}"), 1)
    got = (get("form"), get("ctl"), ctx.is_block(b_.lever, lever(b_.facing, True)))
    expect("one left, the plate held: form, control, lever thrown", got, (1, 1, True))
    if not get("tb") - (fall_back + 200) // STEP <= get("t") <= get("tb"):
        problems.append(f"one left: the clock is {get('t')} of {get('tb')} steps")
    expect(
        "one left: the plate gone, the gate open",
        (ctx.is_block(b_.plate, AIR), bars(b_)),
        (True, 0),
    )
    expect(
        "one left: the water kept", (get("w"), get("stage"), get("live")), (part, 1, 1)
    )
    # solo to duo while the clock runs: nothing changes until it has run out
    stand(S1, entrance)
    stand(S2, entrance)
    ctx.advance(scan + 4 * STEP)
    got = (get("want"), get("form"), get("ctl"), bars(b_))
    expect("a second comes in, the clock running", got, (2, 1, 1, 0))
    ctx.set_score("#fl.t", 2)
    ctx.advance(6 * STEP)
    got = (get("form"), get("ctl"), ctx.is_block(b_.plate, PLATE), bars(b_))
    expect("the clock run out: the plate now", got, (2, 0, True, len(b_.gate)))
    # duo to solo with nobody on the plate: the lever comes back at rest
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(fall_back + 2 * STEP)
    got = (get("form"), get("ctl"), ctx.is_block(b_.lever, lever(b_.facing)))
    expect("one left, the plate not held", got, (1, 0, True))
    as_state("after the changes of form")

    # ---- everyone leaves with the water part drained: it is kept, the
    # control put back; a new entry finds it so, with the level's values
    throw(b_.lever, b_.facing)
    ctx.advance(2 * STEP)
    throw(b_.pump, b_.pump_facing)
    falls(get("w") - 1, "stage B, before leaving")
    part = get("w")
    stand(S1, outside)
    ctx.advance(game_checks.EMPTY + scan)
    got = (get("live"), get("ctl"), get("w"), get("stage"), get("pump"), bars(b_))
    expect("empty, part drained", got, (0, 0, part, 1, 1, len(b_.gate)))
    expect("empty: the engine's torch", ctx.is_block(place.engine_torch, AIR), True)
    as_state("empty, part drained")
    for new in (game.LEVELS[0], game.LEVELS[-1]):
        ctx.set_score("#level", new)
        come_in()
        want = scaled(new)
        expect(f"level {new}: the values", {n: get(n) for n in want}, want)
        expect(f"level {new}: the water kept", (get("w"), get("pump")), (part, 1))
    ctx.set_score("#level", saved["#level"] or game.DEFAULT_LEVEL)
    ctx.function("difficulty/apply")

    # ---- reset, from a scrambled state, and only its own dome
    stand(S2, entrance)
    ctx.advance(scan + 2 * STEP)
    throw(b_.pump, b_.pump_facing)
    stand(S1, middle(b_.plate))
    ctx.advance(get("per") + 30)
    scrambled = state()
    if scrambled.form != 2 or scrambled.gate != 1 or scrambled.w >= part:
        problems.append(f"the room was not scrambled before the reset: {scrambled}")
    back = place.frame.facing(-1, 0)
    ctx.setblock(place.lectern, f"minecraft:lectern[facing={back},has_book=false]")
    before = game_checks.scores(ctx, *others)
    ctx.function(f"{base}/reset")
    ctx.set_score(f"#d{INDEX}", 0)  # locked, so that nothing runs after it
    ctx.advance(25)
    as_state("reset from a scrambled state", START)
    expect(
        "reset: the other domes' and the tunnels' scores",
        game_checks.scores(ctx, *others),
        before,
    )
    if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("a logbook taken from the lectern was not put back")
    for kind in ("item", "falling_block"):
        n = ctx.count(f"@e[type=minecraft:{kind},{domes.sphere(dome)}]")
        expect(f"reset: {kind} entities in the dome (a lever washed off)", n, 0)

    # ---- after: nobody, the tunnels shut and flooded, the hall dry
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.function(f"tunnel/{INDEX}/reset")
    for name in names:
        ctx.set_score(name, saved[name] or 0)
    ctx.advance(fall_back)
    ctx.function(f"{base}/reset")
    ctx.advance(100)
    as_state("left", START)
    for t in (ctx.layout.TUNNELS[INDEX - 1], tunnel):
        got, want = tunnels.counts(ctx, t), tunnels.expected(t, 0)
        if ctx.score(f"#t{t.index}") == 0:
            expect(f"tunnel {t.index} left shut and flooded", got, want)
    problems += [f"left: {p}" for p in domes.check_shell(ctx, dome, False)]
    expect(
        "stand-ins left behind",
        ctx.count(f"@e[tag={S1}]") + ctx.count(f"@e[tag={S2}]"),
        0,
    )
    return problems


MODULE = game.Module(
    "flooded",
    stages={f"dome_{INDEX}_inside": build},
    functions=functions,
    checks={"flooded_dome": check},
)
