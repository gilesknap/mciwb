"""
Record what a castle build would do, without a server: run a castle
directory's ``build_castle.py`` (or castle2's ``build_castle2.py``) against a
fake RCON client that answers every command plausibly, and write

- ``OUT.commands``: every command the build sent, in order;
- ``OUT.blocks``: the final block of every cell it set inside the site box
  (simulating setblock and fill, with fill's modes and filters), sorted.

Two builds of the same castle can then be compared with ``diff``: the
refactor of phase 0 must leave castle's blocks exactly as they were::

    python record_build.py ../castle /tmp/before            # castle
    python record_build.py . /tmp/c2 build_castle2          # castle2

Set RECORD_PNG=file.png to render what was built (RECORD_BOX="x1 y1 z1 x2
y2 z2" for part of the site, RECORD_VIEWS=top,iso for the views).

The fake client is fake_client.py's; the ground is a gentle
deterministic slope (``fake_client.ground``); nothing is read
from a real world, so this checks the build's logic, not the terrain.
The environment (ORIGIN, BAILEY_DEPTH ...) is passed through.
"""

from __future__ import annotations

import importlib
import os
import sys
import time
from pathlib import Path

from fake_client import (  # noqa: F401  (ground, dry_run, summon_counts: used by name)
    Recorder,
    World,
    _ints,
    dry_run,
    ground,
    summon_counts,
)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    folder, out = Path(sys.argv[1]).resolve(), sys.argv[2]
    script = sys.argv[3] if len(sys.argv) > 3 else "build_castle"
    sys.path.insert(0, str(folder))
    sys.path.insert(1, str(Path(__file__).parent.parent / "castle"))
    from mciwb.threads import set_client

    # castle2's build sets up the layout: import it before castle_layout
    module = importlib.import_module(script)
    castle_layout = importlib.import_module("castle_layout")

    a, b = castle_layout.site_box()
    world = World(_ints(a), _ints(b))
    rec = Recorder(world)
    set_client(rec)  # type: ignore[arg-type]
    time.sleep = lambda _s: None
    os.environ.setdefault("FORCE", "1")
    module.main()
    Path(f"{out}.commands").write_text("\n".join(rec.commands) + "\n")
    Path(f"{out}.blocks").write_text("\n".join(world.dump()) + "\n")
    print(f"{len(rec.commands)} commands, site {a}..{b}")
    if png := os.environ.get("RECORD_PNG"):
        # RECORD_PNG=file.png [RECORD_BOX="x1 y1 z1 x2 y2 z2"] [RECORD_VIEWS=top,iso]
        from mciwb.render import render

        box = os.environ.get("RECORD_BOX")
        corners = [int(v) for v in box.split()] if box else None
        grid = world.grid(corners[:3], corners[3:]) if corners else world.grid()
        views = os.environ.get("RECORD_VIEWS", "top,iso").split(",")
        render(grid, views).save(png)
        print(f"rendered {png}")


if __name__ == "__main__":
    main()
