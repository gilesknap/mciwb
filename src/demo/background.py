from demo.shapes import pyramid
from mciwb import Direction, Item, Monitor, Vec3, world


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

        facing = Direction.facing(self.pyramid_centre, world.player.pos)
        if facing != self.old_facing:
            self.old_facing = facing
            pyramid(self.corner, self.size, Item.CARVED_PUMPKIN, facing=facing)


def follow_thread():
    # Use two threads for two pyramids
    p1 = Follower((0, 5, 0))
    p2 = Follower((20, 5, 0))
    p3 = Follower((0, 5, 20))
    p4 = Follower((20, 5, 20))
    Monitor([p1.follow, p2.follow, p3.follow, p4.follow])
