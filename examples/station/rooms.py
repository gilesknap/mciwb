"""
Offline checks every room of The Drowned Station shares: what a dome's
module asks of its own plan (cell -> block) before anything is built. Pure
functions of the layout; each returns the problems it found.

- ``room_problems(dome, blocks, floor)``: every cell inside the dome and
  off the cells the tunnels reserve, the relaid floor in the floor,
  nothing waterlogged, and no block that means something in another dome.
- ``reach`` and ``walk_problems``: can a player walk from the entrance
  to each named place: feet and head in free cells with something to
  stand on, a step to the side level or one up or down (a stair, a slab,
  a jump), with room for the head on the way up?
- ``hidden`` and ``sight_problems``: is each named thing in sight from
  each named place (nothing opaque on the line from the eye)?
- ``window_problems``: is the outgoing door's window in sight from the
  entrance, as the pump event wants? A dome that means to break that
  (the Flooded Dome's dam, the Engine's pavilion) says so with
  ``domes.allow``.
- ``input_problems``: every lever, button and plate is a declared input,
  is carried by ``gold_block``, has a sign by it, and has nothing beside
  its block that redstone would work (a pressed button powers its block,
  and the block every piston, lamp, bulb or dropper touching it).
- **Blocks with a meaning.** ``MEANINGS`` says which blocks belong to one
  dome's puzzle (``mean(block, dome_index)``); ``room_problems`` refuses
  them anywhere else, so a player never meets the Gearworks' track in
  another room's dressing. Gold is the mark of an input everywhere and is
  in no list: gold that carries no input is colour.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import domes
import tunnels

if TYPE_CHECKING:
    from station_layout import Dome

Cell = domes.Cell

GOLD = "minecraft:gold_block"
#: what a player works: a block of these kinds is an input
INPUTS = ("lever", "_button", "pressure_plate")
#: what a powered block works, if it touches it
SENSITIVE = (
    "piston",
    "redstone_lamp",
    "copper_bulb",
    "dropper",
    "dispenser",
    "hopper",
    "note_block",
    "_door",
    "trapdoor",
    "fence_gate",
    "tnt",
    "rail",
    "redstone_wire",
    "repeater",
    "comparator",
    "redstone_torch",
    "redstone_wall_torch",
    "bell",
)
#: blocks one can see through, for sight lines
CLEAR = (
    "glass",
    "bars",
    "grate",
    "chain",
    "lightning_rod",
    "air",
    "sign",
    "torch",
    "barrier",
)
FACES = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0)]

#: block -> the index of the one dome it means something in
MEANINGS: dict[str, int] = {
    # the Gearworks: the two metals of its track, and its pipe when lit
    "minecraft:raw_gold_block": 2,
    "minecraft:raw_copper_block": 2,
    "minecraft:waxed_exposed_copper_bulb": 2,
}


def mean(block: str, dome_index: int) -> None:
    """register a block that means something in one dome's puzzle (when
    the module is imported), so that no other room may use it"""
    if MEANINGS.setdefault(block, dome_index) != dome_index:
        raise ValueError(f"{block} already means something in dome {MEANINGS[block]}")


def name(block: str) -> str:
    """a block without its states and NBT"""
    return block.partition("[")[0].partition("{")[0]


def is_input(block: str) -> bool:
    return any(kind in name(block) for kind in INPUTS)


def room_problems(
    dome: Dome, blocks: dict[Cell, str], floor: dict[Cell, str] | None = None, more=()
) -> list[str]:
    """
    A room's plan against its dome. ``blocks``: everything above the
    floor, cell -> block; ``floor``: the floor cells relaid; ``more``:
    cells the room uses that hold no block (where a piston's head rises,
    where something is summoned).
    """
    cells = domes.dome_cells(dome)
    problems = []
    inside = set(blocks) | set(more)
    if outside := inside - cells.interior:
        problems.append(f"{len(outside)} cells not inside {dome.name}: {min(outside)}")
    if taken := inside & tunnels.reserved_cells(dome):
        problems.append(f"{len(taken)} cells on reserved cells: {min(taken)}")
    floor = floor or {}
    if stray := set(floor) - cells.floor:
        problems.append(f"{len(stray)} floor cells are not in the floor: {min(stray)}")
    everything = {**floor, **blocks}
    wet = [c for c, b in everything.items() if "waterlogged=true" in b]
    if wet:
        problems.append(f"{len(wet)} blocks are waterlogged: {min(wet)}")
    for cell, block in sorted(everything.items()):
        owner = MEANINGS.get(name(block))
        if owner is not None and owner != dome.index:
            problems.append(
                f"{name(block)} at {cell} means something in dome {owner}, not here"
            )
    return problems


#: how far a player may fall into water (it breaks any fall)
WATER_DROP = 12


def reach(
    dome: Dome, start: Cell, solid, blocked=(), ladders=(), drop: int = 1, water=()
) -> set[Cell]:
    """
    The cells a player's feet can get to from ``start`` by walking.
    ``solid``: cells holding something to stand on (the dome's floor is
    added); ``blocked``: other cells a player cannot be in (a lantern, a
    bell, a cell kept shut); ``ladders``: cells holding a ladder, climbed
    cell by cell; ``drop``: how far down a step off an edge may be;
    ``water``: cells of standing water one deep (a basin, which may be let
    into the floor): a player can be in one with nothing underfoot, wades
    from one to the next, climbs out by a step up, and may fall into one
    from as high as ``WATER_DROP``. Nobody stands over water.
    """
    cells = domes.dome_cells(dome)
    water = set(water)
    full = set(solid) | set(blocked)
    ground = (set(cells.floor) - water) | set(solid)
    ladders = set(ladders)

    def free(cell: Cell) -> bool:
        return (cell in cells.interior or cell in water) and cell not in full

    def stands(cell: Cell) -> bool:
        x, y, z = cell
        held = (x, y - 1, z) in ground or cell in ladders or cell in water
        return free(cell) and free((x, y + 1, z)) and held

    seen, edge = {start}, [start]
    while edge:
        x, y, z = edge.pop()
        moves = []
        if (x, y, z) in ladders:
            moves += [(x, y + 1, z), (x, y - 1, z)]
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, *range(-1, -max(drop, WATER_DROP) - 1, -1)):
                to = (x + dx, y + dy, z + dz)
                if dy < -drop and to not in water:
                    continue
                head = (x, y + 2, z) if dy == 1 else (to[0], y + 1, to[2])
                fall = all(free((to[0], h, to[2])) for h in range(to[1], y + 2))
                if stands(to) and free(head) and (dy > 0 or fall):
                    moves.append(to)
        for to in moves:
            if to not in seen and stands(to):
                seen.add(to)
                edge.append(to)
    return seen


def walk_problems(
    dome: Dome, solid, targets: dict[str, Cell], blocked=(), start: Cell | None = None
) -> list[str]:
    """each of ``targets`` (name -> the cell the feet are in) can be
    walked to from ``start`` (default: the dome's entrance)"""
    if start is None:
        start = domes.entrance(dome)[:3]
    seen = reach(dome, start, solid, blocked)
    return [
        f"no walk from the entrance to {what} at {cell}"
        for what, cell in targets.items()
        if cell not in seen
    ]


def hidden(eye: Cell, target: Cell, opaque) -> set[Cell]:
    """the cells of ``opaque`` on the line from the eye of a player
    standing in ``eye`` to the middle of ``target``"""
    start = (eye[0] + 0.5, eye[1] + 1.62, eye[2] + 0.5)
    to = (target[0] + 0.5, target[1] + 0.5, target[2] + 0.5)
    steps = max(1, int(math.dist(start, to) * 8))
    found = set()
    for i in range(steps):
        cell = (
            math.floor(start[0] + (to[0] - start[0]) * i / steps),
            math.floor(start[1] + (to[1] - start[1]) * i / steps),
            math.floor(start[2] + (to[2] - start[2]) * i / steps),
        )
        if cell in opaque and cell != target:
            found.add(cell)
    return found


def opaque(blocks: dict[Cell, str]) -> set[Cell]:
    """the cells of a plan that block a view"""
    return {c for c, b in blocks.items() if not any(w in name(b) for w in CLEAR)}


def sight_problems(
    blocks: dict[Cell, str], eyes: dict[str, Cell], targets: dict[str, Cell]
) -> list[str]:
    """each of ``targets`` can be seen from each of ``eyes`` (name -> the
    cell a player stands in)"""
    solid = opaque(blocks)
    problems = []
    for where, eye in eyes.items():
        for what, cell in targets.items():
            if in_way := hidden(eye, cell, solid):
                problems.append(f"{what} is hidden from {where} by {min(in_way)}")
    return problems


def window_problems(dome: Dome, blocks: dict[Cell, str]) -> list[str]:
    """the outgoing door's window can be seen from the dome's entrance,
    unless the dome has said why not (``domes.allow``)"""
    if domes.ALLOWED.get(dome.index):
        return []
    tunnel = tunnels.layout.TUNNELS[dome.index]
    panes = {
        f"the outgoing door's window at {c}": c
        for c, b in domes.door_blocks(dome, tunnel).items()
        if b == domes.GLASS
    }
    eye = {"the entrance": domes.entrance(dome)[:3]}
    found = sight_problems(blocks, eye, panes)
    # a window is in sight if most of it is
    return found if len(found) > len(panes) // 2 else []


def carrier(cell: Cell, block: str) -> Cell:
    """the cell of the block an input is on: under a plate or a floor
    lever, over a ceiling one, behind one on a wall"""
    x, y, z = cell
    if "pressure_plate" in block or "face=floor" in block:
        return (x, y - 1, z)
    if "face=ceiling" in block:
        return (x, y + 1, z)
    for facing, (dx, dz) in ((n, s) for s, n in domes.COMPASS.items()):
        if f"facing={facing}" in block:
            return (x - dx, y, z - dz)
    return (x, y - 1, z)


def input_problems(
    blocks: dict[Cell, str], inputs, worked=(), floor: dict[Cell, str] | None = None
) -> list[str]:
    """
    A plan's levers, buttons and plates against the room's list of
    ``inputs`` (cells). Each must be in the list, be carried by
    ``gold_block``, and have a sign within two blocks; and its gold block
    must touch nothing redstone would work, but the cells in ``worked``
    (what the input is meant to drive by real redstone).
    """
    everything = {**(floor or {}), **blocks}
    wanted = set(inputs)
    problems = []
    found = {c for c, b in blocks.items() if is_input(b)}
    problems += [
        f"an input at {c} that the room does not list" for c in sorted(found - wanted)
    ]
    problems += [
        f"no input at {c}, which the room lists" for c in sorted(wanted - found)
    ]
    signs = [c for c, b in everything.items() if "sign" in name(b)]
    for cell in sorted(found & wanted):
        on = carrier(cell, blocks[cell])
        if name(everything.get(on, "")) != GOLD:
            problems.append(f"the input at {cell} is not on gold ({on})")
        if not any(math.dist(cell, s) <= 2.5 for s in signs):
            problems.append(f"the input at {cell} has no sign by it")
        for dx, dy, dz in FACES:
            beside = (on[0] + dx, on[1] + dy, on[2] + dz)
            block = name(everything.get(beside, ""))
            if beside in worked or beside == cell or not block:
                continue
            if any(kind in block for kind in SENSITIVE):
                problems.append(
                    f"{block} at {beside} touches the block of the input at {cell}"
                )
    return problems
