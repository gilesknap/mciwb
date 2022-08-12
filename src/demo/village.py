from demo.house import House
from demo.pagoda import build_pagoda
from demo.walls import make_walls
from mciwb.imports import Anchor3, FillMode, Item, Vec3, get_client, get_world, polygon


def make_village():
    # flatten the ground by loading our ground file
    get_world().load("blocks/ground.json", Vec3(610, 72, -1673), Anchor3.BOTTOM_NW)

    # clear an area to build the village
    polygon(
        get_client(),
        Vec3(x=640, y=73, z=-1635),
        sides=4,
        height=200,
        diameter=90,
        item=Item.AIR,
        mode=FillMode.REPLACE,
    )

    # build the pagoda
    pagoda_pos = Vec3(585, 71, -1728)
    build_pagoda(pagoda_pos, width=30)
    pagoda_pos = Vec3(x=606, y=70, z=-1500)
    build_pagoda(pagoda_pos, width=30)

    # build the perimeter walls
    make_walls()

    h = House(width=5, depth=9, height=2)
    h.build(Vec3(x=609, y=72, z=-1601))
    h.resize(3, 3, 3)
    h.build(Vec3(x=615, y=83, z=-1605))
    h.build(Vec3(x=637, y=72, z=-1614))
    h.resize(1, 1, 6)
    h.build(Vec3(x=624, y=80, z=-1633))
    h.build(Vec3(x=610, y=80, z=-1633))
    h.resize(2, 2, 1)
    h.build(Vec3(x=615, y=87, z=-1621))
    h.resize(2, 2, 5)
    h.build(Vec3(x=639, y=87, z=-1616))
