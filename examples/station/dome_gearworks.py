"""
The Gearworks (dome 2) of The Drowned Station: the building puzzle. Its
build stage (``dome_2_inside``), its datapack functions (``dome/2/...``)
and its live check (``gearworks``).

**The puzzle.** Adventure mode becomes building. The steam main has been
torn off its track: lay it again from the steam chest to the pump by the
far door. A player is lent *pipe* (a copper bulb that sticks only to the
rough track, ``can_place_on``) and a *wrench* (a pickaxe that breaks only
that pipe, ``can_break``). Steam creeps out of the chest along laid pipe,
a length every ``STEP`` ticks, lighting each length as it fills it, and
reaches ``n`` lengths from the chest and no further (the gentle rule:
*a length is lit if it is within n lengths of the chest along laid pipe*,
so pipe that leads nowhere costs nothing and the wrench is an eraser).
The way round the gallery is longer than ``n``; the short way crosses the
Great Gear, whose own track lies across the line until the clutch on the
catwalk is thrown. When steam reaches the pump's intake its three lamps
count up, and at the third the dome is solved.

- The risers and the run to the pump are *surviving pipe*, built in
  (``BUILT``, which the wrench cannot break), lit like the rest. Of the
  ``ROUTE`` lengths of the short way a player lays ``TO_LAY``.
- *Solo:* the pipe sticks to both metals of the track.
- *Duo:* each player's pipe sticks to one metal (rough brass, or rough
  copper), and the short way changes metal every few lengths, so the two
  work along it together. A bay each at the pipe store changes a player's
  kind. Nothing is held and nothing is timed.

**The two rules.** Laid pipe is kept when the room is left: ``empty``
only lets the steam out (it creeps again when someone comes back), and
only ``reset`` takes pipe up. The clutch latches once thrown. A change of
form is taken up at the next second's beat (``form/take``), between two
lengths, and changes only what the players carry.

**Real inputs, datapack brain.** The clutch is a real lever on brass with
two redstone lamps lit by its own power; the bays are real plates on
brass; the pipe is real blocks placed and broken by hand. The functions
read them. The room's machine to watch is the tappets: a torch clock in a
cage working two plain pistons (``fittings.torch_clock``). Nothing reads
it.

**State** (scores in ``st``, all ``#gear.<name>``): ``c<i>`` 1 while
length i has pipe in it; ``d<i>`` its distance from the chest along laid
pipe (``BIG``: not reached); ``m<i>`` scratch; ``n`` how far the steam
reaches, from the level in force when the room is first entered
(``scaled``); ``far`` the furthest length lit and ``spent`` 1 while pipe
lies beyond the steam's reach; ``gear`` 0 across, 1 turning, 2 along;
``turn`` ticks of the turn left; ``sink`` steps the intake has been fed;
``form`` and ``want`` (1 solo, 2 duo); ``live`` 1 while the room is set
up for those in it (a record). Tags ``st.gear.a`` (brass) and
``st.gear.b`` (copper) on players and stand-ins in the duo form.

**Functions** (the core calls the hooks, see game.py):

- ``enter``: the first into the unsolved room sets it up (``arm``: the
  level's ``n``, the plaque, the steam let out to creep anew);
- ``tick``: the decoration's beat, the clutch (``turn/start``,
  ``turn/step``, ``turn/end``), every ``STEP`` ticks ``step`` (``scan``
  -> ``restart`` if a lit length was taken -> ``relax`` -> ``show`` ->
  ``stats`` -> ``board`` -> ``intake``, which calls ``done``:
  ``station:dome/2/solved`` then ``restored``), every second ``second``
  (the form, the roles, the bays, the kit, the logbook);
- ``solo`` / ``duo``: what the room should become (``want``);
- ``leave``: what was lent taken back, as each player goes;
- ``empty``: the steam let out of an unsolved room; ``reset``:
  everything as built, all pipe up.

**Places.** Everything is placed in the dome's own frame, from pure data
(``lengths``, ``room``, ``room_blocks``) that the build, the pack, the
offline checks and the live check share. Three levels: the engine floor
(the aisle from door to door under the Great Gear, the steam chest, the
pipe store, both floor stairs, the tappets, the tanks), the gallery (a
square ring walk six blocks up with four bridges in to the Great Gear, a
toothed wheel eleven across lying on four piers; a fallen cog jammed
through its left side where the track is torn out) and the catwalk
across the dome over the gear, with the clutch in its middle. The
decoration: the running lights in the gear's bearing ring and the two
pinions (stepped by ``decor/step``, slow until the dome is solved and
four times the pace after, when the Great Gear's teeth join in), the
tappets, steam from the chest's chimney. None of it has a lever, button
or plate, a bulb or a block of the track.
"""

from __future__ import annotations

import math
from collections import deque
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
from fittings import Frame, frame, snbt

if TYPE_CHECKING:
    from collections.abc import Iterable

    from station_layout import Dome

INDEX = 2  # the Gearworks' place in the ring
OBJ = game.OBJ

STEP = 2  # ticks between steps of the steam: a length a step
BIG = 9999  # the distance of a length the steam has not reached
ROUTE = 63  # lengths of the short way, chest to pump (checked)
TO_LAY = 38  # of them, those a player lays (checked)
SINK_STEPS = 10  # steps of steam at the intake for each of its lamps
INTAKE_LAMPS = 3
TURN_TICKS = 30  # the Great Gear's quarter turn
DECOR_AT = 12  # the decoration steps when its count reaches this
DECOR_SOLVED = 3  # what a solved room adds to the count a tick (else 1)

# the puzzle's own blocks (``rooms.MEANINGS``: in no other dome)
TRACK = {"brass": "minecraft:raw_gold_block", "copper": "minecraft:raw_copper_block"}
PIPE = "minecraft:waxed_exposed_copper_bulb"  # laid by hand
BUILT = "minecraft:waxed_copper_bulb"  # surviving pipe: the wrench leaves it
WRENCH = "minecraft:iron_pickaxe"

BRASS = "minecraft:gold_block"
COPPER = "minecraft:waxed_copper_block"
CUT = "minecraft:waxed_cut_copper"
CHISELED = "minecraft:waxed_chiseled_copper"
EXPOSED = "minecraft:waxed_exposed_copper"
WEATHERED = "minecraft:waxed_weathered_copper"
OLD = "minecraft:waxed_weathered_cut_copper"  # the fallen cog
OLD_RIM = "minecraft:waxed_oxidized_copper"
TOOTH = ("minecraft:waxed_cut_copper", "minecraft:waxed_oxidized_cut_copper")
GRATE = "minecraft:waxed_copper_grate"
BARS = "minecraft:iron_bars"
ROD = "minecraft:waxed_lightning_rod"
STAIRS = "minecraft:waxed_cut_copper_stairs"
SLAB = "minecraft:waxed_cut_copper_slab"
TIMBER = "minecraft:dark_oak_planks"
STONE = "minecraft:polished_blackstone"
PLATE = "minecraft:polished_blackstone_pressure_plate"
LAMP = "minecraft:redstone_lamp"
GLOW = "minecraft:pearlescent_froglight"  # a running light, lit
INTAKE_LIT = "minecraft:ochre_froglight"
LANTERN = "minecraft:lantern[hanging=true]"
#: what a player would have to hold to open a locked block: nobody does
LOCK = '{lock:{items:"minecraft:barrier"}}'
#: the tappets' bed under their dust: lamps that follow the clock. Not
#: among what the fittings' own check proved: False puts cut copper back
TAPPET_LAMPS = True

ENTITY_TAG = "st.d2"  # everything this module summons
BOARD_TAG = "st.d2.board"
ROLE = {"brass": "st.gear.a", "copper": "st.gear.b"}
#: what is lent, by the key of ``fittings.lent``: the three pipes, the wrench
KEYS = {"both": "gear2", "brass": "gear2a", "copper": "gear2b", "wrench": "gear2w"}

# where things are, in the frame (forward, right; h above the floor)
DECK_H = 6  # the gallery's deck; feet are a block above
WALK_H = 12  # the catwalk's deck
LANE = 12  # the ring's inner lane, which carries the track
KERB_IN, KERB_OUT = LANE - 1, LANE + 3  # the kerbs the rails stand on
GEAR_R2 = 30  # the Great Gear: the cells with f^2 + r^2 no more than this
GEAR_REACH = 5  # its track runs this far each way from the hub
TEETH_R2 = 41
TORN = (3, 4, 5)  # the f of the track torn out of the ring's left side
COG = (4, -10, 5)  # the fallen cog: its plane's f, its middle's r and h
PLAQUE = (-13, 4)
LECTERN = (-14, 7)
RECALL = (-19, 3, -1)
CHEST = (-9, -9)  # the steam chest's middle (3 by 3)
CHEST_FEED = ((-9, -7), (-9, -6), (-9, -5), (-10, -5))
RISERS = ((-11, -5, -1), (11, 5, 1))  # f, r, and the side its pillar is on
DOOR_FEED_R = 5
STORE = (-13, -7)  # the pipe store's rack: its f, its middle's r
BAYS = {"brass": (-14, -6), "copper": (-14, -8)}  # the plates
CLUTCH = (2, 0)  # the console's post, in the catwalk's front rail
TAPPETS = (8, -8)  # the torch clock's block
INTAKE = ((18, 7), (19, 7), (20, 7))
FLOOR_STAIRS = ((-17, 6, 1), (16, -6, -1))  # low f, first r, the way it climbs
CATWALK_STAIR = (-8, -14)  # its foot: it climbs forward along the left side
LADDER = (2, 13)
TANKS = ((-4, 19), (2, 19), (-4, -21), (2, -21))  # low corners (3 by 3)
ACROSS, ALONG = 1, 2  # the Great Gear's two lines


# ---------------------------------------------------------------- the main


@dataclass(frozen=True)
class Length:
    """a length of the main: a cell pipe can be in"""

    part: str  # "chest", "ring", "back" (bridge), "along" (the gear) ...
    cell: Cell
    on: Cell | None  # the track block it grips; None for built-in pipe
    metal: str  # "brass" or "copper"; "" for built-in pipe
    line: int = 0  # ACROSS or ALONG: only while the Great Gear lies so

    @property
    def laid(self) -> bool:
        """is this a length a player lays (not surviving pipe)?"""
        return self.on is not None


def ring_lane() -> list[tuple[int, int]]:
    """the ring's inner lane (f, r), from the top of riser 1 round by the
    right side, the front, the left side and back"""
    g = LANE
    lane = [(-g, r) for r in range(RISERS[0][1], g + 1)]
    lane += [(f, g) for f in range(-g + 1, g + 1)]
    lane += [(g, r) for r in range(g - 1, -g - 1, -1)]
    lane += [(f, -g) for f in range(g - 1, -g - 1, -1)]
    lane += [(-g, r) for r in range(-g + 1, RISERS[0][1])]
    return lane


def ring_metal(i: int) -> str:
    """the metal of the ring's track at place i of ``ring_lane``: bands of
    six, set so that the back side from riser 1 is copper and the front
    side to riser 2 brass (each player lays within a few lengths of the
    other on the short way)"""
    half = len(ring_lane()) // 2
    band = (i % half) // 6 % 2
    return ("copper", "brass")[band ^ (i >= half)]


@cache
def lengths(dome: Dome) -> tuple[Length, ...]:
    """every length of the main, laid or built in: the one list the
    build, the pack and the checks share. A length's place in it is its
    number in the pack's scores"""
    fr = frame(dome)
    out: list[Length] = []

    def track(part: str, f: int, r: int, h: int, metal: str, line: int = 0) -> None:
        out.append(Length(part, fr.at(f, r, h + 1), fr.at(f, r, h), metal, line))

    def built(part: str, f: int, r: int, h: int) -> None:
        out.append(Length(part, fr.at(f, r, h), None, ""))

    for f, r in CHEST_FEED:
        track("chest", f, r, 0, "brass")
    f, r, _ = RISERS[0]
    for h in range(1, DECK_H + 2):
        built("riser 1", f, r, h)
    for i, (f, r) in enumerate(ring_lane()):
        if not (r == -LANE and f in TORN):
            track("ring", f, r, DECK_H, ring_metal(i))
    span = range(GEAR_REACH + 1, LANE)  # a bridge: from the gear to the ring
    for a in span:
        track("back", -a, 0, DECK_H, "brass")
        track("front", a, 0, DECK_H, "copper")
        track("left", 0, -a, DECK_H, "copper")
        track("right", 0, a, DECK_H, "brass")
    for a in range(1, span.start):
        track("along", -a, 0, DECK_H, "copper", ALONG)
        track("along", a, 0, DECK_H, "brass", ALONG)
        track("across", 0, -a, DECK_H, "copper", ACROSS)
        track("across", 0, a, DECK_H, "brass", ACROSS)
    built("hub", 0, 0, DECK_H + 1)
    f, r, _ = RISERS[1]
    for h in range(DECK_H + 1, 0, -1):
        built("riser 2", f, r, h)
    engine = fr_of(fr, tunnels.engine_cells(layout.TUNNELS[dome.index])[1, 0])
    for f in range(RISERS[1][0] + 1, engine[0]):
        built("door", f, DOOR_FEED_R, 1)
    return tuple(out)


def fr_of(fr: Frame, cell: Cell) -> tuple[int, int]:
    """a cell's place in a frame: forward and right of the middle"""
    dx, dz = cell[0] - fr.origin[0], cell[2] - fr.origin[2]
    return (
        dx * fr.forward[0] + dz * fr.forward[1],
        dx * fr.right[0] + dz * fr.right[1],
    )


@cache
def neighbours(dome: Dome) -> tuple[tuple[int, ...], ...]:
    """for each length, the lengths it touches (face to face)"""
    at = {ln.cell: i for i, ln in enumerate(lengths(dome))}
    return tuple(
        tuple(
            at[x + dx, y + dy, z + dz]
            for dx, dy, dz in rooms.FACES
            if (x + dx, y + dy, z + dz) in at
        )
        for x, y, z in (ln.cell for ln in lengths(dome))
    )


def part(dome: Dome, *names: str) -> list[int]:
    """the numbers of the lengths of these parts, in the list's order"""
    return [i for i, ln in enumerate(lengths(dome)) if ln.part in names]


def source(dome: Dome) -> int:
    """the length at the chest's outlet, where the steam starts"""
    return part(dome, "chest")[0]


def sink(dome: Dome) -> int:
    """the length against the pump engine: its intake"""
    return part(dome, "door")[-1]


def steam(dome: Dome, laid: Iterable[int], along: bool) -> dict[int, int]:
    """
    The rule of steam, as the pack works it out: the distance from the
    chest of every length that steam can come to through laid pipe.
    ``laid``: the lengths with pipe in them (the built-in ones always
    have); ``along``: how the Great Gear lies. A length is lit if its
    distance is no more than ``n``.
    """
    all_lengths = lengths(dome)
    line = ALONG if along else ACROSS
    there = {
        i
        for i, ln in enumerate(all_lengths)
        if (not ln.laid or i in set(laid)) and ln.line in (0, line)
    }
    start = source(dome)
    if start not in there:
        return {}
    found, edge = {start: 1}, deque([start])
    while edge:
        i = edge.popleft()
        for j in neighbours(dome)[i]:
            if j in there and j not in found:
                found[j] = found[i] + 1
                edge.append(j)
    return found


def line_to_pump(dome: Dome, along: bool) -> list[int]:
    """the shortest line from the chest to the pump with every length
    laid: the short way over the Great Gear (``along``), or the way round
    the gallery. In order from the chest; empty if there is none"""
    everything = range(len(lengths(dome)))
    found = steam(dome, everything, along)
    at = sink(dome)
    if at not in found:
        return []
    line = [at]
    while found[line[-1]] > 1:
        line.append(
            next(
                j
                for j in neighbours(dome)[line[-1]]
                if found.get(j) == found[line[-1]] - 1
            )
        )
    return line[::-1]


def scaled(level: int) -> dict[str, int]:
    """the room's value at a level, as the function ``scale`` works it
    out: how many lengths the steam reaches. At the tuned level 4 to
    spare over the short way; none at the top; at levels 1 and 2 enough
    for the way round the gallery, and the clutch is a short cut"""
    timer = game.scaled(level)["#diff.timer"]
    slack = (timer - 50) // 10 - 1
    if timer > 100:
        slack = (timer - 100) * 35 // 100 + 4
    return {"n": ROUTE + max(slack, 0)}


# ---------------------------------------------------------------- the room


@dataclass(frozen=True)
class Room:
    """where the Gearworks' working parts are"""

    frame: Frame
    post: fittings.Post  # the clutch console
    lever: Cell
    lever_off: str
    clutch_lamps: tuple[Cell, Cell]
    gear_track: dict[int, tuple[tuple[Cell, str], ...]]  # line -> (cell, track)
    intake: tuple[Cell, ...]  # its lamps, in the floor
    lectern: Cell
    bays: dict[str, Cell]  # the plates, by metal
    recall: tuple[int, int, int]  # the recall post: f, r, side
    board: Cell  # the steam board (a text display) is in this cell
    plaque_sign: Cell  # the plaque's third sign, which names ``n``
    chimney: Cell  # where the chest's steam rises
    # the decoration (no part of the puzzle)
    lights: tuple[Cell, ...]  # the running lights, in order round the ring
    teeth: tuple[tuple[Cell, ...], tuple[Cell, ...]]  # the gear's, in two sets
    pinions: tuple[tuple[Cell, ...], tuple[Cell, ...]]
    tappets: fittings.Machine


def gear_cells() -> set[tuple[int, int]]:
    """the Great Gear's disc (f, r)"""
    span = range(-LANE, LANE + 1)
    return {(f, r) for f in span for r in span if f * f + r * r <= GEAR_R2}


def tooth_cells() -> list[tuple[int, int]]:
    """the Great Gear's teeth (f, r), in order round it: the cells just
    outside the disc, clear of the four bridges"""
    span = range(-LANE, LANE + 1)
    found = [
        (f, r)
        for f in span
        for r in span
        if GEAR_R2 < f * f + r * r <= TEETH_R2 and min(abs(f), abs(r)) >= 3
    ]
    return sorted(found, key=_angle)


def _angle(cell: tuple[int, int]) -> float:
    return math.atan2(cell[1], cell[0])


def light_cells() -> list[tuple[int, int]]:
    """the running lights (f, r), in order round the bearing ring: the
    sixteen cells of the ring under the gear beside the four spokes"""
    a = GEAR_REACH
    found = [(s * a, t * k) for s in (-1, 1) for t in (-1, 1) for k in (1, 2)]
    found += [(t * k, s * a) for s in (-1, 1) for t in (-1, 1) for k in (1, 2)]
    return sorted(found, key=_angle)


def pinion_cells(side: int) -> tuple[list[tuple[int, int, int]], ...]:
    """a pinion (f, r, h) in two sets of cells that swap colours: an
    upright wheel between the piers on one side, a hub, a rim and four
    tips"""
    r = side * 5
    cells = [(df, r, 3 + dh) for df in (-1, 0, 1) for dh in (-1, 0, 1) if df or dh]
    cells += [(2, r, 3), (-2, r, 3), (0, r, 1), (0, r, 5)]
    return (
        [c for c in cells if (c[0] + c[2]) % 2 == 0],
        [c for c in cells if (c[0] + c[2]) % 2],
    )


def lever_block(fr: Frame, on: bool = False) -> str:
    return fittings.lever(fr.facing(-1, 0), on)


CLUTCH_SIGN = ("CLUTCH", "Great Gear", "Pull to put", "it in line.")


@cache
def room(dome: Dome) -> Room:
    fr = frame(dome)
    cf, cr = CLUTCH
    post = fittings.input_post(
        fr.at(cf, cr, WALK_H + 1),
        fr.facing(-1, 0),
        lever_block(fr),
        CLUTCH_SIGN,
        "CLUTCH",
        (ENTITY_TAG,),
    )
    gear_track: dict[int, list[tuple[Cell, str]]] = {ACROSS: [], ALONG: []}
    for ln in lengths(dome):
        if ln.line and ln.on:
            gear_track[ln.line].append((ln.on, TRACK[ln.metal]))
    pf, pr = PLAQUE
    hf, hr = CHEST
    teeth = [fr.at(f, r, DECK_H) for f, r in tooth_cells()]
    sets = [pinion_cells(side) for side in (-1, 1)]
    return Room(
        frame=fr,
        post=post,
        lever=post.input,
        lever_off=lever_block(fr),
        clutch_lamps=(fr.at(cf, cr - 1, WALK_H + 2), fr.at(cf, cr + 1, WALK_H + 2)),
        gear_track={line: tuple(cells) for line, cells in gear_track.items()},
        intake=tuple(fr.at(f, r, 0) for f, r in INTAKE),
        lectern=fr.at(*LECTERN, 1),
        bays={metal: fr.at(f, r, 1) for metal, (f, r) in BAYS.items()},
        recall=RECALL,
        board=fr.at(hf, hr, WALK_H - 1),
        plaque_sign=fr.at(pf - 1, pr + 1, 2),
        chimney=fr.at(hf, hr, WALK_H - 2),
        lights=tuple(fr.at(f, r, DECK_H - 1) for f, r in light_cells()),
        teeth=(tuple(teeth[0::2]), tuple(teeth[1::2])),
        pinions=(
            tuple(fr.at(*c) for one in sets for c in one[0]),
            tuple(fr.at(*c) for one in sets for c in one[1]),
        ),
        tappets=fittings.torch_clock(fr, *TAPPETS, h=1, side=1, pistons=True),
    )


def plaque_signs(n: int) -> tuple[tuple[str, ...], ...]:
    """the plaque's three signs; the third names how far the steam reaches"""
    return (
        ("GEARWORKS", "Steam Main", "", "Mend the main."),
        ("Lay pipe on", "the track from", "the steam chest", "to the pump."),
        ("Steam reaches", f"{n} lengths.", "Find the", "short way."),
    )


LOG_TITLE, LOG_AUTHOR = "Gearworks log", "O. Finch"
LOG_PAGES = [
    "Gearworks log\nO. Finch, Chief Engineer\n\nThis room was my answer to the "
    "Engine. Every pump takes its speed from the Great Gear, and the Great "
    "Gear takes it from me. That was the idea.",
    "Last night it pulled its own clutch. The gear swung out of line and tore "
    "the main off the track.\n\nThen a cog came down through the gallery. "
    "Marsh had been standing there a minute before. It waited until he had "
    "stepped clear. I did not see that then.",
    "To mend the main:\n\n1. Pipe and a wrench from the rack. The pipe grips "
    "the rough track and nothing else.\n\n2. Chest to pump, the short way. "
    "Steam only reaches so far.\n\n3. The clutch is on the catwalk. Put the "
    "gear back in line.",
    "With a mate: one takes brass pipe, one copper.\n\nI have sent Marsh up in "
    "the lift. I am going on to the Flooded Dome while the tunnel is dry.\n\n"
    "It did not break the track. It only took the pipe. I think it wants us "
    "to follow.\n\nO. F.",
]


def logbook(fr: Frame) -> str:
    return fittings.lectern_with_book(
        fr.facing(-1, 0), LOG_TITLE, LOG_AUTHOR, LOG_PAGES
    )


def board_text(n: int, far: int = 0, spent: bool = False) -> str:
    """the steam board's text (a list of components), as ``board`` writes it"""
    if spent:
        return (
            f'[{{text:"STEAM SPENT AT {n} LENGTHS\\n",color:"red"}},'
            '{text:"the pump not reached",color:"red"}]'
        )
    return (
        f'[{{text:"STEAM REACHES {n} LENGTHS\\n",color:"gold"}},'
        f'{{text:"filled {far}",color:"yellow"}}]'
    )


def pipe_item(kind: str) -> str:
    """the pipe a player is lent: ``both`` metals (solo), or one of them.
    What it sticks to is left in its tooltip: it is a hint"""
    metals = TRACK.values() if kind == "both" else (TRACK[kind],)
    listed = ",".join(f'"{m}"' for m in metals)
    names = {"both": "Steam pipe", "brass": "Brass-flange pipe"}
    name = names.get(kind, "Copper-flange pipe")
    item = (
        f"{PIPE}[minecraft:can_place_on={{blocks:[{listed}]}},"
        f"minecraft:custom_name={snbt(name)}]"
    )
    return fittings.lent(item, KEYS[kind])


def wrench_item() -> str:
    """the wrench: it breaks pipe laid by hand and nothing else"""
    item = (
        f'{WRENCH}[minecraft:can_break={{blocks:"{PIPE}"}},minecraft:unbreakable={{}},'
        f"minecraft:custom_name={snbt('Pipe wrench')}]"
    )
    return fittings.lent(item, KEYS["wrench"])


# -------------------------------------------------------------- the blocks


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
    #: cells the decoration steps between two blocks: cell -> the two
    either: dict[Cell, tuple[str, str]] = field(default_factory=dict)
    #: cells a moving part passes through (a piston's head)
    swept: set[Cell] = field(default_factory=set)
    #: the cells of the puzzle: what play reads or changes, and the fittings
    puzzle: set[Cell] = field(default_factory=set)

    def everything(self) -> dict[Cell, str]:
        return {**self.floor, **self.solid, **self.attached}

    def used(self) -> set[Cell]:
        return set(self.everything()) | self.clear | self.swept

    def put(self, cell: Cell, block: str, attached: bool = False) -> None:
        """a block where there must be none yet"""
        if cell in self.used():
            raise ValueError(f"cell {cell} given two blocks")
        (self.attached if attached else self.solid)[cell] = block

    def fit(self, cell: Cell, block: str, attached: bool = False) -> None:
        """a block of a run (a deck, a kerb, a rail) wherever something
        that was put before it has not taken the cell"""
        if cell not in self.used():
            (self.attached if attached else self.solid)[cell] = block


def name(block: str) -> str:
    """a block without its states and NBT"""
    return rooms.name(block)


def rod(way: str) -> str:
    return f"{ROD}[facing={way}]"


def cog_cells() -> list[tuple[int, int, int, bool]]:
    """the fallen cog (f, r, h, on its rim): a wheel on edge, jammed
    through the left side of the gallery"""
    f, mid, high = COG
    return [
        (f, mid + dr, high + dh, dr * dr + dh * dh >= 8)
        for dr in range(-3, 4)
        for dh in range(-3, 4)
        if dr * dr + dh * dh <= 10
    ]


def _puzzle(b: Blocks, dome: Dome) -> None:
    """the blocks play reads or changes, and the room's fittings"""
    place = room(dome)
    fr = place.frame
    back = fr.facing(-1, 0)

    # the main: the track where pipe is to be laid, air over it; the
    # surviving pipe, dark
    for ln in lengths(dome):
        if ln.on is None:
            b.put(ln.cell, f"{BUILT}[lit=false]")
            continue
        b.clear.add(ln.cell)
        block = CUT if ln.line == ALONG else TRACK[ln.metal]  # as found: across
        if ln.on[1] == dome.floor_y:
            b.floor[ln.on] = block
        else:
            b.put(ln.on, block)
    # a pillar behind each riser, the floor under the run to the pump
    for f, r, side in RISERS:
        for h in range(1, DECK_H + 2):
            b.put(fr.at(f, r + side, h), CHISELED if h in (1, DECK_H) else COPPER)
    for i in part(dome, "door"):
        x, y, z = lengths(dome)[i].cell
        b.floor[x, y - 1, z] = CUT
    b.put(fr.at(0, 0, DECK_H), CHISELED)  # the hub's seat

    # the intake's lamps, in the floor beside the pump engine
    for cell in place.intake:
        b.floor[cell] = CHISELED

    # the clutch console, in the catwalk's front rail
    for cell, block in place.post.solid.items():
        b.put(cell, block)
    for cell, block in place.post.attached.items():
        b.put(cell, block, attached=True)
    for cell in place.clutch_lamps:
        b.put(cell, f"{LAMP}[lit=false]")

    # the plaque, the logbook, the recall button
    solid, attached = fittings.plaque_blocks(
        fr, *PLAQUE, signs=plaque_signs(scaled(game.DEFAULT_LEVEL)["n"])
    )
    for cell, block in solid.items():
        b.put(cell, block)
    for cell, block in attached.items():
        b.put(cell, block, attached=True)
    b.put(place.lectern, logbook(fr))
    solid, attached = fittings.recall_post_blocks(fr, *place.recall)
    for cell, block in solid.items():
        b.put(cell, block)
    for cell, block in attached.items():
        b.put(cell, block, attached=True)

    # the pipe store: a rack with a bay each side of its sign (the plates
    # are worked in the duo form only)
    f, mid = STORE
    for dr in (-2, -1, 0, 1, 2):
        ends = abs(dr) == 2
        b.put(fr.at(f, mid + dr, 1), CUT)
        b.put(fr.at(f, mid + dr, 2), rod(fr.facing(0, 1)) if ends else CUT)
        b.put(fr.at(f, mid + dr, 3), GRATE if ends or not dr else CUT)
    b.put(
        fr.at(f - 1, mid, 2),
        fittings.wall_sign(
            back, "PIPE STORE", "Pipe grips the", "rough track", "only."
        ),
        attached=True,
    )
    for metal, cell in place.bays.items():
        x, y, z = cell
        b.floor[x, y - 1, z] = BRASS
        b.put(cell, PLATE, attached=True)
        b.put(
            (x, y + 2, z),
            fittings.wall_sign(
                back, metal.upper(), "pipe bay", "Two engineers:", "one each."
            ),
            attached=True,
        )
    b.puzzle = b.used() | set(b.floor)


def _gear(b: Blocks, dome: Dome) -> None:
    """the Great Gear on its piers, the bearing ring and its running
    lights, the pinions"""
    place = room(dome)
    fr = place.frame
    # the spokes under the gear's two lines (they also close the underside
    # of its track), then the disc and its teeth
    reach = GEAR_REACH
    for a in range(-reach, reach + 1):
        b.fit(fr.at(a, 0, DECK_H - 1), CUT)
        if abs(a) < reach:  # (a pinion's tip closes the end of the other)
            b.fit(fr.at(0, a, DECK_H - 1), CUT)
    for f, r in gear_cells():
        b.fit(fr.at(f, r, DECK_H), CUT)
    for i, cells in enumerate(place.teeth):
        for cell in cells:
            b.put(cell, TOOTH[i])
            b.either[cell] = TOOTH
    # four piers, and the bearing ring they carry
    for sf in (-1, 1):
        for sr in (-1, 1):
            for f in (3, 4):
                for r in (3, 4):
                    for h in range(1, DECK_H):
                        top = h == DECK_H - 1
                        b.put(fr.at(sf * f, sr * r, h), CHISELED if top else CUT)
    for cell in place.lights:
        b.put(cell, CUT)
        b.either[cell] = (CUT, GLOW)
    # the pinions, upright between the side piers
    for i, cells in enumerate(place.pinions):
        for cell in cells:
            b.put(cell, TOOTH[i])
            b.either[cell] = TOOTH
    for side in (-1, 1):
        b.put(fr.at(0, side * 5, 3), CHISELED)
    for f, r in gear_cells():
        if 20 <= f * f + r * r:
            b.fit(fr.at(f, r, DECK_H - 1), EXPOSED)


def _gallery(b: Blocks, dome: Dome) -> None:
    """the gallery: the fallen cog, the ring walk and its four bridges,
    the stairs up to it and the columns under it"""
    fr = room(dome).frame
    right, left = fr.facing(0, 1), fr.facing(0, -1)
    # the fallen cog first: it has taken a piece out of the ring
    for f, r, h, rim in cog_cells():
        if h >= 1:
            cell = fr.at(f, r, h)
            if cell in b.clear:  # (never: the track is torn out here)
                raise ValueError(f"the fallen cog is on the main at {cell}")
            b.put(cell, OLD_RIM if rim else OLD)
    # the two stairs from the floor, a landing each outside the ring
    for f0, r0, way in FLOOR_STAIRS:
        up = right if way > 0 else left
        last = r0 + way * (DECK_H - 1)
        for f in (f0, f0 + 1):
            for i in range(DECK_H):
                b.put(
                    fr.at(f, r0 + way * i, 1 + i), f"{STAIRS}[facing={up},half=bottom]"
                )
            for k in (1, 2):
                b.put(fr.at(f, last + way * k, DECK_H), GRATE)
            b.put(fr.at(f, last + way * 3, DECK_H + 1), BARS)
        outer = f0 - 1 if f0 < 0 else f0 + 2
        for k in (1, 2):
            b.put(fr.at(outer, last + way * k, DECK_H + 1), BARS)
    # at the back bridge's gear end, where the steam first stops: the clutch
    b.put(
        fr.at(-GEAR_REACH - 1, 2, DECK_H + 1),
        fittings.standing_sign(
            fr.facing(-1, 0), "GREAT GEAR", "out of line.", "CLUTCH:", "catwalk above."
        ),
        attached=True,
    )
    # the bridges: a deck three wide with the track down its middle, a
    # timber under the track, a kerb and a rail each side
    span = range(GEAR_REACH + 1, LANE)
    for a in span:
        for sign in (-1, 1):
            for swap in (False, True):
                for w in (-2, -1, 0, 1, 2):
                    f, r = (w, sign * a) if swap else (sign * a, w)
                    if abs(w) == 2 and a < KERB_IN:
                        b.fit(fr.at(f, r, DECK_H), TIMBER)
                        b.fit(fr.at(f, r, DECK_H + 1), BARS)
                    elif abs(w) == 1:
                        b.fit(fr.at(f, r, DECK_H), GRATE)
                    elif w == 0:
                        b.fit(fr.at(f, r, DECK_H - 1), TIMBER)
    # the ring: three lanes of grating, the inner one the track's; a
    # timber under the track; a kerb and a rail inside and out
    gaps = set()  # where the outer rail lets a stair's landing in
    for f0, r0, way in FLOOR_STAIRS:
        edge = -KERB_OUT if f0 < 0 else KERB_OUT
        last = r0 + way * (DECK_H - 1)
        gaps |= {(edge, last + way), (edge, last + 2 * way)}
    for f in range(-KERB_OUT, KERB_OUT + 1):
        for r in range(-KERB_OUT, KERB_OUT + 1):
            lane = max(abs(f), abs(r))
            if lane == KERB_IN:
                on_bridge = min(abs(f), abs(r)) <= 1
                b.fit(fr.at(f, r, DECK_H), CUT)
                if not on_bridge:
                    b.fit(fr.at(f, r, DECK_H + 1), BARS)
            elif lane == LANE:
                b.fit(fr.at(f, r, DECK_H), CUT)  # (where the track is torn out)
                b.fit(fr.at(f, r, DECK_H - 1), TIMBER)
            elif LANE < lane < KERB_OUT:
                b.fit(fr.at(f, r, DECK_H), GRATE)
            elif lane == KERB_OUT:
                b.fit(fr.at(f, r, DECK_H), TIMBER)
                if (f, r) not in gaps:
                    b.fit(fr.at(f, r, DECK_H + 1), BARS)
    # columns under the middle lane, lanterns under the outer kerb
    mid = LANE + 1
    for a, c in ((mid, mid), (mid, 10), (10, mid)):
        for sf in (-1, 1):
            for sr in (-1, 1):
                for h in range(1, DECK_H):
                    b.put(fr.at(sf * a, sr * c, h), rod("up"))
    for a, c in ((KERB_OUT, 8), (8, KERB_OUT), (KERB_IN, 8), (8, KERB_IN)):
        for sf in (-1, 1):
            for sr in (-1, 1):
                b.fit(fr.at(sf * a, sr * c, DECK_H - 1), LANTERN, attached=True)


def _catwalk(b: Blocks, dome: Dome) -> None:
    """the catwalk across the dome over the gear, the stair up to it from
    the gallery's left side and the ladder from its right"""
    fr = room(dome).frame
    ahead = fr.facing(1, 0)
    sf, sr = CATWALK_STAIR
    rise = WALK_H - DECK_H
    # the stair, in the ring's outer lane, a rail beside its upper steps
    for i in range(rise):
        b.put(
            fr.at(sf + i, sr, DECK_H + 1 + i), f"{STAIRS}[facing={ahead},half=bottom]"
        )
        b.put(fr.at(sf + i, sr - 1, DECK_H + 2 + i), BARS)  # (the dome's side)
        if i >= 2:
            b.put(fr.at(sf + i, sr + 1, DECK_H + 2 + i), BARS)
    top = sf + rise  # the landing, in the line of the catwalk's back rail
    b.put(fr.at(top, sr, WALK_H), GRATE)
    b.clear |= {fr.at(top, sr, WALK_H + 1), fr.at(top, sr, WALK_H + 2)}
    # the ladder up a mast to a gap in the front rail
    lf, lr = LADDER
    for h in range(DECK_H + 1, WALK_H + 1):
        b.put(fr.at(lf, lr + 1, h), CUT)
        b.put(fr.at(lf, lr, h), f"minecraft:ladder[facing={fr.facing(0, -1)}]", True)
    b.clear |= {fr.at(lf, lr, WALK_H + 1), fr.at(lf, lr, WALK_H + 2)}
    # the deck three wide, a timber and a rail each side and across each end
    end = KERB_OUT
    for r in range(-end, end + 1):
        for f in (-2, -1, 0, 1, 2):
            edge = abs(f) == 2 or abs(r) == end
            b.fit(fr.at(f, r, WALK_H), TIMBER if edge else GRATE)
            if edge:
                b.fit(fr.at(f, r, WALK_H + 1), BARS)
    # masts from the gallery's outer lane to its four corners
    for f, r in ((-2, LANE + 2), (2, -LANE - 2), (-2, -LANE - 2)):
        for h in range(DECK_H + 1, WALK_H):
            b.fit(fr.at(f, r, h), rod("up"))


def _floor(b: Blocks, dome: Dome) -> None:
    """the engine floor: the aisle, the steam chest, the tappets in their
    cage, the tanks"""
    place = room(dome)
    fr = place.frame
    back = fr.facing(-1, 0)
    cells = domes.dome_cells(dome)
    lights = domes.light_cells(dome)[0]
    # the aisle from door to door: blackstone, a line of copper down it
    for f in range(-dome.radius, dome.radius + 1):
        for r in (-2, -1, 0, 1, 2):
            cell = fr.at(f, r, 0)
            if cell in cells.floor and cell not in lights:
                b.floor.setdefault(cell, CUT if r == 0 else STONE)
    # the steam chest: a tank with two fires in its face, an outlet
    # towards the track, a chimney up through the court
    f, r = CHEST
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            for h in (1, 2, 3, 4):
                corner = df and dr
                b.put(fr.at(f + df, r + dr, h), CUT if corner or h == 4 else COPPER)
    for dr in (-1, 0):
        b.solid[fr.at(f - 1, r + dr, 1)] = (
            f"minecraft:furnace[facing={back},lit=true]{LOCK}"
        )
    b.solid[fr.at(f, r + 1, 1)] = CHISELED
    for h in range(5, WALK_H - 2):
        b.put(fr.at(f, r, h), CUT)
    b.put(place.chimney, GRATE)
    b.clear.add(place.board)
    # the tappets: a torch clock that works two plain pistons, lamps under
    # its dust, in a cage with a grating lid
    machine = place.tappets
    b.floor |= machine.bed
    for cell, block in machine.solid.items():
        b.put(cell, block)
    for cell, block in machine.attached.items():
        b.put(cell, block, attached=True)
        if TAPPET_LAMPS and "redstone_wire" in block:
            under = (cell[0], cell[1] - 1, cell[2])
            b.floor[under] = f"{LAMP}[lit=false]"
            b.moving.add(under)
    b.swept |= machine.moving - b.used()
    b.moving |= set(machine.attached) | set(machine.pistons)
    tf, tr = TAPPETS
    for f in range(tf - 3, tf + 4):
        for r in range(tr - 2, tr + 3):
            if f in (tf - 3, tf + 3) or r in (tr - 2, tr + 2):
                for h in (1, 2):
                    b.put(fr.at(f, r, h), BARS)
            b.put(fr.at(f, r, 3), GRATE)
    # the tanks against the glass, a pipe from each to the gallery's kerb
    for f, r in TANKS:
        side = 1 if r > 0 else -1
        for df in (0, 1, 2):
            for dr in (0, 1, 2):
                for h in range(1, 7):
                    b.put(fr.at(f + df, r + dr, h), CUT if h in (1, 6) else WEATHERED)
                b.put(fr.at(f + df, r + dr, 7), f"{SLAB}[type=bottom]")
        near = r - 1 if side > 0 else r + 3
        for pr in range(near, side * KERB_OUT, -side):
            b.put(fr.at(f + 1, pr, DECK_H), rod(fr.facing(0, side)))


@cache
def room_blocks(dome: Dome) -> Blocks:
    """the Gearworks' blocks as built and as ``reset`` leaves them: no pipe
    laid, the Great Gear across, the clutch out. (Cached: do not change
    what it gives.)"""
    b = Blocks()
    _puzzle(b, dome)
    _gear(b, dome)
    _gallery(b, dome)
    _catwalk(b, dome)
    _floor(b, dome)
    return b


def dressing(dome: Dome) -> dict[Cell, str]:
    """the blocks that are no part of the puzzle"""
    b = room_blocks(dome)
    return {c: block for c, block in b.everything().items() if c not in b.puzzle}


# -------------------------------------------------------- the offline checks

#: what stands on or hangs from a block and is still in the way
IN_THE_WAY = ("minecraft:lantern",)


def walks(dome: Dome) -> dict[str, Cell]:
    """where a player must be able to walk to from the entrance, by name:
    the cell their feet are in"""
    place = room(dome)
    fr = place.frame
    up, top = DECK_H + 1, WALK_H + 1
    lx, ly, lz = place.lever
    targets = {
        "the way out": fr.at(dome.radius - 3, 0, 1),
        "the plaque": fr.at(PLAQUE[0] - 2, PLAQUE[1], 1),
        "the logbook": fr.at(LECTERN[0] - 1, LECTERN[1], 1),
        "the pipe store": fr.at(STORE[0] - 2, STORE[1], 1),
        "the steam chest's outlet": fr.at(CHEST_FEED[0][0] + 1, CHEST_FEED[0][1], 1),
        "the foot of riser 1": fr.at(CHEST_FEED[-1][0], CHEST_FEED[-1][1] + 1, 1),
        "the tappets": fr.at(TAPPETS[0], TAPPETS[1] + 3, 1),
        "the intake": fr.at(INTAKE[1][0], INTAKE[1][1] + 1, 1),
        "the run to the pump": fr.at(16, DOOR_FEED_R - 1, 1),
        "the gallery, back": fr.at(-LANE - 1, -2, up),
        "the gallery, right": fr.at(0, LANE + 1, up),
        "the gallery, front": fr.at(LANE + 1, 2, up),
        "the gallery, left": fr.at(0, -LANE - 1, up),
        "past the fallen cog": fr.at(COG[0], -LANE - 2, up),
        "the back bridge": fr.at(-8, 1, up),
        "the front bridge": fr.at(8, -1, up),
        "the left bridge": fr.at(1, -8, up),
        "the right bridge": fr.at(-1, 8, up),
        "the Great Gear": fr.at(-2, 2, up),
        "the head of stair 1": fr.at(FLOOR_STAIRS[0][0], LANE + 1, up),
        "the head of stair 2": fr.at(FLOOR_STAIRS[1][0], -LANE - 1, up),
        "the clutch": (lx, ly - 1, lz),
        "the catwalk's right end": fr.at(0, LANE + 2, top),
    }
    for metal, cell in place.bays.items():
        targets[f"the {metal} bay"] = cell
    return targets


def pipe_states(dome: Dome) -> dict[str, set[int]]:
    """the states of the main a walk is checked in: none laid, and every
    length laid with the Great Gear each way"""
    every = lengths(dome)
    return {
        "no pipe laid": set(),
        "all pipe laid, the gear across": {
            i for i, ln in enumerate(every) if ln.laid and ln.line != ALONG
        },
        "all pipe laid, the gear along": {
            i for i, ln in enumerate(every) if ln.laid and ln.line != ACROSS
        },
    }


def walk_problems(dome: Dome, more: Iterable[Cell] = ()) -> list[str]:
    """
    Every place of ``walks`` can be walked to from the entrance, with no
    pipe laid and with all of it laid (pipe is a block a player steps
    over): feet and head in free cells with something to stand on, a step
    level or one up or down. The two forms are the same room block for
    block. The ladder is left out: a player who cannot use it has the
    stair. ``more``: cells to take as full as well (for trying the check).
    """
    b = room_blocks(dome)
    blocked = set(b.solid) | b.swept | set(more)
    blocked |= {c for c, block in b.attached.items() if name(block) in IN_THE_WAY}
    problems = []
    for state, laid in pipe_states(dome).items():
        pipe = {lengths(dome)[i].cell for i in laid}
        problems += [
            f"{state}: {p}"
            for p in rooms.walk_problems(
                dome, set(b.solid) | set(more) | pipe, walks(dome), blocked | pipe
            )
        ]
    return problems


def sights(dome: Dome) -> tuple[dict[str, Cell], dict[str, Cell]]:
    """what the puzzle wants seen (eyes, targets): the steam board from
    where pipe is laid and from the clutch"""
    spots = walks(dome)
    names = ("the foot of riser 1", "the gallery, back", "the back bridge")
    names += ("the Great Gear", "the front bridge", "the gallery, front", "the clutch")
    return {n: spots[n] for n in names}, {"the steam board": room(dome).board}


def sight_problems(dome: Dome, more: Iterable[Cell] = ()) -> list[str]:
    """the steam board is in sight from where the main is laid, the Great
    Gear's hub from the clutch, and the far door's window from the
    entrance (grating, bars and pipes count as clear)"""
    b = room_blocks(dome)
    blocks = {**b.solid, **dict.fromkeys(more, COPPER)}
    eyes, targets = sights(dome)
    problems = rooms.sight_problems(blocks, eyes, targets)
    hub = lengths(dome)[part(dome, "hub")[0]].cell
    problems += rooms.sight_problems(
        blocks, {"the clutch": eyes["the clutch"]}, {"the Great Gear's hub": hub}
    )
    return problems + rooms.window_problems(dome, blocks)


def stray_cells(dome: Dome) -> set[Cell]:
    """the cells pipe could be stuck in that are no length of the main:
    the open faces of a track block other than the one its length is
    against, with the Great Gear either way. There must be none (the room
    closes every such face), so no function has to clear them"""
    b = room_blocks(dome)
    full = set(b.everything()) | set(domes.dome_cells(dome).floor)
    found = set()
    for ln in lengths(dome):
        if ln.on is not None:
            x, y, z = ln.on
            found |= {
                (x + dx, y + dy, z + dz)
                for dx, dy, dz in rooms.FACES
                if (x + dx, y + dy, z + dz) not in full
            }
    inside = domes.dome_cells(dome).interior  # (under the floor is ground)
    return (found & inside) - {ln.cell for ln in lengths(dome)}


def main_problems(dome: Dome) -> list[str]:
    """the main's own data: the short way and the way round as long as
    the plan says, the left side torn, every level's reach, redstone
    clear of the pipe"""
    problems = []
    every = lengths(dome)
    short, round_ = line_to_pump(dome, True), line_to_pump(dome, False)
    if len(short) != ROUTE:
        problems.append(f"the short way is {len(short)} lengths, not {ROUTE}")
    if sum(every[i].laid for i in short) != TO_LAY:
        problems.append(f"the short way has not {TO_LAY} lengths to lay")
    if not any(every[i].line == ALONG for i in short):
        problems.append("the short way does not cross the Great Gear")
    if len(round_) <= ROUTE or any(every[i].line for i in round_):
        problems.append(f"the way round the gallery is {len(round_)} lengths")
    for level in game.LEVELS:
        n = scaled(level)["n"]
        if n < ROUTE:
            problems.append(f"level {level}: steam for {n} does not reach the pump")
        if level >= game.DEFAULT_LEVEL and n >= len(round_):
            problems.append(f"level {level}: the way round works without the gear")
    if len({ln.cell for ln in every}) != len(every):
        problems.append("two lengths in one cell")
    if stray := stray_cells(dome):
        problems.append(f"{len(stray)} open faces of the track: {min(stray)}")
    # a bulb beside redstone is turned over by it: none within two blocks
    b = room_blocks(dome)
    words = ("redstone", "repeater", "lever", "piston", "pressure_plate", "button")
    live = [c for c, block in b.everything().items() if any(w in block for w in words)]
    for ln in every:
        near = [
            c
            for c in live
            if max(abs(p - q) for p, q in zip(c, ln.cell, strict=True)) <= 2
        ]
        if near:
            problems.append(f"redstone at {near[0]} by the length at {ln.cell}")
            break
    return problems


def inputs(dome: Dome) -> set[Cell]:
    """the room's real inputs: the clutch, the two bays' plates, the recall
    button"""
    place = room(dome)
    b = room_blocks(dome)
    button = {c for c, block in b.attached.items() if "_button" in block}
    return {place.lever, *place.bays.values()} | button


def room_problems(dome: Dome) -> list[str]:
    """the whole plan against the dome, with no server: every cell inside
    it and off the cells the tunnels reserve, the main as the plan says,
    the inputs on brass with their signs and nothing else to work, the
    decoration free of the puzzle's blocks, the walks and the sights"""
    try:
        b = room_blocks(dome)
    except ValueError as e:
        return [str(e)]
    above = {**b.solid, **b.attached}
    more = b.clear | b.swept
    problems = rooms.room_problems(dome, above, b.floor, more)
    problems += fittings.placement_problems(dome, set(above) | more)
    if set(b.solid) & set(b.attached) or set(b.floor) & set(above):
        problems.append("a cell is given two blocks")
    problems += rooms.input_problems(
        above, inputs(dome), room(dome).clutch_lamps, b.floor
    )
    mine = (*TRACK.values(), PIPE, BUILT, "lever", "_button", "pressure_plate")
    problems += [
        f"{name(block)} at {cell} in the dressing"
        for cell, block in dressing(dome).items()
        if any(word in block for word in mine)
    ]
    problems += main_problems(dome)
    return problems + walk_problems(dome) + sight_problems(dome)


# --------------------------------------------------------------- the build


def summons(dome: Dome) -> list[str]:
    """the commands that summon the room's entities: the recall button's
    interaction, the clutch's label, the steam board"""
    place = room(dome)
    x, y, z = place.board
    n = scaled(game.DEFAULT_LEVEL)["n"]
    return [
        fittings.summon_recall(place.frame, *place.recall, tags=(ENTITY_TAG,)),
        *place.post.summons,
        fittings.display(
            (ENTITY_TAG, BOARD_TAG),
            (x + 0.5, y, z + 0.5),
            0,
            board_text(n),
            2.0,
            "center",
        ),
    ]


def build(ctx: Any) -> str:
    """the Gearworks inside its shell; takes the stub's BYPASS away, wipes
    what was inside but the pump engine, and leaves the room as ``reset``
    does"""
    dome = ctx.layout.DOMES[INDEX]
    if problems := room_problems(dome):
        raise RuntimeError("the Gearworks: " + "; ".join(problems))
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    engine = set(tunnels.engine_cells(ctx.layout.TUNNELS[INDEX]).values())
    for command in game.clear_stub_commands(dome):
        ctx.cmd(command)
    ctx.cmd(f"kill @e[tag={ENTITY_TAG}]")
    ctx.fill_boxes(cells.interior - engine, AIR)
    for blocks in (b.floor, b.solid, b.attached):
        for cell, block in sorted(blocks.items()):
            ctx.setblock(cell, block)
    for command in summons(dome):
        ctx.cmd(command)
    # the pack's own idea of the room, if the pack is installed
    ctx.function(f"dome/{INDEX}/reset")
    ctx.advance(10)
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    laid = sum(ln.laid for ln in lengths(dome))
    return (
        f"{dome.name}: {len(b.everything())} blocks: the main's track "
        f"({laid} lengths to lay on, {len(lengths(dome)) - laid} built in), the "
        "steam chest, the pipe store, the clutch, plaque, logbook, recall "
        "button; the Great Gear on its piers, the gallery and its bridges, "
        "the catwalk, 2 floor stairs, the fallen cog, tappets, 4 tanks"
    )


# ----------------------------------------------------------- the functions


def _s(score: str) -> str:
    return f"#gear.{score} {OBJ}"


def _set(score: str, value: int) -> str:
    return f"scoreboard players set {_s(score)} {value}"


def _op(score: str, op: str, other: str) -> str:
    return f"scoreboard players operation {_s(score)} {op} {other} {OBJ}"


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


def _setblock(cell: Cell, block: str) -> str:
    return f"setblock {_xyz(cell)} {block}"


def functions(pack: dp.Pack) -> None:
    """the Gearworks' functions (see the module docstring)"""
    dome = layout.DOMES[INDEX]
    place = room(dome)
    fr = place.frame
    every = lengths(dome)
    touch = neighbours(dome)
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    #: the players alive in the dome and the checks' stand-ins
    bodies = f"@e[tag=st.in,scores={{st.dome={INDEX}}}"
    open_dome = f"#d{INDEX} {OBJ}"
    unsolved = f"if score {open_dome} matches 1"
    store = f"{pack.namespace}:dome{INDEX}"
    pack.constants(OBJ, 10, 35, 100)

    def fid(path: str) -> str:
        return pack.id(f"{base}/{path}")

    def sound(what: str, cell: Cell, volume: float = 1, pitch: float = 1) -> str:
        return f"playsound minecraft:{what} block {here} {_xyz(cell)} {volume} {pitch}"

    def say(text: str, colour: str = "yellow", who: str = here) -> str:
        return f'tellraw {who} {{text:{snbt(text)},color:"{colour}"}}'

    def bulb(ln: Length) -> str:
        return PIPE if ln.laid else BUILT

    hub = every[part(dome, "hub")[0]].cell
    chest = every[source(dome)].cell

    # -- the level's value: how far the steam reaches (``scaled``)
    pack.function(
        f"{base}/scale",
        [
            _op("slack", "=", "#diff.timer"),
            f"scoreboard players remove {_s('slack')} 50",
            _op("slack", "/=", "#10"),
            f"scoreboard players remove {_s('slack')} 1",
            _op("t", "=", "#diff.timer"),
            f"scoreboard players remove {_s('t')} 100",
            _op("t", "*=", "#35"),
            _op("t", "/=", "#100"),
            f"scoreboard players add {_s('t')} 4",
            f"execute if score #diff.timer {OBJ} matches 101.. "
            f"run {_op('slack', '=', '#gear.t')}",
            f"execute if score {_s('slack')} matches ..-1 run {_set('slack', 0)}",
            _set("n", ROUTE),
            _op("n", "+=", "#gear.slack"),
        ],
    )

    # -- the steam. ``scan``: which lengths have pipe in them; one that
    # was reached and is gone lets the steam out beyond it (``restart``)
    scan = [_set("cut", BIG)]
    for i, ln in enumerate(every):
        if ln.laid:
            scan += [
                f"execute if score {_s(f'c{i}')} matches 1 "
                f"unless block {_xyz(ln.cell)} {PIPE} "
                f"run {_op('cut', '<', f'#gear.d{i}')}",
                f"execute store success score {_s(f'c{i}')} "
                f"if block {_xyz(ln.cell)} {PIPE}",
            ]
    pack.function(f"{base}/scan", scan)
    pack.function(
        f"{base}/restart",
        [
            *(
                f"execute if score {_s(f'd{i}')} > {_s('cut')} run {_set(f'd{i}', BIG)}"
                for i in range(len(every))
            ),
            *(
                f"execute if score {_s(f'c{i}')} matches 0 run {_set(f'd{i}', BIG)}"
                for i, ln in enumerate(every)
                if ln.laid
            ),
            sound("block.fire.extinguish", chest, 1, 1.4),
        ],
    )
    # ``relax``: every length one more than the nearest length it touches,
    # all worked out from the last step's distances, so the steam creeps a
    # length a step; a distance only ever falls here
    relax = []
    for i in range(len(every)):
        first = "="
        if i == source(dome):
            relax.append(_set(f"m{i}", 0))
            first = "<"
        for k, j in enumerate(touch[i]):
            relax.append(_op(f"m{i}", first if k == 0 else "<", f"#gear.d{j}"))
        relax.append(f"scoreboard players add {_s(f'm{i}')} 1")
    for i, ln in enumerate(every):
        fall = _op(f"d{i}", "<", f"#gear.m{i}")
        relax.append(
            f"execute if score {_s(f'c{i}')} matches 1 run {fall}" if ln.laid else fall
        )
    pack.function(f"{base}/relax", relax)
    # ``show``: a length within reach lit, the rest dark
    show = []
    for i, ln in enumerate(every):
        at, d = _xyz(ln.cell), _s(f"d{i}")
        show += [
            f"execute if score {d} <= {_s('n')} if block {at} {bulb(ln)}[lit=false] "
            f"run setblock {at} {bulb(ln)}[lit=true]",
            f"execute if score {d} > {_s('n')} if block {at} {bulb(ln)}[lit=true] "
            f"run setblock {at} {bulb(ln)}[lit=false]",
        ]
    pack.function(f"{base}/show", show)
    stats = [_set("far", 0), _set("spent", 0)]
    for i in range(len(every)):
        d = _s(f"d{i}")
        stats += [
            f"execute if score {d} <= {_s('n')} run {_op('far', '>', f'#gear.d{i}')}",
            f"execute if score {d} > {_s('n')} if score {d} matches ..{BIG - 1} "
            f"run {_set('spent', 1)}",
        ]
    pack.function(f"{base}/stats", stats)
    # the steam let out: every length unreached and dark
    pack.function(
        f"{base}/dark",
        [
            *(_set(f"d{i}", BIG) for i in range(len(every))),
            *(
                f"execute unless score {_s(f'c{i}')} matches 0..1 run {_set(f'c{i}', 0)}"
                for i, ln in enumerate(every)
                if ln.laid
            ),
            f"function {fid('show')}",
            f"function {fid('stats')}",
            _set("sink", 0),
            f"function {fid('lamps')}",
            f"function {fid('board')}",
        ],
    )

    # -- the steam board: a text display, written when what it says changes
    board = fittings.display_selector(BOARD_TAG)
    pack.function(
        f"{base}/board/steam",
        [
            f"$data modify entity {board} text set value "
            '[{text:"STEAM REACHES $(n) LENGTHS\\n",color:"gold"},'
            '{text:"filled $(far)",color:"yellow"}]'
        ],
    )
    pack.function(
        f"{base}/board/spent",
        [
            f"$data modify entity {board} text set value "
            '[{text:"STEAM SPENT AT $(n) LENGTHS\\n",color:"red"},'
            '{text:"the pump not reached",color:"red"}]'
        ],
    )
    pack.function(
        f"{base}/board",
        [
            f"execute store result storage {store} n int 1 "
            f"run scoreboard players get {_s('n')}",
            f"execute store result storage {store} far int 1 "
            f"run scoreboard players get {_s('far')}",
            f"execute if score {_s('spent')} matches 0 "
            f"run function {fid('board/steam')} with storage {store}",
            f"execute if score {_s('spent')} matches 1 "
            f"run function {fid('board/spent')} with storage {store}",
            _op("far.shown", "=", "#gear.far"),
            _op("spent.shown", "=", "#gear.spent"),
        ],
    )

    # -- the intake: steam at the pump counts its three lamps up
    at_pump = f"score {_s(f'd{sink(dome)}')} <= {_s('n')}"
    pack.function(
        f"{base}/lamps",
        fittings.gauge_lines(
            place.intake, _s("sink"), SINK_STEPS, INTAKE_LIT, CHISELED
        ),
    )
    pack.function(
        f"{base}/intake",
        [
            f"execute if {at_pump} run scoreboard players add {_s('sink')} 1",
            f"execute unless {at_pump} run {_set('sink', 0)}",
            f"function {fid('lamps')}",
            *(
                f"execute if score {_s('sink')} matches {k * SINK_STEPS} run "
                + sound(
                    "block.note_block.bell", place.intake[k - 1], 2, (8 + 2 * k) / 10
                )
                for k in range(1, INTAKE_LAMPS + 1)
            ),
            f"execute if score {_s('sink')} matches {INTAKE_LAMPS * SINK_STEPS}.. "
            f"run function {fid('done')}",
        ],
    )
    pack.function(
        f"{base}/done",
        [
            f"function {pack.id(f'dome/{INDEX}/solved')}",
            f"function {fid('restored')}",
        ],
    )
    lever_on = lever_block(fr, True)
    lamps_lit = [_setblock(c, f"{LAMP}[lit=true]") for c in place.clutch_lamps]
    # the room once solved: steady, the pipe lit as it lies, nothing lent
    pack.function(
        f"{base}/restored",
        [
            _set("sink", INTAKE_LAMPS * SINK_STEPS),
            f"function {fid('lamps')}",
            f"execute as {bodies}] run function {fid('leave')}",
            fittings.text_line(
                BOARD_TAG, fittings.label_text("THE MAIN IS UP", "green")
            ),
            _set("live", 0),
        ],
    )

    # -- the Great Gear and its clutch
    def teeth(first: int) -> list[str]:
        """the gear's teeth in one of their two states"""
        return [
            _setblock(cell, TOOTH[(i + first) % 2])
            for i, cells in enumerate(place.teeth)
            for cell in cells
        ]

    for k in (0, 1):
        pack.function(f"{base}/turn/teeth_{k}", teeth(k))
    across, along = place.gear_track[ACROSS], place.gear_track[ALONG]
    off_the_gear = [
        f"execute if block {_xyz(ln.cell)} {PIPE} run {_setblock(ln.cell, AIR)}"
        for ln in every
        if ln.line == ACROSS
    ]
    pack.function(
        f"{base}/turn/start",
        [
            _set("gear", 1),
            _set("turn", TURN_TICKS),
            # whatever pipe lies on the gear is thrown off, its track taken up
            *off_the_gear,
            *(_setblock(cell, CUT) for cell, _ in across),
            *lamps_lit,
            sound("block.bell.use", place.lever, 2, 0.7),
            sound("block.piston.extend", hub, 2, 0.5),
            say("The clutch bites. The Great Gear begins to turn."),
        ],
    )
    pack.function(
        f"{base}/turn/step",
        [
            f"scoreboard players remove {_s('turn')} 1",
            f"execute if score {_s('turn')} matches {TURN_TICKS * 2 // 3} "
            f"run function {fid('turn/teeth_1')}",
            f"execute if score {_s('turn')} matches {TURN_TICKS // 3} "
            f"run function {fid('turn/teeth_0')}",
            f"execute if score {_s('turn')} matches ..0 run function {fid('turn/end')}",
        ],
    )
    pack.function(
        f"{base}/turn/end",
        [
            _set("turn", 0),
            _set("gear", 2),
            *(_setblock(cell, block) for cell, block in along),
            f"function {fid('turn/teeth_1')}",
            sound("block.anvil.land", hub, 1, 0.6),
            say("The Great Gear is in line: its track runs fore and aft."),
        ],
    )
    clutch = [
        f"execute if score {_s('gear')} matches 0 "
        f"if block {_xyz(place.lever)} minecraft:lever[powered=true] "
        f"run function {fid('turn/start')}",
        f"execute if score {_s('turn')} matches 1.. run function {fid('turn/step')}",
    ]

    # -- the decoration (no part of the puzzle: nothing above reads it)
    count = len(place.lights) // 2
    for k in range(count):
        on = (place.lights[k], place.lights[k + count])
        off = (place.lights[k - 1], place.lights[k - 1 + count])
        pack.function(
            f"{base}/decor/lights_{k}",
            [*(_setblock(c, CUT) for c in off), *(_setblock(c, GLOW) for c in on)],
        )
    for k in (0, 1):
        pack.function(
            f"{base}/decor/pinions_{k}",
            [
                _setblock(cell, TOOTH[(i + k) % 2])
                for i, cells in enumerate(place.pinions)
                for cell in cells
            ],
        )
    frame_no = _s("frame")
    solved_dome = f"if score {open_dome} matches 2"
    pack.function(
        f"{base}/decor/step",
        [
            f"scoreboard players remove {_s('beat')} {DECOR_AT}",
            f"scoreboard players add {frame_no} 1",
            f"execute if score {frame_no} matches {count}.. run {_set('frame', 0)}",
            *(
                f"execute if score {frame_no} matches {k} "
                f"run function {fid(f'decor/lights_{k}')}"
                for k in range(count)
            ),
            *(
                f"execute if score {frame_no} matches {k} "
                f"run function {fid(f'decor/pinions_{k // 2 % 2}')}"
                for k in range(0, count, 2)
            ),
            # the works awake: the Great Gear's own teeth join in
            *(
                f"execute {solved_dome} if score {frame_no} matches {k} "
                f"run function {fid(f'turn/teeth_{k % 2}')}"
                for k in range(count)
            ),
            f"execute if score {frame_no} matches 0 run "
            + sound("block.note_block.hat", hub, 0.6, 0.8),
            f"execute if score {frame_no} matches {count // 2} run "
            + sound("block.note_block.hat", hub, 0.6, 1.2),
            f"particle minecraft:cloud {middle(place.chimney, 1.2)} 0.2 0.4 0.2 0.01 2",
        ],
    )
    pack.function(
        f"{base}/decor/beat",
        [
            f"scoreboard players add {_s('beat')} 1",
            f"execute {solved_dome} run scoreboard players add {_s('beat')} "
            f"{DECOR_SOLVED}",
            f"execute if score {_s('beat')} matches {DECOR_AT}.. "
            f"run function {fid('decor/step')}",
        ],
    )

    # -- hints: a line of chat each, once per arming
    hints = {
        "start": fittings.hint(
            pack,
            INDEX,
            "start",
            "The pipe grips only the rough track. The track starts at the "
            "steam chest, on the left.",
            45,
        ),
        "short": fittings.hint(
            pack,
            INDEX,
            "short",
            "The steam gives out before the pump. There is a shorter way: "
            "look at the Great Gear.",
            30,
        ),
        "gear": fittings.hint(
            pack,
            INDEX,
            "gear",
            "The Great Gear lies out of line. Its clutch is on the catwalk, "
            "up the stair on the gallery's left side.",
            30,
        ),
    }
    edge = part(dome, "back")[0]  # the back bridge's length next to the gear
    waits = {
        "start": f"score {_s('far')} matches 0",
        "short": f"score {_s('spent')} matches 1",
        "gear": f"score {_s(f'd{edge}')} <= {_s('n')}",
    }
    held = [
        f"execute unless {waits[key]} run {hint.progress}"
        for key, hint in hints.items()
    ]
    # (the gear's hint only while the gear still lies across)
    held.append(
        f"execute unless score {_s('gear')} matches 0 run {hints['gear'].progress}"
    )

    # -- a step of the steam
    changed = (
        f"execute unless score {_s('far')} = {_s('far.shown')} "
        f"run function {fid('board')}",
        f"execute unless score {_s('spent')} = {_s('spent.shown')} "
        f"run function {fid('board')}",
    )
    pack.function(
        f"{base}/step",
        [
            _set("tick", 0),
            f"function {fid('scan')}",
            f"execute if score {_s('cut')} matches ..{BIG - 1} "
            f"run function {fid('restart')}",
            f"function {fid('relax')}",
            f"function {fid('show')}",
            f"function {fid('stats')}",
            *changed,
            *held,
            f"function {fid('intake')}",
        ],
    )

    # -- what is lent, and to whom (every second)
    def lend(kind: str, item: str, count: int) -> str:
        have = fittings.lent_predicate(KEYS[kind])
        return (
            f"execute unless items entity @s container.* {have} "
            f"unless items entity @s weapon.* {have} run give @s {item} {count}"
        )

    for kind in ("both", "brass", "copper"):
        others = [k for k in ("both", "brass", "copper") if k != kind]
        pack.function(
            f"{base}/kit/{kind}",
            [
                *(fittings.take_back_line(KEYS[k]) for k in others),
                lend(kind, pipe_item(kind), 64),
            ],
        )
    a, b_ = ROLE["brass"], ROLE["copper"]
    pack.function(
        f"{base}/kit",
        [
            f"execute if score {_s('form')} matches 1 run function {fid('kit/both')}",
            f"execute if score {_s('form')} matches 2 if entity @s[tag={a}] "
            f"run function {fid('kit/brass')}",
            f"execute if score {_s('form')} matches 2 if entity @s[tag={b_}] "
            f"run function {fid('kit/copper')}",
            lend("wrench", wrench_item(), 1),
        ],
    )
    # a role for one who has none: whichever kind fewer hold, brass first
    pack.function(
        f"{base}/role",
        [
            f"execute store result score {_s('na')} if entity {bodies},tag={a}]",
            f"execute store result score {_s('nb')} if entity {bodies},tag={b_}]",
            f"execute if score {_s('na')} <= {_s('nb')} run tag @s add {a}",
            f"execute if score {_s('na')} > {_s('nb')} run tag @s add {b_}",
        ],
    )
    for metal, other in (("brass", "copper"), ("copper", "brass")):
        pack.function(
            f"{base}/bay/{metal}",
            [
                f"tag @s remove {ROLE[other]}",
                f"execute unless entity @s[tag={ROLE[metal]}] run "
                + say(f"You take the {metal}-flange pipe.", "gray", "@s"),
                f"tag @s add {ROLE[metal]}",
            ],
        )
    # the form taken up: between two lengths, and only in what is carried
    pack.function(
        f"{base}/form/take",
        [
            _op("form", "=", "#gear.want"),
            f"execute if score {_s('form')} matches 1 run "
            + say("One engineer: your pipe grips both metals of the track."),
            f"execute if score {_s('form')} matches 2 run "
            + say(
                "Two engineers: one of you has brass pipe, one copper. Each "
                "grips its own metal. Change at the pipe store's bays."
            ),
        ],
    )
    pack.function(f"{base}/book", [_setblock(place.lectern, logbook(fr))])
    bays = [
        f"execute if score {_s('form')} matches 2 "
        f"if block {_xyz(cell)} {PLATE}[powered=true] "
        f"as @e[tag=st.in,{dp.box_selector(cell, cell)}] "
        f"run function {fid(f'bay/{metal}')}"
        for metal, cell in place.bays.items()
    ]
    pack.function(
        f"{base}/second",
        [
            _set("sec", 0),
            f"execute unless score {_s('want')} matches 1..2 run {_set('want', 1)}",
            f"execute unless score {_s('form')} = {_s('want')} "
            f"run function {fid('form/take')}",
            *(
                f"execute if score {_s('form')} matches 1 run tag {bodies}] remove {tag}"
                for tag in ROLE.values()
            ),
            f"execute if score {_s('form')} matches 2 as {bodies},tag=!{a},tag=!{b_}] "
            f"run function {fid('role')}",
            f"execute as {here} run function {fid('kit')}",
        ],
    )

    # -- the hooks
    pack.function(
        f"{base}/tick",
        [
            # the decoration, whether or not there is a puzzle
            f"function {fid('decor/beat')}",
            # the clutch, once thrown, latches: the gear is never turned
            # back under laid pipe
            fittings.lever_hold_line(
                place.lever, lever_on, f"if score {_s('gear')} matches 1.."
            ),
            # the logbook put back, solved or not
            f"execute if block {_xyz(place.lectern)} minecraft:lectern[has_book=false] "
            f"run function {fid('book')}",
            f"execute unless score {open_dome} matches 1 run return 0",
            # a room never set up has no reach: no steam at all
            f"execute unless score {_s('n')} matches 1.. run function {fid('arm')}",
            *clutch,
            *(hint.tick for hint in hints.values()),
            f"scoreboard players add {_s('tick')} 1",
            f"execute if score {_s('tick')} matches {STEP}.. "
            f"run function {fid('step')}",
            # a step that solved the room lends nothing more
            f"execute unless score {open_dome} matches 1 run return 0",
            # a bay is read every tick: one walked over is taken up
            *bays,
            f"scoreboard players add {_s('sec')} 1",
            f"execute if score {_s('sec')} matches 20.. run function {fid('second')}",
        ],
    )
    sign = _xyz(place.plaque_sign)
    reaches = sorted({scaled(level)["n"] for level in game.LEVELS})
    pack.function(
        f"{base}/arm",
        [
            f"function {fid('scale')}",
            *(
                f"execute if score {_s('n')} matches {n} run data merge block {sign} "
                f"{{{fittings.sign_text(plaque_signs(n)[2])}}}"
                for n in reaches
            ),
            # (a score never set matches nothing: the gear as found)
            *(
                f"execute unless score {_s(score)} matches 0.. run {_set(score, 0)}"
                for score in ("gear", "turn")
            ),
            # the steam starts from the chest: what is laid fills again
            f"function {fid('dark')}",
            *(hint.arm for hint in hints.values()),
            _set("live", 1),
        ],
    )
    pack.function(
        f"{base}/enter",
        [
            # the core's signal: the first into an empty room
            f"execute {unsolved} if score #first {OBJ} matches 1 "
            f"run function {fid('arm')}",
            f"execute {unsolved} run tellraw @s "
            '{text:"You take a wrench and a bundle of pipe from the rack.",'
            'color:"gray",italic:true}',
        ],
    )
    pack.function(f"{base}/solo", [_set("want", 1)])
    pack.function(f"{base}/duo", [_set("want", 2)])
    pack.function(
        f"{base}/leave",
        [
            *(fittings.take_back_line(key) for key in KEYS.values()),
            *(f"tag @s remove {tag}" for tag in ROLE.values()),
        ],
    )
    pack.function(
        f"{base}/empty",
        [
            # the pipe stays where it was laid; the steam is let out of it
            f"execute {unsolved} run function {fid('dark')}",
            _set("live", 0),
        ],
    )
    # everything as built: all pipe up (and any pipe anywhere in the dome)
    lo, hi = domes.box(dome)
    mid_y = (lo[1] + hi[1]) // 2
    zeroed = ("far", "spent", "sink", "gear", "turn", "tick", "sec", "live", "cut")
    pack.function(
        f"{base}/reset",
        [
            # (nothing broken drops: block_drops is off; this is kit thrown
            # down and left lying)
            *(
                f"kill @e[type=minecraft:item,{domes.sphere(dome)},"
                f'nbt={{Item:{{id:"{item}"}}}}]'
                for item in (PIPE, WRENCH)
            ),
            dp.fill(lo, (hi[0], mid_y, hi[2]), AIR, f"replace {PIPE}"),
            dp.fill((lo[0], mid_y + 1, lo[2]), hi, AIR, f"replace {PIPE}"),
            *(_set(f"c{i}", 0) for i, ln in enumerate(every) if ln.laid),
            *(_set(f"c{i}", 1) for i, ln in enumerate(every) if not ln.laid),
            *(_set(score, 0) for score in zeroed),
            _set("far.shown", -1),
            _set("form", 1),
            _set("want", 1),
            # the Great Gear across, the clutch out and its lamps dark
            *(_setblock(cell, CUT) for cell, _ in along),
            *(_setblock(cell, block) for cell, block in across),
            f"function {fid('turn/teeth_0')}",
            *fittings.lever_put_lines(place.lever, place.lever_off),
            *(_setblock(c, f"{LAMP}[lit=false]") for c in place.clutch_lamps),
            f"function {fid('scale')}",
            f"data merge block {sign} "
            f"{{{fittings.sign_text(plaque_signs(scaled(game.DEFAULT_LEVEL)['n'])[2])}}}",
            f"function {fid('dark')}",
            *(f"tag @e[tag={tag}] remove {tag}" for tag in ROLE.values()),
            *(fittings.take_back_line(key, game.PLAYERS) for key in KEYS.values()),
            f"function {fid('book')}",
        ],
    )


# --------------------------------------------------------------- the check

S1, S2, S3 = "st.g1", "st.g2", "st.g3"


def check(ctx: Any) -> list[str]:
    """
    Work the Gearworks in place over RCON. A player is stood in for by an
    armour stand that the core counts (``game.STANDIN``): it is put at the
    entrance to come in and, with a body, on a bay's plate; pipe is laid
    and taken up by ``setblock`` as a hand would leave it, the clutch
    thrown by setting the lever. Leaves the room and its tunnel reset,
    dome 2 as it was found and no stand-in behind.

    What stand-ins cannot prove, and this does not: that the pipe in a
    real adventure-mode hand sticks to the track and to nothing else, each
    duo kind to its own metal; that the wrench breaks pipe and nothing
    else; anything about the kit (``give``, ``clear`` and the item tests
    are aimed at players: a stand-in has no inventory, so only their
    loading is known); a real weight on a bay's plate; a hand on the
    lever (its lamps are lit by the function here, since a lever set by
    command tells nothing round it); standing on the Great Gear as its track
    is swapped; titles, chat, sounds, particles, the board and the signs
    as a player reads them; the recall's teleport.
    """
    game_checks.no_run(ctx)
    dome = ctx.layout.DOMES[INDEX]
    tunnel = ctx.layout.TUNNELS[INDEX]
    place = room(dome)
    fr = place.frame
    every = lengths(dome)
    problems: list[str] = []
    scan = game_checks.SCAN
    base = f"dome/{INDEX}"
    short, round_ = line_to_pump(dome, True), line_to_pump(dome, False)
    lever_on = lever_block(fr, True)

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def get(score: str) -> int:
        return ctx.score(f"#gear.{score}") or 0

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
        ctx.advance(22)  # a second's beat: the form is taken up

    def lay(numbers: Iterable[int]) -> set[int]:
        """pipe put down as a hand would leave it; gives what was laid"""
        laid = {i for i in numbers if every[i].laid}
        for i in sorted(laid):
            ctx.setblock(every[i].cell, f"{PIPE}[lit=false]")
        return laid

    def take_up(numbers: Iterable[int]) -> None:
        for i in numbers:
            ctx.setblock(every[i].cell, AIR)

    def creep(lengths_: int = ROUTE + 20) -> None:
        """long enough for the steam to creep that many lengths"""
        ctx.advance(STEP * lengths_ + 4 * STEP)

    def steam_is(what: str, laid: set[int], along: bool) -> None:
        """every length lit or dark as the rule of steam says, and the
        board's numbers with them"""
        n = get("n")
        want = steam(dome, laid, along)
        wrong = []
        for i, ln in enumerate(every):
            there = not ln.laid or i in laid
            if ln.line and ln.line != (ALONG if along else ACROSS):
                there = False
            lit = "true" if want.get(i, BIG) <= n else "false"
            block = f"{PIPE if ln.laid else BUILT}[lit={lit}]" if there else AIR
            if not ctx.is_block(ln.cell, block):
                wrong.append((ln.part, ln.cell, block))
        if wrong:
            problems.append(f"{what}: {len(wrong)} lengths wrong: {wrong[:4]}")
        within = [d for d in want.values() if d <= n]
        got = {s: get(s) for s in ("far", "spent")}
        spent = int(any(d > n for d in want.values()))
        expect(
            f"{what}: the board's scores",
            got,
            {"far": max(within, default=0), "spent": spent},
        )

    def intake_lit() -> int:
        return sum(ctx.is_block(c, INTAKE_LIT) for c in place.intake)

    def throw_clutch() -> None:
        """the lever set over, and the turn waited out"""
        ctx.setblock(place.lever, lever_on)
        ctx.advance(TURN_TICKS + 6)

    def as_built(what: str) -> None:
        """every block of the room is as ``reset`` leaves it (a block of
        the tappets, and bars: by name; a block the decoration steps: one
        of its two), and the scores with it"""
        b = room_blocks(dome)
        wrong = []
        for cell, block in b.everything().items():
            if cell in b.either:
                ok = any(ctx.is_block(cell, name(x)) for x in b.either[cell])
            elif cell in b.moving:
                # (a tappet caught in mid stroke reads as a ``moving_piston``)
                ok = ctx.is_block(cell, name(block)) or ctx.is_block(
                    cell, "minecraft:moving_piston"
                )
            elif name(block) == BARS:
                ok = ctx.is_block(cell, name(block))
            else:
                ok = ctx.is_block(cell, block.partition("{")[0])
            if not ok:
                wrong.append(cell)
        # (not ``swept``: the tappets' heads are out half the time)
        wrong += [c for c in b.clear if not ctx.is_block(c, AIR)]
        if wrong:
            problems.append(f"{what}: {len(wrong)} blocks not as built: {wrong[:6]}")
        names = ("far", "spent", "sink", "gear", "turn", "live")
        expect(
            f"{what}: the scores", {s: get(s) for s in names}, dict.fromkeys(names, 0)
        )
        tagged = sum(ctx.count(f"@e[tag={tag}]") for tag in ROLE.values())
        expect(f"{what}: roles left on anyone", tagged, 0)

    def solved() -> bool:
        return ctx.score(f"#d{INDEX}") == 2

    def unsolve() -> None:
        """the room and its tunnel put back, the dome open and unsolved"""
        ctx.function(f"tunnel/{INDEX}/reset")
        ctx.function(f"{base}/reset")
        ctx.set_score(f"#d{INDEX}", 1)
        ctx.set_score(f"#d{INDEX + 1}", saved[f"#d{INDEX + 1}"] or 0)
        ctx.set_score("#solved", saved["#solved"] or 0)

    def tappets_run(what: str) -> None:
        """the tappets, which nothing starts or stops: each piston seen
        out and in over 6 s"""
        seen: list[set[bool]] = [set() for _ in place.tappets.pistons]
        for _ in range(30):
            ctx.advance(4)
            for cell, states in zip(place.tappets.pistons, seen, strict=True):
                states.add(ctx.is_block(cell, "minecraft:piston[extended=true]"))
        if any(states != {True, False} for states in seen):
            problems.append(f"{what}: the tappets' pistons, out or in: {seen}")

    # ---- before: nobody about, the room and its tunnel reset, the dome open
    others = [f"#d{d.index}" for d in ctx.layout.DOMES if d.index != INDEX]
    others += [f"#t{t.index}" for t in ctx.layout.TUNNELS if t.index != INDEX]
    # (``#t2`` is left to the tunnel's reset, which leaves it shut)
    names = (f"#d{INDEX}", f"#d{INDEX + 1}", "#solved")
    saved = game_checks.scores(ctx, *names)
    at_level = game_checks.save_level(ctx)
    elsewhere = game_checks.scores(ctx, *others)
    for tag in (S1, S2, S3):
        ctx.cmd(f"kill @e[tag={tag}]")
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan)
    if (count := ctx.score("#players")) or ctx.score(f"#form{INDEX}"):
        return [f"{count} players or stand-ins of another check are in the game"]
    unsolve()
    ctx.advance(scan)
    as_built("built")
    tappets_run("nobody in")
    for what, selector, want in (
        ("recall button", f"@e[type=minecraft:interaction,tag={ENTITY_TAG}]", 1),
        ("steam board", f"@e[type=minecraft:text_display,tag={BOARD_TAG}]", 1),
        ("text displays", f"@e[type=minecraft:text_display,tag={ENTITY_TAG}]", 2),
    ):
        expect(f"the room's entities: {what}", ctx.count(selector), want)
    if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("the logbook is not on the lectern")
    frames = {get("frame")}
    ctx.advance(3 * DECOR_AT)
    frames.add(get("frame"))
    expect("the decoration with nobody in: its frames", len(frames), 1)

    # ---- solo, the success path: in, the chest's feed, the clutch, the line
    stand(S1, entrance)
    ctx.advance(22)
    got = {s: get(s) for s in ("live", "form", "gear")}
    expect("solo, entered", got, {"live": 1, "form": 1, "gear": 0})
    level = ctx.score("#active") or game.DEFAULT_LEVEL
    expect("the level's reach", get("n"), scaled(level)["n"])
    board = f"entity {fittings.display_selector(BOARD_TAG)} text"
    if str(get("n")) not in ctx.data(board):
        problems.append(f"the steam board does not name the reach: {ctx.data(board)}")
    # the decoration runs while someone is in
    seen = set()
    for _ in range(10):
        ctx.advance(DECOR_AT)
        seen.add(get("frame"))
    expect("the decoration with someone in: frames seen", len(seen) >= 4, True)
    # the chest's feed: it lights, and riser 1 with it
    laid = lay(part(dome, "chest"))
    creep(15)
    steam_is("the chest's feed laid", laid, False)
    # on to the gear, which lies across: the steam stops at its edge
    laid |= lay(i for i in short if every[i].part in ("ring", "back"))
    creep(30)
    steam_is("laid to the gear's edge", laid, False)
    expect("the gear's hint counting", (ctx.score(f"#hint{INDEX}.gear") or 0) > 0, True)
    # pipe on the gear as found is thrown off when the clutch is thrown
    stray = lay(part(dome, "across")[:3])
    ctx.advance(4 * STEP)
    throw_clutch()
    expect("the clutch thrown: the gear", get("gear"), 2)
    gone = [ctx.is_block(every[i].cell, AIR) for i in stray]
    expect("pipe on the gear thrown off by the turn", all(gone), True)
    track = [ctx.is_block(c, b) for c, b in place.gear_track[ALONG]]
    track += [ctx.is_block(c, CUT) for c, _ in place.gear_track[ACROSS]]
    expect("the gear's track along, and taken up across", all(track), True)
    lamps = [ctx.is_block(c, f"{LAMP}[lit=true]") for c in place.clutch_lamps]
    expect("the clutch's lamps", lamps, [True, True])
    # the clutch latches: put back by hand, it is held over
    ctx.setblock(place.lever, place.lever_off)
    ctx.advance(3)
    expect("the lever held over", ctx.is_block(place.lever, lever_on), True)
    expect("the gear after the lever was put back", get("gear"), 2)
    # the rest of the short way: the lamps count, the dome is solved
    laid |= lay(short)
    most = 0
    for _ in range(120):
        most = max(most, intake_lit()) if not solved() else most
        if solved():
            break
        ctx.advance(4)
    expect("solo: solved by the short way", solved(), True)
    expect("the intake's lamps seen counting", most >= 1, True)
    expect("solved: the intake's lamps", intake_lit(), INTAKE_LAMPS)
    expect("solved: the room no longer live", get("live"), 0)
    expect("tunnel 2 at the solve", ctx.score(f"#t{INDEX}") in (1, 2), True)
    ctx.advance(tunnels.event_ticks(tunnel) + 60)
    got = game_checks.scores(ctx, f"#t{INDEX}", f"#d{INDEX + 1}")
    expect("tunnel 2 open, dome 3 open", got, {f"#t{INDEX}": 2, f"#d{INDEX + 1}": 1})
    doors = [c for d in tunnels.ends(tunnel) for _, c in domes.door_cells(d, tunnel)]
    expect("door cells open", sum(ctx.is_block(c, AIR) for c in doors), len(doors))
    problems += [f"tunnel open: {p}" for p in domes.check_shell(ctx, dome, False)]
    # the works awake: the Great Gear's teeth seen in both sets
    tooth, sets = place.teeth[0][0], set()
    for _ in range(12):
        ctx.advance(DECOR_AT // (DECOR_SOLVED + 1))
        sets.add(ctx.is_block(tooth, TOOTH[0]))
    expect("solved: the gear's teeth in both sets", sets, {True, False})
    # a second entry leaves a solved room solved, its pipe lit as it lies
    come_in()
    expect("solved, entered again: the dome", ctx.score(f"#d{INDEX}"), 2)
    expect("solved, entered again: set up anew", get("live"), 0)
    lit = sum(
        ctx.is_block(every[i].cell, f"{PIPE}[lit=true]") for i in short if every[i].laid
    )
    expect("solved, entered again: the laid pipe lit", lit, TO_LAY)

    # ---- the limit: the way round the gallery falls short at this level
    unsolve()
    come_in()
    expect("unsolved, entered again: set up anew", get("live"), 1)
    n = get("n")
    laid = lay(round_)
    creep(len(round_) + 20)
    steam_is("the way round laid whole", laid, False)
    if n < len(round_):
        expect("the way round: the dome", solved(), False)
        expect("the way round: the intake", intake_lit(), 0)
        expect("the way round: the steam spent", get("spent"), 1)
        expect(
            "the short hint counting", (ctx.score(f"#hint{INDEX}.short") or 0) > 0, True
        )
        if "SPENT" not in ctx.data(board):
            problems.append(
                f"the board does not say the steam is spent: {ctx.data(board)}"
            )
        # the gentle rule: the short way laid as well, the long one left
        # where it lies, and it solves
        throw_clutch()
        laid |= lay(short)
        creep()
        ctx.advance(INTAKE_LAMPS * SINK_STEPS * STEP + 10)
        expect("the short way beside the long one: solved", solved(), True)

    # ---- a lit length taken out: dark beyond it, lit up to it, and back
    # (one length of the front bridge is left out all through, so that the
    # line is never whole before the end of the duo part)
    unsolve()
    come_in()
    throw_clutch()
    gap = next(i for i in short if every[i].part == "front")
    laid = lay(i for i in short if i != gap)
    creep()
    steam_is("the line laid but for one length", laid, True)
    cut = next(i for i in short if every[i].part == "back")
    take_up([cut])
    ctx.advance(3 * STEP)
    steam_is("a lit length taken out", laid - {cut}, True)
    lay([cut])
    creep()
    steam_is("the length put back", laid, True)
    expect("the line with a gap: the dome", solved(), False)

    # ---- leaving: the pipe is kept, the steam let out, and it fills again
    stand(S1, outside)
    ctx.advance(scan)
    stand(S1, entrance)  # out for a moment: nothing changes
    ctx.advance(scan)
    expect("out for a moment: the room", get("live"), 1)
    steam_is("out for a moment: the steam", laid, True)
    stand(S1, outside)
    ctx.advance(game_checks.EMPTY)
    kept = sum(ctx.is_block(every[i].cell, f"{PIPE}[lit=false]") for i in laid)
    expect("left empty: the pipe kept, and dark", kept, len(laid))
    expect("left empty: the gear still along", get("gear"), 2)
    expect("left empty: the scores", (get("live"), get("far")), (0, 0))
    stand(S1, entrance)
    creep()
    steam_is("back in: the steam fills what was laid", laid, True)
    expect("back in: unsolved still", solved(), False)

    # ---- duo: a kind each, the bays, and one leaving
    stand(S2, entrance)
    ctx.advance(scan + 22)
    expect("two in: the dome's form", ctx.score(f"#form{INDEX}"), 2)
    expect("two in: the form taken up", get("form"), 2)
    kinds = {tag: ctx.count(f"@e[tag={tag}]") for tag in ROLE.values()}
    expect("two in: one brass, one copper", kinds, dict.fromkeys(ROLE.values(), 1))
    steam_is("two in: the laid pipe untouched", laid, True)
    brass = S1 if ctx.count(f"@e[tag={S1},tag={ROLE['brass']}]") else S2
    stand(brass, middle(place.bays["copper"]))
    ctx.advance(45)  # the plate goes down within 15 ticks; then a second's beat
    kinds = {tag: ctx.count(f"@e[tag={tag}]") for tag in ROLE.values()}
    expect("a bay: both copper now", kinds, {ROLE["brass"]: 0, ROLE["copper"]: 2})
    stand(brass, middle(place.bays["brass"]))
    ctx.advance(45)
    expect(
        "the other bay: brass again",
        ctx.count(f"@e[tag={brass},tag={ROLE['brass']}]"),
        1,
    )
    stand(S3, entrance)
    ctx.advance(scan + 22)
    tagged = sum(ctx.count(f"@e[tag={tag}]") for tag in ROLE.values())
    expect("three in: all have a kind", tagged, 3)
    ctx.cmd(f"kill @e[tag={S3}]")
    stand(S2, outside)
    roles = sum(ctx.count(f"@e[tag={S2},tag={tag}]") for tag in ROLE.values())
    expect("one gone out: its role taken back", roles, 0)
    ctx.advance(scan)
    expect("within the fall-back time: still duo", get("form"), 2)
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan + 22)
    expect("one left: the dome's form", ctx.score(f"#form{INDEX}"), 1)
    expect("one left: the form", get("form"), 1)
    tagged = sum(ctx.count(f"@e[tag={tag}]") for tag in ROLE.values())
    expect("one left: no roles", tagged, 0)
    # the form changed under a half-laid line, and the one left finishes it
    lay([gap])
    creep()
    ctx.advance(INTAKE_LAMPS * SINK_STEPS * STEP + 10)
    expect("after one left: solved solo", solved(), True)

    # ---- the recall button: a click on it is taken up (by the core)
    click = f"@e[type=minecraft:interaction,tag={ENTITY_TAG},limit=1]"
    ctx.cmd(
        f"data modify entity {click} interaction set value "
        "{player:[I;1,2,3,4],timestamp:0L}"
    )
    ctx.advance(4)
    expect(
        "the recall button's click, 4 ticks on",
        ctx.data(f"entity {click} interaction"),
        "",
    )

    # ---- difficulty: the reach of the level, on a new entry
    for new in (game.LEVELS[0], game.LEVELS[-1]):
        unsolve()
        ctx.set_score("#level", new)
        come_in()
        want = scaled(new)["n"]
        expect(f"level {new}: the reach", get("n"), want)
        text = ctx.data(f"block {_xyz(place.plaque_sign)} front_text")
        if str(want) not in text:
            problems.append(f"level {new}: the plaque does not say {want}: {text}")
        if want >= len(round_):  # the plain way round works at this level
            lay(round_)
            creep(len(round_) + 20)
            ctx.advance(INTAKE_LAMPS * SINK_STEPS * STEP + 10)
            expect(f"level {new}: the way round alone solves", solved(), True)
        else:  # the short way, exact
            throw_clutch()
            lay(short)
            creep()
            ctx.advance(INTAKE_LAMPS * SINK_STEPS * STEP + 10)
            expect(f"level {new}: the short way solves", solved(), True)
    game_checks.restore_level(ctx, at_level)
    ctx.function("difficulty/apply")
    game_checks.restore_level(ctx, at_level)  # (apply lowers #run.level in a run)

    # ---- reset, from a scrambled state; and only this dome's
    unsolve()
    come_in()
    stand(S2, entrance)
    ctx.advance(scan + 22)
    lay(range(len(every)))  # pipe everywhere
    ctx.setblock(place.lectern, f"minecraft:lectern[facing={fr.facing(-1, 0)}]")
    ctx.advance(22)
    if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("a logbook taken from the lectern was not put back")
    stand(S2, middle(place.bays["brass"]))
    ctx.setblock(place.lever, lever_on)
    ctx.advance(TURN_TICKS // 2)  # the gear half way through its turn
    scrambled = (get("gear"), get("form"), get("far") > 0)
    expect("the room scrambled before the reset", scrambled, (1, 2, True))
    ctx.function(f"{base}/reset")
    ctx.set_score(f"#d{INDEX}", 0)  # locked, so that nothing runs after it
    ctx.advance(4)
    as_built("reset from a scrambled state")
    expect(
        "the reset left the other domes and tunnels",
        game_checks.scores(ctx, *others),
        elsewhere,
    )

    # ---- after: nobody, the tunnel shut and flooded, the dome dry
    for tag in (S1, S2, S3):
        ctx.cmd(f"kill @e[tag={tag}]")
    ctx.function(f"tunnel/{INDEX}/reset")
    for score in names:
        ctx.set_score(score, saved[score] or 0)
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan)
    ctx.function(f"{base}/reset")
    ctx.advance(100)
    as_built("left")
    tappets_run("left")
    got, want_counts = tunnels.counts(ctx, tunnel), tunnels.expected(tunnel, 0)
    expect("tunnel 2 left shut and flooded", got, want_counts)
    problems += [f"left: {p}" for p in domes.check_shell(ctx, dome, False)]
    left = sum(ctx.count(f"@e[tag={tag}]") for tag in (S1, S2, S3))
    expect("stand-ins left behind", left, 0)
    return problems


MODULE = game.Module(
    "gearworks",
    stages={f"dome_{INDEX}_inside": build},
    functions=functions,
    checks={"gearworks": check},
)
