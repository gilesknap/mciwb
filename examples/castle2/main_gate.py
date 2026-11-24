"""
The main gate, closed to the villagers who roam the bailey (PLAN Decision
3: free range inside the castle) but not to visitors: a row of fence gates
across the gate passage, outside the portcullis. A player opens one from
either side; a villager cannot open a fence gate (nor jump one). castle's
portcullis and its lever are left as castle builds them.

The postern: castle's portcullis is worked by a lever inside the gate, so
whoever shuts it shuts everybody else out (or in). An iron door in the
passage's west wall, between the fence gates and the portcullis, leads
through a nook under the guard room's stair into the guard room, whose own
doorway opens onto the bailey: a way round the bars. A stone button on
each side opens it (in the passage it is on the ceiling beside the door:
the walls there are the bars and the fence gates); a villager cannot.

castle2 runs `close` and `postern` after castle's gatehouse stage
(build_castle2), so a rebuild of the gatehouse keeps them. `cells` and
`postern_cells` give what verify checks.
"""

from __future__ import annotations

import castle_lib as L
from castle2_layout import GATE_X1, GATE_X2, GATE_Z, GATEHOUSE, V

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


def postern_cells() -> dict:
    """the postern's parts: the iron door in the passage's west wall, one
    block south of the portcullis, the buttons either side of it (each in
    the cell beside the door's top half, which it powers directly), and the
    way through, from the passage to the guard room's door onto the bailey"""
    x, z = GATE_X1 - 1, GATE_Z + 1
    gx1, gz1, _gx2, _gz2 = GATEHOUSE
    return {
        "door": [V(x, 0, z), V(x, 1, z)],
        "door_facing": "east",
        # (the button's cell, its state, the block it is fixed to)
        "buttons": {
            "passage": (V(x + 1, 1, z), "face=ceiling,facing=north", V(x + 1, 2, z)),
            "nook": (V(x - 1, 1, z), "face=wall,facing=north", V(x - 1, 1, z + 1)),
        },
        "nook": V(x - 1, 0, z),
        # where a visitor walks: in the passage, the nook, the guard room
        # and out of its doorway onto the bailey
        "way": [
            V(x + 1, 0, z),
            V(x - 1, 0, z),
            V(x - 1, 0, z - 1),
            V(gx1 + 9, 0, gz1 + 1),
            V(gx1 + 9, 0, gz1),
            V(gx1 + 9, 0, gz1 - 1),
        ],
    }


def postern() -> None:
    """cut the nook under the guard room's stair and hang the iron door,
    with its two buttons"""
    c = postern_cells()
    nook = c["nook"]
    L.fill(nook, nook + Vec3(0, 1, 0), L.AIR)
    lower, upper = c["door"]
    f = c["door_facing"]
    L.set_block(lower, f"minecraft:iron_door[facing={f},half=lower,hinge=left]")
    L.set_block(upper, f"minecraft:iron_door[facing={f},half=upper,hinge=left]")
    for p, state, _on in c["buttons"].values():
        L.set_block(p, f"minecraft:stone_button[{state}]")
