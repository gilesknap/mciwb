"""
Functions to make some shapes in the world
"""

import logging
from datetime import datetime

from mciwb.imports import Direction, Item, Vec3, get_world

logging.info("loading cool stuff")


def box(start: Vec3, size: int, item=Item.ACACIA_FENCE):
    """
    makes a cube of blocks with SW bottom corner at start

    Factored for easy understanding
    """

    world = get_world()

    # calculate the Vec3 of the NW bottom corner
    opposite = start + (Direction.EAST + Direction.NORTH) * (size - 1)

    # make rows of walls
    for up in range(size):
        # make a rows for each of the four walls
        for east in range(size):
            block_pos = start + Direction.EAST * east + Direction.UP * up
            world.set_block(block_pos, item)
            block_pos = opposite - Direction.EAST * east + Direction.UP * up
            world.set_block(block_pos, item)
        for north in range(size):
            block_pos = start + Direction.NORTH * north + Direction.UP * up
            world.set_block(block_pos, item)
            block_pos = opposite - Direction.NORTH * north + Direction.UP * up
            world.set_block(block_pos, item)

    for up in [0, size - 1]:
        for east in range(size):
            for north in range(size):
                block_pos = (
                    start
                    + Direction.NORTH * north
                    + Direction.EAST * east
                    + Direction.UP * up
                )
                world.set_block(block_pos, item)


def pyramid(start: Vec3, size: int, item=Item.COBBLESTONE, **kwargs):
    """
    Build a pyramid with South West Corner at 'start'
    """
    world = get_world()

    # make rows of walls
    row_size = size
    row_start = start
    for up in range(size):
        opposite = row_start + (Direction.EAST + Direction.NORTH) * (row_size - 1)
        # make a rows for each of the four walls
        for east in range(row_size):
            block_pos = row_start + Direction.EAST * east + Direction.UP * up
            world.set_block(block_pos, item, **kwargs)
            block_pos = opposite - Direction.EAST * east + Direction.UP * up
            world.set_block(block_pos, item, **kwargs)
        for north in range(row_size):
            block_pos = row_start + Direction.NORTH * north + Direction.UP * up
            world.set_block(block_pos, item, **kwargs)
            block_pos = opposite - Direction.NORTH * north + Direction.UP * up
            world.set_block(block_pos, item, **kwargs)

        row_start += Direction.EAST + Direction.NORTH
        row_size -= 2
        if row_size <= 0:
            break


# Minecraft Education Edition Equivalent

# def tower(start, size, height, item):
#     for y in range(height):
#         for x in range(size):
#             for z in range(size):
#                 blocks.place(item, start.add(pos(0,y,z)))
#                 blocks.place(item, start.add(pos(size,y,z)))
#                 blocks.place(item, start.add(pos(x,y,0)))
#                 blocks.place(item, start.add(pos(x,y,size)))
#         blocks.place(item, start.add(pos(x,y,z)))

# tower(world(0, 4, 0), 9, 10, COBBLESTONE)


def tower(start: Vec3, size: int, height: int, item=Item.COBBLESTONE):
    world = get_world()

    start_time = datetime.now()

    z = x = 0
    for y in range(height):
        for x in range(size):
            for z in range(size):
                world.set_block(start + Vec3(0, y, z), item)
                world.set_block(start + Vec3(size, y, z), item)
                world.set_block(start + Vec3(x, y, 0), item)
                world.set_block(start + Vec3(x, y, size), item)
        world.set_block(start + Vec3(x, y, z), item)

    diff_time = datetime.now() - start_time

    logging.warning(f"tower took {diff_time.total_seconds()} seconds")
