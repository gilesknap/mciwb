"""
Verify the castle's mechanisms over RCON, without a player::

    mciwb run verify_castle.py

The server pauses when nobody is online, so ``tick sprint`` advances the
game between a trigger and its check. Levers and hooks set with ``setblock``
only update their own neighbours (a player's click also updates the powered
block's neighbours), so levers here have dust beside them, lever doors get
their first dust re-placed ("poked"), and tripwires are tripped by summoning
an armour stand onto them, which runs the real tripwire logic.

Exits non-zero if any check fails. Leaves everything as it found it.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle_lib as L  # noqa: E402
from castle_layout import GATE_X1, GATE_X2, GATE_Z, KEEP, UD, XG, YU, ZS, V  # noqa: E402

from mciwb.imports import Vec3, get_world  # noqa: E402

world = get_world()
results: list[bool] = []


def c(command: str) -> str:
    return world.cmd(command)


def is_block(pos: Vec3, block: str) -> bool:
    return c(f"execute if block {pos.x} {pos.y} {pos.z} {block}") == "Test passed"


def advance(ticks: int = 40) -> None:
    c(f"tick sprint {ticks}")
    time.sleep(0.7)


def check(name: str, ok: bool) -> None:
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name)


def poke(pos: Vec3) -> None:
    c(f"setblock {pos.x} {pos.y} {pos.z} minecraft:air")
    c(f"setblock {pos.x} {pos.y} {pos.z} minecraft:redstone_wire")


def portcullis(name: str, x1: int, x2: int, z: int, y0: int) -> None:
    lever = Vec3(x2 + 2, y0 + 4, z)
    pistons = [Vec3(x, y0 + 3, z) for x in range(x1, x2 + 1)] + [
        Vec3(x, y0 - 2, z) for x in range(x1, x2 + 1)
    ]
    cells = [Vec3(x, y, z) for x in range(x1, x2 + 1) for y in (y0, y0 + 1)]
    check(f"{name}: lever present", is_block(lever, "minecraft:lever"))
    check(f"{name}: starts open", all(is_block(p, L.AIR) for p in cells))
    L.lever(lever, "north", "floor", powered=True)
    advance()
    check(
        f"{name}: lever on closes it (6 pistons, 6 cells barred)",
        all(is_block(p, "minecraft:sticky_piston[extended=true]") for p in pistons)
        and all(is_block(p, L.BARS) for p in cells),
    )
    L.lever(lever, "north", "floor", powered=False)
    advance()
    check(
        f"{name}: lever off opens it",
        all(is_block(p, "minecraft:sticky_piston[extended=false]") for p in pistons)
        and all(is_block(p, L.AIR) for p in cells),
    )


def trip(wire: Vec3) -> None:
    c(
        f'summon minecraft:armor_stand {wire.x} {wire.y} {wire.z} {{Tags:["castle_verify"]}}'
    )
    advance()


def untrip() -> None:
    c("kill @e[tag=castle_verify]")
    advance()


def main() -> None:
    c("forceload query")
    # ---- the two portcullises
    portcullis(
        "main gate",
        V(GATE_X1, 0, 0).x,
        V(GATE_X2, 0, 0).x,
        V(0, 0, GATE_Z).z,
        V(0, 0, 0).y,
    )
    portcullis(
        "middle gate",
        V(GATE_X1, 0, 0).x,
        V(GATE_X2, 0, 0).x,
        V(0, 0, UD - 2).z,
        V(0, YU, 0).y,
    )
    # the gate passages are clear through
    blocked = [z for z in range(ZS - 8, ZS + 1) if not is_block(V(XG, 0, z), L.AIR)]
    check(
        f"main gate passage is open end to end (blocked at local z {blocked})",
        not blocked,
    )
    check(
        "bridge spans the moat",
        all(is_block(V(XG, -1, z), L.PLANKS) for z in range(ZS + 1, ZS + 8)),
    )

    # ---- the library's bookshelf door
    d = L.hidden_door.__wrapped__ if hasattr(L.hidden_door, "__wrapped__") else None  # noqa: F841 (placeholder)
    base = V(58, YU + 10, 20)
    shelf = base + Vec3(0, 1, 8)
    door_cells = [base, base + Vec3(0, 1, 0)]
    pistons = [base + Vec3(0, 0, 2), base + Vec3(0, 1, 2)]
    check(
        "library: chiseled bookshelf is there",
        is_block(shelf, "minecraft:chiseled_bookshelf"),
    )
    check(
        "library: door starts closed",
        all(is_block(p, "minecraft:bookshelf") for p in door_cells),
    )
    c(f"data merge block {shelf.x} {shelf.y} {shelf.z} {{last_interacted_slot:5}}")
    advance()
    check(
        "library: last book opens the door (pistons retract)",
        all(is_block(p, L.AIR) for p in door_cells)
        and all(
            is_block(p, "minecraft:sticky_piston[extended=false]") for p in pistons
        ),
    )
    check(
        "library: ladder shaft behind it goes down to the vault",
        is_block(V(60, YU + 9, 20), "minecraft:ladder")
        and is_block(V(60, 12, 20), "minecraft:ladder")
        and is_block(V(60, 8, 20), "minecraft:ladder"),
    )
    c(f"data merge block {shelf.x} {shelf.y} {shelf.z} {{last_interacted_slot:1}}")
    advance()
    check(
        "library: another book closes it",
        all(is_block(p, "minecraft:bookshelf") for p in door_cells),
    )

    # ---- lever doors: the dungeon's last cell and the crypt
    for name, base, u, v, lever_b, material, lever_facing in (
        (
            "cell block",
            V(69, -8, 137),
            Vec3(-1, 0, 0),
            Vec3(0, 0, 1),
            -3,
            L.BRICK,
            "east",
        ),
        (
            "crypt",
            V(71, 8, 23),
            Vec3(-1, 0, 0),
            Vec3(0, 0, 1),
            -1,
            L.DARK_BRICK,
            "east",
        ),
    ):
        lever = base - u + v * lever_b + Vec3(0, 1, 0)
        first = base + u + v * lever_b + Vec3(0, 1, 0)
        door_cells = [base, base + Vec3(0, 1, 0)]
        check(f"{name}: lever present", is_block(lever, "minecraft:lever"))
        check(
            f"{name}: door starts closed",
            all(is_block(p, material) for p in door_cells),
        )
        c(
            f"setblock {lever.x} {lever.y} {lever.z} minecraft:lever[face=wall,facing={lever_facing},powered=true]"
        )
        poke(first)
        advance()
        check(
            f"{name}: lever opens the door", all(is_block(p, L.AIR) for p in door_cells)
        )
        c(
            f"setblock {lever.x} {lever.y} {lever.z} minecraft:lever[face=wall,facing={lever_facing},powered=false]"
        )
        poke(first)
        advance()
        check(
            f"{name}: lever closes the door",
            all(is_block(p, material) for p in door_cells),
        )

    # ---- the pit trap in the dungeon approach
    wire = V(95, -8, 125)
    doors = [V(95, -9, 127), V(95, -9, 128)]
    check("pit trap: tripwire present", is_block(wire, "minecraft:tripwire"))
    check(
        "pit trap: trapdoors start closed",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
    )
    trip(wire)
    check(
        "pit trap: walking onto the wire opens the floor",
        all(is_block(p, "minecraft:iron_trapdoor[open=true]") for p in doors),
    )
    check(
        "pit trap: the shaft drops into the oubliette",
        all(is_block(V(95, y, 127), L.AIR) for y in range(-15, -9)),
    )
    untrip()
    check(
        "pit trap: closes again",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
    )

    # ---- the arrow trap in the catacombs
    wire = V(95, -15, 118)
    c(f"kill @e[type=minecraft:arrow,x={wire.x},y={wire.y},z={wire.z},distance=..40]")
    check("arrow trap: tripwire present", is_block(wire, "minecraft:tripwire"))
    check(
        "arrow trap: dispensers loaded",
        all(is_block(V(x, -14, 108), "minecraft:dispenser") for x in (94, 95, 96)),
    )
    c(
        f'summon minecraft:armor_stand {wire.x} {wire.y} {wire.z} {{Tags:["castle_verify"]}}'
    )
    r = "Test failed"
    for _ in range(8):  # the dispensers fire within a few ticks; poll in short steps
        advance(10)
        r = c(
            f"execute if entity @e[type=minecraft:arrow,x={wire.x},y={wire.y},z={wire.z},distance=..40]"
        )
        if r.startswith("Test passed"):
            break
    check(
        f"arrow trap: crossing the wire fires arrows ({r})", r.startswith("Test passed")
    )
    c(f"kill @e[type=minecraft:arrow,x={wire.x},y={wire.y},z={wire.z},distance=..40]")
    untrip()

    # ---- the well
    check(
        "well: water column with soul sand at the bottom",
        is_block(V(60, -9, 105), "minecraft:soul_sand")
        and all(
            is_block(V(60, y, 105), "minecraft:bubble_column") for y in range(-8, 0)
        ),
    )
    check(
        "well: a door at the bottom into a dry tunnel",
        is_block(V(61, -8, 105), "minecraft:dark_oak_door")
        and is_block(V(62, -8, 105), L.AIR)
        and is_block(V(65, -8, 130), L.AIR),
    )
    check(
        "well tunnel stays under the bailey, then climbs to the vault door",
        not is_block(V(65, -1, 80), L.AIR)
        and is_block(V(65, -8, 80), L.AIR)
        and is_block(V(65, 8, 32), L.AIR)
        and is_block(V(65, 8, 31), "minecraft:iron_door"),
    )

    # ---- the smithy's trapdoor and the lower treasury
    check(
        "smithy: trapdoor over a ladder to the lower treasury",
        is_block(V(107, -1, 107), "minecraft:spruce_trapdoor")
        and is_block(V(107, -10, 107), "minecraft:ladder")
        and is_block(V(107, -15, 107), L.AIR),
    )

    # ---- the engine: the lamps should change over time
    cx, cz, ey = 18, 22, YU + 24
    ring = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
    lamp = V(cx, ey, cz - 3)
    lamps, patterns = [], []
    for _ in range(20):
        c("tick sprint 6")
        time.sleep(0.15)
        lamps.append(is_block(lamp, "minecraft:redstone_lamp[lit=true]"))
        patterns.append(
            "".join(
                "X"
                if "amethyst"
                in c(
                    f"data get block {V(cx + dx, ey, cz + dz).x} {V(0, ey, 0).y} {V(0, 0, cz + dz).z} Items"
                )
                else "."
                for dx, dz in ring
            )
        )
    lit = "".join("1" if s else "0" for s in lamps)
    check(
        f"engine: shards circulate the hopper ring ({len(set(patterns))} patterns seen) and the lamp blinks ({lit})",
        len(set(patterns)) > 1 and len(set(lamps)) > 1,
    )

    # ---- the treasure
    r = c(f"data get block {V(54, 8, 17).x} {V(54, 8, 17).y} {V(54, 8, 17).z} Items")
    check("vault: first chest holds diamonds", "diamond" in r)
    check(
        "vault: diamond block on its pedestal",
        is_block(V(60, 9, 23), "minecraft:diamond_block"),
    )

    # ---- the keep's great door and the chapel
    kx1, kz1, kx2, kz2 = KEEP
    check("keep: great door", is_block(V(XG, YU, kz2), "minecraft:dark_oak_door"))
    check(
        "chapel: altar and bell",
        is_block(V(98, YU + 2, 16), "minecraft:gold_block")
        and is_block(V(87, YU + 23, 42), "minecraft:bell"),
    )

    c("kill @e[tag=castle_verify]")
    print(f"{sum(results)}/{len(results)} checks passed")
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
