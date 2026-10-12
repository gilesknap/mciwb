"""
Higher level building blocks: roofs, arches, columns, stairways, roads and
foundations that follow the terrain.

They all build with the RCON client of the current thread (``get_client``),
take ``Vec3`` positions and blocks as ``Item``, block state strings or
`BlockState`, and return the bounding box (a ``Volume``) of the blocks they
placed, ready to ``grab``, save or clear. A server error (e.g. an unknown block,
or a position in an unloaded chunk) raises `BuildError`.

Coordinates follow Minecraft: Y is up, north is -z, east is +x.
"""

from mciwb.builders.arches import arch, arch_profile, column
from mciwb.builders.blockstate import (
    Block,
    BlockState,
    facing_name,
    full_block_of,
    slab_of,
    stair_shapes,
)
from mciwb.builders.paths import PathStep, road, stairway, trace_path
from mciwb.builders.placer import BuildError, Placer
from mciwb.builders.roofs import flat_roof, gable_roof, hip_roof
from mciwb.builders.terrain import (
    Heightmap,
    foundation,
    ground_height,
    ground_heights,
)

__all__ = [
    "Block",
    "BlockState",
    "BuildError",
    "Heightmap",
    "PathStep",
    "Placer",
    "arch",
    "arch_profile",
    "column",
    "facing_name",
    "flat_roof",
    "foundation",
    "full_block_of",
    "gable_roof",
    "ground_height",
    "ground_heights",
    "hip_roof",
    "road",
    "slab_of",
    "stair_shapes",
    "stairway",
    "trace_path",
]
