"""
The main gate, closed to the villagers who roam the bailey (PLAN Decision
3: free range inside the castle) but not to visitors: a row of fence gates
across the gate passage, outside the portcullis. A player opens one from
either side; a villager cannot open a fence gate (nor jump one). castle's
portcullis and its lever are left as castle builds them.

castle2 runs `close` after castle's gatehouse stage (build_castle2), so a
rebuild of the gatehouse keeps its gates. `cells` gives what verify checks.
"""

from __future__ import annotations

import castle_lib as L
from castle2_layout import GATE_X1, GATE_X2, GATE_Z, V

from mciwb.imports import Vec3

# the fence gates' row: outside the portcullis (GATE_Z), with a block to
# stand on between them, south of the guard room's door into the passage
# (so that nobody walks round them) and north of the arch's grille
FENCE_Z = GATE_Z + 2
FENCE_GATE = "minecraft:dark_oak_fence_gate[facing=south,open=false]"


def cells() -> dict[str, list[Vec3]]:
    """the fence gates, and the cells either side of them where a visitor
    stands to open one (inside, between them and the portcullis, and
    outside, under the arch)"""
    xs = range(GATE_X1, GATE_X2 + 1)
    return {
        "gates": [V(x, 0, FENCE_Z) for x in xs],
        "inside": [V(x, 0, FENCE_Z - 1) for x in xs],
        "outside": [V(x, 0, FENCE_Z + 1) for x in xs],
    }


def close() -> None:
    """put the fence gates across the gate passage, closed"""
    for p in cells()["gates"]:
        L.set_block(p, FENCE_GATE)
