"""
.. module:: utils
    :synopsis: Utility functions for common operations in the Minecraft world.

    Under Construction ...
"""

from mcipc.rcon.item import Item
from mcwb import Direction, Vec3


class Utils:
    def __init__(self, world):
        self.world = world

    def place_door(
        self,
        pos: Vec3,
        door_type: Item,
        facing: Direction = Direction.NORTH,  # type: ignore
        open: bool = False,
        right_hinge: bool = False,
    ):
        """
        Place a door in the world

        :param pos: the position of the door in the world
        :param door_type: the type of door to place
        :param direction: the direction the door should face
        :param open: whether the door should be open or closed
        :param left_hinge: whether the door should have a left or right hinge
        """
        if not str(door_type).upper().endswith("_DOOR"):
            raise ValueError("door_type must be a door")

        hinge = "right" if right_hinge else "left"
        open_str = "true" if open else "false"

        common_nbt = [
            f"hinge={hinge}",
            f"open={open_str}",
            f"facing={Direction.name(facing)}",  # type: ignore
        ]

        nbt = ["half=lower"] + common_nbt
        # doors wont replace doors with different nbt so need to clear first
        self.world.set_block(pos, Item.AIR)
        self.world.set_block(pos, door_type, nbt=nbt)
        nbt = ["half=upper"] + common_nbt
        self.world.set_block(pos + Direction.UP, Item.AIR)
        self.world.set_block(pos + Direction.UP, door_type, nbt=nbt)
