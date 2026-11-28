"""
The Cargo Hold of The Drowned Station: a steam lighter, the *Marigold*,
afloat in the dock's basin, her cargo piled anyhow, and over her a brass
gantry crane. Its build stage (``dome_<n>_inside``), its datapack
functions (``dome/<n>/...``) and its live check (``cargo_hold``).

**The one idea.** Stow her to the manifest on the chart table with the
crane, a crate at a time, never setting a crate on a lighter one and
never letting her list past the green on the list gauge: she is afloat,
and loaded unevenly she goes over. A sliding-block
puzzle whose blocks are lifted; and the deckhouse hides half the hold
from the crane's driver, so with a mate one drives and the other calls
the fore hold from the bow.

**Places** are in the dome's own frame (``fittings.frame``): f forward
from the entrance, r to the right (port is r < 0), h up from the floor.
The hold is two rows of four bays (``BAYS``: A1 to A4 aft of the
deckhouse at f -8 and -7, F1 to F4 fore of it at f 7 and 8), each a 2 x 2
square with an aisle all round; a crate is 2 x 2 x 2 and a bay holds three.
The deckhouse (f -4 to 4, solid to h 8) hides each hold's stacks from
the other end (a crate on the hook is seen over it). The pulpit (the crane's controls) is on her stern, the banksman's
stand on her bow; a railed gantry walk runs round at h 10. On the pulpit
the driver stands on a platform at its back, its front row level with
the deck (``DRIVER``, by the keys) and its back row half a block higher
(``DRIVER_BACK``), and looks forward and down: the keys at the feet, then a
glass deck and a glass screen, the aft hold through them, the list gauge
over it. Nobody gets into the aft hold (the screen is too high to climb
from the tables); whoever does all the same leaves by a ladder at its
starboard aft corner (``AFT_LADDER``), through a notch in her side and
over it into the basin.

**Afloat.** The basin (``basin``) is water one deep let into the dome's
floor all round her (two wide along her sides and at her bow, one at her
stern, before the entrance), on a bed laid under the floor; her bottom is
relaid in the floor and her boot-topping is at the waterline. The stairs
to the pulpit and the bow stand in it on piers, the mooring chains cross
it. Every cell beside it in the floor is solid, so it cannot run
(``afloat_problems``); the cells are registered as an opening of the
floor, which the shell's check then leaves to this module's. Whoever
falls in wades to an edge and steps out (the walks are level with its
brim), or goes up the landing steps (``LANDINGS``). No walk the room
asks for is through it (``reach`` keeps dry).

**The list gauge** (``gauge_summons``): a brass arch on each face of the
deckhouse with a needle on a pivot, block displays. The needle stands
upright when she is level and leans to the heavy side, a step a ton,
gliding (``trim/show``); the scale's marks are green to the band's limit
and red past it (``trim/band``). A refused set-down kicks the needle to
where she would have gone and lets it back (``trim/flash``); within a
ton of the limit her timbers creak (``trim/creak``). The pack's names
keep the older word, trim: on every sign, board and message it is her
list.

**The rules** (``Hold``): a crate is iron (3 tons), a barrel (2) or a
bale of wool or hay (1). Never on a lighter one, three high at most, and
the list (``trim``: starboard tons less port tons, a crate on the hook counted
where it came from) never past the band's limit. ``BANDS`` holds three
manifests for each band of two levels (a start and a plan, and the fewest
moves); one is drawn when the room is armed. ``manifest_problems`` runs
the searches: each solvable in its number of moves, no state a player can
make from the start that cannot still reach the plan (no soft lock), and
the player with no plan taking much longer.

**The crane** is block displays all the time, nobody rides it: the bridge
(``st.cargo.b``: everything) glides fore and aft between the holds, the
trolley (``st.cargo.t``) port and starboard between the four columns of
bays, the spreader and hook (``st.cargo.k``) up and down, a quarter of a
block a tick, by ``tp`` with ``teleport_duration:1`` (the lifts' way). The
chain is a display a block, added at the top of each block of a descent
and taken at the start of each block up; the drum turns a quarter a
block. A grabbed crate's blocks become displays that ride the hook (the
lifts' leave), and blocks again where it is set down (their arrive).

**The controls**: eight keys, stone buttons lying on brass let into the
pulpit's deck before the driver's platform, in the ship's own directions. To
the left hand a cross: PORT, FORE, STARBOARD in the far row and AFT under
FORE (travel: the hook goes up first); to the right a square: HOOK UP and
GRAB far, HOOK DOWN and RELEASE near. UNDO is a button on a post beside
the platform; RESET HOLD, a lever pulled twice in 5 s, in the back corner. A
set-down that breaks a rule is refused at HOOK DOWN, with its reason in
chat (``why``: 1 full, 2 crush, 3 trim, 4 shut, 5 stand clear, 6 not on a
crate); the hook never comes down into a bay with anyone in its column,
and waits over them. A crate may always go back where it came from.

**The two-player form** darkens the fore half of the hold table at the
pulpit, so the driver needs the banksman to know the fore hold; nothing
else changes and nothing waits for anybody.

**State**, all ``#cargo.<name>`` in ``st``: ``live`` (armed), ``form`` and
``want``; ``band`` (0 to 4), ``m`` (1 to 3), ``lim``, ``nlim`` (its
negative), ``shut`` (the jammed bay or -1); per bay ``b<i>.n`` and
``b<i>.t<k>`` (the kind at tier k), the plan ``g<i>.t<k>``; ``trim``;
the crane ``row`` and ``col`` (where it is), ``rowto`` and ``colto``
(where it is sent), ``bp``/``bd`` and ``tp``/``td`` (ticks into a glide
and its way), ``hy`` (the spreader's height), ``hyto``, ``hp``/``hd``,
``down`` (a DOWN waiting for travel to end), ``wait`` (waiting over
someone); ``load`` and ``from`` (the crate on the hook and its bay);
``why``; ``moves``, the undo ring ``h0`` to ``h29`` (``from * 8 + to``)
with ``hi`` and ``hn``; ``ask`` (ticks to pull RESET HOLD again), ``free``
(solved). ``force`` (1 to 3) draws that manifest: for the check only.

**Functions** (the core calls the hooks, see game.py): ``enter`` (the first
into a room not armed: ``arm``; every entry: ``crane/mend``), ``tick``
(the log put back, the inputs read, ``crane/step``, the form's safe
point), ``solo``/``duo`` (``want`` only), ``empty`` (a crate on the hook
back where it came from, the crane made anew where it is), ``reset``
(everything as built). Nothing is lent and nothing hurts: no ``leave`` or
``died``.
"""

from __future__ import annotations

import math
import random
import re
import statistics
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
from domes import AIR, Cell

if TYPE_CHECKING:
    from station_layout import Dome

INDEX = layout.index_of("cargo")  # the Cargo Hold's place in the ring
OBJ = game.OBJ

# ------------------------------------------------------------ the puzzle

#: the kinds of crate, by their number in the scores (0 is none)
IRON, BARREL, WOOL, HAY = 1, 2, 3, 4
KINDS = (IRON, BARREL, WOOL, HAY)
LETTER = {IRON: "I", BARREL: "B", WOOL: "W", HAY: "H"}
KIND_OF = {v: k for k, v in LETTER.items()}
WEIGHT = {IRON: 3, BARREL: 2, WOOL: 1, HAY: 1}
KIND_NAME = {IRON: "iron", BARREL: "barrel", WOOL: "wool", HAY: "hay"}
#: the bays: 0 to 3 the aft hold port to starboard, 4 to 7 the fore hold
BAYS = ("A1", "A2", "A3", "A4", "F1", "F2", "F3", "F4")
#: -1 a port bay, 1 a starboard bay
SIDE = (-1, -1, 1, 1, -1, -1, 1, 1)
TIERS = 3  # crates a bay holds, one on another

Stacks = tuple[tuple[int, ...], ...]  # a hold: each bay's kinds, bottom first


@dataclass(frozen=True)
class Band:
    """a band of two levels: its trim limit, the bay shut (or None) and
    its three manifests, each (start, plan, the fewest moves)"""

    levels: tuple[int, int]
    limit: int
    shut: int | None
    manifests: tuple[tuple[str, str, int], ...]


#: the manifests (the design's table, found by its search): bays A1 to A4
#: then F1 to F4, each bottom first, "." an empty bay
BANDS = (
    Band(
        (1, 2),
        5,
        None,
        (
            (".  .  .  IB | H  .  W  .", "I  .  .  B | .  W  H  .", 5),
            (".  .  H  .  | B  IW .  .", ".  IW B  . | .  .  H  .", 5),
            (".  .  B  .  | H  .  .  IW", "B  .  .  . | .  I  H  W", 5),
        ),
    ),
    Band(
        (3, 4),
        4,
        None,
        (
            (".  I  .  .  | .  .  BW IH", "I  B  .  I | .  .  W  H", 7),
            (".  .  .  B  | I  .  HW I", "IB .  .  I | .  .  WH .", 7),
            (".  .  B  .  | .  I  .  IHW", ".  I  I  . | B  .  .  WH", 7),
        ),
    ),
    Band(
        (5, 6),
        2,
        None,
        (
            ("B  .  .  BH | .  I  IW .", "IB .  .  IB | .  W  H  .", 9),
            (".  .  BW .  | .  IB IH .", ".  IW IH .  | .  B  B  .", 9),
            (".  .  BH .  | IB .  .  IW", ".  IB IB .  | W  .  .  H", 9),
        ),
    ),
    Band(
        (7, 8),
        2,
        None,
        (
            (".  .  .  BBW | .  IBH I  .", "IB .  .  IB | .  B  WH .", 11),
            (".  B  H  .  | IW .  .  IBB", ".  IB IB .  | WH .  .  B", 11),
            (".  IBW .  BH | .  .  IB .", "I  BB .  I  | .  .  BW H", 10),
        ),
    ),
    Band(
        (9, 10),
        2,
        4,
        (
            ("W  .  .  BBH | .  IB I  .", ".  IB .  IB | .  B  WH .", 12),
            ("H  .  BBW .  | .  IB .  I", ".  IB IB .  | .  WH .  B", 12),
            (".  IB .  BH  | .  W  IB .", "I  BB .  I  | .  .  BW H", 11),
        ),
    ),
)
#: the manifests' names, the same in every band
MANIFEST_NAMES = (
    "Pump castings for the Flooded Dome",
    "Stores and fodder",
    "Barrels of lamp oil",
)


def band_of(level: int) -> int:
    """the band (0 to 4) of a level (1 to 10)"""
    return (level - 1) // 2


def parse(text: str) -> Stacks:
    """a hold from its text: ``". . IB . | H . W ."``"""
    words = text.replace("|", " ").split()
    assert len(words) == len(BAYS), text
    return tuple(() if w == "." else tuple(KIND_OF[c] for c in w) for w in words)


def show(stacks: Stacks) -> str:
    def bay(s: tuple[int, ...]) -> str:
        return "".join(LETTER[k] for k in s) or "."

    return " ".join(map(bay, stacks[:4])) + " | " + " ".join(map(bay, stacks[4:]))


def trim(stacks: Stacks) -> int:
    """starboard tons less port tons"""
    return sum(SIDE[i] * WEIGHT[k] for i, s in enumerate(stacks) for k in s)


# A hold as one small integer for the searches: each bay a code of 7 bits
# (its kinds bottom first as base-5 digits), bay i at bits 7i
_B = 7
_MASK = (1 << _B) - 1


def _code(stack: tuple[int, ...]) -> int:
    return sum(k * 5**t for t, k in enumerate(stack))


def _stack(code: int) -> tuple[int, ...]:
    out = []
    while code:
        out.append(code % 5)
        code //= 5
    return tuple(out)


def encode(stacks: Stacks) -> int:
    return sum(_code(s) << (_B * i) for i, s in enumerate(stacks))


def decode(state: int) -> Stacks:
    return tuple(_stack((state >> (_B * i)) & _MASK) for i in range(len(BAYS)))


# for each bay code: its height, top kind, the code without its top, the
# code with each kind put on (None if it may not be: full, or a lighter top)
_CODES = [c for c in range(5**TIERS) if all(_stack(c))]
_HEIGHT = {c: len(_stack(c)) for c in _CODES}
_TOP = {c: (_stack(c)[-1] if c else 0) for c in _CODES}
_POP = {c: _code(_stack(c)[:-1]) for c in _CODES if c}
_PUSH = {
    c: {
        k: _code((*_stack(c), k))
        if _HEIGHT[c] < TIERS and (not c or WEIGHT[_TOP[c]] >= WEIGHT[k])
        else None
        for k in KINDS
    }
    for c in _CODES
}
_TONS = {c: sum(WEIGHT[k] for k in _stack(c)) for c in _CODES}


class Hold:
    """the rules of a band: a move takes the top crate of a bay and sets it
    on another, never on a full bay, a shut one or a lighter crate, and
    never so that the trim is past the limit"""

    def __init__(self, limit: int, shut: int | None = None):
        self.limit = limit
        self.open = [i for i in range(len(BAYS)) if i != shut]

    def trim(self, state: int) -> int:
        return sum(
            SIDE[i] * _TONS[(state >> (_B * i)) & _MASK] for i in range(len(BAYS))
        )

    def moves(self, state: int, tr: int):
        """(from, to, the state after, its trim) for each legal move"""
        codes = [(state >> (_B * i)) & _MASK for i in range(len(BAYS))]
        for a, ca in enumerate(codes):
            if not ca:
                continue
            k = _TOP[ca]
            w = WEIGHT[k]
            off = tr - SIDE[a] * w
            base = state + ((_POP[ca] - ca) << (_B * a))
            for b in self.open:
                if b == a:
                    continue
                cb = codes[b]
                nb = _PUSH[cb][k]
                if nb is None:
                    continue
                t = off + SIDE[b] * w
                if -self.limit <= t <= self.limit:
                    yield a, b, base + ((nb - cb) << (_B * b)), t

    def preds(self, state: int, tr: int):
        """(the state, its trim) one legal move before this one"""
        codes = [(state >> (_B * i)) & _MASK for i in range(len(BAYS))]
        for b, cb in enumerate(codes):
            if not cb:
                continue
            k = _TOP[cb]
            w = WEIGHT[k]
            off = tr - SIDE[b] * w
            base = state + ((_POP[cb] - cb) << (_B * b))
            for a in self.open:
                if a == b:
                    continue
                ca = codes[a]
                na = _PUSH[ca][k]
                if na is None:
                    continue
                t = off + SIDE[a] * w
                if -self.limit <= t <= self.limit:
                    yield base + ((na - ca) << (_B * a)), t

    def reach(self, start: int) -> set[int]:
        """every state a player can make from the start"""
        seen, edge = {start}, [(start, self.trim(start))]
        while edge:
            s, tr = edge.pop()
            for _, _, n, t in self.moves(s, tr):
                if n not in seen:
                    seen.add(n)
                    edge.append((n, t))
        return seen

    def able(self, goal: int) -> set[int]:
        """every legal state from which the goal can be reached"""
        seen, edge = {goal}, [(goal, self.trim(goal))]
        while edge:
            s, tr = edge.pop()
            for n, t in self.preds(s, tr):
                if n not in seen:
                    seen.add(n)
                    edge.append((n, t))
        return seen

    def route(self, start: int, goal: int) -> list[tuple[int, int]] | None:
        """the fewest moves (from, to) from the start to the goal"""
        prev: dict[int, Any] = {start: None}
        level = [(start, self.trim(start))]
        while level:
            nxt = []
            for s, tr in level:
                if s == goal:
                    path = []
                    while prev[s] is not None:
                        s, a, b = prev[s]
                        path.append((a, b))
                    return path[::-1]
                for a, b, n, t in self.moves(s, tr):
                    if n not in prev:
                        prev[n] = (s, a, b)
                        nxt.append((n, t))
            level = nxt
        return None

    def naive(self, start: int, goal: int, rng: random.Random, limit: int = 150) -> int:
        """the moves of the player with no plan: a crate straight to where
        the plan wants it whenever one can go, otherwise any move"""
        want = decode(goal)
        s, tr, n = start, self.trim(start), 0
        while s != goal and n < limit:
            have = decode(s)
            good, rest = [], []
            for a, b, t, ttr in self.moves(s, tr):
                after = decode(t)
                ok = (
                    after[b] == want[b][: len(after[b])]
                    and have[a] != want[a][: len(have[a])]
                )
                (good if ok else rest).append((t, ttr))
            s, tr = rng.choice(good or rest)
            n += 1
        return n


#: the tries of the player with no plan, and their seed
NAIVE_TRIES = 61
NAIVE_SEED = 3


@cache
def puzzle() -> dict[tuple[int, int], dict[str, Any]]:
    """
    Each manifest searched, by (band, manifest 0 to 2): ``best`` (the
    fewest moves) and ``route`` (one such, as (from, to) bays), ``states``
    (how many a player can make from the start), ``locks`` (of those, how
    many cannot reach the plan), ``naive`` (the median moves of the
    player with no plan, given up at 150) and ``trim`` at the start.
    """
    found = {}
    for b, band in enumerate(BANDS):
        hold = Hold(band.limit, band.shut)
        for m, (start_text, plan_text, _) in enumerate(band.manifests):
            start, goal = encode(parse(start_text)), encode(parse(plan_text))
            reached = hold.reach(start)
            able = hold.able(goal)
            route = hold.route(start, goal) or []
            rng = random.Random(NAIVE_SEED)
            tries = [hold.naive(start, goal, rng) for _ in range(NAIVE_TRIES)]
            found[b, m] = {
                "best": len(route),
                "route": route,
                "states": len(reached),
                "locks": len(reached - able),
                "naive": statistics.median(tries),
                "trim": hold.trim(start),
            }
    return found


def manifest_problems() -> list[str]:
    """the manifests against their rules and the searches: every start and
    plan legal and within the limit, the plan level from level 3 up, no
    bay already as planned, a start listing at or near the limit; each
    solvable in the moves the table says, with no soft lock; and the
    player with no plan at least two moves longer, and half as long
    again from level 3 up"""
    problems = []
    for b, band in enumerate(BANDS):
        for m, (start_text, plan_text, best) in enumerate(band.manifests):
            name = f"levels {band.levels[0]}-{band.levels[1]} manifest {m + 1}"
            start, plan = parse(start_text), parse(plan_text)
            for what, stacks in (("start", start), ("plan", plan)):
                if sorted(k for s in stacks for k in s) != sorted(
                    k for s in start for k in s
                ):
                    problems.append(f"{name}: its {what} has other crates")
                if any(len(s) > TIERS for s in stacks):
                    problems.append(f"{name}: its {what} has a bay over full")
                if any(
                    WEIGHT[s[t]] < WEIGHT[s[t + 1]]
                    for s in stacks
                    for t in range(len(s) - 1)
                ):
                    problems.append(f"{name}: its {what} has a crate on a lighter one")
                if abs(trim(stacks)) > band.limit:
                    problems.append(f"{name}: its {what} is past the trim limit")
                if band.shut is not None and stacks[band.shut]:
                    problems.append(f"{name}: its {what} has a crate in the shut bay")
            if band.levels[0] >= 3 and trim(plan):
                problems.append(f"{name}: the plan is not level")
            if any(s and s == p for s, p in zip(start, plan, strict=True)):
                problems.append(f"{name}: a bay is already as planned")
            if abs(trim(start)) < max(1, band.limit - 1):
                problems.append(f"{name}: she is not listing at the start")
            got = puzzle()[b, m]
            if got["best"] != best:
                problems.append(f"{name}: {got['best']} moves at best, not {best}")
            if got["locks"]:
                problems.append(
                    f"{name}: {got['locks']} states with no way to the plan"
                )
            if got["naive"] < best + 2:
                problems.append(f"{name}: no plan takes {got['naive']}, best {best}")
            if band.levels[0] >= 3 and got["naive"] < 1.5 * best:
                problems.append(f"{name}: no plan takes {got['naive']}, best {best}")
    return problems


# ---------------------------------------------------------------- the room

Place = tuple[int, int, int]  # f, r, h in the dome's frame

BRASS = "minecraft:gold_block"
BARS = "minecraft:iron_bars"
PANE = "minecraft:glass_pane"
BARRIER = "minecraft:barrier"  # a window with nothing in it, and still a wall
WATER = tunnels.WATER
GLASS = "minecraft:glass"
GRATE = "minecraft:waxed_copper_grate"
CUT = "minecraft:waxed_cut_copper"
CHISELED = "minecraft:waxed_chiseled_copper"
COPPER = "minecraft:waxed_copper_block"
KEEL = "minecraft:polished_blackstone_bricks"
BOOT = "minecraft:red_nether_bricks"  # her boot-topping
HULL = "minecraft:waxed_weathered_cut_copper"
DECK = "minecraft:spruce_planks"
HOUSE = "minecraft:dark_oak_planks"
HOLD_FLOOR = "minecraft:stripped_spruce_log[axis=y]"
DOCK_WALK = "minecraft:polished_andesite"
PILLAR = "minecraft:stripped_dark_oak_log[axis=y]"
SLAB = "minecraft:waxed_cut_copper_slab[type=bottom]"
PLATFORM = "minecraft:waxed_oxidized_cut_copper"
PLATFORM_SLAB = "minecraft:waxed_oxidized_cut_copper_slab[type=bottom]"
LANTERN = "minecraft:lantern[hanging=false]"
HANGING = "minecraft:lantern[hanging=true]"
BULB = "minecraft:waxed_copper_bulb"
GREEN = "minecraft:lime_concrete"
RED = "minecraft:red_concrete"
STAIRS = "minecraft:waxed_cut_copper_stairs"
CHAIN = "minecraft:iron_chain"
HATCH = "minecraft:spruce_trapdoor"
TABLE_TOP = CHISELED
#: each column's colour on the hold floor: red, yellow, green, blue
BAY_COLOUR = (
    "minecraft:red_concrete",
    "minecraft:yellow_concrete",
    "minecraft:green_concrete",
    "minecraft:blue_concrete",
)
#: the crates' blocks: a crate is eight of its kind's, and so is its model
CRATE = {
    IRON: "minecraft:iron_block",
    BARREL: "minecraft:barrel[facing=up]",
    WOOL: "minecraft:white_wool",
    HAY: "minecraft:hay_block[axis=y]",
}

ENTITY_TAG = "st.cargo"  # everything the build and the pack summon
CRANE_TAG = "st.cargo.crane"  # every part of the crane, links and crate too
B_TAG, T_TAG, K_TAG = "st.cargo.b", "st.cargo.t", "st.cargo.k"
PART_TAG = "st.cargo.part"  # the crane's fixed parts, counted by ``mend``
LINK_TAG = "st.cargo.link"
CRATE_TAG = "st.cargo.crate"  # a crate's displays while it rides the hook
SPREADER_TAG = "st.cargo.spreader"
DRUM_TAG = "st.cargo.drum"
BOARD_TAG = "st.cargo.board"
DOCKET_TAG = "st.cargo.docket"
DARK_TAG = "st.cargo.dark"
JAM_TAG = "st.cargo.jam"
NEEDLE_TAG = "st.cargo.needle"  # the list gauges' needles, one a face
ZONE_TAG = "st.cargo.zone"  # the marks of their scales (and ``st.cargo.z<j>``)

#: the hold: the two rows' cells along f, the four columns' along r
BAY_F = ((-8, -7), (7, 8))
BAY_R = ((-5, -4), (-2, -1), (1, 2), (4, 5))
UP = 12  # the spreader's height with the hook up
STEP = 4  # ticks a block of the hook's travel: a quarter block a tick
BRIDGE_TICKS = 60  # ticks from one hold to the other: 15 blocks
TROLLEY_TICKS = 12  # ticks from one column to the next: 3 blocks
#: the deckhouse, solid: f, r and its top
HOUSE_F, HOUSE_R, HOUSE_TOP = (-4, 4), 7, 8
#: the list gauge, a brass dial on each face of the deckhouse: its needle
#: stands on a pivot at this height on her centre line, upright when she
#: is level, and leans ``GAUGE_STEP`` degrees a ton to the heavy side, as
#: her mast would; it is ``NEEDLE`` long, and stops at ``GAUGE_STOP`` tons
GAUGE_PIVOT = 5.5
NEEDLE = 2.9
GAUGE_STEP = 14
GAUGE_STOP = 6
NEEDLE_TICKS = 15  # ticks of the needle's swing to a new list
#: the pulpit (stern) and the bow: decks at h 5
DECK_H = 5
PULPIT_F = (-17, -11)
#: the driver's platform, at the back of the pulpit, the keys before it:
#: its front row level with the deck, its back row a slab higher. The
#: driver stands on either and looks forward over the keys: ``DRIVER``
#: low by them, ``DRIVER_BACK`` high behind (where the walk checks have
#: the feet), the eye ``DRIVER_EYE`` (or ``DRIVER_BACK_EYE``) up, 1.62
#: over the feet
PLATFORM_F, PLATFORM_R = (-16, -15), (-2, 1)
DRIVER: Place = (PLATFORM_F[1], 0, 6)
DRIVER_EYE = DECK_H + 1 + 1.62
DRIVER_BACK: Place = (PLATFORM_F[0], 0, 7)
DRIVER_BACK_EYE = DECK_H + 1.5 + 1.62
BANKSMAN: Place = (12, 0, 6)
#: the keys: stone buttons lying on brass let into the deck before the
#: platform, in the ship's own directions (FORE the far row, PORT to the
#: left): name -> (f, r)
TRAVEL = {
    "PORT": (-13, -3),
    "FORE": (-13, -2),
    "STARBOARD": (-13, -1),
    "AFT": (-14, -2),
}
HOOK = {
    "HOOK UP": (-13, 1),
    "GRAB": (-13, 2),
    "HOOK DOWN": (-14, 1),
    "RELEASE": (-14, 2),
}
UNDO_AT: Place = (-16, 3, 6)  # UNDO's post, its button towards the platform
LEVER_AT: Place = (-16, 7, 6)  # RESET HOLD's post, the lever on its fore side
#: the window: the deck and the rail before the keys, and the top of her
#: transom under them, are glass as far as this either side
WINDOW_R = 4
SCREEN_H = 10  # the rail before the keys is a glass screen, this high
CANOPY_F = -15  # the canopy's fore edge: open sky over the driver's view
#: the tables: (the f of the aft row, the r of A1's column, the lowest tier)
PLAN_TABLE: Place = (-13, -8, 6)
HOLD_TABLE: Place = (-13, 4, 6)
BOW_TABLE: Place = (12, -6, 6)
PLAQUE = (-17, 0)
LECTERN: Place = (-19, -3, 1)
RECALL = (-20, 7, -1)
#: the donkey engine (a torch clock, caged) on the port dock by the bow
DONKEY = (13, -14)
BELL_PITCH = 1.2


def frame(dome: Dome) -> fittings.Frame:
    return fittings.frame(dome)


def point(
    fr: fittings.Frame, u: float, v: float, h: float
) -> tuple[float, float, float]:
    """a point of the frame in the world: u forward and v right, where
    the cell (f, r) spans u from f to f + 1 and v from r to r + 1"""
    ox, oy, oz = fr.origin
    (fx, fz), (rx, rz) = fr.forward, fr.right
    x = ox + fx * u + rx * v + (1 if fx + rx < 0 else 0)
    z = oz + fz * u + rz * v + (1 if fz + rz < 0 else 0)
    return (x, oy + h, z)


def bay_cells(i: int, tier: int | None = None) -> list[Place]:
    """a bay's cells: all six layers, or one crate's two"""
    hs = range(1, 2 * TIERS + 1) if tier is None else (2 * tier + 1, 2 * tier + 2)
    return [(f, r, h) for f in BAY_F[i // 4] for r in BAY_R[i % 4] for h in hs]


def bay_mid(i: int) -> tuple[float, float]:
    """the (u, v) of a bay's middle: where the hook hangs over it"""
    return (BAY_F[i // 4][0] + 1.0, BAY_R[i % 4][0] + 1.0)


def table_cell(at: Place, i: int, tier: int) -> Place:
    """a crate's block on a table: the aft row nearest f, port at r"""
    f, r, h = at
    return (f + i // 4, r + i % 4, h + tier)


def beam(f: int) -> int:
    """the ship's half beam at f (her bow is rounded)"""
    return {14: 6, 15: 5, 16: 3}.get(f, 7)


def footprint() -> set[tuple[int, int]]:
    """the ship's cells, stern to stem"""
    return {
        (f, r) for f in range(PULPIT_F[0], 17) for r in range(-beam(f), beam(f) + 1)
    }


#: the dock's basin, let into the floor: she lies afloat in it, water one
#: deep to this far fore and aft and either side of her centre line
BASIN_F, BASIN_R = (-18, 18), 9
#: landing steps out of the basin up to the dock walks: (f, r)
LANDINGS = ((-9, -9), (3, -9), (-9, 9), (3, 9))


def basin_places() -> set[tuple[int, int]]:
    """the basin's water: all round her, but where the stairs to the
    pulpit and the bow stand in it on their piers, and the landing steps"""
    piers = {(f, r) for f, r, _ in (*PULPIT_STAIRS, *BOW_STAIRS)}
    return (
        {
            (f, r)
            for f in range(BASIN_F[0], BASIN_F[1] + 1)
            for r in range(-BASIN_R, BASIN_R + 1)
        }
        - footprint()
        - piers
        - set(LANDINGS)
    )


def basin(dome: Dome) -> set[Cell]:
    """the basin's cells (in the dome's floor), each a source of water"""
    fr = frame(dome)
    return {fr.at(f, r, 0) for f, r in basin_places()}


def hold_floor() -> set[tuple[int, int]]:
    """the hold's floor: inside her sides, aft and fore of the deckhouse"""
    return {
        (f, r)
        for f in (*range(-10, -4), *range(5, 11))
        for r in range(-HOUSE_R + 1, HOUSE_R)
    }


#: the stair from the bow down into the fore hold, along the starboard
#: aisle: (f, r, h) of each step, highest first
HOLD_STAIR = ((12, 6, 4), (11, 6, 3), (10, 6, 2), (9, 6, 1))
#: the way out of the aft hold, for whoever gets in all the same: a ladder
#: up her starboard side at its aft corner, far from the bays, to a notch
#: in her side at h 4 (the top of the ladder's wall); from there it is
#: over the side into the basin, and there is no way back up
AFT_LADDER = (-10, 6)
NOTCH_H = 4
#: the stairs from the dock up to the pulpit and down from the bow
PULPIT_STAIRS = tuple((f, r, f + 22) for r in (-5, -4, 4, 5) for f in range(-21, -16))
BOW_STAIRS = tuple((f, r, 20 - f) for r in (-4, 4) for f in range(16, 20))
#: the gantry: its columns, rails at h 13, and the walk at h 10 outside
COLUMNS = tuple((f, r) for f in (-12, 0, 12) for r in (-10, 10))
RAIL_H = 13
WALK_H = 10
WALK_F = (-15, 15)
WALK_STAIRS = tuple(
    (-4 - k, side * 13, 1 + k) for side in (-1, 1) for k in range(WALK_H)
)


@dataclass
class Blocks:
    """every block of the room, as built and as ``reset`` leaves it"""

    floor: dict[Cell, str] = field(default_factory=dict)  # relaid floor
    #: under the floor: the basin's bed (not the dome's, so not in
    #: ``everything``)
    bed: dict[Cell, str] = field(default_factory=dict)
    solid: dict[Cell, str] = field(default_factory=dict)
    attached: dict[Cell, str] = field(default_factory=dict)  # need a support
    clear: set[Cell] = field(default_factory=set)  # air, to be kept so
    #: cells whose block changes state by itself (a clock, its lamps)
    moving: set[Cell] = field(default_factory=set)

    def everything(self) -> dict[Cell, str]:
        return {**self.floor, **self.solid, **self.attached}

    def above(self) -> dict[Cell, str]:
        return {**self.solid, **self.attached}


def gauge_cells(face: int) -> list[Place]:
    """the brass plate of a face's list gauge (-1 aft, 1 fore): an arch
    over the needle's pivot"""
    f = HOUSE_F[0] if face < 0 else HOUSE_F[1]
    low = math.floor(GAUGE_PIVOT)
    return [(f, r, h) for h in range(low, HOUSE_TOP) for r in range(-3, 4)] + [
        (f, r, HOUSE_TOP) for r in range(-2, 3)
    ]


def gauge_face(face: int, proud: float) -> float:
    """the u of a face of the deckhouse, and a little out from it"""
    return HOUSE_F[0] - proud if face < 0 else HOUSE_F[1] + 1 + proud


def turned(
    fr: fittings.Frame,
    tons: float,
    inner: float,
    length: float,
    width: float,
    thick: float,
) -> str:
    """the transformation of a bar of a list gauge: a block display at the
    needle's pivot, drawn as a bar from ``inner`` to ``inner + length``
    out from the pivot, ``width`` across and ``thick`` through, standing
    upright and turned to where the needle points at a list of ``tons``
    (to the frame's right, starboard, for more than none)"""
    (fx, fz), (rx, rz) = fr.forward, fr.right
    sx, sz = abs(fx) * thick + abs(rx) * width, abs(fz) * thick + abs(rz) * width
    angle = math.radians(GAUGE_STEP * tons)
    # about the way she points, up towards the right: the axis (rz, 0, -rx).
    # The bar's own middle of its inner end goes to the pivot
    cx, cy, cz = sx / 2, -inner, sz / 2
    cos, sin = math.cos(angle), math.sin(angle)
    ax, az = rz, -rx
    dot = ax * cx + az * cz
    turn = (
        cx * cos + (-az * cy) * sin + ax * dot * (1 - cos),
        cy * cos + (az * cx - ax * cz) * sin,
        cz * cos + (ax * cy) * sin + az * dot * (1 - cos),
    )
    moved = ",".join(f"{_num(-t)}f" for t in turn)
    return (
        f"transformation:{{translation:[{moved}],"
        f"scale:[{_num(sx)}f,{_num(length)}f,{_num(sz)}f],"
        f"left_rotation:{{axis:[{ax}f,0f,{az}f],angle:{_num(angle)}f}},"
        "right_rotation:[0f,0f,0f,1f]}"
    )


def needle_pose(fr: fittings.Frame, tons: int) -> str:
    """the needle's transformation at a list (it has a short tail)"""
    return turned(fr, tons, -0.3, NEEDLE + 0.3, 0.16, 0.06)


#: the scale's marks: one for each ton's width from ``-GAUGE_STOP`` to
#: ``GAUGE_STOP``; mark j lies between j - GAUGE_STOP and the next ton,
#: and is green while both are within the band's limit
ZONES = 2 * GAUGE_STOP


def zone_limit(j: int) -> int:
    """the least limit at which mark j is green"""
    return max(abs(j - GAUGE_STOP), abs(j + 1 - GAUGE_STOP))


def gauge_summons(fr: fittings.Frame) -> list[str]:
    """the list gauges' block displays, on both faces: the scale's marks
    round the arch (red until ``trim/band`` says), a copper hub and the
    needle, upright; all lit whatever the light"""
    found = []

    def bar(face: int, proud: float, block: str, tags, pose: str) -> None:
        x, y, z = point(fr, gauge_face(face, proud), 0.5, GAUGE_PIVOT)
        listed = ",".join(f'"{t}"' for t in (ENTITY_TAG, *tags))
        found.append(
            f"summon minecraft:block_display {_num(x)} {_num(y)} {_num(z)} "
            f"{{Tags:[{listed}],brightness:{{sky:15,block:15}},"
            f"block_state:{fittings.block_state(block)},{pose}}}"
        )

    for face in (-1, 1):
        for j in range(ZONES):
            pose = turned(fr, j + 0.5 - GAUGE_STOP, NEEDLE + 0.05, 0.22, 0.62, 0.04)
            bar(face, 0.03, RED, (ZONE_TAG, f"st.cargo.z{j}"), pose)
        bar(face, 0.14, COPPER, (), turned(fr, 0, -0.2, 0.4, 0.4, 0.08))
        bar(face, 0.09, NEEDLE_BLOCK, (NEEDLE_TAG,), needle_pose(fr, 0))
    return found


NEEDLE_BLOCK = "minecraft:polished_blackstone"


YAWS = {"south": 0, "west": 90, "north": 180, "east": -90}


def key(fr: fittings.Frame, f: int, r: int, name: str) -> fittings.Post:
    """a key of the desk: a stone button lying on a brass block let into
    the deck, its name written flat on the brass at the driver's side,
    black on the gold"""
    ahead = fr.facing(1, 0)
    button = f"minecraft:stone_button[face=floor,facing={ahead},powered=false]"
    yaw = YAWS[fr.facing(-1, 0)]
    words = name.replace(" ", "\n")
    label = fittings.display(
        (ENTITY_TAG,),
        point(fr, f + 0.06, r + 0.5, DECK_H + 1.01),
        yaw,
        fittings.label_text(words, "black", bold="true"),
        0.45,
        pitch=-90,
    )
    at = fr.at(f, r, DECK_H + 1)
    return fittings.Post({fr.at(f, r, DECK_H): BRASS}, {at: button}, [label], at)


def posts(fr: fittings.Frame) -> dict[str, fittings.Post]:
    """the desk's keys, UNDO's button and RESET HOLD's lever on their
    brass posts"""
    ahead, port = fr.facing(1, 0), fr.facing(0, -1)
    found = {name: key(fr, f, r, name) for name, (f, r) in {**TRAVEL, **HOOK}.items()}
    found["UNDO"] = fittings.input_post(
        fr.at(*UNDO_AT),
        port,
        f"minecraft:stone_button[face=wall,facing={port},powered=false]",
        ("UNDO", "the last", "move"),
        "UNDO",
        (ENTITY_TAG,),
    )
    found["RESET HOLD"] = fittings.input_post(
        fr.at(*LEVER_AT),
        ahead,
        fittings.lever(ahead),
        ("RESET HOLD", "every crate", "back.", "Pull twice."),
        "RESET HOLD",
        (ENTITY_TAG,),
    )
    return found


def donkey(fr: fittings.Frame) -> fittings.Machine:
    """the donkey engine: a torch clock with its lamps and pistons"""
    f, r = DONKEY
    return fittings.torch_clock(fr, f, r, 1, 1, lamps=True, pistons=True)


def logbook_pages(band: int | None, m: int) -> list[str]:
    """the log's four pages; the fourth is the manifest drawn (none
    before the room is armed)"""
    pages = [
        "Cargo Hold log\nO. Finch, Chief Engineer\n\nThe Marigold brought our "
        "stores down through the sea gate every month. She is still here, "
        "afloat in the dock. When the Engine took the station it swung the crane about "
        "like a toy and left her cargo anyhow.",
        "The next pump draws through her ballast tanks. Until she is stowed to "
        "the manifest and sits level, its cocks stay shut.\n\nNever set a crate "
        "on a lighter one: it crushes. Iron, then barrels, then bales. Three "
        "high at most. She is afloat: load her level, and watch the list gauge.",
        "The crane is worked from the pulpit. UNDO puts the last crate back. "
        "RESET HOLD puts them all back.\n\nWith a mate: one in the pulpit, one "
        "at the bow. The deckhouse hides the fore hold from the pulpit. The "
        "banksman calls it.\n\nThe hook stopped over my head today. It waited. "
        "Then it went on. It is playing with us.",
    ]
    if band is None:
        return [*pages, "MANIFEST\n\nOn the chart table when you come aboard.\n\nO. F."]
    plan = parse(BANDS[band].manifests[m][1])
    lines = []
    for i, stack in enumerate(plan):
        if not stack:
            continue
        where = ("AFT " if i < 4 else "FORE ") + BAYS[i][1]
        said = KIND_NAME[stack[0]]
        for k in stack[1:]:
            said += f", {KIND_NAME[k]} on it"
        lines.append(f"{where}: {said}.")
    head = f"MANIFEST No. {m + 1}\n{MANIFEST_NAMES[m]}\n\n"
    return [*pages, head + "\n".join(lines) + "\n\nO. F."]


def logbook(fr: fittings.Frame, band: int | None = None, m: int = 0) -> str:
    return fittings.lectern_with_book(
        fr.facing(-1, 0), "Cargo Hold log", "O. Finch", logbook_pages(band, m)
    )


def room_blocks(dome: Dome) -> Blocks:
    """the room as built: the ship and her crane's gantry, the dock round
    her, the dressing; every bay empty (the pack lays the cargo)"""
    fr = frame(dome)
    b = Blocks()

    def put(place: Place, block: str, part: dict[Cell, str] | None = None) -> None:
        (b.solid if part is None else part)[fr.at(*place)] = block

    def stood(place: Place, block: str) -> None:
        b.attached[fr.at(*place)] = block

    ahead, back = fr.facing(1, 0), fr.facing(-1, 0)
    port, star = fr.facing(0, -1), fr.facing(0, 1)
    lights = domes.light_cells(dome)[0]
    interior = domes.dome_cells(dome).interior
    ship = footprint()

    # -- the floor: the hold's tank top, each bay in its column's colour;
    # the dock walks either side of her
    bays = {
        (f, r): i for i in range(len(BAYS)) for f, r, h in bay_cells(i, 0) if h == 1
    }
    for f, r in hold_floor():
        block = BAY_COLOUR[bays[f, r] % 4] if (f, r) in bays else HOLD_FLOOR
        put((f, r, 0), block, b.floor)
    # her bottom, under her sides and ends; the basin she floats in, on a
    # bed of the foundation's stone (the floor's lanterns there go down
    # into it, under the water); the dock walks all round it, and the
    # landing steps up to them
    wet = basin_places()
    for f, r in ship - hold_floor():
        put((f, r, 0), KEEL, b.floor)
    for f, r in wet:
        put((f, r, 0), WATER, b.floor)
        lit = fr.at(f, r, 0) in lights
        b.bed[fr.at(f, r, -1)] = domes.LIGHT if lit else domes.FOUNDATION
    in_floor = domes.dome_cells(dome).floor
    for f in range(BASIN_F[0] - 3, BASIN_F[1] + 3):
        for r in range(-BASIN_R - 2, BASIN_R + 3):
            cell = fr.at(f, r, 0)
            if (f, r) in ship or (f, r) in wet or cell not in in_floor:
                continue
            if cell not in lights:
                put((f, r, 0), DOCK_WALK, b.floor)
    for f, r in LANDINGS:
        put(
            (f, r, 0),
            f"{STAIRS}[facing={star if r > 0 else port},half=bottom]",
            b.floor,
        )
        b.bed[fr.at(f, r, -1)] = domes.FOUNDATION
    for i in range(4):
        put((-10, BAY_R[i][0], 0), "minecraft:sea_lantern", b.floor)
        put((10, BAY_R[i][1], 0), "minecraft:sea_lantern", b.floor)

    # -- the hull: her sides and ends to h 4, the gunwale at h 5; her
    # boot-topping at the waterline
    hold = hold_floor()
    for f, r in ship:
        inside = (f, r) in hold
        if inside:
            continue
        side = abs(r) == beam(f) or (f, r + 1) not in ship or (f, r - 1) not in ship
        end = (f - 1, r) not in ship or (f + 1, r) not in ship
        for h in range(1, DECK_H):
            if HOUSE_F[0] <= f <= HOUSE_F[1]:
                break  # the deckhouse is its own
            if h == 1:
                block = BOOT if side or end else KEEL
            elif side and f % 3 == 0:
                block = CHISELED  # a frame, outside
            else:
                block = HULL
            put((f, r, h), block)
    # her sides along the holds: the gunwale and its rail
    for f, r in ship:
        if (f, r) in hold or not (-10 <= f <= 10) or HOUSE_F[0] <= f <= HOUSE_F[1]:
            continue
        put((f, r, DECK_H), CUT)
        for h in (6, 7):
            put((f, r, h), BARS)

    # the way out of the aft hold: a ladder to a notch in her side
    f, r = AFT_LADDER
    for h in range(1, NOTCH_H):
        stood((f, r, h), f"minecraft:ladder[facing={port}]")
    for h in range(NOTCH_H, 8):
        b.solid.pop(fr.at(f, r + 1, h))
        b.clear.add(fr.at(f, r + 1, h))

    # -- the deckhouse: the engine casing, dark oak in riveted copper
    f0, f1 = HOUSE_F
    for f in range(f0, f1 + 1):
        for r in range(-HOUSE_R, HOUSE_R + 1):
            for h in range(1, HOUSE_TOP + 1):
                edge = (f in (f0, f1)) + (abs(r) == HOUSE_R) + (h in (1, HOUSE_TOP))
                if h == 1:
                    block = BOOT if abs(r) == HOUSE_R else KEEL
                elif edge >= 2:
                    block = CUT
                elif h == HOUSE_TOP:
                    block = COPPER
                elif abs(r) == HOUSE_R and h in (3, 6) and f % 2 == 0:
                    block = CHISELED  # a porthole, not a window
                elif f in (f0, f1) and h == 3 and abs(r) in (2, 5):
                    block = CHISELED
                else:
                    block = HOUSE
                put((f, r, h), block)
    # the list gauges' brass plates (the pack's displays are the rest)
    for face in (-1, 1):
        for place in gauge_cells(face):
            put(place, BRASS)
    # the funnel through the roof, on the centre line where no crate passes
    for up, block in enumerate((COPPER, BRASS, COPPER, GRATE)):
        put((0, 0, HOUSE_TOP + 1 + up), block)
    # ventilator cowls on the roof, between the crates' columns
    for f, r in ((-2, -3), (2, 3), (-3, 6), (3, -6), (2, -3), (-2, 3)):
        put((f, r, HOUSE_TOP + 1), "minecraft:waxed_lightning_rod[facing=up]")

    # -- the pulpit: a deck at h 5 on her stern, its wings over the dock
    # walks, railed, a copper canopy over its back; the driver's platform,
    # the keys in the deck before it, a glass deck and screen before them
    # (clear, with nothing to see, straight before the board), the tables
    # either side, the lever
    p0, p1 = PULPIT_F
    stair_tops = {(f, r) for f, r, h in PULPIT_STAIRS if h == DECK_H}
    for f in range(p0, p1 + 1):
        for r in range(-9, 10):
            if (f, r) in stair_tops:
                continue
            front = f == p1
            window = f >= p1 - 1 and abs(r) <= WINDOW_R
            put((f, r, DECK_H), GLASS if window else GRATE if front else DECK)
            if front and abs(r) < 9:
                # a glass screen, too high to be climbed or jumped from
                # a table: nobody drops into the aft hold from here
                for h in range(6, SCREEN_H + 1):
                    put((f, r, h), BARRIER if abs(r) <= 1 and h >= 8 else PANE)
            elif front or f == p0 or abs(r) == 9:
                for h in (6, 7):
                    put((f, r, h), BARS)
    for r in range(-WINDOW_R, WINDOW_R + 1):
        put((p1, r, DECK_H - 1), GLASS)  # the top of her transom
    for f in (p0, CANOPY_F):
        for r in (-9, 9):
            for h in range(6, 10):
                put((f, r, h), PILLAR)
    for f in range(p0, CANOPY_F + 1):
        for r in range(-9, 10):
            put((f, r, 10), SLAB)
    # the driver's platform: green copper let into the deck, a slab on
    # its back row
    for f in range(PLATFORM_F[0], PLATFORM_F[1] + 1):
        for r in range(PLATFORM_R[0], PLATFORM_R[1] + 1):
            put((f, r, DECK_H), PLATFORM)
            if f == PLATFORM_F[0]:
                put((f, r, DECK_H + 1), PLATFORM_SLAB)
    # a notice at the head of each pair of stairs
    for r in (-4, 4):
        stood(
            (PLATFORM_F[1], r, 6),
            fittings.standing_sign(
                back, "She's afloat.", "Load her level,", "or she'll go", "over."
            ),
        )
    for table in (PLAN_TABLE, HOLD_TABLE):
        for i in range(len(BAYS)):
            f, r, _ = table_cell(table, i, 0)
            put((f, r, DECK_H), TABLE_TOP)
    for f, r, h in PULPIT_STAIRS:
        put((f, r, h), f"{STAIRS}[facing={ahead},half=bottom]")
        for low in range(1, h):
            put((f, r, low), HULL)
    for post in posts(fr).values():
        b.solid.update(post.solid)
        b.attached.update(post.attached)
    stood((-16, -3, 6), f"minecraft:bell[attachment=floor,facing={port}]")
    stood((-14, -8, 6), LANTERN)
    stood((-14, 8, 6), LANTERN)
    for r in (-6, 6):
        stood((-16, r, 9), HANGING)

    # -- the bow: the banksman's stand, railed, its table and bell; a stair
    # down into the fore hold and two to the dock
    hold_stair = {(f, r) for f, r, _ in HOLD_STAIR}
    bow_heads = {(15, -4), (15, 4)}
    for f, r in ship:
        if f < 11 or (f, r) in hold_stair:
            continue
        rim = f == 11 or any(
            (f + df, r + dr) not in ship for df, dr in ((1, 0), (0, 1), (0, -1))
        )
        put((f, r, DECK_H), GRATE if f == 11 and abs(r) < 7 else DECK)
        if rim and (f, r) not in bow_heads:
            for h in (6, 7):
                put((f, r, h), BARS)
    for f, r, h in HOLD_STAIR:
        put((f, r, h), f"{STAIRS}[facing={ahead},half=bottom]")
        for low in range(1, h):
            put((f, r, low), HULL)
        for up in range(h + 1, 8):
            b.solid.pop(fr.at(f, r, up), None)
            b.clear.add(fr.at(f, r, up))
    for f, r, h in BOW_STAIRS:
        put((f, r, h), f"{STAIRS}[facing={back},half=bottom]")
        for low in range(1, h):
            put((f, r, low), HULL)
    for i in range(len(BAYS)):
        f, r, _ = table_cell(BOW_TABLE, i, 0)
        put((f, r, DECK_H), TABLE_TOP)
    stood((14, 3, 6), f"minecraft:bell[attachment=floor,facing={star}]")
    stood(
        (13, 2, 6),
        fittings.standing_sign(
            ahead, "BANKSMAN", "Call the fore", "hold to the", "pulpit."
        ),
    )
    stood(
        (14, 1, 6),
        fittings.standing_sign(
            ahead, "Say what is in", "each bay, and", "when the hook", "is right."
        ),
    )
    for r in (-6, 6):
        stood((14, r, 8), LANTERN)
    # her name, and a cabin skylight on the bow
    put((15, 0, 6), COPPER)
    stood((15, 0, 7), LANTERN)

    # -- the gantry: six lattice columns, two rails at h 13, the walk at
    # h 10 just outside them, railed, with its stairs at the stern corners
    for f, r in COLUMNS:
        for h in range(1, RAIL_H):
            put((f, r, h), CUT if h % 4 == 0 else GRATE)
    for r in (-10, 10):
        for f in range(-12, 13):
            put((f, r, RAIL_H), CHISELED)
    walk_stairs = {(f, r) for f, r, _ in WALK_STAIRS}
    for side in (-1, 1):
        for f in range(WALK_F[0], WALK_F[1] + 1):
            for r in (11 * side, 12 * side):
                put((f, r, WALK_H), GRATE)
            for h in (11, 12):
                if (f, 10 * side) not in COLUMNS:
                    lamp = h == 12 and f % 3 == 0 and -12 < f < 12 and f
                    put((f, 10 * side, h), HANGING if lamp else BARS)
                if (f, 13 * side) not in walk_stairs and (
                    f + 1,
                    13 * side,
                ) not in walk_stairs:
                    put((f, 13 * side, h), BARS)
        for f in WALK_F:  # the ends, closing the corners of the rails
            for r in range(10 * side, 14 * side, side):
                for h in (11, 12):
                    if fr.at(end := f + (1 if f > 0 else -1), r, h) in interior:
                        put((end, r, h), BARS)
    for f, r, h in WALK_STAIRS:
        put((f, r, h), f"{STAIRS}[facing={back},half=bottom]")
        for low in range(1, h):
            put((f, r, low), CUT if low % 4 == 0 else GRATE)
    for f, r in COLUMNS:
        stood((f - 1 if f > -12 else f + 1, r, 1), LANTERN)
    # lanterns hanging under the rails need the bars' cells: those are set
    for cell, block in list(b.solid.items()):
        if block == HANGING:
            b.attached[cell] = b.solid.pop(cell)

    # -- the dock: mooring chains to copper bollards across the water, a
    # coal bunker, a tar tub and a slatted bin (no barrel: a barrel is
    # cargo), the donkey engine, the sea gate she came in by
    axis = "x" if fr.right[0] else "z"
    along = "x" if fr.forward[0] else "z"
    for f in (-7, 7):
        for side in (-1, 1):
            put((f, 10 * side, 1), COPPER)
            put((f, 10 * side, 2), CUT)
            put((f, 10 * side, 3), CHISELED)
            for r in (8 * side, 9 * side):
                put((f, r, 3), f"{CHAIN}[axis={axis}]")
    for f in range(4, 7):
        for r in (11, 12):
            put((f, r, 1), "minecraft:coal_block")
            put((f, 13, 1), CUT)
        put((f, 10, 1), CUT)
    put((-2, 11, 1), "minecraft:cauldron")
    put((-1, 12, 1), "minecraft:composter")
    machine = donkey(fr)
    b.floor.update(machine.bed)
    b.solid.update(machine.solid)
    b.attached.update(machine.attached)
    b.moving |= machine.moving
    df, dr = DONKEY
    for f in range(df - 3, df + 4):
        for r in range(dr - 2, dr + 3):
            ring = f in (df - 3, df + 3) or r in (dr - 2, dr + 2)
            if ring:
                for h in (1, 2):
                    put((f, r, h), BARS)
            put((f, r, 3), SLAB)
    for f in range(-6, 7):
        for h in range(1, 11):
            edge = abs(f) == 6 or h in (1, 10)
            block = (
                BRASS
                if edge
                else (
                    CHISELED if (f, h) == (0, 5) else "minecraft:waxed_oxidized_copper"
                )
            )
            put((f, 19, h), block)

    # lamp posts along the dock walks, capstans at her stern quarters,
    # cable drums and a grindstone by the bow, a tool rack of chain
    for f in (-17, -4, 9):
        for side in (-1, 1):
            put((f, 10 * side, 1), "minecraft:dark_oak_fence")
            put((f, 10 * side, 2), "minecraft:dark_oak_fence")
            stood((f, 10 * side, 3), LANTERN)
    for side in (-1, 1):
        put((-20, 10 * side, 1), CUT)
        put((-20, 10 * side, 2), CHISELED)
        stood((-20, 10 * side, 3), "minecraft:waxed_lightning_rod[facing=up]")
    for f in (17, 18):
        for r in (11, 12):
            put((f, r, 1), f"minecraft:stripped_spruce_log[axis={along}]")
    stood((16, 11, 1), f"minecraft:grindstone[face=floor,facing={ahead}]")
    stood((19, 10, 1), "minecraft:anvil[facing=" + ahead + "]")

    # -- the way in: the plaque on her stern, the log, the recall post
    signs = (
        ("THE CARGO HOLD", "Stow the", "Marigold to the", "manifest."),
        ("Never set a", "crate on a", "lighter one.", ""),
        ("She is afloat.", "Keep her list", "gauge in the", "green."),
    )
    solid, attached = fittings.plaque_blocks(fr, *PLAQUE, signs)
    b.solid.update(solid)
    b.attached.update(attached)
    b.solid[fr.at(*LECTERN)] = logbook(fr)
    solid, attached = fittings.recall_post_blocks(fr, *RECALL)
    b.solid.update(solid)
    b.attached.update(attached)
    return b


def inputs(dome: Dome) -> set[Cell]:
    """every button and lever of the room"""
    fr = frame(dome)
    f, r, side = RECALL
    return {fr.at(f, r + side, 2)} | {p.input for p in posts(fr).values()}


def dressing_cells(dome: Dome) -> set[Cell]:
    """the cells where a crate's block may be: the bays and the tables"""
    fr = frame(dome)
    cells = {fr.at(*c) for i in range(len(BAYS)) for c in bay_cells(i)}
    for table in (PLAN_TABLE, HOLD_TABLE, BOW_TABLE):
        cells |= {
            fr.at(*table_cell(table, i, t))
            for i in range(len(BAYS))
            for t in range(TIERS)
        }
    return cells


# --------------------------------------------------------------- the crane
# Every part is a block display (the drum an item display), summoned with
# its corner at its box's least corner and scaled to the box, so that a
# relative ``tp`` moves it whole. Boxes are in the frame: (u0, u1, v0, v1,
# h0, h1), u forward, v right, at the crane's home: over A1, hook up.

IDENTITY = "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]"
Box = tuple[float, float, float, float, float, float]


def home() -> tuple[float, float]:
    return bay_mid(0)


def crane_boxes() -> list[tuple[str, Box, tuple[str, ...]]]:
    """the crane's fixed parts at home: (block, box, tags beyond the
    crane's): the bridge's two girders in sevens, its end trucks with
    their lamps and the driver's brass cab; the trolley's frame, winch
    house and lamp; the spreader and its iron ends"""
    c, vc = home()
    found: list[tuple[str, Box, tuple[str, ...]]] = []
    bridge = (B_TAG,)
    for lo, hi in ((c - 1.5, c - 0.5), (c + 0.5, c + 1.5)):
        for j in range(7):
            v0 = -10 + 3 * j
            found.append((CUT, (lo, hi, v0, v0 + 3, 14, 15), bridge))
    for v0 in (-11, 11):
        found.append((CHISELED, (c - 2, c + 2, v0, v0 + 1, 13.5, 15), bridge))
        found.append(
            ("minecraft:lantern", (c - 0.5, c + 0.5, v0, v0 + 1, 15, 16), bridge)
        )
    found.append((BRASS, (c + 1, c + 2, -11, -10, 15, 16), bridge))
    trolley = (B_TAG, T_TAG)
    for v0, v1 in ((vc - 1.5, vc - 1.0), (vc + 1.0, vc + 1.5)):
        found.append((COPPER, (c - 1.5, c + 1.5, v0, v1, 15, 15.5), trolley))
    for u0, u1 in ((c - 1.5, c - 1.0), (c + 1.0, c + 1.5)):
        found.append((COPPER, (u0, u1, vc - 1.0, vc + 1.0, 15, 15.5), trolley))
    found.append((HOUSE, (c - 1.0, c, vc - 1.0, vc + 1.0, 15.5, 16.5), trolley))
    found.append(
        (
            f"{BULB}[lit=true]",
            (c - 0.8, c - 0.2, vc - 0.3, vc + 0.3, 16.5, 17.1),
            trolley,
        )
    )
    hook = (B_TAG, T_TAG, K_TAG)
    found.append(
        (
            "minecraft:dark_oak_planks",
            (c - 1, c + 1, vc - 0.2, vc + 0.2, UP, UP + 0.4),
            (*hook, SPREADER_TAG),
        )
    )
    for u0 in (c - 1.1, c + 0.9):
        found.append(
            (IRON_END, (u0, u0 + 0.2, vc - 0.25, vc + 0.25, UP, UP + 0.6), hook)
        )
    return found


IRON_END = "minecraft:iron_block"
#: the crane's fixed parts, and the drum
PARTS = 19 + 6 + 3 + 1


def _num(x: float) -> str:
    return f"{x:.4f}".rstrip("0").rstrip(".") if x != int(x) else f"{int(x)}"


def box_summon(fr: fittings.Frame, block: str, box: Box, tags: tuple[str, ...]) -> str:
    """the command that summons a block display filling a box"""
    u0, u1, v0, v1, h0, h1 = box
    a, z = point(fr, u0, v0, h0), point(fr, u1, v1, h1)
    lo = [min(p, q) for p, q in zip(a, z, strict=True)]
    size = [abs(p - q) for p, q in zip(a, z, strict=True)]
    listed = ",".join(f'"{t}"' for t in (ENTITY_TAG, CRANE_TAG, *tags))
    scale = ",".join(f"{_num(s)}f" for s in size)
    return (
        f"summon minecraft:block_display {' '.join(_num(p) for p in lo)} "
        f"{{Tags:[{listed}],teleport_duration:1,block_state:{fittings.block_state(block)},"
        f"transformation:{{translation:[0f,0f,0f],scale:[{scale}],{IDENTITY}}}}}"
    )


def drum_turn(fr: fittings.Frame, quarter: int) -> str:
    """the winch drum's transformation, a number of quarter turns on: a
    log lying along the bridge (the frame's right), turned about it"""
    rx, rz = fr.right
    lie = "[0f,0f,0.7071068f,0.7071068f]" if rx else "[0.7071068f,0f,0f,0.7071068f]"
    axis = f"[{abs(rx)}f,0f,{abs(rz)}f]"
    angle = round(quarter % 4 * math.pi / 2, 4)
    return (
        "transformation:{translation:[0f,0f,0f],scale:[0.6f,1.6f,0.6f],"
        f"left_rotation:{{axis:{axis},angle:{angle}f}},right_rotation:{lie}}}"
    )


def drum_summon(fr: fittings.Frame) -> str:
    c, vc = home()
    x, y, z = point(fr, c + 0.5, vc, 15.75)
    listed = ",".join(
        f'"{t}"' for t in (ENTITY_TAG, CRANE_TAG, PART_TAG, B_TAG, T_TAG, DRUM_TAG)
    )
    return (
        f"summon minecraft:item_display {_num(x)} {_num(y)} {_num(z)} "
        f'{{Tags:[{listed}],teleport_duration:1,item:{{id:"minecraft:stripped_spruce_log",'
        f"count:1}},{drum_turn(fr, 0)}}}"
    )


def link_box(h: int) -> Box:
    """a link of the chain at home, filling the cell above h"""
    c, vc = home()
    return (c - 0.5, c + 0.5, vc - 0.5, vc + 0.5, h, h + 1)


def link_summon(fr: fittings.Frame, h: int, at_spreader: bool = False) -> str:
    """a link of chain at height h at home, or (``at_spreader``) relative to
    the spreader standing at h, wherever it is"""
    tags = (B_TAG, T_TAG, LINK_TAG, f"st.cargo.l{h}")
    line = box_summon(fr, f"{CHAIN}[axis=y]", link_box(h), tags)
    if not at_spreader:
        return line
    c, vc = home()
    sp = point(fr, c - 1, vc - 0.2, h)  # the spreader's corner, at h
    u0, u1, v0, v1, h0, h1 = link_box(h)
    a, z = point(fr, u0, v0, h0), point(fr, u1, v1, h1)
    lo = [min(p, q) for p, q in zip(a, z, strict=True)]
    spl = [
        min(p, q) for p, q in zip(sp, point(fr, c + 1, vc + 0.2, h + 0.4), strict=True)
    ]
    rel = " ".join(
        f"~{_num(p - q)}" if p != q else "~" for p, q in zip(lo, spl, strict=True)
    )
    head, _, tail = line.partition(" {Tags")
    words = head.split(" ")
    return (
        f"execute at @e[type=minecraft:block_display,tag={SPREADER_TAG},limit=1] "
        f"run {' '.join(words[:2])} {rel} {{Tags{tail}"
    )


def crane_summons(fr: fittings.Frame) -> list[str]:
    """the crane at home, hook up: its parts, the drum, two links"""
    found = [
        box_summon(fr, block, box, (PART_TAG, *tags))
        for block, box, tags in crane_boxes()
    ]
    found.append(drum_summon(fr))
    found += [link_summon(fr, h) for h in range(UP + 1, RAIL_H + 2)]
    return found


def crate_summons(fr: fittings.Frame, i: int, tier: int, kind: int) -> list[str]:
    """a crate of a kind in a bay at a tier, as eight displays that ride
    the hook"""
    found = []
    for f, r, h in bay_cells(i, tier):
        found.append(
            box_summon(
                fr,
                CRATE[kind],
                (f, f + 1, r, r + 1, h, h + 1),
                (B_TAG, T_TAG, K_TAG, CRATE_TAG),
            )
        )
    return found


def crane_places(fr: fittings.Frame) -> set[Cell]:
    """every cell any part of the crane is ever in: at both bridge stops,
    all four trolley stops, the hook at every height, a crate on it"""
    cells: set[Cell] = set()
    parts = [(box, tags) for _, box, tags in crane_boxes()]
    parts += [(link_box(h), (B_TAG, T_TAG)) for h in range(2, RAIL_H + 2)]
    c, vc = home()

    def add(u0: float, u1: float, v0: float, v1: float, h0: float, h1: float) -> None:
        for f in range(math.floor(u0), math.ceil(u1)):
            for r in range(math.floor(v0), math.ceil(v1)):
                for h in range(math.floor(h0), math.ceil(h1)):
                    cells.add(fr.at(f, r, h))

    for row in (0, 1):
        for col in range(4):
            du = bay_mid(row * 4)[0] - c
            dv = bay_mid(col)[1] - vc
            for (u0, u1, v0, v1, h0, h1), tags in parts:
                dw = dv if T_TAG in tags else 0
                drops = range(UP) if K_TAG in tags else (0,)
                for d in drops:
                    add(u0 + du, u1 + du, v0 + dw, v1 + dw, h0 - d, h1 - d)
            # a crate on the hook, up
            for f, r, _ in bay_cells(row * 4 + col, 0):
                cells |= {fr.at(f, r, UP - 2), fr.at(f, r, UP - 1)}
    return cells


# ----------------------------------------------------------- the functions


def _s(name: str) -> str:
    return f"#cargo.{name} {OBJ}"


def _set(name: str, value: int) -> str:
    return f"scoreboard players set {_s(name)} {value}"


def _is(name: str, value: Any) -> str:
    return f"if score {_s(name)} matches {value}"


def _not(name: str, value: Any) -> str:
    return f"unless score {_s(name)} matches {value}"


def _op(a: str, op: str, b: str) -> str:
    """an operation on two scores; ``b`` a number is the pack's constant"""
    other = f"#{b} {OBJ}" if b.isdigit() else _s(b)
    return f"scoreboard players operation {_s(a)} {op} {other}"


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


def _fill(fr: fittings.Frame, places: list[Place], block: str) -> str:
    cells = [fr.at(*p) for p in places]
    lo = tuple(min(c[i] for c in cells) for i in range(3))
    hi = tuple(max(c[i] for c in cells) for i in range(3))
    return dp.fill(lo, hi, block)  # type: ignore[arg-type]


def _tp(dx: float, dz: float, dy: float = 0) -> str:
    def one(d: float) -> str:
        return f"~{_num(d)}" if d else "~"

    return f"tp @s {one(dx)} {one(dy)} {one(dz)}"


#: the reasons for a refusal (``why``), for the check
FULL, CRUSH, TRIM, SHUT, CLEAR, NOT_ON = 1, 2, 3, 4, 5, 6
HISTORY = 30  # moves UNDO can take back
ASK_TICKS = 100  # RESET HOLD's second pull, within 5 s
FLASH_TICKS = 10
CREAK = "block.chest.open"  # low: her timbers
#: playsound's volume over 1 is range, not loudness: a sound fades to
#: nothing at 16 blocks a unit. The far hold is some 25 blocks from the
#: pulpit or the bow, so the crane's sounds carry 48 and the room's 32
LOUD, ROOM = 3, 2
PARTY_TICKS = 40
#: the hints: name -> (seconds at level 5, text)
HINTS = {
    "crane": (
        60,
        "Work the crane from the pulpit on her stern: FORE, AFT, PORT, "
        "STARBOARD, then HOOK DOWN and GRAB.",
    ),
    "stuck": (
        240,
        "Stuck? Build each stack from the bottom: the heaviest crate first. "
        "UNDO takes back a move.",
    ),
}


def column(fr: fittings.Frame, i: int) -> str:
    """anyone in the game (or a stand-in) in a bay's column, floor to hook"""
    (f0, f1), (r0, r1) = BAY_F[i // 4], BAY_R[i % 4]
    return (
        f"entity @e[tag=st.in,{dp.box_selector(fr.at(f0, r0, 1), fr.at(f1, r1, UP))}]"
    )


def lay_lines(band: int, m: int) -> list[str]:
    """the scores of a manifest: its start in the bays, its plan, the
    band's limit and its shut bay"""
    b = BANDS[band]
    start, plan = (parse(t) for t in b.manifests[m][:2])
    lines = [_set("band", band), _set("m", m + 1), _set("lim", b.limit)]
    lines += [_set("nlim", -b.limit), _set("shut", -1 if b.shut is None else b.shut)]
    for i in range(len(BAYS)):
        lines.append(_set(f"b{i}.n", len(start[i])))
        for t in range(TIERS):
            lines.append(_set(f"b{i}.t{t}", start[i][t] if t < len(start[i]) else 0))
            lines.append(_set(f"g{i}.t{t}", plan[i][t] if t < len(plan[i]) else 0))
    return lines


def functions(pack: dp.Pack) -> None:
    """the Cargo Hold's functions (see the module docstring)"""
    dome = layout.DOMES[INDEX]
    fr = frame(dome)
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    pack.constants(OBJ, 2, 4, 8, 30, 100)
    (fx, fz), (rx, rz) = fr.forward, fr.right
    heart = " ".join(_num(p) for p in point(fr, 0, 0.5, 8))
    funnel = " ".join(_num(p) for p in point(fr, 0.5, 0.5, HOUSE_TOP + 5))

    def fid(name: str) -> str:
        return pack.id(f"{base}/{name}")

    def call(name: str, when: str = "") -> str:
        line = f"function {fid(name)}"
        return f"execute {when} run {line}" if when else line

    def fn(name: str, lines: list[str]) -> None:
        pack.function(f"{base}/{name}", lines)

    def sound(name: str, volume: float = ROOM, pitch: float = 1) -> str:
        return f"playsound minecraft:{name} block {here} {heart} {volume} {pitch}"

    # the crane's sounds come from the part that makes them, so the
    # driver and the banksman can follow it by ear
    hook_at = f"at @e[type=minecraft:block_display,tag={SPREADER_TAG},limit=1]"
    drum_at = f"at @e[type=minecraft:item_display,tag={DRUM_TAG},limit=1]"
    bridge_at = (  # the girder over the middle of the hold
        f"positioned {heart} at @e[type=minecraft:block_display,"
        f"tag={B_TAG},tag=!{T_TAG},sort=nearest,limit=1]"
    )

    def sound_at(where: str, name: str, pitch: float, when: str = "") -> str:
        return (
            f"execute {when + ' ' if when else ''}{where} run playsound "
            f"minecraft:{name} block {here} ~ ~ ~ {LOUD} {pitch}"
        )

    buzz = sound_at(hook_at, "block.note_block.bass", 0.5)  # refused

    def say(text: str, colour: str = "yellow") -> str:
        return f'tellraw {here} {{text:{fittings.snbt(text)},color:"{colour}"}}'

    def each_bay(name: str, score: str = "j") -> list[str]:
        """lines that run ``bay/<i>/<name>`` for the bay a score names"""
        return [call(f"bay/{i}/{name}", _is(score, i)) for i in range(len(BAYS))]

    def at_mid(i: int, h: float) -> str:
        u, v = bay_mid(i)
        return " ".join(_num(p) for p in point(fr, u, v, h))

    # -- weights: #cargo.w of the kind in #cargo.k
    fn(
        "weigh",
        [
            _set("w", 0),
            *(f"execute {_is('k', k)} run {_set('w', WEIGHT[k])}" for k in KINDS),
        ],
    )

    # -- each bay: its scores, its blocks and its checks
    for i in range(len(BAYS)):
        name = BAYS[i]
        n = f"b{i}.n"
        # push the kind in #cargo.k on top; pop the top into #cargo.k
        fn(
            f"bay/{i}/push",
            [
                *(
                    f"execute {_is(n, t)} run {_op(f'b{i}.t{t}', '=', 'k')}"
                    for t in range(TIERS)
                ),
                f"scoreboard players add {_s(n)} 1",
            ],
        )
        fn(
            f"bay/{i}/top",
            [
                _set("top", 0),
                *(
                    f"execute {_is(n, t + 1)} run {_op('top', '=', f'b{i}.t{t}')}"
                    for t in range(TIERS)
                ),
            ],
        )
        fn(
            f"bay/{i}/pop",
            [
                call(f"bay/{i}/top"),
                _op("k", "=", "top"),
                *(
                    f"execute {_is(n, t + 1)} run {_set(f'b{i}.t{t}', 0)}"
                    for t in range(TIERS)
                ),
                f"execute {_is(n, '1..')} run scoreboard players remove {_s(n)} 1",
            ],
        )
        # the blocks: a crate at a tier set (the kind in #cargo.k) or taken
        for t in range(TIERS):
            cells = bay_cells(i, t)
            fn(
                f"bay/{i}/set/{t}",
                [
                    f"execute {_is('k', k)} run {_fill(fr, cells, CRATE[k])}"
                    for k in KINDS
                ],
            )
            fn(f"bay/{i}/air/{t}", [_fill(fr, cells, AIR)])
            fn(
                f"bay/{i}/lift/{t}",
                [
                    *(
                        f"execute {_is('k', k)} run {line}"
                        for k in KINDS
                        for line in crate_summons(fr, i, t, k)
                    ),
                    _fill(fr, cells, AIR),
                ],
            )
        # the blocks of the whole bay from its scores
        fn(
            f"bay/{i}/show",
            [
                line
                for t in range(TIERS)
                for line in (
                    f"execute {_is(f'b{i}.t{t}', 0)} run {_fill(fr, bay_cells(i, t), AIR)}",
                    *(
                        f"execute {_is(f'b{i}.t{t}', k)} run {_fill(fr, bay_cells(i, t), CRATE[k])}"
                        for k in KINDS
                    ),
                )
            ],
        )
        # put the crate in #cargo.k on the bay (blocks, then scores); take
        # the top one off into #cargo.k (scores, then blocks)
        fn(
            f"bay/{i}/put",
            [
                *(call(f"bay/{i}/set/{t}", _is(n, t)) for t in range(TIERS)),
                call(f"bay/{i}/push"),
            ],
        )
        fn(
            f"bay/{i}/take",
            [
                call(f"bay/{i}/pop"),
                *(call(f"bay/{i}/air/{t}", _is(n, t)) for t in range(TIERS)),
            ],
        )
        # the tables' cells of this bay: the hold as it is (its fore half
        # dark in the duo form), and the plan on both plan tables
        hold = []
        if i >= 4:
            hold.append(
                f"execute {_is('form', 2)} run return run "
                + _fill(fr, [table_cell(HOLD_TABLE, i, t) for t in range(TIERS)], AIR)
            )
        for t in range(TIERS):
            cell = fr.at(*table_cell(HOLD_TABLE, i, t))
            hold.append(
                f"execute {_is(f'b{i}.t{t}', 0)} run setblock {_xyz(cell)} {AIR}"
            )
            hold += [
                f"execute {_is(f'b{i}.t{t}', k)} run setblock {_xyz(cell)} {CRATE[k]}"
                for k in KINDS
            ]
        fn(f"bay/{i}/table", hold)
        plan = []
        for table in (PLAN_TABLE, BOW_TABLE):
            for t in range(TIERS):
                cell = fr.at(*table_cell(table, i, t))
                plan.append(
                    f"execute {_is(f'g{i}.t{t}', 0)} run setblock {_xyz(cell)} {AIR}"
                )
                plan += [
                    f"execute {_is(f'g{i}.t{t}', k)} run setblock {_xyz(cell)} {CRATE[k]}"
                    for k in KINDS
                ]
        fn(f"bay/{i}/plan", plan)
        # stand clear: why 5 if anyone is in the column, and said
        fn(
            f"bay/{i}/clear",
            [
                f"execute if {column(fr, i)} run {_set('why', CLEAR)}",
                f"execute {_is('why', CLEAR)} run {say(f'Stand clear of bay {name}!', 'red')}",
                sound_at(
                    hook_at, "block.note_block.didgeridoo", 0.5, _is("why", CLEAR)
                ),
            ],
        )
        # HOOK DOWN over this bay: the reasons it may not go, then where to.
        # A crate on the hook goes on the top crate, an empty hook to it
        side = SIDE[i]
        fn(
            f"bay/{i}/check",
            [
                _set("why", 0),
                f"execute {_is('shut', i)} run {_set('why', SHUT)}",
                call(f"bay/{i}/top"),
                _op("k", "=", "top"),
                call("weigh"),
                _op("tw", "=", "w"),
                f"execute {_is('why', 0)} {_is('load', '1..')} {_is(n, f'{TIERS}..')} "
                f"run {_set('why', FULL)}",
                f"execute {_is('why', 0)} {_is('load', '1..')} {_is(n, '1..')} "
                f"if score {_s('tw')} < {_s('lw')} run {_set('why', CRUSH)}",
                # the trim after: a crate counts where it came from until set down
                _op("ta", "=", "trim"),
                _op("x", "=", "lw"),
                _op("x", "*=", "fs"),
                _op("ta", "-=", "x"),
                _op("ta", "+=" if side > 0 else "-=", "lw"),
                f"execute {_is('why', 0)} {_is('load', '1..')} "
                f"if score {_s('ta')} > {_s('lim')} run {_set('why', TRIM)}",
                f"execute {_is('why', 0)} {_is('load', '1..')} "
                f"if score {_s('ta')} < {_s('nlim')} run {_set('why', TRIM)}",
                call(f"bay/{i}/clear", _is("why", 0)),
                f"execute {_is('why', FULL)} run "
                + say(f"Bay {name} is full: three high is the most."),
                f"execute {_is('why', CRUSH)} run "
                + say("That would crush the crate under it. Never on a lighter one."),
                f"execute {_is('why', TRIM)} if score {_s('ta')} matches 1.. run "
                + say("She'd list too far to starboard. Keep the needle in the green."),
                f"execute {_is('why', TRIM)} if score {_s('ta')} matches ..-1 run "
                + say("She'd list too far to port. Keep the needle in the green."),
                f"execute {_is('why', SHUT)} run "
                + say(f"Bay {name}'s hatch is jammed."),
                # where the spreader stops: on the top crate, or a crate above it
                _op("to", "=", n),
                _op("to", "*=", "2"),
                "scoreboard players add " + _s("to") + " 1",
                f"execute {_is('load', '1..')} run scoreboard players add {_s('to')} 2",
            ],
        )
        # GRAB here: the top crate's blocks become displays on the hook
        fn(
            f"bay/{i}/grab",
            [
                call(f"bay/{i}/pop"),
                _op("load", "=", "k"),
                _set("from", i),
                _set("fs", side),
                *(call(f"bay/{i}/lift/{t}", _is(n, t)) for t in range(TIERS)),
                call(f"bay/{i}/table"),
            ],
        )
        # RELEASE here: displays to blocks at the top of the stack
        fn(
            f"bay/{i}/release",
            [
                _op("k", "=", "load"),
                call(f"bay/{i}/put"),
                f"kill @e[tag={CRATE_TAG}]",
                _set("to", i),
                call(f"bay/{i}/table"),
            ],
        )
        # the hook is right over this bay: on the top crate (grab), or with
        # a crate just on it (release)
        fn(
            f"bay/{i}/at",
            [
                _op("on", "=", n),
                _op("on", "*=", "2"),
                "scoreboard players add " + _s("on") + " 1",
            ],
        )
        fn(
            f"bay/{i}/name",
            [f'data modify storage {game.STORE} cargo.bay set value "{name}"'],
        )
        fn(
            f"bay/{i}/puff",
            [
                f"particle minecraft:cloud {at_mid(i, 3)} 0.8 1.5 0.8 0.02 40",
                f"particle minecraft:poof {at_mid(i, 2)} 0.8 1 0.8 0.02 20",
            ],
        )

    # -- the hold as a whole
    fn("show", [call(f"bay/{i}/show") for i in range(len(BAYS))])
    fn(
        "tables",
        [call(f"bay/{i}/{t}") for i in range(len(BAYS)) for t in ("table", "plan")],
    )
    fn(
        "trim/count",
        [
            _set("trim", 0),
            *(
                f"execute {_is(f'b{i}.t{t}', k)} run scoreboard players "
                f"{'add' if SIDE[i] > 0 else 'remove'} {_s('trim')} {WEIGHT[k]}"
                for i in range(len(BAYS))
                for t in range(TIERS)
                for k in KINDS
            ),
        ],
    )
    # the list gauges: the needles swing to the list (``trim/show``), the
    # scales' marks are green as far as the band's limit and red past it
    # (``trim/band``); a refused set-down kicks the needles to where she
    # would have gone, and the tick brings them back (``trim/flash``)
    needles = f"@e[type=minecraft:block_display,tag={NEEDLE_TAG}]"

    def needle_lines(score: str, ticks: int) -> list[str]:
        found = []
        for k in range(-GAUGE_STOP, GAUGE_STOP + 1):
            span = f"{k}" if abs(k) < GAUGE_STOP else (f"{k}.." if k > 0 else f"..{k}")
            found.append(
                f"execute {_is(score, span)} as {needles} run data merge entity @s "
                f"{{start_interpolation:0,interpolation_duration:{ticks},"
                f"{needle_pose(fr, k)}}}"
            )
        return found

    def zone_line(j: int, block: str, when: str = "") -> str:
        return (
            f"execute {when} as @e[type=minecraft:block_display,tag=st.cargo.z{j}] "
            f"run data merge entity @s {{block_state:{fittings.block_state(block)}}}"
        ).replace("execute  as", "execute as")

    fn("trim/show", needle_lines("trim", NEEDLE_TICKS))
    fn(
        "trim/band",
        [
            line
            for j in range(ZONES)
            for line in (
                zone_line(j, GREEN, _is("lim", f"{zone_limit(j)}..")),
                zone_line(j, RED, _is("lim", f"..{zone_limit(j) - 1}")),
            )
        ],
    )
    fn(
        "trim/flash",
        [_set("flash", FLASH_TICKS), *needle_lines("ta", 4), sound(CREAK, ROOM, 0.5)],
    )
    fn(
        "trim/party",
        [
            _set("party", PARTY_TICKS),
            *(zone_line(j, domes.LIGHT) for j in range(ZONES)),
        ],
    )
    # her timbers creak when she is within a ton of the limit
    fn(
        "trim/creak",
        [
            _op("near", "=", "lim"),
            f"scoreboard players remove {_s('near')} 1",
            _op("nnear", "=", "nlim"),
            f"scoreboard players add {_s('nnear')} 1",
            f"execute if score {_s('trim')} >= {_s('near')} run "
            + sound(CREAK, ROOM, 0.6),
            f"execute if score {_s('trim')} <= {_s('nnear')} run "
            + sound(CREAK, ROOM, 0.6),
        ],
    )
    # the stowage against the plan
    fn(
        "done",
        [
            _set("ok", 1),
            *(
                f"execute unless score {_s(f'b{i}.t{t}')} = {_s(f'g{i}.t{t}')} run {_set('ok', 0)}"
                for i in range(len(BAYS))
                for t in range(TIERS)
            ),
            f"execute {_is('ok', 1)} {_is('free', 0)} run {call('stowed')}",
        ],
    )
    fn(
        "stowed",
        [
            _set("free", 1),
            f"function {pack.id(f'dome/{INDEX}/solved')}",
            _set("bells", 3 * 8),
            call("trim/party"),
            f"particle minecraft:large_smoke {funnel} 0.4 1 0.4 0.05 80",
            call("board"),
        ],
    )

    # -- the undo ring: h<hi> = from * 8 + to, the last at hi - 1
    fn(
        "history/push",
        [
            _op("mv", "=", "from"),
            _op("mv", "*=", "8"),
            _op("mv", "+=", "to"),
            *(
                f"execute {_is('hi', k)} run {_op(f'h{k}', '=', 'mv')}"
                for k in range(HISTORY)
            ),
            "scoreboard players add " + _s("hi") + " 1",
            _op("hi", "%=", "30"),
            f"execute {_is('hn', f'..{HISTORY - 1}')} run scoreboard players add {_s('hn')} 1",
        ],
    )
    fn(
        "history/pop",
        [
            "scoreboard players add " + _s("hi") + f" {HISTORY - 1}",
            _op("hi", "%=", "30"),
            *(
                f"execute {_is('hi', k)} run {_op('mv', '=', f'h{k}')}"
                for k in range(HISTORY)
            ),
            "scoreboard players remove " + _s("hn") + " 1",
            _op("ua", "=", "mv"),
            _op("ua", "/=", "8"),
            _op("ub", "=", "mv"),
            _op("ub", "%=", "8"),
        ],
    )

    # -- the crane. Making it anew: every part killed (a crate on the hook
    # put back first), summoned at home, and moved to where row and col say
    fn(
        "crane/make",
        [
            call("putback/quiet", _is("load", "1..")),
            f"kill @e[tag={CRANE_TAG}]",
            *crane_summons(fr),
            f"execute {_is('row', 1)} as @e[tag={B_TAG}] at @s run "
            + _tp(fx * BRIDGE_TICKS / STEP, fz * BRIDGE_TICKS / STEP),
            *(
                f"execute {_is('col', c)} as @e[tag={T_TAG}] at @s run "
                + _tp(rx * 3 * c, rz * 3 * c)
                for c in (1, 2, 3)
            ),
            _op("rowto", "=", "row"),
            _op("colto", "=", "col"),
            *(
                _set(s, v)
                for s, v in (
                    ("hy", UP),
                    ("hyto", UP),
                    ("hp", 0),
                    ("hd", 0),
                    ("bp", 0),
                    ("bd", 0),
                    ("tp", 0),
                    ("td", 0),
                    ("down", 0),
                    ("wait", 0),
                )
            ),
        ],
    )
    fn(
        "crane/mend",
        [
            f"execute store result score {_s('parts')} if entity @e[tag={PART_TAG}]",
            call("crane/make", _not("parts", PARTS)),
        ],
    )
    # the hook: a quarter block a tick, a link at the top of each block
    # down and taken at the start of each block up; a descent waits over
    # anyone in the column
    fn(
        "crane/hook",
        [
            call("crane/hook/start", _is("hp", 0)),
            f"execute {_is('wait', 1)} run return 0",
            f"execute {_is('hd', 1)} as @e[tag={K_TAG}] at @s run "
            + _tp(0, 0, 1 / STEP),
            f"execute {_is('hd', -1)} as @e[tag={K_TAG}] at @s run "
            + _tp(0, 0, -1 / STEP),
            "scoreboard players add " + _s("hp") + " 1",
            call("crane/hook/block", _is("hp", f"{STEP}..")),
        ],
    )
    fn(
        "crane/hook/start",
        [
            _set("hd", 1),
            f"execute if score {_s('hyto')} < {_s('hy')} run {_set('hd', -1)}",
            _set("was", 0),
            f"execute {_is('wait', 1)} run {_set('was', 1)}",
            _set("wait", 0),
            *(
                f"execute {_is('hd', -1)} {_is('j', i)} if {column(fr, i)} run {_set('wait', 1)}"
                for i in range(len(BAYS))
            ),
            sound_at(
                hook_at,
                "block.note_block.didgeridoo",
                0.5,
                f"{_is('wait', 1)} {_is('was', 0)}",
            ),
            f"execute {_is('wait', 1)} {_is('was', 0)} run "
            + say("The hook waits: stand clear of the bay!", "red"),
            f"execute {_is('wait', 1)} run return 0",
            *(
                f"execute {_is('hd', -1)} {_is('hy', h)} run {link_summon(fr, h, True)}"
                for h in range(2, UP + 1)
            ),
            *(
                f"execute {_is('hd', 1)} {_is('hy', h)} run kill @e[tag=st.cargo.l{h + 1}]"
                for h in range(1, UP)
            ),
            sound_at(hook_at, "block.chain.place", 0.7, _is("hd", -1)),
            sound_at(hook_at, "block.chain.break", 0.7, _is("hd", 1)),
        ],
    )
    turns = [
        f"execute {_is('q', q)} run data merge entity "
        f"@e[type=minecraft:item_display,tag={DRUM_TAG},limit=1] "
        f"{{start_interpolation:0,interpolation_duration:{STEP},{drum_turn(fr, q)}}}"
        for q in range(4)
    ]
    fn(
        "crane/hook/block",
        [
            _set("hp", 0),
            _op("hy", "+=", "hd"),
            _op("q", "=", "hy"),
            _op("q", "%=", "4"),
            *turns,
            f"execute if score {_s('hy')} = {_s('hyto')} run {_set('hd', 0)}",
            sound_at(
                hook_at,
                "block.iron_door.close",
                0.8,
                f"if score {_s('hy')} = {_s('hyto')}",
            ),
        ],
    )
    # travel, only with the hook up and still: each glide keeps its way
    # to its end, however the buttons are pressed meanwhile
    along = (fx * 1 / STEP, fz * 1 / STEP)
    across = (rx * 1 / STEP, rz * 1 / STEP)
    fn(
        "crane/bridge",
        [
            f"execute {_is('bp', 0)} if score {_s('rowto')} > {_s('row')} run {_set('bd', 1)}",
            f"execute {_is('bp', 0)} if score {_s('rowto')} < {_s('row')} run {_set('bd', -1)}",
            sound_at(bridge_at, "entity.minecart.riding", 0.6, _is("bp", 0)),
            f"execute {_is('bd', 1)} as @e[tag={B_TAG}] at @s run " + _tp(*along),
            f"execute {_is('bd', -1)} as @e[tag={B_TAG}] at @s run "
            + _tp(-along[0], -along[1]),
            "scoreboard players add " + _s("bp") + " 1",
            f"execute {_is('bp', f'{BRIDGE_TICKS}..')} run {_op('row', '+=', 'bd')}",
            sound_at(
                bridge_at, "block.piston.contract", 0.5, _is("bp", f"{BRIDGE_TICKS}..")
            ),
            f"execute {_is('bp', f'{BRIDGE_TICKS}..')} run {_set('bp', 0)}",
        ],
    )
    fn(
        "crane/trolley",
        [
            f"execute {_is('tp', 0)} if score {_s('colto')} > {_s('col')} run {_set('td', 1)}",
            f"execute {_is('tp', 0)} if score {_s('colto')} < {_s('col')} run {_set('td', -1)}",
            sound_at(drum_at, "block.grindstone.use", 1.5, _is("tp", 0)),
            f"execute {_is('td', 1)} as @e[tag={T_TAG}] at @s run " + _tp(*across),
            f"execute {_is('td', -1)} as @e[tag={T_TAG}] at @s run "
            + _tp(-across[0], -across[1]),
            "scoreboard players add " + _s("tp") + " 1",
            f"execute {_is('tp', f'{TROLLEY_TICKS}..')} run {_op('col', '+=', 'td')}",
            f"execute {_is('tp', f'{TROLLEY_TICKS}..')} run {_set('tp', 0)}",
            sound_at(
                drum_at,
                "block.smithing_table.use",
                0.7,
                f"{_is('tp', 0)} if score {_s('col')} = {_s('colto')}",
            ),
        ],
    )
    fn(
        "crane/travel",
        [
            f"execute unless score {_s('hy')} matches {UP} run return 0",
            # each at most a step a tick: on its way, or sent
            _set("gob", 0),
            f"execute {_is('bp', '1..')} run {_set('gob', 1)}",
            f"execute unless score {_s('row')} = {_s('rowto')} run {_set('gob', 1)}",
            call("crane/bridge", _is("gob", 1)),
            _set("got", 0),
            f"execute {_is('tp', '1..')} run {_set('got', 1)}",
            f"execute unless score {_s('col')} = {_s('colto')} run {_set('got', 1)}",
            call("crane/trolley", _is("got", 1)),
        ],
    )
    # the tick's step: the hook if it is moving, else travel if sent, else
    # a DOWN that waited for the crane to stop
    fn(
        "crane/step",
        [
            _op("j", "=", "row"),
            _op("j", "*=", "4"),
            _op("j", "+=", "col"),
            _set("goh", 0),
            f"execute {_is('hp', '1..')} run {_set('goh', 1)}",
            f"execute unless score {_s('hy')} = {_s('hyto')} run {_set('goh', 1)}",
            call("crane/hook", _is("goh", 1)),
            call("crane/travel", f"{_is('goh', 0)}"),
            call("crane/waited", f"{_is('down', 1)}"),
        ],
    )
    fn(
        "crane/waited",
        [
            call("moving"),
            f"execute {_is('moving', 0)} run function {fid('press/down')}",
        ],
    )
    # moving: 1 while anything of the crane is on its way
    fn(
        "moving",
        [
            _set("moving", 0),
            f"execute {_is('hp', '1..')} run {_set('moving', 1)}",
            f"execute unless score {_s('hy')} = {_s('hyto')} run {_set('moving', 1)}",
            f"execute {_is('bp', '1..')} run {_set('moving', 1)}",
            f"execute {_is('tp', '1..')} run {_set('moving', 1)}",
            f"execute unless score {_s('row')} = {_s('rowto')} run {_set('moving', 1)}",
            f"execute unless score {_s('col')} = {_s('colto')} run {_set('moving', 1)}",
        ],
    )

    # -- the buttons
    clunk = sound("block.iron_trapdoor.close", ROOM, 0.5)
    travel = [_set("down", 0), _set("hyto", UP)]
    fn(
        "press/fore",
        [
            f"execute {_is('rowto', 1)} run return run {clunk}",
            _set("rowto", 1),
            *travel,
        ],
    )
    fn(
        "press/aft",
        [
            f"execute {_is('rowto', 0)} run return run {clunk}",
            _set("rowto", 0),
            *travel,
        ],
    )
    fn(
        "press/port",
        [
            f"execute {_is('colto', 0)} run return run {clunk}",
            f"scoreboard players remove {_s('colto')} 1",
            *travel,
        ],
    )
    fn(
        "press/starboard",
        [
            f"execute {_is('colto', 3)} run return run {clunk}",
            "scoreboard players add " + _s("colto") + " 1",
            *travel,
        ],
    )
    # DOWN: waits while the crane travels; refused with its reason
    fn(
        "press/down",
        [
            _set("down", 0),
            f"execute {_is('bp', '1..')} run return run {_set('down', 1)}",
            f"execute {_is('tp', '1..')} run return run {_set('down', 1)}",
            f"execute unless score {_s('row')} = {_s('rowto')} run return run {_set('down', 1)}",
            f"execute unless score {_s('col')} = {_s('colto')} run return run {_set('down', 1)}",
            _op("j", "=", "row"),
            _op("j", "*=", "4"),
            _op("j", "+=", "col"),
            _op("k", "=", "load"),
            call("weigh"),
            _op("lw", "=", "w"),
            *each_bay("check"),
            f"execute {_is('why', '1..')} run return run function {fid('refuse')}",
            _op("hyto", "=", "to"),
        ],
    )
    fn(
        "refuse",
        [
            buzz,
            call("trim/flash", _is("why", TRIM)),
        ],
    )
    fn("press/up", [_set("down", 0), _set("hyto", UP)])
    # GRAB and RELEASE: only with the hook still, down on a crate
    not_on = f"function {fid('not_on')}"
    fn("not_on", [say("The hook is not down on a crate."), buzz])
    fn(
        "press/grab",
        [
            _set("why", NOT_ON),
            call("moving"),
            *each_bay("at"),
            f"execute {_is('moving', 0)} {_is('load', 0)} {_not('hy', UP)} "
            f"if score {_s('hy')} = {_s('on')} {_not('on', 1)} run {_set('why', 0)}",
            f"execute {_is('why', NOT_ON)} run return run {not_on}",
            *each_bay("grab"),
            _set("hyto", UP),
            sound_at(hook_at, "block.anvil.place", 1.0),
            sound("block.fire.extinguish", ROOM, 1.2),
            f"particle minecraft:cloud {funnel} 0.3 0.5 0.3 0.02 12",
        ],
    )
    fn(
        "press/release",
        [
            _set("why", NOT_ON),
            call("moving"),
            *each_bay("at"),
            "scoreboard players add " + _s("on") + " 2",
            f"execute {_is('moving', 0)} {_is('load', '1..')} {_not('hy', UP)} "
            f"if score {_s('hy')} = {_s('on')} run {_set('why', 0)}",
            f"execute {_is('why', NOT_ON)} run return run {not_on}",
            *each_bay("clear"),
            f"execute {_is('why', CLEAR)} run return 0",
            *each_bay("release"),
            sound_at(hook_at, "block.wood.place", 0.6),
            sound_at(hook_at, "block.iron_trapdoor.open", 0.5),
            _set("load", 0),
            _set("hyto", UP),
            call("trim/count"),
            call("trim/show"),
            f"execute unless score {_s('from')} = {_s('to')} run function {fid('trim/creak')}",
            f"execute unless score {_s('from')} = {_s('to')} run function {fid('moved')}",
            *each_bay("table", "from"),
            sound("block.fire.extinguish", ROOM, 1.0),
            f"particle minecraft:cloud {funnel} 0.3 0.5 0.3 0.02 12",
            call("done"),
        ],
    )
    progress = [
        fittings.hint(pack, INDEX, name, text, secs)
        for name, (secs, text) in HINTS.items()
    ]
    fn(
        "moved",
        [
            "scoreboard players add " + _s("moves") + " 1",
            call("history/push"),
            progress[0].progress,
        ],
    )
    # UNDO: instant, a puff of steam; with a crate on the hook, it goes back
    wait = say("Wait for the crane to stop.")
    fn(
        "press/undo",
        [
            call("moving"),
            f"execute {_is('moving', 1)} run return run {wait}",
            f"execute {_is('load', '1..')} run return run function {fid('putback')}",
            f"execute {_not('hy', UP)} run return run "
            + say("Take the hook up first: HOOK UP."),
            f"execute {_is('hn', 0)} run return run " + say("Nothing to undo.", "gray"),
            _set("why", 0),
            call("history/peek"),
            *(
                call(f"bay/{i}/clear", f"{_is('why', 0)} {_is('ua', i)}")
                for i in range(len(BAYS))
            ),
            *(
                call(f"bay/{i}/clear", f"{_is('why', 0)} {_is('ub', i)}")
                for i in range(len(BAYS))
            ),
            f"execute {_is('why', CLEAR)} run return 0",
            call("history/pop"),
            *each_bay("take", "ub"),
            *each_bay("put", "ua"),
            f"scoreboard players remove {_s('moves')} 1",
            call("trim/count"),
            call("trim/show"),
            call("trim/creak"),
            *each_bay("table", "ua"),
            *each_bay("table", "ub"),
            *each_bay("puff", "ua"),
            *each_bay("puff", "ub"),
            sound("block.fire.extinguish", ROOM, 0.8),
        ],
    )
    # (which bays the last move was between, without taking it off the ring)
    fn(
        "history/peek",
        [
            _op("pk", "=", "hi"),
            "scoreboard players add " + _s("pk") + f" {HISTORY - 1}",
            _op("pk", "%=", "30"),
            *(
                f"execute {_is('pk', k)} run {_op('mv', '=', f'h{k}')}"
                for k in range(HISTORY)
            ),
            _op("ua", "=", "mv"),
            _op("ua", "/=", "8"),
            _op("ub", "=", "mv"),
            _op("ub", "%=", "8"),
        ],
    )
    # a crate on the hook back on the bay it came from, at once
    fn(
        "putback",
        [
            _set("why", 0),
            *(call(f"bay/{i}/clear", _is("from", i)) for i in range(len(BAYS))),
            f"execute {_is('why', CLEAR)} run return 0",
            call("putback/quiet"),
            *each_bay("puff", "from"),
            sound("block.fire.extinguish", ROOM, 0.8),
        ],
    )
    fn(
        "putback/quiet",
        [
            _op("k", "=", "load"),
            *each_bay("put", "from"),
            f"kill @e[tag={CRATE_TAG}]",
            _set("load", 0),
            _set("hyto", UP),
            call("trim/count"),
            call("trim/show"),
            *each_bay("table", "from"),
        ],
    )

    # -- RESET HOLD: the first pull asks, a second within 5 s does it
    lever_post = posts(fr)["RESET HOLD"]
    lever_cell = lever_post.input
    lever_off = lever_post.attached[lever_cell]
    fn(
        "lever",
        [
            *fittings.lever_put_lines(lever_cell, lever_off),
            f"execute {_is('ask', '1..')} run return run function {fid('reset/do')}",
            _set("ask", ASK_TICKS),
            say("RESET HOLD: pull again within 5 s to put every crate back."),
            sound("block.note_block.bell", ROOM, 0.8),
        ],
    )
    fn(
        "reset/do",
        [
            _set("ask", 0),
            _set("why", 0),
            *(call(f"bay/{i}/clear", _is("why", 0)) for i in range(len(BAYS))),
            f"execute {_is('why', CLEAR)} run return 0",
            f"kill @e[tag={CRATE_TAG}]",
            _set("load", 0),
            call("crane/make"),
            call("lay"),
            say("Every crate is back where it was.", "gray"),
            sound("block.fire.extinguish", ROOM, 0.6),
        ],
    )
    # -- laying a manifest: the band from the level in force, its scores
    lay = [
        f"scoreboard players operation {_s('band')} = #active {OBJ}",
        f"scoreboard players remove {_s('band')} 1",
        _op("band", "/=", "2"),
    ]
    for b in range(len(BANDS)):
        for m in range(3):
            fn(f"lay/{b}/{m + 1}", lay_lines(b, m))
            lay.append(call(f"lay/{b}/{m + 1}", f"{_is('band', b)} {_is('m', m + 1)}"))
    lay += [
        call("show"),
        call("tables"),
        call("trim/count"),
        call("trim/show"),
        call("trim/band"),
        call("hatch"),
        call("book"),
        call("docket"),
        _set("moves", 0),
        _set("hn", 0),
        _set("hi", 0),
        _set("load", 0),
    ]
    fn("lay", lay)
    # the jammed hatch over F1 at levels 9 and 10
    shut_bay = next(b.shut for b in BANDS if b.shut is not None)
    hatch = [fr.at(*c) for c in bay_cells(shut_bay, 0) if c[2] == 1]
    trapdoor = f"{HATCH}[facing={fr.facing(1, 0)},half=bottom,open=false]"
    fn(
        "hatch",
        [
            # only a trapdoor: F1's bottom crate, laid just before, stays
            *(
                f"execute if block {_xyz(c)} {HATCH} run setblock {_xyz(c)} {AIR}"
                for c in hatch
            ),
            fittings.text_line(JAM_TAG, '""'),
            f"execute {_is('shut', '0..')} run return run function {fid('hatch/on')}",
        ],
    )
    fn(
        "hatch/on",
        [
            *(f"setblock {_xyz(c)} {trapdoor}" for c in hatch),
            fittings.text_line(JAM_TAG, fittings.label_text("JAMMED", "red")),
        ],
    )
    # the log: page 4 is the manifest drawn
    lectern = fr.at(*LECTERN)
    for b in range(len(BANDS)):
        for m in range(3):
            fn(f"book/{b}/{m + 1}", [f"setblock {_xyz(lectern)} {logbook(fr, b, m)}"])
    fn("book/none", [f"setblock {_xyz(lectern)} {logbook(fr)}"])
    fn(
        "book",
        [
            call("book/none", _not("m", "1..3")),
            *(
                call(f"book/{b}/{m + 1}", f"{_is('band', b)} {_is('m', m + 1)}")
                for b in range(len(BANDS))
                for m in range(3)
            ),
        ],
    )
    fn(
        "docket",
        [
            fittings.text_line(
                DOCKET_TAG,
                fittings.label_text(
                    "TODAY'S MANIFEST:\nchosen when you come aboard", "white"
                ),
            ),
            *(
                f"execute {_is('m', m + 1)} run "
                + fittings.text_line(
                    DOCKET_TAG,
                    fittings.label_text(
                        f"TODAY'S MANIFEST: No. {m + 1}\n{MANIFEST_NAMES[m]}", "white"
                    ),
                )
                for m in range(3)
            ),
        ],
    )

    # -- the status board, rewritten twice a second
    board = fittings.display_selector(BOARD_TAG)
    store = f"storage {game.STORE} cargo"
    hook_says = [
        (f"{_is('hy', UP)}", "UP"),
        (f"{_not('hy', UP)} if score {_s('hy')} = {_s('hyto')}", "DOWN"),
        (f"if score {_s('hyto')} < {_s('hy')}", "GOING DOWN"),
        (f"if score {_s('hyto')} > {_s('hy')}", "GOING UP"),
        (f"{_is('wait', 1)}", "WAITING: STAND CLEAR"),
    ]
    fn(
        "board",
        [
            *each_bay("name"),
            *(
                f'execute {when} run data modify {store}.hook set value "{text}"'
                for when, text in hook_says
            ),
            f'data modify {store}.load set value "EMPTY"',
            *(
                f"execute {_is('load', k)} run data modify {store}.load set value "
                f'"{KIND_NAME[k].upper()} ON"'
                for k in KINDS
            ),
            f"execute store result {store}.moves int 1 run scoreboard players get {_s('moves')}",
            f'data modify {store}.list set value "LEVEL"',
            f"execute store result {store}.lim int 1 run scoreboard players get {_s('lim')}",
            *(
                f"execute {_is('trim', k)} run data modify {store}.list set value "
                + (
                    f'"LIST {abs(k)} {"PORT" if k < 0 else "STARBOARD"}"'
                    if k
                    else '"LEVEL"'
                )
                for k in range(-GAUGE_STOP + 1, GAUGE_STOP)
            ),
            f"execute {_is('free', 0)} run function {fid('board/write')} with {store}",
            f"execute {_is('free', 1)} run function {fid('board/stowed')} with {store}",
        ],
    )
    status = (
        '{text:"HOOK OVER $(bay)\\n",color:"gold"},'
        '{text:"$(hook), $(load)\\n",color:"yellow"},'
        '{text:"$(list) (LIMIT $(lim))\\n",color:"gold"},'
        '{text:"MOVES $(moves)",color:"yellow"}'
    )
    fn("board/write", [f"$data modify entity {board} text set value [{status}]"])
    fn(
        "board/stowed",
        [
            f"$data modify entity {board} text set value "
            f'[{{text:"STOWED. WELL DONE.\\n",color:"green"}},{status}]'
        ],
    )

    # -- the hooks
    hints = progress
    fn(
        "arm",
        [
            _set("live", 1),
            _set("free", 0),
            _set("row", 0),
            _set("col", 0),
            _set("form", 1),
            _set("want", 1),
            f"execute store result score {_s('m')} run random value 1..3",
            f"execute {_is('force', '1..3')} run {_op('m', '=', 'force')}",
            call("crane/make"),
            call("lay"),
            *(h.arm for h in hints),
        ],
    )
    fn(
        "enter",
        [
            call("arm", f"{_not('live', 1)}"),
            call("crane/mend"),
        ],
    )
    button_lines = []
    for name, post in posts(fr).items():
        if name == "RESET HOLD":
            continue
        path = f"{base}/button/{name.lower().replace(' ', '_')}"
        press = {"HOOK DOWN": "down", "HOOK UP": "up"}.get(name, name.lower())
        button_lines.append(
            fittings.button_line(
                pack,
                path,
                post.input,
                post.attached[post.input],
                [
                    sound("block.stone_button.click_on", 0.6, 1),
                    f"function {fid(f'press/{press}')}",
                ],
            )
        )
    smoke = f"particle minecraft:campfire_cosy_smoke {funnel} 0.1 0.2 0.1 0.01 1"
    fn(
        "tick",
        [
            # no arm here: a tick can run after ``reset/all`` before the scan
            # clears ``#occ``, and would arm at a stale level; ``enter`` arms
            f"execute unless block {_xyz(lectern)} minecraft:lectern[has_book=true] "
            f"run function {fid('book')}",
            *button_lines,
            f"execute if block {_xyz(lever_cell)} minecraft:lever[powered=true] "
            f"run function {fid('lever')}",
            call("crane/step"),
            call("moving"),
            f"execute {_is('moving', 1)} run {smoke}",
            # the form's safe point: between moves, the hook still and empty
            f"execute unless score {_s('form')} = {_s('want')} {_is('moving', 0)} "
            f"{_is('load', 0)} run function {fid('form/take')}",
            f"execute {_is('ask', '1..')} run scoreboard players remove {_s('ask')} 1",
            f"execute {_is('flash', '1..')} run scoreboard players remove {_s('flash')} 1",
            call("trim/show", _is("flash", 1)),
            f"execute {_is('party', '1..')} run scoreboard players remove {_s('party')} 1",
            call("trim/band", _is("party", 1)),
            call("bell", _is("bells", "1..")),
            *(
                f"execute {_is('free', 0)} {h.tick.removeprefix('execute ')}"
                for h in hints
            ),
            "scoreboard players add " + _s("clock") + " 1",
            f"execute {_is('clock', '10..')} run {_set('clock', 0)}",
            call("board", _is("clock", 0)),
        ],
    )
    fn(
        "bell",
        [
            f"scoreboard players remove {_s('bells')} 1",
            _op("bq", "=", "bells"),
            _op("bq", "%=", "8"),
            f"execute {_is('bq', 0)} run " + sound("block.bell.use", 2, BELL_PITCH),
        ],
    )
    dark = [
        fittings.text_line(
            DARK_TAG, fittings.label_text("FORE HOLD:\nASK THE BANKSMAN.", "red")
        )
    ]
    fn(
        "form/take",
        [
            _op("form", "=", "want"),
            *(call(f"bay/{i}/table") for i in range(4, len(BAYS))),
            fittings.text_line(DARK_TAG, '""'),
            *(f"execute {_is('form', 2)} run {line}" for line in dark),
        ],
    )
    fn("solo", [_set("want", 1)])
    fn("duo", [_set("want", 2)])
    fn(
        "empty",
        [
            call("putback/quiet", _is("load", "1..")),
            call("crane/make"),
            _set("ask", 0),
            _set("flash", 0),
            # a celebration cut short: the scales' colours back (no tick will)
            call("trim/band", _is("party", "1..")),
            _set("party", 0),
            _set("bells", 0),
            call("trim/show"),
            call("tables"),
            call("board"),
        ],
    )
    fn(
        "reset",
        [
            f"kill @e[tag={CRANE_TAG}]",
            *(_fill(fr, bay_cells(i), AIR) for i in range(len(BAYS))),
            *(
                _set(f"{p}{i}.t{t}", 0)
                for p in "bg"
                for i in range(len(BAYS))
                for t in range(TIERS)
            ),
            *(_set(f"b{i}.n", 0) for i in range(len(BAYS))),
            *(
                _set(s, v)
                for s, v in (
                    ("live", 0),
                    ("free", 0),
                    ("load", 0),
                    ("from", 0),
                    ("row", 0),
                    ("col", 0),
                    ("form", 1),
                    ("want", 1),
                    ("moves", 0),
                    ("hn", 0),
                    ("hi", 0),
                    ("ask", 0),
                    ("flash", 0),
                    ("party", 0),
                    ("bells", 0),
                    ("trim", 0),
                    ("why", 0),
                    ("m", 0),
                    ("band", 2),
                    ("lim", 2),
                    ("nlim", -2),
                    ("shut", -1),
                    ("clock", 0),
                )
            ),
            call("crane/make"),
            call("tables"),
            call("trim/show"),
            call("trim/band"),
            call("hatch"),
            call("book"),
            call("docket"),
            fittings.text_line(DARK_TAG, '""'),
            *fittings.lever_put_lines(lever_cell, lever_off),
            call("board"),
        ],
    )


def summons(dome: Dome) -> list[str]:
    """the commands that summon the room's entities but the crane (which
    the pack makes: ``crane/make``): the labels over the inputs, the bay
    names, the list gauges and their words on the deckhouse, the status board, the
    docket and legend, the tables' titles and the dark table's notice,
    the jammed hatch's label, her name, the recall button's interaction"""
    fr = frame(dome)
    yaws = {"south": 0, "west": 90, "north": 180, "east": -90}
    found = []

    def text(
        u: float,
        v: float,
        h: float,
        way: tuple[int, int],
        words: str,
        tags: tuple[str, ...] = (),
        colour: str = "white",
        scale: float = 1,
        billboard: str = "fixed",
    ) -> None:
        pos = point(fr, u, v, h)
        label = fittings.label_text(words, colour) if words else '""'
        yaw = yaws[fr.facing(*way)]
        found.append(
            fittings.display((ENTITY_TAG, *tags), pos, yaw, label, scale, billboard)
        )

    for post in posts(fr).values():
        found += post.summons
    # the bays' names along the deckhouse's eaves, over their columns
    for i, name in enumerate(BAYS):
        u, v = bay_mid(i)
        face = HOUSE_F[0] - 0.02 if i < 4 else HOUSE_F[1] + 1.02
        way = (-1, 0) if i < 4 else (1, 0)
        text(face, v, HOUSE_TOP + 1.05, way, name, colour="gold", scale=1.2)
    for side, way in ((-1, (-1, 0)), (1, (1, 0))):
        face = gauge_face(side, 0.02)
        text(face, 0.5, GAUGE_PIVOT + 0.6, way, "LIST", colour="black", scale=1.0)
        # port (r < 0) and starboard are the ship's on both faces
        text(face, -3.7, HOUSE_TOP - 0.9, way, "PORT", scale=0.6)
        text(face, 4.8, HOUSE_TOP - 0.9, way, "STARBOARD", scale=0.6)
    found += gauge_summons(fr)
    # the status board over the pulpit's screen, facing the driver, behind
    # the screen's clear window
    text(PULPIT_F[1] + 0.6, 0.5, 9.4, (-1, 0), "", (BOARD_TAG,), scale=1.2)
    # the docket and the legend on her stern, over the plaque
    stern = PULPIT_F[0] - 0.02
    text(stern, 0.5, 3.1, (-1, 0), "", (DOCKET_TAG,), scale=0.7)
    text(
        stern,
        0.5,
        4.2,
        (-1, 0),
        "IRON 3 tons. BARREL 2. BALE 1.",
        colour="gold",
        scale=0.7,
    )
    for table, words in ((PLAN_TABLE, "MANIFEST"), (HOLD_TABLE, "THE HOLD NOW")):
        f, r, h = table
        text(f + 1.0, r + 2.0, 9.2, (-1, 0), words, colour="gold", scale=0.7)
    f, r, h = BOW_TABLE
    text(f + 1.0, r + 4.1, 9.2, (0, 1), "MANIFEST", colour="gold", scale=0.7)
    f, r, h = HOLD_TABLE
    # (a block nearer the driver than the title over it: there the table hid it)
    text(f, r + 2.0, 6.6, (-1, 0), "", (DARK_TAG,), scale=0.6)
    u, v = bay_mid(next(b.shut for b in BANDS if b.shut is not None))
    text(u, v, 3.0, (-1, 0), "", (JAM_TAG,), scale=1.2, billboard="center")
    # her name on the bow, both sides, where her side is still straight
    for side in (-1, 1):
        text(
            11.5,
            side * 7.52 + (0.5 if side > 0 else 0.5),
            3.4,
            (0, side),
            "MARIGOLD",
            colour="gold",
            scale=1.4,
        )
    found.append(fittings.summon_recall(fr, *RECALL, tags=(ENTITY_TAG,)))
    return found


# ------------------------------------------------------ the offline checks

domes.allow(INDEX, "window", "the lighter lies between the doors")
# the basin is water let into the floor: ``afloat_problems`` and the live
# check look after those cells, the shell's check for holes leaves them;
# and the landing steps: the game lets the basin's water into a step
# beside it (it is laid dry, but stands waterlogged a tick later)
_fr = frame(layout.DOMES[INDEX])
domes.add_opening(
    INDEX, basin(layout.DOMES[INDEX]) | {_fr.at(f, r, 0) for f, r in LANDINGS}
)


def over_water(dome: Dome) -> set[Cell]:
    """the cells just over the basin: nobody stands there"""
    return {(x, y + 1, z) for x, y, z in basin(dome)}


def walks(dome: Dome) -> dict[str, Cell]:
    """where a player must be able to get to from the entrance (the cell
    the feet are in)"""
    fr = frame(dome)
    lf, lr, _ = LECTERN
    places: dict[str, Place] = {
        "the driver's place": DRIVER,
        "the driver's place behind": DRIVER_BACK,
        "the RESET HOLD lever": (LEVER_AT[0] + 1, LEVER_AT[1] + 1, 6),
        "the plan table": (PLAN_TABLE[0] - 1, PLAN_TABLE[1] + 1, 6),
        "the hold table": (HOLD_TABLE[0] - 1, HOLD_TABLE[1] + 2, 6),
        "the bow": BANKSMAN,
        "the bow's table": (BOW_TABLE[0] + 2, BOW_TABLE[1] + 2, 6),
        "the fore hold's floor": (6, 0, 1),
        "the port gantry walk": (0, -11, WALK_H + 1),
        "the starboard gantry walk": (0, 11, WALK_H + 1),
        "the logbook": (lf - 1, lr, 1),
        "the plaque": (PLAQUE[0] - 2, PLAQUE[1], 1),
        "the donkey engine": (DONKEY[0], DONKEY[1] + 4, 1),
    }
    targets = {name: fr.at(*at) for name, at in places.items()}
    tunnel = layout.TUNNELS[dome.index]
    lx, ly, lz = tunnels.lever_cell(tunnel)
    ux, uz = domes.outward(dome, tunnel)
    targets["the pump lever"] = (lx - ux, ly - 1, lz - uz)
    return targets


def reach(dome: Dome, b: Blocks, extra: dict[Cell, str] | None = None) -> set[Cell]:
    """where a player's feet can get to from the entrance, dry: nobody
    stands on bars, a rail, the screen or a lantern, and nobody has to
    wade the basin"""
    solid = {**b.solid, **(extra or {})}
    blocked = set(solid) | {
        c for c, block in b.attached.items() if "lantern" in block or "bell" in block
    }
    blocked |= {(x, y + 1, z) for (x, y, z), block in solid.items() if block in RAILS}
    blocked |= over_water(dome)
    return rooms.reach(dome, domes.entrance(dome)[:3], solid, blocked)


RAILS = (BARS, PANE, BARRIER)  # what nobody stands on


def ladders(b: Blocks) -> set[Cell]:
    return {c for c, block in b.attached.items() if "ladder" in block}


def roam(
    dome: Dome,
    b: Blocks,
    extra: dict[Cell, str] | None = None,
    start: Cell | None = None,
) -> set[Cell]:
    """where a player's feet can get to from the entrance (or ``start``)
    as ``reach``, and also by slipping diagonally between two bars that do
    not join, by standing on bars, by climbing a ladder, and by stepping
    off any edge (and a block aside on the way down): for the places
    nobody must get to. The basin is taken as floor: whoever wades it is
    a block lower than this has them, and gets to no more"""
    solid = {**b.solid, **(extra or {})}
    rungs = ladders(b)
    full = set(solid) | {
        c for c, block in b.attached.items() if "lantern" in block or "bell" in block
    }
    cells = domes.dome_cells(dome)
    ground = set(cells.floor) | set(solid)
    sides = ((1, 0), (-1, 0), (0, 1), (0, -1))

    def free(c: Cell) -> bool:
        x, y, z = c
        return c in cells.interior and c not in full and (x, y + 1, z) not in full

    def bars(c: Cell) -> bool:
        x, y, z = c
        return solid.get(c) == BARS and solid.get((x, y + 1, z)) == BARS

    def drop(c: Cell) -> Cell:
        x, y, z = c
        while (x, y - 1, z) not in ground and (x, y, z) not in rungs:
            y -= 1
        return (x, y, z)

    def moves(c: Cell):
        x, y, z = c
        if c in rungs and free((x, y + 1, z)):
            yield (x, y + 1, z)
        for dx, dz in sides:
            for dy in (0, 1):
                to = (x + dx, y + dy, z + dz)
                if free(to) and (not dy or free((x, y + 1, z))):
                    yield to
                    break
        for dx, dz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            to = (x + dx, y, z + dz)
            if free(to) and bars((x + dx, y, z)) and bars((x, y, z + dz)):
                yield to

    start = start or domes.entrance(dome)[:3]
    seen, edge = {start}, [start]
    while edge:
        for to in moves(edge.pop()):
            x, y, z = to
            landed = {drop(to)}
            if (x, y - 1, z) not in ground:
                aside = ((x + dx, y, z + dz) for dx, dz in sides)
                landed |= {drop(a) for a in aside if free(a)}
            for land in landed - seen:
                seen.add(land)
                edge.append(land)
    return seen


def walk_problems(dome: Dome) -> list[str]:
    seen = reach(dome, room_blocks(dome))
    return [
        f"no walk from the entrance to {name} at {cell}"
        for name, cell in walks(dome).items()
        if cell not in seen
    ]


def _eye_hidden(
    eye: tuple[float, float, float], target: Cell, opaque: set[Cell]
) -> bool:
    """is anything opaque on the line from an eye (a point) to the middle
    of a cell (as ``rooms.hidden``, from any height)"""
    to = (target[0] + 0.5, target[1] + 0.5, target[2] + 0.5)
    steps = max(1, int(math.dist(eye, to) * 8))
    for i in range(steps):
        cell = tuple(
            math.floor(eye[k] + (to[k] - eye[k]) * i / steps) for k in range(3)
        )
        if cell in opaque and cell != target:
            return True
    return False


def sight_problems(dome: Dome) -> list[str]:
    """the driver sees the aft hold from the platform's two vantage
    points: low by the keys (the eye ``DRIVER_EYE`` up, a step forward
    from ``DRIVER``) every cell of every aft bay, the aft list gauge's
    plate and the trolley at both stops; high behind (``DRIVER_BACK``,
    the eye ``DRIVER_BACK_EYE`` up) the same but the bottom crate of each
    aft bay, which the deck's edge hides. From both, the top two rows of
    the plate over an aft hold stowed three high. The banksman every fore
    bay cell and the fore gauge; the gantry walk every bay (each from
    where it stands)"""
    fr = frame(dome)
    # a key lies flat on the deck: it hides nothing
    blocks = {
        c: b for c, b in room_blocks(dome).above().items() if not rooms.is_input(b)
    }
    c, vc = home()

    def trolley(row: int) -> dict[str, Cell]:
        return {
            f"the trolley over {BAYS[row * 4 + col]}": fr.at(
                math.floor(bay_mid(row * 4)[0]), math.floor(bay_mid(col)[1]), 15
            )
            for col in range(4)
        }

    def bays(rows) -> dict[str, Cell]:
        return {
            f"{BAYS[i]} at {p}": fr.at(*p)
            for i in range(len(BAYS))
            if i // 4 in rows
            for p in bay_cells(i)
        }

    def gauge(face: int) -> dict[str, Cell]:
        return {f"the list gauge at {p}": fr.at(*p) for p in gauge_cells(face)}

    clear = rooms.opaque(blocks)
    full = clear | {fr.at(*p) for i in range(4) for p in bay_cells(i)}
    bottom = {fr.at(*p) for i in range(4) for p in bay_cells(i, 0)}
    problems: list[str] = []
    for where, eye, hidden_ok in (
        ("by the keys", point(fr, DRIVER[0] + 1.5, DRIVER[1] + 0.5, DRIVER_EYE), set()),
        (
            "behind",
            point(fr, DRIVER_BACK[0] + 0.5, DRIVER_BACK[1] + 0.5, DRIVER_BACK_EYE),
            bottom,
        ),
    ):
        problems += [
            f"{what} is hidden from the driver {where}"
            for what, cell in {
                **bays((0,)),
                **gauge(-1),
                **trolley(0),
                **trolley(1),
            }.items()
            if cell not in hidden_ok and _eye_hidden(eye, cell, clear)
        ]
        problems += [
            f"the list gauge at {p} is hidden from the driver {where} by a full aft hold"
            for p in gauge_cells(-1)
            if p[2] >= HOUSE_TOP - 1 and _eye_hidden(eye, fr.at(*p), full)
        ]
    problems += rooms.sight_problems(
        blocks, {"the banksman": fr.at(*BANKSMAN)}, {**bays((1,)), **gauge(1)}
    )
    # from the gantry walk beside each row, every bay's floor from one side
    # or the other (the ship's side hides the nearest from straight above)
    solid = rooms.opaque(blocks)
    for row in (0, 1):
        f = BAY_F[row][0]
        eyes = [fr.at(f, 11 * side, WALK_H + 1) for side in (-1, 1)]
        for i in range(4 * row, 4 * row + 4):
            for p in bay_cells(i, 0):
                if p[2] == 1 and all(rooms.hidden(e, fr.at(*p), solid) for e in eyes):
                    problems.append(
                        f"{BAYS[i]}'s floor at {p} is hidden from the gantry walk"
                    )
    return problems


#: heights of the eye above the cell the feet are in: standing, jumping
EYES = (1.62, 1.62 + 1.25)


def blind_problems(dome: Dome) -> list[str]:
    """the deckhouse hides each hold from the other end: from wherever a
    player can stand on the pulpit (the tables climbed too), standing or
    jumping, no cell of a fore bay is in sight; from the bow none of an
    aft bay. The tables are taken full and in steps, to be climbed"""
    fr = frame(dome)
    b = room_blocks(dome)
    blocks = b.above()
    solid = rooms.opaque(blocks)
    steps = {}
    for table in (PLAN_TABLE, HOLD_TABLE, BOW_TABLE):
        for i in range(len(BAYS)):
            for t in range(1 + i % TIERS):
                steps[fr.at(*table_cell(table, i, t))] = CRATE[IRON]
    seen = reach(dome, b, steps)
    problems = []
    for end, fs, rows in (
        ("the pulpit", range(PULPIT_F[0], PULPIT_F[1] + 1), (1,)),
        ("the bow", range(11, 17), (0,)),
    ):
        feet = [c for c in seen if any(c == fr.at(f, r, c[1] - dome.floor_y)
                for f in fs for r in range(-9, 10)) and c[1] - dome.floor_y >= DECK_H + 1]  # fmt: skip
        targets = [
            fr.at(*p) for i in range(len(BAYS)) if i // 4 in rows for p in bay_cells(i)
        ]
        opaque = solid | set(steps)
        for x, y, z in feet:
            for up in EYES:
                head = y + up + (1.8 - 1.62)
                if (x, math.floor(head), z) in solid and up > 1.62:
                    continue  # no room to jump
                eye = (x + 0.5, y + up, z + 0.5)
                for cell in targets:
                    if not _eye_hidden(eye, cell, opaque):
                        problems.append(
                            f"from {end} at {(x, y, z)} (eye {up}) {cell} is in sight"
                        )
                        break
                else:
                    continue
                break
    return problems[:8]


def trap_problems(dome: Dome) -> list[str]:
    """nobody gets onto a crate, the deckhouse's roof or the pulpit's
    canopy, or into the aft hold: with every bay one, two or three crates
    high and the pulpit's tables full, in steps, to be climbed (not the
    bow's: the fore hold is walked in anyway), none of them is a
    place to get to, even by a drop or a slip between bars (``roam``); nor
    is a crate's top for whoever is in the aft hold all the same, by its
    ladder; and with every bay empty, every cell of the hold floor leads
    back to the entrance (``rooms.reach``, with the ladder and the drop
    from its notch into the basin)"""
    fr = frame(dome)
    b = room_blocks(dome)
    problems = []
    roof = {
        fr.at(f, r, HOUSE_TOP + 1)
        for f in range(HOUSE_F[0], HOUSE_F[1] + 1)
        for r in range(-HOUSE_R, HOUSE_R + 1)
    } | {
        fr.at(f, r, 11) for f in range(PULPIT_F[0], PULPIT_F[1]) for r in range(-9, 10)
    }
    floor = {fr.at(f, r, 1) for f, r in hold_floor()}
    aft = {fr.at(f, r, 1) for f, r in hold_floor() if f < 0}
    tables = {
        fr.at(*table_cell(table, i, t)): CRATE[IRON]
        for table in (PLAN_TABLE, HOLD_TABLE)
        for i in range(len(BAYS))
        for t in range(1 + i % TIERS)
    }
    for n in range(1, TIERS + 1):
        crates = {
            fr.at(*p): CRATE[IRON]
            for i in range(len(BAYS))
            for t in range(n)
            for p in bay_cells(i, t)
        }
        seen = roam(dome, b, {**crates, **tables})
        # every cell over the crates, up to the feet over a full bay
        tops = {
            fr.at(f, r, h)
            for i in range(len(BAYS))
            for f, r, _ in bay_cells(i, 0)
            for h in range(2 * n + 1, 2 * TIERS + 2)
        }
        if on := seen & (tops | roof):
            problems.append(
                f"{n} high: {len(on)} cells on the crates or the roof, as {min(on)}"
            )
        if on := seen & aft:
            problems.append(f"{n} high: a way into the aft hold, to {min(on)}")
        inside = roam(dome, b, crates, fr.at(AFT_LADDER[0], AFT_LADDER[1] - 1, 1))
        if on := inside & tops:
            problems.append(
                f"{n} high: {len(on)} cells on the crates from the aft hold, "
                f"as {min(on)}"
            )
    start = domes.entrance(dome)[:3]
    blocked = set(b.solid) | {
        (x, y + 1, z) for (x, y, z), k in b.solid.items() if k in RAILS
    }
    wet = basin(dome)
    stuck = [
        c
        for c in sorted(floor)
        if start
        not in rooms.reach(dome, c, b.solid, blocked, ladders(b), drop=3, water=wet)
    ]
    if stuck:
        problems.append(
            f"{len(stuck)} cells of the hold floor with no way out, as {stuck[0]}"
        )
    return problems


def afloat_problems(dome: Dome) -> list[str]:
    """the basin holds and lets go: every cell of it is in the dome's
    floor with a bed under it, and has beside it only more of the basin
    or a block of the floor (the plan's, or the dome's own), so the water
    has nowhere to run; nothing of the room is waterlogged or stands on
    the water; and whoever is in it, anywhere, can wade and step out and
    walk back to the entrance"""
    fr = frame(dome)
    b = room_blocks(dome)
    wet = basin(dome)
    in_floor = domes.dome_cells(dome).floor
    problems = []
    if stray := wet - in_floor:
        problems.append(f"{len(stray)} cells of the basin not in the floor")
    if bare := {(x, y - 1, z) for x, y, z in wet} - set(b.bed):
        problems.append(f"{len(bare)} cells of the basin with no bed: {min(bare)}")
    if any(b.floor.get(c) != WATER for c in wet):
        problems.append("a cell of the basin is not water")
    if spilt := {c for c, block in b.everything().items() if block == WATER} - wet:
        problems.append(f"{len(spilt)} cells of water outside the basin")
    open_to = {
        (x + dx, y, z + dz)
        for x, y, z in wet
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
    } - wet
    if leak := {c for c in open_to if c not in in_floor}:
        problems.append(f"the basin is open at {min(leak)}")
    if on := over_water(dome) & set(b.above()):
        problems.append(f"{len(on)} blocks stand on the water, as {min(on)}")
    blocked = set(b.solid) | {
        (x, y + 1, z) for (x, y, z), k in b.solid.items() if k in RAILS
    }
    start = domes.entrance(dome)[:3]
    out = rooms.reach(dome, start, b.solid, blocked, water=wet)
    if missed := wet - out:
        problems.append(f"{len(missed)} cells of the basin not fallen into")
    # (walking is the same both ways but for a drop: so each cell's own way)
    held = [
        c
        for c in sorted(wet)
        if start not in rooms.reach(dome, c, b.solid, blocked, water=wet)
    ]
    if held:
        problems.append(f"{len(held)} cells of the basin with no way out: {held[0]}")
    if len(LANDINGS) != len({fr.at(f, r, 0) for f, r in LANDINGS} & set(b.floor)):
        problems.append("a landing step is missing")
    return problems


def dressing_problems(dome: Dome) -> list[str]:
    """none of the four crates' blocks anywhere but the bays and tables"""
    b = room_blocks(dome)
    crate_names = {rooms.name(block) for block in CRATE.values()}
    allowed = dressing_cells(dome)
    bad = [
        c
        for c, block in b.everything().items()
        if rooms.name(block) in crate_names and c not in allowed
    ]
    return [f"{len(bad)} crate blocks in the dressing, as {min(bad)}"] if bad else []


def crane_problems(dome: Dome) -> list[str]:
    """every cell any part of the crane is ever in is inside the dome, off
    the reserved cells, and not in a block of the room"""
    fr = frame(dome)
    cells = crane_places(fr)
    problems = fittings.placement_problems(dome, cells)
    b = room_blocks(dome)
    taken = cells & set(b.above()) - b.clear
    if taken:
        problems.append(
            f"{len(taken)} cells of the crane's way in blocks, as {min(taken)}"
        )
    return problems


def gantry_problems(dome: Dome) -> list[str]:
    """two clear blocks over each way in and over the entrance spot, and
    nothing at all over the pump engine, whose chimney steams"""
    used = set(room_blocks(dome).above())
    reserved = tunnels.reserved_cells(dome)
    engine = set(tunnels.engine_cells(layout.TUNNELS[dome.index]).values())
    over = {(x, y + up, z) for x, y, z in reserved for up in (1, 2)} - reserved
    over |= {(x, y + up, z) for x, y, z in engine for up in range(1, dome.radius)}
    bad = over & used
    return [f"{len(bad)} blocks over reserved cells: {min(bad)}"] if bad else []


def room_problems(dome: Dome) -> list[str]:
    """everything the build asks of the plan before it places a block"""
    b = room_blocks(dome)
    problems = rooms.room_problems(dome, b.above(), b.floor, b.clear)
    # a key has no sign: its name is written on its own brass (``key``)
    made = posts(frame(dome))
    unsigned = {
        f"the input at {made[name].input} has no sign by it"
        for name in (*TRAVEL, *HOOK)
    }
    problems += [
        p
        for p in rooms.input_problems(b.above(), inputs(dome), floor=b.floor)
        if p not in unsigned
    ]
    if set(b.floor) & set(b.above()) or set(b.solid) & set(b.attached):
        problems.append("a cell is given two blocks")
    problems += rooms.window_problems(dome, b.above())
    problems += gantry_problems(dome) + crane_problems(dome)
    problems += walk_problems(dome) + sight_problems(dome) + blind_problems(dome)
    problems += trap_problems(dome) + afloat_problems(dome) + dressing_problems(dome)
    return problems + manifest_problems()


# --------------------------------------------------------------- the build


def build(ctx: Any) -> str:
    """the Cargo Hold inside its shell, in place of the stub; wipes what
    was inside but the pump engine, and leaves the room as ``reset``
    does. Plain blocks go by ``fill``, so that the bars join up"""
    dome = ctx.layout.DOMES[INDEX]
    if problems := room_problems(dome):
        raise RuntimeError("the Cargo Hold: " + "; ".join(problems[:12]))
    fr = frame(dome)
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    engine = set(tunnels.engine_cells(ctx.layout.TUNNELS[INDEX]).values())
    for command in game.clear_stub_commands(dome):
        ctx.cmd(command)
    ctx.cmd(f"kill @e[tag={ENTITY_TAG}]")
    ctx.fill_boxes(cells.interior - engine, AIR)
    lectern = fr.at(*LECTERN)
    # the basin's bed before its water, and her bottom and the dock walks
    # before it too (``fill_boxes`` goes block by block, water after stone)
    for block, where in sorted(domes.by_block(b.bed).items()):
        ctx.fill_boxes(where, block)
    for part in (b.floor, b.solid):
        plain = {c: block for c, block in part.items() if "{" not in block}
        for block, where in sorted(domes.by_block(plain).items()):
            ctx.fill_boxes(where, block)
        for cell, block in sorted(part.items()):
            if cell not in plain and cell != lectern:
                ctx.setblock(cell, block)
    # the log's lectern, with a short book: the pack's reset writes it whole
    ctx.setblock(lectern, f"minecraft:lectern[facing={fr.facing(-1, 0)}]")
    for cell, block in sorted(b.attached.items()):
        ctx.setblock(cell, block)
    for command in summons(dome):
        ctx.cmd(command)
    # the pack's own idea of the room, if the pack is installed: the crane,
    # the log, the lamps
    ctx.function(f"dome/{INDEX}/reset")
    ctx.advance(10)
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    return (
        f"{dome.name}: {len(b.everything())} blocks: the Marigold afloat "
        f"in {len(basin(dome))} of water, with her "
        "deckhouse, pulpit and bow, the gantry and its walk, the dock, the "
        "donkey engine and the sea gate, plaque, logbook, recall button"
    )


# --------------------------------------------------------------- the check

S1, S2 = "st.cargo.s1", "st.cargo.s2"  # the check's stand-ins


def check(ctx: Any) -> list[str]:
    """
    The Cargo Hold over RCON, with stand-ins (armour stands the core counts
    as players), working the room through its buttons and its functions.
    Leaves the game reset and no stand-in behind.

    It does not prove what a player sees: the glide's look, the chain, the
    tables and the list gauge read at a distance, the needle's swing, the
    water round her, the blind half, the sounds and titles (all on the
    owner's play-test list); nor that a player gets out of the basin (the
    offline ``afloat_problems`` walks it).
    """
    game_checks.no_run(ctx)
    saved = game_checks.save_level(ctx)
    try:
        return _check(ctx)
    finally:
        for tag in (S1, S2):
            ctx.cmd(f"kill @e[tag={tag}]")
        ctx.set_score("#cargo.force", 0)
        game_checks.restore_level(ctx, saved)
        ctx.function("reset/all")
        ctx.advance(game_checks.SCAN)


def _check(ctx: Any) -> list[str]:
    dome = layout.DOMES[INDEX]
    fr = frame(dome)
    base = f"dome/{INDEX}"
    problems: list[str] = []

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def get(name: str) -> int | None:
        return ctx.score(f"#cargo.{name}")

    eye_x, eye_y, eye_z = (
        _num(p) for p in point(fr, DRIVER[0] + 0.5, DRIVER[1] + 0.5, DRIVER_EYE)
    )

    def run(name: str) -> None:
        ctx.function(f"{base}/{name}")

    def count(tag: str) -> int:
        return ctx.count(f"@e[tag={tag}]")

    def pos(tag: str) -> tuple[float, ...] | None:
        got = ctx.data(f"entity @e[tag={tag},limit=1] Pos")
        found = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?(?=d)", got)]
        return tuple(found) if len(found) == 3 else None

    def needle() -> int | None:
        """the list the aft gauge's needle points at (where it is going),
        in tons, from its turn about the way she points"""
        got = ctx.data(
            f"entity @e[tag={NEEDLE_TAG},limit=1,sort=nearest,"
            f"x={eye_x},y={eye_y},z={eye_z}] transformation.left_rotation"
        )
        q = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?(?=f)", got)]
        if len(q) != 4:
            return None
        along = q[0] * fr.right[1] - q[2] * fr.right[0]
        return round(math.degrees(2 * math.atan2(along, q[3])) / GAUGE_STEP)

    def zones() -> list[bool | None]:
        """each mark of the scale: green (True), red, or neither"""
        found: list[bool | None] = []
        for j in range(ZONES):
            got = ctx.data(f"entity @e[tag=st.cargo.z{j},limit=1] block_state")
            found.append(
                True if rooms.name(GREEN) in got else False if RED in got else None
            )
        return found

    def band(limit: int) -> list[bool | None]:
        return [zone_limit(j) <= limit for j in range(ZONES)]

    def settle(limit: int = 40) -> bool:
        """let the crane come to rest (``moving`` 0, no DOWN waiting)"""
        for _ in range(limit):
            ctx.advance(10)
            if get("moving") == 0 and get("down") == 0:
                return True
        return False

    def hold() -> Stacks:
        """the hold as the scores have it"""
        found = []
        for i in range(len(BAYS)):
            n = get(f"b{i}.n") or 0
            found.append(tuple(get(f"b{i}.t{t}") or 0 for t in range(n)))
        return tuple(found)

    def blocks_are(stacks: Stacks) -> bool:
        """each bay's blocks as the stacks say: a cell of each crate, and
        air over the top"""
        for i, stack in enumerate(stacks):
            for t in range(TIERS):
                cell = fr.at(*bay_cells(i, t)[0])
                want = CRATE[stack[t]] if t < len(stack) else AIR
                if not ctx.is_block(cell, rooms.name(want)):
                    return False
        return True

    def come_in(tag: str = S1) -> None:
        game_checks.stand_in(ctx, tag, INDEX)

    def arm(level: int, m: int) -> None:
        """a fresh game, the level set, the manifest forced, one stand-in in"""
        for tag in (S1, S2):
            ctx.cmd(f"kill @e[tag={tag}]")
        ctx.function("reset/all")
        ctx.set_score("#level", level)
        ctx.set_score("#cargo.force", m)
        ctx.set_score(f"#d{INDEX}", 1)
        come_in()

    def press(name: str) -> None:
        """a button pressed as a hand would: set powered, a tick read"""
        post = posts(fr)[name]
        x, y, z = post.input
        block = post.attached[post.input].replace("powered=false", "powered=true")
        ctx.setblock((x, y, z), block)
        ctx.advance(2)

    def goto(i: int) -> None:
        row, col = divmod(i, 4)
        run("press/fore" if row else "press/aft")
        for _ in range(abs((get("colto") or 0) - col)):
            run("press/starboard" if col > (get("colto") or 0) else "press/port")
        settle()

    def move(a: int, b: int) -> None:
        """a crate from bay a to bay b by the press functions"""
        goto(a)
        run("press/down")
        settle()
        run("press/grab")
        settle()
        goto(b)
        run("press/down")
        settle()
        run("press/release")
        settle()

    # -- as built
    game_checks.fresh(ctx)
    b = room_blocks(dome)
    dry = [c for c in sorted(basin(dome)) if not ctx.is_block(c, f"{WATER}[level=0]")]
    expect("the basin: every cell a source of water", dry[:3], [])
    soft = [c for c, block in sorted(b.bed.items()) if not ctx.is_block(c, block)]
    expect("the basin's bed", soft[:3], [])
    expect("the list gauges' needles", count(NEEDLE_TAG), 2)
    expect("the list gauges' marks", count(ZONE_TAG), 2 * ZONES)
    expect("the needle upright", needle(), 0)
    changing = dressing_cells(dome) | b.moving | {fr.at(*LECTERN)}
    wrong = [
        c
        for k, (c, block) in enumerate(sorted(b.everything().items()))
        if c not in changing
        and (k % 5 == 0 or rooms.is_input(block))
        and not ctx.is_block(c, rooms.name(block))
    ]
    expect("blocks of the room as built (every fifth, and the inputs)", wrong[:3], [])
    screen = fr.at(PULPIT_F[1], 0, SCREEN_H)
    expect("the screen's clear window", ctx.is_block(screen, BARRIER), True)
    slab = fr.at(*DRIVER_BACK[:2], DECK_H + 1)
    expect("the driver's platform", ctx.is_block(slab, rooms.name(PLATFORM_SLAB)), True)
    level = fr.at(*DRIVER[:2], DECK_H + 1)
    expect("the platform's front row, level", ctx.is_block(level, AIR), True)
    expect("the crane's parts at home", count(PART_TAG), PARTS)
    expect("links of chain with the hook up", count(LINK_TAG), RAIL_H + 1 - UP)
    expect("crate displays", count(CRATE_TAG), 0)
    for tag in (BOARD_TAG, DOCKET_TAG, DARK_TAG, JAM_TAG):
        expect(f"the display {tag}", count(tag), 1)
    expect("the recall post", count(fittings.RECALL_TAG + f",tag={ENTITY_TAG}"), 1)
    if "Finch" not in ctx.data(f"block {_xyz(fr.at(*LECTERN))} Book"):
        problems.append("the log is not on its lectern")
    lamp = donkey(fr).lamps[0]
    lit = set()
    for _ in range(6):
        ctx.advance(7)
        lit.add(ctx.is_block(lamp, f"{BULB}[lit=true]"))
    expect("the donkey engine's lamp changes as it runs", lit, {True, False})

    # -- arming at level 5, each manifest
    for m in range(3):
        arm(5, m + 1)
        start, plan = (parse(t) for t in BANDS[2].manifests[m][:2])
        expect(
            f"manifest {m + 1}: armed",
            (get("live"), get("m"), get("band"), get("lim")),
            (1, m + 1, 2, 2),
        )
        expect(f"manifest {m + 1}: the bays' scores", hold(), start)
        expect(f"manifest {m + 1}: the bays' blocks", blocks_are(start), True)
        for i, stack in enumerate(plan):
            for table in (PLAN_TABLE, BOW_TABLE):
                cell = fr.at(*table_cell(table, i, 0))
                want = rooms.name(CRATE[stack[0]]) if stack else AIR
                if not ctx.is_block(cell, want):
                    problems.append(f"manifest {m + 1}: the plan table's {BAYS[i]}")
        cell = fr.at(*table_cell(HOLD_TABLE, 7, 0))
        want = rooms.name(CRATE[start[7][0]]) if start[7] else AIR
        expect(f"manifest {m + 1}: the hold table's F4", ctx.is_block(cell, want), True)
        expect(f"manifest {m + 1}: the list gauge's needle", needle(), trim(start))
        expect(f"manifest {m + 1}: the gauge's green and red", zones(), band(2))
        if MANIFEST_NAMES[m].split()[0] not in ctx.data(
            f"block {_xyz(fr.at(*LECTERN))} Book"
        ):
            problems.append(f"manifest {m + 1}: the log's fourth page")

    # -- the buttons, as a hand presses them: the trolley and bridge glide
    arm(5, 1)
    start = parse(BANDS[2].manifests[0][0])
    home = pos(DRUM_TAG)
    for _ in range(3):
        press("STARBOARD")
    expect("STARBOARD three times", get("colto"), 3)
    ctx.advance(4)
    mid = pos(DRUM_TAG)
    settle()
    end = pos(DRUM_TAG)
    if home and mid and end:
        d = [round(e - h, 4) for e, h in zip(end, home, strict=True)]
        expect(
            "the trolley's glide to the fourth column",
            d,
            [9 * fr.right[0], 0, 9 * fr.right[1]],
        )
        moved = [round(p - h, 4) for p, h in zip(mid, home, strict=True)]
        if not 0 < abs(moved[0] + moved[2]) < 9:
            problems.append(f"the trolley is not on its way part-way: moved {moved}")
    else:
        problems.append("the drum's position cannot be read")
    press("FORE")
    settle()
    there = pos(DRUM_TAG)
    if end and there:
        d = [round(e - h, 4) for e, h in zip(there, end, strict=True)]
        expect(
            "the bridge's glide to the fore hold",
            d,
            [15 * fr.forward[0], 0, 15 * fr.forward[1]],
        )
    expect("the crane over F4", (get("row"), get("col")), (1, 3))
    ctx.advance(12)
    if "F4" not in ctx.data(f"entity @e[tag={BOARD_TAG},limit=1] text"):
        problems.append("the status board does not say F4")

    # -- the hook: down on a stack of two (F3 holds iron and wool)
    press("PORT")
    settle()
    press("HOOK DOWN")
    settle()
    expect("the spreader on a stack of two", get("hy"), 5)
    expect("links of chain down to it", count(LINK_TAG), RAIL_H + 1 - 5)
    press("GRAB")
    top = fr.at(*bay_cells(6, 1)[0])
    expect("the wool's blocks gone", ctx.is_block(top, AIR), True)
    expect("the wool's eight displays", count(CRATE_TAG), 8)
    expect("the wool on the hook", (get("load"), get("from")), (WOOL, 6))
    settle()
    expect("the hook up", get("hy"), UP)
    low = pos(CRATE_TAG)
    if low:
        h = low[1] - dome.floor_y
        expect("the crate rides at h 10 to 12", 10 <= h <= 11, True)
    # refused: the wool across to port is fine, so a barrel test below; the
    # wool to F2 (on the iron): set down, at the right tier
    press("PORT")
    settle()
    press("HOOK DOWN")
    settle()
    expect("the hook over F2's iron with the wool", get("hy"), 5)
    press("RELEASE")
    settle()
    expect("no crate display left", count(CRATE_TAG), 0)
    expect(
        "the wool on F2's iron",
        ctx.is_block(fr.at(*bay_cells(5, 1)[0]), CRATE[WOOL]),
        True,
    )
    after = list(start)
    after[6], after[5] = (IRON,), (IRON, WOOL)
    expect("the hold's scores after a move", hold(), tuple(after))
    expect("the trim after it", get("trim"), trim(tuple(after)))
    expect("the needle after it", needle(), trim(tuple(after)))
    expect("the move counted", get("moves"), 1)
    expect(
        "the hold table's F2",
        ctx.is_block(fr.at(*table_cell(HOLD_TABLE, 5, 1)), CRATE[WOOL]),
        True,
    )

    # -- UNDO: one back, then nothing to undo changes nothing
    run("press/undo")
    expect("UNDO: the start again", hold(), start)
    expect("UNDO: its blocks", blocks_are(start), True)
    before = (hold(), get("moves"))
    run("press/undo")
    expect("UNDO with nothing to undo", (hold(), get("moves")), before)

    # -- refusals, each read by ``why`` with the hook up and loaded
    move_to = {"crush": 6, "trim": 2}
    goto(0)
    run("press/down")
    settle()
    run("press/grab")
    settle()
    for what, bay in move_to.items():
        goto(bay)
        run("press/down")
        ctx.advance(2)
        want = CRUSH if what == "crush" else TRIM
        expect(
            f"a barrel refused ({what})",
            (get("why"), get("hy"), get("load")),
            (want, UP, BARREL),
        )
        if what == "trim":
            kicked = needle()
            expect("refused: the needle kicks into the red", kicked, get("ta"))
            ctx.advance(FLASH_TICKS + 2)
            expect("and swings back", needle(), get("trim"))
            if "LIST" not in ctx.data(f"entity @e[tag={BOARD_TAG},limit=1] text"):
                problems.append("the status board does not say her list")
    # with a crate on the hook UNDO puts it back
    run("press/undo")
    expect("UNDO with a crate on the hook", (hold(), get("load")), (start, 0))
    # full: three crates laid in A3 by the scores, a bale over it
    for t, k in enumerate((IRON, BARREL, HAY)):
        ctx.set_score(f"#cargo.b2.t{t}", k)
    ctx.set_score("#cargo.b2.n", 3)
    run("bay/2/show")
    goto(3)
    run("press/down")
    settle()
    run("press/grab")
    settle()
    goto(2)
    run("press/down")
    ctx.advance(2)
    expect("a bale refused over a full bay", (get("why"), get("hy")), (FULL, UP))
    run("press/undo")

    # -- stand clear: a stand-in in F3's column
    arm(5, 1)
    goto(6)
    (f0, _), (r0, _) = BAY_F[1], BAY_R[2]
    game_checks.stand_at(ctx, S2, domes.middle(fr.at(f0, r0, 6)))
    run("press/down")
    ctx.advance(2)
    expect("DOWN refused over a stand-in", (get("why"), get("hyto")), (CLEAR, UP))
    ctx.cmd(f"kill @e[tag={S2}]")
    run("press/down")
    ctx.advance(10)
    game_checks.stand_at(ctx, S2, domes.middle(fr.at(f0, r0, 2)))
    ctx.advance(20)
    waited = (get("wait"), get("hy"))
    ctx.advance(20)
    expect("the hook waits over the stand-in", (get("wait"), get("hy")), waited)
    expect("waiting", waited[0], 1)
    ctx.cmd(f"kill @e[tag={S2}]")
    settle()
    expect("the hook goes on when they are out", get("hy"), 5)

    # -- a whole solve, manifest 1 at level 5, along the search's route
    arm(5, 1)
    solved_before = ctx.score("#solved")
    for a, z in puzzle()[2, 0]["route"]:
        move(a, z)
    plan = parse(BANDS[2].manifests[0][1])
    expect("the route stows her", hold(), plan)
    expect("its blocks", blocks_are(plan), True)
    expect("the dome solved", (ctx.score(f"#d{INDEX}"), get("free")), (2, 1))
    expect("the pump waits", ctx.score(f"#t{INDEX}.ready"), 1)
    problems += game_checks.pull_pump(ctx, INDEX)
    ctx.advance(10)
    if not ctx.score(f"#t{INDEX}"):
        problems.append(f"tunnel {INDEX} is not pumping after its lever")
    # played with after: a move and back, still solved, nothing called
    move(4 + 1, 4 + 0)
    expect(
        "played with after the solve",
        (ctx.score(f"#d{INDEX}"), ctx.score("#solved")),
        (2, (solved_before or 0) + 1),
    )
    # manifests 2 and 3 by the press functions
    for m in (1, 2):
        arm(5, m + 1)
        for a, z in puzzle()[2, m]["route"]:
            move(a, z)
        expect(f"manifest {m + 1} solved by its route", get("free"), 1)

    # -- three moves and three UNDOs: the start exactly
    arm(5, 1)
    for a, z in puzzle()[2, 0]["route"][:3]:
        move(a, z)
    for _ in range(3):
        run("press/undo")
    expect("three UNDOs: the start", (hold(), get("moves"), get("hn")), (start, 0, 0))
    expect("three UNDOs: its blocks", blocks_are(start), True)

    # -- RESET HOLD: one pull and 5 s, nothing; two pulls, the start again
    lever = posts(fr)["RESET HOLD"]
    thrown = lever.attached[lever.input].replace("powered=false", "powered=true")
    move(*puzzle()[2, 0]["route"][0])
    moved = hold()
    ctx.setblock(lever.input, thrown)
    ctx.advance(ASK_TICKS + 10)
    expect("one pull of RESET HOLD", hold(), moved)
    expect(
        "the lever put back",
        ctx.is_block(lever.input, lever.attached[lever.input]),
        True,
    )
    for _ in range(2):
        ctx.setblock(lever.input, thrown)
        ctx.advance(3)
    expect("two pulls of RESET HOLD", (hold(), get("moves")), (start, 0))

    # -- leaving with a crate on the hook: it goes back, the hook up
    goto(0)
    run("press/down")
    settle()
    run("press/grab")
    settle()
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.advance(game_checks.EMPTY)
    expect("left: the crate back", (hold(), get("load"), get("hy")), (start, 0, UP))
    expect("left: the crane whole", (count(PART_TAG), count(CRATE_TAG)), (PARTS, 0))
    come_in()
    expect("back in: not armed again", (get("live"), get("m")), (1, 1))

    # -- the forms: two in, the hold table's fore half dark between moves
    goto(0)
    run("press/down")
    settle()
    run("press/grab")
    come_in(S2)
    settle()
    expect("duo asked, not taken with a crate up", (get("want"), get("form")), (2, 1))
    run("press/undo")
    ctx.advance(2)
    expect("duo taken between moves", get("form"), 2)
    f4 = fr.at(*table_cell(HOLD_TABLE, 6, 0))
    expect("the fore half of the hold table dark", ctx.is_block(f4, AIR), True)
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance((game.SOLO_AFTER + 2) * game.SCAN_TICKS)
    expect("solo again", get("form"), 1)
    expect(
        "the table lit again", ctx.is_block(f4, rooms.name(CRATE[start[6][0]])), True
    )

    # -- levels 1 and 10; F1's hatch jammed at 9 and 10
    arm(1, 1)
    expect("level 1", (get("band"), get("lim"), get("shut")), (0, 5, -1))
    expect("level 1: the gauge green to 5 tons, red past it", zones(), band(5))
    arm(10, 1)
    expect("level 10", (get("band"), get("lim"), get("shut")), (4, 2, 4))
    hatch = fr.at(*[c for c in bay_cells(4, 0) if c[2] == 1][0])
    expect("level 10: F1's hatch", ctx.is_block(hatch, HATCH), True)
    goto(0)
    run("press/down")
    settle()
    run("press/grab")
    settle()
    goto(4)
    run("press/down")
    ctx.advance(2)
    expect("F1 refused at level 10", get("why"), SHUT)

    # -- the game's reset: as built
    for tag in (S1, S2):
        ctx.cmd(f"kill @e[tag={tag}]")
    ctx.function("reset/all")
    ctx.advance(game_checks.SCAN)
    expect(
        "reset: the crane",
        (count(PART_TAG), count(LINK_TAG), count(CRATE_TAG)),
        (PARTS, RAIL_H + 1 - UP, 0),
    )
    expect("reset: the hold empty", blocks_are(((),) * len(BAYS)), True)
    expect("reset: F1's hatch off", ctx.is_block(hatch, AIR), True)
    expect("reset: not armed", get("live"), 0)
    left = ctx.count(f"@e[type=minecraft:armor_stand,tag={game.STANDIN}]")
    expect("stand-ins left behind", left, 0)
    return problems


MODULE = game.Module(
    "cargo",
    stages={f"dome_{INDEX}_inside": build},
    functions=functions,
    checks={"cargo_hold": check},
)
