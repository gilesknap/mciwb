"""
Verify Castle 2 over RCON, without a player::

    mciwb run verify_castle2.py

Runs all of castle's checks (``verify_castle.checks``, see castle's README)
on castle2's layout, then castle2's own:

- every seat (``castle_lib.seat``, and the houses' seats) faces the way its
  sitter looks, read back from the block's state, with its back to no table
  and something to look at in front: a table, an altar, a lectern, or open
  floor;
- every house has its door, clear floor either side of it, and its stands
  (counter, bedside, hearth) free;
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
  removed (an untagged villager inside the walls fails it).

``CHECKS=seats,pens`` runs only some of them (strays, castle, seats,
houses, pens, people, gate, reach).
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
import reach  # noqa: E402
import verify_castle as VC  # noqa: E402
from record_build import dry_run  # noqa: E402

from castle2_layout import TAG, TOWER_LEVELS, V  # noqa: E402

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


_seat_cells: list[tuple[Vec3, str]] = []


def seat_cells() -> list[tuple[Vec3, str]]:
    """every seat cell the build places and keeps (a later block may
    replace one), and the way its sitter looks: learnt by running the
    build's stages against a fake client (once)"""
    if not _seat_cells:
        _seat_cells.extend(_learn_seats())
    return _seat_cells


def _learn_seats() -> list[tuple[Vec3, str]]:
    L.PLACED_SEATS.clear()
    stages = [f for name, f in build_castle.STAGES.items() if name != "earthworks"]
    rec = dry_run(*stages, box=castle2_layout.site_box())
    cells = []
    for a, b, faces in L.PLACED_SEATS:
        for x in range(min(a.x, b.x), max(a.x, b.x) + 1):
            for y in range(min(a.y, b.y), max(a.y, b.y) + 1):
                for z in range(min(a.z, b.z), max(a.z, b.z) + 1):
                    p = Vec3(x, y, z)
                    if "_stairs" in rec.world.at(p):
                        cells.append((p, faces))
    for h in castle2_layout.village_houses().values():
        cells += h.seats
    return cells


def seat_problem(p: Vec3, faces: str) -> str:
    """what is wrong with the seat at p, or empty"""
    back = castle2_layout.OPPOSITE[faces]
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
            or is_block(q, "#minecraft:fences")  # a post or a rail: seen past
        ):
            return "" if k > 4 else f"a wall {k} in front"
    return ""


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
        f"seats: all {len(cells)} face their table, altar or hall"
        + (f" (not {bad[:4]})" if bad else ""),
        bool(cells) and not bad,
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
    shut = [g for g in c["gates"] if VC.rcon_kind(g + up) not in reach.PASS]
    z = c["gates"][0].z - castle2_layout.ORIGIN.z
    flanks = [V(x, y, z) for x in (GATE_X1 - 1, GATE_X2 + 1) for y in (0, 1)]
    gaps = [p for p in flanks if VC.rcon_kind(p) in reach.PASS]
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
        VC.rcon_kind(p) in reach.PASS
        and VC.rcon_kind(p + up) in reach.PASS
        and VC.rcon_kind(p - up) in reach.FLOOR
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
        VC.rcon_kind(top) == reach.SWIM
        and VC.rcon_kind(top + up) in reach.PASS
        and VC.rcon_kind(top + up * 2) in reach.PASS
        and VC.rcon_kind(V(gx, 0, gz)) == reach.DOOR
        and VC.rcon_kind(V(gx, 1, gz)) in reach.PASS
        and VC.rcon_kind(V(gx, -1, gz)) in reach.FLOOR
        and stand(beyond),
    )
    bad = reach.stair_top_problems(VC.rcon_kind)
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
            if not all(
                VC.rcon_kind(feet + up * h) in reach.PASS for h in range(height)
            ):
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
GROUPS = {
    "strays": strays,
    "castle": VC.checks,
    "seats": seats,
    "houses": houses,
    "pens": pens,
    "people": people_checks,
    "gate": gate_checks,
    "reach": reach_checks,
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
            (p.x - o.x, p.z - o.z, p.x - o.x, p.z - o.z, p.y - o.y, faces)
            for p, faces in seat_cells()
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
