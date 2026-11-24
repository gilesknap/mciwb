"""
What castle2's chests, barrels and droppers hold: one table per container,
used by the stage that builds it, by the reset that fills it again
(play.py) and by verify. A stack is ``(item, count)`` or ``(item, count,
components)``, the components as SNBT (`named`, `PICK_COMPONENTS`); stacks
fill a container from slot 0.

The trail's books lie in slot `NOTE_SLOT` of the chests that hold one
(clues.py puts them there; ``items(stacks, note=...)`` gives the chest
with its book, for the master copies of the command bank).
"""

from __future__ import annotations

import castle_lib as L

NOTE_SLOT = 13  # the middle of a chest: the stacks fill it from slot 0
# the one block the prospector's pick breaks: the caches' walls, used
# nowhere else in the castle (verify counts them in the build)
WEAK_WALL = "minecraft:cracked_deepslate_bricks"

Stack = tuple  # (item, count) or (item, count, components SNBT)


def named(name: str) -> str:
    """an item's components for a custom name"""
    return f'{{"minecraft:custom_name":{L.snbt_string(name)}}}'


def stack(slot: int, item: str, count: int, components: str = "") -> str:
    """one stack in a slot, as SNBT"""
    extra = f",components:{components}" if components else ""
    return f'{{Slot:{slot}b,id:"minecraft:{item}",count:{count}{extra}}}'


def items(stacks: list[Stack], note: str = "") -> str:
    """a container's ``Items`` list, as SNBT; ``note``: a whole item's SNBT
    (a written book, clues.book_snbt) for slot `NOTE_SLOT`"""
    out = [stack(slot, *s) for slot, s in enumerate(stacks)]
    if note:
        out.append(f"{{Slot:{NOTE_SLOT}b,{note[1:]}")
    return "[" + ",".join(out) + "]"


def container(block: str, stacks: list[Stack], note: str = "") -> str:
    """a container block (``minecraft:chest[facing=east]``) with its stacks"""
    return f"{block}{{Items:{items(stacks, note)}}}"


PICK = "iron_pickaxe"
PICK_NAME = "The Prospector's Pick"
PICK_COMPONENTS = (
    f'{{"minecraft:can_break":{{blocks:"{WEAK_WALL}"}},'
    f'"minecraft:custom_name":{L.snbt_string(PICK_NAME)},'
    '"minecraft:unbreakable":{},'
    '"minecraft:lore":["Breaks cracked dark brick,","and nothing else.",'
    '"There is always something","behind a crack."]}'
)

# ---- the secrets' rewards (the trail's books lie in their middle slots)
RELIQUARY = [
    ("golden_apple", 2),
    ("echo_shard", 3),
    ("recovery_compass", 1),
    ("paper", 1, named("The founder: the miller keeps a way below")),
    (PICK, 1, PICK_COMPONENTS),
]
STUDY = [
    ("amethyst_shard", 4),  # the transmuter's ingredient
    ("diamond", 6),
    ("gold_ingot", 12),
    ("map", 1),
    ("spyglass", 1),
]
CELLAR = [
    ("amethyst_shard", 4),
    ("blaze_rod", 3),
    ("experience_bottle", 16),
    ("golden_apple", 2),
    ("ender_pearl", 4),
]
CHAMBER = [
    ("music_disc_otherside", 1),
    ("enchanted_golden_apple", 1),
    ("diamond", 8),
    ("emerald", 16),
    ("golden_helmet", 1),
]
# the end of the trail: the best of the old vault's treasure
INNER_VAULT = [
    ("nether_star", 1),
    ("elytra", 1),
    ("trident", 1),
    ("netherite_ingot", 4),
    ("enchanted_golden_apple", 2),
    ("totem_of_undying", 1),
    ("heart_of_the_sea", 1),
    ("diamond_block", 8),
]
# the main vault, which three easy ways lead into: a respectable hoard,
# without what the inner vault now keeps. By the chest's x (local), west
# to east along the north wall
MAIN_VAULT = {
    54: [("diamond", 12), ("emerald", 24), ("gold_ingot", 64)],
    56: [("gold_block", 8), ("emerald_block", 2), ("lapis_block", 4)],
    58: [("golden_apple", 4), ("experience_bottle", 16), ("saddle", 1)],
    62: [("diamond_sword", 1), ("diamond_chestplate", 1), ("golden_apple", 4)],
    64: [("music_disc_pigstep", 1), ("amethyst_shard", 32), ("echo_shard", 4)],
    66: [("diamond", 8), ("gold_ingot", 32), ("emerald", 16)],
}

# ---- the archery range
ARCHERY_CACHE = [
    ("spectral_arrow", 32),
    ("bow", 1),
    ("arrow", 64),
    ("paper", 1, named("Stop the wheel? No: the sluice opens the stones")),
]
ARCHERY_KIT = [("bow", 1), ("bow", 1), ("bow", 1), ("arrow", 64)]
ARCHERY_ARROWS = [("arrow", 64)] * 9  # the dropper at the line

# ---- the restless dead: what the sexton leaves by the door for the unarmed
SEXTON = [
    ("stone_sword", 1),
    ("stone_sword", 1),
    ("shield", 1),
    ("shield", 1),
    ("bread", 8),
    ("paper", 1, named("The sexton: take a blade, and leave it for the next")),
]
# what each wave pays when its last is dead (item, count, components)
WAVE_REWARDS = [
    [("emerald", 4)],
    [("emerald", 6)],
    [
        (
            "diamond_sword",
            1,
            '{"minecraft:custom_name":"Gravebane",'
            '"minecraft:enchantments":{"minecraft:smite":3}}',
        ),
        ("emerald", 10),
    ],
]

# ---- the caches behind the weak walls (play.CACHES says where)
CACHES = {
    "the restless dead": [("emerald", 8), ("golden_apple", 1), ("bone", 12)],
    "the miller's way": [("emerald", 6), ("bread", 12), ("cooked_beef", 6)],
    "the guard room": [("emerald", 6), ("iron_sword", 1), ("arrow", 32)],
    "the alchemist's cellar": [
        ("emerald", 6),
        ("ender_pearl", 2),
        ("experience_bottle", 8),
    ],
}
# castle's lower treasury (its build_inner.catacombs fills these two chests;
# the reset fills them again from here), by the chest's x (local)
LOWER_TREASURY = {
    103: [
        ("gold_ingot", 24),
        ("emerald", 10),
        ("iron_ingot", 32),
        ("golden_apple", 2),
        ("diamond", 3),
    ],
    105: [
        ("bow", 1),
        ("arrow", 64),
        ("spectral_arrow", 16),
        ("leather_chestplate", 1),
    ],
}
