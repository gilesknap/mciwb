from demo.shapes import pyramid
from mciwb.imports import Direction, Item, Monitor, Vec3, get_world


class SpookyPyramid:
    """
    Spooky Pyramid Class: draws a pyramid centred at pyramid_centre, made
    of carved pumpkins that always turn to face the player
    """

    def __init__(self, pyramid_centre, size=11, player=None):
        self.pyramid_centre = Vec3(*pyramid_centre)
        self.size = size
        self.half = int(size / 2)
        self.corner = (
            self.pyramid_centre
            + Direction.SOUTH * self.half
            + Direction.WEST * self.half
        )
        self.old_direction = 0
        self.world = get_world()
        self.player = player or self.world.player
        self.name = "spooky_pyramid_" + self.player.name

    def stop(self):
        Monitor.stop_named(self.name)

    def go(self):
        Monitor.stop_named(self.name)
        Monitor(self.draw, name=self.name)

    def draw(self):
        direction = Direction.facing(self.pyramid_centre, self.player.pos)
        if direction != self.old_direction:
            self.old_direction = direction
            pyramid(self.corner, self.size, Item.CARVED_PUMPKIN, facing=direction)
