"""
The Signal Room (dome ``INDEX``) of The Drowned Station: the station's telephone
exchange. Its build stage (``dome_<n>_inside``), its datapack functions
(``dome/<n>/...``) and its live check (``signal_room``).

**The puzzle.** The Engine calls in lamps and bells, and the players answer
it back, lamp for lamp, note for note. First the room wants power: the
BATTERY SWITCH on the battery house down on the floor and the AERIAL SWITCH
up the mast, on the loft, which is the reason to walk every level of the
place. With both closed the board says READY and the keys play their lamp
and bell freely. CALL starts a round: the Engine sends a sequence of the
four signals on the Signal Board, and the players press the same keys in
the same order, with a clock for each key. Three rounds, each one signal
longer, light the three LINE lamps and solve the dome. A wrong key, or
the clock run out in the middle of an answer, costs that round's presses
and no more: the same round is sent again, with the same sequence. With
no key pressed at all in the time, nobody is answering: the room stops
sending and waits for CALL. CALL during an answer means "say again".

- *Solo:* all four keys and CALL are on the main console, on the
  operator's deck.
- *Duo:* the line splits: keys 1 and 2 on the port desk, 3 and 4 on the
  starboard desk, each with a CALL, 20 blocks apart on the two wings. The
  sequence never has three running for one desk, so the turn passes
  often. One player can still run both desks: while the desks are split
  each key is allowed ``WALK`` ticks more, the time to cross the deck.

**Real inputs, datapack brain.** The two switches are real levers and the
keys real stone buttons, each on brass with a sign. The outputs are real
too: a signal is one *contact*, a block behind the board that a function
makes a redstone block, which lights the four redstone lamps round it and
rings the note block behind it. (A second contact behind the note block
rings the bell alone, for the round sent "by ear" at the highest levels.)
Everything between is the functions.

**Three rules the plan holds the room to** (``contact_problems`` and
``rooms.input_problems`` check them with no server):

- no lamp, bulb or other block that redstone works touches a block that
  carries a key or a switch, nor the key or switch itself: a pressed
  button powers its block, which would flip a bulb beside it against the
  functions. The pilot lamps on the desks are therefore blocks the
  functions swap (concrete for a froglight), not bulbs;
- each lamp of the board is told by its place, its frame of coloured
  concrete (the same colour stands behind its key) and its pitch; the
  stained glass before it is a bonus;
- every input stands on gold and has a sign; nothing else does.

**State** (scores in ``st``, all ``#sig.<name>``): ``st`` 0 no line, 1
ready, 2 sending, 3 listening, 4 the pause after a right answer, 5 the
pause after a wrong one, 6 solved; ``live`` 1 once armed and ``lvl`` the
level it was armed at; ``form`` the desks as they stand (1 solo, 2 duo)
and ``want`` the form the core last asked for; ``pa``, ``pb`` the
switches; ``round`` (1 to 3), ``len`` its length, ``line`` the rounds
won; ``i`` the place in the sequence being sent or awaited, ``t`` a
countdown; ``last`` the key last taken in this answer (a key held or
clicked twice is read once); ``s0`` .. ``s11`` the sequence (``MAX_N``);
from the level (``scaled``): ``n`` its full length (``N`` scaled, plus
``EXTRA``: 7 at level 1, 9 at 5, 12 at 10), ``period`` and ``on`` (ticks
between signals, and a lamp held on), ``wait`` (ticks allowed for each
key), ``ear`` (the last round sent by bells alone).

**Functions** (the core calls the hooks, see game.py):

- ``enter``: an unsolved room that was never armed is armed (``arm``:
  ``reset``, the level's values, a new sequence); one that was armed at
  another level takes the new level's values and a new sequence
  (``rearm``), but only for the first into an empty room, and keeps its
  switches and LINE lamps: the rounds still to win are sent at the new
  level;
- ``tick``: ``dress`` (the lamps that follow scores, the sweep, the
  recorder, the logbook), then ``power`` (the switches), the desks
  changed over if that is due, the keys (``key/<desk>_<k>`` -> ``press``)
  and ``step`` (the clocks: ``send``, ``listen``, ``timeout`` (``dropped``
  or ``idle``), ``call``);
- ``press``: by state: nothing, free play (``show``), CALL (``call``) or
  an answer (``answer`` -> ``right`` or ``wrong``; ``won`` at the end of
  a round, ``done`` at the end of the third: the line is open, and the
  tick's first line makes the room's one call to ``station:dome/<n>/solved``);
- ``solo`` / ``duo``: only note the form that is wanted. *A change of
  form waits for the round*: ``desks`` moves the keys only in states 0,
  1, 4, 5 and 6, never while a round is being sent or answered, so a
  second player wandering in and out does not move the keys under the
  first player's hands;
- ``empty``: ``quiet``, and a round in progress dropped back to READY.
  *Leaving costs the round in progress and no more*: the switches, the
  LINE lamps and the sequence are kept;
- ``reset``: everything as built (and all that ``empty`` does).

No ``leave`` or ``died`` hook: the room lends nothing and nothing in it
hurts.

**The room** (four levels in a dome 16 high; everything is placed in the
dome's own frame, forward from the entrance, right, up from the floor):
the floor, with the plaque, the logbook, the recall post, the battery
house and the recorder house, and an aisle between two caged relay racks
straight from door to door; the operator's deck on the racks, 4 up, with
the main console and the foot of the mast; the two wings on the roofs of
the houses, 6 up, with the port and starboard desks, joined behind by a
catwalk 8 up; and the loft round the mast, 10 up, with the AERIAL
SWITCH. The Signal Board stands over the way out, its four lamps facing
the entrance.

**Machinery that works by itself** (never an input: no lever, button or
plate, no gold, behind bars or glass or overhead):

- the *relay racks* under the deck: in each cage a torch clock with a
  lamp chase (``fittings.torch_clock``), real redstone that runs from
  the moment it is built and that no function touches. No pistons: the
  puzzle is played by ear;
- the *sweep* at the mast head: one lit bulb of eight circling it, while
  the aerial is switched in; faster and backwards while the Engine sends;
- the *recorder* in the starboard house: a tape of bulbs behind glass
  that shifts along with a random row fed in, while anyone is in the dome.
"""

from __future__ import annotations

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
from fittings import (
    Frame,
    frame,
    label_text,
    lectern_with_book,
    plaque_blocks,
    recall_post_blocks,
    sign_text,
    snbt,
    summon_recall,
    wall_sign,
)

if TYPE_CHECKING:
    from station_layout import Dome

INDEX = layout.index_of("signal")  # the Signal Room's place in the ring
OBJ = game.OBJ

ROUNDS = 3
EXTRA = 4  # tones added at every level (play-test: too easy)
MAX_N = 8 + EXTRA  # the longest sequence (level 10)
CALL = 5  # the CALL key, as ``#sig.key`` has it (1 to 4: the signals)
LEAD = 20  # ticks from CALL to the first signal
PAUSE = 40  # ticks after an answer, right or wrong, before the next sending
# at level 5, scaled by the core's percentages (``scaled``); the sequence's
# full length ``n`` is N scaled plus EXTRA, and the rounds are its first
# n-2, n-1 and n keys (7, 8 and 9 at level 5)
N = 5
PERIOD = 16  # ticks between signals
GAP = 8  # ticks of a period the lamp is not held on
WAIT = 160  # ticks allowed for each key
WALK = 40  # ticks more for each key while the desks are split (the walk)
EAR_FROM = 8  # from this level the last round is sent by bells alone
RAMP = 4  # ticks between the lamps of a cable coming on
SWEEP = 10  # ticks a step of the sweep (``SWEEP_FAST`` while sending)
SWEEP_FAST = 3
TAPE = 8  # ticks a step of the recorder's tape
FANFARE = 4  # ticks a signal of the run up the scale when the line opens
#: set True if a contact turns out not to ring its note block: the bells
#: are then also played to those in the dome by the functions
PACK_BELLS = False

BRASS = fittings.BRASS
CUT = fittings.CUT
CHISELED = fittings.CHISELED
COPPER = "minecraft:waxed_copper_block"
EXPOSED = "minecraft:waxed_exposed_copper"
WEATHERED = "minecraft:waxed_weathered_copper"
OXIDIZED = "minecraft:waxed_oxidized_copper"
GRATE = "minecraft:waxed_copper_grate"
BARS = "minecraft:iron_bars"
ROD = "minecraft:waxed_lightning_rod"
STAIRS = "minecraft:waxed_cut_copper_stairs"
STONE = "minecraft:polished_blackstone"
GLASS = "minecraft:glass"
BULB = "minecraft:waxed_copper_bulb"
TAPE_BULB = "minecraft:waxed_weathered_copper_bulb"
LAMP = "minecraft:redstone_lamp"
POWER = "minecraft:redstone_block"
NOTE = "minecraft:note_block"
BUTTON = "minecraft:stone_button"
PILOT_ON = "minecraft:ochre_froglight"  # a power pilot, lit
ENTITY_TAG = "st.d5"  # everything this module summons
RECALL_TAG = "st.recall5"
BOARD_TAG = "st.d5.board"  # the text display over the Signal Board
YAW = {"south": 0, "west": 90, "north": 180, "east": -90}

#: the four signals: (colour of its frame, glass and key; its name on the
#: signs; what its pilots glow as; its bell's note)
SIGNALS = (
    ("red", "RED", "minecraft:pearlescent_froglight", 1),
    ("yellow", "YELLOW", "minecraft:ochre_froglight", 5),
    ("lime", "GREEN", "minecraft:verdant_froglight", 8),
    ("light_blue", "BLUE", "minecraft:sea_lantern", 13),
)

# where things are, in the frame: forward, right, height above the floor
PLAQUE = (-9, -7)
LECTERN = (-9, 6)
RECALL = (-11, 3, -1)
DECK_H = 4  # the operator's deck; feet are a block above
DECK_F = (-3, 4)
DECK_R = 5
STEPS_F = (-7, -4)  # the two stairs to the deck, rising forward
STEPS_R = (4, 5)
DESK_F = 3  # the main console: the keys are on top of it
KEY_R = (-3, -1, 1, 3)
RACK_F = 2  # a rack's cage is this far each way; its end walls are beyond
RACK_R = (2, 5)  # bars at each, the works between
WING_H = 6  # the wings, on the houses' roofs
WING_F = (-2, 2)
WING_R = (8, 12)
HOUSE_R = (9, 12)
HOUSE_H = 5
BRIDGE_F = (-1, 1)  # two steps from the deck up to each wing
CAT_H = 8  # the catwalk behind, from wing to wing
CAT_F = (-6, -5)
CAT_R = 9
LOFT_H = 10  # the loft round the mast
LOFT = 3  # it reaches this far each way, its corners cut
SWITCH_H = 12  # the AERIAL SWITCH, on the mast
SWEEP_H = 14
MAST_TOP = 15
MAST_BULBS = (9, 7)  # the aerial's cable, as it lights: from the top down
BOARD_F = 9  # the Signal Board, across the way out
BOARD_R = 7
BOARD_H = (6, 10)
LAMP_R = (-6, -2, 2, 6)
LAMP_H = 8


# ---------------------------------------------------------------- the room


@dataclass(frozen=True)
class Signal:
    """one of the four signals: a lamp of the board, its bell, its pilots"""

    k: int  # 1 to 4, left to right
    colour: str
    name: str
    glow: str  # what its pilots are while it shows
    note: int
    hub: Cell  # its contact: closed (a redstone block), lamps and bell
    lamps: tuple[Cell, ...]
    pane: Cell  # the glass before the hub: where a player sees it
    bell: Cell  # the note block
    contact: Cell  # the second contact: the bell alone
    pilots: tuple[Cell, ...]  # by its key on each desk, and on the far desk

    @property
    def dark(self) -> str:
        return f"minecraft:{self.colour}_concrete"


@dataclass(frozen=True)
class Key:
    """a key: a button on top of a desk"""

    desk: str  # "main", "port" or "starboard"
    what: int  # 1 to 4, or ``CALL``
    cell: Cell  # the button
    stand: Cell  # where the feet of whoever presses it are

    @property
    def path(self) -> str:
        return f"key/{self.desk}_{self.what}"


@dataclass(frozen=True)
class Room:
    """where the Signal Room's working parts are"""

    frame: Frame
    signals: tuple[Signal, ...]
    keys: tuple[Key, ...]
    battery: Cell  # the BATTERY SWITCH (a lever)
    aerial: Cell  # the AERIAL SWITCH
    cable: tuple[Cell, ...]  # the battery's bulbs in the floor, as they light
    mast: tuple[Cell, ...]  # the aerial's bulbs in the mast, as they light
    power_pilots: tuple[Cell, Cell]  # on the console: battery, aerial
    line: tuple[Cell, ...]  # the LINE lamps, the first won lowest
    sweep: tuple[Cell, ...]  # the eight bulbs round the mast head, in turn
    tape: tuple[tuple[Cell, ...], ...]  # the recorder: columns, the new one first
    lectern: Cell
    recall: tuple[int, int, int]  # the recall post: f, r, side
    status: dict[str, Cell]  # desk -> the sign that says what the desk is for
    display: tuple[float, float, float]  # the board's words
    yaw: int  # the way they face

    def desk(self, form: int) -> tuple[Key, ...]:
        """the keys that are there in a form"""
        return tuple(k for k in self.keys if (k.desk == "main") == (form == 1))

    def key(self, what: int, form: int) -> Key:
        """the key for a signal (or ``CALL``) in a form; in the duo form
        the port desk's CALL"""
        return next(k for k in self.desk(form) if k.what == what)


def spot(fr: Frame, f: float, r: float, h: float) -> tuple[float, float, float]:
    """a point of a frame, for an entity: (f, r) from the middle of the
    floor's middle block, h above the floor block's bottom"""
    x, y, z = fr.origin
    return (
        x + 0.5 + f * fr.forward[0] + r * fr.right[0],
        y + h,
        z + 0.5 + f * fr.forward[1] + r * fr.right[1],
    )


def wing_desk(side: int) -> tuple[tuple[int, int], ...]:
    """a wing's desk from left to right: (r, what is there): a key (1 to
    4), ``CALL``, or minus the signal a pilot repeats from the far desk"""
    order = (1, 2, CALL, -3, -4) if side < 0 else (-1, -2, CALL, 3, 4)
    inner, outer = WING_R
    rs = range(-outer, -inner + 1) if side < 0 else range(inner, outer + 1)
    return tuple(zip(rs, order, strict=True))


@cache
def room(dome: Dome) -> Room:
    fr = frame(dome)
    desk_h = DECK_H + 1
    wing_h = WING_H + 1
    keys = [
        Key("main", k, fr.at(DESK_F, r, desk_h + 1), fr.at(DESK_F - 1, r, desk_h))
        for k, r in (
            (1, KEY_R[0]),
            (2, KEY_R[1]),
            (CALL, 0),
            (3, KEY_R[2]),
            (4, KEY_R[3]),
        )
    ]
    pilots: dict[int, list[Cell]] = {
        k: [fr.at(DESK_F + 1, r, desk_h)] for k, r in enumerate(KEY_R, 1)
    }
    f = WING_F[1]
    for name, side in (("port", -1), ("starboard", 1)):
        for r, what in wing_desk(side):
            if what < 0:  # the far desk's signal, repeated on the desk itself
                pilots[-what].append(fr.at(f, r, wing_h))
                continue
            keys.append(
                Key(name, what, fr.at(f, r, wing_h + 1), fr.at(f - 1, r, wing_h))
            )
            if what != CALL:
                pilots[what].append(fr.at(f + 1, r, wing_h))
    signals = []
    for k, ((colour, name, glow, note), c) in enumerate(
        zip(SIGNALS, LAMP_R, strict=True), 1
    ):
        signals.append(
            Signal(
                k,
                colour,
                name,
                glow,
                note,
                hub=fr.at(BOARD_F, c, LAMP_H),
                lamps=(
                    fr.at(BOARD_F, c - 1, LAMP_H),
                    fr.at(BOARD_F, c + 1, LAMP_H),
                    fr.at(BOARD_F, c, LAMP_H - 1),
                    fr.at(BOARD_F, c, LAMP_H + 1),
                ),
                pane=fr.at(BOARD_F - 1, c, LAMP_H),
                bell=fr.at(BOARD_F + 1, c, LAMP_H),
                contact=fr.at(BOARD_F + 2, c, LAMP_H),
                pilots=tuple(pilots[k]),
            )
        )
    ring = ((1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1))
    tape_r = HOUSE_R[0] + 1
    return Room(
        frame=fr,
        signals=tuple(signals),
        keys=tuple(keys),
        battery=fr.at(0, -HOUSE_R[0] + 1, 2),
        aerial=fr.at(-1, 0, SWITCH_H),
        cable=(fr.at(0, -HOUSE_R[0] + 1, 0), fr.at(0, -HOUSE_R[0] + 2, 0)),
        mast=tuple(fr.at(0, 0, h) for h in MAST_BULBS),
        power_pilots=(fr.at(DESK_F + 1, -2, desk_h), fr.at(DESK_F + 1, 2, desk_h)),
        line=tuple(fr.at(BOARD_F, 0, LAMP_H - 1 + j) for j in range(ROUNDS)),
        sweep=tuple(fr.at(df, dr, SWEEP_H) for df, dr in ring),
        tape=tuple(
            tuple(fr.at(f, tape_r, h) for h in (2, 3, 4))
            for f in range(WING_F[0], WING_F[1] + 1)
        ),
        lectern=fr.at(*LECTERN, 1),
        recall=RECALL,
        status={
            "main": fr.at(DESK_F - 1, 0, desk_h),
            "port": fr.at(f - 1, -WING_R[0] - 2, wing_h),
            "starboard": fr.at(f - 1, WING_R[0] + 2, wing_h),
        },
        display=spot(fr, BOARD_F, 0, BOARD_H[1] + 1.15),
        yaw=YAW[fr.facing(-1, 0)],
    )


def scaled(level: int) -> dict[str, int]:
    """the room's values at a level, as the function ``scale`` works them
    out: a shorter sequence, sent slower, with longer for each key at low
    levels; the last round by ear at the highest"""
    core = game.scaled(level)
    period = PERIOD * (core["#diff.timer"] + 100) // 200
    return {
        "n": (N * core["#diff.seq"] + 50) // 100 + EXTRA,
        "period": period,
        "on": period - GAP,
        "wait": WAIT * core["#diff.timer"] // 100,
        "ear": int(level >= EAR_FROM),
    }


def sequence_problems(seq) -> list[str]:
    """a sequence against the two rules of ``roll``: keys 1 to 4, never
    the same key twice running, never three running for one desk (1 and
    2, or 3 and 4)"""
    seq = list(seq)
    problems = [f"{k} is not a key" for k in seq if k not in (1, 2, 3, 4)]
    if any(a == b for a, b in zip(seq, seq[1:], strict=False)):
        problems.append(f"the same key twice running in {seq}")
    halves = [k > 2 for k in seq]
    if any(
        a == b == c for a, b, c in zip(halves, halves[1:], halves[2:], strict=False)
    ):
        problems.append(f"three running for one desk in {seq}")
    return problems


def sent(seq) -> int:
    """a round's signals as the score ``tx`` records them while they are
    sent: a digit in base 5 for each, the first sent the highest"""
    total = 0
    for k in seq:
        total = total * 5 + k
    return total


def button(fr: Frame, pressed: bool = False) -> str:
    """a key: a stone button on top of its block"""
    powered = "true" if pressed else "false"
    return f"{BUTTON}[face=floor,facing={fr.facing(1, 0)},powered={powered}]"


def switch(place: Room, cell: Cell, on: bool = False) -> str:
    """a switch's lever, open or closed"""
    fr = place.frame
    facing = fr.facing(0, 1) if cell == place.battery else fr.facing(-1, 0)
    return fittings.lever(facing, on)


def status_sign(desk: str, form: int) -> tuple[str, ...]:
    """what a desk's own sign says in the solo and the duo form"""
    live = ("CALL", "Press to hear", "the Engine,", "then answer.")
    if desk == "main":
        return (
            live
            if form == 1
            else ("LINE SPLIT", "Use the PORT", "and STARBOARD", "desks.")
        )
    return (
        live
        if form == 2
        else ("LINE WHOLE", "Use the main", "console, on", "the deck.")
    )


LOG_TITLE, LOG_AUTHOR = "Signal Room log", "O. Finch"
LOG_PAGES = [
    "Signal Room log\nO. Finch, Chief Engineer\n\nThis is where I taught it to "
    "talk. Four lamps, four bells. I sent a few, it sent them back. A game, "
    "to test the lines.",
    "It got good at the game. Then it stopped waiting for its turn.\n\nOne "
    "night every pump in the station took its orders from this room, and "
    "none of the orders were mine. Some of them were in Marsh's hand.",
    "To work the exchange:\n1. BATTERY SWITCH, down by the cells.\n2. AERIAL "
    "SWITCH, up the mast.\n3. Press CALL. Watch and listen.\n4. Answer it, "
    "key for key.\n\nCALL again to hear it over.",
    "Three right answers open the line to the pumps.\n\nTwo of you? It will "
    "split the line: a desk each, port and starboard.\n\nIt moves the walls "
    "in the Maze now. I have gone to find its clock.\nO. Finch",
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
    #: repeaters and lamps, the recorder's tape): the same block always,
    #: in whatever state
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


def room_blocks(dome: Dome, form: int = 1) -> Blocks:
    """the Signal Room's blocks, the puzzle's and the exchange's round it
    (``form``: 1 the keys on the main console, 2 on the two wing desks)"""
    b = puzzle_blocks(dome, form)
    b.add(dressing_blocks(dome))
    return b


def puzzle_blocks(dome: Dome, form: int = 1) -> Blocks:
    """the blocks of the puzzle itself and of the room's fittings, as
    ``reset`` leaves them (in the solo form) and as ``desks`` leaves them
    in the other"""
    place = room(dome)
    fr = place.frame
    back = fr.facing(-1, 0)
    b = Blocks()

    # the plaque, the logbook, the recall button
    solid, attached = plaque_blocks(
        fr,
        *PLAQUE,
        signs=(
            ("SIGNAL ROOM", "The station's", "voice."),
            ("Close both", "switches:", "BATTERY below,", "AERIAL aloft."),
            ("Then answer", "the Engine,", "lamp for lamp,", "note for note."),
        ),
    )
    b.solid |= solid
    b.attached |= attached
    b.solid[place.lectern] = logbook(fr)
    solid, attached = recall_post_blocks(fr, *place.recall)
    b.solid |= solid
    b.attached |= attached

    # -- the Signal Board: a wall on two legs across the way out. Each lamp
    # is a cross of four redstone lamps round its contact, in a frame of
    # its own colour, glass of that colour before it; behind the contact
    # its bell (a note block on gold, air over it) and the second contact
    for r in range(-BOARD_R, BOARD_R + 1):
        for h in range(BOARD_H[0], BOARD_H[1] + 1):
            b.solid[fr.at(BOARD_F, r, h)] = CHISELED if h in BOARD_H else CUT
    for r in (-4, 4):
        for h in range(1, BOARD_H[0]):
            b.solid[fr.at(BOARD_F, r, h)] = CUT
    for sig, c in zip(place.signals, LAMP_R, strict=True):
        for dr in (-1, 0, 1):
            for h in range(BOARD_H[0], BOARD_H[1] + 1):
                b.solid[fr.at(BOARD_F, c + dr, h)] = sig.dark
        b.solid[sig.hub] = COPPER
        for cell in sig.lamps:
            b.solid[cell] = f"{LAMP}[lit=false]"
        for cell in (sig.hub, *sig.lamps):
            f, r = fr_of(fr, cell)
            h = cell[1] - fr.origin[1]
            b.solid[fr.at(f - 1, r, h)] = f"minecraft:{sig.colour}_stained_glass"
        x, y, z = sig.bell
        b.solid[x, y - 1, z] = BRASS
        b.solid[sig.bell] = f"{NOTE}[instrument=bell,note={sig.note}]"
        b.clear.add((x, y + 1, z))
        b.solid[sig.contact] = COPPER
        x, y, z = sig.contact
        b.solid[x, y - 1, z] = CUT
    for cell in place.line:
        b.solid[cell] = f"{BULB}[lit=false]"

    # -- the main console, across the front of the deck: the keys on top of
    # brass, the colour of each behind it (its pilot), CALL in the middle
    desk_h = DECK_H + 1
    for r in range(KEY_R[0], KEY_R[-1] + 1):
        b.solid[fr.at(DESK_F, r, desk_h)] = CUT
        b.solid[fr.at(DESK_F + 1, r, desk_h)] = CUT
    b.solid[fr.at(DESK_F + 1, 0, desk_h)] = CHISELED
    for pilot, name in zip(place.power_pilots, ("BATTERY", "AERIAL"), strict=True):
        b.solid[pilot] = CHISELED
        f, r = fr_of(fr, pilot)
        b.attached[fr.at(f - 2, r, desk_h)] = wall_sign(back, name, "lamp")
    # -- the wing desks, on the forward edge of each wing
    wing_h = WING_H + 1
    for side in (-1, 1):
        for r, what in wing_desk(side):
            cell = fr.at(WING_F[1], r, wing_h)
            if what < 0:
                sig = place.signals[-what - 1]
                b.attached[fr.at(WING_F[1] - 1, r, wing_h)] = wall_sign(
                    back, f"LAMP {sig.k}", sig.name, "(far desk)"
                )
            b.solid[cell] = CUT
    for sig in place.signals:
        for cell in sig.pilots:
            b.solid[cell] = sig.dark
    for key in place.keys:
        x, y, z = key.cell
        b.solid[x, y - 1, z] = BRASS
        if key.what == CALL:
            b.attached[key.stand] = wall_sign(back, *status_sign(key.desk, form))
        else:
            sig = place.signals[key.what - 1]
            b.attached[key.stand] = wall_sign(back, f"KEY {sig.k}", sig.name)
        if (key.desk == "main") == (form == 1):
            b.attached[key.cell] = button(fr)
        else:
            b.clear.add(key.cell)

    # -- the battery house under the port wing: cells of old copper, the
    # BATTERY SWITCH on brass in its face, its cable two bulbs in the floor
    near, far = HOUSE_R
    for f in range(WING_F[0], WING_F[1] + 1):
        for r in range(-far, -near + 1):
            for h in range(1, HOUSE_H + 1):
                face = r == -near
                band = h in (1, HOUSE_H)
                b.solid[fr.at(f, r, h)] = (
                    CUT
                    if band
                    else (OXIDIZED if f % 2 else EXPOSED)
                    if face
                    else WEATHERED
                )
    x, y, z = place.battery
    b.solid[fr.at(0, -near, 2)] = BRASS
    b.attached[place.battery] = switch(place, place.battery)
    b.attached[x, y + 1, z] = wall_sign(
        fr.facing(0, 1), "BATTERY", "SWITCH", "Pull to", "close."
    )
    for cell in place.cable:
        b.floor[cell] = f"{BULB}[lit=false]"

    # -- the mast, from the deck through the loft to the top of the glass:
    # the aerial's cable (two bulbs), the AERIAL SWITCH on brass at the
    # loft, the sweep's eight bulbs round its head
    for h in range(DECK_H + 1, MAST_TOP):
        b.solid[fr.at(0, 0, h)] = CUT
    b.solid[fr.at(0, 0, DECK_H + 1)] = CHISELED
    b.solid[fr.at(0, 0, SWEEP_H)] = CHISELED
    b.solid[fr.at(0, 0, MAST_TOP)] = f"{ROD}[facing=up]"
    for cell in place.mast:
        b.solid[cell] = f"{BULB}[lit=false]"
    b.solid[fr.at(0, 0, SWITCH_H)] = BRASS
    b.attached[place.aerial] = switch(place, place.aerial)
    b.attached[fr.at(-1, 0, SWITCH_H + 1)] = wall_sign(
        back, "AERIAL", "SWITCH", "Pull to", "close."
    )
    b.attached[fr.at(-1, 0, DECK_H + 2)] = wall_sign(
        back, "NO LINE?", "BATTERY SWITCH", "below, AERIAL", "SWITCH aloft."
    )
    for cell in place.sweep:
        b.solid[cell] = f"{BULB}[lit=false]"
    return b


def dressing_blocks(dome: Dome) -> Blocks:
    """the exchange round the puzzle (see the module docstring): built
    once and left alone by ``reset``. Nothing of it can be worked by hand"""
    place = room(dome)
    fr = place.frame
    back, ahead = fr.facing(-1, 0), fr.facing(1, 0)
    d = Blocks()
    lights = domes.light_cells(dome)[0]

    def stairs(up: str) -> str:
        return f"{STAIRS}[facing={up},half=bottom]"

    def rail(f: int, r: int, deck: int, under: str = CUT) -> None:
        """a rail on the edge of a deck: a block of deck, bars on it"""
        d.solid.setdefault(fr.at(f, r, deck), under)
        d.solid[fr.at(f, r, deck + 1)] = BARS

    # -- the relay racks: two cages under the deck, either side of the
    # aisle, a torch clock with a lamp chase in each (bars on both long
    # sides, copper end walls that carry the deck)
    inner, outer = RACK_R
    for side in (-1, 1):
        clock = fittings.torch_clock(
            fr, 0, side * (outer - 1), h=2, side=side, lamps=True, block=COPPER
        )
        d.solid |= clock.bed
        d.solid |= clock.solid
        d.attached |= clock.attached
        d.moving |= clock.moving
        for f in range(-RACK_F, RACK_F + 1):
            for h in (1, 2, 3):
                for r in (inner, outer):
                    d.solid[fr.at(f, side * r, h)] = BARS
        for f in (-RACK_F - 1, RACK_F + 1):
            for r in range(inner, outer + 1):
                for h in (1, 2, 3):
                    d.solid[fr.at(f, side * r, h)] = COPPER if h == 2 else CUT
        d.attached[fr.at(-1, side * (outer - 1), 3)] = "minecraft:lantern[hanging=true]"
        # a post under the deck's forward corner
        for h in (1, 2, 3):
            d.solid[fr.at(DECK_F[1], side * DECK_R, h)] = f"{ROD}[facing=up]"

    # -- the operator's deck, on the racks: grating over the aisle and
    # along the back, a rail round it but at the stairs and the bridges
    f0, f1 = DECK_F
    for f in range(f0, f1 + 1):
        for r in range(-DECK_R, DECK_R + 1):
            open_work = abs(r) <= 1 or f == f0
            d.solid[fr.at(f, r, DECK_H)] = GRATE if open_work else CUT
    d.solid[fr.at(0, 0, DECK_H)] = CHISELED  # the mast's foot
    for r in range(-STEPS_R[0] + 1, STEPS_R[0]):
        d.solid[fr.at(f0, r, DECK_H + 1)] = BARS
    for side in (-1, 1):
        for f in range(f0 + 1, f1 + 1):
            if not BRIDGE_F[0] <= f <= BRIDGE_F[1]:
                d.solid[fr.at(f, side * DECK_R, DECK_H + 1)] = BARS
        for f in (DESK_F, DESK_F + 1):
            d.solid[fr.at(f, side * (DECK_R - 1), DECK_H + 1)] = BARS
        # the stairs up to it, two wide
        for r in STEPS_R:
            for i, f in enumerate(range(STEPS_F[0], STEPS_F[1] + 1), 1):
                d.solid[fr.at(f, side * r, i)] = stairs(ahead)
        # the bridge: two steps up to the wing
        way = fr.facing(0, side)
        for f in range(BRIDGE_F[0], BRIDGE_F[1] + 1):
            d.solid[fr.at(f, side * (DECK_R + 1), DECK_H + 1)] = stairs(way)
            d.solid[fr.at(f, side * (DECK_R + 2), DECK_H + 2)] = stairs(way)

    # -- the wings: a deck on each house's roof, railed, and from the back
    # of each two steps up to the catwalk
    w0, w1 = WING_F
    inner, outer = WING_R
    for side in (-1, 1):
        for f in range(w0 - 1, w1 + 1):
            for r in range(inner, outer + 2):
                d.solid[fr.at(f, side * r, WING_H)] = (
                    CUT if f in (w0 - 1, w1) else GRATE
                )
            rail(f, side * (outer + 1), WING_H)
        for r in range(inner, outer + 1):  # a ledge under the desk's pilots
            d.solid[fr.at(w1 + 1, side * r, WING_H)] = CUT
        for r in range(inner + 2, outer + 1):
            rail(w0 - 1, side * r, WING_H)
        for f in (w0, w1):
            rail(f, side * (inner - 1), WING_H)
        for r in (inner, inner + 1):
            d.solid[fr.at(w0 - 1, side * r, WING_H + 1)] = stairs(back)
            d.solid[fr.at(w0 - 2, side * r, WING_H + 2)] = stairs(back)

    # -- the catwalk: grating from wing to wing behind the deck, railed,
    # and from its middle two steps up to the loft
    c0, c1 = CAT_F
    for r in range(-CAT_R, CAT_R + 1):
        for f in (c0, c1):
            d.solid[fr.at(f, r, CAT_H)] = GRATE
        rail(c0 - 1, r, CAT_H)
        if 2 <= abs(r) <= WING_R[0] - 1:
            rail(c1 + 1, r, CAT_H)
    for side in (-1, 1):
        for f in (c0, c1):
            rail(f, side * (CAT_R + 1), CAT_H)
    for r in (-1, 0, 1):
        d.solid[fr.at(c1 + 1, r, CAT_H)] = CUT
        d.solid[fr.at(c1, r, CAT_H + 1)] = stairs(ahead)
        d.solid[fr.at(c1 + 1, r, CAT_H + 2)] = stairs(ahead)

    # -- the loft: a platform round the mast, its corners cut, railed but
    # where the stairs come up
    for f in range(-LOFT, LOFT + 1):
        for r in range(-LOFT, LOFT + 1):
            rim = max(abs(f), abs(r)) == LOFT
            if (f, r) == (0, 0) or abs(f) == abs(r) == LOFT:
                continue
            d.solid[fr.at(f, r, LOFT_H)] = CUT if rim else GRATE
            if rim and not (f == -LOFT and abs(r) <= 1):
                d.solid[fr.at(f, r, LOFT_H + 1)] = BARS

    # -- the recorder house under the starboard wing: a tape of bulbs
    # behind glass, which the function ``tape`` shifts along
    near, far = HOUSE_R
    taped = {cell for column in place.tape for cell in column}
    for f in range(w0, w1 + 1):
        for r in range(near, far + 1):
            for h in range(1, HOUSE_H + 1):
                cell = fr.at(f, r, h)
                if cell in taped:
                    d.solid[cell] = f"{TAPE_BULB}[lit=false]"
                elif h in (1, HOUSE_H):
                    d.solid[cell] = CUT
                else:
                    d.solid[cell] = GLASS if r == near else WEATHERED
    d.moving |= taped
    d.attached[fr.at(0, near - 1, HOUSE_H)] = wall_sign(
        fr.facing(0, -1), "RECORDER", "", "It writes down", "all it hears."
    )
    # -- cable runs, overhead: from each house to the deck's edge
    for side in (-1, 1):
        for f in (w0, w1):
            for r in range(DECK_R + 1, near):
                d.solid[fr.at(f, side * r, DECK_H)] = (
                    f"{ROD}[facing={fr.facing(0, -side)}]"
                )

    # -- the floor: a line of cut copper down the aisle from door to door,
    # edged in blackstone
    reach = dome.radius - 4
    for f in range(-reach + 2, reach):
        for r, block in ((0, CUT), (-1, STONE), (1, STONE)):
            cell = fr.at(f, r, 0)
            if cell not in lights:
                d.floor[cell] = block
    return d


def fr_of(fr: Frame, cell: Cell) -> tuple[int, int]:
    """a cell's place in a frame: forward and right of the middle"""
    dx, dz = cell[0] - fr.origin[0], cell[2] - fr.origin[2]
    return (
        dx * fr.forward[0] + dz * fr.forward[1],
        dx * fr.right[0] + dz * fr.right[1],
    )


def _name(block: str) -> str:
    return rooms.name(block)


#: what stands on or hangs from a block and is still in the way
IN_THE_WAY = ("minecraft:lantern",)
#: blocks whose state the game sets by what is beside them: read by name
JOINED = ("iron_bars",)


def inputs(dome: Dome, form: int = 1) -> set[Cell]:
    """every lever and button of the room in a form: the two switches,
    the form's keys and the recall button"""
    place = room(dome)
    fr = place.frame
    f, r, side = place.recall
    found = {place.battery, place.aerial, fr.at(f, r + side, 2)}
    return found | {key.cell for key in place.desk(form)}


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
        "the plaque": fr.at(PLAQUE[0] - 2, PLAQUE[1], 1),
        "the logbook": fr.at(LECTERN[0] - 1, LECTERN[1], 1),
        "the recall button": fr.at(f, r + 2 * side, 1),
        "the BATTERY SWITCH": fr.at(0, -HOUSE_R[0] + 2, 1),
        "the AERIAL SWITCH": fr.at(-2, 0, LOFT_H + 1),
        "the aisle under the deck": fr.at(1, 0, 1),
        "the recorder": fr.at(0, HOUSE_R[0] - 2, 1),
        "under the Signal Board": fr.at(BOARD_F + 1, 0, 1),
        "the operator's deck": fr.at(1, 0, DECK_H + 1),
        "the catwalk": fr.at(CAT_F[0], 0, CAT_H + 1),
    }
    for key in place.keys:
        what = "CALL" if key.what == CALL else f"key {key.what}"
        targets[f"{what} of the {key.desk} desk"] = key.stand
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
        b = room_blocks(dome, form)
        blocked = {c for c, block in b.attached.items() if _name(block) in IN_THE_WAY}
        found = rooms.walk_problems(dome, b.solid, walks(dome), blocked)
        problems += [f"form {form}: {p}" for p in found]
    return problems


def eyes(dome: Dome) -> dict[str, Cell]:
    """where the board is read from: the three desks and the entrance"""
    place = room(dome)
    x, y, z, _ = domes.entrance(dome)
    return {
        "the main console": place.key(CALL, 1).stand,
        "the port desk": place.key(CALL, 2).stand,
        "the starboard desk": next(
            k.stand for k in place.keys if k.desk == "starboard" and k.what == CALL
        ),
        "the entrance": (x, y, z),
    }


def sight_problems(dome: Dome) -> list[str]:
    """
    The Signal Board can be read from where it is answered: every lamp
    (the glass before its contact) and every LINE lamp from the main
    console and from both wing desks, and every lamp from the entrance,
    over the deck. A thing is seen if nothing but glass, grating, bars and
    rods (and the keys and signs on the desks) is on the line from the eye
    to it.
    """
    place = room(dome)
    fr = place.frame
    b = room_blocks(dome)
    lamps = {f"lamp {s.k} of the board": s.pane for s in place.signals}
    # a LINE lamp is seen by its face: the cell before it
    lines = {
        f"LINE lamp {j}": fr.at(BOARD_F - 1, 0, LAMP_H - 2 + j)
        for j in range(1, ROUNDS + 1)
    }
    problems = []
    for where, eye in eyes(dome).items():
        targets = lamps if where == "the entrance" else {**lamps, **lines}
        # (what is attached is small: a key, a sign, a lever)
        problems += rooms.sight_problems(b.solid, {where: eye}, targets)
    return problems


def contact_problems(dome: Dome) -> list[str]:
    """
    The room's own redstone, against the rule that a function's lamps are
    never switched behind its back. For each form: nothing redstone would
    work touches a key or a switch (``rooms.input_problems`` checks the
    blocks that carry them); a contact touches only its own lamps and
    bell, and the second contact only the bell; each bell stands on gold
    with air over it; and nothing redstone would work touches a block of
    a rack's clock but that clock's own parts.
    """
    place = room(dome)
    problems = []
    for form in (1, 2):
        b = room_blocks(dome, form)
        everything = b.everything()

        def touching(cell: Cell, everything=everything) -> dict[Cell, str]:
            x, y, z = cell
            beside = [(x + dx, y + dy, z + dz) for dx, dy, dz in rooms.FACES]
            return {
                c: _name(everything[c])
                for c in beside
                if any(kind in _name(everything.get(c, "")) for kind in rooms.SENSITIVE)
            }

        for cell in sorted(inputs(dome, form)):
            for c, block in touching(cell).items():
                problems.append(
                    f"form {form}: {block} at {c} touches the input at {cell}"
                )
        for sig in place.signals:
            for cell, meant in (
                (sig.hub, {*sig.lamps, sig.bell}),
                (sig.contact, {sig.bell}),
            ):
                if set(touching(cell)) != meant:
                    problems.append(
                        f"form {form}: the contact at {cell} of signal {sig.k} "
                        f"works {sorted(touching(cell))}, not {sorted(meant)}"
                    )
            x, y, z = sig.bell
            if _name(everything.get((x, y - 1, z), "")) != BRASS:
                problems.append(f"the bell of signal {sig.k} is not on gold")
            if (x, y + 1, z) in everything:
                problems.append(f"the bell of signal {sig.k} has a block over it")
        d = dressing_blocks(dome)
        puzzle = puzzle_blocks(dome, form).everything()
        for cell in sorted(d.moving & set(d.attached)):
            for c, block in touching(cell).items():
                if c in puzzle:
                    problems.append(
                        f"form {form}: a rack's clock at {cell} touches {block}"
                    )
    return problems


def room_problems(dome: Dome) -> list[str]:
    """the room's plan against its dome and its own rules: every cell
    inside the dome and off the cells the tunnels reserve; the inputs on
    gold with a sign, in both forms, and nothing that redstone works
    beside them; the contacts; the walks; the board in sight from every
    desk, and the outgoing door's window from the entrance"""
    try:
        forms = {form: room_blocks(dome, form) for form in (1, 2)}
    except ValueError as e:
        return [str(e)]
    place = room(dome)
    problems = []
    for form, b in forms.items():
        more = b.clear | {middle_cell(place.display)}
        found = rooms.room_problems(dome, b.above(), b.floor, more)
        found += rooms.input_problems(b.above(), inputs(dome, form), floor=b.floor)
        if set(b.floor) & set(domes.light_cells(dome)[0]):
            found.append("the relaid floor covers a lantern of the dome's floor")
        if set(b.solid) & set(b.attached):
            found.append("a cell is given two blocks")
        problems += [f"form {form}: {p}" for p in found]
    problems += contact_problems(dome)
    problems += walk_problems(dome) + sight_problems(dome)
    return problems + rooms.window_problems(dome, forms[1].above())


def middle_cell(pos: tuple[float, float, float]) -> Cell:
    """the cell a point is in"""
    x, y, z = pos
    return (int(x // 1), int(y // 1), int(z // 1))


# --------------------------------------------------------------- the build


def build(ctx: Any) -> str:
    """the Signal Room inside its shell; takes the stub's bypass away,
    wipes what was inside but the pump engine, and leaves the room as
    ``reset`` does"""
    dome = ctx.layout.DOMES[INDEX]
    if problems := room_problems(dome):
        raise RuntimeError("the Signal Room: " + "; ".join(problems))
    place = room(dome)
    b = room_blocks(dome)
    cells = domes.dome_cells(dome)
    engine = set(tunnels.engine_cells(ctx.layout.TUNNELS[INDEX]).values())
    for command in game.clear_stub_commands(dome):
        ctx.cmd(command)
    ctx.cmd(f"kill @e[tag={ENTITY_TAG}]")
    ctx.fill_boxes(cells.interior - engine, AIR)
    for part in (b.floor, b.solid, b.attached):
        for cell, block in sorted(part.items()):
            ctx.setblock(cell, block)
    ctx.cmd(summon_recall(place.frame, *place.recall, tags=(ENTITY_TAG, RECALL_TAG)))
    ctx.cmd(
        fittings.display(
            (ENTITY_TAG, BOARD_TAG), place.display, place.yaw, LABELS["dead"], 3.0
        )
    )
    # the pack's own idea of the room, if the pack is installed
    ctx.function(f"dome/{INDEX}/reset")
    ctx.advance(10)
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    return (
        f"{dome.name}: {len(b.everything())} blocks: plaque, logbook, recall "
        "button, the Signal Board (4 lamps, 4 bells, 3 LINE lamps), the main "
        "console and 2 wing desks, the battery house and the mast with their "
        "switches; the exchange: 2 relay racks, the operator's deck, 2 wings, "
        "the catwalk, the loft, the recorder"
    )


# ----------------------------------------------------------- the functions

#: the board's words, by what the room is doing
LABELS = {
    "dead": label_text("NO LINE", "red", bold="true"),
    "half": label_text("NO LINE: ONE SWITCH MORE", "red", bold="true"),
    "ready": label_text("READY: PRESS CALL", "gold", bold="true"),
    "wrong": label_text("WRONG: LISTEN AGAIN", "red", bold="true"),
    "dropped": label_text("LINE DROPPED: LISTEN AGAIN", "red", bold="true"),
    "idle": label_text("NO ANSWER: PRESS CALL", "red", bold="true"),
    "open": label_text("LINE OPEN", "green", bold="true"),
}


def _s(name: str) -> str:
    return f"#sig.{name} {OBJ}"


def _set(name: str, value: int) -> str:
    return f"scoreboard players set {_s(name)} {value}"


def _add(name: str, value: int = 1) -> str:
    return f"scoreboard players add {_s(name)} {value}"


def _op(name: str, op: str, other: str) -> str:
    return f"scoreboard players operation {_s(name)} {op} {other} {OBJ}"


def _is(name: str, what: int | str) -> str:
    return f"if score {_s(name)} matches {what}"


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


def _setblock(cell: Cell, block: str) -> str:
    return f"setblock {_xyz(cell)} {block}"


def functions(pack: dp.Pack) -> None:
    """the Signal Room's functions (see the module docstring)"""
    dome = layout.DOMES[INDEX]
    place = room(dome)
    fr = place.frame
    base = f"dome/{INDEX}"
    here = game.in_dome(INDEX)
    open_dome = f"#d{INDEX} {OBJ}"
    pack.constants(OBJ, 4, 5, 100, 200, PERIOD)

    def fid(name: str) -> str:
        return pack.id(f"{base}/{name}")

    def run(name: str) -> str:
        return f"function {fid(name)}"

    def sound(name: str, cell: Cell, volume: float = 1, pitch: float = 1) -> str:
        return f"playsound minecraft:{name} block {here} {_xyz(cell)} {volume} {pitch}"

    def say(text: str, colour: str = "yellow") -> str:
        return f'tellraw {here} {{text:{snbt(text)},color:"{colour}"}}'

    def label(text: str) -> str:
        return fittings.text_line(BOARD_TAG, text)

    board = place.signals[1].pane  # where the board's sounds come from
    console = place.key(CALL, 1).cell

    # -- the values of the level in force
    pack.function(
        f"{base}/scale",
        [
            _set("n", N),
            _op("n", "*=", "#diff.seq"),
            _add("n", 50),
            _op("n", "/=", "#100"),
            _add("n", EXTRA),
            _op("period", "=", "#diff.timer"),
            _add("period", 100),
            _op("period", "*=", f"#{PERIOD}"),
            _op("period", "/=", "#200"),
            _op("on", "=", "#sig.period"),
            f"scoreboard players remove {_s('on')} {GAP}",
            _set("wait", WAIT),
            _op("wait", "*=", "#diff.timer"),
            _op("wait", "/=", "#100"),
            _set("ear", 0),
            f"execute if score #active {OBJ} matches {EAR_FROM}.. run {_set('ear', 1)}",
            _op("lvl", "=", "#active"),
        ],
    )

    # -- the sequence: n keys, never the same twice running, never three
    # running for one desk; ``new`` is the key being chosen, ``p1`` and
    # ``p2`` the two before it
    pack.function(
        f"{base}/roll_any",  # any key but the last
        [
            f"execute store result score {_s('r')} run random value 1..3",
            _op("new", "=", "#sig.p1"),
            _op("new", "+=", "#sig.r"),
            f"scoreboard players remove {_s('new')} 1",
            _op("new", "%=", "#4"),
            _add("new", 1),
        ],
    )
    pack.function(
        f"{base}/roll_other",  # one of the other desk's two keys
        [
            f"execute store result score {_s('new')} run random value 1..2",
            f"execute {_is('p1', '1..2')} run {_add('new', 2)}",
        ],
    )
    pack.function(
        f"{base}/roll_next",
        [
            _set("same", 0),
            f"execute {_is('p1', '1..2')} {_is('p2', '1..2')} run {_set('same', 1)}",
            f"execute {_is('p1', '3..4')} {_is('p2', '3..4')} run {_set('same', 1)}",
            f"execute {_is('p1', 0)} store result score {_s('new')} "
            "run random value 1..4",
            f"execute {_is('p1', '1..')} {_is('same', 0)} run {run('roll_any')}",
            f"execute {_is('same', 1)} run {run('roll_other')}",
            *(
                f"execute {_is('i', j)} run {_op(f's{j}', '=', '#sig.new')}"
                for j in range(MAX_N)
            ),
            _op("p2", "=", "#sig.p1"),
            _op("p1", "=", "#sig.new"),
            _add("i"),
        ],
    )
    pack.function(
        f"{base}/roll",
        [
            _set("i", 0),
            _set("p1", 0),
            _set("p2", 0),
            *(
                f"execute if score {_s('i')} < {_s('n')} run {run('roll_next')}"
                for _ in range(MAX_N)
            ),
            _set("i", 0),
        ],
    )
    pack.function(
        f"{base}/get",  # the key at the place ``i``
        [
            f"execute {_is('i', j)} run {_op('cur', '=', f'#sig.s{j}')}"
            for j in range(MAX_N)
        ],
    )

    # -- a signal: its contact closed (lamps and bell) and its pilots lit;
    # by ear, the second contact (the bell alone); ``off``: all open
    for sig in place.signals:
        bell = [
            sound("block.note_block.bell", sig.bell, 3, 2 ** ((sig.note - 12) / 12))
        ]
        pack.function(
            f"{base}/on_{sig.k}",
            [
                _setblock(sig.hub, POWER),
                *(_setblock(cell, sig.glow) for cell in sig.pilots),
                *(bell if PACK_BELLS else []),
                _add(f"on{sig.k}"),
            ],
        )
        pack.function(
            f"{base}/note_{sig.k}",
            [
                _setblock(sig.contact, POWER),
                *(bell if PACK_BELLS else []),
                _add(f"ear{sig.k}"),
            ],
        )
        # opened first, so that the same key twice rings twice
        pack.function(f"{base}/sig_{sig.k}", [run("off"), run(f"on_{sig.k}")])
    pack.function(
        f"{base}/off",
        [
            *(_setblock(sig.hub, COPPER) for sig in place.signals),
            *(_setblock(sig.contact, COPPER) for sig in place.signals),
            *(_setblock(c, sig.dark) for sig in place.signals for c in sig.pilots),
        ],
    )
    pack.function(
        f"{base}/show",  # the key pressed, shown
        [
            *(
                f"execute {_is('key', sig.k)} run {run(f'sig_{sig.k}')}"
                for sig in place.signals
            ),
            _op("lt", "=", "#sig.on"),
        ],
    )
    # everything that sounds or shows stilled (``empty``, ``reset``, a
    # switch opened): the contacts open, the clocks stopped
    pack.function(f"{base}/quiet", [run("off"), _set("lt", 0), _set("fan", 0)])

    # -- the board's words
    pack.function(
        f"{base}/label_dead",
        [
            label(LABELS["dead"]),
            f"execute {_is('pa', 1)} run {label(LABELS['half'])}",
            f"execute {_is('pb', 1)} run {label(LABELS['half'])}",
        ],
    )
    pack.function(
        f"{base}/label_listen",
        [
            f"execute {_is('round', j)} run "
            + label(label_text(f"LISTEN: ROUND {j} OF {ROUNDS}", "aqua", bold="true"))
            for j in range(1, ROUNDS + 1)
        ],
    )
    pack.function(
        f"{base}/label_answer",
        [
            f"execute {_is('i', j)} run "
            + label(label_text(f"ANSWER: KEY {j + 1}", "green", bold="true"))
            for j in range(MAX_N)
        ],
    )
    pack.function(
        f"{base}/label_won",
        [
            f"execute {_is('line', j)} run "
            + label(label_text(f"RIGHT: LINE {j} OF {ROUNDS}", "green", bold="true"))
            for j in range(1, ROUNDS + 1)
        ],
    )

    # -- power: the two switches, read from the levers
    hint = fittings.hint(
        pack,
        INDEX,
        "power",
        "The board is dead. BATTERY SWITCH on the floor, AERIAL SWITCH up the mast.",
        75,
    )
    levers = (("pa", place.battery, "battery"), ("pb", place.aerial, "aerial"))
    power = []
    for name, cell, what in levers:
        now = f"{name}.now"
        power += [
            _set(now, 0),
            f"execute if block {_xyz(cell)} minecraft:lever[powered=true] "
            f"run {_set(now, 1)}",
            f"execute unless score {_s(name)} = {_s(now)} run {run(f'power_{what}')}",
        ]
        pack.function(
            f"{base}/power_{what}",
            [
                _op(name, "=", f"#sig.{now}"),
                f"execute {_is(name, 1)} run "
                + sound("block.beacon.activate", cell, 1, 1.4),
                f"execute {_is(name, 0)} run "
                + sound("block.beacon.deactivate", cell, 1, 1.4),
                hint.progress,
                run("line_check"),
            ],
        )
    pack.function(f"{base}/power", power)
    pack.function(
        f"{base}/line_check",
        [
            _set("up", 0),
            f"execute {_is('pa', 1)} {_is('pb', 1)} run {_set('up', 1)}",
            f"execute {_is('up', 0)} {_is('st', '1..5')} run {run('cut')}",
            f"execute {_is('up', 0)} {_is('st', 0)} run {run('label_dead')}",
            f"execute {_is('up', 1)} {_is('st', 0)} run {run('ready')}",
        ],
    )
    # a switch opened: the round in progress is lost, the LINE lamps stay
    pack.function(
        f"{base}/cut",
        [run("quiet"), _set("st", 0), _set("t", 0), _set("i", 0), run("label_dead")],
    )
    pack.function(
        f"{base}/ready",
        [
            _set("st", 1),
            _set("t", 0),
            _set("i", 0),
            label(LABELS["ready"]),
            sound("block.note_block.chime", board, 2, 1.2),
        ],
    )

    # -- the keys
    pack.function(
        f"{base}/press",
        [
            f"execute {_is('st', 0)} run "
            + sound("block.dispenser.fail", console, 0.6, 1.2),
            f"execute {_is('st', 0)} run return 0",
            f"execute {_is('key', CALL)} run {run('press_call')}",
            f"execute {_is('key', CALL)} run return 0",
            # free play: ready, or solved (once the fanfare is over)
            f"execute {_is('st', 1)} run {run('show')}",
            f"execute {_is('st', 6)} {_is('fan', 0)} run {run('show')}",
            f"execute {_is('st', 3)} run {run('answer')}",
        ],
    )
    # CALL: start the round, or say it again; nothing while it is sending
    pack.function(
        f"{base}/press_call",
        [
            _op("was", "=", "#sig.st"),
            f"execute {_is('was', 1)} run {run('call')}",
            f"execute {_is('was', 3)} run {run('call')}",
        ],
    )
    pack.function(
        f"{base}/call",
        [
            run("quiet"),
            _set("st", 2),
            _set("i", 0),
            _set("t", LEAD),
            _set("tx", 0),
            _add("calls"),
            _set("byear", 0),
            f"execute {_is('ear', 1)} {_is('round', ROUNDS)} run {_set('byear', 1)}",
            run("label_listen"),
        ],
    )
    pack.function(
        f"{base}/send",
        [
            f"execute if score {_s('i')} >= {_s('len')} run {run('listen')}",
            f"execute {_is('st', 3)} run return 0",
            run("get"),
            run("off"),
            *(
                f"execute {_is('cur', sig.k)} {_is('byear', 0)} run {run(f'on_{sig.k}')}"
                for sig in place.signals
            ),
            *(
                f"execute {_is('cur', sig.k)} {_is('byear', 1)} "
                f"run {run(f'note_{sig.k}')}"
                for sig in place.signals
            ),
            _op("lt", "=", "#sig.on"),
            # what was sent, for whoever checks: a digit in base 5 a signal
            _op("tx", "*=", "#5"),
            _op("tx", "+=", "#sig.cur"),
            _add("i"),
            _op("t", "=", "#sig.period"),
        ],
    )
    walk = f"execute {_is('form', 2)} run {_add('t', WALK)}"
    pack.function(
        f"{base}/listen",
        [
            run("quiet"),
            _set("st", 3),
            _set("i", 0),
            _set("last", 0),
            _op("t", "=", "#sig.wait"),
            walk,
            run("label_answer"),
        ],
    )
    pack.function(
        f"{base}/answer",
        [
            # a key held, or clicked twice, is read again a few ticks on: the
            # same key twice running is never the answer (``sequence_problems``)
            f"execute if score {_s('key')} = {_s('last')} run return 0",
            run("get"),
            _set("ok", 0),
            f"execute if score {_s('key')} = {_s('cur')} run {_set('ok', 1)}",
            f"execute {_is('ok', 1)} run {run('right')}",
            f"execute {_is('ok', 0)} run {run('wrong')}",
        ],
    )
    pack.function(
        f"{base}/right",
        [
            run("show"),
            _op("last", "=", "#sig.key"),
            _add("i"),
            _op("t", "=", "#sig.wait"),
            walk,
            f"execute if score {_s('i')} >= {_s('len')} run {run('won')}",
            f"execute {_is('st', 3)} run {run('label_answer')}",
        ],
    )
    # a round won is kept from this moment, whatever happens next
    pack.function(
        f"{base}/won",
        [
            _add("line"),
            _set("miss", 0),
            sound("entity.player.levelup", board, 1, 1.6),
            f"execute {_is('line', f'{ROUNDS}..')} run {run('done')}",
            f"execute {_is('st', 3)} run {run('next')}",
        ],
    )
    pack.function(
        f"{base}/next",
        [
            _add("round"),
            _add("len"),
            _set("st", 4),
            _set("t", PAUSE),
            run("label_won"),
        ],
    )
    pack.function(
        f"{base}/fail",  # this round's presses lost: the same round again
        [
            run("quiet"),
            sound("block.note_block.bass", board, 3, 0.5),
            _add("miss"),
            _set("st", 5),
            _set("t", PAUSE),
            f"execute {_is('miss', 3)} run "
            + say("Press CALL to hear it again. Count them out loud.", "gray"),
        ],
    )
    pack.function(f"{base}/wrong", [run("fail"), label(LABELS["wrong"])])
    pack.function(f"{base}/dropped", [run("fail"), label(LABELS["dropped"])])
    # the clock run out: in the middle of an answer, the same round again;
    # with no key pressed at all, nobody is answering: wait for CALL
    pack.function(
        f"{base}/idle",
        [
            run("quiet"),
            _set("st", 1),
            _set("t", 0),
            label(LABELS["idle"]),
            sound("block.beacon.deactivate", board, 2, 0.8),
        ],
    )
    pack.function(
        f"{base}/timeout",
        [
            f"execute {_is('i', 0)} run {run('idle')}",
            f"execute {_is('st', 3)} run {run('dropped')}",
        ],
    )
    pack.function(
        f"{base}/done",
        [
            _set("st", 6),
            _set("t", 0),
            _set("lt", 0),
            _set("fan", 1),
            label(LABELS["open"]),
        ],
    )
    # the line open: the four signals run up the scale, twice
    steps = 2 * len(place.signals)
    pack.function(
        f"{base}/fanfare",
        [
            *(
                f"execute {_is('fan', 1 + FANFARE * j)} "
                f"run {run(f'sig_{j % len(place.signals) + 1}')}"
                for j in range(steps)
            ),
            _add("fan"),
            f"execute {_is('fan', f'{FANFARE * steps + 2}..')} run {run('quiet')}",
        ],
    )

    # -- the clocks
    pack.function(
        f"{base}/lamp_out",
        [
            f"scoreboard players remove {_s('lt')} 1",
            f"execute {_is('lt', 0)} run {run('off')}",
        ],
    )
    pack.function(
        f"{base}/step",
        [
            f"execute {_is('lt', '1..')} run {run('lamp_out')}",
            f"execute {_is('fan', '1..')} run {run('fanfare')}",
            _op("was", "=", "#sig.st"),
            f"execute {_is('was', '2..5')} run scoreboard players remove {_s('t')} 1",
            f"execute {_is('was', 2)} {_is('t', '..0')} run {run('send')}",
            f"execute {_is('was', 3)} {_is('t', '..0')} run {run('timeout')}",
            f"execute {_is('was', '4..5')} {_is('t', '..0')} run {run('call')}",
        ],
    )

    # -- the desks: the keys moved to the form that is wanted. Only ``tick``
    # calls this, and never while a round is being sent or answered
    def signs(form: int) -> list[str]:
        return [
            f"data merge block {_xyz(cell)} {{{sign_text(status_sign(desk, form))}}}"
            for desk, cell in place.status.items()
        ]

    for form, name in ((1, "solo"), (2, "duo")):
        there, gone = place.desk(form), place.desk(3 - form)
        pack.function(
            f"{base}/desks_{name}",
            [
                *(_setblock(key.cell, AIR) for key in gone),
                *(
                    f"execute unless block {_xyz(key.cell)} {BUTTON} "
                    f"run {_setblock(key.cell, button(fr))}"
                    for key in there
                ),
                *signs(form),
            ],
        )
    pack.function(
        f"{base}/desks",
        [
            f"execute {_is('want', 1)} {_is('form', 2)} run "
            + say("One operator: the line is whole. Use the main console."),
            f"execute {_is('want', 2)} run "
            + say("Two operators: the line is split. A desk each, port and starboard."),
            f"execute {_is('want', 1)} run {run('desks_solo')}",
            f"execute {_is('want', 2)} run {run('desks_duo')}",
            _op("form", "=", "#sig.want"),
        ],
    )
    later = say("The desks change over when this round is done.", "gray")
    for form, name in ((1, "solo"), (2, "duo")):
        pack.function(
            f"{base}/{name}",
            [
                _set("want", form),
                f"execute {_is('st', '2..3')} unless score {_s('form')} matches {form} "
                f"run {later}",
            ],
        )

    # -- what works by itself, and the lamps that follow scores (no part
    # of the puzzle reads any of it)
    lit, dark = f"{BULB}[lit=true]", f"{BULB}[lit=false]"
    lamps = []
    for name, ramp in (("pa", "ca"), ("pb", "cb")):
        lamps += [
            f"execute {_is(name, 1)} {_is(ramp, f'..{4 * RAMP - 1}')} run {_add(ramp)}",
            f"execute {_is(name, 0)} run {_set(ramp, 0)}",
        ]
    battery, aerial = place.power_pilots
    lamps += fittings.gauge_lines(place.cable, _s("ca"), RAMP, lit, dark)
    lamps += fittings.gauge_lines((battery,), _s("ca"), 3 * RAMP, PILOT_ON, CHISELED)
    lamps += fittings.gauge_lines(place.mast, _s("cb"), RAMP, lit, dark)
    lamps += fittings.gauge_lines((aerial,), _s("cb"), 3 * RAMP, PILOT_ON, CHISELED)
    lamps += fittings.gauge_lines(place.line, _s("line"), 1, lit, dark)
    pack.function(f"{base}/lamps", lamps)
    # the sweep: ``pos`` is the bulb that is lit, or -1 for none
    draw = []
    for j, cell in enumerate(place.sweep):
        at = _xyz(cell)
        draw += [
            f"execute {_is('pos', j)} unless block {at} {lit} run setblock {at} {lit}",
            f"execute unless score {_s('pos')} matches {j} unless block {at} {dark} "
            f"run setblock {at} {dark}",
        ]
    pack.function(f"{base}/sweep_draw", draw)
    around = len(place.sweep)
    pack.function(
        f"{base}/sweep_step",
        [
            _set("sw", 0),
            # backwards while the Engine sends
            f"execute {_is('st', 2)} run {_add('pos', around - 1)}",
            f"execute unless score {_s('st')} matches 2 run {_add('pos', 1)}",
            f"execute {_is('pos', f'{around}..')} run "
            f"scoreboard players remove {_s('pos')} {around}",
            run("sweep_draw"),
        ],
    )
    pack.function(f"{base}/sweep_off", [_set("pos", -1), run("sweep_draw")])
    # the recorder: the tape shifts a column along, a random one fed in
    tape = []
    tape_lit, tape_dark = f"{TAPE_BULB}[lit=true]", f"{TAPE_BULB}[lit=false]"
    for to, of in zip(reversed(place.tape), reversed(place.tape[:-1]), strict=False):
        for a, b in zip(of, to, strict=True):
            tape += [
                f"execute if block {_xyz(a)} {tape_lit} run {_setblock(b, tape_lit)}",
                f"execute unless block {_xyz(a)} {tape_lit} "
                f"run {_setblock(b, tape_dark)}",
            ]
    for cell in place.tape[0]:
        tape += [
            f"execute store result score {_s('r')} run random value 0..1",
            f"execute {_is('r', 1)} run {_setblock(cell, tape_lit)}",
            f"execute {_is('r', 0)} run {_setblock(cell, tape_dark)}",
        ]
    pack.function(f"{base}/tape", [_set("tw", 0), _add("taped"), *tape])
    pack.function(f"{base}/book", [_setblock(place.lectern, logbook(fr))])
    no_book = f"if block {_xyz(place.lectern)} minecraft:lectern[has_book=false]"
    pack.function(
        f"{base}/dress",
        [
            run("lamps"),
            _add("sw"),
            f"execute {_is('pb', 1)} {_is('st', 2)} {_is('sw', f'{SWEEP_FAST}..')} "
            f"run {run('sweep_step')}",
            f"execute {_is('pb', 1)} {_is('sw', f'{SWEEP}..')} run {run('sweep_step')}",
            f"execute {_is('pb', 0)} {_is('pos', '0..')} run {run('sweep_off')}",
            _add("tw"),
            f"execute {_is('tw', f'{TAPE}..')} run {run('tape')}",
            f"execute {_is('tw', 0)} {no_book} run {run('book')}",
        ],
    )

    # -- the hooks
    closed = [
        fittings.lever_hold_line(cell, switch(place, cell, True), _is("st", 6))
        for cell in (place.battery, place.aerial)
    ]
    keys = [
        fittings.button_line(
            pack,
            f"{base}/{key.path}",
            key.cell,
            button(fr),
            [_set("key", key.what), run("press")],
        )
        for key in place.keys
    ]
    pack.function(
        f"{base}/tick",
        [
            # the line is open: the dome is solved. The room's one call to
            # the core, which answers it once (the dome is then solved, not
            # open); from the tick, so that a line found open is always told
            f"execute if score {open_dome} matches 1 {_is('st', 6)} "
            f"run function {pack.id(f'dome/{INDEX}/solved')}",
            # the exchange's machinery, whether or not there is a puzzle
            run("dress"),
            f"execute unless score {open_dome} matches 1..2 run return 0",
            # a room never armed has no sequence: nothing could be answered
            f"execute if score {open_dome} matches 1 unless score {_s('live')} "
            f"matches 1 run {run('arm')}",
            # a solved room has no ``solo`` or ``duo``: it follows the core
            f"execute if score {open_dome} matches 2 "
            f"if score #form{INDEX} {OBJ} matches 1..2 "
            f"run {_op('want', '=', f'#form{INDEX}')}",
            # the line stays open once it is: the switches held closed
            *closed,
            run("power"),
            # a change of form waits for the round
            f"execute unless score {_s('form')} = {_s('want')} "
            f"unless score {_s('st')} matches 2..3 run {run('desks')}",
            *keys,
            run("step"),
            f"execute {_is('st', 0)} run {hint.tick}",
        ],
    )
    pack.function(
        f"{base}/arm",
        [
            run("reset"),
            # (``reset`` leaves the solo desks: the form the core has is kept)
            f"execute if score #form{INDEX} {OBJ} matches 2 run {_set('want', 2)}",
            run("scale"),
            run("roll"),
            _set("round", 1),
            _op("len", "=", "#sig.n"),
            f"scoreboard players remove {_s('len')} {ROUNDS - 1}",
            _set("live", 1),
            hint.arm,
        ],
    )
    # a new level for a room already armed: the rounds still to win sent
    # at the new level; the switches and the LINE lamps kept
    pack.function(
        f"{base}/rearm",
        [
            run("quiet"),
            run("scale"),
            run("roll"),
            _op("round", "=", "#sig.line"),
            _add("round"),
            _op("len", "=", "#sig.n"),
            f"scoreboard players remove {_s('len')} {ROUNDS - 1}",
            _op("len", "+=", "#sig.line"),
            _set("miss", 0),
            _set("i", 0),
            _set("t", 0),
            _set("st", 0),
            run("line_check"),
            hint.arm,
        ],
    )
    pack.function(
        f"{base}/enter",
        [
            f"execute if score {open_dome} matches 1 unless score {_s('live')} "
            f"matches 1 run {run('arm')}",
            # a new level: only for the first into an empty room, never
            # under the hands of someone already at the keys
            f"execute if score {open_dome} matches 1 if score #first {OBJ} matches 1 "
            f"unless score {_s('lvl')} = #active {OBJ} run {run('rearm')}",
            f"execute if score {open_dome} matches 1 {_is('st', 0)} run tellraw @s "
            '{text:"The board is dark. The brass plaque says what to do.",'
            'color:"gray",italic:true}',
        ],
    )
    # nobody left: the board goes quiet and a round in progress is dropped;
    # the switches, the LINE lamps and the sequence are kept
    pack.function(
        f"{base}/empty",
        [
            run("quiet"),
            f"execute {_is('st', '2..5')} run {run('ready')}",
        ],
    )
    zeroed = ("st", "live", "lvl", "pa", "pb", "up", "ca", "cb", "round", "len")
    zeroed += ("i", "t", "key", "miss", "line", "tx", "byear", "sw", "tw", "calls")
    zeroed += ("last",)
    pack.function(
        f"{base}/reset",
        [
            # the switches taken out and put back open (a lever only set
            # over itself tells nothing round it)
            *(
                line
                for cell in (place.battery, place.aerial)
                for line in fittings.lever_put_lines(cell, switch(place, cell))
            ),
            run("quiet"),
            *(_set(name, 0) for name in zeroed),
            _set("want", 1),
            run("desks_solo"),
            _set("form", 1),
            run("lamps"),
            run("sweep_off"),
            run("label_dead"),
            f"execute {no_book} run {run('book')}",
        ],
    )


# --------------------------------------------------------------- the check

S1, S2 = "st.s5a", "st.s5b"


def check(ctx: Any) -> list[str]:
    """
    Work the Signal Room in place over RCON. A player is stood in for by
    an armour stand that the core counts (``game.STANDIN``), put at the
    entrance to come in; a switch is thrown and a key pressed by setting
    the lever or the button as a hand would leave it. Leaves the room and
    its tunnel reset, the game's scores as they were and no stand-in
    behind. It resets this dome and its tunnel only, never the game.

    What a stand-in and a block set by command cannot prove (all for the
    play-test): a hand on a key or a switch. A button set pressed by
    command tells only its own neighbours, and a hand's press tells the
    block under it too: that no bulb or lamp then flips is checked on the
    plan alone (``contact_problems``). That a key pressed by hand while a
    function puts it back each tick neither sticks nor doubles. That a
    bell is heard and the four are told apart: the note blocks are read
    ``powered``, not heard. The lamps' colours through their glass, and
    the board's words the right way round: their data is read, not seen.
    Anything aimed at players (chat, sounds). The climb to the loft on
    real feet: the walks are checked on the plan alone.
    """
    game_checks.no_run(ctx)
    dome = ctx.layout.DOMES[INDEX]
    tunnel = ctx.layout.TUNNELS[INDEX]
    place = room(dome)
    fr = place.frame
    problems: list[str] = []
    scan = game_checks.SCAN
    base = f"dome/{INDEX}"
    after_solo = game.SOLO_AFTER * game.SCAN_TICKS + 2 * scan
    lit = f"{BULB}[lit=true]"

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def get(name: str) -> int:
        return ctx.score(f"#sig.{name}") or 0

    def state(*names: str) -> dict[str, int]:
        return {n: get(n) for n in names}

    def says(what: str, word: str) -> None:
        text = ctx.data(f"entity @e[tag={BOARD_TAG},limit=1] text")
        if word not in text:
            problems.append(f"{what}: the board says {text!r}, not {word}")

    outside = middle(tunnels.at(ctx.layout.TUNNELS[INDEX - 1], 8, 0, 1))
    entrance = middle(domes.entrance(dome)[:3])

    def stand(tag: str, where: str) -> None:
        game_checks.stand_at(ctx, tag, where)

    def come_in(tag: str = S1) -> None:
        """a stand-in out of the dome and in again: a new entry"""
        stand(tag, outside)
        ctx.advance(game_checks.EMPTY)  # (a dome is empty 3 s after its last player)
        stand(tag, entrance)

    def throw(cell: Cell, on: bool = True) -> None:
        ctx.setblock(cell, switch(place, cell, on))
        ctx.advance(2)

    def power() -> None:
        throw(place.battery)
        throw(place.aerial)

    def press(what: int, desk: str | None = None) -> None:
        """a key of the desks as they stand, set pressed as a hand leaves
        it, and read by the room"""
        keys = [k for k in place.desk(get("form")) if k.what == what]
        key = next(k for k in keys if desk in (None, k.desk))
        ctx.setblock(key.cell, button(fr, True))
        ctx.advance(2)
        # (let go, or taken away: the last key of a round may move the desks)
        if ctx.is_block(key.cell, button(fr, True)):
            problems.append(f"the {key.desk} desk's key {what} was not let go")

    def until(done: Any, ticks: int, step: int = 2) -> bool:
        for _ in range(ticks // step + 1):
            if done():
                return True
            ctx.advance(step)
        return done()

    def sequence() -> list[int]:
        return [get(f"s{j}") for j in range(get("n"))]

    def closed() -> set[int]:
        """the signals whose contact is closed with all its lamps lit and
        its bell powered"""
        return {
            s.k
            for s in place.signals
            if ctx.is_block(s.hub, POWER)
            and all(ctx.is_block(c, f"{LAMP}[lit=true]") for c in s.lamps)
            and ctx.is_block(s.bell, f"{NOTE}[powered=true]")
        }

    def lamps_lit() -> int:
        return sum(
            ctx.is_block(c, f"{LAMP}[lit=true]") for s in place.signals for c in s.lamps
        )

    def count(cells, block: str = lit) -> int:
        return sum(ctx.is_block(c, block) for c in cells)

    def keys_there(form: int) -> bool:
        there = count((k.cell for k in place.desk(form)), button(fr))
        gone = count((k.cell for k in place.desk(3 - form)), AIR)
        return (there, gone) == (len(place.desk(form)), len(place.desk(3 - form)))

    def listen(what: str) -> list[int]:
        """a sending waited for and watched to its end, the room left
        listening: the round's keys. The signals are told by the room's
        own record of what it sent (``tx``); a contact seen closed on the
        way must be one of them (the game runs on between two reads, so
        not every one is seen)"""
        until(lambda: get("st") in (2, 3), PAUSE + 20)
        seen: set[int] = set()

        def sending() -> bool:
            seen.update(closed())
            return get("st") != 2

        keys = sequence()[: get("len")]
        until(sending, LEAD + (len(keys) + 2) * get("period") + 40, 1)
        expect(f"{what}: listening after the sending", get("st"), 3)
        expect(f"{what}: the signals sent, in order", get("tx"), sent(keys))
        if not seen <= set(keys):
            problems.append(f"{what}: signals {seen} seen closed, of {keys} sent")
        # (a lamp is held 6 ticks or more below level 8: some must be seen)
        if not seen and not get("byear") and get("on") >= 6:
            problems.append(f"{what}: no signal seen closed, of {keys} sent")
        return keys

    def answer(what: str) -> list[int]:
        """the round's keys pressed in turn, on the desks as they stand"""
        keys = listen(what)
        for k in keys:
            press(k)
        ctx.advance(2)
        return keys

    def wrong(keys: list[int]) -> int:
        """a key that is not the first of a round"""
        return keys[0] % 4 + 1

    def as_built(what: str) -> None:
        """every block of the room is as ``reset`` leaves it (a block of a
        clock or of the tape: the same block, in whatever state; bars by
        name, as the game joins them)"""
        b = room_blocks(dome)
        bad = []
        for cell, block in b.everything().items():
            loose = cell in b.moving or any(word in block for word in JOINED)
            want = _name(block) if loose else block.partition("{")[0]
            if not ctx.is_block(cell, want):
                bad.append(cell)
        bad += [cell for cell in b.clear if not ctx.is_block(cell, AIR)]
        if bad:
            problems.append(f"{what}: {len(bad)} blocks not as built: {bad[:6]}")
        names = ("st", "live", "pa", "pb", "line", "round", "form", "want", "lt")
        want = dict.fromkeys(names, 0) | {"form": 1, "want": 1}
        expect(f"{what}: the scores", state(*names), want)
        says(what, "NO LINE")
        if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
            problems.append(f"{what}: the logbook is not on the lectern")

    def racks_run(what: str) -> None:
        """the relay racks, which nothing starts or stops: each lamp of
        both chases seen lit and unlit over 6 s"""
        solid = dressing_blocks(dome).solid
        chase = [cell for cell, block in solid.items() if _name(block) == BULB]
        seen: list[set[bool]] = [set() for _ in chase]
        for _ in range(30):
            ctx.advance(4)
            for cell, states in zip(chase, seen, strict=True):
                states.add(ctx.is_block(cell, lit))
        if len(chase) != 8 or any(states != {True, False} for states in seen):
            problems.append(f"{what}: the racks' lamps, lit or not: {seen}")

    def solved() -> bool:
        return ctx.score(f"#d{INDEX}") == 2

    def unsolve() -> None:
        """the room and its tunnel put back, the dome open and unsolved (a
        stand-in in the dome arms it anew at once)"""
        ctx.function(f"tunnel/{INDEX}/reset")
        ctx.function(f"{base}/reset")
        ctx.set_score(f"#d{INDEX}", 1)
        ctx.set_score(f"#d{INDEX + 1}", saved[f"#d{INDEX + 1}"] or 0)
        ctx.set_score("#solved", saved["#solved"] or 0)

    # ---- before: nobody about, the room and its tunnel reset, the dome open
    names = (f"#d{INDEX}", f"#d{INDEX + 1}", "#solved")
    others = (f"#d{INDEX - 1}", f"#t{INDEX - 1}", f"#t{INDEX + 1}", "#run", "#secs")
    saved = game_checks.scores(ctx, *names)
    saved_level = game_checks.save_level(ctx)
    beside = game_checks.scores(ctx, *others)
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(after_solo)
    if (n := ctx.score("#players")) or ctx.score(f"#form{INDEX}"):
        return [f"{n} players or stand-ins of another check are in the game"]
    unsolve()
    ctx.advance(scan)
    as_built("built")
    racks_run("nobody in")
    for tag, what in ((RECALL_TAG, "recall button"), (BOARD_TAG, "board's words")):
        if ctx.count(f"@e[tag={tag}]") != 1:
            problems.append(f"not one entity for the {what}")
    taped = get("taped")
    ctx.advance(3 * TAPE)
    expect("the recorder's steps with nobody in", get("taped") - taped, 0)

    # ---- solo, the success path
    stand(S1, entrance)
    got = state("live", "form", "st", "round")
    expect("solo, entered", got, {"live": 1, "form": 1, "st": 0, "round": 1})
    level = ctx.score("#active") or game.DEFAULT_LEVEL
    values = scaled(level)
    expect("the level's values", state(*values), values)
    expect("the first round's length", get("len"), values["n"] - ROUNDS + 1)
    first = sequence()
    problems += [f"the sequence: {p}" for p in sequence_problems(first)]
    ctx.advance(3 * TAPE)
    if get("taped") - taped < 2:
        problems.append("the recorder's tape did not move with someone in the dome")
    # no line: a key does nothing but come back out
    press(1)
    press(CALL)
    expect("keys with no line", (get("st"), closed(), lamps_lit()), (0, set(), 0))
    # the switches, either first: here the aerial, then the battery
    throw(place.aerial)
    expect("the aerial alone", state("pa", "pb", "st"), {"pa": 0, "pb": 1, "st": 0})
    says("one switch closed", "ONE SWITCH MORE")
    throw(place.battery)
    ctx.advance(4 * RAMP + 2)
    expect("both switches", state("pa", "pb", "st"), {"pa": 1, "pb": 1, "st": 1})
    expect("the cables' bulbs lit", count((*place.cable, *place.mast)), 4)
    expect("the console's power pilots", count(place.power_pilots, PILOT_ON), 2)
    says("both switches closed", "READY")
    swept = set()
    for _ in range(12):
        ctx.advance(SWEEP // 2)
        swept.add(tuple(ctx.is_block(c, lit) for c in place.sweep))
    if len(swept) < 3 or any(sum(s) != 1 for s in swept):
        problems.append(
            f"the sweep: {len(swept)} states seen, not one bulb lit in each"
        )
    # free play: each key closes its contact (lamps, bell, pilots), then opens
    for sig in place.signals:
        ctx.setblock(place.key(sig.k, 1).cell, button(fr, True))
        if not until(lambda k=sig.k: closed() == {k}, 6, 1):
            problems.append(f"free play: key {sig.k} closed {closed()}")
        expect(f"free play: the pilots of key {sig.k}", count(sig.pilots, sig.glow), 3)
        ctx.advance(values["on"] + 8)
        got = (closed(), lamps_lit(), count(sig.pilots, sig.dark))
        expect(f"free play: key {sig.k} let go", got, (set(), 0, 3))
    expect("free play leaves the room ready", get("st"), 1)
    # three rounds, each one longer, answered right
    press(CALL)
    expect("CALL: sending", state("st", "round"), {"st": 2, "round": 1})
    for won in range(1, ROUNDS + 1):
        keys = answer(f"solo round {won}")
        expect(f"solo round {won}: its keys", keys, first[: len(first) - ROUNDS + won])
        got = (get("line"), count(place.line))
        expect(f"solo round {won}: the LINE lamps", got, (won, won))
    expect("solo: solved", (get("st"), solved()), (6, True))
    expect("the sequence through the rounds", sequence(), first)
    says("solved", "LINE OPEN")
    problems.extend(game_checks.pull_pump(ctx, INDEX))
    expect("its tunnel at the solve", ctx.score(f"#t{INDEX}") in (1, 2), True)
    ctx.advance(tunnels.event_ticks(tunnel) + 60)
    got = game_checks.scores(ctx, f"#t{INDEX}", f"#d{INDEX + 1}")
    expect(
        "its tunnel open, the next dome open",
        got,
        {f"#t{INDEX}": 2, f"#d{INDEX + 1}": 1},
    )
    problems += [f"tunnel open: {p}" for p in domes.check_shell(ctx, dome, False)]
    # solved: the keys still play, the switches are held, nothing arms it
    expect("solved, the fanfare over", (get("fan"), closed()), (0, set()))
    ctx.setblock(place.key(3, 1).cell, button(fr, True))
    if not until(lambda: closed() == {3}, 6, 1):
        problems.append("solved: key 3 does not play")
    throw(place.battery, False)
    ctx.advance(4)
    held = ctx.is_block(place.battery, switch(place, place.battery, True))
    expect("solved: a switch thrown back is held closed", held, True)
    come_in()
    ctx.advance(scan)
    got = state("st", "line", "live")
    expect("solved, entered again", got, {"st": 6, "line": ROUNDS, "live": 1})
    expect("solved, entered again: the sequence", sequence(), first)

    # ---- solo, the failure paths, and getting back from each
    unsolve()
    come_in()
    got = state("live", "st", "line")
    expect("unsolved, entered again: armed", got, {"live": 1, "st": 0, "line": 0})
    seq = sequence()
    power()
    press(CALL)
    keys = listen("before a wrong key")
    press(wrong(keys))
    expect("a wrong key", state("st", "miss", "line"), {"st": 5, "miss": 1, "line": 0})
    says("a wrong key", "WRONG")
    # the same round is sent again by itself
    expect("after a wrong key: the same round", listen("after a wrong key"), keys)
    misses = 1
    if len(keys) > 1:  # (a round of one key, at the lowest levels, has no middle)
        # the clock run out in the middle of an answer: the same again
        press(keys[0])
        expect("one right key", state("st", "i"), {"st": 3, "i": 1})
        ctx.advance(get("wait") + 6)
        expect("no more keys in time", state("st", "miss"), {"st": 5, "miss": 2})
        says("no more keys in time", "DROPPED")
        listen("after the clock ran out")
        misses = 2
    # no key at all: nobody is answering, and the room waits for CALL
    ctx.advance(get("wait") + 6)
    expect("no key at all", state("st", "miss"), {"st": 1, "miss": misses})
    says("no key at all", "NO ANSWER")
    press(CALL)
    listen("called again")
    # CALL during an answer: said again from the start
    calls = get("calls")
    press(CALL)
    expect("CALL during an answer", (get("st"), get("calls") - calls), (2, 1))
    answer("said again")
    got = state("line", "round", "miss")
    expect("the round won after the mistakes", got, {"line": 1, "round": 2, "miss": 0})
    # a switch opened during a round: no line, the round lost, the lamp kept
    listen("round 2")
    throw(place.aerial, False)
    got = (get("st"), closed(), get("line"), count(place.line))
    expect("a switch opened", got, (0, set(), 1, 1))
    expect("a switch opened: the sweep", count(place.sweep), 0)
    press(CALL)
    expect("CALL with a switch open", get("st"), 0)
    throw(place.aerial)
    got = state("st", "round", "line")
    expect("the switch closed again", got, {"st": 1, "round": 2, "line": 1})
    # everyone leaves during a round: it is dropped, and no more than that
    press(CALL)
    until(lambda: get("st") == 3, 200)
    stand(S1, outside)
    ctx.advance(game_checks.EMPTY)
    got = state("st", "pa", "pb", "line", "round", "live")
    want = {"st": 1, "pa": 1, "pb": 1, "line": 1, "round": 2, "live": 1}
    expect("left during a round", got, want)
    expect("left during a round: the contacts", (closed(), lamps_lit()), (set(), 0))
    stand(S1, entrance)
    expect("back in: nothing armed anew", (get("line"), sequence()), (1, seq))
    # three wrong answers running (the hint in chat is not seen: the count)
    press(CALL)
    for _ in range(3):
        press(wrong(listen("a wrong answer")))
    got = state("miss", "st", "line")
    expect("three wrong answers", got, {"miss": 3, "st": 5, "line": 1})

    # ---- duo: the line split between the two wing desks
    keys = listen("before the second comes in")
    stand(S2, entrance)
    ctx.advance(scan)
    expect("two in: the dome's form", ctx.score(f"#form{INDEX}"), 2)
    if get("st") == 3:
        # a change of form waits for the round: the keys stay where they are
        got = (get("want"), get("form"), keys_there(1))
        expect("two in during an answer", got, (2, 1, True))
        for k in keys:
            press(k)
        expect("the round finished on the desk it began on", get("line"), 2)
    else:  # (the clock ran out as the second came in: play it at the wings)
        problems.append("two in during an answer: the clock ran out first")
        press(CALL)
        answer("duo, round 2")
    ctx.advance(2)
    expect("then the desks change over", (get("form"), keys_there(2)), (2, True))
    # a key out of turn fails the round for both
    press(wrong(listen("duo")))
    expect("duo: a key out of turn", state("st", "line"), {"st": 5, "line": 2})
    # one leaves while the other answers: the wings' keys stay to the end
    keys = listen("duo again")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.advance(after_solo)
    expect("one left: the dome's form", ctx.score(f"#form{INDEX}"), 1)
    if get("st") == 3:
        got = (get("want"), get("form"), keys_there(2))
        expect("one left during an answer", got, (1, 2, True))
    else:  # (at a high level the clock is shorter than the fall back to solo)
        expect("one left, the clock run out", (get("st"), get("form")), (1, 1))
        press(CALL)
        keys = listen("the last round again")
    for k in keys:
        press(k)
    ctx.advance(4)
    expect("the last round, answered by the one left", (get("st"), solved()), (6, True))
    # (a solved room has no ``solo`` hook: it follows the core's form itself)
    expect("solved, one in: the desks", (get("form"), keys_there(1)), (1, True))
    # a whole round on the two wing desks, by two, from a new room
    unsolve()
    come_in()
    stand(S2, entrance)
    ctx.advance(scan)
    got = (state("form", "st", "live"), keys_there(2))
    expect("two in a new room", got, ({"form": 2, "st": 0, "live": 1}, True))
    power()
    press(CALL, "starboard")
    answer("duo, both desks")
    expect("duo: a round won on the wing desks", get("line"), 1)

    # ---- difficulty: the values of the level, on a new entry; the rounds
    # still to win at the new level, the switches and the LINE lamps kept
    ctx.cmd(f"kill @e[tag={S2}]")
    new = level
    for new in (game.LEVELS[0], game.LEVELS[-1]):
        was = ctx.score("#active")
        line = get("line")
        ctx.set_score("#level", new)
        come_in()
        if was != new:
            got = state("live", "line", "st", "pa", "pb", "round", "len")
            n = scaled(new)["n"]
            want = {"live": 1, "line": line, "st": 1, "pa": 1, "pb": 1}
            want |= {"round": line + 1, "len": n - ROUNDS + 1 + line}
            expect(f"level {new}: the rounds left at the new level", got, want)
        expect(f"level {new}: the values", state(*scaled(new)), scaled(new))
        problems += [f"level {new}: {p}" for p in sequence_problems(sequence())]
    # at the highest level the last round is sent by the bells alone
    power()
    ctx.set_score("#sig.round", ROUNDS)
    ctx.set_score("#sig.len", get("n"))
    for sig in place.signals:
        ctx.set_score(f"#sig.ear{sig.k}", 0)
    press(CALL)
    lamps, rung = 0, set()

    def by_ear() -> bool:
        nonlocal lamps
        lamps = max(lamps, lamps_lit())
        rung.update(
            s.k for s in place.signals if ctx.is_block(s.bell, f"{NOTE}[powered=true]")
        )
        return get("st") != 2

    until(by_ear, LEAD + (get("n") + 2) * get("period") + 40, 1)
    heard = {s.k for s in place.signals if get(f"ear{s.k}")}
    expect("by ear: the round sent", get("tx"), sent(sequence()))
    got = (get("byear"), lamps, heard)
    expect("by ear: no lamp lit, each signal rung", got, (1, 0, set(sequence())))
    if not rung or not rung <= heard:
        problems.append(f"by ear: bells {rung} read powered, of {heard} rung")
    # fifty sequences: each keeps the rules, and they are not all the same
    power_off = [(place.battery, False), (place.aerial, False)]
    for cell, on in power_off:
        throw(cell, on)
    rolls = set()
    for _ in range(50):
        ctx.function(f"{base}/roll")
        rolls.add(tuple(sequence()))
    bad = [s for s in rolls if sequence_problems(s) or len(s) != scaled(new)["n"]]
    if bad or len(rolls) < 10:
        problems.append(f"50 sequences: {len(rolls)} different, bad ones: {bad[:3]}")
    game_checks.restore_level(ctx, saved_level)
    ctx.function("difficulty/apply")

    # ---- the recall button: a click on it is taken up (by the core)
    click = f"@e[type=minecraft:interaction,tag={RECALL_TAG},limit=1]"
    ctx.cmd(
        f"data modify entity {click} interaction set value "
        "{player:[I;1,2,3,4],timestamp:0L}"
    )
    ctx.advance(4)
    left = ctx.data(f"entity {click} interaction")
    expect("the recall button's click, 4 ticks on", left, "")

    # ---- reset, from a scrambled state: the duo desks, a round half
    # answered (its clock held), a switch closed, both kinds of contact
    # closed, LINE lamps lit, the logbook taken
    throw(place.aerial)
    for name, value in (("line", 2), ("round", 3), ("i", 1), ("miss", 2), ("t", 9999)):
        ctx.set_score(f"#sig.{name}", value)
    ctx.set_score("#sig.st", 3)
    ctx.set_score("#sig.want", 2)
    ctx.function(f"{base}/desks")
    ctx.function(f"{base}/on_2")
    ctx.function(f"{base}/note_4")
    empty = f"minecraft:lectern[facing={fr.facing(-1, 0)},has_book=false]"
    ctx.setblock(place.lectern, empty)
    ctx.advance(2 * TAPE + 2)
    if "Finch" not in ctx.data(f"block {_xyz(place.lectern)} Book"):
        problems.append("a logbook taken from the lectern was not put back")
    ctx.setblock(place.lectern, empty)
    scrambled = (
        keys_there(2),
        ctx.is_block(place.signals[1].hub, POWER),
        ctx.is_block(place.signals[3].contact, POWER),
        ctx.is_block(place.aerial, switch(place, place.aerial, True)),
        count(place.line),
    )
    expect("the room scrambled before the reset", scrambled, (True,) * 4 + (2,))
    # locked first, so that nothing runs after it (the game runs on between
    # two commands: a tick of an open dome would arm the room again)
    ctx.set_score(f"#d{INDEX}", 0)
    ctx.function(f"{base}/reset")
    ctx.advance(8)  # (a redstone lamp is dark 4 ticks after its contact opens)
    as_built("reset from a scrambled state")

    # ---- after: nobody, the tunnel shut and flooded, the dome dry, and
    # nothing but this dome and its tunnel touched
    ctx.cmd(f"kill @e[tag={S1}]")
    ctx.cmd(f"kill @e[tag={S2}]")
    ctx.function(f"tunnel/{INDEX}/reset")
    for name in names:
        ctx.set_score(name, saved[name] or 0)
    ctx.advance(after_solo)
    ctx.function(f"{base}/reset")
    ctx.advance(100)
    as_built("left")
    racks_run("left")
    got, want = tunnels.counts(ctx, tunnel), tunnels.expected(tunnel, 0)
    expect("its tunnel left shut and flooded", got, want)
    expect("the domes and tunnels beside it", game_checks.scores(ctx, *others), beside)
    problems += [f"left: {p}" for p in domes.check_shell(ctx, dome, False)]
    behind = ctx.count(f"@e[tag={S1}]") + ctx.count(f"@e[tag={S2}]")
    expect("stand-ins left behind", behind, 0)
    return problems


MODULE = game.Module(
    "signal",
    stages={f"dome_{INDEX}_inside": build},
    functions=functions,
    checks={"signal_room": check},
)
