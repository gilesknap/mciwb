"""
The re-site of The Drowned Station: what a build must take away when the
ring changes under a station already built in the world, and what must be
taken away before a rollback to the ring before.

Round 3 grew the ring from eight domes to ten (`PREVIOUS_RING` is the
eight): the Cargo Hold and Hull Breach stand where the Flooded Dome and the
Foundry stood, and those two moved a column east. Every tunnel of the
eight but one runs where a tunnel of the ten runs; the one that does not
is the eight's tunnel 3, from the Flooded Dome south to the Foundry.

Two stages (build_station.py):

- ``resite``, in the full build after ``rules`` and before any dome: puts
  the sea back where a tunnel of the previous ring ran and no tunnel of
  this ring runs (`former_tunnels`), and where a dome of the previous ring
  stood and none of this ring stands (`former_domes`; none for round 3),
  then carves the craters round the domes dug deep into the sea floor
  and the trenches along their tunnels (`carve`; seabed.py, "the
  craters": for round 3 the moved Flooded Dome and Foundry, and tunnels
  3, 4 and 5), so that their glass looks out on water, not ground. The
  carving is plain fills of water and sand, so a rerun puts the craters
  back as they were and takes away the sea floor's dressing in them:
  run ``seabed`` after it, as the full build does.
  A dome of the previous ring where one of this ring stands (the same
  centre, size and floor) is left to that dome's shell stage, which
  rebuilds it whole; the old module's entities there go when that module
  is built again at its new place (each kills its own tag), and the
  automatons with the game's reset.
- ``rollback``, run only when named in ``STAGES`` (``MANUAL_STAGES``), on
  this branch, before a full build of the previous ring from its own
  branch: puts the sea back where this ring has a dome or a tunnel that
  the previous ring has not (`new_domes`, `new_tunnels`), kills every
  entity but players in those domes and in the domes whose key changed
  (the previous ring's shell stage there does not), fills the craters
  with sand up to the surveyed floor, takes away the sea floor's
  dressing but the seagrass (the previous ring's ``seabed`` stage
  dresses its own box again), and stops forceloading the chunks outside the previous
  ring's box. The water's biome outside that box stays a warm ocean.

**Putting the sea back** (`sea_back`) trusts the survey, as the seabed
does: a cell above the surveyed sea floor becomes water, a cell at or
below it sand (what the ground was is not known). A tunnel's cells are put
back only where they hold what a tunnel is built of (`TUBE`), so the stage
is the same run twice and takes nothing that the ``seabed`` stage placed
since; its piers become water again (a pier stands only where the ground
was not). A dome's cells are put back whatever they hold, and its
foundation becomes water again.
"""

from __future__ import annotations

from typing import Any

import domes
import seabed
import station_layout as layout
import tunnels
from station_layout import Dome, Tunnel

#: the ring before round 3 (``examples/station-2``), as `layout.RING`
PREVIOUS_RING: tuple[tuple[str, str, tuple[int, int], int, int], ...] = (
    ("start", "The Pump House", (0, 0), 48, 0),
    ("boiler", "Boiler Room", (66, 0), 32, 0),
    ("gearworks", "Gearworks", (136, 0), 48, 0),
    ("flooded", "Flooded Dome", (208, 0), 48, 0),
    ("foundry", "Foundry", (208, -80), 48, 0),
    ("signal", "Signal Room", (144, -80), 32, 0),
    ("maze", "Clockwork Maze", (80, -80), 48, 0),
    ("boss", "The Engine", (0, -80), 64, 8),
)
PREVIOUS_DOMES = layout.make_domes(ring=PREVIOUS_RING)
PREVIOUS_TUNNELS = layout.make_tunnels(PREVIOUS_DOMES)

WATER, SAND = tunnels.WATER, seabed.SAND
#: what a tunnel is built of: what `unbuild_tunnel` puts back
TUBE = (
    domes.GLASS,
    tunnels.FLOOR,
    tunnels.LAMP,
    tunnels.LAMP_DIM,
    tunnels.STAIRS,
    WATER,
    domes.AIR,
)


def same_place(d: Dome, e: Dome) -> bool:
    return (d.centre, d.diameter, d.floor_y) == (e.centre, e.diameter, e.floor_y)


def at_place(dome: Dome, ring: tuple[Dome, ...]) -> Dome | None:
    """the dome of a ring that stands where a dome stands, if any"""
    return next((d for d in ring if same_place(d, dome)), None)


def _route(t: Tunnel) -> frozenset:
    return frozenset((t.a, t.b))


def former_tunnels() -> list[Tunnel]:
    """
    The tunnels of the previous ring that run where no tunnel of this ring
    runs, each as a tunnel between this ring's domes at its ends (so that
    its cells leave theirs alone)

    :raises ValueError: if a dome at its end is not in this ring
    """
    routes = {_route(t) for t in layout.TUNNELS}
    out = []
    for t in PREVIOUS_TUNNELS:
        if _route(t) in routes:
            continue
        a = at_place(PREVIOUS_DOMES[t.start], layout.DOMES)
        b = at_place(PREVIOUS_DOMES[t.end], layout.DOMES)
        if a is None or b is None:
            raise ValueError(f"the previous tunnel {t.index} ends at a dome gone")
        out.append(layout.tunnel_between(t.index, a, b))
    return out


def former_domes() -> list[Dome]:
    """the domes of the previous ring where no dome of this ring stands"""
    return [d for d in PREVIOUS_DOMES if at_place(d, layout.DOMES) is None]


def new_tunnels() -> list[Tunnel]:
    """the tunnels of this ring that run where no previous tunnel ran"""
    routes = {_route(t) for t in PREVIOUS_TUNNELS}
    return [t for t in layout.TUNNELS if _route(t) not in routes]


def new_domes() -> list[Dome]:
    """the domes of this ring where no dome of the previous ring stood"""
    return [d for d in layout.DOMES if at_place(d, PREVIOUS_DOMES) is None]


def renamed_domes() -> list[Dome]:
    """the domes of this ring where a previous dome with another key stood"""
    return [
        d
        for d in layout.DOMES
        if (e := at_place(d, PREVIOUS_DOMES)) is not None and e.key != d.key
    ]


def previous_chunks() -> set[tuple[int, int]]:
    """the chunks of the previous ring's box (as `layout.station_bounds`)"""
    m, ds = layout.MARGIN, PREVIOUS_DOMES
    x1 = min(d.centre[0] - d.radius for d in ds) - m
    x2 = max(d.centre[0] + d.radius for d in ds) + m
    z1 = min(d.centre[1] - d.radius for d in ds) - m
    z2 = max(d.centre[1] + d.radius for d in ds) + m
    return {
        (cx, cz)
        for cx in range(x1 >> 4, (x2 >> 4) + 1)
        for cz in range(z1 >> 4, (z2 >> 4) + 1)
    }


# ----------------------------------------------------------------- the stages


def sea_back(ctx: Any, cells, kinds: tuple[str, ...] | None = None) -> None:
    """
    the sea put back in cells: water above the surveyed sea floor, sand at
    or below it; only over the blocks named in ``kinds``, if given
    """
    where = seabed.site()
    wet = {c for c in cells if c[1] > where.surveyed_at(c[0], c[2])}
    for part, block in ((wet, WATER), (set(cells) - wet, SAND)):
        for a, b in domes.boxes(part):
            if kinds is None:
                ctx.fill(a, b, block)
            for kind in kinds or ():
                if kind != block:
                    ctx.fill(a, b, block, f"replace {kind}")


def unbuild_tunnel(ctx: Any, tunnel: Tunnel) -> None:
    """a tunnel's tube and piers taken away (not its doors: the domes')"""
    cells = tunnels.tunnel_cells(tunnel)
    sea_back(ctx, cells.ring | cells.floor | cells.inside | set(cells.stairs), TUBE)
    for x, y, z in sorted(cells.piers):
        a, b = (x, y - domes.FOUNDATION_DEPTH, z), (x, y, z)
        ctx.fill(a, b, WATER, f"replace {tunnels.PIER}")


def unbuild_dome(ctx: Any, dome: Dome) -> None:
    """a dome and everything in it taken away, and its foundation"""
    ctx.cmd(f"kill @e[type=!minecraft:player,{domes.sphere(dome)}]")
    sea_back(ctx, domes.dome_cells(dome).all)
    for a, b in domes.foundation_boxes(dome):
        ctx.fill(a, b, WATER, f"replace {domes.FOUNDATION}")
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")


def carve(ctx: Any) -> tuple[int, int]:
    """the craters carved (``seabed.crater_cells``): the ground cut away
    to water, sand at the bottom. How many cells of each"""
    water, bed = seabed.crater_cells()
    ctx.fill_boxes(water, WATER)
    ctx.fill_boxes(bed, SAND)
    return len(water), len(bed)


def resite(ctx: Any) -> str:
    """the ``resite`` stage: the previous ring's tunnels and domes that
    this ring has not, taken away, and the craters carved"""
    gone_t, gone_d = former_tunnels(), former_domes()
    for t in gone_t:
        unbuild_tunnel(ctx, t)
    for d in gone_d:
        unbuild_dome(ctx, d)
    water, bed = carve(ctx)
    ctx.advance(10)
    told = [f"tunnel {t.a} to {t.b}" for t in gone_t] + [d.name for d in gone_d]
    return (
        f"the sea put back where the previous ring had "
        f"{', '.join(told) or 'nothing more'}; craters carved: {water} cells "
        f"of ground to water, {bed} of sand at the bottom"
    )


def rollback(ctx: Any) -> str:
    """the ``rollback`` stage: what this ring has that the previous has not
    taken away, for a build of the previous ring to follow"""
    for d in renamed_domes():
        ctx.cmd(f"kill @e[type=!minecraft:player,{domes.sphere(d)}]")
    for t in new_tunnels():
        unbuild_tunnel(ctx, t)
    for d in new_domes():
        unbuild_dome(ctx, d)
    for a, b in seabed.clear_boxes():
        for what, with_ in seabed.CLEAR:
            ctx.fill(a, b, with_, f"replace {what}")
    # the craters filled again, to the surveyed floor
    ctx.fill_boxes(seabed.crater_cells()[0], SAND)
    (cx1, cz1), (cx2, cz2) = layout.station_chunks()
    extra = {
        (cx, cz) for cx in range(cx1, cx2 + 1) for cz in range(cz1, cz2 + 1)
    } - previous_chunks()
    for cz in sorted({cz for _, cz in extra}):
        row = sorted(cx for cx, z in extra if z == cz)
        runs: list[list[int]] = []
        for cx in row:
            if runs and runs[-1][1] == cx - 1:
                runs[-1][1] = cx
            else:
                runs.append([cx, cx])
        for first, last in runs:
            ctx.cmd(f"forceload remove {first * 16} {cz * 16} {last * 16} {cz * 16}")
    ctx.advance(10)
    return (
        f"taken away: tunnels {[t.index for t in new_tunnels()]}, domes "
        f"{[d.name for d in new_domes()]}, the sea floor's dressing, the "
        "craters (filled with sand); entities "
        f"killed in {[d.name for d in renamed_domes()]}; {len(extra)} chunks no "
        "longer forceloaded. Now build the previous ring from its own branch"
    )
