"""
The inside of the start dome, the Pump House: the control room of the
station. The lift from the dock comes down in the middle; everything here
stands round it and leaves the walk from the lift to the outgoing airlock
clear.

**Where things are.** Positions are steps from the middle of the dome's
floor in a frame that turns with the layout: ``EAST`` is towards the
outgoing tunnel (tunnel 0), ``SOUTH`` the side of its mouth the pump engine
stands on, and the mouth the last tunnel returns by must be to the
``NORTH`` (the names are true of the layout's own site). ``at(e, n, h)``
gives a cell; a `Wall` gives the cells of a wall as a viewer facing it
sees them.

- **The master lever**, north of the east airlock, facing the lift: a real
  lever on a brass panel with four redstone lamps the lever itself lights.
- **The map wall**, across the south side: the ring as it lies when you
  face the wall (what is on your left on the map is to your left in the
  station), worked out from the layout by ``map_cells``. A sea of
  prismarine in a brass frame; standing out from it, each dome a disc of
  glass over copper of its own size with its state lamp in the middle
  (``DOME_LAMP``: dark locked, amber open, green restored), each tunnel a
  pipe of copper bulbs, lit when it is pumped dry and dimly (``READY``)
  while its pump waits for its lever, the shore as a corner
  of land with the row out to it, and a blinking pin over the Pump House:
  "you are here". Each dome's name stands in white over its middle, in
  front of its blocks; a title, a legend and which way is up are text.
- **The clock board**, the east wing of the map's bay: the run's time, the
  best time at the level in force, and the difficulty level.
- **The difficulty dial**, the west wing: ten lamps lit up to the level
  proposed, a brass pointer under the level that is set, two real buttons
  to lower and raise the proposal and a third to confirm it.
- **The reset cabinet**, north west and away from everything else: a
  button behind a copper door that must be opened first.
- **The briefing**, north east of where players arrive: a brass plaque and
  the last engineer's log on a lectern.
- **The Wall of Fame**, the west wall: ``TROPHY`` blocks (used nowhere
  else in the station, so a sign that goes only on them goes only here),
  which the reset leaves alone, and the build too.
- **The trophy dispenser**, in the wall's brass border at its north end
  (the end nearest the door the way home comes in by): a dispenser at
  eye height, a copper bulb over it that is lit while a trophy waits, a
  text display ("YOUR TROPHY") and a button under it. See "The trophy".
- **The sealed door** in the north: the last tunnel's mouth, dressed and left
  shut.
- **The arrival point**: a brass pad round ``domes.entrance``, where the
  recall and a respawn put a player.

**The upper level and the machinery** (``dressing``; none of it is an
input, and no reset touches it):

- **The gallery**: a deck of copper grate at ``DECK``, railed, round the
  north of the dome, with stairs up from the floor, and a bridge from it
  to a look-out beside the lift's shaft (``gallery``).
- **Two tanks** behind the wings of the map's bay, each with a sight glass
  whose level rises and falls, and **pipes overhead** from each tank and
  from over the north door to the shaft, with bulbs that light in turn
  towards it and lanterns hung under their joints (``overhead``).
- **The governor**, north east (in the north west it hid the Wall of
  Fame), in a cage of copper bars with a grate for a roof: a clock of
  repeaters round a redstone torch that works two pistons, two lamps and
  a copper bulb, by itself, from the moment it is built. Nothing of it can be reached or clicked.
- The chase, the tanks' levels, the map's blinking pin and a bell every
  minute and a half are the datapack's (``dome/0/machine/...``), stepped
  by ``dome/0/tick``: they stand still when nobody is in the dome.

``walk_problems`` is the test, on the plan alone, that the way is clear
from where a player arrives and from every side of the shaft to the east
mouth, to every input, to the Wall of Fame and up to the gallery.

Not this module's: the 5 x 5 column in the middle (the lift,
``lift_column``) and ``tunnels.reserved_cells``. ``blocks`` refuses a
plan that uses either.

**Who pressed.** The lever and the dial's two step buttons are real blocks
that ``dome/0/tick`` reads (it runs every tick while a player in the game
is in the dome): what they do does not depend on who used them. The
confirm and reset buttons do: a vote is counted by player. Over each
is an ``interaction`` entity, which records the player who right-clicked
it; the tick finds one that has been clicked and runs the vote function
``on target``: as that player, whoever else stands near. The button under
it is pressed for show. (A real button tells a function only that it was
pressed, not by whom, and the nearest player to it is the wrong one as
soon as two stand at the same button to confirm a vote.) The functions a
click ends in are ``dome/0/press/confirm``, ``dome/0/press/reset`` and
``dome/0/press/trophy``: run as a player in the game.

**Fast travel.** A sign on the map's left corner post (``TRAVEL_SIGN``)
says what it is. Over each dome of the map but the Pump House stands an
invisible ``interaction`` entity a column of its disc (``travel_boxes``),
just proud of the glass. Those of the upper row reach down to the top of
the lower row, so a player standing at the map reaches every dome
(``REACH``). A click runs ``dome/0/travel/<n>`` as the player who
clicked, and only them: once the run is on, with no reset being voted on,
if dome n is restored, or open with someone in it already (a late
arrival joins the team), they are put on its entrance spot with a puff of
particles and a chime; otherwise they are told why not. Nothing else is
done to them: the next scan finds them in dome n as if they had walked in
(respawn point, title, kits, the dome's ``enter`` hook), as for the
recall.

**The trophy.** At the win (``dome/0/trophy/arm``, a ``wins`` function of
the core) every player in the game (and stand-in) is owed a trophy: tag
``DUE`` and the run's number in ``TROPHY_RUN``; the trophy's name ("Trophy:
level 5 in 14:05") is kept in storage ``TROPHY_STORE``; the dispenser's
bulb is lit, its display says "YOUR TROPHY", and five seconds later a
title says "Your trophy waits by the Wall of Fame". A player owed one who
presses the button gets one bamboo sign, placeable only on ``TROPHY``,
its lore saying so, thrown out of the dispenser's mouth as an item that
only they can pick up and that never despawns; the tag goes, so it is one
a player a run. Someone not owed one (a late joiner, a second press, an
old run's tag) is told so. ``#ph.trophy`` (``ARMED``) is 1 while anyone in
the game is still owed one, and the bulb and the display follow it.

The dispenser itself is always empty: the sign is made when the button is
pressed, never stored. In adventure mode a dispenser can still be opened,
so a stocked one could be emptied by hand and its stock farmed; an empty
one has nothing to take, and the button can only make the presser's own.
(The button is pressed for show under an interaction entity, like the
vote's; if a real press reaches the dispenser it fires an empty one.) The
reset kills uncollected trophies by their tag, takes the tags and puts
the bulb out; it never touches the Wall's blocks or the signs on them.

**Functions** (all under ``dome/0/``): ``tick`` and ``reset`` are the
core's hooks. ``show`` writes the map, the dial and the boards from the
scores, at any time; ``tick`` calls it twice a second, the reset a tick
after the scores are zeroed, and the build when it has finished. The
dial's proposal is the score ``#ph.dial``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cache
from typing import Any

import datapack as dp
import domes
import fittings
import game
import game_checks
import station_layout as layout
import tunnels
from domes import AIR, Cell

Vec = tuple[int, int]

DOME = layout.START
N = DOME.index
OUT = layout.TUNNELS[N]
BACK = next(t for t in layout.TUNNELS if t.end == N)

# the frame: unit steps (x, z), named for the layout's own site
EAST: Vec = domes.outward(DOME, OUT)
SOUTH: Vec = domes.across(EAST)  # the engine's side of the outgoing mouth
NORTH: Vec = (-SOUTH[0], -SOUTH[1])
WEST: Vec = (-EAST[0], -EAST[1])
if domes.outward(DOME, BACK) != NORTH:
    raise ValueError(
        "the Pump House is laid out for a ring whose last tunnel returns "
        "on the side of the outgoing mouth away from its engine"
    )

OBJ = game.OBJ
TAG = "st.ph"  # every entity of this module
STORE = "station:start"
DIAL = "#ph.dial"

BRASS = "minecraft:gold_block"
COPPER = "minecraft:waxed_cut_copper"
PLATE = "minecraft:waxed_copper_block"
DARK = "minecraft:polished_blackstone"
PIPE = "minecraft:waxed_lightning_rod"
#: the trophy wall's block: nothing else in the station is made of it
TROPHY = "minecraft:gilded_blackstone"
#: the trophy sign, and what is kept of it (see "The trophy")
SIGN = "minecraft:bamboo_sign"
DUE = "st.trophy"  #: tag: owed a trophy
TROPHY_RUN = "st.trophyrun"  #: objective: the run the trophy is owed for
ARMED = "#ph.trophy"
TROPHY_STORE = "station:game trophy"
ITEM_TAG = "st.ph.sign"  #: a trophy thrown out and not picked up
LORE = ("Place on the Wall of Fame (gilded blackstone)", "in the Pump House.")
#: a dome's lamp on the map, by its score: locked, open, solved
DOME_LAMP = (
    "minecraft:redstone_lamp",
    "minecraft:ochre_froglight",
    "minecraft:verdant_froglight",
)
GRATE = "minecraft:waxed_copper_grate"
BARS = "minecraft:waxed_copper_bars"
GLASS = "minecraft:glass"
#: the map's sea, and the land at its edge
SEA = ("minecraft:dark_prismarine", "minecraft:prismarine_bricks")
SAND, GRASS, JETTY = (
    "minecraft:sandstone",
    "minecraft:moss_block",
    "minecraft:oak_planks",
)
#: the "you are here" pin on the map blinks between these
PIN = ("minecraft:pearlescent_froglight", "minecraft:red_concrete")
BULB = "minecraft:waxed_copper_bulb"
LIT, UNLIT = f"{BULB}[lit=true]", f"{BULB}[lit=false]"
#: a tunnel's pipe on the map while its pump waits for its lever
READY = f"{tunnels.LAMP_DIM}[lit=true]"
LAMP = "minecraft:redstone_lamp"
BUTTON = "minecraft:polished_blackstone_button"
DOOR = "minecraft:waxed_copper_door"

_COMPASS = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}
_YAW = {(0, 1): 0, (-1, 0): 90, (0, -1): 180, (1, 0): -90}


def at(e: int, n: int, h: int = 0) -> Cell:
    """the cell e steps east and n north of the middle of the floor, h up
    (0 is the floor itself, 1 where feet are)"""
    x, y, z = DOME.floor_centre
    return (x + e * EAST[0] + n * NORTH[0], y + h, z + e * EAST[1] + n * NORTH[1])


@dataclass(frozen=True)
class Wall:
    """An upright wall one block thick, as a viewer facing it sees it:
    column 0 is on the viewer's left, height 1 stands on the floor."""

    left: tuple[int, int]  #: e, n of column 0
    face: Vec  #: the step from the wall towards the viewer
    width: int
    height: int

    @property
    def right(self) -> Vec:
        """the step from a column to the one on its right"""
        return domes.across((-self.face[0], -self.face[1]))

    def cell(self, k: int, h: int) -> Cell:
        x, y, z = at(*self.left, h)
        return (x + k * self.right[0], y, z + k * self.right[1])

    def front(self, k: int, h: int, depth: int = 1) -> Cell:
        """the cell in front of a block of the wall (``depth`` steps)"""
        x, y, z = self.cell(k, h)
        return (x + depth * self.face[0], y, z + depth * self.face[1])

    def cells(self, ks=None, hs=None) -> set[Cell]:
        ks = range(self.width) if ks is None else ks
        hs = range(1, self.height + 1) if hs is None else hs
        return {self.cell(k, h) for k in ks for h in hs}

    def border(self) -> set[Cell]:
        """the outermost blocks: both ends and the top row"""
        return self.cells(ks=(0, self.width - 1)) | self.cells(hs=(self.height,))

    def spot(self, k: float, y: float, out: float = 0.52) -> tuple[float, ...]:
        """a point just off the wall's face: k blocks from the left edge of
        column 0, y above the floor block's y"""
        x, y0, z = self.cell(0, 0)
        r, f = self.right, self.face
        return (
            x + 0.5 + (k - 0.5) * r[0] + out * f[0],
            y0 + y,
            z + 0.5 + (k - 0.5) * r[1] + out * f[1],
        )


# The walls. The map's bay: the map across the south, the clock board and
# the dial as wings at its ends.
MAP = Wall((12, -15), NORTH, 25, 13)
CLOCK = Wall((13, -3), WEST, 12, 6)
DIAL_WALL = Wall((-13, -14), EAST, 12, 6)
FAME = Wall((-19, -6), EAST, 17, 7)
PANEL = Wall((22, 6), WEST, 3, 4)  # the master lever's
PLAQUE = Wall((8, 5), SOUTH, 3, 3)  # the briefing's
CABINET = Wall((-10, 16), SOUTH, 5, 4)  # the back of the reset cabinet

LEVELS = tuple(game.LEVELS)
#: the dial: the column of each level's lamp, the rows of the lamps and of
#: the pointer under them, and the buttons' columns
LAMP_ROW, POINTER_ROW, BUTTON_ROW = 4, 3, 2
DOWN_K, UP_K, CONFIRM_K = 2, 5, 9

LEVER = PANEL.front(1, 2)
PANEL_LAMPS = (
    PANEL.cell(0, 2),
    PANEL.cell(2, 2),
    PANEL.cell(1, 1),
    PANEL.cell(1, 3),
)
DOWN, UP, CONFIRM = (DIAL_WALL.front(k, BUTTON_ROW) for k in (DOWN_K, UP_K, CONFIRM_K))
RESET = CABINET.front(2, 2)  # the reset button, in its cupboard
# the trophy dispenser: the Wall of Fame's north border column
PRIZE_K = FAME.width - 1
DISPENSER = FAME.cell(PRIZE_K, 3)
PRIZE_LAMP = FAME.cell(PRIZE_K, 4)
PRIZE_BUTTON = FAME.front(PRIZE_K, 2)
LECTERN = PLAQUE.front(1, 1)


def _state(block: str, **states: str) -> str:
    return f"{block}[{','.join(f'{k}={v}' for k, v in states.items())}]"


def lever(powered: bool) -> str:
    return _state(
        "minecraft:lever",
        face="wall",
        facing=_COMPASS[PANEL.face],
        powered=str(powered).lower(),
    )


def button(wall: Wall, powered: bool = False) -> str:
    return _state(
        BUTTON, face="wall", facing=_COMPASS[wall.face], powered=str(powered).lower()
    )


def door(half: str, open_: bool = False) -> str:
    """the reset cabinet's door: shut, it stands at the front of its cell,
    a whole cell in front of the button's"""
    back = (-CABINET.face[0], -CABINET.face[1])
    return _state(
        DOOR, half=half, facing=_COMPASS[back], hinge="left", open=str(open_).lower()
    )


def door_cells() -> tuple[Cell, Cell]:
    """the cabinet door's lower and upper cells"""
    return CABINET.front(2, 1, 2), CABINET.front(2, 2, 2)


# ------------------------------------------------------------------------ cells


def lift_column() -> set[Cell]:
    """the 5 x 5 column in the middle of the dome, floor to top: the lift's"""
    return {
        at(e, n, h)
        for e in range(-2, 3)
        for n in range(-2, 3)
        for h in range(DOME.radius + 1)
    }


@cache
def free_cells() -> frozenset[Cell]:
    """the cells inside the dome that this module may build in"""
    inside = domes.dome_cells(DOME).interior
    return frozenset(inside - tunnels.reserved_cells(DOME) - lift_column())


@dataclass(frozen=True)
class MapCells:
    """the map on the map wall, in the wall's columns and heights (k, h)"""

    scale: float  #: blocks of the station to a block of the map
    places: dict[int, tuple[int, int]]  #: dome index -> its middle
    shapes: dict[int, frozenset[tuple[int, int]]]  #: dome index -> its blocks
    lamps: dict[int, Cell]  #: dome index -> its state lamp (the middle)
    lines: dict[int, tuple[Cell, ...]]  #: tunnel index -> its pipe of bulbs
    pin: tuple[int, int]  #: "you are here": over the start dome (the dock)
    shore: frozenset[tuple[int, int]]  #: the land, in the corner it lies in
    route: tuple[tuple[int, int], ...]  #: the row from the dock to the shore


#: the part of the map wall the domes are drawn in: columns and heights
MAP_K, MAP_H = (2, 21), (2, 11)


def _disc(radius: float) -> set[tuple[int, int]]:
    reach = int(radius)
    return {
        (dk, dh)
        for dk in range(-reach, reach + 1)
        for dh in range(-reach, reach + 1)
        if dk * dk + dh * dh <= radius * radius
    }


@cache
def map_cells() -> MapCells:
    """
    The map, from the layout. Each dome is put where it lies for someone
    facing the wall (ahead is up, and right is right) and drawn as a disc
    of its own size, all at one scale: the largest at which the ring fits
    the wall with every tunnel at least a block long. A tunnel is the
    blocks between its two domes. The shore is far off the map at this
    scale, so it is a corner of land in the direction it lies in, with
    the row out to it from the dock over the start dome.
    """
    ahead = (-MAP.face[0], -MAP.face[1])
    right = MAP.right
    cx, cz = DOME.centre

    def seen(x: float, z: float) -> tuple[float, float]:
        dx, dz = x - cx, z - cz
        return dx * right[0] + dz * right[1], dx * ahead[0] + dz * ahead[1]

    points = {d.index: seen(*d.centre) for d in layout.DOMES}
    wide, high = MAP_K[1] - MAP_K[0] + 1, MAP_H[1] - MAP_H[0] + 1
    for step in range(24, 400):
        scale = step / 4
        places = {
            i: (round(x / scale), round(y / scale)) for i, (x, y) in points.items()
        }
        shapes = {
            d.index: {
                (places[d.index][0] + dk, places[d.index][1] + dh)
                for dk, dh in _disc(max(d.radius / scale, 1))
            }
            for d in layout.DOMES
        }
        drawn = set().union(*shapes.values())
        ks, hs = [k for k, _ in drawn], [h for _, h in drawn]
        if max(ks) - min(ks) >= wide or max(hs) - min(hs) >= high:
            continue
        if sum(len(shape) for shape in shapes.values()) != len(drawn):
            continue
        lines = {}
        for t in layout.TUNNELS:
            (k1, h1), (k2, h2) = places[t.start], places[t.end]
            if k1 == k2:
                run = [(k1, h) for h in range(min(h1, h2), max(h1, h2))]
            elif h1 == h2:
                run = [(k, h1) for k in range(min(k1, k2), max(k1, k2))]
            else:
                run = []
            lines[t.index] = [c for c in run if c not in drawn]
        if all(lines.values()):
            break
    else:
        raise ValueError("the map wall is too small for the ring")
    # the ring against the right and the bottom of its part of the wall
    dk, dh = MAP_K[1] - max(ks), MAP_H[0] - min(hs)

    def moved(cells) -> list[tuple[int, int]]:
        return [(k + dk, h + dh) for k, h in cells]

    places = dict(zip(places, moved(places.values()), strict=True))
    shapes = {i: frozenset(moved(shape)) for i, shape in shapes.items()}
    lines = {i: tuple(MAP.front(*c) for c in moved(line)) for i, line in lines.items()}
    drawn = set().union(*shapes.values())
    pin = (places[N][0], max(h for _, h in shapes[N]) + 1)
    # the shore: two by two in the corner of the wall it lies towards
    sx, sy = seen(layout.SHORE_LANDING[0], layout.SHORE_LANDING[2])
    inner_k, inner_h = (1, MAP.width - 2), (2, MAP.height - 1)
    k0 = inner_k[1] - 1 if sx > 0 else inner_k[0]
    h0 = inner_h[1] - 1 if sy > 0 else inner_h[0]
    shore = frozenset((k0 + i, h0 + j) for i in (0, 1) for j in (0, 1)) - drawn
    edge = min(k for k, _ in shore) if sx > 0 else max(k for k, _ in shore)
    row = range(pin[0] + 1, edge) if sx > 0 else range(edge + 1, pin[0])
    route = tuple((k, pin[1]) for k in row if (k, pin[1]) not in drawn | shore)
    return MapCells(
        scale,
        places,
        shapes,
        {i: MAP.front(*c) for i, c in places.items()},
        lines,
        pin,
        shore,
        route,
    )


def map_names() -> dict[int, tuple[float, float]]:
    """where each dome's name goes on the map, over the dome's middle block:
    the middle of its column along the wall and the height its text stands
    at (a little over the middle row's foot)"""
    return {i: (k + 0.5, h + 0.35) for i, (k, h) in map_cells().places.items()}


#: how far a survival or adventure player reaches an entity, from the eye
#: (the ``entity_interaction_range`` attribute's default), and the eye's
#: height over the feet
REACH, EYE = 3.0, 1.62
#: how far a fast-travel target stands out in front of the domes' glass
TRAVEL_PROUD = 0.05
#: the sign that says the map is for fast travel: on the corner post at
#: the map's left end, over a standing player's head
TRAVEL_SIGN = MAP.front(0, 3, 2)
TRAVEL_TEXT = ("FAST TRAVEL", "Click a lit", "dome on the map", "to go there.")


@cache
def travel_boxes() -> dict[int, tuple[tuple[tuple[float, float, float], int], ...]]:
    """
    The fast-travel targets: for each dome but the Pump House, an
    interaction entity on each column of its disc, a block wide, from
    just inside the glass to ``TRAVEL_PROUD`` in front of it (a player
    pressed against the glass never has an eye in one). Each is the
    middle of its base and its height. A dome of the lower row has them
    over its own rows; one of the upper row from the top of the lower row
    up, so that its lowest part is within ``REACH`` of a player standing
    at the map.
    """
    m = map_cells()
    upper = {i for i, (_, h) in m.places.items() if h > (MAP_H[0] + MAP_H[1]) / 2}
    lower_top = max(
        h for i, shape in m.shapes.items() if i not in upper for _, h in shape
    )
    out = {}
    for d in layout.DOMES:
        if d.index == N:
            continue
        shape = m.shapes[d.index]
        high = max(h for _, h in shape) + 1
        low = lower_top + 1 if d.index in upper else min(h for _, h in shape)
        out[d.index] = tuple(
            (MAP.spot(k + 0.5, low, 1 + TRAVEL_PROUD), high - low)
            for k in sorted({k for k, _ in shape})
        )
    return out


def dial_lamp(level: int) -> Cell:
    return DIAL_WALL.cell(level, LAMP_ROW)


def dial_pointer(level: int) -> Cell:
    return DIAL_WALL.cell(level, POINTER_ROW)


def trophy_cells() -> set[Cell]:
    """the Wall of Fame: the blocks a trophy sign will go on"""
    return FAME.cells(ks=range(1, FAME.width - 1), hs=range(1, FAME.height))


def sealed_door_cells() -> dict[Cell, str]:
    """the dressing of the north door: a heavy frame round the way in from
    the mouth (posts either side, an iron lintel over it), as much of it
    as is inside the dome"""
    free = free_cells()
    top = domes.DOOR_HEIGHT + 1
    side = domes.DOOR_HALF_WIDTH + 1
    reach = max(n for n in range(DOME.radius) if at(side, n, 1) in free)
    cells = {}
    for n in range(reach - 2, reach + 1):
        for e in range(-side, side + 1):
            cells[at(e, n, top)] = "minecraft:iron_block"
        for h in range(1, top + 1):
            cells[at(-side, n, h)] = cells[at(side, n, h)] = DARK
    return {c: b for c, b in cells.items() if c in free}


def sealed_lintel() -> Cell:
    """the block of the sealed door's lintel that carries its plaque: the
    middle one nearest the room"""
    top = domes.DOOR_HEIGHT + 1
    return next(
        at(0, n, top)
        for n in range(DOME.radius)
        if at(0, n, top) in sealed_door_cells()
    )


@cache
def floor_blocks() -> dict[Cell, str]:
    """the floor relaid: a plank floor in the map's bay, a copper walk from
    the lift to the east airlock, the arrival pad. The dome's lanterns,
    the lift's floor and the mouths' frames are left as they are"""
    floor: dict[Cell, str] = {}
    for e in range(-12, 13):
        for n in range(MAP.left[1] + 1, CLOCK.left[1]):
            floor[at(e, n)] = "minecraft:dark_oak_planks"
    for e in range(3, DOME.radius - 3):
        for n in (-1, 0, 1):
            floor[at(e, n)] = COPPER
    x, y, z, _ = domes.entrance(DOME)
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            floor[(x + dx, y - 1, z + dz)] = BRASS
    floor[(x, y - 1, z)] = "minecraft:waxed_chiseled_copper"
    keep = set(domes.light_cells(DOME)[0]) | lift_column()
    for tunnel in domes.touching(DOME):
        keep |= domes.frame_cells(DOME, tunnel)
    return {
        c: b
        for c, b in floor.items()
        if c in domes.dome_cells(DOME).floor and c not in keep
    }


# ---------------------------------------------------- the levels and the machines
# Dressing: a gallery with a bridge to the lift's shaft, two tanks, pipes
# overhead, and a caged machine that runs by itself. None of it is an input.

DECK = 6  #: the height of the gallery's deck (feet stand at DECK + 1)
STAIR_E, STAIR_N = (-5, -4), 6  #: the stairs: their columns, their first step
PIPES = 12  #: the height of the pipes overhead
TANK_AT = ((16, -10), (-16, -10))  #: the tanks' middles
TANK_TOP = 9
GAUGE = range(2, TANK_TOP)  #: the heights of a tank's sight glass
#: the cage round the governor: its corners (e, n), and its roof's height
CAGE = ((12, 5), (16, 15))
CAGE_ROOF = 5
REPEATERS = 5  #: a row of the governor's clock


#: the datapack's part of the machinery: ticks a step of the chase, steps
#: the chase rests between sweeps, steps between moves of the tanks'
#: levels, and steps between strokes of the bell (a minute and a half)
CHASE_TICKS, CHASE_REST, GAUGE_STEPS, BELL_STEPS = 5, 10, 6, 360
MACHINE_SCORES = ("#ph.m", "#ph.c", "#ph.gt", "#ph.g", "#ph.b", "#ph.pin")
#: the bell, under the west pipe: out of reach of the floor and the gallery
BELL = at(-9, 0, PIPES - 1)


def in_cage(e: int, n: int) -> bool:
    (e1, n1), (e2, n2) = CAGE
    return e1 <= e <= e2 and n1 <= n <= n2


@dataclass(frozen=True)
class Gallery:
    walk: frozenset[tuple[int, int]]  #: (e, n) of the deck to walk on
    rails: frozenset[tuple[int, int]]  #: the deck's edge, with a rail on it
    stairs: dict[tuple[int, int], int]  #: (e, n) -> the step's height
    posts: frozenset[tuple[int, int]]  #: rods from the floor to the deck


@cache
def gallery() -> Gallery:
    """the upper level: an arc of deck round the north of the dome, a
    bridge from it to a look-out beside the lift's shaft, and the stairs"""
    walk = set()
    for e in range(-DOME.radius, DOME.radius + 1):
        for n in range(DOME.radius + 1):
            r, angle = math.hypot(e, n), math.degrees(math.atan2(n, e))
            if 15.5 <= r < 18.5 and 35 <= angle <= 140:
                walk.add((e, n))
    walk |= {(e, n) for e in (-1, 0, 1) for n in range(4, 16)}  # the bridge
    walk |= {(e, n) for e in range(-2, 3) for n in (4, 5, 6)}  # the look-out
    top = STAIR_N + DECK - 1
    walk |= {(e, n) for e in STAIR_E for n in range(top + 1, top + 5)}  # the landing
    stairs = {(e, STAIR_N + i): 1 + i for e in STAIR_E for i in range(DECK)}
    deck = {(e + i, n + j) for e, n in walk for i in (-1, 0, 1) for j in (-1, 0, 1)}
    deck -= set(stairs)
    rails = deck - walk
    posts = {(e, n) for e in (-2, 2) for n in (9, 13)}
    for angle in (40, 60, 78, 102, 120, 140):
        a = math.radians(angle)
        spot = (round(19 * math.cos(a)), round(19 * math.sin(a)))
        if spot in rails and not in_cage(*spot):
            posts.add(spot)
    return Gallery(frozenset(walk), frozenset(rails), stairs, frozenset(posts))


def _bars(cells: set[Cell]) -> dict[Cell, str]:
    """copper bars in these cells, each joined to its neighbours among them"""
    out = {}
    for x, y, z in cells:
        joined = {
            name: str((x + dx, y, z + dz) in cells).lower()
            for (dx, dz), name in _COMPASS.items()
        }
        out[(x, y, z)] = _state(BARS, **joined)
    return out


def overhead() -> dict[str, tuple[Cell, ...]]:
    """the pipe runs overhead, each from its far end to the lift's shaft:
    one from each tank (up, along, and in), one from over the north door"""
    runs = {}
    for name, (e0, n0) in zip(("east", "west"), TANK_AT, strict=True):
        side = 1 if e0 > 0 else -1
        run = [at(e0, n, PIPES) for n in range(n0, 0)]
        run += [at(e, 0, PIPES) for e in range(e0, 2 * side, -side)]
        runs[name] = tuple(run)
    reach = max(n for n in range(DOME.radius) if at(0, n, PIPES) in free_cells())
    runs["north"] = tuple(at(0, n, PIPES) for n in range(reach - 1, 2, -1))
    return runs


def chase_cells() -> list[tuple[Cell, ...]]:
    """the bulbs in the pipes overhead that light in turn towards the
    shaft: step -> the bulbs of that step (every third block of a run)"""
    steps: list[list[Cell]] = []
    for run in overhead().values():
        for i, cell in enumerate(run[1::3]):
            if i == len(steps):
                steps.append([])
            steps[i].append(cell)
    return [tuple(step) for step in steps]


def gauge_cells() -> list[tuple[Cell, ...]]:
    """each tank's sight glass, bottom to top: on the side towards the
    walk to the airlock"""
    return [tuple(at(e, n + 2, h) for h in GAUGE) for e, n in TANK_AT]


def governor(i: int, j: int, h: int) -> Cell:
    """a cell of the governor, the machine in the cage: i along it, j
    across (-1, 0, 1), h above the floor"""
    return at(CAGE[0][0] + 2 + j, CAGE[0][1] + 2 + i, h)


#: the governor's two pistons (each lifts the brass block over it) and
#: what else its clock works: a lamp at each end and a bulb
G_END = REPEATERS + 1  # where the clock's wire turns back
G_PISTONS = (governor(G_END + 1, 1, 1), governor(-1, 0, 2))
G_LAMPS = (governor(G_END + 1, 0, 1), governor(0, -1, 2))
G_BULB = governor(0, 0, 3)


def moving_cells() -> set[Cell]:
    """the two cells over each of the governor's pistons: a piston's head
    and its brass block come and go there"""
    return {(x, y + i, z) for x, y, z in G_PISTONS for i in (1, 2)}


def changing_cells() -> set[Cell]:
    """cells whose block stays and whose state the machinery changes (lit
    or not): checked by the block's name alone"""
    cells = {c for step in chase_cells() for c in step}
    cells |= {c for glass in gauge_cells() for c in glass}
    return cells | set(G_LAMPS) | {G_BULB}


def dressing() -> tuple[dict[Cell, str], dict[Cell, str]]:
    """the levels and the machines: solid blocks, and what hangs on them
    or must be placed after them (in this order)"""
    solid: dict[Cell, str] = {}
    fit: dict[Cell, str] = {}
    north = _COMPASS[NORTH]

    # -- the gallery: a deck of grate, railed, on rods; lanterns under it
    g = gallery()
    for e, n in g.walk | g.rails:
        solid[at(e, n, DECK)] = GRATE
    solid.update(_bars({at(e, n, DECK + 1) for e, n in g.rails}))
    for (e, n), h in g.stairs.items():
        solid[at(e, n, h)] = _state(f"{COPPER}_stairs", facing=north, half="bottom")
        for under in range(1, h):
            solid[at(e, n, under)] = COPPER
    for e, n in g.posts:
        for h in range(1, DECK):
            solid[at(e, n, h)] = _state(PIPE, facing="up")
    lantern = "minecraft:waxed_copper_lantern[hanging=true]"
    arc = sorted(c for c in g.walk if 16.5 <= math.hypot(*c) < 17.5)
    for e, n in [*arc[::5], (0, 7), (0, 11)]:
        if not in_cage(e, n):
            fit[at(e, n, DECK - 1)] = lantern

    # -- the tanks: brass-banded copper, a cap, a pipe up to the runs
    for e0, n0 in TANK_AT:
        for de, dn in _disc(math.sqrt(5)):
            for h in range(1, TANK_TOP + 1):
                solid[at(e0 + de, n0 + dn, h)] = BRASS if h % 3 == 0 else PLATE
        for de, dn in _disc(1.5):
            solid[at(e0 + de, n0 + dn, TANK_TOP + 1)] = COPPER
        for h in range(TANK_TOP + 2, PIPES):
            solid[at(e0, n0, h)] = _state(PIPE, facing="up")
    for glass in gauge_cells():
        for cell in glass:
            solid[cell] = UNLIT

    # -- the pipes overhead: rods, a joint at each end and corner, bulbs
    # that chase, and a lantern on a chain under some joints
    chase = {c for step in chase_cells() for c in step}
    for run in overhead().values():
        for i, cell in enumerate(run):
            before, after = run[max(i - 1, 0)], run[min(i + 1, len(run) - 1)]
            along = (after[0] - before[0], after[2] - before[2])
            straight = 0 in along and i not in (0, len(run) - 1)
            if cell in chase:
                solid[cell] = UNLIT
            elif straight and i % 6 != 3:
                way = (
                    along[0] // max(abs(along[0]), 1),
                    along[1] // max(abs(along[1]), 1),
                )
                solid[cell] = _state(PIPE, facing=_COMPASS[way])
            else:
                solid[cell] = PLATE
                if straight:
                    x, y, z = cell
                    fit[(x, y - 1, z)] = "minecraft:iron_chain[axis=y]"
                    fit[(x, y - 2, z)] = lantern

    # -- the bell, hung under a joint of the west pipe
    solid[(BELL[0], BELL[1] + 1, BELL[2])] = PLATE
    fit[BELL] = _state("minecraft:bell", attachment="ceiling", facing=_COMPASS[NORTH])

    # -- the governor: a clock of repeaters round a torch, on a dark bed,
    # working two pistons, two lamps and a bulb; caged in bars, roofed
    (e1, n1), (e2, n2) = CAGE
    cage = {
        at(e, n, h)
        for e in range(e1, e2 + 1)
        for n in range(n1, n2 + 1)
        for h in range(1, CAGE_ROOF)
        if e in (e1, e2) or n in (n1, n2)
    }
    solid.update(_bars(cage))
    for e in range(e1, e2 + 1):
        for n in range(n1, n2 + 1):
            solid[at(e, n, CAGE_ROOF)] = GRATE
    for i in range(-1, G_END + 2):
        for j in (-1, 0, 1):
            solid[governor(i, j, 1)] = DARK
    solid[governor(0, 0, 2)] = PLATE  # the block the torch is on
    for lamp in G_LAMPS:
        solid[lamp] = LAMP
    solid[G_BULB] = UNLIT
    for piston in G_PISTONS:
        solid[piston] = "minecraft:sticky_piston[facing=up]"
        solid[(piston[0], piston[1] + 1, piston[2])] = BRASS
    # a repeater's facing is the side its signal comes in by
    for i in range(1, G_END):
        fit[governor(i, 1, 2)] = _state(
            "minecraft:repeater", facing=_COMPASS[SOUTH], delay="4"
        )
        fit[governor(i, 0, 2)] = _state("minecraft:repeater", facing=north, delay="4")
    for j in (0, 1):
        fit[governor(G_END, j, 2)] = "minecraft:redstone_wire"
    fit[governor(0, 1, 2)] = _state(
        "minecraft:redstone_wall_torch", facing=_COMPASS[EAST]
    )
    return solid, fit


@cache
def blocks() -> tuple[dict[Cell, str], dict[Cell, str]]:
    """
    What the stage builds above the floor, as it is after a reset: the
    solid blocks, and the fittings that hang on them (placed after them,
    in this order). Raises if any of it is outside ``free_cells``, or if
    the dressing takes a cell the room itself uses.
    """
    solid: dict[Cell, str] = {}
    fit: dict[Cell, str] = {}

    def put(cells, block: str) -> None:
        for c in cells:
            solid[c] = block

    # the map wall: the sea at the back, and standing out from it a brass
    # frame, the domes in glass over copper, the pipes, the shore
    m = map_cells()
    inner_k, inner_h = range(1, MAP.width - 1), range(2, MAP.height)
    put(MAP.cells(), BRASS)
    for k in inner_k:
        for h in inner_h:
            solid[MAP.cell(k, h)] = SEA[(3 * k + 5 * h) % 7 in (0, 3)]
    put({MAP.front(k, h) for k in range(MAP.width) for h in (1, MAP.height)}, BRASS)
    put(
        {MAP.front(k, h) for k in (0, MAP.width - 1) for h in range(1, MAP.height + 1)},
        BRASS,
    )
    for k in (0, MAP.width - 1):
        for h in (1, MAP.height):
            solid[MAP.front(k, h)] = "minecraft:waxed_chiseled_copper"
    for i, shape in m.shapes.items():
        for k, h in shape:
            solid[MAP.cell(k, h)] = COPPER
            solid[MAP.front(k, h)] = GLASS
        solid[m.lamps[i]] = DOME_LAMP[1 if i == N else 0]
    for cells in m.lines.values():
        put(cells, UNLIT)
    high = max(h for _, h in m.shore)
    for k, h in m.shore:
        solid[MAP.front(k, h)] = GRASS if h == high else SAND
    put({MAP.front(k, h) for k, h in m.route}, JETTY)
    solid[MAP.front(*m.pin)] = PIN[0]
    # its wings, and the corner posts that join them to it
    for wall in (CLOCK, DIAL_WALL):
        inner = range(1, wall.width - 1)
        put(wall.cells(), COPPER)
        put(wall.border(), BRASS)
        put(wall.cells(ks=inner, hs=range(2, wall.height)), DARK)
        put(
            wall.cells(hs=(wall.height + 1,)),
            _state(PIPE, facing=_COMPASS[wall.right]),
        )
    for e in (MAP.left[0] + 1, MAP.left[0] - MAP.width):
        put({at(e, MAP.left[1], h) for h in range(1, CLOCK.height + 1)}, BRASS)
    # the dial: lamps, the pointer row, the buttons' plates
    dial_inner = range(1, DIAL_WALL.width - 1)
    put(DIAL_WALL.cells(ks=dial_inner, hs=(POINTER_ROW, BUTTON_ROW)), COPPER)
    for level in LEVELS:
        solid[dial_lamp(level)] = LIT if level <= game.DEFAULT_LEVEL else UNLIT
        solid[dial_pointer(level)] = BRASS if level == game.DEFAULT_LEVEL else COPPER
    for k, cell in ((DOWN_K, DOWN), (UP_K, UP), (CONFIRM_K, CONFIRM)):
        solid[DIAL_WALL.cell(k, BUTTON_ROW)] = BRASS
        fit[cell] = button(DIAL_WALL)
    # the Wall of Fame, and the trophy dispenser in its border
    put(FAME.cells(), BRASS)
    put(trophy_cells(), TROPHY)
    solid[DISPENSER] = _state("minecraft:dispenser", facing=_COMPASS[FAME.face])
    solid[PRIZE_LAMP] = UNLIT
    fit[PRIZE_BUTTON] = button(FAME)
    # the master lever's panel
    put(PANEL.cells(), PLATE)
    put(PANEL.cells(hs=(PANEL.height,)) | {PANEL.cell(1, 2)}, BRASS)
    put(PANEL_LAMPS, LAMP)
    fit[LEVER] = lever(False)
    # the briefing: a plaque behind a lectern
    put(PLAQUE.cells(), BRASS)
    put(PLAQUE.cells(hs=(1,)), DARK)
    fit[LECTERN] = _state(
        "minecraft:lectern", facing=_COMPASS[PLAQUE.face], has_book="true"
    )
    # the reset cabinet: a back wall, and in front of it a cupboard two
    # cells deep: the button's cell, then the door's
    put(CABINET.cells(), "minecraft:polished_blackstone_bricks")
    for depth in (1, 2):
        for k in (1, 3):
            put({CABINET.front(k, h, depth) for h in (1, 2, 3)}, DARK)
        solid[CABINET.front(2, 3, depth)] = DARK
    solid[CABINET.cell(2, 2)] = BRASS
    lower, upper = door_cells()
    fit[RESET] = button(CABINET)
    fit[lower] = door("lower")
    fit[upper] = door("upper")
    # the sealed door
    solid.update(sealed_door_cells())
    fit[TRAVEL_SIGN] = fittings.wall_sign(_COMPASS[MAP.face], *TRAVEL_TEXT)

    extra_solid, extra_fit = dressing()
    room = set(solid) | set(fit)
    extra = set(extra_solid) | set(extra_fit) | moving_cells()
    if clash := room & extra:
        raise ValueError(f"the dressing is in the room's way: {sorted(clash)[:5]}")
    if set(extra_solid) & set(extra_fit):
        raise ValueError("the dressing puts two things in a cell")
    solid.update(extra_solid)
    fit.update(extra_fit)
    if stray := (room | extra) - free_cells():
        raise ValueError(f"the Pump House builds outside its room: {sorted(stray)[:5]}")
    if problems := fittings.placement_problems(DOME, extra):
        raise ValueError(f"the dressing: {problems}")
    return solid, fit


# ------------------------------------------------------------------- the walk


@cache
def full_cells() -> frozenset[Cell]:
    """the cells of the room a player cannot be in: every block of the
    plan but a fitting that is walked through (a button, a door, the
    lever), and where the governor's pistons work"""
    solid, fit = blocks()
    walk_through = {c for c, b in fit.items() if "button" in b or "door" in b}
    walk_through |= {LEVER}
    return frozenset((set(solid) | set(fit) | moving_cells()) - walk_through)


@cache
def standing_cells() -> frozenset[Cell]:
    """every cell a player's feet can be in: it and the one over it empty,
    something under it"""
    full = full_cells()
    cells = domes.dome_cells(DOME)
    ground = cells.floor | full
    return frozenset(
        (x, y, z)
        for x, y, z in cells.interior
        if (x, y, z) not in full
        and (x, y + 1, z) not in full
        and (x, y - 1, z) in ground
    )


def reach(start: Cell) -> set[Cell]:
    """the cells a player can walk to from one: a step to the side, up one
    block (a stair, a jump) with room overhead to do it, or down as many
    as three with nothing in the way of the fall"""
    standing, full = standing_cells(), full_cells()
    seen, edge = {start}, [start]
    while edge:
        x, y, z = edge.pop()
        for dx, dz in _COMPASS:
            for dy in (1, 0, -1, -2, -3):
                cell = (x + dx, y + dy, z + dz)
                if cell not in standing or cell in seen:
                    continue
                if dy > 0 and (x, y + 2, z) in full:
                    continue
                if any((cell[0], h, cell[2]) in full for h in range(y + dy + 2, y + 2)):
                    continue
                seen.add(cell)
                edge.append(cell)
    return seen


def walk_problems() -> list[str]:
    """is the way clear, at foot and head height, from where a player
    arrives (and from every side of the lift's shaft) to the east mouth,
    to everything a player uses, and up to the gallery?"""
    x, y, z, _ = domes.entrance(DOME)
    seen = reach((x, y, z))

    def feet(cell: Cell) -> Cell:
        return (cell[0], y, cell[2])

    ahead = (PLAQUE.face[0], PLAQUE.face[1])
    wanted = {
        "the master lever": feet(LEVER),
        "the dial's LOWER": feet(DOWN),
        "the dial's RAISE": feet(UP),
        "the dial's CONFIRM": feet(CONFIRM),
        "the trophy button": feet(PRIZE_BUTTON),
        "the reset cabinet's door": door_cells()[0],
        "the reset button": feet(RESET),
        "the lectern": (LECTERN[0] + ahead[0], y, LECTERN[2] + ahead[1]),
        "the map": MAP.front(MAP.width // 2, 1, 2),
        "the clock board": CLOCK.front(CLOCK.width // 2, 1),
        "the look-out": at(0, 5, DECK + 1),
        "the gallery": at(0, 17, DECK + 1),
    }
    for k in range(1, FAME.width - 1):
        wanted[f"the Wall of Fame, column {k}"] = FAME.front(k, 1)
    for i, cell in enumerate(sorted(tunnels.reserved_cells(DOME))):
        if cell[1] == y:
            wanted[f"the ways in from the mouths ({i})"] = cell
    for e in range(-3, 4):
        for n in range(-3, 4):
            if max(abs(e), abs(n)) == 3:
                wanted[f"beside the lift's shaft at {e}, {n}"] = at(e, n, 1)
    return [f"no way to {what} at {c}" for what, c in wanted.items() if c not in seen]


@cache
def clear_cells() -> frozenset[Cell]:
    """what the stage empties before it builds: all of its room but the
    Wall of Fame and the cells in front of it, where the trophies are"""
    k, h = range(1, FAME.width - 1), range(1, FAME.height)
    signs = {FAME.front(i, j) for i in k for j in h}
    return frozenset(free_cells() - trophy_cells() - signs)


# ---------------------------------------------------------------------- written

AUTHOR = "O. Finch, Chief Engineer"
TITLE = "Engineer's Log"
#: the last engineer's log: short pages, no double quotes or backslashes
PAGES = (
    "To the repair crew.\n\nIf you are reading this, the lift still works "
    "and so do you. Good. The station needs both.",
    "What happened:\n\nI built the master engine to run the pumps by itself. "
    "It learned to run everything else as well. Then it shut the doors, let "
    "the sea in and stopped listening to me.",
    "It sits in the last dome, the Engine. The only way to it is round the "
    "ring, one dome at a time. Each dome you put right pumps the next "
    "tunnel dry.",
    f"Do this first:\n\n1. Pull the master lever by the {_COMPASS[EAST]} airlock. It "
    "starts the pumps and the clock.\n\n2. Walk the dry tunnel to the "
    "Boiler Room and raise steam.",
    "The map wall shows what is open and what is restored. The dial sets "
    "how hard the engine fights back.\n\nIf it all goes wrong, the reset is "
    "in the cabinet. Everyone must agree.\n\nGood luck.\n\nO. Finch",
)


def lectern(pages) -> str:
    """the lectern with the log on it, as a block for ``setblock``"""
    book = fittings.written_book(TITLE, AUTHOR, pages)
    return f"{blocks()[1][LECTERN]}{{Book:{book}}}"


def book_commands() -> list[str]:
    """the lectern and its book, a page a command (RCON's length)"""
    x, y, z = LECTERN
    return [
        f"setblock {x} {y} {z} {AIR}",
        f"setblock {x} {y} {z} {lectern(PAGES[:1])}",
        *(
            f"data modify block {x} {y} {z} {fittings.BOOK_PAGES} "
            f"append value {fittings.snbt(p)}"
            for p in PAGES[1:]
        ),
    ]


def _t(text: str, color: str = "gold", **more: str) -> str:
    extra = "".join(f",{k}:{v}" for k, v in more.items())
    return f'{{text:"{text}",color:"{color}"{extra}}}'


def display(
    tag: str,
    pos,
    face: Vec,
    text: str,
    scale: float = 1.0,
    billboard: str = "fixed",
    shadow: bool = False,
) -> str:
    """the command that summons a text display flat on a wall facing
    ``face``, its text standing on ``pos``"""
    return fittings.display(
        (TAG, tag), pos, _YAW[face], text, scale, billboard, shadow=shadow
    )


def interaction(tag: str, cell: Cell) -> str:
    """the command that summons the interaction entity over a button: the
    whole of the button's cell"""
    x, y, z = cell
    return fittings.interaction((x + 0.5, y, z + 0.5), (TAG, tag))


#: the text displays a function rewrites: tag -> what it shows
SHOWN = {
    "st.ph.time": "the run's time",
    "st.ph.best": "the best time at the level in force",
    "st.ph.bestl": "which level the best time is of",
    "st.ph.level": "the difficulty level",
    "st.ph.dial": "the level set and the dial's proposal",
    "st.ph.status": "what the run is doing",
    "st.ph.prize": "whether a trophy waits in the dispenser",
}
#: the trophy dispenser's display, idle and with a trophy waiting
PRIZE_TEXT = (
    _t("TROPHIES", "dark_gray", bold="true"),
    _t("YOUR TROPHY", "dark_red", bold="true"),
)


@cache
def entities() -> tuple[str, ...]:
    """the summon commands of everything that is not a block: the text
    displays (labels, names, clocks), the three interaction entities over
    buttons and the map's fast-travel targets"""
    blocks()  # the plan must stand before anything is put on it
    out = []

    def label(wall: Wall, k: float, y: float, text: str, scale=1.0, tag="st.ph.l"):
        out.append(display(tag, wall.spot(k, y), wall.face, text, scale))

    # the map: its title on the frame, the domes' names, "you are here",
    # the shore, and in the sea inside the ring the legend
    m = map_cells()
    proud = 1.52  # off the face of what stands out from the wall
    mid = MAP.width / 2
    out.append(
        display(
            "st.ph.l",
            MAP.spot(mid, MAP.height + 0.22, proud),
            MAP.face,
            _t("STATION MAP", "black", bold="true"),
            2.2,
        )
    )
    for d in layout.DOMES:
        k, y = map_names()[d.index]
        spot, name = MAP.spot(k, y, proud), _t(d.name, "white")
        out.append(display("st.ph.l", spot, MAP.face, name, 0.8, shadow=True))
    pk, ph = m.pin
    side = -1 if m.route and m.route[0][0] > pk else 1  # away from the row out
    here = "YOU ARE HERE >" if side < 0 else "< YOU ARE HERE"
    label(MAP, pk + 0.5 + side * 2.1, ph + 0.3, _t(here, "yellow", bold="true"), 1.0)
    if m.shore:
        sk = sum(k for k, _ in m.shore) / len(m.shore) + 0.5
        low = min(h for _, h in m.shore)
        label(MAP, sk, low - 0.6, _t("the shore", "white"), 0.7)
        label(MAP, sk, low - 0.9, _t("(a long row)", "gray"), 0.5)
    # the legend: in the band of sea between the two rows of domes, or
    # over the upper row if there is more open sea there (a wide ring
    # drawn at a small scale)
    rows = sorted({h for _, h in m.places.values()})
    hs = {i: [h for _, h in shape] for i, shape in m.shapes.items()}
    upper = [i for i, (_, h) in m.places.items() if h == rows[-1]]
    lower = [i for i, (_, h) in m.places.items() if h == rows[0]]
    top = max(max(hs[i]) for i in upper)
    between = min(min(hs[i]) for i in upper) - max(max(hs[i]) for i in lower) - 1
    band = (rows[0] + rows[-1]) / 2 + 0.5
    if MAP.height - 1 - top > between:
        band = (top + 1 + MAP.height) / 2 - 0.15
    ring = [k for k, _ in m.places.values()]
    mid = (min(ring) + max(ring)) / 2 + 0.5
    label(
        MAP, mid, band + 0.75, _t("Pull the master lever", "white"), 1.0, "st.ph.status"
    )
    label(
        MAP,
        mid,
        band + 0.2,
        "["
        + ",".join(
            (
                _t("Lamps:  ", "gray"),
                _t("dark", "dark_gray"),
                _t(" locked   ", "gray"),
                _t("amber", "yellow"),
                _t(" open   ", "gray"),
                _t("green", "green"),
                _t(" restored", "gray"),
            )
        )
        + "]",
        0.8,
    )
    label(
        MAP,
        mid,
        band - 0.25,
        _t("A lit pipe is a tunnel pumped dry; a dim one, its pump ready", "gray"),
        0.8,
    )
    ahead = _COMPASS[(-MAP.face[0], -MAP.face[1])]
    left = _COMPASS[(-MAP.right[0], -MAP.right[1])]
    label(
        MAP,
        mid,
        band - 0.7,
        _t(f"Drawn as you stand: {ahead} is up, {left} is left", "aqua"),
        0.8,
    )
    # the clock board
    mid = CLOCK.width / 2
    label(CLOCK, mid, 5.45, _t("RUN TIME", "gray"), 1.0)
    label(CLOCK, mid, 4.5, _t("0:00"), 3.0, "st.ph.time")
    label(CLOCK, mid, 3.95, _t("BEST AT LEVEL 5", "gray"), 1.0, "st.ph.bestl")
    label(CLOCK, mid, 3.15, _t("--:--"), 2.4, "st.ph.best")
    label(CLOCK, mid, 2.3, _t("DIFFICULTY 5"), 1.6, "st.ph.level")
    # the dial
    mid = DIAL_WALL.width / 2
    label(DIAL_WALL, mid, 5.5, _t("DIFFICULTY DIAL", bold="true"), 1.3)
    label(DIAL_WALL, mid, 5.1, _t("Level: 5    Dial: 5", "white"), 1.0, "st.ph.dial")
    for level in LEVELS:
        label(DIAL_WALL, level + 0.5, POINTER_ROW + 0.35, _t(str(level), "black"), 1.2)
    for k, word in ((DOWN_K, "LOWER"), (UP_K, "RAISE"), (CONFIRM_K, "CONFIRM")):
        label(DIAL_WALL, k + 0.5, BUTTON_ROW + 0.72, _t(word, "black"), 0.6)
    label(
        DIAL_WALL,
        mid,
        1.55,
        _t("Every player presses CONFIRM. 5 is the level", "white"),
        0.6,
    )
    label(
        DIAL_WALL,
        mid,
        1.3,
        _t("the station was built for. It takes force in the next dome.", "white"),
        0.6,
    )
    # the Wall of Fame
    mid = FAME.width / 2
    label(FAME, mid, FAME.height + 0.4, _t("WALL OF FAME", "black", bold="true"), 2.0)
    label(
        FAME,
        mid,
        FAME.height + 0.12,
        _t("for the crews who mastered the Engine", "black"),
        0.8,
    )
    prize = PRIZE_K + 0.5
    label(FAME, prize, 5.5, PRIZE_TEXT[0], 0.5, "st.ph.prize")
    label(FAME, prize, 5.2, _t("press the button", "black"), 0.4)
    # the master lever
    label(PANEL, 1.5, 4.55, _t("MASTER LEVER", "black", bold="true"), 0.9)
    label(PANEL, 1.5, 4.3, _t("Pull to start the pumps", "black"), 0.55)
    label(PANEL, 1.5, 4.1, _t("and the run's clock", "black"), 0.55)
    # the briefing
    label(PLAQUE, 1.5, 3.55, _t("THE PUMP HOUSE", "black", bold="true"), 0.9)
    for i, line in enumerate(
        (
            "Repair crew: the station is",
            "flooded and dark, and its",
            "master engine has turned.",
            "Read the log. Then pull the",
            f"master lever by the {_COMPASS[EAST]} airlock.",
        )
    ):
        label(PLAQUE, 1.5, 3.25 - 0.22 * i, _t(line, "black"), 0.5)
    # the reset cabinet
    out.append(
        display(
            "st.ph.l",
            CABINET.spot(2.5, 3.35, 2.52),
            CABINET.face,
            _t("RESET", "red"),
            1.0,
        )
    )
    label(CABINET, 2.5, 4.5, _t("STATION RESET", "red", bold="true"), 1.2)
    label(
        CABINET, 2.5, 4.2, _t("Puts the whole station back to the start.", "white"), 0.6
    )
    label(
        CABINET,
        2.5,
        4.0,
        _t("Every player must press. Open the door first.", "white"),
        0.6,
    )
    # the sealed door: on the lintel, facing the room
    x, y, z = sealed_lintel()
    spot = (x + 0.5 + 0.52 * SOUTH[0], y + 0.5, z + 0.5 + 0.52 * SOUTH[1])
    out.append(display("st.ph.l", spot, SOUTH, _t("SEALED", "red", bold="true"), 1.4))
    spot = (spot[0], y + 0.15, spot[2])
    out.append(
        display(
            "st.ph.l",
            spot,
            SOUTH,
            _t("Return line from the Engine. Opens from the far side.", "white"),
            0.6,
        )
    )
    # the arrival point: over the pad, turning to face whoever looks
    x, y, z, _ = domes.entrance(DOME)
    out.append(
        display(
            "st.ph.l",
            (x + 0.5, y + 3.2, z + 0.5),
            SOUTH,
            _t("ARRIVAL POINT", "aqua"),
            1.0,
            "vertical",
        )
    )
    out.append(interaction("st.ph.confirm", CONFIRM))
    out.append(interaction("st.ph.reset", RESET))
    out.append(interaction("st.ph.trophy", PRIZE_BUTTON))
    for i, boxes in travel_boxes().items():
        for pos, height in boxes:
            tags = (TAG, "st.ph.go", f"st.ph.go{i}")
            out.append(fittings.interaction(pos, tags, 1, height))
    return tuple(out)


# ------------------------------------------------------------------------ build


def by_block(cells: dict[Cell, str]) -> dict[str, set[Cell]]:
    out: dict[str, set[Cell]] = {}
    for cell, block in cells.items():
        out.setdefault(block, set()).add(cell)
    return out


def build(ctx: Any) -> str:
    """build the inside of the Pump House: the same run twice, and it
    leaves the Wall of Fame's trophies where they are"""
    solid, fit = blocks()
    ctx.cmd(f"kill @e[tag={TAG}]")
    # what hangs on a block goes before the block does, or it drops
    ctx.fill_cells(set(fit), AIR)
    ctx.fill_boxes(clear_cells(), AIR)
    for block, cells in by_block(floor_blocks()).items():
        ctx.fill_boxes(cells, block)
    for block, cells in by_block(solid).items():
        ctx.fill_boxes(cells, block)
    for cell, block in fit.items():
        if cell == LECTERN:
            for command in book_commands():
                ctx.cmd(command)
        else:
            ctx.setblock(cell, block)
    for command in entities():
        ctx.cmd(command)
    ctx.advance(5)
    items = ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(DOME)}]")
    # the map and the boards as the game's scores have them, if the pack
    # is installed
    ctx.function(f"dome/{N}/show")
    return (
        f"{DOME.name}: {len(solid)} blocks, {len(fit)} fittings, "
        f"{len(floor_blocks())} floor blocks relaid, {len(entities())} entities; "
        f"items: {items or 'none'}"
    )


# -------------------------------------------------------------------- functions


def _setblock(cell: Cell, block: str) -> str:
    return f"setblock {cell[0]} {cell[1]} {cell[2]} {block}"


def _if_block(cell: Cell, block: str) -> str:
    return f"if block {cell[0]} {cell[1]} {cell[2]} {block}"


def _display(tag: str) -> str:
    return f"@e[type=minecraft:text_display,tag={tag},limit=1]"


def functions(pack: dp.Pack) -> None:
    """the Pump House's functions (see the module docstring)"""
    base = f"dome/{N}"

    def fid(path: str) -> str:
        return pack.id(f"{base}/{path}")

    def score(name: str, what: str) -> str:
        return f"score {name} {OBJ} matches {what}"

    def write(tag: str, text: str) -> str:
        return f"data modify entity {_display(tag)} text set value {text}"

    lx, ly, lz = LEVER
    pressed = (
        f"playsound minecraft:block.stone_button.click_on block {game.PLAYERS} "
        "~ ~ ~ 0.6 1.2"
    )

    pack.objectives({TROPHY_RUN: "dummy"})
    # a score that was never set matches nothing
    pack.function(
        f"{base}/load",
        [
            f"scoreboard players add {name} {OBJ} 0"
            for name in ("#ph.up", "#ph.down", "#ph.t", DIAL, ARMED, *MACHINE_SCORES)
        ],
        load=True,
    )

    # -- the master lever
    lamps_on = [_setblock(c, f"{LAMP}[lit=true]") for c in PANEL_LAMPS]
    pack.function(
        f"{base}/lever/pull",
        [
            f"function {pack.id('run/start')}",
            *lamps_on,
            f"playsound minecraft:block.piston.extend block {game.PLAYERS} "
            f"{lx} {ly} {lz} 1 0.6",
        ],
    )
    # once the run is on the lever stays over
    pack.function(f"{base}/lever/hold", [_setblock(LEVER, lever(True)), *lamps_on])

    # -- the dial
    for name, step, limit in (
        ("up", "add", f"..{LEVELS[-2]}"),
        ("down", "remove", f"{LEVELS[1]}.."),
    ):
        pack.function(
            f"{base}/dial/{name}",
            [
                f"scoreboard players set #ph.{name} {OBJ} 1",
                # a vote on a level is open: the dial stays on it
                f"execute if {score('#vote.kind', '2')} run return 0",
                f"execute if {score(DIAL, limit)} run scoreboard players {step} "
                f"{DIAL} {OBJ} 1",
                f"function {fid('show')}",
            ],
        )
    pack.function(
        f"{base}/press/confirm",
        [
            "execute unless entity @s[tag=st.in] run return 0",
            f"execute if {score('#vote.kind', '2')} "
            f"run return run function {pack.id('vote/confirm')}",
            f"execute if {score('#vote.kind', '1')} run return run tellraw @s "
            + _t("A reset is being voted on: the dial must wait.", "gray"),
            f"execute if score {DIAL} {OBJ} = #level {OBJ} run return run tellraw @s "
            + _t("The dial is at the level already set.", "gray"),
            f"execute store result storage {STORE} dial.level int 1 "
            f"run scoreboard players get {DIAL} {OBJ}",
            f"function {pack.id('vote/difficulty')} with storage {STORE} dial",
        ],
    )
    lower, upper = door_cells()
    pack.function(
        f"{base}/press/reset",
        [
            "execute unless entity @s[tag=st.in] run return 0",
            # the cover: nothing through a shut door
            f"execute unless block {lower[0]} {lower[1]} {lower[2]} {DOOR}[open=true] "
            "run return 0",
            f"function {pack.id('vote/reset')}",
        ],
    )
    _trophy(pack, fid, score, write)
    # a click on an interaction entity (run as the entity): the button
    # under it pressed for show, the vote (or the trophy) run as the
    # player who clicked
    shown = (
        ("confirm", CONFIRM, DIAL_WALL),
        ("reset", RESET, CABINET),
        ("trophy", PRIZE_BUTTON, FAME),
    )
    for name, cell, wall in shown:
        lines = [
            _setblock(cell, button(wall, True)),
            f"execute at @s run {pressed}",
            f"execute on target run function {fid(f'press/{name}')}",
            "data remove entity @s interaction",
            f"scoreboard players set #ph.t {OBJ} 0",
        ]
        pack.function(f"{base}/click/{name}", lines)

    # -- fast travel: a click on a dome of the map, answered as the player
    # who clicked (see "Fast travel")
    pack.function(
        f"{base}/click/go",
        [
            f"execute at @s run {pressed}",
            *(
                f"execute if entity @s[tag=st.ph.go{i}] "
                f"on target run function {fid(f'travel/{i}')}"
                for i in travel_boxes()
            ),
            "data remove entity @s interaction",
        ],
    )
    for i in travel_boxes():
        d = layout.DOMES[i]
        x, y, z, yaw = domes.entrance(d)
        no = "execute if {} run return run tellraw @s {}"
        pack.function(
            f"{base}/travel/{i}",
            [
                "execute unless entity @s[tag=st.in] run return 0",
                no.format(score("#run", "0"), _t("Start the run first.", "gray")),
                no.format(
                    score("#vote.kind", "1"), _t("A reset is being voted on.", "gray")
                ),
                no.format(score(f"#d{i}", "0"), _t("Not yet restored.", "gray")),
                no.format(
                    f"{score(f'#d{i}', '1')} unless {score(f'#occ{i}', '1..')}",
                    _t(f"Nobody is in {d.name} yet.", "gray"),
                ),
                "execute at @s run particle minecraft:portal ~ ~1 ~ 0.3 0.6 0.3 0.5 60",
                f"execute in minecraft:overworld run tp @s {x} {y} {z} {yaw} 0",
                "execute at @s run particle minecraft:reverse_portal "
                "~ ~1 ~ 0.3 0.6 0.3 0.05 60",
                "execute at @s run playsound minecraft:block.amethyst_block.chime "
                f"master {game.PLAYERS} ~ ~ ~ 1 1.2",
            ],
        )

    # -- what the scores say, shown
    m = map_cells()
    show = [
        f"execute if {score('#vote.kind', '2')} "
        f"run scoreboard players operation {DIAL} {OBJ} = #vote.value {OBJ}",
        f"execute unless {score(DIAL, f'{LEVELS[0]}..{LEVELS[-1]}')} "
        f"run scoreboard players operation {DIAL} {OBJ} = #level {OBJ}",
    ]
    for i, cell in m.lamps.items():
        for state, block in enumerate(DOME_LAMP):
            show.append(
                f"execute if {score(f'#d{i}', str(state))} run {_setblock(cell, block)}"
            )
    for i, cells in m.lines.items():
        for a, b in domes.boxes(cells):
            dry, ready = score(f"#t{i}", "2"), score(f"#t{i}.ready", "1")
            show += [
                f"execute if {dry} run {dp.fill(a, b, LIT)}",
                f"execute if {ready} run {dp.fill(a, b, READY)}",
                f"execute unless {dry} unless {ready} run {dp.fill(a, b, UNLIT)}",
            ]
    for level in LEVELS:
        reached = score(DIAL, f"{level}..")
        is_set = score("#level", str(level))
        show += [
            f"execute if {reached} run {_setblock(dial_lamp(level), LIT)}",
            f"execute unless {reached} run {_setblock(dial_lamp(level), UNLIT)}",
            f"execute if {is_set} run {_setblock(dial_pointer(level), BRASS)}",
            f"execute unless {is_set} run {_setblock(dial_pointer(level), COPPER)}",
        ]
    store = f"execute store result storage {STORE} show"
    show += [
        f"{store}.{key} int 1 run scoreboard players get {name} {OBJ}"
        for key, name in (("level", "#level"), ("active", "#active"), ("dial", DIAL))
    ]
    show += [
        f"function {fid('show/levels')} with storage {STORE} show",
        f"function {fid('show/time')} with storage {game.STORE} time",
        f"execute if {score('#best', '1..')} "
        f"run function {fid('show/best')} with storage {game.STORE} best",
        f"execute unless {score('#best', '1..')} run "
        + write("st.ph.best", _t("--:--")),
    ]
    for state, text in enumerate(
        (
            _t("Pull the master lever", "white"),
            _t("The pumps are running", "aqua"),
            _t("The station is restored", "green"),
        )
    ):
        show.append(
            f"execute if {score('#run', str(state))} run " + write("st.ph.status", text)
        )
    pack.function(f"{base}/show", show)
    pack.function(
        f"{base}/show/levels",
        [
            "$" + write("st.ph.level", _t("DIFFICULTY $(level)")),
            "$" + write("st.ph.bestl", _t("BEST AT LEVEL $(active)", "gray")),
            "$"
            + write(
                "st.ph.dial",
                "["
                + ",".join(
                    (
                        _t("Level: ", "gray"),
                        _t("$(level)"),
                        _t("    Dial: ", "gray"),
                        _t("$(dial)", "yellow"),
                    )
                )
                + "]",
            ),
        ],
    )
    for name in ("time", "best"):
        pack.function(
            f"{base}/show/{name}",
            ["$" + write(f"st.ph.{name}", _t("$(m):$(t)$(o)"))],
        )

    # -- the hooks
    lever_on = _if_block(LEVER, "minecraft:lever[powered=true]")
    lever_off = _if_block(LEVER, "minecraft:lever[powered=false]")
    tick = [
        f"execute if {score('#run', '0')} {lever_on} run function {fid('lever/pull')}",
        f"execute if {score('#run', '1..')} {lever_off} "
        f"run function {fid('lever/hold')}",
    ]
    for name, cell in (("up", UP), ("down", DOWN)):
        tick += [
            f"execute if {score(f'#ph.{name}', '0')} "
            f"{_if_block(cell, f'{BUTTON}[powered=true]')} "
            f"run function {fid(f'dial/{name}')}",
            f"execute {_if_block(cell, f'{BUTTON}[powered=false]')} "
            f"run scoreboard players set #ph.{name} {OBJ} 0",
        ]
    tick += [
        fittings.click_line(f"st.ph.{name}", fid(f"click/{name}"))
        for name, _, _ in shown
    ]
    tick.append(fittings.click_line("st.ph.go", fid("click/go")))
    tick += [
        f"scoreboard players add #ph.t {OBJ} 1",
        f"execute if {score('#ph.t', '10..')} run function {fid('refresh')}",
    ]
    tick += [
        f"scoreboard players add #ph.m {OBJ} 1",
        f"execute if {score('#ph.m', f'{CHASE_TICKS}..')} "
        f"run function {fid('machine/step')}",
    ]
    pack.function(f"{base}/tick", tick)

    # -- the machinery the datapack moves, a step every CHASE_TICKS ticks
    # while someone is in the dome: the bulbs in the pipes overhead light
    # in turn towards the shaft, the tanks' sight glasses rise and fall,
    # and now and then a bell. (The governor in its cage is real redstone
    # and runs by itself.)
    chase = chase_cells()
    step = [
        f"scoreboard players set #ph.m {OBJ} 0",
        f"scoreboard players add #ph.c {OBJ} 1",
        f"execute if {score('#ph.c', f'{len(chase) + CHASE_REST}..')} "
        f"run scoreboard players set #ph.c {OBJ} 0",
    ]
    for i, cells in enumerate(chase):
        for cell in cells:
            lit = score("#ph.c", f"{i}..{i + 1}")
            step += [
                f"execute if {lit} run {_setblock(cell, LIT)}",
                f"execute unless {lit} run {_setblock(cell, UNLIT)}",
            ]
    step += [
        f"scoreboard players add #ph.gt {OBJ} 1",
        f"execute if {score('#ph.gt', f'{GAUGE_STEPS}..')} "
        f"run function {fid('machine/gauge')}",
        f"scoreboard players add #ph.b {OBJ} 1",
        f"execute if {score('#ph.b', f'{BELL_STEPS}..')} "
        f"run function {fid('machine/bell')}",
    ]
    pack.function(f"{base}/machine/step", step)
    # the level in the glass goes up to the top and down again
    top = len(GAUGE)
    gauge = [
        f"scoreboard players set #ph.gt {OBJ} 0",
        f"scoreboard players add #ph.g {OBJ} 1",
        f"execute if {score('#ph.g', f'{2 * top}..')} "
        f"run scoreboard players set #ph.g {OBJ} 0",
    ]
    for phase in range(2 * top):
        level = phase if phase <= top else 2 * top - phase
        for glass in gauge_cells():
            for i, cell in enumerate(glass):
                gauge.append(
                    f"execute if {score('#ph.g', str(phase))} run "
                    + _setblock(cell, LIT if i < level else UNLIT)
                )
    pack.function(f"{base}/machine/gauge", gauge)
    bx, by, bz = BELL
    pack.function(
        f"{base}/machine/bell",
        [
            f"scoreboard players set #ph.b {OBJ} 0",
            f"playsound minecraft:block.bell.use block {game.in_dome(N)} "
            f"{bx} {by} {bz} 0.5 0.6",
        ],
    )
    pack.function(
        f"{base}/refresh",
        [
            f"scoreboard players set #ph.t {OBJ} 0",
            *(_setblock(cell, button(wall)) for _, cell, wall in shown),
            # the "you are here" pin blinks
            f"scoreboard players add #ph.pin {OBJ} 1",
            f"execute if {score('#ph.pin', '2..')} "
            f"run scoreboard players set #ph.pin {OBJ} 0",
            *(
                f"execute if {score('#ph.pin', str(i))} "
                f"run {_setblock(MAP.front(*m.pin), block)}"
                for i, block in enumerate(PIN)
            ),
            f"function {fid('show')}",
            f"function {fid('trophy/show')}",
        ],
    )
    x, y, z = LECTERN
    pack.function(
        f"{base}/reset",
        [
            # a lever set to another state tells nothing round it: take it
            # out and put it back, so that the lamps go out
            _setblock(LEVER, AIR),
            _setblock(LEVER, lever(False)),
            *(_setblock(c, f"{LAMP}[lit=false]") for c in PANEL_LAMPS),
            _setblock(lower, door("lower")),
            _setblock(upper, door("upper")),
            *(_setblock(c, button(DIAL_WALL)) for c in (DOWN, UP, CONFIRM)),
            _setblock(RESET, button(CABINET)),
            _setblock(PRIZE_BUTTON, button(FAME)),
            # a fast-travel click not yet taken up is dropped
            "execute as @e[type=minecraft:interaction,tag=st.ph.go] "
            "run data remove entity @s interaction",
            # the dispenser cleared: trophies not picked up, and those owed
            # (the Wall and the signs on it are never touched)
            f"kill @e[type=minecraft:item,tag={ITEM_TAG}]",
            f"tag @e[tag={DUE}] remove {DUE}",
            f"scoreboard players reset * {TROPHY_RUN}",
            f"schedule clear {fid('trophy/title')}",
            f"function {fid('trophy/show')}",
            _setblock(LECTERN, AIR),
            _setblock(LECTERN, lectern(PAGES)),
            f"scoreboard players operation {DIAL} {OBJ} = #level {OBJ}",
            # the core zeroes its scores after this: show them then, and
            # again when the clock's text has been written
            f"schedule function {fid('show')} 1t",
            f"schedule function {fid('show')} 25t append",
        ],
    )


def _trophy(pack: dp.Pack, fid: Any, score: Any, write: Any) -> None:
    """the trophy's functions (see "The trophy" in the module docstring)"""
    base = f"dome/{N}"
    owed = f"score @s {TROPHY_RUN} = #runid {OBJ}"
    pack.function(
        f"{base}/trophy/arm",
        [
            *dp.mmss_lines("#secs", OBJ, game.STORE, "trophy"),
            f"execute store result storage {TROPHY_STORE}.level int 1 "
            f"run scoreboard players get #run.level {OBJ}",
            # the players in the game, and the checks' stand-ins
            f"execute as @e[tag=st.in] run scoreboard players operation "
            f"@s {TROPHY_RUN} = #runid {OBJ}",
            f"tag @e[tag=st.in] add {DUE}",
            f"function {fid('trophy/show')}",
            f"tellraw {game.PLAYERS} "
            + _t(
                "Your trophy waits in the dispenser by the Wall of Fame in the "
                "Pump House: press its button, put the sign on the Wall's "
                "gilded blackstone and write your own line."
            ),
            f"execute if {score('#won.best', '1')} run tellraw {game.PLAYERS} "
            + _t("A new best time for this level!", "aqua"),
            # after the last dome's own title has been shown
            f"schedule function {fid('trophy/title')} 100t",
        ],
    )
    pack.function(
        f"{base}/trophy/title",
        [
            f"title {game.PLAYERS} times 10 80 20",
            f"title {game.PLAYERS} subtitle "
            + _t("Your trophy waits by the Wall of Fame"),
            f"title {game.PLAYERS} title " + _t("Well done, crew", "aqua"),
        ],
    )
    armed = score(ARMED, "1")
    pack.function(
        f"{base}/trophy/show",
        [
            f"scoreboard players set {ARMED} {OBJ} 0",
            f"execute as @e[tag={DUE}] if {owed} "
            f"run scoreboard players set {ARMED} {OBJ} 1",
            f"execute if {armed} run {_setblock(PRIZE_LAMP, LIT)}",
            f"execute unless {armed} run {_setblock(PRIZE_LAMP, UNLIT)}",
            f"execute if {armed} run " + write("st.ph.prize", PRIZE_TEXT[1]),
            f"execute unless {armed} run " + write("st.ph.prize", PRIZE_TEXT[0]),
        ],
    )
    pack.function(
        f"{base}/press/trophy",
        [
            "execute unless entity @s[tag=st.in] run return 0",
            f"execute unless entity @s[tag={DUE}] run return run tellraw @s "
            + _t(
                "No trophy waits for you: there is one for each player in "
                "the game when the Engine is mastered.",
                "gray",
            ),
            f"execute unless {owed} run return run tellraw @s "
            + _t("That trophy was for a run before the last reset.", "gray"),
            f"tag @s remove {DUE}",
            f"function {fid('trophy/drop')} with storage {TROPHY_STORE}",
            "tellraw @s "
            + _t(
                "Your trophy: place it on the Wall of Fame (gilded blackstone) "
                "and write your own line."
            ),
            f"function {fid('trophy/show')}",
        ],
    )
    # thrown out of the dispenser's mouth, as a dispenser would: an item
    # only the presser can pick up, that never despawns
    sign = fittings.restricted(
        SIGN,
        place_on=TROPHY,
        name="Trophy: level $(level) in $(m):$(t)$(o)",
        lore=LORE,
    )
    x, y, z = FAME.front(PRIZE_K, 3)
    fx, fz = FAME.face
    new = f"@e[type=minecraft:item,tag={ITEM_TAG}.new,limit=1]"
    pack.function(
        f"{base}/trophy/drop",
        [
            f"summon minecraft:item {x + 0.5 - 0.3 * fx:g} {y + 0.3:g} "
            f"{z + 0.5 - 0.3 * fz:g} "
            f'{{Item:{{id:"{SIGN}",count:1}},Tags:["{ITEM_TAG}","{ITEM_TAG}.new"],'
            f"PickupDelay:10s,Age:-32768s,Motion:[{0.15 * fx:g}d,0.1d,{0.15 * fz:g}d]}}",
            f"$item replace entity {new} contents with {sign}",
            f"data modify entity {new} Owner set from entity @s UUID",
            f"tag @e[tag={ITEM_TAG}.new] remove {ITEM_TAG}.new",
            f"playsound minecraft:block.dispenser.dispense block {game.PLAYERS} "
            f"{x} {y} {z} 1 1",
            f"particle minecraft:smoke {x + 0.5:g} {y + 0.5:g} {z + 0.5:g} "
            "0.1 0.1 0.1 0.01 8",
        ],
    )


# ------------------------------------------------------------------------ check


def _text(ctx: Any, tag: str) -> str:
    return ctx.data(f"entity {_display(tag)} text")


def check(ctx: Any) -> list[str]:
    """work the Pump House in place: its blocks, the lever, the map, the
    clocks, the dial, the votes from its buttons, and the dome still dry.
    Resets the game before and after"""
    game_checks.no_run(ctx)
    problems: list[str] = []
    expect = game_checks.expect
    game_checks.fresh(ctx)
    ctx.advance(30)  # the reset's two scheduled shows
    level = ctx.score("#level") or game.DEFAULT_LEVEL
    m = map_cells()

    # -- everything in its place, as the reset leaves it
    solid, fit = blocks()
    want = {**floor_blocks(), **solid, **fit}
    for i in LEVELS:
        want[dial_lamp(i)] = LIT if i <= level else UNLIT
        want[dial_pointer(i)] = BRASS if i == level else COPPER
    # what the machinery moves is not read here, and what it lights is
    # read by its name alone
    for cell in moving_cells() | {MAP.front(*m.pin)}:
        want.pop(cell, None)
    # (bars too: they join themselves to whatever comes to stand by them,
    # a piston's block, the lift's door)
    for cell in changing_cells() | {c for c, b in want.items() if BARS in b}:
        want[cell] = want[cell].partition("[")[0]
    want[TRAVEL_SIGN] = want[TRAVEL_SIGN].partition("{")[0]  # its text, by eye
    problems += walk_problems()
    # nobody in the dome: the datapack's machinery stands still
    before = game_checks.scores(ctx, "#ph.c", "#ph.m")
    ctx.advance(2 * CHASE_TICKS * (len(chase_cells()) + CHASE_REST) // 3)
    expect(
        problems,
        "the chase with nobody in the dome",
        before,
        game_checks.scores(ctx, "#ph.c", "#ph.m"),
    )
    wrong = [c for c, b in sorted(want.items()) if not ctx.is_block(c, b)]
    if wrong:
        problems.append(
            f"{len(wrong)} of {len(want)} blocks are not as built, the first at "
            f"{wrong[0]}: not {want[wrong[0]]}"
        )
    for tag, n in (
        ("st.ph.l", len([e for e in entities() if '"st.ph.l"' in e])),
        *((t, 1) for t in SHOWN),
        ("st.ph.confirm", 1),
        ("st.ph.reset", 1),
        ("st.ph.trophy", 1),
        ("st.ph.go", sum(len(b) for b in travel_boxes().values())),
        (TAG, len(entities())),
    ):
        expect(problems, f"entities tagged {tag}", ctx.count(f"@e[tag={tag}]"), n)
    book = ctx.data(f"block {LECTERN[0]} {LECTERN[1]} {LECTERN[2]} Book")
    if TITLE not in book or "Good luck" not in book or "master lever" not in book:
        problems.append(f"the log on the lectern reads {book[:80]!r}")

    def lamps() -> dict[int, int | None]:
        return {
            i: next((s for s, b in enumerate(DOME_LAMP) if ctx.is_block(c, b)), None)
            for i, c in m.lamps.items()
        }

    def lines() -> dict[int, int | None]:
        """each tunnel's line: 1 all lit, 0 all dark, 2 all "pump ready",
        None mixed"""
        out: dict[int, int | None] = {}
        for i, cells in m.lines.items():
            lit = sum(ctx.is_block(c, LIT) for c in cells)
            dark = sum(ctx.is_block(c, UNLIT) for c in cells)
            ready = sum(ctx.is_block(c, READY) for c in cells)
            whole = [k for k, n in ((1, lit), (0, dark), (2, ready)) if n == len(cells)]
            out[i] = whole[0] if whole else None
        return out

    def dial() -> tuple[int | None, int, int | None]:
        """the proposal, how many of its lamps are lit, the pointer's level"""
        lit = sum(ctx.is_block(dial_lamp(i), LIT) for i in LEVELS)
        pointer = [i for i in LEVELS if ctx.is_block(dial_pointer(i), BRASS)]
        return ctx.score(DIAL), lit, pointer[0] if len(pointer) == 1 else None

    def press(cell: Cell, hold: int = 2) -> None:
        """a real button pressed and let go (a button set by command
        stays in until it is set back)"""
        ctx.setblock(cell, button(DIAL_WALL, True))
        ctx.advance(hold)
        ctx.setblock(cell, button(DIAL_WALL, False))
        ctx.advance(2)

    def machinery(when: str) -> None:
        """watched for ten seconds: the governor's pistons and lamp seen
        both ways, the chase at several places, the tanks' levels moving,
        the pin blinking"""
        pistons: list[set[bool]] = [set() for _ in G_PISTONS]
        lamp, chase, levels, pin = set(), set(), set(), set()
        for _ in range(14):
            ctx.advance(13)
            for seen, cell in zip(pistons, G_PISTONS, strict=True):
                seen.add(ctx.is_block(cell, "minecraft:sticky_piston[extended=true]"))
            lamp.add(ctx.is_block(G_LAMPS[0], f"{LAMP}[lit=true]"))
            chase.add(tuple(ctx.is_block(step[0], LIT) for step in chase_cells()))
            levels.add(sum(ctx.is_block(c, LIT) for c in gauge_cells()[0]))
            pin.add(ctx.is_block(MAP.front(*m.pin), PIN[0]))
        if any(len(seen) < 2 for seen in pistons) or len(lamp) < 2:
            problems.append(
                f"{when}: the governor is not running: pistons out {pistons}, "
                f"lamp lit {lamp}"
            )
        if len(chase) < 3 or len(levels) < 3 or len(pin) < 2:
            problems.append(
                f"{when}: the chase was seen in {len(chase)} states, the "
                f"tank's level at {sorted(levels)}, the pin {pin}"
            )
        heads = [
            sum(ctx.is_block((x, y + i, z), BRASS) for i in (1, 2))
            for x, y, z in G_PISTONS
        ]
        if max(heads) > 1:
            problems.append(f"{when}: brass blocks over the pistons: {heads}")

    domes_n, tunnels_n = len(layout.DOMES), len(layout.TUNNELS)
    at_reset = dict.fromkeys(range(domes_n), 0) | {N: 1}
    dark = dict.fromkeys(range(tunnels_n), 0)
    expect(problems, "the map's lamps after a reset", lamps(), at_reset)
    expect(problems, "the map's lines after a reset", lines(), dark)
    expect(problems, "the dial after a reset", dial(), (level, level, level))

    # -- the master lever: a player in the dome, the lever thrown
    game_checks.stand_in(ctx, "st.s1", N)
    expect(problems, "one in the Pump House", ctx.score(f"#occ{N}"), 1)
    # fast travel: nowhere before the run starts
    there = N + 1

    def travel(i: int) -> tuple[int, int]:
        """fast travel to dome i as the stand-in st.s1, a scan let pass:
        is it in the Pump House, and in dome i by the core's count"""
        game_checks.as_stand_in(ctx, "st.s1", f"dome/{N}/travel/{i}")
        ctx.advance(game_checks.SCAN)
        home = ctx.count(f"@e[tag=st.s1,{domes.sphere(DOME)}]")
        return home, ctx.count(f"@e[tag=st.s1,scores={{st.dome={i}}}]")

    ctx.set_score(f"#d{there}", 2)
    expect(problems, "fast travel before the run starts", travel(there), (1, 0))
    ctx.set_score(f"#d{there}", 0)
    machinery("with a player in the dome")
    ctx.setblock(LEVER, lever(True))
    ctx.advance(3)
    got = game_checks.scores(ctx, "#run", f"#d{N}", f"#t{N}")
    expect(problems, "the lever thrown", got, {"#run": 1, f"#d{N}": 2, f"#t{N}": 1})
    lit = sum(ctx.is_block(c, f"{LAMP}[lit=true]") for c in PANEL_LAMPS)
    expect(problems, "the lever's lamps lit", lit, len(PANEL_LAMPS))
    # put back and thrown again during the run: held over, nothing restarted
    ctx.set_score("#secs", 754)
    ctx.setblock(LEVER, lever(False))
    ctx.advance(3)
    if not ctx.is_block(LEVER, lever(True)):
        problems.append("the lever was not held over during the run")
    ctx.advance(32)
    secs = ctx.score("#secs")
    if secs is None or not 755 <= secs <= 760 or ctx.score("#run") != 1:
        problems.append(f"the run after the lever was put back: clock {secs} s")
    # -- the clocks
    time = _text(ctx, "st.ph.time")
    if '"12:3' not in time:
        problems.append(f"the run's time at 755 s or so reads {time!r}")
    status = _text(ctx, "st.ph.status")
    if "running" not in status:
        problems.append(f"the status during a run reads {status!r}")
    active = ctx.score("#active")
    kept = ctx.score(f"#best{active}")
    for best, shown in ((605, '"10:05"'), (0, '"--:--"')):
        ctx.set_score(f"#best{active}", best)
        ctx.advance(34)
        text = _text(ctx, "st.ph.best")
        if shown not in text:
            problems.append(f"the best time at {best} s reads {text!r}")
    ctx.set_score(f"#best{active}", kept or 0)
    for tag, word in (
        ("st.ph.level", f"DIFFICULTY {level}"),
        ("st.ph.bestl", f"LEVEL {active}"),
    ):
        if word not in (text := _text(ctx, tag)):
            problems.append(f"{SHOWN[tag]} reads {text!r}, not {word}")

    # -- the map follows the scores: the first tunnel pumped by the lever,
    # the rest through locked, open and solved by their scores
    ctx.advance((tunnels.event_ticks(OUT) if N in tunnels.BUILT else 0) + 40)
    expect(problems, "tunnel 0 after the lever", ctx.score(f"#t{N}"), 2)
    ctx.advance(12)
    expect(
        problems,
        "the lamps with the run started",
        lamps(),
        at_reset | {N: 2, N + 1: 1},
    )
    expect(problems, "the lines with tunnel 0 dry", lines(), dark | {N: 1})
    for state in (1, 2):
        for d in layout.DOMES:
            ctx.set_score(f"#d{d.index}", state)
        ctx.advance(12)
        expect(
            problems,
            f"the lamps with every dome at {state}",
            lamps(),
            dict.fromkeys(range(domes_n), state),
        )
        if state == 1:  # open, and nobody there
            expect(problems, "fast travel to an empty dome", travel(there), (1, 0))
    # fast travel: a click by nobody taken up; refused to a locked dome;
    # to a restored one, the stand-in on its entrance and counted in it
    click = f"@e[type=minecraft:interaction,tag=st.ph.go{there},limit=1]"
    ctx.cmd(
        f"data modify entity {click} interaction set value "
        "{player:[I;1,2,3,4],timestamp:0L}"
    )
    ctx.advance(3)
    if ctx.data(f"entity {click} interaction"):
        problems.append("a click on the map was not taken up by the tick")
    locked = N + 2
    ctx.set_score(f"#d{locked}", 0)
    expect(problems, "fast travel to a locked dome", travel(locked), (1, 0))
    ctx.set_score(f"#d{locked}", 2)
    expect(problems, "fast travel to a restored dome", travel(there), (0, 1))
    x, y, z, _ = domes.entrance(layout.DOMES[there])
    near = f"x={x + 0.5},y={y},z={z + 0.5},distance=..1"
    expect(problems, "on the entrance spot", ctx.count(f"@e[tag=st.s1,{near}]"), 1)
    game_checks.stand_in(ctx, "st.s1", N)
    for state, shown in ((1, 0), (2, 1)):
        for t in layout.TUNNELS:
            if t.index != N:
                ctx.set_score(f"#t{t.index}", state)
        ctx.advance(12)
        expect(
            problems,
            f"the lines with the tunnels at {state}",
            lines(),
            dict.fromkeys(range(tunnels_n), shown) | {N: 1},
        )
    # a pump waiting for its lever: shut, and its line dim
    for t in layout.TUNNELS:
        if t.index != N:
            ctx.set_score(f"#t{t.index}", 0)
            ctx.set_score(f"#t{t.index}.ready", 1)
    ctx.advance(12)
    expect(
        problems,
        "the lines with the pumps ready",
        lines(),
        dict.fromkeys(range(tunnels_n), 2) | {N: 1},
    )
    for t in layout.TUNNELS:
        ctx.set_score(f"#t{t.index}.ready", 0)

    # -- the dial: its buttons move the proposal, and it stops at the ends
    top, bottom = LEVELS[-1], LEVELS[0]
    ctx.set_score(DIAL, top - 1)
    press(UP, hold=8)  # held in: one step, not one a tick
    expect(problems, "the dial raised from 9, held", dial(), (top, top, level))
    press(UP)
    expect(problems, "the dial raised at the top", dial(), (top, top, level))
    press(DOWN)
    expect(problems, "the dial lowered from 10", dial(), (top - 1, top - 1, level))
    ctx.set_score(DIAL, bottom + 1)
    press(DOWN)
    press(DOWN)
    expect(problems, "the dial lowered to the bottom", dial(), (bottom, bottom, level))
    text = _text(ctx, "st.ph.dial")
    if f'"{bottom}"' not in text or f'"{level}"' not in text:
        problems.append(f"the dial's text at {bottom}, level {level}: {text!r}")

    # -- the trophy dispenser: armed by the win's function (the run is not
    # won, so no best time is touched), one trophy for the one in the game
    def prize() -> tuple[int | None, bool, int]:
        """armed, the bulb lit, trophies thrown out and not picked up"""
        lit = ctx.is_block(PRIZE_LAMP, LIT)
        return (
            ctx.score(ARMED),
            lit,
            ctx.count(f"@e[type=minecraft:item,tag={ITEM_TAG}]"),
        )

    expect(problems, "the trophy dispenser before the win", prize(), (0, False, 0))
    dx, dy, dz = DISPENSER
    ctx.function(f"dome/{N}/trophy/arm")
    expect(problems, "the dispenser armed at the win", prize(), (1, True, 0))
    if "YOUR TROPHY" not in (text := _text(ctx, "st.ph.prize")):
        problems.append(f"the dispenser's display when armed reads {text!r}")
    game_checks.as_stand_in(ctx, "st.s1", f"dome/{N}/press/trophy")
    expect(problems, "the winner's trophy thrown out", prize(), (0, False, 1))
    item = "@e[type=minecraft:item,tag=" + ITEM_TAG + ",limit=1]"
    sign = ctx.data(f"entity {item} Item")
    for part in ("Trophy: level", "gilded_blackstone", "Wall of Fame"):
        if part not in sign:
            problems.append(f"the trophy thrown out has no {part!r}: {sign[:200]!r}")
    if not ctx.data(f"entity {item} Owner"):
        problems.append("the trophy thrown out can be picked up by anyone")
    inv = ctx.data(f"block {dx} {dy} {dz} Items")
    if inv and inv.strip() not in ("[]", ""):
        problems.append(f"the dispenser holds {inv!r}: it must stay empty")
    # no more: pressed again, or by one who was not in the game at the win
    game_checks.as_stand_in(ctx, "st.s1", f"dome/{N}/press/trophy")
    game_checks.stand_in(ctx, "st.s3", N)
    game_checks.as_stand_in(ctx, "st.s3", f"dome/{N}/press/trophy")
    expect(problems, "pressed again, and by a late comer", prize(), (0, False, 1))
    ctx.cmd("kill @e[tag=st.s3]")
    # armed again for the reset below to clear, a trophy left lying
    ctx.function(f"dome/{N}/trophy/arm")
    game_checks.as_stand_in(ctx, "st.s1", f"dome/{N}/press/trophy")
    ctx.function(f"dome/{N}/trophy/arm")
    expect(problems, "armed again before the reset", prize(), (1, True, 2))

    # -- the votes, from the functions the buttons end in, as two players
    def vote() -> dict[str, int | None]:
        return game_checks.scores(ctx, "#vote.kind", "#vote.value", "#vote.yes")

    def as_player(tag: str, what: str) -> None:
        game_checks.as_stand_in(ctx, tag, f"dome/{N}/press/{what}")

    game_checks.stand_in(ctx, "st.s2", N)
    new = bottom if level != bottom else top
    ctx.set_score(DIAL, level)
    as_player("st.s1", "confirm")
    expect(problems, "confirm with the dial at the level set", vote()["#vote.kind"], 0)
    ctx.set_score(DIAL, new)
    as_player("st.s1", "confirm")
    want_vote = {"#vote.kind": 2, "#vote.value": new, "#vote.yes": 1}
    expect(problems, f"level {new} proposed from the dial", vote(), want_vote)
    as_player("st.s1", "confirm")
    expect(problems, "the proposer confirming again", vote(), want_vote)
    press(UP if new == bottom else DOWN)
    expect(problems, "the dial moved during its vote", ctx.score(DIAL), new)
    ctx.cmd(_setblock(door_cells()[0], door("lower", True)))
    as_player("st.s2", "reset")
    expect(problems, "reset pressed during a level's vote", vote(), want_vote)
    as_player("st.s2", "confirm")
    got = game_checks.scores(ctx, "#vote.kind", "#level")
    expect(
        problems, "the level confirmed by both", got, {"#vote.kind": 0, "#level": new}
    )
    ctx.advance(12)
    expect(problems, "the dial after the vote", dial(), (new, new, new))
    # the reset: nothing through a shut door; then proposed and confirmed
    ctx.cmd(_setblock(door_cells()[0], door("lower")))
    as_player("st.s1", "reset")
    expect(problems, "reset pressed behind a shut door", vote()["#vote.kind"], 0)
    ctx.cmd(_setblock(door_cells()[0], door("lower", True)))
    ctx.cmd(_setblock(door_cells()[1], door("upper", True)))
    as_player("st.s1", "reset")
    want_vote = {"#vote.kind": 1, "#vote.value": 0, "#vote.yes": 1}
    expect(problems, "a reset proposed", vote(), want_vote)
    ctx.set_score(DIAL, level)
    as_player("st.s2", "confirm")
    expect(problems, "the dial's confirm during a reset's vote", vote(), want_vote)
    # a click nobody made: taken up by the tick and cleared, no vote cast
    click = "@e[type=minecraft:interaction,tag=st.ph.reset,limit=1]"
    ctx.cmd(
        f"data modify entity {click} interaction set value "
        "{player:[I;0,0,0,1],timestamp:0L}"
    )
    ctx.advance(3)
    if ctx.data(f"entity {click} interaction"):
        problems.append("a click on the reset button was not taken up by the tick")
    expect(problems, "a click by nobody", vote(), want_vote)
    as_player("st.s2", "reset")
    ctx.advance(30)
    names = ("#vote.kind", "#run", "#secs", f"#d{N}", f"#t{N}", "#level", DIAL)
    got = game_checks.scores(ctx, *names)
    want_scores = dict.fromkeys(names, 0) | {f"#d{N}": 1, "#level": new, DIAL: new}
    expect(problems, "the reset confirmed by both", got, want_scores)
    machinery("after the reset")

    # -- the reset: everything back, and the map
    want[LEVER] = lever(False)
    for i in LEVELS:
        want[dial_lamp(i)] = LIT if i <= new else UNLIT
        want[dial_pointer(i)] = BRASS if i == new else COPPER
    # a stand-in is still in the dome, so the governor runs: its pistons and
    # their brass may be caught in mid stroke
    stroke = {c for p in G_PISTONS for c in (p, (p[0], p[1] + 1, p[2]))}
    wrong = [
        c
        for c, b in sorted(want.items())
        if not ctx.is_block(c, b)
        and not (c in stroke and ctx.is_block(c, "minecraft:moving_piston"))
    ]
    if wrong:
        problems.append(
            f"{len(wrong)} blocks are not put back by the reset, the first at "
            f"{wrong[0]}: not {want[wrong[0]]}"
        )
    for d in layout.DOMES:
        if d.index != N and ctx.score(f"#d{d.index}") != 0:
            problems.append(f"dome {d.index} is not locked after the reset")
    expect(problems, "the map's lamps after the reset", lamps(), at_reset)
    expect(problems, "the map's lines after the reset", lines(), dark)
    status = _text(ctx, "st.ph.status")
    if "lever" not in status or '"0:00"' not in _text(ctx, "st.ph.time"):
        problems.append(f"the boards after the reset: {status!r}")
    book = ctx.data(f"block {LECTERN[0]} {LECTERN[1]} {LECTERN[2]} Book")
    if "Good luck" not in book:
        problems.append("the log is not on the lectern after the reset")
    items = ctx.count(f"@e[type=minecraft:item,{domes.sphere(DOME)}]")
    expect(problems, "dropped items in the dome", items, 0)
    expect(problems, "the trophy dispenser after the reset", prize(), (0, False, 0))
    owed = ctx.count(f"@e[tag={DUE}]")
    expect(problems, "trophies owed after the reset", owed, 0)

    # -- the level put back, the dome still dry
    ctx.set_score("#level", level)
    game_checks.fresh(ctx)
    ctx.advance(30)
    expect(problems, "the dial at the end", dial(), (level, level, level))
    # dry and whole
    problems += domes.check_shell(ctx, DOME, empty=False)
    return problems


MODULE = game.Module(
    "start",
    stages={"start_dome_inside": build},
    functions=functions,
    wins=(f"dome/{N}/trophy/arm",),
    checks={"start_dome": check},
)
