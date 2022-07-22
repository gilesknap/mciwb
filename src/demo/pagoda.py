def pagoda(pos, width=4, floor_height=4, item: Item = Item.GOLD_BLOCK):
    """
    Create a pagoda out of blocks at the given position.
    """

    from mcwb.api import polygon

    c = get_client()

    level = 0
    for floor_width in range(width, 2, -2):

        base = pos + Direction.UP * level * floor_height
        balcony = base + Direction.UP * (floor_height - 1)

        polygon(c, balcony, 1, floor_width + 2, sides=4, item=item)
        polygon(c, base, floor_height, floor_width, sides=4, item=item)

        level += 1
