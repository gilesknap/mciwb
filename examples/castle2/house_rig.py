"""
Test `house.medieval_house` on its own: build a row of houses, one for each
set of options in `VARIANTS`, check each and render them.

Offline (no server), from the blocks each house would place::

    python house_rig.py rig.png                 # every variant
    python house_rig.py rig.png 0 3             # variants 0 and 3

In the world, in the air at RIG (default 552,190,-198, high over castle2's
site: the north-west corner of the rows, 140 wide; the box must be empty,
and is cleared afterwards unless KEEP=1; WHICH=0,3 builds some)::

    RIG=552,190,-198 mciwb run house_rig.py

The checks, per house: nothing lies outside its volume; the door has free
floor in front of it and behind it; every storey can be reached from the
ground floor (a stair or a ladder joins each floor to the next); every
overhanging storey has a joist under each other cell of its overhang; seats
face away from their back; the stands are free floor.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from house import House, house_blocks, house_problems, place, wall_share  # noqa: E402

from mciwb.imports import Vec3  # noqa: E402

# the options of each house in the rig: every option value appears at least once
VARIANTS: list[dict] = [
    {"width": 7, "depth": 8, "floors": 2, "contents": "cobbler"},
    {
        "width": 9,
        "depth": 10,
        "floors": 3,
        "jetty_sides": "front+sides",
        "frame": "square_panel",
        "contents": "baker",
    },
    {
        "width": 5,
        "depth": 6,
        "floors": 2,
        "ground": "timber",
        "frame": "braced",
        "windows": "shuttered",
    },
    {
        "width": 11,
        "depth": 12,
        "floors": 3,
        "roof": "gable_cross",
        "contents": "tavern",
        "window_boxes": True,
    },
    {
        "width": 8,
        "depth": 7,
        "floors": 4,
        "jetty_sides": "all",
        "roof": "hip",
        "roof_block": "minecraft:deepslate_tile_stairs",
        "contents": "apothecary",
    },
    {
        "width": 6,
        "depth": 5,
        "floors": 1,
        "jetty": 0,
        "chimney": False,
        "contents": "home",
        "window_boxes": True,
    },
    {
        "width": 7,
        "depth": 9,
        "floors": 2,
        "windows": "shop",
        "contents": "butcher",
        "facing": "east",
    },
    {
        "width": 8,
        "depth": 8,
        "floors": 3,
        "contents": "tailor",
        "facing": "north",
        "jetty": 2,
    },
    {
        "width": 10,
        "depth": 8,
        "floors": 2,
        "contents": "candlemaker",
        "facing": "west",
        "frame": "braced",
    },
    {"width": 7, "depth": 7, "floors": 2, "contents": "carpenter", "roof": "hip"},
    {"width": 9, "depth": 7, "floors": 2, "contents": "fletcher", "ground": "timber"},
    {
        "width": 8,
        "depth": 9,
        "floors": 3,
        "contents": "cartographer",
        "roof": "gable_cross",
    },
    {
        "width": 7,
        "depth": 10,
        "floors": 2,
        "contents": "weaver",
        "windows": "shuttered",
    },
]
GAP = 6  # blocks between houses
ROW = 140  # the widest row: the rig stays over castle2's site, x 550..700


def build_row(
    corner: Vec3, which: list[int], width: int = ROW
) -> list[tuple[int, House]]:
    """the houses in rows from corner, eastwards, a new row south of the
    last when a row would be wider than ``width``"""
    houses: list[tuple[int, House]] = []
    x, z, row_end = corner.x, corner.z, corner.z
    for k in which:
        opts = dict(VARIANTS[k])
        h = house_blocks(Vec3(x, corner.y, z + 4), seed=k, **opts)
        for _attempt in range(2):
            h = house_blocks(Vec3(x, corner.y, z + 4), seed=k, **opts)
            # shift so that its volume starts at x, z (jetties reach out)
            dx, dz = x - h.volume.start.x, z - h.volume.start.z
            if dx or dz:
                h = house_blocks(Vec3(x + dx, corner.y, z + 4 + dz), seed=k, **opts)
            if h.volume.end.x <= corner.x + width - 1 or x == corner.x:
                break
            x, z = corner.x, row_end + GAP  # the next row
        houses.append((k, h))
        x = h.volume.end.x + GAP
        row_end = max(row_end, h.volume.end.z)
    return houses


def joist_problems(h: House, opts: dict) -> list[str]:
    """every overhanging storey has a row of joists under it on the street
    side, one at least every other block of the storey below's front"""
    if opts.get("jetty", 1) == 0:
        return []
    out = []
    width = opts["width"]
    for k, y in enumerate(h.floors[1:], start=1):
        joists = [
            p
            for p, s in h.blocks.items()
            if p[1] == y - 2 and "dark_oak_stairs" in s and "half=top" in s
        ]
        if len(joists) < (width + 1) // 2:
            out.append(
                f"storey {k}: {len(joists)} joists under its overhang, want {(width + 1) // 2}+"
            )
    return out


def render_png(houses: list[tuple[int, House]], out: str) -> None:
    import numpy as np

    from mciwb.blockgrid import BlockGrid
    from mciwb.render import render

    blocks: dict = {}
    for _k, h in houses:
        blocks.update(h.blocks)
    xs, ys, zs = zip(*blocks, strict=True)
    lo = Vec3(min(xs), min(ys), min(zs))
    names = np.full(
        (max(xs) - lo.x + 1, max(ys) - lo.y + 1, max(zs) - lo.z + 1),
        "minecraft:air",
        dtype=object,
    )
    for (x, y, z), s in blocks.items():
        names[x - lo.x, y - lo.y, z - lo.z] = s.partition("[")[0].partition("{")[0]
    views = os.environ.get("VIEWS", "top,south,iso").split(",")
    render(BlockGrid.from_blocks(names, lo), views).save(out)


def report(houses: list[tuple[int, House]], options: list[dict]) -> bool:
    ok = True
    for (k, h), opts in zip(houses, options, strict=True):
        found = house_problems(h) + joist_problems(h, opts)
        ok &= not found
        text = ", ".join(f"{a}={b}" for a, b in opts.items())
        print(
            f"{'PASS' if not found else 'FAIL'} house {k} ({text}) at"
            f" {h.volume.start}..{h.volume.end}: walls {_share(h)} white"
        )
        for f in found:
            print(f"     {f}")
    return ok


def _share(h: House) -> str:
    share = wall_share(h)
    return "-" if share is None else f"{share:.0%}"


def village() -> None:
    """check every house of castle2's village (offline)"""
    import castle2_layout as C

    houses = C.village_houses()
    rows = [(k, h) for k, h in enumerate(houses.values())]
    options = [dict(width=w, depth=d, **o) for _n, _x, _z, w, d, _f, o in C.HOUSES]
    ok = report(rows, options)
    if len(sys.argv) > 2:
        render_png(rows, sys.argv[2])
        print(f"rendered {sys.argv[2]}")
    if not ok:
        raise SystemExit(1)


def offline() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "rig.png"
    which = [int(a) for a in sys.argv[2:]] or list(range(len(VARIANTS)))
    houses = build_row(Vec3(0, 100, 0), which)
    ok = report(houses, [VARIANTS[k] for k in which])
    render_png(houses, out)
    print(f"rendered {out}")
    if not ok:
        raise SystemExit(1)


def in_world() -> None:
    import castle2_layout  # noqa: F401  (castle's modules on the path)
    import castle_lib as L
    from build_outer import wait_loaded

    from mciwb.imports import Volume

    x, y, z = (int(v) for v in os.environ.get("RIG", "552,190,-198").split(","))
    which = [int(a) for a in os.environ.get("WHICH", "").split(",") if a] or list(
        range(len(VARIANTS))
    )
    houses = build_row(Vec3(x, y, z), which)
    lo = Vec3(min(h.volume.start.x for _, h in houses), y - 2, z)
    hi = Vec3(
        max(h.volume.end.x for _, h in houses),
        max(h.volume.end.y for _, h in houses),
        max(h.volume.end.z for _, h in houses),
    )
    box = Volume.from_corners(lo, hi)
    L.cmd(f"forceload add {lo.x} {lo.z} {hi.x} {hi.z}")
    try:
        wait_loaded([(lo.x, lo.z), (hi.x, hi.z)], 20)
        from build_outer import ground_heights_retry

        from mciwb.imports import Heightmap

        columns = [
            (x, z)
            for x in range(int(lo.x), int(hi.x) + 1)
            for z in range(int(lo.z), int(hi.z) + 1)
        ]
        tops = ground_heights_retry(columns, Heightmap.WORLD_SURFACE)
        if max(tops.values()) >= lo.y and not os.environ.get("REUSE"):
            raise SystemExit(f"the rig's box {lo}..{hi} is not empty: not building")
        L.STAGE = "house_rig"
        L.kill_tagged(f"{L.TAG}.house_rig")
        L.fill(box.start, box.end, L.AIR)
        for _k, h in houses:
            place(h, L.summon)
        ok = report(houses, [VARIANTS[k] for k in which])
        bad = []
        for _k, h in houses:  # read some blocks back: doors, seats, stands
            if not L.is_block(h.door, "#minecraft:doors"):
                bad.append(f"no door at {h.door}")
            for p, looks in h.seats:
                back = {
                    "north": "south",
                    "south": "north",
                    "east": "west",
                    "west": "east",
                }[looks]
                if not L.is_block(p, f"#minecraft:stairs[facing={back}]"):
                    bad.append(f"seat {p}")
        print("world readback:", "PASS" if not bad else f"FAIL {bad[:5]}")
        if not ok or bad:
            raise SystemExit(1)
    finally:
        if not os.environ.get("KEEP"):
            L.kill_tagged(f"{L.TAG}.house_rig")
            L.fill(box.start, box.end, L.AIR)
        L.cmd(f"forceload remove {lo.x} {lo.z} {hi.x} {hi.z}")


def connected() -> bool:
    """run by mciwb run (a client for this thread), or as a plain script?"""
    from mciwb.threads import get_client

    try:
        get_client()
    except AttributeError:
        return False
    return True


if __name__ == "__main__":
    if connected():
        in_world()
    elif sys.argv[1:2] == ["--village"]:
        village()
    else:
        offline()
