"""
Arches in a wall plane, and columns.

Each function returns the bounding box (a ``Volume``) of the blocks it placed.
"""

from __future__ import annotations

from math import ceil

from mcwb import Item, Vec3, Volume

from mciwb.builders.blockstate import Block
from mciwb.builders.placer import Placer

__all__ = ["arch", "arch_profile", "column"]

ROUND = "round"
POINTED = "pointed"


def arch_profile(
    span: int, thickness: int = 1, style: str = ROUND
) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    """
    The blocks of an arch, as (u, v) cells where u counts across the span
    from 0 to ``span - 1`` and v counts up from the springing line (v = 0).

    :param span: the outside width of the arch, in blocks
    :param thickness: the thickness of the ring of the arch, in blocks
    :param style: ``"round"`` (a semicircle) or ``"pointed"`` (a gothic,
        equilateral arch: two arcs whose radius is the width of the opening)
    :returns: (ring, opening): the cells of the ring of the arch, and the
        cells of the opening under it
    """
    if style not in (ROUND, POINTED):
        raise ValueError(f"style must be '{ROUND}' or '{POINTED}'")
    if thickness < 1:
        raise ValueError("thickness must be at least 1")
    if span < 2 * thickness + 1:
        raise ValueError(f"span must be at least {2 * thickness + 1}")

    # the opening, measured from the middle of the span at the springing line
    half = span / 2 - thickness
    top = ceil(half * 2) + 1

    def in_opening(u: int, v: int) -> bool:
        x, y = u + 0.5 - span / 2, v + 0.5
        if style == ROUND:
            return x * x + y * y <= half * half
        radius = 2 * half
        return (x - half) ** 2 + y * y <= radius**2 and (
            x + half
        ) ** 2 + y * y <= radius**2

    opening = {(u, v) for u in range(span) for v in range(top) if in_opening(u, v)}
    ring = set()
    for u, v in opening:
        for du in range(-thickness, thickness + 1):
            for dv in range(-thickness, thickness + 1):
                cell = (u + du, v + dv)
                if 0 <= cell[0] < span and cell[1] >= 0 and cell not in opening:
                    ring.add(cell)
    return ring, opening


def _runs(values: list[int]) -> list[tuple[int, int]]:
    """consecutive runs in a sorted list of ints, as (first, last)"""
    runs: list[tuple[int, int]] = []
    for value in values:
        if runs and runs[-1][1] == value - 1:
            runs[-1] = (runs[-1][0], value)
        else:
            runs.append((value, value))
    return runs


def arch(
    start: Vec3,
    end: Vec3,
    block: Block = Item.STONE_BRICKS,
    *,
    style: str = ROUND,
    thickness: int = 1,
    depth: int = 1,
    clear: bool = False,
) -> Volume:
    """
    An arch standing in a vertical wall plane.

    *start* and *end* are the two outermost blocks at the foot of the arch,
    on the same y and in a line along x or along z. The arch rises from
    there: a 7 block span with the default thickness of 1 looks like this
    (``#`` is the arch, ``.`` the opening)::

          ###          y = start.y + 3
        ###.###
        #.....#
        #.....#        y = start.y: start and end are the # at each end

    Its legs are short: build walls or a `column` under it for a taller
    opening (or start it higher up). `arch_profile` gives the shape of any
    arch without building it.

    :param start: the block at one foot of the arch
    :param end: the block at the other foot, in line with *start* along x or z
    :param block: the block to build the arch from
    :param style: ``"round"`` (semicircular) or ``"pointed"`` (gothic)
    :param thickness: the thickness of the ring of the arch, in blocks
    :param depth: how many blocks thick the arch is through the wall. The
        extra blocks go south (for an arch along x) or east (along z)
    :param clear: also set the opening under the arch to air, e.g. to cut
        an arched doorway through an existing wall
    :returns: the bounding box of the arch, and the opening if cleared
    """
    start, end = Vec3(*start).with_ints(), Vec3(*end).with_ints()
    if start.y != end.y:
        raise ValueError("start and end must be at the same height")
    if start.x != end.x and start.z != end.z:
        raise ValueError("start and end must be in a line along x or along z")
    if start == end:
        raise ValueError("start and end must be different blocks")
    if depth < 1:
        raise ValueError("depth must be at least 1")

    along_x = start.x != end.x
    first = Vec3(min(start.x, end.x), start.y, min(start.z, end.z))
    span = int(abs(end.x - start.x) + abs(end.z - start.z)) + 1
    across = Vec3(1, 0, 0) if along_x else Vec3(0, 0, 1)
    through = Vec3(0, 0, depth - 1) if along_x else Vec3(depth - 1, 0, 0)

    ring, opening = arch_profile(span, thickness, style)
    placer = Placer()
    parts: list[tuple[set[tuple[int, int]], Block]] = [(ring, block)]
    if clear:
        parts.append((opening, Item.AIR))
    for cells, item in parts:
        for u in range(span):
            column_v = sorted(v for cu, v in cells if cu == u)
            for v1, v2 in _runs(column_v):
                bottom = first + across * u + Vec3(0, v1, 0)
                top = first + across * u + Vec3(0, v2, 0) + through
                placer.fill(bottom, top, item)

    return placer.volume


def column(
    base: Vec3,
    height: int,
    block: Block = Item.QUARTZ_PILLAR,
    *,
    width: int = 1,
    plinth: Block | None = None,
    capital: Block | None = None,
) -> Volume:
    """
    A square column standing on *base*.

    :param base: the bottom block in the middle of the column
    :param height: the total height of the column, including any plinth and
        capital
    :param block: the block for the shaft
    :param width: the width of the shaft. Odd widths are centred on *base*,
        even widths have the extra block to the east and south
    :param plinth: if given, the bottom layer is this block, one block wider
        than the shaft on every side
    :param capital: if given, the top layer is this block, one block wider
        than the shaft on every side
    :returns: the bounding box of the column
    """
    base = Vec3(*base).with_ints()
    if width < 1:
        raise ValueError("width must be at least 1")
    needed = 1 + (plinth is not None) + (capital is not None)
    if height < needed:
        raise ValueError(f"height must be at least {needed}")

    lo = base - Vec3((width - 1) // 2, 0, (width - 1) // 2)
    hi = lo + Vec3(width - 1, 0, width - 1)
    placer = Placer()
    bottom, top = 0, height - 1
    if plinth is not None:
        placer.fill(lo - Vec3(1, 0, 1), hi + Vec3(1, 0, 1), plinth)
        bottom += 1
    if capital is not None:
        placer.fill(lo + Vec3(-1, top, -1), hi + Vec3(1, top, 1), capital)
        top -= 1
    placer.fill(lo + Vec3(0, bottom, 0), hi + Vec3(0, top, 0), block)
    return placer.volume
