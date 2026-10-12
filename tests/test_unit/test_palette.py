import pytest

from mciwb.imports import Item
from mciwb.palette import (
    BLOCK_COLOURS,
    DYE_COLOURS,
    GLASS_ALPHA,
    TERRACOTTA_COLOURS,
    THIN_ALPHA,
    WOODS,
    Palette,
    default_palette,
    set_colour,
)

palette = Palette()


def rgb(name: str) -> tuple[int, ...]:
    return palette.colour(name)[:3]


def test_curated():
    assert palette.colour("minecraft:gold_block") == (246, 208, 61, 255)
    # names without a namespace, with block states, and Items all work
    assert palette.colour("gold_block") == (246, 208, 61, 255)
    assert palette.colour("minecraft:gold_block[x=1]") == (246, 208, 61, 255)
    assert palette.colour(Item.GOLD_BLOCK) == (246, 208, 61, 255)
    assert palette.colour("water")[3] < 255


def test_invisible():
    for name in ("air", "cave_air", "void_air", "barrier", "light"):
        assert palette.colour(name)[3] == 0


def test_dyed():
    assert rgb("red_wool") == DYE_COLOURS["red"]
    assert rgb("light_blue_wool") == DYE_COLOURS["light_blue"]
    assert rgb("blue_wool") == DYE_COLOURS["blue"]
    assert rgb("light_gray_terracotta") == TERRACOTTA_COLOURS["light_gray"]
    # concrete is a little darker than wool, powder lighter
    assert sum(rgb("red_concrete")) < sum(rgb("red_wool"))
    assert sum(rgb("red_concrete_powder")) > sum(rgb("red_wool"))
    assert sum(rgb("red_glazed_terracotta")) > sum(rgb("red_wool"))
    # glass is see through, carpet is thin
    assert palette.colour("lime_stained_glass")[3] < 255
    assert palette.colour("lime_stained_glass_pane")[3] < 255
    assert palette.colour("pink_carpet") == (*DYE_COLOURS["pink"], THIN_ALPHA)
    assert palette.colour("pink_bed") == (*DYE_COLOURS["pink"], 255)
    assert palette.colour("purple_shulker_box") == (*DYE_COLOURS["purple"], 255)


def test_wood():
    for wood_name, wood in WOODS.items():
        assert rgb(f"{wood_name}_planks") == wood.planks
        assert rgb(f"{wood_name}_stairs") == wood.planks
        assert palette.colour(f"{wood_name}_fence")[3] == THIN_ALPHA
    assert rgb("dark_oak_log") == WOODS["dark_oak"].log
    assert rgb("oak_log") == WOODS["oak"].log
    assert rgb("oak_wood") == WOODS["oak"].log
    assert rgb("crimson_stem") == WOODS["crimson"].log
    assert rgb("cherry_leaves") == WOODS["cherry"].leaves
    assert rgb("stripped_birch_log") != WOODS["birch"].log
    assert rgb("bamboo_mosaic_slab") == WOODS["bamboo"].planks
    assert palette.colour("spruce_door")[3] == THIN_ALPHA
    assert palette.colour("spruce_trapdoor")[3] == THIN_ALPHA


def test_shapes():
    assert rgb("stone_brick_stairs") == BLOCK_COLOURS["stone_bricks"]
    assert rgb("brick_wall") == BLOCK_COLOURS["bricks"]
    assert rgb("quartz_slab") == BLOCK_COLOURS["quartz_block"]
    assert rgb("purpur_stairs") == BLOCK_COLOURS["purpur_block"]
    assert rgb("smooth_sandstone_slab") == BLOCK_COLOURS["smooth_sandstone"]
    assert rgb("deepslate_tile_wall") == BLOCK_COLOURS["deepslate_tiles"]
    assert rgb("red_nether_brick_fence") == BLOCK_COLOURS["red_nether_bricks"]
    assert (
        rgb("polished_blackstone_pressure_plate")
        == (BLOCK_COLOURS["polished_blackstone"])
    )


def test_copper():
    assert rgb("waxed_copper_block") == BLOCK_COLOURS["copper_block"]
    assert rgb("oxidized_cut_copper_stairs") == BLOCK_COLOURS["oxidized_copper"]
    assert rgb("waxed_weathered_copper") == BLOCK_COLOURS["weathered_copper"]
    assert rgb("cut_copper") == BLOCK_COLOURS["copper_block"]


def test_ores_and_keywords():
    # an ore is mostly the stone it is set in
    assert rgb("iron_ore") != rgb("stone")
    assert abs(sum(rgb("diamond_ore")) - sum(rgb("stone"))) < 150
    assert rgb("deepslate_gold_ore") != rgb("gold_ore")
    assert palette.colour("tube_coral_block")[2] > 150
    assert palette.colour("dead_brain_coral_fan")[3] == THIN_ALPHA
    assert palette.colour("glass")[3] == GLASS_ALPHA
    assert palette.colour("torch")[3] == THIN_ALPHA
    assert palette.colour("poppy")[3] == THIN_ALPHA
    assert palette.colour("mushroom_stem")[3] == 255
    assert palette.colour("jack_o_lantern")[3] == 255


def test_every_item_has_a_colour():
    for item in Item:
        colour = palette.colour(item)
        assert len(colour) == 4
        assert all(0 <= c <= 255 for c in colour)


def test_unknown_blocks():
    # unknown blocks get a stable colour from their name
    assert palette.colour("mymod:widget") == Palette().colour("mymod:widget")
    assert palette.colour("mymod:widget") != palette.colour("mymod:gadget")
    assert palette.colour("mymod:widget")[3] == 255


def test_overrides():
    custom = Palette({"mymod:widget": (1, 2, 3), "stone": (4, 5, 6, 7)})
    assert custom.colour("mymod:widget") == (1, 2, 3, 255)
    assert custom.colour("minecraft:stone") == (4, 5, 6, 7)
    # shapes of an overridden block follow it
    assert custom.colour("stone_stairs")[:3] == (4, 5, 6)
    custom.set("minecraft:stone", (9, 9, 9))
    assert custom.colour("stone") == (9, 9, 9, 255)
    assert palette.colour("stone") == (125, 125, 125, 255)

    with pytest.raises(ValueError, match="colour must be"):
        custom.set("stone", (1, 2))  # type: ignore
    with pytest.raises(ValueError, match="colour must be"):
        custom.set("stone", (1, 2, 300))


def test_set_colour():
    before = default_palette.colour("minecraft:dirt")
    try:
        set_colour("dirt", (10, 20, 30))
        assert default_palette.colour("minecraft:dirt") == (10, 20, 30, 255)
    finally:
        set_colour("dirt", before)
