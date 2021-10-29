import sys
from getpass import getpass

from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Anchor3, Blocks, Cuboid, Vec3
from mcwb.types import Planes3d
from mciwb.backup import Backup

from mciwb.copy import Copy
from mciwb.player import Player


c: Client


def bye():
    # I cannot work out how to hook exit when there is a thread running
    # (atexit only calls hooks after all threads are done)
    # we need to tell threads to exit in order to leave gracefully
    try:
        global cp
        cp.__del__()
        cp = None
    except Exception:
        pass
    exit()


def connect():
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = 20501

    if len(sys.argv) > 2:
        passw = sys.argv[2]
    else:
        passw = getpass(f"Password for localhost mc server at rcon port {port}: ")

    c = Client("localhost", int(port), passwd=passw)
    c.connect(True)
    print("connected")
    # don't announce every rcon command
    c.gamerule("sendCommandFeedback", False)

    return c


if __name__ == "__main__":
    c = connect()
    zipper = Backup(
        "science",
        "/mnt/bigdisk/mc-servers/science/science/",
        "/mnt/bigdisk/MinecraftQuickBackups",
        c
    )
    cp = Copy(c, "TransformerScorn", zipper)
