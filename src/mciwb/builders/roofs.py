"""
Roofs over a rectangular footprint: gable, hip and flat (with a parapet).

Each roof covers the rectangle between two opposite corners, *start* and
*end*, which are usually the corners of the tops of the walls. The roof's
lowest course is at ``start.y + 1``, i.e. directly on top of walls whose top
blocks are at ``start.y`` (the y of *end* is ignored). The sloping roofs are
built from stairs that rise one block for each block in from the eaves.

Each function returns the bounding box (a ``Volume``) of the blocks it placed.
"""

from __future__ import annotations

from mcwb import Item, Vec3, Volume

from mciwb.builders.blockstate import Block, BlockState, slab_of, stair_shapes
from mciwb.builders.placer import Placer

__all__ = ["flat_roof", "gable_roof", "hip_roof"]


def _footprint(start: Vec3, end: Vec3, overhang: int) -> tuple[int, int, int, int]:
    """(x1, z1, x2, z2) with x1 <= x2 and z1 <= z2, expanded by overhang"""
    x1, x2 = sorted((int(start.x), int(end.x)))
    z1, z2 = sorted((int(start.z), int(end.z)))
    if overhang < 0:
        raise ValueError("overhang must not be negative")
    return x1 - overhang, z1 - overhang, x2 + overhang, z2 + overhang


def _ridge_state(stairs: Block, ridge: Block | None) -> BlockState:
    state = BlockState.parse(slab_of(stairs) if ridge is None else ridge)
    if state.name.endswith("_slab") and "type" not in state.props:
        state = state.with_props(type="bottom")
    return state


def _ridge_core(ridge: BlockState) -> BlockState:
    """
    The block under a ridge, between the stairs of the course below it: the
    ridge as a full block (a double slab) so that there is no hole under it
    """
    if ridge.name.endswith("_slab"):
        return ridge.with_props(type="double")
    return ridge


def gable_roof(
    start: Vec3,
    end: Vec3,
    stairs: Block = Item.OAK_STAIRS,
    *,
    ridge: Block | None = None,
    gable: Block | None = None,
    axis: str | None = None,
    overhang: int = 0,
) -> Volume:
    """
    A gable (pitched) roof: two slopes of stairs meeting at a ridge.

    For a footprint 7 wide across the ridge, seen from the gable end
    (``#`` is the *gable*, if one is given)::

              ▄            <- ridge slab, y = start.y + 4
            ◢ # ◣
          ◢ # # # ◣
        ◢ # # # # # ◣      <- stairs, y = start.y + 1
        W . . . . . W      <- walls, top at start.y

    :param start: a corner of the footprint, e.g. the top of a corner of the
        walls; the roof starts at ``start.y + 1``
    :param end: the opposite corner of the footprint (only x and z are used)
    :param stairs: the stairs to build the slopes from
    :param ridge: the block along the ridge when the footprint is an odd
        number of blocks across. Defaults to the slab matching *stairs*,
        placed as a bottom slab. The gap under it, between the stairs of
        the course below, is filled with the same block as a double slab
        (or with *ridge* itself if it is not a slab)
    :param gable: if given, fill the triangular gable ends under the roof
        with this block, above the footprint's end walls
    :param axis: ``"x"`` or ``"z"``, the direction that the ridge runs.
        Defaults to the longer side of the footprint
    :param overhang: extend the roof this many blocks past the footprint on
        every side (the slopes stay at the same height, so the eaves overhang
        the walls)
    :returns: the bounding box of the roof (and gables)
    """
    x1, z1, x2, z2 = _footprint(start, end, overhang)
    if axis is None:
        axis = "x" if x2 - x1 >= z2 - z1 else "z"
    if axis not in ("x", "z"):
        raise ValueError("axis must be 'x' or 'z'")

    # work in (along, across) the ridge; to_world maps back to (x, z)
    if axis == "x":
        a1, a2, c1, c2 = x1, x2, z1, z2
        rising, falling = "south", "north"  # facing of the low and high sides

        def to_world(a: int, c: int) -> tuple[int, int]:
            return a, c
    else:
        a1, a2, c1, c2 = z1, z2, x1, x2
        rising, falling = "east", "west"

        def to_world(a: int, c: int) -> tuple[int, int]:
            return c, a

    placer = Placer()
    base_y = int(start.y) + 1
    slope = BlockState.of(stairs, half="bottom", shape="straight")
    ridge_state = _ridge_state(stairs, ridge)
    core_state = _ridge_core(ridge_state)
    gable_ends = (a1 + overhang, a2 - overhang)

    course = 0
    while c1 + course <= c2 - course:
        y = base_y + course
        lo, hi = c1 + course, c2 - course
        cells: dict[tuple[int, int], BlockState] = {}
        for a in range(a1, a2 + 1):
            if lo == hi:
                cells[to_world(a, lo)] = ridge_state
            else:
                cells[to_world(a, lo)] = slope.with_props(facing=rising)
                cells[to_world(a, hi)] = slope.with_props(facing=falling)
            if hi - lo == 2 and not (gable is not None and a in gable_ends):
                # the ridge goes on the next course: fill the gap under it
                cells[to_world(a, lo + 1)] = core_state
        placer.layer(y, cells)

        # the gable ends: inside the slopes, above the footprint's ends
        g_lo, g_hi = max(lo + 1, c1 + overhang), min(hi - 1, c2 - overhang)
        if gable is not None and g_lo <= g_hi:
            for a in gable_ends:
                wx1, wz1 = to_world(a, g_lo)
                wx2, wz2 = to_world(a, g_hi)
                placer.fill(Vec3(wx1, y, wz1), Vec3(wx2, y, wz2), gable)
        course += 1

    return placer.volume


def hip_roof(
    start: Vec3,
    end: Vec3,
    stairs: Block = Item.OAK_STAIRS,
    *,
    ridge: Block | None = None,
    overhang: int = 0,
) -> Volume:
    """
    A hip roof: four slopes of stairs, one from each side of the footprint,
    with outer corner stairs where they meet. Each course is a ring of stairs
    one block in and one block up from the course below. Where the slopes
    meet along a line one block wide (the ridge) the roof is finished with
    *ridge* blocks, on a line of full blocks (the ridge slab doubled) that
    fills the middle of the course below.

    :param start: a corner of the footprint, e.g. the top of a corner of the
        walls; the roof starts at ``start.y + 1``
    :param end: the opposite corner of the footprint (only x and z are used)
    :param stairs: the stairs to build the slopes from
    :param ridge: the block for a ridge one block wide, defaults to the slab
        matching *stairs*, placed as a bottom slab. The middle of the course
        below it is filled with the same block as a double slab (or with
        *ridge* itself if it is not a slab)
    :param overhang: extend the roof this many blocks past the footprint on
        every side
    :returns: the bounding box of the roof
    """
    x1, z1, x2, z2 = _footprint(start, end, overhang)
    placer = Placer()
    base_y = int(start.y) + 1
    slope = BlockState.of(stairs, half="bottom")
    ridge_state = _ridge_state(stairs, ridge)
    core_state = _ridge_core(ridge_state)

    course = 0
    while x1 + course <= x2 - course and z1 + course <= z2 - course:
        y = base_y + course
        lx, hx = x1 + course, x2 - course
        lz, hz = z1 + course, z2 - course

        if lx == hx or lz == hz:
            # the slopes meet in a line: finish with the ridge
            placer.fill(Vec3(lx, y, lz), Vec3(hx, y, hz), ridge_state)
            break

        # a ring of stairs facing inwards, the corners belong to the north
        # and south sides and the server makes them outer corners
        facings: dict[tuple[int, int], str] = {}
        for x in range(lx, hx + 1):
            facings[(x, lz)] = "south"
            facings[(x, hz)] = "north"
        for z in range(lz + 1, hz):
            facings[(lx, z)] = "east"
            facings[(hx, z)] = "west"
        shapes = stair_shapes(facings)
        cells = {
            pos: slope.with_props(facing=facing, shape=shapes[pos])
            for pos, facing in facings.items()
        }
        if hx - lx == 2 or hz - lz == 2:
            # the ridge goes on the next course, over the middle of this
            # ring: fill the middle so that there is no hole under it
            for x in range(lx + 1, hx):
                for z in range(lz + 1, hz):
                    cells[(x, z)] = core_state
        placer.layer(y, cells)
        course += 1

    return placer.volume


def flat_roof(
    start: Vec3,
    end: Vec3,
    block: Block = Item.SMOOTH_STONE,
    *,
    parapet: Block | None = None,
    parapet_height: int = 1,
    overhang: int = 0,
) -> Volume:
    """
    A flat roof: one layer of *block*, optionally with a parapet around its
    edge.

    :param start: a corner of the footprint, e.g. the top of a corner of the
        walls; the roof is at ``start.y + 1``
    :param end: the opposite corner of the footprint (only x and z are used)
    :param block: the roof block, e.g. a full block or a slab
    :param parapet: if given, build a low wall of this block around the edge
        of the roof, on top of it. Walls, fences and panes join up
        automatically
    :param parapet_height: the height of the parapet
    :param overhang: extend the roof this many blocks past the footprint on
        every side
    :returns: the bounding box of the roof and parapet
    """
    x1, z1, x2, z2 = _footprint(start, end, overhang)
    placer = Placer()
    y = int(start.y) + 1
    placer.fill(Vec3(x1, y, z1), Vec3(x2, y, z2), block)

    if parapet is not None and parapet_height > 0:
        top = y + parapet_height
        corners = [(x1, z1, x2, z1), (x1, z2, x2, z2), (x1, z1, x1, z2)]
        corners.append((x2, z1, x2, z2))
        for ax, az, bx, bz in corners:
            placer.fill(Vec3(ax, y + 1, az), Vec3(bx, top, bz), parapet)

    return placer.volume
