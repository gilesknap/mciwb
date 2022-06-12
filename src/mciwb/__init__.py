from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Anchor3 as Corner
from mcwb import Blocks, Cuboid
from mcwb import Vec3 as Position
from mcwb.types import Direction, Planes3d

from mciwb.copyblock import Copy
from mciwb.player import Player

try:
    # Use live version from git
    from setuptools_scm import get_version

    # Warning: If the install is nested to the same depth, this will always succeed
    tmp_version = get_version(root="../../", relative_to=__file__)
    del get_version
except (ImportError, LookupError):
    # Use installed version
    from ._version import version as __version__
else:
    __version__ = tmp_version

__all__ = [
    "__version__",
    # TODO: is this the right way to give easy access to classes in
    # user provided functions?
    "Item",
    "Client",
    "Corner",
    "Blocks",
    "Cuboid",
    "Position",
    "Direction",
    "Planes3d",
    "Copy",
    "Player",
]
