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
            wall_section_len = abs(dx / count)
            wall_dir = Direction.EAST * np.sign(dx)
            step_dir = Direction.SOUTH * np.sign(dz)
        else:
            count = abs(dx) + 1
            wall_section_len = abs(dz / count)
            wall_dir = Direction.SOUTH * np.sign(dz)
            step_dir = Direction.EAST * np.sign(dx)

        for step in range(count):
            end = begin + wall_dir * wall_section_len
            self.render_columns(begin, wall_section_len, wall_dir)
            begin = end + step_dir

    def render_columns(self, begin: Vec3, length: float, wall_dir: Vec3):
        c = get_client()
        begin_i = begin.with_ints()

        for step in range(int(length) + 1):
            c.fill(begin_i, begin_i + Direction.UP * self.height, self.item)
            begin_i = begin_i + wall_dir


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
