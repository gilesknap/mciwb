"""
The Clockwork Maze (dome ``INDEX``) of The Drowned Station: a three-storey brass
cage whose gates and floors move with a clock. Its build stage
(``dome_<n>_inside``), its datapack functions (``dome/<n>/...``) and its live
check (``clockwork_maze``).

**The one idea.** The clock has three hours, Green (I), Iron (II) and Gold
(III), four quarters each. Every gate wears the colour of the hour it
opens in (its lintel, and a numeral for those who cannot tell the
colours), and everything moves when the bell strikes. A floor of grating
is only there in its hours. Climb with the clock to the Regulator on the
crown and throw it: the clock is tamed, every gate opens and stays open,
and its tunnel pumps dry.

**The puzzle** is the way up, and it is planned, not found. No cell has
two gates of one hour, so every cell is a wait for a bell, and most have
two or three gates: which one to wait for? The gate that opens first is
often the wrong one (it leads to a dead end, a full turn of the clock to
get out of, or the long way round). Deck 1 and deck 2 are each such a
maze, with a brass plan of each (``PLAN_AT``) on the tower's face beside
the dial: every gate on it in its own colour and numeral. ``puzzle``
measures it: the best route against the walker who takes whatever opens
first, the dead ends, and the gates the best route lets go by.

**The clock is told** everywhere: the Great Dial over the door (its rim
in the three hours' blocks, a lamp a quarter, and a hand that sweeps
round it), the light on every post of every cell in the hour's colour
(``HOUR_LIGHT``), three lamps on the atrium, a bell at each player's ear
that strikes once for Green, twice for Iron and three times for Gold, and
through an hour's last quarter a clank every half second while the
lights go to the colour of the hour to come and back.

**Places** are in the dome's own frame (``fittings.frame``): f forward
from the entrance, r to the right, h up from the floor. The tower is a
lattice of pitch 4: wall lines at f and r = ``LINES``, a post where two
cross, and between them cells 3 by 3; cell (i, j) has its middle at
f = -8 + 4i, r = -8 + 4j. Deck d is walked at h = 6d - 5; the crown at
h 19. The middle cell is the atrium, a shaft from the floor to the crown.

**A gate** (``GATES``, 39 of them) is a doorway 1 wide and 2 high shut by
a real two-block piston door: along the wall, the doorway, the parked
leaves, two sticky pistons in the post, and beside them the valve slot.
The rig's rules, kept exactly: the pack never writes a piston. It shuts a
gate by filling the slot with redstone and opens it by clearing the slot
(to ``SLOT_OPEN``: grating, not air, so that an open slot is not a way
through the wall), never fills a slot while someone is in the doorway,
and every tick runs ``mend``, which reads each piston and writes only
leaves and doorway: a piston that is in has its leaf parked and its
doorway clear, one that is out with its head out has its leaf in the
doorway. ``reset`` clears every slot and lets the mend do the rest.

**The two-player form** never strands anybody (``held``):

- the tower door is a held gate only while two are in the dome and nobody
  is inside the tower: one stands on the plate outside, the other goes
  in, and the door then stands open for the one who held it;
- the gate from F to K on deck 2 is held only while nobody is beyond it;
  with anyone beyond, it follows the clock (Green) as it does solo;
- the Regulator wants two keys (two plates, 6 apart, both stood on for a
  second) only while two or more players are on deck 3 or the crown;
  otherwise its lever is there.

``solo_problems`` and ``pair_problems`` search every position (and pair of
positions) at every hour, at one gate an hour, and report any from which
the crown cannot be reached.

**The lifts.** A, B and C go up at the strike of Green and down at the
strike of Gold; a lift takes whoever stands on its platform, which is a
whole cell. At rest a platform is blocks; to travel it becomes block
displays that glide a quarter of a block a tick, its riders seated on
item displays that move with them (the dock lift's way), and at the other
end it is blocks again. A shutter of iron trapdoors closes the hole it
leaves at the top. There are no ladders: the lifts are the way. So that
nobody is stuck, a lift's gate opens while its platform stands at the
bottom (through Gold) and for anyone found inside, a platform does not
come down onto anybody (it waits over them), and whoever stays on one at
the top is brought down at Gold and up again at Green. The Ram in the
atrium stays at the crown until the dome is solved, then takes whoever
stands on it down to the Ram Door, and after that goes with the clock.

**Nowhere to be stuck** (``trap_problems``): the band between a wall's
top and the floor over it is closed at foot height and each machine cell
has a lid, so that nobody drifting down from a timed floor can walk the
wall tops and drop into a machine cell; the search rides the lifts and
falls (drifting) with the lifts up and down and the floors in and out.

**State** (scores in ``st``, all ``#maze.<name>``): ``live`` 1 once the
room is set up for those in it; ``form`` 1 solo, 2 duo; ``free`` 1 once
solved; ``qlen`` ticks in a quarter and ``early`` quarters a floor drops
early (``scaled``, from the level when the room is set up); ``t``, ``q``
(0 to 11), ``hour`` (0 to 2); ``in``, ``beyond``, ``top`` who is in the
tower, beyond the second held gate, and up top; ``keys`` 1 while the
Regulator wants two keys, ``hold`` the ticks both have been held; for
each lift its height and where it is going (``l<id>``, ``l<id>.to``),
``l<id>.m`` 1 while it travels, ``.p`` the ticks into the block, ``.d``
its way and ``.w`` 1 while it waits over someone; ``bells`` the strokes
still to come, ``fl`` the warning's flash.

**Functions** (the core calls the hooks, see game.py): ``enter`` (the
first into an unsolved room: ``arm``), ``tick`` (the log put back, then
``work``: ``clock`` -> ``gates`` -> ``mend`` -> ``floors`` -> ``lifts`` ->
``keys``, which calls ``done``: ``station:dome/<n>/solved``, then ``restored``),
``solo`` / ``duo`` (the two held gates' plates and signs, nothing else:
a gate never shuts on anyone, so a change of form takes effect when the
doorway is clear), ``empty`` (an unsolved room parked: the clock stopped
at the strike of Green, every gate open), ``reset`` (everything as
built). Nothing is lent, and nothing here hurts: no ``leave`` or ``died``.

**To watch** (``dressing_blocks``): the Great Dial over the tower door
(twelve lamps, one more each quarter) with its hand, a block display
that the pack turns a twelfth of a turn a quarter (``hand/go``: made anew
if it is gone, put back to twelve by ``park``), and a pendulum of two
more that it swings; the plans; the Tally Engine in
the left yard, a torch clock (``fittings.torch_clock``) feeding six copper
bulbs that count in binary through comparators, behind bars; tanks and
pipes in the right yard; the Walk, a railed gantry round the dome's wall
for looking down into the maze. None has a lever, button or plate.
"""

from __future__ import annotations

import math
import re
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

if TYPE_CHECKING:
    from station_layout import Dome

INDEX = layout.index_of("maze")  # the Clockwork Maze's place in the ring
OBJ = game.OBJ

QUARTER = 30  # ticks a quarter at level 5: an hour is 6 s
HOURS = ("GREEN", "IRON", "GOLD")
GREEN, IRON, GOLD = 0, 1, 2
LINES = (-10, -6, -2, 2, 6, 10)
CROWN_H = 19  # where feet are on the crown
KEY_TICKS = 20  # both keys held this long
RAM_WAIT = 60  # ticks from the solve to the Ram's first descent
LIFT_STEP = 4  # ticks a block of a lift's travel: a quarter block a tick
BELL_GAP = 7  # ticks between the strokes of the bell
BELL_PITCH = (0.6, 0.85, 1.2)  # of each hour

BRASS = "minecraft:gold_block"
COPPER = "minecraft:waxed_copper_block"
CUT = "minecraft:waxed_cut_copper"
LEAF = "minecraft:waxed_chiseled_copper"
GRATE = "minecraft:waxed_copper_grate"
BARS = "minecraft:iron_bars"
RAIL = "minecraft:polished_blackstone_wall"
#: the light on every post, in the colour of the hour
HOUR_LIGHT = (
    "minecraft:verdant_froglight",
    "minecraft:pearlescent_froglight",
    "minecraft:ochre_froglight",
)
BULB = "minecraft:waxed_copper_bulb"
PISTON = "minecraft:sticky_piston"
POWER = "minecraft:redstone_block"
SLOT_OPEN = GRATE  # an open valve slot: not air, which would be a way through
PLATE = "minecraft:polished_blackstone_pressure_plate"
ROD = "minecraft:waxed_lightning_rod"
TRAPDOOR = "minecraft:iron_trapdoor[half=top,open=false]"
BED = "minecraft:polished_deepslate"
PLANKS = "minecraft:dark_oak_planks"
TANK = "minecraft:waxed_weathered_copper"
#: the block of each hour, on a gate's lintel and on the key. Not gold
#: for Gold: gold is the station's mark of an input, and only an input's
HOUR_BLOCK = (
    "minecraft:waxed_oxidized_copper",
    "minecraft:iron_block",
    "minecraft:yellow_concrete",
)
DECK_FLOOR = {2: "minecraft:waxed_weathered_cut_copper", 3: CUT}
NUMERAL = ("I", "II", "III")
ENTITY_TAG = "st.d6"  # everything this module summons
PEND_TAGS = ("st.maze.rod", "st.maze.bob")
HAND_TAG = "st.maze.hand"  # the Great Dial's hand
HAND = "minecraft:polished_blackstone"
CAR_TAG, SEAT_TAG = "st.maze.car", "st.maze.seat"  # a lift as it travels
BOARD = "minecraft:polished_blackstone"  # a cell on a plan
ARCH_MARK = "minecraft:sea_lantern"  # an open arch on a plan

# the kinds of gate that do not simply follow the hour
DOOR, FK, LIFT, RAM, GREAT = "door", "fk", "lift", "ram", "great"

P = tuple[int, int]  # a place on a deck: forward, right
Place = tuple[int, int, int]  # forward, right, up
Node = Any  # (deck, i, j), "out" (the dome's floor) or "crown"


@dataclass(frozen=True)
class Gate:
    deck: int
    kind: Any  # the hour it opens in (0, 1, 2), or DOOR, FK, LIFT, RAM, GREAT
    door: P
    piston: P
    slot: P

    @property
    def leaf(self) -> P:
        return (
            (self.door[0] + self.piston[0]) // 2,
            (self.door[1] + self.piston[1]) // 2,
        )

    @property
    def name(self) -> str:
        return f"gate {self.kind} of deck {self.deck} at {self.door}"


def _gates(deck: int, *rows: tuple) -> list[Gate]:
    return [Gate(deck, *row) for row in rows]


#: every gate: its deck, when it opens, its doorway, piston stack and slot.
#: No cell has two gates of one hour (``puzzle_problems``), so every way
#: through a cell is a wait for the bell, and which gate to wait for is
#: the puzzle
GATES: tuple[Gate, ...] = tuple(
    _gates(
        1,
        (DOOR, (-10, 0), (-10, 2), (-10, 3)),  # the tower door
        (IRON, (-8, -2), (-10, -2), (-10, -1)),
        (GREEN, (-8, 2), (-6, 2), (-5, 2)),
        (GOLD, (-6, -4), (-6, -2), (-5, -2)),
        (GOLD, (-6, 4), (-6, 6), (-5, 6)),
        (GREEN, (-4, -6), (-6, -6), (-7, -6)),
        (IRON, (-2, -4), (-2, -2), (-1, -2)),
        (GOLD, (-2, 8), (-2, 10), (-1, 10)),
        (GREEN, (0, -6), (-2, -6), (-3, -6)),
        (GOLD, (2, -8), (2, -10), (3, -10)),
        (GOLD, (2, -4), (2, -2), (3, -2)),
        (GREEN, (2, 8), (2, 10), (3, 10)),
        (IRON, (4, -6), (2, -6), (1, -6)),
        (GREEN, (4, 2), (6, 2), (7, 2)),
        (GOLD, (4, 6), (2, 6), (1, 6)),
        (GREEN, (6, -4), (6, -6), (7, -6)),
        (IRON, (6, 4), (6, 6), (7, 6)),
        (IRON, (6, 8), (6, 10), (7, 10)),
        (IRON, (8, -2), (6, -2), (5, -2)),
        (GOLD, (8, 2), (10, 2), (10, 3)),
        (GREEN, (8, 6), (10, 6), (10, 7)),
        (LIFT, (8, -6), (10, -6), (10, -5)),  # into lift A
        (RAM, (2, 0), (2, 2), (2, 3)),  # the Ram Door: solved only
        (GREAT, (10, 0), (10, -2), (9, -2)),  # the Great Door: solved only
    )
    + _gates(
        2,
        (FK, (2, -8), (2, -10), (3, -10)),  # F to K: held, or Green
        (GREEN, (-8, -2), (-6, -2), (-5, -2)),
        (IRON, (-6, 0), (-6, 2), (-5, 2)),
        (GREEN, (-6, 4), (-6, 6), (-5, 6)),
        (GOLD, (-4, -6), (-6, -6), (-7, -6)),
        (GREEN, (-4, -2), (-2, -2), (-1, -2)),
        (GOLD, (-4, 2), (-2, 2), (-1, 2)),
        (IRON, (-4, 6), (-2, 6), (-1, 6)),
        (IRON, (-2, -8), (-2, -10), (-1, -10)),
        (IRON, (-2, -4), (-2, -6), (-1, -6)),
        (GREEN, (-2, 8), (-2, 10), (-1, 10)),
        (GOLD, (0, -6), (2, -6), (3, -6)),
        (GREEN, (2, -4), (2, -2), (3, -2)),
        (LIFT, (0, 6), (2, 6), (3, 6)),  # into lift B
    )
    + _gates(3, (LIFT, (4, -2), (6, -2), (6, -3)))  # into lift C
)
#: doorways with no door: deck -> where
ARCHES: dict[int, tuple[P, ...]] = {
    1: ((6, 0),),
    2: ((6, -8),),
    3: ((2, -4), (-2, -4), (-4, -2), (-4, 2), (-2, 4)),
}
ATRIUM = (2, 2)
#: the cells of each deck (i, j), the atrium among them
CELLS: dict[int, frozenset[P]] = {
    1: frozenset((i, j) for i in range(5) for j in range(5)),
    2: frozenset(
        {(4, 0), (3, 0), (3, 1), (3, 2), (3, 3), (2, 0), (2, 1), (2, 2), (2, 3)}
        | {(2, 4), (1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (0, 1), (0, 2), (0, 3)}
    ),
    3: frozenset((i, j) for i in (1, 2, 3) for j in (1, 2, 3)),
}
#: cells nobody goes into: static machinery behind bars
MACHINE: dict[int, frozenset[P]] = {
    1: frozenset({(0, 0), (0, 4), (1, 2), (2, 3)}),
    2: frozenset({(3, 2), (3, 3)}),
    3: frozenset({(3, 3)}),
}
F_CELL: Node = (2, 3, 0)  # where the second held gate's plate is
DOOR_PLATE: Place = (-13, 2, 1)
FK_PLATE: Place = (4, -9, 7)  # within reach of its gate's sign
KEY_PLATES: tuple[Place, Place] = ((0, -3, CROWN_H), (0, 3, CROWN_H))
LEVER_POST: Place = (-4, 0, CROWN_H)


@dataclass(frozen=True)
class Floor:
    """a timed floor: a cell's whole floor in grating, there in two hours"""

    name: str
    deck: int
    cell: P
    start: int  # the first of its two hours

    @property
    def node(self) -> Node:
        return (self.deck, *self.cell)

    @property
    def below(self) -> Node:
        return (self.deck - 1, *self.cell)

    def out(self, hour: int) -> bool:
        return (hour - self.start) % 3 < 2


FLOORS = (
    Floor("t2", 2, (1, 0), IRON),
    Floor("w1", 3, (1, 3), GREEN),
    Floor("w2", 3, (1, 2), IRON),
    Floor("w3", 3, (1, 1), GOLD),
    Floor("w4", 3, (2, 1), GREEN),
    Floor("w5", 3, (3, 1), IRON),
)


@dataclass(frozen=True)
class Lift:
    """a platform 3 by 3, a whole cell, that takes whoever stands on it"""

    name: str
    cell: P
    bottom: int  # the height of the platform's blocks at the bottom
    travel: int
    low: Node  # the cell at the bottom, and at the top
    high: Node

    @property
    def top(self) -> int:
        return self.bottom + self.travel

    @property
    def mid(self) -> P:
        return (-8 + 4 * self.cell[0], -8 + 4 * self.cell[1])

    @property
    def score(self) -> str:
        return f"#maze.l{self.name} {OBJ}"

    @property
    def car(self) -> str:
        return f"{CAR_TAG}.{self.name}"


LIFT_LIST = (
    Lift("a", (4, 0), 0, 6, (1, 4, 0), (2, 4, 0)),
    Lift("b", (2, 3), 6, 6, (2, 2, 3), (3, 2, 3)),
    Lift("c", (3, 2), 12, 6, (3, 3, 2), "crown"),
    Lift("ram", ATRIUM, 0, 18, (1, 2, 2), "crown"),
)
RAM_LIFT = LIFT_LIST[3]


def walk_h(deck: int) -> int:
    """where feet are on a deck"""
    return 6 * deck - 5


def cell_mid(node: Node) -> Place:
    """the middle of a cell, at foot height"""
    deck, i, j = node
    return (-8 + 4 * i, -8 + 4 * j, walk_h(deck))


def sides(deck: int, door: P) -> tuple[Node, Node]:
    """the two cells a doorway joins; "out" for one that is not a cell"""
    f, r = door
    if f in LINES:
        i, j = LINES.index(f), (r + 10) // 4
        pair = ((i - 1, j), (i, j))
    else:
        i, j = (f + 10) // 4, LINES.index(r)
        pair = ((i, j - 1), (i, j))
    a, b = (
        (deck, *c) if c in CELLS[deck] and c not in MACHINE[deck] else "out"
        for c in pair
    )
    return a, b


def scaled(level: int) -> dict[str, int]:
    """the room's values at a level, as the function ``scale`` works them
    out: a slower clock at low levels; at high ones a timed floor drops a
    quarter or two before its hours are over"""
    timer = game.scaled(level)["#diff.timer"]
    return {
        "qlen": QUARTER * timer // 100,
        "early": 2 if timer <= 60 else 1 if timer <= 80 else 0,
    }


# ------------------------------------------------- the maze as a graph
# The same tables the build and the pack use, searched: can the crown be
# reached from everywhere, alone and as a pair, at one gate an hour?


def floor_at(node: Node) -> Floor | None:
    return next((fl for fl in FLOORS if fl.node == node), None)


def land(node: Node, hour: int) -> Node:
    """where someone in a cell in an hour really is: a deck down if the
    cell is a timed floor that is not out"""
    fl = floor_at(node)
    return fl.below if fl and not fl.out(hour) else node


def beyond(node: Node) -> bool:
    """beyond the second held gate: deck 2 but for F and lift A, and up"""
    if node == "out":
        return False
    return node == "crown" or (node[0] >= 2 and node not in (F_CELL, (2, 4, 0)))


@cache
def edges() -> tuple[tuple[Node, Node, Any], ...]:
    """every way from a cell to the next: (from, to, rule), the rule an
    hour, "arch" or a gate's kind"""
    found = []
    for g in GATES:
        a, b = sides(g.deck, g.door)
        if g.kind in (RAM, GREAT) or ATRIUM in (a[1:], b[1:]):
            continue
        found.append((a, b, g.kind))
    for deck, doors in ARCHES.items():
        found += [(*sides(deck, door), "arch") for door in doors]
    return tuple(found)


def nodes() -> list[Node]:
    found = {n for a, b, _ in edges() for n in (a, b)}
    found |= {n for lift in LIFT_LIST[:3] for n in (lift.low, lift.high)}
    return sorted(found, key=str)


def room(node: Node, hour: int | None = None) -> set[Node]:
    """a cell and the cells its open arches lead to: one room. With an
    ``hour``, only through timed floors that are out in it"""
    seen, edge = {node}, [node]
    while edge:
        here = edge.pop()
        for a, b, rule in edges():
            for one, other in ((a, b), (b, a)):
                if rule != "arch" or one != here or other in seen:
                    continue
                if hour is not None and land(other, hour) != other:
                    continue
                seen.add(other)
                edge.append(other)
    return seen


def opens(rule: Any, hour: int) -> bool:
    """whether a gate is open in an hour, alone, with nobody in a lift"""
    return hour == {FK: GREEN, LIFT: GOLD}.get(rule, rule)


def moves(node: Node, hour: int, other: Node | None = None) -> dict[Node, bool]:
    """
    Where a player in ``node`` can be at the end of ``hour``, moving
    through one gate at most and any arches before and after it (an arch
    has no door: it takes no time): place -> whether the partner must
    stand still on a plate for it. ``other`` is the partner's place (None:
    the solo form). Stepping through an arch onto a timed floor that is
    not out is a fall to the cell below.
    """
    found: dict[Node, bool] = {}

    def spread(start: Node, hold: bool) -> None:
        for at in room(start, hour):
            found[at] = found.get(at, True) and hold
            for a, b, rule in edges():
                for one, there in ((a, b), (b, a)):
                    if rule == "arch" and one == at and land(there, hour) != there:
                        down = land(there, hour)
                        found[down] = found.get(down, True) and hold

    spread(node, False)
    lifts = {lift.low for lift in LIFT_LIST}
    for here in room(node, hour):
        for a, b, rule in edges():
            for one, there in ((a, b), (b, a)):
                if one != here or rule == "arch":
                    continue
                hold = False
                if rule == LIFT:  # in during Gold; out whenever
                    ok = hour == GOLD or here in lifts
                elif rule == DOOR:
                    # held only while two are here and nobody is inside
                    hold = other == "out" and here == "out"
                    ok = True
                elif rule == FK:
                    held = other is not None and not beyond(here) and not beyond(other)
                    hold = held
                    ok = other == F_CELL if held else hour == GREEN
                else:
                    ok = hour == rule
                if ok:
                    spread(land(there, hour), hold)
    # from the crown onto lift C's platform, to be taken down at Gold
    for lift in LIFT_LIST[:3]:
        if node == lift.high == "crown" and hour == IRON:
            found[lift.low] = False
    return found


def strike(node: Node, hour: int) -> Node:
    """where someone is after the strike that begins ``hour``: a deck
    down if their timed floor has gone, and with a lift's platform if
    they stand on it (up at the strike of Green, down at Gold: the top of
    lift A and of lift B is all platform, the crown is not)"""
    node = land(node, hour)
    for lift in LIFT_LIST[:3]:
        if hour == GREEN and node == lift.low:
            return lift.high
        if hour == GOLD and node == lift.high != "crown":
            return lift.low
    return node


def solo_steps() -> dict[tuple[Node, int], set[tuple[Node, int]]]:
    return {
        (n, h): {(strike(to, (h + 1) % 3), (h + 1) % 3) for to in moves(n, h)}
        for n in nodes()
        for h in range(3)
    }


def pair_steps() -> dict[tuple, set[tuple]]:
    steps = {}
    for a in nodes():
        for b in nodes():
            for h in range(3):
                nxt = (h + 1) % 3
                found = set()
                for to_a, hold_a in moves(a, h, b).items():
                    for to_b, hold_b in moves(b, h, a).items():
                        # whoever holds a plate for the other stands still
                        if (hold_a and to_b != b) or (hold_b and to_a != a):
                            continue
                        found.add((strike(to_a, nxt), strike(to_b, nxt), nxt))
                steps[a, b, h] = found
    return steps


def stuck(steps: dict, goal) -> list:
    """the states from which no state of ``goal`` can be reached"""
    good = {s for s in steps if goal(s)}
    grew = True
    while grew:
        more = {s for s, to in steps.items() if s not in good and to & good}
        good |= more
        grew = bool(more)
    return sorted(set(steps) - good, key=str)


def solo_problems() -> list[str]:
    """alone: from every cell at every hour the crown can be reached"""
    bad = stuck(solo_steps(), lambda s: s[0] == "crown")
    return [f"alone, no way to the crown from {n} in {HOURS[h]}" for n, h in bad]


def pair_problems() -> list[str]:
    """as a pair, with the held gates and the two keys: from every pair of
    places at every hour both can reach the crown"""
    bad = stuck(pair_steps(), lambda s: s[0] == s[1] == "crown")
    return [
        f"a pair at {a} and {b} in {HOURS[h]} cannot both reach the crown"
        for a, b, h in bad
    ]


def solo_route(
    start: Node = "out", hour: int = GREEN, goal: Node = "crown"
) -> list[tuple[Node, int]]:
    """the shortest way to ``goal`` alone, an hour a step: the place after
    each strike, with the hour it begins"""
    steps = solo_steps()
    came: dict = {(start, hour): None}
    edge = [(start, hour)]
    while edge:
        new = []
        for state in edge:
            if state[0] == goal:
                route = []
                while came[state] is not None:
                    route.append(state)
                    state = came[state]
                return route[::-1]
            for to in sorted(steps[state], key=str):
                if to not in came:
                    came[to] = state
                    new.append(to)
        edge = new
    return []


# ------------------------------------------------- is the puzzle a puzzle?
# The clock tells when a gate opens. That is only worth knowing if it
# matters which gate: so the route that plans ahead is measured against
# the walker who goes through whatever opens first.


def naive_step(node: Node, hour: int) -> tuple[Node, int]:
    """an hour of the walker with no plan: through the gate of their room
    that is open, if there is one (never back out of the tower door), and
    whatever the strike then does with them"""
    nxt = (hour + 1) % 3
    for here in sorted(room(node, hour), key=str):
        for a, b, rule in edges():
            for one, there in ((a, b), (b, a)):
                if one == here and rule not in ("arch", DOOR) and opens(rule, hour):
                    return strike(land(there, hour), nxt), nxt
    return strike(node, nxt), nxt


def naive_hours(start: Node, hour: int, goal: Node) -> int | None:
    """how many hours the walker with no plan takes; None: they go round
    for ever"""
    state, seen, hours = (start, hour), set(), 0
    while goal not in room(state[0]):
        if state in seen:
            return None
        seen.add(state)
        state = naive_step(*state)
        hours += 1
    return hours


def hours_left(goal: Node) -> dict[tuple[Node, int], int]:
    """from every place and hour, the fewest hours to ``goal``"""
    steps = solo_steps()
    left = {s: 0 for s in steps if s[0] == goal}
    grew = True
    while grew:
        grew = False
        for s, to in steps.items():
            best = min((left[t] + 1 for t in to if t in left), default=None)
            if best is not None and best < left.get(s, 10**6):
                left[s] = best
                grew = True
    return left


#: each deck of gates as a puzzle: where it starts and where it ends (the
#: top of its lift, reached at a strike of Green)
LEGS: dict[int, tuple[Node, Node]] = {
    1: ((1, 0, 2), LIFT_LIST[0].high),
    2: (LIFT_LIST[0].high, LIFT_LIST[1].high),
}


def dead_ends(deck: int) -> list[Node]:
    """the rooms of a deck with one gate and no other way on"""
    lifts = {n for lift in LIFT_LIST for n in (lift.low, lift.high)}
    found = []
    for node in nodes():
        if node in ("out", "crown") or node[0] != deck or node in lifts:
            continue
        mine = room(node)
        gates = [(a, b) for a, b, rule in edges() if rule != "arch" and {a, b} & mine]
        if len(gates) == 1 and node == min(mine, key=str) and not mine & lifts:
            found.append(node)
    return found


def puzzle() -> dict[int, dict[str, Any]]:
    """
    The numbers of each deck's puzzle, in hours of the clock: for a start
    in each hour the ``best`` route and the ``naive`` one (None: never
    arrives); the ``dead`` ends; and ``ahead``, the places on the best
    route from Green where the gate that opens first is the wrong one,
    with the hours it costs to take it (a turn of the clock or more).
    """
    found = {}
    for deck, (start, goal) in LEGS.items():
        left = hours_left(goal)
        ahead = []
        state = (start, GREEN)
        for nxt in solo_route(start, GREEN, goal):
            there = naive_step(*state)
            cost = 1 + left[there] - left[state]
            if cost >= 3:
                ahead.append((state[0], HOURS[state[1]], cost))
            state = nxt
        found[deck] = {
            "best": [left[start, h] for h in range(3)],
            "naive": [naive_hours(start, h, goal) for h in range(3)],
            "dead": dead_ends(deck),
            "ahead": ahead,
        }
    return found


def puzzle_problems() -> list[str]:
    """the route is worth planning: no room has two gates of one hour (so
    nobody runs through two in an hour, at any level), most have two or
    three; on each deck there are dead ends, the walker with no plan
    takes half as long again as the best route or more (or never arrives),
    and the best route passes two or more gates that open first and are
    wrong"""
    problems = []
    for deck in LEGS:
        rooms_, wide = set(), 0
        for node in nodes():
            if node in ("out", "crown") or node[0] != deck:
                continue
            mine = room(node)
            if min(mine, key=str) != node:
                continue
            hours = [
                {FK: GREEN, LIFT: GOLD}.get(rule, rule)
                for a, b, rule in edges()
                if rule not in ("arch", DOOR) and {a, b} & mine
            ]
            if len(hours) != len(set(hours)):
                problems.append(f"the room of {node} has two gates of one hour")
            rooms_.add(node)
            wide += len(hours) >= 2
        if 2 * wide <= len(rooms_):
            problems.append(f"deck {deck}: {wide} of {len(rooms_)} rooms have a choice")
    for deck, n in puzzle().items():
        best, naive = n["best"][GREEN], n["naive"][GREEN]
        if naive is not None and 2 * naive < 3 * best:
            problems.append(f"deck {deck}: no plan {naive} hours, the best {best}")
        if len(n["dead"]) < 2:
            problems.append(f"deck {deck}: {len(n['dead'])} dead ends")
        if len(n["ahead"]) < 2:
            problems.append(f"deck {deck}: {len(n['ahead'])} gates to let go by")
    return problems


def table_problems() -> list[str]:
    """the gate table against the lattice: each doorway in the middle of a
    wall, its pistons in a post two along, its slot against the pistons
    and in a wall; no cell used twice on a deck; no slot face to face with
    another gate's piston"""
    problems = []
    used: dict[tuple[int, P], str] = {}
    for deck, doors in ARCHES.items():
        for door in doors:
            used[deck, door] = f"an arch of deck {deck}"
    for g in GATES:
        on_f, on_r = g.door[0] in LINES, g.door[1] in LINES
        along = g.door[1] if on_f else g.door[0]
        if on_f == on_r or (along + 10) % 4 != 2:
            problems.append(f"{g.name}: its doorway is not the middle of a wall")
        if not (g.piston[0] in LINES and g.piston[1] in LINES):
            problems.append(f"{g.name}: its pistons are not in a post")
        if math.dist(g.door, g.piston) != 2:
            problems.append(f"{g.name}: its pistons are not two from its doorway")
        in_wall = (g.slot[0] in LINES) != (g.slot[1] in LINES)
        if math.dist(g.slot, g.piston) != 1 or not in_wall or g.slot == g.leaf:
            problems.append(f"{g.name}: its slot is not in a wall by its pistons")
        if all(side == "out" for side in sides(g.deck, g.door)):
            problems.append(f"{g.name}: it joins no cell")
        for where in (g.door, g.leaf, g.piston, g.slot):
            if (g.deck, where) in used:
                problems.append(f"{g.name}: {where} is {used[g.deck, where]}'s too")
            used[g.deck, where] = g.name
    for g in GATES:
        for other in GATES:
            near = math.dist(g.slot, other.piston) == 1
            if other is not g and other.deck == g.deck and near:
                problems.append(f"{g.name}: its slot powers {other.name}")
    return problems


# ---------------------------------------------------------------- the room


@dataclass
class Blocks:
    """every block of the room, as built and as ``reset`` leaves it"""

    floor: dict[Cell, str] = field(default_factory=dict)  # relaid floor
    solid: dict[Cell, str] = field(default_factory=dict)
    attached: dict[Cell, str] = field(default_factory=dict)  # need a support
    clear: set[Cell] = field(default_factory=set)  # air, to be kept so
    #: cells whose block changes state by itself (a clock, its lamps)
    moving: set[Cell] = field(default_factory=set)

    def everything(self) -> dict[Cell, str]:
        return {**self.floor, **self.solid, **self.attached}

    def above(self) -> dict[Cell, str]:
        return {**self.solid, **self.attached}


def gate_places(g: Gate) -> dict[str, tuple[Place, ...]]:
    """a gate's cells by part: door, leaf, piston, slot (two high each),
    lintel and lamp"""
    h = walk_h(g.deck)
    two = lambda p: ((*p, h), (*p, h + 1))  # noqa: E731
    return {
        "door": two(g.door),
        "leaf": two(g.leaf),
        "piston": two(g.piston),
        "slot": two(g.slot),
        "lintel": ((*g.door, h + 2),),
        "lamp": ((*g.door, h + 3),),
    }


def gate_sign_at(g: Gate, reader: P) -> tuple[Place, P]:
    """where a gate's sign goes, and the frame step it faces: on the wall
    beside the doorway, one along from it away from the piston stack, at
    head height, on the side of the wall ``reader`` (a place in the cell a
    player reads it from) is on"""
    along = (g.door[0] - g.piston[0]) // 2, (g.door[1] - g.piston[1]) // 2
    across = abs(along[1]), abs(along[0])
    side = (
        1
        if (reader[0] - g.door[0]) * across[0] + (reader[1] - g.door[1]) * across[1] > 0
        else -1
    )
    out = across[0] * side, across[1] * side
    f, r = g.door[0] + along[0] + out[0], g.door[1] + along[1] + out[1]
    return (f, r, walk_h(g.deck) + 1), out


def lift_gate(lift: Lift) -> Gate:
    """the gate into a lift at its bottom"""
    return next(g for g in GATES if g.kind == LIFT and g.deck == lift.low[0])


def lift_sign_at(lift: Lift) -> tuple[Place, P]:
    """a lift's sign: by its gate, on the side away from the lift"""
    g = lift_gate(lift)
    reader = 2 * g.door[0] - lift.mid[0], 2 * g.door[1] - lift.mid[1]
    return gate_sign_at(g, reader)


def lintel(g: Gate) -> tuple[str, str]:
    """a gate's lintel block and what its faces say"""
    if g.kind in (GREEN, IRON, GOLD):
        return HOUR_BLOCK[g.kind], NUMERAL[g.kind]
    if g.kind == FK:  # alone it follows Green
        return HOUR_BLOCK[GREEN], "I"
    if g.kind == LIFT:  # it opens with the platform down: Gold
        return HOUR_BLOCK[GOLD], "III"
    return CUT, {DOOR: "IN", RAM: "RAM", GREAT: "OUT"}[g.kind]


def lift_places(lift: Lift, k: int, riding: bool = False) -> dict[Place, str]:
    """a lift's whole shaft with the platform k blocks up: the platform,
    the ram under it, the bed it left, and a shutter of trapdoors over the
    hole at the top while it is away. ``riding``: the platform is on its
    way (display entities, ``car_summons``), so none of it is blocks"""
    cf, cr = lift.mid
    found = {}
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            for level in range(lift.travel + 1):
                if level == k and not riding:
                    block = COPPER
                elif level == 0:
                    block = BED
                elif level < k:
                    block = f"{ROD}[facing=up]" if (df, dr) == (0, 0) else AIR
                elif level == lift.travel:
                    block = TRAPDOOR
                else:
                    block = AIR
                found[cf + df, cr + dr, lift.bottom + level] = block
    return found


def floor_places(fl: Floor) -> list[Place]:
    f, r, h = cell_mid(fl.node)
    return [(f + df, r + dr, h - 1) for df in (-1, 0, 1) for dr in (-1, 0, 1)]


def dial_places() -> tuple[list[Place], dict[Place, str]]:
    """the Great Dial: its twelve lamps from twelve o'clock round, and the
    disc behind them, its rim in the block of the hour of the nearest lamp"""
    hands = [(0, 4), (2, 3), (3, 2), (4, 0), (3, -2), (2, -3)]
    hands += [(-r, -h) for r, h in hands]
    lamps = [(-11, r, 9 + h) for r, h in hands]
    disc = {}
    for r in range(-5, 6):
        for h in range(-5, 6):
            if math.hypot(r, h) > 5.2:
                continue
            near = min(range(12), key=lambda n: math.dist(hands[n], (r, h)))
            rim = math.hypot(r, h) > 3.2
            disc[-11, r, 9 + h] = HOUR_BLOCK[near // 4] if rim else BED
    return lamps, disc


def turned(
    fr: fittings.Frame,
    angle: float,
    size: tuple[float, float, float],
    corner: tuple[float, float, float],
    out: float = 0.0,
) -> str:
    """the ``transformation`` of a block display hung at the dial's
    middle: a block of ``size`` with its ``corner`` (from the pivot, with
    the display upright) turned by ``angle`` about the frame's forward,
    clockwise as the entrance sees it, and stood ``out`` towards it"""
    ax, az = fr.forward
    # Rodrigues: the corner turned by ``angle`` about (ax, 0, az)
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = corner
    dot = ax * x + az * z
    cross = (-az * y, az * x - ax * z, ax * y)
    tx, ty, tz = (
        p * c + q * s + k * (dot * (1 - c) - out)
        for p, q, k in zip(corner, cross, (ax, 0, az), strict=True)
    )
    return (
        f"transformation:{{translation:[{tx:.3f}f,{ty:.3f}f,{tz:.3f}f],"
        f"scale:[{size[0]}f,{size[1]}f,{size[2]}f],"
        f"left_rotation:{{axis:[{ax}f,0f,{az}f],angle:{angle:.4f}f}},"
        "right_rotation:[0f,0f,0f,1f]}"
    )


def hand(fr: fittings.Frame, q: int) -> str:
    """the dial's hand pointing at lamp ``q`` (0 to 12: twelve o'clock,
    and round to it again)"""
    return turned(fr, q * math.pi / 6, (0.2, 3.6, 0.2), (-0.1, -0.4, -0.1), 0.3)


def hand_turn(q: int) -> tuple[float, float]:
    """what the hand's ``left_rotation`` reads back as when it points at
    lamp ``q``, as (the sine of half its angle, the cosine); the same turn
    with both signs changed"""
    return math.sin(q * math.pi / 12), math.cos(q * math.pi / 12)


def hand_summon(fr: fittings.Frame) -> str:
    return (
        f"summon minecraft:block_display {middle(fr.at(-12, 0, 9), 0.5)} "
        f'{{Tags:["{ENTITY_TAG}","{HAND_TAG}"],'
        f"block_state:{fittings.block_state(HAND)},{hand(fr, 0)}}}"
    )


def atrium_lamps() -> list[tuple[int, Place]]:
    """the hour lamps on two faces of the atrium, on every deck: (hour,
    where)"""
    found = []
    for deck in (1, 2, 3):
        h = walk_h(deck) + 3
        for hour in range(3):
            found += [(hour, (-2, hour - 1, h)), (hour, (hour - 1, 2, h))]
    return found


def walk_places() -> tuple[set[P], set[P]]:
    """the Walk, a horseshoe round the dome's wall open at the entrance's
    end: where its deck is, and which of that carries a rail"""
    deck, rails = set(), set()
    for f in range(-8, 21):
        for r in range(-20, 21):
            d = math.hypot(f, r)
            if 16.5 <= d < 20.5:
                deck.add((f, r))
                if not 17.5 <= d < 19.5:
                    rails.add((f, r))
    return deck, rails


def lever(fr: fittings.Frame, on: bool = False) -> str:
    return fittings.lever(fr.facing(1, 0), on)


LOG_TITLE, LOG_AUTHOR = "Clockwork Maze log", "O. Finch"
LOG_PAGES = [
    "Clockwork Maze log\nO. Finch, Chief Engineer\n\nThis tower was my lock on "
    "the Engine. One clock, three hours, every gate on a piston.\n\nThe Engine "
    "learned the clock. It keeps the hours now, and I am locked out.",
    "It cannot change the rule, only run it.\n\nA gate opens in the hour of its "
    "colour: GREEN, IRON, GOLD, and round again. A floor of grating is only "
    "there in its hours. A lift's gate opens in GOLD.\n\nListen for the ticks "
    "before the bell.",
    "At the top is the Regulator. Throw it and the clock is ours: every gate "
    "opens.\n\nWith a mate: a HELD gate wants one of you on its plate. If two "
    "of you are up top, the Regulator wants two keys.",
    "Beyond this is the Engine itself. Three steam mains feed it. Shut all "
    "three and whoever it answers to must come out.\n\nI go through tonight, "
    "alone. If this book is still here, I did not come back.\n\nFinish it.\n\n"
    "O. Finch",
]
HELD_SIGNS = {
    DOOR: (("TOWER DOOR", "Alone, it", "stands open."), ("HELD GATE", "One on the", "plate. The", "other goes in.")),
    FK: (("GREEN GATE", "Alone, it", "opens in", "GREEN."), ("HELD GATE", "One on the", "plate. The", "other goes on.")),
}  # fmt: skip
FK_GATE = next(g for g in GATES if g.kind == FK)
#: the F-to-K gate's sign on the wall by its doorway, read from F
FK_SIGN, FK_SIGN_WAY = gate_sign_at(FK_GATE, cell_mid(F_CELL)[:2])
SIGN_AT: dict[str, Place] = {DOOR: (-13, 3, 1), FK: FK_SIGN}
PLAQUE = (-14, -4)
LECTERN: Place = (-14, 4, 1)
RECALL = (-18, 3, -1)
KEY_AT = (-12, 4)  # the key to the hours: three blocks from here rightwards
TALLY = (-6, -14)  # the Tally Engine's clock
TALLY_BULBS = 5  # counting lamps after the clock's own


def logbook(fr: fittings.Frame) -> str:
    return fittings.lectern_with_book(
        fr.facing(-1, 0), LOG_TITLE, LOG_AUTHOR, LOG_PAGES
    )


def tally(fr: fittings.Frame) -> tuple[fittings.Machine, list[Cell]]:
    """the Tally Engine's clock and its counting lamps, the clock's first"""
    f, r = TALLY
    machine = fittings.torch_clock(fr, f, r, h=3, side=1, lamps=True)
    lamps = [fr.at(f + 2 + 2 * n, r, 2) for n in range(TALLY_BULBS + 1)]
    return machine, lamps


def tower_places(free: bool = False) -> tuple[dict[Place, str], set[Place]]:
    """the tower in the frame: its blocks (the dome's floor too, at h 0)
    and the cells kept clear. Every gate open, every lift at the top, the
    timed floors as in Green (``free``: all of them out)"""
    solid: dict[Place, str] = {}
    clear: set[Place] = set()

    def player(deck: int, c: P) -> bool:
        return c in CELLS[deck] and c not in MACHINE[deck] and c != ATRIUM

    def post(deck: int, i: int, j: int) -> bool:
        return deck in CELLS and any(
            (a, b) in CELLS[deck] for a in (i - 1, i) for b in (j - 1, j)
        )

    for deck in (1, 2, 3):
        h0 = walk_h(deck)
        gone = {lift.cell for lift in LIFT_LIST if deck in (lift.low[0], lift.high[0])}
        gone |= {fl.cell for fl in FLOORS if fl.deck == deck} | {ATRIUM}
        if deck > 1:
            for i, j in CELLS[deck]:
                for df in range(-2, 3):
                    for dr in range(-2, 3):
                        if (i, j) in gone and abs(df) < 2 and abs(dr) < 2:
                            continue
                        at = (-8 + 4 * i + df, -8 + 4 * j + dr, h0 - 1)
                        solid.setdefault(at, DECK_FLOOR[deck])
        for li, line in enumerate(LINES):
            for k in range(5):
                for turned in (False, True):
                    a, b = ((k, li - 1), (k, li)) if turned else ((li - 1, k), (li, k))
                    if a not in CELLS[deck] and b not in CELLS[deck]:
                        continue
                    block = GRATE if player(deck, a) and player(deck, b) else BARS
                    for d in range(3):
                        along = -9 + 4 * k + d
                        f, r = (along, line) if turned else (line, along)
                        for h in range(h0, h0 + 3):
                            solid[f, r, h] = block
        for i, f in enumerate(LINES):
            for j, r in enumerate(LINES):
                if not post(deck, i, j):
                    continue
                for h in range(h0, h0 + 3):
                    solid[f, r, h] = CUT
                solid[f, r, h0 + 3] = HOUR_LIGHT[GREEN]
                if post(deck + 1, i, j):
                    solid[f, r, h0 + 4] = CUT
        for i, j in MACHINE[deck]:  # a cylinder behind the bars
            f, r, _ = cell_mid((deck, i, j))
            low = (deck, i, j) == (1, 1, 2)  # the one the door looks through
            for h in range(h0, h0 + (1 if low else 3)):
                solid[f, r, h] = COPPER if h % 2 else LEAF
        for door in ARCHES[deck]:
            for h in (h0, h0 + 1):
                del solid[(*door, h)]
                clear.add((*door, h))
            solid[(*door, h0 + 2)] = CUT
    for hour, at in atrium_lamps():
        solid[at] = f"{BULB}[lit={'true' if hour == GREEN else 'false'}]"
        solid[at[0], at[1], at[2] - 1] = HOUR_BLOCK[hour]
    for g in GATES:
        part = gate_places(g)
        way = (g.door[0] - g.piston[0]) // 2, (g.door[1] - g.piston[1]) // 2
        for at in part["door"]:
            del solid[at]
            clear.add(at)
        for at in part["leaf"]:
            solid[at] = LEAF
        for at in part["piston"]:
            solid[at] = f"{PISTON}[extended=false,facing=%s]" % (way,)
        for at in part["slot"]:
            solid[at] = SLOT_OPEN
        solid[part["lintel"][0]] = lintel(g)[0]
        solid[part["lamp"][0]] = f"{BULB}[lit=true]"
    # the crown: a railed floor on four legs, the Regulator's post, a
    # collar round lift C's top
    top = CROWN_H - 1
    for f in range(-4, 5):
        for r in range(-4, 5):
            solid[f, r, top] = CUT
            edge = max(abs(f), abs(r)) == 4
            if edge and (f, r) != LEVER_POST[:2] and not (f == 4 and abs(r) < 2):
                solid[f, r, CROWN_H] = RAIL
    for f, r in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
        solid[f, r, top - 1] = CUT
    for f, r in ((6, -1), (6, 0), (6, 1), (5, -2), (5, 2), (6, -2), (6, 2)):
        solid[f, r, top] = CUT
        solid[f, r, CROWN_H] = RAIL
    # the timed floors, the lifts parked at the top
    for fl in FLOORS:
        for at in floor_places(fl):
            if free or fl.out(GREEN):
                solid[at] = GRATE
            else:
                solid.pop(at, None)
                clear.add(at)
    for lift in LIFT_LIST:
        for at, block in lift_places(lift, lift.travel).items():
            if block == AIR:
                solid.pop(at, None)
                clear.add(at)
            else:
                solid[at] = block
    # no wall top to stand on: the band between a wall and the floor over
    # it closed at foot height (drifting down from a timed floor, a
    # player could walk the tops and drop into a machine cell),
    # and a lid of bars on each machine cell
    for deck in (1, 2, 3):
        h0 = walk_h(deck)
        for f in range(-10, 11):
            for r in range(-10, 11):
                on_line = f in LINES or r in LINES
                if on_line and (f, r, h0 + 2) in solid and (f, r, h0 + 5) in solid:
                    solid.setdefault((f, r, h0 + 3), BARS)
        for node in MACHINE[deck]:
            f, r, _ = cell_mid((deck, *node))
            for df in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    solid[f + df, r + dr, h0 + 3] = BARS
    return solid, clear


def turn(fr: fittings.Frame, block: str) -> str:
    """a block of ``tower_places`` with its facing written for the frame"""
    if "facing=(" not in block:
        return block
    head, _, rest = block.partition("facing=(")
    step, _, tail = rest.partition(")")
    df, dr = (int(n) for n in step.split(","))
    return f"{head}facing={fr.facing(df, dr)}{tail}"


def room_blocks(
    dome: Dome, form: int = 1, keys: bool = False, free: bool = False
) -> Blocks:
    """
    The room's blocks. ``form`` 2: the two held gates' plates are down;
    ``keys``: the Regulator's two key plates, not its lever; ``free``: the
    solved room, every timed floor out and the lever thrown.
    """
    fr = frame(dome)
    back, ahead = fr.facing(-1, 0), fr.facing(1, 0)
    b = Blocks()
    places, clear = tower_places(free)
    for (f, r, h), block in places.items():
        (b.solid if h else b.floor)[fr.at(f, r, h)] = turn(fr, block)
    b.clear = {fr.at(*at) for at in clear}

    def put(part: dict[Cell, str], new: dict[Cell, str]) -> None:
        if both := set(new) & (set(b.everything()) | b.clear):
            raise ValueError(f"cells given two blocks: {sorted(both)[:5]}")
        part |= new

    for cell, block in plate_bases(dome, form, keys).items():
        (b.solid if cell[1] > dome.floor_y else b.floor)[cell] = block

    # the inputs: the Regulator's lever or its two keys, the held gates'
    # plates; the fittings by the entrance
    post = fittings.input_post(
        fr.at(*LEVER_POST),
        ahead,
        lever(fr, free),
        ("THE REGULATOR", "Two of you up", "here? Two keys."),
    )
    put(b.solid, post.solid)
    put(b.attached, post.attached)
    if keys:
        del b.attached[post.input]
        b.clear.add(post.input)
    for at in KEY_PLATES:
        if keys:
            put(b.attached, {fr.at(*at): PLATE})
        else:
            b.clear.add(fr.at(*at))
        f, r, h = at
        put(b.attached, {fr.at(f - 1, r, h): fittings.standing_sign(
            ahead, "KEY", "Two up here?", "Stand on", "both.")})  # fmt: skip
    for kind, at in ((DOOR, DOOR_PLATE), (FK, FK_PLATE)):
        if form == 2:
            put(b.attached, {fr.at(*at): PLATE})
        else:
            b.clear.add(fr.at(*at))
        text = HELD_SIGNS[kind][form - 1]
        if kind == DOOR:
            sign = fittings.standing_sign(back, *text)
        else:
            sign = fittings.wall_sign(fr.facing(*FK_SIGN_WAY), *text)
        put(b.attached, {fr.at(*SIGN_AT[kind]): sign})
    solid, attached = fittings.plaque_blocks(
        fr,
        *PLAQUE,
        signs=(
            ("CLOCKWORK MAZE", "", "Each gate opens", "in its hour:"),
            ("I GREEN", "II IRON", "III GOLD", ""),
            ("Plan your", "way up.", "The plans are", "by the dial."),
        ),
    )
    put(b.solid, solid)
    put(b.attached, attached)
    put(b.solid, {fr.at(*LECTERN): logbook(fr)})
    solid, attached = fittings.recall_post_blocks(fr, *RECALL)
    put(b.solid, solid)
    put(b.attached, attached)
    for lift in LIFT_LIST:
        if lift is RAM_LIFT:
            continue
        at, way = lift_sign_at(lift)
        put(b.attached, {fr.at(*at): fittings.wall_sign(
            fr.facing(*way), f"LIFT {lift.name.upper()}", "Its gate opens", "in GOLD.", "Stand on it.")})  # fmt: skip
    dress = dressing_blocks(dome)
    put(b.floor, dress.floor)
    put(b.solid, dress.solid)
    put(b.attached, dress.attached)
    b.moving |= dress.moving
    return b


def plate_bases(dome: Dome, form: int = 1, keys: bool = False) -> dict[Cell, str]:
    """the blocks under the four plates' places: gold while the plate is
    there, the floor round it while it is not"""
    fr = frame(dome)
    door = fr.at(DOOR_PLATE[0], DOOR_PLATE[1], 0)
    shell = domes.LIGHT if door in domes.light_cells(dome)[0] else domes.FLOOR
    found = {door: BRASS if form == 2 else shell}
    f, r, h = FK_PLATE
    found[fr.at(f, r, h - 1)] = BRASS if form == 2 else DECK_FLOOR[2]
    for f, r, h in KEY_PLATES:
        found[fr.at(f, r, h - 1)] = BRASS if keys else CUT
    return found


def dressing_blocks(dome: Dome) -> Blocks:
    """what is only to look at: the key to the hours, the Great Dial, the
    Tally Engine in its cage, the right yard's tanks and pipes, the Walk
    and its stairs. No lever, button or plate; ``reset`` leaves all of it
    alone (the dial's lamps are the clock's, and only they change)"""
    fr = frame(dome)
    ahead, back = fr.facing(1, 0), fr.facing(-1, 0)
    d = Blocks()
    kf, kr = KEY_AT
    for hour in range(3):
        d.solid[fr.at(kf, kr + hour, 1)] = CUT
        d.solid[fr.at(kf, kr + hour, 2)] = HOUR_BLOCK[hour]
    lamps, disc = dial_places()
    for at, block in disc.items():
        d.solid[fr.at(*at)] = block
    for n, at in enumerate(lamps):
        d.solid[fr.at(*at)] = f"{BULB}[lit={'true' if n == 0 else 'false'}]"
    for at, block in plan_blocks().items():
        d.solid[fr.at(*at)] = block

    # the Tally Engine: a torch clock on a bench, its first lamp read by a
    # comparator into the next lamp, and so on: six lamps counting
    machine, row = tally(fr)
    f, r = TALLY
    for df in range(-2, 2 * TALLY_BULBS + 3):
        for dr in (0, -1):
            d.solid[fr.at(f + df, r + dr, 1)] = CUT
    d.solid |= machine.bed | machine.solid
    d.attached |= machine.attached
    d.moving |= machine.moving
    for n, cell in enumerate(row[1:]):
        d.solid[cell] = f"{BULB}[lit=false]"
        d.attached[fr.at(f + 3 + 2 * n, r, 2)] = f"minecraft:comparator[facing={back}]"
        d.moving |= {cell, fr.at(f + 3 + 2 * n, r, 2)}
    f1, f2 = f - 3, f + 2 * TALLY_BULBS + 3
    for cf in range(f1, f2 + 1):
        for cr in range(r - 2, r + 2):
            if cf in (f1, f2) or cr in (r - 2, r + 1):
                for h in (1, 2, 3):
                    d.solid[fr.at(cf, cr, h)] = BARS
            d.solid[fr.at(cf, cr, 4)] = BARS  # a lid: nobody in, no hand on it
    d.attached[fr.at(f + 5, r + 2, 1)] = fittings.standing_sign(
        fr.facing(0, 1), "TALLY ENGINE", "It is counting.", "Nobody set", "it going."
    )

    # the right yard: three tanks and the pipe between them
    for tf, tr, high in ((-5, 13, 4), (3, 13, 4), (-1, 15, 6)):
        for df in (0, 1):
            for dr in (0, 1):
                for h in range(1, high + 1):
                    d.solid[fr.at(tf + df, tr + dr, h)] = TANK if h < high else CUT
    for pf in range(-3, 3):
        d.solid[fr.at(pf, 13, 3)] = f"{ROD}[facing={ahead}]"

    # the Walk: a railed deck of planks round the wall, six stairs up to
    # each end, posts under its inner edge
    deck, rails = walk_places()
    for f, r in deck:
        d.solid[fr.at(f, r, 6)] = PLANKS
        if (f, r) in rails:
            d.solid[fr.at(f, r, 7)] = RAIL
    for f, r in sorted(rails):
        inner = math.hypot(f, r) < 17.5
        if inner and abs(r) > 3 and (f % 6 == 0 or r % 6 == 0) and f > -8:
            for h in range(1, 6):
                d.solid.setdefault(fr.at(f, r, h), CUT)
    stairs = "minecraft:waxed_cut_copper_stairs"
    for i in range(6):
        for r in (-17, -16, 16, 17):
            d.solid[fr.at(-14 + i, r, 1 + i)] = f"{stairs}[facing={ahead},half=bottom]"
    return d


def frame(dome: Dome) -> fittings.Frame:
    return fittings.frame(dome)


#: the brass plans on the tower's face, either side of the dial: for each
#: deck where its cell (0, 0) is, a block a cell, forward up the board
PLAN_AT: dict[int, Place] = {1: (-11, -11, 5), 2: (-11, 7, 5), 3: (-11, 7, 10)}


def plan_blocks() -> dict[Place, str]:
    """the boards: a block for each cell of a deck: a cell to walk in, a
    machine cell, the atrium (bars), a lift (a lit bulb), a timed floor
    (grating, as it is)"""
    found = {}
    lifts = {n for lift in LIFT_LIST[:3] for n in (lift.low, lift.high)}
    for deck, (f, r, h) in PLAN_AT.items():
        for i, j in CELLS[deck]:
            node = (deck, i, j)
            if (i, j) == ATRIUM:
                block = BARS
            elif (i, j) in MACHINE[deck]:
                block = COPPER
            elif floor_at(node):
                block = GRATE
            elif node in lifts:
                block = f"{BULB}[lit=true]"
            else:
                block = BOARD
            found[f, r + j, h + i] = block
    return found


def plan_marks() -> list[tuple[tuple[float, float, float], str, str, float]]:
    """what stands on the boards: (where in the frame, a block or "", the
    words, the words' size): a small block in each gate's own lintel
    block where the gate is, with its numeral; a light where an arch is;
    the hours of a timed floor; UP on a lift's cell and IN where the one
    from below comes up; a title"""
    marks: list[tuple[tuple[float, float, float], str, str, float]] = []
    floors = {fl.node: fl for fl in FLOORS}
    for deck, (f, r, h) in PLAN_AT.items():

        def at(pf: float, pr: float, f=f, r=r, h=h) -> tuple[float, float, float]:
            """a place on the deck (f, r) as a point on the board's face"""
            return (f - 0.5, r + (pr + 8) / 4, h + 0.5 + (pf + 8) / 4)

        for g in GATES:
            if g.deck == deck and g.kind not in (RAM, GREAT):
                block, words = lintel(g)
                marks.append((at(*g.door), block, words, 0.5))
        marks += [(at(*door), ARCH_MARK, "", 0.5) for door in ARCHES[deck]]
        for i, j in CELLS[deck]:
            node, words = (deck, i, j), ""
            if node in floors:
                words = " ".join(NUMERAL[n] for n in range(3) if floors[node].out(n))
            for lift in LIFT_LIST[:3]:
                words = {lift.low: "UP", lift.high: "IN"}.get(node, words)
            if words:
                marks.append((at(-8 + 4 * i, -8 + 4 * j), "", words, 0.45))
        rows = [i for i, _ in CELLS[deck]]
        mid = sum(j for _, j in CELLS[deck]) / len(CELLS[deck])
        top = (f - 0.5, r + mid, h + max(rows) + 1.15)
        marks.append((top, "", f"DECK {deck}", 0.9))
    return marks


def plan_summons(fr: fittings.Frame) -> list[str]:
    """the commands that summon ``plan_marks``, facing the entrance"""
    yaw = {"south": 0, "west": 90, "north": 180, "east": -90}[fr.facing(-1, 0)]
    ox, oy, oz = fr.at(0, 0, 0)
    found = []

    def point(f: float, r: float, h: float) -> tuple[float, float, float]:
        return (
            ox + 0.5 + f * fr.forward[0] + r * fr.right[0],
            oy + h,
            oz + 0.5 + f * fr.forward[1] + r * fr.right[1],
        )

    for (f, r, h), block, words, size in plan_marks():
        if block:
            x, y, z = point(f, r, h)
            found.append(
                f"summon minecraft:block_display {x:.3f} {y:.3f} {z:.3f} "
                f'{{Tags:["{ENTITY_TAG}"],block_state:{fittings.block_state(block)},'
                "transformation:{translation:[-0.2f,-0.2f,-0.2f],"
                "scale:[0.4f,0.4f,0.4f],left_rotation:[0f,0f,0f,1f],"
                "right_rotation:[0f,0f,0f,1f]}}"
            )
        if words:
            pos = point(f - (0.23 if block else 0.03), r, h - 0.12 * size / 0.5)
            label = fittings.label_text(words, "black" if block else "white")
            found.append(fittings.display((ENTITY_TAG,), pos, yaw, label, size))
    return found


def inputs(dome: Dome, form: int = 1, keys: bool = False) -> set[Cell]:
    """every lever, button and plate of the room in a form"""
    fr = frame(dome)
    f, r, side = RECALL
    found = {fr.at(f, r + side, 2)}
    if keys:
        found |= {fr.at(*at) for at in KEY_PLATES}
    else:
        found.add(fr.at(LEVER_POST[0] + 1, LEVER_POST[1], LEVER_POST[2] + 1))
    if form == 2:
        found |= {fr.at(*DOOR_PLATE), fr.at(*FK_PLATE)}
    return found


def summons(dome: Dome) -> list[str]:
    """the commands that summon the room's entities: a numeral on both
    faces of every gate's lintel, the key's names, the Great Door's
    notice, the recall button's interaction, the pendulum, the marks on
    the plans (the dial's hand is the pack's: ``hand/put``)"""
    fr = frame(dome)
    yaws = {"south": 0, "west": 90, "north": 180, "east": -90}
    found = []

    def text(at: Place, way: P, words: str, up: float = 0.3, scale: float = 1) -> None:
        x, y, z = fr.at(*at)
        wx, _, wz = (a - b for a, b in zip(fr.at(*way, 0), fr.at(0, 0, 0), strict=True))
        pos = (x + 0.5 + 0.52 * wx, y + up, z + 0.5 + 0.52 * wz)
        yaw = yaws[fr.facing(*way)]
        label = fittings.label_text(words, "white")
        found.append(fittings.display((ENTITY_TAG,), pos, yaw, label, scale))

    for g in GATES:
        normal = (1, 0) if g.door[0] in LINES else (0, 1)
        for sign in (1, -1):
            way = (normal[0] * sign, normal[1] * sign)
            text(gate_places(g)["lintel"][0], way, lintel(g)[1])
    kf, kr = KEY_AT
    for hour in range(3):
        text((kf, kr + hour, 2), (-1, 0), f"{NUMERAL[hour]} {HOURS[hour]}")
    text((10, 0, 4), (1, 0), "Opens when the clock is ours again.", 0.2, 0.6)
    found.append(fittings.summon_recall(fr, *RECALL, tags=(ENTITY_TAG,)))
    for tag, pose in zip(PEND_TAGS, pendulum(fr, 1), strict=True):
        found.append(
            f"summon minecraft:block_display {middle(fr.at(-12, 0, 9), 0.5)} "
            f'{{Tags:["{ENTITY_TAG}","{tag}"],'
            f"block_state:{fittings.block_state(BRASS)},{pose}}}"
        )
    return found + plan_summons(fr)


def pendulum(fr: fittings.Frame, side: int) -> tuple[str, str]:
    """the pendulum's rod and bob at one end of the swing (``side`` -1 or
    1), each the ``transformation`` of a block display hung at the dial's
    middle"""
    angle, length = 0.5 * side, 4.0
    return (
        turned(fr, angle, (0.15, length, 0.15), (-0.075, -length, -0.075)),
        turned(fr, angle, (0.8, 0.8, 0.8), (-0.4, -length - 0.4, -0.4)),
    )


# ------------------------------------------------------ the offline checks

#: (form, keys, free): every shape the room's inputs and floors can take
SHAPES = ((1, False, False), (2, False, False), (2, True, False), (1, False, True))

domes.allow(
    INDEX,
    "tower",
    "the tower stands between the entrance and the outgoing door's window; "
    "it is grating and bars, and its Great Door faces the airlock",
)


def rides(dome: Dome) -> list[tuple[Cell, Cell]]:
    """each lift's ride: where a rider's feet are at the bottom and at
    the top (beside the ram, which stands in the middle at the bottom)"""
    fr = frame(dome)
    found = []
    for lift in LIFT_LIST:
        f, r = lift.mid
        found.append((fr.at(f - 1, r, lift.bottom + 1), fr.at(f - 1, r, lift.top + 1)))
    return found


def reach(dome: Dome, b: Blocks) -> set[Cell]:
    """where a player's feet can get to from the entrance: by walking
    (``rooms.reach``) and by the lifts; nobody stands on a rail"""
    blocked = set(b.solid)
    blocked |= {(x, y + 1, z) for (x, y, z), block in b.solid.items() if block == RAIL}
    seen = rooms.reach(dome, domes.entrance(dome)[:3], b.solid, blocked)
    grew = True
    while grew:
        grew = False
        for foot, head in rides(dome):
            for a, z in ((foot, head), (head, foot)):
                if a in seen and z not in seen:
                    seen |= rooms.reach(dome, z, b.solid, blocked)
                    grew = True
    return seen


def shapes_in_play(dome: Dome) -> list[set[Cell]]:
    """the room as it can stand while someone is in it, as the cells that
    hold a body up or block it: every gate open (a gate only ever takes a
    way away), the timed floors in and out, and with the platforms at the
    top and at the bottom"""
    fr = frame(dome)
    b = room_blocks(dome, free=True)
    holes = {fr.at(*p) for fl in FLOORS for p in floor_places(fl)}
    found = []
    for k in ("top", "bottom"):
        solid = set(b.solid)
        if k == "bottom":
            for lift in LIFT_LIST:
                for p, block in lift_places(lift, 0).items():
                    (solid.discard if block == AIR else solid.add)(fr.at(*p))
        found += [solid, solid - holes]
    return found


def traps(dome: Dome) -> tuple[set[Cell], set[Cell]]:
    """
    Where a player's feet can get to from the entrance, and of those the
    ones from which there is no way back to it. Wider than ``reach``: a
    fall is of any height and drifts a block sideways for each block fallen
    (as a player steering in the air, or under slow falling, can), a rail
    can be landed on though not stepped onto, a timed floor can go from
    under someone, and a lift takes whoever stands on its platform to its
    other end. A move in any of ``shapes_in_play`` counts.
    """
    cells = domes.dome_cells(dome)
    fr = frame(dome)
    b = room_blocks(dome, free=True)
    rails = {c for c, block in b.solid.items() if block == RAIL}
    ride: dict[Cell, Cell] = {}
    for lift in LIFT_LIST:
        f, r = lift.mid
        for df in (-1, 0, 1):
            for dr in (-1, 0, 1):
                low = fr.at(f + df, r + dr, lift.bottom + 1)
                high = fr.at(f + df, r + dr, lift.top + 1)
                ride[low], ride[high] = high, low
    shapes = []
    for solid in shapes_in_play(dome):
        ground = set(cells.floor) | solid

        def free(c: Cell, solid=solid) -> bool:
            return c in cells.interior and c not in solid

        def held(c: Cell, ground=ground) -> bool:
            return (c[0], c[1] - 1, c[2]) in ground

        shapes.append((free, held))

    def fall(c: Cell, free, held) -> set[Cell]:
        """where a body in the air at ``c`` can come to rest"""
        out, edge, seen = set(), [c], {c}
        while edge:
            x, y, z = edge.pop()
            if held((x, y, z)):
                out.add((x, y, z))
                continue
            for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                to = (x + dx, y - 1, z + dz)
                if to not in seen and free(to) and free((to[0], y, to[2])):
                    seen.add(to)
                    edge.append(to)
        return out

    def moves(c: Cell) -> set[Cell]:
        x, y, z = c
        out = set()
        for free, held in shapes:
            if not (free(c) and free((x, y + 1, z))):
                continue
            if not held(c):  # the floor went from under them
                out |= fall(c, free, held)
                continue
            if c in ride:
                out.add(ride[c])
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                to, up = (x + dx, y, z + dz), (x + dx, y + 1, z + dz)
                rail_step = (to[0], y, to[2]) in rails
                if free(up) and free((x, y + 2, z)) and free((up[0], y + 2, up[2])):
                    if held(up) and not rail_step:
                        out.add(up)
                if free(to) and free(up):
                    out |= fall(to, free, held)
        out.discard(c)
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
    return seen, seen - home


def machine_cells(dome: Dome) -> set[Cell]:
    """the inside of every machine cell, from its floor to under the deck
    above"""
    fr = frame(dome)
    found = set()
    for deck, where in MACHINE.items():
        for node in where:
            f, r, h = cell_mid((deck, *node))
            found |= {
                fr.at(f + df, r + dr, h + dh)
                for df in (-1, 0, 1)
                for dr in (-1, 0, 1)
                for dh in range(5)
            }
    return found


def local(fr: fittings.Frame, cell: Cell) -> Place:
    """a cell in the frame: (f, r, h)"""
    dx, dz = cell[0] - fr.origin[0], cell[2] - fr.origin[2]
    return (
        dx * fr.forward[0] + dz * fr.forward[1],
        dx * fr.right[0] + dz * fr.right[1],
        cell[1] - fr.origin[1],
    )


def trap_problems(dome: Dome) -> list[str]:
    """nobody can get into a machine cell, and nowhere a player can get to
    is a place with no way back to the entrance"""
    fr = frame(dome)
    seen, pits = traps(dome)
    problems = []
    if inside := seen & machine_cells(dome):
        where = sorted(local(fr, c) for c in inside)
        problems.append(f"{len(inside)} cells of machine cells reachable: {where[:4]}")
    if pits:
        where = sorted(local(fr, c) for c in pits)
        problems.append(f"{len(pits)} cells with no way back: {where[:6]}")
    return problems


def walks(dome: Dome) -> dict[str, Cell]:
    """where a player must be able to get to from the entrance, by name:
    the cell their feet are in"""
    fr = frame(dome)
    ux, uz = domes.outward(dome, layout.TUNNELS[dome.index])
    ox, oy, oz = dome.floor_centre
    mouth = dome.radius - 3
    lf, lr, _ = LECTERN
    places: dict[str, Place] = {
        "the plaque": (PLAQUE[0] - 2, PLAQUE[1], 1),
        "the logbook": (lf - 1, lr, 1),
        "the key to the hours": (KEY_AT[0] - 1, KEY_AT[1] + 1, 1),
        "the tower door's plate": DOOR_PLATE,
        "the second held gate's plate": FK_PLATE,
        "the Tally Engine": (TALLY[0] + 5, TALLY[1] + 3, 1),
        "the right yard": (0, 12, 1),
        "the Walk": (18, 0, 7),
        "the Regulator": (LEVER_POST[0] + 2, LEVER_POST[1], CROWN_H),
        "the first key": KEY_PLATES[0],
        "the second key": KEY_PLATES[1],
        "the foot of the Ram": (-1, 0, 1),
    }
    low = {lift.low for lift in LIFT_LIST}
    for node in nodes():
        if node in ("out", "crown"):
            continue
        f, r, h = cell_mid(node)
        # (a ram stands in the middle of a lift's lower cell)
        places[f"cell {node}"] = (f - 1 if node in low else f, r, h)
    targets = {name: fr.at(*at) for name, at in places.items()}
    targets["the way out"] = (ox + ux * mouth, oy + 1, oz + uz * mouth)
    return targets


def walk_problems(dome: Dome) -> list[str]:
    """every place of ``walks`` can be got to from the entrance at foot
    and head height, in the solo and the duo form, in the solved room
    (every gate open, every floor out: the plan's gates are open)"""
    problems = []
    for form, keys in ((1, False), (2, True)):
        seen = reach(dome, room_blocks(dome, form, keys, free=True))
        problems += [
            f"form {form}: no way from the entrance to {name} at {cell}"
            for name, cell in walks(dome).items()
            if cell not in seen
        ]
    return problems


def sight_problems(dome: Dome) -> list[str]:
    """the clock can be read: every lamp of the Great Dial and the key to
    the hours from the entrance and the logbook, and the atrium's hour
    lamps from the cell inside the tower door (each by the cell in front
    of it, which the line of sight must reach)"""
    fr = frame(dome)
    blocks = room_blocks(dome).above()
    spots = walks(dome)
    eyes = {"the entrance": domes.entrance(dome)[:3], "the log": spots["the logbook"]}
    lamps, _ = dial_places()
    targets = {
        f"lamp {n} of the dial": fr.at(f - 1, r, h) for n, (f, r, h) in enumerate(lamps)
    }
    for hour in range(3):
        targets[f"the key's {HOURS[hour]}"] = fr.at(KEY_AT[0] - 1, KEY_AT[1] + hour, 2)
    problems = rooms.sight_problems(blocks, eyes, targets)
    inside = {"the cell inside the door": spots["cell (1, 0, 2)"]}
    hours = {
        f"the atrium's {HOURS[hour]} lamp": fr.at(f - 1, r, h)
        for hour, (f, r, h) in atrium_lamps()
        if (f, h) == (-2, 4)
    }
    return problems + rooms.sight_problems(blocks, inside, hours)


def plan_problems(dome: Dome) -> list[str]:
    """the gates in the built room: nothing redstone would work is face
    to face with a valve slot but that gate's own pistons, and the Tally
    Engine's redstone is 3 blocks or more from every gate"""
    fr = frame(dome)
    b = room_blocks(dome)
    everything = b.everything()
    problems = table_problems()
    machine, lamps = tally(fr)
    engine = machine.cells | set(lamps)
    for g in GATES:
        part = {k: [fr.at(*at) for at in v] for k, v in gate_places(g).items()}
        for x, y, z in part["slot"]:
            for dx, dy, dz in rooms.FACES:
                beside = (x + dx, y + dy, z + dz)
                block = rooms.name(everything.get(beside, ""))
                if beside in part["piston"] or not block:
                    continue
                if any(kind in block for kind in rooms.SENSITIVE):
                    problems.append(f"{g.name}: its slot is against {block}")
        mine = [c for cells in part.values() for c in cells]
        if any(max(abs(p - q) for p, q in zip(c, e, strict=True)) < 3
               for c in mine for e in engine):  # fmt: skip
            problems.append(f"{g.name}: the Tally Engine is within 3 blocks")
    return problems


def gantry_problems(dome: Dome) -> list[str]:
    """the Walk and the rest against the tunnels' cells: two clear blocks
    over each way in and over the entrance spot, and nothing at all over
    the pump engine, whose chimney steams"""
    used = set(room_blocks(dome).above())
    reserved = tunnels.reserved_cells(dome)
    engine = set(tunnels.engine_cells(layout.TUNNELS[dome.index]).values())
    over = {(x, y + up, z) for x, y, z in reserved for up in (1, 2)} - reserved
    over |= {(x, y + up, z) for x, y, z in engine for up in range(1, dome.radius)}
    return [f"{len(bad)} blocks over reserved cells: {min(bad)}"] if (
        bad := over & used
    ) else []  # fmt: skip


def room_problems(dome: Dome) -> list[str]:
    """everything the build asks of the plan before it places a block"""
    fr = frame(dome)
    problems = []
    for form, keys, free in SHAPES:
        try:
            b = room_blocks(dome, form, keys, free)
        except ValueError as e:
            return [str(e)]
        more = b.clear | {fr.at(-12, 0, h) for h in range(4, 10)}
        problems += rooms.room_problems(dome, b.above(), b.floor, more)
        problems += rooms.input_problems(
            b.above(), inputs(dome, form, keys), floor=b.floor
        )
        if set(b.floor) & set(b.above()) or set(b.solid) & set(b.attached):
            problems.append("a cell is given two blocks")
    problems += rooms.window_problems(dome, room_blocks(dome).above())
    problems += plan_problems(dome) + gantry_problems(dome)
    problems += walk_problems(dome) + trap_problems(dome) + sight_problems(dome)
    return problems + solo_problems() + pair_problems() + puzzle_problems()


# --------------------------------------------------------------- the build


def build(ctx: Any) -> str:
    """the Clockwork Maze inside its shell, in place of the stub; wipes
    what was inside but the pump engine, and leaves the room as ``reset``
    does. Plain blocks go by ``fill``, so that the bars join up"""
    dome = ctx.layout.DOMES[INDEX]
    if problems := room_problems(dome):
        raise RuntimeError("the Clockwork Maze: " + "; ".join(problems[:12]))
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    engine = set(tunnels.engine_cells(ctx.layout.TUNNELS[INDEX]).values())
    for command in game.clear_stub_commands(dome):
        ctx.cmd(command)
    ctx.cmd(f"kill @e[tag={ENTITY_TAG}]")
    ctx.fill_boxes(cells.interior - engine, AIR)
    for part in (b.floor, b.solid):
        plain = {c: block for c, block in part.items() if "{" not in block}
        for block, where in sorted(domes.by_block(plain).items()):
            ctx.fill_boxes(where, block)
        for cell, block in sorted(part.items()):
            if cell not in plain:
                ctx.setblock(cell, block)
    for cell, block in sorted(b.attached.items()):
        ctx.setblock(cell, block)
    for command in summons(dome):
        ctx.cmd(command)
    # the pack's own idea of the room, if the pack is installed
    ctx.function(f"dome/{INDEX}/reset")
    ctx.advance(10)
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    return (
        f"{dome.name}: {len(b.everything())} blocks: a tower of three decks "
        f"and a crown, {len(GATES)} piston gates, {len(FLOORS)} timed floors, "
        f"{len(LIFT_LIST)} lifts, the Great Dial with its hand and pendulum, "
        f"{len(PLAN_AT)} plans, the Tally Engine, the Walk, plaque, logbook, "
        "recall button"
    )


# ----------------------------------------------------------- the functions


def _s(name: str) -> str:
    return f"#maze.{name} {OBJ}"


def _set(name: str, value: int) -> str:
    return f"scoreboard players set {_s(name)} {value}"


def _is(name: str, value: Any) -> str:
    return f"if score {_s(name)} matches {value}"


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


def _setblock(cell: Cell, block: str) -> str:
    return f"setblock {_xyz(cell)} {block}"


def _someone(a: Cell, b: Cell) -> str:
    """a player in the game, or a stand-in, touching a box of cells"""
    return f"entity @e[tag=st.in,{dp.box_selector(a, b)}]"


def _fills(blocks: dict[Cell, str]) -> list[str]:
    """lines that write these blocks, a ``fill`` a box"""
    return [
        dp.fill(a, b, block)
        for block, where in sorted(domes.by_block(blocks).items())
        for a, b in domes.boxes(where)
    ]


def _lamp(cell: Cell, lit: bool, when: str = "") -> str:
    """the line that makes a bulb lit or dark, if it is not"""
    block = f"{BULB}[lit={'true' if lit else 'false'}]"
    return (
        f"execute {when}unless block {_xyz(cell)} {block} run {_setblock(cell, block)}"
    )


def gate_lines(dome: Dome, g: Gate) -> dict[str, Any]:
    """a gate's lines: ``open`` and ``shut`` (each takes the clauses it
    waits on), its ``lamp`` (lit or not) and its three ``mend`` lines a
    piston"""
    fr = frame(dome)
    part = {k: [fr.at(*at) for at in v] for k, v in gate_places(g).items()}
    slot, door = part["slot"], part["door"]
    full = f"block {_xyz(slot[0])} {POWER}"
    mend = []
    for p, leaf, d in zip(part["piston"], part["leaf"], door, strict=True):
        is_in = f"execute if block {_xyz(p)} {PISTON}[extended=false] "
        is_out = (
            f"execute if block {_xyz(p)} {PISTON}[extended=true] "
            f"if block {_xyz(leaf)} minecraft:piston_head "
        )
        mend += [
            f"{is_in}unless block {_xyz(leaf)} {LEAF} run {_setblock(leaf, LEAF)}",
            f"{is_in}unless block {_xyz(d)} {AIR} run {_setblock(d, AIR)}",
            f"{is_out}unless block {_xyz(d)} {LEAF} run {_setblock(d, LEAF)}",
        ]
    return {
        # open: the slot cleared. Shut: the slot filled, but never while
        # someone is in the doorway (tried again every tick)
        "open": lambda when="": (
            f"execute {when}if {full} run " + dp.fill(slot[0], slot[1], SLOT_OPEN)
        ),
        "shut": lambda when="": (
            f"execute {when}unless {full} "
            f"unless {_someone(door[0], door[1])} run "
            + dp.fill(slot[0], slot[1], POWER)
        ),
        "lamp": lambda lit, when="": _lamp(part["lamp"][0], lit, when),
        "mend": mend,
    }


def functions(pack: dp.Pack) -> None:
    """the Clockwork Maze's functions (see the module docstring)"""
    dome = layout.DOMES[INDEX]
    fr = frame(dome)
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    open_dome = f"#d{INDEX} {OBJ}"
    pack.constants(OBJ, 10, 100)
    free, not_free = _is("free", 1) + " ", "unless score " + _s("free") + " matches 1 "
    lines = {g: gate_lines(dome, g) for g in GATES}
    hour_gates = [g for g in GATES if g.kind in (GREEN, IRON, GOLD)]
    heart = middle(fr.at(0, 0, 10))

    def at(place: Place) -> Cell:
        return fr.at(*place)

    def fid(name: str) -> str:
        return pack.id(f"{base}/{name}")

    def call(name: str, when: str = "") -> str:
        return f"execute {when}run function {fid(name)}" if when else (
            f"function {fid(name)}"
        )  # fmt: skip

    def sound(name: str, volume: float = 1, pitch: float = 1) -> str:
        return f"playsound minecraft:{name} block {here} {heart} {volume} {pitch}"

    def loud(name: str, pitch: float = 1, when: str = "") -> str:
        """a sound at each player's own ear: as loud wherever they are"""
        return (
            f"execute {when}as {here} at @s run "
            f"playsound minecraft:{name} block @s ~ ~ ~ 1 {pitch}"
        )

    def layer(deck: int) -> tuple[Cell, Cell]:
        """the level of a deck's post lights, across the tower"""
        h = walk_h(deck) + 3
        return at((-10, -10, h)), at((10, 10, h))

    def say(text: str, colour: str = "yellow") -> str:
        return f'tellraw {here} {{text:{fittings.snbt(text)},color:"{colour}"}}'

    # -- the values of the level in force
    pack.function(
        f"{base}/scale",
        [
            _set("qlen", QUARTER),
            f"scoreboard players operation {_s('qlen')} *= #diff.timer {OBJ}",
            f"scoreboard players operation {_s('qlen')} /= #100 {OBJ}",
            _set("early", 0),
            f"execute if score #diff.timer {OBJ} matches ..80 run {_set('early', 1)}",
            f"execute if score #diff.timer {OBJ} matches ..60 run {_set('early', 2)}",
        ],
    )

    # -- the clock: ticks to quarters, quarters to hours, the dial
    pack.function(
        f"{base}/clock",
        [
            f"scoreboard players add {_s('t')} 1",
            f"scoreboard players operation {_s('w')} = {_s('t')}",
            f"scoreboard players operation {_s('w')} %= #10 {OBJ}",
            # the warning, through an hour's last quarter: every half
            # second a clank, and the lights of every post go to the
            # colour of the hour to come and back
            call("warn", f"{_is('last', 1)} {_is('w', 0)} "),
            call("bell", _is("bells", "1..") + " "),
            f"execute if score {_s('t')} >= {_s('qlen')} run function {fid('quarter')}",
        ],
    )
    pack.function(
        f"{base}/warn",
        [
            f"scoreboard players add {_s('fl')} 1",
            f"execute {_is('fl', '2..')} run {_set('fl', 0)}",
            loud("block.note_block.cow_bell", 1.3, not_free),
            loud("block.note_block.hat", 1.4, not_free),
            *(
                call(f"lights/{(h + n) % 3}", f"{_is('hour', h)} {_is('fl', n)} ")
                for h in range(3)
                for n in (0, 1)
            ),
        ],
    )
    # the bell counts the hour: one stroke for Green, two for Iron, three
    # for Gold, each hour at its own pitch
    pack.function(
        f"{base}/bell",
        [
            f"scoreboard players remove {_s('bellt')} 1",
            f"execute {_is('bellt', '1..')} run return 0",
            *(
                loud("block.bell.use", pitch, _is("hour", h) + " ")
                for h, pitch in enumerate(BELL_PITCH)
            ),
            f"scoreboard players remove {_s('bells')} 1",
            _set("bellt", BELL_GAP),
        ],
    )
    pack.function(
        f"{base}/quarter",
        [
            _set("t", 0),
            f"scoreboard players add {_s('q')} 1",
            f"execute {_is('q', '12..')} run {_set('q', 0)}",
            _set("last", 0),
            *(f"execute {_is('q', 4 * h + 3)} run {_set('last', 1)}" for h in range(3)),
            call("dial"),
            call("hand/go"),
            *(call(f"strike/{h}", f"{_is('q', 4 * h)} ") for h in range(3)),
            f"scoreboard players add {_s('swing')} 1",
            f"execute {_is('swing', '2..')} run {_set('swing', 0)}",
            *(call(f"pend/{n}", f"{_is('swing', n)} ") for n in (0, 1)),
        ],
    )
    lamps, _ = dial_places()
    dial = []
    for n, place in enumerate(lamps):
        lit = f"score {_s('q')} matches {n}..{4 * (n // 4) + 3} "
        dial += [
            _lamp(at(place), True, f"if {lit}"),
            _lamp(at(place), False, f"unless {lit}"),
        ]
    pack.function(f"{base}/dial", dial)
    for n, side in enumerate((-1, 1)):
        pack.function(
            f"{base}/pend/{n}",
            [
                f"data merge entity @e[type=minecraft:block_display,tag={tag},limit=1] "
                f"{{start_interpolation:0,interpolation_duration:20,{pose}}}"
                for tag, pose in zip(PEND_TAGS, pendulum(fr, side), strict=True)
            ],
        )
    # the hand: a quarter's sweep to the next lamp, begun at each quarter,
    # so that it stands on twelve as Green strikes; made anew if it is gone
    one_hand = f"@e[type=minecraft:block_display,tag={HAND_TAG},limit=1]"
    pack.function(f"{base}/hand/put", [f"kill @e[tag={HAND_TAG}]", hand_summon(fr)])
    pack.function(
        f"{base}/hand/go",
        [
            f"execute unless entity @e[tag={HAND_TAG}] run function {fid('hand/put')}",
            f"execute store result entity {one_hand} interpolation_duration int 1 "
            f"run scoreboard players get {_s('qlen')}",
            *(
                f"execute {_is('q', q)} run data merge entity {one_hand} "
                f"{{start_interpolation:0,{hand(fr, q + 1)}}}"
                for q in range(12)
            ),
        ],
    )
    for h in range(3):
        pack.function(
            f"{base}/lights/{h}",
            [
                dp.fill(*layer(deck), HOUR_LIGHT[h], f"replace {HOUR_LIGHT[other]}")
                for deck in (1, 2, 3)
                for other in range(3)
                if other != h
            ],
        )
    for h in range(3):
        going = []
        if h != IRON:  # up at the strike of Green, down at Gold
            to = 1 if h == GREEN else 0
            going = [_set(f"l{lift.name}.to", to) for lift in LIFT_LIST[:3]]
            going.append(
                f"execute {free}{_is('ramwait', -1)} run {_set('lram.to', to)}"
            )
        pack.function(
            f"{base}/strike/{h}",
            [
                _set("hour", h),
                loud("block.bell.use", BELL_PITCH[h]),
                _set("bells", h),
                _set("bellt", BELL_GAP),
                _set("fl", 0),
                call(f"lights/{h}"),
                call(f"atrium/{h}"),
                call(f"lamps/{h}", not_free),
                *going,
            ],
        )
        pack.function(
            f"{base}/atrium/{h}",
            [
                _setblock(at(place), f"{BULB}[lit={'true' if hour == h else 'false'}]")
                for hour, place in atrium_lamps()
            ],
        )
        pack.function(
            f"{base}/lamps/{h}", [lines[g]["lamp"](g.kind == h) for g in hour_gates]
        )
        # one hour's whole table, safe to run every tick
        pack.function(
            f"{base}/gates/{h}",
            [lines[g]["open" if g.kind == h else "shut"]() for g in hour_gates],
        )
    pack.function(f"{base}/lamps/free", [lines[g]["lamp"](True) for g in GATES])
    pack.function(f"{base}/gates/free", [lines[g]["open"]() for g in GATES])
    pack.function(f"{base}/mend", [line for g in GATES for line in lines[g]["mend"]])
    for name in ("mend_a", "mend_b"):  # a mend when nobody is there to tick
        pack.function(f"{base}/{name}", [call("mend")])
    pack.function(
        f"{base}/gates",
        [
            *(call(f"gates/{h}", f"{not_free}{_is('hour', h)} ") for h in range(3)),
            call("held", not_free),
            call("gates/free", free),
        ],
    )

    # -- the gates that do not simply follow the hour
    def count(name: str, a: Place, b: Place) -> str:
        return f"execute store result score {_s(name)} if {_someone(at(a), at(b))}"

    held = [
        count("in", (-10, -10, 1), (10, 10, 23)),
        count("up", (-10, -10, 7), (10, 10, 23)),
        count("near", (3, -9, 7), (9, -7, 11)),  # cell F and lift A's top
        count("top", (-6, -6, 13), (6, 6, 23)),
        f"scoreboard players operation {_s('beyond')} = {_s('up')}",
        f"scoreboard players operation {_s('beyond')} -= {_s('near')}",
    ]
    duo = _is("form", 2) + " "
    for g in GATES:
        if g in hour_gates:
            continue
        if g.kind == DOOR:  # held while two are here and nobody is inside
            alone = f"{duo}{_is('in', 0)} "
            plate = fittings.plate_held(at(DOOR_PLATE))
            held += [
                _set("g", 1),
                f"execute {alone}run {_set('g', 0)}",
                f"execute {alone}{plate} run {_set('g', 1)}",
            ]
        elif g.kind == FK:  # held while nobody is beyond it; else Green
            alone = f"{duo}{_is('beyond', '..0')} "
            plate = fittings.plate_held(at(FK_PLATE))
            held += [
                _set("g", 0),
                f"execute {_is('hour', GREEN)} run {_set('g', 1)}",
                f"execute {alone}run {_set('g', 0)}",
                f"execute {alone}{plate} run {_set('g', 1)}",
            ]
        elif g.kind == LIFT:
            # open while its platform stands at the bottom (through Gold),
            # and for anyone found inside
            lift = next(x for x in LIFT_LIST if x.low in sides(g.deck, g.door))
            f, r = lift.mid
            a, b = (f - 1, r - 1, lift.bottom + 1), (f + 1, r + 1, lift.bottom + 2)
            down = f"if score {lift.score} matches 0 {_is(f'l{lift.name}.m', 0)}"
            held += [
                _set("g", 0),
                f"execute {down} run {_set('g', 1)}",
                f"execute if {_someone(at(a), at(b))} run {_set('g', 1)}",
            ]
        else:  # the Ram Door and the Great Door: shut until the room is solved
            held.append(_set("g", 0))
        held += [
            lines[g]["open"](_is("g", 1) + " "),
            lines[g]["shut"](_is("g", 0) + " "),
            lines[g]["lamp"](True, _is("g", 1) + " "),
            lines[g]["lamp"](False, _is("g", 0) + " "),
        ]
    pack.function(f"{base}/held", held)

    # -- the timed floors
    def floor_box(fl: Floor, block: str) -> str:
        cells = [at(p) for p in floor_places(fl)]
        return dp.fill(min(cells), max(cells), block)

    pack.function(
        f"{base}/hint",
        [
            _set("hinted", 1),
            say("The grating only stays for its hours. Climb back up.", "gray"),
        ],
    )
    for fl in FLOORS:
        cells = [at(p) for p in floor_places(fl)]
        lo, (x, y, z) = min(cells), max(cells)
        column = dp.box_selector(lo, (x, y + 3, z))
        pack.function(
            f"{base}/floor/{fl.name}/out",
            [floor_box(fl, GRATE), sound("block.iron_trapdoor.close", 1, 0.7)],
        )
        pack.function(
            f"{base}/floor/{fl.name}/drop",
            [
                # those on it drift down a deck, unhurt
                f"effect give @a[tag=st.in,{column}] minecraft:slow_falling 4 0 true",
                f"execute {_is('hinted', 0)} if entity @a[tag=st.in,{column}] "
                f"run function {fid('hint')}",
                floor_box(fl, AIR),
                sound("block.iron_trapdoor.open", 1, 0.7),
            ],
        )

    def gap(fl: Floor) -> str:
        """selector arguments for a floor's own level and just over it"""
        cells = [at(p) for p in floor_places(fl)]
        x, y, z = max(cells)
        return dp.box_selector(min(cells), (x, y + 2, z))

    for early in range(3):
        floors = []
        for fl in FLOORS:
            first = 4 * fl.start
            last = first + 8 - early - 1
            spans = [(first, min(last, 11))] + ([(0, last - 12)] if last > 11 else [])
            is_out = f"block {_xyz(at(floor_places(fl)[4]))} {GRATE} "
            for a, b in spans:
                floors.append(
                    f"execute {_is('q', f'{a}..{b}')} unless {is_out}"
                    f"run function {fid(f'floor/{fl.name}/out')}"
                )
            # its own warning in its last quarter out: a thud and sparks
            # every half second, for those on it (the bell's ticks are the
            # whole dome's, and at levels 7 to 10 it goes before them)
            warn = f"execute {_is('q', last % 12)} {_is('w', 0)} if {is_out}run "
            centre = middle(at(floor_places(fl)[4]), 1)
            floors += [
                f"{warn}playsound minecraft:block.note_block.bass block "
                f"@a[tag=st.in,{gap(fl)}] {centre} 1 0.6",
                f"{warn}particle minecraft:electric_spark {centre} 1 0 1 0 8",
            ]
            away = "".join(
                f"unless score {_s('q')} matches {a}..{b} " for a, b in spans
            )
            floors.append(
                f"execute {away}if {is_out}run function {fid(f'floor/{fl.name}/drop')}"
            )
            # whoever steps into the gap drifts down too
            floors.append(
                f"execute unless {is_out}run effect give @a[tag=st.in,{gap(fl)}] "
                "minecraft:slow_falling 2 0 true"
            )
        pack.function(f"{base}/floors/e{early}", floors)
    all_out = [floor_box(fl, GRATE) for fl in FLOORS]
    pack.function(
        f"{base}/floors",
        [
            *(call(f"floors/e{e}", f"{not_free}{_is('early', e)} ") for e in range(3)),
            *(
                f"execute {free}unless block {_xyz(at(floor_places(fl)[4]))} {GRATE} "
                f"run {floor_box(fl, GRATE)}"
                for fl in FLOORS
            ),
        ],
    )

    # -- the lifts. At rest a platform is blocks. To travel it becomes
    # block displays that glide a quarter of a block a tick (the dock
    # lift's way), everyone on it seated on an item display that moves
    # with them; at the other end it is blocks again and they stand up.
    # Each block of the way the shaft under it is written (the ram), the
    # way to go is read again, and a platform going down waits while
    # anyone is under it
    seats = f"@e[type=minecraft:item_display,tag={SEAT_TAG}"
    for lift in LIFT_LIST:
        path = f"{base}/lift/{lift.name}"
        f, r = lift.mid
        top = lift.travel
        n = lift.name
        to, m, p, d, wait = (f"l{n}.to", f"l{n}.m", f"l{n}.p", f"l{n}.d", f"l{n}.w")
        car = f"@e[tag={lift.car}]"
        on = f"st.maze.on.{n}"
        seat = f"{seats},tag={lift.car}"

        def lcall(name: str, when: str = "", path=path) -> str:
            line = f"function {pack.id(f'{path}/{name}')}"
            return f"execute {when}run {line}" if when else line

        def above(k: int, lift=lift, f=f, r=r) -> str:
            """those standing on the platform k blocks up"""
            return "@e[tag=st.in," + dp.box_selector(
                at((f - 1, r - 1, lift.bottom + k + 1)),
                at((f + 1, r + 1, lift.bottom + k + 2)),
            ) + "]"  # fmt: skip

        for k in range(top + 1):
            state = {at(q): block for q, block in lift_places(lift, k, True).items()}
            pack.function(f"{path}/air_{k}", _fills(state))
        for k in (0, top):
            state = {at(q): block for q, block in lift_places(lift, k).items()}
            pack.function(f"{path}/at_{k}", _fills(state))
            y = dome.floor_y + lift.bottom + k
            cells = [at((f + df, r + dr, lift.bottom + k)) for df in (-1, 0, 1) for dr in (-1, 0, 1)]  # fmt: skip
            # leaving an end: the platform's blocks become what travels,
            # and everyone on it gets a seat where they stand
            pack.function(
                f"{path}/leave_{k}",
                [
                    lcall(f"air_{k}"),
                    *(
                        f"summon minecraft:block_display {x}.0 {y}.0 {z}.0 "
                        f'{{Tags:["{CAR_TAG}","{lift.car}"],teleport_duration:1,'
                        f"block_state:{fittings.block_state(COPPER)}}}"
                        for x, _, z in sorted(cells)
                    ),
                    f"execute as {above(k)} at @s positioned ~ {y + 1.1} ~ "
                    f"run function {pack.id(f'{path}/seat')}",
                    _set(m, 1),
                    _set(p, 0),
                    sound("block.piston.extend", 1, 0.6),
                ],
            )
            # arriving: blocks again, the riders stood where they sat
            pack.function(
                f"{path}/arrive_{k}",
                [
                    lcall(f"at_{k}"),
                    f"execute as {seat}] at @s positioned ~ {y + 1} ~ on passengers "
                    f"run function {pack.id(f'{path}/off')}",
                    f"kill {car}",
                    f"tag @e[tag={on}] remove {on}",
                    _set(m, 0),
                    sound("block.piston.contract", 1, 0.6),
                ],
            )
        pack.function(
            f"{path}/seat",
            [
                "summon minecraft:item_display ~ ~ ~ "
                f'{{Tags:["{CAR_TAG}","{lift.car}","{SEAT_TAG}","st.maze.new"],'
                "teleport_duration:1}",
                f"ride @s mount {seats},tag=st.maze.new,limit=1,sort=nearest]",
                "tag @e[tag=st.maze.new] remove st.maze.new",
                f"tag @s add {on}",
            ],
        )
        pack.function(
            f"{path}/off", ["ride @s dismount", "tp @s ~ ~ ~", f"tag @s remove {on}"]
        )
        # the way to go, read once a block; going down it waits while
        # anyone is under it
        pack.function(
            f"{path}/aim",
            [
                _set(d, -1),
                f"execute {_is(to, 1)} run {_set(d, 1)}",
                _set(wait, 0),
                *(
                    f"execute {_is(d, -1)} if score {lift.score} matches {k} "
                    f"if {_someone(at((f - 1, r - 1, lift.bottom + 1)), at((f + 1, r + 1, lift.bottom + k - 1)))} "
                    f"run {_set(wait, 1)}"
                    for k in range(2, top + 1)
                ),
            ],
        )
        pack.function(
            f"{path}/glide",
            [
                lcall("aim", _is(p, 0) + " "),
                f"execute {_is(wait, 1)} run return 0",
                f"execute {_is(d, 1)} as {car} at @s run tp @s ~ ~{1 / LIFT_STEP} ~",
                f"execute {_is(d, -1)} as {car} at @s run tp @s ~ ~-{1 / LIFT_STEP} ~",
                # one who has got off their seat is put back on it
                f"execute as @a[tag={on}] at @s run ride @s mount {seat},limit=1,sort=nearest]",
                f"scoreboard players add {_s(p)} 1",
                lcall("landed", _is(p, f"{LIFT_STEP}..") + " "),
            ],
        )
        pack.function(
            f"{path}/landed",
            [
                _set(p, 0),
                f"scoreboard players operation {lift.score} += {_s(d)}",
                *(
                    f"execute if score {lift.score} matches {k} "
                    f"run function {pack.id(f'{path}/air_{k}')}"
                    for k in range(1, top)
                ),
                f"execute if score {lift.score} matches 0 {_is(to, 0)} "
                f"run function {pack.id(f'{path}/arrive_0')}",
                f"execute if score {lift.score} matches {top} {_is(to, 1)} "
                f"run function {pack.id(f'{path}/arrive_{top}')}",
            ],
        )
        under = _someone(
            at((f - 1, r - 1, lift.bottom + 1)), at((f + 1, r + 1, lift.top - 1))
        )
        pack.function(
            f"{path}/move",
            [
                f"execute {_is(m, 0)} {_is(to, 1)} if score {lift.score} matches 0 "
                f"run function {pack.id(f'{path}/leave_0')}",
                f"execute {_is(m, 0)} {_is(to, 0)} if score {lift.score} matches {top} "
                f"unless {under} run function {pack.id(f'{path}/leave_{top}')}",
                lcall("glide", _is(m, 1) + " "),
            ],
        )
        stop = [f"kill {car}", f"tag @e[tag={on}] remove {on}", _set(m, 0), _set(p, 0)]
        pack.function(
            f"{path}/park",
            [
                *stop,
                lcall(f"at_{top}"),
                f"scoreboard players set {lift.score} {top}",
                _set(to, 1),
            ],
        )
        pack.function(  # written whole at the end it was going to
            f"{path}/settle",
            [
                *stop,
                lcall("at_0", _is(to, 0) + " "),
                f"execute {_is(to, 0)} run scoreboard players set {lift.score} 0",
                f"execute unless score {_s(to)} matches 0 "
                f"run function {pack.id(f'{path}/park')}",
            ],
        )
    pack.function(
        f"{base}/lifts",
        [
            f"execute {_is('ramwait', '1..')} "
            f"run scoreboard players remove {_s('ramwait')} 1",
            f"execute {free}{_is('ramwait', 0)} run {_set('lram.to', 0)}",
            f"execute {free}{_is('ramwait', 0)} run {_set('ramwait', -1)}",
            *(call(f"lift/{lift.name}/move") for lift in LIFT_LIST),
        ],
    )

    # -- the Regulator: a lever, or two keys while two are up top
    post = at((LEVER_POST[0] + 1, LEVER_POST[1], LEVER_POST[2] + 1))
    keys = [at(p) for p in KEY_PLATES]
    plates = [at(DOOR_PLATE), at(FK_PLATE)]
    # the gold under a plate is there only while the plate is
    plain = plate_bases(dome)
    gold = plate_bases(dome, 2, True)

    def bases(cells: list[Cell], block: dict[Cell, str]) -> list[str]:
        return [
            f"execute unless block {_xyz(c)} {block[c]} run {_setblock(c, block[c])}"
            for c in ((x, y - 1, z) for x, y, z in cells)
        ]

    pack.function(
        f"{base}/keys/on",
        [
            _setblock(post, AIR),
            *bases(keys, gold),
            *(_setblock(c, PLATE) for c in keys),
            _set("keys", 1),
            _set("hold", 0),
            say("Two of you up here: the Regulator wants two keys. Stand on both."),
        ],
    )
    pack.function(
        f"{base}/keys/off",
        [
            *(_setblock(c, AIR) for c in keys),
            *bases(keys, plain),
            *fittings.lever_put_lines(post, lever(fr)),
            _set("keys", 0),
            _set("hold", 0),
        ],
    )
    both = " ".join(fittings.plate_held(c) for c in keys)
    pack.function(
        f"{base}/keys/held",
        [
            _set("ok", 0),
            f"execute {both} run {_set('ok', 1)}",
            f"execute {_is('ok', 0)} run {_set('hold', 0)}",
            f"execute {_is('ok', 1)} run scoreboard players add {_s('hold')} 1",
            call("done", _is("hold", f"{KEY_TICKS}..") + " "),
        ],
    )
    pack.function(
        f"{base}/keys",
        [
            _set("want", 0),
            f"execute {duo}{_is('top', '2..')} run {_set('want', 1)}",
            # (a change waits for hands off the keys: nobody is mid-press)
            call("keys/on", f"{_is('want', 1)} unless score {_s('keys')} matches 1 "),
            call("keys/off", f"{_is('want', 0)} unless score {_s('keys')} matches 0 "),
            f"execute {_is('keys', 0)} if block {_xyz(post)} "
            f"minecraft:lever[powered=true] run function {fid('done')}",
            call("keys/held", _is("keys", 1) + " "),
        ],
    )
    pack.function(
        f"{base}/done",
        [
            f"function {pack.id(f'dome/{INDEX}/solved')}",
            sound("block.bell.use", 3, 0.5),
            call("tame"),
            _set("ramwait", RAM_WAIT),
        ],
    )
    # the solved room left steady: every gate open, every floor out, the
    # lever shown thrown, the plates gone, the clock at its slowest
    pack.function(
        f"{base}/tame",
        [
            _set("free", 1),
            call("gates/free"),
            call("lamps/free"),
            *all_out,
            *(_setblock(c, AIR) for c in (*keys, *plates)),
            *bases([*keys, *plates], plain),
            _setblock(post, lever(fr, True)),
            _set("keys", 0),
            _set("hold", 0),
            _set("qlen", scaled(game.LEVELS[0])["qlen"]),
        ],
    )

    # -- the hooks
    lectern = at(LECTERN)
    pack.function(f"{base}/book", [_setblock(lectern, logbook(fr))])
    pack.function(
        f"{base}/work",
        [
            call("clock"),
            call("gates"),
            call("mend"),
            call("floors"),
            call("lifts"),
            call("keys", not_free),
            fittings.lever_hold_line(post, lever(fr, True), free.strip()),
        ],
    )
    pack.function(
        f"{base}/tick",
        [
            f"execute if block {_xyz(lectern)} minecraft:lectern[has_book=false] "
            f"run function {fid('book')}",
            f"execute unless score {open_dome} matches 1.. run return 0",
            # a room never set up has no clock
            f"execute if score {open_dome} matches 1 "
            f"unless score {_s('live')} matches 1 run function {fid('arm')}",
            f"execute if score {open_dome} matches 2 {not_free}run function {fid('tame')}",
            call("work"),
        ],
    )
    pack.function(
        f"{base}/enter",
        [
            # the core's signal: the first into an empty room
            # (not over a player who logged back in inside the room)
            f"execute if score {open_dome} matches 1 "
            f"if score #first {OBJ} matches 1 "
            f"unless score {_s('live')} matches 1 run function {fid('arm')}",
            f"execute if score {open_dome} matches 1 run tellraw @s "
            '{text:"A bell strikes. All over the tower, gates slide.",'
            'color:"gray",italic:true}',
        ],
    )
    pack.function(
        f"{base}/arm",
        [
            call("reset"),
            _set("live", 1),
            call("strike/0"),
            call("hand/go"),
            # set up from the tick, not on entry: the form is known
            f"execute if score #form{INDEX} {OBJ} matches 2 run function {fid('duo')}",
        ],
    )

    def signs(form: int) -> list[str]:
        return [
            f"data merge block {_xyz(at(SIGN_AT[kind]))} "
            f"{{{fittings.sign_text(HELD_SIGNS[kind][form - 1])}}}"
            for kind in (DOOR, FK)
        ]

    pack.function(
        f"{base}/solo",
        [
            _set("form", 1),
            *(_setblock(c, AIR) for c in plates),
            *bases(plates, plain),
            *signs(1),
        ],
    )
    pack.function(
        f"{base}/duo",
        [
            _set("form", 2),
            *bases(plates, gold),
            *(
                f"execute unless block {_xyz(c)} {PLATE} run {_setblock(c, PLATE)}"
                for c in plates
            ),
            *signs(2),
            say("Two in the tower: a HELD gate wants one of you on its plate."),
        ],
    )
    # the clock stopped at the strike of Green, every slot cleared (the
    # mend does the rest), the floors as in Green, the lifts at the top
    parked = {
        at(p): GRATE if fl.out(GREEN) else AIR
        for fl in FLOORS
        for p in floor_places(fl)
    }
    pack.function(
        f"{base}/park",
        [
            *(_set(name, 0) for name in ("t", "q", "hour", "last", "swing")),
            *(_set(name, 0) for name in ("fl", "bells", "bellt")),
            call("lights/0"),
            call("hand/put"),
            call("gates/free"),
            call("lamps/free"),
            *_fills(parked),
            *(call(f"lift/{lift.name}/park") for lift in LIFT_LIST),
            call("dial"),
            call("atrium/0"),
            f"schedule function {fid('mend_a')} 4t",
            f"schedule function {fid('mend_b')} 12t",
        ],
    )
    pack.function(
        f"{base}/empty",
        [
            *(call(f"lift/{x.name}/settle") for x in LIFT_LIST),
            f"execute if score {open_dome} matches 1 run function {fid('park')}",
            _set("live", 0),
        ],
    )
    zeroed = ("free", "live", "keys", "hold", "hinted", "ramwait", "g", "want", "ok")
    pack.function(
        f"{base}/reset",
        [
            call("park"),
            *(_set(name, 0) for name in zeroed),
            _set("form", 1),
            *(_setblock(c, AIR) for c in (*keys, *plates)),
            *bases([*keys, *plates], plain),
            *fittings.lever_put_lines(post, lever(fr)),
            *signs(1),
            call("book"),
            call("scale"),
            f"kill @e[type=minecraft:item,{domes.sphere(dome)}]",
        ],
    )


# --------------------------------------------------------------- the check

S1, S2 = "st.m1", "st.m2"


def shut_alone(g: Gate, hour: int) -> bool:
    """whether a gate is shut in an hour of the unsolved room, solo, with
    nobody in a lift"""
    if g.kind in (RAM, GREAT):
        return True
    if g.kind == DOOR:
        return False
    return not opens(g.kind, hour)


def check(ctx: Any) -> list[str]:
    """
    Work the Clockwork Maze in place over RCON. A player is stood in for
    by an armour stand that the core counts (``game.STANDIN``), with a
    body and a weight, moved by teleport; the lever is thrown by setting
    the block as a hand would leave it. Leaves the room and its tunnel
    reset, the dome as it was and no stand-in behind.

    What the stand-ins cannot prove: that a player can walk a gate in the
    time an hour gives, read a plan, or see and tell the colours; the
    ``slow_falling`` given as a floor goes (an armour stand takes no
    effect: it simply falls); a gate's leaves against a real body; the
    bell, the ticks, the titles and the chat lines (all aimed at
    players); a hand on the lever, the recall button or the log; the
    pendulum's swing and the hand's sweep (their data is read back, not
    seen); how a lift's ride feels and whether a player stays on a seat.

    It refuses while a run is in progress (``game_checks.no_run``); the
    level is put back (``save_level``) and the stand-ins killed whatever
    happens.
    """
    game_checks.no_run(ctx)
    saved_level = game_checks.save_level(ctx)
    try:
        return _check(ctx, saved_level)
    finally:
        ctx.cmd(f"kill @e[tag={S1}]")
        ctx.cmd(f"kill @e[tag={S2}]")
        game_checks.restore_level(ctx, saved_level)
        ctx.function("difficulty/apply")


def _check(ctx: Any, saved_level: dict[str, int | None]) -> list[str]:
    dome = ctx.layout.DOMES[INDEX]
    tunnel = ctx.layout.TUNNELS[INDEX]
    fr = frame(dome)
    problems: list[str] = []
    scan = game_checks.SCAN
    base = f"dome/{INDEX}"
    post = fr.at(LEVER_POST[0] + 1, LEVER_POST[1], LEVER_POST[2] + 1)
    keys = [fr.at(*p) for p in KEY_PLATES]
    part = {
        g: {k: [fr.at(*p) for p in v] for k, v in gate_places(g).items()} for g in GATES
    }
    by_kind = {g.kind: g for g in GATES if g.kind in (DOOR, FK)}

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def get(name: str) -> int:
        return ctx.score(f"#maze.{name}") or 0

    def spot(node: Node) -> str:
        """where a stand-in is put in a cell (beside a lift's ram)"""
        if node == "out":
            return middle(domes.entrance(dome)[:3])
        if node == "crown":
            return middle(fr.at(-2, 2, CROWN_H))
        f, r, h = cell_mid(node)
        low = node in {lift.low for lift in LIFT_LIST}
        return middle(fr.at(f - 1 if low else f, r, h))

    def hand_at() -> tuple[float, float] | None:
        """the hand's turn read back: (sine, cosine) of half its angle"""
        got = ctx.data(
            f"entity @e[tag={HAND_TAG},limit=1] transformation.left_rotation"
        )
        found = [float(n) for n in re.findall(r"-?\d+\.?\d*(?:[eE]-?\d+)?", got)][-4:]
        if len(found) != 4:
            return None
        x, _, z, w = found
        return x * fr.forward[0] + z * fr.forward[1], w

    def hand_reads(what: str, q: int) -> None:
        want = hand_turn(q)
        got = hand_at()
        flipped = (-want[0], -want[1])  # the same turn
        if got is None or min(math.dist(got, want), math.dist(got, flipped)) > 0.02:
            problems.append(f"{what}: the hand reads {got}, not {want} (lamp {q})")

    def light_is(hour: int) -> bool:
        """a post's light on each deck is the hour's"""
        return all(
            ctx.is_block(fr.at(-6, -6, walk_h(deck) + 3), HOUR_LIGHT[hour])
            for deck in (1, 2, 3)
        )

    outside = middle(tunnels.at(ctx.layout.TUNNELS[INDEX - 1], 8, 0, 1))

    def stand(tag: str, where: str) -> None:
        game_checks.stand_at(ctx, tag, where, gravity=True)

    def come_in(tag: str = S1) -> None:
        """a stand-in out of the dome and in again: a new entry"""
        stand(tag, outside)
        ctx.advance(game_checks.EMPTY)
        stand(tag, spot("out"))

    def is_shut(g: Gate) -> tuple[bool, bool, bool]:
        """a gate read: its slot full, its pistons out, its doorway shut"""
        p = part[g]
        return (
            ctx.is_block(p["slot"][0], POWER),
            ctx.is_block(p["piston"][0], f"{PISTON}[extended=true]"),
            ctx.is_block(p["door"][0], LEAF) and ctx.is_block(p["door"][1], LEAF),
        )

    def whole(g: Gate) -> bool:
        """an open gate at rest: both leaves parked, the doorway clear"""
        p = part[g]
        return all(ctx.is_block(c, LEAF) for c in p["leaf"]) and all(
            ctx.is_block(c, AIR) for c in p["door"]
        )

    def gates_read(what: str, want) -> None:
        wrong = []
        for g in GATES:
            shut = want(g)
            if is_shut(g) != (shut, shut, shut) or (not shut and not whole(g)):
                wrong.append(g.name)
        if wrong:
            problems.append(f"{what}: {len(wrong)} gates not as the table: {wrong[:4]}")

    def wait_hour(hour: int) -> bool:
        """wait for the next strike of an hour, and for the pistons"""
        limit = 14 * max(get("qlen"), 1)
        for _ in range(limit):
            if get("hour") == hour and get("q") % 4 == 0 and get("t") <= 6:
                ctx.advance(8)
                return True
            ctx.advance(2)
        problems.append(f"the clock never struck {HOURS[hour]}")
        return False

    def inside(tag: str, node: Node) -> bool:
        f, r, h = cell_mid(node)
        box = dp.box_selector(fr.at(f - 1, r - 1, h), fr.at(f + 1, r + 1, h + 2))
        return ctx.count(f"@e[tag={tag},{box}]") == 1

    def as_built(what: str) -> None:
        """every block of the room is as ``reset`` leaves it (a block of
        the Tally Engine: the same block, in whatever state)"""
        b = room_blocks(dome)
        wrong = [
            cell
            for cell, block in b.everything().items()
            if not ctx.is_block(
                cell, rooms.name(block) if cell in b.moving else block.partition("{")[0]
            )
        ]
        wrong += [cell for cell in b.clear if not ctx.is_block(cell, AIR)]
        if wrong:
            problems.append(f"{what}: {len(wrong)} blocks not as built: {wrong[:6]}")
        names = ("free", "live", "keys", "q", "hour", "t")
        expect(
            f"{what}: the scores", {n: get(n) for n in names}, dict.fromkeys(names, 0)
        )
        expect(f"{what}: the dial's hand", ctx.count(f"@e[tag={HAND_TAG}]"), 1)
        hand_reads(what, 0)
        expect(f"{what}: a lift on its way", ctx.count(f"@e[tag={CAR_TAG}]"), 0)

    def tally_counts(what: str) -> None:
        """the Tally Engine, which nothing starts or stops: three or more
        patterns of its six lamps in 12 s. (Not proved in a rig: if this
        fails the engine is decoration that does not count, no more)"""
        _, lamps = tally(fr)
        seen = set()
        for _ in range(60):
            ctx.advance(4)
            seen.add(tuple(ctx.is_block(c, f"{BULB}[lit=true]") for c in lamps))
        if len(seen) < 3:
            problems.append(f"{what}: the Tally Engine showed {len(seen)} patterns")

    def solved() -> bool:
        return ctx.score(f"#d{INDEX}") == 2

    def unsolve() -> None:
        """the room and its tunnel put back, the dome open and unsolved"""
        ctx.function(f"tunnel/{INDEX}/reset")
        ctx.function(f"{base}/reset")
        ctx.set_score(f"#d{INDEX}", 1)
        ctx.set_score(f"#d{(INDEX + 1) % 8}", saved[f"#d{(INDEX + 1) % 8}"] or 0)
        ctx.set_score("#solved", saved["#solved"] or 0)
        ctx.advance(16)  # the two mends that follow a reset

    # ---- before: nobody about, the room and its tunnel reset, the dome open
    names = (f"#d{INDEX}", f"#d{(INDEX + 1) % 8}", "#solved")
    saved = game_checks.scores(ctx, *names)
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan)
    if (others := ctx.score("#players")) or ctx.score(f"#form{INDEX}"):
        return [f"{others} players or stand-ins of another check are in the game"]
    unsolve()
    as_built("built")
    tally_counts("nobody in")
    for kind in ("text_display", "block_display"):
        want = sum(c.startswith(f"summon minecraft:{kind} ") for c in summons(dome))
        want += kind == "block_display"  # the hand, which the pack summons
        shows = ctx.count(f"@e[type=minecraft:{kind},tag={ENTITY_TAG}]")
        expect(f"the room's {kind}s", shows, want)
    for tag in PEND_TAGS:
        expect(f"the pendulum's {tag}", ctx.count(f"@e[tag={tag}]"), 1)
    recall = f"@e[type=minecraft:interaction,tag={ENTITY_TAG}]"
    expect("the recall button's interaction entity", ctx.count(recall), 1)
    if "Finch" not in ctx.data(f"block {_xyz(fr.at(*LECTERN))} Book"):
        problems.append("the logbook is not on the lectern")

    # ---- solo: in, the level's values, the clock from the strike of Green
    stand(S1, spot("out"))
    level = ctx.score("#active") or game.DEFAULT_LEVEL
    got = {n: get(n) for n in ("live", "form", *scaled(level))}
    expect("solo, entered", got, {"live": 1, "form": 1, **scaled(level)})
    lamps, _ = dial_places()
    for turn_ in range(2):  # two full turns: every gate at every hour
        for hour in range(3):
            if not wait_hour(hour):
                break
            hand_reads(f"turn {turn_}, {HOURS[hour]}", 4 * hour + 1)
            expect(f"the post lights in {HOURS[hour]}", light_is(hour), True)
            lit = [ctx.is_block(fr.at(*p), f"{BULB}[lit=true]") for p in lamps]
            want = [n == 4 * hour for n in range(12)]
            expect(f"the dial at the strike of {HOURS[hour]}", lit, want)
            bulbs = [
                ctx.is_block(fr.at(*p), f"{BULB}[lit=true]") == (h == hour)
                for h, p in atrium_lamps()
            ]
            expect(f"the atrium's lamps in {HOURS[hour]}", all(bulbs), True)
            # (a lift's gate opens when its platform has come down)
            ctx.advance(LIFT_STEP * (LIFT_LIST[0].travel + 4))
            gates_read(
                f"turn {turn_}, {HOURS[hour]}", lambda g, h=hour: shut_alone(g, h)
            )
    # the warning: in an hour's last quarter the post lights go to the
    # colour of the hour to come and back, every half second
    wait_hour(GREEN)
    ctx.advance(3 * get("qlen"))
    seen = set()
    for _ in range(max(get("qlen") // 2, 10)):
        ctx.advance(2)
        seen |= {h for h in range(3) if light_is(h)}
    expect("the lights in Green's last quarter", seen, {GREEN, IRON})
    # the hand made anew if it is gone
    ctx.cmd(f"kill @e[tag={HAND_TAG}]")
    ctx.advance(get("qlen") + 2)
    expect("the hand, killed, a quarter on", ctx.count(f"@e[tag={HAND_TAG}]"), 1)
    q0 = get("q")
    ctx.advance(get("qlen") * 3)
    expect("three quarters on", (get("q") - q0) % 12, 3)

    # ---- the interlock: a gate does not shut on a stand-in in its doorway
    g = next(g for g in GATES if (g.deck, g.kind) == (1, IRON))
    wait_hour(IRON)
    stand(S1, middle(part[g]["door"][0]))
    wait_hour(GOLD)
    expect("a gate with someone in its doorway, its hour over", is_shut(g)[0], False)
    stand(S1, spot((1, 0, 2)))
    ctx.advance(8)
    expect("that gate once the doorway is clear", is_shut(g), (True, True, True))

    # ---- the run, along the search's shortest route: walked by teleport
    # from cell to cell, each gate read open first, and ridden up each
    # lift from its lower cell. (It proves each doorway is clear in the
    # hour the table says and that the lifts carry a stand-in: not that a
    # player can walk it in the time)
    stand(S1, spot("out"))
    wait_hour(GOLD)
    here, riding = "out", None
    top_of = {lift.high: lift for lift in LIFT_LIST[:3]}
    for node, after in solo_route("out", GREEN):
        if not wait_hour((after - 1) % 3):
            break
        if riding:  # the strike of Green has taken it up
            ctx.advance(LIFT_STEP * (riding.travel + 2))
            name = riding.name
            expect(f"the run: up lift {name}", inside(S1, riding.high), True)
            expect(f"lift {name} at the top", get(f"l{name}"), riding.travel)
            here, riding = riding.high, None
        if node == here:
            continue
        lift = top_of.get(node)
        to = lift.low if lift and here not in room(node) else node
        if lift and to != node:  # in at Gold, once its platform is down
            ctx.advance(LIFT_STEP * (lift.travel + 4))
        ways = [
            gate
            for gate in GATES
            if to in sides(gate.deck, gate.door)
            and set(sides(gate.deck, gate.door)) & room(here)
        ]
        if to not in room(here) and not any(whole(gate) for gate in ways):
            problems.append(f"the run: no gate is open for {here} to {to}")
        stand(S1, spot(to))
        if to != "crown" and not inside(S1, to):
            problems.append(f"the run: the stand-in did not stay in {to}")
        here, riding = to, lift if to != node else None
    if riding:  # the last ride, to the crown
        wait_hour(GREEN)
        ctx.advance(LIFT_STEP * (riding.travel + 2))
        here = riding.high
        box = dp.box_selector(fr.at(-5, -2, CROWN_H), fr.at(6, 2, CROWN_H + 2))
        expect(
            "the run: lift C took the stand-in up", ctx.count(f"@e[tag={S1},{box}]"), 1
        )
    expect("the run ends on the crown", here, "crown")
    expect("alone on the crown: the lever, no keys", get("keys"), 0)
    # on the Ram, to be taken down once the room is solved
    stand(S1, middle(fr.at(-1, 0, CROWN_H)))
    ctx.setblock(post, lever(fr, True))
    ctx.advance(6)
    expect("the lever thrown: solved", (solved(), get("free")), (True, 1))
    problems.extend(game_checks.pull_pump(ctx, INDEX))
    expect("solved: its tunnel", ctx.score(f"#t{INDEX}") in (1, 2), True)
    ctx.advance(12)
    gates_read("solved", lambda g: False)
    out = [ctx.is_block(fr.at(*floor_places(fl)[4]), GRATE) for fl in FLOORS]
    expect("solved: every timed floor out", all(out), True)
    # the mend: a gate wrecked (its leaves in the doorway, none parked),
    # and a gate given a short pulse (a sticky piston drops its block),
    # each whole again within a few ticks, with nobody writing a piston
    g = GATES[1]
    for cell in part[g]["door"]:
        ctx.setblock(cell, LEAF)
    for cell in part[g]["leaf"]:
        ctx.setblock(cell, AIR)
    ctx.advance(5)
    expect("a wrecked gate, mended", whole(g), True)
    ctx.cmd(dp.fill(part[g]["slot"][0], part[g]["slot"][1], POWER))
    ctx.advance(12)
    expect("a gate given a short pulse, mended", whole(g), True)
    ctx.advance(RAM_WAIT + LIFT_STEP * (RAM_LIFT.travel + 2) + 10)
    expect("solved: the Ram gone down", (get("lram"), get("lram.m")), (0, 0))
    expect("its rider at the foot", inside(S1, RAM_LIFT.low), True)
    expect("its rider off the seat", ctx.count(f"@e[tag={SEAT_TAG}]"), 0)
    shutter = fr.at(-1, 0, RAM_LIFT.top)
    expect("the shutter over its hole", ctx.is_block(shutter, TRAPDOOR), True)
    stand(S1, spot((1, 3, 2)))  # off the Ram, which goes on with the clock
    ctx.setblock(post, lever(fr))
    ctx.advance(3)
    expect("the lever put back by hand", ctx.is_block(post, lever(fr, True)), True)
    come_in()  # a second entry into the solved room changes nothing
    ctx.advance(12)
    gates_read("solved, entered again", lambda g: False)

    # ---- a timed floor: still on T2 at the strike of Green, a deck down
    unsolve()
    come_in()
    t2 = FLOORS[0]
    wait_hour(IRON)
    stand(S1, spot(t2.node))
    expect("on T2 in Iron", inside(S1, t2.node), True)
    wait_hour(GREEN)
    ctx.advance(30)
    expect("after the strike of Green: in the cell below", inside(S1, t2.below), True)

    # ---- duo: the held gates, each only while it strands nobody
    door, fk = by_kind[DOOR], by_kind[FK]
    plates = [fr.at(*DOOR_PLATE), fr.at(*FK_PLATE)]
    stand(S1, spot("out"))
    stand(S2, spot("out"))
    ctx.advance(scan + 8)
    expect("two in: the forms", (ctx.score(f"#form{INDEX}"), get("form")), (2, 2))
    expect("duo: the plates", [ctx.is_block(c, PLATE) for c in plates], [True, True])
    expect("duo, both outside: the tower door", is_shut(door), (True, True, True))
    stand(S2, middle(plates[0]))
    ctx.advance(20)
    expect("the door's plate stood on", is_shut(door), (False, False, False))
    stand(S2, spot("out"))
    ctx.advance(40)
    expect("the door's plate left", is_shut(door)[0], True)
    ctx.cmd(
        f"summon minecraft:item {middle(plates[0], 0.2)} "
        '{Item:{id:"minecraft:stick",count:1},Tags:["st.m.item"]}'
    )
    ctx.advance(30)
    expect("an item on the door's plate", is_shut(door)[0], True)
    ctx.cmd("kill @e[tag=st.m.item]")
    stand(S1, spot((1, 0, 2)))  # one inside: the door stands open for the other
    ctx.advance(8)
    expect("one inside: the tower door", is_shut(door)[0], False)
    stand(S1, spot(F_CELL))
    stand(S2, spot(F_CELL))  # (not on the lift's top: it would ride)
    wait_hour(GREEN)  # held: shut even in its own hour until the plate is held
    expect("duo, nobody beyond: F to K in Green", is_shut(fk)[0], True)
    stand(S2, middle(plates[1]))
    ctx.advance(20)
    expect("its plate stood on", is_shut(fk)[0], False)
    stand(S1, spot((2, 2, 0)))  # one beyond: it follows the clock again
    stand(S2, spot(F_CELL))
    wait_hour(IRON)
    expect("one beyond: F to K in Iron", is_shut(fk)[0], True)
    wait_hour(GREEN)
    expect("one beyond: F to K in Green", is_shut(fk)[0], False)
    # the Regulator: the lever with one up top, two keys with two
    stand(S1, middle(keys[0]))
    ctx.advance(8)
    expect(
        "one up top: the lever", (get("keys"), ctx.is_block(post, lever(fr))), (0, True)
    )
    stand(S2, spot("crown"))
    ctx.advance(8)
    shape = (
        get("keys"),
        ctx.is_block(post, AIR),
        [ctx.is_block(c, PLATE) for c in keys],
    )
    expect("two up top: two keys, no lever", shape, (1, True, [True, True]))
    ctx.advance(60)
    expect("one key held for 3 s", solved(), False)
    stand(S2, middle(keys[1]))
    ctx.advance(KEY_TICKS + 30)
    expect("both keys held", solved(), True)

    # ---- duo, and one leaves: solo within the core's fall-back
    unsolve()
    come_in(S1)
    stand(S2, spot("out"))
    ctx.advance(scan)
    expect("two in again: the form", get("form"), 2)
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan + 8)
    expect("one left: the form", (ctx.score(f"#form{INDEX}"), get("form")), (1, 1))
    expect("one left: the plates", [ctx.is_block(c, AIR) for c in plates], [True, True])
    expect("one left: the tower door", is_shut(door)[0], False)
    expect("one left: the room not set up anew", get("live"), 1)

    # ---- difficulty: the values of the level, on a new entry
    for new in (game.LEVELS[0], game.LEVELS[-1]):
        ctx.set_score("#level", new)
        come_in()
        expect(
            f"level {new}: the values", {n: get(n) for n in scaled(new)}, scaled(new)
        )
    game_checks.restore_level(ctx, saved_level)
    ctx.function("difficulty/apply")

    # ---- a lift does not come down onto anybody, and its gate opens for
    # whoever is under it; then a ride up at the strike of Green, and down
    # again at Gold for one who stays on
    come_in()
    lift_a = LIFT_LIST[0]
    gate_a = next(g for g in GATES if (g.deck, g.kind) == (1, LIFT))
    wait_hour(IRON)
    stand(S1, spot(lift_a.low))
    ctx.advance(8)
    expect("under lift A in Iron: its gate", is_shut(gate_a)[0], False)
    wait_hour(GOLD)
    ctx.advance(LIFT_STEP * (lift_a.travel + 4))
    expect("lift A with someone under it: waiting", get("la") >= 3, True)
    stand(S1, spot((1, 4, 1)))
    ctx.advance(LIFT_STEP * (lift_a.travel + 4))
    expect("lift A, the bed clear: down", (get("la"), get("la.m")), (0, 0))
    stand(S1, spot(lift_a.low))
    wait_hour(GREEN)
    ctx.advance(LIFT_STEP * (lift_a.travel + 2))
    expect("lift A's rider after the strike of Green", inside(S1, lift_a.high), True)
    wait_hour(GOLD)
    ctx.advance(LIFT_STEP * (lift_a.travel + 2))
    expect("lift A's rider after the strike of Gold", inside(S1, lift_a.low), True)
    expect("nothing of lift A left in the air", ctx.count(f"@e[tag={CAR_TAG}]"), 0)

    # ---- everyone out of an unsolved room: parked
    stand(S1, outside)
    ctx.advance(game_checks.EMPTY + 20)
    as_built("emptied")

    # ---- reset, from a scrambled state, and of this dome only
    come_in()
    stand(S2, middle(plates[0]))
    ctx.advance(scan)
    ctx.advance(get("qlen") * 5 + 7)
    stand(S1, spot("crown"))  # two up top: the keys
    stand(S2, spot("crown"))
    ctx.advance(scan + 8)
    ctx.function(f"{base}/lift/a/air_3")
    ctx.function(f"{base}/floors/e2")
    ctx.setblock(fr.at(*LECTERN), f"minecraft:lectern[facing={fr.facing(-1, 0)}]")
    ctx.advance(3)
    if "Finch" not in ctx.data(f"block {_xyz(fr.at(*LECTERN))} Book"):
        problems.append("a logbook taken from the lectern was not put back")
    if not (get("q") and ctx.is_block(keys[0], PLATE) and get("form") == 2):
        problems.append("the room was not scrambled before the reset")
    rest = [f"#d{d.index}" for d in layout.DOMES if d.index != INDEX] + [
        f"#t{t.index}" for t in layout.TUNNELS
    ]
    before = game_checks.scores(ctx, *rest)
    ctx.function(f"{base}/reset")
    ctx.set_score(f"#d{INDEX}", 0)  # locked, so that nothing runs after it
    ctx.advance(16)
    as_built("reset from a scrambled state")
    expect(
        "the reset left the other domes alone", game_checks.scores(ctx, *rest), before
    )

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
    tally_counts("left")
    for tag in PEND_TAGS:
        expect(f"the pendulum's {tag}, left", ctx.count(f"@e[tag={tag}]"), 1)
    got, want = tunnels.counts(ctx, tunnel), tunnels.expected(tunnel, 0)
    expect("its tunnel left shut and flooded", got, want)
    problems += [f"left: {p}" for p in domes.check_shell(ctx, dome, False)]
    left = ctx.count(f"@e[tag={S1}]") + ctx.count(f"@e[tag={S2}]")
    expect("stand-ins left behind", left, 0)
    return problems


MODULE = game.Module(
    "maze",
    stages={f"dome_{INDEX}_inside": build},
    functions=functions,
    checks={"clockwork_maze": check},
)
