"""
The people stage (phase 4): who lives in castle2, from `castle2_layout`.

- Static people (``NoAI``, invulnerable, facing set): the shopkeepers at
  their counters with trades that match their shops, the king and queen on
  their thrones, the cook, the librarian, the monk, the alchemist, the
  blacksmith, the jailer, and drinkers in the tavern. Seated people ride an
  invisible marker armour stand on their seat.
- Mobile ones: nitwits and children (kept young) round the market square,
  with a bell at the cross for their meeting point; cats; chickens loose in
  the square; a copper golem sorting the market's chests.
- Guards: posed armour stands with spears on the wall walks, the gatehouse
  and the keep's roof, the captain and the gate sergeant named.

Everything is tagged (castle_lib.summon) and persistent. Villagers with
beds and workstations about can bring stray cats and iron golems: those
are untagged, and `kill_strays` removes them from the site.
"""

from __future__ import annotations

import castle2_layout as C
import castle_lib as L
from castle2_layout import KEEP, KEEP_ROOF, SQUARE, WALL_H, YU, ZS, V

from mciwb.imports import Vec3

YAW = {"south": 0, "west": 90, "north": 180, "east": -90}
STATIC = "NoAI:1b,Invulnerable:1b,Silent:1b,PersistenceRequired:1b"

# what each profession sells: (price in emeralds, item, how many)
TRADES = {
    "baker": [
        (1, "bread", 6),
        (1, "cake", 1),
        (1, "pumpkin_pie", 4),
        (1, "cookie", 12),
    ],
    "butcher": [
        (1, "cooked_porkchop", 5),
        (1, "cooked_beef", 5),
        (1, "rabbit_stew", 1),
    ],
    "tailor": [(2, "white_wool", 8), (3, "leather_chestplate", 1), (1, "shears", 1)],
    "apothecary": [(3, "potion", 1), (2, "glowstone_dust", 4), (1, "glass_bottle", 4)],
    "candlemaker": [(1, "candle", 4), (1, "white_candle", 4), (2, "honeycomb", 3)],
    "carpenter": [(1, "oak_planks", 16), (1, "spruce_log", 8), (2, "iron_axe", 1)],
    "fletcher": [(1, "arrow", 16), (2, "bow", 1), (3, "crossbow", 1)],
    "cartographer": [(2, "map", 1), (3, "compass", 1), (1, "paper", 8)],
    "cobbler": [(2, "leather_boots", 1), (5, "iron_boots", 1), (1, "leather", 4)],
    "weaver": [(1, "white_carpet", 8), (2, "blue_wool", 8), (1, "string", 6)],
    "tavern": [(1, "honey_bottle", 2), (1, "bread", 4), (1, "cooked_beef", 2)],
    "blacksmith": [
        (3, "iron_sword", 1),
        (4, "iron_helmet", 1),
        (5, "iron_chestplate", 1),
    ],
    "librarian": [(5, "book", 1), (8, "enchanted_book", 1), (2, "lantern", 1)],
    "alchemist": [(4, "potion", 1), (8, "experience_bottle", 2), (3, "ender_pearl", 1)],
}
# the profession (villager data) and a name for each keeper
KEEPER = {
    "baker": ("farmer", "Bertha the Baker"),
    "butcher": ("butcher", "Hob the Butcher"),
    "tailor": ("shepherd", "Agnes the Tailor"),
    "apothecary": ("cleric", "Ambrose the Apothecary"),
    "candlemaker": ("cleric", "Cecily Chandler"),
    "carpenter": ("mason", "Walter Wright"),
    "fletcher": ("fletcher", "Robin the Fletcher"),
    "cartographer": ("cartographer", "Mercator"),
    "cobbler": ("leatherworker", "Tom Cobbler"),
    "weaver": ("shepherd", "Joan Webster"),
    "tavern": ("butcher", "Old Ned the Innkeeper"),
}


def offers(trades: list[tuple[int, str, int]]) -> str:
    recipes = ",".join(
        f'{{buy:{{id:"minecraft:emerald",count:{price}}},'
        f'sell:{{id:"minecraft:{item}",count:{n}}},maxUses:9999,rewardExp:0b}}'
        for price, item, n in trades
    )
    return f"Offers:{{Recipes:[{recipes}]}}"


def villager(profession: str, name: str = "", level: int = 5) -> str:
    data = f'VillagerData:{{profession:"minecraft:{profession}",level:{level},type:"minecraft:plains"}}'
    return data + (f',CustomName:"{name}"' if name else "")


def stand_at(pos: Vec3, facing: str, nbt: str) -> None:
    """a static villager standing at pos (a block position), facing"""
    L.summon(
        "villager",
        pos + Vec3(0.5, 0, 0.5),
        f"{STATIC},Rotation:[{YAW[facing]}f,0f],{nbt}",
    )


def sit_at(pos: Vec3, facing: str, nbt: str) -> None:
    """a static villager seated on the stair at pos: riding an invisible
    marker armour stand at the top of the stair's lower half"""
    rider = f'{{id:"minecraft:villager",Tags:["{L.TAG}","{L.TAG}.{L.STAGE}"],{STATIC},Rotation:[{YAW[facing]}f,0f],{nbt}}}'
    L.summon(
        "armor_stand",
        pos + Vec3(0.5, 0.35, 0.5),
        f"Invisible:1b,Marker:1b,NoGravity:1b,Invulnerable:1b,Rotation:[{YAW[facing]}f,0f],Passengers:[{rider}]",
    )


# ---- the static people of the castle (local block positions)
KX1, KZ1, KX2, KZ2 = KEEP
IX1, IZ1, IX2, IZ2 = KX1 + 3, KZ1 + 3, KX2 - 3, KZ2 - 3
CASTLE_PEOPLE = [
    # (what, local position, facing, seated, profession, name, trades)
    ("king", (IX1 + 1, YU + 1, 26), "east", True, "librarian", "King Edmund", None),
    ("queen", (IX1 + 1, YU + 1, 28), "east", True, "cleric", "Queen Matilda", None),
    ("cook", (72, YU, 17), "north", False, "butcher", "Martha the Cook", None),
    (
        "librarian",
        (50, YU + 10, 25),
        "north",
        False,
        "librarian",
        "Brother Bede",
        "librarian",
    ),
    ("monk", (98, YU + 1, 17), "south", False, "cleric", "Father Anselm", None),
    (
        "alchemist",
        (16, YU, 21),
        "west",
        False,
        "cleric",
        "Master Paracelsus",
        "alchemist",
    ),
    (
        "blacksmith",
        (107, 0, 101),
        "east",
        False,
        "weaponsmith",
        "Godric the Smith",
        "blacksmith",
    ),
    ("jailer", (93, -8, 137), "east", True, "nitwit", "Grimsby the Jailer", None),
]
# the mobile people and creatures round the square (local block positions)
SX1, SZ1, SX2, SZ2 = SQUARE
WANDERERS = [(48, 150), (72, 150), (47, 163), (73, 163), (56, 160), (64, 150)]
CHILDREN = [(50, 160), (70, 161), (55, 149)]
CATS = [(46, 158), (74, 152)]
CHICKENS = [(49, 152), (50, 153), (71, 160), (72, 159)]
BELL = (55, 156)  # the villagers' meeting point, by the market cross
COPPER_GOLEM = (76, 214)  # by the market stalls and their chests
MARKET_CHESTS = [(75, 210), (77, 210)]  # a copper chest and a chest
GUARDS = [
    # (local position, facing, name)
    ((30, WALL_H, ZS - 2), "south", ""),
    ((90, WALL_H, ZS - 2), "south", ""),
    ((2, WALL_H, 140), "west", ""),
    ((118, WALL_H, 140), "east", ""),
    ((2, WALL_H, 195), "west", ""),
    ((118, WALL_H, 195), "east", ""),
    ((60, YU + WALL_H, 2), "north", ""),
    ((60, 16, ZS - 4), "south", "Sergeant Ward"),
    ((60, KEEP_ROOF, KZ2 - 5), "south", "Captain Aldric"),
]


def guard(pos: Vec3, facing: str, name: str) -> None:
    eq = (
        'head:{id:"minecraft:iron_helmet",count:1},'
        'chest:{id:"minecraft:chainmail_chestplate",count:1},'
        'legs:{id:"minecraft:chainmail_leggings",count:1},'
        'feet:{id:"minecraft:iron_boots",count:1},'
        'mainhand:{id:"minecraft:iron_spear",count:1},'
        'offhand:{id:"minecraft:shield",count:1}'
    )
    named = f',CustomName:"{name}",CustomNameVisible:1b' if name else ""
    L.summon(
        "armor_stand",
        pos + Vec3(0.5, 0, 0.5),
        f"ShowArms:1b,Invulnerable:1b,Rotation:[{YAW[facing]}f,0f],"
        f"Pose:{{RightArm:[-60f,0f,10f],LeftArm:[-20f,0f,-10f]}},equipment:{{{eq}}}{named}",
    )


def counts() -> dict[str, int]:
    """what the stage summons, by entity type (castle_layout.SUMMONED)"""
    houses = C.village_houses()
    keepers = sum(
        1 for h in houses.values() if "counter" in h.stands and h.contents in KEEPER
    )
    tavern = houses.get("tavern")
    drinkers = min(3, len(tavern.seats)) if tavern else 0
    seated = sum(1 for p in CASTLE_PEOPLE if p[3]) + drinkers
    villagers = len(CASTLE_PEOPLE) + keepers + drinkers + len(WANDERERS) + len(CHILDREN)
    return {
        "villager": villagers,
        "armor_stand": seated + len(GUARDS),
        "cat": len(CATS),
        "chicken": len(CHICKENS),
        "copper_golem": 1,
    }


def people() -> str:
    # the castle's people
    for _what, (x, y, z), facing, seated, profession, name, trades in CASTLE_PEOPLE:
        nbt = villager(profession, name) + (
            f",{offers(TRADES[trades])}" if trades else ""
        )
        (sit_at if seated else stand_at)(V(x, y, z), facing, nbt)
    # the shopkeepers, at their counters facing the street, and the drinkers
    houses = C.village_houses()
    for h in houses.values():
        if "counter" in h.stands and h.contents in KEEPER:
            profession, name = KEEPER[h.contents]
            nbt = villager(profession, name) + f",{offers(TRADES[h.contents])}"
            stand_at(h.stands["counter"], h.facing, nbt)
    tavern = houses.get("tavern")
    if tavern:
        for k, (p, looks) in enumerate(tavern.seats[:3]):
            sit_at(p, looks, villager("nitwit", ("Wat", "Piers", "Old Gib")[k], 1))
    # the meeting point, the wanderers, the children, cats and chickens
    bx, bz = BELL
    L.set_block(V(bx, 0, bz), "minecraft:bell[attachment=floor,facing=east]")
    for x, z in WANDERERS:
        L.summon(
            "villager",
            V(x, 0, z) + Vec3(0.5, 0, 0.5),
            f"{L.PERSIST},{villager('nitwit', level=1)}",
        )
    for x, z in CHILDREN:
        L.summon(
            "villager",
            V(x, 0, z) + Vec3(0.5, 0, 0.5),
            f"{L.PERSIST},Age:-24000,AgeLocked:1b,{villager('nitwit', level=1)}",
        )
    for k, (x, z) in enumerate(CATS):
        variant = ("tabby", "black")[k % 2]
        L.summon(
            "cat",
            V(x, 0, z) + Vec3(0.5, 0, 0.5),
            f'{L.PERSIST},variant:"minecraft:{variant}"',
        )
    for x, z in CHICKENS:
        L.summon("chicken", V(x, 0, z) + Vec3(0.5, 0, 0.5), L.PERSIST)
    # the copper golem and the market's chests
    (cx, cz), (dx, dz) = MARKET_CHESTS
    L.set_block(V(cx, 0, cz), "minecraft:copper_chest[facing=south]")
    L.set_block(V(dx, 0, dz), "minecraft:chest[facing=south]")
    gx, gz = COPPER_GOLEM
    L.summon("copper_golem", V(gx, 0, gz) + Vec3(0.5, 0, 0.5), L.PERSIST)
    # the guards
    for (x, y, z), facing, name in GUARDS:
        guard(V(x, y, z), facing, name)
    kill_strays()
    return f"{sum(counts().values())} people and creatures"


def kill_strays() -> None:
    """the cats and iron golems that villages bring, and wild animals of
    the kinds the castle keeps that have wandered into the site: not ours"""
    a, b = C.site_box()
    for kind in ("cat", "iron_golem", *C.pen_animals()):
        L.cmd(f"kill @e[type=minecraft:{kind},tag=!{L.TAG},{L.box_selector(a, b)}]")
