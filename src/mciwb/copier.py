import logging

from mcipc.rcon.enumerations import CloneMode, Item, MaskMode
from mcwb.types import Vec3

from mciwb.threads import get_client

zero = Vec3(0, 0, 0)


class CopyPaste:
    """
    Provides an interactive way to use copy and paste commands within a
    Minecraft world.
    """

    def __init__(self):
        self.start_pos: Vec3 = zero
        self.stop_pos: Vec3 = self.start_pos
        self.paste_pos: Vec3 = self.start_pos
        self._clone_dest = zero
        self.size = zero

    def get_commands(self):
        return {
            "select": self.select,
            "paste": self.paste,
            "expand": self.expand_to,
            "clear": self.clear,
        }

    def select(self, pos: Vec3):
        """
        Select a new copy buffer start point in the world.
        The previous start point becomes the stop point
        (i.e. opposite corner of the paste buffer)
        """
        self.stop_pos = self.start_pos
        self.start_pos = pos.with_ints()
        self.size = self.stop_pos - self.start_pos
        self._set_paste(Vec3(self.start_pos.x, self.start_pos.y, self.start_pos.z))

    def _set_paste(self, pos: Vec3):
        """
        Set the paste point relative to the current player position
        """
        self.paste_pos = pos
        # adjust clone dest so the paste corner matches the start paste buffer
        self._clone_dest = self.paste_pos
        x_off = self.size.x if self.size.x < 0 else 0
        y_off = self.size.y if self.size.y < 0 else 0
        z_off = self.size.z if self.size.z < 0 else 0
        self._clone_dest += Vec3(x_off, y_off, z_off)

    def paste(self, pos: Vec3, force=True):
        """
        Copy the contents of past buffer to position x y z
        """
        client = get_client()
        self._set_paste(pos)
        mode = CloneMode.FORCE if force else CloneMode.NORMAL
        result = client.clone(
            self.start_pos,
            self.stop_pos,
            self._clone_dest,
            mask_mode=MaskMode.REPLACE,
            clone_mode=mode,
        )
        logging.info(result)

    def paste_safe(self, pos: Vec3):
        self.paste(pos, force=False)

    def fill(self, pos: Vec3 = zero, item: Item = Item.AIR):
        """
        fill the paste buffer offset by x y z with Air or a specified block
        """
        client = get_client()

        offset = pos
        end = self.paste_pos + self.size + offset
        result = client.fill(self.paste_pos + offset, end, item.value)
        logging.info(result)

    def clear(self, _: Vec3 = zero):
        """
        Clear the current paste buffer
        """
        self.fill()

    def expand_to(self, pos: Vec3):
        """
        expand one or more of the dimensions of the copy buffer by moving
        the faces outwards to the specified point
        """
        # use mutable start and stop here to make the code more readable
        start = self.start_pos._asdict()
        stop = self.stop_pos._asdict()

        for dim in ["x", "y", "z"]:
            if start[dim] <= stop[dim]:
                if pos[dim] > stop[dim]:
                    stop[dim] = pos[dim]
                elif pos[dim] < start[dim]:
                    start[dim] = pos[dim]
            elif start[dim] >= stop[dim]:
                if pos[dim] < stop[dim]:
                    stop[dim] = pos[dim]
                elif pos[dim] > start[dim]:
                    start[dim] = pos[dim]

        self.select(Vec3(**stop))
        self.select(Vec3(**start))

    def expand(self, x=0, y=0, z=0):
        """
        expand one or more of the dimensions of the copy buffer by relative
        amounts
        """
        expander = Vec3(x, y, z)
        # use mutable start and stop here to make the code more readable
        start = self.start_pos._asdict()
        stop = self.stop_pos._asdict()

        for dim in ["x", "y", "z"]:
            if expander[dim] > 0:
                if start[dim] > stop[dim]:
                    start[dim] += expander[dim]
                else:
                    stop[dim] += expander[dim]
            elif expander[dim] < 0:
                if start[dim] < stop[dim]:
                    start[dim] += expander[dim]
                else:
                    stop[dim] += expander[dim]

        self.select(Vec3(**stop))
        self.select(Vec3(**start))
