"""
The pens stage (phase 3): farm animals in fenced pens in the south of the
bailey, the allotments with a scarecrow, a frog pond, and bee hives by the
upper ward's garden. Each pen has a fence ring with a gate onto the pen
lane, a water trough, hay, a shelter and a lantern, so that nothing hostile
spawns in it. The animals are summoned tagged (castle_lib.summon) and
persistent; the young ones are kept young. They are never fed, so they do
not breed: verify counts each pen's animals inside its fence.
"""

from __future__ import annotations

import random

import castle_lib as L
from castle2_layout import BEEHIVES, GARDEN, PEN_LANE, PENS, YU, V

from mciwb.imports import Vec3

FENCE = "minecraft:spruce_fence"
GATE = "minecraft:spruce_fence_gate[facing=north,open=false]"
YOUNG = "Age:-24000,AgeLocked:1b"
_rng = random.Random(162)

# the pens whose fence is higher: goats and frogs leap
TALL = {"goat pen": 3, "frog pond": 3}


def gate_x(name: str) -> int:
    """the x of a pen's gate, in the middle of its north side"""
    (x1, _z1, x2, _z2), _ = PENS[name]
    return (x1 + x2) // 2


def fence_ring(name: str) -> None:
    (x1, z1, x2, z2), _ = PENS[name]
    tall = TALL.get(name, 1)
    for y in range(tall):
        L.fill(V(x1, y, z1), V(x2, y, z1), FENCE)
        L.fill(V(x1, y, z2), V(x2, y, z2), FENCE)
        L.fill(V(x1, y, z1), V(x1, y, z2), FENCE)
        L.fill(V(x2, y, z1), V(x2, y, z2), FENCE)
    if tall > 1:
        # goats and frogs leap higher than any fence a visitor would like
        # to look over: an invisible barrier rises above theirs
        for y in range(tall, tall + 5):
            L.fill(V(x1, y, z1), V(x2, y, z1), "minecraft:barrier")
            L.fill(V(x1, y, z2), V(x2, y, z2), "minecraft:barrier")
            L.fill(V(x1, y, z1), V(x1, y, z2), "minecraft:barrier")
            L.fill(V(x2, y, z1), V(x2, y, z2), "minecraft:barrier")
    gx = gate_x(name)
    L.set_block(V(gx, 0, z1), GATE)
    if tall > 1:  # a lintel over the gate, so that the upper fence ends
        L.fill(
            V(gx, 1, z1), V(gx, tall - 1, z1), "minecraft:stripped_spruce_log[axis=x]"
        )


def furniture(name: str, shelter: bool = True) -> list[tuple[int, int]]:
    """trough, hay, shelter and lantern; returns the cells they take.
    Nothing stands next to the fence: an animal on a block beside it could
    step over it"""
    (x1, z1, x2, z2), _ = PENS[name]
    taken = []
    # a water trough (cauldrons) near the west fence, hay near the east
    for z in (z1 + 2, z1 + 3):
        L.set_block(V(x1 + 2, 0, z), "minecraft:water_cauldron[level=3]")
        taken.append((x1 + 2, z))
    L.set_block(V(x2 - 2, 0, z1 + 2), "minecraft:hay_block")
    taken.append((x2 - 2, z1 + 2))
    if shelter:
        # a lean-to roof in the south-east corner on four posts
        sx1, sz1, sx2, sz2 = x2 - 5, z2 - 4, x2 - 2, z2 - 2
        for x, z in ((sx1, sz1), (sx2, sz1), (sx1, sz2), (sx2, sz2)):
            L.fill(V(x, 0, z), V(x, 1, z), FENCE)
            taken.append((x, z))
        L.fill(V(sx1, 2, sz1), V(sx2, 2, sz2), "minecraft:spruce_slab[type=bottom]")
        L.set_block(V(sx1 + 1, 1, sz1 + 1), f"{L.LANTERN}[hanging=true]")
    # a lantern on a post in the middle (on the ground beside the frogs'
    # pond, two blocks in from the fence, where a frog on it cannot leap out)
    if name == "frog pond":
        L.set_block(V(x1 + 2, 0, z2 - 2), L.LANTERN)
        taken.append((x1 + 2, z2 - 2))
    else:
        cx, cz = (x1 + x2) // 2, (z1 + z2) // 2
        L.fill(V(cx, 0, cz), V(cx, 1, cz), FENCE)
        L.set_block(V(cx, 2, cz), L.LANTERN)
        taken.append((cx, cz))
    return taken


def animals(name: str, taken: list[tuple[int, int]], extra: str = "") -> None:
    """summon a pen's animals on free cells inside its fence"""
    (x1, z1, x2, z2), kinds = PENS[name]
    free = [
        (x, z)
        for x in range(x1 + 2, x2 - 1)
        for z in range(z1 + 2, z2 - 1)
        if (x, z) not in taken
    ]
    _rng.shuffle(free)
    for what, n in kinds.items():
        kind, *young = what.split()
        for k in range(n):
            x, z = free.pop()
            nbt = [L.PERSIST]
            if young:
                nbt.append(YOUNG)
            if kind == "sheep":
                nbt.append(f"Color:{(0, 14, 15, 12, 8)[k % 5]}b")
            if kind == "frog":
                nbt.append(
                    f'variant:"minecraft:{("temperate", "warm", "cold")[k % 3]}"'
                )
            if extra:
                nbt.append(extra)
            L.summon(kind, V(x, 0, z) + Vec3(0.5, 0, 0.5), ",".join(nbt))


def pig_wallow() -> None:
    (x1, z1, x2, z2), _ = PENS["pig pen"]
    L.fill(V(x1 + 2, -1, z2 - 6), V(x2 - 2, -1, z2 - 4), "minecraft:mud")


def goat_mound() -> list[tuple[int, int]]:
    """a rocky mound in the goat pen, 1 high, 2 blocks clear of the
    fence (which is 3 high: a goat on the mound cannot leap it)"""
    (x1, z1, x2, z2), _ = PENS["goat pen"]
    cx, cz = (x1 + x2) // 2 + 3, (z1 + z2) // 2
    taken = []
    for h, r in ((0, 1),):
        for x in range(cx - r, cx + r + 1):
            for z in range(cz - r, cz + r + 1):
                L.set_block(
                    V(x, h, z),
                    _rng.choice(
                        (
                            "minecraft:stone",
                            "minecraft:cobblestone",
                            "minecraft:andesite",
                        )
                    ),
                )
                taken.append((x, z))
    return taken


def chicken_coop() -> list[tuple[int, int]]:
    """a little coop with nesting barrels in the run's south-west corner"""
    (x1, z1, x2, z2), _ = PENS["chicken run"]
    cx1, cz1, cx2, cz2 = x1 + 2, z2 - 5, x1 + 6, z2 - 2
    L.fill(V(cx1, 0, cz1), V(cx2, 2, cz2), "minecraft:spruce_planks")
    L.fill(V(cx1 + 1, 0, cz1 + 1), V(cx2 - 1, 1, cz2 - 1), L.AIR)
    L.fill(V(cx1, 3, cz1), V(cx2, 3, cz2), "minecraft:spruce_slab[type=bottom]")
    L.fill(V(cx1 + 1, 0, cz1), V(cx1 + 2, 1, cz1), L.AIR)  # the doorway north
    for x in range(cx1 + 1, cx2):
        L.set_block(V(x, 0, cz2 - 1), "minecraft:barrel[facing=up]")
    L.set_block(V(cx1 + 3, 1, cz1 + 1), f"{L.LANTERN}[hanging=false]")
    return [(x, z) for x in range(cx1, cx2 + 1) for z in range(cz1, cz2 + 1)]


def rabbit_hutch() -> list[tuple[int, int]]:
    """a hutch of trapdoors and a carrot patch"""
    (x1, z1, x2, z2), _ = PENS["rabbit hutch"]
    hx, hz = x1 + 2, z2 - 4
    L.fill(V(hx, 0, hz), V(hx + 2, 0, hz + 1), "minecraft:spruce_planks")
    L.fill(V(hx, 1, hz), V(hx + 2, 1, hz + 1), "minecraft:spruce_trapdoor[half=bottom]")
    L.fill(
        V(x2 - 4, -1, z1 + 2), V(x2 - 2, -1, z1 + 3), "minecraft:farmland[moisture=7]"
    )
    L.fill(V(x2 - 4, 0, z1 + 2), V(x2 - 2, 0, z1 + 3), "minecraft:carrots[age=7]")
    return [(x, z) for x in range(hx, hx + 3) for z in (hz, hz + 1)] + [
        (x, z) for x in range(x2 - 4, x2 - 1) for z in (z1 + 2, z1 + 3)
    ]


def frog_pond() -> list[tuple[int, int]]:
    """a pond with lily pads, reeds and a mossy bank"""
    (x1, z1, x2, z2), _ = PENS["frog pond"]
    px1, pz1, px2, pz2 = x1 + 3, z1 + 2, x2 - 3, z2 - 2
    L.fill(V(px1, -3, pz1), V(px2, -2, pz2), "minecraft:clay")
    L.fill(V(px1, -1, pz1), V(px2, -1, pz2), L.WATER)
    L.fill(V(px1 + 1, -2, pz1 + 1), V(px2 - 1, -2, pz2 - 1), L.WATER)
    for x, z in ((px1 + 1, pz1 + 1), (px2 - 2, pz1 + 2), (px1 + 4, pz2 - 1)):
        L.set_block(V(x, 0, z), "minecraft:lily_pad")
    L.fill(V(x1 + 1, -1, z1 + 1), V(px1 - 1, -1, z2 - 1), "minecraft:moss_block")
    for z in range(pz1, pz2 + 1, 2):
        L.set_block(V(px1 - 1, 0, z), "minecraft:short_grass")
    return [(x, z) for x in range(px1, px2 + 1) for z in range(pz1, pz2 + 1)]


def allotments() -> None:
    """rows of crops with water channels between, and a scarecrow"""
    x1, z1, x2, z2 = GARDEN
    L.fill(V(x1, 0, z1), V(x2, 0, z1), "minecraft:oak_fence")
    L.fill(V(x1, 0, z2), V(x2, 0, z2), "minecraft:oak_fence")
    L.fill(V(x1, 0, z1), V(x1, 0, z2), "minecraft:oak_fence")
    L.fill(V(x2, 0, z1), V(x2, 0, z2), "minecraft:oak_fence")
    L.set_block(V(x1 + 4, 0, z1), "minecraft:oak_fence_gate[facing=north,open=false]")
    crops = ("wheat[age=7]", "carrots[age=7]", "beetroots[age=3]", "potatoes[age=7]")
    k = 0
    for x in range(x1 + 1, x2 - 3, 5):
        L.fill(V(x, -1, z1 + 1), V(x + 3, -1, z2 - 1), "minecraft:farmland[moisture=7]")
        L.fill(V(x, 0, z1 + 1), V(x + 3, 0, z2 - 1), f"minecraft:{crops[k % 4]}")
        L.fill(V(x + 4, -1, z1 + 1), V(x + 4, -1, z2 - 1), L.WATER)  # a channel
        k += 1
    # the scarecrow, on a post in the middle
    sx, sz = (x1 + x2) // 2, (z1 + z2) // 2
    L.set_block(V(sx, 0, sz), "minecraft:oak_fence")
    L.summon(
        "armor_stand",
        V(sx, 1, sz) + Vec3(0.5, 0, 0.5),
        "ShowArms:1b,Rotation:[0f,0f],equipment:{"
        'head:{id:"minecraft:carved_pumpkin",count:1},'
        'chest:{id:"minecraft:leather_chestplate",count:1},'
        'mainhand:{id:"minecraft:wheat",count:1}}',
    )
    for x in (x1 + 2, x2 - 2):
        L.fill(V(x, 0, z1 + 1), V(x, 1, z1 + 1), "minecraft:oak_fence")
        L.set_block(V(x, 2, z1 + 1), L.LANTERN)


def beehives() -> None:
    """hives with bees in them by the upper ward's garden (bees inside a
    hive are not entities, so nothing to count)"""
    bee = '{entity_data:{id:"minecraft:bee"},min_ticks_in_hive:600,ticks_in_hive:0}'
    for x, z in BEEHIVES:
        L.set_block(V(x, YU - 1, z), "minecraft:oak_log")
        try:
            L.set_nbt(
                V(x, YU, z),
                f"minecraft:beehive[facing=south,honey_level=5]{{bees:[{bee},{bee}]}}",
            )
        except RuntimeError as e:  # an empty hive is better than none
            print(f"   bees not accepted ({e}): an empty hive")
            L.set_block(V(x, YU, z), "minecraft:beehive[facing=south,honey_level=5]")
        L.set_block(V(x, YU, z + 1), "minecraft:cornflower")


def clear() -> None:
    """clear the pens and the allotments down to grass, so that the stage
    can be run again"""
    for (x1, z1, x2, z2), _ in PENS.values():
        L.fill(V(x1, 0, z1), V(x2, 8, z2), L.AIR)
        L.fill(V(x1, -3, z1), V(x2, -2, z2), L.STONE)
        L.fill(V(x1, -1, z1), V(x2, -1, z2), "minecraft:grass_block")
    x1, z1, x2, z2 = GARDEN
    L.fill(V(x1, 0, z1), V(x2, 4, z2), L.AIR)
    L.fill(V(x1, -1, z1), V(x2, -1, z2), "minecraft:grass_block")


def pens() -> str:
    clear()
    x1, z1, x2, z2 = PEN_LANE
    L.fill(V(x1, -1, z1), V(x2, -1, z2), "minecraft:dirt_path")
    for name in PENS:
        fence_ring(name)
    special = {
        "pig pen": lambda: (pig_wallow(), [])[1],
        "goat pen": goat_mound,
        "chicken run": chicken_coop,
        "rabbit hutch": rabbit_hutch,
        "frog pond": frog_pond,
    }
    for name in PENS:
        extra = special[name]() if name in special else []
        # no shelter for the goats: from their mound they would climb its
        # roof, and leap the fence from there
        taken = furniture(
            name, shelter=name not in ("chicken run", "frog pond", "goat pen")
        )
        animals(name, taken + (extra or []))
    allotments()
    beehives()
    return f"{len(PENS)} pens"
