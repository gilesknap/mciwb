"""
System tests for mciwb.builders: build each primitive on the test server, then
read it back (with block states) to check that the server ended up with
exactly the blocks and states that the builder sent. The server recalculates
the shape of stairs from their neighbours, so this checks that the builders
work out the same stair shapes as Minecraft.
"""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from mcwb import Item, Vec3, Volume

from mciwb.builders import (
    BlockState,
    Heightmap,
    Placer,
    Schematic,
    arch,
    column,
    flat_roof,
    foundation,
    gable_roof,
    ground_height,
    hip_roof,
    road,
    stairway,
)
from mciwb.threads import get_client, set_client
from tests.mockclient import MockClient
from tests.test_system.helpers import is_block

# a corner of the forceloaded test area away from the other system tests
LO = Vec3(-46, -60, -46)
HI = Vec3(-6, -40, -6)
GROUND = -61  # the top (grass) block of the flat test world


@pytest.fixture(autouse=True)
def clear_area() -> Iterator[None]:
    """Clear the building area before and after each test"""

    def clear():
        placer = Placer()
        placer.fill(LO, HI, Item.AIR)
        # restore the grass, in case a test changed the ground
        placer.fill(
            Vec3(LO.x, GROUND, LO.z), Vec3(HI.x, GROUND, HI.z), Item.GRASS_BLOCK
        )

    clear()
    yield
    clear()


def expected_blocks(build: Callable[[], Volume], volume: Volume) -> np.ndarray:
    """
    The block states that *build* sends, recorded by building in a MockClient
    world, over the given volume
    """
    real = get_client()
    mock = MockClient("expected", 0)
    set_client(mock)  # type: ignore
    try:
        assert build().size == volume.size
        blocks = np.empty(volume.size.i_tuple, dtype=object)
        for idx in np.ndindex(blocks.shape):
            blocks[idx] = BlockState.parse(mock.state_at(volume.start + Vec3(*idx)))
        return blocks
    finally:
        MockClient.reset()
        set_client(real)


def check_build(build: Callable[[], Volume]) -> Volume:
    """
    Build in the real world, read the blocks back and compare them with what
    the builder sent
    """
    volume = build()
    actual = Schematic.from_world(volume).blocks
    expected = expected_blocks(build, volume)

    def same(actual: Any, sent: Any) -> bool:
        # the server has every state sent, and its defaults for the others
        # e.g. a slab sent with no type is a bottom slab
        return actual.name == sent.name and all(
            actual.props.get(key) == value for key, value in sent.props.items()
        )

    differences = [
        f"{volume.start + Vec3(*idx)}: {actual[idx]} != {expected[idx]}"
        for idx in np.ndindex(actual.shape)
        if not same(actual[idx], expected[idx])
    ]
    assert not differences, "\n".join(differences)
    return volume


def test_gable_roof():
    volume = check_build(
        lambda: gable_roof(
            Vec3(-40, -61, -40), Vec3(-34, -61, -36), gable=Item.OAK_PLANKS
        )
    )
    assert (volume.start, volume.end) == (Vec3(-40, -60, -40), Vec3(-34, -58, -36))
    assert is_block(Vec3(-37, -60, -40), "minecraft:oak_stairs[facing=south]")
    assert is_block(Vec3(-37, -58, -38), "minecraft:oak_slab[type=bottom]")


def test_gable_roof_overhang():
    check_build(
        lambda: gable_roof(
            Vec3(-40, -60, -40),
            Vec3(-37, -60, -32),
            Item.SPRUCE_STAIRS,
            gable=Item.SPRUCE_PLANKS,
            overhang=1,
        )
    )


def test_hip_roof():
    volume = check_build(
        lambda: hip_roof(Vec3(-40, -61, -40), Vec3(-31, -61, -34), Item.BRICK_STAIRS)
    )
    # the server made the outer corners that the builder sent
    assert is_block(
        Vec3(-40, -60, -40), "minecraft:brick_stairs[facing=south,shape=outer_left]"
    )
    assert is_block(
        volume.end - Vec3(0, volume.size.y - 1, 0),
        "minecraft:brick_stairs[facing=north,shape=outer_left]",
    )


def test_flat_roof():
    check_build(
        lambda: flat_roof(
            Vec3(-40, -61, -40),
            Vec3(-35, -61, -35),
            Item.SMOOTH_STONE_SLAB,
            parapet=Item.STONE_BRICKS,
            parapet_height=2,
        )
    )


def test_flat_roof_wall_parapet():
    # walls join up by themselves: the server sets their connections
    flat_roof(Vec3(-40, -61, -40), Vec3(-35, -61, -35), parapet=Item.STONE_BRICK_WALL)
    assert is_block(
        Vec3(-38, -59, -40), "minecraft:stone_brick_wall[east=low,west=low]"
    )


def test_arches():
    check_build(lambda: arch(Vec3(-40, -60, -40), Vec3(-30, -60, -40)))
    check_build(
        lambda: arch(
            Vec3(-40, -60, -30),
            Vec3(-40, -60, -18),
            Item.DEEPSLATE_BRICKS,
            style="pointed",
            thickness=2,
            depth=3,
        )
    )


def test_arch_clears_opening():
    Placer().fill(Vec3(-40, -60, -40), Vec3(-30, -50, -40), Item.BRICKS)
    arch(Vec3(-38, -60, -40), Vec3(-32, -60, -40), clear=True)
    assert is_block(Vec3(-35, -60, -40), Item.AIR)
    assert is_block(Vec3(-35, -57, -40), Item.STONE_BRICKS)
    assert is_block(Vec3(-35, -56, -40), Item.BRICKS)


def test_column():
    check_build(
        lambda: column(
            Vec3(-30, -60, -30),
            8,
            width=3,
            plinth=Item.STONE_BRICKS,
            capital=Item.SMOOTH_STONE_SLAB,
        )
    )


def test_stairway():
    volume = check_build(
        lambda: stairway(
            [Vec3(-40, -60, -40), Vec3(-34, -56, -40), Vec3(-34, -54, -34)],
            Item.STONE_BRICK_STAIRS,
            width=3,
            support=Item.COBBLESTONE,
            clearance=2,
        )
    )
    assert volume.start.y == -60
    assert is_block(Vec3(-39, -59, -40), "minecraft:stone_brick_stairs[facing=east]")


def test_stairway_descending():
    check_build(
        lambda: stairway(
            [Vec3(-20, -52, -40), Vec3(-20, -60, -30), Vec3(-12, -60, -30)],
            Item.OAK_STAIRS,
        )
    )


def test_ground_height():
    pos = Vec3(-20, GROUND, -20)
    assert ground_height(pos.x, pos.z) == GROUND
    # a flower is ground for world_surface, but not for the others
    get_client().setblock(pos + Vec3(0, 1, 0), str(Item.POPPY))
    assert ground_height(pos.x, pos.z, Heightmap.WORLD_SURFACE) == GROUND + 1
    assert ground_height(pos.x, pos.z) == GROUND
    get_client().setblock(pos + Vec3(0, 5, 0), str(Item.STONE))
    assert ground_height(pos.x, pos.z, Heightmap.OCEAN_FLOOR) == GROUND + 5


def test_foundation():
    # a mound of dirt under part of the footprint
    Placer().fill(Vec3(-40, -60, -40), Vec3(-38, -58, -38), Item.DIRT)
    volume = foundation(Vec3(-40, -56, -40), Vec3(-35, -56, -35), Item.COBBLESTONE)
    assert (volume.start, volume.end) == (Vec3(-40, -60, -40), Vec3(-35, -56, -35))
    for y in range(-57, -55):
        assert is_block(Vec3(-39, y, -39), Item.COBBLESTONE)
    assert is_block(Vec3(-39, -58, -39), Item.DIRT)
    for y in range(-60, -55):
        assert is_block(Vec3(-36, y, -36), Item.COBBLESTONE)
    assert is_block(Vec3(-36, -55, -36), Item.AIR)


def test_road():
    # a step up in the ground east of x = -30
    Placer().fill(Vec3(-30, -60, -46), Vec3(-6, -60, -6), Item.GRASS_BLOCK)
    get_client().setblock(Vec3(-35, -60, -40), str(Item.POPPY))
    volume = road(
        [Vec3(-40, 0, -40), Vec3(-25, 0, -40), Vec3(-25, 0, -30)],
        Item.GRAVEL,
        border=Item.COBBLESTONE,
    )
    assert volume.start.y == GROUND
    assert is_block(Vec3(-35, GROUND, -40), Item.GRAVEL)
    assert is_block(Vec3(-35, GROUND + 1, -40), Item.AIR)  # the poppy is cleared
    assert is_block(Vec3(-35, GROUND, -41), Item.COBBLESTONE)
    assert is_block(Vec3(-28, GROUND + 1, -40), Item.GRAVEL)
    assert is_block(Vec3(-25, GROUND + 1, -32), Item.GRAVEL)
    assert is_block(Vec3(-24, GROUND + 1, -32), Item.COBBLESTONE)


def test_schematic_round_trip(tmp_path: Path):
    hip_roof(Vec3(-40, -61, -40), Vec3(-34, -61, -36), Item.OAK_STAIRS)
    Placer().setblock(Vec3(-40, -60, -36), "minecraft:oak_log[axis=x]")
    original = Volume.from_corners(Vec3(-40, -60, -40), Vec3(-34, -58, -36))
    file = tmp_path / "hip.schem"
    schematic = Schematic.from_world(original)
    schematic.save(file)

    loaded = Schematic.load(file)
    assert (loaded.blocks == schematic.blocks).all()
    for transformed in (loaded.rotate(1), loaded.mirror("x"), loaded.mirror("z")):
        volume = transformed.paste(Vec3(-25, -60, -25), air=True)
        copied = Schematic.from_world(volume)
        assert (copied.blocks == transformed.blocks).all()
