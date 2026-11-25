"""
The glass tunnels of The Drowned Station and their pumps: the cells of a
tunnel (pure functions of the layout), its build, its datapack functions
(drain, refill, the pump event) and its live check.

**What a tunnel is** (``tunnel_cells(tunnel)``). Places along a tunnel are
slices ``s``: 0 at the layout's end point ``a`` on the upstream dome's
shell, ``tunnel.length`` at ``b`` on the downstream dome's. A slice is a
ring of glass, 7 wide and 6 high, round an inside 5 wide and 4 high, on a
``FLOOR`` at the y the tunnel has there (``floor_y``: level for most; for
a tunnel whose domes' floors differ it steps a block at a time, which is
why everything here is done by slice; at each step a row of
``STAIRS`` stands on the lower side, so a player walks the slope: 3
blocks of floor, a stair, 3 of floor ... for the ring's two, which climb 8
in 24). Cells that belong to a dome are
left to the dome; the tunnel's inside starts behind the dome's door
(``domes.door_blocks``: brass, with a window to watch the tunnel through)
and ends behind the next dome's.

- ``layers``: the inside by height, the top layer first. A level tunnel
  has 4; a sloping one has one for every y its inside reaches.
- ``sections``: the inside cut along its length, ``SECTION`` slices each.
  Each has a copper bulb in the floor (``lamps``), dark while the tunnel
  is flooded.
- Every ``PIER_EVERY`` slices a pier of ``PIER`` stands under the tunnel,
  ``domes.FOUNDATION_DEPTH`` down, wherever the ground is not there.
- The pump engine (``engine_cells``, 3 along the wall, 1 deep, 4 high)
  stands inside the upstream dome, on its floor beside the mouth: two
  sticky pistons that lift brass heads in turn when a function puts a
  redstone block under them, a furnace between them, a lamp over it that
  flashes with the strokes and a chimney that steams.

**Reserved inside a dome** (``reserved_cells(dome)``): the two cells of
the entrance spot, a way in from each mouth as wide and high as the mouth
and 3 deep, and the engine of the outgoing tunnel. Nothing else of a
dome's inside is the tunnels'. See "Dressing a dome" in domes.py.

**Functions** (``add_functions``; ``<n>`` is the tunnel's index, the same
as the dome it leaves). The state is the score ``#t<n>`` in ``st``: 0
flooded and shut, 1 the pump event running, 2 dry and open.
``#t<n>.dry`` is how many layers are dry, ``#t<n>.lit`` how many lamps
are fully lit.

- ``station:tunnel/<n>/open``: the pump event, the same for every tunnel.
  Does nothing unless the tunnel is flooded and shut. The klaxon sounds,
  the lamps come on dimly so the water can be seen through the door's
  window, and the engine runs; after ``PUMP_LEAD`` ticks the water level
  falls a layer every ``layer_step(tunnel)`` ticks (3 s in a level
  tunnel); then the lamps come on fully one by one towards the next dome;
  then both doors slide open from the middle and the engine stops.
  ``event_ticks(tunnel)`` is how long all of it takes.
- ``station:tunnel/<n>/reset``: at once, from any state: the schedule
  cleared, the doors shut, the tunnel flooded and dark, the engine still.
- ``station:tunnel/<n>/state_<d>``: the water with the top d layers dry,
  written whole in one tick, so any state can follow any other and
  state 0 is the refill: the wet layers made sources again
  (``fill ... water replace water`` turns flowing water back to sources,
  then ``replace air``), the dry layers air. Water with air over it stays
  where it is: a layer of sources whose sides are all glass, brass or
  more sources has nowhere to flow, so no bulkhead is needed (the old
  drain, section by section along the tube, needed a wall of barrier).
  The layers go by their y, not by height above the floor, so that in a
  sloping tunnel too the surface is level and nothing runs downhill.
  Nothing waterlogged may be put in a tunnel: the fills leave such a
  block wet.

A tunnel that is not built yet has only ``open`` and ``reset``, which set
the score and nothing else, so the game's progress runs the same.

**The build** (``build_tunnel``): piers, then the tube solid glass, its
floor and lamps, the inside filled with water, the engine, both doors
shut. It leaves the tunnel in state 0 and is the same run twice.

**The check** (``check_tunnel``) works a built tunnel over RCON: reset,
open, each state read as it comes (``station:check/tunnel/<n>`` counts the
cells: every layer state must be all sources below and all air above,
with no flowing water and no air under water), the lamps, the doors, the
engine's pistons seen to move, the tunnel and both domes dry afterwards,
then reset and flooded again.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache, cached_property
from typing import TYPE_CHECKING, Any

import datapack as dp
import domes
import station_layout as layout
from domes import AIR, DOOR_HALF_WIDTH, DOOR_HEIGHT, GLASS, Cell

if TYPE_CHECKING:
    from station_layout import Dome, Tunnel

WATER = "minecraft:water"
FLOOR = "minecraft:polished_deepslate"
LAMP = "minecraft:waxed_copper_bulb"  # light 15 when lit
#: a lamp during the pump event: lit, it gives light 8, enough to see the
#: water by through the window
LAMP_DIM = "minecraft:waxed_weathered_copper_bulb"
PIER = "minecraft:deepslate_bricks"
OBJECTIVE = "st"

SECTION = 4  # slices a section
PIER_EVERY = 8
PUMP_LEAD = 40  # ticks the engine runs before the water starts to fall
DRAIN_TICKS = 240  # about how long the water takes to fall, whatever the layers
LAMP_STEP = 8  # ticks between the lamps coming on
STROKE = 8  # ticks between the engine's strokes
HORN_EVERY = 80  # ticks between the klaxon's blasts
DOOR_STEP = 4  # ticks between the columns of a door sliding open

STAIRS = "minecraft:polished_deepslate_stairs"

#: the tunnels that are built: all of the ring
BUILT = tuple(t.index for t in layout.TUNNELS)

# the engine: blocks by (place along the wall 0..2, height 0..3)
ENGINE_IDLE = "minecraft:waxed_cut_copper"
ENGINE_POWER = "minecraft:redstone_block"
ENGINE_LAMP = "minecraft:waxed_copper_bulb"
ENGINE = {
    (0, 0): ENGINE_IDLE,
    (1, 0): "minecraft:waxed_copper_block",
    (2, 0): ENGINE_IDLE,
    (0, 1): "minecraft:sticky_piston[facing=up]",
    (1, 1): "minecraft:blast_furnace",
    (2, 1): "minecraft:sticky_piston[facing=up]",
    (0, 2): "minecraft:gold_block",
    (1, 2): f"{ENGINE_LAMP}[lit=false]",
    (2, 2): "minecraft:gold_block",
    (0, 3): AIR,
    (1, 3): "minecraft:waxed_lightning_rod",
    (2, 3): AIR,
}


@dataclass(frozen=True)
class TunnelCells:
    ring: frozenset[Cell]  #: the glass round the inside (not the floor)
    floor: frozenset[Cell]
    sections: tuple[frozenset[Cell], ...]  #: the inside, upstream first
    lamps: tuple[Cell, ...]  #: one in the floor of each section
    piers: frozenset[Cell]  #: the top cell of each pier's columns
    stairs: dict[Cell, str]  #: a sloping tunnel's steps: cell -> stair block

    @cached_property
    def inside(self) -> frozenset[Cell]:
        return frozenset().union(*self.sections)

    @cached_property
    def layers(self) -> tuple[frozenset[Cell], ...]:
        """the inside by y, the top layer first"""
        ys = sorted({c[1] for c in self.inside}, reverse=True)
        return tuple(frozenset(c for c in self.inside if c[1] == y) for y in ys)


def ends(tunnel: Tunnel) -> tuple[Dome, Dome]:
    """the domes a tunnel leaves and arrives at"""
    return layout.DOMES[tunnel.start], layout.DOMES[tunnel.end]


def floor_y(tunnel: Tunnel, s: int) -> int:
    """the y of a tunnel's floor at slice s: the upstream dome's floor at
    0 and before, the downstream dome's at the far end and beyond, and in
    between a step at a time"""
    s = min(max(s, 0), tunnel.length)
    return tunnel.a[1] + round(tunnel.rise * s / tunnel.length)


def at(tunnel: Tunnel, s: int, w: int, h: int) -> Cell:
    """the cell at slice s, w across (right of the way from a to b, seen
    from above) and h above the floor there"""
    sx, sz = tunnel.step
    ax, az = domes.across(tunnel.step)
    return (
        tunnel.a[0] + s * sx + w * ax,
        floor_y(tunnel, s) + h,
        tunnel.a[2] + s * sz + w * az,
    )


def sections_of(tunnel: Tunnel) -> int:
    """how many sections a tunnel has"""
    return -(-(tunnel.length - 1) // SECTION)


@cache
def tunnel_cells(tunnel: Tunnel) -> TunnelCells:
    """a tunnel's cells (see the module docstring)"""
    taken = set().union(*(domes.dome_cells(d).all for d in ends(tunnel)))
    n = sections_of(tunnel)
    ring, floor = set(), set()
    sections: list[set[Cell]] = [set() for _ in range(n)]
    hw = DOOR_HALF_WIDTH
    reach = max(d.radius for d in ends(tunnel))
    for s in range(-reach, tunnel.length + reach + 1):
        section = min(max((s - 1) // SECTION, 0), n - 1)
        for w in range(-hw - 1, hw + 2):
            for h in range(DOOR_HEIGHT + 2):
                cell = at(tunnel, s, w, h)
                if cell in taken:
                    continue
                if abs(w) <= hw and 1 <= h <= DOOR_HEIGHT:
                    sections[section].add(cell)
                elif h == 0 and abs(w) <= hw:
                    floor.add(cell)
                else:
                    ring.add(cell)
    slices = range(1, tunnel.length)
    # where the floor steps, a row of stairs on the lower side, so the
    # slope is walked, not jumped. They stand where water would, dry
    # (never waterlogged), and are not part of the inside
    stairs: dict[Cell, str] = {}
    sx, sz = tunnel.step
    for s in slices:
        for other, towards in ((s - 1, (-sx, -sz)), (s + 1, (sx, sz))):
            if floor_y(tunnel, other) > floor_y(tunnel, s):
                block = (
                    f"{STAIRS}[facing={domes.COMPASS[towards]},half=bottom,"
                    "waterlogged=false]"
                )
                for w in range(-hw, hw + 1):
                    if at(tunnel, s, w, 1) not in taken:
                        stairs[at(tunnel, s, w, 1)] = block
    for section in sections:
        section -= set(stairs)
    lamps = tuple(
        at(tunnel, min(1 + i * SECTION + SECTION // 2, tunnel.length - 1), 0, 0)
        for i in range(n)
    )
    piers = frozenset(
        at(tunnel, s, w, -1) for s in slices if s % PIER_EVERY == 4 for w in (-1, 0, 1)
    )
    return TunnelCells(
        frozenset(ring),
        frozenset(floor),
        tuple(frozenset(s) for s in sections),
        lamps,
        piers,
        stairs,
    )


@cache
def engine_cells(tunnel: Tunnel) -> dict[tuple[int, int], Cell]:
    """
    The cells of a tunnel's pump engine, by (place along the wall, height)
    as in ``ENGINE``: inside the upstream dome, on its floor, to the right
    of the mouth as you leave, as near the wall as leaves it clear of the
    shell.
    """
    dome = ends(tunnel)[0]
    inside = domes.dome_cells(dome).interior
    for s in range(0, -dome.radius, -1):
        cells = {
            (u, v): at(tunnel, s, DOOR_HALF_WIDTH + 2 + u, v + 1) for u, v in ENGINE
        }
        if all(c in inside for c in cells.values()):
            return cells
    raise ValueError(f"no room for the engine of tunnel {tunnel.index}")


def reserved_cells(dome: Dome) -> set[Cell]:
    """the cells inside a dome that an interior must keep clear: the spot
    a player is put at, a way in from each mouth, and the pump engine of
    its outgoing tunnel"""
    x, y, z, _ = domes.entrance(dome)
    keep = {(x, y, z), (x, y + 1, z)}
    inside = domes.dome_cells(dome).interior
    for tunnel in domes.touching(dome):
        ux, uz = domes.outward(dome, tunnel)
        ax, az = domes.across((ux, uz))
        ox, oy, oz = dome.floor_centre
        for w in range(-DOOR_HALF_WIDTH, DOOR_HALF_WIDTH + 1):
            for h in range(1, DOOR_HEIGHT + 1):
                way = [
                    (ox + s * ux + w * ax, oy + h, oz + s * uz + w * az)
                    for s in range(dome.radius, 0, -1)
                ]
                keep.update([c for c in way if c in inside][:3])
    keep.update(engine_cells(layout.TUNNELS[dome.index]).values())
    return keep


# ----------------------------------------------------------------------- build


def build_tunnel(ctx: Any, tunnel: Tunnel) -> str:
    """build a tunnel, flooded and shut, with its engine (see the module
    docstring)"""
    cells = tunnel_cells(tunnel)
    for x, y, z in sorted(cells.piers):
        for what in domes.NOT_GROUND:
            ctx.fill(
                (x, y - domes.FOUNDATION_DEPTH, z), (x, y, z), PIER, f"replace {what}"
            )
    ctx.fill_boxes(cells.ring | cells.floor | cells.inside | set(cells.stairs), GLASS)
    ctx.fill_boxes(cells.floor, FLOOR)
    for lamp in cells.lamps:
        ctx.setblock(lamp, f"{LAMP}[lit=false]")
    ctx.fill_boxes(cells.inside, WATER)
    for block, steps in sorted(domes.by_block(cells.stairs).items()):
        ctx.fill_boxes(steps, block)
    for dome in ends(tunnel):
        domes.plug_doors(ctx, dome, tunnel)
    for cell in engine_cells(tunnel).values():
        ctx.setblock(cell, AIR)  # (a piston's head, if it was caught out)
    for key, cell in engine_cells(tunnel).items():
        ctx.setblock(cell, ENGINE[key])
    ctx.advance(10)
    return (
        f"tunnel {tunnel.index}: {tunnel.length} long, {len(cells.inside)} cells "
        f"of water in {len(cells.layers)} layers and {len(cells.sections)} sections, {len(cells.piers) // 3} piers"
    )


# ------------------------------------------------------------------- functions


def score(tunnel_index: int, what: str = "") -> str:
    """the fake player holding a tunnel's state (or its ``.dry`` or
    ``.lit`` count)"""
    return f"#t{tunnel_index}{what} {OBJECTIVE}"


def layer_step(tunnel: Tunnel) -> int:
    """ticks between the layers of a tunnel's water going"""
    return max(20, DRAIN_TICKS // len(tunnel_cells(tunnel).layers))


def event_ticks(tunnel: Tunnel) -> int:
    """how long a built tunnel's pump event takes, from ``open`` to the
    doors open and the score at 2"""
    cells = tunnel_cells(tunnel)
    dry = PUMP_LEAD + layer_step(tunnel) * len(cells.layers)
    lit = dry + LAMP_STEP * len(cells.lamps)
    return lit + DOOR_STEP * DOOR_HALF_WIDTH


def state_lines(tunnel: Tunnel, d: int) -> list[str]:
    """the commands of state d: the top d layers dry, the rest water"""
    cells = tunnel_cells(tunnel)
    wet = frozenset().union(*cells.layers[d:])
    dry = frozenset().union(*cells.layers[:d])
    lines = [f"scoreboard players set {score(tunnel.index, '.dry')} {d}"]
    for a, b in domes.boxes(wet):
        lines += [
            dp.fill(a, b, WATER, f"replace {WATER}"),  # flowing -> source
            dp.fill(a, b, WATER, f"replace {AIR}"),
        ]
    for a, b in domes.boxes(dry):
        lines.append(dp.fill(a, b, AIR, f"replace {WATER}"))
    return lines


def lamp_lines(tunnel: Tunnel, lit: int, rest: str) -> list[str]:
    """commands that light the first ``lit`` lamps fully and set the
    others to the block ``rest``"""
    lines = [f"scoreboard players set {score(tunnel.index, '.lit')} {lit}"]
    for i, (x, y, z) in enumerate(tunnel_cells(tunnel).lamps):
        block = f"{LAMP}[lit=true]" if i < lit else rest
        lines.append(f"setblock {x} {y} {z} {block}")
    return lines


def door_lines(tunnel: Tunnel, shut: bool, columns=None) -> list[str]:
    """commands that shut both doors, or open those of their cells that
    are ``columns`` across (default all)"""
    lines = []
    for dome in ends(tunnel):
        if shut:
            blocks = domes.by_block(domes.door_blocks(dome, tunnel))
        else:
            blocks = {
                AIR: {
                    c
                    for w, c in domes.door_cells(dome, tunnel)
                    if columns is None or abs(w) in columns
                }
            }
        for block, cells in sorted(blocks.items()):
            lines += [dp.fill(a, b, block) for a, b in domes.boxes(cells)]
    return lines


def add_functions(pack: dp.Pack, tunnel: Tunnel, players: str) -> None:
    """add a built tunnel's functions to the pack (see the module
    docstring). ``players`` is the selector of who hears the event"""
    n = tunnel.index
    base = f"tunnel/{n}"
    cells = tunnel_cells(tunnel)
    layers, lamps = len(cells.layers), len(cells.lamps)
    engine = engine_cells(tunnel)
    state = score(n)

    def fid(name: str) -> str:
        return pack.id(f"{base}/{name}")

    def setblock(key: tuple[int, int], block: str) -> str:
        x, y, z = engine[key]
        return f"setblock {x} {y} {z} {block}"

    def sound(name: str, volume: float, pitch: float, kind: str = "block") -> str:
        where = domes.middle(engine[1, 1], 0.5)
        return f"playsound minecraft:{name} {kind} {players} {where} {volume} {pitch}"

    pack.function(
        f"{base}/state_0",
        [*state_lines(tunnel, 0), *lamp_lines(tunnel, 0, f"{LAMP}[lit=false]")],
    )
    for d in range(1, layers + 1):
        pack.function(
            f"{base}/state_{d}",
            [
                *state_lines(tunnel, d),
                sound("block.bubble_column.whirlpool_ambient", 1, 0.6),
            ],
        )
    pack.function(f"{base}/glow", lamp_lines(tunnel, 0, f"{LAMP_DIM}[lit=true]"))
    for k in range(1, lamps + 1):
        x, y, z = cells.lamps[k - 1]
        pack.function(
            f"{base}/lamp_{k}",
            [
                f"scoreboard players set {score(n, '.lit')} {k}",
                f"setblock {x} {y} {z} {LAMP}[lit=true]",
                sound("block.copper_bulb.turn_on", 1, 1),
            ],
        )

    # the engine: a stroke lifts one head and drops the other, the lamp
    # flashes, the chimney steams and the rising head puffs
    running = f"execute unless score {state} matches 1 run return 0"
    smoke = (
        f"particle minecraft:campfire_cosy_smoke {domes.middle(engine[1, 3], 1.1)} "
        "0.1 0.5 0.1 0.01 10"
    )
    strokes = (("a", "b", 0, 2, "true"), ("b", "a", 2, 0, "false"))
    for this, other, up, down, lit in strokes:
        puff = f"particle minecraft:cloud {domes.middle(engine[up, 3], 0.6)} 0.2 0.2 0.2 0.02 8"
        pack.function(
            f"{base}/pump/{this}",
            [
                running,
                setblock((up, 0), ENGINE_POWER),
                setblock((down, 0), ENGINE_IDLE),
                setblock((1, 2), f"{ENGINE_LAMP}[lit={lit}]"),
                smoke,
                puff,
                sound("block.fire.extinguish", 0.5, 0.6 if lit == "true" else 0.8),
                f"schedule function {fid(f'pump/{other}')} {STROKE}t",
            ],
        )
    pack.function(
        f"{base}/pump/horn",
        [
            running,
            sound("event.raid.horn", 4, 1.4, "master"),
            f"schedule function {fid('pump/horn')} {HORN_EVERY}t",
        ],
    )
    pack.function(
        f"{base}/pump/stop",
        [
            setblock((0, 0), ENGINE_IDLE),
            setblock((2, 0), ENGINE_IDLE),
            setblock((1, 1), ENGINE[1, 1]),
            setblock((1, 2), ENGINE[1, 2]),
        ],
    )

    scheduled = [f"{base}/pump/a", f"{base}/pump/b", f"{base}/pump/horn"]
    begin = [
        f"scoreboard players set {state} 1",
        f"function {fid('glow')}",
        setblock((1, 1), f"{ENGINE[1, 1]}[lit=true]"),
        f"function {fid('pump/a')}",
        f"function {fid('pump/horn')}",
    ]
    step = layer_step(tunnel)
    for d in range(1, layers + 1):
        when = PUMP_LEAD + step * (d - 1)
        begin.append(f"schedule function {fid(f'state_{d}')} {when}t")
        scheduled.append(f"{base}/state_{d}")
    dry_at = PUMP_LEAD + step * layers
    for k in range(1, lamps + 1):
        begin.append(
            f"schedule function {fid(f'lamp_{k}')} {dry_at + LAMP_STEP * (k - 1)}t"
        )
        scheduled.append(f"{base}/lamp_{k}")
    doors_at = dry_at + LAMP_STEP * lamps
    for column in range(DOOR_HALF_WIDTH + 1):
        begin.append(
            f"schedule function {fid(f'door_{column}')} {doors_at + DOOR_STEP * column}t"
        )
        scheduled.append(f"{base}/door_{column}")
        lines = door_lines(tunnel, False, {column})
        lines.append(sound("block.piston.contract", 1, 0.6))
        if column == DOOR_HALF_WIDTH:
            lines += [
                f"scoreboard players set {state} 2",
                f"function {fid('pump/stop')}",
            ]
        pack.function(f"{base}/door_{column}", lines)
    pack.function(f"{base}/begin", begin)
    pack.function(
        f"{base}/open",
        [f"execute if score {state} matches 0 run function {fid('begin')}"],
    )
    pack.function(
        f"{base}/reset",
        [
            *(f"schedule clear {pack.id(path)}" for path in scheduled),
            f"scoreboard players set {state} 0",
            f"function {fid('pump/stop')}",
            *door_lines(tunnel, True),
            f"function {fid('state_0')}",
        ],
    )

    # the check's counts, over every cell
    add = f"run scoreboard players add #t_{{}} {domes.CHECK_OBJECTIVE} 1"
    lines = [f"scoreboard players set #t_{k} {domes.CHECK_OBJECTIVE} 0" for k in COUNTS]
    for x, y, z in sorted(cells.inside):
        here = f"execute if block {x} {y} {z}"
        lines += [
            f"{here} {WATER} {add.format('water')}",
            f"{here} {WATER}[level=0] {add.format('source')}",
            f"{here} {AIR} {add.format('air')}",
            f"execute positioned {x} {y} {z} if predicate {domes.WET} "
            f"{add.format('wet')}",
        ]
        if (x, y + 1, z) in cells.inside:
            lines.append(
                f"{here} {AIR} if block {x} {y + 1} {z} {WATER} {add.format('under')}"
            )
    for x, y, z in cells.lamps:
        lines += [
            f"execute if block {x} {y} {z} {LAMP}[lit=true] {add.format('lit')}",
            f"execute if block {x} {y} {z} {LAMP_DIM}[lit=true] {add.format('dim')}",
        ]
    for dome in ends(tunnel):
        for (x, y, z), block in sorted(domes.door_blocks(dome, tunnel).items()):
            lines.append(f"execute if block {x} {y} {z} {block} {add.format('shut')}")
    for x, y, z in sorted(cells.ring | cells.floor | set(cells.stairs)):
        lines += [
            f"execute if block {x} {y} {z} {AIR} {add.format('ring')}",
            f"execute positioned {x} {y} {z} if predicate {domes.WET} "
            f"{add.format('ring')}",
        ]
    pack.function(f"check/tunnel/{n}", lines)


def add_stub_functions(pack: dp.Pack, tunnel: Tunnel) -> None:
    """``open`` and ``reset`` for a tunnel that is not built yet: the score
    only"""
    state = score(tunnel.index)
    pack.function(
        f"tunnel/{tunnel.index}/open",
        [f"execute if score {state} matches 0 run scoreboard players set {state} 2"],
    )
    pack.function(f"tunnel/{tunnel.index}/reset", [f"scoreboard players set {state} 0"])


# ----------------------------------------------------------------------- check

#: what ``station:check/tunnel/<n>`` counts: inside cells that are water,
#: sources, air, wet (the predicate), air with water over them; lamps fully
#: lit and dimly lit; door cells shut; ring and floor cells that are holes
COUNTS = ("water", "source", "air", "wet", "under", "lit", "dim", "shut", "ring")


def counts(ctx: Any, tunnel: Tunnel) -> dict[str, int | None]:
    ctx.function(f"check/tunnel/{tunnel.index}")
    return {k: ctx.score(f"#t_{k}", domes.CHECK_OBJECTIVE) for k in COUNTS}


def expected(
    tunnel: Tunnel, d: int, lit: int = 0, dim: int = 0, shut: bool = True
) -> dict[str, int]:
    """what ``counts`` reads with the top d layers dry, ``lit`` lamps fully
    lit and ``dim`` dimly, the doors shut or open"""
    cells = tunnel_cells(tunnel)
    dry = sum(len(layer) for layer in cells.layers[:d])
    water = len(cells.inside) - dry
    doors = sum(len(domes.door_cells(e, tunnel)) for e in ends(tunnel))
    return {
        "water": water,
        "source": water,
        "air": dry,
        "wet": water,
        "under": 0,
        "lit": lit,
        "dim": dim,
        "shut": doors if shut else 0,
        "ring": 0,
    }


def check_tunnel(ctx: Any, tunnel: Tunnel) -> list[str]:
    """work a built tunnel in place (see the module docstring); leaves it
    reset"""
    n = tunnel.index
    name = f"tunnel {n}"
    cells = tunnel_cells(tunnel)
    layers, lamps = len(cells.layers), len(cells.lamps)
    engine = engine_cells(tunnel)
    problems: list[str] = []

    def state() -> tuple[int | None, int | None, int | None]:
        return ctx.score(f"#t{n}"), ctx.score(f"#t{n}.dry"), ctx.score(f"#t{n}.lit")

    def differ(what: str, want: dict[str, int]) -> None:
        got = counts(ctx, tunnel)
        if got != want:
            wrong = {k: (got[k], want[k]) for k in want if got[k] != want[k]}
            problems.append(f"{name} {what}: (read, expected) {wrong}")

    def pistons() -> int:
        return sum(
            ctx.is_block(engine[u, 1], "minecraft:sticky_piston[extended=true]")
            for u in (0, 2)
        )

    ctx.function(f"tunnel/{n}/reset")
    ctx.advance(5)
    if state() != (0, 0, 0):
        problems.append(f"{name}: state after reset is {state()}, not (0, 0, 0)")
    differ("reset", expected(tunnel, 0))

    ctx.function(f"tunnel/{n}/open")
    ctx.function(f"tunnel/{n}/open")  # a second call must change nothing
    seen_pistons, flashes = set(), set()
    seen: list[tuple[int, int]] = []  # (layers dry, lamps lit) read whole
    deadline = event_ticks(tunnel) + 200
    waited = 0
    while waited < deadline:
        ctx.advance(3)
        waited += 3
        seen_pistons.add(pistons())
        flashes.add(ctx.is_block(engine[1, 2], f"{ENGINE_LAMP}[lit=true]"))
        phase, dry, lit = state()
        if phase == 2:
            break
        if phase != 1 or dry is None or lit is None or (dry, lit) in seen:
            continue
        got = counts(ctx, tunnel)
        if state() != (phase, dry, lit):
            continue  # a step ran between the reads: catch the next
        seen.append((dry, lit))
        # while the event runs every lamp not yet fully lit glows dimly
        want = expected(tunnel, dry, lit, lamps - lit)
        if got != want:
            wrong = {k: (got[k], want[k]) for k in want if got[k] != want[k]}
            problems.append(
                f"{name}, {dry} layers dry, {lit} lamps lit: (read, expected) {wrong}"
            )
    else:
        problems.append(f"{name}: not open {deadline} ticks after open: {state()}")
    print(f"     {name}: read whole (layers dry, lamps lit): {seen}", flush=True)
    if seen != sorted(seen) or {d for d, _ in seen} != set(range(layers + 1)):
        problems.append(
            f"{name}: the layers read dry while draining were "
            f"{sorted({d for d, _ in seen})} of 0..{layers}"
        )
    lit_seen = {k for d, k in seen if d == layers}
    if len(lit_seen) < lamps // 2 or any(k for d, k in seen if d < layers):
        problems.append(
            f"{name}: lamps read lit once dry were {sorted(lit_seen)} of 0..{lamps}, "
            f"and before it was dry {[s for s in seen if s[0] < layers and s[1]]}"
        )
    if not {1} <= seen_pistons:
        problems.append(
            f"{name}: never one piston out and one in while pumping: {seen_pistons}"
        )
    if flashes != {True, False}:
        problems.append(f"{name}: the engine's lamp did not flash: {flashes}")
    ctx.advance(10)
    differ("open", expected(tunnel, layers, lamps, 0, shut=False))
    if pistons():
        problems.append(f"{name}: a piston still out after the event")
    for u in (0, 2):
        if not ctx.is_block(engine[u, 0], ENGINE_IDLE):
            problems.append(f"{name}: the engine is still powered at {engine[u, 0]}")
    for dome in ends(tunnel):
        open_ = sum(ctx.is_block(c, AIR) for _, c in domes.door_cells(dome, tunnel))
        if open_ != len(domes.door_cells(dome, tunnel)):
            problems.append(f"{name}: door into {dome.name} not open: {open_} air")
    ctx.advance(150)
    differ("open, 150 ticks on", expected(tunnel, layers, lamps, 0, shut=False))
    for dome in ends(tunnel):
        problems += [f"{name} open: {p}" for p in domes.check_shell(ctx, dome, False)]

    ctx.function(f"tunnel/{n}/reset")
    ctx.advance(40)
    if state() != (0, 0, 0):
        problems.append(f"{name}: state after the last reset is {state()}")
    differ("reset again", expected(tunnel, 0))
    # any state can follow any other (behind shut doors): half drained
    # from dry, then from flooded, each left to stand
    half = layers // 2
    for first in (layers, 0):
        ctx.function(f"tunnel/{n}/state_{first}")
        ctx.function(f"tunnel/{n}/state_{half}")
        ctx.advance(100)
        got = counts(ctx, tunnel)
        want = expected(tunnel, half)
        wrong = {
            k: (got[k], want[k])
            for k in ("water", "source", "air", "wet", "under")
            if got[k] != want[k]
        }
        if wrong:
            problems.append(
                f"{name}: state {half} after state {first}, 100 ticks on: "
                f"(read, expected) {wrong}"
            )

    ctx.function(f"tunnel/{n}/reset")
    ctx.advance(10)
    ctx.advance(event_ticks(tunnel))  # nothing left scheduled
    differ("reset again, and the event's time on", expected(tunnel, 0))
    for dome in ends(tunnel):
        problems += [f"{name} shut: {p}" for p in domes.check_shell(ctx, dome, False)]
    return problems
