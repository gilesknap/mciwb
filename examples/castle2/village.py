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
from house import place


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


def houses() -> dict:
    """build every house; returns them (`house.House`) by name"""
    built = C.village_houses()
    for h in built.values():
        place(h, L.summon)
    return built


def village() -> str:
    lanes_and_square()
    market_cross()
    built = houses()
    return f"{len(built)} houses"


def frames() -> int:
    """how many item frames the houses hang (castle_layout.SUMMONED)"""
    return sum(len(h.frames) for h in C.village_houses().values())
