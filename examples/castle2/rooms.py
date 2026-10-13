"""
castle2's furnishing (phase 5): every room in full detail. castle builds
the rooms (its ``*_shell`` functions); castle2 furnishes them its own way
in place of castle's ``*_furnishing`` (see build_castle2's stages).

Every seat goes through `castle_lib.seat`, given the way its sitter looks,
and verify_castle2 reads each one back. Renders draw stairs as full blocks,
so they cannot show which way a seat faces: that check can.

Rooms (local coordinates, castle's layout): the keep's great hall, kitchen,
library, armoury, the lord's chamber, the map room and the guest rooms
with a nursery and a privy; the chapel and its crypt. Kept clear for the
machines of phase 6: the chapel's north-west corner (the organ).
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
FACING_BYTE = {"north": 2, "south": 3, "west": 4, "east": 5}  # paintings, frames


# ---------------------------------------------------------------- helpers


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
        "painting", pos, f'facing:{FACING_BYTE[facing]}b,variant:"minecraft:{variant}"'
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
    """a hearth among smokers and ovens, shelves of food, a pantry, a table,
    lanterns on chains; the cook stands at (72, 17) (people.py)"""
    y = F1 + 1
    x1, z1, x2, z2 = 68, IZ1, IX2, 27
    row = {
        68: "minecraft:smoker[facing=south]",
        69: "minecraft:smoker[facing=south]",
        70: "minecraft:furnace[facing=south]",
        71: "minecraft:campfire[lit=true]",
        72: "minecraft:campfire[lit=true]",
        73: "minecraft:furnace[facing=south]",
        74: "minecraft:smoker[facing=south]",
        75: "minecraft:water_cauldron[level=3]",
        76: "minecraft:water_cauldron[level=3]",
        77: "minecraft:barrel[facing=south]",
    }
    for x, block in row.items():
        L.set_block(V(x, y, z1), block)
    food = [
        "bread",
        "apple",
        "cooked_beef",
        "carrot",
        "baked_potato",
        "pumpkin_pie",
        "cookie",
    ]
    for x in (68, 69, 70, 73, 74, 75, 76):
        shelf(V(x, y + 1, z1), "south", _rng.sample(food, 3))
    L.fill(V(71, y + 1, z1), V(72, y + 2, z1), "minecraft:bricks")  # the hood
    L.fill(V(70, y + 2, z1), V(73, y + 2, z1), "minecraft:brick_slab[type=bottom]")
    for x in (70, 75):  # lanterns on chains
        L.fill(V(x, y + 5, 21), V(x, y + 8, 21), L.CHAIN)
        L.set_block(V(x, y + 4, 21), f"{L.LANTERN}[hanging=true]")
    # the table, with a meal laid on it
    table(V(71, y, 20), V(74, y, 21))
    L.set_block(V(71, y + 1, 21), "minecraft:cake")
    L.set_block(V(73, y + 1, 21), "minecraft:melon")
    L.set_block(V(74, y + 1, 20), "minecraft:carved_pumpkin[facing=west]")
    L.set_block(V(72, y + 1, 20), "minecraft:white_candle[candles=2,lit=true]")
    # the pantry along the east wall
    L.fill(V(x2, y, 17), V(x2, y + 1, 19), "minecraft:barrel[facing=west]")
    for z in range(21, 25):
        shelf(V(x2, y, z), "west", _rng.sample(food, 3))
        shelf(V(x2, y + 1, z), "west", _rng.sample(food, 3))
    chest(
        V(x2, y, 25),
        "west",
        [("bread", 16), ("cooked_beef", 8), ("apple", 16), ("golden_carrot", 4)],
    )
    # sacks of grain, the scraps and the chopping block
    L.fill(V(x1, y, 24), V(x1, y, 26), "minecraft:hay_block")
    L.fill(V(x1, y + 1, 25), V(x1, y + 1, 26), "minecraft:hay_block")
    L.set_block(V(73, y, z2), "minecraft:composter")
    L.set_block(V(74, y, z2), "minecraft:crafting_table")
    L.set_block(V(76, y, z2), "minecraft:stripped_oak_log")


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
    # reading desks with a chair at each end, and candles
    for z in (21, 27, 33):
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
    L.set_block(V(55, y, 37), "minecraft:loom")
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


def chambers() -> None:
    """the lord's chamber (a four-poster bed, wardrobes, a dressing table,
    a desk, armchairs by the fire, paintings, a rug), the map room, and the
    east wing's guest room, nursery and privy"""
    y = F3 + 1
    # a rug: red with a yellow border
    carpet(IX1, IZ1, 57, IZ2, y, "red")
    carpet(47, 21, 55, 33, y, "yellow")
    carpet(48, 22, 54, 32, y, "red")
    # the four-poster bed, its head to the west wall
    for z in (26, 27):
        bed(V(IX1 + 2, y, z), "west", "red")
    for x, z in ((IX1, 25), (IX1, 28), (IX1 + 3, 25), (IX1 + 3, 28)):
        L.fill(V(x, y, z), V(x, y + 2, z), "minecraft:dark_oak_fence")
    L.fill(V(IX1, y + 3, 25), V(IX1 + 3, y + 3, 28), "minecraft:red_wool")
    L.set_block(V(IX1, y + 4, 27), f"minecraft:{BANNER2}_wall_banner[facing=east]")
    # wardrobes and chests along the north wall
    L.fill(V(46, y, IZ1), V(47, y + 1, IZ1), "minecraft:barrel[facing=south]")
    chest(
        V(48, y, IZ1),
        "south",
        [("golden_apple", 2), ("gold_ingot", 12), ("emerald", 6), ("book", 3)],
    )
    # the dressing table, its mirror and stool
    table(V(54, y, IZ1 + 1), V(55, y, IZ1 + 1))
    L.set_block(V(54, y + 1, IZ1 + 1), "minecraft:potted_allium")
    L.set_block(V(55, y + 1, IZ1 + 1), "minecraft:candle[candles=1,lit=true]")
    L.fill(
        V(54, y + 1, IZ1), V(55, y + 2, IZ1), "minecraft:light_blue_stained_glass_pane"
    )
    L.seat(V(54, y, IZ1 + 2), "north")
    # the lord's desk by the east wall
    table(V(56, y, 20), V(56, y, 22))
    L.seat(V(55, y, 21), "east")
    L.set_block(V(56, y + 1, 21), "minecraft:lectern[facing=west,has_book=true]")
    # armchairs facing the fireplace in the south wall
    L.seat(V(50, y, 37), "south")
    L.seat(V(52, y, 37), "south")
    L.set_block(V(51, y, 37), "minecraft:jukebox")
    # paintings
    for x, variant in ((44, "kebab"), (51, "aztec"), (56, "alban")):
        painting(V(x, y + 2, IZ1), "south", variant)
    for x, variant in ((45, "bomb"), (56, "plant")):
        painting(V(x, y + 2, IZ2), "north", variant)
    # the map room, x 59..66: a map table with chairs, maps on the walls
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
    # the east wing: a guest bed, a nursery with a cot, and a privy
    bed(V(IX2, y, 18), "west", "blue")
    chest(V(IX2, y, 20), "west", [("book", 1), ("candle", 2)])
    bed(V(IX2, y, 24), "west", "white")  # the nursery's cot, with a rail round it
    L.fill(V(IX2 - 2, y, 23), V(IX2 - 2, y, 25), "minecraft:oak_fence")
    L.seat(V(73, y, 26), "east", block="minecraft:oak_stairs")  # the nurse's chair
    item_frame(V(IX2, y + 2, 24), 4, "rabbit_foot")
    # the privy in the north-west corner: a closet with a lid
    L.fill(V(69, y, IZ1), V(69, y + 2, IZ1 + 1), "minecraft:spruce_planks")
    L.set_block(V(68, y, IZ1), "minecraft:composter")
    L.set_block(V(68, y + 1, IZ1), "minecraft:spruce_trapdoor[half=bottom,open=false]")
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
    """tombs with effigies (a skull on a stone lid), skulls in niches in the
    walls, cobwebs, candles"""
    x1, z1, x2, z2 = 88, 16, 108, 30
    for x in range(x1 + 3, x2 - 2, 4):
        for z in (z1 + 3, z2 - 4):
            L.fill(V(x, 8, z), V(x, 8, z + 1), "minecraft:polished_deepslate")
            L.set_block(V(x, 9, z), "minecraft:skeleton_skull[rotation=0]")
            L.set_block(
                V(x, 9, z + 1), "minecraft:polished_deepslate_slab[type=bottom]"
            )
            L.set_block(V(x + 1, 8, z), "minecraft:white_candle[candles=1,lit=true]")
    # skulls in niches cut into the side walls (clear of the ladder at x 94)
    for x in range(x1 + 2, x2 - 1, 4):
        if x == 94:
            continue
        for z, rot in ((z1, 0), (z2, 8)):
            L.set_block(V(x, 9, z), f"minecraft:skeleton_skull[rotation={rot}]")
    L.set_block(V(96, 8, 23), "minecraft:cobweb")
    L.set_block(V(104, 10, 19), "minecraft:cobweb")
    L.set_block(V(75, 8, 20), "minecraft:skeleton_skull[rotation=12]")
