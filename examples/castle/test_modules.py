"""
Exercise each redstone module of castle_lib in a block of stone in the air,
toggle it and read the result back. Run before trusting a module in the
castle::

    mciwb run test_modules.py        # TEST_KEEP=1 leaves the rigs in place

The server pauses when no player is online, so ticks are advanced with
``tick sprint``. A lever toggled with ``setblock`` only updates its own
neighbours, so every lever has a dust block beside it.
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle_lib as L  # noqa: E402

from mciwb.imports import Vec3, get_world  # noqa: E402

world = get_world()
OX = 130  # the rig stands east of the river, clear of the castle
B, E = (
    Vec3(OX - 20, 118, -200),
    Vec3(OX + 80, 140, -170),
)  # the rig: a slab of stone in the air


def c(command: str) -> str:
    return world.cmd(command)


def is_block(pos: Vec3, block: str) -> bool:
    return c(f"execute if block {pos.x} {pos.y} {pos.z} {block}") == "Test passed"


def advance(ticks: int = 40) -> None:
    c(f"tick sprint {ticks}")
    time.sleep(0.7)


def check(name: str, ok: bool) -> bool:
    print(("PASS " if ok else "FAIL ") + name)
    return ok


results = []
c(f"forceload add {B.x} {B.z} {E.x} {E.z}")
L.fill(B, E, L.AIR)
L.fill(B, E, L.STONE)
y0 = 126  # standing level in the rigs

# ---- portcullis: passage x 0..2, through z=-185, floor at 125
L.fill(Vec3(OX + 0, y0, -200), Vec3(OX + 2, y0 + 1, -170), L.AIR)
g = L.portcullis(OX + 0, OX + 2, -185, y0)
advance()
results.append(
    check("portcullis starts open", all(is_block(p, L.AIR) for p in g["closed_cells"]))
)
L.lever(g["lever"], "north", "floor", powered=True)
advance()
closed = all(
    is_block(p, "minecraft:sticky_piston[extended=true]")
    for p in g["ceiling_pistons"] + g["floor_pistons"]
)
bars = all(is_block(p, L.BARS) for p in g["closed_cells"])
results.append(
    check("portcullis closes (6 pistons extended, 6 cells barred)", closed and bars)
)
L.lever(g["lever"], "north", "floor", powered=False)
advance()
opened = all(
    is_block(p, "minecraft:sticky_piston[extended=false]")
    for p in g["ceiling_pistons"] + g["floor_pistons"]
)
results.append(
    check(
        "portcullis opens again",
        opened and all(is_block(p, L.AIR) for p in g["closed_cells"]),
    )
)

# ---- bookshelf door: library x 20..29, wall x=30, hidden room x 31..35; door at z=-190
L.fill(Vec3(OX + 20, y0, -195), Vec3(OX + 29, y0 + 2, -175), L.AIR)
L.fill(Vec3(OX + 31, y0, -195), Vec3(OX + 35, y0 + 2, -175), L.AIR)
d = L.bookshelf_door(OX + 30, y0, -190)
advance()
results.append(
    check(
        "bookshelf door starts closed (pistons extended, bookshelf in doorway)",
        all(is_block(p, "minecraft:sticky_piston[extended=true]") for p in d["pistons"])
        and all(is_block(p, "minecraft:bookshelf") for p in d["door"]),
    )
)
s = d["trigger"]
c(f"data merge block {s.x} {s.y} {s.z} {{last_interacted_slot:5}}")
advance()
results.append(
    check(
        "pulling the 6th book opens the door",
        all(
            is_block(p, "minecraft:sticky_piston[extended=false]") for p in d["pistons"]
        )
        and all(is_block(p, L.AIR) for p in d["door"]),
    )
)
c(f"data merge block {s.x} {s.y} {s.z} {{last_interacted_slot:2}}")
advance()
results.append(
    check(
        "touching another book closes it",
        all(is_block(p, "minecraft:sticky_piston[extended=true]") for p in d["pistons"])
        and all(is_block(p, "minecraft:bookshelf") for p in d["door"]),
    )
)

# ---- lever door along an x-running wall: room to the south (z > -178), hidden space north
L.fill(Vec3(OX + 36, y0, -177), Vec3(OX + 48, y0 + 2, -172), L.AIR)
L.fill(Vec3(OX + 36, y0, -186), Vec3(OX + 48, y0 + 2, -180), L.AIR)
ld = L.hidden_door(
    Vec3(OX + 40, y0, -178),
    Vec3(0, 0, -1),
    Vec3(1, 0, 0),
    trigger="lever",
    material=L.BRICK,
)
advance()
results.append(
    check("lever door starts closed", all(is_block(p, L.BRICK) for p in ld["door"]))
)
t = ld["trigger"]
c(f"setblock {t.x} {t.y} {t.z} minecraft:lever[face=wall,facing=south,powered=true]")
f = ld["first_dust"]
c(f"setblock {f.x} {f.y} {f.z} minecraft:air")
c(
    f"setblock {f.x} {f.y} {f.z} minecraft:redstone_wire"
)  # a lever set by command does not update the wall's neighbours: poke the dust
advance()
results.append(
    check(
        "lever opens the door",
        all(is_block(p, L.AIR) for p in ld["door"])
        and all(
            is_block(p, "minecraft:sticky_piston[extended=false]")
            for p in ld["pistons"]
        ),
    )
)
c(f"setblock {t.x} {t.y} {t.z} minecraft:lever[face=wall,facing=south,powered=false]")
c(f"setblock {f.x} {f.y} {f.z} minecraft:air")
c(f"setblock {f.x} {f.y} {f.z} minecraft:redstone_wire")
advance()
results.append(
    check("lever closes the door", all(is_block(p, L.BRICK) for p in ld["door"]))
)

# ---- pit trap: corridor x=50, z -200..-170
L.fill(Vec3(OX + 50, y0, -200), Vec3(OX + 50, y0 + 1, -170), L.AIR)
t = L.pit_trap(OX + 50, y0, -185, 8)
advance()
results.append(
    check(
        "pit trap starts closed",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in t["trapdoors"]),
    )
)
w = t["wire"]
c(f'summon minecraft:armor_stand {w.x} {w.y} {w.z} {{Tags:["castle_test"]}}')
advance()
results.append(
    check(
        "walking onto the wire opens the pit",
        all(is_block(p, "minecraft:iron_trapdoor[open=true]") for p in t["trapdoors"]),
    )
)
c("kill @e[tag=castle_test]")
advance()
results.append(
    check(
        "pit closes again",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in t["trapdoors"]),
    )
)

# ---- arrow trap: corridor x 60..62
L.fill(Vec3(OX + 60, y0, -200), Vec3(OX + 62, y0 + 1, -170), L.AIR)
a = L.arrow_trap(OX + 60, OX + 62, y0, -185, -193)
c(f"kill @e[type=minecraft:arrow,x={OX + 61},y={y0},z=-185,distance=..30]")
advance()
w = a["wire"]
c(f'summon minecraft:armor_stand {w.x} {w.y} {w.z} {{Tags:["castle_test"]}}')
advance()
r = c(
    f"execute if entity @e[type=minecraft:arrow,x={OX + 61},y={y0},z=-185,distance=..30]"
)
results.append(
    check(f"tripping the wire fires arrows ({r})", r.startswith("Test passed"))
)
c(f"kill @e[type=minecraft:arrow,x={OX + 61},y={y0},z=-185,distance=..30]")
c("kill @e[tag=castle_test]")

if not os.environ.get("TEST_KEEP"):
    L.fill(B, E, L.AIR)
    c(
        f"kill @e[type=!player,x={B.x},y={B.y},z={B.z},dx={E.x - B.x},dy={E.y - B.y},dz={E.z - B.z}]"
    )
    c(f"forceload remove {B.x} {B.z} {E.x} {E.z}")
print(f"{sum(results)}/{len(results)} module checks passed")
if not all(results):
    raise SystemExit(1)
