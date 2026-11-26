"""
The glass domes of The Drowned Station: the cells of a dome (pure functions
of the layout, shared by the build, the datapack and the checks), the build
of a dome's empty shell, and the checks that it is dry and whole.

**What a dome is** (``dome_cells(dome)``; all positions come from the
layout's ``Dome``):

- A half ball of cells within ``radius + 0.5`` of the floor's centre block,
  so it spans ``centre +- radius`` and its top is at ``floor_y + radius``.
- ``floor``: the whole disc at ``y = floor_y``. Players stand on it, feet
  at ``floor_y + 1``. It is ``FLOOR`` with a grid of ``LIGHT`` set in it.
  An interior may relay it with any full, solid block (never a waterlogged
  one), but must leave the outer ring solid.
- ``shell``: the cells above the floor with a face on the sea. Glass, with
  ``LIGHT`` dotted over it. Not to be changed, except through an opening.
- ``interior``: everything else, air after the build. This is the room an
  interior has to itself, except the reserved cells below.

**Openings.** Where a tunnel of the layout meets the shell there is a
mouth, ``DOOR_HALF_WIDTH * 2 + 1`` wide and ``DOOR_HEIGHT`` high, standing
on the floor: ``door_cells(dome, tunnel)``. The dome's build plugs each
mouth with a brass door with a glass window in it (``door_blocks``: the
window is 3 wide and 3 high, a full block of glass like the shell's, so
it holds the sea as the brass does), framed in ``FRAME``; a built
tunnel's functions open and close it (tunnels.py), and the mouth of a
tunnel not built yet stays plugged, so a dome is watertight by itself.
``openings(dome)`` gives the mouths by tunnel index. A module that cuts the
shell anywhere else (the lift's shaft through the top) calls
``add_opening(dome_index, cells)`` when it is imported, so that the check
for holes leaves those cells to that module's own check. A module whose
dome holds water on purpose registers those cells with
``add_wet(dome_index, cells)`` in the same way, and the wet check counts
water everywhere in the dome but there.

**Reserved inside a dome** (keep clear; ``reserved_cells(dome)`` in
tunnels.py gives them all):

- the two cells above ``entrance(dome)``, where a player is put by the
  recall and on respawn: for the start dome ``ENTRANCE_OFFSET`` blocks from
  the centre towards its outgoing tunnel, for the others that far inside
  the mouth of the tunnel they are reached by;
- a clear way from each mouth, as wide and high as the mouth, 3 deep;
- the pump engine beside the outgoing mouth (``tunnels.engine_cells``).

**Dressing a dome** (walkways, pipes, machinery that runs by itself). The
rules that keep it out of the way of the game:

- Build only in ``dome_cells(dome).interior`` less
  ``tunnels.reserved_cells(dome)`` and less what the dome's own module
  uses (``fittings.placement_problems`` checks the first two). The way in
  from a mouth is what a player watches the pump event through: nothing
  may stand in it, and nothing taller than a player's waist just beyond
  it on the line from the entrance to the outgoing door's window.
- Nothing waterlogged, and no water or lava: the wet check counts any,
  but in cells a module has registered with ``add_wet``.
- A room that must break one of these rules says so by name with
  ``allow(dome_index, name, why)``; rooms.py has the offline checks of
  them (``room_problems``, ``walk_problems``, ``sight_problems``,
  ``window_problems``, ``input_problems``).
- The floor may be relaid; the shell, the mouths and their frames may not.
- A machine that only decorates is built by the dome's ``_inside`` stage
  and is left alone by every ``reset`` function (which puts back only
  what play changes), so it must run by itself from the moment it is
  built: a torch or observer clock, copper bulbs, pistons. Give it no
  lever, button, plate or other thing a player can work, and none of the
  blocks the dome's puzzle reads; put no item or entity in it that a
  reset's ``kill`` by position or tag would take.
- Positions with a fraction (entities, particles, sounds, selectors) come
  from ``middle(cell)``, never from ``f"{x}.5"``, which is a block off
  where x is negative.

**The build** (``build_shell``) is the method the rig proved
(rig_mechanisms.py check 3): the ground under the floor is filled with
``FOUNDATION`` wherever it is water, air or plants, ``FOUNDATION_DEPTH``
down, so no part of a floor hangs over a ravine; the whole dome is made
solid glass, which also replaces any sea floor a dug-in dome stands in;
then the floor is laid and the inside hollowed to air. Nothing is ever
cleared of water row by row. The kelp the shell cuts drops items: they are
killed. Run twice it gives the same dome, and it wipes whatever was inside
(an interior, and the pump engines: run the interior's stage and
``tunnels`` again after it).

**The checks** are functions of the datapack, since only a function can
look at tens of thousands of cells (``add_check_functions``):
``station:check/dome/<n>/wet_<part>`` adds to ``#wet`` (objective
``st.chk``) one for every interior or mouth cell that holds water or a
waterlogged block (the rig's predicate), and ``.../holes`` adds to
``#holes`` one for every shell or floor cell that is air or wet (mouths of
built tunnels and registered openings left out), and to ``#under`` one for
every cell under the floor that nothing solid fills. Each adds one to
``#ran`` as its last line. ``check_shell`` runs them over RCON.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache, cached_property
from typing import TYPE_CHECKING, Any

import datapack as dp
import station_layout as layout

if TYPE_CHECKING:
    from station_layout import Dome, Tunnel

Cell = tuple[int, int, int]

GLASS = "minecraft:glass"
AIR = "minecraft:air"
FLOOR = "minecraft:polished_deepslate"
LIGHT = "minecraft:sea_lantern"
FOUNDATION = "minecraft:deepslate"
FRAME = "minecraft:waxed_cut_copper"
#: what is not ground under a floor: water, air, lava and small plants
#: (the block tag), and kelp, which the tag leaves out
NOT_GROUND = ("#minecraft:replaceable", "minecraft:kelp", "minecraft:kelp_plant")
#: how far under a floor the foundation goes (the survey's ravines reach
#: 23 below the floors)
FOUNDATION_DEPTH = 24
#: lanterns in the floor every this many blocks each way, and over the shell
FLOOR_LIGHTS, SHELL_LIGHTS = 6, 8

#: a mouth is 5 wide and 4 high: the inside of a tunnel
DOOR_HALF_WIDTH, DOOR_HEIGHT = 2, 4
#: how far the entrance spot is from the centre (start dome) or inside the
#: mouth (the others)
ENTRANCE_OFFSET = 5

#: the rig's predicate: water or a waterlogged block at a place
WET = '{type:"minecraft:location_check",predicate:{fluid:{fluids:"#minecraft:water"}}}'
CHECK_OBJECTIVE = "st.chk"
#: cells a check function looks at, at most (a function runs 65536 commands)
CHECK_PART = 30000

#: the domes whose shells are built: all of the ring
BUILT = tuple(d.index for d in layout.DOMES)

COMPASS = {(0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west"}

#: cells inside a dome that are meant to hold water: dome index -> cells
WET_OK: dict[int, set[Cell]] = {}


#: what a dome's room does against the rules for dressing, on purpose:
#: dome index -> {name: why}
ALLOWED: dict[int, dict[str, str]] = {}


def allow(index: int, name: str, why: str) -> None:
    """register a named exception to the rules for dressing a dome (when
    the module is imported): the Flooded Dome's dam and the Engine's
    pavilion stand between the entrance and the outgoing door's window on
    purpose. ``rooms.window_problems`` then passes that dome, and the
    exception is listed with the checks"""
    ALLOWED.setdefault(index, {})[name] = why


def add_wet(index: int, cells) -> None:
    """register cells inside dome ``index`` that hold water on purpose (the
    Flooded Dome's pool), when the module is imported: the wet check then
    leaves them to that module's own check, and still counts water
    anywhere else in the dome"""
    WET_OK.setdefault(index, set()).update(cells)


#: cells of a dome's shell that another module has cut: dome index -> cells
OPENINGS: dict[int, set[Cell]] = {}


def add_opening(index: int, cells: set[Cell]) -> None:
    """register cells of dome ``index``'s shell (or floor) that a module
    opens itself, so that the check for holes skips them"""
    OPENINGS.setdefault(index, set()).update(cells)


# ----------------------------------------------------------------------- cells


@dataclass(frozen=True)
class DomeCells:
    shell: frozenset[Cell]
    interior: frozenset[Cell]
    floor: frozenset[Cell]

    @cached_property
    def all(self) -> frozenset[Cell]:
        return self.shell | self.interior | self.floor


@cache
def dome_cells(dome: Dome) -> DomeCells:
    """a dome's glass shell, the cells inside it and its floor (see the
    module docstring)"""
    r = dome.radius
    limit = (r + 0.5) ** 2
    inside = {
        (dx, dy, dz)
        for dx in range(-r, r + 1)
        for dz in range(-r, r + 1)
        for dy in range(r + 1)
        if dx * dx + dy * dy + dz * dz <= limit
    }
    # water passes through faces only, so a shell cell is one with a face
    # (sideways or up) on the outside
    faces = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)]
    shell = {
        c
        for c in inside
        if c[1] > 0
        and any((c[0] + f[0], c[1] + f[1], c[2] + f[2]) not in inside for f in faces)
    }
    ox, oy, oz = dome.floor_centre

    def world(cells) -> frozenset[Cell]:
        return frozenset((ox + x, oy + y, oz + z) for x, y, z in cells)

    floor = {c for c in inside if c[1] == 0}
    return DomeCells(world(shell), world(inside - shell - floor), world(floor))


def outward(dome: Dome, tunnel: Tunnel) -> tuple[int, int]:
    """the unit step (x, z) from a dome's centre towards a tunnel that
    leaves it or arrives at it"""
    sx, sz = tunnel.step
    if tunnel.start == dome.index:
        return (sx, sz)
    if tunnel.end == dome.index:
        return (-sx, -sz)
    raise ValueError(f"tunnel {tunnel.index} does not touch dome {dome.key}")


def across(step: tuple[int, int]) -> tuple[int, int]:
    """the unit step (x, z) to the right of a step, seen from above with
    north up: the direction a mouth's width runs in"""
    return (-step[1], step[0])


@cache
def door_cells(dome: Dome, tunnel: Tunnel) -> tuple[tuple[int, Cell], ...]:
    """
    The mouth where a tunnel meets a dome: the cells of the shell that lie
    in the tunnel's way, each with its place across the mouth (-2 .. 2, 0
    the middle). Where the shell curves, the mouth is more than one cell
    thick.
    """
    cells = dome_cells(dome)
    ux, uz = outward(dome, tunnel)
    ax, az = across((ux, uz))
    ox, oy, oz = dome.floor_centre
    found = []
    for w in range(-DOOR_HALF_WIDTH, DOOR_HALF_WIDTH + 1):
        for h in range(1, DOOR_HEIGHT + 1):
            for s in range(dome.radius, 0, -1):
                cell = (ox + s * ux + w * ax, oy + h, oz + s * uz + w * az)
                if cell in cells.interior:
                    break
                if cell in cells.shell:
                    found.append((w, cell))
    return tuple(found)


def touching(dome: Dome) -> list[Tunnel]:
    """the tunnels of the layout that leave a dome or arrive at it"""
    return [t for t in layout.TUNNELS if dome.index in (t.start, t.end)]


def openings(dome: Dome) -> dict[int, frozenset[Cell]]:
    """a dome's mouths: tunnel index -> the cells of the shell in it"""
    return {
        t.index: frozenset(c for _, c in door_cells(dome, t)) for t in touching(dome)
    }


def door_block(w: int, h: int) -> str:
    """the block of a closed door, by its place across the mouth (-2 .. 2)
    and its height above the floor (1 .. 4): heavy brass (gold) down both
    sides and along the sill, with a copper boss in the middle of the
    sill, and above it a window of glass, 3 by 3"""
    if abs(w) < DOOR_HALF_WIDTH and h > 1:
        return GLASS
    return "minecraft:waxed_chiseled_copper" if w == 0 else "minecraft:gold_block"


def door_blocks(dome: Dome, tunnel: Tunnel) -> dict[Cell, str]:
    """a mouth's closed door: cell -> block"""
    return {
        cell: door_block(w, cell[1] - dome.floor_y)
        for w, cell in door_cells(dome, tunnel)
    }


def middle(cell: Cell, up: float = 0) -> str:
    """the middle of a cell, ``up`` above its bottom, as the ``x y z`` of a
    command. (Not ``f"{x}.5"``: for a negative x that is the middle of the
    cell before it.)"""
    return f"{cell[0] + 0.5} {cell[1] + up} {cell[2] + 0.5}"


def by_block(blocks: dict[Cell, str]) -> dict[str, set[Cell]]:
    """cell -> block turned round: block -> its cells"""
    out: dict[str, set[Cell]] = {}
    for cell, block in blocks.items():
        out.setdefault(block, set()).add(cell)
    return out


@cache
def frame_cells(dome: Dome, tunnel: Tunnel) -> frozenset[Cell]:
    """the cells of the shell and floor round a mouth"""
    cells = dome_cells(dome)
    doors = {c for _, c in door_cells(dome, tunnel)}
    ax, az = across(outward(dome, tunnel))
    ring = {
        (x + w * ax, y + h, z + w * az)
        for x, y, z in doors
        for w in (-1, 0, 1)
        for h in (-1, 0, 1)
    }
    return frozenset((ring & (cells.shell | cells.floor)) - doors)


def facing(dome: Dome) -> tuple[int, int]:
    """the unit step (x, z) a player faces at a dome's entrance: into the
    dome, away from the mouth they came by (the start dome: towards its
    outgoing tunnel)"""
    if dome.index == 0:
        return outward(dome, layout.TUNNELS[0])
    ux, uz = outward(dome, layout.TUNNELS[dome.index - 1])
    return (-ux, -uz)


def entrance(dome: Dome) -> tuple[int, int, int, int]:
    """
    Where a player is put in a dome (recall, respawn): the x, y, z of the
    feet and the yaw, facing into the dome. The start dome's is beside the
    lift, towards its outgoing tunnel; another dome's is just inside the
    mouth of the tunnel it is reached by.
    """
    ox, oy, oz = dome.floor_centre
    if dome.index == 0:
        ux, uz = outward(dome, layout.TUNNELS[0])
        s = ENTRANCE_OFFSET
        face = (ux, uz)
    else:
        ux, uz = outward(dome, layout.TUNNELS[dome.index - 1])
        s = dome.radius - ENTRANCE_OFFSET
        face = (-ux, -uz)
    yaw = {(0, 1): 0, (-1, 0): 90, (0, -1): 180, (1, 0): -90}[face]
    return (ox + s * ux, oy + 1, oz + s * uz, yaw)


def sphere(dome: Dome) -> str:
    """selector arguments for what is in a dome: within its radius of the
    middle of its floor, the shell and the mouths included"""
    x, y, z = dome.floor_centre
    return f"x={x + 0.5},y={y},z={z + 0.5},distance=..{dome.radius + 1}"


def box(dome: Dome) -> tuple[Cell, Cell]:
    """the corners of the box round a dome, floor to top"""
    x, y, z = dome.floor_centre
    r = dome.radius
    return (x - r, y, z - r), (x + r, y + r, z + r)


def light_cells(dome: Dome) -> tuple[set[Cell], set[Cell]]:
    """the lanterns: those set in the floor and those in the shell"""
    cells = dome_cells(dome)
    ox, _, oz = dome.floor_centre
    doors = set().union(*openings(dome).values())
    frames = set().union(*(frame_cells(dome, t) for t in touching(dome)))

    def on_grid(c: Cell, step: int) -> bool:
        return (c[0] - ox) % step == 0 and (c[2] - oz) % step == 0

    floor = {c for c in cells.floor if on_grid(c, FLOOR_LIGHTS)} - frames
    shell = {c for c in cells.shell if on_grid(c, SHELL_LIGHTS)} - doors - frames
    return floor, shell


def light_probes(dome: Dome) -> list[Cell]:
    """places at head height to read the light at: the middle of the dome
    and eight points two thirds of the way out"""
    x, y, z = dome.floor_centre
    d = dome.radius * 2 // 3
    e = d * 7 // 10
    offsets = [(0, 0), (d, 0), (-d, 0), (0, d), (0, -d)]
    offsets += [(e, e), (e, -e), (-e, e), (-e, -e)]
    return [(x + dx, y + 2, z + dz) for dx, dz in offsets]


def runs(cells) -> list[tuple[Cell, Cell]]:
    """cells as rows along x: (first, last) of each unbroken row"""
    out = []
    rows: dict[tuple[int, int], list[int]] = {}
    for x, y, z in cells:
        rows.setdefault((y, z), []).append(x)
    for (y, z), xs in sorted(rows.items()):
        xs.sort()
        start = prev = xs[0]
        for x in xs[1:]:
            if x != prev + 1:
                out.append(((start, y, z), (prev, y, z)))
                start = x
            prev = x
        out.append(((start, y, z), (prev, y, z)))
    return out


def boxes(cells) -> list[tuple[Cell, Cell]]:
    """cells as boxes (low corner, high corner): rows along x, joined
    across z and then up y where they match, none bigger than a ``fill``
    takes. Far fewer than the rows for anything box-like"""
    merged: list[tuple[Cell, Cell]] = []
    for axis in (2, 1):
        flat = merged if axis == 1 else runs(cells)
        merged = []
        open_: dict[tuple, tuple[Cell, Cell]] = {}
        for a, b in sorted(flat, key=lambda r: (r[0][axis], r[0])):
            # the part of a box that must match for two to join along axis
            key = tuple(v for i, v in enumerate(a + b) if i % 3 != axis)
            last = open_.get(key)
            if (
                last
                and last[1][axis] == a[axis] - 1
                and dp.fill_volume(last[0], b) <= dp.MAX_FILL
            ):
                open_[key] = (last[0], b)
            else:
                if last:
                    merged.append(last)
                open_[key] = (a, b)
        merged += open_.values()
    return sorted(merged)


# ----------------------------------------------------------------------- build


def foundation_boxes(dome: Dome) -> list[tuple[Cell, Cell]]:
    """the ground under a dome's floor, as boxes ``FOUNDATION_DEPTH`` deep"""
    y = dome.floor_y
    return [
        ((a[0], y - FOUNDATION_DEPTH, a[2]), (b[0], y - 1, b[2]))
        for a, b in boxes(dome_cells(dome).floor)
    ]


def plug_doors(ctx: Any, dome: Dome, tunnel: Tunnel) -> None:
    """close the mouth of a tunnel in a dome's shell, and frame it"""
    ctx.fill_cells(frame_cells(dome, tunnel), FRAME)
    for block, cells in sorted(by_block(door_blocks(dome, tunnel)).items()):
        ctx.fill_boxes(cells, block)


def build_shell(ctx: Any, dome: Dome) -> str:
    """build a dome's empty, lit shell (see the module docstring); wipes
    whatever was inside it"""
    cells = dome_cells(dome)
    for a, b in foundation_boxes(dome):
        for what in NOT_GROUND:
            ctx.fill(a, b, FOUNDATION, f"replace {what}")
    ctx.fill_boxes(cells.all, GLASS)
    ctx.fill_boxes(cells.floor, FLOOR)
    ctx.fill_boxes(cells.interior, AIR)
    in_floor, in_shell = light_cells(dome)
    ctx.fill_boxes(in_floor | in_shell, LIGHT)
    for tunnel in touching(dome):
        plug_doors(ctx, dome, tunnel)
    # let the cut kelp drop, and what the build left standing settle
    ctx.advance(40)
    lo, hi = box(dome)
    where = dp.box_selector((lo[0], lo[1] - 1, lo[2]), (hi[0], hi[1] + 1, hi[2]))
    items = ctx.cmd(f"kill @e[type=minecraft:item,{where}]")
    return (
        f"{dome.name}: {len(cells.shell)} shell, {len(cells.floor)} floor, "
        f"{len(cells.interior)} cells inside, {len(in_floor) + len(in_shell)} "
        f"lanterns, {len(touching(dome))} mouths plugged; items: {items or 'none'}"
    )


# ---------------------------------------------------------------------- checks


def _count(name: str) -> str:
    return f"run scoreboard players add {name} {CHECK_OBJECTIVE} 1"


#: what a check function can do to each cell of a row, by the family's
#: name: lines with ``%k`` for the cell's place along the row. A function
#: of rows is a line a row, not a line (or five) a cell: the pack was 15 MB
#: of checks before these
ROW_FAMILIES = {
    # wet: water or a waterlogged block
    "row": (f"execute positioned ~%k ~ ~ if predicate {WET} {_count('#wet')}",),
    # a hole: air, or wet
    "hole": (
        f"execute if block ~%k ~ ~ {AIR} {_count('#holes')}",
        f"execute positioned ~%k ~ ~ if predicate {WET} {_count('#holes')}",
    ),
    # nothing solid under a floor cell
    "under": (f"execute if block ~%k ~-1 ~ {NOT_GROUND[0]} {_count('#under')}",),
}


def row_lines(pack: dp.Pack, cells, family: str = "row") -> list[str]:
    """function lines that apply a family of ``ROW_FAMILIES`` to each of
    the cells, a line for each row of them along x; the row functions
    they call (``check/<family>/<length>``) are added to the pack"""
    lines = []
    for a, b in runs(cells):
        n = b[0] - a[0] + 1
        if f"check/{family}/{n}" not in pack.functions:
            pack.function(
                f"check/{family}/{n}",
                [
                    t.replace("%k", str(k))
                    for k in range(n)
                    for t in ROW_FAMILIES[family]
                ],
            )
        lines.append(
            f"execute positioned {a[0]} {a[1]} {a[2]} "
            f"run function {pack.id(f'check/{family}/{n}')}"
        )
    return lines


def wet_lines(pack: dp.Pack, cells) -> list[str]:
    """function lines that add to ``#wet`` for each of the cells that is
    wet"""
    return row_lines(pack, cells, "row")


def check_parts(dome: Dome) -> list[list[tuple[Cell, Cell]]]:
    """the rows of a dome's inside and mouths, in parts small enough for
    one function each"""
    cells = dome_cells(dome)
    doors = set().union(*openings(dome).values())
    parts: list[list[tuple[Cell, Cell]]] = [[]]
    size = 0
    for a, b in runs((cells.interior | doors) - WET_OK.get(dome.index, set())):
        n = b[0] - a[0] + 2
        if size + n > CHECK_PART:
            parts.append([])
            size = 0
        parts[-1].append((a, b))
        size += n
    return parts


def wet_functions(dome: Dome) -> list[str]:
    """the paths of a dome's wet-counting functions"""
    return [f"check/dome/{dome.index}/wet_{i}" for i in range(len(check_parts(dome)))]


def add_check_functions(pack: dp.Pack, dome: Dome, built_tunnels=()) -> None:
    """add a dome's check functions to the pack (see the module docstring).
    ``built_tunnels``: the indexes of the tunnels whose doors may be open"""
    pack.objectives({CHECK_OBJECTIVE: "dummy"})
    cells = dome_cells(dome)
    ran = f"scoreboard players add #ran {CHECK_OBJECTIVE} 1"
    for path, part in zip(wet_functions(dome), check_parts(dome), strict=True):
        part_cells = {(x, a[1], a[2]) for a, b in part for x in range(a[0], b[0] + 1)}
        pack.function(path, [*wet_lines(pack, part_cells), ran])
    skip = set(OPENINGS.get(dome.index, ()))
    for index, mouth in openings(dome).items():
        if index in built_tunnels:
            skip |= mouth
    lines = row_lines(pack, (cells.shell | cells.floor) - skip, "hole")
    lines += row_lines(pack, cells.floor - skip, "under")
    pack.function(f"check/dome/{dome.index}/holes", [*lines, ran])


def check_shell(ctx: Any, dome: Dome, empty: bool = True) -> list[str]:
    """
    Live: a dome's shell and floor have no hole, nothing inside it or in
    its mouths is wet, its floor stands on something, and the sea is over
    its top (unless a module has registered an opening there). With ``empty``
    (no interior built yet) also: the light at head height at nine places,
    and no dropped item or falling block in it.
    """
    problems = []
    for name in ("#wet", "#holes", "#under", "#ran"):
        ctx.set_score(name, 0, CHECK_OBJECTIVE)
    paths = [*wet_functions(dome), f"check/dome/{dome.index}/holes"]
    for path in paths:
        ctx.function(path)
    # each function's last line counts it: one cut short (the game's limit
    # on commands) or missing would otherwise read as "nothing wet"
    if (ran := ctx.score("#ran", CHECK_OBJECTIVE)) != len(paths):
        problems.append(f"{dome.name}: {ran} of {len(paths)} check functions ran whole")
    wet, holes, under = (
        ctx.score(n, CHECK_OBJECTIVE) for n in ("#wet", "#holes", "#under")
    )
    if wet != 0:
        problems.append(f"{dome.name}: {wet} cells inside it or in its mouths are wet")
    if holes != 0:
        problems.append(f"{dome.name}: {holes} holes in its shell and floor")
    if under != 0:
        problems.append(f"{dome.name}: {under} floor cells stand on nothing")
    x, _, z = dome.floor_centre
    top = (x, dome.top_y + 1, z)
    cut = (x, dome.top_y, z) in OPENINGS.get(dome.index, ())  # e.g. a lift's shaft
    if dome.water_above > 0 and not cut and not ctx.is_block(top, "minecraft:water"):
        problems.append(f"{dome.name}: no sea over its top at {top}")
    if not empty:
        return problems
    dark = [
        p
        for p in light_probes(dome)
        if not ctx.test(
            f"execute positioned {p[0]} {p[1]} {p[2]} if predicate "
            '{type:"minecraft:location_check",predicate:{light:{light:{min:8}}}}'
        )
    ]
    if dark:
        problems.append(f"{dome.name}: light under 8 at {dark}")
    for kind in ("item", "falling_block"):
        n = ctx.count(f"@e[type=minecraft:{kind},{sphere(dome)}]")
        if n:
            problems.append(f"{dome.name}: {n} {kind} entities in it")
    return problems
