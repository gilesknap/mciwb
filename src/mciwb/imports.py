"""
A module that does all the imports needed in __main__.py and in user modules

This exists to simplify the import process for novice users.

__main__.py: launches iPython and all of the below are available in the shell.
user modules (and modules in demo package) can import everything with

    from mciwb.imports import ... ...
"""

from mcipc.rcon.enumerations import FillMode, Item
from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Anchor3 as Corner
from mcwb import Blocks, Cuboid, Vec3, Volume
from mcwb.api import make_tunnel, polygon
from mcwb.itemlists import grab, load_items, save_items
from mcwb.types import Direction, Planes3d

from mciwb.copier import CopyPaste
from mciwb.iwb import Iwb, world
from mciwb.monitor import Monitor
from mciwb.player import Player
from mciwb.switch import Switch
from mciwb.threads import get_client

imported = [
    Blocks,
    Client,
    CopyPaste,
    Corner,
    Cuboid,
    Direction,
    FillMode,
    Item,
    Iwb,
    Monitor,
    Planes3d,
    Player,
    Switch,
    Vec3,
    Volume,
    get_client,
    grab,
    load_items,
    make_tunnel,
    polygon,
    save_items,
    world,
]
