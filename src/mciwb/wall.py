import logging
from typing import Any, List, Optional

import numpy as np
from mcipc.rcon.enumerations import SetblockMode
from mcipc.rcon.item import Item
from mcwb import Vec3
from mcwb.types import Direction

from mciwb.iwb import get_world
from mciwb.threads import get_client


class Wall:
    def __init__(self, height=5, item=Item.STONE, profile: Optional[List[Any]] = None):
        self._start: Vec3 = None  # type: ignore
        self._end: Vec3 = None  # type: ignore
        self.height: int = height
        self.item = str(item)
        if profile is None:
            # default profile is just a single column of stone
            profile = [self.item] * self.height
        self.profile = profile
        self.profile_idx = 0
        self.profile_idx_limit = len(profile)

    def draw(self, end: Optional[Vec3] = None):
        self._end = end + Direction.UP if end else self._end
        # start at the same height as the new end
        self._start = Vec3(self._start.x, self._end.y, self._start.z)
        self.render()
        self._start = self._end

    def set_start(self, pos: Vec3):
        self._start = pos + Direction.UP

    def set_end(self, pos: Vec3):
        self._end = pos + Direction.UP

    def render(self):
        logging.debug(f"drawing a wall v2 from {self._start} to {self._end}")

        dx = int(self._end.x - self._start.x)
        dz = int(self._end.z - self._start.z)

        begin = self._start

        if abs(dx) > abs(dz):
            sections = abs(dz) + 1
            wall_section_len = abs(dx / sections)
            wall_dir = Direction.EAST * np.sign(dx)
            step_dir = Direction.SOUTH * np.sign(dz)
        else:
            sections = abs(dx) + 1
            wall_section_len = abs(dz / sections)
            wall_dir = Direction.SOUTH * np.sign(dz)
            step_dir = Direction.EAST * np.sign(dx)

        logging.info(f"wall has {sections} sections of len {wall_section_len}")

        for step in range(sections):

            last_end = self.render_section(begin, wall_section_len, wall_dir)
            begin = last_end + step_dir

    def render_section(self, begin: Vec3, length: float, wall_dir: Vec3):
        battlement_dir = self._rot_right(wall_dir)
        c = get_client()
        base = begin
        end_base = begin + wall_dir * length
        # TODO need an to_int for Vec3 in mcwb
        end_base = Vec3(int(end_base.x), int(base.y), int(end_base.z))
        logging.info(
            f"render section len {length} from {begin}"
            f" to {begin + wall_dir * length} ({end_base})"
        )

        while True:
            logging.info(f"{base}")
            profile = self.profile[self.profile_idx]

            for level in range(len(profile)):
                level_profile = profile[level]
                if not isinstance(level_profile, List):
                    level_profile = [level_profile]
                for i, item in enumerate(level_profile):
                    pos = base.with_ints() + Direction.UP * level + battlement_dir * i
                    c.setblock(pos, level_profile[i], mode=SetblockMode.KEEP)

            if base.with_ints() == end_base:
                return end_base

            base = base + wall_dir
            self.profile_idx = (self.profile_idx + 1) % self.profile_idx_limit

    def _rot_left(self, direction: Vec3) -> Vec3:
        # TODO this function should be a member of Direction in mcwb
        index = Direction.cardinals.index(direction)
        return Direction.cardinals[(index - 1) % 4]

    def _rot_right(self, direction: Vec3) -> Vec3:
        # TODO this function should be a member of Direction in mcwb
        index = Direction.cardinals.index(direction)
        return Direction.cardinals[(index + 1) % 4]


class WallMaker:
    start = "start_wall"
    end = "end_wall"

    def __init__(self, wall: Optional[Wall] = None):
        self.wall = wall or Wall()
        signs = get_world().signs
        signs.add_sign(self.start, self.wall.set_start)
        signs.add_sign(self.end, self.wall.draw)
        signs.give_signs()

    def remove(self):
        signs = get_world().signs
        signs.remove_sign(self.start)
        signs.remove_sign(self.end)
