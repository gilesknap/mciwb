from mcipc.rcon.enumerations import CloneMode, Item, MaskMode
from mcipc.rcon.je import Client
from mcwb.types import Vec3

from mciwb.player import Player

zero = Vec3(0, 0, 0)


class CopyPaste:
    """
    Provides an interactive way to use copy and paste commands within a
    Minecraft world.
    """

    def __init__(self, player: Player, client: Client):
        self.player = player
        self.client = client
        self.start_b: Vec3 = self.player.pos(client=client)
        self.stop_b: Vec3 = self.start_b
        self.paste_b: Vec3 = self.start_b
        self.clone_dest = zero
        self.size = zero

    def get_commands(self):
        return {
            "select": self.select,
            "paste": self.paste,
            "expand": self.expand_to,
            "clear": self.fill,
        }

    def select(self, pos: Vec3, client=None):
        """
        Select a new copy buffer start point in the world.
        The previous start point becomes the stop point
        (i.e. opposite corner of the paste buffer)
        """
        self.stop_b = self.start_b
        self.start_b = pos
        self.size = self.stop_b - self.start_b
        self._set_paste(Vec3(self.start_b.x, self.start_b.y, self.start_b.z))

    def _set_paste(self, pos: Vec3):
        """
        Set the paste point relative to the current player position
        """
        self.paste_b = pos
        # adjust clone dest so the paste corner matches the start paste buffer
        self.clone_dest = self.paste_b
        x_off = self.size.x if self.size.x < 0 else 0
        y_off = self.size.y if self.size.y < 0 else 0
        z_off = self.size.z if self.size.z < 0 else 0
        self.clone_dest += Vec3(x_off, y_off, z_off)

    def paste(self, pos: Vec3, force=True, client=None):
        """
        Copy the contents of past buffer to position x y z
        """
        client = client or self.client
        self._set_paste(pos)
        mode = CloneMode.FORCE if force else CloneMode.NORMAL
        result = client.clone(
            self.start_b,
            self.stop_b,
            self.clone_dest,
            mask_mode=MaskMode.REPLACE,
            clone_mode=mode,
        )
        print(result)

    def paste_safe(self, pos: Vec3, client=None):
        self.paste(pos, client=client, force=False)

    def fill(self, pos: Vec3, client=None, item: Item = Item.AIR):
        """
        fill the paste buffer offset by x y z with Air or a specified block
        """
        client = client or self.client
        item = item or Item.AIR
        offset = pos
        end = self.paste_b + self.size + offset
        result = client.fill(self.paste_b + offset, end, str(item))
        print(result)

    def expand_to(self, pos: Vec3, client=None):
        """
        expand one or more of the dimensions of the copy buffer by moving
        the faces outwards to the specified point
        """
        # use mutable start and stop here to make the code more readable
        start = self.start_b._asdict()
        stop = self.stop_b._asdict()

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

        self.select(**stop)
        self.select(**start)

    def expand(self, x=0, y=0, z=0):
        """
        expand one or more of the dimensions of the copy buffer by relative
        amounts
        """
        expander = Vec3(x, y, z)
        # use mutable start and stop here to make the code more readable
        start = self.start_b._asdict()
        stop = self.stop_b._asdict()

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

        self.select(**stop)
        self.select(**start)
