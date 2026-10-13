"""
Verify the castle's mechanisms over RCON, without a player::

    ORIGIN=-80,82,-230 mciwb run verify_castle.py

The server pauses when nobody is online, so ``tick sprint`` advances the
game between a trigger and its check. Levers and hooks set with ``setblock``
only update their own neighbours (a player's click also updates the powered
block's neighbours), so levers here have dust beside them, lever doors get
their first dust re-placed ("poked"), and tripwires are tripped by summoning
an armour stand onto them, which runs the real tripwire logic.

The site is forceloaded for the checks and unloaded again afterwards.
Exits non-zero if any check fails. Leaves everything as it found it: the
levers off, the bookshelf untouched, the dispensers reloaded.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import build_outer  # noqa: E402
import castle_lib as L  # noqa: E402
from castle_layout import (  # noqa: E402
    ARROW_TRAP,
    BRIDGE_END,
    CELL_DOOR,
    CHAPEL,
    CRYPT_DOOR,
    ENGINE,
    HIGHEST,
    KEEP,
    KEEP_ROOF,
    LIBRARY_DOOR,
    LIBRARY_LADDER,
    LOWEST,
    MAIN_GATE,
    MIDDLE_GATE,
    PIT_TRAP,
    TAG,
    TELEPORTS,
    VAULT_Y,
    WELL,
    WELL_TUNNEL_X,
    XG,
    YU,
    ZS,
    V,
    site_box,
)

from mciwb.imports import Vec3, get_world  # noqa: E402

E, S, Wd = Vec3(1, 0, 0), Vec3(0, 0, 1), Vec3(-1, 0, 0)
world = get_world()
results: list[bool] = []
# what the build summons, by type: a rerun must not add to them
ENTITIES = {
    "horse": 6,
    "armor_stand": 12,
    "item_frame": 24,
    "iron_golem": 1,
    "cat": 1,
}


def c(command: str) -> str:
    return world.cmd(command)


def is_block(pos: Vec3, block: str) -> bool:
    for _attempt in range(3):  # an empty reply is another RCON client's doing
        r = c(f"execute if block {pos.x} {pos.y} {pos.z} {block}")
        if r.strip():
            break
    return "Test passed" in r


def count(selector: str) -> int:
    """how many entities a selector matches"""
    r = c(f"execute if entity @e[{selector}]")
    m = re.search(r"[Cc]ount: (\d+)", r)
    return int(m.group(1)) if m else 0


def advance(ticks: int = 40) -> None:
    c(f"tick sprint {ticks}")
    time.sleep(0.7)


def check(name: str, ok: bool) -> None:
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name)


def poke(pos: Vec3) -> None:
    c(f"setblock {pos.x} {pos.y} {pos.z} minecraft:air")
    c(f"setblock {pos.x} {pos.y} {pos.z} minecraft:redstone_wire")


def set_lever(pos: Vec3, facing: str, face: str, on: bool) -> None:
    L.lever(pos, facing, face, powered=on)


def portcullis(name: str, gate: tuple[int, int, int, int]) -> None:
    g = L.portcullis_cells(*build_outer.portcullis_args(gate))
    lever, cells = g["lever"], g["closed_cells"]
    pistons = g["ceiling_pistons"] + g["floor_pistons"]
    check(f"{name}: lever present", is_block(lever, "minecraft:lever"))
    check(f"{name}: starts open", all(is_block(p, L.AIR) for p in cells))
    set_lever(lever, "north", "floor", True)
    advance()
    check(
        f"{name}: lever on closes it (6 pistons, 6 cells barred)",
        all(is_block(p, "minecraft:sticky_piston[extended=true]") for p in pistons)
        and all(is_block(p, L.BARS) for p in cells),
    )
    set_lever(lever, "north", "floor", False)
    advance()
    check(
        f"{name}: lever off opens it",
        all(is_block(p, "minecraft:sticky_piston[extended=false]") for p in pistons)
        and all(is_block(p, L.AIR) for p in cells),
    )


def lever_door(name: str, base: Vec3, lever_b: int, material: str) -> None:
    d = L.hidden_door_cells(base, Wd, S, trigger="lever", lever_b=lever_b)
    lever, first, facing = d["trigger"], d["first_dust"], d["trigger_facing"]
    check(f"{name}: lever present", is_block(lever, "minecraft:lever"))
    check(f"{name}: door starts closed", all(is_block(p, material) for p in d["door"]))
    set_lever(lever, facing, "wall", True)
    poke(first)
    advance()
    check(f"{name}: lever opens the door", all(is_block(p, L.AIR) for p in d["door"]))
    set_lever(lever, facing, "wall", False)
    poke(first)
    advance()
    check(
        f"{name}: lever closes the door", all(is_block(p, material) for p in d["door"])
    )


def trip(wire: Vec3) -> None:
    c(
        f'summon minecraft:armor_stand {wire.x} {wire.y} {wire.z} {{Tags:["castle_verify"]}}'
    )
    advance()


def untrip() -> None:
    c("kill @e[tag=castle_verify]")
    advance()


def library() -> None:
    d = L.hidden_door_cells(V(*LIBRARY_DOOR), E, S)
    shelf, door, pistons = d["trigger"], d["door"], d["pistons"]
    lx, lz = LIBRARY_LADDER
    check(
        "library: chiseled bookshelf is there",
        is_block(shelf, "minecraft:chiseled_bookshelf"),
    )
    check(
        "library: door starts closed",
        all(is_block(p, "minecraft:bookshelf") for p in door),
    )
    try:
        c(f"data merge block {shelf.x} {shelf.y} {shelf.z} {{last_interacted_slot:5}}")
        advance()
        check(
            "library: last book opens the door (pistons retract)",
            all(is_block(p, L.AIR) for p in door)
            and all(
                is_block(p, "minecraft:sticky_piston[extended=false]") for p in pistons
            ),
        )
        check(
            "library: ladder shaft behind it goes down to the vault",
            all(
                is_block(V(lx, y, lz), "minecraft:ladder")
                for y in range(VAULT_Y, YU + 11)
            ),
        )
        c(f"data merge block {shelf.x} {shelf.y} {shelf.z} {{last_interacted_slot:1}}")
        advance()
        check(
            "library: another book closes it",
            all(is_block(p, "minecraft:bookshelf") for p in door),
        )
    finally:
        # as built: no book touched yet
        c(f"data merge block {shelf.x} {shelf.y} {shelf.z} {{last_interacted_slot:-1}}")
        advance()


def traps() -> None:
    px, py, pz, depth = PIT_TRAP
    t = L.pit_trap_cells(*V(px, py, pz), depth, travel=1)
    wire, doors = t["wire"], t["trapdoors"]
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
        all(is_block(p, L.AIR) for p in t["shaft"]),
    )
    untrip()
    check(
        "pit trap: closes again",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
    )

    ax1, ax2, ay, zw, zd = ARROW_TRAP
    o = V(0, 0, 0)
    a = L.arrow_trap_cells(o.x + ax1, o.x + ax2, o.y + ay, o.z + zw, o.z + zd)
    wire, dispensers = a["wire"], a["dispensers"]
    arrows = f"type=minecraft:arrow,x={wire.x},y={wire.y},z={wire.z},distance=..40"
    c(f"kill @e[{arrows}]")
    check("arrow trap: tripwire present", is_block(wire, "minecraft:tripwire"))
    check(
        "arrow trap: dispensers loaded with arrows",
        all(
            is_block(p, "minecraft:dispenser")
            and "minecraft:arrow" in c(f"data get block {p.x} {p.y} {p.z} Items")
            for p in dispensers
        ),
    )
    try:
        c(
            f'summon minecraft:armor_stand {wire.x} {wire.y} {wire.z} {{Tags:["castle_verify"]}}'
        )
        r = "Test failed"
        for _ in range(
            8
        ):  # the dispensers fire within a few ticks; poll in short steps
            advance(10)
            r = c(f"execute if entity @e[{arrows}]")
            if r.startswith("Test passed"):
                break
        check(
            f"arrow trap: crossing the wire fires arrows ({r})",
            r.startswith("Test passed"),
        )
    finally:
        c(f"kill @e[{arrows}]")
        untrip()
        for p in dispensers:  # reload them
            c(
                f"item replace block {p.x} {p.y} {p.z} container.4 with minecraft:arrow 64"
            )


def passages() -> None:
    wx, wz = WELL
    tx = WELL_TUNNEL_X
    check(
        "well: water column with soul sand at the bottom",
        is_block(V(wx, -9, wz), "minecraft:soul_sand")
        and all(
            is_block(V(wx, y, wz), "minecraft:bubble_column") for y in range(-8, 0)
        ),
    )
    check(
        "well: a door at the bottom into a dry tunnel",
        is_block(V(wx + 1, -8, wz), "minecraft:dark_oak_door")
        and is_block(V(wx + 2, -8, wz), L.AIR)
        and is_block(V(tx, -8, 130), L.AIR),
    )
    check(
        "well tunnel stays under the bailey, then climbs to the vault door",
        not is_block(V(tx, -1, 80), L.AIR)
        and is_block(V(tx, -8, 80), L.AIR)
        and is_block(V(tx, VAULT_Y, 32), L.AIR)
        and is_block(V(tx, VAULT_Y, 31), "minecraft:iron_door"),
    )
    check(
        "well tunnel is lined (cobble beside and above it)",
        is_block(V(tx - 1, -8, 120), L.COBBLE)
        and is_block(V(tx + 1, -8, 120), L.COBBLE)
        and is_block(V(tx, -5, 120), L.COBBLE),
    )
    check(
        "smithy: trapdoor over a ladder to the lower treasury",
        is_block(V(107, -1, 105), "minecraft:spruce_trapdoor")
        and all(is_block(V(107, y, 105), "minecraft:ladder") for y in range(-14, -1))
        and is_block(V(107, -15, 105), L.AIR),
    )


def engine() -> None:
    cx, cz, ey = ENGINE
    ring = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
    lamp = V(cx, ey, cz - 3)
    lamps, patterns = [], []
    # hoppers move items every 8 ticks: sample at 5 and 7 ticks alternately,
    # so that the samples do not fall into step with the lamp
    for i in range(32):
        c(f"tick sprint {5 if i % 2 else 7}")
        time.sleep(0.15)
        lamps.append(is_block(lamp, "minecraft:redstone_lamp[lit=true]"))
        pattern = ""
        for dx, dz in ring:
            h = V(cx + dx, ey, cz + dz)
            items = c(f"data get block {h.x} {h.y} {h.z} Items")
            pattern += "X" if "amethyst" in items else "."
        patterns.append(pattern)
    lit = "".join("1" if s else "0" for s in lamps)
    check(
        f"engine: shards circulate the hopper ring ({len(set(patterns))} patterns seen) and the lamp blinks ({lit})",
        len(set(patterns)) > 1 and len(set(lamps)) > 1,
    )


def places() -> None:
    kx1, kz1, kx2, kz2 = KEEP
    chest = V(54, VAULT_Y, 17)
    r = c(f"data get block {chest.x} {chest.y} {chest.z} Items")
    check("vault: first chest holds diamonds", "diamond" in r)
    check(
        "vault: diamond block on its pedestal",
        is_block(V(60, VAULT_Y + 1, 23), "minecraft:diamond_block"),
    )
    check("keep: great door", is_block(V(XG, YU, kz2), "minecraft:dark_oak_door"))
    cx1, cz1, cx2, cz2 = CHAPEL
    check(
        "chapel: altar and bell",
        is_block(V(98, YU + 2, cz1 + 2), "minecraft:gold_block")
        and is_block(V(cx1 + 1, YU + 23, cz2 + 2), "minecraft:bell"),
    )
    check(
        "extents: lightning rod on the keep's lantern tower, lining under the catacombs",
        any(  # lightning rods oxidise like copper as the game ticks
            is_block(
                V(XG, HIGHEST, (kz1 + kz2) // 2), f"minecraft:{stage}lightning_rod"
            )
            for stage in ("", "exposed_", "weathered_", "oxidized_")
        )
        and is_block(V(91, LOWEST, 123), L.DARK_BRICK)
        and is_block(V(XG, KEEP_ROOF - 1, 35), L.ANDESITE),
    )
    for name, (x, y, z) in TELEPORTS.items():
        p = V(x, y, z)
        check(
            f"teleport to {name} ({p.x} {p.y} {p.z}) lands on a floor with head room",
            is_block(p, L.AIR)
            and is_block(p + Vec3(0, 1, 0), L.AIR)
            and not is_block(p - Vec3(0, 1, 0), L.AIR)
            and not is_block(p - Vec3(0, 1, 0), L.WATER),
        )


def entities() -> None:
    a, b = site_box()
    box = f"x={a.x},y={a.y},z={a.z},dx={b.x - a.x + 1},dy={b.y - a.y + 1},dz={b.z - a.z + 1}"
    for kind, n in ENTITIES.items():
        tagged = count(f"type=minecraft:{kind},tag={TAG}")
        strays = count(f"type=minecraft:{kind},tag=!{TAG},{box}")
        check(
            f"entities: {n} {kind} tagged {TAG} (found {tagged}), none untagged in the site (found {strays})",
            tagged == n and strays == 0,
        )


def main() -> None:
    build_outer.forceload(True, with_road=False)
    try:
        portcullis("main gate", MAIN_GATE)
        portcullis("middle gate", MIDDLE_GATE)
        blocked = [z for z in range(ZS - 8, ZS + 1) if not is_block(V(XG, 0, z), L.AIR)]
        check(
            f"main gate passage is open end to end (blocked at local z {blocked})",
            not blocked,
        )
        check(
            "bridge spans the moat",
            all(
                is_block(V(XG, -1, z), L.PLANKS) for z in range(ZS + 1, BRIDGE_END + 1)
            ),
        )
        library()
        lever_door("cell block", V(*CELL_DOOR), -3, L.BRICK)
        lever_door("crypt", V(*CRYPT_DOOR), -1, L.DARK_BRICK)
        traps()
        passages()
        engine()
        places()
        entities()
    finally:
        c("kill @e[tag=castle_verify]")
        build_outer.forceload(False, with_road=False)
    print(f"{sum(results)}/{len(results)} checks passed")
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
