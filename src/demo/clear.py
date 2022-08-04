from mciwb.imports import FillMode, Item, Vec3, get_client, polygon


def clear():
    polygon(
        get_client(),
        Vec3(x=639, y=73, z=-1630),
        100,
        40,
        4,
        item=Item.AIR,
        mode=FillMode.REPLACE,
    )
