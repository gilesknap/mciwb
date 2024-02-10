from typing import Any

import numpy as np
from mcipc.rcon.enumerations import SetblockMode
from mcipc.rcon.item import Item
from mcwb import Vec3
from mcwb.types import Direction

from mciwb.iwb import get_world
from mciwb.logging import log
from mciwb.threads import get_client


class Wall:
    def __init__(self, height=None, item=Item.STONE, profile: list[Any] | None = None):
        self._start: Vec3 = None  # type: ignore
        self._end: Vec3 = None  # type: ignore
        self.height: int | None = height

        if profile is None:
            # default profile is just a single column of stone
            if height is None or item is None:
                raise ValueError("height and item or a profile must be specified")
            else:
                profile = [item] * height
        else:
            self.profile = profile
            self.profile_idx = 0
            self.profile_idx_limit = len(profile)

    def set_start(self, pos: Vec3):
        self._start = pos + Direction.UP

    def set_end(self, pos: Vec3):
        self._end = pos + Direction.UP

    def draw(self, end: Vec3 | None = None):
        self._end = end + Direction.UP if end else self._end
        # start at the same height as the new end
        self._start = Vec3(self._start.x, self._end.y, self._start.z)
        self._render()
        self._start = self._end

    def _render(self):
        log.debug(f"drawing a wall v2 from {self._start} to {self._end}")

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

        log.debug(
            f"wall has {sections} sections of len {wall_section_len} "
            "wall_dir {wall_dir} step_dir {step_dir}"
        )

        for _section in range(sections):
            end = begin + wall_dir * wall_section_len
            self._render_section(begin, wall_section_len, wall_dir)
            begin = end + step_dir

    def _render_section(self, begin: Vec3, length: float, wall_dir: Vec3):
        col_dir = self._rot_right(wall_dir)
        base = begin

        log.debug(
            f"render section len {length} from {begin}"
            f" to {begin + wall_dir * length}"
        )

        for _column in range(int(length) + 1):
            profile = self.profile[self.profile_idx]
            self._render_column(base, profile, col_dir)

            base = base + wall_dir
            self.profile_idx = (self.profile_idx + 1) % self.profile_idx_limit

    def _render_column(self, base: Vec3, profile: list[Any], direction: Vec3):
        c = get_client()
        height = self.height or len(profile)
        for level in range(height):
            level_profile = profile[(height - level - 1) % len(profile)]
            if not isinstance(level_profile, list):
                level_profile = [level_profile]
            for i, _item in enumerate(level_profile):
                pos = base.with_ints() + Direction.UP * level + direction * i
                c.setblock(pos, level_profile[i], mode=SetblockMode.REPLACE)

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

    def __init__(self, wall: Wall | None = None):
        self.wall = wall or Wall()
        signs = get_world().signs
        signs.add_sign(self.start, self.wall.set_start)
        signs.add_sign(self.end, self.wall.draw)
        signs.give_signs()

    def remove(self):
        signs = get_world().signs
        signs.remove_sign(self.start)
        signs.remove_sign(self.end)
