"""
The village stage: the lanes, the market square with its cross, and the
houses of `castle2_layout.HOUSES`, each built by `house.medieval_house`.
Runs after castle's bailey buildings (whose paths it meets) and before its
details (whose lantern posts keep out of the houses).
"""

from __future__ import annotations

import castle2_layout as C
import castle_lib as L
from castle2_layout import LANES, MARKET_CROSS, SQUARE, V
from house import House, medieval_house


def lanes_and_square() -> None:
    for x1, z1, x2, z2 in LANES.values():
        L.fill(V(x1, -1, z1), V(x2, -1, z2), "minecraft:dirt_path")
    # the square: cobbles with a border of polished andesite, the main street
    # through it left as castle laid it
    x1, z1, x2, z2 = SQUARE
    L.fill(V(x1, -1, z1), V(x2, -1, z2), "minecraft:polished_andesite")
    L.fill(V(x1 + 1, -1, z1 + 1), V(x2 - 1, -1, z2 - 1), "minecraft:cobblestone")
    for x in range(x1 + 2, x2 - 1, 4):
        for z in range(z1 + 2, z2 - 1, 4):
            L.set_block(V(x, -1, z), "minecraft:mossy_cobblestone")
    gx1, _gz1, gx2, _gz2 = C.PATHS["gate path south"]
    L.fill(V(gx1, -1, z1), V(gx2, -1, z2), "minecraft:dirt_path")
    L.fill(V(gx1 + 1, -1, z1), V(gx2 - 1, -1, z2), L.ANDESITE)


def market_cross() -> None:
    """a stone cross on steps"""
    x, z = MARKET_CROSS
    L.fill(V(x - 1, 0, z - 1), V(x + 1, 0, z + 1), L.BRICK)
    L.set_block(V(x, 1, z), L.CHISELED)
    L.fill(V(x, 2, z), V(x, 5, z), L.BRICK_WALL)
    L.set_block(V(x - 1, 4, z), L.BRICK_WALL)
    L.set_block(V(x + 1, 4, z), L.BRICK_WALL)
    L.set_block(V(x, 6, z), f"{L.LANTERN}[hanging=false]")


def houses() -> dict[str, House]:
    """build every house of `castle2_layout.HOUSES` with
    `house.medieval_house`; returns them by name"""
    built = {}
    for k, (name, x, z, width, depth, facing, opts) in enumerate(C.HOUSES):
        built[name] = medieval_house(
            V(x, 0, z), width, depth, facing=facing, seed=k, summon=L.summon, **opts
        )
    return built


# the village's lots: everything in this part of the bailey (x1, z1, x2,
# z2) but castle's buildings, paths and towers, the lanes and the square
LOTS = (4, 120, 116, 189)
TOP = 40  # above the highest chimney


def _box(x1: int, z1: int, x2: int, z2: int) -> set[tuple[int, int]]:
    return {(x, z) for x in range(x1, x2 + 1) for z in range(z1, z2 + 1)}


def lot_cells() -> set[tuple[int, int]]:
    from castle_layout import ROUND_TOWERS, footprints

    x1, z1, x2, z2 = LOTS
    cells = _box(x1, z1, x2, z2)
    for taken in footprints().values():
        cells -= taken
    for lane in LANES.values():
        cells -= _box(*lane)
    cells -= _box(*SQUARE)
    for cx, cz, r in ROUND_TOWERS.values():
        rr = (r + 1 + 0.5) ** 2
        cells = {(x, z) for x, z in cells if (x - cx) ** 2 + (z - cz) ** 2 > rr}
    return cells


def clear_lots() -> None:
    """clear the lots (houses move when the layout changes) back to grass"""
    o = V(0, 0, 0)
    cells = {(x + int(o.x), z + int(o.z)) for x, z in lot_cells()}
    L.fill_cells(cells, int(o.y), int(o.y) + TOP, L.AIR)
    L.fill_cells(cells, int(o.y) - 1, int(o.y) - 1, "minecraft:grass_block")


def relight() -> None:
    """castle's lantern posts on the lots (its 16-block grid), where they
    are in the open: clear_lots took them away"""
    import build_inner
    from castle_layout import UD, ZS, W

    cells = lot_cells()
    for x in range(8, W - 4, 16):
        for z in range(UD + 6, ZS - 4, 16):
            if (x, z) in cells:
                build_inner.post(x, 0, z)


def village() -> str:
    clear_lots()
    lanes_and_square()
    market_cross()
    built = houses()
    relight()
    return f"{len(built)} houses"
