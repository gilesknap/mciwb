"""
Test castle2's machines (machines_upper.py, organ.py) on their own, in the
air: each is built in a block of stone at RIG (its local coordinates moved
there), worked over RCON as verify_castle2 works it in the castle, and the
rig is cleared again (unless KEEP=1)::

    RIG=560,150,-118 WHICH=lectern,copper mciwb run machines_rig.py

WHICH picks machines (lectern, copper, astrolabe, engine, transmuter,
organ; default all). The box (RIG to RIG + 60, 32, 56) must be empty.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle2_layout  # noqa: E402, F401, I001  (first: castle's layout)
import castle_lib as L  # noqa: E402
import machines_upper as M  # noqa: E402
from build_outer import wait_loaded  # noqa: E402

from mciwb.imports import Vec3  # noqa: E402

results: list[bool] = []


def check(name: str, ok: bool) -> None:
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name, flush=True)


def corner() -> Vec3:
    x, y, z = (int(v) for v in os.environ.get("RIG", "560,150,-118").split(","))
    return Vec3(x, y, z)


# per machine: the local box (x1, y1, z1, x2, y2, z2) moved to the rig's corner
BOXES = {
    "lectern": (56, 27, 26, 63, 35, 41),
    "copper": (39, 6, 11, 51, 14, 34),
    "astrolabe": (12, 11, 17, 25, 43, 30),
    "transmuter": (17, 33, 18, 24, 39, 25),
    "organ": (70, 5, 3, 108, 26, 37),
}
BOXES["engine"] = BOXES["astrolabe"]


def mover(box: tuple):
    x1, y1, z1 = box[:3]
    c = corner()

    def pos(x: float, y: float, z: float) -> Vec3:
        return Vec3(int(c.x + x - x1), int(c.y + y - y1), int(c.z + z - z1))

    return pos


def surroundings(name: str, pos) -> None:
    """what the castle gives a machine: walls and floors round it"""
    stone = "minecraft:stone"
    if name == "lectern":
        L.fill(pos(57, 27, 26), pos(63, 27, 41), "minecraft:dark_oak_planks")
        L.fill(pos(58, 28, 26), pos(62, 35, 40), L.BRICK)
    elif name == "copper":
        L.fill(pos(49, 7, 12), pos(49, 12, 33), "minecraft:polished_blackstone_bricks")
        L.fill(pos(50, 7, 12), pos(51, 7, 33), "minecraft:deepslate_tiles")
    elif name in ("astrolabe", "engine"):
        L.fill(pos(14, 17, 18), pos(22, 17, 28), "minecraft:dark_oak_planks")
        if name == "engine":
            import build_inner
            from castle2_layout import ENGINE

            cx, cz, ey = ENGINE
            L.fill(
                pos(13, ey - 1, 17), pos(23, ey - 1, 27), "minecraft:dark_oak_planks"
            )
            saved = build_inner.V
            build_inner.V = pos
            try:
                build_inner.engine(cx, cz, ey)
            finally:
                build_inner.V = saved
            L.fill(pos(23, ey, 21), pos(24, ey + 2, 25), stone)
    elif name == "organ":
        L.fill(pos(86, 17, 15), pos(93, 17, 21), "minecraft:polished_andesite")
    elif name == "transmuter":
        L.fill(pos(17, 33, 18), pos(23, 33, 25), "minecraft:dark_oak_planks")
        L.fill(pos(23, 34, 18), pos(23, 39, 25), L.BRICK)


def build(name: str, pos) -> None:
    if name == "lectern":
        M.lectern_lock(pos)
    elif name == "copper":
        M.copper_puzzle(pos)
    elif name == "astrolabe":
        M.astrolabe(pos, cellar=False)
    elif name == "engine":
        M.astrolabe(pos, cellar=False)
        M.engine_purpose(pos)
    elif name == "transmuter":
        M.transmuter(pos)
    elif name == "organ":
        import organ

        organ.organ(pos)


def work(name: str, pos) -> None:
    if name == "organ":
        import organ

        organ.work_organ(check, pos)
    else:
        getattr(M, f"work_{name}")(check, pos)


def main() -> None:
    which = os.environ.get("WHICH", "lectern,copper,astrolabe,engine,transmuter,organ")
    for name in which.split(","):
        box = BOXES[name]
        pos = mover(box)
        a, b = pos(*box[:3]), pos(*box[3:])
        L.cmd(f"forceload add {a.x} {a.z} {b.x} {b.z}")
        try:
            wait_loaded([(int(a.x), int(a.z)), (int(b.x), int(b.z))], 4)
            L.fill(a, b, L.AIR)
            surroundings(name, pos)
            build(name, pos)
            L.tick(40)
            print(f"-- {name} at {a} .. {b}", flush=True)
            work(name, pos)
        finally:
            if not os.environ.get("KEEP"):
                L.fill(a, b, L.AIR)
                L.cmd(
                    f"kill @e[type=item,x={a.x},y={a.y},z={a.z},"
                    f"dx={b.x - a.x},dy={b.y - a.y},dz={b.z - a.z}]"
                )
            L.cmd(f"forceload remove {a.x} {a.z} {b.x} {b.z}")
    print(f"{sum(results)}/{len(results)} checks passed")


if __name__ == "__main__":
    main()
