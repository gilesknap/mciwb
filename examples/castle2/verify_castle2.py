"""
Verify Castle 2 over RCON, without a player::

    mciwb run verify_castle2.py

Runs all of castle's checks (``verify_castle.checks``, see castle's README)
on castle2's layout, then castle2's own:

- every seat (``castle_lib.seat``) faces the way its sitter looks, read back
  from the block's state, with its back to no table and something to look
  at in front: a table, an altar, a lectern, or open floor.

Refuses to run while a player is within 200 blocks of the site, unless
FORCE=1. Exits non-zero if any check fails.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle2_layout  # noqa: E402, F401, I001  (first: it sets up castle's layout)
import build_castle2  # noqa: E402, F401  (adds castle2's stages to castle's)
import build_castle  # noqa: E402
import build_outer  # noqa: E402
import castle_lib as L  # noqa: E402
import verify_castle as VC  # noqa: E402
from record_build import dry_run  # noqa: E402

from mciwb.imports import Vec3  # noqa: E402

check, is_block = VC.check, L.is_block
STEP = {
    "north": Vec3(0, 0, -1),
    "south": Vec3(0, 0, 1),
    "east": Vec3(1, 0, 0),
    "west": Vec3(-1, 0, 0),
}
# what a seat may look at: a table, an altar, a lectern or the steps of a dais
FOCUS = (
    "minecraft:dark_oak_slab[type=top]",
    "minecraft:chiseled_quartz_block",
    "minecraft:gold_block",
    "minecraft:lectern",
    "#minecraft:slabs[type=top]",
)
TABLES = ("#minecraft:slabs[type=top]",)


def seat_cells() -> list[tuple[Vec3, str]]:
    """every seat cell the build places and keeps (a later block may
    replace one, as the hall's aisle carpet does), and the way its sitter
    looks: learnt by running the build's stages against a fake client"""
    L.SEATS.clear()
    stages = [f for name, f in build_castle.STAGES.items() if name != "earthworks"]
    rec = dry_run(*stages, box=castle2_layout.site_box())
    cells = []
    for a, b, faces in L.SEATS:
        for x in range(min(a.x, b.x), max(a.x, b.x) + 1):
            for y in range(min(a.y, b.y), max(a.y, b.y) + 1):
                for z in range(min(a.z, b.z), max(a.z, b.z) + 1):
                    p = Vec3(x, y, z)
                    if "_stairs" in rec.world.at(p):
                        cells.append((p, faces))
    return cells


def seat_problem(p: Vec3, faces: str) -> str:
    """what is wrong with the seat at p, or empty"""
    back = L.OPPOSITE[faces]
    if not is_block(p, f"#minecraft:stairs[facing={back},half=bottom]"):
        return "not a stair with its back behind the sitter"
    d = STEP[faces]
    if any(is_block(p - d, t) for t in TABLES):
        return "its back to a table"
    if any(is_block(p + d, t) for t in FOCUS):
        return ""
    # a pew or a throne: something to look at further on, or open floor
    for k in range(1, 25):
        q = p + d * k
        if any(is_block(q, f) for f in FOCUS):
            return ""
        if not (
            is_block(q, L.AIR)
            or is_block(q, "#minecraft:stairs")
            or is_block(q, "#minecraft:wool_carpets")
        ):
            return "" if k > 4 else f"a wall {k} in front"
    return ""


def seats() -> None:
    cells = seat_cells()
    bad = [
        (p.x, p.y, p.z, faces, why)
        for p, faces in cells
        if (why := seat_problem(p, faces))
    ]
    check(
        f"seats: all {len(cells)} face their table, altar or hall"
        + (f" (not {bad[:4]})" if bad else ""),
        bool(cells) and not bad,
    )


def main() -> None:
    a, b = castle2_layout.site_box()
    near = L.players_near(a, b, 200)
    if near and not os.environ.get("FORCE"):
        raise SystemExit(
            f"{', '.join(near)} within 200 blocks of the site: not verifying"
        )
    build_outer.forceload(True)
    try:
        VC.checks()
        seats()
    finally:
        VC.c("kill @e[tag=castle_verify]")
        build_outer.forceload(False)
    print(f"{sum(VC.results)}/{len(VC.results)} checks passed")
    if not all(VC.results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
