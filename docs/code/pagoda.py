def pagoda(pos, width=4, floor_height=4, item: Item = Item.GOLD_BLOCK):
    """
    Create a pagoda out of blocks at the given position.
    """

    from mcwb.api import polygon

    c = get_client()

    level = 0
    for floor_width in range(width, 2, -2):

        # calculate the base position of the walls for this level
        base = pos + Direction.UP * level * floor_height

        # calculate the position of the balcony for this level
        # it should appear around the top layer of the walls for this level
        balcony = base + Direction.UP * (floor_height - 1)

        # use a 4 sided polygon (square) to create the balcony for this level
        polygon(c, balcony, 1, floor_width + 2, sides=4, item=item)

        # create the walls for this level by stacking squares
        # on top of each other to make a cube of size
        # floor_width x floor_width x floor_height
        polygon(c, base, floor_height, floor_width, sides=4, item=item)

        level += 1
