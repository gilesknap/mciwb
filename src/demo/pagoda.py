from mciwb import Direction, Item, get_client, polygon


def build_pagoda(pos, width=4, floor_height=4, item: Item = Item.GOLD_BLOCK):
    """
    Create a pagoda out of blocks at the given position.

    Each successive floor is narrower and each has a balcony at the top.

    The first floors width is `width` and each floor height is `floor_height`.
    """
    c = get_client()

    # calculate how many levels we can make if we reduce width by 2 each level
    levels = width // 2

    print(levels)
    for level in range(levels):
        print(level)
        # calculate the width of the pagoda for this level
        floor_width = width - 2 * level

        # calculate the base position of the walls for this level
        base = pos + Direction.UP * level * floor_height

        # calculate the position of the balcony for this level
        # it should surround the top layer of the walls for this level
        balcony = base + Direction.UP * (floor_height - 1)

        # create the balcony for this level
        polygon(
            client=c,
            center=balcony,
            height=1,
            diameter=floor_width + 2,
            sides=4,
            item=item,
        )

        # create the walls for this level
        polygon(
            client=c,
            center=base,
            height=floor_height,
            diameter=floor_width,
            sides=4,
            item=item,
        )
