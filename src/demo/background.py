"""
Demonstrate the use of Monitor to set up a number of background threads to
monitor the world and respond to player movement.
"""

from demo.shapes import pyramid
from mciwb.imports import Direction, Item, Monitor, Vec3, get_world


class Follower:
    def __init__(self, center=(0, 5, 0), size=11):
        self.center = center
        self.old_facing = None
        self.size = size
        self.pyramid_centre = Vec3(*center)
        half = int(size / 2)
        self.corner = (
            self.pyramid_centre + Direction.SOUTH * half + Direction.WEST * half
        )

    def follow(self):
        """
        Spooky Pyramid function: draws a pyramid centred at pyramid_centre, made
        of carved pumpkins that always turn to face the player
        """
        world = get_world()

        facing = Direction.facing(self.pyramid_centre, world.player.pos)
        if facing != self.old_facing:
            self.old_facing = facing
            pyramid(self.corner, self.size, Item.CARVED_PUMPKIN, facing=facing)


def follow_thread():
    # Use 4 threads for 4 pyramids
    m = Monitor(start=False)
    m.add_poller_func(Follower((0, 5, 0)).follow)
    m.add_poller_func(Follower((20, 5, 0)).follow)
    m.add_poller_func(Follower((0, 5, 20)).follow)
    m.add_poller_func(Follower((20, 5, 20)).follow)
    m.start_poller()
