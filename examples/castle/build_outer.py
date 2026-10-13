"""
The outer works: earthworks, curtain walls, towers, gatehouse, bridge and
road, the grand stair and the keep's shell. Each stage is a function; the
driver (build_castle.py) runs them in order.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

import castle_lib as L
from castle_layout import (
    BANNER,
    BANNER2,
    BRIDGE_END,
    DITCH_FLOOR,
    GATE_BANNER_DX,
    GATE_X1,
    GATE_X2,
    GATEHOUSE,
    KEEP,
    KEEP_ROOF,
    LD,
    MAIN_GATE,
    MIDDLE_GATE,
    MOAT_FLOOR,
    MOAT_W,
    NAME,
    ORIGIN,
    SITE_TOP,
    SPAWN,
    TR,
    UD,
    WALL_H,
    XG,
    YU,
    ZS,
    V,
    W,
    centre,
    site_box,
)
from mcwb import Vec3

from mciwb.builders import arch, foundation, ground_height, road, stairway
from mciwb.builders import paths as _paths
from mciwb.builders import terrain as _terrain
from mciwb.builders.placer import BuildError, Placer, rectangles
from mciwb.threads import get_client

N, S, E, Wd = Vec3(0, 0, -1), Vec3(0, 0, 1), Vec3(1, 0, 0), Vec3(-1, 0, 0)


# ---------------------------------------------------------------- workaround
# gilesknap/mciwb#166 (item 2): the server keeps one output buffer for all
# its RCON connections, so when another client (the dashboard polling
# ``list``) runs a command at the same moment, a reply comes back empty or
# with the other client's output in front of ours. About one in 10k
# commands. mciwb's ground_heights then aborts the whole foundation, and
# Placer.fill and Placer.setblock raise BuildError. Until the library copes
# with it, this section wraps them: a polluted reply that still holds the
# command's own reply is accepted, an empty one is retried a few times.
# Delete it when the fix is released.

RETRIES = 3
OK_REPLIES = (
    "Changed the block",
    "Could not set the block",
    "Successfully filled",
    "No blocks were filled",
)


def _retrying(method):
    """a Placer method that accepts a polluted reply and retries an empty one"""

    def wrapper(self, *args, **kwargs):
        for attempt in range(RETRIES):
            try:
                return method(self, *args, **kwargs)
            except BuildError as e:
                reply = str(e).partition(" failed: ")[2]
                if any(ok in reply for ok in OK_REPLIES):
                    return reply
                if reply.strip() or attempt == RETRIES - 1:
                    raise
                print(f"   retrying: {e}")

    return wrapper


Placer.fill = _retrying(Placer.fill)
Placer.setblock = _retrying(Placer.setblock)


def ground_heights_retry(
    columns: Iterable[tuple[float, float]],
    heightmap: _terrain.Heightmap | str = _terrain.Heightmap.MOTION_BLOCKING_NO_LEAVES,
) -> dict[tuple[int, int], int]:
    import re
    from math import floor
    from uuid import uuid4

    teleported = re.compile(r"Teleported .* to (-?[\d.]+), (-?[\d.]+), (-?[\d.]+)")
    columns = [(floor(x), floor(z)) for x, z in columns]
    if not columns:
        return {}
    heightmap = _terrain.Heightmap(heightmap).value
    client = get_client()
    tag = f"mciwb_{uuid4().hex[:8]}"
    entity = f"@e[type=minecraft:marker,tag={tag},limit=1]"
    x, z = columns[0]
    result = client.run(f'summon minecraft:marker {x} 0 {z} {{Tags:["{tag}"]}}')
    if not result.startswith("Summoned"):
        raise BuildError(f"could not summon a marker at {x} 0 {z}: {result}")
    heights = {}
    try:
        for x, z in columns:
            for _attempt in range(5):
                result = client.run(
                    f"execute positioned {x} 0 {z} positioned over {heightmap} run tp {entity} ~ ~ ~"
                )
                match = teleported.search(result)
                if match:
                    break
                print(f"   retrying the ground at {x}, {z}: {result!r}")
                if "No entity" in result:
                    client.run(f'summon minecraft:marker {x} 0 {z} {{Tags:["{tag}"]}}')
            else:
                raise BuildError(f"could not read the ground at {x}, {z}: {result}")
            heights[(x, z)] = round(float(match.group(2))) - 1
    finally:
        client.run(f"kill @e[type=minecraft:marker,tag={tag}]")
    return heights


_terrain.ground_heights = ground_heights_retry
_paths.ground_heights = ground_heights_retry
# ---------------------------------------------------------------- end workaround

# local cell sets of the big regions
BAILEY = L.rect(-1, UD - 1, W, UD + LD)  # platform incl. a 1-block berm
UPPER = L.rect(-1, -1, W, UD - 1)
MOAT = (
    L.rect(-MOAT_W - 1, UD - 1, -2, ZS + MOAT_W + 1)
    | L.rect(W + 1, UD - 1, W + MOAT_W, ZS + MOAT_W + 1)
    | L.rect(-MOAT_W - 1, ZS + 2, W + MOAT_W, ZS + MOAT_W + 1)
)
BANK = (
    L.rect(-MOAT_W - 2, UD - 1, -MOAT_W - 2, ZS + MOAT_W + 2)
    | L.rect(W + MOAT_W + 1, UD - 1, W + MOAT_W + 1, ZS + MOAT_W + 2)
    | L.rect(-MOAT_W - 2, ZS + MOAT_W + 2, W + MOAT_W + 1, ZS + MOAT_W + 2)
)
DITCH = (
    L.rect(-MOAT_W - 1, -MOAT_W - 1, W + MOAT_W, -2)
    | L.rect(-MOAT_W - 1, -MOAT_W - 1, -2, UD - 2)
    | L.rect(W + 1, -MOAT_W - 1, W + MOAT_W, UD - 2)
)


def wcells(cells: L.Cells) -> L.Cells:
    """local cells to world cells"""
    return {(ORIGIN.x + x, ORIGIN.z + z) for x, z in cells}


def portcullis_args(gate: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """a gate's (x1, x2, z, standing level) from local to world"""
    x1, x2, z, y0 = gate
    return ORIGIN.x + x1, ORIGIN.x + x2, ORIGIN.z + z, ORIGIN.y + y0


def foundation_cells(cells: L.Cells, top_y: int, block: str) -> None:
    """a level platform at local top_y over a set of cells, filled down to the ground"""
    for ax, az, bx, bz in rectangles(wcells(cells)):
        foundation(
            Vec3(ax, ORIGIN.y + top_y, az),
            Vec3(bx, ORIGIN.y + top_y, bz),
            block,
            max_depth=48,
        )


# ---------------------------------------------------------------- the site and the road

ROAD_MARGIN = 5  # how far the road keeps from the site
FORCELOAD_LIMIT = 256  # chunks per forceload command


def bridge_foot() -> Vec3:
    """the first block beyond the bridge, where the stair to the ground starts"""
    return V(XG, -1, BRIDGE_END + 1)


def road_start() -> Vec3:
    """
    Where the road begins: at the ground, beyond the stair that runs down
    (or up) from the bank at the end of the bridge, one block per block of
    height. Needs the chunks loaded; `bridge_foot` is the stair's top.
    """
    foot = bridge_foot()
    ground = ground_height(foot.x, foot.z + 6)
    run = abs(foot.y - ground)
    if run > MAX_STAIR:
        raise BuildError(f"the ground at the bridge is {run} blocks from the bank")
    return Vec3(foot.x, ground, foot.z + run + 1)


MAX_STAIR = 48  # the most the stair can drop or climb (foundation.max_depth)


def road_points(start: Vec3) -> list[Vec3]:
    """
    The corners of the road from ``start`` (see `road_start`) to SPAWN,
    round the castle's site and never through it: south until clear of the
    site, then, unless spawn is south of there, north along the side of the
    site nearer spawn as far as spawn's row, then along it to spawn. y is
    ignored: the road follows the ground.
    """
    a, b = site_box()
    x1, x2 = a.x - ROAD_MARGIN, b.x + ROAD_MARGIN
    zs = max(int(start.z), b.z + ROAD_MARGIN)
    points = [start, Vec3(start.x, 0, zs)]
    if SPAWN.z < zs:
        # hug the site's side, then go along spawn's row: the shortest
        # route keeps near the castle and away from whatever is at spawn
        side = x1 if SPAWN.x < (x1 + x2) / 2 else x2
        points += [Vec3(side, 0, zs), Vec3(side, 0, SPAWN.z)]
    else:
        points.append(Vec3(start.x, 0, SPAWN.z))
    points.append(Vec3(SPAWN.x, 0, SPAWN.z))
    route = [points[0]]
    for p in points[1:]:
        if (p.x, p.z) != (route[-1].x, route[-1].z):
            route.append(p)
    return route


def chunk_pieces(
    x1: int, z1: int, x2: int, z2: int, limit: int = FORCELOAD_LIMIT
) -> list[tuple[int, int, int, int]]:
    """a block box split into boxes of at most ``limit`` chunks each"""
    cx1, cx2, cz1, cz2 = x1 // 16, x2 // 16, z1 // 16, z2 // 16
    columns = min(cx2 - cx1 + 1, limit)
    rows = max(1, limit // columns)
    pieces = []
    for cx in range(cx1, cx2 + 1, columns):
        for cz in range(cz1, cz2 + 1, rows):
            ex, ez = min(cx + columns - 1, cx2), min(cz + rows - 1, cz2)
            pieces.append((cx * 16, cz * 16, ex * 16 + 15, ez * 16 + 15))
    return pieces


def wait_loaded(
    points: Iterable[tuple[int, int]], chunks: int, timeout: float = 60
) -> None:
    """
    Wait until the chunks at these (x, z) have their blocks, then a moment
    more for their entities: forceloading only asks for the chunks, and a
    build is faster than the loading, so commands sent at once find no
    chunk, or no entities. (``execute if loaded`` cannot be used: a server
    with no players does not tick, and never calls a chunk fully loaded.)
    ``chunks`` is how many were asked for.
    """
    import time

    deadline = time.time() + timeout
    for x, z in points:
        while "not loaded" in L.cmd(f"execute if block {x} 0 {z} minecraft:air"):
            if time.time() > deadline:
                raise BuildError(
                    f"chunk at {x}, {z} still not loaded after {timeout} s"
                )
            time.sleep(0.5)
    time.sleep(2 + chunks / 100)
    # a server with no players does not tick, and until it has ticked the
    # chunks their entities are not selectable: make it tick a little
    L.tick(20)
    time.sleep(1)


def forceload(add: bool = True, with_road: bool = True) -> None:
    """forceload (or unload) the site and, if asked, the road to spawn; when
    loading, wait until the chunks are in"""
    a, b = site_box()
    xs, zs = [a.x, b.x], [a.z, b.z]
    if with_road:
        # the road's start depends on the ground, not known until the
        # chunks are loaded: allow for the longest stair
        foot = bridge_foot()
        for p in road_points(Vec3(foot.x, 0, foot.z + MAX_STAIR + 1)):
            xs += [p.x - 4, p.x + 4]
            zs += [p.z - 4, p.z + 4]
    x1, z1, x2, z2 = min(xs), min(zs), max(xs), max(zs)
    for px1, pz1, px2, pz2 in chunk_pieces(x1, z1, x2, z2):
        print(L.cmd(f"forceload {'add' if add else 'remove'} {px1} {pz1} {px2} {pz2}"))
    if add:
        corners = [
            (x, z) for x in (x1, (x1 + x2) // 2, x2) for z in (z1, (z1 + z2) // 2, z2)
        ]
        wait_loaded(corners, (x2 - x1) * (z2 - z1) // 256)


def earthworks() -> None:
    """clear the site and make the two platforms, the moat and the ditch"""
    # clear: the bailey from its standing level up, the upper ward from its
    # standing level, the moat and ditch from their floors up
    L.fill_cells(wcells(BAILEY | BANK), ORIGIN.y, ORIGIN.y + SITE_TOP, L.AIR)
    L.fill_cells(wcells(UPPER), ORIGIN.y + YU, ORIGIN.y + SITE_TOP, L.AIR)
    L.fill_cells(wcells(MOAT), ORIGIN.y + MOAT_FLOOR + 1, ORIGIN.y + SITE_TOP, L.AIR)
    L.fill_cells(wcells(DITCH), ORIGIN.y + DITCH_FLOOR + 1, ORIGIN.y + SITE_TOP, L.AIR)
    # platforms
    foundation_cells(BAILEY, -1, L.STONE)
    foundation_cells(UPPER, YU - 1, L.STONE)
    foundation_cells(MOAT, MOAT_FLOOR, "minecraft:gravel")
    foundation_cells(BANK, -1, L.BRICK)
    foundation_cells(DITCH, DITCH_FLOOR, "minecraft:coarse_dirt")
    # water in the moat
    L.fill_cells(wcells(MOAT), ORIGIN.y + MOAT_FLOOR + 1, ORIGIN.y - 2, L.WATER)
    # grass on the wards (the walls and buildings replace their own footprints)
    L.fill(V(3, -1, UD + 3), V(W - 4, -1, ZS - 3), "minecraft:grass_block")
    L.fill(V(3, YU - 1, 3), V(W - 4, YU - 1, UD - 4), "minecraft:grass_block")
    # the cliff face between the wards, dressed in stone with buttresses
    L.fill(V(0, 0, UD - 1), V(W - 1, YU - 1, UD - 1), L.BRICK)
    for x in range(6, W - 6, 12):
        if abs(x - XG) > 8:
            L.fill(V(x, 0, UD), V(x + 1, YU - 6, UD), L.BRICK)
            L.fill(
                V(x, YU - 5, UD),
                V(x + 1, YU - 5, UD),
                f"{L.BRICK_STAIRS}[facing=south,half=top]",
            )


def bailey_walls() -> None:
    y = 0
    # west, east and south curtains (the south one in two parts round the gatehouse)
    L.curtain(V(0, y, UD), V(0, y, ZS), WALL_H, Wd)
    L.curtain(V(W - 1, y, UD), V(W - 1, y, ZS), WALL_H, E)
    L.curtain(V(0, y, ZS), V(GATEHOUSE[0] - 1, y, ZS), WALL_H, S)
    L.curtain(V(GATEHOUSE[2] + 1, y, ZS), V(W - 1, y, ZS), WALL_H, S)
    L.weather(
        wcells(
            L.rect(0, UD, 0, ZS)
            | L.rect(W - 1, UD, W - 1, ZS)
            | L.rect(0, ZS, W - 1, ZS)
        ),
        ORIGIN.y + 2,
        ORIGIN.y + WALL_H - 1,
    )
    # corner towers straddling the corners, and mid-wall towers
    walk = WALL_H
    towers = [
        (3, ZS - 3, [(walk, N, -1), (walk, E, 1), (0, N, 1)], BANNER),
        (W - 4, ZS - 3, [(walk, N, 1), (walk, Wd, 1), (0, N, -1)], BANNER),
        (3, 105, [(walk, N, -1), (walk, S, -1), (0, E, 0)], None),
        (W - 4, 105, [(walk, N, 1), (walk, S, 1), (0, Wd, 0)], None),
    ]
    for cx, cz, doors, banner in towers:
        r = TR if cz != 105 else TR - 1
        L.round_tower(
            ORIGIN.x + cx,
            ORIGIN.z + cz,
            r,
            ORIGIN.y + MOAT_FLOOR,
            ORIGIN.y + walk + 8,
            floors=[ORIGIN.y, ORIGIN.y + walk],
            doors=[(ORIGIN.y + dy, d, o) for dy, d, o in doors],
            banner=banner,
        )
    # the junction towers where the bailey walls meet the cliff: up past the upper ward's walls
    for cx, doors in (
        (3, [(walk, S, -1), (YU + WALL_H, N, -1), (0, S, 1), (YU, S, 1)]),
        (W - 4, [(walk, S, 1), (YU + WALL_H, N, 1), (0, S, -1), (YU, S, -1)]),
    ):
        L.round_tower(
            ORIGIN.x + cx,
            ORIGIN.z + UD - 1,
            TR,
            ORIGIN.y + MOAT_FLOOR,
            ORIGIN.y + YU + WALL_H + 8,
            floors=[ORIGIN.y, ORIGIN.y + walk, ORIGIN.y + YU, ORIGIN.y + YU + walk],
            doors=[(ORIGIN.y + dy, d, o) for dy, d, o in doors],
            banner=BANNER2,
        )
    # stairs from the courtyard up to the wall walks (west, east, and beside the gatehouse)
    stairway(
        [V(3, -1, 100), V(3, walk - 1, 110)],
        L.BRICK_STAIRS,
        width=2,
        support=L.BRICK,
        clearance=3,
    )
    stairway(
        [V(W - 4, -1, 100), V(W - 4, walk - 1, 110)],
        L.BRICK_STAIRS,
        width=2,
        support=L.BRICK,
        clearance=3,
    )
    stairway(
        [V(GATEHOUSE[0] - 14, -1, ZS - 3), V(GATEHOUSE[0] - 4, walk - 1, ZS - 3)],
        L.BRICK_STAIRS,
        width=2,
        support=L.BRICK,
        clearance=3,
    )
    stairway(
        [V(GATEHOUSE[2] + 14, -1, ZS - 3), V(GATEHOUSE[2] + 4, walk - 1, ZS - 3)],
        L.BRICK_STAIRS,
        width=2,
        support=L.BRICK,
        clearance=3,
    )


def gatehouse() -> dict:
    x1, z1, x2, z2 = GATEHOUSE
    top = 16
    # the solid block, from the moat floor
    L.fill(V(x1, MOAT_FLOOR, z1), V(x2, top - 1, z2), L.BRICK)
    L.fill(V(x1, MOAT_FLOOR, z1), V(x2, 1, z2), L.DARK_BRICK)
    # parapet and merlons round the top
    L.fill(V(x1, top, z1), V(x2, top, z2), L.BRICK)
    L.fill(V(x1 + 1, top, z1 + 1), V(x2 - 1, top, z2 - 1), L.AIR)
    L.fill(V(x1, top - 1, z1), V(x2, top - 1, z2), L.ANDESITE)
    L.merlons(
        [(ORIGIN.x + x, ORIGIN.z + z1) for x in range(x1, x2 + 1)]
        + [(ORIGIN.x + x, ORIGIN.z + z2) for x in range(x1, x2 + 1)]
        + [(ORIGIN.x + x1, ORIGIN.z + z) for z in range(z1, z2 + 1)]
        + [(ORIGIN.x + x2, ORIGIN.z + z) for z in range(z1, z2 + 1)],
        ORIGIN.y + top + 1,
    )
    # the passage, 3 wide and 2 high, through the whole depth
    L.fill(V(GATE_X1, 0, z1 - 1), V(GATE_X2, 1, z2), L.AIR)
    L.fill(V(GATE_X1, -1, z1 - 1), V(GATE_X2, -1, z2), L.ANDESITE)
    # a tall pointed arch recess on the outer face, 7 wide
    arch(
        V(XG - 3, 0, z2 - 1),
        V(XG + 3, 0, z2 - 1),
        L.CHISELED,
        style="pointed",
        depth=2,
        clear=True,
    )
    L.fill(
        V(XG - 2, 0, z2 - 1), V(XG + 2, 3, z2 - 1), L.BARS
    )  # a fixed grille in the recess...
    L.fill(
        V(GATE_X1, 0, z2 - 1), V(GATE_X2, 1, z2), L.AIR
    )  # ...with the passage through it
    L.fill(V(GATE_X1, 2, z2 - 1), V(GATE_X2, 2, z2), L.BARS)
    # the west guard room, with a door to the passage and one to the bailey
    L.fill(V(x1 + 7, 0, z1 + 1), V(GATE_X1 - 2, 3, z2 - 2), L.AIR)
    L.fill(V(GATE_X1 - 1, 0, z1 + 3), V(GATE_X1 - 1, 1, z1 + 3), L.AIR)
    L.fill(V(x1 + 9, 0, z1), V(x1 + 9, 1, z1), L.AIR)
    L.fill(V(x1 + 7, -1, z1 + 1), V(GATE_X1 - 2, -1, z2 - 2), L.PLANKS)
    # the winch room above the passage and the guard room, with a stair up from the guard room
    L.fill(V(x1 + 7, 4, z1 + 1), V(GATE_X2 + 3, 7, z2 - 2), L.AIR)
    L.fill(V(x1 + 7, 3, z1 + 1), V(GATE_X2 + 3, 3, z2 - 2), L.PLANKS)
    stairway(
        [V(x1 + 7, -1, z2 - 3), V(x1 + 11, 3, z2 - 3)],
        "minecraft:dark_oak_stairs",
        width=2,
        support=L.PLANKS,
        clearance=3,
    )
    # murder holes: a grille in the winch room floor over the passage
    L.fill(V(GATE_X1, 2, z1 + 2), V(GATE_X2, 2, z1 + 2), L.AIR)
    L.fill(V(GATE_X1, 3, z1 + 2), V(GATE_X2, 3, z1 + 2), L.BARS)
    # the portcullis itself
    g = L.portcullis(*portcullis_args(MAIN_GATE))
    # drum towers straddling the gatehouse's outer corners (clear of the
    # portcullis wiring channel east of the passage), up past the gatehouse top
    for cx, doors in (
        (x1 - 2, [(0, N, 0), (top, E, 0)]),
        (x2 + 2, [(0, N, 0), (top, Wd, 0)]),
    ):
        L.round_tower(
            ORIGIN.x + cx,
            ORIGIN.z + z2 - 3,
            4,
            ORIGIN.y + MOAT_FLOOR,
            ORIGIN.y + top + 8,
            floors=[ORIGIN.y, ORIGIN.y + top],
            doors=[(ORIGIN.y + dy, d, o) for dy, d, o in doors],
            banner=BANNER,
        )
    # a lamp and banners over the arch (clear of the drawbridge chains at XG +- 4)
    for x in (XG - GATE_BANNER_DX, XG + GATE_BANNER_DX):
        L.set_block(V(x, 5, z2 + 1), f"minecraft:{BANNER}_wall_banner[facing=south]")
    L.set_block(V(XG, 6, z2 + 1), f"{L.LANTERN}[hanging=true]")
    L.set_block(V(XG, 7, z2 + 1), L.CHAIN)
    L.set_block(V(XG, 8, z2 + 1), L.CHAIN)
    L.set_block(V(XG, 9, z2), L.BRICK)
    # dungeon stair: not here (see build_inner)
    return g


def bridge_and_road() -> None:
    z1 = ZS + 1
    z2 = ZS + MOAT_W + 2
    # the bridge over the moat, 7 wide, with fences and lanterns
    L.fill(V(XG - 3, -1, z1), V(XG + 3, -1, z2), L.PLANKS)
    L.fill(V(XG - 3, -2, z1), V(XG + 3, -2, z2), "minecraft:dark_oak_log[axis=z]")
    L.fill(V(XG - 3, 0, z1), V(XG - 3, 0, z2), "minecraft:dark_oak_fence")
    L.fill(V(XG + 3, 0, z1), V(XG + 3, 0, z2), "minecraft:dark_oak_fence")
    for z in (z1 + 2, z2 - 1):
        for x in (XG - 3, XG + 3):
            L.set_block(V(x, 1, z), L.LANTERN)
    # chains hanging down the gatehouse front beside the arch, as if the bridge could be raised
    for x in (XG - 4, XG + 4):
        L.fill(V(x, 1, z1), V(x, 6, z1), L.CHAIN)
        L.set_block(
            V(x, 7, z1), "minecraft:dark_oak_trapdoor[facing=south,half=top,open=false]"
        )
    # a stair from the bank down (or up) to the ground, then the road to spawn
    foot, start = bridge_foot(), road_start()
    if start.z > foot.z + 1:  # the stair climbs or drops one block per block
        stairway(
            [foot, Vec3(start.x, start.y, start.z - 1)],
            L.BRICK_STAIRS,
            width=5,
            support=L.COBBLE,
            clearance=3,
        )
    points = road_points(start)
    road(points, "minecraft:dirt_path", width=3, border=L.COBBLE)
    lamp_posts(points)
    signpost(points)


def leg_of(a: Vec3, b: Vec3) -> tuple[Vec3, Vec3, int]:
    """the direction of a leg of the road, its right-hand side and its length"""
    dx, dz = int(b.x - a.x), int(b.z - a.z)
    d = Vec3((dx > 0) - (dx < 0), 0, (dz > 0) - (dz < 0))
    return d, Vec3(-d.z, 0, d.x), abs(dx) + abs(dz)


POST_HEIGHT = 2  # fence blocks under a lamp post's lantern
POST_EVERY = 12  # blocks between lamp posts


def lamp_post_cells(points: list[Vec3], every: int = POST_EVERY) -> list[Vec3]:
    """where the lamp posts stand: every ``every`` blocks along each leg,
    three blocks to the right of the way to spawn (y is 0)"""
    cells = []
    for a, b in zip(points, points[1:], strict=False):
        d, right, length = leg_of(a, b)
        for k in range(every // 2, length - 2, every):
            p = a + d * k + right * 3
            cells.append(Vec3(p.x, 0, p.z))
    return cells


def lamp_posts(points: list[Vec3]) -> None:
    """
    Lantern posts beside the road, except where another castle's road or
    post is already. A post that is there already is left alone: the
    heightmap counts fences and lanterns as ground, so building on top of
    it would stack another post on it.
    """
    for p in lamp_post_cells(points):
        top = ground_height(p.x, p.z)
        if L.is_block(Vec3(p.x, top, p.z), L.LANTERN):
            continue  # a post is there (ours from before, or another castle's)
        y = top + 1
        foot = Vec3(p.x, y, p.z)
        if L.is_block(Vec3(p.x, top, p.z), "minecraft:dirt_path") or not all(
            L.is_block(Vec3(p.x, yy, p.z), "#minecraft:replaceable")  # air or a plant
            for yy in range(y, y + POST_HEIGHT + 1)
        ):
            continue
        L.fill(foot, Vec3(p.x, y + POST_HEIGHT - 1, p.z), "minecraft:dark_oak_fence")
        L.set_block(Vec3(p.x, y + POST_HEIGHT, p.z), L.LANTERN)


def road_centre(points: list[Vec3]) -> list[tuple[int, int]]:
    """the (x, z) cells of the road's centre line: what verify checks"""
    cells = []
    for a, b in zip(points, points[1:], strict=False):
        d, _, length = leg_of(a, b)
        for k in range(length + 1):
            p = a + d * k
            cells.append((int(p.x), int(p.z)))
    return cells


def signpost_position(
    points: list[Vec3], taken: Callable[[Vec3], bool] | None = None
) -> tuple[Vec3, int]:
    """
    Where the castle's signpost stands, and its rotation: beside the end of
    the road's last leg, on the right, a few blocks back along the leg. How
    many differs per castle (from its ORIGIN), so that castles whose roads
    arrive by the same leg do not usually want the same spot; and given
    ``taken`` (is another castle's sign at this spot?) it steps further
    back until the spot is free, so they never collide. y is 0: the sign
    stands on the ground.
    """
    d, right, _ = leg_of(points[-2], points[-1])
    back = 2 + 2 * ((ORIGIN.x // 16 + ORIGIN.z // 16) % 5)
    # the sign faces the road, i.e. left: rotation 0 south, 4 west, 8 north, 12 east
    rotation = {(0, 1): 0, (-1, 0): 4, (0, -1): 8, (1, 0): 12}[(-right.x, -right.z)]
    for _ in range(20):
        p = points[-1] - d * back + right * 2
        p = Vec3(p.x, 0, p.z)
        if taken is None or not taken(p):
            return p, rotation
        back += 2
    raise BuildError("no free spot for the signpost within 40 blocks of spawn")


def other_sign_at(p: Vec3) -> bool:
    """is there a sign on the ground at (x, z) that is not this castle's?"""
    y = ground_height(p.x, p.z) + 1
    if not L.is_block(Vec3(p.x, y, p.z), "#minecraft:all_signs"):
        return False
    return NAME not in L.cmd(f"data get block {p.x} {y} {p.z} front_text.messages")


def compass(dx: int, dz: int) -> str:
    """the bearing of (dx, dz) as north, north-east ..."""
    ns = "north" if dz < 0 else "south"
    ew = "east" if dx > 0 else "west"
    if abs(dx) > 2 * abs(dz):
        return ew
    if abs(dz) > 2 * abs(dx):
        return ns
    return f"{ns}-{ew}"


def signpost(points: list[Vec3]) -> None:
    """a signpost at spawn beside the road's end, pointing the way"""
    p, rotation = signpost_position(points, other_sign_at)
    y = ground_height(p.x, p.z) + 1
    middle = centre()
    L.sign(
        Vec3(p.x, y, p.z),
        f"oak_sign[rotation={rotation}]",
        f"Castle {NAME}",
        "follow the road",
        compass(middle.x - SPAWN.x, middle.z - SPAWN.z),
    )


def upper_walls() -> None:
    y = YU
    L.curtain(V(0, y, 0), V(0, y, UD - 1), WALL_H, Wd)
    L.curtain(V(W - 1, y, 0), V(W - 1, y, UD - 1), WALL_H, E)
    L.curtain(V(0, y, 0), V(W - 1, y, 0), WALL_H, N)
    # the south wall on the cliff edge, in two parts round the middle gate
    L.curtain(V(0, y, UD - 1), V(XG - 10, y, UD - 1), WALL_H, S)
    L.curtain(V(XG + 10, y, UD - 1), V(W - 1, y, UD - 1), WALL_H, S)
    L.weather(
        wcells(
            L.rect(0, 0, 0, UD - 1)
            | L.rect(W - 1, 0, W - 1, UD - 1)
            | L.rect(0, 0, W - 1, 0)
        ),
        ORIGIN.y + y + 2,
        ORIGIN.y + y + WALL_H - 1,
    )
    walk = y + WALL_H
    # north corner towers with conical roofs, mid-wall towers with battlements
    for cx, doors, roof in (
        (3, [(walk, S, -1), (walk, E, 1), (y, S, 1)], L.DARK_TILES),
        (W - 4, [(walk, S, 1), (walk, Wd, 1), (y, S, -1)], L.DARK_TILES),
    ):
        L.round_tower(
            ORIGIN.x + cx,
            ORIGIN.z + 3,
            TR,
            ORIGIN.y + DITCH_FLOOR - 1,
            ORIGIN.y + walk + 12,
            floors=[ORIGIN.y + y, ORIGIN.y + walk, ORIGIN.y + walk + 6],
            doors=[(ORIGIN.y + dy, d, o) for dy, d, o in doors],
            roof=roof,
            banner=BANNER2,
        )
    for cx, doors in (
        (3, [(walk, N, -1), (walk, S, -1), (y, E, 0)]),
        (W - 4, [(walk, N, 1), (walk, S, 1), (y, Wd, 0)]),
    ):
        L.round_tower(
            ORIGIN.x + cx,
            ORIGIN.z + 32,
            TR - 1,
            ORIGIN.y + DITCH_FLOOR - 1,
            ORIGIN.y + walk + 6,
            floors=[ORIGIN.y + y, ORIGIN.y + walk],
            doors=[(ORIGIN.y + dy, d, o) for dy, d, o in doors],
        )
    # stairs up to the wall walks
    stairway(
        [V(3, y - 1, 12), V(3, walk - 1, 22)],
        L.BRICK_STAIRS,
        width=2,
        support=L.BRICK,
        clearance=3,
    )
    stairway(
        [V(W - 4, y - 1, 12), V(W - 4, walk - 1, 22)],
        L.BRICK_STAIRS,
        width=2,
        support=L.BRICK,
        clearance=3,
    )


def grand_stair() -> dict:
    """the stair from the bailey up to the middle gate, and the gate's portcullis"""
    z_bottom = UD + YU  # 18 blocks of rise over 18 blocks of run
    stairway(
        [V(XG, -1, z_bottom), V(XG, YU - 1, UD)],
        L.BRICK_STAIRS,
        width=7,
        support=L.BRICK,
        clearance=5,
    )
    # balustrades with lanterns, following the slope
    for k in range(0, YU + 1):
        z = z_bottom - k
        for x in (XG - 4, XG + 4):
            L.fill(
                V(x, -1, z), V(x, k - 1, z), L.BRICK
            )  # a parapet wall up to the stair's level
            L.set_block(V(x, k, z), L.BRICK_WALL)
            if k % 4 == 0:
                L.set_block(V(x, k + 1, z), L.LANTERN)
    # the middle gate's square towers either side of the stair head
    for x1 in (XG - 9, XG + 5):
        L.fill(V(x1, 0, UD - 6), V(x1 + 4, YU + WALL_H + 5, UD + 2), L.BRICK)
        L.fill(
            V(x1 + 1, YU + WALL_H + 6, UD - 5),
            V(x1 + 3, YU + WALL_H + 6, UD + 1),
            L.BRICK,
        )
        L.fill(
            V(x1, YU + WALL_H + 6, UD - 6), V(x1 + 4, YU + WALL_H + 6, UD + 2), L.BRICK
        )
        L.fill(
            V(x1 + 1, YU + WALL_H + 6, UD - 5),
            V(x1 + 3, YU + WALL_H + 6, UD + 1),
            L.AIR,
        )
        L.merlons(
            [
                (ORIGIN.x + x, ORIGIN.z + z)
                for x in range(x1, x1 + 5)
                for z in (UD - 6, UD + 2)
            ]
            + [
                (ORIGIN.x + x, ORIGIN.z + z)
                for z in range(UD - 5, UD + 2)
                for x in (x1, x1 + 4)
            ],
            ORIGIN.y + YU + WALL_H + 7,
        )
        L.set_block(
            V(x1 + 2, YU + WALL_H + 7, UD + 2),
            f"minecraft:{BANNER2}_wall_banner[facing=south]",
        )
    # the gate passage through the south wall and its portcullis
    L.fill(V(GATE_X1, YU, UD - 4), V(GATE_X2, YU + 1, UD), L.AIR)
    L.fill(V(GATE_X1, YU - 1, UD - 4), V(GATE_X2, YU - 1, UD), L.ANDESITE)
    L.fill(V(GATE_X1, YU + 2, UD - 1), V(GATE_X2, YU + 2, UD), L.BARS)
    L.fill(
        V(XG - 4, YU, UD - 1), V(XG + 4, YU + 5, UD), L.BRICK
    )  # a facade block over the passage
    arch(
        V(XG - 3, YU, UD),
        V(XG + 3, YU, UD),
        L.CHISELED,
        style="pointed",
        depth=1,
        clear=True,
    )
    L.fill(V(GATE_X1, YU, UD - 1), V(GATE_X2, YU + 1, UD), L.AIR)
    L.fill(
        V(XG - 4, YU + 1, UD + 1),
        V(XG + 4, YU + 1, UD + 1),
        f"{L.BRICK_STAIRS}[facing=north]",
    )
    L.fill(V(GATE_X1, YU + 1, UD + 1), V(GATE_X2, YU + 1, UD + 1), L.AIR)
    L.fill(V(GATE_X1, YU, UD + 1), V(GATE_X2, YU, UD + 1), L.AIR)
    g = L.portcullis(*portcullis_args(MIDDLE_GATE))
    # the winch room of this gate is reached through the WEST tower (the
    # wiring channel runs inside the east one): a door from the ward, a
    # lobby, a stair up four blocks and a passage east into the winch room
    L.fill(
        V(XG - 7, YU, UD - 6), V(XG - 7, YU + 1, UD - 6), L.AIR
    )  # door in the tower's north face
    L.fill(V(XG - 8, YU, UD - 5), V(XG - 6, YU + 2, UD + 1), L.AIR)  # the lobby
    stairway(
        [V(XG - 7, YU - 1, UD + 1), V(XG - 7, YU + 3, UD - 3)],
        L.BRICK_STAIRS,
        width=1,
        support=L.BRICK,
        clearance=3,
    )
    L.fill(
        V(XG - 7, YU + 4, UD - 5), V(XG - 7, YU + 5, UD - 2), L.AIR
    )  # landing at the top of the stair
    L.fill(
        V(XG - 6, YU + 4, UD - 2), V(XG - 2, YU + 5, UD - 2), L.AIR
    )  # east into the winch room
    L.set_block(V(XG - 8, YU + 2, UD - 2), f"{L.LANTERN}[hanging=false]")
    return g


def keep_shell() -> None:
    x1, z1, x2, z2 = KEEP
    y = YU
    top = KEEP_ROOF - 1  # the roof slab
    L.fill(V(x1, y - 1, z1), V(x2, top, z2), L.BRICK)
    L.fill(V(x1, y - 1, z1), V(x2, y + 1, z2), L.DARK_BRICK)
    # hollow: interior x1+3..x2-3, z1+3..z2-3, from y to top-1
    L.fill(V(x1 + 3, y, z1 + 3), V(x2 - 3, top - 1, z2 - 3), L.AIR)
    # string courses at each floor outside
    for fy in (y + 10, y + 19, KEEP_ROOF - 1):
        L.shell(
            V(x1 - 1, fy - 1, z1 - 1),
            V(x2 + 1, fy - 1, z2 + 1),
            f"{L.BRICK_STAIRS}[half=top,facing=north]",
        )
        L.fill(
            V(x1 - 1, fy - 1, z2 + 1),
            V(x2 + 1, fy - 1, z2 + 1),
            f"{L.BRICK_STAIRS}[half=top,facing=south]",
        )
        L.fill(
            V(x1 - 1, fy - 1, z1 - 1),
            V(x1 - 1, fy - 1, z2 + 1),
            f"{L.BRICK_STAIRS}[half=top,facing=west]",
        )
        L.fill(
            V(x2 + 1, fy - 1, z1 - 1),
            V(x2 + 1, fy - 1, z2 + 1),
            f"{L.BRICK_STAIRS}[half=top,facing=east]",
        )
    # the string courses are ledges a mob could spawn on in the dark: lanterns
    for fy in (y + 10, y + 19, KEEP_ROOF - 1):
        for x in range(x1 - 1, x2 + 2, 6):
            for z in (z1 - 1, z2 + 1):
                L.set_block(V(x, fy, z), f"{L.LANTERN}[hanging=false]")
        for z in range(z1 + 5, z2 - 4, 6):
            for x in (x1 - 1, x2 + 1):
                L.set_block(V(x, fy, z), f"{L.LANTERN}[hanging=false]")
    # parapet round the roof terrace
    L.shell(V(x1, KEEP_ROOF, z1), V(x2, KEEP_ROOF, z2), L.BRICK)
    L.merlons(
        [(ORIGIN.x + x, ORIGIN.z + z) for x in range(x1, x2 + 1) for z in (z1, z2)]
        + [(ORIGIN.x + x, ORIGIN.z + z) for z in range(z1 + 1, z2) for x in (x1, x2)],
        ORIGIN.y + KEEP_ROOF + 1,
    )
    # corner turrets with conical roofs, reached from the roof terrace and the ground
    for cx, cz, dirs in (
        (x1, z1, (E, S)),
        (x2, z1, (Wd, S)),
        (x1, z2, (E, N)),
        (x2, z2, (Wd, N)),
    ):
        doors = [
            (KEEP_ROOF, dirs[0], 0),
            (KEEP_ROOF, dirs[1], 0),
            (y, dirs[0], 0),
            (y, dirs[1], 0),
        ]
        L.round_tower(
            ORIGIN.x + cx,
            ORIGIN.z + cz,
            4,
            ORIGIN.y + y - 2,
            ORIGIN.y + KEEP_ROOF + 10,
            floors=[
                ORIGIN.y + y,
                ORIGIN.y + y + 10,
                ORIGIN.y + y + 19,
                ORIGIN.y + KEEP_ROOF,
            ],
            doors=[(ORIGIN.y + dy, d, o) for dy, d, o in doors],
            roof=L.DARK_TILES,
            banner=BANNER,
        )
    # windows: tall stained glass in pairs on every face, each storey
    for fy in (y + 2, y + 12, y + 21):
        for x in range(x1 + 6, x2 - 5, 6):
            for z in (z1, z2):
                L.fill(
                    V(x, fy, z),
                    V(x + 1, fy + 3, z + 2 if z == z1 else z - 2),
                    "minecraft:light_blue_stained_glass_pane",
                )
        for z in range(z1 + 6, z2 - 5, 6):
            for x in (x1, x2):
                L.fill(
                    V(x, fy, z),
                    V(x + 2 if x == x1 else x - 2, fy + 3, z + 1),
                    "minecraft:light_blue_stained_glass_pane",
                )
    # the great door on the south face, a pointed arch
    arch(
        V(XG - 3, y, z2),
        V(XG + 3, y, z2),
        L.CHISELED,
        style="pointed",
        depth=1,
        clear=True,
    )
    L.fill(V(XG - 2, y, z2 - 2), V(XG + 2, y + 3, z2), L.AIR)
    for x in range(XG - 2, XG + 3):
        L.set_block(
            V(x, y, z2),
            f"minecraft:dark_oak_door[facing=north,half=lower,hinge={'left' if x < XG else 'right'}]",
        )
        L.set_block(
            V(x, y + 1, z2),
            f"minecraft:dark_oak_door[facing=north,half=upper,hinge={'left' if x < XG else 'right'}]",
        )
    L.fill(V(XG - 2, y + 2, z2), V(XG + 2, y + 3, z2), L.BARS)
    # a central lantern tower on the roof
    L.round_tower(
        ORIGIN.x + XG,
        ORIGIN.z + (z1 + z2) // 2,
        3,
        ORIGIN.y + KEEP_ROOF - 1,
        ORIGIN.y + KEEP_ROOF + 8,
        floors=[ORIGIN.y + KEEP_ROOF],
        doors=[(ORIGIN.y + KEEP_ROOF, S, 0)],
        roof=L.DARK_TILES,
        banner=BANNER,
        stair=False,
    )
    # a path from the middle gate to the great door
    L.fill(V(XG - 1, y - 1, z2 + 1), V(XG + 1, y - 1, UD - 5), L.ANDESITE)
