"""
Colours for rendering blocks: a map from block name to an RGBA colour.

mciwb does not ship Minecraft's textures. Instead each block gets a single
colour, close to the average colour of its texture, from:

1. a curated table of common blocks (`BLOCK_COLOURS`),
2. rules for families of blocks: the 16 dye colours (``red_wool``,
   ``blue_concrete``, ``lime_stained_glass`` ...), the wood types
   (``spruce_planks``, ``cherry_log``, ``birch_leaves`` ...), shapes made from
   another block (``stone_brick_stairs`` is coloured like ``stone_bricks``),
   and waxed or weathered copper,
3. keywords in the name (``_ore``, ``glass``, ``coral`` ...),
4. otherwise a muted colour made from a hash of the name, so that unknown
   blocks (e.g. from mods) still differ from each other.

The alpha channel says how much light a block stops: 0 for air, 255 for a
solid block. Translucent blocks such as glass and water, and small blocks such
as torches, flowers and fences, are partly transparent, so the blocks behind
them show through.

Add or change colours for one render with a `Palette`, or for every render
with `set_colour`::

    from mciwb.palette import set_colour
    set_colour("minecraft:gold_block", (255, 215, 0))
"""

from __future__ import annotations

import colorsys
import zlib
from collections.abc import Mapping

RGB = tuple[int, int, int]
RGBA = tuple[int, int, int, int]

# alpha of glass and the like, of water, and of small blocks that only fill
# part of their space
GLASS_ALPHA = 80
WATER_ALPHA = 150
THIN_ALPHA = 170

# blocks that are never drawn
INVISIBLE = {
    "air",
    "cave_air",
    "void_air",
    "barrier",
    "light",
    "structure_void",
    "moving_piston",
}

DYE_COLOURS: dict[str, RGB] = {
    "white": (234, 236, 237),
    "orange": (240, 118, 19),
    "magenta": (189, 68, 179),
    "light_blue": (58, 175, 217),
    "yellow": (248, 197, 39),
    "lime": (112, 185, 25),
    "pink": (237, 141, 172),
    "gray": (62, 68, 71),
    "light_gray": (142, 142, 134),
    "cyan": (21, 137, 145),
    "purple": (121, 42, 172),
    "blue": (53, 57, 157),
    "brown": (114, 71, 40),
    "green": (84, 109, 27),
    "red": (160, 39, 34),
    "black": (20, 21, 25),
}

# dyed terracotta is much more muted than the dye colour
TERRACOTTA_COLOURS: dict[str, RGB] = {
    "white": (209, 178, 161),
    "orange": (161, 83, 37),
    "magenta": (149, 88, 108),
    "light_blue": (113, 108, 137),
    "yellow": (186, 133, 35),
    "lime": (103, 117, 52),
    "pink": (161, 78, 78),
    "gray": (57, 42, 35),
    "light_gray": (135, 106, 97),
    "cyan": (86, 91, 91),
    "purple": (118, 70, 86),
    "blue": (74, 59, 91),
    "brown": (77, 51, 35),
    "green": (76, 83, 42),
    "red": (143, 61, 46),
    "black": (37, 22, 16),
}


class Wood:
    """the colours of a wood type"""

    def __init__(self, planks: RGB, log: RGB, leaves: RGB | None = None):
        self.planks = planks
        self.log = log
        self.leaves = leaves


WOODS: dict[str, Wood] = {
    "oak": Wood((162, 130, 78), (109, 85, 50), (64, 120, 36)),
    "spruce": Wood((114, 84, 48), (58, 37, 16), (60, 94, 60)),
    "birch": Wood((192, 175, 121), (216, 215, 210), (96, 130, 60)),
    "jungle": Wood((160, 115, 80), (85, 67, 25), (48, 130, 30)),
    "acacia": Wood((168, 90, 50), (103, 96, 86), (70, 120, 30)),
    "dark_oak": Wood((66, 43, 20), (60, 46, 26), (54, 100, 26)),
    "mangrove": Wood((117, 54, 48), (84, 66, 36), (80, 120, 40)),
    "cherry": Wood((226, 178, 172), (54, 33, 44), (230, 170, 200)),
    "pale_oak": Wood((227, 217, 215), (87, 77, 75), (160, 165, 155)),
    # poplar is new in Minecraft 26.x, its colours are a guess
    "poplar": Wood((205, 185, 135), (130, 120, 100), (90, 150, 50)),
    "bamboo": Wood((193, 173, 80), (127, 144, 58)),
    "crimson": Wood((101, 48, 70), (92, 25, 29)),
    "warped": Wood((43, 104, 99), (58, 58, 77)),
}

# the average colours of common blocks, by name without the namespace.
# Alpha is 255 unless given.
BLOCK_COLOURS: dict[str, RGB | RGBA] = {
    # stone and friends
    "stone": (125, 125, 125),
    "cobblestone": (118, 118, 118),
    "mossy_cobblestone": (110, 118, 94),
    "stone_bricks": (122, 121, 122),
    "mossy_stone_bricks": (115, 121, 105),
    "cracked_stone_bricks": (118, 117, 118),
    "chiseled_stone_bricks": (119, 118, 119),
    "smooth_stone": (158, 158, 158),
    "granite": (149, 103, 85),
    "polished_granite": (154, 106, 89),
    "diorite": (188, 188, 188),
    "polished_diorite": (192, 193, 194),
    "andesite": (136, 136, 136),
    "polished_andesite": (132, 134, 133),
    "deepslate": (80, 80, 82),
    "cobbled_deepslate": (77, 77, 80),
    "polished_deepslate": (72, 72, 73),
    "deepslate_bricks": (70, 70, 71),
    "deepslate_tiles": (54, 54, 55),
    "chiseled_deepslate": (54, 54, 54),
    "tuff": (108, 109, 102),
    "polished_tuff": (97, 104, 99),
    "tuff_bricks": (98, 103, 95),
    "calcite": (223, 224, 220),
    "dripstone_block": (134, 107, 92),
    "bedrock": (85, 85, 85),
    "obsidian": (15, 10, 24),
    "crying_obsidian": (32, 10, 60),
    "bricks": (150, 97, 83),
    "mud_bricks": (137, 103, 79),
    "packed_mud": (142, 106, 79),
    # sand and earth
    "sand": (219, 207, 163),
    "red_sand": (190, 102, 33),
    "sandstone": (216, 203, 155),
    "cut_sandstone": (217, 206, 159),
    "chiseled_sandstone": (216, 203, 155),
    "smooth_sandstone": (223, 214, 170),
    "red_sandstone": (186, 99, 29),
    "cut_red_sandstone": (189, 101, 31),
    "chiseled_red_sandstone": (183, 97, 28),
    "smooth_red_sandstone": (181, 98, 31),
    "gravel": (131, 127, 126),
    "clay": (160, 166, 179),
    "dirt": (134, 96, 67),
    "coarse_dirt": (119, 85, 59),
    "rooted_dirt": (144, 103, 76),
    "podzol": (91, 63, 24),
    "mycelium": (111, 99, 105),
    "grass_block": (95, 159, 53),
    "dirt_path": (148, 122, 65),
    "farmland": (143, 102, 70),
    "mud": (60, 57, 61),
    "moss_block": (89, 109, 45),
    "moss_carpet": (89, 109, 45, THIN_ALPHA),
    "pale_moss_block": (107, 112, 104),
    "terracotta": (152, 94, 67),
    # snow, ice and liquids
    "snow": (249, 254, 254, THIN_ALPHA),
    "snow_block": (249, 254, 254),
    "powder_snow": (248, 253, 253),
    "ice": (145, 183, 253, 180),
    "packed_ice": (141, 180, 250),
    "blue_ice": (116, 167, 253),
    "water": (63, 118, 228, WATER_ALPHA),
    "bubble_column": (63, 118, 228, WATER_ALPHA),
    "lava": (207, 92, 20),
    # plants
    "short_grass": (95, 159, 53, THIN_ALPHA),
    "tall_grass": (95, 159, 53, THIN_ALPHA),
    "fern": (85, 140, 50, THIN_ALPHA),
    "large_fern": (85, 140, 50, THIN_ALPHA),
    "azalea_leaves": (90, 120, 40),
    "flowering_azalea_leaves": (110, 120, 70),
    "cactus": (85, 127, 43),
    "sugar_cane": (148, 192, 101, THIN_ALPHA),
    "bamboo": (93, 144, 19, THIN_ALPHA),
    "kelp": (88, 142, 45, THIN_ALPHA),
    "seagrass": (88, 142, 45, THIN_ALPHA),
    "vine": (62, 110, 30, THIN_ALPHA),
    "lily_pad": (32, 128, 48, THIN_ALPHA),
    "pumpkin": (198, 118, 24),
    "carved_pumpkin": (198, 118, 24),
    "jack_o_lantern": (214, 152, 52),
    "melon": (111, 145, 30),
    "hay_block": (166, 136, 38),
    "dried_kelp_block": (50, 58, 38),
    "mushroom_stem": (203, 196, 185),
    "brown_mushroom_block": (149, 111, 81),
    "red_mushroom_block": (200, 46, 45),
    "nether_wart_block": (114, 2, 2),
    "warped_wart_block": (22, 119, 121),
    "crimson_nylium": (130, 31, 31),
    "warped_nylium": (43, 114, 101),
    "shroomlight": (240, 146, 70),
    "dandelion": (255, 236, 79, THIN_ALPHA),
    "poppy": (237, 48, 44, THIN_ALPHA),
    "sponge": (195, 192, 74),
    "wet_sponge": (171, 181, 70),
    # the nether and the end
    "netherrack": (97, 38, 38),
    "nether_bricks": (44, 21, 26),
    "red_nether_bricks": (69, 7, 9),
    "soul_sand": (81, 62, 51),
    "soul_soil": (75, 57, 46),
    "basalt": (80, 81, 86),
    "polished_basalt": (88, 88, 91),
    "smooth_basalt": (72, 72, 78),
    "blackstone": (42, 36, 41),
    "polished_blackstone": (53, 48, 56),
    "polished_blackstone_bricks": (48, 42, 49),
    "gilded_blackstone": (56, 43, 38),
    "glowstone": (171, 131, 84),
    "magma_block": (142, 63, 31),
    "end_stone": (219, 222, 158),
    "end_stone_bricks": (218, 224, 162),
    "purpur_block": (169, 125, 169),
    "purpur_pillar": (171, 129, 171),
    "sculk": (12, 29, 36),
    # the ocean
    "prismarine": (99, 156, 151),
    "prismarine_bricks": (99, 171, 158),
    "dark_prismarine": (51, 91, 75),
    "sea_lantern": (172, 199, 190),
    # quartz
    "quartz_block": (235, 229, 222),
    "smooth_quartz": (235, 229, 222),
    "quartz_bricks": (234, 229, 221),
    "quartz_pillar": (235, 230, 224),
    "chiseled_quartz_block": (231, 226, 218),
    # mineral blocks
    "coal_block": (16, 15, 15),
    "iron_block": (220, 220, 220),
    "gold_block": (246, 208, 61),
    "diamond_block": (98, 237, 228),
    "emerald_block": (42, 203, 87),
    "lapis_block": (30, 67, 140),
    "redstone_block": (175, 24, 5),
    "netherite_block": (66, 61, 63),
    "amethyst_block": (133, 97, 191),
    "raw_iron_block": (166, 135, 107),
    "raw_gold_block": (221, 169, 46),
    "raw_copper_block": (154, 105, 79),
    "resin_block": (217, 99, 25),
    "resin_bricks": (206, 101, 39),
    "copper_block": (192, 107, 79),
    "exposed_copper": (161, 125, 103),
    "weathered_copper": (108, 153, 110),
    "oxidized_copper": (82, 162, 132),
    # glass and other see-through blocks
    "glass": (200, 220, 230, GLASS_ALPHA),
    "glass_pane": (200, 220, 230, GLASS_ALPHA),
    "tinted_glass": (44, 38, 46, 200),
    "iron_bars": (136, 139, 135, THIN_ALPHA),
    "cobweb": (228, 233, 234, 120),
    "slime_block": (111, 192, 91, 200),
    "honey_block": (251, 185, 52, 200),
    # furniture and machines
    "bookshelf": (117, 94, 59),
    "crafting_table": (119, 73, 42),
    "furnace": (110, 110, 110),
    "blast_furnace": (108, 108, 107),
    "smoker": (107, 87, 66),
    "chest": (162, 115, 47),
    "trapped_chest": (162, 115, 47),
    "ender_chest": (40, 55, 57),
    "barrel": (134, 100, 58),
    "note_block": (88, 58, 40),
    "jukebox": (94, 64, 47),
    "tnt": (219, 68, 52),
    "target": (226, 170, 157),
    "beacon": (117, 220, 215),
    "anvil": (68, 68, 68),
    "cauldron": (74, 74, 74),
    "hopper": (68, 68, 70),
    "scaffolding": (175, 140, 75, THIN_ALPHA),
    "ladder": (125, 97, 55, THIN_ALPHA),
    "torch": (255, 200, 80, THIN_ALPHA),
    "wall_torch": (255, 200, 80, THIN_ALPHA),
    "soul_torch": (110, 225, 230, THIN_ALPHA),
    "lantern": (106, 91, 83, THIN_ALPHA),
    "redstone_wire": (175, 24, 5, THIN_ALPHA),
    "redstone_torch": (175, 24, 5, THIN_ALPHA),
    "rail": (125, 110, 90, THIN_ALPHA),
    "lever": (110, 95, 70, THIN_ALPHA),
    "light_weighted_pressure_plate": (246, 208, 61, THIN_ALPHA),
    "bone_block": (229, 225, 207),
    "honeycomb_block": (229, 148, 29),
    "ancient_debris": (95, 66, 58),
    "ochre_froglight": (245, 233, 180),
    "verdant_froglight": (229, 244, 228),
    "pearlescent_froglight": (245, 240, 245),
    "cinnabar": (150, 40, 35),
    "sulfur": (200, 190, 60),
    "chiseled_tuff": (100, 105, 98),
    "chiseled_bookshelf": (117, 94, 59),
    "beehive": (182, 146, 89),
    "bee_nest": (196, 151, 75),
    "composter": (110, 75, 40),
    "lectern": (160, 125, 75),
    "loom": (142, 119, 92),
    "smithing_table": (57, 58, 70),
    "fletching_table": (197, 181, 132),
    "cartography_table": (103, 87, 67),
    "enchanting_table": (128, 50, 58),
    "dispenser": (110, 110, 110),
    "dropper": (110, 110, 110),
    "observer": (98, 98, 98),
    "piston": (153, 127, 85),
    "sticky_piston": (120, 150, 90),
    "spawner": (36, 46, 62),
    "trial_spawner": (60, 70, 80),
    "vault": (60, 70, 80),
    "crafter": (110, 100, 95),
    "respawn_anchor": (40, 25, 70),
    "end_portal_frame": (91, 120, 97),
    "end_portal": (0, 0, 0),
    "end_gateway": (0, 0, 0),
    "dragon_egg": (12, 9, 15),
    "chorus_plant": (93, 57, 93),
    "chorus_flower": (151, 120, 151),
    "creaking_heart": (90, 75, 70),
    "fire": (230, 140, 40, THIN_ALPHA),
    "soul_fire": (80, 200, 210, THIN_ALPHA),
    "cake": (240, 220, 210, THIN_ALPHA),
    "bell": (246, 208, 61, THIN_ALPHA),
    "petrified_oak_slab": (162, 130, 78),
    "glow_lichen": (112, 130, 120, THIN_ALPHA),
    "melon_stem": (100, 150, 50, THIN_ALPHA),
    "pumpkin_stem": (100, 150, 50, THIN_ALPHA),
    "attached_melon_stem": (100, 150, 50, THIN_ALPHA),
    "attached_pumpkin_stem": (100, 150, 50, THIN_ALPHA),
    "pale_moss_carpet": (107, 112, 104, THIN_ALPHA),
    "pale_hanging_moss": (107, 112, 104, THIN_ALPHA),
    "leaf_litter": (150, 110, 50, THIN_ALPHA),
    "kelp_plant": (88, 142, 45, THIN_ALPHA),
    "wheat": (170, 160, 60, THIN_ALPHA),
    "carrots": (80, 150, 40, THIN_ALPHA),
    "potatoes": (80, 150, 40, THIN_ALPHA),
    "beetroots": (80, 150, 40, THIN_ALPHA),
    "candle": (225, 210, 170, THIN_ALPHA),
    "candle_cake": (240, 220, 210, THIN_ALPHA),
    "decorated_pot": (140, 80, 60, THIN_ALPHA),
    "end_rod": (240, 235, 225, THIN_ALPHA),
    "conduit": (160, 140, 110, THIN_ALPHA),
    "heavy_core": (80, 85, 95, THIN_ALPHA),
    "soul_lantern": (80, 100, 110, THIN_ALPHA),
    "soul_wall_torch": (110, 225, 230, THIN_ALPHA),
    "tripwire": (200, 200, 200, 60),
    "tripwire_hook": (140, 140, 140, THIN_ALPHA),
    "repeater": (160, 160, 160, THIN_ALPHA),
    "comparator": (160, 160, 160, THIN_ALPHA),
    "daylight_detector": (130, 115, 95, THIN_ALPHA),
    "brewing_stand": (120, 100, 70, THIN_ALPHA),
    "turtle_egg": (230, 225, 200, THIN_ALPHA),
    "sniffer_egg": (150, 60, 50, THIN_ALPHA),
    "sea_pickle": (100, 120, 50, THIN_ALPHA),
    "frogspawn": (100, 90, 80, THIN_ALPHA),
    "cocoa": (150, 90, 40, THIN_ALPHA),
    "spore_blossom": (210, 100, 170, THIN_ALPHA),
    "heavy_weighted_pressure_plate": (220, 220, 220, THIN_ALPHA),
}

# the endings of blocks that are made from another block, e.g. stairs
SHAPES = (
    "_stairs",
    "_slab",
    "_wall",
    "_fence_gate",
    "_fence",
    "_pressure_plate",
    "_button",
    "_trapdoor",
    "_door",
    "_wall_hanging_sign",
    "_hanging_sign",
    "_wall_sign",
    "_sign",
    "_pillar",
    "_grate",
    "_bulb",
    "_shelf",
)

# keywords for small blocks that only fill part of their space, so the
# blocks behind them show through
THIN = (
    "torch",
    "sapling",
    "rail",
    "button",
    "pressure_plate",
    "sign",
    "banner",
    "ladder",
    "vine",
    "lever",
    "tripwire",
    "grass",
    "fern",
    "bush",
    "flower",
    "tulip",
    "orchid",
    "allium",
    "bluet",
    "daisy",
    "cornflower",
    "lily",
    "rose",
    "lilac",
    "peony",
    "pane",
    "bars",
    "fence",
    "door",
    "carpet",
    "candle",
    "chain",
    "pot",
    "coral",
    "seagrass",
    "kelp",
    "mushroom",
    "wheat",
    "carrots",
    "beetroots",
    "berry",
    "head",
    "skull",
    "lantern",
    "rod",
    "petals",
    "roots",
    "sprouts",
    "fungus",
    "dripleaf",
    "pickle",
)

# colour keywords for blocks that nothing else matched, most specific first
KEYWORDS: tuple[tuple[str, RGB | RGBA], ...] = (
    ("glass", (200, 220, 230, GLASS_ALPHA)),
    ("potted_", (124, 68, 52)),
    ("sapling", (70, 130, 40)),
    ("propagule", (90, 140, 60)),
    ("vines", (60, 110, 40)),
    ("roots", (110, 90, 60)),
    ("crimson_fungus", (160, 40, 40)),
    ("warped_fungus", (40, 140, 120)),
    ("stem", (100, 150, 50)),
    ("dripleaf", (90, 140, 50)),
    ("bush", (90, 130, 50)),
    ("eyeblossom", (180, 120, 90)),
    ("froglight", (240, 235, 210)),
    ("sculk", (12, 29, 36)),
    ("command_block", (170, 120, 90)),
    ("structure_block", (90, 75, 90)),
    ("lightning_rod", (192, 107, 79)),
    ("rail", (125, 110, 90)),
    ("cinnabar", (150, 40, 35)),
    ("sulfur", (200, 190, 60)),
    ("head", (190, 190, 180)),
    ("skull", (190, 190, 180)),
    ("campfire", (110, 80, 50)),
    ("cauldron", (74, 74, 74)),
    ("_table", (130, 100, 70)),
    ("deepslate", (80, 80, 82)),
    ("blackstone", (42, 36, 41)),
    ("nether", (97, 38, 38)),
    ("copper", (192, 107, 79)),
    ("tube_coral", (49, 87, 207)),
    ("brain_coral", (207, 91, 159)),
    ("bubble_coral", (161, 24, 160)),
    ("fire_coral", (164, 35, 47)),
    ("horn_coral", (216, 200, 66)),
    ("coral", (130, 123, 119)),
    ("sandstone", (216, 203, 155)),
    ("sand", (219, 207, 163)),
    ("gravel", (131, 127, 126)),
    ("ice", (145, 183, 253)),
    ("snow", (249, 254, 254)),
    ("leaves", (64, 120, 36)),
    ("grass", (95, 159, 53)),
    ("flower", (200, 120, 180)),
    ("tulip", (220, 90, 60)),
    ("allium", (180, 120, 220)),
    ("bluet", (220, 225, 230)),
    ("daisy", (230, 230, 220)),
    ("lilac", (200, 150, 200)),
    ("peony", (230, 170, 200)),
    ("lily_of_the_valley", (230, 230, 230)),
    ("wither_rose", (40, 40, 30)),
    ("orchid", (50, 170, 220)),
    ("cornflower", (70, 100, 220)),
    ("pitcher", (100, 130, 160)),
    ("mushroom", (149, 111, 81)),
    ("dirt", (134, 96, 67)),
    ("bricks", (150, 97, 83)),
    ("quartz", (235, 229, 222)),
    ("prismarine", (99, 156, 151)),
    ("purpur", (169, 125, 169)),
    ("amethyst", (133, 97, 191)),
    ("redstone", (175, 24, 5)),
    ("stone", (125, 125, 125)),
    ("iron", (220, 220, 220)),
    ("gold", (246, 208, 61)),
    ("anvil", (68, 68, 68)),
    ("bed", (160, 39, 34)),
    ("shulker_box", (151, 103, 151)),
)

# the stone that an ore is set in, by prefix
ORE_HOSTS: dict[str, RGB] = {
    "deepslate_": (80, 80, 82),
    "nether_": (97, 38, 38),
}
ORE_MINERALS: dict[str, RGB] = {
    "coal": (46, 46, 46),
    "iron": (216, 175, 147),
    "copper": (224, 128, 90),
    "gold": (252, 238, 75),
    "redstone": (255, 0, 0),
    "emerald": (23, 221, 98),
    "lapis": (30, 67, 140),
    "diamond": (92, 219, 213),
    "quartz": (235, 229, 222),
}

COPPER_AGES = ("exposed_", "weathered_", "oxidized_")


def _mix(a: RGB, b: RGB, amount: float) -> RGB:
    """mix *amount* of colour b into colour a"""
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b, strict=True))  # type: ignore


def _scale(colour: RGB, factor: float) -> RGB:
    return tuple(min(255, round(c * factor)) for c in colour)  # type: ignore


def _rgba(colour: RGB | RGBA) -> RGBA:
    if len(colour) == 4:
        return colour  # type: ignore
    return (*colour, 255)  # type: ignore


def _dyed(name: str) -> RGB | RGBA | None:
    """colours of blocks named <dye colour>_<material>"""
    # try light_blue before blue
    for dye in sorted(DYE_COLOURS, key=len, reverse=True):
        if not name.startswith(dye + "_"):
            continue
        material = name[len(dye) + 1 :]
        colour = DYE_COLOURS[dye]
        if material == "terracotta":
            return TERRACOTTA_COLOURS[dye]
        if material == "glazed_terracotta":
            return _mix(colour, (255, 255, 255), 0.15)
        if material == "concrete_powder":
            return _mix(colour, (255, 255, 255), 0.2)
        if material == "concrete":
            return _scale(colour, 0.9)
        if "glass" in material:
            return (*colour, 110)
        if material in ("carpet", "candle", "banner", "wall_banner", "bed"):
            return (*colour, THIN_ALPHA) if material != "bed" else colour
        return colour
    return None


def _wood(name: str) -> RGB | RGBA | None:
    """colours of blocks made of wood, e.g. oak_planks, stripped_birch_log"""
    stripped = name.startswith("stripped_")
    base = name.removeprefix("stripped_")
    for wood_name in sorted(WOODS, key=len, reverse=True):
        wood = WOODS[wood_name]
        if base == wood_name or base == f"{wood_name}_planks":
            return wood.planks
        rest = base.removeprefix(wood_name + "_")
        if rest == base:
            continue
        if rest in ("log", "wood", "stem", "hyphae", "block"):
            return _scale(wood.planks, 1.05) if stripped else wood.log
        if rest == "leaves":
            return wood.leaves or wood.planks
        if rest in ("mosaic", "planks"):
            return wood.planks
    return None


def _ore(name: str) -> RGB | None:
    """ores: the host stone with a little of the mineral"""
    if not name.endswith("_ore"):
        return None
    host = BLOCK_COLOURS["stone"][:3]
    mineral = name.removesuffix("_ore")
    for prefix, colour in ORE_HOSTS.items():
        if mineral.startswith(prefix):
            host = colour
            mineral = mineral.removeprefix(prefix)
    return _mix(host, ORE_MINERALS.get(mineral, host), 0.3)  # type: ignore


def _hashed(name: str) -> RGB:
    """a muted colour for a block that no rule knows"""
    hue = (zlib.crc32(name.encode()) % 360) / 360
    r, g, b = colorsys.hsv_to_rgb(hue, 0.35, 0.7)
    return round(r * 255), round(g * 255), round(b * 255)


class Palette:
    """
    The colours of blocks, see the module documentation for the rules.

    :param colours: colours that take precedence over the defaults, keyed by
        block name (with or without the ``minecraft:`` namespace), as (r, g, b)
        or (r, g, b, a) with values 0-255
    """

    def __init__(self, colours: Mapping[str, RGB | RGBA] | None = None):
        self._overrides: dict[str, RGBA] = {}
        self._cache: dict[str, RGBA] = {}
        for name, colour in (colours or {}).items():
            self.set(name, colour)

    def set(self, name: str, colour: RGB | RGBA) -> None:
        """
        Set the colour of a block

        :param name: the block name, e.g. "minecraft:stone" or "stone"
        :param colour: (r, g, b) or (r, g, b, a), values 0-255
        """
        if len(colour) not in (3, 4) or not all(0 <= c <= 255 for c in colour):
            raise ValueError(f"colour must be (r, g, b[, a]) 0-255, not {colour}")
        self._overrides[_short(name)] = _rgba(tuple(int(c) for c in colour))  # type: ignore
        self._cache.clear()

    def colour(self, name: str) -> RGBA:
        """
        The colour of a block

        :param name: the block name, e.g. "minecraft:red_wool"; any block
            states, e.g. "[facing=north]", are ignored
        :returns: (r, g, b, a) with values 0-255. a is 0 for blocks that are
            not drawn, 255 for solid blocks
        """
        short = _short(name)
        if short not in self._cache:
            self._cache[short] = self._lookup(short)
        return self._cache[short]

    def _lookup(self, name: str) -> RGBA:
        if name in self._overrides:
            return self._overrides[name]
        if name in INVISIBLE:
            return (0, 0, 0, 0)
        colour = self._base(name)
        if colour is None:
            colour = _hashed(name)
        if len(colour) == 3 and _is_thin(name):
            colour = (*colour, THIN_ALPHA)
        return _rgba(colour)

    def _base(self, name: str) -> RGB | RGBA | None:
        if name in self._overrides:
            return self._overrides[name]
        if name in BLOCK_COLOURS:
            return BLOCK_COLOURS[name]
        if name.startswith("waxed_"):
            return self._base(name.removeprefix("waxed_"))
        for shape in SHAPES:
            if name.endswith(shape):
                base = name.removesuffix(shape)
                colour = self._block_named(base)
                if colour is not None:
                    return colour
        for rule in (_dyed, _wood, _ore, _copper):
            colour = rule(name)
            if colour is not None:
                return colour
        for keyword, colour in KEYWORDS:
            if keyword in name:
                return colour
        return None

    def _block_named(self, base: str) -> RGB | RGBA | None:
        """the colour of the full block for *base*, e.g. stone_brick -> bricks"""
        if not base:
            return None
        if base in WOODS and base not in self._overrides:
            # e.g. bamboo_stairs are made of bamboo planks, not bamboo
            return WOODS[base].planks
        for candidate in (base, base + "s", base + "_block", base + "_planks"):
            if candidate in self._overrides or candidate in BLOCK_COLOURS:
                return self._base(candidate)
        return self._base(base)


def _copper(name: str) -> RGB | None:
    """weathered copper of all shapes, e.g. oxidized_cut_copper"""
    if "copper" not in name:
        return None
    for age in COPPER_AGES:
        if name.startswith(age):
            return BLOCK_COLOURS[age + "copper"][:3]  # type: ignore
    return None


def _short(name: str) -> str:
    """the block name without namespace or block states"""
    name = str(name).split("[", 1)[0].split("{", 1)[0].strip()
    return name.removeprefix("minecraft:")


def _is_thin(name: str) -> bool:
    """
    True for small blocks such as torches or fences. The curated table gives
    its blocks' alpha explicitly
    """
    if name in BLOCK_COLOURS or name.endswith("_block"):
        return False
    return any(keyword in name for keyword in THIN)


default_palette = Palette()


def set_colour(name: str, colour: RGB | RGBA) -> None:
    """
    Set the colour of a block in the default palette, used by every render
    that is not given a palette of its own

    :param name: the block name, e.g. "minecraft:stone" or "stone"
    :param colour: (r, g, b) or (r, g, b, a), values 0-255
    """
    default_palette.set(name, colour)
