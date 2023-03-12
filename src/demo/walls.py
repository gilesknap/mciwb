from demo.gate import disable_gate, make_gate
from mciwb.imports import Item, Vec3, Wall

battlements_profile = [
    [
        Item.STONE,
        Item.OAK_PLANKS,
        [Item.STONE, Item.STONE, Item.STONE],
        Item.STONE,
        Item.STONE,
        Item.STONE,
    ],
    [
        [Item.OAK_PLANKS, Item.AIR, Item.TORCH],
        [Item.STONE, Item.STONE, Item.STONE],
        Item.STONE,
        Item.IRON_BARS,
        Item.STONE,
    ],
    [
        Item.STONE,
        Item.OAK_PLANKS,
        [Item.STONE, Item.STONE, Item.STONE],
        Item.STONE,
        Item.STONE,
        Item.STONE,
    ],
    [
        Item.OAK_PLANKS,
        [Item.OAK_PLANKS, Item.STONE, Item.STONE],
        Item.OAK_PLANKS,
        Item.OAK_PLANKS,
        Item.OAK_PLANKS,
    ],
]


def make_walls():
    w = Wall(profile=battlements_profile)

    # build the castle walls
    w.set_start(Vec3(x=630, y=72, z=-1660))
    w.draw(Vec3(x=644, y=72, z=-1660))
    w.draw(Vec3(x=644, y=72, z=-1637))
    w.draw(Vec3(x=659, y=72, z=-1637))
    w.draw(Vec3(x=659, y=72, z=-1606))
    w.draw(Vec3(x=642, y=72, z=-1606))
    w.draw(Vec3(x=642, y=72, z=-1601))
    w.draw(Vec3(x=609, y=72, z=-1601))
    w.draw(Vec3(x=609, y=72, z=-1636))
    w.draw(Vec3(x=617, y=72, z=-1660))
    w.draw(Vec3(x=620, y=72, z=-1660))

    # disable first to remove monitor on the portcullis lever
    disable_gate()
    # build the gate
    make_gate()
