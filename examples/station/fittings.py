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
    return interaction((px, y + 0.2, pz), tags, 0.6, 0.6)


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
