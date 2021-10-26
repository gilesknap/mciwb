from getpass import getpass
from time import sleep
from typing import cast

from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Anchor3, Blocks, Cuboid, Vec3
from mcwb.types import Planes3d

from mciwb.copy import Copy
from mciwb.player import Player

useful_classes = [Player]


# my server ports
science = 20501


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


def bye():
    # I cannot work out how to hook exit when there is a thread running
    # (atexit only calls hooks after all threads are done)
    # we need to tell threads to exit in order to leave gracefully
    global cp
    cp.__del__()
    cp = None
    exit()


def connect():
    passw = getpass(f"Password for mc server at port {science}: ")
    c = Client("localhost", science, passwd=passw)
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
