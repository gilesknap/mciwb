"""
The way in to The Drowned Station: the shore landing with its jetty and
boats, the dock over the start dome, and the lift from the dock down to
the dome's floor. Three build stages (``shore``, ``dock``, ``lift``), the
functions that keep the boats and run the lift, and their live checks.

Every position is worked out from the layout: the shore from
``SHORE_LANDING`` and ``SPAWN``, the dock and the lift from ``DOCK`` and
``LIFT_*``. Places are steps ``(d, w)`` from a middle: ``d`` blocks along a
direction and ``w`` to its right (``domes.across``).

**The shore.** A jetty of dark oak, three wide, runs from the landing out
over the water in the direction of the dock. Its deck is laid only where
there was water, air or plants, so the ground it leaves is as it was; the
landing block itself, where the reset puts players, is not touched. A sign
at its end says where to row. Two boats lie beside it, one each side. From
the world spawn, which is left where the world has it, a signpost and a
line of lamp posts lead to the landing: each stands on whatever ground is
under its place (found by the game's heightmap, with a marker left there so
that a rebuild removes its own), and a place that falls on water or on a
tree is skipped.

The shore is outside the station's box, which is all the game keeps
loaded: the ``shore`` stage and its check forceload the shore's chunks for
as long as they run and release those they added (``loaded``).

**The boats.** A marker stands at each mooring (two at the jetty, two at
the dock, on its two sides nearest the shore), and once a second
``station:shore/boats`` puts a boat at any mooring that has none within
``BOAT_NEAR`` blocks: the rig's method (rig_mechanisms.py check 7). So a
boat rowed away is replaced, and two players have a boat each at once;
none is made while ``BOAT_CAP`` boats are about (rowing off and back
again and again).
Boats are tagged ``st.boat`` and carry the number of the reset they were
made after (objective ``st.boat``); ``station:shore/reset`` raises the
number, and a boat with an older one is killed as soon as it is seen, so a
boat left in a chunk that was not loaded at the reset goes when someone
comes near it. It runs only where chunks are ticking: at the shore, when a
player is there.

**The dock** stands on piles over the start dome, whose top is one block
under the surface: the piles are filled into the water only, so they end on
the glass and change none of it. On each of its four sides a landing lies
level with the water, for a boat to come alongside and a swimmer to climb
out, with two stairs up to the deck. Over the lift stands a mast with a
beacon, its beam tinted amber: the thing to row for.

**The lift** is a cage (a floor and a roof of copper grate, 3 x 3) in a
shaft of iron bars, 5 x 5 outside, from the deck down through the dome's
top to its floor. It is slow, to be watched: about eleven seconds a trip.
Standing at an end the cage is blocks. When it leaves, its blocks become
block displays and everyone in it is sat on a seat of their own (an item
display, ``ride``); then every tick the displays and the seats move an
eighth of a block, so the riders are carried, not teleported, and nothing
falls. At the other end the blocks are put back and the riders stood up
where they sat. On the way a chain of real blocks is paid out above the
cage (and taken in going up), the winch's drum turns a quarter for each
block, a counterweight slides the other way up a corner of the shaft, and
the cage passes the shaft's lamps. One who gets off their seat on the way
is put back on it.

- Where the shaft passes the dome's top it is a collar of copper, built
  solid and then hollowed (the rig's rule), from the shell up to the deck:
  the sea never has a way in. The cells of the shell it replaces are
  registered with ``domes.add_opening``.
- Each end has a doorway with a gate of bars, shut whenever the cage is not
  there, and two real buttons that ``station:lift/tick`` reads: one outside
  that calls the cage to that end, one inside (there only while the cage
  is) that sends it to the other. Whoever stands in the doorway when it
  leaves is taken along.
- The cage rests at the top; ``station:lift/reset`` puts it there from any
  state.
- A player found in the shaft outside the cage while it stands still (one
  who logged off in mid ride) is put into the cage.

Scores, in ``st``: ``#lift.y`` the y of the cage's floor (the last whole
block), ``#lift.p`` the eighths past it, ``#lift.to`` where it is going,
``#lift.dir`` which way, ``#lift.busy`` 1 while it travels.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import datapack as dp
import domes
import game
import game_checks
import station_layout as layout
from domes import AIR, Cell

PLANKS = "minecraft:dark_oak_planks"
LOG = "minecraft:dark_oak_log"
FENCE = "minecraft:dark_oak_fence"
STAIRS = "minecraft:dark_oak_stairs"
LANTERN = "minecraft:lantern"
COPPER = "minecraft:waxed_copper_block"
CUT = "minecraft:waxed_cut_copper"
BRASS = "minecraft:gold_block"
BARS = "minecraft:iron_bars"
CHAIN = "minecraft:waxed_copper_chain"
GRATE = "minecraft:waxed_copper_grate"
BUTTON = "minecraft:polished_blackstone_button"
BEACON = "minecraft:beacon"
BEAM_GLASS = "minecraft:orange_stained_glass"
GRINDSTONE = "minecraft:grindstone"
WATER = "minecraft:water"
SIGN = "minecraft:dark_oak_sign"
WALL_SIGN = "minecraft:dark_oak_wall_sign"
BOAT = "minecraft:dark_oak_boat"
BOATS = "@e[type=#minecraft:boat,tag=st.boat]"
REPLACEABLE = "#minecraft:replaceable"

OBJ = game.OBJ
BOAT_OBJ = "st.boat"
#: a mooring with no boat this near gets one
BOAT_NEAR = 2.5
BOAT_EVERY = 20  # ticks between looks at the moorings
BOAT_CAP = 12  # no boat is made at a mooring while this many are about

Step = tuple[int, int]
FACING = {(0, 1): "south", (-1, 0): "west", (0, -1): "north", (1, 0): "east"}
#: a standing sign's rotation when it faces each way
ROTATION = {(0, 1): 0, (-1, 0): 4, (0, -1): 8, (1, 0): 12}

SEA = layout.SEA_LEVEL  # the first layer of air over the sea
WATER_Y = SEA - 1  # the top layer of water


def towards(a: tuple[int, ...], b: tuple[int, ...]) -> Step:
    """the step along x or z (whichever is further) from a towards b;
    positions are (x, y, z)"""
    dx, dz = b[0] - a[0], b[2] - a[2]
    if abs(dx) > abs(dz):
        return (1 if dx > 0 else -1, 0)
    return (0, 1 if dz > 0 else -1)


def yaw(a: tuple[float, ...], b: tuple[float, ...]) -> int:
    """the yaw of something at a that looks at b (0 south, 90 west)"""
    return round(math.degrees(math.atan2(-(b[0] - a[0]), b[2] - a[2])))


def back(u: Step) -> Step:
    return (-u[0], -u[1])


def text(*lines: str) -> str:
    """a sign's NBT: up to four lines, glowing, not to be edited"""
    padded = [*lines, "", "", "", ""][:4]
    messages = ",".join(f'"{line}"' for line in padded)
    return (
        f"{{front_text:{{messages:[{messages}],has_glowing_text:1b,"
        'color:"yellow"},is_waxed:1b}'
    )


# ----------------------------------------------------------------- the shore

LX, LY, LZ = layout.SHORE_LANDING
#: the jetty runs this way from the landing, and this far
SHORE_U: Step = towards(layout.SHORE_LANDING, layout.DOCK)
JETTY = 8
#: how far along the jetty the boats lie, and how far from its middle
MOORING_D, MOORING_W = 6, 3
LAMP_EVERY = 5  # blocks between the lamp posts from the spawn
SIGN_WITHIN = 6  # the signpost is at most this far from the spawn


def shore_at(d: int, w: int, y: int = LY) -> Cell:
    """the cell d along the jetty from the landing and w to the right"""
    ax, az = domes.across(SHORE_U)
    return (LX + d * SHORE_U[0] + w * ax, y, LZ + d * SHORE_U[1] + w * az)


def jetty_cells() -> set[Cell]:
    """the jetty's deck, level with the landing block"""
    return {shore_at(d, w) for d in range(1, JETTY + 1) for w in (-1, 0, 1)}


def jetty_piles() -> list[Cell]:
    """the deck cells that stand on a pile"""
    return [shore_at(d, w) for d in range(2, JETTY + 1, 3) for w in (-1, 1)]


def jetty_fittings() -> dict[Cell, str]:
    """the lamp posts on the jetty: half way and at its end"""
    blocks = {}
    for d in (JETTY // 2 - 1, JETTY):
        for w in (-1, 1):
            blocks[shore_at(d, w, LY + 1)] = FENCE
            blocks[shore_at(d, w, LY + 2)] = LANTERN
    return blocks


def jetty_sign() -> tuple[Cell, str]:
    """the sign at the jetty's end, read by someone walking out along it"""
    block = f"{SIGN}[rotation={ROTATION[back(SHORE_U)]}]"
    words = text("THE DROWNED", "STATION", "Row out to", "the beacon")
    return shore_at(JETTY, 0, LY + 1), block + words


def moorings(place: str) -> list[Cell]:
    """where the boats lie, at ``shore`` or at ``dock``: cells of the sea's
    surface; the boat floats in the middle of one"""
    if place == "shore":
        return [shore_at(MOORING_D, w, SEA) for w in (-MOORING_W, MOORING_W)]
    return [
        dock_at(u, DECK_HALF + RISE + 1, MOORING_W, SEA) for u in shoreward_sides()[:2]
    ]


def spawn_line() -> tuple[list[tuple[int, int]], list[list[tuple[int, int]]]]:
    """
    The way from the world spawn to the landing, as x, z on the straight
    line between them: the places to try for the signpost, nearest the
    spawn first, and for each lamp post its place and those two and four
    blocks to each side of the line. The build takes the first of each that is on
    open ground.
    """
    sx, _, sz = layout.SPAWN
    length = math.hypot(LX - sx, LZ - sz)
    ux, uz = (LX - sx) / length, (LZ - sz) / length

    def point(t: float, side: float = 0) -> tuple[int, int]:
        return (round(sx + ux * t - uz * side), round(sz + uz * t + ux * side))

    signs = list(dict.fromkeys(point(t) for t in range(1, SIGN_WITHIN + 1)))
    lamps = [
        [point(t, side) for side in (0, 2, -2, 4, -4)]
        for t in range(LAMP_EVERY, int(length) - 1, LAMP_EVERY)
    ]
    return signs, lamps


def spawn_sign() -> str:
    """the signpost's block: it faces back along the line, to the spawn"""
    turn = round(yaw(layout.SHORE_LANDING, layout.SPAWN) / 22.5) % 16
    words = text("THE DROWNED", "STATION", "Straight on", "to the jetty")
    return f"{SIGN}[rotation={turn}]{words}"


def shore_chunks() -> set[tuple[int, int]]:
    """the chunks the shore's build and check need loaded"""
    points = [shore_at(d, w) for d in (0, JETTY + 2) for w in (-5, 5)]
    signs, lamps = spawn_line()
    points += [layout.SPAWN, *((x, 0, z) for x, z in signs + sum(lamps, []))]
    xs, zs = [p[0] for p in points], [p[2] for p in points]
    return {
        (cx, cz)
        for cx in range((min(xs) - 2) >> 4, ((max(xs) + 2) >> 4) + 1)
        for cz in range((min(zs) - 2) >> 4, ((max(zs) + 2) >> 4) + 1)
    }


def forceloaded(ctx: Any) -> set[tuple[int, int]]:
    """the forceloaded chunks. Asked twice, and a chunk in either reply
    counts: one missed (another RCON client can spoil a reply) would be
    released by `loaded` as if this module had added it"""
    found = set()
    for _ in range(2):
        reply = ctx.cmd("forceload query", "force loaded chunk")
        found |= {
            (int(x), int(z)) for x, z in re.findall(r"\[(-?\d+), (-?\d+)\]", reply)
        }
    return found


@contextmanager
def loaded(ctx: Any, chunks: set[tuple[int, int]]) -> Iterator[None]:
    """forceload chunks for as long as the block runs, and release those
    (and only those) that were not forceloaded before"""
    added = sorted(chunks - forceloaded(ctx))
    try:
        for cx, cz in added:
            ctx.cmd(f"forceload add {cx * 16} {cz * 16}")
        for cx, cz in sorted(chunks):
            for _ in range(120):
                probe = f"execute if block {cx * 16} 0 {cz * 16} {AIR}"
                if "not loaded" not in ctx.cmd(probe):
                    break
                ctx.pause(0.5)
            else:
                raise RuntimeError(f"chunk {cx}, {cz} did not load")
        ctx.advance(10)  # their entities too
        yield
    finally:
        for cx, cz in added:
            ctx.cmd(f"forceload remove {cx * 16} {cz * 16}")


def summon_moorings(ctx: Any, place: str) -> None:
    """the markers of a place's moorings, in place of any there were"""
    ctx.cmd(f"kill @e[type=minecraft:marker,tag=st.moor.{place}]")
    for x, y, z in moorings(place):
        ctx.cmd(
            f"summon minecraft:marker {domes.middle((x, y, z))} "
            f'{{Tags:["st.mooring","st.moor.{place}"]}}'
        )


def build_shore(ctx: Any) -> str:
    """the jetty, its boats, and the way to it from the world spawn"""
    mine = "@e[type=minecraft:marker,tag=st.way]"
    with loaded(ctx, shore_chunks()):
        # what an earlier build put on the ground between spawn and landing
        # (the lantern before its post: one left with nothing under it
        # drops as an item)
        for block in (LANTERN, FENCE, SIGN):
            ctx.cmd(f"execute at {mine} run fill ~ ~ ~ ~ ~1 ~ {AIR} replace {block}")
        ctx.cmd(f"kill {mine}")

        for a, b in domes.boxes(jetty_cells()):
            ctx.fill(a, b, PLANKS, f"replace {REPLACEABLE}")
        for x, y, z in jetty_piles():
            ctx.fill((x, y - 20, z), (x, y - 1, z), LOG, f"replace {WATER}")
        place(ctx, jetty_fittings())
        ctx.setblock(*jetty_sign())
        summon_moorings(ctx, "shore")

        # the signpost and the lamps stand on the ground, wherever it is:
        # a marker at the first place tried that is not water or a tree
        def mark(x: int, z: int, kind: str, one: str) -> None:
            ctx.cmd(
                f"execute positioned {x} 0 {z} "
                "positioned over motion_blocking_no_leaves "
                f"unless entity @e[type=minecraft:marker,tag={one}] "
                f"unless block ~ ~-1 ~ {WATER} unless block ~ ~-1 ~ #minecraft:logs "
                "unless block ~ ~-1 ~ #minecraft:leaves "
                "run summon minecraft:marker ~ ~ ~ "
                f'{{Tags:["st.way","st.way.{kind}","{one}"]}}'
            )

        signs, lamps = spawn_line()
        for x, z in signs:
            mark(x, z, "sign", "st.way.sign")
        for i, places in enumerate(lamps):
            for x, z in places:
                mark(x, z, "lamp", f"st.way.lamp{i}")
        at = "execute at @e[type=minecraft:marker,tag=st.way.{}] run setblock"
        ctx.cmd(f"{at.format('sign')} ~ ~ ~ {spawn_sign()}")
        ctx.cmd(f"{at.format('lamp')} ~ ~ ~ {FENCE}")
        ctx.cmd(f"{at.format('lamp')} ~ ~1 ~ {LANTERN}")
        ctx.advance(BOAT_EVERY + 5)  # the boats come, if the pack is in
    return (
        f"a jetty of {len(jetty_cells())} cells towards {FACING[SHORE_U]}, "
        f"{len(moorings('shore'))} moorings, a signpost and up to {len(lamps)} "
        "lamp posts from the world spawn"
    )


def place(ctx: Any, blocks: dict[Cell, str]) -> None:
    """set blocks, a kind at a time in the order the kinds first come (so
    what hangs on a block is put after it)"""
    kinds: dict[str, set[Cell]] = {}
    for cell, block in blocks.items():
        kinds.setdefault(block, set()).add(cell)
    for block, cells in kinds.items():
        ctx.fill_boxes(cells, block)


# ------------------------------------------------------------------ the dock

CX, DECK_Y, CZ = layout.DOCK
START = layout.START
DECK_HALF = 5  # the deck reaches this far from its middle
RING = 2  # the lift's shaft reaches this far: 5 x 5 outside, 3 x 3 inside
#: stairs from a landing (level with the water) up to the deck
RISE = DECK_Y - WATER_Y
MAST_TOP = DECK_Y + 7  # the platform the beacon stands on


def dock_at(u: Step, d: int, w: int, y: int) -> Cell:
    """the cell d from the dock's middle towards u and w to the right"""
    ax, az = domes.across(u)
    return (CX + d * u[0] + w * ax, y, CZ + d * u[1] + w * az)


def shoreward_sides() -> list[Step]:
    """the dock's four sides, the one that most faces the shore first"""
    dx, dz = LX - CX, LZ - CZ
    return sorted(FACING, key=lambda u: -(u[0] * dx + u[1] * dz))


def in_lift(dx: int, dz: int) -> bool:
    return abs(dx) <= RING and abs(dz) <= RING


def beacon_cell() -> Cell:
    return (CX, MAST_TOP + 1, CZ)


def dock_blocks() -> dict[Cell, str]:
    """the dock but for its piles: deck, rails, lamps, the four landings
    and their stairs, the mast and its beacon. Nothing in the lift's shaft"""
    blocks: dict[Cell, str] = {}
    span = range(-DECK_HALF, DECK_HALF + 1)
    for dx in span:
        for dz in span:
            edge = max(abs(dx), abs(dz)) == DECK_HALF
            if not in_lift(dx, dz):
                blocks[CX + dx, DECK_Y, CZ + dz] = CUT if edge else PLANKS
            # a rail round the edge, open at the head of each stair
            if edge and min(abs(dx), abs(dz)) > 1:
                blocks[CX + dx, DECK_Y + 1, CZ + dz] = FENCE
    for u in FACING:
        for w in (-1, 0, 1):
            for k in range(1, RISE + 1):
                d = DECK_HALF + RISE - k + 1
                for y in range(WATER_Y, WATER_Y + k):
                    blocks[dock_at(u, d, w, y)] = PLANKS
                blocks[dock_at(u, d, w, WATER_Y + k)] = (
                    f"{STAIRS}[facing={FACING[back(u)]}]"
                )
            for d in (DECK_HALF + RISE + 1, DECK_HALF + RISE + 2):
                blocks[dock_at(u, d, w, WATER_Y)] = PLANKS
    for dx in (-1, 1):
        for dz in (-1, 1):
            x, z = CX + dx * DECK_HALF, CZ + dz * DECK_HALF
            blocks[x, DECK_Y + 2, z] = FENCE
            blocks[x, DECK_Y + 3, z] = LANTERN
            # the mast: four legs astride the lift, a platform, the beacon
            for y in range(DECK_Y + 1, MAST_TOP):
                blocks[CX + dx * RING, y, CZ + dz * RING] = LOG
    for dx in range(-RING, RING + 1):
        for dz in range(-RING, RING + 1):
            inner = max(abs(dx), abs(dz)) < RING
            blocks[CX + dx, MAST_TOP, CZ + dz] = BRASS if inner else CUT
    blocks[beacon_cell()] = BEACON
    blocks[CX, MAST_TOP + 2, CZ] = BEAM_GLASS
    return blocks


def dock_piles() -> list[Cell]:
    """the top cell of each pile: in the water's top layer under the
    deck's corners, and under the outer corners of the landings"""
    piles = [
        (CX + dx * DECK_HALF, WATER_Y, CZ + dz * DECK_HALF)
        for dx in (-1, 1)
        for dz in (-1, 1)
    ]
    return piles + [
        dock_at(u, DECK_HALF + RISE + 2, w, WATER_Y - 1)
        for u in FACING
        for w in (-1, 1)
    ]


def build_dock(ctx: Any) -> str:
    """the dock over the start dome: see the module docstring"""
    blocks = dock_blocks()
    place(ctx, blocks)
    for x, y, z in dock_piles():
        # into the water only: a pile ends on the dome's glass, or the sea bed
        ctx.fill((x, START.top_y - 8, z), (x, y, z), LOG, f"replace {WATER}")
        if (x, y + 1, z) not in blocks:
            ctx.setblock((x, y + 1, z), LOG)
    summon_moorings(ctx, "dock")
    ctx.advance(BOAT_EVERY + 5)
    return (
        f"a deck {2 * DECK_HALF + 1} square, {len(FACING)} landings, "
        f"{len(dock_piles())} piles, {len(moorings('dock'))} moorings, "
        f"the beacon at y {beacon_cell()[1]}"
    )


# ------------------------------------------------------------------ the lift

TOP, BOTTOM = layout.LIFT_TOP_Y, layout.LIFT_BOTTOM_Y  # the cage's floor at each end
APEX = START.top_y  # the layer of the dome's shell the shaft passes
ROOF = 4  # the cage's roof is this far above its floor
LEAD = 10  # ticks from the button to the first move
SUB = 8  # ticks a block: the cage moves an eighth of a block a tick
TRIP = (TOP - BOTTOM) * SUB  # ticks from end to end
STORE = "station:lift"
BULB = "minecraft:waxed_copper_bulb[lit=true]"
LAMP_GAP = 5  # blocks between the lamps in the shaft
#: what moves with the cage while it travels (display entities), the seats
#: among them, and who rides
CAR, SEAT, ON = "st.lift.car", "st.lift.seat", "st.lift.on"
WEIGHT, DRUM = "st.lift.weight", "st.lift.drum"

#: the side each end's doorway is on: at the dock the side that faces the
#: shore, in the dome the side of the outgoing tunnel
DOOR: dict[str, Step] = {
    "top": shoreward_sides()[0],
    "bottom": domes.outward(START, layout.TUNNELS[0]),
}
FLOOR_Y = {"top": TOP, "bottom": BOTTOM}
OTHER = {"top": "bottom", "bottom": "top"}


def ring_cells(y: int) -> set[Cell]:
    """the 16 cells round the shaft at a height"""
    span = range(-RING, RING + 1)
    return {
        (CX + dx, y, CZ + dz)
        for dx in span
        for dz in span
        if max(abs(dx), abs(dz)) == RING
    }


def inside_cells(y1: int, y2: int) -> set[Cell]:
    """the 3 x 3 inside of the shaft from y1 up to y2"""
    span = range(-RING + 1, RING)
    return {
        (CX + dx, y, CZ + dz) for dx in span for dz in span for y in range(y1, y2 + 1)
    }


def opening_cells() -> set[Cell]:
    """the cells of the start dome's shell that the shaft replaces: the
    collar's lowest ring and the hole in it"""
    column = ring_cells(APEX) | inside_cells(APEX, APEX)
    return column & domes.dome_cells(START).shell


def column_cells() -> set[Cell]:
    """the whole 5 x 5 column from the dome's floor to the deck"""
    return {
        (x, y, z)
        for y in range(BOTTOM, TOP + 1)
        for x, _, z in ring_cells(0) | inside_cells(0, 0)
    }


def gate_cells(end: str) -> list[Cell]:
    """an end's doorway: two cells in the ring"""
    f = FLOOR_Y[end]
    return [dock_at(DOOR[end], RING, 0, y) for y in (f + 1, f + 2)]


def inside_button(end: str) -> tuple[Cell, str]:
    """the button in the cage at an end, on the door post to the right of
    someone walking in: its cell and its block"""
    u = DOOR[end]
    cell = dock_at(u, RING - 1, 1, FLOOR_Y[end] + 2)
    return cell, f"{BUTTON}[face=wall,facing={FACING[back(u)]}]"


def call_button(end: str) -> tuple[Cell, str]:
    """the button outside an end that calls the cage. At the dock it is on
    the face of the door post; in the dome, where nothing of the lift may
    stand outside its column, on the post's side, in the open corner"""
    u = DOOR[end]
    y = FLOOR_Y[end] + 2
    if end == "top":
        return dock_at(u, RING + 1, 1, y), f"{BUTTON}[face=wall,facing={FACING[u]}]"
    side = FACING[domes.across(u)]
    return dock_at(u, RING, RING, y), f"{BUTTON}[face=wall,facing={side}]"


def lift_signs() -> list[tuple[Cell, str]]:
    """a sign by each doorway, on the other door post from the call button"""
    u, y = DOOR["top"], TOP + 2
    top = f"{WALL_SIGN}[facing={FACING[u]}]" + text(
        "LIFT", "to the", "Pump House", "Press the button"
    )
    v = DOOR["bottom"]
    bottom = f"{WALL_SIGN}[facing={FACING[back(domes.across(v))]}]" + text(
        "LIFT", "to the dock", "", "Press the button"
    )
    return [
        (dock_at(u, RING + 1, -1, y), top),
        (dock_at(v, RING, -RING, BOTTOM + 2), bottom),
    ]


def winch_cells() -> dict[Cell, str]:
    """the winch on the head frame, over the cage: a drum between two
    grindstones, each on a block of the frame"""
    u = DOOR["top"]
    a = domes.across(u)
    y = TOP + ROOF + 1
    return {
        dock_at(u, 0, -RING, y): CUT,
        dock_at(u, 0, RING, y): CUT,
        dock_at(u, 0, 0, y): AIR,  # the drum: an entity, so that it can turn
        dock_at(u, 0, -1, y): f"{GRINDSTONE}[face=wall,facing={FACING[a]}]",
        dock_at(u, 0, 1, y): f"{GRINDSTONE}[face=wall,facing={FACING[back(a)]}]",
    }


def lift_blocks() -> dict[Cell, str]:
    """everything of the lift that does not move: the shaft's ring from the
    dome's floor to the head frame, the stations, the winch, the call
    buttons. Not the gates, the cage or the buttons in it (``reset_lines``)"""
    blocks: dict[Cell, str] = {}

    def corner(cell: Cell) -> bool:
        return abs(cell[0] - CX) == RING and abs(cell[2] - CZ) == RING

    def station(end: str, corners: str | None) -> None:
        """the three levels a cage stands in: posts and a lintel of brass
        round the doorway, bars on the other sides"""
        f, u = FLOOR_Y[end], DOOR[end]
        gate = set(gate_cells(end))
        posts = {dock_at(u, RING, w, 0)[::2] for w in (-1, 0, 1)}
        by_door = {dock_at(u, RING, w, 0)[::2] for w in (-RING, RING)}
        for y in range(f + 1, f + ROOF):
            for cell in ring_cells(y) - gate:
                if corner(cell):
                    # by the doorway the corners are left open: the call
                    # button and the sign are in them
                    if corners and cell[::2] not in by_door:
                        blocks[cell] = corners
                else:
                    blocks[cell] = BRASS if cell[::2] in posts else BARS

    # the dome's floor under the cage (its lantern is left in the middle)
    for cell in inside_cells(BOTTOM, BOTTOM) - {(CX, BOTTOM, CZ)}:
        blocks[cell] = CUT
    station("bottom", CHAIN)
    for y in range(BOTTOM + ROOF, APEX):
        for cell in ring_cells(y):
            blocks[cell] = CHAIN if corner(cell) else BARS
    for cell in shaft_lamps():
        blocks[cell] = BULB
    for y in range(APEX, TOP):
        for cell in ring_cells(y):
            blocks[cell] = COPPER
    for cell in ring_cells(TOP):
        blocks[cell] = CUT
    # at the dock the corners are the mast's legs (the dock's)
    station("top", None)
    for y in (TOP + ROOF, TOP + ROOF + 2):
        for cell in ring_cells(y):
            if not corner(cell):
                blocks[cell] = CUT
    blocks.update(winch_cells())
    for end in FLOOR_Y:
        cell, block = call_button(end)
        blocks[cell] = block
    return blocks


def shaft_lamps() -> list[Cell]:
    """lamps in the shaft's wall for the cage to pass: in the side away
    from the dome's doorway"""
    u = back(DOOR["bottom"])
    return [
        dock_at(u, RING, 0, y) for y in range(BOTTOM + ROOF + 2, APEX - 1, LAMP_GAP)
    ]


def weight_column() -> tuple[int, int]:
    """the x, z of the counterweight: the corner of the shaft that is
    beside neither doorway"""
    corners = {(CX + dx * RING, CZ + dz * RING) for dx in (-1, 1) for dz in (-1, 1)}
    for u in DOOR.values():
        corners -= {dock_at(u, RING, w, 0)[::2] for w in (-RING, RING)}
    return min(corners)


#: the counterweight's y with the cage at the top, and at the bottom
WEIGHT_Y = {TOP: BOTTOM + 2, BOTTOM: APEX - 2}
WEIGHT_STEP = (WEIGHT_Y[BOTTOM] - WEIGHT_Y[TOP]) / TRIP

IDENTITY = "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]"


def weight_summon(f: int) -> str:
    """the counterweight, for the cage standing at an end: a block of
    chiseled copper, a little small, on the chain of its corner"""
    x, z = weight_column()
    return (
        f"summon minecraft:block_display {domes.middle((x, WEIGHT_Y[f], z))} "
        f'{{Tags:["{WEIGHT}"],teleport_duration:1,'
        'block_state:{Name:"minecraft:waxed_chiseled_copper"},transformation:'
        f"{{translation:[-0.4f,0f,-0.4f],scale:[0.8f,0.8f,0.8f],{IDENTITY}}}}}"
    )


def drum_turn(quarter: int) -> str:
    """the winch drum's transformation, a number of quarter turns on: a
    log lying along the winch, turned about its length"""
    a = domes.across(DOOR["top"])
    lie = "[0f,0f,0.7071068f,0.7071068f]" if a[0] else "[0.7071068f,0f,0f,0.7071068f]"
    axis = f"[{abs(a[0])}f,0f,{abs(a[1])}f]"
    angle = round(quarter % 4 * math.pi / 2, 4)
    return (
        "transformation:{translation:[0f,0f,0f],scale:[1f,1f,1f],"
        f"left_rotation:{{axis:{axis},angle:{angle}f}},right_rotation:{lie}}}"
    )


def drum_summon() -> str:
    cell = dock_at(DOOR["top"], 0, 0, TOP + ROOF + 1)
    return (
        f"summon minecraft:item_display {domes.middle(cell, 0.5)} "
        f'{{Tags:["{DRUM}"],item:{{id:"{LOG}",count:1}},{drum_turn(0)}}}'
    )


def car_summons(f: int) -> list[str]:
    """the cage as it travels, from where it stands with its floor at y f:
    a block display for each block of its floor and roof"""
    return [
        f"summon minecraft:block_display {x}.0 {y}.0 {z}.0 "
        f'{{Tags:["{CAR}"],teleport_duration:1,block_state:{{Name:"{GRATE}"}}}}'
        for x, y, z in sorted(inside_cells(f, f) | inside_cells(f + ROOF, f + ROOF))
    ]


def cage_cells(f: int) -> tuple[set[Cell], set[Cell], set[Cell]]:
    """the cage with its floor at y f: its floor (none at the bottom, where
    it stands on the dome's), its roof, and the chain above it"""
    floor = set() if f == BOTTOM else inside_cells(f, f)
    chain = {(CX, y, CZ) for y in range(f + ROOF + 1, TOP + ROOF + 1)}
    return floor, inside_cells(f + ROOF, f + ROOF), chain


def set_score(name: str, value: int) -> str:
    return f"scoreboard players set {name} {OBJ} {value}"


def setblock(cell: Cell, block: str) -> str:
    return f"setblock {cell[0]} {cell[1]} {cell[2]} {block}"


def end_lines(end: str, here: bool) -> list[str]:
    """an end with the cage standing at it (gate open, the button in the
    cage) or without (gate shut, no button)"""
    gate = gate_cells(end)
    cell, block = inside_button(end)
    return [
        dp.fill(gate[0], gate[-1], AIR if here else BARS),
        setblock(cell, block if here else AIR),
    ]


def reset_lines() -> list[str]:
    """commands that put the cage at the top, from any state"""
    low, high = (CX - 1, BOTTOM + 1, CZ - 1), (CX + 1, TOP + ROOF, CZ + 1)
    floor, roof, _ = cage_cells(TOP)
    lines = [
        dp.fill(low, high, AIR, f"replace {GRATE}"),
        dp.fill((CX, low[1], CZ), (CX, high[1], CZ), AIR, f"replace {CHAIN}"),
        dp.fill(min(floor), max(floor), GRATE, f"replace {AIR}"),
        dp.fill(min(roof), max(roof), GRATE),
        *end_lines("top", True),
        *end_lines("bottom", False),
        *(setblock(*call_button(end)) for end in FLOOR_Y),
        f"kill @e[tag={CAR}]",
        f"tag @e[tag={ON}] remove {ON}",
        f"kill @e[tag={WEIGHT}]",
        weight_summon(TOP),
        f"kill @e[tag={DRUM}]",
        drum_summon(),
        set_score("#lift.y", TOP),
        set_score("#lift.to", TOP),
        set_score("#lift.busy", 0),
        set_score("#lift.t", 0),
        set_score("#lift.p", 0),
    ]
    return lines


def build_lift(ctx: Any) -> str:
    """the shaft, sealed; the stations; the cage at the top"""
    # where it meets the sea the shaft is made solid, then hollowed
    ring = ring_cells(APEX)
    low, high = min(ring), (max(ring)[0], TOP - 1, max(ring)[2])
    ctx.fill(low, high, COPPER)
    ctx.fill_boxes(inside_cells(BOTTOM + 1, TOP + ROOF), AIR)
    place(ctx, lift_blocks())
    for cell, block in lift_signs():
        ctx.setblock(cell, block)
    for line in reset_lines():
        ctx.cmd(line)
    return (
        f"a shaft from y {TOP} down to y {BOTTOM}, {len(opening_cells())} cells "
        f"of the dome's shell replaced, the cage at the top; doors "
        f"{FACING[DOOR['top']]} at the dock and {FACING[DOOR['bottom']]} below"
    )


# ------------------------------------------------------------- the functions


def boat_functions(pack: dp.Pack) -> None:
    pack.objectives({BOAT_OBJ: "dummy"})
    gen = f"#gen {BOAT_OBJ}"
    each = f"execute as {BOATS}"
    lines = [
        set_score("#boat.t", 0),
        f"execute store result score #boats {OBJ} if entity {BOATS}",
        # a new boat takes the number of the last reset; an older one goes
        f"{each} unless score @s {BOAT_OBJ} = @s {BOAT_OBJ} "
        f"run scoreboard players operation @s {BOAT_OBJ} = {gen}",
        f"{each} unless score @s {BOAT_OBJ} = {gen} run kill @s",
    ]
    for name, aim in (("shore", layout.DOCK), ("dock", layout.SHORE_LANDING)):
        turn = yaw(moorings(name)[0], aim)
        lines.append(
            f"execute if score #boats {OBJ} matches ..{BOAT_CAP - 1} "
            f"at @e[type=minecraft:marker,tag=st.moor.{name}] "
            f"unless entity @e[type=#minecraft:boat,distance=..{BOAT_NEAR}] "
            f"run summon {BOAT} ~ ~ ~ "
            f'{{Tags:["st.boat"],Invulnerable:1b,Rotation:[{turn}f,0f]}}'
        )
    pack.function("shore/boats", lines)
    pack.function(
        "shore/tick",
        [
            f"scoreboard players add #boat.t {OBJ} 1",
            f"execute if score #boat.t {OBJ} matches {BOAT_EVERY}.. "
            f"run function {pack.id('shore/boats')}",
        ],
        tick=True,
    )
    pack.function(
        "shore/reset",
        [
            f"scoreboard players add {gen} 1",
            f"function {pack.id('shore/boats')}",
        ],
    )
    pack.function("shore/load", [f"scoreboard players add {gen} 0"], load=True)


def lift_functions(pack: dp.Pack) -> None:
    y, to, busy, t, p, way = (
        f"#lift.{n} {OBJ}" for n in ("y", "to", "busy", "t", "p", "dir")
    )
    moving = f"execute if score {busy} matches 1 run return 0"
    car, weight = f"@e[tag={CAR}]", f"@e[tag={WEIGHT}]"
    seat = f"@e[type=minecraft:item_display,tag={SEAT}"
    clank = "playsound minecraft:block.chain.place block @a[distance=..24] ~ ~ ~ 1 0.6"
    pack.constants(OBJ, 4)

    pack.function("lift/reset", reset_lines())
    # the winch drum, a quarter turn on for each block the cage has moved
    pack.function(
        "lift/drum",
        [
            f"scoreboard players operation #lift.q {OBJ} = {y}",
            f"scoreboard players operation #lift.q {OBJ} %= #4 {OBJ}",
            *(
                f"execute if score #lift.q {OBJ} matches {q} run data merge entity "
                f"@e[tag={DRUM},limit=1] "
                f"{{start_interpolation:0,interpolation_duration:{SUB},{drum_turn(q)}}}"
                for q in range(4)
            ),
        ],
    )
    # run where the cage's floor is, once a block: going down the chain is
    # paid out into the cell the roof is leaving, going up it is taken in
    # from the cell the roof has come to
    pack.function("lift/pay", [f"setblock ~ ~{ROOF} ~ {CHAIN}", clank])
    pack.function("lift/reel", [f"setblock ~ ~{ROOF} ~ {AIR}", clank])
    for way_, do in (("down", "pay"), ("up", "reel")):
        pack.function(
            f"lift/at/{do}",
            [
                f"$execute positioned {CX} $(y) {CZ} "
                f"run function {pack.id(f'lift/{do}')}"
            ],
        )
        pack.function(
            f"lift/block/{way_}",
            [
                f"execute store result storage {STORE} y int 1 "
                f"run scoreboard players get {y}",
                f"function {pack.id(f'lift/at/{do}')} with storage {STORE}",
            ],
        )
    # someone in the cage as it leaves: a seat of their own, where they stand
    pack.function(
        "lift/seat",
        [
            "summon minecraft:item_display ~ ~ ~ "
            f'{{Tags:["{CAR}","{SEAT}","st.lift.new"],teleport_duration:1}}',
            f"ride @s mount {seat},tag=st.lift.new,limit=1,sort=nearest]",
            "tag @e[tag=st.lift.new] remove st.lift.new",
            f"tag @s add {ON}",
        ],
    )
    pack.function(
        "lift/off", ["ride @s dismount", "tp @s ~ ~ ~", f"tag @s remove {ON}"]
    )
    # every tick of the ride: the cage, its riders and the counterweight
    # move an eighth of a block
    glide = [
        f"execute if score {p} matches 0 if score {way} matches -1 "
        f"run function {pack.id('lift/block/down')}",
    ]
    for sign, word in ((-1, "-"), (1, "")):
        going = f"execute if score {way} matches {sign}"
        glide += [
            f"{going} as {car} at @s run tp @s ~ ~{word}{1 / SUB} ~",
            f"{going} as {weight} at @s run tp @s ~ ~{-sign * WEIGHT_STEP:.6f} ~",
        ]
    glide += [
        # one who has got off their seat is put back on it
        f"execute as @a[tag={ON}] at @s run ride @s mount {seat},limit=1,sort=nearest]",
        f"scoreboard players add {p} 1",
        f"execute if score {p} matches {SUB}.. run function {pack.id('lift/landed')}",
    ]
    pack.function("lift/glide", glide)
    pack.function(
        "lift/landed",
        [
            f"scoreboard players set {p} 0",
            f"scoreboard players add #lift.steps {OBJ} 1",
            f"scoreboard players operation {y} += {way}",
            f"execute if score {way} matches 1 run function {pack.id('lift/block/up')}",
            f"function {pack.id('lift/drum')}",
            f"execute if score {y} = {to} run function {pack.id('lift/arrive')}",
        ],
    )
    pack.function(
        "lift/run",
        [
            f"execute if score {t} matches ..0 run function {pack.id('lift/glide')}",
            f"execute if score {t} matches 1.. run scoreboard players remove {t} 1",
        ],
    )

    arrive = [set_score("#lift.busy", 0)]
    tick = []
    for end, f in FLOOR_Y.items():
        other = OTHER[end]
        gate = gate_cells(end)
        mid = domes.middle((CX, f + 1, CZ))
        floor, roof = inside_cells(f, f), inside_cells(f + ROOF, f + ROOF)
        cage = dp.box_selector((CX - 1, f + 1, CZ - 1), (CX + 1, f + ROOF - 1, CZ + 1))
        seated = f"at @s positioned ~ {f + 1.1} ~ run function {pack.id('lift/seat')}"
        # leaving an end: whoever is in the doorway comes too, the gate
        # shuts, the button in the cage goes with it; the cage's blocks
        # become what travels, and everyone in it gets a seat
        pack.function(
            f"lift/leave/{end}",
            [
                f"tp @a[{dp.box_selector(gate[0], gate[-1])}] {mid}",
                *end_lines(end, False),
                dp.fill(min(floor), max(floor), AIR, f"replace {GRATE}"),
                dp.fill(min(roof), max(roof), AIR, f"replace {GRATE}"),
                *car_summons(f),
                f"execute as @a[{cage}] {seated}",
                f"execute as @e[type=minecraft:armor_stand,{cage}] {seated}",
                set_score("#lift.to", FLOOR_Y[other]),
                set_score("#lift.dir", 1 if FLOOR_Y[other] > f else -1),
                set_score("#lift.busy", 1),
                set_score("#lift.t", LEAD),
                set_score("#lift.p", 0),
                f"execute positioned {mid} run playsound "
                "minecraft:block.iron_door.close block @a[distance=..24] ~ ~ ~ 1 0.6",
            ],
        )
        x, z = weight_column()
        pack.function(
            f"lift/here/{end}",
            [
                dp.fill(min(floor), max(floor), GRATE, f"replace {AIR}"),
                dp.fill(min(roof), max(roof), GRATE),
                # the riders stand where they sat
                f"execute as {seat}] at @s positioned ~ {f + 1} ~ on passengers "
                f"run function {pack.id('lift/off')}",
                f"kill {car}",
                f"tag @e[tag={ON}] remove {ON}",
                f"tp {weight} {domes.middle((x, WEIGHT_Y[f], z))}",
                *end_lines(end, True),
                f"execute positioned {mid} run playsound "
                "minecraft:block.bell.use block @a[distance=..24] ~ ~ ~ 1 1.2",
            ],
        )
        arrive.append(
            f"execute if score {y} matches {f} "
            f"run function {pack.id(f'lift/here/{end}')}"
        )
        # the cage to an end: nothing while it travels or if it is there
        pack.function(
            f"lift/to/{end}",
            [
                moving,
                f"execute if score {y} matches {f} run return 0",
                f"function {pack.id(f'lift/leave/{other}')}",
            ],
        )
        call, call_block = call_button(end)
        pack.function(
            f"lift/press/{end}",
            [setblock(call, call_block), f"function {pack.id(f'lift/to/{end}')}"],
        )
        inside, _ = inside_button(end)
        pressed = "execute if block {} {} {} " + BUTTON + "[powered=true] run function "
        tick += [
            pressed.format(*call) + pack.id(f"lift/press/{end}"),
            pressed.format(*inside) + pack.id(f"lift/to/{other}"),
        ]
        # a player in the shaft and not in the cage, which stands at this
        # end: into the cage
        low = (CX - 1, BOTTOM + (1 if end == "top" else ROOF + 1), CZ - 1)
        shaft = dp.box_selector(low, (CX + 1, TOP - 1, CZ + 1))
        tick.append(
            f"execute if score {busy} matches 0 if score {y} matches {f} "
            f"run tp @a[{shaft}] {mid}"
        )
    pack.function("lift/arrive", arrive)
    tick += [
        # (a seat that came back with a player who logged off on it)
        f"execute if score {busy} matches 0 run kill {car}",
        # (and a rider's tag kept by logging off mid-ride)
        f"execute if score {busy} matches 0 run tag @a[tag={ON}] remove {ON}",
        f"execute if score {busy} matches 1 run function {pack.id('lift/run')}",
    ]
    pack.function("lift/tick", tick, tick=True)
    pack.function(
        "lift/load",
        [
            f"execute unless score {y} matches {BOTTOM}..{TOP} "
            f"run function {pack.id('lift/reset')}",
        ],
        load=True,
    )

    # the check's: the cage sent off and called back and sent off again in
    # one tick, and how many cells of the column are wet
    pack.function(
        "check/lift/thrice",
        [
            f"function {pack.id(f'lift/to/{end}')}"
            for end in ("bottom", "top", "bottom")
        ],
    )
    pack.objectives({domes.CHECK_OBJECTIVE: "dummy"})
    pack.function(
        "check/lift/wet",
        [
            *domes.wet_lines(pack, column_cells()),
            f"scoreboard players add #ran {domes.CHECK_OBJECTIVE} 1",
        ],
    )


def functions(pack: dp.Pack) -> None:
    boat_functions(pack)
    lift_functions(pack)


# ---------------------------------------------------------------- the checks
# Live, over RCON, with nobody online. The lift is ridden by an armour
# stand: that proves the buttons are read, the cage travels and a rider is
# seated, carried and stood up at the other end, both ways. It does not prove how the
# ride is for a player (standing on a floor that steps), that a player in
# the doorway is taken along, or that one found in the shaft is put in the
# cage: those lines aim at players. PROGRESS.md lists them for a person.

RIDER = "st.liftcheck"


def wrong(ctx: Any, blocks: dict[Cell, str]) -> list[str]:
    """the cells that do not hold their block (one that reads wrong is
    read again: another RCON client can garble a reply)"""
    bad = [(c, b) for c, b in blocks.items() if not ctx.is_block(c, b)]
    bad = [(c, b) for c, b in bad if not ctx.is_block(c, b)]
    if not bad:
        return []
    cell, block = bad[0]
    return [f"{len(bad)} of {len(blocks)} blocks are not in place: {block} at {cell}"]


def boats_at(ctx: Any, cell: Cell) -> int:
    x, y, z = cell
    near = f"x={x + 0.5},y={y},z={z + 0.5},distance=..{BOAT_NEAR}"
    return ctx.count(f"{BOATS[:-1]},{near}]")


def check_boats(ctx: Any, place: str) -> list[str]:
    """one boat at each of a place's moorings; one taken away or killed is
    replaced; the reset kills the strays"""
    problems: list[str] = []
    wait = 2 * BOAT_EVERY + 5
    spots = moorings(place)
    markers = ctx.count(f"@e[type=minecraft:marker,tag=st.moor.{place}]")
    if markers != len(spots):
        problems.append(f"{markers} mooring markers at the {place}, not {len(spots)}")

    def each(what: str, total: int | None = None) -> None:
        # (each is read again if it is not as expected: another RCON client
        # can put its own reply in place of ours)
        one = [1] * len(spots)

        def at_moorings() -> list[int]:
            return [boats_at(ctx, spot) for spot in spots]

        if (got := at_moorings()) != one and (got := at_moorings()) != one:
            problems.append(f"{place}, {what}: {got} boats at the moorings, not 1 each")
        if total is None:
            return
        if (n := ctx.count(BOATS)) != total and (n := ctx.count(BOATS)) != total:
            problems.append(f"{place}, {what}: {n} boats in all, expected {total}")

    ctx.function("shore/reset")
    ctx.advance(wait)
    start = ctx.count(BOATS)
    each("after a reset")
    ctx.advance(150)
    each("150 ticks on", start)
    # one is rowed away
    x, y, z = spots[0]
    at = f"x={x + 0.5},y={y},z={z + 0.5},distance=..{BOAT_NEAR},limit=1]"
    ctx.cmd(f"tp {BOATS[:-1]},{at} {domes.middle((x + 12, y, z))}")
    ctx.advance(wait)
    each("one taken 12 blocks away", start + 1)
    ctx.cmd(f"kill {BOATS[:-1]},{at}")
    ctx.advance(wait)
    each("one killed", start + 1)
    ctx.function("shore/reset")
    ctx.advance(wait)
    each("reset with a stray", start)
    if n := ctx.count(f"@e[type=minecraft:item,x={x},y={y},z={z},distance=..16]"):
        problems.append(f"{place}: {n} dropped items by the moorings")
    return problems


def check_shore(ctx: Any) -> list[str]:
    """the jetty, the way from the spawn, the boats"""
    game_checks.no_run(ctx)
    problems: list[str] = []
    obj = domes.CHECK_OBJECTIVE
    with loaded(ctx, shore_chunks()):
        bare = [c for c in jetty_cells() if ctx.is_block(c, REPLACEABLE)]
        bare = [c for c in bare if ctx.is_block(c, REPLACEABLE)]
        if bare:
            problems.append(f"{len(bare)} cells of the jetty have no deck: {bare[0]}")
        end = {shore_at(JETTY, w): PLANKS for w in (-1, 0, 1)}
        cell, sign = jetty_sign()
        problems += wrong(
            ctx, {**end, **jetty_fittings(), cell: sign.partition("{")[0]}
        )
        x, y, z = game.shore_spot()
        ground = not ctx.is_block((x, y - 1, z), REPLACEABLE)
        room = all(ctx.is_block((x, y + h, z), REPLACEABLE) for h in (0, 1))
        if not (ground and room):
            problems.append(f"where the reset puts players, {(x, y, z)}, is not clear")
        # the signpost and the lamps: each marker has what it marks
        at = "execute at @e[type=minecraft:marker,tag=st.way.{}] if block ~ ~ ~ {} "
        add = f"run scoreboard players add #n {obj} 1"
        ctx.set_score("#n", 0, obj)
        ctx.cmd(at.format("sign", SIGN) + add)
        if (n := ctx.score("#n", obj)) != 1:
            problems.append(f"{n} signposts by the world spawn, not 1")
        ctx.set_score("#n", 0, obj)
        ctx.cmd(at.format("lamp", FENCE) + f"if block ~ ~1 ~ {LANTERN} " + add)
        lamps = ctx.count("@e[type=minecraft:marker,tag=st.way.lamp]")
        print(f"     {lamps} lamp posts between the world spawn and the landing")
        if lamps == 0 or ctx.score("#n", obj) != lamps:
            problems.append(
                f"{ctx.score('#n', obj)} lamp posts stand, of {lamps} marked"
            )
        problems += check_boats(ctx, "shore")
    return problems


def check_dock(ctx: Any) -> list[str]:
    """the dock's blocks, its piles, the beacon lit, the boats"""
    game_checks.no_run(ctx)
    problems = wrong(ctx, dock_blocks())
    piles = [c for c in dock_piles() if not ctx.is_block(c, LOG)]
    if piles:
        problems.append(f"{len(piles)} piles do not reach the surface: {piles[0]}")
    x, y, z = beacon_cell()
    # a beacon just built takes 25 ticks to look up its beam, and looks at
    # its base every 80
    ctx.advance(200)
    lit = [ctx.data(f"block {x} {y} {z} Levels") for _ in range(2)]
    if not any(re.match(r"[1-4]\b", levels) for levels in lit):
        problems.append(f"the beacon is not lit: its levels read {lit}")
    return problems + check_boats(ctx, "dock")


def lift_state(f: int) -> dict[Cell, str]:
    """what moves, with the cage standing at an end"""
    here = "top" if f == TOP else "bottom"
    floor, roof, chain = cage_cells(f)
    blocks = dict.fromkeys(inside_cells(BOTTOM + 1, TOP + ROOF), AIR)
    blocks.update(dict.fromkeys(floor | roof, GRATE))
    blocks.update(dict.fromkeys(chain, CHAIN))
    for end in FLOOR_Y:
        blocks.update(dict.fromkeys(gate_cells(end), AIR if end == here else BARS))
        cell, block = inside_button(end)
        blocks[cell] = block if end == here else AIR
    return blocks


def check_lift(ctx: Any) -> list[str]:
    """the lift's blocks, the shaft and the dome dry, the cage called and
    sent both ways with a rider"""
    game_checks.no_run(ctx)
    problems: list[str] = []
    obj = domes.CHECK_OBJECTIVE
    rider = f"@e[type=minecraft:armor_stand,tag={RIDER}]"
    car = f"@e[tag={CAR}]"
    ctx.cmd(f"kill {rider}")
    ctx.function("lift/reset")
    fixed = lift_blocks()
    fixed.update({c: b.partition("{")[0] for c, b in lift_signs()})

    def expect(what: str, read: Callable[[], Any], want: Any) -> None:
        # (read again if it is not as expected: another RCON client can
        # put its own reply in place of ours)
        if (got := read()) != want and (got := read()) != want:
            problems.append(f"{what}: read {got}, expected {want}")

    def score(name: str) -> Callable[[], int | None]:
        return lambda: ctx.score(name)

    def height(tag: str) -> Callable[[], float | None]:
        def read() -> float | None:
            pos = ctx.data(f"entity @e[tag={tag},limit=1] Pos[1]")
            m = re.match(r"(-?[\d.]+)", pos)
            return round(float(m.group(1)), 2) if m else None

        return read

    def standing(what: str, f: int) -> None:
        expect(f"{what}: the cage's floor", score("#lift.y"), f)
        expect(f"{what}: travelling parts left", lambda: ctx.count(car), 0)
        expect(f"{what}: the counterweight", height(WEIGHT), WEIGHT_Y[f])
        for tag in (WEIGHT, DRUM):
            expect(
                f"{what}: entities {tag}", lambda t=tag: ctx.count(f"@e[tag={t}]"), 1
            )
        problems.extend(f"{what}: {p}" for p in wrong(ctx, lift_state(f)))
        problems.extend(f"{what}: {p}" for p in dry() and dry())

    def dry() -> list[str]:
        ctx.set_score("#wet", 0, obj)
        ctx.set_score("#ran", 0, obj)
        ctx.function("check/lift/wet")
        if ctx.score("#ran", obj) != 1:
            return ["the lift's wet check did not run whole"]
        wet = ctx.score("#wet", obj)
        return [f"{wet} cells of the lift's column are wet"] if wet else []

    ride_y = height(RIDER)

    def board(f: int) -> None:
        ctx.cmd(f"kill {rider}")
        ctx.cmd(
            f"summon minecraft:armor_stand {domes.middle((CX, f + 1, CZ))} "
            f'{{Tags:["{RIDER}"],NoGravity:1b,Invisible:1b}}'
        )

    def press(cell: Cell, block: str) -> None:
        ctx.setblock(cell, block.replace("]", ",powered=true]"))

    started = [0]

    def go(cell: Cell, block: str) -> None:
        ctx.set_score("#lift.steps", 0)
        started[0] = ctx.gametime() or 0
        press(cell, block)

    def travel(what: str, f: int, rider_y: int | None) -> None:
        """let the cage go, look at it half way, and see it arrive: by the
        pack's count a block at a time, and in the time a trip should take"""
        ctx.advance(LEAD + TRIP // 2)
        at, parts = ctx.score("#lift.y"), ctx.count(car)
        seats = 0 if rider_y is None else 1
        if ctx.score("#lift.busy") != 1 or at is None or not BOTTOM < at < TOP:
            problems.append(f"{what}: half way it is not on its way (floor at y {at})")
        if parts != 18 + seats:
            problems.append(f"{what}: {parts} travelling parts, not {18 + seats}")
        if seats and not BOTTOM + 1 < (ride_y() or 0) < TOP + 1:
            problems.append(f"{what}: half way the rider is at y {ride_y()}")
        if not WEIGHT_Y[TOP] < (height(WEIGHT)() or 0) < WEIGHT_Y[BOTTOM]:
            problems.append(f"{what}: half way the counterweight is at an end")
        for _ in range(40):
            if ctx.score("#lift.busy") == 0 == ctx.score("#lift.busy"):
                break
            ctx.advance(5)
        took = (ctx.gametime() or 0) - started[0]
        if started[0] and not LEAD + TRIP <= took <= LEAD + TRIP + 30:
            problems.append(f"{what}: took {took} ticks, not about {LEAD + TRIP}")
        started[0] = 0
        ctx.advance(2)
        standing(what, f)
        expect(f"{what}: steps taken", score("#lift.steps"), TOP - BOTTOM)
        expect(f"{what}: the rider's feet", ride_y, rider_y)

    problems += wrong(ctx, fixed)
    hole = opening_cells() - ring_cells(APEX)
    if (len(opening_cells()), len(hole)) != (25, 9):
        problems.append(f"the shaft opens {len(hole)} cells of the shell, not 9")
    standing("at rest", TOP)

    # down with a rider, by the button in the cage
    board(TOP)
    go(*inside_button("top"))
    travel("sent down", BOTTOM, BOTTOM + 1)
    # and up again
    go(*inside_button("bottom"))
    travel("sent up", TOP, TOP + 1)
    # called down empty, then called back up by a button at the top with a
    # rider in it
    ctx.cmd(f"kill {rider}")
    go(*call_button("bottom"))
    travel("called down", BOTTOM, None)
    board(BOTTOM)
    go(*call_button("top"))
    travel("called up", TOP, TOP + 1)
    # a button at the end where the cage is does nothing
    press(*call_button("top"))
    ctx.advance(LEAD)
    expect("called where it stands: busy", score("#lift.busy"), 0)
    # once it is on its way it heeds no button: sent down, called back and
    # sent down again in one tick, it goes down once
    ctx.cmd(f"kill {rider}")
    ctx.set_score("#lift.steps", 0)
    ctx.function("check/lift/thrice")
    expect("sent off three times: going to", score("#lift.to"), BOTTOM)
    travel("sent off three times", BOTTOM, None)
    # the reset, from the bottom and from on its way (or, if another
    # client's sprint has run it through, from the top)
    ctx.function("lift/reset")
    standing("reset from the bottom", TOP)
    ctx.function("lift/to/bottom")
    ctx.advance(LEAD + 4 * SUB)
    ctx.function("lift/reset")
    ctx.advance(LEAD + SUB)
    standing("reset on its way down", TOP)

    # the dome under it: dry, whole but for the opening
    return problems + domes.check_shell(ctx, START, empty=False)


domes.add_opening(START.index, opening_cells())

MODULE = game.Module(
    "shore",
    stages={"shore": build_shore, "dock": build_dock, "lift": build_lift},
    functions=functions,
    resets=("shore/reset", "lift/reset"),
    checks={"shore": check_shore, "dock": check_dock, "lift": check_lift},
)
