"""
Build Castle 2, stage by stage::

    mciwb run build_castle2.py                           # everything
    STAGES=earthworks,bailey mciwb run build_castle2.py  # some stages

Castle 2 is Castle Fable (``examples/castle``, which must sit beside this
folder) with a bailey of depth 162: this driver runs castle's build
(``build_castle.main``) with castle2's layout and castle2's stages added to
castle's: ``village`` (the lanes, the square and the houses) after
``bailey_buildings``, then ``pens`` (the animals, the allotments and
the bee hives). The stages, the site's forceload, the player check and the
entity checks are castle's (see its README). The defaults (site, name,
banner) are in castle2_layout.DEFAULTS; the environment overrides them.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle2_layout  # noqa: E402, I001  (first: it sets up castle's layout)
import build_castle  # noqa: E402
import build_inner  # noqa: E402
import castle_lib as L  # noqa: E402
import pens  # noqa: E402
import village  # noqa: E402

from mciwb.imports import Vec3  # noqa: E402

# castle's layout check, extended with castle2's
build_castle.layout_problems = castle2_layout.castle2_problems

# castle's lantern posts go wherever the 5 blocks above the ground are free,
# which in castle2 can be under a house's eaves or between the chapel's pews
# (its roof is 6 up): castle2 only puts one where the sky is clear
_castle_post = build_inner.post


def post_in_the_open(x: int, y: int, z: int) -> None:
    p = castle2_layout.V(x, y, z)
    if all(L.is_block(Vec3(p.x, p.y + k, p.z), L.AIR) for k in range(5, 14)):
        _castle_post(x, y, z)


build_inner.post = post_in_the_open


def _insert_after(after: str, name: str, func) -> None:
    """add a stage to castle's, after another"""
    stages = list(build_castle.STAGES.items())
    k = [n for n, _ in stages].index(after) + 1
    build_castle.STAGES.clear()
    build_castle.STAGES.update(stages[:k] + [(name, func)] + stages[k:])


# castle2's stages, and what they summon
_insert_after("bailey_buildings", "village", village.village)
castle2_layout.SUMMONED["village"] = {"item_frame": village.frames()}
_insert_after("village", "pens", pens.pens)
castle2_layout.SUMMONED["pens"] = {**castle2_layout.pen_animals(), "armor_stand": 1}


def main() -> None:
    build_castle.main()


if __name__ == "__main__":
    main()
