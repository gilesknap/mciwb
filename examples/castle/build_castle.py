"""
Build the castle, stage by stage::

    mciwb run build_castle.py                            # everything
    STAGES=earthworks,bailey mciwb run build_castle.py   # some stages

Stages, in order: earthworks, bailey, gatehouse, bridge, upper, stair, keep,
interiors, vault, chapel, alchemist, bailey_buildings, dungeons, details.
The site and the road to spawn are forceloaded while the build runs and
unloaded again when it ends, however it ends; dropped items and hostile mobs
in the site are removed too (``STAGES=cleanup`` does just that).

Where to build, and the castle's name and colour, come from the
environment (see castle_layout.py)::

    ORIGIN=-80,82,-230 SPAWN=32,74,-64 NAME=Fable BANNER=red mciwb run build_castle.py

Rebuilding is safe: every entity the castle summons is tagged with the
castle's tag and its stage's, a stage removes its own before it runs, and
earthworks (a fresh site) removes every entity in the site. Refuses to run
if a player is within 200 blocks of the site, unless FORCE=1; with anyone
online at all it waits for the game's own ticks instead of sprinting them.
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
from castle_layout import NAME, ORIGIN, SPAWN, SUMMONED, TAG, site_box  # noqa: E402

from mciwb.imports import Volume  # noqa: E402

PLAYER_MARGIN = 200  # how far from the site a player must be for a build to go ahead

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


def kill_in_site(selector: str) -> None:
    a, b = site_box()
    print(f"   {L.cmd(f'kill @e[{selector},{L.box_selector(a, b)}]')}")


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


def missing_entities(stage: str) -> list[str]:
    """the entity types a stage summoned that are not all there"""
    return [
        f"{kind} {found}/{n}"
        for kind, n in SUMMONED.get(stage, {}).items()
        if (found := L.count_entities(f"type=minecraft:{kind},tag={TAG}.{stage}")) < n
    ]


def settle_entities(stages: list[str]) -> None:
    """
    Make sure every entity the stages summoned survives its chunk being
    unloaded and loaded again, and summon the missing ones again. Now and
    then one is lost between the build and the first check (observed, not
    explained: gilesknap/mciwb#166, item 9); an unload and reload before
    counting has caught it so far.
    """
    L.tick(60)
    time.sleep(2)
    L.cmd("save-all flush")
    build_outer.forceload(False)
    L.tick(100)
    time.sleep(3)
    build_outer.forceload(True)
    for stage in stages:
        missing = missing_entities(stage)
        if missing:
            print(f"== {stage} again: missing {', '.join(missing)}")
            run_stage(stage)
            L.tick(20)
            time.sleep(2)
            missing = missing_entities(stage)
            if missing:
                raise SystemExit(f"{stage}: still missing {', '.join(missing)}")


def main() -> None:
    a, b = site_box()
    site = Volume.from_corners(a, b)
    if site.inside(SPAWN):
        raise SystemExit(f"spawn {SPAWN} is inside the site {a}..{b}: not building")
    near = L.players_near(a, b, PLAYER_MARGIN)
    if near and not os.environ.get("FORCE"):
        raise SystemExit(
            f"{', '.join(near)} within {PLAYER_MARGIN} blocks of the site {a}..{b}: not building"
        )
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
        settle_entities([s for s in wanted if s in SUMMONED])
    finally:
        print("== cleanup")
        kill_in_site("type=minecraft:item")
        print(f"   killed {L.kill_hostiles(*site_box())} hostile mobs")
        build_outer.forceload(False)
    print(f"castle {NAME} built in {time.time() - t_start:.0f} s")


if __name__ == "__main__":
    main()
