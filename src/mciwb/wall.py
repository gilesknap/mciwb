"""
Build walls with a repeating profile of blocks
"""

from typing import Any

import numpy as np
from mcipc.rcon.enumerations import SetblockMode
from mcwb import Item, Vec3
from mcwb.types import Direction

from mciwb.iwb import get_world
from mciwb.logging import log
from mciwb.threads import get_client


class Wall:
    """
    Draw walls between pairs of points in the world.

    A wall is drawn column by column along the line from its start to its
    end. The *profile* describes the columns, and is repeated along the
    length of the wall:

    - the profile is a list of columns
    - each column is a list of blocks, from the top of the column down
    - each block is an ``Item``, or a list of Items to make the wall more than
      one block thick (extending to the right of the direction of drawing)

    If the column is shorter than *height* it is repeated to fill the height.

    For example, a castle wall with crenellations on top::

        battlement = [Item.AIR, Item.STONE_BRICKS, Item.STONE_BRICKS]
        solid = [Item.STONE_BRICKS] * 3
        wall = Wall(profile=[solid, battlement])
        wall.set_start(Vec3(0, -60, 0))
        wall.draw(Vec3(20, -60, 0))

    :param height: the height of the wall, defaults to the length of each
        column in the profile
    :param item: the block to build a plain wall from, used when no profile
        is given
    :param profile: the profile of the wall, a list of columns
    """

    def __init__(
        self,
        height: int | None = None,
        item: Item | str = Item.STONE,
        profile: list[Any] | None = None,
    ):
        self._start: Vec3 = None  # type: ignore
        self._end: Vec3 = None  # type: ignore
        self.height: int | None = height

        if profile is None:
            # default profile is just a single column of item
            if height is None:
                raise ValueError("height or a profile must be specified")
            profile = [[item] * height]

        self.profile = profile
        self.profile_idx = 0
        self.profile_idx_limit = len(profile)

    def set_start(self, pos: Vec3):
        """
        Set the start point of the next wall. The wall is built on top of
        the block at *pos*.

        :param pos: the block that the wall starts on
        """
        self._start = pos + Direction.UP

    def set_end(self, pos: Vec3):
        """
        Set the end point of the next wall without drawing it.

        :param pos: the block that the wall ends on
        """
        self._end = pos + Direction.UP

    def draw(self, end: Vec3 | None = None):
        """
        Draw the wall from the start point to *end* (or the end point set
        with `set_end`). The end becomes the start of the next wall, so
        calling draw repeatedly draws a connected series of walls.

        :param end: the block that the wall ends on
        """
        if self._start is None:
            raise ValueError("call set_start before draw")
        self._end = end + Direction.UP if end else self._end
        if self._end is None:
            raise ValueError("no end point given for the wall")
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
            f"render section len {length} from {begin} to {begin + wall_dir * length}"
        )

        for _column in range(int(length) + 1):
            profile = self.profile[self.profile_idx]
            self._render_column(base, profile, col_dir)

            base = base + wall_dir
            self.profile_idx = (self.profile_idx + 1) % self.profile_idx_limit

    def _render_column(self, base: Vec3, profile: Any, direction: Vec3):
        c = get_client()
        if not isinstance(profile, list):
            profile = [profile]  # a column of a single block
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
        index = Direction.cardinals().index(direction)
        return Direction.cardinals()[(index - 1) % 4]

    def _rot_right(self, direction: Vec3) -> Vec3:
        # TODO this function should be a member of Direction in mcwb
        index = Direction.cardinals().index(direction)
        return Direction.cardinals()[(index + 1) % 4]


class WallMaker:
    """
    Build walls interactively with command signs. Gives the player a
    'start_wall' sign and an 'end_wall' sign. Place 'start_wall' to set
    the start of a wall, then place 'end_wall' to draw the wall up to it.
    Keep placing 'end_wall' signs to draw a connected series of walls.

    Requires a player added with `Iwb.add_player`.

    :param wall: the `Wall` to draw, defaults to a plain stone wall 3 high
    """

    start = "start_wall"
    end = "end_wall"

    def __init__(self, wall: Wall | None = None):
        self.wall = wall or Wall(height=3)
        signs = get_world().signs
        signs.add_sign(self.start, self.wall.set_start)
        signs.add_sign(self.end, self.wall.draw)
        signs.give_signs()

    def remove(self):
        """Stop responding to the wall signs"""
        signs = get_world().signs
        signs.remove_sign(self.start)
        signs.remove_sign(self.end)
