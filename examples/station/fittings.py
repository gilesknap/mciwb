"""
Fittings every dome of The Drowned Station has: a frame of directions to
place things by, signs and a brass plaque, a lectern with a written book,
the recall post, and the ``interaction`` entity that tells a function who
pressed a button. Small functions that give blocks (for ``setblock``),
commands or function lines; nothing here talks to a server.

- ``frame(dome)``: a `Frame`, the dome's own directions (forward as a
  player faces at its entrance, right, up from the floor), so a room is
  laid out without a world coordinate: ``fr.at(f, r, h)``.
- ``wall_sign``, ``standing_sign``, ``sign_text``; ``plaque_blocks``: a
  brass wall with signs on it.
- ``written_book`` and ``lectern_with_book`` (the 26.3 form).
- **Who pressed.** A button's block state says that it was pressed, not by
  whom. An ``interaction`` entity over the button (``interaction``) takes
  the right-click instead and keeps the player; a tick line
  (``click_line``) runs a function as the entity when it has been
  clicked, and that function reaches the player with
  ``execute on target run ...`` and ends with ``CLICK_DONE``.
- ``restricted(item, place_on=, breaks=, name=)``: an item an
  adventure-mode player can place only on, or break only, certain blocks.
- The recall post: ``recall_post_blocks``, ``summon_recall`` and
  ``recall_functions``, which calls ``station:recall`` as the presser.
- ``placement_problems(dome, cells)``: are these cells inside the dome
  and off the cells the tunnels reserve? For a room or its dressing to
  check itself offline.
- **Inputs**: ``input_post`` (a lever, button or plate on brass with its
  sign and a glowing label, in one call), ``lever``, ``lever_put_lines``
  (a reset that tells the neighbours), ``lever_hold_line`` (a lever held
  over), ``button_line`` (read a button and let it go), ``plate_held``
  (a plate that counts only with a player on it).
- **Displays**: ``display`` (summon a text display), ``text_line`` and
  ``turn_line`` (rewrite and turn one), ``label_text``.
- ``gauge_lines``: lamps that follow a score.
- ``hint``: a line of chat after a level-scaled time without progress,
  once per arming.
- **Lent items**: ``lent``, ``lend_line``, ``take_back_line``,
  ``lend_again_line``: items marked by ``custom_data`` so that exactly
  what a dome lent is taken back, whatever it is.
- **Machinery** that runs by itself: ``torch_clock`` (with a lamp chase
  and two plain pistons tapped off it).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import datapack as dp
import domes
import tunnels
from domes import Cell

if TYPE_CHECKING:
    from station_layout import Dome

BRASS = "minecraft:gold_block"
CUT = "minecraft:waxed_cut_copper"
CHISELED = "minecraft:waxed_chiseled_copper"
SIGN = "minecraft:bamboo"

COMPASS = domes.COMPASS
ROTATION = {"south": 0, "west": 4, "north": 8, "east": 12}

#: the tag of every recall post's interaction entity: the core answers a
#: click on any of them, so a module only places the post
RECALL_TAG = "st.recall"

#: the last lines of a function run as a clicked ``interaction`` entity:
#: the click forgotten, so that it is answered once
CLICK_DONE = ("data remove entity @s interaction", "data remove entity @s attack")


@dataclass(frozen=True)
class Frame:
    """a dome's own directions: forward from its entrance to its middle,
    right of that, and up from its floor"""

    origin: Cell  # the middle of the floor
    forward: tuple[int, int]
    right: tuple[int, int]

    def at(self, f: int, r: int, h: int = 1) -> Cell:
        """the cell f forward and r right of the middle, h above the floor
        (0 the floor itself, 1 where feet are)"""
        x, y, z = self.origin
        return (
            x + f * self.forward[0] + r * self.right[0],
            y + h,
            z + f * self.forward[1] + r * self.right[1],
        )

    def facing(self, f: int, r: int) -> str:
        """the compass name of a unit step of the frame"""
        return COMPASS[
            f * self.forward[0] + r * self.right[0],
            f * self.forward[1] + r * self.right[1],
        ]


def frame(dome: Dome) -> Frame:
    """a dome's frame: forward is the way a player faces at its entrance"""
    forward = domes.facing(dome)
    return Frame(dome.floor_centre, forward, domes.across(forward))


def placement_problems(dome: Dome, cells) -> list[str]:
    """what is wrong with building in these cells of a dome: any outside
    its inside (in the shell, the floor or the sea), any on the cells the
    tunnels reserve (``tunnels.reserved_cells``)"""
    cells = set(cells)
    problems = []
    if outside := cells - domes.dome_cells(dome).interior:
        problems.append(f"{len(outside)} cells not inside {dome.name}: {min(outside)}")
    if taken := cells & tunnels.reserved_cells(dome):
        problems.append(f"{len(taken)} cells on reserved cells: {min(taken)}")
    return problems


# ----------------------------------------------------------- signs and books


def snbt(text: str) -> str:
    """a string as SNBT"""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def sign_text(lines: tuple[str, ...]) -> str:
    """the NBT of a sign's front: up to four lines, the first one bold"""
    padded = (*lines, "", "", "", "")[:4]
    first = f"{{text:{snbt(padded[0])},bold:true}}" if padded[0] else '""'
    rest = ",".join(snbt(line) for line in padded[1:])
    return f"front_text:{{messages:[{first},{rest}]}}"


def wall_sign(facing: str, *lines: str) -> str:
    """a waxed sign on a wall, facing away from it"""
    return f"{SIGN}_wall_sign[facing={facing}]{{is_waxed:1b,{sign_text(lines)}}}"


def standing_sign(facing: str, *lines: str) -> str:
    """a waxed sign on a post"""
    return f"{SIGN}_sign[rotation={ROTATION[facing]}]{{is_waxed:1b,{sign_text(lines)}}}"


def plaque_blocks(
    fr: Frame, f: int, r: int, signs: tuple[tuple[str, ...], ...]
) -> tuple[dict[Cell, str], dict[Cell, str]]:
    """a brass plaque: a wall of brass two high across the way at f, as
    wide as there are signs and centred on r, the signs on the side a
    player coming in sees, read left to right. Gives (solid, attached)"""
    solid, attached = {}, {}
    back = fr.facing(-1, 0)
    for i, lines in enumerate(signs):
        across = r - len(signs) // 2 + i
        for h in (1, 2):
            solid[fr.at(f, across, h)] = BRASS
        attached[fr.at(f - 1, across, 2)] = wall_sign(back, *lines)
    return solid, attached


def written_book(title: str, author: str, pages) -> str:
    """a written book as an item's SNBT (the 26.3 form: the
    ``written_book_content`` component, its pages plain strings). RCON
    takes a short command only: give a long book its first page here and
    append the rest, a page a command, to ``BOOK_PAGES`` of the lectern"""
    content = (
        f"title:{snbt(title)},author:{snbt(author)},"
        f"pages:[{','.join(snbt(p) for p in pages)}]"
    )
    return (
        '{id:"minecraft:written_book",count:1,components:'
        f'{{"minecraft:written_book_content":{{{content}}}}}}}'
    )


#: where a lectern's book keeps its pages, for ``data modify block``
BOOK_PAGES = 'Book.components."minecraft:written_book_content".pages'


def lectern_with_book(facing: str, title: str, author: str, pages) -> str:
    """a lectern holding a written book"""
    book = written_book(title, author, pages)
    return f"minecraft:lectern[facing={facing},has_book=true]{{Book:{book}}}"


# -------------------------------------------------------- restricted items


def restricted(
    item: str,
    place_on: str | None = None,
    breaks: str | None = None,
    name: str | None = None,
) -> str:
    """
    An item for an adventure-mode player that can be placed only on
    ``place_on`` or can break only ``breaks`` (each a block, a ``#tag``, or
    blocks separated by commas), with an optional name: the item argument
    of ``give``, ``clear`` and ``item replace``. The lists are kept out of
    the tooltip. Give it in a dome's ``enter`` hook and take it back in
    its ``leave`` and ``reset`` hooks with ``clear <players> <item id>``
    (which takes every item of that id, restricted or not).
    """

    def blocks(what: str) -> str:
        names = [b.strip() for b in what.split(",")]
        listed = ",".join(f'"{b}"' for b in names)
        return (
            f"{{blocks:[{listed}]}}" if len(names) > 1 else f'{{blocks:"{names[0]}"}}'
        )

    parts, hidden = [], []
    if place_on:
        parts.append(f"minecraft:can_place_on={blocks(place_on)}")
        hidden.append('"minecraft:can_place_on"')
    if breaks:
        parts.append(f"minecraft:can_break={blocks(breaks)}")
        hidden.append('"minecraft:can_break"')
    if hidden:
        parts.append(
            f"minecraft:tooltip_display={{hidden_components:[{','.join(hidden)}]}}"
        )
    if name:
        parts.append(f"minecraft:custom_name={snbt(name)}")
    return f"{item}[{','.join(parts)}]" if parts else item


# ------------------------------------------------------------ who pressed


def interaction(
    pos: tuple[float, float, float], tags, width: float = 1, height: float = 1
) -> str:
    """the command that summons an ``interaction`` entity, ``pos`` the
    middle of its base: a right-click anywhere in it is kept, with who
    clicked, for ``click_line`` to answer"""
    listed = ",".join(f'"{t}"' for t in tags)
    x, y, z = pos
    return (
        f"summon minecraft:interaction {x:g} {y:g} {z:g} "
        f"{{Tags:[{listed}],width:{width:g}f,height:{height:g}f,response:1b}}"
    )


def click_line(tag: str, function: str) -> str:
    """the line for a ``tick`` function that runs ``function`` (its full
    name) as each interaction entity with this tag that has been clicked"""
    return (
        f"execute as @e[type=minecraft:interaction,tag={tag}] "
        f"if data entity @s interaction run function {function}"
    )


# -------------------------------------------------------------- the recall


def recall_post_blocks(
    fr: Frame, f: int, r: int, side: int
) -> tuple[dict[Cell, str], dict[Cell, str]]:
    """the recall button's post at (f, r): the button and its sign on the
    side ``side`` (-1 left, 1 right) of it. Gives (solid, attached)"""
    out = fr.facing(0, side)
    solid = {fr.at(f, r, 1): CHISELED, fr.at(f, r, 2): BRASS, fr.at(f, r, 3): CUT}
    attached = {
        fr.at(f, r + side, 2): f"minecraft:stone_button[face=wall,facing={out}]",
        fr.at(f, r + side, 3): wall_sign(out, "RECALL", "to the", "Pump House"),
    }
    return solid, attached


def summon_recall(fr: Frame, f: int, r: int, side: int, tags: tuple[str, ...]) -> str:
    """the command that puts an ``interaction`` entity over the button of
    the post at (f, r): a click on the button is a click on it"""
    x, y, z = fr.at(f, r + side, 2)
    # a quarter of a block back towards the post, where the button is
    px = x + 0.5 - 0.25 * side * fr.right[0]
    pz = z + 0.5 - 0.25 * side * fr.right[1]
    return interaction((px, y + 0.2, pz), (*tags, RECALL_TAG), 0.6, 0.6)


def recall_lines(pack: dp.Pack) -> list[str]:
    """the lines that answer a click on a recall post, run as its
    interaction entity: the presser recalled, as themselves"""
    return [
        "execute on target at @s run playsound "
        "minecraft:block.stone_button.click_on block @s ~ ~ ~ 1 1",
        f"execute on target run function {pack.id('recall')}",
        *CLICK_DONE,
    ]


def recall_functions(pack: dp.Pack, path: str, tag: str) -> str:
    """add the function that answers a recall button (``path``) and give
    the line a dome's ``tick`` runs: whoever clicked an interaction with
    this tag is recalled, as themselves"""
    pack.function(
        path,
        [
            "execute on target at @s run playsound "
            "minecraft:block.stone_button.click_on block @s ~ ~ ~ 1 1",
            f"execute on target run function {pack.id('recall')}",
            *CLICK_DONE,
        ],
    )
    return click_line(tag, pack.id(path))


# ------------------------------------------------------------------ inputs
# What a function needs to read a real lever, button or plate. Every input
# stands on (or hangs from) ``BRASS`` with a sign: ``input_post``.

STEP = {name: step for step, name in COMPASS.items()}


def _xyz(cell: Cell) -> str:
    return f"{cell[0]} {cell[1]} {cell[2]}"


def _base(block: str) -> str:
    """a block without its states and NBT"""
    return block.partition("[")[0].partition("{")[0]


def lever(facing: str, on: bool = False, face: str = "wall") -> str:
    """a lever on the side of a block, pointing ``facing`` away from it
    (``face``: ``floor`` or ``ceiling`` for one on top or underneath)"""
    powered = "true" if on else "false"
    return f"minecraft:lever[face={face},facing={facing},powered={powered}]"


def lever_put_lines(cell: Cell, block: str) -> list[str]:
    """lines that put a lever (or any input) back as ``block``, for a
    reset: taken out first, so that its neighbours (lamps, dust) are told;
    a lever only set over itself by command does not tell them"""
    return [f"setblock {_xyz(cell)} minecraft:air", f"setblock {_xyz(cell)} {block}"]


def lever_hold_line(cell: Cell, block: str, when: str = "") -> str:
    """the line that holds a lever over as ``block`` (its thrown state)
    while ``when`` (``if``/``unless`` clauses) is true: a player who moves
    it finds it back the next tick"""
    clause = f"{when} " if when else ""
    return (
        f"execute {clause}unless block {_xyz(cell)} {block} "
        f"run setblock {_xyz(cell)} {block}"
    )


def button_line(pack: dp.Pack, path: str, cell: Cell, block: str, then) -> str:
    """
    Read a button and let it go: adds the function ``path`` (the lines
    ``then``, and the button, ``block`` in its unpressed state, put back
    out) and gives the line for a ``tick`` function that runs it when the
    button is in. One press is answered once, however long the button
    would have stayed in. It does not say who pressed: for that put an
    ``interaction`` over it.
    """
    pack.function(path, [*then, f"setblock {_xyz(cell)} {block}"])
    return (
        f"execute if block {_xyz(cell)} {_base(block)}[powered=true] "
        f"run function {pack.id(path)}"
    )


def plate_held(cell: Cell) -> str:
    """the clauses that are true while a pressure plate at ``cell`` is
    down with someone in the game standing in its cell: a dropped item, a
    mob or an arrow on the plate does not count"""
    here = dp.box_selector(cell, cell)
    return (
        f"if block {_xyz(cell)} #minecraft:pressure_plates[powered=true] "
        f"if entity @e[tag=st.in,{here}]"
    )


@dataclass
class Post:
    """an input and what carries it: blocks to place (``solid`` before
    ``attached``) and commands that summon its label"""

    solid: dict[Cell, str]
    attached: dict[Cell, str]
    summons: list[str]
    input: Cell  #: where the lever, button or plate is

    @property
    def cells(self) -> set[Cell]:
        return set(self.solid) | set(self.attached)


def label_text(text: str, color: str = "gold", **more: str) -> str:
    """a text component for a display: ``{text:"...",color:"..."}``"""
    extra = "".join(f",{k}:{v}" for k, v in more.items())
    return f'{{text:{snbt(text)},color:"{color}"{extra}}}'


def input_post(
    cell: Cell,
    facing: str,
    block: str,
    sign: tuple[str, ...] = (),
    label: str = "",
    tags: tuple[str, ...] = (),
) -> Post:
    """
    An input on a brass post, in one call. ``cell`` is the post's lowest
    block (where feet would be), ``facing`` the side the input is on,
    ``block`` the lever or button as it faces (``lever(facing)``), or a
    pressure plate, which lies on the floor in front of the post instead.
    The post is two blocks of ``BRASS`` with the input on the upper one at
    hand height, a ``CUT`` cap carrying the ``sign`` over it, and a
    glowing text ``label`` floating above, which reads from any side.
    """
    dx, dz = STEP[facing]
    x, y, z = cell
    front = (x + dx, y, z + dz)
    solid = {cell: BRASS, (x, y + 1, z): BRASS}
    plate = "pressure_plate" in block
    where = front if plate else (x + dx, y + 1, z + dz)
    attached = {where: block}
    top = y + 2
    if sign:
        solid[x, y + 2, z] = CUT
        attached[x + dx, y + 2, z + dz] = wall_sign(facing, *sign)
        top = y + 3
    summons = []
    if label:
        summons.append(
            display(
                tags,
                (x + 0.5, top + 0.25, z + 0.5),
                0,
                label_text(label),
                0.8,
                "center",
            )
        )
    return Post(solid, attached, summons, where)


# ---------------------------------------------------------------- displays


def display(
    tags,
    pos: tuple[float, float, float],
    yaw: float,
    text: str,
    scale: float = 1.0,
    billboard: str = "fixed",
) -> str:
    """the command that summons a text display, its text (a component:
    ``label_text``) standing on ``pos``, lit whatever the light, flat and
    facing ``yaw`` (0 south, 90 west ...) or with ``billboard="center"``
    turning to whoever looks"""
    x, y, z = pos
    s = f"{scale}f"
    listed = ",".join(f'"{t}"' for t in tags)
    return (
        f"summon minecraft:text_display {x:.2f} {y:.2f} {z:.2f} "
        f'{{Tags:[{listed}],Rotation:[{yaw}f,0f],billboard:"{billboard}",'
        f"background:0,line_width:400,brightness:{{sky:15,block:15}},text:{text},"
        f"transformation:{{translation:[0f,0f,0f],scale:[{s},{s},{s}],"
        "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]}}"
    )


def display_selector(tag: str) -> str:
    return f"@e[type=minecraft:text_display,tag={tag},limit=1]"


def text_line(tag: str, text: str) -> str:
    """the line that rewrites the display with this tag (a state label:
    ``text_line("st.d5.board", label_text("ROUND 2"))``)"""
    return f"data modify entity {display_selector(tag)} text set value {text}"


def turn_line(tag: str, yaw: float, pitch: float = 0) -> str:
    """the line that turns the display with this tag"""
    return (
        f"data modify entity {display_selector(tag)} Rotation "
        f"set value [{yaw}f,{pitch}f]"
    )


# ------------------------------------------------------------------ gauges


def gauge_lines(cells, score: str, per_lamp: int, lit: str, dark: str) -> list[str]:
    """
    Lines that make a column or row of lamps follow a score: lamp k (the
    first of ``cells`` is 1) is ``lit`` while the score (``#name
    objective``) is ``k * per_lamp`` or more, else ``dark``. A lamp is set
    only when it is wrong, so the lines can run every tick.
    """
    lines = []
    for k, cell in enumerate(cells, 1):
        at = _xyz(cell)
        lines += [
            f"execute if score {score} matches {k * per_lamp}.. "
            f"unless block {at} {lit} run setblock {at} {lit}",
            f"execute unless score {score} matches {k * per_lamp}.. "
            f"unless block {at} {dark} run setblock {at} {dark}",
        ]
    return lines


# ------------------------------------------------------------------- hints


@dataclass
class Hint:
    """the lines of a hint: ``arm`` when the room is set up, ``progress``
    whenever the players get somewhere, ``tick`` every tick it is live"""

    arm: str
    progress: str
    tick: str


def hint(pack: dp.Pack, index: int, name: str, text: str, seconds: int) -> Hint:
    """
    One line of chat to the players in dome ``index`` when ``seconds``
    (at level 5; scaled by ``#diff.timer``, so longer at low levels) pass
    without progress, once per arming. Adds ``dome/<n>/hint/<name>`` and
    gives the lines the dome's functions use (`Hint`).
    """
    obj = "st"
    clock, at = f"#hint{index}.{name} {obj}", f"#hint{index}.{name}.at {obj}"
    who = f"@a[tag=st.in,scores={{st.dome={index}}}]"
    base = f"dome/{index}/hint/{name}"
    pack.objectives({obj: "dummy"})
    pack.constants(obj, 100)
    pack.function(
        f"{base}/arm",
        [
            f"scoreboard players set {clock} 0",
            f"scoreboard players set {at} {seconds * 20}",
            f"scoreboard players operation {at} *= #diff.timer {obj}",
            f"scoreboard players operation {at} /= #100 {obj}",
        ],
    )
    pack.function(
        f"{base}/say",
        [
            f'tellraw {who} {{text:{snbt(text)},color:"gray",italic:true}}',
            # past its time for good: said once
            f"scoreboard players set {clock} -2147483648",
        ],
    )
    pack.function(
        f"{base}/step",
        [
            f"scoreboard players add {clock} 1",
            f"execute if score {clock} >= {at} run function {pack.id(f'{base}/say')}",
        ],
    )
    return Hint(
        arm=f"function {pack.id(f'{base}/arm')}",
        progress=(
            f"execute if score {clock} matches 0.. run scoreboard players set {clock} 0"
        ),
        tick=(
            f"execute if score {clock} matches 0.. "
            f"run function {pack.id(f'{base}/step')}"
        ),
    )


# -------------------------------------------------------------- lent items

LENT = "st_lent"


def lent(item: str, key: str) -> str:
    """an item marked as lent by a dome (``key``, e.g. ``pipe2``), by its
    ``custom_data``: ``item`` may already have components
    (``restricted(...)``)"""
    mark = f"minecraft:custom_data={{{LENT}:{snbt(key)}}}"
    if item.endswith("]"):
        return f"{item[:-1]},{mark}]"
    return f"{item}[{mark}]"


def lent_predicate(key: str) -> str:
    """the item predicate that matches whatever was lent under a key"""
    return f"*[minecraft:custom_data~{{{LENT}:{snbt(key)}}}]"


def lend_line(item: str, key: str, count: int = 1, who: str = "@s") -> str:
    """the line that gives ``who`` a lent item (in a dome's ``enter``)"""
    return f"give {who} {lent(item, key)} {count}"


def take_back_line(key: str, who: str = "@s") -> str:
    """the line that takes back all that was lent under a key (in a dome's
    ``leave`` and, for ``@a``-selected players, its ``reset``)"""
    return f"clear {who} {lent_predicate(key)}"


def lend_again_line(index: int, item: str, key: str, count: int = 1) -> str:
    """the line that gives the item again to any player in dome ``index``
    who has none left (dropped into a hole, used up)"""
    who = f"@a[tag=st.in,scores={{st.dome={index}}}]"
    have = lent_predicate(key)
    return (
        f"execute as {who} unless items entity @s container.* {have} "
        f"unless items entity @s weapon.* {have} run give @s {lent(item, key)} {count}"
    )


# --------------------------------------------------------------- machinery
# Redstone that runs by itself, for dressing: one proved form (the Boiler
# Room's feed pump and lamp chaser), to be dressed differently in each
# room. It has no lever, button or plate, and no reset touches it.


@dataclass
class Machine:
    """a machine's blocks: ``bed`` (full blocks under it, for where the
    floor is not), ``solid`` then ``attached`` to place, and ``moving``:
    the cells whose state changes as it runs (a check must not expect
    them still)"""

    bed: dict[Cell, str]
    solid: dict[Cell, str]
    attached: dict[Cell, str]
    moving: set[Cell]
    lamps: tuple[Cell, ...] = ()
    pistons: tuple[Cell, ...] = ()

    @property
    def cells(self) -> set[Cell]:
        return set(self.bed) | set(self.solid) | set(self.attached) | self.moving


def torch_clock(
    fr: Frame,
    f: int,
    r: int,
    h: int = 1,
    side: int = 1,
    lamps: bool = False,
    pistons: bool = False,
    block: str = "minecraft:waxed_copper_block",
    bed: str = CUT,
) -> Machine:
    """
    A torch clock at (f, r) of a frame, its parts at height ``h``: a
    redstone torch on the forward face of ``block``, its light led round
    through dust and two repeaters (4 ticks each) to the back of the block
    to put the torch out, and so on for ever: a period of about a second.
    It covers 5 cells along the frame's forward (f - 2 .. f + 2) by 2
    across (r and r - ``side``).

    - ``lamps``: a lamp chase: copper bulbs in the bed under the four end
      dusts, each toggling as its dust comes on, in turn.
    - ``pistons``: two plain pistons facing up on the other side
      (r + ``side``, at f and f + 1), tapped off the torch and its block,
      working in turn. Plain, with nothing on them: a sticky piston drops
      its load if the clock is cut short. Each needs the cell above it.
    """
    ahead, back = fr.facing(1, 0), fr.facing(-1, 0)
    wire = [(2, 0), (2, -side), (1, -side), (-1, -side), (-2, -side), (-2, 0)]
    ends = [(2, 0), (2, -side), (-2, -side), (-2, 0)]
    solid = {fr.at(f, r, h): block}
    attached = {
        fr.at(f + 1, r, h): f"minecraft:redstone_wall_torch[facing={ahead}]",
        # a repeater's facing names the side its input is on
        fr.at(f, r - side, h): f"minecraft:repeater[facing={ahead},delay=4]",
        fr.at(f - 1, r, h): f"minecraft:repeater[facing={back},delay=4]",
    }
    for df, dr in wire:
        attached[fr.at(f + df, r + dr, h)] = "minecraft:redstone_wire"
    under = {
        fr.at(f + df, r + dr, h - 1): bed for df in range(-2, 3) for dr in (0, -side)
    }
    moving = set(attached)
    lamp_cells: tuple[Cell, ...] = ()
    if lamps:
        lamp_cells = tuple(fr.at(f + df, r + dr, h - 1) for df, dr in ends)
        for cell in lamp_cells:
            under[cell] = "minecraft:waxed_copper_bulb[lit=false]"
        moving |= set(lamp_cells)
    piston_cells: tuple[Cell, ...] = ()
    if pistons:
        piston_cells = (fr.at(f + 1, r + side, h), fr.at(f, r + side, h))
        for cell in piston_cells:
            solid[cell] = "minecraft:piston[facing=up]"
            under[cell[0], cell[1] - 1, cell[2]] = bed
            moving |= {cell, (cell[0], cell[1] + 1, cell[2])}
    return Machine(under, solid, attached, moving, lamp_cells, piston_cells)


# ----------------------------------------------------------- for the checks
# A place to try these fittings, and the automatons, in the world, away
# from every room: a sealed glass cell in the open sea in the middle of the
# ring, which no dome, tunnel, the dock, the lift or the test bench comes
# near (they are all on the ring's edges or by the start dome). The checks
# that use it build it first and put the sea back after (``build_cell``,
# ``remove_cell``).

#: the number the checks' automatons, waves and hint go by: no dome's
CHECK_INDEX = len(tunnels.layout.DOMES)
#: the cell's inside: half its length along x and its width along z, and
#: its height; its floor this far above the base floor (clear of the sea
#: floor, under water)
CELL_HALF = (5, 3)
CELL_HEIGHT = 5
CELL_RISE = 8


@dataclass(frozen=True)
class CheckCell:
    """the check cell: its frame (the middle of its floor; f along x, r
    along z, h up), the glass box's corners and the air inside it"""

    fr: Frame
    low: Cell
    high: Cell
    inside: frozenset[Cell]

    @property
    def selector(self) -> str:
        """selector arguments for what is in the cell"""
        return dp.box_selector(self.low, self.high)


def check_cell() -> CheckCell:
    """the check cell, from the layout: in the middle of the ring"""
    layout = tunnels.layout
    xs = [d.centre[0] for d in layout.DOMES]
    zs = [d.centre[1] for d in layout.DOMES]
    origin = (
        (min(xs) + max(xs)) // 2,
        layout.BASE_FLOOR_Y + CELL_RISE,
        (min(zs) + max(zs)) // 2,
    )
    fr = Frame(origin, (1, 0), (0, 1))
    (lf, lr), h = CELL_HALF, CELL_HEIGHT
    inside = frozenset(
        fr.at(f, r, k)
        for f in range(-lf, lf + 1)
        for r in range(-lr, lr + 1)
        for k in range(1, h + 1)
    )
    return CheckCell(
        fr, fr.at(-lf - 1, -lr - 1, 0), fr.at(lf + 1, lr + 1, h + 1), inside
    )


def build_cell(ctx) -> list[str]:
    """build the check cell where the sea is open (the problems if not)"""
    cell = check_cell()
    (x1, y1, z1), (x2, y2, z2) = cell.low, cell.high
    corners = [(x, y, z) for x in (x1, x2) for y in (y1, y2) for z in (z1, z2)]
    if not all(ctx.is_block(c, tunnels.WATER) for c in corners):
        if not all(ctx.is_block(c, domes.GLASS) for c in corners):
            return ["the check cell's site is not open sea"]
    ctx.fill(cell.low, cell.high, domes.GLASS, "hollow")
    return []


def remove_cell(ctx) -> None:
    """the check cell gone: what is in it, then the sea put back"""
    cell = check_cell()
    ctx.cmd(f"kill @e[type=!minecraft:player,{cell.selector}]")
    ctx.fill(cell.low, cell.high, tunnels.WATER)
    ctx.cmd(f"kill @e[type=minecraft:item,{cell.selector}]")


def check_button() -> tuple[Cell, Cell, str]:
    """the check's button: its brass block, its cell and its block"""
    fr = check_cell().fr
    facing = fr.facing(1, 0)
    block = f"minecraft:stone_button[face=wall,facing={facing},powered=false]"
    return fr.at(-2, 0, 1), fr.at(-1, 0, 1), block


def add_check_functions(pack: dp.Pack) -> None:
    """what the live check of these fittings needs in the pack: a button
    read by ``button_line`` and a hint"""
    _, cell, block = check_button()
    button_line(
        pack,
        "check/button",
        cell,
        block,
        ["scoreboard players add #chk.pressed st 1"],
    )
    hint(pack, CHECK_INDEX, "check", "A hint, from the check.", 2)
