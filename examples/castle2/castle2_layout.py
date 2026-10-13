"""
Castle 2: Castle Fable (``examples/castle``) with a lower bailey twice as
deep, filled with a village. Import this module before any of castle's: it
sets castle2's defaults in the environment (the bailey's depth, the site,
the name and the banner colour), puts ``examples/castle`` on the import
path, and then re-exports ``castle_layout``'s names, so that castle's
modules and castle2's see the same layout (the names castle2 uses are
imported explicitly below; any other castle_layout name is passed through
by ``__getattr__``)::

    import castle2_layout  # first
    import build_inner     # castle's, laid out for castle2

Local coordinates are castle's (see castle_layout): x east, y up from the
bailey's standing level, z south from the upper ward's north wall. With
BAILEY_DEPTH=162 the bailey is x 0..120, z 65..226 and the gate is at
z 218..226.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
CASTLE = HERE.parent / "castle"
for folder in (HERE, CASTLE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

# castle2's defaults: the site surveyed at x 550..700, z -200..70 (flat and
# dry, ground 62..72, higher in the north-west), a name and a banner colour
# no other castle in the world uses (Fable red, the one at 148,-262 purple,
# the one at -300,-40 yellow)
DEFAULTS = {
    "BAILEY_DEPTH": "162",
    "ORIGIN": "560,68,-190",
    "SPAWN": "32,74,-64",
    "NAME": "Fable II",
    "BANNER": "cyan",
}
for _key, _value in DEFAULTS.items():
    os.environ.setdefault(_key, _value)

_early = sys.modules.get("castle_layout")
if _early is not None and str(_early.LD) != os.environ["BAILEY_DEPTH"]:
    raise SystemExit("import castle2_layout before castle's modules")

import castle_layout  # noqa: E402
from castle_layout import (  # noqa: E402, F401  (re-exported for castle2's modules)
    ALCH,
    BANNER,
    BANNER2,
    BARRACKS,
    CELL_ROWS,
    CHAPEL,
    DUNGEON_Y,
    GATE_X1,
    GATE_X2,
    GATE_Z,
    GATEHOUSE,
    KEEP,
    KEEP_ROOF,
    LD,
    NAME,
    OPPOSITE,
    ORIGIN,
    PATHS,
    SEATS,
    SMITHY,
    SPAWN,
    STABLES,
    SUMMONED,
    TAG,
    TELEPORTS,
    TOWER_LEVELS,
    UD,
    VAULT_Y,
    WALL_H,
    WELL,
    WELL_GATE,
    YU,
    ZS,
    V,
    W,
    layout_problems,
    site_box,
)


def __getattr__(name: str):
    """any other name of castle_layout's"""
    try:
        return getattr(castle_layout, name)
    except AttributeError:
        raise AttributeError(f"module 'castle2_layout' has no {name!r}") from None


def castle2_problems() -> list[str]:
    """castle's layout check, plus castle2's own (houses, pens and lanes
    come in later phases)"""
    problems = layout_problems()
    if LD != 162:
        problems.append(f"castle2 is laid out for BAILEY_DEPTH=162, not {LD}")
        return problems
    return problems + village_problems()


# ---------------------------------------------------------------- the village
# (local coordinates; all at the bailey's standing level 0)

# the market square, paved, with the main street (castle's gate path, x
# 58..62) running through it
SQUARE = (44, 147, 76, 165)  # x1, z1, x2, z2
MARKET_CROSS = (52, 156)  # a stone cross on steps in the square's west half
CLOCK_TOWER = (68, 156)  # the square's east half: kept clear for the clock tower
# the lanes round the square, joining the main street (x1, z1, x2, z2)
LANES = {
    "north lane": (26, 131, 96, 133),
    "south lane": (26, 176, 96, 178),
    "west lane": (26, 131, 28, 178),
    "east lane": (94, 131, 96, 178),
}

# the houses: (name, corner x, corner z, width, depth, facing, options). The
# corner is the north-west corner of the ground floor; width runs along the
# street the house faces, depth back from it (see house.medieval_house).
# Each keeps its jetties and eaves off the lanes, the square and the
# streets (layout_problems checks it).
HOUSES: list[tuple[str, int, int, int, int, str, dict]] = [
    # north of the north lane, facing it
    ("baker", 30, 121, 8, 8, "south", {"contents": "baker"}),
    ("house n2", 40, 121, 8, 8, "south", {"frame": "square_panel"}),
    ("butcher", 50, 121, 7, 8, "south", {"contents": "butcher", "roof": "hip"}),
    ("tailor", 64, 121, 7, 8, "south", {"contents": "tailor"}),
    ("house n5", 73, 121, 8, 8, "south", {"frame": "braced", "jetty": 0}),
    (
        "candlemaker",
        83,
        121,
        8,
        8,
        "south",
        {"contents": "candlemaker", "roof": "gable_cross"},
    ),
    # between the north lane and the square, facing the square
    ("house c1", 30, 136, 8, 8, "south", {"window_boxes": True}),
    (
        "apothecary",
        40,
        136,
        8,
        8,
        "south",
        {"contents": "apothecary", "roof_block": "minecraft:deepslate_tile_stairs"},
    ),
    ("house c3", 50, 136, 7, 8, "south", {"floors": 3}),
    ("cartographer", 64, 136, 7, 8, "south", {"contents": "cartographer", "floors": 3}),
    (
        "house c5",
        73,
        136,
        8,
        8,
        "south",
        {"frame": "square_panel", "windows": "shuttered"},
    ),
    ("house c6", 83, 136, 8, 8, "south", {"roof": "hip", "window_boxes": True}),
    # the square's west and east sides, facing it
    (
        "tavern",
        31,
        148,
        8,
        9,
        "east",
        {"contents": "tavern", "floors": 3, "roof": "gable_cross"},
    ),
    ("house w2", 31, 158, 7, 9, "east", {"frame": "braced"}),
    ("cobbler", 81, 148, 8, 9, "west", {"contents": "cobbler"}),
    ("weaver", 81, 158, 7, 9, "west", {"contents": "weaver", "windows": "shuttered"}),
    # south of the square, facing it
    ("fletcher", 30, 168, 8, 6, "north", {"contents": "fletcher"}),
    ("house s2", 40, 168, 8, 6, "north", {"window_boxes": True, "ground": "timber"}),
    ("carpenter", 50, 168, 7, 6, "north", {"contents": "carpenter", "roof": "hip"}),
    ("house s4", 64, 168, 7, 6, "north", {"frame": "square_panel"}),
    ("house s5", 73, 168, 8, 6, "north", {"windows": "shuttered"}),
    ("house s6", 83, 168, 8, 6, "north", {"roof": "gable_cross"}),
    # south of the south lane, facing it
    ("house l1", 30, 181, 8, 7, "north", {"frame": "braced", "window_boxes": True}),
    ("house l2", 40, 182, 8, 7, "north", {"floors": 3}),
    ("house l3", 50, 181, 7, 7, "north", {"ground": "timber"}),
    ("house l4", 64, 181, 7, 7, "north", {"frame": "square_panel"}),
    ("house l5", 73, 181, 8, 7, "north", {"roof": "hip"}),
    ("house l6", 83, 181, 8, 7, "north", {"window_boxes": True}),
]


# ---- the south of the bailey: pens and paddocks along the walls, the
# kitchen garden and allotments, a frog pond (x1, z1, x2, z2: the fence
# ring), and what lives in each. The gates open north onto the pen lane.
PEN_LANE = (12, 190, 57, 191)  # from the pens to the main street
PENS = {
    "cow pen": ((12, 192, 27, 205), {"cow": 4, "cow calf": 1}),
    "sheep pen": ((30, 192, 43, 205), {"sheep": 5}),
    "pig pen": ((46, 192, 55, 205), {"pig": 3, "pig piglet": 1}),
    "chicken run": ((12, 208, 24, 216), {"chicken": 6}),
    "goat pen": ((27, 208, 41, 216), {"goat": 3, "goat kid": 1}),
    "rabbit hutch": ((44, 208, 55, 216), {"rabbit": 4}),
    "frog pond": ((90, 208, 106, 216), {"frog": 3}),
}
GARDEN = (66, 192, 88, 205)  # the allotments, with a scarecrow (the mill east of them)
# the water mill (machines_bailey.py): its plot (x1, z1, x2, z2), east of the
# allotments and north of the frog pond
MILL = (92, 192, 108, 205)
BEEHIVES = [(10, 37), (14, 37), (18, 37)]  # by the upper ward's garden (at YU)


def pen_animals() -> dict[str, int]:
    """every animal the pens hold, by entity type (young ones included)"""
    out: dict[str, int] = {}
    for _box, animals in PENS.values():
        for what, n in animals.items():
            kind = what.split()[0]
            out[kind] = out.get(kind, 0) + n
    return out


def village_houses(origin=None):
    """every house of the village, as `house.House` (its blocks not placed),
    at ``origin`` (default: the world position of local 0, 0, 0)"""
    from house import house_blocks

    from mciwb.imports import Vec3

    o = V(0, 0, 0) if origin is None else origin
    out = {}
    for k, (name, x, z, width, depth, facing, opts) in enumerate(HOUSES):
        out[name] = house_blocks(
            Vec3(o.x + x, o.y, o.z + z), width, depth, facing=facing, seed=k, **opts
        )
    return out


def _cells(x1: int, z1: int, x2: int, z2: int) -> set[tuple[int, int]]:
    return {(x, z) for x in range(x1, x2 + 1) for z in range(z1, z2 + 1)}


def village_footprints() -> dict[str, set[tuple[int, int]]]:
    """the (x, z) cells (local) of each house (eaves and jetties included),
    the square, the market cross and the clock tower's plot, and each lane"""
    from mciwb.imports import Vec3

    out = {
        f"house '{name}'": h.footprint
        for name, h in village_houses(Vec3(0, 0, 0)).items()
    }
    for name, (box, _animals) in PENS.items():
        out[name] = _cells(*box)
    out["the allotments"] = _cells(*GARDEN)
    out["the mill"] = _cells(*MILL)
    out["market cross"] = _cells(
        MARKET_CROSS[0] - 1,
        MARKET_CROSS[1] - 1,
        MARKET_CROSS[0] + 1,
        MARKET_CROSS[1] + 1,
    )
    out["clock tower"] = _cells(
        CLOCK_TOWER[0] - 2, CLOCK_TOWER[1] - 2, CLOCK_TOWER[0] + 2, CLOCK_TOWER[1] + 2
    )
    return out


def village_problems() -> list[str]:
    """the houses against the round towers (out to radius + 1), castle's
    buildings, stairs, paths and signs, the lanes, the square and each other"""
    from castle_layout import ROUND_TOWERS, footprints

    problems = []
    feet = village_footprints()
    houses = {
        n: c
        for n, c in feet.items()
        if n.startswith("house ") or n in PENS or n in ("the allotments", "the mill")
    }
    castle = footprints()
    open_ground = {
        **{n: _cells(*r) for n, r in LANES.items()},
        "the square": _cells(*SQUARE),
        "the pen lane": _cells(*PEN_LANE),
    }
    for name, cells in houses.items():
        for tname, (cx, cz, r) in ROUND_TOWERS.items():
            rr = (r + 1 + 0.5) ** 2
            if any((x - cx) ** 2 + (z - cz) ** 2 <= rr for x, z in cells):
                problems.append(f"{name} overlaps the {tname}")
        for other, ocells in {**castle, **open_ground}.items():
            hit = cells & ocells
            if hit:
                problems.append(f"{name} overlaps {other} at {sorted(hit)[:3]}")
        if not all(4 <= x <= 116 and UD + 1 <= z <= ZS - 4 for x, z in cells):
            problems.append(f"{name} is not inside the bailey")
    names = list(houses)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if houses[a] & houses[b]:
                problems.append(
                    f"{a} overlaps {b} at {sorted(houses[a] & houses[b])[:3]}"
                )
    for fixture in ("market cross", "clock tower"):
        if not feet[fixture] <= _cells(*SQUARE):
            problems.append(f"the {fixture} is not in the square")
        for name, cells in castle.items():
            if feet[fixture] & cells:
                problems.append(f"the {fixture} overlaps {name}")
    return problems


def _tavern_door() -> tuple[int, int, int]:
    from mciwb.imports import Vec3

    h = village_houses(Vec3(0, 0, 0))["tavern"]
    return (int(h.outside.x), 0, int(h.outside.z))


# castle2's places for visitors, added to castle's (castle's verify checks
# each lands on a floor with head room, and the guide lists them)
TELEPORTS.update(
    {
        "the market square, by the cross": (55, 0, 152),
        "the tavern's door": _tavern_door(),
        "the pens, on the pen lane": (34, 0, 190),
        "the allotments' gate": (70, 0, 191),
        "the mill's door": (98, 0, 191),
        "the clock tower's door": (65, 0, 156),
        "the archery range's shooting line": (37, 0, 80),
    }
)

# ---- phase 6: the secrets, the machines that open them and their clues.
# One entry per secret (castle's old ones included), in the order of the
# clue trail (each secret's clues lead on to the next):
#   "name": {
#       "machine": the machine that opens it ("lectern lock" ...), or castle's
#                  mechanism ("library bookshelf door" ...),
#       "where": (x, y, z) local: where the machine is worked (its trigger),
#       "opens": what it opens or gives,
#       "solution": how to work it (the guide's spoilers),
#       "clues": [(kind, (x, y, z) local, what it says or shows), ...]:
#                kind is "book", "sign", "frame", "map", "trade", "banner",
#                "path", "painting" ...; at least two per secret,
#   }
# verify checks every clue is in place and works every machine.
SECRETS: dict[str, dict] = {}

# ---- phase 6: the bailey's machines (machines_bailey.py), local coordinates
# the listening door: the lower cell of the sliding door in the oubliette's
# west wall (the hidden space and the ossuary are west of it); a bell before
# a carved face 5 blocks south of it, a sculk sensor tuned to bells behind
LISTENING_DOOR = (91, -15, 125)
# the archery range in the barracks yard: the target (on its post, facing
# west; its straw butt and the cache east of it) and the shooting line's x
ARCHERY_TARGET = (51, 1, 80)
ARCHERY_LINE = 38
# the mill: the house's north-west corner (11 x 9, door north), the water
# wheel's hub (in the race east of the house), and the secret door in the
# house's south wall (lower cell) with the tunnel at x 95 down to the
# dungeon's guard room (castle's, its south wall at z 140)
MILL_HOUSE = (93, 0, 193)
MILL_WHEEL = (107, 1, 197)
MILL_DOOR = (95, 0, 201)
MILL_TUNNEL = (95, -8, 140)  # x, standing level, the guard room wall's z
SECRETS.update(
    {
        "the ossuary": {
            "machine": "listening door",
            "where": (92, -15, 130),
            "opens": "a sliding door in the oubliette's west wall (91, -15, 125)"
            " onto a hidden ossuary (x 81..87, z 120..128) with the founder's"
            " reliquary (a chest)",
            "solution": "In the oubliette, ring the bell before the carved face"
            " in the west wall: a calibrated sculk sensor behind the face hears"
            " only bells (vibration frequency 11) and the wall beside it slides"
            " open. Ring it again to shut it; inside, the ossuary's own bell"
            " does the same. Footsteps, arrows, the pit's trapdoors, doors and"
            " chests opening do nothing.",
            "clues": [
                ("sign", (92, -13, 130), "The dead hear / only the bell"),
                (
                    "carving",
                    (91, -14, 130),
                    "a carved face (chiseled polished"
                    " blackstone) in the oubliette's west wall, a bell before it",
                ),
            ],
        },
        "the archery cache": {
            "machine": "archery lock",
            "where": ARCHERY_TARGET,
            "opens": "an iron hatch behind the target's straw butt (55, 0, 80)"
            " over a barrel: arrows, a bow and a note",
            "solution": "From the shooting line (x 38: bows and an arrow dropper"
            " with a button are there) hit the target's bullseye: only a"
            " bullseye gives 15, the comparator behind it passes nothing less,"
            " and a copper bulb latches the hatch open. Another bullseye shuts"
            " it.",
            "clues": [
                ("sign", (37, 0, 77), "Archery range / a true eye / opens the stores"),
            ],
        },
        "the miller's way": {
            "machine": "water wheel and mill",
            "where": (99, 1, 200),
            "opens": "the wall beside the mill's fireplace (95, 0, 201): a"
            " ladder down to a tunnel north to the dungeon's guard room"
            " (95, -8, 140)",
            "solution": "Pull the lever marked 'Sluice' on the mill's south"
            " wall (it does not stop the wheel): the stones beside the hearth"
            " slide aside. The lever on the far side (on the brick in the"
            " passage) opens it from within.",
            "clues": [
                ("sign", (100, 1, 200), "Sluice"),
                (
                    "mark",
                    (95, 2, 201),
                    "a mason's mark (chiseled stone bricks) over the stones that move",
                ),
            ],
        },
    }
)

BAILEY_DEPTH_NOTE = (
    f"Its lower bailey is {LD} blocks deep (BAILEY_DEPTH), with a village in it."
)
