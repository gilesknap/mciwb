"""
Exercise each redstone module of castle_lib in a block of stone in the air,
toggle it and read the result back. Run before trusting a module in the
castle::

    mciwb run test_modules.py              # the rig at RIG, default 0,160,-40
    RIG=200,150,100 mciwb run test_modules.py

RIG is the north-west bottom corner of the rig, a 70 x 22 x 30 block of
stone. The rig's box must be empty (all air): the test refuses to run
otherwise, and it always clears the rig again, whatever happens.

The server pauses when no player is online, so ticks are advanced with
``tick sprint``. A lever toggled with ``setblock`` only updates its own
neighbours, so every lever has a dust block beside it.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle_layout  # noqa: E402
import castle_lib as L  # noqa: E402
from build_outer import wait_loaded  # noqa: E402

from mciwb.builders import ground_heights  # noqa: E402
from mciwb.imports import Heightmap, Vec3, get_world  # noqa: E402

world = get_world()
SIZE = Vec3(70, 22, 30)
results: list[bool] = []


def rig_corner() -> Vec3:
    value = os.environ.get("RIG", "0,160,-40")
    try:
        x, y, z = (int(v) for v in value.replace(" ", "").split(","))
    except ValueError:
        raise SystemExit(f"RIG must be X,Y,Z, not {value!r}") from None
    return Vec3(x, y, z)


def c(command: str) -> str:
    return world.cmd(command)


is_block = L.is_block


def arrows_in(dispensers: list[Vec3]) -> list[int]:
    """how many arrows each dispenser holds"""
    counts = []
    for p in dispensers:
        items = c(f"data get block {p.x} {p.y} {p.z} Items")
        counts.append(sum(int(n) for n in re.findall(r"count: (\d+)", items)))
    return counts


def advance(ticks: int = 40) -> None:
    L.tick(ticks)
    time.sleep(0.5)


def check(name: str, ok: bool) -> None:
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name)


def is_empty(b: Vec3, e: Vec3) -> bool:
    """is the box all air? (the highest block of every column is below it)"""
    columns = [(x, z) for x in range(b.x, e.x + 1) for z in range(b.z, e.z + 1)]
    tops = ground_heights(columns, Heightmap.WORLD_SURFACE)
    return all(top < b.y for top in tops.values())


def test_layout() -> None:
    """no bailey building, stair, path or sign overlaps a tower or another
    building; and the check finds the overlaps it is there to catch (the
    stables, wall stairs and smithy of earlier rounds cut the mid-wall towers,
    and the stairs beside the gatehouse ran into its drum towers)"""
    problems = castle_layout.layout_problems()
    check(f"layout: nothing overlaps {problems[:3]}", not problems)
    saved = castle_layout.STABLES, castle_layout.SMITHY, dict(castle_layout.WALL_STAIRS)
    try:
        castle_layout.STABLES = (3, 92, 15, 122)
        castle_layout.SMITHY = (104, 95, 117, 115)
        stairs = castle_layout.WALL_STAIRS
        stairs["west wall stair"] = ([(3, -1, 100), (3, 9, 110)], 2, 10)
        zs = castle_layout.ZS - 3
        stairs["stair west of the gatehouse"] = ([(32, -1, zs), (42, 9, zs)], 2, 10)
        stairs["stair east of the gatehouse"] = ([(88, -1, zs), (78, 9, zs)], 2, 10)
        found = "\n".join(castle_layout.layout_problems())
        check(
            "layout: the check finds the old stables, smithy and stairs in the towers",
            all(
                f"{what} overlaps the {tower}" in found
                for what, tower in (
                    ("stables", "west mid-wall tower"),
                    ("smithy", "east mid-wall tower"),
                    ("west wall stair", "west mid-wall tower"),
                    ("stair west of the gatehouse", "west drum tower"),
                    ("stair east of the gatehouse", "east drum tower"),
                )
            ),
        )
    finally:
        castle_layout.STABLES, castle_layout.SMITHY = saved[0], saved[1]
        castle_layout.WALL_STAIRS.clear()
        castle_layout.WALL_STAIRS.update(saved[2])


def pull(g: dict, on: bool) -> None:
    """a portcullis's lever, set by command: then its wall block is changed
    (to stone and back) to give the torch on it the update a player's pull
    gives (a lever set by command updates only its own neighbours)"""
    L.lever(g["lever"], g["lever_facing"], "wall", powered=on)
    b = g["lever_block"]
    c(f"setblock {b.x} {b.y} {b.z} {L.STONE}")
    c(f"setblock {b.x} {b.y} {b.z} {L.BRICK}")


def test_portcullis(x: int, y0: int, z: int) -> None:
    """passage x..x+2 through z, floor at y0-1"""
    L.fill(Vec3(x, y0, z - 14), Vec3(x + 2, y0 + 1, z + 14), L.AIR)
    g = L.portcullis(x, x + 2, z, y0)
    advance()
    check("portcullis starts open", all(is_block(p, L.AIR) for p in g["closed_cells"]))
    check(
        "its lever is in the passage, beside the bars",
        is_block(g["lever"], "minecraft:lever")
        and g["lever"] + Vec3(0, 0, 1) in g["closed_cells"],
    )
    pistons = g["ceiling_pistons"] + g["floor_pistons"]
    pull(g, True)
    advance()
    check(
        "portcullis closes (6 pistons extended, 6 cells barred)",
        all(is_block(p, "minecraft:sticky_piston[extended=true]") for p in pistons)
        and all(is_block(p, L.BARS) for p in g["closed_cells"]),
    )
    pull(g, False)
    advance()
    check(
        "portcullis opens again",
        all(is_block(p, "minecraft:sticky_piston[extended=false]") for p in pistons)
        and all(is_block(p, L.AIR) for p in g["closed_cells"]),
    )


def test_bookshelf_door(xw: int, y0: int, zd: int) -> None:
    """library west of the wall x=xw, hidden room east of it; door at zd"""
    L.fill(Vec3(xw - 10, y0, zd - 5), Vec3(xw - 1, y0 + 2, zd + 15), L.AIR)
    L.fill(Vec3(xw + 1, y0, zd - 5), Vec3(xw + 5, y0 + 2, zd + 15), L.AIR)
    d = L.bookshelf_door(xw, y0, zd)
    advance()
    check(
        "bookshelf door starts closed (pistons extended, bookshelf in doorway)",
        all(is_block(p, "minecraft:sticky_piston[extended=true]") for p in d["pistons"])
        and all(is_block(p, "minecraft:bookshelf") for p in d["door"]),
    )
    s = d["trigger"]
    c(f"data merge block {s.x} {s.y} {s.z} {{last_interacted_slot:5}}")
    advance()
    check(
        "pulling the 6th book opens the door",
        all(
            is_block(p, "minecraft:sticky_piston[extended=false]") for p in d["pistons"]
        )
        and all(is_block(p, L.AIR) for p in d["door"]),
    )
    c(f"data merge block {s.x} {s.y} {s.z} {{last_interacted_slot:2}}")
    advance()
    check(
        "touching another book closes it",
        all(is_block(p, "minecraft:sticky_piston[extended=true]") for p in d["pistons"])
        and all(is_block(p, "minecraft:bookshelf") for p in d["door"]),
    )


def test_lever_door(x: int, y0: int, zw: int) -> None:
    """along an x-running wall at zw: room to the south, hidden space north"""
    L.fill(Vec3(x - 4, y0, zw + 1), Vec3(x + 8, y0 + 2, zw + 6), L.AIR)
    L.fill(Vec3(x - 4, y0, zw - 8), Vec3(x + 8, y0 + 2, zw - 2), L.AIR)
    ld = L.hidden_door(
        Vec3(x, y0, zw),
        Vec3(0, 0, -1),
        Vec3(1, 0, 0),
        trigger="lever",
        material=L.BRICK,
    )
    advance()
    check("lever door starts closed", all(is_block(p, L.BRICK) for p in ld["door"]))
    t, f, facing = ld["trigger"], ld["first_dust"], ld["trigger_facing"]
    L.lever(t, facing, "wall", powered=True)
    L.set_block(f, L.AIR)  # a lever set by command does not update the wall's
    L.set_block(f, L.DUST)  # neighbours: poke the dust
    advance()
    check(
        "lever opens the door",
        all(is_block(p, L.AIR) for p in ld["door"])
        and all(
            is_block(p, "minecraft:sticky_piston[extended=false]")
            for p in ld["pistons"]
        ),
    )
    L.lever(t, facing, "wall", powered=False)
    L.set_block(f, L.AIR)
    L.set_block(f, L.DUST)
    advance()
    check("lever closes the door", all(is_block(p, L.BRICK) for p in ld["door"]))


def stand_y() -> float | None:
    m = re.search(
        r"\[[-\d.]+d, (-?[\d.]+)d, ",
        c("data get entity @e[tag=castle_test,limit=1] Pos"),
    )
    return float(m.group(1)) if m else None


def test_pit_trap(x: int, y0: int, zw: int) -> None:
    """corridor at x running north-south, the wire at zw"""
    L.fill(Vec3(x, y0, zw - 14), Vec3(x, y0 + 1, zw + 14), L.AIR)
    t = L.pit_trap(x, y0, zw, 6)
    advance()
    doors = t["trapdoors"]
    check(
        "pit trap starts closed",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
    )
    for travel in (1, -1):
        r, on = L.pit_timing(zw, [d.z for d in doors], travel)
        check(
            f"a walker ({travel:+d}) is over the pit in {r:.1f} <= {on:.1f} ticks",
            r <= on,
        )
    w = t["wire"] + Vec3(0.5, 0, 0.5)
    # a walker: on the string until the floor opens, then gone on along the
    # corridor at once; the floor is still open under where they were
    c(
        f'summon minecraft:armor_stand {w.x} {w.y} {w.z} {{Tags:["castle_test"],Invulnerable:1b}}'
    )
    opened = L.wait_until(
        lambda: all(is_block(p, "minecraft:iron_trapdoor[open=true]") for p in doors),
        20,
    )
    c(f"tp @e[tag=castle_test] {w.x} {w.y} {w.z + 3}")
    check(
        f"the wire opens the pit ({opened}), and it stays open after the walker steps off",
        opened
        and all(is_block(p, "minecraft:iron_trapdoor[open=true]") for p in doors),
    )
    c("kill @e[tag=castle_test]")
    advance()
    check(
        "pit closes again",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
    )
    # and whoever is on the wire falls in
    c(
        f'summon minecraft:armor_stand {w.x} {w.y} {w.z} {{Tags:["castle_test"],Invulnerable:1b}}'
    )
    advance()
    y = stand_y()
    check(
        f"what steps on the wire falls to the bottom (y {y}, bottom {t['bottom']}), and the pit shuts over it",
        y is not None
        and y < t["bottom"] + 1
        and is_block(t["wire"], "minecraft:tripwire")
        and all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
    )
    c("kill @e[tag=castle_test]")


def test_arrow_trap(x: int, y0: int, zw: int) -> None:
    """corridor x..x+2, the wire at zw, the dispensers 8 north of it"""
    L.fill(Vec3(x, y0, zw - 14), Vec3(x + 2, y0 + 1, zw + 14), L.AIR)
    a = L.arrow_trap(x, x + 2, y0, zw, zw - 8)
    w, dispensers = a["wire"], a["dispensers"]
    box = f"x={x - 2},y={y0 - 2},z={zw - 14},dx=7,dy=6,dz=29"
    advance()
    for trial in ("first", "second"):  # it must fire again, not just once
        c(f"kill @e[type=!minecraft:player,{box}]")
        advance()
        before = arrows_in(dispensers)
        c(
            f"summon minecraft:armor_stand {w.x} {w.y} {w.z} "
            '{Tags:["castle_test"],Invulnerable:1b}'
        )
        after = before
        for _ in range(6):
            advance(10)
            after = arrows_in(dispensers)
            if all(n < m for n, m in zip(after, before, strict=True)):
                break
        check(
            f"tripping the wire fires every dispenser, {trial} time ({before} -> {after})",
            all(n < m for n, m in zip(after, before, strict=True)),
        )
        c("kill @e[tag=castle_test]")
    c(f"kill @e[type=!minecraft:player,{box}]")


def main() -> None:
    test_layout()  # arithmetic only: before the rig
    b = rig_corner()
    e = b + SIZE - Vec3(1, 1, 1)
    near = L.players_near(b, e, 200)
    if near and not os.environ.get("FORCE"):
        raise SystemExit(f"{', '.join(near)} within 200 blocks of the rig: not testing")
    print(f"the rig: {b} to {e}")
    print(c(f"forceload add {b.x} {b.z} {e.x} {e.z}"))
    wait_loaded([(b.x, b.z), (e.x, e.z)], SIZE.x * SIZE.z // 256)
    try:
        if not is_empty(b, e):
            raise SystemExit(f"the rig's box {b}..{e} is not empty: give another RIG")
        L.fill(b, e, L.STONE)
        y0 = b.y + 8  # the standing level in the rigs
        zm = b.z + 15  # the middle of the rig, north to south
        x = b.x + 2
        test_portcullis(x, y0, zm)
        test_bookshelf_door(x + 28, y0, zm - 5)
        test_lever_door(x + 38, y0, zm + 7)
        test_pit_trap(x + 48, y0, zm)
        test_arrow_trap(x + 58, y0, zm)
    finally:
        L.fill(b, e, L.AIR)
        c(
            f"kill @e[type=!minecraft:player,x={b.x},y={b.y},z={b.z},dx={SIZE.x},dy={SIZE.y},dz={SIZE.z}]"
        )
        print(c(f"forceload remove {b.x} {b.z} {e.x} {e.z}"))
    print(f"{sum(results)}/{len(results)} module checks passed")
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
