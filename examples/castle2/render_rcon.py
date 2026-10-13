"""
Render a small region over RCON (at most 32768 blocks), forceloading it
while it reads, for a server whose world files are not on this machine::

    REND="x1 y1 z1 x2 y2 z2" OUT=house.png VIEWS=top,iso mciwb run render_rcon.py
"""

import os
import time

from mciwb.imports import Vec3, get_world

world = get_world()

x1, y1, z1, x2, y2, z2 = (int(v) for v in os.environ["REND"].split())
world.cmd(f"forceload add {x1} {z1} {x2} {z2}")
try:
    while "not loaded" in world.cmd(
        f"execute if block {x1} 0 {z1} minecraft:air"
    ) or "not loaded" in world.cmd(f"execute if block {x2} 0 {z2} minecraft:air"):
        time.sleep(0.5)
    world.render(
        Vec3(x1, y1, z1),
        Vec3(x2, y2, z2),
        os.environ.get("OUT", "r.png"),
        views=os.environ.get("VIEWS", "top,iso").split(","),
    )
finally:
    world.cmd(f"forceload remove {x1} {z1} {x2} {z2}")
