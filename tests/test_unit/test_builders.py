import pytest

from mciwb.builders import (
    BlockState,
    BuildError,
    Placer,
    arch,
    arch_profile,
    column,
    flat_roof,
    foundation,
    full_block_of,
    gable_roof,
    ground_height,
    ground_heights,
    hip_roof,
    road,
    slab_of,
    stair_shapes,
    stairway,
    trace_path,
)
from mciwb.builders.placer import rectangles
from mciwb.imports import Direction, Item, Vec3
from tests.mockclient import MockClient


def stairs(facing: str, shape: str = "straight", block: str = "oak_stairs") -> str:
    return f"minecraft:{block}[facing={facing},half=bottom,shape={shape}]"


# block states ################################################################


def test_block_state_parse_and_format():
    state = BlockState.parse("oak_stairs[facing=east, half=top]")
    assert state.name == "minecraft:oak_stairs"
    assert state.props == {"facing": "east", "half": "top"}
    assert str(state) == "minecraft:oak_stairs[facing=east,half=top]"
    assert state.item is Item.OAK_STAIRS
    assert BlockState.parse(Item.STONE) == BlockState("minecraft:stone")
    assert str(BlockState.of(Item.LEVER, facing=Direction.WEST)) == (
        "minecraft:lever[facing=west]"
    )
    # equal states hash the same, whatever the order of their properties
    other = BlockState.parse("minecraft:oak_stairs[half=top,facing=east]")
    assert other == state
    assert len({state, other}) == 1
    assert BlockState.parse("cave_air").is_air
    with pytest.raises(ValueError):
        BlockState.parse("oak_stairs[facing=east")
    with pytest.raises(ValueError):
        BlockState.parse("oak_stairs[facing]")


def test_block_state_rotate():
    state = BlockState.of(Item.OAK_STAIRS, facing="north", shape="outer_left")
    assert state.rotate(1).props == {"facing": "east", "shape": "outer_left"}
    assert state.rotate(2).props["facing"] == "south"
    assert state.rotate(-1).props["facing"] == "west"
    assert state.rotate(4) == state
    assert BlockState.of("oak_log", axis="x").rotate(1).props == {"axis": "z"}
    assert BlockState.of("oak_log", axis="y").rotate(1).props == {"axis": "y"}
    assert BlockState.of("oak_sign", rotation="15").rotate(1).props == {"rotation": "3"}
    fence = BlockState.of("oak_fence", north="true", east="false")
    assert fence.rotate(1).props == {"east": "true", "south": "false"}
    assert BlockState.of("rail", shape="north_east").rotate(1).props == {
        "shape": "south_east"
    }
    assert BlockState.of("rail", shape="north_south").rotate(1).props == {
        "shape": "east_west"
    }
    assert BlockState.of("rail", shape="ascending_north").rotate(1).props == {
        "shape": "ascending_east"
    }


def test_block_state_mirror():
    state = BlockState.of(Item.OAK_STAIRS, facing="east", shape="outer_left")
    assert state.mirror("x").props == {"facing": "west", "shape": "outer_right"}
    assert state.mirror("z").props == {"facing": "east", "shape": "outer_right"}
    door = BlockState.of("oak_door", facing="north", hinge="left")
    assert door.mirror("z").props == {"facing": "south", "hinge": "right"}
    assert BlockState.of("oak_sign", rotation="4").mirror("x").props == {
        "rotation": "12"
    }
    assert BlockState.of("oak_sign", rotation="0").mirror("z").props == {
        "rotation": "8"
    }
    with pytest.raises(ValueError):
        state.mirror("y")


def test_stair_shapes():
    # an outer corner: the north row faces south, the west column faces east
    shapes = stair_shapes({(0, 0): "south", (1, 0): "south", (0, 1): "east"})
    assert shapes == {(0, 0): "outer_left", (1, 0): "straight", (0, 1): "straight"}
    shapes = stair_shapes({(0, 0): "south", (-1, 0): "south", (0, 1): "west"})
    assert shapes[(0, 0)] == "outer_right"
    # an inner corner: the stairs behind face across
    shapes = stair_shapes({(0, 0): "south", (0, -1): "east"})
    assert shapes[(0, 0)] == "inner_left"
    shapes = stair_shapes({(0, 0): "south", (0, -1): "west"})
    assert shapes[(0, 0)] == "inner_right"


def test_materials():
    assert slab_of(Item.OAK_STAIRS) is Item.OAK_SLAB
    assert full_block_of(Item.OAK_STAIRS) is Item.OAK_PLANKS
    assert full_block_of(Item.STONE_BRICK_STAIRS) is Item.STONE_BRICKS
    assert full_block_of(Item.QUARTZ_STAIRS) is Item.QUARTZ_BLOCK
    assert full_block_of(Item.STONE_STAIRS) is Item.STONE
    with pytest.raises(ValueError):
        slab_of(Item.STONE)


# placing #####################################################################


def test_rectangles():
    assert rectangles([]) == []
    square = [(x, z) for x in range(3) for z in range(2)]
    assert rectangles(square) == [(0, 0, 2, 1)]
    # an L shape needs two rectangles
    assert len(rectangles([(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)])) == 2
    # a column is one rectangle, whichever axis it runs along
    assert rectangles([(0, z) for z in range(5)]) == [(0, 0, 0, 4)]


def test_placer_errors_and_volume(
    mock_client: MockClient, monkeypatch: pytest.MonkeyPatch
):
    placer = Placer()
    with pytest.raises(ValueError):
        placer.volume  # noqa: B018 - nothing placed yet
    placer.setblock(Vec3(1, 2, 3), Item.STONE)
    placer.fill(Vec3(0, 0, 0), Vec3(-1, 1, 1), "oak_slab[type=top]")
    assert placer.volume.start == Vec3(-1, 0, 0)
    assert placer.volume.end == Vec3(1, 2, 3)
    assert mock_client.state_at(Vec3(-1, 1, 1)) == "minecraft:oak_slab[type=top]"

    monkeypatch.setattr(
        mock_client, "setblock", lambda *_: "Unknown block type 'minecraft:nope'"
    )
    with pytest.raises(BuildError, match="Unknown block"):
        Placer().setblock(Vec3(0, 0, 0), "nope")


def test_placer_splits_large_fills(mock_client: MockClient):
    Placer().fill(Vec3(0, 0, 0), Vec3(39, 39, 39), Item.STONE)
    fills = mock_client.block_commands
    assert len(fills) == 2
    assert fills[0] == "fill 0 0 0 19 39 39 minecraft:stone"
    assert fills[1] == "fill 20 0 0 39 39 39 minecraft:stone"


# roofs #######################################################################


def test_gable_roof(mock_client: MockClient):
    volume = gable_roof(Vec3(0, 0, 0), Vec3(6, 0, 4), gable=Item.OAK_PLANKS)
    # the ridge runs along the longer side, x
    assert (volume.start, volume.end) == (Vec3(0, 1, 0), Vec3(6, 3, 4))
    assert mock_client.block_commands == [
        f"fill 0 1 0 6 1 0 {stairs('south')}",
        f"fill 0 1 4 6 1 4 {stairs('north')}",
        "fill 0 1 1 0 1 3 minecraft:oak_planks",
        "fill 6 1 1 6 1 3 minecraft:oak_planks",
        f"fill 0 2 1 6 2 1 {stairs('south')}",
        f"fill 0 2 3 6 2 3 {stairs('north')}",
        "fill 0 2 2 0 2 2 minecraft:oak_planks",
        "fill 6 2 2 6 2 2 minecraft:oak_planks",
        "fill 0 3 2 6 3 2 minecraft:oak_slab[type=bottom]",
    ]


def test_gable_roof_along_z_with_overhang(mock_client: MockClient):
    volume = gable_roof(
        Vec3(0, 0, 0),
        Vec3(3, 0, 8),
        Item.SPRUCE_STAIRS,
        ridge=Item.SPRUCE_PLANKS,
        overhang=1,
    )
    # 6 blocks across x: 3 courses of stairs that meet, no ridge needed
    assert (volume.start, volume.end) == (Vec3(-1, 1, -1), Vec3(4, 3, 9))
    for course in range(3):
        y = 1 + course
        for z in range(-1, 10):
            east = mock_client.state_at(Vec3(-1 + course, y, z))
            west = mock_client.state_at(Vec3(4 - course, y, z))
            assert east == stairs("east", block="spruce_stairs")
            assert west == stairs("west", block="spruce_stairs")
    assert Item.SPRUCE_PLANKS not in mock_client.world


def test_hip_roof(mock_client: MockClient):
    volume = hip_roof(Vec3(0, 0, 0), Vec3(4, 0, 3), Item.OAK_STAIRS)
    assert (volume.start, volume.end) == (Vec3(0, 1, 0), Vec3(4, 2, 3))

    state = mock_client.state_at
    # outer corners on the bottom course
    assert state(Vec3(0, 1, 0)) == stairs("south", "outer_left")
    assert state(Vec3(4, 1, 0)) == stairs("south", "outer_right")
    assert state(Vec3(0, 1, 3)) == stairs("north", "outer_right")
    assert state(Vec3(4, 1, 3)) == stairs("north", "outer_left")
    # sides
    assert state(Vec3(2, 1, 0)) == stairs("south")
    assert state(Vec3(2, 1, 3)) == stairs("north")
    assert state(Vec3(0, 1, 1)) == stairs("east")
    assert state(Vec3(4, 1, 2)) == stairs("west")
    # the second course is 3 by 2: a row facing south and one facing north
    assert state(Vec3(1, 2, 1)) == stairs("south")
    assert state(Vec3(3, 2, 2)) == stairs("north")
    assert state(Vec3(2, 2, 1)) == stairs("south")
    # the middle of each course is open
    assert state(Vec3(2, 1, 1)) == "minecraft:air"
    assert state(Vec3(2, 3, 1)) == "minecraft:air"


def test_hip_roof_ridge(mock_client: MockClient):
    hip_roof(Vec3(0, 0, 0), Vec3(4, 0, 2), Item.OAK_STAIRS, overhang=0)
    # 5 by 3: one ring, then a ridge of slabs 3 long
    for x in range(1, 4):
        assert mock_client.state_at(Vec3(x, 2, 1)) == "minecraft:oak_slab[type=bottom]"
    assert mock_client.block_commands[-1] == (
        "fill 1 2 1 3 2 1 minecraft:oak_slab[type=bottom]"
    )


def test_flat_roof(mock_client: MockClient):
    volume = flat_roof(
        Vec3(0, 0, 0),
        Vec3(3, 0, 3),
        Item.SMOOTH_STONE_SLAB,
        parapet=Item.STONE_BRICKS,
        parapet_height=2,
    )
    assert (volume.start, volume.end) == (Vec3(0, 1, 0), Vec3(3, 3, 3))
    assert mock_client.getblock(Vec3(1, 1, 1)) == Item.SMOOTH_STONE_SLAB
    for y in (2, 3):
        assert mock_client.getblock(Vec3(0, y, 2)) == Item.STONE_BRICKS
        assert mock_client.getblock(Vec3(3, y, 3)) == Item.STONE_BRICKS
        assert mock_client.getblock(Vec3(1, y, 1)) == Item.AIR
    assert mock_client.getblock(Vec3(0, 4, 0)) == Item.AIR


def test_roof_errors(mock_client: MockClient):
    with pytest.raises(ValueError):
        gable_roof(Vec3(0, 0, 0), Vec3(3, 0, 3), axis="y")
    with pytest.raises(ValueError):
        hip_roof(Vec3(0, 0, 0), Vec3(3, 0, 3), overhang=-1)


# arches and columns ##########################################################


def render(cells: set[tuple[int, int]], other: set[tuple[int, int]]) -> list[str]:
    top = max(v for _, v in cells)
    span = max(u for u, _ in cells) + 1
    return [
        "".join(
            "#" if (u, v) in cells else "." if (u, v) in other else " "
            for u in range(span)
        )
        for v in range(top, -1, -1)
    ]


def test_arch_profiles():
    ring, opening = arch_profile(7)
    assert render(ring, opening) == [
        "  ###  ",
        "###.###",
        "#.....#",
        "#.....#",
    ]
    ring, opening = arch_profile(11, style="pointed")
    assert render(ring, opening) == [
        "    ###    ",
        "   ##.##   ",
        "  ##...##  ",
        " ##.....## ",
        " #.......# ",
        "##.......##",
        "#.........#",
        "#.........#",
        "#.........#",
    ]
    ring, opening = arch_profile(9, thickness=2)
    assert render(ring, opening) == [
        "  #####  ",
        "#########",
        "####.####",
        "##.....##",
        "##.....##",
    ]
    with pytest.raises(ValueError):
        arch_profile(2)
    with pytest.raises(ValueError):
        arch_profile(7, style="ogee")
    with pytest.raises(ValueError):
        arch_profile(7, thickness=0)


def test_arch(mock_client: MockClient):
    mock_client.fill(Vec3(0, 0, 0), Vec3(6, 5, 0), Item.BRICKS)
    volume = arch(Vec3(6, 0, 0), Vec3(0, 0, 0), Item.STONE_BRICKS, clear=True)
    assert (volume.start, volume.end) == (Vec3(0, 0, 0), Vec3(6, 3, 0))
    get = mock_client.getblock
    assert get(Vec3(0, 0, 0)) == Item.STONE_BRICKS
    assert get(Vec3(3, 3, 0)) == Item.STONE_BRICKS
    assert get(Vec3(3, 2, 0)) == Item.AIR  # the opening is cleared
    assert get(Vec3(1, 0, 0)) == Item.AIR
    assert get(Vec3(0, 3, 0)) == Item.BRICKS  # the wall around is untouched
    assert get(Vec3(0, 4, 0)) == Item.BRICKS


def test_arch_along_z_with_depth(mock_client: MockClient):
    volume = arch(Vec3(0, 0, 0), Vec3(0, 0, 4), depth=2, style="pointed")
    # the depth goes east, for an arch along z
    assert (volume.start, volume.end) == (Vec3(0, 0, 0), Vec3(1, 3, 4))
    for x in (0, 1):
        assert mock_client.getblock(Vec3(x, 0, 0)) == Item.STONE_BRICKS
        assert mock_client.getblock(Vec3(x, 0, 2)) == Item.AIR
    with pytest.raises(ValueError):
        arch(Vec3(0, 0, 0), Vec3(4, 0, 4))
    with pytest.raises(ValueError):
        arch(Vec3(0, 0, 0), Vec3(4, 1, 0))
    with pytest.raises(ValueError):
        arch(Vec3(0, 0, 0), Vec3(0, 0, 0))
    with pytest.raises(ValueError):
        arch(Vec3(0, 0, 0), Vec3(4, 0, 0), depth=0)


def test_column(mock_client: MockClient):
    volume = column(
        Vec3(5, 0, 5),
        6,
        Item.QUARTZ_PILLAR,
        width=3,
        plinth=Item.STONE_BRICKS,
        capital=Item.SMOOTH_STONE_SLAB,
    )
    assert (volume.start, volume.end) == (Vec3(3, 0, 3), Vec3(7, 5, 7))
    assert mock_client.block_commands == [
        "fill 3 0 3 7 0 7 minecraft:stone_bricks",
        "fill 3 5 3 7 5 7 minecraft:smooth_stone_slab",
        "fill 4 1 4 6 4 6 minecraft:quartz_pillar",
    ]
    volume = column(Vec3(0, 0, 0), 3)
    assert (volume.start, volume.end) == (Vec3(0, 0, 0), Vec3(0, 2, 0))
    with pytest.raises(ValueError):
        column(Vec3(0, 0, 0), 2, plinth=Item.STONE, capital=Item.STONE)
    with pytest.raises(ValueError):
        column(Vec3(0, 0, 0), 2, width=0)


# paths #######################################################################


def test_trace_path():
    steps = trace_path([Vec3(0, 0, 0), Vec3(4, 2, 0), Vec3(4, 0, 4)])
    heights = [(int(s.pos.x), int(s.pos.y), int(s.pos.z)) for s in steps]
    assert heights == [
        (0, 0, 0),
        (1, 1, 0),  # climbs start at once
        (2, 1, 0),
        (3, 2, 0),
        (4, 2, 0),  # a level corner
        (4, 2, 1),
        (4, 1, 2),
        (4, 1, 3),
        (4, 0, 4),  # descents finish at the end
    ]
    assert steps[0].direction == Direction.EAST
    assert steps[-1].direction == Direction.SOUTH
    with pytest.raises(ValueError, match="diagonal"):
        trace_path([Vec3(0, 0, 0), Vec3(2, 0, 2)])
    with pytest.raises(ValueError, match="climbs"):
        trace_path([Vec3(0, 0, 0), Vec3(2, 3, 0)])
    with pytest.raises(ValueError, match="vertical"):
        trace_path([Vec3(0, 0, 0), Vec3(0, 3, 0)])
    with pytest.raises(ValueError):
        trace_path([Vec3(0, 0, 0)])
    with pytest.raises(ValueError):
        trace_path([Vec3(0, 0, 0), Vec3(0, 0, 0)])


def test_stairway(mock_client: MockClient):
    volume = stairway(
        [Vec3(0, 0, 0), Vec3(4, 2, 0), Vec3(4, 0, 4)], Item.STONE_BRICK_STAIRS
    )
    assert (volume.start, volume.end) == (Vec3(0, 0, 0), Vec3(4, 2, 4))
    state = mock_client.state_at
    landing = "minecraft:stone_bricks"
    up = "stone_brick_stairs"
    assert state(Vec3(0, 0, 0)) == landing
    assert state(Vec3(1, 1, 0)) == stairs("east", block=up)
    assert state(Vec3(2, 1, 0)) == landing
    assert state(Vec3(3, 2, 0)) == stairs("east", block=up)
    assert state(Vec3(4, 2, 0)) == landing
    # going down to the south, the stairs face back north, up the steps
    assert state(Vec3(4, 2, 1)) == stairs("north", block=up)
    assert state(Vec3(4, 1, 2)) == landing
    assert state(Vec3(4, 1, 3)) == stairs("north", block=up)
    assert state(Vec3(4, 0, 4)) == landing


def test_wide_stairway_with_support(mock_client: MockClient):
    mock_client.fill(Vec3(0, 3, 0), Vec3(9, 5, 9), Item.DIRT)
    stairway(
        [Vec3(2, 0, 1), Vec3(2, 2, 3), Vec3(5, 2, 3)],
        Item.OAK_STAIRS,
        landing=Item.OAK_PLANKS,
        width=3,
        support=Item.COBBLESTONE,
        clearance=2,
    )
    state = mock_client.state_at
    # 3 wide, south from x = 1 to 3
    for x in (1, 2, 3):
        assert state(Vec3(x, 1, 2)) == stairs("south")
        assert state(Vec3(x, 0, 2)) == "minecraft:cobblestone"
        assert state(Vec3(x, 3, 2)) == "minecraft:air"  # clearance
    # the corner step climbs too: its row, and the gap outside the corner,
    # are stairs. The row before the corner keeps its place inside it
    assert state(Vec3(1, 2, 3)) == stairs("south")
    assert state(Vec3(1, 2, 4)) == stairs("south")
    assert state(Vec3(3, 1, 2)) == stairs("south")
    # then a level path east
    for x in (4, 5):
        for z in (2, 3, 4):
            assert state(Vec3(x, 2, z)) == "minecraft:oak_planks"
            assert state(Vec3(x, 1, z)) == "minecraft:cobblestone"
            assert state(Vec3(x, 4, z)) == "minecraft:air"
        assert state(Vec3(x, 5, 3)) == "minecraft:dirt"


def test_road(mock_client: MockClient):
    # a step in the ground at x >= 5
    mock_client.fill(Vec3(0, -10, 0), Vec3(9, 0, 9), Item.GRASS_BLOCK)
    mock_client.fill(Vec3(5, 1, 0), Vec3(9, 1, 9), Item.GRASS_BLOCK)
    volume = road(
        [Vec3(1, 99, 1), Vec3(8, 99, 1)], Item.GRAVEL, width=3, border=Item.STONE
    )
    assert (volume.start, volume.end) == (Vec3(1, 0, 0), Vec3(8, 3, 2))
    get = mock_client.getblock
    assert get(Vec3(2, 0, 1)) == Item.GRAVEL
    assert get(Vec3(2, 0, 0)) == Item.STONE
    assert get(Vec3(2, 0, 2)) == Item.STONE
    assert get(Vec3(1, 0, 1)) == Item.GRAVEL  # no border across the ends
    assert get(Vec3(7, 1, 1)) == Item.GRAVEL
    assert get(Vec3(7, 1, 2)) == Item.STONE
    # clear 2 blocks above the road
    assert "fill 1 1 0 4 2 2 minecraft:air" in mock_client.block_commands
    # the markers used to read the ground are removed
    assert mock_client.markers == {}


# terrain #####################################################################


def test_ground_height(mock_client: MockClient):
    mock_client.fill(Vec3(0, -20, 0), Vec3(9, 3, 9), Item.STONE)
    mock_client.setblock(Vec3(4, 7, 4), Item.STONE)
    assert ground_height(1, 1) == 3
    assert ground_heights([(1, 1), (4, 4)], "ocean_floor") == {(1, 1): 3, (4, 4): 7}
    assert ground_heights([]) == {}
    commands = mock_client.commands
    assert commands[-1].startswith("kill @e[type=minecraft:marker,tag=mciwb_")
    assert "positioned over ocean_floor run tp" in commands[-2]
    assert mock_client.markers == {}


def test_ground_height_errors(mock_client: MockClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mock_client, "run", lambda _: "That position is not loaded")
    with pytest.raises(BuildError, match="summon"):
        ground_height(1000, 1000)

    real_run = MockClient.run

    def unloaded(command: str) -> str:
        if command.startswith("execute"):
            return "That position is not loaded"
        return real_run(mock_client, command)

    monkeypatch.setattr(mock_client, "run", unloaded)
    with pytest.raises(BuildError, match="ground"):
        ground_height(0, 0)
    # the marker is removed even so
    assert mock_client.markers == {}


def test_foundation(mock_client: MockClient):
    # ground at y = 0, with a hump at x = 3 up to y = 4
    mock_client.fill(Vec3(0, -10, 0), Vec3(9, 0, 9), Item.DIRT)
    mock_client.fill(Vec3(3, 1, 0), Vec3(3, 4, 9), Item.DIRT)
    volume = foundation(Vec3(1, 3, 1), Vec3(4, 3, 2), Item.COBBLESTONE)
    assert (volume.start, volume.end) == (Vec3(1, 1, 1), Vec3(4, 3, 2))
    get = mock_client.getblock
    for z in (1, 2):
        for y in (1, 2, 3):
            assert get(Vec3(1, y, z)) == Item.COBBLESTONE
            assert get(Vec3(4, y, z)) == Item.COBBLESTONE
        # the hump is above the top: it just gets the top layer
        assert get(Vec3(3, 3, z)) == Item.COBBLESTONE
        assert get(Vec3(3, 2, z)) == Item.DIRT
        assert get(Vec3(3, 4, z)) == Item.DIRT
    assert get(Vec3(0, 1, 1)) == Item.AIR


def test_foundation_max_depth(mock_client: MockClient):
    volume = foundation(Vec3(0, 10, 0), Vec3(1, 10, 1), max_depth=3)
    assert (volume.start, volume.end) == (Vec3(0, 8, 0), Vec3(1, 10, 1))
    assert mock_client.block_commands == ["fill 0 8 0 1 10 1 minecraft:cobblestone"]
