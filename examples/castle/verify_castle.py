"""
Verify the castle's mechanisms over RCON, without a player::

    ORIGIN=-80,82,-230 mciwb run verify_castle.py

The server pauses when nobody is online, so ``tick sprint`` advances the
game between a trigger and its check (with a player online it waits for
the game's own ticks instead). It refuses to run while a player is within
200 blocks of the site, unless FORCE=1. Levers and hooks set with ``setblock``
only update their own neighbours (a player's click also updates the powered
block's neighbours), so levers here have dust beside them, lever doors get
their first dust re-placed ("poked"), and tripwires are tripped by summoning
an armour stand onto them, which runs the real tripwire logic.

The site is forceloaded for the checks and unloaded again afterwards.
Hostile mobs in the site (the night its ticks bring spawns them where it
is dark) and anything on a tripwire are cleared first. Exits non-zero if
any check fails. Leaves everything as it found it: the levers off, the
bookshelf untouched, the dispensers reloaded, its own armour stands gone.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import build_outer  # noqa: E402
import castle_lib as L  # noqa: E402
from castle_layout import (  # noqa: E402
    ARROW_TRAP,
    BAILEY_TOWERS,
    BRIDGE_END,
    CELL_DOOR,
    CELL_LEVER,
    CELL_ROWS,
    CHAPEL,
    CRYPT_DOOR,
    DUNGEON_Y,
    ENGINE,
    GATE_BANNER_DX,
    GATEHOUSE,
    HIGHEST,
    KEEP,
    KEEP_ROOF,
    LIBRARY_DOOR,
    LIBRARY_LADDER,
    LOWEST,
    MAIN_GATE,
    MIDDLE_GATE,
    NAME,
    ORIGIN,
    PIT_TRAP,
    ROOFED_TOWERS,
    SMITHY_HATCH,
    SPAWN,
    STANDING_SIGNS,
    SUMMONED,
    TAG,
    TELEPORTS,
    VAULT,
    VAULT_Y,
    WALL_H,
    WALL_STAIRS,
    WELL,
    WELL_TUNNEL_X,
    XG,
    YU,
    ZS,
    V,
    layout_problems,
    site_box,
)

from mciwb.builders import ground_height  # noqa: E402
from mciwb.imports import Vec3, get_world  # noqa: E402

E, S, Wd = Vec3(1, 0, 0), Vec3(0, 0, 1), Vec3(-1, 0, 0)
world = get_world()
results: list[bool] = []
# what the build summons, by type: a rerun must not add to them
ENTITIES: dict[str, int] = {}
for _counts in SUMMONED.values():
    for _kind, _n in _counts.items():
        ENTITIES[_kind] = ENTITIES.get(_kind, 0) + _n


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


def clear(a: Vec3, b: Vec3) -> None:
    """clear a trap of what would hold its wire or get in the way: hostile
    mobs, armour stands that are not the castle's, arrows, and dropped
    armour stands and arrows (the checks' own leavings; never other items
    or pets, which may be a player's)"""
    box = L.box_selector(a, b)
    L.kill_hostiles(a, b)
    c(f"kill @e[type=minecraft:armor_stand,tag=!{TAG},{box}]")
    c(f"kill @e[type=minecraft:arrow,{box}]")
    for item in ("armor_stand", "arrow"):  # what the checks themselves drop
        c(f'kill @e[type=minecraft:item,nbt={{Item:{{id:"minecraft:{item}"}}}},{box}]')


count = L.count_entities


def advance(ticks: int = 40) -> None:
    L.tick(ticks)
    time.sleep(0.5)


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
    was_on = is_block(lever, "minecraft:lever[powered=true]")
    barred = all(is_block(p, L.BARS) for p in cells)
    open_ = all(is_block(p, L.AIR) for p in cells)
    state = "closed" if barred else "open" if open_ else "half way"
    check(
        f"{name}: found {state}, lever {'on' if was_on else 'off'} (a visitor may leave it closed)",
        (barred and was_on) or (open_ and not was_on),
    )
    try:
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
    finally:
        if was_on:  # leave it as found
            set_lever(lever, "north", "floor", True)
            advance()


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
    """stand something on the wire: invulnerable, so that the arrows it draws
    do not break it (a broken stand drops an item, and the item holds the
    wire tripped)"""
    c(
        f"summon minecraft:armor_stand {wire.x} {wire.y} {wire.z} "
        '{Tags:["castle_verify"],Invulnerable:1b}'
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
    clear(V(px - 3, py - 1, pz - 10), V(px + 3, py + 3, pz + 10))
    advance()
    check(
        "pit trap: tripwire present and not already tripped",
        is_block(wire, "minecraft:tripwire[powered=false]"),
    )
    check(
        "pit trap: trapdoors start closed",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
    )
    try:
        trip(wire)
        check(
            "pit trap: walking onto the wire opens the floor",
            all(is_block(p, "minecraft:iron_trapdoor[open=true]") for p in doors),
        )
        check(
            "pit trap: the shaft drops into the oubliette",
            all(is_block(p, L.AIR) for p in t["shaft"]),
        )
    finally:
        untrip()
    check(
        "pit trap: closes again",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
    )

    ax1, ax2, ay, zw, zd = ARROW_TRAP
    o = V(0, 0, 0)
    a = L.arrow_trap_cells(o.x + ax1, o.x + ax2, o.y + ay, o.z + zw, o.z + zd)
    wire, dispensers = a["wire"], a["dispensers"]
    # the corridor and the oubliette behind it: nothing on the wire, no
    # mob in the way, no arrows about
    clear(V(ax1 - 3, ay - 2, zd - 4), V(ax2 + 3, ay + 4, zw + 16))
    advance()
    check(
        "arrow trap: tripwire present and not already tripped",
        is_block(wire, "minecraft:tripwire[powered=false]")
        and all(
            is_block(h, "minecraft:tripwire_hook[powered=false]") for h in a["hooks"]
        ),
    )
    before = arrows_in(dispensers)
    check(
        f"arrow trap: dispensers loaded with arrows ({before})",
        all(is_block(p, "minecraft:dispenser") for p in dispensers)
        and all(n > 0 for n in before),
    )
    try:
        # arrows that hit the stand on the wire break it and vanish, so the
        # proof of firing is the dispensers' stock going down, not arrows
        trip(wire)
        after = before
        for _ in range(8):
            after = arrows_in(dispensers)
            if all(n < m for n, m in zip(after, before, strict=True)):
                break
            advance(10)
        check(
            f"arrow trap: crossing the wire fires every dispenser ({before} -> {after})",
            all(n < m for n, m in zip(after, before, strict=True)),
        )
    finally:
        untrip()
        clear(V(ax1 - 3, ay - 2, zd - 4), V(ax2 + 3, ay + 4, zw + 16))
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
    hx, hz = SMITHY_HATCH
    check(
        "smithy: trapdoor over a ladder to the lower treasury",
        is_block(V(hx, -1, hz), "minecraft:spruce_trapdoor")
        and all(is_block(V(hx, y, hz), "minecraft:ladder") for y in range(-14, -1))
        and is_block(V(hx, -15, hz), L.AIR),
    )


def engine() -> None:
    cx, cz, ey = ENGINE
    ring = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
    lamp = V(cx, ey, cz - 3)
    lamps, patterns = [], []
    # hoppers move items every 8 ticks: sample at 5 and 7 ticks alternately,
    # so that the samples do not fall into step with the lamp
    for i in range(32):
        L.tick(5 if i % 2 else 7)
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


# the edge of its block that a closed door's or an open trapdoor's panel
# lies against, by its facing: the edge opposite the facing
PANEL_EDGE = {"north": "south", "south": "north", "east": "west", "west": "east"}


def facing_of(p: Vec3, block: str, state: str) -> str:
    """the facing of the block at p if it is ``block[state]``, else empty"""
    for f in PANEL_EDGE:
        if is_block(p, f"{block}[{state},facing={f}]"):
            return f
    return ""


def cells() -> None:
    """every dungeon cell: the door's closed panel and the grille's open
    trapdoor panels on the same (corridor) edge of the front, buttons on
    both sides attached to the frame, and power at the frame opens the door"""
    y = DUNGEON_Y
    for zc, zdoor, into, xs in CELL_ROWS:
        for x in xs:
            c_ = L.cell_cells(*V(x, y, zc), zdoor + ORIGIN.z, into)
            door, grille, frame = c_["door"], c_["grille"], c_["frame"]
            name = f"cell {x},{zc}"
            # the panels' edges, read from the blocks' own state
            edges = {
                PANEL_EDGE.get(facing_of(p, "minecraft:iron_door", "open=false"), "-")
                for p in door
            } | {
                PANEL_EDGE.get(
                    facing_of(p, "minecraft:iron_trapdoor", "open=true"), "-"
                )
                for p in grille
            }
            check(
                f"{name}: closed iron door flush with the open trapdoor grille, both on the {c_['corridor']} edge (found {sorted(edges)})",
                edges == {c_["corridor"]}
                and all(p.z == door[0].z for p in grille + frame),
            )
            check(
                f"{name}: a button on each side, attached to the solid frame",
                all(
                    is_block(p, f"minecraft:stone_button[face=wall,facing={f}]")
                    and is_block(s_, L.BRICK)
                    for p, f, s_ in c_["buttons"]
                ),
            )
            try:
                # press: the frame the buttons power becomes a power source
                c(
                    f"setblock {frame[1].x} {frame[1].y} {frame[1].z} minecraft:redstone_block"
                )
                advance(10)
                check(
                    f"{name}: power at the frame opens both halves of the door",
                    all(is_block(p, "minecraft:iron_door[open=true]") for p in door),
                )
            finally:
                c(f"setblock {frame[1].x} {frame[1].y} {frame[1].z} {L.BRICK}")
                for p, f, _ in c_["buttons"]:  # the frame's change knocked them off
                    c(
                        f"setblock {p.x} {p.y} {p.z} minecraft:stone_button[face=wall,facing={f}]"
                    )
                advance(10)
            check(
                f"{name}: closes again, the grille still open",
                all(is_block(p, "minecraft:iron_door[open=false]") for p in door)
                and all(
                    is_block(p, "minecraft:iron_trapdoor[open=true]") for p in grille
                ),
            )


def mounts() -> None:
    """every wall-mounted block the build places that a player can reach is
    on a solid block: levers, buttons, torches, the gate's banners"""
    cx1, cz1, cx2, cz2 = CHAPEL
    bx1, bz1 = cx1 - 2, cz2 - 1
    gx1, gz1, gx2, gz2 = GATEHOUSE
    up = Vec3(0, 1, 0)
    pairs: list[tuple[Vec3, str, Vec3]] = []  # (block, what, its support)
    for base, lever_b in ((V(*CELL_DOOR), CELL_LEVER), (V(*CRYPT_DOOR), -1)):
        d = L.hidden_door_cells(base, Wd, S, trigger="lever", lever_b=lever_b)
        pairs.append((d["trigger"], "minecraft:lever", d["trigger"] + Wd))
        pairs.append(
            (
                base + Wd + up + S * 2,
                "minecraft:redstone_wall_torch",
                base + Wd * 2 + up + S * 2,
            )
        )
    lib = L.hidden_door_cells(V(*LIBRARY_DOOR), E, S)
    pairs.append((lib["trigger"], "minecraft:chiseled_bookshelf", lib["trigger"] - up))
    pairs.append(
        (
            V(*LIBRARY_DOOR) + E + up + S * 2,
            "minecraft:redstone_wall_torch",
            V(*LIBRARY_DOOR) + E * 2 + up + S * 2,
        )
    )
    tx = WELL_TUNNEL_X
    for z in (VAULT[3], VAULT[3] + 2):
        pairs.append(
            (
                V(tx + 1, VAULT_Y + 1, z),
                "minecraft:stone_button",
                V(tx + 1, VAULT_Y + 1, VAULT[3] + 1),
            )
        )
    for k in (4, 11, 18):
        pairs.append(
            (
                V(bx1 + 5, YU + k, bz1 + 3),
                "minecraft:wall_torch",
                V(bx1 + 6, YU + k, bz1 + 3),
            )
        )
    for x in (XG - GATE_BANNER_DX, XG + GATE_BANNER_DX):
        pairs.append((V(x, 5, gz2 + 1), "#minecraft:banners", V(x, 5, gz2)))
    bad = [
        (p.x, p.y, p.z, what)
        for p, what, s_ in pairs
        if not is_block(p, what) or is_block(s_, L.AIR) or is_block(s_, L.BARS)
    ]
    check(
        f"mounts: levers, buttons, torches and banners are on solid blocks{' (not ' + str(bad[:4]) + ')' if bad else ''}",
        not bad,
    )


def banners() -> None:
    """each roofed tower's banner hangs beside the top of its cone, in the
    open, on the step it is attached to"""
    bad = []
    for cx, cz, r, y_top in ROOFED_TOWERS:
        o = V(cx, y_top, cz)
        p = L.cone_banner(o.x, o.z, r, o.y)
        if not (
            is_block(p, "#minecraft:banners")
            and not is_block(Vec3(p.x - 1, p.y, p.z), L.AIR)
            and is_block(p + Vec3(1, 0, 0), L.AIR)
            and is_block(p - Vec3(0, 1, 0), L.AIR)  # where its cloth hangs
        ):
            bad.append((p.x, p.y, p.z))
    check(
        f"towers: every cone's banner hangs beside its top{' (not ' + str(bad) + ')' if bad else ''}",
        not bad,
    )


def walk_step(x: int, walk: int, z: int) -> bool:
    """somewhere to stand at a wall walk's level: solid under, air for feet and head"""
    return not is_block(V(x, walk - 1, z), L.AIR) and all(
        is_block(V(x, walk + k, z), L.AIR) for k in (0, 1)
    )


def bailey() -> None:
    """the layout keeps clear of the round towers, the mid-wall towers
    (which buildings and stairs once cut) stand whole, every wall stair
    reaches its walk, and every standing sign stands on something"""
    problems = layout_problems()
    check(
        f"layout: no building, stair, path or sign in a round tower or another building{' (' + '; '.join(problems[:3]) + ')' if problems else ''}",
        not problems,
    )
    bad = []
    for name in ("west mid-wall tower", "east mid-wall tower"):
        cx, cz, r = BAILEY_TOWERS[name]
        # the pillar, and the north and south walls below the wall-walk doors
        for x, z in (
            (cx, cz),
            (cx, cz - r),
            (cx, cz - r + 1),
            (cx, cz + r),
            (cx, cz + r - 1),
        ):
            bad += [
                (name, x, y, z) for y in range(0, WALL_H) if is_block(V(x, y, z), L.AIR)
            ]
    check(
        f"towers: the mid-wall towers' pillars and north and south walls are whole{' (not ' + str(bad[:3]) + ')' if bad else ''}",
        not bad,
    )
    # every wall stair: its top steps at the walk's level with headroom, and
    # along one row (the one on the curtain's inner edge) the walk goes on
    for name, (points, width, walk) in WALL_STAIRS.items():
        (ax, _, az), (bx, _, bz) = points[-2], points[-1]
        dx, dz = (bx > ax) - (bx < ax), (bz > az) - (bz < az)
        tops = [
            (bx - dz * o, bz + dx * o)
            for o in range(-((width - 1) // 2), width // 2 + 1)
        ]

        top_ok = all(walk_step(x, walk, z) for x, z in tops)
        walk_on = any(walk_step(x + dx, walk, z + dz) for x, z in tops)
        check(
            f"{name}: top step at the walk (y {ORIGIN.y + walk}) with headroom ({top_ok}), and the walk goes on beyond it ({walk_on})",
            top_ok and walk_on,
        )
    floating = []
    for first, (x, y, z, _r) in STANDING_SIGNS.items():
        p = V(x, y, z)
        under = p - Vec3(0, 1, 0)
        if not is_block(p, "#minecraft:standing_signs") or any(
            is_block(under, b) for b in (L.AIR, L.WATER, "#minecraft:replaceable")
        ):
            floating.append(first)
    check(
        f"signs: every standing sign stands on a solid block{' (not ' + str(floating) + ')' if floating else ''}",
        not floating,
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


def top_is(x: int, z: int, block: str) -> bool:
    """is the top block of this column ``block``?"""
    r = c(
        f"execute positioned {x} 0 {z} positioned over motion_blocking_no_leaves "
        f"if block ~ ~-1 ~ {block}"
    )
    return "Test passed" in r


def road_block(x: int, z: int, d: Vec3) -> bool:
    """is this centre cell of a leg running in direction ``d`` the road's
    path? Cobble is allowed only where another road crosses or ends: then
    the cells two to the side, beyond this road's own edges, are road too"""
    if top_is(x, z, "minecraft:dirt_path"):
        return True
    px, pz = -int(d.z), int(d.x)
    return top_is(x, z, "minecraft:cobblestone") and any(  # any: a road may end here
        top_is(x + s * 2 * px, z + s * 2 * pz, "minecraft:dirt_path")
        or top_is(x + s * 2 * px, z + s * 2 * pz, "minecraft:cobblestone")
        for s in (1, -1)
    )


def road_start() -> Vec3 | None:
    """where the road leaves the stair at the foot of the bridge: the first
    path block south of the bridge (the ground there is the stair now, so
    the build's reading cannot be repeated)"""
    foot = build_outer.bridge_foot()
    for dz in range(1, build_outer.MAX_STAIR + 3):
        p = Vec3(foot.x, 0, foot.z + dz)
        if "Test passed" in c(
            f"execute positioned {p.x} 0 {p.z} positioned over motion_blocking_no_leaves "
            "if block ~ ~-1 ~ minecraft:dirt_path"
        ):
            return p
    return None


def road() -> None:
    start = road_start()
    check("road: a path leaves the stair at the foot of the bridge", start is not None)
    if start is None:
        return
    points = build_outer.road_points(start)
    gaps = []
    for a, b in zip(points, points[1:], strict=False):
        d, _, length = build_outer.leg_of(a, b)
        for k in range(length + 1):
            p = a + d * k
            if not road_block(int(p.x), int(p.z), d):
                gaps.append((int(p.x), int(p.z)))
    check(
        f"road: dirt path all the way from the castle to spawn {tuple(SPAWN)}"
        + (f" ({len(gaps)} gaps, first at {gaps[:6]})" if gaps else ""),
        not gaps,
    )
    p, _ = build_outer.signpost_position(points, build_outer.other_sign_at)
    y = ground_height(p.x, p.z) + 1
    text = c(f"data get block {p.x} {y} {p.z} front_text.messages")
    check(
        f"road: signpost at ({p.x}, {y}, {p.z}) names Castle {NAME}",
        is_block(Vec3(p.x, y, p.z), "#minecraft:all_signs") and NAME in text,
    )
    # every lamp post is one post: a lantern on exactly POST_HEIGHT fence
    # blocks, nothing on it and no post under it (or no post at all, where
    # another road was in the way)
    h = build_outer.POST_HEIGHT
    bad = []
    for q in build_outer.lamp_post_cells(points):
        top = ground_height(q.x, q.z)
        if not is_block(Vec3(q.x, top, q.z), L.LANTERN):
            continue
        fences = all(
            is_block(Vec3(q.x, top - k, q.z), "minecraft:dark_oak_fence")
            for k in range(1, h + 1)
        )
        below = Vec3(q.x, top - h - 1, q.z)
        if (
            not fences
            or is_block(below, "minecraft:dark_oak_fence")
            or is_block(below, L.LANTERN)
        ):
            bad.append((q.x, top, q.z))
    check(
        f"road: every lamp post is a single post{' (not ' + str(bad[:6]) + ')' if bad else ''}",
        not bad,
    )
    # and nothing post-shaped (a lantern over fences) within 4 blocks of the
    # road that is not one of them: a stray from an older route. Another
    # castle's road may share a leg, and its posts stand in the same lane
    # (3 to the side) at its own spacing: those are allowed if they are
    # single posts; anything post-shaped out of the lane is a stray
    wanted = {(q.x, q.z) for q in build_outer.lamp_post_cells(points)}
    strays = []
    for a, b in zip(points, points[1:], strict=False):
        d, right, length = build_outer.leg_of(a, b)
        for k in range(length + 1):
            for o in range(-4, 5):
                q = a + d * k + right * o
                x, z = int(q.x), int(q.z)
                if (x, z) in wanted or not top_is(x, z, L.LANTERN):
                    continue
                top = ground_height(x, z)
                if not is_block(Vec3(x, top - 1, z), "minecraft:dark_oak_fence"):
                    continue
                single = all(
                    is_block(Vec3(x, top - j, z), "minecraft:dark_oak_fence")
                    for j in range(1, h + 1)
                ) and not any(
                    is_block(Vec3(x, top - h - 1, z), blk)
                    for blk in ("minecraft:dark_oak_fence", L.LANTERN)
                )
                if o != 3 or not single:
                    strays.append((x, top, z))
    check(
        f"road: no stray posts within 4 blocks of it{' (found ' + str(strays[:6]) + ')' if strays else ''}",
        not strays,
    )


def entities() -> None:
    a, b = site_box()
    box = L.box_selector(a, b)
    for kind, n in ENTITIES.items():
        tagged = count(f"type=minecraft:{kind},tag={TAG}")
        strays = count(f"type=minecraft:{kind},tag=!{TAG},{box}")
        check(
            f"entities: {n} {kind} tagged {TAG} (found {tagged}), none untagged in the site (found {strays})",
            tagged == n and strays == 0,
        )


def main() -> None:
    a, b = site_box()
    near = L.players_near(a, b, 200)
    if near and not os.environ.get("FORCE"):
        raise SystemExit(
            f"{', '.join(near)} within 200 blocks of the site: not verifying"
        )
    build_outer.forceload(True)
    try:
        print(f"killed {L.kill_hostiles(*site_box())} hostile mobs in the site")
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
        lever_door("cell block", V(*CELL_DOOR), CELL_LEVER, L.BRICK)
        lever_door("crypt", V(*CRYPT_DOOR), -1, L.DARK_BRICK)
        traps()
        passages()
        engine()
        places()
        cells()
        mounts()
        banners()
        bailey()
        road()
        entities()
    finally:
        c("kill @e[tag=castle_verify]")
        build_outer.forceload(False)
    print(f"{sum(results)}/{len(results)} checks passed")
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
