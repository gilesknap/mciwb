"""
Render a plan (top) view of a large region over RCON, for a server whose
world files are not on this machine (``mciwb render`` reads at most 32768
blocks over RCON)::

    TOP="550 -200 690 47" OUT=top.png mciwb run top_render.py

It reads the highest block of each column (the WORLD_SURFACE heightmap, then
the block there), two RCON commands per column: about a minute for a castle.
The region is forceloaded while it reads. TOP may add a step (every Nth
column, default 1) and a y range to clip to: ``TOP="x1 z1 x2 z2 step ymin ymax"``
(a column whose top is above ymax is read at ymax, so a roof can be cut off).
"""

from __future__ import annotations

import os
import time

import numpy as np
from mcwb.api import get_block

from mciwb.blockgrid import BlockGrid
from mciwb.imports import Heightmap, Vec3, get_client, ground_heights
from mciwb.render import render


def block_at(client, pos: Vec3):
    """get_block, read again when another RCON client's output got mixed into
    the reply (gilesknap/mciwb#166, item 2; mciwb#170 retries these itself)"""
    for attempt in range(5):
        try:
            return get_block(client, pos)
        except ValueError:
            if attempt == 4:
                raise
    raise AssertionError


def main() -> None:
    values = [int(v) for v in os.environ["TOP"].split()]
    x1, z1, x2, z2 = values[:4]
    step = values[4] if len(values) > 4 else 1
    ymin = values[5] if len(values) > 5 else -64
    ymax = values[6] if len(values) > 6 else 319
    out = os.environ.get("OUT", "top.png")
    client = get_client()
    client.run(f"forceload add {x1} {z1} {x2} {z2}")
    try:
        for x, z in ((x1, z1), (x2, z2)):
            while "not loaded" in client.run(
                f"execute if block {x} 0 {z} minecraft:air"
            ):
                time.sleep(0.5)
        xs, zs = range(x1, x2 + 1, step), range(z1, z2 + 1, step)
        columns = [(x, z) for x in xs for z in zs]
        tops = ground_heights(columns, Heightmap.WORLD_SURFACE)
        lo = max(ymin, min(tops.values()))
        hi = min(ymax, max(tops.values()))
        names = np.full((len(xs), hi - lo + 1, len(zs)), "minecraft:air", dtype=object)
        for i, x in enumerate(xs):
            for k, z in enumerate(zs):
                y = min(tops[(x, z)], hi)
                if y < lo:
                    continue
                block = block_at(client, Vec3(x, y, z))
                if block.value == "minecraft:air" and y > lo:  # cut at ymax: look lower
                    for yy in range(y - 1, lo - 1, -1):
                        block = block_at(client, Vec3(x, yy, z))
                        if block.value != "minecraft:air":
                            y = yy
                            break
                names[i, y - lo, k] = block.value
    finally:
        client.run(f"forceload remove {x1} {z1} {x2} {z2}")
    grid = BlockGrid.from_blocks(names, Vec3(x1, lo, z1))
    if step > 1:  # the labels would be wrong: say so
        print(f"note: every {step}th column; labels count columns, not blocks")
    render(grid, ["top"]).save(out)
    print(f"wrote {out} ({len(columns)} columns, y {lo}..{hi})")


main()
