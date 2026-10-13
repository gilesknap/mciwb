"""
Build each of the bailey's machines (machines_bailey.py) in a box in the
air, work it over RCON with the same checks verify_castle2 runs in the
castle, and clear the box again::

    RIG="630,150,-120" MACHINES=archery,clock,mill,listening mciwb run rig_bailey.py

RIG is the north-west bottom corner of a 69 x 33 x 61 box that must be
empty (it is cleared before and after). The machines are built one at a
time: each one's local coordinates are shifted into the box (``at``), with
a little ground under it (and, for the listening door, a mock oubliette).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle2_layout  # noqa: E402, F401, I001  (first: it sets up castle's layout)
import castle_lib as L  # noqa: E402
import machines_bailey as M  # noqa: E402

from mciwb.imports import Vec3, get_world  # noqa: E402

world = get_world()
SIZE = Vec3(69, 33, 61)
results: list[bool] = []


def corner() -> Vec3:
    x, y, z = (int(v) for v in os.environ.get("RIG", "630,150,-120").split(","))
    return Vec3(x, y, z)


def shift(local: Vec3, world_pos: Vec3) -> M.At:
    """the map that puts local cell ``local`` at ``world_pos``"""

    def at(x: int, y: int, z: int) -> Vec3:
        return Vec3(
            x + world_pos.x - local.x,
            y + world_pos.y - local.y,
            z + world_pos.z - local.z,
        )

    return at


def report(results_of) -> None:
    for name, ok in results_of:
        results.append(ok)
        print(("PASS " if ok else "FAIL ") + name)


def archery(r: Vec3) -> None:
    at = shift(Vec3(36, -2, 75), r + Vec3(10, 10, 10))
    L.fill(at(36, -2, 75), at(57, -2, 86), L.STONE)
    L.fill(at(36, -1, 75), at(57, -1, 86), "minecraft:grass_block")
    M.archery(at)
    report(M.check_archery(at))


def clock(r: Vec3) -> None:
    at = shift(Vec3(64, -3, 152), r + Vec3(10, 2, 10))
    L.fill(at(64, -3, 152), at(72, -1, 160), L.STONE)
    M.clock_tower(at)
    report(M.check_clock_tower(at))


def mill(r: Vec3) -> None:
    at = shift(Vec3(88, -11, 189), r + Vec3(10, 1, 10))
    L.fill(at(88, -11, 189), at(109, -2, 206), L.STONE)
    L.fill(at(88, -1, 189), at(109, -1, 206), "minecraft:grass_block")
    M.mill(at, tunnel_z=195)
    report(M.check_mill(at, tunnel_z=195))


def listening(r: Vec3) -> None:
    at = shift(Vec3(79, -17, 118), r + Vec3(10, 3, 10))
    L.fill(at(79, -17, 118), at(99, -11, 134), L.DARK_BRICK)
    L.fill(at(92, -15, 124), at(98, -13, 131), L.AIR)  # the oubliette
    L.fill(at(92, -16, 124), at(98, -16, 131), L.MOSSY_COBBLE)
    L.set_block(at(95, -13, 128), f"{L.SOUL_LANTERN}[hanging=true]")
    M.listening_door(at)
    report(M.check_listening_door(at))


def clear(a: Vec3, b: Vec3) -> None:
    box = L.box_selector(a, b)
    for kind in ("item_frame", "arrow", "item", "armor_stand"):
        world.cmd(f"kill @e[type=minecraft:{kind},{box}]")
    L.fill(a, b, L.AIR)


def main() -> None:
    a = corner()
    b = a + SIZE - Vec3(1, 1, 1)
    world.cmd(f"forceload add {a.x} {a.z} {b.x} {b.z}")
    try:
        for x, z in ((a.x, a.z), (b.x, b.z)):
            while "not loaded" in world.cmd(
                f"execute if block {x} 0 {z} minecraft:air"
            ):
                time.sleep(0.5)
        L.tick(20)
        for name in os.environ.get("MACHINES", "archery,clock,mill,listening").split(
            ","
        ):
            clear(a, b)
            print(f"-- {name}")
            {"archery": archery, "clock": clock, "mill": mill, "listening": listening}[
                name
            ](a)
            if os.environ.get("KEEP"):
                break
    finally:
        if not os.environ.get("KEEP"):
            clear(a, b)
        world.cmd(f"forceload remove {a.x} {a.z} {b.x} {b.z}")
    print(f"{sum(results)}/{len(results)} checks passed")
    if not all(results):
        raise SystemExit(1)


main()
