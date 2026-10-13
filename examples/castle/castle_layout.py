"""
Where everything is. All positions are relative to ORIGIN, the north-west
corner of the castle's outer wall at the level of the lower bailey floor:
``V(x, y, z)`` gives the world position of local (x, y, z).

The castle has two wards on a hillside:

- the **upper ward** on the plateau, local z 0..UD-1, standing level YU,
  with the keep, chapel, alchemist's tower and the north towers;
- the **lower bailey** to the south, local z UD..UD+LD-1, standing level 0,
  with the gatehouse (facing south), stables, smithy, well and the dungeons
  under its east side;
- a retaining cliff between them with the Grand Stair and the Middle Gate.

Local axes: x east, y up, z south (as Minecraft). People stand at a level
y when the floor block is at y - 1.

The site and the castle's name are set by environment variables, so that
the same scripts build any number of castles::

    ORIGIN=-80,82,-230 SPAWN=32,74,-64 NAME=Fable BANNER=red mciwb run build_castle.py
"""

from __future__ import annotations

import os

from mcwb import Vec3


def _vec(name: str, default: Vec3) -> Vec3:
    """a Vec3 from the environment, as ``X,Y,Z``"""
    value = os.environ.get(name)
    if not value:
        return default
    try:
        x, y, z = (int(v) for v in value.replace(" ", "").split(","))
    except ValueError:
        raise SystemExit(f"{name} must be X,Y,Z, not {value!r}") from None
    return Vec3(x, y, z)


# ---- the one thing to change to move the castle: the NW corner of the
# outer wall, at the bailey's standing level (ground y + 1 of the lower site)
ORIGIN = _vec("ORIGIN", Vec3(-80, 82, -230))
# the world spawn point, where the road from the gate leads
SPAWN = _vec("SPAWN", Vec3(32, 74, -64))
# the castle's name, on the sign inside the gate and the signpost at spawn
NAME = os.environ.get("NAME") or "Fable"
# the colour of the castle's banners (the second colour is fixed)
COLOURS = (
    "white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
    "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black",
)  # fmt: skip
BANNER = os.environ.get("BANNER") or "red"
if BANNER not in COLOURS:
    raise SystemExit(f"BANNER must be a dye colour, not {BANNER!r}: {COLOURS}")
BANNER2 = "blue"
# every entity the castle summons carries this tag, unique to the site, so
# that a rebuild can remove the old ones (see castle_lib.summon)
TAG = f"castle_{ORIGIN.x}_{ORIGIN.z}"

W = 121  # width of both wards, x 0..W-1 (outer wall faces)
UD = 65  # upper ward depth: z 0..UD-1
LD = 81  # lower bailey depth: z UD..UD+LD-1
YU = 18  # the upper ward's standing level above the bailey's
WALL_H = 10  # curtain walls: solid blocks above the standing level
MOAT_W = 6  # the width of the water moat round the bailey and the dry ditch round the upper ward
MOAT_FLOOR = -6  # the bed of the moat (water from -5 to -2)
DITCH_FLOOR = YU - 7  # the floor of the dry ditch round the upper ward
TR = 6  # corner tower radius

# the bailey's south edge and the gate
ZS = UD + LD - 1  # south outer face of the bailey, z = 145
XG = W // 2  # the gate's centre line, x = 60
GATE_X1, GATE_X2 = XG - 1, XG + 1  # the passage is 3 wide
GATE_Z = ZS - 4  # the portcullis line, inside the gatehouse
GATEHOUSE = (XG - 14, ZS - 8, XG + 14, ZS)  # x1, z1, x2, z2 of the gatehouse block
BRIDGE_END = ZS + MOAT_W + 2  # the bridge's far end (the bank beyond the moat)

# the keep in the upper ward
KEEP = (40, 12, 80, 42)  # x1, z1, x2, z2 of its outer walls
KEEP_FLOORS = (YU, YU + 10, YU + 19)  # standing levels of the three storeys
KEEP_ROOF = YU + 28  # the roof terrace's standing level
KEEP_TOP = KEEP_ROOF + 2  # top of the parapet
HIGHEST = KEEP_ROOF + 16  # the lightning rod on the keep's lantern tower
LOWEST = -16  # the floor of the catacombs' lining

# the site to clear and forceload (local), with margins for moat, bridge and road
SITE_X1, SITE_X2 = -MOAT_W - 4, W + MOAT_W + 3
SITE_Z1, SITE_Z2 = -MOAT_W - 4, UD + LD + MOAT_W + 4
SITE_TOP = YU + 75
SITE_BOTTOM = -20

# ---- the mechanisms (local): the build places them here and
# verify_castle.py exercises them here. castle_lib has the geometry of each.
# portcullises: x1, x2, z, standing level, and which side of the bars the
# lever is on, in the passage (-1 north, +1 south): the main gate's on the
# bailey's side; the middle gate's in the passage through its facade, the
# only walled part (north of the bars is the open ward)
MAIN_GATE = (GATE_X1, GATE_X2, GATE_Z, 0, -1)
MIDDLE_GATE = (GATE_X1, GATE_X2, UD - 2, YU, 1)
# hidden doors: the lower door cell, the direction into the hidden space,
# the direction along the wall, the trigger and the lever's offset
LIBRARY_DOOR = (58, YU + 10, 16)  # base; u east, v south, bookshelf trigger
LIBRARY_LADDER = (60, 16)  # the shaft from its hidden space down to the vault
CRYPT_DOOR = (71, 8, 23)  # base; u west, v south, lever at -1
CELL_DOOR = (69, -8, 137)  # base; u west, v south, lever at CELL_LEVER
# the cell door's lever: in the middle of the first north cell's west wall,
# clear of that cell's grille (a lever beside an iron trapdoor powers it)
CELL_LEVER = -4
# the pit trap: corridor x, standing level, the wire's z (the trapdoors are
# under it and either side), depth
PIT_TRAP = (95, -8, 127, 7)
ARROW_TRAP = (94, 96, -15, 118, 108)  # x1, x2, standing level, wire z, dispenser z
WELL = (60, 105)
# ---- the lower bailey's buildings and features, x1, z1, x2, z2 (local).
# Each keeps clear of the bailey's round towers (BAILEY_TOWERS), with room
# for a tower's ground door: `layout_problems` checks it before a build.
MID_Z = 105  # the z of the mid-wall towers
# the stables (the stall fronts face east at x2), east of the west mid-wall
# tower and the lane at x 9 that its ground door opens onto
STABLES = (10, 92, 21, 122)
# the barracks (door east), clear of the west junction tower
BARRACKS = (10, 70, 23, 88)
# the smithy (door west), west of the east mid-wall tower and the lane at
# x 110..111 that its ground door opens onto; its gable roof overhangs by 1
SMITHY = (99, 95, 109, 115)
# the smithy's secret trapdoor (x, z), in its floor over the ladder down to
# the lower treasury (catacombs() carries the ladder through its ceiling)
SMITHY_HATCH = (107, 105)
DUNGEON_HUT = (93, 108, 97, 112)  # the dungeon entrance over its stair
MARKET = (70, 130, 82, 132)  # two stalls by the gate
# the stairs up to the wall walks: (points, width, walk), the points and
# width as for mciwb.builders.stairway (the walkway blocks; each row widens
# to the right of the way up), and the walk's standing level, which the
# last point reaches (its walkway block is one below). Each climbs beside a
# curtain with one row on the curtain's inner edge, so that the block after
# the top step along that row is the walk. West and east of the bailey:
# south beside the curtains, south of the mid-wall towers. Beside the
# gatehouse: along the south curtain, ending before the gatehouse's drum
# towers. In the upper ward: south beside the curtains, north of the
# mid-wall towers
WALL_STAIRS = {
    "west wall stair": ([(3, -1, 112), (3, WALL_H - 1, 122)], 2, WALL_H),
    "east wall stair": ([(W - 3, -1, 112), (W - 3, WALL_H - 1, 122)], 2, WALL_H),
    "stair west of the gatehouse": (
        [(GATEHOUSE[0] - 18, -1, ZS - 3), (GATEHOUSE[0] - 8, WALL_H - 1, ZS - 3)],
        2,
        WALL_H,
    ),
    "stair east of the gatehouse": (
        [(GATEHOUSE[2] + 18, -1, ZS - 2), (GATEHOUSE[2] + 8, WALL_H - 1, ZS - 2)],
        2,
        WALL_H,
    ),
    "upper west wall stair": (
        [(3, YU - 1, 12), (3, YU + WALL_H - 1, 22)],
        2,
        YU + WALL_H,
    ),
    "upper east wall stair": (
        [(W - 3, YU - 1, 12), (W - 3, YU + WALL_H - 1, 22)],
        2,
        YU + WALL_H,
    ),
}
# the courtyard paths (x1, z1, x2, z2): gate to grand stair, and across
# from the stables to the smithy's door. The well stands where they cross,
# and each stops at its rim
PATHS = {
    "gate path north": (XG - 2, UD + YU + 1, XG + 2, WELL[1] - 2),
    "gate path south": (XG - 2, WELL[1] + 2, XG + 2, ZS - 9),
    "cross path west": (STABLES[2] + 1, MID_Z - 1, WELL[0] - 2, MID_Z + 1),
    "cross path east": (WELL[0] + 2, MID_Z - 1, SMITHY[0] - 1, MID_Z + 1),
}
# the standing signs (x, y, z, rotation; standing positions on the ground)
STANDING_SIGNS = {
    "Stables": (STABLES[2] + 1, 0, MID_Z + 2, 4),
    "Barracks": (BARRACKS[2] + 1, 0, 77, 4),
    "The Smithy": (SMITHY[0] - 1, 0, MID_Z - 2, 12),
    "Welcome to": (XG + 4, 0, ZS - 10, 0),
    "The Keep": (XG + 5, YU, UD - 8, 0),
}
# the bailey's round towers: centre x, z, radius (build_outer.bailey_walls)
BAILEY_TOWERS = {
    "south-west corner tower": (3, ZS - 3, TR),
    "south-east corner tower": (W - 4, ZS - 3, TR),
    "west mid-wall tower": (3, MID_Z, TR - 1),
    "east mid-wall tower": (W - 4, MID_Z, TR - 1),
    "west junction tower": (3, UD - 1, TR),
    "east junction tower": (W - 4, UD - 1, TR),
}
# the gatehouse's drum towers, on its outer corners (build_outer.gatehouse)
GATE_TOWERS = {
    "west drum tower": (GATEHOUSE[0] - 2, ZS - 3, 4),
    "east drum tower": (GATEHOUSE[2] + 2, ZS - 3, 4),
}
# the upper ward's wall towers (build_outer.upper_walls)
UPPER_MID_Z = 32
UPPER_TOWERS = {
    "north-west corner tower": (3, 3, TR),
    "north-east corner tower": (W - 4, 3, TR),
    "upper west mid-wall tower": (3, UPPER_MID_Z, TR - 1),
    "upper east mid-wall tower": (W - 4, UPPER_MID_Z, TR - 1),
}
DUNGEON_Y = -8  # the dungeon's standing level
# the two rows of cells: interior z, the z of the cell front (grille, door
# and its frame), +1 if the corridor is south of the front, -1 if north, and the
# west x of each cell (3 wide). The south row starts a cell further east:
# the hidden door's pilaster at the corridor's west end takes that space
CELL_ROWS = ((132, 135, 1, range(70, 87, 4)), (140, 139, -1, range(74, 87, 4)))
GATE_BANNER_DX = 6  # the gate's banners hang this far either side of the arch
WELL_TUNNEL_X = (
    65  # the tunnel from the well: south to the dungeons, north to the vault
)
ENGINE = (18, 22, YU + 24)  # the alchemist's engine: centre x, z and its floor level
ALCH = (18, 22)  # the alchemist's tower's centre
CHAPEL = (86, 14, 110, 40)
VAULT = (50, 16, 70, 30)
VAULT_Y = 8

# what each stage summons, by entity type: the build checks they are all
# there before it finishes (an entity summoned into a chunk whose entities
# have not finished loading can be lost) and verify counts them
SUMMONED = {
    "interiors": {"armor_stand": 4, "item_frame": 12},
    "vault": {"armor_stand": 2, "item_frame": 6},
    "alchemist": {"item_frame": 6},
    "bailey_buildings": {"horse": 6, "armor_stand": 2},
    "details": {"armor_stand": 4, "iron_golem": 1, "cat": 1},
}

# the round towers' doorways: centre x, z, radius, wall thickness and the
# doors as (standing level, direction, offset), as castle_lib.round_tower
# takes them: a 2-high opening from the tower's floor out through its wall,
# shifted sideways by offset to the right of the direction (east of a door
# facing north, west of one facing south) to meet a wall walk. The curtains'
# walks are their two inner rows (x 1..2 and W-3..W-2, z 1..2, and the
# south curtains' z ZS-2..ZS-1 and UD-3..UD-2), and the ground doors keep
# off the curtains. Every door opens onto something to stand on at its
# level on both sides: a floor inside, and outside the walk, the ward or
# the keep's roof (reach.door_problems checks it). The mid-wall towers'
# walls are one thick, so that there is a floor between their spiral stair
# and the wall for the walk's doors to open onto
_N, _S, _E, _W = Vec3(0, 0, -1), Vec3(0, 0, 1), Vec3(1, 0, 0), Vec3(-1, 0, 0)
_WALK, _UWALK = WALL_H, YU + WALL_H
TOWER_DOORS = {
    "south-west corner tower": (
        *BAILEY_TOWERS["south-west corner tower"],
        2,
        [(_WALK, _N, -1), (_WALK, _E, 1), (0, _N, 1)],
    ),
    "south-east corner tower": (
        *BAILEY_TOWERS["south-east corner tower"],
        2,
        [(_WALK, _N, 1), (_WALK, _W, -1), (0, _N, -1)],
    ),
    "west mid-wall tower": (
        *BAILEY_TOWERS["west mid-wall tower"],
        1,
        [(_WALK, _N, -1), (_WALK, _S, 1), (0, _E, 0)],
    ),
    "east mid-wall tower": (
        *BAILEY_TOWERS["east mid-wall tower"],
        1,
        [(_WALK, _N, 1), (_WALK, _S, -1), (0, _W, 0)],
    ),
    # the junction towers: the bailey's walk, the bailey, the upper ward and
    # its west (east) and south walks
    "west junction tower": (
        *BAILEY_TOWERS["west junction tower"],
        2,
        [
            (_WALK, _S, 1),
            (0, _S, -1),
            (YU, _N, 1),
            (_UWALK, _N, -1),
            (_UWALK, _E, -1),
        ],
    ),
    "east junction tower": (
        *BAILEY_TOWERS["east junction tower"],
        2,
        [
            (_WALK, _S, -1),
            (0, _S, 1),
            (YU, _N, -1),
            (_UWALK, _N, 1),
            (_UWALK, _W, 1),
        ],
    ),
    "west drum tower": (*GATE_TOWERS["west drum tower"], 2, [(0, _N, 0), (16, _E, 0)]),
    "east drum tower": (*GATE_TOWERS["east drum tower"], 2, [(0, _N, 0), (16, _W, 0)]),
    "north-west corner tower": (
        *UPPER_TOWERS["north-west corner tower"],
        2,
        [(_UWALK, _S, 1), (_UWALK, _E, -1), (YU, _S, -1)],
    ),
    "north-east corner tower": (
        *UPPER_TOWERS["north-east corner tower"],
        2,
        [(_UWALK, _S, -1), (_UWALK, _W, 1), (YU, _S, 1)],
    ),
    "upper west mid-wall tower": (
        *UPPER_TOWERS["upper west mid-wall tower"],
        1,
        [(_UWALK, _N, -1), (_UWALK, _S, 1), (YU, _E, 0)],
    ),
    "upper east mid-wall tower": (
        *UPPER_TOWERS["upper east mid-wall tower"],
        1,
        [(_UWALK, _N, 1), (_UWALK, _S, -1), (YU, _W, 0)],
    ),
    # the keep's turrets: from the roof terrace, one row in from the parapet
    # on either side, and from the ward, away from the keep (not north: the
    # ladder is on the north wall inside)
    "keep turret 40,12": (
        KEEP[0], KEEP[1], 4, 2, [(KEEP_ROOF, _E, 1), (KEEP_ROOF, _S, -1), (YU, _W, 0)]
    ),
    "keep turret 80,12": (
        KEEP[2], KEEP[1], 4, 2, [(KEEP_ROOF, _W, -1), (KEEP_ROOF, _S, 1), (YU, _E, 0)]
    ),
    "keep turret 40,42": (
        KEEP[0], KEEP[3], 4, 2, [(KEEP_ROOF, _E, -1), (KEEP_ROOF, _N, 1), (YU, _S, 0)]
    ),
    "keep turret 80,42": (
        KEEP[2], KEEP[3], 4, 2, [(KEEP_ROOF, _W, 1), (KEEP_ROOF, _N, -1), (YU, _S, 0)]
    ),
    "keep's lantern tower": (
        XG, (KEEP[1] + KEEP[3]) // 2, 3, 2, [(KEEP_ROOF, _S, 0)]
    ),
    "alchemist's tower": (*ALCH, 6, 2, [(YU, _S, 0)]),
}  # fmt: skip

# every round tower standing on a ward's ground, for `layout_problems`
ROUND_TOWERS = {
    **BAILEY_TOWERS,
    **GATE_TOWERS,
    **UPPER_TOWERS,
    "alchemist's tower": (ALCH[0], ALCH[1], 6),
    **{
        f"keep turret {x},{z}": (x, z, 4)
        for x in (KEEP[0], KEEP[2])
        for z in (KEEP[1], KEEP[3])
    },
}

# the roofed towers (centre x, z, radius, standing level of the top floor):
# each flies a banner beside the top of its cone (castle_lib.cone_banner)
ROOFED_TOWERS = [
    (3, 3, TR, YU + WALL_H + 12),
    (W - 4, 3, TR, YU + WALL_H + 12),
    (KEEP[0], KEEP[1], 4, KEEP_ROOF + 10),
    (KEEP[2], KEEP[1], 4, KEEP_ROOF + 10),
    (KEEP[0], KEEP[3], 4, KEEP_ROOF + 10),
    (KEEP[2], KEEP[3], 4, KEEP_ROOF + 10),
    (XG, (KEEP[1] + KEEP[3]) // 2, 3, KEEP_ROOF + 8),
    (ALCH[0], ALCH[1], 6, YU + 31),
]

# where visitors are teleported to (local, standing positions); verify checks
# that each has free feet and head on a solid floor
TELEPORTS = {
    "outside the main gate, on the bridge": (XG, 0, ZS + 4),
    "in the lower bailey, looking at the grand stair": (XG, 0, ZS - 35),
    "on the upper ward in front of the keep": (XG, YU, KEEP[3] + 3),
    "keep roof terrace": (XG, KEEP_ROOF, KEEP[3] - 7),
    "dungeon entrance hut (bailey, east side)": (95, 0, DUNGEON_HUT[1] - 1),
    "the vault": (56, VAULT_Y, 23),
    "the lower treasury": (105, -15, 108),
}


def V(x: float, y: float, z: float) -> Vec3:
    """world position of a local position"""
    return Vec3(ORIGIN.x + int(x), ORIGIN.y + int(y), ORIGIN.z + int(z))


def world_xz(x: int, z: int) -> tuple[int, int]:
    return ORIGIN.x + x, ORIGIN.z + z


def site_box() -> tuple[Vec3, Vec3]:
    """the world box the castle is built in, moat, ditch and bridge included"""
    return V(SITE_X1, SITE_BOTTOM, SITE_Z1), V(SITE_X2, SITE_TOP, SITE_Z2)


def centre() -> Vec3:
    """the middle of the castle, at bailey level"""
    return V(W // 2, 0, (UD + LD) // 2)


def built_box() -> tuple[Vec3, Vec3]:
    """the world box of what is built: the castle's extents"""
    return V(SITE_X1 + 2, LOWEST, SITE_Z1 + 2), V(SITE_X2 - 2, HIGHEST, SITE_Z2 - 2)


def _cells(x1: int, z1: int, x2: int, z2: int) -> set[tuple[int, int]]:
    return {(x, z) for x in range(x1, x2 + 1) for z in range(z1, z2 + 1)}


def stair_cells(points: list[tuple[int, int, int]], width: int) -> set[tuple[int, int]]:
    """the (x, z) cells of a straight-sectioned stairway, as `stairway` lays
    it: each section's row widens to the right of its direction"""
    offsets = range(-((width - 1) // 2), width // 2 + 1)
    cells = set()
    for (ax, _, az), (bx, _, bz) in zip(points, points[1:], strict=False):
        dx, dz = (bx > ax) - (bx < ax), (bz > az) - (bz < az)
        rx, rz = -dz, dx  # to the right
        for k in range(max(abs(bx - ax), abs(bz - az)) + 1):
            for o in offsets:
                cells.add((ax + dx * k + rx * o, az + dz * k + rz * o))
    return cells


def footprints() -> dict[str, set[tuple[int, int]]]:
    """the (x, z) cells of each bailey building (roof overhangs included),
    stair, path and sign"""
    out = {
        "stables": _cells(*STABLES),
        "barracks": _cells(
            BARRACKS[0] - 1, BARRACKS[1] - 1, BARRACKS[2] + 1, BARRACKS[3] + 1
        ),
        "smithy": _cells(SMITHY[0] - 1, SMITHY[1] - 1, SMITHY[2] + 1, SMITHY[3] + 1),
        "dungeon hut": _cells(*DUNGEON_HUT),
        "market": _cells(*MARKET),
        "well": _cells(WELL[0] - 1, WELL[1] - 1, WELL[0] + 1, WELL[1] + 1),  # its rim
    }
    for name, (points, width, _walk) in WALL_STAIRS.items():
        out[name] = stair_cells(points, width)
    for name, rect in PATHS.items():
        out[name] = _cells(*rect)
    for name, (x, _, z, _r) in STANDING_SIGNS.items():
        out[f"sign {name}"] = {(x, z)}
    return out


def layout_problems() -> list[str]:
    """
    What in the lower bailey's layout overlaps what it must not: any
    footprint (`footprints`) inside a round tower's disc (`ROUND_TOWERS`)
    out to radius + 1 (its plinth, so its walls and ground door stay clear),
    any two buildings or stairs on each other, a path running into one, and
    a wall stair whose top is not at its walk's level. Pure arithmetic on the constants
    above: build_castle.py refuses to build if this finds anything.
    """
    feet = footprints()
    problems = []
    for name, (points, _width, walk) in WALL_STAIRS.items():
        if points[-1][1] != walk - 1:
            problems.append(
                f"{name} ends at {points[-1][1] + 1}, not the walk at {walk}"
            )
    for tname, (cx, cz, r) in ROUND_TOWERS.items():
        rr = (r + 1 + 0.5) ** 2  # as castle_lib.disc
        for fname, cells in feet.items():
            hit = sorted(c for c in cells if (c[0] - cx) ** 2 + (c[1] - cz) ** 2 <= rr)
            if hit:
                problems.append(f"{fname} overlaps the {tname} at {hit[:3]}")
    solid = [n for n in feet if n not in PATHS and not n.startswith("sign ")]
    for i, a in enumerate(solid):
        for b in solid[i + 1 :]:
            if feet[a] & feet[b]:
                problems.append(f"{a} overlaps {b} at {sorted(feet[a] & feet[b])[:3]}")
    # a path may pass under a roof's overhang, not into a building's walls
    ground = {
        "stables": _cells(*STABLES),
        "barracks": _cells(*BARRACKS),
        "smithy": _cells(*SMITHY),
        **{n: feet[n] for n in solid if n not in ("stables", "barracks", "smithy")},
    }
    for a in PATHS:
        for b, cells in ground.items():
            if feet[a] & cells:
                problems.append(f"{a} runs into {b} at {sorted(feet[a] & cells)[:3]}")
    return problems
