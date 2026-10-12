"""
Stairways and roads along a path.

A path is a polyline: a list of points, where each straight section runs
along x or along z (not diagonally). Turn corners by adding a point at the
corner. The path is the line of blocks that people walk on top of, and it is
*width* blocks wide, centred on the line (an even width has its extra block
on the right, looking along the path). Wide paths turn corners best where
they are level for a few blocks either side of the corner.

Each function returns the bounding box (a ``Volume``) of the blocks it placed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from mcipc.rcon.enumerations import FillMode
from mcwb import Item, Vec3, Volume

from mciwb.builders.blockstate import (
    Block,
    BlockState,
    facing_name,
    full_block_of,
    stair_shapes,
)
from mciwb.builders.placer import Placer, rectangles
from mciwb.builders.terrain import Heightmap, ground_heights

__all__ = ["PathStep", "road", "stairway", "trace_path"]


@dataclass(frozen=True)
class PathStep:
    """One block along the middle of a path"""

    #: the position of the block
    pos: Vec3
    #: the horizontal direction of travel into this block (out of it, for
    #: the first block)
    direction: Vec3


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def trace_path(points: Sequence[Vec3]) -> list[PathStep]:
    """
    The blocks along the middle of a path through *points*, with the
    heights of the blocks spread evenly between the heights of the points.

    In a section that climbs (or descends) by less than its length, the first
    block (last, when descending) after each point stays level, so that a
    corner is a landing.

    :raises ValueError: if a section is diagonal, or climbs more than one
        block for each block along
    """
    points = [Vec3(*p).with_ints() for p in points]
    if len(points) < 2:
        raise ValueError("a path needs at least two points")
    steps = [PathStep(points[0], Vec3(0, 0, 0))]
    for p, q in zip(points, points[1:], strict=False):
        dx, dz, rise = int(q.x - p.x), int(q.z - p.z), int(q.y - p.y)
        if dx and dz:
            raise ValueError(f"{p} to {q} is diagonal: run along x or z only")
        length = abs(dx) + abs(dz)
        if length == 0:
            if rise:
                raise ValueError(f"{p} to {q} is vertical")
            continue
        if abs(rise) > length:
            raise ValueError(
                f"{p} to {q} climbs {abs(rise)} blocks in {length}: stairs "
                "climb at most one block for each block along"
            )
        direction = Vec3(_sign(dx), 0, _sign(dz))
        for k in range(1, length + 1):
            # ceil(rise * k / length): climbs start at once, descents finish
            # at the end, so there is a level block at each corner
            y = p.y - (-rise * k // length)
            steps.append(PathStep(p + direction * k + Vec3(0, y - p.y, 0), direction))
    if len(steps) < 2:
        raise ValueError("the path has no length")
    steps[0] = PathStep(steps[0].pos, steps[1].direction)
    return steps


def _offsets(width: int) -> range:
    if width < 1:
        raise ValueError("width must be at least 1")
    return range(-((width - 1) // 2), width // 2 + 1)


def _right(direction: Vec3) -> Vec3:
    """the horizontal direction to the right of *direction*"""
    return Vec3(-direction.z, 0, direction.x)


def _spread(steps: list[PathStep], width: int) -> dict[tuple[int, int], int]:
    """
    Widen the path: map each (x, z) of the widened path to the index of the
    step that it belongs to. Corners get a square of the corner step.
    """
    offsets = _offsets(width)
    cells: dict[tuple[int, int], int] = {}
    corners = []
    for i, step in enumerate(steps):
        for o in offsets:
            pos = step.pos + _right(step.direction) * o
            # where a corner makes rows overlap, the earlier row wins
            cells.setdefault((int(pos.x), int(pos.z)), i)
        if i + 1 < len(steps) and steps[i + 1].direction != step.direction:
            corners.append(i)
    for i in corners:
        # fill the gap on the outside of the corner
        pos = steps[i].pos
        for a in offsets:
            for b in offsets:
                cells.setdefault((int(pos.x) + a, int(pos.z) + b), i)
    return cells


def stairway(
    points: Sequence[Vec3],
    stairs: Block = Item.STONE_BRICK_STAIRS,
    *,
    landing: Block | None = None,
    width: int = 1,
    support: Block | None = None,
    clearance: int = 0,
) -> Volume:
    """
    A stairway along a path, climbing (or descending) between the heights
    of its points.

    Each point is a block of the walkway, the block that people stand on, so
    the walkway's surface is one block above it. Each section between two
    points climbs at most one block for each block along it. Where a block
    is higher than the one before it there is a stairs block (facing the way
    up), elsewhere a level *landing* block. So ``points`` at the same height
    give a level path.

    For example, from (0, 64, 0) east to (4, 66, 0)::

                      ◢ #    y = 66: stairs, then a landing at the end
                  ◢ #        y = 65: stairs, landing
                #            y = 64: a landing at the start

    :param points: the walkway blocks at the start, each corner and the end
    :param stairs: the stairs to climb with
    :param landing: the block for the level parts, defaults to the full block
        matching *stairs* e.g. ``Item.STONE_BRICKS``
    :param width: the width of the stairway
    :param support: if given, fill the space under the stairway with this
        block, down to the height of its lowest block (only replacing air)
    :param clearance: set this many blocks above the walkway to air, to
        make headroom through the terrain
    :returns: the bounding box of the stairway
    """
    steps = trace_path(points)
    landing_state = BlockState.parse(
        full_block_of(stairs) if landing is None else landing
    )
    stairs_state = BlockState.of(stairs, half="bottom")

    # a stairs block on the higher block of each step up or down, facing
    # away from the lower block. A block between two lower blocks stays flat
    facing: dict[int, str | None] = {}
    for i in range(1, len(steps)):
        rise = steps[i].pos.y - steps[i - 1].pos.y
        if rise > 0:
            upper, toward = i, steps[i].direction
        elif rise < 0:
            upper, toward = i - 1, -steps[i].direction
        else:
            continue
        facing[upper] = None if upper in facing else facing_name(toward)

    cells = _spread(steps, width)
    blocks: dict[int, dict[tuple[int, int], str | None]] = {}  # y -> cells
    for (x, z), i in cells.items():
        blocks.setdefault(int(steps[i].pos.y), {})[(x, z)] = facing.get(i)

    placer = Placer()
    lowest = min(blocks)
    for y, layer in sorted(blocks.items()):
        if clearance > 0:
            for ax, az, bx, bz in rectangles(layer):
                placer.fill(Vec3(ax, y + 1, az), Vec3(bx, y + clearance, bz), Item.AIR)
        if support is not None and y > lowest:
            for ax, az, bx, bz in rectangles(layer):
                placer.fill(
                    Vec3(ax, lowest, az), Vec3(bx, y - 1, bz), support, FillMode.KEEP
                )
    for y, layer in sorted(blocks.items()):
        stair_cells = {pos: f for pos, f in layer.items() if f is not None}
        shapes = stair_shapes(stair_cells)
        placer.layer(
            y,
            {
                pos: landing_state
                if f is None
                else stairs_state.with_props(facing=f, shape=shapes[pos])
                for pos, f in layer.items()
            },
        )
    return placer.volume


def road(
    points: Sequence[Vec3],
    block: Block = Item.DIRT_PATH,
    *,
    width: int = 3,
    border: Block | None = None,
    clearance: int = 2,
    heightmap: Heightmap | str = Heightmap.MOTION_BLOCKING_NO_LEAVES,
) -> Volume:
    """
    A road along a path that follows the terrain: each block of the road
    replaces the top ground block of its column. The y of *points* is
    ignored.

    The road does not smooth the terrain, it steps up and down with it.
    Use `stairway` for a path at fixed heights.

    :param points: the start, each corner and the end of the road
    :param block: the road surface
    :param width: the width of the road
    :param border: if given, the blocks along both edges of the road
    :param clearance: set this many blocks above the road to air, clearing
        grass, flowers and snow
    :param heightmap: what counts as the ground, see `Heightmap`. The
        default ignores leaves, but the road goes over the top of water
    :returns: the bounding box of the road
    """
    steps = trace_path([Vec3(p.x, 0, p.z) for p in points])
    cells = _spread(steps, width)
    ground = ground_heights(cells, heightmap)

    # the edges are cells next to a cell that is not road, except beyond
    # the two ends of the road
    caps = set()
    for step, outward in ((steps[0], -1), (steps[-1], 1)):
        for o in _offsets(width):
            pos = step.pos + step.direction * outward + _right(step.direction) * o
            caps.add((int(pos.x), int(pos.z)))
    edges = set()
    for x, z in cells:
        for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if (nx, nz) not in cells and (nx, nz) not in caps:
                edges.add((x, z))

    by_height: dict[int, dict[tuple[int, int], Block]] = {}
    for pos, y in ground.items():
        edge = border is not None and pos in edges
        by_height.setdefault(y, {})[pos] = border if edge else block  # type: ignore

    placer = Placer()
    for y, layer in sorted(by_height.items()):
        if clearance > 0:
            for ax, az, bx, bz in rectangles(layer):
                placer.fill(Vec3(ax, y + 1, az), Vec3(bx, y + clearance, bz), Item.AIR)
        placer.layer(y, layer)
    return placer.volume
