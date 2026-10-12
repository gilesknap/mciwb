"""
Minecraft Interactive World Builder: build in a Minecraft world from Python.

The main entry point is `Iwb`, which connects to a Minecraft server. The
building blocks (``Vec3``, ``Item``, ``Direction``, ``Volume``, ``polygon``
etc.) come from the mcwb library. These and the classes below can all be
imported from ``mciwb.imports``. :py:mod:`mciwb.builders` has higher level building
blocks: roofs, arches, stairways, foundations and schematic files.

Read and draw regions with ``scan`` and ``render`` from the :py:mod:`mciwb.render`
module (or ``mciwb.imports``). They are not imported here, where a function
called ``render`` would hide the ``mciwb.render`` module.

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""

from . import builders, render
from ._version import __version__
from .backup import Backup
from .blockgrid import BlockGrid
from .copier import CopyPaste
from .iwb import Iwb, get_world
from .monitor import Monitor
from .nbt import parse_nbt
from .palette import Palette
from .player import Player, PlayerNotInWorldError
from .server import MinecraftServer
from .signs import Signs
from .switch import Switch
from .threads import Client, get_client, new_thread, set_client
from .wall import Wall, WallMaker

__all__ = [
    "__version__",
    "Iwb",
    "get_world",
    "Player",
    "PlayerNotInWorldError",
    "CopyPaste",
    "Signs",
    "Wall",
    "WallMaker",
    "Switch",
    "Monitor",
    "Client",
    "get_client",
    "set_client",
    "new_thread",
    "parse_nbt",
    "Backup",
    "MinecraftServer",
    "BlockGrid",
    "Palette",
    "render",
    "builders",
]
