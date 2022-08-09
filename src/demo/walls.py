from mciwb.imports import FillMode, Item, Vec3, Wall, get_client, polygon

profile = [
    [
        Item.STONE,
        Item.STONE,
        [Item.STONE, Item.STONE, Item.STONE],
        Item.STONE,
        Item.PURPLE_CONCRETE,
        Item.GOLD_BLOCK,
    ],
    [
        Item.STONE,
        [Item.STONE, Item.STONE, Item.STONE],
        Item.STONE,
        Item.GOLD_BLOCK,
        Item.PURPLE_CONCRETE,
    ],
]


def castle_wall():
    polygon(
        get_client(),
        Vec3(x=640, y=71, z=-1635),
        height=200,
        diameter=55,
        item=Item.AIR,
        mode=FillMode.REPLACE,
    )

    w = Wall(profile=profile)

    w.set_start(Vec3(x=633, y=70, z=-1647))

    w.set_start(Vec3(x=630, y=72, z=-1660))
    w.draw(Vec3(x=635, y=72, z=-1658))
    w.draw(Vec3(x=646, y=71, z=-1657))
    w.draw(Vec3(x=660, y=71, z=-1637))
    w.draw(Vec3(x=660, y=71, z=-1632))
    w.draw(Vec3(x=661, y=70, z=-1610))
    w.draw(Vec3(x=658, y=70, z=-1604))
    w.draw(Vec3(x=637, y=70, z=-1605))
    w.draw(Vec3(x=637, y=70, z=-1619))
    w.draw(Vec3(x=631, y=70, z=-1619))
    w.draw(Vec3(x=623, y=69, z=-1619))
    w.draw(Vec3(x=623, y=69, z=-1630))
    w.draw(Vec3(x=623, y=70, z=-1639))
    w.draw(Vec3(x=623, y=71, z=-1646))
    w.draw(Vec3(x=619, y=71, z=-1646))
    w.draw(Vec3(x=619, y=71, z=-1648))
    w.draw(Vec3(x=620, y=72, z=-1660))
