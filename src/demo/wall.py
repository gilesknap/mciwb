import numpy as np

from mciwb.imports import Direction, Item, get_client


def wall(start, end):
    c = get_client()
    dx = end.x - start.x
    dz = end.z - start.z

    section_begin = start

    if abs(dx) > abs(dz):
        z_dir = np.sign(dz)
        count = abs(dz + 1)

        for step in range(count):
            section_end = section_begin + Direction.EAST * dx / count
            c.fill(
                section_begin.with_ints(),
                section_end.with_ints() + Direction.UP * 5,
                Item.STONE,
            )
            section_begin = section_end + Direction.SOUTH * z_dir
