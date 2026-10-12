from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from mciwb.blockgrid import BlockGrid, block_name, grab_blocks
from mciwb.imports import Item, Vec3, Volume
from mciwb.palette import BLOCK_COLOURS, GLASS_ALPHA, Palette
from mciwb.render import BACKGROUND, VIEWS, auto_scale, render, render_view, scan
from tests.anvil_writer import write_world
from tests.mockclient import MockClient

ORIGIN = Vec3(100, 60, -20)
GOLD = BLOCK_COLOURS["gold_block"]
STONE = BLOCK_COLOURS["stone"]
RED = (160, 39, 34)
SCALE = 4


def make_grid(size=(5, 4, 3), blocks=None) -> BlockGrid:
    """an empty grid of air with blocks keyed by local (x, y, z)"""
    array = np.full(size, "air", dtype=object)
    for pos, name in (blocks or {}).items():
        array[pos] = name
    return BlockGrid.from_blocks(array, ORIGIN)


def at(image: Image.Image, x: int, y: int) -> tuple[int, ...]:
    """the colour of a pixel"""
    colour = image.getpixel((x, y))
    assert isinstance(colour, tuple)
    return colour


def pixel(image: Image.Image, col: int, row: int, scale: int = SCALE):
    """the colour at the centre of the block at (col, row) of a view"""
    return at(image, col * scale + scale // 2, row * scale + scale // 2)


def test_block_grid():
    grid = make_grid(blocks={(0, 0, 0): Item.STONE, (4, 3, 2): "minecraft:gold_block"})
    assert grid.size == Vec3(5, 4, 3)
    assert grid.end == ORIGIN + Vec3(4, 3, 2)
    assert grid.volume.start == ORIGIN
    assert grid[ORIGIN] == "minecraft:stone"
    assert grid[ORIGIN + Vec3(4, 3, 2)] == "minecraft:gold_block"
    assert grid[ORIGIN + Vec3(1, 0, 0)] == "minecraft:air"
    assert grid.counts() == {"minecraft:stone": 1, "minecraft:gold_block": 1}
    assert grid.counts(include_air=True)["minecraft:air"] == 58
    assert grid.to_names()[4, 3, 2] == "minecraft:gold_block"
    with pytest.raises(IndexError):
        grid[ORIGIN + Vec3(5, 0, 0)]
    with pytest.raises(ValueError, match="3D"):
        BlockGrid.from_blocks([["stone"]], ORIGIN)
    with pytest.raises(ValueError, match="3 dimensional"):
        BlockGrid(ORIGIN, np.zeros((2, 2)), ["minecraft:air"])


def test_block_name():
    assert block_name(Item.STONE) == "minecraft:stone"
    assert block_name("stone") == "minecraft:stone"
    assert block_name("minecraft:oak_stairs[facing=east]") == "minecraft:oak_stairs"
    assert block_name("mymod:widget") == "mymod:widget"


def test_grab_blocks(mock_client: MockClient):
    mock_client.setblock(Vec3(1, 2, 3), Item.GOLD_BLOCK)
    grid = grab_blocks(mock_client, Volume.from_corners(Vec3(0, 2, 3), Vec3(2, 2, 3)))  # type: ignore
    assert grid.counts(include_air=True) == {
        "minecraft:air": 2,
        "minecraft:gold_block": 1,
    }
    assert grid[Vec3(1, 2, 3)] == "minecraft:gold_block"


def test_top_view():
    # a gold block on a stone floor, and a red block in the north west corner
    blocks = {(x, 0, z): "stone" for x in range(5) for z in range(3)}
    blocks[(0, 0, 0)] = "red_wool"
    blocks[(2, 2, 0)] = "gold_block"
    image = render_view(make_grid(blocks=blocks), "top", SCALE, labels=False)

    # x across, z down, one pixel square per block
    assert image.size == (5 * SCALE, 3 * SCALE)
    # the highest blocks are lit fully, the lowest are darker
    assert pixel(image, 2, 0) == GOLD
    stone = pixel(image, 4, 2)
    assert stone == tuple(round(c * 0.7) for c in STONE)
    red = pixel(image, 0, 0)
    assert red[0] > red[1] + 50
    # the stone south of the gold block is in its shadow, lower than its
    # northern neighbour
    assert pixel(image, 2, 1)[0] < stone[0]


def test_top_view_background_and_glass():
    blocks = {(0, 0, 0): "gold_block", (0, 3, 0): "glass", (1, 3, 0): "glass"}
    image = render_view(make_grid(blocks=blocks), "top", SCALE, labels=False)
    assert pixel(image, 4, 2) == BACKGROUND
    # gold seen through glass is a mix of the two
    seen = pixel(image, 0, 0)
    assert seen != GOLD
    assert seen[2] < 150 < seen[0]
    # glass over nothing is mostly background
    glass = pixel(image, 1, 0)
    alpha = GLASS_ALPHA / 255
    assert glass[0] == pytest.approx(BACKGROUND[0] * (1 - alpha) + 200 * alpha, abs=2)


@pytest.mark.parametrize(
    "view, size, gold_at",
    [
        # (columns, rows) and where the gold block at local (4, 3, 0) appears
        ("south", (5, 4), (4, 0)),  # x across, y up
        ("north", (5, 4), (0, 0)),  # looking south, east is on the left
        ("east", (3, 4), (2, 0)),  # looking west, north is on the right
        ("west", (3, 4), (0, 0)),  # looking east, north is on the left
        ("top", (5, 3), (4, 0)),
    ],
)
def test_elevations(view: str, size: tuple[int, int], gold_at: tuple[int, int]):
    grid = make_grid(blocks={(4, 3, 0): "gold_block", (0, 0, 2): "stone"})
    image = render_view(grid, view, SCALE, labels=False)
    assert image.size == (size[0] * SCALE, size[1] * SCALE)
    gold = pixel(image, *gold_at)
    assert gold[0] > 150 and gold[2] < 100, gold


def test_iso_single_block():
    grid = make_grid((1, 1, 1), {(0, 0, 0): "gold_block"})
    scale = 8
    image = render_view(grid, "iso", scale, labels=False)
    # (size x + size z) * scale across, half that plus size y * scale high
    assert image.size == (2 * scale + 1, scale + scale + 1)
    # the middle of the top face is lit fully, the sides are darker
    assert at(image, scale, scale // 2) == GOLD
    south = at(image, scale // 2, scale + scale // 4)
    east = at(image, scale + scale // 2, scale + scale // 4)
    assert sum(GOLD) > sum(south) > sum(east)
    assert at(image, 0, 0) == BACKGROUND


@pytest.mark.parametrize(
    "view, west_end_on_left", [("iso", True), ("iso_nw", False), ("iso_ne", False)]
)
def test_iso_turns(view: str, west_end_on_left: bool):
    """a row of blocks along x with gold at the west end"""
    blocks = {(x, 0, 0): "stone" for x in range(1, 6)}
    blocks[(0, 0, 0)] = "gold_block"
    image = render_view(make_grid((6, 1, 1), blocks), view, 8, labels=False)
    pixels = np.asarray(image)
    gold_columns = np.nonzero((pixels == GOLD).all(axis=2).any(axis=0))[0]
    assert gold_columns.size
    assert (gold_columns.mean() < image.width / 2) == west_end_on_left


def test_iso_glass_shows_what_is_behind():
    grid = make_grid((1, 1, 2), {(0, 0, 0): "gold_block", (0, 0, 1): "glass"})
    image = render_view(grid, "iso", 8, labels=False)
    # the gold block's top is drawn, the glass in front of it blends with
    # the background
    assert GOLD in [c for _, c in image.getcolors(1000)]  # type: ignore


def test_render_layout():
    grid = make_grid(blocks={(1, 1, 1): "stone"})
    one = render(grid, ["top"], scale=SCALE, labels=False)
    assert one.size == (5 * SCALE, 3 * SCALE)

    labelled = render(grid, ["top"], scale=SCALE)
    assert labelled.width > one.width and labelled.height > one.height
    both = render(grid, ["top", "south"], scale=SCALE)
    assert both.width > labelled.width
    every = render(grid, VIEWS, scale=SCALE)
    assert every.height > both.height

    with pytest.raises(ValueError, match="unknown view"):
        render(grid, ["sideways"])
    with pytest.raises(ValueError, match="no views"):
        render(grid, [])
    with pytest.raises(ValueError, match="scale"):
        render(grid, ["top"], scale=-1)


def test_labels_large_region():
    """labels on a region too large for one per block"""
    grid = BlockGrid(ORIGIN, np.zeros((300, 2, 40), dtype=np.int32), ["minecraft:air"])
    assert auto_scale(grid) == 1
    image = render(grid, ["top", "iso"])
    assert image.width > 300


def test_auto_scale():
    assert auto_scale(make_grid((10, 10, 10))) == 16
    assert auto_scale(make_grid((64, 1, 1))) == 8


def test_palette_argument():
    grid = make_grid((1, 1, 1), {(0, 0, 0): "stone"})
    palette = Palette({"stone": (1, 2, 3)})
    image = render(grid, ["top"], scale=2, labels=False, palette=palette)
    assert at(image, 0, 0) == (1, 2, 3)


def test_scan_world_files(tmp_path: Path, mock_client: MockClient):
    world = write_world(tmp_path / "world", {(1, 2, 3): "minecraft:gold_block"})
    vol = Volume.from_corners(Vec3(0, 2, 3), Vec3(2, 2, 3))

    grid = scan(vol, world)
    assert grid[Vec3(1, 2, 3)] == "minecraft:gold_block"
    assert mock_client.commands == []

    # with a client, the server is asked to save its changes first
    grid = scan(vol, world, mock_client)  # type: ignore
    assert mock_client.commands == ["save-all flush"]
    assert grid[Vec3(1, 2, 3)] == "minecraft:gold_block"


def test_scan_rcon(tmp_path: Path, mock_client: MockClient):
    mock_client.setblock(Vec3(1, 2, 3), Item.GOLD_BLOCK)
    vol = Volume.from_corners(Vec3(0, 2, 3), Vec3(2, 2, 3))

    # no world in the folder, so read over RCON
    for folder in (None, tmp_path):
        grid = scan(vol, folder, mock_client)  # type: ignore
        assert grid[Vec3(1, 2, 3)] == "minecraft:gold_block"

    with pytest.raises(ValueError, match="too many"):
        scan(vol, None, mock_client, max_rcon_blocks=2)  # type: ignore
    with pytest.raises(ValueError, match="no world in"):
        scan(vol, tmp_path)
    with pytest.raises(ValueError, match="no world folder"):
        scan(vol)


def test_render_module_not_shadowed():
    """``import mciwb.render`` gives the module, not the render function"""
    import importlib

    import mciwb.render as module

    assert module.scan is scan and module.render is render
    package = importlib.import_module("mciwb")
    assert package.render is module
