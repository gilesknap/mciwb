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

``CHECKS=seats,pens`` runs only some of them (castle, seats, signs, houses, pens,
people).
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
import verify_castle as VC  # noqa: E402
from record_build import dry_run  # noqa: E402

import numpy as np  # noqa: E402

from castle2_layout import TAG, V  # noqa: E402

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


_recording: list = []


def recording():
    """the build's stages run against a fake client (once), with the blocks
    they place in the site (``.world``): what the checks expect to find"""
    if not _recording:
        L.PLACED_SEATS.clear()
        stages = [f for name, f in build_castle.STAGES.items() if name != "earthworks"]
        _recording.append(dry_run(*stages, box=castle2_layout.site_box()))
    return _recording[0]


def _learn_seats() -> list[tuple[Vec3, str]]:
    rec = recording()
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


_SNBT_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'')


def snbt_strings(text: str) -> list[str]:
    """the quoted strings in SNBT text (a sign's messages), unescaped"""
    return [
        re.sub(r"\\(.)", r"\1", a if a or not b else b)
        for a, b in _SNBT_STRING.findall(text)
    ]


def placed_signs() -> list[tuple[Vec3, list[str]]]:
    """every sign the build places in the site, with its front lines as
    written: learnt from the recording"""
    rec = recording()
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

        P.kill_strays()  # the cats and golems a village brings: not ours
        # castle's seat check knows castle's seats: castle2 furnishes the
        # rooms its own way, so give it castle2's (local) seats instead
        o = castle2_layout.ORIGIN
        castle2_layout.SEATS.clear()
        castle2_layout.SEATS["castle2's seats"] = [
            (p.x - o.x, p.z - o.z, p.x - o.x, p.z - o.z, p.y - o.y, faces)
            for p, faces in seat_cells()
        ]
        wanted = os.environ.get(
            "CHECKS", "castle,seats,signs,houses,pens,people"
        ).split(",")
        for name, func in (
            ("castle", VC.checks),
            ("seats", seats),
            ("signs", signs),
            ("houses", houses),
            ("pens", pens),
            ("people", people_checks),
        ):
            if name in wanted:
                func()
    finally:
        VC.c("kill @e[tag=castle_verify]")
        build_outer.forceload(False)
    print(f"{sum(VC.results)}/{len(VC.results)} checks passed")
    if not all(VC.results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
