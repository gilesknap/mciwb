"""
Build the castle, stage by stage::

    mciwb run build_castle.py                 # everything
    STAGES=earthworks,bailey mciwb run build_castle.py   # some stages

Stages, in order: earthworks, bailey, gatehouse, bridge, upper, stair, keep,
interiors, vault, chapel, alchemist, bailey_buildings, dungeons, details,
cleanup. Set ORIGIN in castle_layout.py to move the whole castle. The site
is forceloaded for the build and unloaded again by ``cleanup``.

Refuses to run if a player is inside the site, unless FORCE=1.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import build_inner  # noqa: E402
import build_outer  # noqa: E402
from castle_layout import SITE_TOP, SITE_X1, SITE_X2, SITE_Z1, SITE_Z2, V  # noqa: E402

from mciwb.imports import Player, Volume, get_client, get_world  # noqa: E402

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


def main() -> None:
    world = get_world()
    site = Volume.from_corners(V(SITE_X1, -20, SITE_Z1), V(SITE_X2, SITE_TOP, SITE_Z2))
    inside = players_inside(site)
    if inside and not os.environ.get("FORCE"):
        raise SystemExit(
            f"{', '.join(inside)} inside the site {site.start}..{site.end}: not building"
        )
    wanted = os.environ.get("STAGES", ",".join(STAGES)).split(",")
    unknown = [s for s in wanted if s not in STAGES and s != "cleanup"]
    if unknown:
        raise SystemExit(
            f"unknown stages {unknown}: choose from {list(STAGES)} and cleanup"
        )
    build_outer.forceload(True)
    for name in wanted:
        if name == "cleanup":
            continue
        t0 = time.time()
        print(f"== {name}")
        result = STAGES[name]()
        if result:
            print(f"   {result}")
        print(f"   {name} done in {time.time() - t0:.0f} s")
    if "cleanup" in wanted:
        world.cmd("kill @e[type=minecraft:item]")
        build_outer.forceload(False)
    print("castle built")


if __name__ == "__main__":
    main()
