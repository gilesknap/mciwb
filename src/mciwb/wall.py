import logging
from typing import Any, List, Optional

import numpy as np
from mcipc.rcon.item import Item
from mcwb import Vec3
from mcwb.types import Direction

from mciwb.iwb import get_world
from mciwb.threads import get_client


class Wall:
    def __init__(self, height=5, item=Item.STONE, profile: Optional[List[Any]] = None):
        self._start = Vec3(0, 0, 0)
        self._end = Vec3(0, 0, 0)
        self.height: int = height
        self.item = str(item)
        self.profile = profile or []

    def draw(self, end: Optional[Vec3] = None):
        self._end = end or self._end
        self.render()
        self._start = self._end

    def set_start(self, pos: Vec3):
        self._start = pos

    def set_end(self, pos: Vec3):
        self._end = pos

    def render(self):
        logging.debug(f"drawing a wall v2 from {self._start} to {self._end}")

        dx = int(self._end.x - self._start.x)
        dz = int(self._end.z - self._start.z)

        begin = end = self._start

        if abs(dx) > abs(dz):
            count = abs(dz) + 1
            wall_dir = Direction.EAST * dx / count
            step_dir = Direction.SOUTH * np.sign(dz)
        else:
            count = abs(dx) + 1
            wall_dir = Direction.SOUTH * dz / count
            step_dir = Direction.EAST * np.sign(dx)

        for step in range(count):
            end = begin + wall_dir
            self.render_columns(begin, end)
            begin = end + step_dir

    def render_columns(self, begin: Vec3, end: Vec3):
        c = get_client()
        c.fill(
            begin.with_ints(), end.with_ints() + Direction.UP * self.height, self.item
        )


class WallMaker:
    start = "start_wall"
    end = "end_wall"

    def __init__(self):
        self.wall = Wall()
        signs = get_world().signs
        signs.add_sign(self.start, self.wall.set_start)
        signs.add_sign(self.end, self.wall.draw)
        signs.give_signs()

    def remove(self):
        signs = get_world().signs
        signs.remove_sign(self.start)
        signs.remove_sign(self.end)
