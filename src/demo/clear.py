from mciwb.imports import FillMode, Item, Vec3, get_client, polygon


def clear():
    polygon(
        get_client(),
        Vec3(x=640, y=71, z=-1635),
        height=200,
        diameter=65,
        item=Item.AIR,
        mode=FillMode.REPLACE,
    )
