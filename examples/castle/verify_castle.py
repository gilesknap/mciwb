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
import reach  # noqa: E402
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
    SEATS,
    SMITHY_HATCH,
    SPAWN,
    STANDING_SIGNS,
    STEPS,
    SUMMONED,
    TAG,
    TELEPORTS,
    TOWER_DOORS,
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
    seat_facing,
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


def pull_gate_lever(g: dict, on: bool) -> None:
    """set a portcullis's lever, then change its wall block (to stone and
    back): a lever set by command updates only its own neighbours, and the
    torch on the wall block above it needs the update a player's pull gives"""
    set_lever(g["lever"], g["lever_facing"], "wall", on)
    b = g["lever_block"]
    c(f"setblock {b.x} {b.y} {b.z} {L.STONE}")
    c(f"setblock {b.x} {b.y} {b.z} {L.BRICK}")


# blocks that redstone power changes: nothing of these may touch a lever
# or its block except what it is meant to drive
POWERED_KINDS = (
    "minecraft:redstone_wire",
    "minecraft:repeater",
    "minecraft:comparator",
    "#minecraft:redstone_ores",
    "minecraft:piston",
    "minecraft:sticky_piston",
    "minecraft:redstone_lamp",
    "minecraft:dispenser",
    "minecraft:dropper",
    "minecraft:note_block",
    "#minecraft:doors",
    "#minecraft:trapdoors",
    "#minecraft:fence_gates",
    "minecraft:redstone_torch",
    "minecraft:redstone_wall_torch",
    "minecraft:hopper",
)

NEIGHBOURS = [Vec3(1, 0, 0), Vec3(-1, 0, 0), Vec3(0, 1, 0), Vec3(0, -1, 0), S, S * -1]


def powered_neighbours(p: Vec3, allowed: list[Vec3]) -> list[tuple[int, int, int]]:
    """the redstone-driven blocks next to p, other than ``allowed``"""
    found = []
    for d in NEIGHBOURS:
        q = p + d
        if q in allowed:
            continue
        if any(is_block(q, k) for k in POWERED_KINDS):
            found.append((q.x, q.y, q.z))
    return found


def portcullis(name: str, gate: tuple[int, int, int, int, int]) -> None:
    g = L.portcullis_cells(*build_outer.portcullis_args(gate))
    lever, cells = g["lever"], g["closed_cells"]
    pistons = g["ceiling_pistons"] + g["floor_pistons"]
    torch1, torch2 = g["torches"]
    check(f"{name}: lever present", is_block(lever, "minecraft:lever"))
    # the lever is in the passage beside the bars, where its puller sees them
    beside = [q for q in cells if q.y == lever.y and abs(q.z - lever.z) == 1]
    check(
        f"{name}: lever at {tuple(lever)} in the passage, next to the bars at {[tuple(q) for q in beside]}",
        bool(beside)
        and all(is_block(lever + Vec3(0, dy, 0) + Wd, L.AIR) for dy in (-1, 0)),
    )
    # it drives only the first torch (on its block); the torches drive only
    # the next torch and the winch line
    bad = powered_neighbours(lever, [g["lever_block"]])
    bad += powered_neighbours(g["lever_block"], [lever, torch1])
    bad += powered_neighbours(torch1, [g["lever_block"]])
    bad += powered_neighbours(
        torch2, [torch2 + S * (-1 if torch2.z > cells[0].z else 1)]
    )
    check(
        f"{name}: the lever and its torches touch nothing else redstone drives{' (' + str(bad) + ')' if bad else ''}",
        not bad,
    )
    was_on = is_block(lever, "minecraft:lever[powered=true]")
    barred = all(is_block(p, L.BARS) for p in cells)
    open_ = all(is_block(p, L.AIR) for p in cells)
    state = "closed" if barred else "open" if open_ else "half way"
    check(
        f"{name}: found {state}, lever {'on' if was_on else 'off'} (a visitor may leave it closed)",
        (barred and was_on) or (open_ and not was_on),
    )
    try:
        pull_gate_lever(g, True)
        advance()
        check(
            f"{name}: lever on closes it (6 pistons, 6 cells barred)",
            all(is_block(p, "minecraft:sticky_piston[extended=true]") for p in pistons)
            and all(is_block(p, L.BARS) for p in cells),
        )
        pull_gate_lever(g, False)
        advance()
        check(
            f"{name}: lever off opens it",
            all(is_block(p, "minecraft:sticky_piston[extended=false]") for p in pistons)
            and all(is_block(p, L.AIR) for p in cells),
        )
    finally:
        if was_on:  # leave it as found
            pull_gate_lever(g, True)
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


def stand_y() -> float | None:
    """the height of the checks' armour stand"""
    m = re.search(
        r"\[[-\d.]+d, (-?[\d.]+)d, ",
        c("data get entity @e[tag=castle_verify,limit=1] Pos"),
    )
    return float(m.group(1)) if m else None


def traps() -> None:
    px, py, pz, depth = PIT_TRAP
    t = L.pit_trap_cells(*V(px, py, pz), depth)
    wire, doors = t["wire"], t["trapdoors"]
    clear(V(px - 3, py - depth - 1, pz - 10), V(px + 3, py + 3, pz + 10))
    advance()
    check(
        "pit trap: tripwire present and not already tripped",
        is_block(wire, "minecraft:tripwire[powered=false]"),
    )
    check(
        "pit trap: trapdoors start closed",
        all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
    )
    # a walker is on the string for a moment only: they must be wholly over
    # the opening by the time they step off it, from either side
    reach = 0.0
    for travel, way in ((1, "south"), (-1, "north")):
        r, on = L.pit_timing(wire.z, [d.z for d in doors], travel)
        reach = max(reach, r)
        check(
            f"pit trap: walking {way}, wholly over the opening {r:.1f} ticks after touching the wire, while still on the string ({on:.1f} ticks)",
            r <= on,
        )
    centre = wire + Vec3(0.5, 0, 0.5)
    try:
        # the walker: on the string until the floor opens, then moved on
        # along the corridor at once (as if stepping off); the floor must
        # still be open when they would be wholly over it
        c(
            f"summon minecraft:armor_stand {centre.x} {centre.y} {centre.z} "
            '{Tags:["castle_verify"],Invulnerable:1b}'
        )
        opened = L.wait_until(
            lambda: all(
                is_block(p, "minecraft:iron_trapdoor[open=true]") for p in doors
            ),
            20,
        )
        c(f"tp @e[tag=castle_verify] {centre.x} {centre.y} {centre.z + 3}")
        if reach > 0:
            L.tick(int(reach + 0.5))
        check(
            f"pit trap: the wire opens the floor ({opened}), still open after the walker has stepped off",
            opened
            and all(is_block(p, "minecraft:iron_trapdoor[open=true]") for p in doors),
        )
        untrip()
        check(
            "pit trap: shuts again by itself",
            all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
        )
        # the victim: on the wire, and down the shaft into the oubliette
        c(
            f"summon minecraft:armor_stand {centre.x} {centre.y} {centre.z} "
            '{Tags:["castle_verify"],Invulnerable:1b}'
        )
        opened = L.wait_until(
            lambda: all(
                is_block(p, "minecraft:iron_trapdoor[open=true]") for p in doors
            ),
            20,
        )
        advance()
        y = stand_y()
        check(
            f"pit trap: whoever is on the wire falls into the oubliette (the floor opens: {opened}; landed at y {y}, the bottom is {t['bottom']})",
            opened and y is not None and y < t["bottom"] + 1,
        )
        check(
            "pit trap: the shaft drops into the oubliette",
            all(is_block(p, L.AIR) for p in t["shaft"]),
        )
        check(
            "pit trap: and shuts again over them",
            all(is_block(p, "minecraft:iron_trapdoor[open=false]") for p in doors),
        )
    finally:
        untrip()

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
    for gate in (MAIN_GATE, MIDDLE_GATE):
        g = L.portcullis_cells(*build_outer.portcullis_args(gate))
        pairs.append((g["lever"], "minecraft:lever", g["lever_block"]))
        for t in g["torches"]:
            pairs.append((t, "minecraft:redstone_torch", t - up))
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


def seats() -> None:
    """every seat's stair has its back behind its sitter (a stair faces
    its tall back), and every dais step faces the way up"""
    for kind, table, facing in (
        ("seat", SEATS, seat_facing),
        ("step", STEPS, lambda up: up),
    ):
        for name, rects in table.items():
            bad = []
            for x1, z1, x2, z2, y, way in rects:
                want = facing(way)
                for x in range(x1, x2 + 1):
                    for z in range(z1, z2 + 1):
                        p = V(x, y, z)
                        if not is_block(
                            p, f"#minecraft:stairs[facing={want},half=bottom]"
                        ):
                            bad.append((p.x, p.y, p.z))
            what = "sitters face" if kind == "seat" else "the way up is"
            check(
                f"{kind}s: {name} ({what} {', '.join(sorted({r[5] for r in rects}))}){' (wrong at ' + str(bad[:4]) + ')' if bad else ''}",
                not bad,
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
    for name in (n for n in BAILEY_TOWERS if "mid-wall" in n):
        cx, cz, r = BAILEY_TOWERS[name]
        # the pillar, and the north and south walls beside the wall-walk doors
        for x, z in ((cx, cz), (cx, cz - r), (cx, cz + r)):
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


# how verify reads a block's class (reach.kind) over RCON: the first test
# that passes; anything else is solid
_KIND_TESTS = [
    ("minecraft:air", reach.OPEN),
    ("minecraft:cave_air", reach.OPEN),
    ("#minecraft:planks", reach.SOLID),
    ("#minecraft:stone_bricks", reach.SOLID),
    ("#minecraft:doors", reach.DOOR),
    ("#minecraft:fence_gates", reach.DOOR),
    ("minecraft:iron_trapdoor[open=true]", reach.BLOCK),
    ("minecraft:iron_trapdoor", reach.SOLID),
    ("#minecraft:trapdoors", reach.HATCH),
    ("#minecraft:climbable", reach.CLIMB),
    ("minecraft:water", reach.SWIM),
    ("minecraft:bubble_column", reach.SWIM),
    ("#minecraft:fences", reach.BLOCK),
    ("#minecraft:walls", reach.BLOCK),
    ("minecraft:lava", reach.BLOCK),
    ("minecraft:iron_bars", reach.PANE),
    ("minecraft:iron_chain", reach.PANE),
    ("minecraft:glass_pane", reach.PANE),
    ("#minecraft:replaceable", reach.OPEN),
    ("#minecraft:wool_carpets", reach.OPEN),
    ("#minecraft:all_signs", reach.OPEN),
    ("#minecraft:banners", reach.OPEN),
    ("#minecraft:buttons", reach.OPEN),
    ("#minecraft:candles", reach.OPEN),
    *(
        (f"minecraft:{b}", reach.OPEN)
        for b in (
            "lantern", "soul_lantern", "redstone_wire", "lever", "torch",
            "wall_torch", "redstone_torch", "redstone_wall_torch", "repeater",
            "comparator", "tripwire", "tripwire_hook", "cobweb",
        )
    ),
]  # fmt: skip
_kinds: dict[tuple[int, int, int], int] = {}


def rcon_kind(p: Vec3) -> int:
    """the class (reach.kind) of the block at p, read over RCON"""
    key = (int(p.x), int(p.y), int(p.z))
    if key not in _kinds:
        _kinds[key] = next(
            (k for test, k in _KIND_TESTS if is_block(p, test)), reach.SOLID
        )
    return _kinds[key]


POS = re.compile(r"\[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]")
FACING = {
    0: Vec3(0, -1, 0),
    1: Vec3(0, 1, 0),
    2: Vec3(0, 0, -1),
    3: Vec3(0, 0, 1),
    4: Vec3(-1, 0, 0),
    5: Vec3(1, 0, 0),
}


def summoned_clear(kind_at) -> None:
    """no armour stand stands in a block (a chest, a wall ...) and every
    item frame hangs in an open cell on a solid block"""
    from math import floor

    bad = []
    stands = c(
        # (not markers: an invisible marker stand that a sitter rides sits
        # in its seat, castle2's do)
        f"execute as @e[type=minecraft:armor_stand,tag={TAG},nbt=!{{Marker:1b}}] "
        "run data get entity @s Pos"
    )
    n_stands = 0
    for m in POS.finditer(stands):
        n_stands += 1
        x, y, z = (float(v) for v in m.groups())
        cells = {
            Vec3(floor(x + dx), floor(y + dy), floor(z + dz))
            for dx in (-0.25, 0.25)
            for dz in (-0.25, 0.25)
            for dy in (0.1, 1.0, 1.9)
        }
        if any(kind_at(q) not in reach.PASS for q in cells):
            bad.append(("armour stand", round(x, 1), round(y, 1), round(z, 1)))
    frames = c(
        f"execute as @e[type=minecraft:item_frame,tag={TAG}] run data get entity @s Pos"
    )
    n_frames = 0
    for m in POS.finditer(frames):
        n_frames += 1
        x, y, z = (float(v) for v in m.groups())
        r = c(
            f"data get entity @e[type=minecraft:item_frame,tag={TAG},"
            f"x={x},y={y},z={z},distance=..0.2,limit=1] Facing"
        )
        f = re.search(r"(\d)b", r)
        own = Vec3(floor(x), floor(y), floor(z))
        on = own - FACING[int(f.group(1))] if f else None
        if on is None or kind_at(own) not in reach.PASS or kind_at(on) in reach.PASS:
            bad.append(("item frame", round(x, 1), round(y, 1), round(z, 1)))
    check(
        f"entities: none of the {n_stands} armour stands is in a block, and the {n_frames} item frames hang in the open on solid blocks{' (not ' + str(bad[:6]) + ')' if bad else ''}",
        not bad and n_stands > 0 and n_frames > 0,
    )


def towers(kind_at, describe=None) -> None:
    """every round tower's doorway opens onto somewhere to stand at its
    level on both sides"""
    for name, (_cx, _cz, _r, _wall, doors) in TOWER_DOORS.items():
        bad = [
            b
            for b in reach.door_problems(kind_at, describe)
            if b.startswith(name + ",")
        ]
        check(
            f"towers: the {name}'s {len(doors)} doors open onto floors at their levels on both sides{' (' + '; '.join(bad) + ')' if bad else ''}",
            not bad,
        )


def reachable(g: reach.Grid) -> None:
    """a visitor can walk from the bridge to every room (the secret doors
    opened)"""
    problems = reach.problems(g)
    for line in problems:
        check(f"reach: {line}", False)
    n = len(reach.spaces())
    check(
        f"reach: {n - len(problems)} of the {n} rooms and spaces can be walked to from the gate",
        not problems,
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
        checks()
    finally:
        c("kill @e[tag=castle_verify]")
        build_outer.forceload(False)
    print(f"{sum(results)}/{len(results)} checks passed")
    if not all(results):
        raise SystemExit(1)


def checks() -> None:
    """every check, with the site loaded (castle2's verify runs these too)"""
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
        all(is_block(V(XG, -1, z), L.PLANKS) for z in range(ZS + 1, BRIDGE_END + 1)),
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
    seats()
    banners()
    bailey()
    road()
    entities()
    world_folder = os.environ.get("WORLD_FOLDER")
    if world_folder:
        # read the site from the world files (RCON is too slow for a
        # flood fill over it): doors and reachability
        c("save-all flush")
        g = reach.load_world(world_folder)
        summoned_clear(reach.grid_kind(g))
        towers(reach.grid_kind(g), g.name)
        reachable(g)
    else:
        summoned_clear(rcon_kind)
        towers(rcon_kind)
        print(
            "INFO reach: not checked (set WORLD_FOLDER to the server's world "
            "folder to walk the castle from its files)"
        )


if __name__ == "__main__":
    main()
