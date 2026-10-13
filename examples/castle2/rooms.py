"""
castle2's furnishing (phase 5): every room in full detail. castle builds
the rooms (its ``*_shell`` functions); castle2 furnishes them its own way
in place of castle's ``*_furnishing`` (see build_castle2's stages).

Every seat goes through `castle_lib.seat`, given the way its sitter looks,
and verify_castle2 reads each one back. Renders draw stairs as full blocks,
so they cannot show which way a seat faces: that check can.

Rooms (local coordinates, castle's layout): the keep's great hall, kitchen,
library, gallery and armoury, the lord's bedchamber, the solar, the map
room, the guest room, the nursery and the privy; the chapel and its crypt;
the barracks and its training yard, the stables, the smithy; detail in the
alchemist's tower, the dungeon, the vault and the winch room.

Kept clear for the machines of phase 6 (local coordinates):

- the chapel's north wall west of the altar, x 87..92 (z 14, y 18..23),
  and the floor before it (x 87..92, z 15..21): the organ;
- the library's east wall (castle's bookshelf wall, x 58) from z 28 to 38
  and the floor before it (x 54..57, z 28..38): the lectern lock and a
  hidden door;
- the barracks yard east of the training ground, x 37..55, z 66..86: the
  archery range;
- the alchemist's tower: castle2 adds only a powder snow cauldron and
  specimen jars (ground floor), a parrot and a star chart on the south
  wall (second floor); the third floor's walls are bare;
- the vault's west wall (x 50, z 18..28) and the catacombs, which castle2
  does not furnish.

`KEYS` and `KEY_ENTITIES` list the key pieces (the kitchen's hearth and
oven, the effigies, the dummies, the beds ...) for verify_castle2's rooms
check.
"""

from __future__ import annotations

import random

import castle_lib as L
from build_inner import (
    F1,
    F2,
    F3,
    FR,
    IX1,
    IX2,
    IZ1,
    IZ2,
    armour_stand,
    bed,
    carpet,
    chest,
    item_frame,
    table,
)
from castle2_layout import BANNER, BANNER2, CHAPEL, V

from mciwb.builders import column
from mciwb.imports import Vec3

_rng = random.Random(173)
YAW = {"south": 0, "west": 90, "north": 180, "east": -90}
STATIC = "NoAI:1b,Invulnerable:1b,Silent:1b,PersistenceRequired:1b"
# a painting's facing is a horizontal direction: 0 south, 1 west, 2 north,
# 3 east (an item frame's is a 3D one: 2 north, 3 south, 4 west, 5 east)
PAINTING_FACING = {"south": 0, "west": 1, "north": 2, "east": 3}

# the key pieces of the rooms, which verify_castle2's rooms check reads back:
# (what, world position, block) and (what, entity type, box corners)
KEYS: list[tuple[str, Vec3, str]] = []
KEY_ENTITIES: list[tuple[str, str, Vec3, Vec3]] = []


# ---------------------------------------------------------------- helpers


def key(what: str, pos: Vec3, block: str) -> None:
    """place a block that the rooms check reads back"""
    L.set_block(pos, block)
    KEYS.append((what, pos, block))


def key_entities(
    what: str, kind: str, a: tuple[int, int, int], b: tuple[int, int, int]
) -> None:
    """the rooms check counts the entities of a kind in a box (local corners)"""
    KEY_ENTITIES.append((what, kind, V(*a), V(*b)))


def hanging_frame(pos: Vec3, item: str) -> None:
    """an invisible item frame under the block above pos: the item hangs"""
    L.summon(
        "item_frame",
        pos,
        f'Facing:0b,Invisible:1b,Item:{{id:"minecraft:{item}",count:1}}',
    )


def tapestry(
    pos: Vec3, facing: str, colour: str, patterns: list[tuple[str, str]]
) -> None:
    """a wall banner with patterns: [(pattern, colour) ...], e.g. ("border", "yellow")"""
    pats = ",".join(f'{{color:"{c}",pattern:"minecraft:{p}"}}' for p, c in patterns)
    L.set_block(
        pos, f"minecraft:{colour}_wall_banner[facing={facing}]{{patterns:[{pats}]}}"
    )


def shelf(pos: Vec3, facing: str, items: list[str]) -> None:
    """a shelf showing up to three items"""
    slots = ",".join(
        f'{{Slot:{k}b,id:"minecraft:{item}",count:1}}'
        for k, item in enumerate(items[:3])
    )
    L.set_block(pos, f"minecraft:spruce_shelf[facing={facing}]{{Items:[{slots}]}}")


def book_lectern(
    pos: Vec3, facing: str, title: str, author: str, pages: list[str]
) -> None:
    """a lectern holding a written book"""
    text = ",".join('"' + p.replace('"', "'") + '"' for p in pages)
    book = (
        f'{{id:"minecraft:written_book",count:1,components:{{"minecraft:written_book_content":'
        f'{{title:"{title}",author:"{author}",pages:[{text}]}}}}}}'
    )
    L.set_block(pos, f"minecraft:lectern[facing={facing},has_book=true]{{Book:{book}}}")


def bookcase(pos: Vec3, facing: str, books: int) -> None:
    """a chiseled bookshelf holding its first ``books`` books"""
    props = ",".join(
        f"slot_{k}_occupied={'true' if k < books else 'false'}" for k in range(6)
    )
    items = ",".join(f'{{Slot:{k}b,id:"minecraft:book",count:1}}' for k in range(books))
    L.set_block(
        pos, f"minecraft:chiseled_bookshelf[facing={facing},{props}]{{Items:[{items}]}}"
    )


def painting(pos: Vec3, facing: str, variant: str) -> None:
    """a 1x1 painting hung in the cell at pos, on the wall behind it"""
    L.summon(
        "painting",
        pos,
        f'facing:{PAINTING_FACING[facing]}b,variant:"minecraft:{variant}"',
    )


def person(pos: Vec3, facing: str, profession: str, name: str = "") -> None:
    """a villager standing still at a block position"""
    named = f',CustomName:"{name}"' if name else ""
    L.summon(
        "villager",
        pos + Vec3(0.5, 0, 0.5),
        f"{STATIC},Rotation:[{YAW[facing]}f,0f],"
        f'VillagerData:{{profession:"minecraft:{profession}",level:2,type:"minecraft:plains"}}{named}',
    )


def hound(pos: Vec3, facing: str, variant: str) -> None:
    L.summon(
        "wolf",
        pos + Vec3(0.5, 0, 0.5),
        f'{STATIC},Rotation:[{YAW[facing]}f,0f],variant:"minecraft:{variant}"',
    )


def free(x: int, y: int, z: int, taken: set) -> bool:
    return (x, y, z) not in taken


def rushes(
    x1: int, z1: int, x2: int, z2: int, y: int, keep_clear: set, density: float = 0.18
) -> None:
    """rushes strewn on a floor: green and yellow carpet here and there"""
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            if (x, z) not in keep_clear and _rng.random() < density:
                L.set_block(
                    V(x, y, z),
                    _rng.choice(("minecraft:moss_carpet", "minecraft:yellow_carpet")),
                )


# ---------------------------------------------------------------- the keep


def interiors_furnishing() -> None:
    """castle2's furniture for the keep's rooms (`build_inner.interiors_shell`)"""
    great_hall()
    kitchen()
    library()
    armoury()
    chambers()
    for x in (IX1 + 4, IX2 - 4):  # the roof terrace's braziers
        for z in (IZ1 + 4, IZ2 - 4):
            L.set_block(V(x, FR + 1, z), "minecraft:campfire[lit=true]")


def great_hall() -> None:
    """thrones and a high table on the dais, long tables with benches,
    columns, tapestries, a fireplace with a spit and hounds before it,
    rushes on the floor, a minstrels' gallery and servants"""
    y = F1 + 1
    d = y + 1  # standing on the dais
    # the thrones and the nobles' seats at the high table, looking down the hall
    for z in (24, 26, 28, 30):
        L.seat(V(IX1 + 1, d, z), "east")
    table(V(IX1 + 2, d, 24), V(IX1 + 2, d, 30))
    L.set_block(V(IX1 + 2, d + 1, 27), "minecraft:cake")
    for z in (25, 29):
        L.set_block(V(IX1 + 2, d + 1, z), "minecraft:white_candle[candles=3,lit=true]")
    for z in (24, 30):
        L.set_block(V(IX1 + 2, d + 1, z), "minecraft:decorated_pot[facing=east]")
    for z in (26, 28):
        L.set_block(V(IX1, d + 1, z), f"minecraft:{BANNER}_wall_banner[facing=east]")
    L.set_block(V(IX1, d + 2, 27), "minecraft:gold_block")
    # the aisle from the great door to the dais step
    carpet(IX1 + 5, 26, 61, 28, y, "red")
    carpet(59, 29, 61, IZ2, y, "red")
    # four columns either side of the aisle, chandeliers between them
    for x in (50, 56):
        for z in (23, 31):
            column(V(x, y, z), 9, L.BRICK, plinth=L.CHISELED, capital=L.CHISELED)
    for x in (53, 63):
        L.fill(V(x, y + 7, 27), V(x, y + 8, 27), L.CHAIN)
        L.set_block(V(x, y + 6, 27), f"{L.LANTERN}[hanging=true]")
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            L.set_block(V(x + dx, y + 6, 27 + dz), "minecraft:dark_oak_fence")
            L.set_block(
                V(x + dx, y + 7, 27 + dz), "minecraft:white_candle[candles=2,lit=true]"
            )
    # long tables with benches, west and east of the aisle
    taken = set()
    for z in (19, 35):
        for x1, x2 in ((48, 57), (63, 65)):
            table(V(x1, y, z), V(x2, y, z))
            L.seat(V(x1, y, z - 1), "south", V(x2, y, z - 1))
            L.seat(V(x1, y, z + 1), "north", V(x2, y, z + 1))
            for x in range(x1, x2 + 1):
                taken |= {(x, z - 1), (x, z), (x, z + 1)}
            for x in range(x1 + 1, x2, 3):
                L.set_block(
                    V(x, y + 1, z), "minecraft:white_candle[candles=3,lit=true]"
                )
        L.set_block(V(52, y + 1, z), "minecraft:cake")
        L.set_block(V(55, y + 1, z), "minecraft:decorated_pot")
    # the fireplace: a spit over the fire, a pot, and two hounds before it
    L.set_block(V(53, y, IZ1 - 2), "minecraft:lightning_rod[facing=up]")
    L.set_block(V(55, y, IZ1 - 2), "minecraft:lightning_rod[facing=up]")
    L.set_block(V(54, y + 1, IZ1 - 2), "minecraft:lightning_rod[facing=east]")
    L.set_block(V(52, y, IZ1 - 1), "minecraft:water_cauldron[level=2]")
    hound(V(53, y, IZ1 + 1), "north", "pale")
    hound(V(55, y, IZ1 + 1), "north", "woods")
    # tapestries on the south, north and west walls, between the windows
    designs = [
        (BANNER, [("border", "yellow"), ("cross", "white"), ("circle", "yellow")]),
        (
            BANNER2,
            [
                ("stripe_center", "white"),
                ("triangle_top", "yellow"),
                ("border", "black"),
            ],
        ),
        ("purple", [("rhombus", "yellow"), ("border", "yellow"), ("flower", "white")]),
        ("green", [("gradient", "lime"), ("border", "brown"), ("skull", "black")]),
    ]
    for k, x in enumerate(range(IX1 + 2, 67, 6)):
        colour, pats = designs[k % len(designs)]
        tapestry(V(x, y + 4, IZ2), "north", colour, pats)
    for k, x in enumerate((50, 56, 62)):
        colour, pats = designs[(k + 1) % len(designs)]
        tapestry(V(x, y + 4, IZ1), "south", colour, pats)
    for z in (22, 32):
        tapestry(
            V(IX1, d + 2, z),
            "east",
            BANNER2,
            [("border", "yellow"), ("mojang", "white")],
        )
    # the minstrels' gallery along the east wall, over the east tables
    L.fill(V(63, y + 4, 30), V(66, y + 4, 38), L.PLANKS)
    L.fill(V(62, y + 5, 30), V(62, y + 5, 38), "minecraft:dark_oak_fence")
    L.fill(V(62, y + 5, 29), V(66, y + 5, 29), "minecraft:dark_oak_fence")
    L.fill(V(66, y, 38), V(66, y + 5, 38), "minecraft:ladder[facing=west]")
    L.set_block(V(66, y + 5, 33), "minecraft:note_block[instrument=harp]")
    L.set_block(V(66, y + 5, 35), "minecraft:jukebox")
    person(V(64, y + 5, 32), "west", "nitwit", "the Lutenist")
    person(V(64, y + 5, 36), "west", "nitwit", "the Piper")
    # servants by the tables
    person(V(58, y, 21), "west", "nitwit", "a servant")
    person(V(58, y, 33), "west", "nitwit", "a servant")
    # rushes on the floor, clear of the aisle, the tables and the dais
    clear = taken | {(x, z) for x in range(IX1 + 4, 62) for z in range(26, 29)}
    clear |= {(x, z) for x in range(58, 63) for z in range(24, IZ2 + 1)}
    clear |= {(x, z) for x in range(59, 62) for z in range(IZ1, IZ1 + 3)}  # the pier
    clear |= {(x, z) for x in range(49, 52) for z in (22, 23, 24, 30, 31, 32)}
    clear |= {(x, z) for x in range(55, 58) for z in (22, 23, 24, 30, 31, 32)}
    clear |= {
        (53, IZ1 + 1),
        (55, IZ1 + 1),
        (58, 21),
        (58, 33),
        (66, 38),
        (66, 20),
        (66, 21),
        (66, 33),
        (66, 34),
    }
    rushes(IX1 + 5, IZ1, 66, IZ2, y, clear)


def kitchen() -> None:
    """the hearth (a spit over the fire under a brick hood, smokers and
    cauldrons either side), a bread oven, a work counter and a long work
    table, a pantry of barrels and shelves, hams and herbs hanging from a
    beam, lanterns on chains; the cook stands at the hearth, (72, 17)
    (people.py). The doorways (x 68, z 20..21; x 70..71, z 27) stay clear."""
    y = F1 + 1
    x1, z1, x2, z2 = 68, IZ1, IX2, 27
    L.fill(V(x1, y, z1), V(x2, F2 - 1, z2), L.AIR)  # a rebuild starts clear
    food = [
        "bread",
        "apple",
        "cooked_beef",
        "carrot",
        "baked_potato",
        "pumpkin_pie",
        "cookie",
        "cooked_mutton",
        "beetroot",
    ]
    # the hearth along the north wall
    row = {
        68: "minecraft:water_cauldron[level=3]",
        69: "minecraft:smoker[facing=south]",
        70: "minecraft:smoker[facing=south]",
        71: "minecraft:campfire[lit=true]",
        72: "minecraft:campfire[lit=true]",
        73: "minecraft:smoker[facing=south]",
        74: "minecraft:water_cauldron[level=2]",
        75: "minecraft:cauldron",
        76: "minecraft:water_cauldron[level=3]",
        77: "minecraft:barrel[facing=south]",
    }
    for x, block in row.items():
        key("the kitchen's hearth", V(x, y, z1), block)
    for x in (68, 69, 70, 73, 74, 75, 76):
        shelf(V(x, y + 1, z1), "south", _rng.sample(food, 3))
    for x in (71, 72):  # the spit over the fire
        key(
            "the kitchen's spit",
            V(x, y + 1, z1),
            "minecraft:lightning_rod[facing=east]",
        )
    L.fill(V(70, y + 2, z1), V(73, y + 3, z1), "minecraft:bricks")  # the hood
    L.fill(V(70, y + 2, z1 + 1), V(73, y + 2, z1 + 1), "minecraft:brick_slab[type=top]")
    L.fill(V(71, y + 4, z1), V(72, F2 - 1, z1), "minecraft:bricks")  # its chimney
    # the bread oven in the south-west corner: a brick dome, its mouth east
    L.fill(V(x1, y, 24), V(x1 + 1, y + 1, 26), "minecraft:bricks")
    key("the bread oven", V(x1 + 1, y, 25), "minecraft:furnace[facing=east,lit=true]")
    L.fill(V(x1, y + 2, 24), V(x1 + 1, y + 2, 26), "minecraft:brick_slab[type=bottom]")
    L.fill(V(x1, y + 2, 25), V(x1, y + 3, 25), "minecraft:brick_wall")
    for h in (0, 1):  # the loaves, cooling on a shelf by the oven
        shelf(V(x1, y + h, 23), "east", ["bread", "bread", "bread"])
    # the work counter by the west wall, between the hearth and the door
    L.fill(V(x1, y, 16), V(x1, y, 18), "minecraft:spruce_slab[type=top]")
    L.set_block(V(x1, y + 1, 16), "minecraft:decorated_pot")
    L.set_block(V(x1, y + 1, 17), "minecraft:potted_red_mushroom")
    L.set_block(V(x1, y + 1, 18), "minecraft:white_candle[candles=2,lit=true]")
    L.set_block(V(x1, y, 19), "minecraft:barrel[facing=up]")
    # the long work table, with a meal being made on it
    table(V(71, y, 20), V(74, y, 21))
    key("the kitchen's work table", V(71, y, 20), "minecraft:dark_oak_slab[type=top]")
    L.set_block(V(71, y + 1, 21), "minecraft:cake")
    L.set_block(V(73, y + 1, 21), "minecraft:melon")
    L.set_block(V(74, y + 1, 20), "minecraft:carved_pumpkin[facing=west]")
    L.set_block(V(72, y + 1, 20), "minecraft:white_candle[candles=2,lit=true]")
    L.set_block(V(73, y + 1, 20), "minecraft:decorated_pot[facing=south]")
    L.set_block(V(72, y + 1, 21), "minecraft:potted_brown_mushroom")
    # lanterns on chains over the table
    for x in (70, 75):
        L.fill(V(x, y + 5, 21), V(x, F2 - 1, 21), L.CHAIN)
        key("the kitchen's lanterns", V(x, y + 4, 21), f"{L.LANTERN}[hanging=true]")
    # hams and fowl hanging from a beam on chains, herbs drying beside them
    # (clear of the ceiling's lanterns at x 71, 77, z 18, 24)
    bz = 23
    L.fill(V(72, y + 6, bz), V(75, y + 6, bz), "minecraft:stripped_spruce_log[axis=x]")
    key("the ham beam", V(73, y + 6, bz), "minecraft:stripped_spruce_log[axis=x]")
    for x in (72, 75):
        L.fill(V(x, y + 7, bz), V(x, F2 - 1, bz), L.CHAIN)
    for x, item in (
        (72, "porkchop"),
        (73, "porkchop"),
        (74, "chicken"),
        (75, "rabbit"),
    ):
        hanging_frame(V(x, y + 5, bz), item)
    key_entities("the hams", "item_frame", (72, y + 5, bz), (75, y + 5, bz))
    for x, z in ((69, 22), (76, 18), (69, 17)):
        L.set_block(V(x, F2 - 1, z), "minecraft:hanging_roots")
    # the pantry along the east wall
    L.fill(V(x2, y, 16), V(x2, y, 20), "minecraft:barrel[facing=west]")
    L.fill(V(x2, y + 1, 17), V(x2, y + 1, 19), "minecraft:barrel[facing=up]")
    key("the pantry", V(x2, y, 17), "minecraft:barrel[facing=west]")
    for z in range(21, 25):
        shelf(V(x2, y, z), "west", _rng.sample(food, 3))
        shelf(V(x2, y + 1, z), "west", _rng.sample(food, 3))
    key("the pantry's shelves", V(x2, y, 22), "minecraft:spruce_shelf[facing=west]")
    chest(
        V(x2, y, 25),
        "west",
        [("bread", 16), ("cooked_beef", 8), ("apple", 16), ("golden_carrot", 4)],
    )
    L.fill(V(x2, y, 26), V(x2, y + 1, z2), "minecraft:barrel[facing=up]")
    L.set_block(V(x2 - 1, y, z2), "minecraft:barrel[facing=up]")
    # sacks of grain, the scraps and the chopping block (an axe in it)
    L.fill(V(74, y, z2), V(75, y, z2), "minecraft:hay_block")
    L.set_block(V(75, y, z2 - 1), "minecraft:hay_block")
    L.set_block(V(75, y + 1, z2), "minecraft:hay_block")
    L.set_block(V(72, y, z2), "minecraft:composter[level=4]")
    L.set_block(V(73, y, z2), "minecraft:stripped_oak_log")
    L.summon(
        "item_frame",
        V(73, y + 1, z2),
        'Facing:1b,Invisible:1b,Item:{id:"minecraft:iron_axe",count:1}',
    )


HISTORY = [
    "A History of Castle Fable II. The castle was raised on the dry plain east of the old roads, by the same masons who built Castle Fable, and twice as large.",
    "Its lords kept their treasure below the keep, and trusted no door to keep it: every way in is hidden, and every hidden way is guarded by a riddle.",
    "The librarian keeps the first riddle. Of the six books on the shelf by the east wall, only the last one tells the truth.",
]


def library() -> None:
    """bookcases round the walls (chiseled ones among them), reading desks
    with chairs, lecterns with written books (the castle's history hints at
    the secret door), a map wall and a globe; the librarian stands at the
    history (people.py)"""
    y = F2 + 1
    x1, z1, x2, z2 = IX1, IZ1, 57, IZ2
    # a rebuild starts clear, under the ceiling's lanterns (library_shell)
    L.fill(V(x1, y, z1), V(x2, F3 - 2, z2), L.AIR)
    carpet(x1, z1, x2, z2, y, "blue")
    windows_z = {18, 19, 24, 25, 30, 31, 36, 37}  # the west wall's windows (from y + 2)
    windows_x = {46, 47, 52, 53}  # the north and south walls' windows
    for z in range(z1, z2 + 1):
        top = 1 if z in windows_z else 2
        for h in range(top + 1):
            if (z + h) % 5 == 0:
                bookcase(V(x1, y + h, z), "east", _rng.randint(2, 6))
            else:
                L.set_block(V(x1, y + h, z), "minecraft:bookshelf")
    for x in range(x1 + 1, x2 + 1):
        top = 1 if x in windows_x else 2
        for zz, facing in ((z1, "south"), (z2, "north")):
            for h in range(top + 1):
                if (x + h) % 4 == 0:
                    bookcase(V(x, y + h, zz), facing, _rng.randint(1, 6))
                else:
                    L.set_block(V(x, y + h, zz), "minecraft:bookshelf")
    # reading desks on rugs, with a chair at each end, and candles
    for z in (21, 27, 33):
        carpet(46, z - 1, 54, z + 1, y, "light_blue")
        table(V(48, y, z), V(52, y, z))
        L.seat(V(47, y, z), "east")
        L.seat(V(53, y, z), "west")
        L.set_block(V(50, y + 1, z), "minecraft:white_candle[candles=2,lit=true]")
    # the lecterns: the castle's history, and a book of the house
    book_lectern(V(50, y, 24), "south", "A History", "Brother Bede", HISTORY)
    book_lectern(
        V(50, y, 30),
        "north",
        "Rules of the Library",
        "Brother Bede",
        ["Speak softly. Return every book to its place, the last one last."],
    )
    L.set_block(V(45, y, 27), "minecraft:enchanting_table")
    L.set_block(V(55, y, 17), "minecraft:cartography_table")
    L.set_block(V(IX1 + 1, y, 37), "minecraft:loom[facing=east]")
    # the scribe's desk in the north-west corner: a candle, ink and a quill
    table(V(45, y, 17), V(46, y, 17))
    key("the scribe's desk", V(46, y, 17), "minecraft:dark_oak_slab[type=top]")
    L.set_block(V(45, y + 1, 17), "minecraft:white_candle[candles=1,lit=true]")
    L.set_block(V(46, y + 1, 17), "minecraft:decorated_pot[facing=south]")
    L.seat(V(45, y, 18), "north")
    for z, item in ((21, "writable_book"), (27, "feather"), (33, "ink_sac")):
        item_frame(V(x1, y + 3, z), 5, item)  # over the west bookcases
    # (the floor x 54..57, z 28..38 by the east wall is kept clear for phase 6)
    # the map wall: maps in frames over the north bookcases, between the windows
    for x in (44, 49, 50, 55):
        item_frame(V(x, y + 3, z1), 3, "map")
    # a globe on a stand: a blue and green banner pattern on a block
    L.set_block(V(45, y, 33), "minecraft:dark_oak_fence")
    L.set_block(V(45, y + 1, 33), "minecraft:lapis_block")


def armoury() -> None:
    """weapon racks (frames and shelves), armour stands in every material,
    a grindstone, anvil and smithing table, practice dummies; the gallery's
    carpet and banners"""
    y = F2 + 1
    x1, z1, x2, _z2 = 68, IZ1, IX2, 27
    L.set_block(V(x1, y, 17), "minecraft:anvil[facing=east]")
    L.set_block(V(x1, y, 18), "minecraft:grindstone[face=floor,facing=east]")
    L.set_block(V(x1, y, 23), "minecraft:smithing_table")
    L.set_block(V(x1, y, 24), "minecraft:fletching_table")
    for i, material in enumerate(
        ("leather", "chainmail", "iron", "golden", "diamond", "netherite", "copper")
    ):
        armour_stand(V(x1 + 1 + i, y, z1 + 1) + Vec3(0.5, 0, 0.5), material, rotation=0)
    weapons = [
        "iron_sword", "diamond_sword", "iron_spear", "bow", "crossbow", "trident",
        "iron_axe", "mace", "shield", "diamond_spear", "golden_sword", "netherite_axe",
    ]  # fmt: skip
    for i, item in enumerate(weapons):
        item_frame(V(x2, y + 1 + i % 2, z1 + 3 + i // 2), 4, item)  # on the east wall
    for z in range(z1 + 3, z1 + 9):
        shelf(
            V(x2, y, z),
            "west",
            _rng.sample(
                ["arrow", "spectral_arrow", "iron_ingot", "flint", "leather", "string"],
                3,
            ),
        )
    # practice dummies: a carved pumpkin on hay on a post, and a target
    for x in (72, 74):
        L.set_block(V(x, y, 22), "minecraft:dark_oak_fence")
        L.set_block(V(x, y + 1, 22), "minecraft:hay_block")
        L.set_block(V(x, y + 2, 22), "minecraft:carved_pumpkin[facing=west]")
    L.set_block(V(76, y, 24), "minecraft:target")
    chest(
        V(69, y, 26),
        "north",
        [("arrow", 64), ("iron_ingot", 32), ("shield", 1), ("iron_helmet", 1)],
    )
    chest(V(72, y, 26), "north", [("iron_spear", 2), ("crossbow", 1), ("arrow", 32)])
    # the gallery between library and armoury: x 63..66, carpet and banners
    for z in range(IZ1 + 1, IZ2, 4):
        L.set_block(V(66, y + 3, z), f"minecraft:{BANNER}_wall_banner[facing=west]")
    carpet(63, IZ1, 66, IZ2, F2 + 1, "red")
    # the gallery's portraits (on the library's partition) and pots on plinths
    for z, variant in ((17, "kebab"), (25, "aztec"), (29, "bomb"), (37, "wasteland")):
        painting(V(63, y + 2, z), "east", variant)
    for z in (23, 31):
        L.set_block(V(63, y, z), "minecraft:chiseled_stone_bricks")
        L.set_block(V(63, y + 1, z), "minecraft:decorated_pot[facing=east]")


def chambers() -> None:
    """the top storey: the lord's bedchamber and the solar (the west half,
    split by a wall of wardrobes), the map room, and the east wing's guest
    room, nursery and privy"""
    y = F3 + 1
    L.fill(V(IX1, y, IZ1), V(57, FR - 1, IZ2), L.AIR)  # a rebuild starts clear
    carpet(IX1, IZ1, 57, IZ2, y, "red")
    # the wardrobe wall between the bedchamber (north) and the solar
    # (south): the way through is by the door, x 54..57
    L.fill(V(IX1, y, 28), V(53, y + 3, 28), "minecraft:spruce_planks")
    L.fill(V(IX1, y + 4, 28), V(53, y + 4, 28), "minecraft:spruce_slab[type=bottom]")
    for x in range(48, 52):  # the wardrobes' doors, on the bedchamber's side
        for h in (0, 1):
            L.set_block(
                V(x, y + h, 27), "minecraft:spruce_trapdoor[facing=north,open=true]"
            )
    key("the wardrobe wall", V(50, y + 2, 28), "minecraft:spruce_planks")
    bedchamber()
    solar()
    map_room()
    east_wing()


def bedchamber() -> None:
    """a four-poster bed, bedside cupboards, chests at its foot, an armoire
    and a dressing table, the lord's desk and his armour, paintings, a rug"""
    y = F3 + 1
    carpet(48, 17, 55, 25, y, "yellow")
    carpet(49, 18, 54, 24, y, "orange")
    carpet(50, 19, 53, 23, y, "red")
    # the four-poster bed, its head to the west wall, a red canopy on posts
    for z in (20, 21):
        bed(V(IX1 + 1, y, z), "west", "red")
    key("the four-poster bed", V(IX1, y, 20), "minecraft:red_bed[part=head]")
    for x, z in ((IX1, 19), (IX1, 22), (IX1 + 2, 19), (IX1 + 2, 22)):
        L.fill(V(x, y, z), V(x, y + 2, z), "minecraft:dark_oak_fence")
    L.fill(V(IX1, y + 3, 19), V(IX1 + 2, y + 3, 22), "minecraft:red_wool")
    key("the bed's canopy", V(IX1 + 1, y + 3, 20), "minecraft:red_wool")
    for z in (20, 21):
        tapestry(
            V(IX1, y + 2, z),
            "east",
            BANNER2,
            [("border", "yellow"), ("flower", "white")],
        )
    for z, top in ((18, "minecraft:white_candle[candles=3,lit=true]"),
                   (23, "minecraft:potted_lily_of_the_valley")):  # fmt: skip
        L.set_block(V(IX1, y, z), "minecraft:barrel[facing=up]")
        L.set_block(V(IX1, y + 1, z), top)
    for z in (20, 21):  # chests at the bed's foot
        chest(
            V(IX1 + 3, y, z),
            "east",
            [("golden_apple", 2), ("gold_ingot", 12), ("emerald", 6), ("book", 3)]
            if z == 20
            else [("white_wool", 8), ("red_wool", 4), ("candle", 6)],
        )
    # the armoire against the north wall (between its windows), doors open
    L.fill(V(48, y, IZ1), V(51, y + 2, IZ1), "minecraft:spruce_planks")
    L.fill(V(48, y + 3, IZ1), V(51, y + 3, IZ1), "minecraft:spruce_slab[type=bottom]")
    for x in range(48, 52):
        for h in (0, 1):
            L.set_block(
                V(x, y + h, IZ1 + 1),
                "minecraft:spruce_trapdoor[facing=south,open=true]",
            )
    key("the armoire", V(49, y + 1, IZ1), "minecraft:spruce_planks")
    # the dressing table, its drawers, mirror and stool
    L.fill(V(55, y, IZ1), V(56, y, IZ1), "minecraft:barrel[facing=south]")
    L.fill(
        V(55, y + 1, IZ1), V(56, y + 2, IZ1), "minecraft:light_blue_stained_glass_pane"
    )
    table(V(55, y, IZ1 + 1), V(56, y, IZ1 + 1))
    L.set_block(V(55, y + 1, IZ1 + 1), "minecraft:potted_allium")
    L.set_block(V(56, y + 1, IZ1 + 1), "minecraft:candle[candles=1,lit=true]")
    L.seat(V(55, y, IZ1 + 2), "north")
    # the lord's desk by the east wall, his treasure chest and his armour
    table(V(57, y, 19), V(57, y, 21))
    L.set_block(V(57, y + 1, 19), "minecraft:white_candle[candles=3,lit=true]")
    L.set_block(V(57, y + 1, 21), "minecraft:decorated_pot[facing=west]")
    L.seat(V(56, y, 20), "east")
    chest(V(57, y, 17), "west", [("gold_block", 4), ("emerald", 16), ("map", 1)])
    armour_stand(V(57, y, 24) + Vec3(0.5, 0, 0.5), "golden", rotation=90)
    # paintings on the north wall and the wardrobe wall
    painting(V(IX1 + 1, y + 2, IZ1), "south", "kebab")
    painting(V(55, y + 3, IZ1), "south", "alban")
    painting(V(IX1 + 1, y + 2, 27), "north", "bomb")
    painting(V(53, y + 2, 27), "north", "plant")


def solar() -> None:
    """the lord and lady's sitting room: armchairs at the fire, a card table,
    the lady's loom and wool, a harp, bookshelves, tapestries, paintings"""
    y = F3 + 1
    carpet(47, 34, 55, IZ2, y, "yellow")
    carpet(48, 35, 54, IZ2, y, "brown")
    # armchairs facing the fireplace in the south wall, a side table between
    for x in (50, 52):
        L.seat(V(x, y, IZ2 - 1), "south")
        L.set_block(V(x, y, IZ2 + 2), "minecraft:campfire[lit=true]")
    L.set_block(V(51, y, IZ2 - 1), "minecraft:spruce_slab[type=top]")
    L.set_block(V(51, y + 1, IZ2 - 1), "minecraft:decorated_pot[facing=south]")
    # the card table, a chair either side
    table(V(IX1 + 1, y, 32), V(IX1 + 2, y, 33))
    L.seat(V(IX1, y, 32), "east", V(IX1, y, 33))
    L.seat(V(IX1 + 3, y, 32), "west", V(IX1 + 3, y, 33))
    L.set_block(V(IX1 + 1, y + 1, 32), "minecraft:white_candle[candles=2,lit=true]")
    L.set_block(V(IX1 + 2, y + 1, 33), "minecraft:potted_azure_bluet")
    # the lady's corner: a loom, a spinning wheel, bales of wool
    key("the lady's loom", V(56, y, 38), "minecraft:loom[facing=north]")
    L.set_block(V(55, y, IZ2), "minecraft:grindstone[face=floor,facing=east]")
    L.fill(V(57, y, 38), V(57, y, IZ2), "minecraft:white_wool")
    L.set_block(V(57, y + 1, IZ2), "minecraft:light_blue_wool")
    L.set_block(V(56, y, IZ2), "minecraft:pink_wool")
    # the harp and the music box, bookshelves against the wardrobe wall
    L.set_block(V(57, y, 33), "minecraft:note_block[instrument=harp]")
    L.set_block(V(57, y, 34), "minecraft:jukebox")
    L.fill(V(IX1, y, 29), V(IX1 + 2, y + 2, 29), "minecraft:bookshelf")
    bookcase(V(IX1 + 3, y, 29), "south", 4)
    for z in (36, IZ2):
        L.set_block(V(IX1, y, z), "minecraft:potted_orange_tulip")
    for x, colour in ((49, BANNER), (52, BANNER2)):
        tapestry(
            V(x, y + 2, 29),
            "south",
            colour,
            [("stripe_middle", "yellow"), ("flower", "white"), ("border", "black")],
        )
    painting(V(IX1 + 1, y + 2, IZ2), "north", "aztec")
    painting(V(56, y + 2, IZ2), "north", "wasteland")


def map_room() -> None:
    """a map table with chairs, maps and a compass on the walls"""
    y = F3 + 1
    carpet(59, IZ1, 66, IZ2, y, "green")
    table(V(61, y, 22), V(64, y, 31))
    for x, z in ((61, 22), (64, 31), (61, 31), (64, 22)):
        L.set_block(V(x, y + 1, z), "minecraft:white_candle[candles=1,lit=true]")
    for z in (24, 29):
        L.seat(V(60, y, z), "east")
        L.seat(V(65, y, z), "west")
    for z in (19, 34):
        item_frame(V(66, y + 2, z), 4, "map")  # on the partition
    item_frame(V(66, y + 2, 26), 4, "compass")
    L.set_block(V(60, y, IZ1), "minecraft:lectern[facing=south,has_book=true]")


def east_wing() -> None:
    """the east wing (its door at x 70, z 28): a guest room behind a
    planked wall (x 73..77, z 15..21), the privy closet in the north-west
    corner, and the nursery in the rest: a cot behind a rail, the child's
    bed, a toy chest and toys, the nurse's chair, a cat"""
    y = F3 + 1
    # the nursery's carpet, then the guest room's, then the guest room's walls
    # a rebuild starts clear (but the wall closing the partition's doorway)
    L.fill(V(68, y, IZ1), V(IX2, FR - 1, 27), L.AIR)
    L.fill(V(68, y, 20), V(68, y + 1, 21), L.BRICK)
    carpet(68, 18, IX2, 27, y, "light_blue")
    carpet(69, 24, 71, 26, y, "pink")
    carpet(73, 15, IX2, 21, y, "blue")
    L.fill(V(72, y, 15), V(72, y + 3, 22), "minecraft:spruce_planks")
    L.fill(V(73, y, 22), V(IX2, y + 3, 22), "minecraft:spruce_planks")
    L.set_block(
        V(72, y, 19), "minecraft:spruce_door[facing=east,half=lower,hinge=left]"
    )
    L.set_block(
        V(72, y + 1, 19), "minecraft:spruce_door[facing=east,half=upper,hinge=left]"
    )
    # the guest room: a bed, a chest, a desk and chair, a wardrobe, a painting
    bed(V(IX2 - 1, y, 16), "east", "blue")
    key("the guest bed", V(IX2, y, 16), "minecraft:blue_bed[part=head]")
    chest(V(IX2, y, 18), "west", [("book", 1), ("candle", 2), ("bread", 3)])
    table(V(IX2, y, 20), V(IX2, y, 20))
    L.set_block(V(IX2, y + 1, 20), "minecraft:candle[candles=1,lit=true]")
    L.seat(V(IX2 - 1, y, 20), "east")
    L.fill(V(73, y, 15), V(74, y + 1, 15), "minecraft:barrel[facing=south]")
    L.set_block(V(73, y, 21), "minecraft:potted_cornflower")
    painting(V(75, y + 2, 15), "south", "aztec2")
    # the nursery's cot, railed round, against the east wall
    bed(V(IX2 - 1, y, 25), "east", "white")
    key("the nursery's cot", V(IX2, y, 25), "minecraft:white_bed[part=head]")
    for x, z in ((75, 24), (75, 25), (75, 26), (76, 24), (77, 24), (76, 26), (77, 26)):
        L.set_block(V(x, y, z), "minecraft:oak_fence")
    L.set_block(V(IX2, y, 27), "minecraft:note_block[instrument=bell]")  # a music box
    # the child's bed, the toy chest and a heap of toy blocks
    bed(V(69, y, 23), "west", "pink")
    key("the child's bed", V(68, y, 23), "minecraft:pink_bed[part=head]")
    chest(
        V(68, y, 22),
        "east",
        [("stick", 2), ("slime_ball", 3), ("snowball", 8), ("rabbit_foot", 1),
         ("feather", 4), ("music_disc_cat", 1)],
    )  # fmt: skip
    for p, block in (
        ((69, y, 20), "minecraft:yellow_wool"),
        ((69, y, 21), "minecraft:light_blue_wool"),
        ((69, y + 1, 20), "minecraft:red_wool"),
    ):
        L.set_block(V(*p), block)
    # the nurse's chair at a little table, near the door
    table(V(73, y, 27), V(73, y, 27))
    L.set_block(V(73, y + 1, 27), "minecraft:potted_blue_orchid")
    L.seat(V(72, y, 27), "east", block="minecraft:oak_stairs")
    # a rabbit's foot for luck and a painting on the guest room's wall
    item_frame(V(74, y + 2, 23), 3, "rabbit_foot")
    painting(V(76, y + 2, 23), "south", "kebab")
    L.summon(
        "cat",
        V(70, y, 25) + Vec3(0.5, 0, 0.5),
        f'{STATIC},Rotation:[90f,0f],variant:"minecraft:calico",CustomName:"Whiskers"',
    )
    # the privy in the north-west corner: a closet with a lid
    L.fill(V(69, y, IZ1), V(69, y + 2, IZ1 + 1), "minecraft:spruce_planks")
    L.set_block(V(68, y, IZ1), "minecraft:composter")
    key("the privy", V(68, y + 1, IZ1), "minecraft:spruce_trapdoor[half=bottom]")
    L.set_block(
        V(68, y, IZ1 + 2), "minecraft:spruce_door[facing=south,half=lower,hinge=left]"
    )
    L.set_block(
        V(68, y + 1, IZ1 + 2),
        "minecraft:spruce_door[facing=south,half=upper,hinge=left]",
    )
    L.fill(V(69, y, IZ1 + 2), V(69, y + 2, IZ1 + 2), "minecraft:spruce_planks")
    L.set_block(V(68, y + 2, IZ1 + 2), "minecraft:spruce_planks")


# ---------------------------------------------------------------- the chapel


def chapel_furnishing() -> None:
    """pews facing the altar, the altar with candles and a cross, banners
    on the walls, candle stands; the crypt's tombs with effigies and
    skulls in niches. The north-west corner is kept for the organ."""
    x1, z1, x2, z2 = CHAPEL
    y = 18
    for z in range(z2 - 4, z1 + 8, -2):  # the pews face the altar
        L.seat(V(x1 + 3, y, z), "north", V(95, y, z))
        L.seat(V(101, y, z), "north", V(x2 - 3, y, z))
    L.fill(
        V(96, y + 1, z1 + 2), V(100, y + 1, z1 + 2), "minecraft:chiseled_quartz_block"
    )
    L.set_block(V(98, y + 2, z1 + 2), "minecraft:gold_block")
    L.set_block(V(98, y + 3, z1 + 2), "minecraft:end_rod[facing=up]")
    L.set_block(V(97, y + 3, z1 + 2), "minecraft:end_rod[facing=west]")
    L.set_block(V(99, y + 3, z1 + 2), "minecraft:end_rod[facing=east]")
    for x in (96, 100):
        L.set_block(V(x, y + 2, z1 + 2), "minecraft:white_candle[candles=4,lit=true]")
    L.set_block(V(98, y + 1, z1 + 4), "minecraft:lectern[facing=south,has_book=true]")
    # candle stands at the ends of the front pews
    for x in (x1 + 2, x2 - 2):
        L.set_block(V(x, y, z1 + 8), "minecraft:dark_oak_fence")
        L.set_block(V(x, y + 1, z1 + 8), "minecraft:white_candle[candles=3,lit=true]")
    # banners between the side windows
    for z in range(z1 + 6, z2 - 2, 8):
        tapestry(
            V(x1 + 1, y + 3, z),
            "east",
            "white",
            [("cross", "yellow"), ("border", "purple")],
        )
        tapestry(
            V(x2 - 1, y + 3, z),
            "west",
            "white",
            [("cross", "yellow"), ("border", "purple")],
        )
    crypt_furnishing()


def crypt_furnishing() -> None:
    """two rows of tombs, each with an effigy lying on its lid (a stone
    knight: his skull at the wall end, his body a slab, his feet a stair
    standing up at the aisle end) and his sword in a frame on the tomb's
    side; skulls in niches in the walls, cobwebs, candles"""
    x1, z1, x2, z2 = 88, 16, 108, 30
    y = 8
    L.fill(
        V(x1 + 1, y, z1 + 1), V(x2 - 1, y + 2, z2 - 1), L.AIR
    )  # a rebuild starts clear
    for x in range(x1 + 3, x2 - 2, 4):
        # (head, body, feet) z, and the way the feet point (to the aisle)
        for zs, toes, rot in (((18, 19, 20), "south", 0), ((28, 27, 26), "north", 8)):
            head, body, feet = zs
            L.fill(V(x, y, min(zs)), V(x, y, max(zs)), "minecraft:polished_deepslate")
            key(
                "an effigy's head",
                V(x, y + 1, head),
                f"minecraft:skeleton_skull[rotation={rot}]",
            )
            key(
                "an effigy's body",
                V(x, y + 1, body),
                "minecraft:smooth_stone_slab[type=bottom]",
            )
            key("an effigy's feet", V(x, y + 1, feet),
                f"minecraft:stone_brick_stairs[facing={toes},half=bottom]")  # fmt: skip
            item_frame(V(x - 1, y, body), 4, "iron_sword")  # on the tomb's west side
            L.set_block(V(x + 1, y, head), "minecraft:white_candle[candles=1,lit=true]")
    key_entities("the effigies' swords", "item_frame", (x1, y, z1), (x2, y, z2))
    # skulls in niches cut into the side walls (clear of the ladder at x 94)
    for x in range(x1 + 2, x2 - 1, 4):
        if x == 94:
            continue
        for z, rot in ((z1, 0), (z2, 8)):
            L.set_block(V(x, 9, z), f"minecraft:skeleton_skull[rotation={rot}]")
    L.set_block(V(96, 8, 23), "minecraft:cobweb")
    L.set_block(V(104, 10, 19), "minecraft:cobweb")
    L.set_block(V(75, 8, 20), "minecraft:skeleton_skull[rotation=12]")


# ---------------------------------------------------------------- the bailey


def bailey_furnishing() -> None:
    """castle2's furniture for the bailey's buildings (`build_inner.bailey_shell`):
    tack and feed in the stables, the forge's tools, bunks and kit in the
    barracks, and castle's market goods"""
    from build_inner import market

    stables()
    smithy()
    barracks()
    market()


def stables() -> None:
    """a horse in each stall, with hay, water, oats and its tack on the wall
    (nothing beside the stall's front fence, which is one high)"""
    from castle2_layout import STABLES

    x1, z1, x2, z2 = STABLES
    for s in range(z1 + 1, z2, 5):  # each stall's interior is z s..s+3
        L.fill(V(x1 + 1, 0, s), V(x2 - 1, 2, s + 3), L.AIR)  # castle's shell leaves it
        L.fill(V(x1 + 1, 0, s + 1), V(x1 + 1, 0, s + 2), "minecraft:hay_block")
        L.set_block(V(x1 + 1, 0, s + 3), "minecraft:water_cauldron[level=3]")
        L.set_block(V(x1 + 1, 0, s), "minecraft:barrel[facing=up]")
        item_frame(V(x1 + 1, 2, s + 1), 5, "saddle")
        item_frame(V(x1 + 1, 2, s + 2), 5, "lead")
        L.summon(
            "horse", V(x1 + 6, 0, s + 1) + Vec3(0.5, 0, 0.5), f"{L.PERSIST},Tame:1b"
        )


def smithy() -> None:
    """the forge with a lava pot, anvils, a grindstone, a smithing table, a
    quenching trough, racks of tools and weapons, barrels of coal, armour on
    stands; the smith stands at his anvil (people.py)"""
    from castle2_layout import SMITHY

    x1, z1, x2, z2 = SMITHY
    y = 0
    L.set_block(V(x2 - 3, y, z1 + 1), "minecraft:lava_cauldron")  # in the forge
    L.set_block(V(x2 - 1, y, z1 + 3), "minecraft:blast_furnace[facing=west]")
    L.set_block(V(x2 - 1, y, z1 + 4), "minecraft:blast_furnace[facing=west]")
    L.set_block(V(x2 - 1, y, z1 + 6), "minecraft:anvil[facing=north]")
    L.set_block(V(x2 - 1, y, z1 + 8), "minecraft:grindstone[face=floor,facing=west]")
    L.set_block(V(x2 - 1, y, z1 + 11), "minecraft:smithing_table")
    L.set_block(V(x2 - 1, y, z1 + 12), "minecraft:water_cauldron[level=3]")
    L.set_block(V(x1 + 2, y, z1 + 2), "minecraft:anvil[facing=east]")
    tools = [
        "iron_pickaxe",
        "iron_shovel",
        "iron_axe",
        "iron_hoe",
        "shears",
        "flint_and_steel",
    ]
    for k, x in enumerate(range(x1 + 1, x1 + 5)):
        shelf(V(x, y + 1, z1 + 1), "south", tools[k : k + 3])
    for k, item in enumerate(("iron_sword", "iron_spear", "mace")):
        item_frame(V(x1 + 1, y + 2, z1 + 6 + k), 5, item)
    L.fill(
        V(x1 + 1, y, z2 - 4), V(x1 + 1, y + 1, z2 - 1), "minecraft:barrel[facing=up]"
    )
    chest(
        V(x1 + 1, y, z1 + 4),
        "east",
        [
            ("iron_ingot", 16),
            ("coal", 32),
            ("iron_pickaxe", 1),
            ("iron_horse_armor", 1),
        ],
    )
    armour_stand(V(x1 + 4, y, z2 - 2) + Vec3(0.5, 0, 0.5), "iron")
    armour_stand(V(x1 + 6, y, z2 - 2) + Vec3(0.5, 0, 0.5), "chainmail")
    L.set_block(V(x1 + 3, y, z2 - 1), "minecraft:iron_block")


def barracks() -> None:
    """bunks (a bed on a bed), a chest at each, a weapon rack, a mess table
    with benches, the soldiers' kit on stands"""
    from castle2_layout import BARRACKS

    x1, z1, x2, z2 = BARRACKS
    for z in range(z1 + 2, z2 - 2, 3):
        bed(V(x1 + 2, 0, z), "west", "white")
        L.fill(V(x1 + 1, 1, z), V(x1 + 2, 1, z), "minecraft:spruce_slab[type=bottom]")
        bed(V(x1 + 2, 2, z), "west", "light_gray")
        L.set_block(V(x1 + 3, 0, z), "minecraft:chest[facing=east]")
    for x in range(x1 + 4, x2 - 2, 2):
        item_frame(
            V(x, 2, z1 + 1),
            3,
            ("iron_spear", "bow", "iron_sword", "crossbow", "shield")[x % 5],
        )
    table(V(x2 - 4, 0, 80), V(x2 - 4, 0, 85))
    L.seat(V(x2 - 5, 0, 80), "east", V(x2 - 5, 0, 85))
    L.seat(V(x2 - 3, 0, 80), "west", V(x2 - 3, 0, 85))
    for z in (82, 84):
        L.set_block(V(x2 - 4, 1, z), "minecraft:candle[candles=2,lit=true]")
    armour_stand(V(x2 - 2, 0, z1 + 2) + Vec3(0.5, 0, 0.5), "chainmail", rotation=90)
    armour_stand(V(x2 - 4, 0, z1 + 2) + Vec3(0.5, 0, 0.5), "iron", rotation=0)
    barracks_yard()


def barracks_yard() -> None:
    """the training ground east of the barracks (x 27..35, z 68..76):
    beaten earth, two straw dummies (a carved pumpkin on hay on a post),
    two armour-stand dummies with their arms out, a rack of practice
    weapons. The yard east of it (x 37..55, z 66..86) is kept clear for
    the archery range of phase 6."""
    rx1, rz1, rx2, rz2 = 27, 68, 35, 76
    L.fill(V(rx1, -1, rz1), V(rx2, -1, rz2), "minecraft:coarse_dirt")
    for x in (29, 33):
        L.set_block(V(x, 0, 70), "minecraft:dark_oak_fence")
        key("a straw dummy", V(x, 1, 70), "minecraft:hay_block")
        L.set_block(V(x, 2, 70), "minecraft:carved_pumpkin[facing=south]")
        L.summon(
            "armor_stand",
            V(x, 0, 74) + Vec3(0.5, 0, 0.5),
            "Rotation:[180f,0f],ShowArms:1b,NoBasePlate:1b,"
            "Pose:{LeftArm:[0f,0f,-90f],RightArm:[0f,0f,90f]},"
            'equipment:{head:{id:"minecraft:carved_pumpkin",count:1},'
            'chest:{id:"minecraft:leather_chestplate",count:1},'
            'mainhand:{id:"minecraft:wooden_sword",count:1}}',
        )
    key_entities("the practice dummies", "armor_stand", (rx1, 0, rz1), (rx2, 2, rz2))
    # the rack of practice weapons on the north side
    for x in (30, 32):
        L.set_block(V(x, 0, rz1), "minecraft:dark_oak_fence")
    L.fill(V(30, 1, rz1), V(32, 1, rz1), "minecraft:stripped_spruce_log[axis=x]")
    for x, item in ((30, "wooden_sword"), (31, "shield"), (32, "stone_sword")):
        item_frame(V(x, 1, rz1 + 1), 3, item)
    L.set_block(V(34, 0, rz1), "minecraft:barrel[facing=up]")


# ---------------------------------------------------------------- the rest


def extras() -> str:
    """detail added to rooms castle furnishes as it builds them: the
    alchemist's tower, prisoners in the dungeon, treasure in the vault,
    a guard at the gate's winch"""
    alchemist()
    dungeon()
    vault()
    winch_room()
    return "the alchemist's, the dungeon, the vault, the winch room"


def alchemist() -> None:
    from castle2_layout import ALCH, YU

    cx, cz = ALCH
    y, f = YU, YU + 8
    # specimen jars on the bookcase, a cauldron of powdered snow
    for k, plant in enumerate(("crimson_fungus", "warped_fungus", "wither_rose")):
        L.set_block(V(cx + 1 + k, y + 3, cz - 3), f"minecraft:potted_{plant}")
    L.set_block(V(cx - 2, y, cz + 3), "minecraft:powder_snow_cauldron[level=3]")
    # a parrot on a perch and a star chart on the second floor
    L.set_block(V(cx + 1, f, cz + 3), "minecraft:dark_oak_fence")
    L.summon(
        "parrot", V(cx + 1, f + 1, cz + 3) + Vec3(0.5, 0, 0.5), f"{STATIC},Variant:2"
    )
    tapestry(
        V(cx, f + 2, cz + 4),
        "north",
        "black",
        [("flower", "white"), ("circle", "yellow"), ("border", "blue")],
    )
    tapestry(
        V(cx - 1, f + 2, cz + 4),
        "north",
        "black",
        [("small_stripes", "white"), ("border", "blue")],
    )


def dungeon() -> None:
    """prisoners in two cells, chained"""
    from castle2_layout import CELL_ROWS, DUNGEON_Y

    for (zc, _zdoor, into, xs), k in zip(CELL_ROWS, (2, 2), strict=True):
        x = list(xs)[k]
        person(
            V(x + 1, DUNGEON_Y, zc + 1),
            "south" if into > 0 else "north",
            "nitwit",
            "a prisoner",
        )
        L.set_block(V(x, DUNGEON_Y + 1, zc + 1), L.CHAIN)


def vault() -> None:
    """heaps of treasure on the floor"""
    from castle2_layout import VAULT_Y

    y = VAULT_Y
    for x1, z1 in ((54, 25), (62, 25)):
        L.fill(V(x1, y, z1), V(x1 + 2, y, z1 + 1), "minecraft:raw_gold_block")
        L.set_block(V(x1 + 1, y + 1, z1), "minecraft:gold_block")
        L.set_block(V(x1, y + 1, z1 + 1), "minecraft:emerald_block")
        L.set_block(V(x1 + 2, y + 1, z1 + 1), "minecraft:diamond_block")
        L.set_block(V(x1 + 1, y + 2, z1), "minecraft:yellow_candle[candles=4,lit=true]")


def winch_room() -> None:
    """a guard at the main gate's winch"""
    from castle2_layout import GATEHOUSE

    x1, z1, _x2, _z2 = GATEHOUSE
    armour_stand(V(x1 + 9, 4, z1 + 4) + Vec3(0.5, 0, 0.5), "chainmail", rotation=-90)
