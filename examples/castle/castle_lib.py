"""
Building blocks for the castle: bulk fills, round towers, battlements, and
the redstone mechanisms (portcullis, bookshelf door, pit trap, arrow trap).

Everything goes through a `Placer`, which raises `BuildError` if the server
rejects a command, so a typo in a block name stops the build at once.
All block names are 26.3 ids (``minecraft:iron_chain`` not ``chain``).
"""

from __future__ import annotations

import random
import re
from collections.abc import Iterable

from castle_layout import TAG
from mcipc.rcon.enumerations import FillMode
from mcwb import Vec3

from mciwb.builders.paths import stairway
from mciwb.builders.placer import Placer, rectangles
from mciwb.threads import get_client

AIR = "minecraft:air"
STONE = "minecraft:stone"
BRICK = "minecraft:stone_bricks"
MOSSY = "minecraft:mossy_stone_bricks"
CRACKED = "minecraft:cracked_stone_bricks"
CHISELED = "minecraft:chiseled_stone_bricks"
BRICK_STAIRS = "minecraft:stone_brick_stairs"
BRICK_SLAB = "minecraft:stone_brick_slab"
BRICK_WALL = "minecraft:stone_brick_wall"
DARK = "minecraft:polished_deepslate"
DARK_BRICK = "minecraft:deepslate_bricks"
DARK_TILES = "minecraft:deepslate_tiles"
ANDESITE = "minecraft:polished_andesite"
COBBLE = "minecraft:cobblestone"
MOSSY_COBBLE = "minecraft:mossy_cobblestone"
PLANKS = "minecraft:dark_oak_planks"
SPRUCE = "minecraft:spruce_planks"
BARS = "minecraft:iron_bars"
LANTERN = "minecraft:lantern"
SOUL_LANTERN = "minecraft:soul_lantern"
CHAIN = "minecraft:iron_chain"
WATER = "minecraft:water"
GLASS = "minecraft:glass_pane"
DUST = "minecraft:redstone_wire"
PISTON_DOWN = "minecraft:sticky_piston[facing=down]"
PISTON_UP = "minecraft:sticky_piston[facing=up]"

_rng = random.Random(1234)


def placer() -> Placer:
    return Placer(get_client())


def fill(
    a: Vec3,
    b: Vec3,
    block: str,
    mode: FillMode | None = None,
    filter: str | None = None,
) -> None:
    """fill a box of any size (split into /fill commands of 32768 blocks)"""
    placer().fill(a, b, block, mode, filter)


def keep(a: Vec3, b: Vec3, block: str) -> None:
    """fill only the air in a box"""
    placer().fill(a, b, block, FillMode.KEEP)


def seal(a: Vec3, b: Vec3, block: str) -> None:
    """
    Make a box solid without touching what is solid already: the lining of
    an underground passage that runs close to other parts of the castle.
    Air (a cave), water and lava (an aquifer) and sand and gravel (which
    would fall in) all become ``block``.
    """
    p = placer()
    p.fill(a, b, block, FillMode.KEEP)
    for loose in (
        "minecraft:water",
        "minecraft:lava",
        "#minecraft:sand",
        "minecraft:gravel",
    ):
        p.fill(a, b, block, FillMode.REPLACE, loose)


def set_block(pos: Vec3, block: str) -> None:
    placer().setblock(pos, block)


def cmd(command: str) -> str:
    return get_client().run(command)


def run(command: str, ok: tuple[str, ...]) -> str:
    """a command whose reply must hold one of ``ok``: an empty reply is
    retried, and another client's output in front of ours is tolerated
    (gilesknap/mciwb#166, item 2)"""
    for _attempt in range(3):
        r = cmd(command)
        if r.strip():
            break
    if not any(k in r for k in ok):
        raise RuntimeError(f"{command[:60]}... failed: {r!r}")
    return r


def set_nbt(pos: Vec3, block: str) -> None:
    """setblock for blocks with block-entity data, e.g. signs: Placer cannot
    parse the {...} suffix (gilesknap/mciwb#166, item 3)"""
    run(f"setblock {pos.x} {pos.y} {pos.z} {block}", ("Changed", "Could not set"))


def sign(pos: Vec3, block: str, *lines: str) -> None:
    """a sign (``oak_sign[rotation=4]``, ``oak_wall_sign[facing=north]`` ...)
    with up to four lines of text"""
    text = ",".join(f"'\"{line}\"'" for line in (*lines, "", "", "", "")[:4])
    set_nbt(pos, f"minecraft:{block}{{front_text:{{messages:[{text}]}}}}")


# the build stage running now, for the tag on summoned entities
STAGE = "build"
# mobs are summoned with this so that they never despawn
PERSIST = "PersistenceRequired:1b"


def summon(kind: str, pos: Vec3, nbt: str = "") -> None:
    """
    Summon an entity, tagged ``TAG`` (the castle's) and ``TAG.STAGE`` so that
    a rebuild of the castle or of a stage removes the old ones first (see
    build_castle.kill_stage_entities). ``nbt`` is extra NBT, without braces.
    """
    tags = f'Tags:["{TAG}","{TAG}.{STAGE}"]'
    data = f"{{{tags},{nbt}}}" if nbt else f"{{{tags}}}"
    run(f"summon minecraft:{kind} {pos.x} {pos.y} {pos.z} {data}", ("Summoned",))


def kill_tagged(tag: str) -> str:
    """kill every entity with a tag, wherever it has wandered to"""
    return cmd(f"kill @e[tag={tag}]")


# the hostile mobs that spawn in the dark (the night a verify's ticks bring)
HOSTILES = (
    "zombie",
    "husk",
    "drowned",
    "zombie_villager",
    "skeleton",
    "stray",
    "bogged",
    "creeper",
    "spider",
    "cave_spider",
    "enderman",
    "witch",
    "slime",
    "phantom",
    "breeze",
)


def box_selector(a: Vec3, b: Vec3) -> str:
    """the ``x=,y=,z=,dx=,dy=,dz=`` of an entity selector for a box"""
    lo = Vec3(min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))
    hi = Vec3(max(a.x, b.x), max(a.y, b.y), max(a.z, b.z))
    return (
        f"x={lo.x},y={lo.y},z={lo.z},"
        f"dx={hi.x - lo.x + 1},dy={hi.y - lo.y + 1},dz={hi.z - lo.z + 1}"
    )


def kill_hostiles(a: Vec3, b: Vec3) -> int:
    """kill the hostile mobs in a box; returns how many"""
    killed = 0
    for kind in HOSTILES:
        r = cmd(f"kill @e[type=minecraft:{kind},{box_selector(a, b)}]")
        if r.startswith("Killed"):  # "Killed 3 entities", or "Killed Skeleton"
            m = re.match(r"Killed (\d+) entities", r)
            killed += int(m.group(1)) if m else 1
    return killed


def count_entities(selector: str) -> int:
    """how many entities a selector matches"""
    r = cmd(f"execute if entity @e[{selector}]")
    m = re.search(r"[Cc]ount: (\d+)", r)
    return int(m.group(1)) if m else 0


def is_block(pos: Vec3, block: str) -> bool:
    """is this block (or block tag) at pos? an empty reply is another RCON
    client's doing (gilesknap/mciwb#166, item 2) and is read again"""
    for _attempt in range(3):
        r = cmd(f"execute if block {pos.x} {pos.y} {pos.z} {block}")
        if r.strip():
            break
    return "Test passed" in r


def shell(a: Vec3, b: Vec3, block: str) -> None:
    """the four vertical walls of a box (not top or bottom)"""
    lo = Vec3(min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))
    hi = Vec3(max(a.x, b.x), max(a.y, b.y), max(a.z, b.z))
    p = placer()
    p.fill(Vec3(lo.x, lo.y, lo.z), Vec3(hi.x, hi.y, lo.z), block)
    p.fill(Vec3(lo.x, lo.y, hi.z), Vec3(hi.x, hi.y, hi.z), block)
    p.fill(Vec3(lo.x, lo.y, lo.z), Vec3(lo.x, hi.y, hi.z), block)
    p.fill(Vec3(hi.x, lo.y, lo.z), Vec3(hi.x, hi.y, hi.z), block)


# ---------------------------------------------------------------- cells

Cells = set[tuple[int, int]]


def disc(cx: int, cz: int, r: float) -> Cells:
    """the (x, z) cells of a filled circle"""
    rr = (r + 0.5) ** 2
    span = int(r) + 1
    return {
        (cx + dx, cz + dz)
        for dx in range(-span, span + 1)
        for dz in range(-span, span + 1)
        if dx * dx + dz * dz <= rr
    }


def ring(cx: int, cz: int, r: float, thickness: int = 1) -> Cells:
    return disc(cx, cz, r) - disc(cx, cz, r - thickness)


def rect(x1: int, z1: int, x2: int, z2: int) -> Cells:
    x1, x2 = sorted((x1, x2))
    z1, z2 = sorted((z1, z2))
    return {(x, z) for x in range(x1, x2 + 1) for z in range(z1, z2 + 1)}


def fill_cells(
    cells: Iterable[tuple[int, int]],
    y1: int,
    y2: int,
    block: str,
    mode: FillMode | None = None,
) -> None:
    """fill the columns of a set of cells between two heights"""
    y1, y2 = sorted((y1, y2))
    p = placer()
    for ax, az, bx, bz in rectangles(set(cells)):
        p.fill(Vec3(ax, y1, az), Vec3(bx, y2, bz), block, mode)


def perimeter_order(cells: Cells) -> list[tuple[int, int]]:
    """the cells of a ring in order around it (by angle from the centre)"""
    from math import atan2

    cx = sum(x for x, _ in cells) / len(cells)
    cz = sum(z for _, z in cells) / len(cells)
    return sorted(cells, key=lambda c: atan2(c[1] - cz, c[0] - cx))


def weather(
    cells: Iterable[tuple[int, int]], y1: int, y2: int, fraction: float = 0.08
) -> None:
    """scatter mossy and cracked bricks over stone brick faces"""
    p = placer()
    for x, z in cells:
        for y in range(y1, y2 + 1):
            if _rng.random() < fraction:
                p.setblock(Vec3(x, y, z), _rng.choice((MOSSY, CRACKED, MOSSY)))


# ---------------------------------------------------------------- battlements


def merlons(
    cells: Iterable[tuple[int, int]], y: int, block: str = BRICK, every: int = 2
) -> None:
    """merlons (the raised teeth) on every other cell of a line, at height y"""
    p = placer()
    for i, (x, z) in enumerate(cells):
        if i % every == 0:
            p.setblock(Vec3(x, y, z), block)


def curtain(
    a: Vec3, b: Vec3, height: int, outward: Vec3, thickness: int = 3, block: str = BRICK
) -> None:
    """
    A straight curtain wall between two ground cells a and b (same y, in line
    along x or z): solid ``height`` blocks from a.y, ``thickness`` thick
    extending inward (away from ``outward``), a parapet on the outer edge one
    block higher with merlons above it, and a walkway on top of the rest.
    """
    lo = Vec3(min(a.x, b.x), a.y, min(a.z, b.z))
    hi = Vec3(max(a.x, b.x), a.y, max(a.z, b.z))
    inward = outward * -1
    far = inward * (thickness - 1)
    p = placer()
    # the solid body
    p.fill(lo, Vec3(hi.x + far.x, lo.y + height - 1, hi.z + far.z), block)
    if far.x < 0 or far.z < 0:
        p.fill(
            Vec3(lo.x + far.x, lo.y, lo.z + far.z),
            Vec3(hi.x, lo.y + height - 1, hi.z),
            block,
        )
    # dark plinth
    p.fill(lo, Vec3(hi.x, lo.y + 1, hi.z), DARK_BRICK)
    # parapet and merlons on the outer line
    top = lo.y + height
    p.fill(Vec3(lo.x, top, lo.z), Vec3(hi.x, top, hi.z), block)
    line = [(x, z) for x in range(lo.x, hi.x + 1) for z in range(lo.z, hi.z + 1)]
    merlons(line, top + 1, block)
    # arrow slits every 7 blocks through the outer face, 2 high
    for i, (x, z) in enumerate(line):
        if i % 7 == 3:
            p.fill(Vec3(x, lo.y + height - 5, z), Vec3(x, lo.y + height - 4, z), AIR)
            for k in range(1, thickness):
                q = Vec3(x, 0, z) + inward * k
                p.fill(
                    Vec3(q.x, lo.y + height - 5, q.z),
                    Vec3(q.x, lo.y + height - 4, q.z),
                    AIR,
                )
    # torches along the walkway's inner edge
    for i, (x, z) in enumerate(line):
        if i % 8 == 4:
            q = Vec3(x, 0, z) + far
            p.setblock(Vec3(q.x, top, q.z), LANTERN)


# ---------------------------------------------------------------- towers


def spiral_points(cx: int, cz: int, y1: int, y2: int, rad: int = 2) -> list[Vec3]:
    """points for a `stairway` spiralling up round a square pillar"""
    corners = [(rad, rad), (-rad, rad), (-rad, -rad), (rad, -rad)]
    side = 2 * rad
    points = []
    y = y1
    k = 0
    while True:
        dx, dz = corners[k % 4]
        points.append(Vec3(cx + dx, y, cz + dz))
        if y >= y2:
            break
        rise = min(side, y2 - y)
        if rise < side:
            # a partial side to finish exactly at y2
            nx, nz = corners[(k + 1) % 4]
            fx = dx + (nx - dx) * rise // side
            fz = dz + (nz - dz) * rise // side
            points.append(Vec3(cx + fx, y2, cz + fz))
            break
        y += rise
        k += 1
    return points


def round_tower(
    cx: int,
    cz: int,
    r: int,
    y_bottom: int,
    y_top: int,
    *,
    wall: int = 2,
    floors: Iterable[int] = (),
    doors: Iterable[tuple[int, Vec3, int]] = (),
    stair: bool = True,
    block: str = BRICK,
    roof: str | None = None,
    banner: str | None = None,
) -> None:
    """
    A hollow round tower. ``y_top`` is the top floor's standing level: the
    parapet ring stands at y_top and merlons at y_top + 1.

    :param floors: standing levels that get a floor slab (the slab is one
        block below), plus a lantern on the pillar
    :param doors: (standing level, direction, offset) triples: a 2-high
        opening through the wall in that direction, shifted sideways by
        offset blocks (to meet a wall walk that is not on the centre line)
    :param stair: a spiral stairway round a central pillar from the lowest
        floor to the top
    :param roof: a block for a stepped conical roof instead of battlements
    :param banner: a banner block to fly from the top
    """
    floors = sorted(floors)
    outer = disc(cx, cz, r)
    inner = disc(cx, cz, r - wall)
    fill_cells(outer, y_bottom, y_top - 1, block)
    fill_cells(
        disc(cx, cz, r + 1) - outer, y_bottom, y_bottom + 1, DARK_BRICK
    )  # a splayed plinth
    fill_cells(inner, floors[0] if floors else y_bottom + 1, y_top - 1, AIR)
    # floors
    for fy in floors:
        fill_cells(inner, fy - 1, fy - 1, PLANKS if fy > y_bottom + 1 else DARK)
    # doors
    for dy, direction, offset in doors:
        side = Vec3(-direction.z, 0, direction.x) * offset
        for k in range(0, r + 1):
            q = Vec3(cx, 0, cz) + direction * k + side
            if (q.x, q.z) in inner and k < r - wall:
                continue
            fill(Vec3(q.x, dy, q.z), Vec3(q.x, dy + 1, q.z), AIR)
    # arrow slits on each floor, in the four diagonal directions
    for fy in floors:
        for dx, dz in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            for k in range(r - wall, r + 1):
                q = Vec3(cx + round(dx * k * 0.7071), 0, cz + round(dz * k * 0.7071))
                fill(Vec3(q.x, fy + 1, q.z), Vec3(q.x, fy + 2, q.z), AIR)
    # the spiral stair round a pillar
    if stair and floors and r - wall >= 3:
        pillar = rect(cx - 1, cz - 1, cx + 1, cz + 1)
        fill_cells(pillar, floors[0] - 1, y_top - 1, DARK)
        stairway(
            spiral_points(cx, cz, floors[0] - 1, y_top - 1),
            BRICK_STAIRS,
            width=1,
            support=block,
            clearance=3,
        )
        for fy in floors:
            if (cx + 3, cz) in inner:
                set_block(
                    Vec3(cx + 3, fy, cz), f"{LANTERN}[hanging=false]"
                )  # standing on the floor
    elif floors:
        # a ladder up the north inside wall, and a lantern on every floor
        q = Vec3(cx, 0, cz - (r - wall))
        fill(
            Vec3(q.x, floors[0], q.z),
            Vec3(q.x, y_top, q.z),
            "minecraft:ladder[facing=south]",
        )
        for fy in floors[1:] + [y_top]:
            fill(
                Vec3(q.x, fy - 1, q.z),
                Vec3(q.x, fy - 1, q.z),
                "minecraft:ladder[facing=south]",
            )
        for fy in floors:
            set_block(Vec3(cx + 1, fy, cz), f"{LANTERN}[hanging=false]")
    # top: battlements or a stepped cone (clearing anything left above the top floor first)
    fill_cells(inner, y_top - 1, y_top - 1, BRICK)
    fill_cells(disc(cx, cz, r + 1), y_top, y_top + 4, AIR)
    if roof is None:
        fill_cells(ring(cx, cz, r, 1), y_top, y_top, block)
        merlons(perimeter_order(ring(cx, cz, r, 1)), y_top + 1, block)
        set_block(Vec3(cx + 1, y_top, cz), f"{LANTERN}[hanging=false]")
        if banner:
            set_block(Vec3(cx, y_top, cz), f"minecraft:{banner}_banner[rotation=0]")
    else:
        fill_cells(ring(cx, cz, r + 1, 1), y_top, y_top, roof)  # eaves
        level = y_top
        rr = r
        while rr >= 0:
            fill_cells(disc(cx, cz, rr), level, level + 1, roof)
            level += 2
            rr -= 1
        set_block(Vec3(cx, level, cz), "minecraft:lightning_rod")
        if banner:
            set_block(
                Vec3(cx + 1, level - 2, cz),
                f"minecraft:{banner}_wall_banner[facing=east]",
            )


# ---------------------------------------------------------------- mechanisms


def lever(
    pos: Vec3, facing: str = "north", face: str = "wall", powered: bool = False
) -> None:
    set_block(
        pos,
        f"minecraft:lever[face={face},facing={facing},powered={str(powered).lower()}]",
    )


def dust(*positions: Vec3) -> None:
    p = placer()
    for pos in positions:
        p.setblock(pos, DUST)


def portcullis_cells(x1: int, x2: int, z: int, y0: int) -> dict:
    """the positions of a `portcullis`'s parts: what to check"""
    return {
        "lever": Vec3(x2 + 2, y0 + 4, z),
        "ceiling_pistons": [Vec3(x, y0 + 3, z) for x in range(x1, x2 + 1)],
        "floor_pistons": [Vec3(x, y0 - 2, z) for x in range(x1, x2 + 1)],
        "closed_cells": [
            Vec3(x, y, z) for x in range(x1, x2 + 1) for y in (y0, y0 + 1)
        ],
    }


def portcullis(x1: int, x2: int, z: int, y0: int) -> dict:
    """
    A piston portcullis across a passage ``x1..x2`` wide running north-south
    through ``z``, whose floor is at ``y0 - 1`` (people stand at ``y0``; the
    passage is 2 high, y0..y0+1).

    When the lever is on, iron bars drop from the ceiling and rise from the
    floor, closing the passage completely: sticky pistons at y0+3 face down
    (dust on top of them), sticky pistons at y0-2 face up, powered through
    repeaters from a dust line at y0-3, two blocks south of the gate line.

    The lever stands in the "winch room" above the passage, whose floor is
    the row of ceiling pistons: at (x2+2, y0+4, z), with the dust line
    running through it. A diagonal dust channel descends inside the wall mass
    east of the passage (x2+4 .. x2+10) to the floor line. Everything from
    x1-1 .. x2+10, y0-4 .. y0+6, z-1 .. z+3 must be solid wall mass before
    this is called (the module carves what it needs).
    Returns the positions to check.
    """
    p = placer()
    xr = x2 + 10  # the bottom of the diagonal channel
    for x in range(x1, x2 + 1):
        p.setblock(Vec3(x, y0 + 3, z), PISTON_DOWN)
        p.setblock(Vec3(x, y0 + 2, z), BARS)
        p.setblock(Vec3(x, y0 + 4, z), DUST)
        p.setblock(Vec3(x, y0 - 2, z), PISTON_UP)
        p.setblock(Vec3(x, y0 - 1, z), BARS)
        p.setblock(Vec3(x, y0 - 3, z), STONE)  # power block under the piston
        p.setblock(Vec3(x, y0 - 4, z + 1), STONE)
        p.setblock(
            Vec3(x, y0 - 3, z + 1), "minecraft:repeater[facing=south]"
        )  # input from z+2, output north
        p.setblock(Vec3(x, y0 - 4, z + 2), STONE)
        p.setblock(Vec3(x, y0 - 3, z + 2), DUST)
    # the winch room: 3 high above the piston row, from x1-1 to x2+3
    p.fill(Vec3(x1 - 1, y0 + 4, z - 1), Vec3(x2 + 3, y0 + 6, z + 1), AIR)
    p.fill(
        Vec3(x1 - 1, y0 + 3, z - 1), Vec3(x2 + 3, y0 + 3, z + 1), BRICK
    )  # its floor (the pistons are re-set below)
    for x in range(x1, x2 + 1):
        p.setblock(Vec3(x, y0 + 3, z), PISTON_DOWN)
        p.setblock(Vec3(x, y0 + 4, z), DUST)
    p.setblock(Vec3(x2 + 1, y0 + 4, z), DUST)
    lever(Vec3(x2 + 2, y0 + 4, z), "north", "floor")
    p.setblock(Vec3(x2 + 3, y0 + 4, z), DUST)
    p.setblock(Vec3(x2 + 2, y0 + 5, z), LANTERN)  # light over the lever
    # the diagonal channel down: dust at (x2+3+k, y0+4-k, z) for k = 1..7, air above each
    for k in range(1, 8):
        x = x2 + 3 + k
        y = y0 + 4 - k
        p.setblock(Vec3(x, y - 1, z), STONE)
        p.setblock(Vec3(x, y, z), DUST)
        p.setblock(Vec3(x, y + 1, z), AIR)
    # at the bottom (xr, y0-3, z): a repeater south into the floor line's row z+2
    p.setblock(Vec3(xr, y0 - 4, z + 1), STONE)
    p.setblock(
        Vec3(xr, y0 - 3, z + 1), "minecraft:repeater[facing=north]"
    )  # input from z, output south
    p.setblock(Vec3(xr, y0 - 4, z + 2), STONE)
    p.fill(Vec3(x2 + 1, y0 - 4, z + 2), Vec3(xr, y0 - 4, z + 2), STONE)
    for x in range(x2 + 1, xr + 1):
        p.setblock(Vec3(x, y0 - 3, z + 2), DUST)
    return portcullis_cells(x1, x2, z, y0)


def _facing(d: Vec3) -> str:
    return {(0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west"}[
        (int(d.x), int(d.z))
    ]


def hidden_door(
    base: Vec3,
    u: Vec3,
    v: Vec3,
    *,
    trigger: str = "bookshelf",
    material: str = "minecraft:bookshelf",
    lever_b: int = 8,
) -> dict:
    """
    A secret sliding door in a wall. ``base`` is the lower door cell, in the
    wall's face plane. ``u`` is the horizontal direction from the room into
    the hidden space behind the wall; ``v`` runs along the wall. Cells are
    ``base + u*a + v*b + (0, h, 0)``.

    The door is the two ``material`` blocks at a=0, b=0, h=0..1. Sticky
    pistons at b=2 (extended into b=1) hold it; the trigger cuts the power
    to a redstone torch and the pistons pull the door to b=1, opening b=0.

    - ``trigger="bookshelf"``: a chiseled bookshelf at (a=0, b=8, h=1) read
      by a comparator: taking or replacing the LAST (6th) book opens the
      door; touching any other slot closes it.
    - ``trigger="lever"``: a lever on the room side of the wall at
      (a=-1, b=lever_b, h=1): on opens, off closes. lever_b may be negative
      (the other side of the door) but not 0..2.

    The hidden space a=1..3, h=0..3 is carved and floored, along b=0..8 for
    the bookshelf (its dust line) or from the lever to the pistons for a
    lever; the room side a=-1 at b=1..2 gets a 2-high pilaster of
    ``material`` hiding the piston faces. Everything from a=-1 to a=3,
    h=-1 to h=4 along the strip must be solid before this is called: it
    carves what it needs and leaves the rest as the walls. Returns the
    positions to check (`hidden_door_cells`).
    """
    p = placer()
    up = Vec3(0, 1, 0)

    def at(a: int, b: int, h: int) -> Vec3:
        return base + u * a + v * b + up * h

    f_mv = _facing(v * -1)  # towards the door
    f_mu = _facing(u * -1)  # towards the room
    b_lo, b_hi = _hidden_door_strip(trigger, lever_b)
    # the wall strip, solid
    for b in range(b_lo, b_hi + 1):
        p.fill(at(0, b, -1), at(0, b, 2), material)
        p.setblock(at(0, b, -1), BRICK)
        p.setblock(at(0, b, 2), BRICK)
    for h in (0, 1):
        p.setblock(at(0, 2, h), f"minecraft:sticky_piston[facing={f_mv}]")
        p.setblock(at(0, 1, h), AIR)
        p.setblock(at(0, 0, h), material)
    for b in (1, 2):
        p.fill(at(-1, b, 0), at(-1, b, 1), material)
        p.setblock(at(-1, b, 2), BRICK_SLAB)
    # the hidden space
    for b in range(b_lo + 1, b_hi):
        p.fill(at(1, b, -1), at(3, b, -1), BRICK)
        p.fill(at(1, b, 0), at(3, b, 3), AIR)
    if trigger == "bookshelf":
        for b in range(3, 9):
            p.setblock(at(2, b, 0), BRICK)  # under the dust line
        p.setblock(at(1, 8, 0), BRICK)  # under the comparator
        s = at(0, 8, 1)
        p.setblock(s, f"minecraft:chiseled_bookshelf[facing={f_mu}]")
        for slot in range(6):
            cmd(
                f"item replace block {s.x} {s.y} {s.z} container.{slot} with minecraft:book 1"
            )
        cmd(f"data merge block {s.x} {s.y} {s.z} {{last_interacted_slot:-1}}")
        p.setblock(at(1, 8, 1), f"minecraft:comparator[facing={f_mu}]")
        for b in range(3, 9):
            p.setblock(at(2, b, 1), DUST)
    else:
        s = at(-1, lever_b, 1)
        p.setblock(at(0, lever_b, 1), BRICK)
        p.setblock(s, f"minecraft:lever[face=wall,facing={f_mu},powered=false]")
        p.setblock(at(1, lever_b, 0), BRICK)
        p.setblock(at(1, lever_b, 1), DUST)
        run = range(lever_b, 2) if lever_b < 2 else range(lever_b, 2, -1)
        for b in run:
            p.setblock(at(2, b, 0), BRICK)
            p.setblock(at(2, b, 1), DUST)
    # the block whose power turns the torch off, and the torch beside the upper piston
    p.setblock(at(2, 2, 1), BRICK)
    p.setblock(at(1, 2, 1), f"minecraft:redstone_wall_torch[facing={f_mu}]")
    return hidden_door_cells(base, u, v, trigger=trigger, lever_b=lever_b)


def _hidden_door_strip(trigger: str, lever_b: int) -> tuple[int, int]:
    """the extent along the wall (b) of a hidden door's wall strip"""
    if trigger == "lever" and lever_b in (0, 1, 2):
        raise ValueError("lever_b must not be 0..2 (the door and its pistons)")
    if trigger == "lever":
        return min(-1, lever_b - 1), max(3, lever_b + 1)
    return -1, 9


def hidden_door_cells(
    base: Vec3, u: Vec3, v: Vec3, *, trigger: str = "bookshelf", lever_b: int = 8
) -> dict:
    """the positions of a `hidden_door`'s parts: what to check and trigger"""
    up = Vec3(0, 1, 0)

    def at(a: int, b: int, h: int) -> Vec3:
        return base + u * a + v * b + up * h

    if trigger == "bookshelf":
        s, first = at(0, 8, 1), at(2, 8, 1)
    else:
        s, first = at(-1, lever_b, 1), at(1, lever_b, 1)
    return {
        "trigger": s,
        "trigger_facing": _facing(u * -1),  # a lever faces the room
        "first_dust": first,
        "pistons": [at(0, 2, 0), at(0, 2, 1)],
        "door": [at(0, 0, 0), at(0, 0, 1)],
        "inside": at(1, 0, 0),
    }


def bookshelf_door(xw: int, y: int, zd: int) -> dict:
    """the library's secret door: wall plane x = xw, room to the west"""
    return hidden_door(Vec3(xw, y, zd), Vec3(1, 0, 0), Vec3(0, 0, 1))


def pit_trap(x: int, y: int, zt: int, depth: int, travel: int = -1) -> dict:
    """
    A pit trap in a 1-wide corridor running north-south at ``x`` with its
    floor at ``y - 1`` (people stand at ``y``): a tripwire across the corridor
    two blocks before the pit (people walk in direction ``travel`` along z:
    -1 north, +1 south) opens two iron trapdoors set flush in the floor at
    ``zt`` and ``zt + travel``, over a shaft ``depth`` deep. The corridor walls must be
    solid from x-3 to x-1 and x+1 to x+2 (the hooks sit in alcoves, and the
    wiring runs inside the west wall).
    """
    p = placer()
    s = 1 if travel > 0 else -1
    doors = (zt, zt + s)
    # the shaft under the two trapdoor cells
    p.fill(Vec3(x, y - depth - 1, doors[0]), Vec3(x, y - 2, doors[1]), AIR)
    p.fill(Vec3(x, y - depth - 1, doors[0]), Vec3(x, y - depth - 1, doors[1]), COBBLE)
    for zz in doors:
        p.setblock(
            Vec3(x, y - 1, zz),
            "minecraft:iron_trapdoor[facing=north,half=top,open=false]",
        )
        p.setblock(
            Vec3(x - 1, y - 1, zz), STONE
        )  # the wall block beside the trapdoor: its power block
        p.setblock(
            Vec3(x - 2, y - 1, zz), "minecraft:repeater[facing=west]"
        )  # input from x-3, output east
        p.setblock(Vec3(x - 2, y - 2, zz), STONE)
        p.setblock(Vec3(x - 3, y - 2, zz), STONE)
        p.setblock(Vec3(x - 3, y - 1, zz), DUST)
        p.setblock(Vec3(x - 3, y, zz), AIR)  # headroom for the dust channel
        p.setblock(Vec3(x - 3, y + 1, zz), STONE)
    # tripwire: alcoves either side, two blocks before the pit, hooks on the alcove backs
    zh = zt - 2 * s
    p.setblock(Vec3(x - 2, y, zh), STONE)
    p.setblock(Vec3(x + 2, y, zh), STONE)
    p.setblock(Vec3(x - 1, y, zh), "minecraft:tripwire_hook[facing=east,attached=true]")
    p.setblock(Vec3(x + 1, y, zh), "minecraft:tripwire_hook[facing=west,attached=true]")
    p.setblock(Vec3(x, y, zh), "minecraft:tripwire[attached=true,east=true,west=true]")
    # the west hook powers (x-2, y, zh); dust beside it (towards the pit) runs west then steps down
    zn = zh + s
    p.setblock(Vec3(x - 2, y - 1, zn), STONE)
    p.setblock(Vec3(x - 2, y, zn), DUST)
    p.setblock(Vec3(x - 2, y + 1, zn), STONE)
    p.setblock(Vec3(x - 3, y - 1, zn), STONE)
    p.setblock(Vec3(x - 3, y, zn), DUST)
    p.setblock(
        Vec3(x - 3, y + 1, zn), AIR
    )  # so the dust can step down to (x-3, y-1, zt)
    return pit_trap_cells(x, y, zt, depth, travel)


def pit_trap_cells(x: int, y: int, zt: int, depth: int, travel: int = -1) -> dict:
    """the positions of a `pit_trap`'s parts: what to check and trigger"""
    s = 1 if travel > 0 else -1
    zh = zt - 2 * s
    return {
        "hooks": [Vec3(x - 1, y, zh), Vec3(x + 1, y, zh)],
        "wire": Vec3(x, y, zh),
        "trapdoors": [Vec3(x, y - 1, z) for z in (zt, zt + s)],
        "shaft": [Vec3(x, yy, zt) for yy in range(y - depth, y - 1)],
    }


def arrow_trap(x1: int, x2: int, y: int, zw: int, zdisp: int) -> dict:
    """
    Dispensers in the end wall of a corridor ``x1..x2`` wide (people stand
    at ``y``) at ``zdisp``, firing arrows along the corridor when a tripwire
    at ``zw`` is crossed. The wiring climbs inside the corridor's east wall
    (which must be solid 2 thick, x2+1 and x2+2, from y-1 to y+4) and runs
    at y+3, above head height, so doorways through that wall are fine, then
    drops to a dust line lying directly on the dispensers: a dispenser only
    fires again once it has had a block update while unpowered, and dust on
    the block above it (the usual trick) left the end one stuck "triggered".
    """
    p = placer()
    side = -1 if zdisp < zw else 1  # from the wire towards the dispensers
    facing = "south" if side < 0 else "north"
    cells = []
    for x in range(x1, x2 + 1):
        p.setblock(Vec3(x, y + 1, zdisp), f"minecraft:dispenser[facing={facing}]")
        cmd(
            f"item replace block {x} {y + 1} {zdisp} container.4 with minecraft:arrow 64"
        )
        cells.append(Vec3(x, y + 1, zdisp))
    # the dust line lies on the dispensers themselves (and on the wall
    # beyond them), under a stone ceiling; its last cell, under the drop
    # from the run at y+3, stays open so that the dust connects down
    p.fill(Vec3(x1, y + 3, zdisp), Vec3(x2 + 1, y + 3, zdisp), STONE)
    p.setblock(Vec3(x2 + 2, y + 3, zdisp), AIR)
    p.fill(Vec3(x1, y + 4, zdisp), Vec3(x2 + 2, y + 4, zdisp), STONE)
    for x in range(x1, x2 + 3):
        p.setblock(Vec3(x, y + 2, zdisp), DUST)
    # the tripwire
    p.setblock(Vec3(x1 - 1, y, zw), STONE)
    p.setblock(Vec3(x2 + 1, y, zw), STONE)
    p.setblock(Vec3(x1, y, zw), "minecraft:tripwire_hook[facing=east,attached=true]")
    p.setblock(Vec3(x2, y, zw), "minecraft:tripwire_hook[facing=west,attached=true]")
    for x in range(x1 + 1, x2):
        p.setblock(
            Vec3(x, y, zw), "minecraft:tripwire[attached=true,east=true,west=true]"
        )
    # the east hook powers (x2+1, y, zw); dust beside it climbs three diagonal steps to y+3
    steps = [
        (x2 + 1, y, zw + side),
        (x2 + 2, y + 1, zw + side),
        (x2 + 2, y + 2, zw + 2 * side),
        (x2 + 2, y + 3, zw + 3 * side),
    ]
    for sx, sy, sz in steps:
        p.setblock(Vec3(sx, sy - 1, sz), STONE)
        p.setblock(Vec3(sx, sy, sz), DUST)
        p.setblock(Vec3(sx, sy + 1, sz), AIR)
    p.setblock(Vec3(x2 + 2, y + 4, zw + 3 * side), STONE)
    # a repeater, then the run at y+3 inside the wall to the dispenser row
    z4 = zw + 4 * side
    p.setblock(Vec3(x2 + 2, y + 2, z4), STONE)
    p.setblock(
        Vec3(x2 + 2, y + 3, z4),
        f"minecraft:repeater[facing={'south' if side < 0 else 'north'}]",
    )
    p.setblock(Vec3(x2 + 2, y + 4, z4), STONE)
    za, zb = sorted((zw + 5 * side, zdisp - side))
    if za <= zb:
        p.fill(Vec3(x2 + 2, y + 2, za), Vec3(x2 + 2, y + 2, zb), STONE)
        p.fill(Vec3(x2 + 2, y + 4, za), Vec3(x2 + 2, y + 4, zb), STONE)
        for z in range(za, zb + 1):
            p.setblock(Vec3(x2 + 2, y + 3, z), DUST)
    return arrow_trap_cells(x1, x2, y, zw, zdisp)


def arrow_trap_cells(x1: int, x2: int, y: int, zw: int, zdisp: int) -> dict:
    """the positions of an `arrow_trap`'s parts: what to check and trigger"""
    return {
        "hooks": [Vec3(x1, y, zw), Vec3(x2, y, zw)],
        "dispensers": [Vec3(x, y + 1, zdisp) for x in range(x1, x2 + 1)],
        "wire": Vec3(x1 + 1, y, zw),
    }
