"""
Build Castle 2, stage by stage::

    mciwb run build_castle2.py                           # everything
    STAGES=earthworks,bailey mciwb run build_castle2.py  # some stages

Castle 2 is Castle Fable (``examples/castle``, which must sit beside this
folder) with a bailey of depth 162: this driver runs castle's build
(``build_castle.main``) with castle2's layout and castle2's stages added to
castle's, and its own furniture in castle's rooms (``interiors``,
``chapel``, ``bailey_buildings``: rooms.py) in place of castle's, with
``furnish`` (more detail in the alchemist's tower, the dungeon, the vault
and the winch room) after ``dungeons``, then ``machines`` (machines_upper and
organ: the lectern lock, the copper puzzle, the astrolabe, the engine's
bell, the transmuter, the organ; rebuild it after rebuilding the rooms it
stands in); ``village`` (the lanes, the square and the houses) after
``bailey_buildings``, then ``pens`` (the animals, the allotments and
the bee hives), ``bailey_machines`` (machines_bailey: the clock tower, the
archery lock, the mill, the listening door), and ``people`` (the castle's people, the shopkeepers,
the villagers and the guards) after castle's ``details``. The stages, the site's forceload, the player check and the
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
import build_outer  # noqa: E402
import castle_lib as L  # noqa: E402
import machines_bailey  # noqa: E402
import machines_upper  # noqa: E402
import main_gate  # noqa: E402
import pens  # noqa: E402
import people  # noqa: E402
import rooms  # noqa: E402
import village  # noqa: E402
from fake_client import summon_counts  # noqa: E402

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


# castle2's stages, and the castle stages whose furniture castle2 swaps
_insert_after("bailey_buildings", "village", village.village)
_insert_after("village", "pens", pens.pens)
_insert_after("details", "people", people.people)


def interiors() -> None:
    """the keep's rooms (castle's), castle2's furniture, castle's lights"""
    build_inner.interiors_shell()
    rooms.interiors_furnishing()
    build_inner.interiors_lights()


def chapel() -> None:
    """the chapel and crypt (castle's), castle2's furniture"""
    build_inner.chapel_shell()
    rooms.chapel_furnishing()


def bailey_buildings() -> None:
    """the bailey's paths and buildings (castle's), castle2's furniture"""
    build_inner.bailey_shell()
    rooms.bailey_furnishing()


def gatehouse() -> dict:
    """the gatehouse (castle's), its passage closed to villagers by fence
    gates (main_gate)"""
    g = build_outer.gatehouse()
    main_gate.close()
    return g


build_castle.STAGES["gatehouse"] = gatehouse
build_castle.STAGES["interiors"] = interiors
build_castle.STAGES["chapel"] = chapel
build_castle.STAGES["bailey_buildings"] = bailey_buildings
_insert_after("dungeons", "furnish", rooms.extras)
# phase 6: the machines (the lectern lock, the copper puzzle, the astrolabe,
# the engine's bell, the transmuter, the organ), after the rooms they stand in
_insert_after("furnish", "machines", machines_upper.machines)

# phase 6, the bailey's machines (machines_bailey.py): the clock tower, the
# archery lock, the mill and its tunnel, the listening door. The dungeons
# stage builds the oubliette's and the guard room's walls again, so the
# listening door and the tunnel's doorway are built again after it
_insert_after("pens", "bailey_machines", machines_bailey.bailey_machines)
_castle_dungeons = build_castle.STAGES["dungeons"]


def dungeons():
    """castle's dungeons, then the machines that cut into their walls"""
    result = _castle_dungeons()
    machines_bailey.after_dungeons()
    return result


build_castle.STAGES["dungeons"] = dungeons

# what each of these stages summons, learnt by running it against a fake
# client: the build checks they are all there, verify counts them
for _stage in (
    "village",
    "pens",
    "bailey_machines",
    "people",
    "interiors",
    "chapel",
    "bailey_buildings",
    "furnish",
    "machines",
):
    castle2_layout.SUMMONED[_stage] = summon_counts(build_castle.STAGES[_stage])
    if not castle2_layout.SUMMONED[_stage]:
        del castle2_layout.SUMMONED[_stage]


def wrong_entities(stage: str) -> list[str]:
    """the entity types a stage summoned that are not all there, or that
    are there too many times (an old one that survived the stage's kill in
    a chunk whose entities had not loaded): castle's build runs the stage
    again for either"""
    return [
        f"{kind} {found}/{n}"
        for kind, n in castle2_layout.SUMMONED.get(stage, {}).items()
        if (
            found := L.count_entities(
                f"type=minecraft:{kind},tag={castle2_layout.TAG}.{stage}"
            )
        )
        != n
    ]


build_castle.missing_entities = wrong_entities


def main() -> None:
    build_castle.main()


if __name__ == "__main__":
    main()
