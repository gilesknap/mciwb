"""
Build a small known structure on the test server, read it back from the
world files and over RCON, and render it
"""

import logging
import os
from time import monotonic

import numpy as np
from mcwb import Item, Vec3, Volume

from mciwb.blockgrid import grab_blocks
from mciwb.iwb import _rcon_port
from mciwb.palette import BLOCK_COLOURS, DYE_COLOURS
from mciwb.render import render_view, scan
from mciwb.server import MinecraftServer
from mciwb.threads import Client

# inside the chunks that the test server keeps loaded, away from other tests
LOW = Vec3(-30, -61, -30)
HIGH = Vec3(-24, -55, -24)
SCALE = 4


def build(client: Client) -> None:
    """
    A hollow stone brick hut with a red wool roof, a gold block inside and a
    glass window in the middle of its east wall, oak stairs facing east and an
    oak log lying east-west in two corners, on a lime concrete floor at
    y -61. Not grass, which turns to dirt under the hut while the test runs
    """
    client.fill(LOW + Vec3(0, 1, 0), HIGH, Item.AIR)
    client.fill(LOW, Vec3(HIGH.x, LOW.y, HIGH.z), Item.LIME_CONCRETE)
    client.fill(Vec3(-29, -60, -29), Vec3(-25, -57, -25), Item.STONE_BRICKS)
    client.fill(Vec3(-28, -60, -28), Vec3(-26, -57, -26), Item.AIR)
    client.fill(Vec3(-29, -56, -29), Vec3(-25, -56, -25), Item.RED_WOOL)
    client.setblock(Vec3(-27, -60, -27), Item.GOLD_BLOCK)
    client.setblock(Vec3(-25, -59, -27), Item.GLASS)
    # blocks in non default states give their sections a palette of compounds
    client.setblock(Vec3(-28, -60, -28), f"{Item.OAK_STAIRS}[facing=east]")
    client.setblock(Vec3(-26, -60, -26), f"{Item.OAK_LOG}[axis=x]")


def report(text: str) -> None:
    """log timings, and add them to the GitHub Actions job summary"""
    logging.info(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"- {text}\n")


def test_render(minecraft_container: MinecraftServer, minecraft_client: Client):
    client = minecraft_client
    build(client)
    vol = Volume.from_corners(LOW, HIGH)

    start = monotonic()
    grid = scan(vol, minecraft_container.world, client)
    report(f"scan {vol.size.volume} blocks from files: {monotonic() - start:.2f}s")

    assert grid.size == Vec3(7, 7, 7)
    assert grid[Vec3(-27, -60, -27)] == "minecraft:gold_block"
    assert grid[Vec3(-25, -59, -27)] == "minecraft:glass"
    assert grid[Vec3(-27, -59, -27)] == "minecraft:air"
    assert grid[Vec3(-28, -60, -28)] == "minecraft:oak_stairs"
    assert grid[Vec3(-26, -60, -26)] == "minecraft:oak_log"
    counts = grid.counts()
    assert counts["minecraft:red_wool"] == 25
    assert counts["minecraft:stone_bricks"] == 16 * 4 - 1
    assert counts["minecraft:lime_concrete"] == 49

    # the world files agree with the server, block for block
    start = monotonic()
    by_rcon = grab_blocks(client, vol)
    report(f"grab {vol.size.volume} blocks over RCON: {monotonic() - start:.2f}s")
    differ = np.argwhere(grid.to_names() != by_rcon.to_names())
    assert not differ.size, [
        (tuple(grid.origin + Vec3(*d)), grid.names[grid.ids[tuple(d)]])
        for d in differ[:10]
    ]

    # the plan shows the roof, with the floor around it
    top = render_view(grid, "top", SCALE, labels=False)
    roof = top.getpixel((3 * SCALE + 1, 3 * SCALE + 1))
    assert isinstance(roof, tuple)
    assert roof[:3] == DYE_COLOURS["red"]
    floor = top.getpixel((1, 1))
    assert isinstance(floor, tuple)
    assert floor[1] > floor[0] and floor[1] > floor[2]

    # the east side shows the window: stone bricks seen through glass
    east = render_view(grid, "east", SCALE, labels=False)
    # columns run from south (z -24) to north (z -30), rows from y -55 down
    window = east.getpixel((3 * SCALE + 1, 4 * SCALE + 1))
    wall = east.getpixel((2 * SCALE + 1, 4 * SCALE + 1))
    assert isinstance(wall, tuple) and isinstance(window, tuple)
    # grey, a little darker than the palette's stone bricks with distance
    bricks = BLOCK_COLOURS["stone_bricks"]
    assert all(0.8 * b <= w <= b for w, b in zip(wall, bricks, strict=True))
    assert window != wall


def test_scan_speed(minecraft_container: MinecraftServer, minecraft_client: Client):
    """measure reading the loaded chunks of the test server, for the docs"""
    vol = Volume.from_corners(Vec3(-48, -64, -48), Vec3(47, 319, 47))
    start = monotonic()
    grid = scan(vol, minecraft_container.world, minecraft_client)
    report(f"scan {vol.size.volume} blocks from files: {monotonic() - start:.2f}s")
    assert grid.counts()["minecraft:bedrock"] == 96 * 96

    vol = Volume.from_corners(Vec3(-16, -61, -16), Vec3(-1, -46, -1))
    start = monotonic()
    grab_blocks(minecraft_client, vol)
    report(f"grab {vol.size.volume} blocks over RCON: {monotonic() - start:.2f}s")


def test_world_folder_found_by_port(minecraft_container: MinecraftServer):
    """
    Iwb finds the world folder of a server started on a non default port by
    the rcon.port that the server writes to its server.properties
    """
    assert _rcon_port(minecraft_container.server_folder) == minecraft_container.rcon
