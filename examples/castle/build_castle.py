"""
Build the castle, stage by stage::

    mciwb run build_castle.py                            # everything
    STAGES=earthworks,bailey mciwb run build_castle.py   # some stages

Stages, in order: earthworks, bailey, gatehouse, bridge, upper, stair, keep,
interiors, vault, chapel, alchemist, bailey_buildings, dungeons, details.
The site and the road to spawn are forceloaded while the build runs and
unloaded again when it ends, however it ends; dropped items in the site are
removed too (``STAGES=cleanup`` does just that).

Where to build, and the castle's name and colour, come from the
environment (see castle_layout.py)::

    ORIGIN=-80,82,-230 SPAWN=32,74,-64 NAME=Fable BANNER=red mciwb run build_castle.py

Rebuilding is safe: every entity the castle summons is tagged with the
castle's tag and its stage's, a stage removes its own before it runs, and
earthworks (a fresh site) removes every entity in the site. Refuses to run
if a player is inside the site, unless FORCE=1.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import build_inner  # noqa: E402
import build_outer  # noqa: E402
import castle_lib as L  # noqa: E402
from castle_layout import NAME, ORIGIN, SPAWN, TAG, site_box  # noqa: E402

from mciwb.imports import Player, Vec3, Volume, get_client  # noqa: E402

STAGES = {
    "earthworks": build_outer.earthworks,
    "bailey": build_outer.bailey_walls,
    "gatehouse": build_outer.gatehouse,
    "bridge": build_outer.bridge_and_road,
    "upper": build_outer.upper_walls,
    "stair": build_outer.grand_stair,
    "keep": build_outer.keep_shell,
    "interiors": build_inner.keep_interiors,
    "vault": build_inner.vault,
    "chapel": build_inner.chapel,
    "alchemist": build_inner.alchemist_tower,
    "bailey_buildings": build_inner.bailey_buildings,
    "dungeons": build_inner.dungeons,
    "details": build_inner.details,
}


def players_inside(vol: Volume) -> list[str]:
    names = [p.name for p in get_client().players.players]
    return [name for name in names if vol.inside(Player(name).pos, 2, 2, 2)]


def box_selector(a: Vec3, b: Vec3) -> str:
    """the ``x=,y=,z=,dx=,dy=,dz=`` of an entity selector for a box"""
    return f"x={a.x},y={a.y},z={a.z},dx={b.x - a.x + 1},dy={b.y - a.y + 1},dz={b.z - a.z + 1}"


def kill_in_site(selector: str) -> None:
    a, b = site_box()
    print(f"   {L.cmd(f'kill @e[{selector},{box_selector(a, b)}]')}")


def run_stage(name: str) -> None:
    t0 = time.time()
    print(f"== {name}")
    L.STAGE = name
    print(f"   {L.kill_tagged(f'{TAG}.{name}')}")
    if name == "earthworks":
        kill_in_site("type=!minecraft:player")
    result = STAGES[name]()
    if result:
        print(f"   {result}")
    print(f"   {name} done in {time.time() - t0:.0f} s")


def main() -> None:
    a, b = site_box()
    site = Volume.from_corners(a, b)
    if site.inside(SPAWN):
        raise SystemExit(f"spawn {SPAWN} is inside the site {a}..{b}: not building")
    inside = players_inside(site)
    if inside and not os.environ.get("FORCE"):
        raise SystemExit(f"{', '.join(inside)} inside the site {a}..{b}: not building")
    wanted = os.environ.get("STAGES", ",".join(STAGES)).split(",")
    unknown = [s for s in wanted if s not in STAGES and s != "cleanup"]
    if unknown:
        raise SystemExit(
            f"unknown stages {unknown}: choose from {list(STAGES)} and cleanup"
        )
    print(f"castle {NAME} at {ORIGIN}, road to {SPAWN}, entities tagged {TAG}")
    t_start = time.time()
    build_outer.forceload(True)
    try:
        for name in wanted:
            if name != "cleanup":
                run_stage(name)
    finally:
        print("== cleanup")
        kill_in_site("type=minecraft:item")
        build_outer.forceload(False)
    print(f"castle {NAME} built in {time.time() - t_start:.0f} s")


if __name__ == "__main__":
    main()
