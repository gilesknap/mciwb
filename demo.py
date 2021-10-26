from typing import cast
from time import sleep

from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Anchor3, Blocks, Cuboid, Vec3
from mcwb.types import Planes3d
from mciwb.copy import Copy

from mciwb.player import Player

useful_classes = [Player]

# my server ports
science = 20501, "spider"
quest = 25575
flat = 25901
docker = 20201, "spider"
docker2 = 30351, "CHANGEME!"


def setup(client):
    # don't announce every rcon command
    client.gamerule("sendCommandFeedback", False)


def funky_cube(size: int) -> Cuboid:
    half = int(size / 2)
    size = 2 * half

    left = [Item.RED_CONCRETE] * size
    right = [Item.GREEN_CONCRETE] * size
    row = [Item.BLUE_CONCRETE] + [Item.AIR] * (size - 2) + [Item.YELLOW_CONCRETE]
    square = [left] + [row] * (size - 2) + [right]

    top = [
        [Item.WHITE_CONCRETE, Item.GRAY_CONCRETE] * half,
        [Item.GRAY_CONCRETE, Item.WHITE_CONCRETE] * half,
    ] * half
    bottom = [[Item.BLACK_CONCRETE, Item.GRAY_CONCRETE] * half] * size

    return cast(Cuboid, [top] + [square] * (size - 2) + [bottom])


c: Client


def connect():
    port, passw = science
    c = Client("localhost", port, passwd=passw)
    c.connect(True)
    print("connected")
    # don't announce every rcon command
    c.gamerule("sendCommandFeedback", False)

    return c


if __name__ == "__main__":
    c = connect()
    p = Player(c, "TransformerScorn")
    cp = Copy(c, "TransformerScorn")

    pos = Vec3(0, 150, -40)
    cube = funky_cube(30)
    anchor = Anchor3.BOTTOM_MIDDLE

    fun_cube = Blocks(c, pos, cube, anchor=anchor)

    plane = Planes3d.XZ
    fun_cube.rotate(plane)
