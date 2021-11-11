import sys

from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Anchor3, Blocks, Cuboid, Vec3
from mcwb.types import Planes3d

from mciwb.backup import Backup
from mciwb.copy import Copy
from mciwb.player import Player

# these classes pre imported for use in interactive shell
useful_classes = [Item, Anchor3, Blocks, Cuboid, Vec3, Planes3d, Player]
c: Client


def bye():
    # use this to exit instead of "exit"
    # TODO: I cannot work out how to hook ipython exit with a thread running
    # (atexit only calls hooks after all threads are done)

    # we need to tell all threads to exit in order to leave gracefully
    if "cp" in globals():
        global cp
        cp.polling = False
    exit()


def connect():
    port = sys.argv[1] if len(sys.argv) > 1 else 20401
    passwd = sys.argv[2] if len(sys.argv) > 2 else "pass"

    c = Client("localhost", int(port), passwd=passwd)
    c.connect(True)
    print("connected")
    # don't announce every rcon command
    c.gamerule("sendCommandFeedback", False)

    return c


if __name__ == "__main__":
    zipper = Backup(
        "science",
        "/mnt/bigdisk/mc-servers/science/science/",
        "/mnt/bigdisk/MinecraftQuickBackups"
        )
    c = connect()
    cp = Copy(c, "TransformerScorn", None)
    cp.give_signs()
