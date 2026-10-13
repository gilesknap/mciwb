"""
Verify Castle 2 over RCON, without a player::

    mciwb run verify_castle2.py

Runs all of castle's checks (``verify_castle.checks``, see castle's README)
on castle2's layout, then castle2's own:

- every seat (``castle_lib.seat``, and the houses' seats) faces the way its
  sitter looks, read back from the block's state, with its back to no table
  and something to look at straight ahead over open floor (air or carpet):
  a table right in front, a lectern or an altar within 2, a hearth within
  3; a pew instead looks at its room's focus (the chapel's altar) ahead of
  it, within 24 (``FOCUS``, ``seat_targets``);
- rooms: the key pieces of castle2's rooms (``rooms.KEYS``: the kitchen's
  hearth, spit, oven, pantry and lanterns, the beds, the wardrobes, the
  effigies on the tombs, the straw dummies ...) are in place, and their
  entities (the hams, the effigies' swords, the armour-stand dummies) are
  all there;
- every house has its door, clear floor either side of it, and its stands
  (counter, bedside, hearth) free, and every step of its stairs (or rung of
  its ladder) in place with the headroom a player needs to climb it;
- every pen's fence ring is whole with its gate closed, and its animals are
  all inside it. (castle's entity check counts every animal and item frame
  the stages summoned, castle2's included.)

- every static person is at their spot, and every villager is inside the
  castle's walls (stray cats and iron golems, which villages bring, are
  removed first).

- every bee hive's tagged bees, in the hive or out of it;
- gate: the main gate's fence gates (main_gate) closed and walled either
  side, so the villagers stay in, with room to open them from both sides;
  the well's gate closed;
- reach: over RCON (castle's flood fill needs the world files), the places
  visitors got stuck: the well's bubble column comes up beside its gate
  onto the bailey, and every tower's stair or ladder (and the keep's) comes
  out on its top floor with headroom;
- strays: the untagged golems, cats, bees, villagers and wild animals of
  the pens' kinds in the site, listed with where they are, before they are
  removed (an untagged villager inside the walls fails it);
- bailey_machines: the clock tower rings at dusk and dawn and lights its
  lamps at night, a bullseye opens the archery cache and an outer ring does
  not, the mill's wheel turns and its lever opens the way down to the
  tunnel, the listening door opens to a bell and not to an arrow; each
  trigger is one a player in adventure mode may use.

``CHECKS=seats,pens`` runs only some of them (strays, castle, seats,
signs, rooms, houses, pens, people, gate, reach, bailey_machines).
Refuses to run while a player is within 200 blocks of the site, unless
FORCE=1. Exits non-zero if any check fails.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle2_layout  # noqa: E402, F401, I001  (first: it sets up castle's layout)
import build_castle2  # noqa: E402, F401  (adds castle2's stages to castle's)
import build_castle  # noqa: E402
import build_outer  # noqa: E402
import castle_lib as L  # noqa: E402
import reach as R  # noqa: E402  (castle's)
import verify_castle as VC  # noqa: E402
from fake_client import dry_run  # noqa: E402

import numpy as np  # noqa: E402

from castle2_layout import TAG, TOWER_LEVELS, V  # noqa: E402

from mciwb.imports import Vec3  # noqa: E402

check, is_block = VC.check, L.is_block
STEP = {
    "north": Vec3(0, 0, -1),
    "south": Vec3(0, 0, 1),
    "east": Vec3(1, 0, 0),
    "west": Vec3(-1, 0, 0),
}
# what a seat looks at, and how far off it may be over open floor (air or
# carpet): a table or a desk right in front (a house's seats too), a
# lectern or an altar close by, a hearth across the hearthstone
FOCUS = (
    ("#minecraft:slabs[type=top]", 1),  # a table
    ("minecraft:lectern", 2),
    ("minecraft:chiseled_quartz_block", 2),  # an altar
    ("#minecraft:campfires", 3),  # a fire in a fireplace
)
TABLES = ("#minecraft:slabs[type=top]",)


def seat_targets() -> list[tuple[str, tuple[int, int, int, int, int], Vec3, int]]:
    """the seats that look at a room's focus further off, over other seats
    (pews): (room, (x1, z1, x2, z2, y) of its seats, the focus block,
    its reach), local coordinates in, the focus in world coordinates"""
    from castle_layout import CHAPEL, YU

    x1, z1, x2, z2 = CHAPEL
    y = YU
    return [("chapel's altar", (x1, z1, x2, z2, y), V(98, y + 1, z1 + 2), 24)]


_seat_cells: list[tuple[Vec3, str]] = []
_dry: list = []


def dry_build():
    """castle2's whole build (but its earthworks) run against a fake client,
    once: what it places (``.world``), and the seats (`castle_lib.PLACED_SEATS`)
    and the rooms' key pieces (`rooms.KEYS`) it records on the way"""
    if not _dry:
        import rooms

        L.PLACED_SEATS.clear()
        rooms.KEYS.clear()
        rooms.KEY_ENTITIES.clear()
        stages = [f for name, f in build_castle.STAGES.items() if name != "earthworks"]
        _dry.append(dry_run(*stages, box=castle2_layout.site_box()))
    return _dry[0]


def seat_cells() -> list[tuple[Vec3, str]]:
    """every seat cell the build places and keeps (a later block may
    replace one), and the way its sitter looks: learnt by running the
    build's stages against a fake client (once)"""
    if not _seat_cells:
        _seat_cells.extend(_learn_seats())
    return _seat_cells


def _learn_seats() -> list[tuple[Vec3, str]]:
    rec = dry_build()
    cells = []
    for a, b, faces in L.PLACED_SEATS:
        (ax, ay, az), (bx, by, bz) = (int(v) for v in a), (int(v) for v in b)
        for x in range(min(ax, bx), max(ax, bx) + 1):
            for y in range(min(ay, by), max(ay, by) + 1):
                for z in range(min(az, bz), max(az, bz) + 1):
                    p = Vec3(x, y, z)
                    if "_stairs" in rec.world.at(p):
                        cells.append((p, faces))
    for h in castle2_layout.village_houses().values():
        cells += h.seats
    return cells


def seat_problem(p: Vec3, faces: str) -> str:
    """what is wrong with the seat at p, or empty: its stair must have its
    back behind the sitter, no table behind it, and in front either a
    `FOCUS` within its reach over open floor, or (a pew) its room's focus
    (`seat_targets`) ahead of it"""
    back = castle2_layout.OPPOSITE[faces]
    if not is_block(p, f"#minecraft:stairs[facing={back},half=bottom]"):
        return "not a stair with its back behind the sitter"
    d = STEP[faces]
    if any(is_block(p - d, t) for t in TABLES):
        return "its back to a table"
    o = V(0, 0, 0)
    for room, (x1, z1, x2, z2, y), focus, reach in seat_targets():
        if x1 <= p.x - o.x <= x2 and z1 <= p.z - o.z <= z2 and p.y - o.y == y:
            ahead = (focus.x - p.x) * d.x + (focus.z - p.z) * d.z
            aside = abs((focus.x - p.x) * d.z - (focus.z - p.z) * d.x)
            if not 1 <= ahead <= reach or aside > ahead + 2:
                return f"not looking at the {room}"
            if not any(is_block(focus, t) for t, _ in FOCUS):
                return f"no {room} at {tuple(focus)}"
            return ""
    for k in range(1, max(r for _, r in FOCUS) + 1):
        q = p + d * k
        if any(k <= reach and is_block(q, t) for t, reach in FOCUS):
            return ""
        if not (is_block(q, L.AIR) or is_block(q, "#minecraft:wool_carpets")):
            break
    return "no table, lectern, altar or hearth in front"


def seats() -> None:
    cells = seat_cells()
    # a seat that fails is read again: a reply can be lost to another RCON
    # client (gilesknap/mciwb#166, item 2)
    bad = [
        (p.x, p.y, p.z, faces, why)
        for p, faces in cells
        if seat_problem(p, faces) and (why := seat_problem(p, faces))
    ]
    check(
        f"seats: all {len(cells)} face their table, altar or hearth"
        + (f" (not {bad[:4]})" if bad else ""),
        bool(cells) and not bad,
    )


_SNBT_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'')


def snbt_strings(text: str) -> list[str]:
    """the quoted strings in SNBT text (a sign's messages), unescaped"""
    return [
        re.sub(r"\\(.)", r"\1", a if a or not b else b)
        for a, b in _SNBT_STRING.findall(text)
    ]


def placed_signs() -> list[tuple[Vec3, list[str]]]:
    """every sign the build places in the site, with its front lines as
    written: learnt from the dry build"""
    rec = dry_build()
    blocks = rec.world.blocks
    has_text = np.asarray(np.frompyfunc(lambda b: "front_text:" in b, 1, 1)(blocks))
    out = []
    for i, j, k in np.argwhere(has_text.astype(bool)):
        block = blocks[i, j, k]
        front = re.search(r"front_text:\{messages:\[(.*?)\]", block)
        if front:
            lo = rec.world.lo
            pos = Vec3(int(lo[0] + i), int(lo[1] + j), int(lo[2] + k))
            out.append((pos, snbt_strings(front.group(1))))
    return out


def signs() -> None:
    """every sign's front text, read back, is exactly the lines the build
    wrote: no quote marks shown (the pre-26 JSON-in-a-string form) and no
    sign of empty lines"""
    bad = []
    wanted = placed_signs()
    for p, lines in wanted:
        if not any(lines) or any('"' in line for line in lines):
            bad.append(f"{tuple(p)} written as {lines}")
            continue
        reply = VC.c(f"data get block {p.x} {p.y} {p.z} front_text.messages")
        found = snbt_strings(reply.split(":", 1)[-1])
        if found != lines:
            bad.append(f"{tuple(p)} reads {found}, not {lines}")
    check(
        f"signs: all {len(wanted)} read back exactly as written, no quotes shown"
        + (f" (not {bad[:4]})" if bad else ""),
        bool(wanted) and not bad,
    )


def rooms_check() -> None:
    """the rooms' key pieces (`rooms.KEYS`: the kitchen's hearth, spit, oven
    and pantry, the beds, the effigies, the dummies ...) are in place, read
    back from the world, and their entities (the hams, the effigies'
    swords, the armour-stand dummies) are all there"""
    import rooms

    rec = dry_build()
    bad = []
    keys = [
        (what, p, block.split("[")[0].split("{")[0])
        for what, p, block in rooms.KEYS
        if rec.world.at(p).split("[")[0] == block.split("[")[0].split("{")[0]
    ]
    for what, p, block in keys:
        if not (is_block(p, block) or is_block(p, block)):
            bad.append(f"{what} at {tuple(p)}")
    for what, kind, a, b in rooms.KEY_ENTITIES:
        lo = Vec3(min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))
        hi = Vec3(max(a.x, b.x), max(a.y, b.y), max(a.z, b.z))
        want = 0
        for command in rec.commands:
            words = command.split()
            if command.startswith(f"summon minecraft:{kind} ") and all(
                (lo.x, lo.y, lo.z)[i] <= float(words[2 + i]) < (hi.x, hi.y, hi.z)[i] + 1
                for i in range(3)
            ):
                want += 1
        found = VC.count(f"type=minecraft:{kind},tag={TAG},{L.box_selector(lo, hi)}")
        if not want or found != want:
            bad.append(f"{what}: {found} of {want} {kind}")
    check(
        f"rooms: all {len(keys)} key pieces and {len(rooms.KEY_ENTITIES)} groups of"
        " entities in place (hearth, oven, pantry, hams, beds, effigies, dummies)"
        + (f" (not {bad[:4]})" if bad else ""),
        bool(keys) and not bad,
    )


def free(p: Vec3) -> bool:
    """room to stand: feet and head free (air or carpet), something under"""
    up = Vec3(0, 1, 0)
    return all(
        is_block(q, L.AIR) or is_block(q, "#minecraft:wool_carpets")
        for q in (p, p + up)
    ) and not is_block(p - up, L.AIR)


def houses() -> None:
    """every house: its door, free floor in front of and behind it, and
    every stand (counter, bedside, hearth) free to stand on"""
    bad = []
    built = castle2_layout.village_houses()
    for name, h in built.items():
        inside = h.door - (h.outside - h.door)
        if not is_block(h.door, "#minecraft:doors"):
            bad.append(f"{name}: no door at {h.door}")
        for what, p in (("outside", h.outside), ("inside", inside), *h.stands.items()):
            if not (free(p) or free(p)):
                bad.append(f"{name}: {what} {tuple(p)} not free")
    check(
        f"village: {len(built)} houses, each with its door clear and its stands free"
        + (f" (not {bad[:4]})" if bad else ""),
        not bad,
    )
    # the stairs: every step (or rung) in place, and the cells a player
    # needs free to climb them (house.House.headroom: 3 over each step, 2 at
    # the top, the landings) free: only these cells are read
    bad, reads = [], 0
    for name, h in built.items():
        for p in h.steps:
            reads += 1
            if not (
                is_block(p, "#minecraft:stairs")
                or is_block(p, "minecraft:ladder")
                or is_block(p, "#minecraft:stairs")  # read again (#166)
            ):
                bad.append(f"{name}: no step at {tuple(p)}")
        for p in h.headroom:
            reads += 1
            if not (
                is_block(p, L.AIR)
                or is_block(p, "#minecraft:wool_carpets")
                or is_block(p, L.AIR)
            ):
                bad.append(f"{name}: no headroom at {tuple(p)}")
    check(
        f"village: every house's stairs climbable ({reads} cells read)"
        + (f" (not {bad[:4]})" if bad else ""),
        not bad,
    )


def pens() -> None:
    """every pen: its fence ring whole (fences, a closed gate) and its
    animals inside it"""
    import pens as P
    from castle2_layout import PENS

    for name, ((x1, z1, x2, z2), animals) in PENS.items():
        gaps = []
        ring = [(x, z) for x in range(x1, x2 + 1) for z in (z1, z2)]
        ring += [(x, z) for z in range(z1 + 1, z2) for x in (x1, x2)]
        for x, z in ring:
            p = V(x, 0, z)
            if not (
                is_block(p, "#minecraft:fences")
                or is_block(p, "#minecraft:fence_gates[open=false]")
                or is_block(p, "#minecraft:fences")  # read again (#166)
            ):
                gaps.append((p.x, p.z))
        high = P.TALL.get(name, 1)
        counts = {}
        a, b = V(x1, -3, z1), V(x2, high + 2, z2)  # (frogs swim in the pond)
        for what, n in animals.items():
            kind = what.split()[0]
            counts[kind] = counts.get(kind, 0) + n
        found = {
            kind: VC.count(f"type=minecraft:{kind},tag={TAG},{L.box_selector(a, b)}")
            for kind in counts
        }
        check(
            f"{name}: fence closed{' (gaps ' + str(gaps[:4]) + ')' if gaps else ''}, "
            f"animals inside {found} of {counts}",
            not gaps and found == counts,
        )
    bees()


def bees() -> None:
    """the bee hives' bees, tagged: in their hives (block data) or out"""
    import pens as P
    from castle2_layout import BEEHIVES, YU

    home = 0
    for x, z in BEEHIVES:
        p = V(x, YU, z)
        r = VC.c(
            f'execute if data block {p.x} {p.y} {p.z} bees[{{entity_data:{{Tags:["{TAG}"]}}}}]'
        )
        m = re.search(r"[Cc]ount: (\d+)", r)
        home += int(m.group(1)) if m else 0
    out = VC.count(f"type=minecraft:bee,tag={TAG}")
    want = P.BEES_PER_HIVE * len(BEEHIVES)
    check(
        f"bee hives: {want} tagged bees ({home} in their hives, {out} out)",
        home + out == want,
    )


# ---------------------------------------------------------------- the gate


def gate_checks() -> None:
    """the main gate closed to villagers by fence gates (main_gate), which
    a visitor opens from either side; the well's gate closed too"""
    import main_gate
    from castle2_layout import GATE_X1, GATE_X2, WELL_GATE

    c = main_gate.cells()
    up = Vec3(0, 1, 0)
    open_ = [
        g for g in c["gates"] if not is_block(g, "#minecraft:fence_gates[open=false]")
    ]
    shut = [g for g in c["gates"] if VC.rcon_kind(g + up) not in R.PASS]
    z = c["gates"][0].z - castle2_layout.ORIGIN.z
    flanks = [V(x, y, z) for x in (GATE_X1 - 1, GATE_X2 + 1) for y in (0, 1)]
    gaps = [p for p in flanks if VC.rcon_kind(p) in R.PASS]
    check(
        f"main gate: {len(c['gates'])} fence gates across the passage, closed"
        f" (open: {[g.x for g in open_]}), walled either side (gaps {gaps})",
        not open_ and not gaps,
    )
    sides = {
        side: [p for p in c[side] if not stand(p)] for side in ("inside", "outside")
    }
    check(
        "main gate: a visitor can reach the fence gates from both sides and"
        f" walk through (no room at {sides}, no headroom over {shut})",
        not sides["inside"] and not sides["outside"] and not shut,
    )
    gx, gz = WELL_GATE
    check(
        "well: its gate closed (villagers stay out of the well)",
        is_block(V(gx, 0, gz), "#minecraft:fence_gates[open=false]"),
    )


def stand(p: Vec3) -> bool:
    """room for a visitor at p (feet and head), with a floor under them"""
    up = Vec3(0, 1, 0)
    return (
        VC.rcon_kind(p) in R.PASS
        and VC.rcon_kind(p + up) in R.PASS
        and VC.rcon_kind(p - up) in R.FLOOR
    )


# ---------------------------------------------------------------- ways out


def reach_checks() -> None:
    """what castle's file-based reach check would find, over RCON for the
    places visitors got stuck: out of the well at the top of its bubble
    column, and onto each tower's top floor (and the keep's roof) at the
    top of its stair or ladder"""
    from build_inner import F3, FR
    from castle2_layout import WELL, WELL_GATE

    from mciwb.builders.paths import trace_path

    up = Vec3(0, 1, 0)
    wx, wz = WELL
    gx, gz = WELL_GATE
    beyond = V(2 * gx - wx, 0, 2 * gz - wz)
    top = V(wx, -1, wz)
    check(
        "reach: the well's bubble column comes up to the open air, beside a"
        " gate in the rim that opens onto the bailey",
        VC.rcon_kind(top) == R.SWIM
        and VC.rcon_kind(top + up) in R.PASS
        and VC.rcon_kind(top + up * 2) in R.PASS
        and VC.rcon_kind(V(gx, 0, gz)) == R.DOOR
        and VC.rcon_kind(V(gx, 1, gz)) in R.PASS
        and VC.rcon_kind(V(gx, -1, gz)) in R.FLOOR
        and stand(beyond),
    )
    bad = R.stair_top_problems(VC.rcon_kind)
    check(
        f"reach: every tower's stair or ladder ({len(TOWER_LEVELS)} towers) comes"
        " out on its top floor"
        f" with headroom{' (' + '; '.join(bad) + ')' if bad else ''}",
        not bad,
    )
    # the keep's stair hall: its top flight (2 wide) up through the roof
    shut = []
    for x in (75, 76):
        steps = trace_path([V(x, F3, 29), V(x, FR, 38)])
        for s in steps[-5:]:
            feet = s.pos + up
            height = 2 if s is steps[-1] else 3
            if not all(VC.rcon_kind(feet + up * h) in R.PASS for h in range(height)):
                shut.append((feet.x, feet.y, feet.z))
    off = steps[-1].pos + up + steps[-1].direction
    check(
        "reach: the keep's stair comes out on the roof terrace with headroom"
        f"{f' (none at {shut})' if shut else ''}",
        not shut and stand(off),
    )


# ---------------------------------------------------------------- strays


def _positions(selector: str) -> list[str]:
    """where the entities a selector matches are, read over RCON"""
    r = VC.c(f"execute as @e[{selector}] run data get entity @s Pos")
    return [
        f"{float(x):.0f} {float(y):.0f} {float(z):.0f}"
        for x, y, z in re.findall(r"\[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]", r)
    ]


def strays() -> None:
    """
    The untagged creatures in the site, listed with where they are, before
    people.kill_strays removes them: iron golems and cats (which villages
    bring), bees, and wild animals of the kinds the pens keep. These only
    get listed: they wander in from outside, and are not the castle's
    fault. An untagged villager inside the walls fails the check: castle2's
    villagers are all tagged and cannot breed, so one is someone else's
    villager let in, or one of ours that lost its tags.
    """
    import people as P

    a, b = castle2_layout.site_box()
    site = L.box_selector(a, b)
    found = []
    for kind in (*P.STRAY_KINDS, *castle2_layout.pen_animals()):
        where = _positions(f"type=minecraft:{kind},tag=!{TAG},{site}")
        if where:
            found.append(f"{kind} at {', '.join(where[:6])}")
    check(
        "strays (listed, not counted against the castle): "
        + ("; ".join(found) if found else "none"),
        True,
    )
    walls = L.box_selector(V(0, -20, 0), V(castle2_layout.W - 1, 80, castle2_layout.ZS))
    villagers = _positions(f"type=minecraft:villager,tag=!{TAG},{walls}")
    check(
        f"strays: no untagged villager inside the walls (found {villagers})",
        not villagers,
    )


def people_checks() -> None:
    """every static person at their spot, every mobile one inside the
    castle's walls"""
    import people as P

    def at(p: Vec3, extra: str = "") -> int:
        box = L.box_selector(p, p + Vec3(0, 1, 0))
        return VC.count(f"type=minecraft:villager,tag={TAG}.people,{box}{extra}")

    missing = []
    for what, (x, y, z), _facing, _seated, *_rest in P.CASTLE_PEOPLE:
        if not at(V(x, y, z)) and not at(V(x, y, z)):
            missing.append(what)
    for name, h in castle2_layout.village_houses().items():
        if "counter" in h.stands and h.contents in P.KEEPER:
            if not at(h.stands["counter"]) and not at(h.stands["counter"]):
                missing.append(f"{name}'s keeper")
    check(
        "people: everyone in their place (the king and queen, the cook, the"
        " librarian, the monk, the alchemist, the smith, the jailer, the"
        " shopkeepers)" + (f" (missing {missing})" if missing else ""),
        not missing,
    )
    walls = L.box_selector(V(0, -20, 0), V(castle2_layout.W - 1, 80, castle2_layout.ZS))
    total = VC.count(f"type=minecraft:villager,tag={TAG}.people")
    inside = VC.count(f"type=minecraft:villager,tag={TAG}.people,{walls}")
    want = castle2_layout.SUMMONED["people"]["villager"]
    check(
        f"people: all {want} villagers inside the walls (found {inside} of {total})",
        inside == total == want,
    )


# the groups of checks, in order (CHECKS=... picks some)
def bailey_machines_check() -> None:
    """the bailey's machines (machines_bailey), each worked in place and
    put back as found: the clock tower (time set to day and night, then
    back), the archery lock (arrows at the target), the mill (its wheel
    turning, its lever opening the way down), the listening door (an arrow
    and the bells)"""
    import machines_bailey

    for name, ok in machines_bailey.checks():
        check(name, ok)


GROUPS = {
    "strays": strays,
    "castle": VC.checks,
    "seats": seats,
    "signs": signs,
    "rooms": rooms_check,
    "houses": houses,
    "pens": pens,
    "people": people_checks,
    "gate": gate_checks,
    "reach": reach_checks,
    "bailey_machines": bailey_machines_check,
}


def main() -> None:
    a, b = castle2_layout.site_box()
    near = L.players_near(a, b, 200)
    if near and not os.environ.get("FORCE"):
        raise SystemExit(
            f"{', '.join(near)} within 200 blocks of the site: not verifying"
        )
    build_outer.forceload(True)
    try:
        import people as P

        wanted = os.environ.get("CHECKS", ",".join(GROUPS)).split(",")
        if "strays" in wanted:
            strays()  # listed before they go
        P.kill_strays()  # the cats and golems a village brings: not ours
        # castle's seat check knows castle's seats: castle2 furnishes the
        # rooms its own way, so give it castle2's (local) seats instead
        o = castle2_layout.ORIGIN
        castle2_layout.SEATS.clear()
        castle2_layout.SEATS["castle2's seats"] = [
            (x, z, x, z, y, faces)
            for p, faces in seat_cells()
            for x, y, z in [(int(p.x - o.x), int(p.y - o.y), int(p.z - o.z))]
        ]
        for name, func in GROUPS.items():
            if name in wanted and name != "strays":
                func()
    finally:
        VC.c("kill @e[tag=castle_verify]")
        build_outer.forceload(False)
    print(f"{sum(VC.results)}/{len(VC.results)} checks passed")
    if not all(VC.results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
