"""
Read the height of the ground, and build foundations that follow it.

The ground height comes from the server's heightmaps, with
``execute positioned over <heightmap>``: one RCON command per column, which
is much cheaper than reading blocks one at a time. The columns must be in
loaded chunks (near a player, or ``forceload``-ed).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import Enum
from math import floor
from uuid import uuid4

from mcwb import Item, Vec3, Volume

from mciwb.builders.blockstate import Block
from mciwb.builders.placer import BuildError, Placer, rectangles
from mciwb.threads import ReplyCheck, get_client, reply_matches, retry_command

__all__ = ["Heightmap", "foundation", "ground_height", "ground_heights"]


class Heightmap(str, Enum):  # noqa: UP042 - str, like mcwb.Item
    """
    The Minecraft heightmaps: what counts as the ground.
    """

    #: the highest block that is not air (includes plants, snow layers ...)
    WORLD_SURFACE = "world_surface"
    #: the highest block that blocks movement, or holds water or lava
    MOTION_BLOCKING = "motion_blocking"
    #: as MOTION_BLOCKING, but ignoring leaves
    MOTION_BLOCKING_NO_LEAVES = "motion_blocking_no_leaves"
    #: the highest block that blocks movement, e.g. the bed of a lake or the sea
    OCEAN_FLOOR = "ocean_floor"


_teleported = re.compile(r"Teleported \S+ to (-?[\d.]+), (-?[\d.]+), (-?[\d.]+)")


def ground_heights(
    columns: Iterable[tuple[float, float]],
    heightmap: Heightmap | str = Heightmap.MOTION_BLOCKING_NO_LEAVES,
) -> dict[tuple[int, int], int]:
    """
    The y of the top ground block of each of a set of columns.

    Teleports a temporary marker entity to the top of each column, which
    costs one RCON command per column (plus two to make and remove the
    marker).

    :param columns: ``(x, z)`` pairs
    :param heightmap: what counts as the ground, see `Heightmap`
    :returns: the y of the top ground block, keyed by ``(x, z)``. In a column
        with no ground at all (e.g. the void in the End) this is one below
        the bottom of the world
    :raises BuildError: if a column is not in a loaded chunk
    """
    columns = [(floor(x), floor(z)) for x, z in columns]
    if not columns:
        return {}
    heightmap = Heightmap(heightmap).value
    client = get_client()
    tag = f"mciwb_{uuid4().hex[:8]}"
    entity = f"@e[type=minecraft:marker,tag={tag},limit=1]"

    # Every reply is checked and the command sent again if another RCON
    # client garbled it (see mciwb.threads.retry_command). Summoning is not
    # usually safe to repeat, but here a second marker does no harm: tp picks
    # one of them, and kill removes them all.
    x, z = columns[0]
    summon = f'summon minecraft:marker {x} 0 {z} {{Tags:["{tag}"]}}'
    result = retry_command(
        lambda: client.run(summon), reply_matches(r"Summoned new \S+"), summon
    )
    if not result.startswith("Summoned"):
        raise BuildError(f"could not summon a marker at {x} 0 {z}: {result}")
    heights = {}
    try:
        for x, z in columns:
            command = (
                f"execute positioned {x} 0 {z} positioned over {heightmap} "
                f"run tp {entity} ~ ~ ~"
            )
            result = retry_command(
                lambda command=command: client.run(command),
                _teleported_to(x, z),
                command,
            )
            match = _teleported.match(result)
            if not match:
                raise BuildError(f"could not read the ground at {x}, {z}: {result!r}")
            # the heightmap is the first block above the ground
            heights[(x, z)] = round(float(match.group(2))) - 1
    finally:
        client.run(f"kill @e[type=minecraft:marker,tag={tag}]")
    return heights


def _teleported_to(x: int, z: int) -> ReplyCheck:
    """
    A check for the reply to teleporting the marker to column x, z. It must
    name the column, so that another client's tp reply is not taken for ours
    """

    def check(reply: str) -> str | None:
        for match in _teleported.finditer(reply):
            if (floor(float(match.group(1))), floor(float(match.group(3)))) == (x, z):
                return match.group(0)
        return None

    return check


def ground_height(
    x: float, z: float, heightmap: Heightmap | str = Heightmap.MOTION_BLOCKING_NO_LEAVES
) -> int:
    """
    The y of the top ground block at ``(x, z)``, see `ground_heights`.
    """
    return ground_heights([(x, z)], heightmap)[(floor(x), floor(z))]


def foundation(
    start: Vec3,
    end: Vec3,
    block: Block = Item.COBBLESTONE,
    *,
    heightmap: Heightmap | str = Heightmap.OCEAN_FLOOR,
    max_depth: int = 64,
) -> Volume:
    """
    A foundation that follows the terrain: fill each column of a rectangular
    footprint from the ground up to ``start.y``, giving a level platform at
    ``start.y`` to build on (at ``start.y + 1``).

    Build the foundation before anything above it: the ground height is the
    top of the highest block in each column, so a building already standing
    there would count as the ground. Columns where the ground is higher than
    ``start.y`` just get the top layer (replacing the ground there).

    :param start: a corner of the footprint, at the height of the top of the
        foundation
    :param end: the opposite corner of the footprint (only x and z are used)
    :param block: the block to build the foundation from
    :param heightmap: what counts as the ground. The default ignores water,
        so the foundation goes down to the bed of a lake or the sea
    :param max_depth: the deepest any column may go, in blocks below
        ``start.y`` (a guard against building down into a ravine or the
        void). 0 gives just the top layer
    :returns: the bounding box of the foundation
    """
    if max_depth < 0:
        raise ValueError(f"max_depth must not be negative, not {max_depth}")
    top = int(start.y)
    x1, x2 = sorted((int(start.x), int(end.x)))
    z1, z2 = sorted((int(start.z), int(end.z)))
    columns = [(x, z) for z in range(z1, z2 + 1) for x in range(x1, x2 + 1)]
    ground = ground_heights(columns, heightmap)

    # the bottom of the foundation in each column, then group the columns
    # with the same bottom into rectangles
    lowest = top - max_depth
    bottoms: dict[int, list[tuple[int, int]]] = {}
    for column, y in ground.items():
        bottom = min(max(y + 1, lowest), top)
        bottoms.setdefault(bottom, []).append(column)

    placer = Placer()
    for bottom, cells in sorted(bottoms.items()):
        for ax, az, bx, bz in rectangles(cells):
            placer.fill(Vec3(ax, bottom, az), Vec3(bx, top, bz), block)
    return placer.volume
