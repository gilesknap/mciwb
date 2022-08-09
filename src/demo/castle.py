from demo.gate import disable_gate, make_gate
from demo.pagoda import build_pagoda
from mciwb.imports import (
    Anchor3,
    FillMode,
    Item,
    Vec3,
    Wall,
    get_client,
    get_world,
    polygon,
)

profile = [
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


def make_castle():
    # flatten the ground
    get_world().load("blocks/ground.json", Vec3(610, 72, -1673), Anchor3.BOTTOM_NW)

    # clear an area to build the castle
    polygon(
        get_client(),
        Vec3(x=640, y=73, z=-1635),
        sides=4,
        height=200,
        diameter=90,
        item=Item.AIR,
        mode=FillMode.REPLACE,
    )

    w = Wall(profile=profile)

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

    # build the pagoda
    pagoda_pos = Vec3(585, 71, -1728)
    build_pagoda(pagoda_pos, width=30)
