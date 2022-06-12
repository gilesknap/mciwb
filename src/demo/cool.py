from mciwb.main import c, mc

print("loading cool stuff")


def box(start: mc.Position, size: int, item=mc.Item.ACACIA_FENCE):
    """
    makes a cube of blocks with SW bottom corner at start

    Factored for easy understanding
    """

    # calculate the position of the NW bottom corner
    opposite = start + (mc.Direction.EAST + mc.Direction.NORTH) * (size - 1)

    # make rows of walls
    for up in range(size):
        # make a rows for each of the four walls
        for east in range(size):
            block_pos = start + mc.Direction.EAST * east + mc.Direction.UP * up
            c.setblock(block_pos, item.value)
            block_pos = opposite - mc.Direction.EAST * east + mc.Direction.UP * up
            c.setblock(block_pos, item.value)
        for north in range(size):
            block_pos = start + mc.Direction.NORTH * north + mc.Direction.UP * up
            c.setblock(block_pos, item.value)
            block_pos = opposite - mc.Direction.NORTH * north + mc.Direction.UP * up
            c.setblock(block_pos, item.value)

    for up in [0, size - 1]:
        for east in range(size):
            for north in range(size):
                block_pos = (
                    start
                    + mc.Direction.NORTH * north
                    + mc.Direction.EAST * east
                    + mc.Direction.UP * up
                )
                c.setblock(block_pos, item.value)


def pyramid(start: mc.Position, size: int, item=mc.Item.MOSSY_COBBLESTONE):
    # make rows of walls
    row_size = size
    row_start = start
    for up in range(size):
        opposite = row_start + (mc.Direction.EAST + mc.Direction.NORTH) * (row_size - 1)
        # make a rows for each of the four walls
        for east in range(row_size):
            block_pos = row_start + mc.Direction.EAST * east + mc.Direction.UP * up
            c.setblock(block_pos, item.value)
            block_pos = opposite - mc.Direction.EAST * east + mc.Direction.UP * up
            c.setblock(block_pos, item.value)
        for north in range(row_size):
            block_pos = row_start + mc.Direction.NORTH * north + mc.Direction.UP * up
            c.setblock(block_pos, item.value)
            block_pos = opposite - mc.Direction.NORTH * north + mc.Direction.UP * up
            c.setblock(block_pos, item.value)

        row_start += mc.Direction.EAST + mc.Direction.NORTH
        row_size -= 2
        if row_size <= 0:
            break
