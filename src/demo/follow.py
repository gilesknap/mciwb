import time

from demo.shapes import pyramid
from mciwb import Direction, Item, Vec3, world


def follow(pyramid_centre):
    """
    Spooky Pyramid function: draws a pyramid centred at pyramid_centre, made
    of carved pumpkins that always turn to face the player
    """
    pyramid_centre = Vec3(*pyramid_centre)
    size = 11
    half = int(size / 2)
    corner = pyramid_centre + Direction.SOUTH * half + Direction.WEST * half

    old_direction = 0
    while True:
        time.sleep(0.5)
        direction = Direction.facing(Vec3(5, 0, -5), world.player.pos)
        if direction != old_direction:
            old_direction = direction
            pyramid(corner, size, Item.CARVED_PUMPKIN, facing=direction)
