from mciwb import Direction, Item, Vec3


def tower(world, pos, width=5, height=8):
    """
    Create a tower of blocks at a given position.
    """

    # make sure the caller passed a variable of type Vec3 for pos
    assert isinstance(pos, Vec3)

    # each tower's wall is one less that width steps away from its opposite
    opposite = width - 1

    # outer loop does the layers of the tower
    for layer in range(height):

        y_offset = Direction.UP * layer

        # inner loop does the blocks in each of 4 walls
        for i in range(width):

            # calculate the position i steps to the east of pos
            eastward = pos + Direction.EAST * i + y_offset
            # front wall of tower
            world.set_block(eastward, Item.COBBLESTONE)
            # back wall of tower
            world.set_block(eastward + Direction.NORTH * opposite, Item.COBBLESTONE)

            # calculate the position i steps to the north of pos
            northward = pos + Direction.NORTH * i + y_offset
            # left wall of tower
            world.set_block(northward, Item.COBBLESTONE)
            # right wall of tower
            world.set_block(northward + Direction.EAST * opposite, Item.COBBLESTONE)
