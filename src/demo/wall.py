import numpy as np

from mciwb.imports import Direction, Item, get_client


def wall(start, stop):
    def section(begin, wall_dir, step_dir):
        end = begin + wall_dir
        c.fill(begin.with_ints(), end.with_ints() + Direction.UP * 5, Item.STONE)
        begin = end + step_dir
        return begin, end

    c = get_client()
    dx = stop.x - start.x
    dz = stop.z - start.z

    begin = start

    if abs(dx) > abs(dz):
        count = abs(dz + 1)
        wall_dir = Direction.EAST * dx / count

        for step in range(count):
            begin, end = section(begin, wall_dir, Direction.SOUTH * np.sign(dz))
    else:
        count = abs(dx + 1)
        wall_dir = Direction.SOUTH * dz / count

        for step in range(count):
            begin, end = section(begin, wall_dir, Direction.EAST * np.sign(dx))
