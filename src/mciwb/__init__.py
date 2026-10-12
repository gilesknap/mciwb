"""
Minecraft Interactive World Builder: build in a Minecraft world from Python.

The main entry point is `Iwb`, which connects to a Minecraft server. The
building blocks (`Vec3`, `Item`, `Direction`, `Volume`, `polygon` etc.) come
from the mcwb library, and are all available from `mciwb.imports`.

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""

from ._version import __version__
from .backup import Backup
from .copier import CopyPaste
from .iwb import Iwb, get_world
from .monitor import Monitor
from .nbt import parse_nbt
from .player import Player, PlayerNotInWorldError
from .server import MinecraftServer
from .signs import Signs
from .switch import Switch
from .threads import get_client, new_thread, set_client
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
    "get_client",
    "set_client",
    "new_thread",
    "parse_nbt",
    "Backup",
    "MinecraftServer",
]
