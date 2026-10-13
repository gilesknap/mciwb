"""
Survey a building site: the players nearby, the ground height and what the
ground is made of, and a top and iso render of the area.

Run it with ``mciwb run``, giving the site in the SURVEY environment variable
as ``X Z [RADIUS [YMIN YMAX]]`` (RADIUS defaults to 16, YMIN YMAX to the whole
world height)::

    SURVEY="632 -1658 24" mciwb run survey.py
    mciwb run survey.py --player NAME     # or around a player: ops them, creative

It prints a report and writes ``survey.png`` (set SURVEY_PNG to change it).
Reading the whole world height needs the world files on this machine (the
server of ``mciwb start``). Over RCON, which reads at most 32768 blocks, it
reads just a few blocks either side of the ground instead, finding the ground
with `ground_heights` (Minecraft's heightmaps) on a grid of columns; that
fails on hilly sites, so give a smaller RADIUS or a YMIN YMAX range.
"""

import os
from statistics import median

import numpy as np

from mciwb.imports import (
    BlockGrid,
    Iwb,
    Player,
    Vec3,
    Volume,
    get_client,
    get_world,
    ground_heights,
    render,
)

DEFAULT_RADIUS = 16
WORLD_BOTTOM, WORLD_TOP = -64, 319
# the most columns of the printed height map: wider sites are sampled
MAP_COLUMNS = 48
# over RCON: the spacing of the columns whose ground height is sampled, and
# how far below and above the sampled ground to read the blocks
SAMPLE_STEP = 4
BELOW_GROUND, ABOVE_GROUND = 4, 6

# blocks that sit on the ground rather than being it: plants, trees, snow layers
NOT_GROUND_ENDINGS = (
    "air",
    "_leaves",
    "_log",
    "_sapling",
    "_flower",
    "_tulip",
    "_mushroom",
    "_carpet",
    "_roots",
    "_vine",
    "_vines",
    "_bush",
)
NOT_GROUND = {
    "minecraft:short_grass",
    "minecraft:tall_grass",
    "minecraft:fern",
    "minecraft:large_fern",
    "minecraft:dandelion",
    "minecraft:poppy",
    "minecraft:blue_orchid",
    "minecraft:allium",
    "minecraft:azure_bluet",
    "minecraft:oxeye_daisy",
    "minecraft:cornflower",
    "minecraft:lily_of_the_valley",
    "minecraft:sunflower",
    "minecraft:lilac",
    "minecraft:rose_bush",
    "minecraft:peony",
    "minecraft:snow",
    "minecraft:vine",
    "minecraft:sugar_cane",
    "minecraft:lily_pad",
    "minecraft:seagrass",
    "minecraft:tall_seagrass",
    "minecraft:kelp",
    "minecraft:kelp_plant",
    "minecraft:cactus",
    "minecraft:bamboo",
    "minecraft:pink_petals",
    "minecraft:leaf_litter",
}
WATER = {"minecraft:water", "minecraft:ice", "minecraft:lava"}


def is_ground(name: str) -> bool:
    """True for blocks that a build can stand on (water is flagged separately)"""
    return name not in NOT_GROUND and not name.endswith(NOT_GROUND_ENDINGS)


def surface(grid: BlockGrid) -> tuple[np.ndarray, np.ndarray]:
    """
    The ground of each column of the grid: the y of its highest ground block
    (or the bottom of the grid less one for a column with no ground), and the
    index of that block's name, both indexed [x][z]
    """
    ground = np.array([is_ground(name) for name in grid.names])[grid.ids]
    # the highest ground block in each column, counting down from the top
    from_top = np.argmax(ground[:, ::-1, :], axis=1)
    top = grid.ids.shape[1] - 1 - from_top
    has_ground = ground.any(axis=1)
    x, z = np.indices(top.shape)
    # signed: the ids read from world files are uint16, where -1 does not fit
    ids = np.where(has_ground, grid.ids[x, top, z].astype(np.int64), -1)
    heights = np.where(has_ground, top + grid.origin.y, grid.origin.y - 1)
    return heights, ids


def players_near(vol: Volume) -> list[tuple[str, Vec3, bool]]:
    """the players online, their positions and whether each is inside vol"""
    found = []
    for online in get_client().players.players:
        pos = Player(online.name).pos
        found.append((online.name, pos, vol.inside(pos)))
    return found


def height_map(heights: np.ndarray, ids: np.ndarray, names: list[str]) -> list[str]:
    """
    Rows of a text height map, north first: each column's ground height above
    the lowest ground, as 0-9 then a-z (higher is '+'), '~' for water, ice or
    lava and ' ' for no ground
    """
    step = max(1, -(-max(heights.shape) // MAP_COLUMNS))
    low = heights[ids >= 0].min() if (ids >= 0).any() else 0
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    rows = []
    for z in range(0, heights.shape[1], step):
        row = ""
        for x in range(0, heights.shape[0], step):
            index = ids[x, z]
            if index < 0:
                row += " "
            elif names[index] in WATER:
                row += "~"
            else:
                rise = int(heights[x, z] - low)
                row += digits[rise] if rise < len(digits) else "+"
        rows.append(row)
    return rows


def near_ground(vol: Volume) -> Volume:
    """
    vol cut down to a few blocks below and above the ground, found from the
    heightmap of a grid of columns (one RCON command per column)
    """
    start, end = vol.start, vol.end
    xs = sorted({*range(start.x, end.x + 1, SAMPLE_STEP), end.x})
    zs = sorted({*range(start.z, end.z + 1, SAMPLE_STEP), end.z})
    heights = ground_heights([(x, z) for x in xs for z in zs]).values()
    low = max(start.y, min(heights) - BELOW_GROUND)
    high = min(end.y, max(heights) + ABOVE_GROUND)
    print(
        f"no world files: sampled the ground every {SAMPLE_STEP} blocks "
        f"(y {min(heights)}..{max(heights)}), reading y {low}..{high} over RCON"
    )
    return Volume.from_corners(Vec3(start.x, low, start.z), Vec3(end.x, high, end.z))


def site(world: Iwb) -> Volume:
    """the region to survey, from the SURVEY variable or around the player"""
    args = os.environ.get("SURVEY", "").split()
    if len(args) in (2, 3, 5):
        x, z = int(args[0]), int(args[1])
        radius = int(args[2]) if len(args) > 2 else DEFAULT_RADIUS
        y_low, y_high = (int(args[3]), int(args[4])) if len(args) == 5 else (0, 0)
    elif not args and world.player:
        pos = world.player.pos
        x, z, radius, y_low, y_high = int(pos.x), int(pos.z), DEFAULT_RADIUS, 0, 0
    else:
        raise SystemExit(
            'give the site as SURVEY="X Z [RADIUS [YMIN YMAX]]", or --player NAME'
        )
    if y_low == y_high == 0:
        y_low, y_high = WORLD_BOTTOM, WORLD_TOP
    return Volume.from_corners(
        Vec3(x - radius, y_low, z - radius), Vec3(x + radius, y_high, z + radius)
    )


def survey(world: Iwb, vol: Volume, png: str) -> None:
    """print a report on the site and render it"""
    start, end = vol.start, vol.end
    print(
        f"site x {start.x}..{end.x}, z {start.z}..{end.z} "
        f"(y {start.y}..{end.y}), north up, x increases east"
    )
    for name, pos, inside in players_near(vol):
        where = "INSIDE the site: do not build over them" if inside else "outside"
        x, y, z = pos.with_ints()
        print(f"player {name} at ({x}, {y}, {z}), {where}")

    try:
        grid = world.scan(start, end)
    except ValueError as e:
        if (start.y, end.y) != (WORLD_BOTTOM, WORLD_TOP):
            raise SystemExit(f"{e}: give a smaller RADIUS or Y range") from e
        # too many blocks to read over RCON: read only those near the ground
        vol = near_ground(vol)
        start, end = vol.start, vol.end
        try:
            grid = world.scan(start, end)
        except ValueError as e:
            raise SystemExit(f"{e}: give a smaller RADIUS") from e
    heights, ids = surface(grid)
    with_ground = heights[ids >= 0]
    if with_ground.size == 0:
        print("no ground in this region: it is all air or plants")
        return
    print(
        f"ground y (top ground block, ignoring plants, trees and snow): "
        f"min {with_ground.min()}, median {median(with_ground.tolist()):g}, "
        f"max {with_ground.max()}. Build on ground y + 1"
    )
    totals = np.bincount(ids[ids >= 0], minlength=len(grid.names))
    common = sorted(
        ((int(n), grid.names[i]) for i, n in enumerate(totals) if n), reverse=True
    )
    print("ground blocks: " + ", ".join(f"{name} {n}" for n, name in common[:6]))
    if any(name in WATER for _, name in common):
        print("there is water, ice or lava ('~' below)")

    rows = height_map(heights, ids, grid.names)
    step = max(1, -(-max(heights.shape) // MAP_COLUMNS))
    print(
        f"height map: ground y - {with_ground.min()}, one character per "
        f"{step} block(s), first row z {start.z}, first column x {start.x}"
    )
    for row in rows:
        print(f"  |{row}|")

    # render from just below the ground to a little above it, not the whole
    # world height, so that the iso view is not tiny
    bottom = max(start.y, int(with_ground.min()) - 4)
    top = min(end.y, int(with_ground.max()) + 16)
    ground_layers = BlockGrid(
        grid.origin + Vec3(0, bottom - start.y, 0),
        grid.ids[:, bottom - start.y : top - start.y + 1, :],
        grid.names,
    )
    render(ground_layers, ["top", "iso"]).save(png)
    print(f"rendered y {bottom}..{top} to {png}: read it to see the site")


if __name__ == "__main__":
    world = get_world()  # connected by `mciwb run`
    survey(world, site(world), os.environ.get("SURVEY_PNG", "survey.png"))
