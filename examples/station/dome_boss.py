"""
The Engine (the last dome, the boss dome) of The Drowned Station: the last room
of the ring. Its build stage (``dome_<n>_inside``), its datapack functions
(``dome/<n>/...``) and its live check (``boss``).

**The one idea.** Starve the Engine of steam by winding shut its three
steam mains, each on a different level of the dome, while it sends
automatons to move you off them; then (phase 2) fight what comes out of
the firebox when the last one shuts.

**The switch.** ``PHASE_2`` (below) is the one switch of this module, and
it is on. On, the third main starts the breach: the firebox doors are
forced from inside and the Master comes out on his ravager; the win is
their death. Off, the fight ends when the third main shuts: that is the
win. The room, the mains and phase 1 are the same either way, and phase
2's functions are in the pack only when the switch is on, so that a line
of theirs the game refuses cannot stop the pack that phase 1 needs. What
phase 2 assumes and no server has yet shown is listed at ``PHASE_2``.

**Phase 2, in order.** *The breach* (7 s, no fighting): the automatons
are gone; the lights fail (the lanterns in the floor dim to copper bulbs,
``floor_lights``, and the players are given the Darkness effect for a few
seconds); a title, "THE MAINS ARE SHUT"; the Master's red bossbar comes
up empty and fills as he breaks out; knocking in the firebox; its doors
are forced in three bangs from the middle outwards. Nobody can stand in
the porch or the firebox meanwhile (``breach/clear``). *The Master*
(``master/out``): Old Grinder, a ravager, comes out of the firebox with
the Master on its back (``master_nbt``: a husk a quarter bigger than
life, in the whole golden suit trimmed with copper, a golden axe, his
name in gold over him); a title, "THE MASTER", a roar. The bar is their
two healths added; their health is by who is in the dome when he comes
out (170% for two, 50% more for each beyond) and by the level. The
ravager dead, he fights on foot; both dead is the win: the bar goes, the
lanterns come back, and the end is phase 1's own (``won``).

- *No outlasting him.* With nobody in the arena (all dead or in the
  pavilion) the pair cannot be hurt, and after ``mend`` they mend about
  two points a second. The high level, where the ravager cannot follow,
  is steamed seven seconds in fourteen once a player has been up for five.
- *The dead respawn in the antechamber*: the core's respawn point for
  this dome is its entrance spot, in the pavilion, which no mob stays in
  (``fence``: the ravager is put back at ``back``, carrying its rider).
  Dying costs the walk back; the Master keeps his wounds.
- *A rider that draws armour.* A ravager fights by itself only under a
  rider of the game's entity tag ``#minecraft:raiders`` (the rig: it bit
  under a vindicator and only carried a husk). No illager draws armour,
  so the pack adds the husk to that tag (``RIDER_MOB``). The live check
  sets a golem before the pair and reports a ravager that does not bite.

**A main** (``Main``: A on the floor to the right of the way in, B on the
gallery to the left, over the way out, C on the high platform behind the
Engine) is a real lever on a brass post with a sign (the room's only
inputs: ``inputs``), a gauge of five lamps and a deck. It *winds* while
its lever is over and a player stands on its deck: a lamp every 3 s at
level 5, and at the fifth it is shut for good: the lever is taken away,
its gauge turns green, its telltales on the Engine's drum go out. Left
alone it winds open again, a lamp every 2 s. Automatons cannot work
levers: all they can do is move a player off a deck.

- *Solo form:* each main winds alone, in any order.
- *Two-player form:* mains A and B wind only together, a player on each
  deck; with one side ready neither winds nor drains, and an amber lamp
  blinks at the ready station. Main C winds for one. If only one of A
  and B is still open it winds alone.

The form here follows **who is in the arena**, not who is in the dome:
the arena is the dome less the pavilion at the entrance (where the dead
respawn, the logbook is read and a partner may stand idle). Two-player
with two or more in the arena, solo 3 s after there are fewer
(``form/count``). The core's ``solo`` and ``duo`` hooks only ask for a
count at once. A change to the two-player form waits for the room's safe
point: while a player is winding A or B it is put off (``form/change``),
so nothing is ever stopped under a hand. A change to solo stops nothing
and is taken at once.

**Leaving** costs the gauge being wound and no more: when the dome
empties in phase 1 (``empty``, 3 s after the last player went) the open
mains' levers go back and their gauges empty, and the shut mains stay
shut until the game's reset. In phase 2 the Master is removed and comes
out again at full health when a player next walks into the arena.

**Automatons** are the core's three kinds (automatons.py), one at a time
from four hatches in the Engine's plinth, at a hatch with a player in
reach of it, up to a cap that grows with each main shut; any that gets
into the pavilion is put back at its hatch. Their dress, team, loot,
count and removal are the core's.

**State** (scores in ``st``, all ``#b7.<name>``): ``phase`` 0 watchful,
1 the mains, 2 the breach, 3 the Master, 4 the Master waiting (the dome
emptied in 2 or 3), 5 over; ``na`` players in the arena, ``want`` and
``form`` the form asked for and the one in force, ``grace`` the steps
since there were two; for each main x: ``g<x>`` its gauge (a lamp is
``LAMP``), ``l<x>`` shut or not, ``r<x>`` ready this step, ``w<x>``
winding this step; ``shut`` how many are shut; ``amb`` which of A and B
waits for the other; ``t`` steps in the phase; ``next`` steps to the next
automaton, ``cap`` the cap now, ``hatch`` the hatch last used; ``live`` 1
once the room is set up; ``out`` the lamps of the way out lit. From the
level in force when an untouched room is first entered (``scaled``):
``rate``, ``drain``, ``cnt``, ``hp``, ``mend``, ``steam``.

**Functions** (the core calls the hooks, see game.py):

- ``enter``: the first into a room with no main shut sets it up
  (``arm``: the level's values);
- ``tick``: the governor turned, the hints, and every ``STEP`` ticks
  ``step``: who is in the arena and the form, the machinery (``dress``),
  then the function of the phase (``p0``, ``p1``, and with the switch
  on ``breach/step``, ``p3``, ``p4``);
- ``solo`` / ``duo``: a count of the arena at once;
- ``leave`` / ``died``: the player is out of the arena;
- ``empty``: the stage in progress put back (see "Leaving");
- ``reset``: everything as built, and all that ``empty`` does;
- ``won``: the one call of ``station:dome/<n>/solved`` (the trophy is the
  Pump House's: ``dome_start``, "The trophy").

**The room** (``dressing_blocks``; everything is placed in the dome's own
frame, forward from the entrance, right, up from the floor). Three levels
round a centrepiece that goes from the floor to the glass:

- *the floor*: the pavilion at the way in (four piers, a roof, waist-high
  sides; the plaque, the logbook, the recall post), the Engine on its
  plinth with the firebox doors in its face at the back of a porch, main
  A under the gallery, nine columns, the lamps of the way out set in the
  floor towards the exit airlock, three ramps;
- *the gallery*, a ring of copper grating on the columns six up, the
  pavilion's roof its balcony, main B on its inner edge;
- *the high level*, twelve up: the crown deck round the Engine's drum,
  four catwalks in a cross, the platform of main C, reached by a stair
  one block wide (which automatons climb and a ravager cannot) and three
  ladders.

Machinery that works by itself, none of it an input and none of it read:

- the *cylinders*: two caged engine houses either side of the porch, in
  plain view from the pavilion, each a real redstone torch clock
  (``fittings.torch_clock``) with a lamp chase in its bed and two plain
  pistons working in turn. Nothing starts, stops or resets them;
- the *governor* on the Engine's crown: block displays turned by the
  pack, slowly while the Engine watches, faster with each main shut,
  racing in the breach, run down to a stop when it is over;
- the *brow*: twelve lamps in the Engine's face that count the run's
  clock in binary, minutes over seconds. Nobody is told;
- steam at each open main and from the chimney, and a heartbeat that
  quickens as the mains shut.

``room_problems`` checks all of it with no server, and the build refuses
a room that fails: every cell inside the dome and off the cells the
tunnels reserve, every input on gold with a sign, every walk the fight
needs clear at foot and head height with the firebox shut and open, and
the gauges and telltales in sight from where they are needed. The
pavilion stands between the entrance spot and the outgoing door's window
on purpose (``domes.allow``, below): it is the antechamber.
"""

from __future__ import annotations

import math
import re
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
from fittings import Frame, frame, label_text, sign_text, snbt

if TYPE_CHECKING:
    from station_layout import Dome

INDEX = layout.index_of("boss")  # the Engine's place in the ring
OBJ = game.OBJ

# ============================================================================
# THE SWITCH. True: the third main starts the breach and phase 2 (the Master
# on his ravager). False: the room, the mains and phase 1, and the third main
# shut is the win. The rig (PROGRESS, "Rig, second round") proved, against an
# iron golem: a ravager with a vindicator up hunts and bites by itself with
# ``mob_griefing`` off and the vindicator strikes from its back; with a husk
# up it only carries, and the husk strikes; it passes under a deck 5 up,
# climbs stairs 3 and 2 wide and not 1 wide; ``damage @s <n>
# minecraft:generic`` from a function hurts (husks). What the rig did not
# show, as written here (the live check, passed on 26 Nov 2026, reads all but
# 1, 7 and 8 back; PROGRESS, "Round 2 live"):
#
# 1. any of the pair's fight against a player, and the Master fighting on
#    foot once the ravager dies;
# 2. ``#minecraft:raiders`` with the husk added by this pack lets the
#    ravager fight under him: shown live (the tag took; the golem was bitten
#    with the husk up);
# 3. the Master's NBT: the trims (``components:{"minecraft:trim":...}``),
#    ``minecraft:scale`` in ``attributes``, ``CustomName`` as a compound,
#    ``CustomNameVisible`` (the check reads each back; that they are drawn,
#    and how he sits at that size, only an eye can tell);
# 4. ``Team`` in the NBT of the ravager and of its passenger puts both on the
#    automatons' team, so that a Riveter's stray arrow starts no fight;
# 5. the core's ``station:mob/dress`` (max health, attack damage, ``Health``)
#    works on a ravager and its rider, called ``with storage``; ``data get
#    entity <mob> Health`` stored in a score reads their health;
# 6. ``effect give`` of Resistance 5 and of Regeneration takes on both, and
#    a teleport of the ravager carries its rider (the pavilion's fence);
# 7. the steam's ``damage`` and the Darkness effect on a player;
# 8. the pair passes the firebox's doorway (5 wide, 5 high).
#
# Should the ravager stop biting under the husk, ``RIDER_MOB`` (below) set to
# the vindicator is the pair the rig proved, at the cost of the armour.
# ============================================================================
PHASE_2 = True

domes.allow(
    INDEX,
    "the pavilion",
    "the antechamber where the dead respawn stands round the entrance spot, "
    "its roof and piers between the spot and the outgoing door's window",
)

STEP = 10  # ticks between steps of the state machine
LAMP = 600  # a lamp of a main's gauge
LAMPS = 5
FULL = LAMP * LAMPS  # a main is shut here
SOLO_STEPS = game.SOLO_AFTER  # steps with fewer than two in the arena: solo
# at level 5, scaled by the core's percentages (``scaled``)
WIND = 100  # a step of winding: a lamp every 3 s
DRAIN = 150  # a step left alone: a lamp every 2 s
CAP = {1: 3, 2: 5}  # automatons alive at once with no main shut, by form
GAP = {1: 10, 2: 7}  # steps between automatons, by form
FIRST = 8  # steps from the first lever to the first automaton
NEAR = 30  # a hatch is used with a player this close
RIVETERS = {1: 2, 2: 3}  # the most Riveters alive, by form
MEND = 10  # steps with nobody in the arena before the Master mends
# phase 2
RAVAGER_HP, RAVAGER_DAMAGE = 100, 120  # as ``mob/dress`` takes them
MASTER_HP, MASTER_DAMAGE = 40, 50
#: who rides the ravager. A husk draws armour, and the rig saw one ride and
#: strike from a ravager's back; a ravager fights by itself only under a
#: rider of the game's tag ``#minecraft:raiders``, so the pack puts the
#: husk in that tag (``RAIDERS_TAG``). ``minecraft:vindicator`` is the pair
#: the rig proved whole (the ravager bites under him), and he is in the tag
#: already; but an illager draws no armour: he is a grey coat with an axe
RIDER_MOB = "minecraft:husk"
RAIDERS_TAG = "minecraft:raiders"
#: the mobs that tag holds in the game itself
RAIDERS = ("evoker", "illusioner", "pillager", "ravager", "vindicator", "witch")
MASTER_NAME, MOUNT_NAME = "The Master", "Old Grinder"
MASTER_SCALE = 1.25  # a quarter bigger than a man
#: his brass: the players' own (the core's kit for this dome is a golden
#: helm and cuirass), the whole suit, trimmed in copper
MASTER_KIT = {
    "head": "minecraft:golden_helmet",
    "chest": "minecraft:golden_chestplate",
    "legs": "minecraft:golden_leggings",
    "feet": "minecraft:golden_boots",
}
MASTER_TRIM = ("minecraft:copper", "minecraft:silence")  # material, pattern
MASTER_AXE = "minecraft:golden_axe"
TWO_PLAYERS, MORE_PLAYERS = 170, 50  # percent of health for two, and each more
EARLY = 10  # steps: the pair lost sooner than this is no win
ROAR = 6  # steps a player is in the arena before the Master comes out again
BREACH = (4, 6, 8, 10, 14)  # steps: the knock, the doors' three bangs, out
VENT_AFTER, VENT_CYCLE, VENT_WARN, VENT_BLOW = 10, 28, 6, 14  # steps
ESCORT_FROM = 110  # ``#diff.health`` from which the Master has an escort
DARK = 8  # seconds of the Darkness effect when the mains shut
#: what the floor's lanterns become while the Master is about: a dim lamp
#: (light 8, where a sea lantern gives 15)
DIM = "minecraft:waxed_weathered_copper_bulb[lit=true]"

BRASS = "minecraft:gold_block"
COPPER = "minecraft:waxed_copper_block"
EXPOSED = "minecraft:waxed_exposed_copper"
WEATHERED = "minecraft:waxed_weathered_copper"
OXIDIZED = "minecraft:waxed_oxidized_copper"
CUT = "minecraft:waxed_cut_copper"
CHISELED = "minecraft:waxed_chiseled_copper"
GRATE = "minecraft:waxed_copper_grate"
BULB = "minecraft:waxed_copper_bulb"
GREEN_BULB = "minecraft:waxed_oxidized_copper_bulb"  # a shut main's gauge
AMBER = "minecraft:ochre_froglight"  # "waiting for the other main"
BARS = "minecraft:iron_bars"
ROD = "minecraft:waxed_lightning_rod"
STAIRS = "minecraft:waxed_cut_copper_stairs"
TIMBER = "minecraft:dark_oak_planks"
STONE = "minecraft:polished_blackstone"
BRICKS = "minecraft:polished_blackstone_bricks"
TILES = "minecraft:deepslate_tiles"
LADDER = "minecraft:ladder"
LANTERN = "minecraft:lantern[hanging=true]"

ENTITY_TAG = "st.b7"  # everything the build summons here
RECALL_TAG = "st.recall7"
GOVERNOR_TAG = "st.b7.gov"
ARENA = "st.b7.arena"  # a player or stand-in in the dome and out of the pavilion
BOSS, RAVAGER, RIDER = "st.b7.boss", "st.b7.rav", "st.b7.rider"
#: the governor's turn a tick, in degrees: the speeds the pack uses
SPEEDS = (2, 4, 6, 9, 12, 16, 24)

FR = tuple[int, int]  # a place in the frame: forward, right
FRH = tuple[int, int, int]  # and its height above the floor

# ---------------------------------------------------------------- the plan
# where things are, in the frame

PAV_F, PAV_R = (-30, -21), 5  # the pavilion, front to back, and half its width
ARCH_R = 3  # half the width of its arch
PLAQUE = (-24, 4)  # the middle of the brass wall, on the right inside
LECTERN = (-27, 4)
RECALL = (-28, -4, 1)  # the recall post: f, r, side
PIER_H = 5

PLINTH = ((8, 12), (7, 11))  # the plinth's two courses, as octagons
BODY, BODY_H = (6, 9), (3, 11)
DRUM, DRUM_H, CAP_H = 3, (13, 17), 18
FACE_F = -6  # the plane of the Engine's face
DOOR_R, DOOR_H = 2, 5  # the firebox doors: half their width, their height
FIREBOX_F = (-5, -1)
PORCH_F = (-8, -7)
HATCHES = ((-6, -6), (-6, 6), (6, -6), (6, 6))
EYES_H, BROW_H = 7, (10, 9)  # the brow's rows: minutes over seconds
BROW_R = (3, 2, 1, -1, -2, -3)  # its lamps, the lowest bit first
CHIMNEY, CHIMNEY_H = (2, 0), (19, 26)
GOVERNOR = (-2, 0)
GOVERNOR_H = 21

GALLERY_H, RING = 6, (19.0, 25.0)  # the gallery's deck and its ring's radii
HIGH_H = 12  # the high level's deck
COLUMNS = (
    (-18, 13),
    (-18, -13),
    (-6, 21),
    (-6, -21),
    (6, 21),
    (6, -21),
    (18, 13),
    (18, -13),
    (22, 3),
)
#: the ramps to the gallery, each three wide: the stairs' rows (the cells
#: of the lowest step first, a row a step) and the step of the frame they
#: climb by
RAMPS = (
    (tuple(tuple((f, r) for r in (16, 17, 18)) for f in range(-22, -17)), (1, 0)),
    (tuple(tuple((f, r) for r in (-18, -17, -16)) for f in range(-22, -17)), (1, 0)),
    (tuple(tuple((f, r) for r in (-1, 0, 1)) for f in range(29, 24, -1)), (-1, 0)),
)
C_STAIR_F, C_STAIR_R = 17, (8, 7, 6, 5, 4)  # the stair to main C, lowest first
PLATFORM = ((15, 21), (-3, 3))  # main C's platform
#: the catwalks of the high level, each with a lane of rail on both sides
CATWALKS = (
    ((9, 14), (-1, 2)),
    ((-23, -9), (-1, 2)),
    ((3, 6), (8, 22)),
    ((3, 6), (-22, -8)),
)
#: the ladders from the gallery to the high level: the ladder's cell, the
#: post it is on
LADDERS = (((4, 21), (4, 22)), ((4, -21), (4, -22)), ((-22, 0), (-23, 0)))
CYLINDER_F, CYLINDER_R = -11, 6  # the cylinders' clocks, right and left
WAY_OUT_R = range(-9, -29, -1)  # the lamps of the way out, from the Engine


@dataclass(frozen=True)
class Main:
    """a steam main: its lever, gauge and deck"""

    key: str  # "a": in the names of its scores and functions
    name: str  # "A"
    post: fittings.Post  # the brass post that carries its lever
    lever: Cell
    lever_off: str  # the lever's block, not thrown
    lever_on: str
    sign: Cell
    label: str  # the tag of its floating label
    gauge: tuple[Cell, ...]  # five lamps, the lowest first
    #: the lamp that says "waiting for the other main" (main C has one too,
    #: to look the same: it waits for nobody, and its lamp is never lit)
    amber: Cell
    deck: tuple[Cell, Cell]  # the box a player holds it from
    stand: Cell  # a place on the deck (feet)
    look: Cell  # a place on the deck that the gauge and telltales are read from
    telltales: tuple[Cell, ...]  # its lamps on the drum, a face each
    steam: Cell  # where its relief steams
    where: str  # for a line of chat


@dataclass(frozen=True)
class Room:
    """where the Engine's working parts are"""

    frame: Frame
    mains: tuple[Main, Main, Main]
    doors: dict[Cell, str]  # the firebox doors, as built
    door_columns: tuple[tuple[Cell, ...], ...]  # by the order they are forced
    firebox: tuple[Cell, Cell]  # the corners of its inside
    spot: Cell  # where the Master comes out
    porch: tuple[Cell, Cell]  # the box in front of the doors
    back: Cell  # where one standing in the porch is put at the breach
    hatches: tuple[Cell, ...]  # where automatons appear
    eyes: tuple[Cell, Cell]
    brow: tuple[tuple[Cell, ...], tuple[Cell, ...]]  # minutes, seconds: low bit first
    way_out: tuple[Cell, ...]
    lectern: Cell
    recall: tuple[int, int, int]
    pavilion: tuple[Cell, Cell]  # the box that is not the arena
    fence: tuple[Cell, Cell]  # the box no mob may be in
    high: tuple[Cell, Cell]  # the box of the high level, for the steam
    vents: tuple[Cell, ...]  # where the high level's steam shows
    governor: Cell
    chimney: Cell  # where its smoke rises
    arch: Cell  # just outside the pavilion's arch (feet)
    cylinders: tuple[fittings.Machine, fittings.Machine]


def octagon(big: int, total: int) -> set[FR]:
    """the places within ``big`` of the middle each way and ``total`` in all"""
    span = range(-big, big + 1)
    return {(f, r) for f in span for r in span if abs(f) + abs(r) <= total}


def rect(fs: tuple[int, int], rs: tuple[int, int]) -> set[FR]:
    return {(f, r) for f in range(fs[0], fs[1] + 1) for r in range(rs[0], rs[1] + 1)}


def ring(inner: float, outer: float) -> set[FR]:
    """the places whose distance from the middle is in [inner, outer)"""
    span = range(-math.ceil(outer), math.ceil(outer) + 1)
    return {(f, r) for f in span for r in span if inner <= math.hypot(f, r) < outer}


def edge(cells: set[FR]) -> set[FR]:
    """the places of a deck with open air beside them"""
    return {
        (f, r)
        for f, r in cells
        if any(
            (f + df, r + dr) not in cells
            for df, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
        )
    }


def gallery() -> tuple[set[FR], set[FR]]:
    """the gallery's deck (the ring and the pavilion's roof, less the
    wells the ramps come up through) and its rails"""
    deck = ring(*RING) | rect(PAV_F, (-PAV_R, PAV_R))
    mouths: set[FR] = {(C_STAIR_F, C_STAIR_R[0] + 1)}
    for rows, (df, dr) in RAMPS:
        deck -= {place for row in rows for place in row}
        mouths |= {(f + df, r + dr) for f, r in rows[-1]}
    return deck, edge(deck) - mouths


def high_level() -> tuple[set[FR], set[FR], set[FR]]:
    """the high level's deck (the crown deck, the catwalks, main C's
    platform), its rails, and the holes in it over the ladders"""
    deck = octagon(*PLINTH[0]) | rect(*PLATFORM)
    for fs, rs in CATWALKS:
        deck |= rect(fs, rs)
    holes = {ladder for ladder, _ in LADDERS}
    mouths = {(C_STAIR_F, C_STAIR_R[-1] - 1)}
    return deck, edge(deck) - mouths, holes


def engine_volume() -> set[FRH]:
    """the Engine as a solid: plinth, body, drum and cap, less the porch,
    the firebox, the doorway and the hatches"""
    v: set[FRH] = set()
    for h, course in enumerate(PLINTH, 1):
        v |= {(f, r, h) for f, r in octagon(*course)}
    for h in range(BODY_H[0], BODY_H[1] + 1):
        v |= {(f, r, h) for f, r in octagon(*BODY)}
    square = rect((-DRUM, DRUM), (-DRUM, DRUM))
    for h in range(DRUM_H[0], CAP_H + 1):
        v |= {(f, r, h) for f, r in square}
    v -= {(f, r, h) for f, r in rect(PORCH_F, (-ARCH_R, ARCH_R)) for h in (1, 2)}
    v -= firebox_places() | set(door_places())
    v -= {(f, r, 1) for f, r in HATCHES}
    return v


def firebox_places() -> set[FRH]:
    return {
        (f, r, h)
        for f, r in rect(FIREBOX_F, (-DOOR_R, DOOR_R))
        for h in range(1, DOOR_H + 1)
    }


def door_places() -> dict[FRH, str]:
    """the firebox doors: brass, riveted, a grate to see the glow by"""
    doors = {}
    for r in range(-DOOR_R, DOOR_R + 1):
        for h in range(1, DOOR_H + 1):
            if abs(r) <= 1 and h == 3:
                block = GRATE
            elif r == 0 or h in (1, DOOR_H):
                block = CHISELED
            else:
                block = BRASS
            doors[FACE_F, r, h] = block
    return doors


def engine_block(f: int, r: int, h: int, lining: bool) -> str:
    """the block of the Engine's shell at a place"""
    if lining:  # the firebox: it glows at the back
        return "minecraft:ochre_froglight" if f == FIREBOX_F[1] + 1 else STONE
    if f == FACE_F and abs(r) == DOOR_R + 1 and h <= DOOR_H:
        return CUT  # the doors' jambs
    if h <= 2:
        return CUT if h == 2 and (f, r) in edge(octagon(*PLINTH[1])) else BRICKS
    if h <= BODY_H[1]:
        if h in (5, 10):
            return CUT
        if abs(f) + abs(r) == BODY[1] and BODY[0] in (abs(f), abs(r)):
            return CHISELED
        return (COPPER, EXPOSED, COPPER, WEATHERED, EXPOSED)[
            (7 * f + 13 * r + 5 * h) % 5
        ]
    if h == CAP_H or h == DRUM_H[1] or (abs(f) == DRUM and abs(r) == DRUM):
        return CUT
    return WEATHERED


def _mains(fr: Frame) -> tuple[Main, Main, Main]:
    """the three mains: A on the floor, B on the gallery, C on the high
    platform. Each lever is on the side of its post away from the Engine,
    so a player working it has the Engine, and what it sends, in view"""
    right, left = fr.facing(0, 1), fr.facing(0, -1)
    drum = ((0, DRUM), (0, -DRUM), (DRUM, 0), (-DRUM, 0))  # the faces
    # the post, the side of it the lever is on, the gauge, the amber lamp's
    # post, the deck's reach forward and right, where a player stands on
    # it, and where the gauge and telltales are read from
    spec = {
        "a": ((2, 21), (0, 1), (-2, 21), (4, 21), (-3, 3), (22, 26), (0, 23), (3, 23)),
        "b": (
            (2, -19),
            (0, -1),
            (-2, -19),
            (4, -19),
            (-3, 3),
            (-24, -20),
            (0, -21),
            (3, -21),
        ),
        "c": ((15, -2), (1, 0), (15, 3), (15, -3), (16, 20), (-2, 2), (17, 0), (19, 0)),
    }
    feet = {"a": 1, "b": GALLERY_H + 1, "c": HIGH_H + 1}
    steam = {"a": (0, 21, 3), "b": (0, -19, 9), "c": (13, -2, 17)}
    where = {
        "a": f"on the floor to the {right}, under the gallery",
        "b": f"on the gallery to the {left}, over the way out",
        "c": "on the high platform behind the Engine",
    }
    found = []
    for i, key in enumerate("abc"):
        post_at, step, gauge, amber, deck_f, deck_r, stand, look = spec[key]
        h = feet[key]
        facing = fr.facing(*step)
        name = key.upper()
        label = f"{ENTITY_TAG}.label.{key}"
        post = fittings.input_post(
            fr.at(*post_at, h),
            facing,
            fittings.lever(facing),
            main_sign(name, "solo"),
            f"MAIN {name}",
            (ENTITY_TAG, label),
        )
        sign = next(c for c, b in post.attached.items() if "sign" in b)
        found.append(
            Main(
                key=key,
                name=name,
                post=post,
                lever=post.input,
                lever_off=fittings.lever(facing),
                lever_on=fittings.lever(facing, on=True),
                sign=sign,
                label=label,
                gauge=tuple(fr.at(*gauge, h + k) for k in range(LAMPS)),
                amber=fr.at(*amber, h + 2),
                deck=(
                    fr.at(deck_f[0], deck_r[0], h),
                    fr.at(deck_f[1], deck_r[1], h + 1),
                ),
                stand=fr.at(*stand, h),
                look=fr.at(*look, h),
                telltales=tuple(fr.at(f, r, DRUM_H[1] - i) for f, r in drum),
                steam=fr.at(*steam[key]),
                where=where[key],
            )
        )
    return (found[0], found[1], found[2])


def main_sign(name: str, state: str) -> tuple[str, ...]:
    """what a main's sign says: ``solo``, ``pair`` (it winds only with
    the other of A and B) or ``shut``"""
    other = {"A": "B", "B": "A"}.get(name, "")
    how = {
        "solo": ("Throw the lever", "and stand here", "till 5 lamps."),
        "pair": ("Winds only", "together with", f"main {other}."),
        "shut": ("", "SHUT", ""),
    }[state]
    return (f"STEAM MAIN {name}", *how)


@cache
def room(dome: Dome) -> Room:
    fr = frame(dome)
    doors = {fr.at(*place): block for place, block in door_places().items()}
    columns = tuple(
        tuple(fr.at(FACE_F, r, h) for r in rs for h in range(1, DOOR_H + 1))
        for rs in ((0,), (-1, 1), (-DOOR_R, DOOR_R))
    )
    cylinders = tuple(
        fittings.torch_clock(
            fr,
            CYLINDER_F,
            side * CYLINDER_R,
            2,
            side=-side,
            lamps=True,
            pistons=True,
            block=COPPER,
            bed=CUT,
        )
        for side in (1, -1)
    )
    reach = dome.radius
    return Room(
        frame=fr,
        mains=_mains(fr),
        doors=doors,
        door_columns=columns,
        firebox=(fr.at(FIREBOX_F[0], -DOOR_R, 1), fr.at(FIREBOX_F[1], DOOR_R, DOOR_H)),
        spot=fr.at(-3, 0, 1),
        porch=(fr.at(-10, -ARCH_R, 1), fr.at(PORCH_F[1], ARCH_R, 3)),
        back=fr.at(-16, 0, 1),
        hatches=tuple(fr.at(f, r, 1) for f, r in HATCHES),
        eyes=(fr.at(FACE_F, -2, EYES_H), fr.at(FACE_F, 2, EYES_H)),
        brow=(
            tuple(fr.at(FACE_F, r, BROW_H[0]) for r in BROW_R),
            tuple(fr.at(FACE_F, r, BROW_H[1]) for r in BROW_R),
        ),
        way_out=tuple(
            cell
            for cell in (fr.at(0, r, 0) for r in WAY_OUT_R)
            if cell not in domes.light_cells(dome)[0]
        ),
        lectern=fr.at(*LECTERN, 1),
        recall=RECALL,
        pavilion=(fr.at(-reach - 2, -PAV_R, 0), fr.at(PAV_F[1], PAV_R, PIER_H)),
        # (the same box: where a mob may not be, a player is not in the
        # arena, so nobody shoots from a place nothing can reach)
        fence=(fr.at(-reach - 2, -PAV_R, 0), fr.at(PAV_F[1], PAV_R, PIER_H)),
        high=(fr.at(-reach, -reach, HIGH_H + 1), fr.at(reach, reach, reach)),
        vents=tuple(
            fr.at(f, r, HIGH_H + 2) for f, r in ((12, 0), (-15, 1), (4, 14), (5, -14))
        ),
        governor=fr.at(*GOVERNOR, GOVERNOR_H),
        chimney=fr.at(*CHIMNEY, CHIMNEY_H[1] + 2),
        arch=fr.at(PAV_F[1] + 1, 0, 1),
        cylinders=(cylinders[0], cylinders[1]),
    )


def scaled(level: int) -> dict[str, int]:
    """the room's values at a level, as the function ``scale`` works them
    out: at a low level a main winds faster and drains slower, there are
    fewer automatons, and the Master is weaker and mends later"""
    core = game.scaled(level)
    return {
        "rate": WIND * 100 // core["#diff.damage"],
        "drain": DRAIN * core["#diff.damage"] // 100,
        "cnt": core["#diff.count"],
        "hp": core["#diff.health"],
        "mend": MEND * core["#diff.timer"] // 100,
        "steam": (2 * core["#diff.damage"] + 50) // 100,
    }


def cap(level: int, form: int, shut: int) -> int:
    """the automatons alive at once, as the function ``pour`` works it out"""
    return max(1, ((CAP[form] + shut) * scaled(level)["cnt"] + 50) // 100)


def exit_name(dome: Dome) -> str:
    """the compass name of the side the way out is on"""
    return domes.COMPASS[domes.outward(dome, layout.TUNNELS[dome.index])]


def plaque_signs() -> tuple[tuple[str, ...], ...]:
    last = (
        ("Then face", "what it", "answers to.")
        if PHASE_2
        else ("Starve it", "of steam and", "it stops.")
    )
    return (
        ("THE ENGINE", "Master Engine", "No. 1"),
        ("Shut its three", "steam mains:", "A, B and C."),
        last,
    )


LOG_TITLE, LOG_AUTHOR = "Engine House log", "O. Finch"


def log_pages(dome: Dome) -> list[str]:
    """the last log of Chief Engineer O. Finch: four pages, each short
    enough for a page of a book (fourteen lines of some nineteen letters)"""
    fr = frame(dome)
    right, left = fr.facing(0, 1), fr.facing(0, -1)
    end = (
        "Shut the third and he must come out."
        if PHASE_2
        else "Shut the third and it stops."
    )
    return [
        "Engine House log\nO. Finch, Chief Engineer\n\nLast entry. You came all "
        "the way round the ring: in an hour you did what I could not do in a "
        "year.\n\nRead this, then finish it.",
        "The Engine thinks with steam. Three mains feed it: A on the floor, "
        f"{right}; B on the gallery, {left}; C high up behind it.\n\nThrow a "
        "main's lever and stand by it till five lamps light. Step away and it "
        "winds open.",
        "It will send its automatons to move you. Do not be moved. If two of "
        "you come, it will make mains A and B wind only together.\n\nI shut "
        "two, once. Then the firebox doors opened from inside.",
        "It had stopped listening to me. It listens to Marsh. He wears our "
        "brass, rides what it cast him, and calls himself the Master.\n"
        f"{end}\nGo home by the {exit_name(dome)} airlock.\nO. Finch",
    ]


def logbook(dome: Dome, pages: int | None = None) -> str:
    """the lectern with the log on it (``pages``: only the first so many,
    for a command short enough for RCON)"""
    fr = frame(dome)
    return fittings.lectern_with_book(
        fr.facing(0, -1), LOG_TITLE, LOG_AUTHOR, log_pages(dome)[:pages]
    )


# --------------------------------------------------------------- the blocks


@dataclass
class Blocks:
    """every block the room is made of, as built and as ``reset`` leaves it"""

    floor: dict[Cell, str] = field(default_factory=dict)  # relaid floor
    solid: dict[Cell, str] = field(default_factory=dict)
    attached: dict[Cell, str] = field(default_factory=dict)  # need a support
    clear: set[Cell] = field(default_factory=set)  # air, to be kept so
    #: cells whose block's state changes by itself (a clock's dust, its
    #: repeaters, its lamps, its pistons), and the cells its pistons' heads
    #: rise into: a check must not expect them still
    moving: set[Cell] = field(default_factory=set)

    def everything(self) -> dict[Cell, str]:
        return {**self.floor, **self.solid, **self.attached}

    def above(self) -> dict[Cell, str]:
        """all but the floor"""
        return {**self.solid, **self.attached}

    def add(self, other: Blocks) -> None:
        """take in another set of blocks; no cell may be given twice"""
        mine, theirs = self.everything(), other.everything()
        if both := (set(mine) | self.clear) & (set(theirs) | other.clear):
            raise ValueError(f"cells given two blocks: {sorted(both)[:5]}")
        self.floor |= other.floor
        self.solid |= other.solid
        self.attached |= other.attached
        self.clear |= other.clear
        self.moving |= other.moving


def room_blocks(dome: Dome, open_doors: bool = False) -> Blocks:
    """the Engine's blocks, the fight's and the room's (``open_doors``: as
    the breach leaves the firebox). The two forms differ in no block: only
    in what the signs of mains A and B say"""
    b = puzzle_blocks(dome)
    b.add(dressing_blocks(dome))
    if open_doors:
        for cell in room(dome).doors:
            del b.solid[cell]
            b.clear.add(cell)
    return b


def puzzle_blocks(dome: Dome) -> Blocks:
    """the blocks the fight reads or changes, and the room's fittings, as
    ``reset`` leaves them"""
    place = room(dome)
    fr = place.frame
    b = Blocks()

    # the plaque (on the pavilion's right side, facing in), the logbook and
    # the recall post
    side = Frame(fr.origin, fr.right, (-fr.forward[0], -fr.forward[1]))
    solid, attached = fittings.plaque_blocks(
        side, PLAQUE[1], -PLAQUE[0], signs=plaque_signs()
    )
    b.solid |= solid
    b.attached |= attached
    b.solid[place.lectern] = logbook(dome)
    solid, attached = fittings.recall_post_blocks(fr, *place.recall)
    b.solid |= solid
    b.attached |= attached

    # the mains: a lever on a brass post, a gauge of five lamps, a short
    # post with the amber lamp
    for main in place.mains:
        b.solid |= main.post.solid
        b.attached |= main.post.attached
        for cell in main.gauge:
            b.solid[cell] = f"{BULB}[lit=false]"
        x, y, z = main.amber
        b.solid[x, y - 2, z] = b.solid[x, y - 1, z] = CUT
        b.solid[main.amber] = CUT
        for cell in main.telltales:
            b.solid[cell] = f"{BULB}[lit=true]"

    # the Engine's face: the firebox doors, the eyes, the counting brow
    b.solid |= place.doors
    for cell in place.eyes:
        b.solid[cell] = f"{BULB}[lit=true]"
    for row in place.brow:
        for cell in row:
            b.solid[cell] = f"{BULB}[lit=false]"
    for h in BROW_H:
        b.solid[fr.at(FACE_F, 0, h)] = CHISELED
    lo, hi = place.firebox
    b.clear |= {
        (x, y, z)
        for x in range(min(lo[0], hi[0]), max(lo[0], hi[0]) + 1)
        for y in range(lo[1], hi[1] + 1)
        for z in range(min(lo[2], hi[2]), max(lo[2], hi[2]) + 1)
    }
    b.clear |= set(place.hatches)

    # the lamps of the way out, in the floor
    for cell in place.way_out:
        b.floor[cell] = f"{BULB}[lit=false]"
    return b


def dressing_blocks(dome: Dome) -> Blocks:
    """the room round the fight (see the module docstring): built once,
    and left alone by every function of the pack"""
    place = room(dome)
    fr = place.frame
    taken = puzzle_blocks(dome)
    used = set(taken.everything()) | taken.clear
    inside = domes.dome_cells(dome).interior - tunnels.reserved_cells(dome)
    d = Blocks()

    def put(where: FRH, block: str, attached: bool = False, clip: bool = False) -> None:
        """a block of the dressing: the first given to a cell stays, and
        the fight's cells are never touched (``clip``: left out where the
        dome's wall or a way in is, for what stands against them)"""
        cell = fr.at(*where)
        if cell in used or (clip and cell not in inside):
            return
        used.add(cell)
        (d.attached if attached else d.solid)[cell] = block

    def rod(way: str = "up") -> str:
        return f"{ROD}[facing={way}]"

    def stairs(step: FR) -> str:
        return f"{STAIRS}[facing={fr.facing(*step)},half=bottom]"

    # -- the cylinders, either side of the porch: a torch clock each, on a
    # pedestal, in a cage of bars under a grating, an exhaust on top
    for side, machine in zip((1, -1), place.cylinders, strict=True):
        cells = set(machine.bed) | set(machine.solid) | set(machine.attached)
        d.solid |= machine.bed | machine.solid
        d.attached |= machine.attached
        d.moving |= machine.moving
        used |= cells | machine.moving
        rs = sorted((side * (CYLINDER_R - 1), side * (CYLINDER_R + 1)))
        house = rect((CYLINDER_F - 2, CYLINDER_F + 2), (rs[0], rs[1]))
        cage = rect((CYLINDER_F - 3, CYLINDER_F + 3), (rs[0] - 1, rs[1] + 1))
        for f, r in house:
            put((f, r, 1), CUT)
        for f, r in cage:
            if (f, r) not in house:
                for h in (1, 2, 3):
                    put((f, r, h), BARS)
            put((f, r, 4), GRATE)
        for f in (CYLINDER_F, CYLINDER_F + 1):
            put((f, side * (CYLINDER_R - 1), 5), CHISELED)
            put((f, side * (CYLINDER_R - 1), 6), rod())

    # -- the mains' valve bodies (a lump of green copper with a wheel on the
    # side its deck is on) and their pipes from the Engine
    bodies = (
        (rect((-1, 1), (19, 20)), range(1, 6), (0, 20, 3)),
        (rect((-1, 1), (-18, -17)), range(7, 11), (0, -18, 8)),
        (rect((13, 14), (-3, -1)), range(HIGH_H, 17), (14, -2, 15)),
    )
    for places, heights, hub in bodies:
        for f, r in places:
            for h in heights:
                near = max(abs(f - hub[0]), abs(r - hub[1]), abs(h - hub[2]))
                put(
                    (f, r, h), CHISELED if near == 0 else CUT if near == 1 else OXIDIZED
                )
    pipes = (
        (rect((-1, 0), (BODY[0] + 1, 18)), (4, 5), 1),
        (rect((-1, 0), (-16, -BODY[0] - 1)), (7, 8), 1),
        (rect((DRUM + 1, 12), (-2, -1)), (15, 16), 0),
    )
    for places, heights, along in pipes:
        for f, r in places:
            for h in heights:
                put((f, r, h), CHISELED if (f, r)[along] % 4 == 0 else EXPOSED)
    for r in (11, 15):  # main A's pipe stands on two trestles
        for f in (-1, 0):
            for h in (1, 2, 3):
                put((f, r, h), rod())

    # -- the Engine: its shell (it is hollow), the chimney, the governor's
    # spindle, lanterns in the firebox
    volume = engine_volume()
    doors = set(door_places())
    fire = firebox_places()
    high, rails, holes = high_level()
    faces = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))

    def filled(where: FRH) -> bool:
        f, r, h = where
        under_deck = h == HIGH_H and (f, r) in high
        return where in volume or where in doors or h == 0 or under_deck

    for f, r, h in sorted(volume):
        beside = [(f + i, r + j, h + k) for i, j, k in faces]
        if all(filled(c) for c in beside):
            continue
        put((f, r, h), engine_block(f, r, h, any(c in fire for c in beside)))
    cf, cr = CHIMNEY
    for h in range(CHIMNEY_H[0], CHIMNEY_H[1] + 1):
        for df in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if df or dr:
                    put((cf + df, cr + dr, h), CUT if h % 4 == 3 else WEATHERED)
    put((cf + 1, cr, CHIMNEY_H[1] + 1), rod())
    for h in range(CAP_H + 1, GOVERNOR_H + 1):
        put((*GOVERNOR, h), rod())

    # -- the high level: the crown deck, the catwalks and main C's platform,
    # railed; the ladders' posts stand through it
    square = rect((-DRUM, DRUM), (-DRUM, DRUM))
    for f, r in sorted(high - holes):
        put((f, r, HIGH_H), CUT if (f, r) in square else GRATE)
    for f, r in sorted(rails - holes):
        put((f, r, HIGH_H + 1), BARS)
    for h in range(GALLERY_H + 1, HIGH_H):  # the stair to main C, one wide
        r = C_STAIR_R[h - GALLERY_H - 1]
        put((C_STAIR_F, r, h), stairs((0, -1)))
        put((C_STAIR_F, r, h - 1), TIMBER)
        for f in (C_STAIR_F - 1, C_STAIR_F + 1):
            put((f, r, h + 1), BARS)
    for (lf, lr), (pf, pr) in LADDERS:
        for h in range(GALLERY_H + 1, HIGH_H + 1):
            put((pf, pr, h), CUT)
            put((lf, lr, h), f"{LADDER}[facing={fr.facing(lf - pf, lr - pr)}]", True)
    for f, r in ((11, 0), (-12, 1), (-18, 0), (4, 12), (5, 17), (4, -12), (5, -17)):
        put((f, r, HIGH_H - 1), LANTERN, attached=True)

    # -- the gallery: a ring of grating on nine columns, the pavilion's roof
    # its balcony, railed but where a ramp or the stair comes up
    deck, rails = gallery()
    roof = rect(PAV_F, (-PAV_R, PAV_R))
    for f, r in sorted(deck):
        put((f, r, GALLERY_H), CUT if (f, r) in roof else GRATE, clip=True)
    for f, r in sorted(rails):
        put((f, r, GALLERY_H + 1), BARS, clip=True)
    for f, r in COLUMNS:
        for h in range(1, GALLERY_H - 1):
            put((f, r, h), CHISELED if h == 1 else CUT)
        put((f, r, GALLERY_H - 1), f"{BULB}[lit=true]")
    for rows, step in RAMPS:
        for h, row in enumerate(rows, 1):
            for f, r in row:
                put((f, r, h), stairs(step))
                if h > 1:
                    put((f, r, h - 1), TIMBER)

    # -- the pavilion: four piers, waist-high sides, lanterns under the roof
    front, back = PAV_F[1], PAV_F[0]
    for f in (back, back + 1, front - 1, front):
        for r in (PAV_R - 1, PAV_R):
            for side in (-1, 1):
                for h in range(1, PIER_H + 1):
                    put((f, side * r, h), CHISELED if h == PIER_H else CUT, clip=True)
    for f in range(back + 2, front - 1):
        for side in (-1, 1):
            put((f, side * PAV_R, 1), CUT)
    for r in (-3, 3):
        put((-25, r, GALLERY_H - 1), LANTERN, attached=True)

    # -- the floor: a machine bed of blackstone, rings of copper round the
    # Engine and under the gallery, eight spokes of tiles between them; the
    # outer ring and the lanterns stay the core's
    lights = domes.light_cells(dome)[0]
    for f, r in ring(0, 29.5):
        cell = fr.at(f, r, 0)
        if cell in lights or cell in taken.floor:
            continue
        far = math.hypot(f, r)
        if 11.5 <= far < 12.5 or 18.5 <= far < 19.5:
            block = CUT
        elif 12.5 <= far < 18.5 and (f == 0 or r == 0 or abs(f) == abs(r)):
            block = TILES
        else:
            block = STONE
        d.floor[cell] = block

    # -- each main's deck in cut copper, on the floor, the gallery and the
    # platform alike: the sign's "stand here" has a here
    for main in place.mains:
        (x1, y, z1), (x2, _, z2) = main.deck
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                for part in (d.floor, d.solid):
                    if part.get((x, y - 1, z)) in (STONE, GRATE):
                        part[x, y - 1, z] = CUT
    return d


#: what stands on or hangs from a block and is still in the way
IN_THE_WAY = ("minecraft:lantern",)
#: small things a player sees past, for the sight lines
SEE_PAST = ("lever", "ladder", "lantern", "button")


def _name(block: str) -> str:
    return block.partition("[")[0].partition("{")[0]


def _up(cell: Cell, by: int = 1) -> Cell:
    return (cell[0], cell[1] + by, cell[2])


def inputs(dome: Dome) -> set[Cell]:
    """every block of the room a player works: the three levers, and the
    recall post's button"""
    place = room(dome)
    f, r, side = place.recall
    return {m.lever for m in place.mains} | {place.frame.at(f, r + side, 2)}


def walks(dome: Dome) -> dict[str, Cell]:
    """where a player must be able to walk to from the entrance, by name:
    the cell their feet are in"""
    place = room(dome)
    fr = place.frame
    out = layout.TUNNELS[dome.index]
    ux, uz = domes.outward(dome, out)
    ox, oy, oz = dome.floor_centre
    mouth = dome.radius - 3
    f, r, side = place.recall
    targets = {
        "the way out": (ox + ux * mouth, oy + 1, oz + uz * mouth),
        "the plaque": fr.at(PLAQUE[0], PLAQUE[1] - 2, 1),
        "the logbook": fr.at(LECTERN[0], LECTERN[1] - 1, 1),
        "the recall button": fr.at(f, r + 2 * side, 1),
        "the arch": place.arch,
        "the porch": fr.at(PORCH_F[0] - 1, 0, 1),
        "the balcony": fr.at(-26, 0, GALLERY_H + 1),
        "the gallery, north": fr.at(0, 22, GALLERY_H + 1),
        "the gallery, west": fr.at(22, -6, GALLERY_H + 1),
        "the crown deck": fr.at(0, -6, HIGH_H + 1),
        "the east catwalk": fr.at(-21, 1, HIGH_H + 1),
        "the north catwalk": fr.at(5, 20, HIGH_H + 1),
        "the south catwalk": fr.at(5, -20, HIGH_H + 1),
        "where the Master is put back": place.back,
    }
    for main in place.mains:
        targets[f"main {main.name}'s deck"] = main.stand
        targets[f"main {main.name}'s gauge"] = main.look
        x, y, z = main.lever
        targets[f"main {main.name}'s lever"] = (x, main.stand[1], z)
    for (lf, lr), (pf, pr) in LADDERS:
        # (beside the ladder, on the side away from its post)
        beside = (2 * lf - pf, 2 * lr - pr)
        targets[f"the foot of the ladder at {lf}, {lr}"] = fr.at(*beside, GALLERY_H + 1)
        targets[f"the head of the ladder at {lf}, {lr}"] = fr.at(*beside, HIGH_H + 1)
    for i, (rows, (df, dr)) in enumerate(RAMPS):
        f, r = rows[-1][1]
        targets[f"the head of ramp {i}"] = fr.at(f + df, r + dr, GALLERY_H + 1)
    return targets


def _walkable(b: Blocks) -> tuple[set[Cell], set[Cell]]:
    """a plan as ``rooms.reach`` takes it: what can be stood on, and what
    else a player cannot be in (a rail of bars is a block and a half high:
    it is not stepped over)"""
    blocked = set(b.moving)
    blocked |= {c for c, block in b.attached.items() if _name(block) in IN_THE_WAY}
    blocked |= {_up(c) for c, block in b.solid.items() if _name(block) == BARS}
    return set(b.solid), blocked


def walk_problems(dome: Dome) -> list[str]:
    """
    Every place of ``walks`` can be walked to from the entrance without a
    ladder, with the firebox shut and with it open (and then its inside
    too): feet and head in free cells with something to stand on, a step
    to a cell beside, level or one up or down. The two forms are one
    plan: nothing a player walks on differs between them.
    """
    problems = []
    for what, opened in (("shut", False), ("open", True)):
        solid, blocked = _walkable(room_blocks(dome, open_doors=opened))
        targets = walks(dome)
        if opened:
            targets["the firebox"] = room(dome).spot
        problems += [
            f"the firebox {what}: {p}"
            for p in rooms.walk_problems(dome, solid, targets, blocked)
        ]
    return problems


def sights(dome: Dome) -> dict[str, tuple[Cell, dict[str, Cell]]]:
    """what the fight depends on seeing: name of the place -> (where the
    player stands, what must be in sight from there)"""
    place = room(dome)
    faces = {"a": 0, "b": 1, "c": 2}  # the drum's face each deck looks at
    found: dict[str, tuple[Cell, dict[str, Cell]]] = {}
    for main in place.mains:
        seen = {f"lamp {k} of its gauge": c for k, c in enumerate(main.gauge, 1)}
        seen["its amber lamp"] = main.amber
        for other in place.mains:
            seen[f"main {other.name}'s telltale"] = other.telltales[faces[main.key]]
        found[f"main {main.name}'s deck"] = (main.look, seen)
    face = {f"the firebox doors at {c}": c for c in place.door_columns[0]}
    face |= {"the left eye": place.eyes[0], "the right eye": place.eyes[1]}
    face |= {f"the brow's lamp at {c}": c for row in place.brow for c in row}
    face |= {f"main {m.name}'s telltale": m.telltales[3] for m in place.mains}
    found["the arch"] = (place.arch, face)
    return found


def sight_problems(dome: Dome) -> list[str]:
    """each thing of ``sights`` is in sight from its place: nothing but
    grating, bars, rods and glass on the line from the eye to its middle"""
    blocks = {
        cell: block
        for cell, block in room_blocks(dome).above().items()
        if not any(word in _name(block) for word in SEE_PAST)
    }
    problems = []
    for where, (eye, targets) in sights(dome).items():
        problems += rooms.sight_problems(blocks, {where: eye}, targets)
    return problems


def room_problems(dome: Dome) -> list[str]:
    """the room's plan against its dome and the rules of rooms.py: every
    cell inside the dome and off the cells the tunnels reserve, the relaid
    floor in the floor, the inputs on gold with a sign and nothing beside
    them that redstone would work, the walks clear, what must be seen in
    sight"""
    try:
        b = room_blocks(dome)
    except ValueError as e:
        return [str(e)]
    place = room(dome)
    more = b.clear | b.moving | {place.spot, place.governor, place.chimney}
    more |= {m.steam for m in place.mains} | set(place.vents)
    problems = fittings.placement_problems(dome, set(b.above()) | more)
    problems += rooms.room_problems(dome, b.above(), b.floor, more)
    problems += rooms.input_problems(b.above(), inputs(dome), floor=b.floor)
    problems += rooms.window_problems(dome, b.above())
    lights = domes.light_cells(dome)[0]
    if lost := set(b.floor) & lights:
        problems.append(f"{len(lost)} of the floor's lanterns are relaid")
    return problems + walk_problems(dome) + sight_problems(dome)


# --------------------------------------------------------------- the build

IDENTITY = "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]"
#: the governor: (block, where its low corner is from the spindle's top,
#: its size): two brass balls on a cross arm, and a hub
GOVERNOR_PARTS = (
    (BRASS, (1.1, -0.9, -0.35), (0.7, 0.7, 0.7)),
    (BRASS, (-1.8, -0.9, -0.35), (0.7, 0.7, 0.7)),
    (CUT, (-1.5, -0.1, -0.1), (3.0, 0.2, 0.2)),
    (CHISELED, (-0.3, -0.3, -0.3), (0.6, 0.6, 0.6)),
)


def governor_summons(dome: Dome) -> list[str]:
    """the commands that summon the governor: block displays that all
    stand at the top of the spindle, so that turning them (``gov/spin``)
    swings the arm and its balls round it"""
    x, y, z = room(dome).governor
    at = f"{x + 0.5} {y + 1} {z + 0.5}"
    return [
        f"summon minecraft:block_display {at} "
        f'{{Tags:["{ENTITY_TAG}","{GOVERNOR_TAG}"],teleport_duration:1,'
        f"block_state:{fittings.block_state(block)},transformation:{{"
        f"translation:[{dx}f,{dy}f,{dz}f],scale:[{sx}f,{sy}f,{sz}f],{IDENTITY}}}}}"
        for block, (dx, dy, dz), (sx, sy, sz) in GOVERNOR_PARTS
    ]


def summons(dome: Dome) -> list[str]:
    """everything the build summons: the recall post's interaction, the
    mains' labels, the governor"""
    place = room(dome)
    found = [
        fittings.summon_recall(
            place.frame, *place.recall, tags=(ENTITY_TAG, RECALL_TAG)
        )
    ]
    for main in place.mains:
        found += main.post.summons
    return found + governor_summons(dome)


def build(ctx: Any) -> str:
    """the Engine inside its shell; takes the stub's bypass away, wipes
    what was inside but the pump engine, and leaves the room as ``reset``
    does"""
    dome = ctx.layout.DOMES[INDEX]
    if problems := room_problems(dome):
        raise RuntimeError("the Engine: " + "; ".join(problems))
    place = room(dome)
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    engine = set(tunnels.engine_cells(ctx.layout.TUNNELS[INDEX]).values())
    for command in game.clear_stub_commands(dome):
        ctx.cmd(command)
    ctx.cmd(f"kill @e[tag={ENTITY_TAG}]")
    ctx.cmd(f"kill @e[tag={BOSS}]")
    ctx.cmd(f"kill {automatons.selector(INDEX)}")
    ctx.fill_boxes(cells.interior - engine, AIR)
    # by block, a box at a time; then what has text (a sign: its text has
    # spaces), and last the cylinders' redstone, a block at a time in the
    # order the shared clock gives it, as it was proved to start
    clocks = {c for c in b.attached if c in b.moving}
    for part in (b.floor, b.solid, b.attached):
        plain = {c: block for c, block in part.items() if c not in clocks}
        for block, where in sorted(domes.by_block(plain).items()):
            if "{" not in block:
                ctx.fill_boxes(where, block)
    for cell, block in sorted(b.above().items()):
        if "{" in block and cell != place.lectern:
            ctx.setblock(cell, block)
    for cell, block in b.attached.items():
        if cell in clocks:
            ctx.setblock(cell, block)
    # the log: a page a command, each short enough for RCON
    x, y, z = place.lectern
    ctx.setblock(place.lectern, logbook(dome, pages=1))
    for page in log_pages(dome)[1:]:
        ctx.cmd(
            f"data modify block {x} {y} {z} {fittings.BOOK_PAGES} "
            f"append value {snbt(page)}"
        )
    for command in summons(dome):
        ctx.cmd(command)
    # the pack's own idea of the room, if the pack is installed
    ctx.function(f"dome/{INDEX}/reset")
    ctx.advance(10)
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    return (
        f"{dome.name}: {len(b.everything())} blocks: the pavilion (plaque, "
        "logbook, recall post), the Engine (firebox, eyes, brow, drum, chimney, "
        "governor), 3 steam mains, the gallery and 3 ramps, the high level (crown "
        "deck, 4 catwalks, main C's platform, its stair, 3 ladders), 2 caged "
        f"cylinders, the way out; phase 2 {'on' if PHASE_2 else 'off'}"
    )


# ----------------------------------------------------------- the functions


def _s(name: str) -> str:
    return f"#b7.{name} {OBJ}"


def _set(name: str, value: int) -> str:
    return f"scoreboard players set {_s(name)} {value}"


def _add(name: str, value: int = 1) -> str:
    return f"scoreboard players add {_s(name)} {value}"


def _op(name: str, op: str, other: str) -> str:
    return f"scoreboard players operation {_s(name)} {op} {other} {OBJ}"


def _if(name: str, what: int | str) -> str:
    return f"if score {_s(name)} matches {what}"


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


def _setblock(cell: Cell, block: str) -> str:
    return f"setblock {_xyz(cell)} {block}"


def _lamp(cell: Cell, score: str, lit: str, dark: str) -> list[str]:
    """one lamp that is ``lit`` while a score is 1 or more"""
    return fittings.gauge_lines([cell], score, 1, lit, dark)


def floor_lights(dome: Dome) -> tuple[Cell, ...]:
    """the core's lanterns in this dome's floor that the breach dims: all
    but any that touches the room's redstone (a cylinder's clock, a main's
    post), since what they become is a copper bulb, which a pulse beside
    it would flip"""
    b = room_blocks(dome)
    live = set(b.moving)
    for main in room(dome).mains:
        live |= main.post.cells
    near = {
        (x + dx, y + dy, z + dz)
        for x, y, z in live
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        for dz in (-1, 0, 1)
    }
    lights = domes.light_cells(dome)[0]
    return tuple(sorted(lights - near - set(b.everything()) - b.clear))


def rider_is_raider() -> bool:
    """whether the Master's mob is one the game itself lets a ravager
    fight under"""
    return RIDER_MOB.removeprefix("minecraft:") in RAIDERS


def master_nbt(tags: tuple[str, ...], common: str) -> str:
    """the Master as a passenger: named in gold over his head, a quarter
    bigger than life, in the whole brass suit trimmed with copper and with
    a golden axe, none of which he drops. (On a vindicator the suit is
    worn and not drawn.)"""
    material, pattern = MASTER_TRIM
    trim = (
        f'components:{{"minecraft:trim":{{material:"{material}",pattern:"{pattern}"}}}}'
    )
    worn = [
        f'{slot}:{{id:"{item}",count:1,{trim}}}' for slot, item in MASTER_KIT.items()
    ]
    worn.append(f'mainhand:{{id:"{MASTER_AXE}",count:1}}')
    kept = ",".join(f"{slot}:0f" for slot in (*MASTER_KIT, "mainhand"))
    attributes = [f'{{id:"minecraft:scale",base:{MASTER_SCALE}d}}']
    more = ""
    if RIDER_MOB.removeprefix("minecraft:") in automatons.ZOMBIES:
        attributes.append('{id:"minecraft:spawn_reinforcements",base:0d}')
        more = "IsBaby:0b,"
    listed = ",".join(f'"{t}"' for t in tags)
    return (
        f'{{id:"{RIDER_MOB}",Tags:[{listed}],'
        f'CustomName:{{text:"{MASTER_NAME}",color:"gold",bold:true}},'
        f"CustomNameVisible:1b,{common},{more}"
        f"attributes:[{','.join(attributes)}],"
        f"equipment:{{{','.join(worn)}}},drop_chances:{{{kept}}}}}"
    )


def pair_summon(
    where: str, mount_tags: tuple[str, ...], rider_tags: tuple[str, ...], common: str
) -> str:
    """the command that summons the ravager with the Master on its back
    (``common``: NBT both are given)"""
    listed = ",".join(f'"{t}"' for t in mount_tags)
    return (
        f"summon minecraft:ravager {where} "
        f'{{Tags:[{listed}],CustomName:"{MOUNT_NAME}",{common},'
        f"Passengers:[{master_nbt(rider_tags, common)}]}}"
    )


def master_summon(spot: Cell) -> str:
    """
    The command that summons the pair of phase 2: Old Grinder, a ravager,
    with the Master (``RIDER_MOB``, ``master_nbt``) on its back. Written
    here, as ``automatons.summon`` has no passengers; it follows that
    function's rules by hand: both named, on the automatons' team,
    persistent, picking nothing up, dropping nothing. They carry this
    dome's own tags and not the automatons', so that the core does not
    sweep them from round the entrance when a player respawns, nor dress
    them as a wave.
    """
    common = (
        f'Team:"{automatons.TEAM}",PersistenceRequired:1b,CanPickUpLoot:0b,'
        f'DeathLootTable:"station:{automatons.LOOT}"'
    )
    return pair_summon(middle(spot), (BOSS, RAVAGER), (BOSS, RIDER), common)


def clock_torches(place: Room) -> dict[Cell, str]:
    """the torches of the cylinders' clocks: taken out, the pistons stop"""
    return {
        cell: block
        for machine in place.cylinders
        for cell, block in machine.attached.items()
        if "redstone_wall_torch" in block
    }


def functions(pack: dp.Pack) -> None:
    """the Engine's functions (see the module docstring)"""
    dome = layout.DOMES[INDEX]
    place = room(dome)
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    open_dome = f"if score #d{INDEX} {OBJ} matches 1"
    arena = f"@e[tag={ARENA}]"
    boss = f"@e[tag={BOSS}]"
    heart = place.spot  # where the Engine's sounds come from
    torches = clock_torches(place)  # out at the win, back at the reset
    pack.constants(OBJ, 2, 4, 8, 16, 32, 50, 60, 100)

    def fid(name: str) -> str:
        return pack.id(f"{base}/{name}")

    def call(name: str) -> str:
        return f"function {fid(name)}"

    def sound(name: str, cell: Cell, volume: float = 1, pitch: float = 1) -> str:
        return f"playsound minecraft:{name} block {here} {_xyz(cell)} {volume} {pitch}"

    def say(text: str, colour: str = "yellow", who: str = here) -> str:
        return f'tellraw {who} {{text:{snbt(text)},color:"{colour}"}}'

    def title(text: str, sub: str, colour: str = "red") -> list[str]:
        return [
            f"title {here} times 5 50 10",
            f'title {here} subtitle {{text:{snbt(sub)},color:"yellow"}}',
            f'title {here} title {{text:{snbt(text)},color:"{colour}"}}',
        ]

    def box(corners: tuple[Cell, Cell]) -> str:
        return dp.box_selector(*corners)

    start = fittings.hint(
        pack,
        INDEX,
        "start",
        "The log on the lectern says how to stop it: throw the lever at a "
        "steam main and stand by it.",
        45,
    )
    pair = fittings.hint(
        pack,
        INDEX,
        "pair",
        f"Two of you: mains A and B wind only together. A is "
        f"{place.mains[0].where}; B is {place.mains[1].where}.",
        10,
    )
    bar = automatons.bar(pack, INDEX, "The Master")
    remove_boss = f"execute as {boss} run function {pack.id('mob/remove')}"

    # -- the values of the level in force
    pack.function(
        f"{base}/scale",
        [
            _set("rate", WIND * 100),
            _op("rate", "/=", "#diff.damage"),
            _set("drain", DRAIN),
            _op("drain", "*=", "#diff.damage"),
            _op("drain", "/=", "#100"),
            _op("cnt", "=", "#diff.count"),
            _op("hp", "=", "#diff.health"),
            _set("mend", MEND),
            _op("mend", "*=", "#diff.timer"),
            _op("mend", "/=", "#100"),
            _op("steam", "=", "#diff.damage"),
            _op("steam", "+=", "#diff.damage"),
            _add("steam", 50),
            _op("steam", "/=", "#100"),
        ],
    )
    pack.function(
        f"{base}/arm",
        [
            call("scale"),
            _set("live", 1),
            start.arm,
            pair.arm,
            f"function {pack.id('fight/difficulty')}",
        ],
    )

    # -- who is in the arena, and the form that follows them
    pack.function(
        f"{base}/form/count",
        [
            f"tag {arena} remove {ARENA}",
            f"tag @e[tag=st.in,scores={{st.dome={INDEX}}}] add {ARENA}",
            f"tag @e[tag={ARENA},{box(place.pavilion)}] remove {ARENA}",
            f"execute store result score {_s('na')} if entity {arena}",
            # two-player with two in the arena, solo 3 s after there are fewer
            f"execute {_if('na', '2..')} run {_set('want', 2)}",
            f"execute {_if('na', '2..')} run {_set('grace', 0)}",
            f"execute {_if('na', '..1')} {_if('want', 2)} run {_add('grace')}",
            f"execute {_if('grace', f'{SOLO_STEPS}..')} run {_set('want', 1)}",
            f"execute unless score {_s('want')} matches 2 run {_set('want', 1)}",
            f"execute {_if('want', 1)} run {_set('grace', 0)}",
            f"execute unless score {_s('form')} = {_s('want')} run {call('form/change')}",
        ],
    )
    pack.function(
        f"{base}/form/change",
        [
            # to solo at once: it stops nothing. To the two-player form
            # only at the safe point: not while a player is winding A or B
            f"execute {_if('want', 1)} run {call('form/set')}",
            f"execute {_if('want', 2)} unless score {_s('ra')} matches 1 "
            f"unless score {_s('rb')} matches 1 run {call('form/set')}",
        ],
    )
    pack.function(
        f"{base}/form/set",
        [
            _op("form", "=", "#b7.want"),
            call("signs"),
            f"execute {open_dome} {_if('phase', '0..1')} {_if('form', 2)} run "
            + say("Two engineers in the arena: mains A and B wind only together."),
            f"execute {open_dome} {_if('phase', 1)} {_if('form', 1)} run "
            + say("One engineer in the arena: each main winds alone."),
        ],
    )
    # the pair: A and B wind only together in the two-player form, and
    # only while both are open
    pack.function(
        f"{base}/form/pair",
        [
            _set("pair", 0),
            f"execute {_if('form', 2)} {_if('la', 0)} {_if('lb', 0)} "
            f"run {_set('pair', 1)}",
        ],
    )
    signs = [call("form/pair")]
    for main in place.mains:
        at = _xyz(main.sign)
        shut = _if(f"l{main.key}", 1)
        is_open = _if(f"l{main.key}", 0)

        def write(state: str, at: str = at, name: str = main.name) -> str:
            return f"data merge block {at} {{{sign_text(main_sign(name, state))}}}"

        signs.append(f"execute {shut} run {write('shut')}")
        if main.key == "c":
            signs.append(f"execute {is_open} run {write('solo')}")
        else:
            signs += [
                f"execute {is_open} {_if('pair', 1)} run {write('pair')}",
                f"execute {is_open} {_if('pair', 0)} run {write('solo')}",
            ]
    pack.function(f"{base}/signs", signs)

    # -- a main: put back open, read, wound, shut
    for main in place.mains:
        k, name = main.key, main.name
        pack.function(
            f"{base}/main/open_{k}",
            [
                _set(f"l{k}", 0),
                _set(f"g{k}", 0),
                _set(f"r{k}", 0),
                _set(f"w{k}", 0),
                *fittings.lever_put_lines(main.lever, main.lever_off),
                *(_setblock(cell, f"{BULB}[lit=false]") for cell in main.gauge),
                _setblock(main.amber, CUT),
                fittings.text_line(main.label, label_text(f"MAIN {name}")),
            ],
        )
        pack.function(
            f"{base}/main/gauge_{k}",
            fittings.gauge_lines(
                main.gauge, _s(f"g{k}"), LAMP, f"{BULB}[lit=true]", f"{BULB}[lit=false]"
            ),
        )
        pack.function(
            f"{base}/main/shut_{k}",
            [
                _set(f"l{k}", 1),
                _set(f"g{k}", FULL),
                _set(f"r{k}", 0),
                _set(f"w{k}", 0),
                _add("shut"),
                _setblock(main.lever, AIR),
                *(_setblock(cell, f"{GREEN_BULB}[lit=true]") for cell in main.gauge),
                _setblock(main.amber, CUT),
                fittings.text_line(
                    main.label, label_text(f"MAIN {name}: SHUT", "green")
                ),
                call("signs"),
                sound("block.iron_door.close", main.lever, 2, 0.6),
                sound("block.fire.extinguish", main.steam, 2, 0.8),
                f"particle minecraft:cloud {middle(main.steam, 0.5)} 0.5 0.5 0.5 0.05 40",
                f'tellraw {here} [{{text:"Main {name} is shut: ",color:"green"}},'
                f'{{score:{{name:"#b7.shut",objective:"{OBJ}"}}}},{{text:" of 3."}}]',
                start.progress,
            ],
        )

    # -- phase 0: the Engine watches until a lever is thrown
    thrown = "minecraft:lever[powered=true]"
    pack.function(
        f"{base}/p0",
        [
            _set("any", 0),
            *(
                f"execute {_if(f'l{m.key}', 0)} if block {_xyz(m.lever)} {thrown} "
                f"run {_set('any', 1)}"
                for m in place.mains
            ),
            f"execute {_if('any', 1)} if score #difficulty {OBJ} matches 1.. "
            f"run {call('p1/wake')}",
            f"execute {_if('any', 1)} unless score #difficulty {OBJ} matches 1.. "
            f"run {call('p0/asleep')}",
        ],
    )
    pack.function(
        f"{base}/p0/asleep",
        [
            *(
                f"execute {_if(f'l{m.key}', 0)} run {line}"
                for m in place.mains
                for line in fittings.lever_put_lines(m.lever, m.lever_off)
            ),
            f"function {pack.id('fight/difficulty')}",
            say("The Engine sleeps while the world is on Peaceful.", "gray"),
        ],
    )
    pack.function(
        f"{base}/p1/wake",
        [
            _set("phase", 1),
            _set("t", 0),
            _set("next", FIRST),
            _set("beat", 0),
            *title("THE ENGINE WAKES", "Hold the mains. Do not be moved."),
            sound("entity.warden.heartbeat", heart, 3, 0.6),
            sound("block.bell.use", heart, 3, 0.5),
            start.progress,
        ],
    )

    # -- phase 1: the mains
    ready = []
    for main in place.mains:
        k = main.key
        ready += [
            _set(f"r{k}", 0),
            f"execute {_if(f'l{k}', 0)} if block {_xyz(main.lever)} {thrown} "
            f"if entity @e[tag={ARENA},{box(main.deck)}] run {_set(f'r{k}', 1)}",
        ]
    pack.function(f"{base}/p1/ready", ready)
    both = f"{_if('pair', 1)} {_if('ra', 1)} {_if('rb', 1)}"
    wind = [
        call("form/pair"),
        *(_set(name, 0) for name in ("wa", "wb", "amb")),
        _op("wc", "=", "#b7.rc"),
        f"execute {_if('pair', 0)} run {_op('wa', '=', '#b7.ra')}",
        f"execute {_if('pair', 0)} run {_op('wb', '=', '#b7.rb')}",
        f"execute {both} run {_set('wa', 1)}",
        f"execute {both} run {_set('wb', 1)}",
        # one side ready and the other not: neither winds, neither drains
        f"execute {_if('pair', 1)} {_if('ra', 1)} {_if('rb', 0)} run {_set('amb', 1)}",
        f"execute {_if('pair', 1)} {_if('ra', 0)} {_if('rb', 1)} run {_set('amb', 2)}",
        f"execute {_if('amb', 0)} run {pair.progress}",
    ]
    for main in place.mains:
        k = main.key
        is_open = _if(f"l{k}", 0)
        held = "" if k == "c" else f"{_if('amb', 0)} "
        wind += [
            f"execute {is_open} {_if(f'w{k}', 1)} run {_op(f'g{k}', '+=', '#b7.rate')}",
            f"execute {is_open} {_if(f'w{k}', 0)} {held}"
            f"run {_op(f'g{k}', '-=', '#b7.drain')}",
            f"execute {_if(f'g{k}', '..-1')} run {_set(f'g{k}', 0)}",
            f"execute {is_open} {_if(f'g{k}', f'{FULL}..')} run {call(f'main/shut_{k}')}",
            f"execute {_if(f'l{k}', 0)} run {call(f'main/gauge_{k}')}",
        ]
    pack.function(f"{base}/p1/wind", wind)

    # -- the automatons: one at a time from a hatch with a player in reach
    def near(cell: Cell) -> str:
        x, y, z = cell
        return (
            f"if entity @e[tag={ARENA},x={x + 0.5},y={y},z={z + 0.5},distance=..{NEAR}]"
        )

    kinds = (automatons.STOKER, automatons.RIVETER, automatons.SLAG_HUSK)
    for i, hatch in enumerate(place.hatches):
        pack.function(
            f"{base}/pour/at_{i}",
            [
                _set("cast", 1),
                call("pour/kind"),
                *(
                    f"execute {_if('kind', j)} run "
                    + automatons.summon_kind(
                        kind, middle(hatch), INDEX, (automatons.home_tag(i),)
                    )
                    for j, kind in enumerate(kinds)
                ),
                # round the Engine a player is often out of sight: they
                # look further than a zombie does, and are set on the
                # nearest player in the arena (a touch "by" them, as the
                # rig proved: a zombie hit takes its hitter as its target)
                f"execute as {automatons.selector(INDEX, f'tag={automatons.NEW}')} "
                "run attribute @s minecraft:follow_range base set 48",
                f"execute as {automatons.selector(INDEX, f'tag={automatons.NEW}')} "
                "at @s run damage @s 0.01 minecraft:mob_attack by "
                f"{game.PLAYERS[:-1]},tag={ARENA},sort=nearest,limit=1]",
                *(automatons.dress_kind_line(INDEX, kind) for kind in kinds),
                f"particle minecraft:large_smoke {middle(hatch, 1)} 0.3 0.5 0.3 0.02 12",
                sound("block.iron_trapdoor.open", hatch, 1.5, 0.6),
            ],
        )
    riveters = automatons.selector(INDEX, f"tag={automatons.RIVETER.tag}")
    pack.function(
        f"{base}/pour/kind",
        [
            # a Stoker; a Slag Husk once two mains are shut; one in four a
            # Riveter, while there are few of them
            _add("n"),
            _set("kind", 0),
            f"execute {_if('shut', '2..')} run {_set('kind', 2)}",
            _op("k", "=", "#b7.n"),
            _op("k", "%=", "#4"),
            f"execute store result score {_s('riv')} if entity {riveters}",
            _set("rivcap", RIVETERS[1]),
            f"execute {_if('form', 2)} run {_set('rivcap', RIVETERS[2])}",
            f"execute {_if('k', 3)} if score {_s('riv')} < {_s('rivcap')} "
            f"run {_set('kind', 1)}",
        ],
    )
    pack.function(
        f"{base}/pour/wait",
        [
            _set("next", GAP[1]),
            f"execute {_if('form', 2)} run {_set('next', GAP[2])}",
        ],
    )
    pack.function(
        f"{base}/pour/one",
        [
            call("pour/wait"),
            _add("hatch"),
            f"execute {_if('hatch', f'{len(place.hatches)}..')} run {_set('hatch', 0)}",
            _set("cast", 0),
            # the next hatch round, if a player is in reach of it; else any
            *(
                f"execute {_if('hatch', i)} {near(hatch)} run {call(f'pour/at_{i}')}"
                for i, hatch in enumerate(place.hatches)
            ),
            *(
                f"execute {_if('cast', 0)} {near(hatch)} run {call(f'pour/at_{i}')}"
                for i, hatch in enumerate(place.hatches)
            ),
        ],
    )
    full = f"if score #mob.alive {OBJ} >= {_s('cap')}"
    room_left = f"if score #mob.alive {OBJ} < {_s('cap')}"
    pack.function(
        f"{base}/pour",
        [
            # the cap: more with two in the arena and with each main shut
            _set("cap", CAP[1]),
            f"execute {_if('form', 2)} run {_set('cap', CAP[2])}",
            _op("cap", "+=", "#b7.shut"),
            _op("cap", "*=", "#b7.cnt"),
            _add("cap", 50),
            _op("cap", "/=", "#100"),
            f"execute {_if('cap', '..0')} run {_set('cap', 1)}",
            automatons.alive_line(INDEX),
            # the gap runs from when there is room for one: an automaton
            # killed is not replaced at once
            f"execute {full} run {call('pour/wait')}",
            f"execute {room_left} run scoreboard players remove {_s('next')} 1",
            f"execute {_if('next', '..0')} {room_left} run {call('pour/one')}",
        ],
    )
    # the pavilion is the antechamber: no mob stays in it
    fence = [
        "execute as "
        + automatons.selector(INDEX, f"tag={automatons.home_tag(i)},{box(place.fence)}")
        + f" run tp @s {middle(hatch)}"
        for i, hatch in enumerate(place.hatches)
    ]
    if PHASE_2:
        fence += [
            f"execute as @e[tag={RAVAGER},{box(place.fence)}] "
            f"run tp @s {middle(place.back)}",
            # (a mount that is teleported carries its rider, and a rider
            # teleported by himself is taken off it: the Master is put
            # back by himself only once he is on foot)
            f"execute unless entity @e[tag={RAVAGER}] as @e[tag={RIDER},"
            f"{box(place.fence)}] run tp @s {middle(place.back)}",
        ]
    pack.function(f"{base}/fence", fence)
    pack.function(
        f"{base}/p1",
        [
            _add("t"),
            call("p1/ready"),
            call("p1/wind"),
            call("pour"),
            call("fence"),
            f"execute {_if('shut', '3..')} run {call('all_shut')}",
        ],
    )
    pack.function(f"{base}/all_shut", [call("breach/start" if PHASE_2 else "won")])

    # -- the end: the one call of the core's ``solved``
    pack.function(
        f"{base}/won",
        [
            _set("phase", 5),
            _set("t", 0),
            _set("out", 0),
            _set("down", len(SPEEDS) - 2),
            *(_set(name, 0) for name in ("wa", "wb", "wc", "ra", "rb", "rc", "amb")),
            automatons.remove_line(INDEX),
            remove_boss,
            bar.hide,
            *([call("lights/full")] if PHASE_2 else []),
            *(_setblock(cell, f"{BULB}[lit=false]") for cell in place.eyes),
            *(_setblock(cell, AIR) for cell in torches),
            sound("block.beacon.deactivate", heart, 3, 0.5),
            sound("block.fire.extinguish", heart, 3, 0.5),
            f"particle minecraft:cloud {middle(place.chimney)} 1 2 1 0.05 200",
            say(
                "The Engine is still. The way out is lit: go home by the "
                f"{exit_name(dome)} airlock.",
                "green",
            ),
            f"function {pack.id(f'dome/{INDEX}/solved')}",
        ],
    )

    # -- the machinery, every step that anyone is in the dome, whatever the
    # state of the fight. No function above reads any of it
    lit, dark = f"{BULB}[lit=true]", f"{BULB}[lit=false]"
    dress = [
        _add("blink"),
        f"execute {_if('blink', '2..')} run {_set('blink', 0)}",
    ]
    for main in place.mains:
        k = main.key
        # a main's telltales: lit while it is open, blinking while it
        # winds, out once it is shut
        dress += [
            _set("x", 1),
            f"execute unless score {_s(f'l{k}')} matches 0 run {_set('x', 0)}",
            f"execute {_if(f'w{k}', 1)} {_if('blink', 1)} run {_set('x', 0)}",
            *(
                line
                for cell in main.telltales
                for line in _lamp(cell, _s("x"), lit, dark)
            ),
            f"execute {_if(f'l{k}', 0)} {open_dome} run particle minecraft:cloud "
            f"{middle(main.steam, 0.5)} 0.2 0.2 0.2 0.02 2",
        ]
    for which, main in ((1, place.mains[0]), (2, place.mains[1])):
        dress += [
            _set("x", 0),
            f"execute {_if('amb', which)} {_if('blink', 1)} run {_set('x', 1)}",
            *_lamp(main.amber, _s("x"), AMBER, CUT),
        ]
    # the governor's speed, by the state of the fight
    speeds = {
        _if("phase", 0): SPEEDS[0],
        f"{_if('phase', 1)} {_if('shut', 0)}": SPEEDS[1],
        f"{_if('phase', 1)} {_if('shut', 1)}": SPEEDS[2],
        f"{_if('phase', 1)} {_if('shut', '2..')}": SPEEDS[3],
        _if("phase", 2): SPEEDS[6],
        f"{_if('phase', 3)} {_if('blink', 0)}": SPEEDS[3],
        f"{_if('phase', 3)} {_if('blink', 1)}": SPEEDS[5],
        _if("phase", 4): SPEEDS[0],
    }
    dress += [
        _set("spin", 0),
        *(
            f"execute {when} run {_set('spin', speed)}"
            for when, speed in speeds.items()
        ),
        # over: it runs down to a stop
        f"execute {_if('phase', 5)} {_if('down', '1..')} "
        f"run scoreboard players remove {_s('down')} 1",
        *(
            f"execute {_if('phase', 5)} {_if('down', i)} run {_set('spin', SPEEDS[i])}"
            for i in range(1, len(SPEEDS) - 1)
        ),
        # the heartbeat: quicker with each main shut
        _add("beat"),
        _set("per", 0),
        f"execute {open_dome} {_if('phase', 0)} run {_set('per', 8)}",
        f"execute {_if('phase', 1)} run {_set('per', 4)}",
        f"execute {_if('phase', 1)} run {_op('per', '-=', '#b7.shut')}",
        f"execute {_if('phase', 3)} run {_set('per', 2)}",
        f"execute {_if('per', '1..')} if score {_s('beat')} >= {_s('per')} "
        f"run {call('beat')}",
        f"execute {_if('blink', 0)} run {call('brow')}",
        f"execute unless score {_s('phase')} matches 5 run particle "
        f"minecraft:campfire_cosy_smoke {middle(place.chimney)} 0.3 1 0.3 0.01 2",
        # the lamps of the way out, one a step once it is over
        f"execute {_if('phase', 5)} {_if('out', f'..{len(place.way_out) - 1}')} "
        f"run {_add('out')}",
        *fittings.gauge_lines(place.way_out, _s("out"), 1, lit, dark),
        f"execute if block {_xyz(place.lectern)} minecraft:lectern[has_book=false] "
        f"run {call('book')}",
    ]
    pack.function(f"{base}/dress", dress)
    pack.function(
        f"{base}/beat",
        [_set("beat", 0), sound("block.note_block.basedrum", heart, 3, 0.5)],
    )
    pack.function(f"{base}/book", [_setblock(place.lectern, logbook(dome))])
    # the brow: the run's clock in binary, minutes over seconds
    brow = [
        _op("m", "=", "#secs"),
        _op("m", "/=", "#60"),
        _op("s", "=", "#secs"),
        _op("s", "%=", "#60"),
    ]
    for value, row in zip(("m", "s"), place.brow, strict=True):
        for bit, cell in enumerate(row):
            brow.append(_op("x", "=", f"#b7.{value}"))
            if bit:
                brow.append(_op("x", "/=", f"#{2**bit}"))
            brow.append(_op("x", "%=", "#2"))
            brow += _lamp(cell, _s("x"), lit, dark)
    pack.function(f"{base}/brow", brow)
    pack.function(
        f"{base}/gov/spin",
        [
            f"execute {_if('spin', speed)} as @e[type=minecraft:block_display,"
            f"tag={GOVERNOR_TAG}] at @s run tp @s ~ ~ ~ ~{speed} ~"
            for speed in SPEEDS
        ],
    )

    # -- the firebox doors
    pack.function(
        f"{base}/face/shut", [_setblock(c, b) for c, b in place.doors.items()]
    )
    pack.function(f"{base}/face/open", [_setblock(c, AIR) for c in place.doors])

    if PHASE_2:
        _phase_2(pack, dome, place, bar, title, sound, say, call, box)

    # -- a step, and the hooks
    phases = ["p0", "p1"] + (["breach/step", "p3", "p4"] if PHASE_2 else [])
    pack.function(
        f"{base}/step",
        [
            # a room the pack has never reset has no scores: give it them
            f"execute unless score {_s('phase')} matches 0.. run {call('reset')}",
            call("form/count"),
            call("dress"),
            f"execute unless score #d{INDEX} {OBJ} matches 1 run return 0",
            f"execute unless score {_s('live')} matches 1 run {call('arm')}",
            *(
                f"execute {_if('phase', i)} run {call(name)}"
                for i, name in enumerate(phases)
            ),
        ],
    )
    pack.function(
        f"{base}/tick",
        [
            f"execute {_if('spin', '1..')} run {call('gov/spin')}",
            f"execute {open_dome} {_if('phase', 0)} run {start.tick}",
            f"execute {_if('phase', 1)} {_if('amb', '1..')} run {pair.tick}",
            _add("tick"),
            f"execute unless score {_s('tick')} matches {STEP}.. run return 0",
            _set("tick", 0),
            call("step"),
        ],
    )
    pack.function(
        f"{base}/enter",
        [
            # the core's signal, the first into an empty dome: a room with
            # no main shut is set up with the level in force
            f"execute {open_dome} if score #first {OBJ} matches 1 {_if('phase', 0)} "
            f"{_if('shut', 0)} run {call('arm')}",
            f"execute {open_dome} {_if('phase', '0..1')} run tellraw @s "
            '{text:"The Engine watches. The brass plaque says how to stop it.",'
            'color:"gray",italic:true}',
            f"execute {open_dome} {_if('phase', 4)} run tellraw @s "
            '{text:"The firebox stands open. He is waiting for you.",'
            'color:"gray",italic:true}',
        ],
    )
    # the core's form follows who is in the dome; this room's follows who
    # is in the arena: the hooks only ask for a count at once
    pack.function(f"{base}/solo", [call("form/count")])
    pack.function(f"{base}/duo", [call("form/count")])
    pack.function(f"{base}/leave", [f"tag @s remove {ARENA}"])
    pack.function(
        f"{base}/died",
        [
            # back at the entrance, in the pavilion: out of the arena. Dying
            # costs the walk back and no more
            f"tag @s remove {ARENA}",
            f"execute {open_dome} {_if('phase', '1..4')} run tellraw @s "
            '{text:"The Engine does not wait. Walk back in.",color:"gray",italic:true}',
        ],
    )
    # the stage in progress put back when the dome empties: a main being
    # wound is lost, a main shut is kept
    pack.function(
        f"{base}/p1/abandon",
        [
            *(
                f"execute {_if(f'l{m.key}', 0)} run {call(f'main/open_{m.key}')}"
                for m in place.mains
            ),
            _set("phase", 0),
            _set("amb", 0),
            start.arm,
        ],
    )
    quiet = [
        bar.hide,
        remove_boss,
        f"tag {arena} remove {ARENA}",
        *(_set(name, 0) for name in ("na", "grace", "tick")),
        _set("want", 1),
        _set("form", 1),
    ]
    pack.function(
        f"{base}/empty",
        [
            *quiet,
            f"execute {_if('phase', 1)} run {call('p1/abandon')}",
            *(
                [f"execute {_if('phase', '2..3')} run {call('p3/abandon')}"]
                if PHASE_2
                else []
            ),
            call("signs"),
        ],
    )
    zeroed = ("phase", "t", "shut", "amb", "pair", "next", "hatch", "n", "cast", "any")
    zeroed += ("live", "out", "down", "blink", "beat", "spin", "idle", "up", "vent")
    zeroed += ("esc", "boss", "x")
    lo, hi = place.firebox
    pack.function(
        f"{base}/reset",
        [
            call("scale"),
            *quiet,
            *(_set(name, 0) for name in zeroed),
            *(call(f"main/open_{m.key}") for m in place.mains),
            *(_setblock(c, lit) for m in place.mains for c in m.telltales),
            *(_setblock(c, lit) for c in place.eyes),
            *(_setblock(c, dark) for c in place.way_out),
            *(_setblock(c, dark) for row in place.brow for c in row),
            *(
                f"execute if block {_xyz(c)} {AIR} run {_setblock(c, block)}"
                for c, block in torches.items()
            ),
            call("face/shut"),
            *([call("lights/full")] if PHASE_2 else []),
            dp.fill(lo, hi, AIR),
            automatons.remove_line(INDEX),
            call("signs"),
            call("book"),
        ],
    )


def _phase_2(
    pack: dp.Pack,
    dome: Dome,
    place: Room,
    bar: Any,
    title: Any,
    sound: Any,
    say: Any,
    call: Any,
    box: Any,
) -> None:
    """the breach and the Master: in the pack only with ``PHASE_2`` on
    (what they assume is listed at the switch)"""
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    boss = f"@e[tag={BOSS}]"
    heart = place.spot
    doorway = place.door_columns[0][2]
    store = f"{game.STORE} b7"
    occ = f"#occ{INDEX}"
    knock, *bangs, out = BREACH
    pack.constants(OBJ, out)
    if not rider_is_raider():
        # a ravager fights by itself only under one of these (see RIDER_MOB)
        pack.tag("entity_type", RAIDERS_TAG, [RIDER_MOB])

    # -- the light: the floor's lanterns dim while he is about
    lights = floor_lights(dome)
    pack.function(f"{base}/lights/dim", [_setblock(c, DIM) for c in lights])
    pack.function(f"{base}/lights/full", [_setblock(c, domes.LIGHT) for c in lights])
    # -- nobody stands in the doorway he comes out of: the porch and the
    # firebox, as one box
    corners = (*place.porch, *place.firebox)
    low, top = (
        tuple(pick(c[i] for c in corners) for i in range(3)) for pick in (min, max)
    )
    pack.function(
        f"{base}/breach/clear",
        [f"tp @e[tag=st.in,{box((low, top))}] {middle(place.back)}"],
    )

    # -- the breach: the lights fail, the bar fills, and the doors are
    # forced from the middle outwards
    pack.function(
        f"{base}/breach/start",
        [
            _set("phase", 2),
            _set("t", 0),
            *(_set(name, 0) for name in ("wa", "wb", "wc", "ra", "rb", "rc", "amb")),
            automatons.remove_line(INDEX),
            call("breach/clear"),
            call("lights/dim"),
            f"effect give {here} minecraft:darkness {DARK} 0 true",
            f"bossbar set {bar.id} value 0",
            bar.show,
            *title("THE MAINS ARE SHUT", "Something is knocking in the firebox."),
            sound("block.beacon.deactivate", heart, 3, 0.5),
            sound("entity.warden.heartbeat", heart, 3, 0.6),
            say("The lamps fail. The firebox doors are moving.", "red"),
        ],
    )
    for i, column in enumerate(place.door_columns):
        pack.function(
            f"{base}/breach/bang_{i}",
            [
                *(_setblock(cell, AIR) for cell in column),
                sound("entity.generic.explode", doorway, 3, 0.7 + 0.1 * i),
                f"particle minecraft:large_smoke {middle(doorway)} 1.5 1.5 0.5 0.05 60",
            ],
        )
    pack.function(
        f"{base}/breach/step",
        [
            _add("t"),
            call("breach/clear"),
            # the Master's bar fills as he breaks out
            _op("pct", "=", "#b7.t"),
            _op("pct", "*=", "#100"),
            _op("pct", "/=", f"#{out}"),
            bar.value_line(_s("pct")),
            f"execute {_if('t', f'{knock}..{bangs[0] - 1}')} run "
            + sound("entity.zombie.attack_iron_door", doorway, 3, 0.5),
            *(
                f"execute {_if('t', at)} run {call(f'breach/bang_{i}')}"
                for i, at in enumerate(bangs)
            ),
            f"execute {_if('t', f'{out}..')} run {call('master/out')}",
        ],
    )

    # -- the Master out of the firebox, his health by who is in the dome
    dress = []
    for tag, health, damage, path in (
        (RAVAGER, RAVAGER_HP, RAVAGER_DAMAGE, "rav"),
        (RIDER, MASTER_HP, MASTER_DAMAGE, "rider"),
    ):
        dress += [
            _set("x", health),
            _op("x", "*=", "#b7.mult"),
            _op("x", "/=", "#100"),
            f"execute store result storage {store}.{path}.health int 1 "
            f"run scoreboard players get {_s('x')}",
            f"data modify storage {store}.{path}.damage set value {damage}",
            f"execute as @e[tag={tag}] run function {pack.id('mob/dress')} "
            f"with storage {store}.{path}",
        ]
    pack.function(
        f"{base}/master/out",
        [
            f"execute as {boss} run function {pack.id('mob/remove')}",
            call("face/open"),
            call("breach/clear"),
            master_summon(place.spot),
            # two players: 170%; each one more: 50% more
            _set("mult", 100),
            f"execute if score {occ} {OBJ} matches 2.. run {_set('mult', TWO_PLAYERS)}",
            _op("x", "=", occ),
            f"scoreboard players remove {_s('x')} 2",
            _op("x", "*=", f"#{MORE_PLAYERS}"),
            f"execute {_if('x', '1..')} run {_op('mult', '+=', '#b7.x')}",
            *dress,
            call("p3/health"),
            _op("hmax", "=", "#b7.hsum"),
            f"execute {_if('hmax', '..0')} run {_set('hmax', 1)}",
            f"bossbar set {bar.id} value 100",
            bar.show,
            _set("phase", 3),
            *(_set(name, 0) for name in ("t", "idle", "up", "vent", "esc")),
            # from level 6 he has an escort: one automaton, or two
            f"execute {_if('hp', f'{ESCORT_FROM}..')} run {_op('esc', '=', '#b7.form')}",
            *title("THE MASTER", "T. Marsh, on Old Grinder", "gold"),
            sound("entity.ravager.roar", heart, 3, 0.8),
            sound("entity.wither.spawn", heart, 2, 0.8),
            f"particle minecraft:flame {middle(doorway)} 1.5 1.5 0.5 0.1 80",
        ],
    )
    pack.function(
        f"{base}/p3/health",
        [
            _set("hr", 0),
            _set("hm", 0),
            f"execute as @e[tag={RAVAGER},limit=1] store result score {_s('hr')} "
            "run data get entity @s Health",
            f"execute as @e[tag={RIDER},limit=1] store result score {_s('hm')} "
            "run data get entity @s Health",
            _op("hsum", "=", "#b7.hr"),
            _op("hsum", "+=", "#b7.hm"),
        ],
    )
    pack.function(
        f"{base}/p3/gone",
        [
            # lost before he could have been fought: he comes out again
            f"execute {_if('t', f'..{EARLY}')} run {call('master/out')}",
            f"execute {_if('t', f'{EARLY + 1}..')} run {call('won')}",
        ],
    )
    high = f"@a[tag=st.in,{box(place.high)}]"
    warn = f"{_if('up', f'{VENT_AFTER}..')} {_if('vent', f'..{VENT_WARN - 1}')}"
    blow = (
        f"{_if('up', f'{VENT_AFTER}..')} {_if('vent', f'{VENT_WARN}..{VENT_BLOW - 1}')}"
    )
    pack.function(
        f"{base}/p3/vent",
        [
            # the high level is no safe seat: steam there, seven seconds in
            # fourteen, once a player has been up for five
            f"execute store result score {_s('hi')} if entity "
            f"@e[tag={ARENA},{box(place.high)}]",
            f"execute {_if('hi', '1..')} run {_add('up')}",
            f"execute {_if('hi', 0)} run {_set('up', 0)}",
            f"execute {_if('hi', 0)} run {_set('vent', 0)}",
            f"execute {_if('up', f'{VENT_AFTER}..')} run {_add('vent')}",
            f"execute {_if('vent', f'{VENT_CYCLE}..')} run {_set('vent', 0)}",
            f"execute {warn} run "
            + sound("block.lava.extinguish", place.governor, 3, 1.6),
            *(
                f"execute {warn} run particle minecraft:smoke {middle(cell)} 1 0.2 1 0.01 8"
                for cell in place.vents
            ),
            *(
                f"execute {blow} run particle minecraft:cloud {middle(cell)} 3 0.6 3 0.05 60"
                for cell in place.vents
            ),
            f"execute {blow} run "
            + sound("block.fire.extinguish", place.governor, 3, 0.7),
            *(
                f"execute {blow} {_if('blink', 0)} {_if('steam', n)} as {high} "
                f"run damage @s {n} minecraft:generic"
                for n in (1, 2, 3)
            ),
        ],
    )
    under = f"if score #mob.alive {OBJ} < {_s('esc')}"
    pack.function(
        f"{base}/p3/escort",
        [
            automatons.alive_line(INDEX),
            f"execute unless score #mob.alive {OBJ} < {_s('esc')} "
            f"run {call('pour/wait')}",
            f"execute {under} run scoreboard players remove {_s('next')} 1",
            f"execute {_if('next', '..0')} {under} run {call('pour/one')}",
        ],
    )
    pack.function(
        f"{base}/p3",
        [
            _add("t"),
            f"execute store result score {_s('boss')} if entity {boss}",
            f"execute {_if('boss', 0)} run {call('p3/gone')}",
            f"execute {_if('boss', 0)} run return 0",
            call("p3/health"),
            _op("pct", "=", "#b7.hsum"),
            _op("pct", "*=", "#100"),
            _op("pct", "/=", "#b7.hmax"),
            bar.value_line(_s("pct")),
            # with nobody in the arena he cannot be hurt, and then he mends
            f"execute {_if('na', '1..')} run {_set('idle', 0)}",
            f"execute {_if('na', 0)} run {_add('idle')}",
            f"execute {_if('na', 0)} run effect give {boss} minecraft:resistance 2 4 true",
            f"execute {_if('na', 0)} if score {_s('idle')} >= {_s('mend')} "
            f"run effect give {boss} minecraft:regeneration 2 2 true",
            call("p3/vent"),
            f"execute {_if('esc', '1..')} run {call('p3/escort')}",
            call("fence"),
        ],
    )
    # the dome emptied in the breach or the fight: he goes, the doors stay
    # open, and he comes out again at full health when a player is back
    pack.function(
        f"{base}/p3/abandon",
        [call("face/open"), _set("phase", 4), _set("t", 0)],
    )
    pack.function(
        f"{base}/p4",
        [
            f"execute {_if('na', '1..')} run {_add('t')}",
            f"execute {_if('na', 0)} run {_set('t', 0)}",
            f"execute {_if('t', 1)} run " + sound("entity.ravager.roar", heart, 3, 0.6),
            f"execute {_if('t', 1)} run "
            + say("Something stirs in the firebox.", "red", here),
            f"execute {_if('t', f'{ROAR}..')} run {call('master/out')}",
        ],
    )


# --------------------------------------------------------------- the check

S1, S2 = "st.e1", "st.e2"
PREY = "st.b7.prey"  # the golem the check sets before the ravager
BITE_WAIT = 600  # ticks the check gives the ravager to bite it


def check(ctx: Any) -> list[str]:
    """
    Work the Engine in place over RCON. A player is stood in for by an
    armour stand that the core counts (``game.STANDIN``), put at the
    entrance to come in, on a main's deck to hold it, in the pavilion to
    be out of the arena; a lever is thrown and the recall button clicked
    by setting the block or the entity as a hand would leave it. With
    ``PHASE_2`` off the third main is the win; on, the breach and the
    Master are worked too: the lanterns dimmed and the bar up at the
    breach, the porch kept clear, the doors' order; the pair out, the
    Master's kit, trims, size and name read back, his mob among the game's
    raiders, their health; lost early and out again; a golem set before
    them and bitten by the ravager with the rider's blow at nothing; the
    ravager put out of the pavilion with its rider still up; Resistance
    and mending with nobody in the arena; the steam's cycle; the ravager
    dead, the Master dead, the win, the lanterns back; the dome emptied in
    the breach, and he out again whole.

    It solves the last dome, which is the game's win: the run's scores are saved
    and put back, and ``#run.level`` is 0 while it runs so that no best
    time is touched. It resets its own dome and its own tunnel and nothing
    else, and leaves no stand-in behind.

    What stand-ins cannot prove (all in the play-test list): a lever
    thrown by hand, and a player's own body on a deck; a dead partner not
    counting in the arena (a stand-in does not die: it is moved to the
    pavilion); everything aimed at players: titles, chat, sounds,
    particles, the bossbar, the Darkness at the breach, the steam's
    ``damage``, the trophy sign given and placed; that automatons, or the
    Master and his ravager, go for a player, find a way round the Engine
    and up the ramps, and fight fairly; how the Master looks (that his
    armour, trims and name are drawn, how he sits on the ravager at his
    size) and how dim the room is with the floor's lanterns down; the governor seen turning (its displays are only counted); the
    automatons set on the nearest player as they come (a stand-in is no
    ``@a``).

    It refuses while a run is in progress (``game_checks.no_run``): the
    scores it puts back are the run's, not the room's or the tunnel's
    state. The scores and the level are put back, and the stand-ins
    killed, whatever happens.
    """
    game_checks.no_run(ctx)
    saved_level = game_checks.save_level(ctx)
    saved = game_checks.scores(ctx, *RUN_SCORES)
    try:
        return _check(ctx, saved)
    finally:
        ctx.cmd(f"kill @e[tag={S1}]")
        ctx.cmd(f"kill @e[tag={S2}]")
        ctx.cmd(f"kill @e[tag={PREY}]")
        for name, value in saved.items():
            ctx.set_score(name, value or 0)
        game_checks.restore_level(ctx, saved_level)
        ctx.function("difficulty/apply")


#: the run's scores the check changes (it solves the last dome: the win)
RUN_SCORES = (
    f"#d{INDEX}",
    "#solved",
    "#run",
    "#run.level",
    "#secs",
    "#level",
    "#won.best",
)


def _check(ctx: Any, saved: dict[str, int | None]) -> list[str]:
    dome = ctx.layout.DOMES[INDEX]
    tunnel = ctx.layout.TUNNELS[INDEX]
    place = room(dome)
    a, b, c = place.mains
    problems: list[str] = []
    scan = game_checks.SCAN
    base = f"dome/{INDEX}"
    mobs = automatons.selector(INDEX)
    lit_bulbs = (f"{BULB}[lit=true]", f"{GREEN_BULB}[lit=true]")
    torches = clock_torches(place)

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def get(name: str) -> int:
        return ctx.score(f"#b7.{name}") or 0

    def put(name: str, value: int) -> None:
        ctx.set_score(f"#b7.{name}", value)

    outside = middle(tunnels.at(ctx.layout.TUNNELS[INDEX - 1], 8, 0, 1))
    entrance = middle(domes.entrance(dome)[:3])
    floor = middle(place.back)  # in the arena, on no deck

    def stand(tag: str, where: str) -> None:
        """a stand-in that hangs where it is put (there are no plates here).
        On a deck it hangs half a block up: a marker has no height, and one
        at the bottom face of the deck's box is not in it (tried live)"""
        game_checks.stand_at(ctx, tag, where)

    def come_in(tag: str = S1) -> None:
        """a stand-in out of the dome and in again: a new entry"""
        stand(tag, outside)
        ctx.advance(game_checks.EMPTY)  # (a dome is empty 3 s after its last player)
        stand(tag, entrance)

    def steps(n: int) -> None:
        ctx.advance(n * STEP)

    def throw(main: Main, on: bool = True) -> None:
        ctx.setblock(main.lever, main.lever_on if on else main.lever_off)

    def lamps(cells: Any) -> int:
        return sum(any(ctx.is_block(c, kind) for kind in lit_bulbs) for c in cells)

    def seen(cell: Cell, block: str, times: int = 10, every: int = 5) -> set[bool]:
        """whether a cell held a block, looked at several times"""
        found = set()
        for _ in range(times):
            ctx.advance(every)
            found.add(ctx.is_block(cell, block))
        return found

    def nearly(main: Main, short: int = 2) -> None:
        """a main's gauge put a few steps short of full"""
        put(f"g{main.key}", FULL - short * get("rate"))

    def hold(tag: str, main: Main) -> None:
        """a stand-in on a main's deck, its lever over"""
        stand(tag, middle(main.stand, 0.5))
        throw(main)

    def shut(tag: str, main: Main) -> None:
        """a main wound shut by a stand-in, the last lamps of it"""
        hold(tag, main)
        nearly(main)
        steps(5)

    def as_built(what: str) -> None:
        """every block of the room is as ``reset`` leaves it (a block of a
        clock that runs by itself: the same block, in whatever state; a
        cell its pistons' heads rise into: not looked at; a piston caught
        in mid stroke is a ``moving_piston``)"""
        blocks = room_blocks(dome)
        wrong = [
            cell
            for cell, block in blocks.everything().items()
            if not (
                ctx.is_block(cell, _name(block))
                or ctx.is_block(cell, "minecraft:moving_piston")
                if cell in blocks.moving
                else ctx.is_block(cell, block.partition("{")[0])
            )
        ]
        wrong += [cell for cell in blocks.clear if not ctx.is_block(cell, AIR)]
        if wrong:
            problems.append(f"{what}: {len(wrong)} blocks not as built: {wrong[:6]}")
        names = ("phase", "shut", "ga", "gb", "gc", "la", "lb", "lc", "live", "out")
        expect(
            f"{what}: the scores", {n: get(n) for n in names}, dict.fromkeys(names, 0)
        )
        expect(f"{what}: automatons", ctx.count(mobs), 0)
        expect(f"{what}: the Master and his mount", ctx.count(f"@e[tag={BOSS}]"), 0)
        if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
            problems.append(f"{what}: the logbook is not on the lectern")

    def cylinders_run(what: str) -> None:
        """the two cylinders, which nothing starts or stops: every piston
        seen out and in and every lamp lit and dark over 6 s"""
        watched = [
            (cell, "minecraft:piston[extended=true]")
            for machine in place.cylinders
            for cell in machine.pistons
        ]
        watched += [
            (cell, f"{BULB}[lit=true]")
            for machine in place.cylinders
            for cell in machine.lamps
        ]
        states: list[set[bool]] = [set() for _ in watched]
        for _ in range(30):
            ctx.advance(4)
            for (cell, block), found in zip(watched, states, strict=True):
                found.add(ctx.is_block(cell, block))
        still = [
            cell
            for (cell, _), found in zip(watched, states, strict=True)
            if len(found) < 2
        ]
        if still:
            problems.append(
                f"{what}: {len(still)} parts of the cylinders stood still: {still[:4]}"
            )

    lights = floor_lights(dome)
    in_porch = f"@e[tag={S1},{dp.box_selector(*place.porch)}]"
    in_fence = f"@e[tag={BOSS},{dp.box_selector(*place.fence)}]"

    def dimmed() -> int:
        return sum(ctx.is_block(cell, DIM) for cell in lights)

    def bar_shown() -> bool:
        reply = ctx.cmd(f"bossbar get {automatons.bar_id(INDEX)} visible", "currently")
        return "hidden" not in reply

    def attribute(who: str, what: str) -> float | None:
        reply = ctx.cmd(f"attribute {who} minecraft:{what}", "is ")
        m = re.search(r"is (-?[\d.]+)", reply)
        return float(m.group(1)) if m else None

    def riding() -> bool:
        """the Master is on the ravager's back"""
        mob = RIDER_MOB.removeprefix("minecraft:")
        return mob in ctx.data(f"entity @e[tag={RAVAGER},limit=1] Passengers")

    def unsolve() -> None:
        """the room and its tunnel put back, the dome open and unsolved,
        and the run as it was but for its level (no best time is touched)"""
        ctx.function(f"tunnel/{INDEX}/reset")
        ctx.function(f"{base}/reset")
        ctx.set_score(f"#d{INDEX}", 1)
        ctx.set_score("#solved", saved["#solved"] or 0)
        ctx.set_score("#run", saved["#run"] or 0)
        ctx.set_score("#run.level", 0)

    def won(what: str) -> None:
        """the win, however it was come by"""
        got = {
            "phase": get("phase"),
            "dome": ctx.score(f"#d{INDEX}"),
            "run": ctx.score("#run"),
        }
        expect(f"{what}: won", got, {"phase": 5, "dome": 2, "run": 2})
        expect(f"{what}: automatons left", ctx.count(mobs), 0)
        problems.extend(game_checks.pull_pump(ctx, INDEX))
        expect(
            f"{what}: the tunnel home at the win",
            ctx.score(f"#t{INDEX}") in (1, 2),
            True,
        )
        steps(len(place.way_out) + 3)
        expect(
            f"{what}: the lamps of the way out",
            lamps(place.way_out),
            len(place.way_out),
        )
        expect(f"{what}: the eyes", lamps(place.eyes), 0)
        expect(f"{what}: the governor, run down", get("spin"), 0)
        # the core's run/win armed the Pump House's trophy dispenser: the
        # trophy's name made (the level is the check's 0)
        trophy = ctx.data(f"storage {game.STORE} trophy")
        expect(f"{what}: the trophy's name made ({trophy!r})", "level" in trophy, True)
        # the cylinders: their clocks out, the pistons come to rest
        out = sum(ctx.is_block(cell, AIR) for cell in torches)
        expect(f"{what}: the cylinders' clocks out", out, len(torches))
        ctx.advance(80)
        moved = [
            cell
            for machine in place.cylinders
            for cell in machine.pistons
            if True in seen(cell, "minecraft:piston[extended=true]", 5, 4)
        ]
        expect(f"{what}: the cylinders at rest", moved, [])

    # ---- before: nobody about, the room and its tunnel reset, the dome open
    names = RUN_SCORES
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan)
    if (others := ctx.score("#players")) or ctx.score(f"#form{INDEX}"):
        return [f"{others} players or stand-ins of another check are in the game"]
    unsolve()
    ctx.cmd(f"data remove storage {game.STORE} trophy")
    ctx.advance(scan)
    as_built("built")
    cylinders_run("nobody in")
    counts = {
        "recall": ctx.count(f"@e[type=minecraft:interaction,tag={RECALL_TAG}]"),
        "governor": ctx.count(f"@e[type=minecraft:block_display,tag={GOVERNOR_TAG}]"),
        "labels": ctx.count(f"@e[type=minecraft:text_display,tag={ENTITY_TAG}]"),
    }
    want = {"recall": 1, "governor": len(GOVERNOR_PARTS), "labels": len(place.mains)}
    expect("the entities the build summons", counts, want)
    expect("the eyes, lit", lamps(place.eyes), 2)
    expect(
        "the telltales, lit", lamps([t for m in place.mains for t in m.telltales]), 12
    )

    # ---- solo: in, set up, and nothing happens until a lever is thrown
    stand(S1, entrance)
    steps(2)
    got = {n: get(n) for n in ("live", "phase", "na", "form")}
    expect("solo, entered", got, {"live": 1, "phase": 0, "na": 0, "form": 1})
    level = ctx.score("#active") or game.DEFAULT_LEVEL
    expect("the level's values", {n: get(n) for n in scaled(level)}, scaled(level))
    stand(S1, floor)
    steps(8)
    got = {"phase": get("phase"), "na": get("na"), "mobs": ctx.count(mobs)}
    expect("in the arena, no lever", got, {"phase": 0, "na": 1, "mobs": 0})
    # the lever with nobody on the deck wakes the Engine and winds nothing
    throw(a)
    steps(3)
    expect("a lever thrown: the phase", get("phase"), 1)
    expect("a lever thrown, nobody on its deck: the gauge", get("ga"), 0)
    # on the deck it winds, and the gauge and the telltales show it
    stand(S1, middle(a.stand, 0.5))
    steps(8)
    gauge = get("ga")
    if not 4 * get("rate") <= gauge < FULL:
        problems.append(f"main A held for 4 s: its gauge is {gauge}")
    shown = lamps(a.gauge)
    if shown not in (gauge // LAMP, gauge // LAMP + 1):
        problems.append(f"main A's gauge shows {shown} lamps at {gauge}")
    expect(
        "A's telltale, winding",
        seen(a.telltales[0], f"{BULB}[lit=true]"),
        {True, False},
    )
    expect("B's telltale, open", seen(b.telltales[0], f"{BULB}[lit=true]", 4), {True})
    # off the deck, and with the lever back, it runs down
    put("ga", 3 * LAMP)
    stand(S1, floor)
    steps(4)
    if not 0 < get("ga") < 3 * LAMP:
        problems.append(f"main A left for 2 s from 3 lamps: {get('ga')}")
    stand(S1, middle(a.stand, 0.5))
    throw(a, False)
    put("ga", 3 * LAMP)
    steps(4)
    if not 0 < get("ga") < 3 * LAMP:
        problems.append(f"main A's lever put back for 2 s from 3 lamps: {get('ga')}")
    # held to the fifth lamp it is shut for good
    shut(S1, a)
    got = {"la": get("la"), "shut": get("shut"), "lamps": lamps(a.gauge)}
    expect("main A shut", got, {"la": 1, "shut": 1, "lamps": LAMPS})
    expect("main A shut: its lever gone", ctx.is_block(a.lever, AIR), True)
    expect("main A shut: its telltales", lamps(a.telltales), 0)
    expect(
        "main A shut: its sign",
        "SHUT" in ctx.data(f"block {_xyz(a.sign)} front_text"),
        True,
    )
    expect("main A shut: the dome", ctx.score(f"#d{INDEX}"), 1)

    # ---- the automatons: up to the cap and no further, put out of the
    # pavilion, another after one is lost
    stand(S1, floor)
    limit = cap(level, 1, 1)
    for _ in range(40):
        if ctx.count(mobs) >= limit:
            break
        steps(4)
    expect("automatons, at the cap", ctx.count(mobs), limit)
    steps(3 * GAP[1])
    expect("automatons, no more than the cap", ctx.count(mobs), limit)
    team = ctx.count(automatons.selector(INDEX, f"team={automatons.TEAM}"))
    expect("automatons on the team", team, limit)
    kinds = sum(
        ctx.count(automatons.selector(INDEX, f"tag={kind.tag}"))
        for kind in automatons.KINDS
    )
    expect("automatons of the core's three kinds", kinds, limit)
    reply = ctx.cmd(
        f"attribute {automatons.selector(INDEX, 'limit=1')} "
        "minecraft:follow_range base get",
        "is ",
    )
    expect(f"an automaton's follow range ({reply!r})", "48" in reply, True)
    ctx.cmd(f"tp {automatons.selector(INDEX, 'limit=1')} {entrance}")
    steps(2)
    fenced = ctx.count(automatons.selector(INDEX, dp.box_selector(*place.fence)))
    expect("an automaton put into the pavilion: left in it", fenced, 0)
    ctx.cmd(f"kill {automatons.selector(INDEX, 'limit=1')}")
    steps(GAP[1] + 3)
    expect("an automaton lost: another comes", ctx.count(mobs), limit)

    # ---- B and C: the third main ends phase 1
    shut(S1, b)
    expect("main B shut", {"lb": get("lb"), "shut": get("shut")}, {"lb": 1, "shut": 2})
    hold(S1, c)
    steps(4)
    if not 0 < get("gc") < FULL:
        problems.append(f"main C held for 2 s: {get('gc')}")
    nearly(c)
    steps(5)
    expect("main C shut", {"lc": get("lc"), "shut": get("shut")}, {"lc": 1, "shut": 3})
    if PHASE_2:
        # the breach: no automatons, the lights dimmed, the bar up and
        # filling, the doors forced from the middle out
        expect("the breach: the phase", get("phase"), 2)
        expect("the breach: automatons", ctx.count(mobs), 0)
        expect("the breach: the floor's lanterns dimmed", dimmed(), len(lights))
        expect("the breach: the Master's bar shown", bar_shown(), True)
        # one who walks into the porch while the doors go is put back
        # (moved with no wait for a scan: the doors' order is timed below)
        ctx.cmd(f"tp @e[tag={S1}] {middle(place.porch[0])}")
        order = []
        for _ in range(BREACH[-1] + 4):
            gone = [
                all(ctx.is_block(x, AIR) for x in col) for col in place.door_columns
            ]
            if not order or order[-1] != gone:
                order.append(gone)
            steps(1)
        want_order = [
            [False] * 3,
            [True, False, False],
            [True, True, False],
            [True] * 3,
        ]
        expect("the doors forced, by column", order, want_order)
        expect("the breach: the porch kept clear", ctx.count(in_porch), 0)
        # the pair, out of the firebox, at the level's health
        ravager, rider = f"@e[tag={RAVAGER},limit=1]", f"@e[tag={RIDER},limit=1]"
        got = {
            "phase": get("phase"),
            "ravager": ctx.count(f"@e[type=minecraft:ravager,tag={RAVAGER}]"),
            "rider": ctx.count(f"@e[type={RIDER_MOB},tag={RIDER}]"),
            "team": ctx.count(f"@e[tag={BOSS},team={automatons.TEAM}]"),
        }
        expect("the Master out", got, {"phase": 3, "ravager": 1, "rider": 1, "team": 2})
        expect("the Master on the ravager", riding(), True)
        # as he is meant to look: the brass suit, trimmed, the axe, his
        # size, his name over him (that the game draws them: by eye)
        kit = ctx.data(f"entity {rider} equipment")
        missing = [
            item for item in (*MASTER_KIT.values(), MASTER_AXE) if item not in kit
        ]
        expect("the Master's kit, missing", missing, [])
        expect("the Master's trims", kit.count(MASTER_TRIM[1]), len(MASTER_KIT))
        expect("the Master's size", attribute(rider, "scale get"), MASTER_SCALE)
        named = ctx.data(f"entity {rider} CustomName")
        expect(f"the Master's name ({named!r})", MASTER_NAME in named, True)
        shown = ctx.data(f"entity {rider} CustomNameVisible")
        expect("the Master's name over him", shown, "1b")
        # the ravager fights by itself only under a rider of the game's
        # tag of raiders: the pack's addition to it took
        raider = ctx.count(f"@e[tag={RIDER},type=#{RAIDERS_TAG}]")
        expect("the Master one of the game's raiders", raider, 1)
        full = (RAVAGER_HP + MASTER_HP) * scaled(level)["hp"] // 100
        if abs(get("hmax") - full) > 2:
            problems.append(f"the pair's health, one player: {get('hmax')}, not {full}")
        expect("the Master's bar shown", bar_shown(), True)
        # lost inside five seconds: he comes out again, and it is no win
        # (the game runs on while the reads above are made: his time out
        # is counted from here)
        put("t", 0)
        ctx.cmd(f"kill @e[tag={BOSS}]")
        steps(3)
        got = {"phase": get("phase"), "pair": ctx.count(f"@e[tag={BOSS}]")}
        expect("the pair lost at once: out again", got, {"phase": 3, "pair": 2})
        expect("the pair lost at once: the dome", ctx.score(f"#d{INDEX}"), 1)
        steps(EARLY + 2)
        # the ravager bites by itself with this rider up, as at the rig: a
        # golem that cannot move, of no team, set before them; the rider's
        # own blow set to nothing and his axe taken (it strikes by itself),
        # so that what the golem loses the ravager took
        blow = attribute(rider, "attack_damage base get")
        ctx.cmd(f"attribute {rider} minecraft:attack_damage base set 0")
        ctx.cmd(f"item replace entity {rider} weapon.mainhand with {AIR}")
        ctx.cmd(
            f"summon minecraft:iron_golem {floor} "
            f'{{Tags:["{PREY}"],NoAI:1b,PersistenceRequired:1b,'
            f'DeathLootTable:"station:{automatons.LOOT}",'
            'attributes:[{id:"minecraft:max_health",base:1000d}],Health:1000f}'
        )
        prey = f"@e[tag={PREY},limit=1]"
        lost = 0.0
        for _ in range(BITE_WAIT // 40):
            ctx.advance(40)
            health = ctx.data(f"entity {prey} Health").rstrip("f")
            lost = 1000 - float(health or 1000)
            if lost > 0:
                break
        if lost <= 0:
            problems.append(
                f"the ravager did not bite a golem in {BITE_WAIT // 20} s with a "
                f"{RIDER_MOB} up (see RIDER_MOB)"
            )
        expect("the Master still on the ravager after it fought", riding(), True)
        ctx.cmd(f"kill @e[tag={PREY}]")
        ctx.cmd(f"attribute {rider} minecraft:attack_damage base set {blow or 0}")
        ctx.cmd(f"item replace entity {rider} weapon.mainhand with {MASTER_AXE}")
        kit = ctx.data(f"entity {rider} equipment")
        expect("the Master's axe given back", MASTER_AXE in kit, True)
        # a mount in the pavilion is put out, and carries its rider
        ctx.cmd(f"tp {ravager} {entrance}")
        steps(2)
        expect("the ravager put out of the pavilion", ctx.count(in_fence), 0)
        expect("the ravager put out: the Master still on it", riding(), True)
        # nobody in the arena: he cannot be hurt, and then he mends
        stand(S1, entrance)
        ctx.cmd(f"data modify entity {ravager} Health set value 20f")
        steps(3)
        effects = ctx.data(f"entity {ravager} active_effects")
        expect("nobody in the arena: Resistance", "resistance" in effects, True)
        steps(get("mend") + 8)
        effects = ctx.data(f"entity {ravager} active_effects")
        expect("nobody in the arena: mending", "regeneration" in effects, True)
        if get("hr") <= 20:
            problems.append(f"the ravager did not mend from 20: {get('hr')}")
        # a stand-in on the high level: the steam's cycle runs
        stand(S1, middle(c.stand, 0.5))
        steps(VENT_AFTER + 2)
        cycle = set()
        for _ in range(VENT_CYCLE):
            steps(1)
            cycle.add(get("vent") >= VENT_WARN)
        expect("the high level's steam, off and on", cycle, {True, False})
        # the ravager dead: the bar falls; the Master too: the win
        before = get("pct")
        ctx.cmd(f"kill {ravager}")
        steps(2)
        got = {"phase": get("phase"), "pair": ctx.count(f"@e[tag={BOSS}]")}
        expect("the ravager dead: the Master fights on", got, {"phase": 3, "pair": 1})
        if not 0 < get("pct") < before:
            problems.append(f"the bar after the ravager died: {before} to {get('pct')}")
        ctx.cmd(f"kill @e[tag={RIDER}]")
        steps(3)
        expect("the Master dead: the floor's lanterns back", dimmed(), 0)
        expect("the Master dead: his bar hidden", bar_shown(), False)
    won("solo")
    # the tunnel home pumps dry and opens; the dome stays dry and whole
    ctx.advance(tunnels.event_ticks(tunnel) + 60)
    expect("the tunnel home open", ctx.score(f"#t{INDEX}"), 2)
    doors = [x for d in tunnels.ends(tunnel) for _, x in domes.door_cells(d, tunnel)]
    expect("door cells open", sum(ctx.is_block(x, AIR) for x in doors), len(doors))
    problems += [f"tunnel open: {p}" for p in domes.check_shell(ctx, dome, False)]
    # a second entry leaves a solved room as it is
    come_in()
    steps(4)
    got = {"phase": get("phase"), "dome": ctx.score(f"#d{INDEX}"), "live": get("live")}
    expect("solved, entered again", got, {"phase": 5, "dome": 2, "live": 1})
    expect(
        "solved, entered again: the way out", lamps(place.way_out), len(place.way_out)
    )
    expect("solved, entered again: automatons", ctx.count(mobs), 0)

    # ---- leaving costs the gauge being wound, and no more
    unsolve()
    come_in()
    shut(S1, a)
    hold(S1, b)
    steps(8)
    if not 0 < get("gb") < FULL:
        problems.append(f"main B part wound before leaving: {get('gb')}")
    stand(S1, outside)
    ctx.advance(game_checks.EMPTY + 2 * STEP)
    got = {n: get(n) for n in ("phase", "la", "lb", "shut", "gb")}
    expect("left in phase 1", got, {"phase": 0, "la": 1, "lb": 0, "shut": 1, "gb": 0})
    expect("left: B's lever put back", ctx.is_block(b.lever, b.lever_off), True)
    expect("left: A's lever still gone", ctx.is_block(a.lever, AIR), True)
    expect("left: automatons", ctx.count(mobs), 0)
    stand(S1, entrance)
    steps(2)
    got = {n: get(n) for n in ("phase", "la", "shut")}
    expect("back in: main A still shut", got, {"phase": 0, "la": 1, "shut": 1})
    if PHASE_2:
        # emptied in the breach: he waits, and comes out at full health
        shut(S1, b)
        shut(S1, c)
        expect("the breach again", get("phase"), 2)
        stand(S1, outside)
        ctx.advance(game_checks.EMPTY + 2 * STEP)
        got = {"phase": get("phase"), "pair": ctx.count(f"@e[tag={BOSS}]")}
        expect("left in the breach", got, {"phase": 4, "pair": 0})
        open_cells = sum(ctx.is_block(x, AIR) for x in place.doors)
        expect("left in the breach: the doors open", open_cells, len(place.doors))
        stand(S1, entrance)
        steps(ROAR + 4)
        expect("back in the pavilion: he waits", get("phase"), 4)
        stand(S1, floor)
        steps(ROAR + 4)
        got = {"phase": get("phase"), "pair": ctx.count(f"@e[tag={BOSS}]")}
        expect("back in the arena: he comes out", got, {"phase": 3, "pair": 2})
        expect("he comes out at full health", get("hsum"), get("hmax"))
        expect("he waits and comes out: the lanterns still dim", dimmed(), len(lights))

    # ---- two players: the form follows who is in the arena
    unsolve()
    come_in()
    stand(S2, entrance)
    ctx.advance(scan)
    got = {"dome": ctx.score(f"#form{INDEX}"), "na": get("na"), "form": get("form")}
    expect("two in the pavilion", got, {"dome": 2, "na": 0, "form": 1})
    # one in the arena, the partner idle in the pavilion: A winds alone
    hold(S1, a)
    steps(6)
    first = get("ga")
    expect("a partner in the pavilion: the form", get("form"), 1)
    if first <= 0:
        problems.append("a partner in the pavilion: main A did not wind alone")
    # the partner walks out while A is being wound: the change waits
    stand(S2, floor)
    steps(3)
    got = {n: get(n) for n in ("na", "want", "form")}
    expect("two in the arena, A being wound", got, {"na": 2, "want": 2, "form": 1})
    if get("ga") <= first:
        problems.append("the form change stopped main A under a hand")
    # the safe point: nobody winding A or B
    stand(S1, floor)
    steps(2)
    expect("two in the arena, nobody winding", get("form"), 2)
    expect(
        "A's sign, paired",
        "together" in ctx.data(f"block {_xyz(a.sign)} front_text"),
        True,
    )
    # A ready alone: it neither winds nor drains, and its amber lamp blinks
    stand(S1, middle(a.stand, 0.5))
    steps(2)
    held = get("ga")
    expect("A ready alone: its amber lamp", seen(a.amber, AMBER), {True, False})
    got = {"ga": get("ga"), "amb": get("amb")}
    expect("A ready alone for 2.5 s", got, {"ga": held, "amb": 1})
    # both ready: they climb in step, and shut together
    stand(S2, middle(b.stand, 0.5))
    put("gb", held)
    throw(b)
    steps(4)
    both = (get("ga"), get("gb"))
    if not (both[0] > held and abs(both[0] - both[1]) <= 2 * get("rate")):
        problems.append(f"A and B wound together from {held}: {both}")
    nearly(a)
    nearly(b)
    steps(5)
    got = {n: get(n) for n in ("la", "lb", "shut")}
    expect("A and B shut together", got, {"la": 1, "lb": 1, "shut": 2})
    expect("two in the arena: the cap", get("cap"), cap(level, 2, 2))
    # C winds for one
    hold(S1, c)
    steps(4)
    if get("gc") <= 0:
        problems.append("two players: main C did not wind for one")
    # one leaves in the middle: solo within 3 s, and the one left goes on
    unsolve()
    come_in()
    stand(S1, floor)
    stand(S2, floor)
    steps(2)
    expect("two in the arena from the start: the form", get("form"), 2)
    hold(S1, a)
    hold(S2, b)
    steps(8)
    part = (get("ga"), get("gb"))
    if not (part[0] > 0 and abs(part[0] - part[1]) <= 2 * get("rate")):
        problems.append(f"both held from the start: {part}")
    ctx.cmd(f"kill @e[tag={S2}]")
    steps(SOLO_STEPS + 4)
    expect("one left: the form", get("form"), 1)
    if not (get("ga") > part[0] and get("gb") < part[1]):
        problems.append(
            f"one left: A went {part[0]} to {get('ga')}, B {part[1]} to {get('gb')}"
        )
    nearly(a)
    steps(5)
    expect("one left: main A shut alone", get("la"), 1)

    # ---- the hooks a stand-in can run, and the recall button
    ctx.cmd(f"tag @e[tag={S1}] add {ARENA}")
    game_checks.as_stand_in(ctx, S1, f"{base}/died")
    expect("died: out of the arena", ctx.count(f"@e[tag={S1},tag={ARENA}]"), 0)
    click = f"@e[type=minecraft:interaction,tag={RECALL_TAG},limit=1]"
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

    # ---- difficulty: the values of the level, on a new entry
    for new in (game.LEVELS[0], game.LEVELS[-1]):
        unsolve()
        ctx.set_score("#level", new)
        come_in()
        steps(2)
        expect(
            f"level {new}: the values", {n: get(n) for n in scaled(new)}, scaled(new)
        )
    ctx.set_score("#level", saved["#level"] or game.DEFAULT_LEVEL)
    ctx.function("difficulty/apply")

    # ---- reset, from a scrambled state
    unsolve()
    come_in()
    shut(S1, a)
    stand(S1, floor)
    for _ in range(20):
        if ctx.count(mobs):
            break
        steps(2)
    hold(S1, b)
    put("gb", 2 * LAMP + 100)
    for cell in place.door_columns[0]:
        ctx.setblock(cell, AIR)
    taken = f"minecraft:lectern[facing={place.frame.facing(0, -1)},has_book=false]"
    ctx.setblock(place.lectern, taken)
    ctx.setblock(place.eyes[0], f"{BULB}[lit=false]")
    steps(3)
    if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("a logbook taken from the lectern was not put back")
    if not (get("la") == 1 and lamps(b.gauge) >= 2 and ctx.count(mobs) >= 1):
        problems.append("the room was not scrambled before the reset")
    ctx.function(f"{base}/reset")
    ctx.set_score(f"#d{INDEX}", 0)  # locked, so that nothing runs after it
    ctx.advance(STEP)
    as_built("reset from a scrambled state")

    # ---- after: nobody, the tunnel shut and flooded, the dome dry
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.function(f"tunnel/{INDEX}/reset")
    for name in names:
        ctx.set_score(name, saved[name] or 0)
    ctx.advance(game.EMPTY_AFTER * game.SCAN_TICKS + 2 * scan)
    ctx.function(f"{base}/reset")
    ctx.advance(40)
    as_built("left")
    expect("left: the floor's lanterns dimmed", dimmed(), 0)
    cylinders_run("left")
    got, wanted = tunnels.counts(ctx, tunnel), tunnels.expected(tunnel, 0)
    expect("the tunnel home left shut and flooded", got, wanted)
    problems += [f"left: {p}" for p in domes.check_shell(ctx, dome, False)]
    left = ctx.count(f"@e[tag={S1}]") + ctx.count(f"@e[tag={S2}]")
    expect("stand-ins left behind", left, 0)
    return problems


MODULE = game.Module(
    "boss",
    stages={f"dome_{INDEX}_inside": build},
    functions=functions,
    checks={"boss": check},
)
