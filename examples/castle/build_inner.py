"""
The inner works: the keep's rooms, the chapel and its crypt, the alchemist's
tower and its engine, the bailey's buildings and well, the dungeons with
their traps, the treasure vault, and the finishing details.

Secrets (see the README for the full list):

- library (keep, 2nd floor): take the last book of the chiseled bookshelf
  and a bookcase slides open onto a ladder down to the vault;
- the well in the bailey: swim down, a door at the bottom opens into a
  tunnel to the dungeons and (climbing) to the vault;
- the last cell of the dungeon: a lever opens the end wall of the cell block
  onto the same tunnels;
- the chapel crypt: a lever in the crypt's end chamber opens into the vault;
- the smithy: a trapdoor in the floor drops down a ladder into the lower
  treasury behind the arrow trap.
"""

from __future__ import annotations

import castle_lib as L
from castle_layout import KEEP, KEEP_ROOF, UD, XG, YU, ZS, V, W
from mcwb import Vec3

from mciwb.builders import column, gable_roof, hip_roof, stairway

N, S, E, Wd = Vec3(0, 0, -1), Vec3(0, 0, 1), Vec3(1, 0, 0), Vec3(-1, 0, 0)

F1, F2, F3, FR = YU - 1, YU + 9, YU + 18, KEEP_ROOF - 1  # the keep's floor slabs
KX1, KZ1, KX2, KZ2 = KEEP
IX1, IZ1, IX2, IZ2 = KX1 + 3, KZ1 + 3, KX2 - 3, KZ2 - 3  # the keep's interior

# where the mechanisms are, filled in as they are built (local coordinates
# are in the README; these are world positions for verify_castle.py)
MECHANISMS: dict[str, dict] = {}


def door(pos: Vec3, facing: str, kind: str = "dark_oak") -> None:
    """a 2-high door with its lower half at pos"""
    L.set_block(pos, f"minecraft:{kind}_door[facing={facing},half=lower]")
    L.set_block(
        pos + Vec3(0, 1, 0), f"minecraft:{kind}_door[facing={facing},half=upper]"
    )


def doorway(a: Vec3, b: Vec3) -> None:
    """a 2-high opening between two floor-level cells (inclusive)"""
    L.fill(a, b + Vec3(0, 1, 0), L.AIR)


def lanterns(
    x1: int, z1: int, x2: int, z2: int, y: int, step: int = 6, block: str = L.LANTERN
) -> None:
    """hanging lanterns on a grid under a ceiling (local coordinates; y is the lantern's level)"""
    for x in range(x1 + step // 2, x2 + 1, step):
        for z in range(z1 + step // 2, z2 + 1, step):
            L.set_block(V(x, y, z), f"{block}[hanging=true]")


def carpet(x1: int, z1: int, x2: int, z2: int, y: int, colour: str = "red") -> None:
    L.fill(V(x1, y, z1), V(x2, y, z2), f"minecraft:{colour}_carpet")


def chest(pos: Vec3, facing: str, items: list[tuple[str, int]]) -> None:
    L.set_block(pos, f"minecraft:chest[facing={facing}]")
    for slot, (item, count) in enumerate(items):
        L.cmd(
            f"item replace block {pos.x} {pos.y} {pos.z} container.{slot} with minecraft:{item} {count}"
        )


def armour_stand(pos: Vec3, material: str, rotation: int = 0) -> None:
    eq = ",".join(
        f'{slot}:{{id:"minecraft:{material}_{piece}",count:1}}'
        for slot, piece in (
            ("head", "helmet"),
            ("chest", "chestplate"),
            ("legs", "leggings"),
            ("feet", "boots"),
        )
    )
    L.cmd(
        f"summon minecraft:armor_stand {pos.x} {pos.y} {pos.z} {{Rotation:[{rotation}f,0f],equipment:{{{eq}}}}}"
    )


def item_frame(pos: Vec3, facing: int, item: str) -> None:
    """facing: 2 north, 3 south, 4 west, 5 east (the side of the block it hangs on)"""
    L.cmd(
        f'summon minecraft:item_frame {pos.x} {pos.y} {pos.z} {{Facing:{facing}b,Item:{{id:"minecraft:{item}",count:1}}}}'
    )


def bed(pos: Vec3, facing: str, colour: str = "red") -> None:
    d = {"north": N, "south": S, "east": E, "west": Wd}[facing]
    L.set_block(pos, f"minecraft:{colour}_bed[facing={facing},part=foot]")
    L.set_block(pos + d, f"minecraft:{colour}_bed[facing={facing},part=head]")


def table(a: Vec3, b: Vec3) -> None:
    L.fill(a, b, "minecraft:dark_oak_slab[type=top]")


# ---------------------------------------------------------------- the keep


def keep_interiors() -> None:
    # floor slabs for the upper storeys
    L.fill(V(IX1, F2, IZ1), V(IX2, F2, IZ2), L.PLANKS)
    L.fill(V(IX1, F3, IZ1), V(IX2, F3, IZ2), L.PLANKS)
    L.fill(V(IX1, F1, IZ1), V(IX2, F1, IZ2), L.ANDESITE)
    # partitions: the east wing (x >= 68) on every storey, split at z = 28
    for fy in (F1, F2, F3):
        L.fill(V(67, fy + 1, IZ1), V(67, fy + 9, IZ2), L.BRICK)
        L.fill(V(68, fy + 1, 28), V(IX2, fy + 9, 28), L.BRICK)
        doorway(V(67, fy + 1, 20), V(67, fy + 1, 21))
        doorway(V(67, fy + 1, 33), V(67, fy + 1, 34))
        doorway(V(70, fy + 1, 28), V(71, fy + 1, 28))
    # the stair hall: three flights, each cutting through the slab above
    stairway(
        [V(76, F1, 29), V(76, F2, 39)],
        L.BRICK_STAIRS,
        width=2,
        support=L.BRICK,
        clearance=3,
    )
    stairway(
        [V(72, F2, 39), V(72, F3, 30)],
        L.BRICK_STAIRS,
        width=2,
        support=L.BRICK,
        clearance=3,
    )
    stairway(
        [V(76, F3, 29), V(76, FR, 38)],
        L.BRICK_STAIRS,
        width=2,
        support=L.BRICK,
        clearance=3,
    )
    for fy in (F2, F3, FR):
        L.fill(
            V(69, fy + 1, 30), V(70, fy + 1, 38), L.BRICK_WALL
        )  # a rail round the stairwell

    great_hall()
    kitchen()
    library()
    armoury()
    chambers()
    # the roof terrace
    L.fill(V(IX1, FR, IZ1), V(IX2, FR, IZ2), L.ANDESITE)
    for x in (IX1 + 4, IX2 - 4):
        for z in (IZ1 + 4, IZ2 - 4):
            L.set_block(V(x, FR + 1, z), "minecraft:campfire[lit=true]")
    # lighting on every storey
    for ceiling in (F2, F3, FR):
        lanterns(IX1, IZ1, 66, IZ2, ceiling - 1)  # the hall / library / chambers
        lanterns(68, IZ1, IX2, 27, ceiling - 1)  # the east wing, not the stair hall


def great_hall() -> None:
    y = F1 + 1
    # dais and thrones at the west end
    L.fill(V(IX1, F1, 22), V(IX1 + 3, F1, 32), L.DARK)
    L.fill(V(IX1, y, 22), V(IX1 + 3, y, 32), L.DARK)
    L.fill(V(IX1 + 4, y, 26), V(IX1 + 4, y, 28), f"{L.BRICK_STAIRS}[facing=east]")
    for z in (26, 28):
        L.set_block(V(IX1 + 1, y + 1, z), "minecraft:dark_oak_stairs[facing=east]")
        L.set_block(V(IX1, y + 2, z), "minecraft:red_wall_banner[facing=east]")
    L.set_block(V(IX1, y + 3, 27), "minecraft:gold_block")
    # two long tables with benches, and candles
    for z in (20, 34):
        table(V(50, y, z), V(64, y, z))
        L.fill(
            V(50, y, z - 1), V(64, y, z - 1), "minecraft:dark_oak_stairs[facing=south]"
        )
        L.fill(
            V(50, y, z + 1), V(64, y, z + 1), "minecraft:dark_oak_stairs[facing=north]"
        )
        for x in range(51, 64, 4):
            L.set_block(V(x, y + 1, z), "minecraft:white_candle[candles=3,lit=true]")
        L.set_block(V(57, y + 1, z), "minecraft:cake")
    # columns down the hall and chandeliers between them
    for x in (49, 58):
        for z in (24, 30):
            column(V(x, y, z), 9, L.BRICK, plinth=L.CHISELED, capital=L.CHISELED)
    for x in (53, 62):
        L.fill(V(x, y + 7, 27), V(x, y + 8, 27), L.CHAIN)
        L.set_block(V(x, y + 6, 27), f"{L.LANTERN}[hanging=true]")
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            L.set_block(V(x + dx, y + 6, 27 + dz), "minecraft:dark_oak_fence")
            L.set_block(
                V(x + dx, y + 7, 27 + dz), "minecraft:white_candle[candles=2,lit=true]"
            )
    # a fireplace in the north wall
    L.fill(V(52, y, IZ1 - 1), V(56, y + 2, IZ1 - 2), L.AIR)
    L.fill(V(52, F1, IZ1 - 2), V(56, F1, IZ1 - 1), L.DARK)
    L.set_block(V(54, y, IZ1 - 2), "minecraft:campfire[lit=true]")
    L.fill(V(52, y + 3, IZ1 - 1), V(56, y + 3, IZ1 - 1), L.DARK_BRICK)
    L.fill(V(51, y, IZ1 - 1), V(51, y + 3, IZ1 - 1), L.DARK_BRICK)
    L.fill(V(57, y, IZ1 - 1), V(57, y + 3, IZ1 - 1), L.DARK_BRICK)
    # banners along the south wall between the windows, and the carpet from the door
    for x in range(IX1 + 2, 67, 6):
        L.set_block(V(x, y + 4, IZ2), "minecraft:blue_wall_banner[facing=north]")
    carpet(XG - 1, 24, XG + 1, IZ2, F1 + 1)
    carpet(IX1 + 4, 26, XG + 1, 28, F1 + 1)
    # the great door's inside: a lintel lantern
    L.set_block(V(XG, y + 4, IZ2), f"{L.LANTERN}[hanging=false]")


def kitchen() -> None:
    y = F1 + 1
    x1, z1, x2, z2 = 68, IZ1, IX2, 27
    L.fill(V(x1, F1, z1), V(x2, F1, z2), "minecraft:smooth_stone")
    for x in range(x1 + 1, x2, 2):
        L.set_block(
            V(x, y, z1),
            "minecraft:smoker[facing=south]"
            if x % 4 == 1
            else "minecraft:furnace[facing=south]",
        )
    L.fill(V(x1, y + 1, z1), V(x2, y + 1, z1), L.DARK_BRICK)
    L.set_block(V(x2, y, z1 + 2), "minecraft:water_cauldron[level=3]")
    L.set_block(V(x2, y, z1 + 3), "minecraft:water_cauldron[level=3]")
    L.fill(V(x2, y, z1 + 5), V(x2, y + 1, z1 + 7), "minecraft:barrel[facing=up]")
    L.fill(V(x1, y, z2 - 3), V(x1, y, z2), "minecraft:hay_block")
    L.fill(V(x1, y + 1, z2 - 1), V(x1, y + 1, z2), "minecraft:hay_block")
    table(V(71, y, 20), V(74, y, 21))
    L.set_block(V(71, y + 1, 21), "minecraft:cake")
    L.set_block(V(74, y + 1, 20), "minecraft:white_candle[candles=1,lit=true]")
    chest(
        V(x2, y, z2),
        "west",
        [("bread", 12), ("cooked_beef", 8), ("apple", 16), ("golden_carrot", 4)],
    )
    L.set_block(V(x1 + 1, y, z2), "minecraft:crafting_table")
    L.set_block(V(x1 + 2, y, z2), "minecraft:composter")


def library() -> None:
    y = F2 + 1
    x1, z1, x2, z2 = IX1, IZ1, 57, IZ2
    carpet(x1, z1, x2, z2, F2 + 1, "blue")
    # the secret partition x 58..61, solid, with the bookshelf wall on its west face
    L.fill(V(58, y, IZ1), V(61, y + 7, IZ2), L.BRICK)
    L.fill(V(58, y, IZ1), V(58, y + 2, IZ2), "minecraft:bookshelf")
    # bookcases round the walls, three high, leaving the windows
    L.fill(V(x1, y, z1), V(x2, y + 2, z1), "minecraft:bookshelf")
    L.fill(V(x1, y, z2), V(x2, y + 2, z2), "minecraft:bookshelf")
    L.fill(V(x1, y, z1), V(x1, y + 2, z2), "minecraft:bookshelf")
    for z in range(z1 + 3, z2 - 2, 6):  # keep the windows in the west wall
        L.fill(V(x1, y, z), V(x1, y + 2, z + 1), L.AIR)
    # the secret door in the east bookcase wall (hidden space x 59..61)
    MECHANISMS["library_door"] = L.hidden_door(V(58, y, 20), E, S)
    # the ladder shaft from the hidden space down to the vault
    L.fill(V(60, 8, 20), V(60, F2, 20), L.AIR)
    L.fill(V(60, 8, 20), V(60, F2 + 1, 20), "minecraft:ladder[facing=south]")
    L.set_block(V(60, y + 3, 20), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_block(
        V(61, y + 3, 24), f"{L.SOUL_LANTERN}[hanging=true]"
    )  # a dim light in the mechanism room
    # reading tables, lecterns, candles and a globe
    for z in (21, 27, 33):
        table(V(48, y, z), V(52, y, z))
        L.set_block(V(47, y, z), "minecraft:dark_oak_stairs[facing=east]")
        L.set_block(V(53, y, z), "minecraft:dark_oak_stairs[facing=west]")
        L.set_block(V(50, y + 1, z), "minecraft:white_candle[candles=2,lit=true]")
    L.set_block(V(50, y, 24), "minecraft:lectern[facing=south,has_book=true]")
    L.set_block(V(50, y, 30), "minecraft:lectern[facing=north,has_book=true]")
    L.set_block(V(45, y, 27), "minecraft:enchanting_table")
    L.set_block(V(55, y, 17), "minecraft:cartography_table")
    L.set_block(V(55, y, 37), "minecraft:loom")
    lanterns(x1, z1, x2, z2, F3 - 1, step=5)


def armoury() -> None:
    y = F2 + 1
    x1, z1, x2, z2 = 68, IZ1, IX2, 27
    L.fill(V(x1, F2, z1), V(x2, F2, z2), "minecraft:smooth_stone")
    L.set_block(V(x1 + 1, y, z1), "minecraft:anvil[facing=east]")
    L.set_block(V(x1 + 3, y, z1), "minecraft:grindstone[face=floor,facing=south]")
    L.set_block(V(x1 + 5, y, z1), "minecraft:smithing_table")
    L.set_block(V(x1 + 7, y, z1), "minecraft:fletching_table")
    for i, material in enumerate(("iron", "golden", "diamond", "chainmail")):
        armour_stand(
            V(x1 + 1 + i * 2, y, z2 - 1) + Vec3(0.5, 0, 0.5), material, rotation=180
        )
    for i, item in enumerate(
        (
            "iron_sword",
            "diamond_sword",
            "bow",
            "crossbow",
            "trident",
            "shield",
            "iron_axe",
            "mace",
        )
    ):
        item_frame(V(x2 + 1, y + 1 + (i % 2), z1 + 2 + i), 4, item)
    L.fill(V(x1, y, 22), V(x1, y + 1, 24), L.BARS)  # a weapons rack
    chest(
        V(x1 + 1, y, 26),
        "north",
        [("arrow", 64), ("iron_ingot", 32), ("shield", 1), ("iron_helmet", 1)],
    )
    L.set_block(V(x1 + 2, y, 26), "minecraft:chest[facing=north]")
    # the gallery between library and armoury: x 62..66, with the windows and banners
    for z in range(IZ1 + 1, IZ2, 4):
        L.set_block(V(66, y + 3, z), "minecraft:red_wall_banner[facing=west]")
    carpet(62, IZ1, 66, IZ2, F2 + 1, "red")


def chambers() -> None:
    y = F3 + 1
    # the lord's chamber, west half
    L.fill(V(58, y, IZ1), V(58, y + 7, IZ2), L.BRICK)
    doorway(V(58, y, 27), V(58, y, 27))
    door(V(58, y, 27), "east")
    carpet(IX1, IZ1, 57, IZ2, F3 + 1, "red")
    bed(V(46, y, 26), "west", "red")
    bed(V(46, y, 28), "west", "red")
    L.fill(V(IX1, y, 20), V(IX1, y + 2, 22), "minecraft:bookshelf")
    chest(
        V(IX1, y, 32),
        "east",
        [("golden_apple", 2), ("gold_ingot", 12), ("emerald", 6), ("book", 3)],
    )
    L.set_block(V(IX1, y, 33), "minecraft:chest[facing=east]")
    table(V(52, y, 18), V(54, y, 18))
    L.set_block(V(53, y + 1, 18), "minecraft:white_candle[candles=4,lit=true]")
    L.set_block(V(53, y, 19), "minecraft:dark_oak_stairs[facing=north]")
    L.set_block(V(50, y, 36), "minecraft:jukebox")
    L.set_block(V(IX1, y + 3, 27), "minecraft:blue_wall_banner[facing=east]")
    # a fireplace in the south wall
    L.fill(V(50, y, IZ2 + 1), V(52, y + 1, IZ2 + 2), L.AIR)
    L.set_block(V(51, y, IZ2 + 2), "minecraft:campfire[lit=true]")
    L.fill(V(49, y, IZ2 + 1), V(49, y + 2, IZ2 + 1), L.DARK_BRICK)
    L.fill(V(53, y, IZ2 + 1), V(53, y + 2, IZ2 + 1), L.DARK_BRICK)
    L.fill(V(49, y + 2, IZ2 + 1), V(53, y + 2, IZ2 + 1), L.DARK_BRICK)
    # the map room, x 59..66
    carpet(59, IZ1, 66, IZ2, F3 + 1, "green")
    table(V(61, y, 22), V(64, y, 31))
    for x, z in ((61, 22), (64, 31), (61, 31), (64, 22)):
        L.set_block(V(x, y + 1, z), "minecraft:white_candle[candles=1,lit=true]")
    for z in (19, 24, 29, 34):
        item_frame(V(67, y + 2, z), 4, "map")
    L.set_block(V(60, y, IZ1), "minecraft:lectern[facing=south,has_book=true]")
    # guest rooms in the east wing
    carpet(68, IZ1, IX2, 27, F3 + 1, "light_gray")
    for z in (18, 24):
        bed(V(IX2, y, z), "west", "blue")
        chest(V(IX2, y, z + 2), "west", [("book", 1)])
    L.fill(V(68, y, 20), V(68, y + 1, 21), L.BRICK)
    door(V(70, y, 28), "south")


# ---------------------------------------------------------------- the chapel and crypt

CHAPEL = (86, 14, 110, 40)


def chapel() -> None:
    x1, z1, x2, z2 = CHAPEL
    y = YU
    h = 7
    L.fill(V(x1, y - 1, z1), V(x2, y + h - 1, z2), L.BRICK)
    L.fill(V(x1 + 1, y, z1 + 1), V(x2 - 1, y + h - 1, z2 - 1), L.AIR)
    L.fill(V(x1 + 1, y - 1, z1 + 1), V(x2 - 1, y - 1, z2 - 1), L.ANDESITE)
    gable_roof(
        V(x1, y + h - 1, z1),
        V(x2, y + h - 1, z2),
        "minecraft:deepslate_tile_stairs",
        gable=L.BRICK,
        axis="z",
        overhang=1,
    )
    # stained glass windows down both sides, in three colours
    colours = ("red", "yellow", "blue")
    for i, z in enumerate(range(z1 + 3, z2 - 2, 4)):
        for x in (x1, x2):
            L.fill(
                V(x, y + 2, z),
                V(x, y + 4, z + 1),
                f"minecraft:{colours[i % 3]}_stained_glass_pane",
            )
    # the great west... south door, pews and the aisle
    doorway(V(XG + 37, y, z2), V(XG + 39, y, z2))
    L.fill(
        V(XG + 37, y + 2, z2), V(XG + 39, y + 3, z2), "minecraft:red_stained_glass_pane"
    )
    carpet(97, z1 + 1, 99, z2 - 1, y, "purple")
    for z in range(z2 - 4, z1 + 8, -2):
        L.fill(V(x1 + 3, y, z), V(95, y, z), "minecraft:dark_oak_stairs[facing=north]")
        L.fill(V(101, y, z), V(x2 - 3, y, z), "minecraft:dark_oak_stairs[facing=north]")
    # the altar on a dais at the north end
    L.fill(V(93, y, z1 + 1), V(103, y, z1 + 4), L.DARK)
    L.fill(V(93, y, z1 + 4), V(103, y, z1 + 4), f"{L.BRICK_STAIRS}[facing=south]")
    L.fill(
        V(96, y + 1, z1 + 2), V(100, y + 1, z1 + 2), "minecraft:chiseled_quartz_block"
    )
    L.set_block(V(98, y + 2, z1 + 2), "minecraft:gold_block")
    for x in (96, 100):
        L.set_block(V(x, y + 2, z1 + 2), "minecraft:white_candle[candles=4,lit=true]")
    L.set_block(V(98, y + 1, z1 + 4), "minecraft:lectern[facing=south,has_book=true]")
    L.fill(V(95, y + 2, z1), V(101, y + 5, z1), "minecraft:yellow_stained_glass_pane")
    L.fill(V(97, y + 3, z1), V(99, y + 4, z1), "minecraft:red_stained_glass_pane")
    L.fill(
        V(x1 + 1, y + h - 1, z1 + 1), V(x2 - 1, y + h - 1, z2 - 1), L.PLANKS
    )  # a ceiling under the roof
    lanterns(x1 + 1, z1 + 1, x2 - 1, z2 - 1, y + h - 2, step=6)
    # the bell tower at the south-west corner
    bx1, bz1 = x1 - 2, z2 - 1
    L.fill(V(bx1, y - 1, bz1), V(bx1 + 6, y + 24, bz1 + 6), L.BRICK)
    L.fill(V(bx1 + 1, y, bz1 + 1), V(bx1 + 5, y + 23, bz1 + 5), L.AIR)
    L.fill(V(bx1 + 3, y, bz1), V(bx1 + 3, y + 1, bz1), L.AIR)  # door from the chapel
    L.fill(
        V(bx1 + 1, y, bz1 + 1),
        V(bx1 + 1, y + 20, bz1 + 1),
        "minecraft:ladder[facing=east]",
    )
    L.fill(V(bx1 + 1, y + 21, bz1 + 1), V(bx1 + 5, y + 21, bz1 + 5), L.PLANKS)
    L.set_block(V(bx1 + 1, y + 21, bz1 + 1), L.AIR)
    for dx, dz in ((0, 3), (6, 3), (3, 0), (3, 6)):
        L.fill(V(bx1 + dx, y + 22, bz1 + dz), V(bx1 + dx, y + 23, bz1 + dz), L.AIR)
    L.fill(V(bx1 + 2, y + 22, bz1 + 2), V(bx1 + 4, y + 23, bz1 + 4), L.AIR)
    L.set_block(V(bx1 + 3, y + 24, bz1 + 3), L.BRICK)
    L.set_block(V(bx1 + 3, y + 23, bz1 + 3), "minecraft:bell[attachment=ceiling]")
    hip_roof(
        V(bx1, y + 24, bz1),
        V(bx1 + 6, y + 24, bz1 + 6),
        "minecraft:deepslate_tile_stairs",
        overhang=1,
    )
    L.fill(
        V(bx1 + 3, y + 28, bz1 + 3), V(bx1 + 3, y + 29, bz1 + 3), L.DARK_TILES
    )  # the hip roof's top ring has a hole in the middle
    L.set_block(V(bx1 + 3, y + 30, bz1 + 3), "minecraft:lightning_rod")
    # the crypt under the altar: a trapdoor behind it and a ladder down
    L.set_block(
        V(94, y, z1 + 2), "minecraft:dark_oak_trapdoor[facing=south,half=top,open=true]"
    )
    L.fill(V(94, 9, z1 + 2), V(94, y - 1, z1 + 2), L.AIR)
    L.fill(V(94, 9, z1 + 2), V(94, y - 1, z1 + 2), "minecraft:ladder[facing=east]")
    crypt()


def crypt() -> None:
    """under the chapel: tombs, and the hidden way into the vault"""
    x1, z1, x2, z2 = 88, 16, 108, 30
    L.fill(V(x1, 7, z1), V(x2, 12, z2), L.DARK_BRICK)
    L.fill(V(x1 + 1, 8, z1 + 1), V(x2 - 1, 11, z2 - 1), L.AIR)
    L.fill(V(94, 8, 16), V(94, 11, 16), L.AIR)  # under the ladder
    L.fill(V(x1 + 1, 7, z1 + 1), V(x2 - 1, 7, z2 - 1), L.DARK_TILES)
    for x in range(x1 + 3, x2 - 2, 4):
        for z in (z1 + 3, z2 - 4):
            L.fill(V(x, 8, z), V(x + 1, 8, z + 1), "minecraft:polished_deepslate")
            L.set_block(V(x, 9, z), "minecraft:skeleton_skull[rotation=8]")
            L.set_block(
                V(x + 1, 9, z + 1), "minecraft:white_candle[candles=1,lit=true]"
            )
    L.fill(V(x1 + 1, 11, z1 + 1), V(x2 - 1, 11, z2 - 1), L.DARK_BRICK)
    for x in range(x1 + 2, x2 - 1, 5):
        L.set_block(V(x, 11, 23), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_block(V(96, 8, 23), "minecraft:cobweb")
    L.set_block(V(104, 10, 19), "minecraft:cobweb")
    # the passage west towards the vault, ending in a small chamber with the lever
    L.fill(V(76, 8, 23), V(x1, 9, 23), L.AIR)
    L.fill(V(76, 7, 23), V(x1, 7, 23), L.DARK_TILES)
    L.fill(V(72, 8, 20), V(75, 10, 26), L.AIR)
    L.fill(V(72, 7, 20), V(75, 7, 26), L.DARK_TILES)
    L.set_block(V(74, 10, 23), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_block(V(75, 8, 20), "minecraft:skeleton_skull[rotation=12]")
    L.set_nbt(
        V(73, 9, 26),
        "minecraft:dark_oak_wall_sign[facing=north]{front_text:{messages:['\"Here lies\"','\"the first lord.\"','\"His gold\"','\"lies further.\"']}}",
    )
    MECHANISMS["crypt_door"] = L.hidden_door(
        V(71, 8, 23), Wd, S, trigger="lever", material=L.DARK_BRICK, lever_b=-1
    )


# ---------------------------------------------------------------- the alchemist's tower

ALCH = (18, 22)  # centre, local


def alchemist_tower() -> None:
    cx, cz = ALCH
    r = 6
    y = YU
    floors = [y, y + 8, y + 16, y + 24]
    L.round_tower(
        V(cx, 0, cz).x,
        V(cx, 0, cz).z,
        r,
        V(0, y - 2, 0).y,
        V(0, y + 31, 0).y,
        floors=[V(0, f, 0).y for f in floors],
        doors=[(V(0, y, 0).y, S, 0)],
        roof="minecraft:oxidized_copper",
        banner="purple",
        stair=False,
    )
    # ground floor: the laboratory
    L.set_block(V(cx - 3, y, cz - 2), "minecraft:brewing_stand")
    L.set_block(V(cx - 3, y, cz - 1), "minecraft:water_cauldron[level=3]")
    L.set_block(V(cx - 3, y, cz), "minecraft:lava_cauldron")
    L.set_block(V(cx - 3, y, cz + 1), "minecraft:brewing_stand")
    L.fill(V(cx + 1, y, cz - 3), V(cx + 3, y + 2, cz - 3), "minecraft:bookshelf")
    L.set_block(V(cx + 3, y, cz + 2), "minecraft:enchanting_table")
    L.set_block(V(cx + 3, y, cz + 3), "minecraft:white_candle[candles=3,lit=true]")
    L.set_block(V(cx - 3, y, cz + 3), "minecraft:decorated_pot")
    # second floor: potions in frames, a telescope... a spyglass on a lectern
    f = floors[1]
    for i, item in enumerate(
        (
            "potion",
            "splash_potion",
            "dragon_breath",
            "ghast_tear",
            "blaze_powder",
            "spider_eye",
        )
    ):
        item_frame(V(cx - 4, f + 1 + i % 2, cz - 2 + i // 2 * 2), 5, item)
    L.set_block(V(cx + 3, f, cz), "minecraft:lectern[facing=west,has_book=true]")
    L.set_block(V(cx + 3, f, cz + 2), "minecraft:amethyst_cluster[facing=up]")
    L.set_block(V(cx - 2, f, cz + 3), "minecraft:brewing_stand")
    # third floor: the orrery... crystals and an end rod display
    f = floors[2]
    for dx, dz in ((3, 0), (-3, 0), (0, 3), (0, -3)):
        L.set_block(V(cx + dx, f, cz + dz), "minecraft:amethyst_block")
        L.set_block(V(cx + dx, f + 1, cz + dz), "minecraft:end_rod")
    L.set_block(V(cx + 3, f, cz + 3), "minecraft:sea_lantern")
    # top floor: the engine
    engine(cx, cz, floors[3])


def engine(cx: int, cz: int, y: int) -> None:
    """
    The alchemist's engine: a ring of eight hoppers passes two amethyst
    shards round and round; twelve comparators read the hoppers and chase
    lamps round the ring, pump a copper piston and strike note blocks.
    It runs while a player is near (the server pauses otherwise).
    Everything stands on the tower's top floor (standing level y).
    """
    ring = [
        ((-1, -1), "east"),
        ((0, -1), "east"),
        ((1, -1), "south"),
        ((1, 0), "south"),
        ((1, 1), "west"),
        ((0, 1), "west"),
        ((-1, 1), "north"),
        ((-1, 0), "north"),
    ]
    for (dx, dz), facing in ring:
        L.set_block(V(cx + dx, y, cz + dz), f"minecraft:hopper[facing={facing}]")
    for dx, dz in ((-1, -1), (1, 1)):
        h = V(cx + dx, y, cz + dz)
        L.cmd(
            f"item replace block {h.x} {h.y} {h.z} container.2 with minecraft:amethyst_shard 1"
        )
    # comparators outside the ring read the hoppers; lamps (or the pump) beyond them
    lamps = []
    for dx in (-1, 0, 1):
        for dz, facing in ((-2, "south"), (2, "north")):
            L.set_block(
                V(cx + dx, y, cz + dz), f"minecraft:comparator[facing={facing}]"
            )
            out = V(cx + dx, y, cz + dz + (dz // 2))
            if dx == 0 and dz == 2:
                L.set_block(out, L.DUST)  # the pump and a note block hang off this one
                L.set_block(V(cx + 1, y, cz + 3), "minecraft:sticky_piston[facing=up]")
                L.set_block(V(cx + 1, y + 1, cz + 3), "minecraft:copper_block")
                L.set_block(V(cx - 1, y, cz + 3), "minecraft:note_block")
            else:
                L.set_block(out, "minecraft:redstone_lamp")
                lamps.append(out)
    for dz in (-1, 0, 1):
        for dx, facing in ((-2, "east"), (2, "west")):
            L.set_block(
                V(cx + dx, y, cz + dz), f"minecraft:comparator[facing={facing}]"
            )
            out = V(cx + dx + (dx // 2), y, cz + dz)
            L.set_block(
                out, "minecraft:redstone_lamp" if dz else "minecraft:note_block"
            )
            if dz:
                lamps.append(out)
    # decoration: an observer, crystals and a warning
    L.set_block(V(cx, y + 1, cz), "minecraft:observer[facing=up]")
    L.set_block(V(cx, y + 2, cz), "minecraft:lightning_rod")
    L.fill(V(cx - 3, y + 3, cz - 3), V(cx - 3, y + 4, cz - 3), L.CHAIN)
    L.set_block(V(cx - 3, y + 2, cz - 3), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_block(V(cx + 3, y, cz - 3), "minecraft:lectern[facing=west,has_book=true]")
    L.set_nbt(
        V(cx + 3, y + 1, cz - 3),
        "minecraft:dark_oak_wall_sign[facing=west]{front_text:{messages:['\"The Engine\"','\"do not touch\"','\"the hoppers\"','\"\"']}}",
    )
    MECHANISMS["engine"] = {"lamps": lamps, "piston": V(cx + 1, y, cz + 3)}


# ---------------------------------------------------------------- the bailey's buildings

WELL = (60, 105)


def bailey_buildings() -> None:
    # paths first: from the gate to the grand stair, and across to the buildings
    L.fill(V(XG - 2, -1, UD + YU + 1), V(XG + 2, -1, ZS - 9), "minecraft:dirt_path")
    L.fill(V(XG - 1, -1, UD + YU + 1), V(XG + 1, -1, ZS - 9), L.ANDESITE)
    L.fill(V(17, -1, 104), V(103, -1, 106), "minecraft:dirt_path")
    stables()
    smithy()
    barracks()
    well()
    # a market: two stalls by the gate
    for x in (70, 78):
        L.fill(V(x, -1, 130), V(x + 4, -1, 132), L.PLANKS)
        for dx, dz in ((0, 0), (4, 0), (0, 2), (4, 2)):
            L.fill(
                V(x + dx, 0, 130 + dz),
                V(x + dx, 2, 130 + dz),
                "minecraft:dark_oak_fence",
            )
        L.fill(
            V(x, 3, 130),
            V(x + 4, 3, 132),
            "minecraft:red_wool" if x == 70 else "minecraft:white_wool",
        )
        L.fill(V(x + 1, 0, 131), V(x + 3, 0, 131), "minecraft:dark_oak_slab[type=top]")
        L.set_block(V(x + 2, 0, 130), "minecraft:barrel[facing=up]")
        L.set_block(V(x + 1, 1, 131), "minecraft:lantern")
    L.set_block(V(72, 1, 131), "minecraft:cake")
    L.set_block(V(80, 1, 131), "minecraft:pumpkin")
    L.set_block(V(74, 0, 132), "minecraft:hay_block")


def stables() -> None:
    x1, z1, x2, z2 = 3, 92, 15, 122
    L.fill(V(x1, -1, z1), V(x2, -1, z2), "minecraft:coarse_dirt")
    L.fill(V(x1, 4, z1), V(x2, 4, z2), "minecraft:dark_oak_slab[type=bottom]")
    L.fill(V(x1, 4, z1), V(x2, 4, z1), L.PLANKS)
    L.fill(V(x1, 4, z2), V(x2, 4, z2), L.PLANKS)
    for z in range(z1, z2 + 1, 5):
        L.fill(V(x2, 0, z), V(x2, 3, z), "minecraft:stripped_dark_oak_log")
        L.fill(V(x1, 0, z), V(x2 - 1, 0, z), "minecraft:dark_oak_fence") if z not in (
            z1,
            z2,
        ) else None
        L.set_block(V(x2 - 1, 3, z), "minecraft:lantern")
    L.fill(V(x1, 0, z1), V(x2 - 1, 2, z1), L.PLANKS)
    L.fill(V(x1, 0, z2), V(x2 - 1, 2, z2), L.PLANKS)
    for z in range(z1 + 2, z2, 5):
        L.fill(V(x1, 0, z), V(x1 + 1, 0, z + 1), "minecraft:hay_block")
        L.set_block(V(x1 + 2, 0, z + 2), "minecraft:water_cauldron[level=3]")
        L.cmd(
            f"summon minecraft:horse {V(x1 + 6, 0, z + 1).x + 0.5} {V(0, 0, 0).y} {V(0, 0, z + 1).z + 0.5}"
        )
    L.set_nbt(
        V(x2 + 1, 1, 107),
        "minecraft:oak_sign[rotation=4]{front_text:{messages:['\"Stables\"','\"\"','\"\"','\"\"']}}",
    )


def smithy() -> None:
    x1, z1, x2, z2 = 104, 95, 117, 115
    y = 0
    L.fill(V(x1, y - 1, z1), V(x2, y + 4, z2), L.COBBLE)
    L.fill(V(x1 + 1, y, z1 + 1), V(x2 - 1, y + 4, z2 - 1), L.AIR)
    L.fill(V(x1 + 1, y - 1, z1 + 1), V(x2 - 1, y - 1, z2 - 1), "minecraft:smooth_stone")
    gable_roof(
        V(x1, y + 4, z1),
        V(x2, y + 4, z2),
        "minecraft:spruce_stairs",
        gable=L.COBBLE,
        axis="z",
        overhang=1,
    )
    doorway(V(x1, y, 104), V(x1, y, 106))
    L.fill(
        V(x1, y + 2, 104),
        V(x1, y + 2, 106),
        "minecraft:spruce_trapdoor[facing=west,half=top,open=false]",
    )
    # the forge: a chimney over a campfire, blast furnaces, anvils
    L.fill(V(x2 - 3, y, z1 + 1), V(x2 - 1, y + 12, z1 + 1), L.DARK_BRICK)
    L.fill(V(x2 - 3, y, z1 + 1), V(x2 - 1, y + 1, z1 + 1), L.AIR)
    L.set_block(V(x2 - 2, y, z1 + 1), "minecraft:campfire[lit=true]")
    L.set_block(V(x2 - 2, y + 13, z1 + 1), "minecraft:campfire[lit=true]")
    L.fill(V(x2 - 3, y + 2, z1 + 1), V(x2 - 1, y + 2, z1 + 1), L.DARK_BRICK)
    L.set_block(V(x2 - 1, y, z1 + 3), "minecraft:blast_furnace[facing=west]")
    L.set_block(V(x2 - 1, y, z1 + 4), "minecraft:blast_furnace[facing=west]")
    L.set_block(V(x2 - 1, y, z1 + 6), "minecraft:anvil[facing=north]")
    L.set_block(V(x2 - 1, y, z1 + 8), "minecraft:grindstone[face=floor,facing=west]")
    L.set_block(V(x2 - 1, y, z1 + 10), "minecraft:smithing_table")
    L.set_block(V(x2 - 1, y, z1 + 12), "minecraft:water_cauldron[level=3]")
    L.set_block(V(x1 + 2, y, z1 + 2), "minecraft:anvil[facing=east]")
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
    L.fill(
        V(x1 + 1, y + 4, z1 + 1), V(x2 - 1, y + 4, z2 - 1), L.PLANKS
    )  # a ceiling under the roof
    lanterns(x1 + 1, z1 + 1, x2 - 1, z2 - 1, y + 3, step=6)
    L.set_nbt(
        V(x1 - 1, 1, 103),
        "minecraft:oak_sign[rotation=12]{front_text:{messages:['\"The Smithy\"','\"\"','\"\"','\"\"']}}",
    )
    # the secret: a trapdoor in the floor over a ladder down to the lower treasury
    L.set_block(
        V(107, y - 1, 107),
        "minecraft:spruce_trapdoor[facing=north,half=top,open=false]",
    )
    L.fill(V(107, -14, 107), V(107, y - 2, 107), L.AIR)
    L.fill(V(107, -14, 107), V(107, y - 2, 107), "minecraft:ladder[facing=north]")
    L.set_block(V(107, -15, 107), L.COBBLE)
    L.fill(
        V(105, y, 107), V(109, y, 107), "minecraft:red_carpet"
    )  # a rug... over the trapdoor? carpet cannot sit on a trapdoor
    L.set_block(V(107, y, 107), L.AIR)


def barracks() -> None:
    x1, z1, x2, z2 = 3, 70, 16, 88
    L.fill(V(x1, -1, z1), V(x2, 4, z2), L.COBBLE)
    L.fill(V(x1 + 1, 0, z1 + 1), V(x2 - 1, 4, z2 - 1), L.AIR)
    L.fill(V(x1 + 1, -1, z1 + 1), V(x2 - 1, -1, z2 - 1), L.PLANKS)
    gable_roof(
        V(x1, 4, z1),
        V(x2, 4, z2),
        "minecraft:spruce_stairs",
        gable=L.COBBLE,
        axis="z",
        overhang=1,
    )
    doorway(V(x2, 0, 78), V(x2, 0, 79))
    for z in range(z1 + 2, z2 - 2, 3):
        bed(V(x1 + 1, 0, z), "east", "white")
        L.set_block(V(x1 + 3, 0, z), "minecraft:chest[facing=east]")
    for z in range(z1 + 3, z2 - 2, 6):
        L.fill(V(x2, 1, z), V(x2, 2, z), L.GLASS)
    L.fill(V(x2 - 2, 0, 73), V(x2 - 2, 0, 85), "minecraft:dark_oak_slab[type=top]")
    L.fill(
        V(x1 + 1, 4, z1 + 1), V(x2 - 1, 4, z2 - 1), L.PLANKS
    )  # a ceiling under the roof
    lanterns(x1 + 1, z1 + 1, x2 - 1, z2 - 1, 3, step=6)
    L.set_nbt(
        V(x2 + 1, 1, 77),
        "minecraft:oak_sign[rotation=4]{front_text:{messages:['\"Barracks\"','\"\"','\"\"','\"\"']}}",
    )


def well() -> None:
    x, z = WELL
    # the well head
    L.fill(V(x - 1, 0, z - 1), V(x + 1, 0, z + 1), "minecraft:cobblestone_wall")
    L.fill(V(x - 1, -1, z - 1), V(x + 1, -1, z + 1), L.COBBLE)
    for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        L.fill(V(x + dx, 1, z + dz), V(x + dx, 3, z + dz), "minecraft:dark_oak_fence")
    L.fill(
        V(x - 2, 4, z - 2), V(x + 2, 4, z + 2), "minecraft:dark_oak_slab[type=bottom]"
    )
    L.set_block(V(x, 3, z), f"{L.LANTERN}[hanging=true]")
    # the shaft: water with soul sand at the bottom (a bubble column lifts you back up)
    L.fill(V(x, -9, z), V(x, 0, z), L.AIR)
    L.set_block(V(x, -9, z), "minecraft:soul_sand")
    L.fill(V(x, -8, z), V(x, -1, z), L.WATER)
    # the shaft's walls, then a door at the bottom into the tunnel east
    L.shell(V(x - 1, -9, z - 1), V(x + 1, -1, z + 1), L.MOSSY_COBBLE)
    L.fill(V(x + 1, -8, z), V(x + 1, -7, z), L.AIR)
    door(V(x + 1, -8, z), "east", "dark_oak")
    # the tunnel: east to x = 65, then south to the dungeon's hidden chamber, and north
    # (level under the bailey, then climbing under the upper ward) to the vault
    L.fill(V(x + 2, -8, z), V(65, -7, z), L.AIR)
    L.fill(V(x + 2, -9, z), V(65, -9, z), L.COBBLE)
    L.fill(V(65, -8, z), V(65, -7, 138), L.AIR)
    L.fill(V(65, -9, z), V(65, -9, 138), L.COBBLE)
    for zz in range(z + 4, 139, 8):
        L.set_block(V(65, -6, zz), f"{L.SOUL_LANTERN}[hanging=true]")
    for xx in range(x + 4, 65, 4):
        L.set_block(V(xx, -6, z), f"{L.SOUL_LANTERN}[hanging=true]")
    stairway(
        [V(65, -9, z - 1), V(65, -9, UD + 1), V(65, 7, UD - 15), V(65, 7, 32)],
        L.BRICK_STAIRS,
        width=1,
        clearance=3,
    )
    for zz in range(z - 8, UD, -8):
        L.set_block(V(65, -6, zz), f"{L.SOUL_LANTERN}[hanging=true]")
    for zz in range(UD - 20, 33, -8):
        L.set_block(V(65, 11, zz), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_nbt(
        V(x + 2, -7, z - 1),
        "minecraft:dark_oak_wall_sign[facing=south]{front_text:{messages:['\"South: dungeons\"','\"North: climb\"','\"to the vault\"','\"\"']}}",
    )


# ---------------------------------------------------------------- the dungeons


def dungeons() -> None:
    y = -8  # the dungeon's standing level
    # the entrance: a little stone hut in the courtyard over a stair going south
    L.fill(V(93, -1, 108), V(97, 3, 112), L.COBBLE)
    L.fill(V(94, 0, 109), V(96, 2, 111), L.AIR)
    L.fill(V(94, 4, 108), V(96, 4, 112), L.COBBLE)
    doorway(V(95, 0, 108), V(95, 0, 108))
    L.set_block(V(95, 2, 109), f"{L.LANTERN}[hanging=true]")
    L.set_nbt(
        V(94, 1, 107),
        "minecraft:oak_wall_sign[facing=north]{front_text:{messages:['\"DUNGEONS\"','\"mind your step\"','\"\"','\"\"']}}",
    )
    stairway([V(95, -1, 112), V(95, y - 1, 120)], L.BRICK_STAIRS, width=1, clearance=3)
    L.fill(V(95, y - 1, 121), V(95, y - 1, 133), L.COBBLE)
    L.fill(V(95, y, 121), V(95, y + 1, 133), L.AIR)
    MECHANISMS["pit_trap"] = L.pit_trap(
        V(95, 0, 0).x, V(0, y, 0).y, V(0, 0, 127).z, 7, travel=1
    )
    # the guard room
    L.fill(V(90, y - 1, 134), V(100, y + 3, 140), L.BRICK)
    L.fill(V(91, y, 135), V(99, y + 2, 139), L.AIR)
    doorway(V(95, y, 134), V(95, y, 134))
    table(V(94, y, 137), V(96, y, 137))
    L.set_block(V(95, y + 1, 137), "minecraft:white_candle[candles=2,lit=true]")
    L.set_block(V(93, y, 137), "minecraft:dark_oak_stairs[facing=east]")
    L.set_block(V(97, y, 137), "minecraft:dark_oak_stairs[facing=west]")
    chest(V(99, y, 135), "west", [("bread", 3), ("iron_sword", 1), ("lead", 2)])
    L.set_block(V(91, y, 139), "minecraft:water_cauldron[level=2]")
    L.set_block(V(95, y + 2, 137), f"{L.LANTERN}[hanging=true]")
    # the cell block: a corridor west with cells both sides
    L.fill(V(69, y - 1, 131), V(90, y + 3, 143), L.BRICK)
    L.fill(V(70, y, 136), V(90, y + 2, 138), L.AIR)
    for i, x in enumerate(range(70, 87, 4)):
        for zc, zdoor, facing in ((132, 135, "south"), (140, 139, "north")):
            L.fill(V(x, y, zc), V(x + 2, y + 1, zc + 2), L.AIR)
            L.fill(V(x, y, zdoor), V(x + 2, y + 1, zdoor), L.BARS)
            L.set_block(
                V(x + 1, y, zdoor), f"minecraft:iron_door[facing={facing},half=lower]"
            )
            L.set_block(
                V(x + 1, y + 1, zdoor),
                f"minecraft:iron_door[facing={facing},half=upper]",
            )
            # a button on the corridor side opens the door
            zb = zdoor + (1 if facing == "south" else -1)
            L.set_block(
                V(x + 2, y + 1, zb),
                f"minecraft:stone_button[face=wall,facing={facing}]",
            )
            L.set_block(
                V(x, y, zc if facing == "south" else zc + 2), "minecraft:hay_block"
            )
            if i % 2 == 0:
                L.set_block(V(x + 2, y + 1, zc + 1), L.CHAIN)
                L.set_block(V(x + 2, y, zc + 1), "minecraft:skeleton_skull[rotation=4]")
            else:
                L.set_block(V(x + 2, y + 1, zc + 1), "minecraft:cobweb")
    for x in range(72, 90, 6):
        L.set_block(V(x, y + 2, 137), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_block(V(88, y, 136), "minecraft:water_cauldron[level=1]")
    # the secret in the last cell: a lever opens the end wall of the corridor
    MECHANISMS["cell_door"] = L.hidden_door(
        V(69, y, 137), Wd, S, trigger="lever", material=L.BRICK, lever_b=-3
    )
    # the hidden chamber behind it (x 66..68, z 134..145) opens onto the well tunnel at x = 65
    L.set_nbt(
        V(66, y + 1, 141),
        "minecraft:dark_oak_wall_sign[facing=east]{front_text:{messages:['\"The prisoners\"','\"dug this.\"','\"North to the well\"','\"and the vault\"']}}",
    )
    catacombs()


def catacombs() -> None:
    """under the dungeon: the oubliette, the arrow trap and the lower treasury"""
    y = -15
    # the oubliette, where the pit drops you
    L.fill(V(91, y - 1, 123), V(99, y + 3, 132), L.DARK_BRICK)
    L.fill(V(92, y, 124), V(98, y + 2, 131), L.AIR)
    L.fill(V(92, y - 1, 124), V(98, y - 1, 131), L.MOSSY_COBBLE)
    L.set_block(V(92, y, 124), "minecraft:skeleton_skull[rotation=6]")
    L.set_block(V(98, y, 131), "minecraft:cobweb")
    L.set_block(V(93, y + 2, 125), "minecraft:redstone_torch")
    L.set_nbt(
        V(93, y + 1, 131),
        "minecraft:dark_oak_wall_sign[facing=north]{front_text:{messages:['\"You fell for it.\"','\"The only way\"','\"out is north,\"','\"and it is guarded.\"']}}",
    )
    # the trap corridor north, 3 wide, dispensers in its end wall
    L.fill(V(93, y - 1, 105), V(97, y + 3, 123), L.DARK_BRICK)
    L.fill(V(94, y, 109), V(96, y + 1, 123), L.AIR)
    L.fill(V(94, y - 1, 109), V(96, y - 1, 123), L.MOSSY_COBBLE)
    L.fill(
        V(98, y - 1, 105), V(99, y + 4, 120), L.DARK_BRICK
    )  # thick east wall for the wiring
    L.fill(
        V(95, y + 3, 127), V(95, y + 5, 128), L.AIR
    )  # the pit's shaft through the oubliette's ceiling
    MECHANISMS["arrow_trap"] = L.arrow_trap(
        V(94, 0, 0).x, V(96, 0, 0).x, V(0, y, 0).y, V(0, 0, 118).z, V(0, 0, 108).z
    )
    L.set_block(V(96, y + 2, 115), "minecraft:soul_lantern[hanging=true]")
    # a door east into the lower treasury
    L.fill(V(100, y - 1, 104), V(110, y + 3, 114), L.DARK_BRICK)
    L.fill(V(101, y, 105), V(109, y + 2, 113), L.AIR)
    L.fill(V(101, y - 1, 105), V(109, y - 1, 113), L.DARK_TILES)
    doorway(V(97, y, 110), V(100, y, 111))
    chest(
        V(103, y, 106),
        "south",
        [
            ("gold_ingot", 24),
            ("emerald", 10),
            ("iron_ingot", 32),
            ("golden_apple", 2),
            ("diamond", 3),
        ],
    )
    chest(
        V(105, y, 106),
        "south",
        [("bow", 1), ("arrow", 64), ("spectral_arrow", 16), ("leather_chestplate", 1)],
    )
    L.set_block(V(107, y, 106), "minecraft:chest[facing=south]")
    L.fill(V(108, y, 105), V(109, y + 1, 106), "minecraft:gold_block")
    L.fill(V(101, y, 112), V(102, y, 113), "minecraft:raw_gold_block")
    L.set_block(V(105, y + 2, 109), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_block(V(101, y, 109), "minecraft:skeleton_skull[rotation=4]")
    # the ladder up into the smithy (built by smithy()) arrives at (107, y, 107)
    L.set_nbt(
        V(106, y + 1, 105),
        "minecraft:dark_oak_wall_sign[facing=south]{front_text:{messages:['\"Up: the smithy\"','\"(the ladder)\"','\"\"','\"\"']}}",
    )


# ---------------------------------------------------------------- the vault

VAULT = (50, 16, 70, 30)


def vault() -> None:
    x1, z1, x2, z2 = VAULT
    y = 8
    L.fill(
        V(x1 - 1, y - 2, z1 - 1),
        V(x2 + 1, y + 4, z2 + 1),
        "minecraft:polished_blackstone_bricks",
    )
    L.fill(V(x1, y, z1), V(x2, y + 3, z2), L.AIR)
    L.fill(V(x1, y - 1, z1), V(x2, y - 1, z2), L.DARK_TILES)
    for x in range(x1 + 2, x2, 4):
        for z in range(z1 + 2, z2, 4):
            L.set_block(V(x, y - 1, z), "minecraft:sea_lantern")
    # the ladder from the library arrives at (60, y, 20); the crypt door is in the east wall;
    # the well tunnel arrives from the south at (67, y, 31)
    L.fill(V(65, y, z2 + 1), V(65, y + 1, z2 + 1), L.AIR)
    L.set_block(V(65, y, z2 + 1), "minecraft:iron_door[facing=north,half=lower]")
    L.set_block(V(65, y + 1, z2 + 1), "minecraft:iron_door[facing=north,half=upper]")
    L.set_block(
        V(66, y + 1, z2), "minecraft:stone_button[face=wall,facing=north]"
    )  # both buttons power the block beside the door
    L.set_block(V(66, y + 1, z2 + 2), "minecraft:stone_button[face=wall,facing=south]")
    # the library's ladder comes down at (60, *, 20): a pillar for it to hang on
    L.fill(V(60, y, 19), V(60, y + 4, 19), "minecraft:polished_blackstone")
    L.fill(
        V(60, y, 20), V(60, y + 4, 20), "minecraft:ladder[facing=south]"
    )  # through the vault's ceiling too
    # gold and gems
    for x, z in ((x1, z1), (x2 - 1, z1), (x1, z2 - 1), (x2 - 1, z2 - 1)):
        L.fill(V(x, y, z), V(x + 1, y + 1, z + 1), "minecraft:gold_block")
    L.fill(V(59, y, 22), V(61, y, 24), "minecraft:polished_blackstone")
    L.set_block(V(60, y + 1, 23), "minecraft:diamond_block")
    L.set_block(V(60, y + 2, 23), "minecraft:end_rod")
    L.fill(V(52, y, 22), V(52, y, 24), "minecraft:emerald_block")
    L.fill(V(68, y, 22), V(68, y, 24), "minecraft:lapis_block")
    L.fill(V(55, y, 29), V(57, y, 29), "minecraft:raw_gold_block")
    L.fill(V(63, y, 29), V(65, y, 29), "minecraft:netherite_block")
    chests = [
        (
            V(54, y, 17),
            [
                ("diamond", 32),
                ("emerald", 32),
                ("gold_ingot", 64),
                ("netherite_ingot", 4),
                ("enchanted_golden_apple", 2),
            ],
        ),
        (
            V(56, y, 17),
            [
                ("diamond_block", 8),
                ("gold_block", 8),
                ("emerald_block", 4),
                ("totem_of_undying", 1),
            ],
        ),
        (
            V(58, y, 17),
            [
                ("elytra", 1),
                ("trident", 1),
                ("nether_star", 1),
                ("heart_of_the_sea", 1),
            ],
        ),
        (
            V(62, y, 17),
            [
                ("diamond_sword", 1),
                ("diamond_pickaxe", 1),
                ("diamond_chestplate", 1),
                ("golden_apple", 8),
            ],
        ),
        (
            V(64, y, 17),
            [
                ("music_disc_pigstep", 1),
                ("music_disc_otherside", 1),
                ("amethyst_shard", 32),
                ("echo_shard", 4),
            ],
        ),
        (
            V(66, y, 17),
            [
                ("diamond", 16),
                ("ancient_debris", 8),
                ("gold_ingot", 32),
                ("emerald", 16),
            ],
        ),
    ]
    for pos, items in chests:
        chest(pos, "south", items)
    for i, item in enumerate(
        (
            "diamond",
            "emerald",
            "netherite_ingot",
            "nether_star",
            "golden_apple",
            "heart_of_the_sea",
        )
    ):
        item_frame(V(53 + i * 2, y + 2, z1), 3, item)
    armour_stand(V(52, y, 27) + Vec3(0.5, 0, 0.5), "golden", 180)
    armour_stand(V(68, y, 27) + Vec3(0.5, 0, 0.5), "netherite", 180)
    L.set_block(V(60, y, 27), "minecraft:enchanting_table")
    L.set_block(V(60, y, 28), "minecraft:lectern[facing=north,has_book=true]")
    for x in (x1 + 5, x2 - 5):
        for z in (z1 + 1, z2 - 1):
            L.set_block(V(x, y + 3, z), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_nbt(
        V(60, y + 1, 16),
        "minecraft:dark_oak_wall_sign[facing=south]{front_text:{messages:['\"The Vault\"','\"of the castle.\"','\"You found it.\"','\"\"']}}",
    )


# ---------------------------------------------------------------- details


def details() -> None:
    # banners along the bailey and upper walls
    for x in range(10, W - 10, 20):
        L.set_block(V(x, 8, ZS - 3), "minecraft:red_wall_banner[facing=north]")
        L.set_block(V(x, YU + 8, 3), "minecraft:blue_wall_banner[facing=south]")
    for z in range(UD + 10, ZS - 10, 20):
        L.set_block(V(3, 8, z), "minecraft:red_wall_banner[facing=east]")
        L.set_block(V(W - 4, 8, z), "minecraft:red_wall_banner[facing=west]")
    # courtyard lanterns on posts
    for x, z in ((40, 90), (80, 90), (40, 125), (80, 125), (30, 110), (90, 110)):
        L.fill(V(x, 0, z), V(x, 2, z), "minecraft:dark_oak_fence")
        L.set_block(V(x, 3, z), L.LANTERN)
    for x, z in ((30, 30), (30, 50), (85, 50), (110, 8)):
        L.fill(V(x, YU, z), V(x, YU + 2, z), "minecraft:dark_oak_fence")
        L.set_block(V(x, YU + 3, z), L.LANTERN)
    # a garden in the upper ward, south-west of the keep
    for x, z in ((12, 40), (20, 48), (30, 56), (8, 56)):
        L.fill(V(x, YU, z), V(x, YU + 3, z), "minecraft:dark_oak_log")
        L.fill(
            V(x - 2, YU + 3, z - 2),
            V(x + 2, YU + 5, z + 2),
            "minecraft:dark_oak_leaves[persistent=true]",
        )
        L.fill(
            V(x - 1, YU + 6, z - 1),
            V(x + 1, YU + 6, z + 1),
            "minecraft:dark_oak_leaves[persistent=true]",
        )
    for x in range(8, 36, 2):
        for z in range(36, 60, 2):
            if (x + z) % 6 == 0:
                L.set_block(
                    V(x, YU, z), "minecraft:poppy" if x % 4 else "minecraft:cornflower"
                )
    L.fill(V(14, YU - 1, 44), V(26, YU - 1, 52), "minecraft:water")
    L.shell(V(13, YU - 1, 43), V(27, YU - 1, 53), L.BRICK)
    # guards: armour stands at the gate and the keep door
    for x in (XG - 3, XG + 3):
        armour_stand(V(x, 0, ZS - 9) + Vec3(0.5, 0, 0.5), "iron")
        armour_stand(V(x, YU, KZ2 + 2) + Vec3(0.5, 0, 0.5), "iron")
    # a flagpole on the keep's lantern tower is the banner; signs at the main places
    L.set_nbt(
        V(XG + 4, 0, ZS - 10),
        "minecraft:oak_sign[rotation=0]{front_text:{messages:['\"Welcome to\"','\"Castle\"','\"Fable\"','\"\"']}}",
    )
    L.set_nbt(
        V(XG + 5, YU, UD - 8),
        "minecraft:oak_sign[rotation=0]{front_text:{messages:['\"The Keep\"','\"Chapel: east\"','\"Alchemist: west\"','\"\"']}}",
    )
    L.cmd(
        f"summon minecraft:iron_golem {V(XG, 0, ZS - 12).x + 0.5} {V(0, 0, 0).y} {V(0, 0, ZS - 12).z + 0.5}"
    )
    L.cmd(
        f"summon minecraft:cat {V(IX1 + 6, F1 + 1, 30).x + 0.5} {V(0, F1 + 1, 0).y} {V(0, 0, 30).z + 0.5}"
    )
