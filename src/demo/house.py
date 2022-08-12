from mciwb.imports import Direction, Item, Wall, get_client, get_world


class House:
    """
    A class for constructing a house in the Minecraft world.

    :param width: The new width of the house in no. of windows
    :param depth: The new depth of the house in no. of windows
    :param height: The new height of the house in no. of floors
    """

    sign_name = "house"

    house_profile = [
        [
            [Item.STONE, Item.STONE, Item.STONE, Item.STONE],
            Item.STONE,
            Item.STONE,
            Item.STONE,
        ],
        [
            [Item.STONE, Item.STONE, Item.STONE, Item.STONE],
            Item.OAK_PLANKS,
            Item.IRON_BARS,
            Item.OAK_PLANKS,
        ],
        [
            [Item.STONE, Item.STONE, Item.STONE, Item.STONE],
            Item.OAK_PLANKS,
            Item.IRON_BARS,
            Item.OAK_PLANKS,
        ],
        [
            [Item.STONE, Item.STONE, Item.STONE, Item.STONE],
            Item.STONE,
            Item.STONE,
            Item.STONE,
        ],
    ]

    def __init__(
        self,
        height=1,
        width=3,
        depth=2,
        roof_item=Item.OAK_STAIRS,
    ):
        self.resize(width, depth, height)
        self.roof_item = roof_item
        self.add_signs()

    def resize(self, width=None, depth=None, height=None):
        """
        Resize the house.

        :param width: The new width of the house in no. of windows
        :param depth: The new depth of the house in no. of windows
        :param height: The new height of the house in no. of floors
        """
        if height:
            self.height = height * 4
        if width:
            self.width = width * 4 - 1
        if depth:
            self.depth = depth * 4 - 1

    def build(self, position):
        """
        Build the house at the given position. The dimensions of the house are
        determined by the width, height, and depth attributes of the house class.

        :param position: the location of the south-west bottom corner of the house.
        """

        w = Wall(profile=self.house_profile, height=self.height)

        depth, width = self.depth, self.width
        next = position

        # build the house walls
        w.set_start(next)
        next += Direction.NORTH * depth
        w.draw(next)
        next += Direction.EAST * width
        w.draw(next)
        next += Direction.SOUTH * depth
        w.draw(next)
        next += Direction.WEST * width
        w.draw(next)

        # build the roof
        c = get_client()
        start = (
            position
            + Direction.UP * (self.height + 1)
            + Direction.WEST
            + Direction.SOUTH
        )
        width += 2
        depth += 2
        while True:
            end = start + Direction.NORTH * depth
            c.fill(start, end, str(self.roof_item) + "[facing=east]")
            start = end
            end = start + Direction.EAST * width
            c.fill(start, end, str(self.roof_item) + "[facing=south]")
            start = end
            end = start + Direction.SOUTH * depth
            c.fill(start, end, str(self.roof_item) + "[facing=west]")
            start = end
            end = start + Direction.WEST * width
            c.fill(start, end, str(self.roof_item) + "[facing=north]")
            start = end + Direction.UP + Direction.EAST + Direction.NORTH

            width -= 2
            depth -= 2
            if width <= 0 or depth <= 0:
                break

    def add_signs(self):
        signs = get_world().signs
        signs.remove_sign(self.sign_name)
        signs.add_sign(self.sign_name, self.build)
        signs.give_signs()

    def remove_signs(self):
        signs = get_world().signs
        signs.remove_sign(self.sign_name)
