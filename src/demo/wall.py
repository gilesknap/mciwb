import logging

import numpy as np
from mcwb import Vec3

from mciwb.imports import Direction, Item, get_client
from mciwb.iwb import get_world


def wall(start: Vec3, stop: Vec3, height=5, item=Item.STONE):
    def section(wall_dir: Vec3, step_dir: Vec3):
        nonlocal begin, end
        end = begin + wall_dir
        c.fill(begin.with_ints(), end.with_ints() + Direction.UP * height, str(item))
        begin = end + step_dir

    c = get_client()
    dx = int(stop.x - start.x)
    dz = int(stop.z - start.z)

    begin = end = start

    if abs(dx) > abs(dz):
        count = abs(dz) + 1
        wall_dir = Direction.EAST * dx / count
        for step in range(count):
            section(wall_dir, Direction.SOUTH * np.sign(dz))
    else:
        count = abs(dx) + 1
        wall_dir = Direction.SOUTH * dz / count
        for step in range(count):
            section(wall_dir, Direction.EAST * np.sign(dx))


class WallMaker:
    def __init__(self):
        self.start = Vec3(0, 0, 0)
        self.end = self.start
        signs = get_world().signs
        signs.add_sign("start_wall", self.start_wall)
        signs.add_sign("end_wall", self.end_wall)
        signs.give_signs()

    def start_wall(self, pos: Vec3):
        self.start = pos

    def end_wall(self, pos: Vec3):
        self.end = pos
        logging.info(self.start, self.end)
        wall(self.start, self.end)
        self.start = pos
