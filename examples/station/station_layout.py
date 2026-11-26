"""
The layout of the Drowned Station: where the shore landing, the dock, the
lift, the eight domes and the eight tunnels are. Plain data and small pure
functions: nothing here talks to a server, so the build, the datapack
generator, the verify script and the tests can all import it.

The module has two parts. The *site* block says where the station is in
one particular world: an anchor (the x, z of the middle of the start dome
and the y of its floor), the sea level, and what belongs to the place
rather than to the station (the world spawn, the shore landing, hazards
found there). The *shape* block says what the station is: every dome as an
offset from the anchor. Everything else is worked out from those two, so
moving the anchor moves the whole station.

To put the station in another world: survey the sea there
(`survey_site.py` writes ``site_survey.npz``), set the site block, run
`check_site` (does this layout fit that sea?) and draw it with
`render_layout.py` (``layout_plan.png``). `check_layout` checks the rules
of the plan, which do not depend on the site.

Conventions:

- Coordinates are world blocks, ``(x, y, z)`` with y up; north is -z.
- A dome is a half sphere standing on its floor. ``centre`` is the middle of
  the floor, ``floor_y`` the y of the floor blocks (players stand on top of
  them, feet at ``floor_y + 1``). The shell lies ``radius`` blocks from the
  centre, so the dome spans ``centre +- radius`` and its top block is at
  ``floor_y + radius``.
- The domes stand on a rectangular ring, so every tunnel runs straight along
  x or along z. A tunnel's end points are the blocks where its centre line
  meets the shells of its two domes, each at that dome's floor level; its
  length is the distance between them. Floors differ by a few blocks, so
  some tunnels slope.
- The ring is walked in order: dome 0 (the start), 1 ... 7 (the boss), and
  tunnel 7 leads from the boss back into dome 0.
"""

from dataclasses import dataclass

Pos = tuple[int, int, int]

# ----------------------------------------------------------------------------
# the site: where the station is in this world. Change this block (and only
# this block) to put the station somewhere else, then run check_site().

#: the sea's surface: the top layer of water blocks is at SEA_LEVEL - 1
SEA_LEVEL = 63
#: the x, z of the middle of the start dome: every dome is an offset from it
ANCHOR: tuple[int, int] = (63, -109)
#: the y of the floor blocks of the start dome, and of every dome that is
#: not sunk below it (see ``sunk`` in `RING`)
BASE_FLOOR_Y = 37
#: the world spawn (here: on the shore south west of the station)
SPAWN: Pos = (-32, 63, 81)
#: where players start: a block of the shore to stand on with the sea (and
#: the boat) beside it, facing the dock across the water. Here: grass at
#: the tip of the headland north east of the world spawn
SHORE_LANDING: Pos = (-18, 63, 66)
#: Hazards of this site. Monster spawners of the abandoned mineshaft that
#: runs under its sea floor (its highest timbers are at y 34, the dome
#: floors at y 37). The first is within a spawner's 16 block reach of the
#: Gearworks floor: the build should remove both so that nothing breeds
#: under the station. Empty for a site without any.
MINESHAFT_SPAWNERS: tuple[Pos, ...] = ((188, 23, -102), (197, 22, -137))

# ----------------------------------------------------------------------------
# the rules (the plan's, the same for any site)

#: tunnels are between this many blocks long, shell to shell (the plan)
TUNNEL_MIN, TUNNEL_MAX = 20, 40
#: the least clear sea between the shells of domes that no tunnel joins
DOME_GAP_MIN = 24
#: how far the station's box reaches beyond the outermost shells
MARGIN = 8


# ----------------------------------------------------------------------------
# the domes


@dataclass(frozen=True)
class Dome:
    """One dome of the ring (see the module docstring for the conventions)"""

    index: int
    key: str  #: a short name for function and tag names, e.g. "boiler"
    name: str  #: the name shown to players
    centre: tuple[int, int]  #: x, z of the middle of the floor
    diameter: int
    floor_y: int

    @property
    def radius(self) -> int:
        return self.diameter // 2

    @property
    def floor_centre(self) -> Pos:
        """the floor block in the middle of the dome"""
        return (self.centre[0], self.floor_y, self.centre[1])

    @property
    def top_y(self) -> int:
        """the y of the topmost block of the shell"""
        return self.floor_y + self.radius

    @property
    def water_above(self) -> int:
        """
        layers of sea water over the top of the shell; negative when the
        dome breaks the surface, by that many blocks plus one
        """
        return SEA_LEVEL - 1 - self.top_y

    def contains(self, x: float, y: float, z: float) -> bool:
        """is a position inside the dome (shell included)?"""
        dx, dy, dz = x - self.centre[0], y - self.floor_y, z - self.centre[1]
        return dy >= 0 and dx * dx + dy * dy + dz * dz <= self.radius**2


# The shape: the ring in order, each dome as its key, its name, the offset
# (x, z) of its centre from the anchor, its diameter, and ``sunk``: how far
# its floor lies below the base floor (the boss dome's is dug into the sea
# floor so that its top comes no higher than the others'). The first is the
# start dome, at the anchor; the domes stand on a rectangle, four by two.
RING: tuple[tuple[str, str, tuple[int, int], int, int], ...] = (
    ("start", "The Pump House", (0, 0), 48, 0),
    ("boiler", "Boiler Room", (66, 0), 32, 0),
    ("gearworks", "Gearworks", (136, 0), 48, 0),
    ("flooded", "Flooded Dome", (208, 0), 48, 0),
    ("foundry", "Foundry", (208, -80), 48, 0),
    ("signal", "Signal Room", (144, -80), 32, 0),
    ("maze", "Clockwork Maze", (80, -80), 48, 0),
    ("boss", "The Engine", (0, -80), 64, 8),
)


def make_domes(
    anchor: tuple[int, int] = ANCHOR, base_floor_y: int = BASE_FLOOR_Y
) -> tuple[Dome, ...]:
    """the domes of the ring, for an anchor and a base floor height"""
    return tuple(
        Dome(
            index,
            key,
            name,
            (anchor[0] + dx, anchor[1] + dz),
            diameter,
            base_floor_y - sunk,
        )
        for index, (key, name, (dx, dz), diameter, sunk) in enumerate(RING)
    )


DOMES: tuple[Dome, ...] = make_domes()

START, BOSS = DOMES[0], DOMES[-1]


def dome(key: str) -> Dome:
    """the dome with a key, e.g. ``dome("boiler")``"""
    for each in DOMES:
        if each.key == key:
            return each
    raise KeyError(key)


def dome_at(x: float, y: float, z: float) -> Dome | None:
    """the dome that a position is inside, if any"""
    for each in DOMES:
        if each.contains(x, y, z):
            return each
    return None


# ----------------------------------------------------------------------------
# the tunnels


@dataclass(frozen=True)
class Tunnel:
    """The tunnel from one dome to the next round the ring"""

    index: int  #: the same as the index of the dome it leaves
    start: int  #: index of the dome it leaves
    end: int  #: index of the dome it arrives at
    a: Pos  #: the end point on the shell of ``start``, at its floor level
    b: Pos  #: the end point on the shell of ``end``, at its floor level
    axis: str  #: "x" or "z": the direction it runs in

    @property
    def length(self) -> int:
        """the distance from ``a`` to ``b``: shell to shell, edge to edge"""
        return abs(self.b[0] - self.a[0]) + abs(self.b[2] - self.a[2])

    @property
    def step(self) -> tuple[int, int]:
        """the unit step in x, z from ``a`` towards ``b``"""
        dx, dz = self.b[0] - self.a[0], self.b[2] - self.a[2]
        return ((dx > 0) - (dx < 0), (dz > 0) - (dz < 0))

    @property
    def rise(self) -> int:
        """how far the floor climbs (or, negative, falls) from a to b"""
        return self.b[1] - self.a[1]


def tunnel_between(index: int, start: Dome, end: Dome) -> Tunnel:
    """
    The straight tunnel between two domes whose centres share an x or a z.

    :raises ValueError: if they share neither (or both)
    """
    (x1, z1), (x2, z2) = start.centre, end.centre
    if (x1 == x2) == (z1 == z2):
        raise ValueError(f"domes {start.key} and {end.key} are not in line")
    if z1 == z2:
        sign = 1 if x2 > x1 else -1
        a = (x1 + sign * start.radius, start.floor_y, z1)
        b = (x2 - sign * end.radius, end.floor_y, z2)
        return Tunnel(index, start.index, end.index, a, b, "x")
    sign = 1 if z2 > z1 else -1
    a = (x1, start.floor_y, z1 + sign * start.radius)
    b = (x2, end.floor_y, z2 - sign * end.radius)
    return Tunnel(index, start.index, end.index, a, b, "z")


def make_tunnels(domes: tuple[Dome, ...] = DOMES) -> tuple[Tunnel, ...]:
    """the tunnels of a ring of domes: each to the next, the last to the first"""
    return tuple(
        tunnel_between(d.index, d, domes[(i + 1) % len(domes)])
        for i, d in enumerate(domes)
    )


TUNNELS: tuple[Tunnel, ...] = make_tunnels()


# ----------------------------------------------------------------------------
# the way in: shore, dock and lift

#: the middle of the dock's deck, directly above the start dome
DOCK: Pos = (START.centre[0], SEA_LEVEL + 1, START.centre[1])
#: the lift shaft: straight down from the dock through the top of the start
#: dome to its floor. x, z, then the y of the deck and of the dome's floor
LIFT_XZ: tuple[int, int] = (DOCK[0], DOCK[2])
LIFT_TOP_Y: int = DOCK[1]
LIFT_BOTTOM_Y: int = START.floor_y


def station_bounds(margin: int = MARGIN) -> tuple[Pos, Pos]:
    """
    The box that holds the dock, the domes and the tunnels (not the shore):
    its low and high corners. Players inside it are "in the game".
    """
    low_x = min(d.centre[0] - d.radius for d in DOMES) - margin
    high_x = max(d.centre[0] + d.radius for d in DOMES) + margin
    low_z = min(d.centre[1] - d.radius for d in DOMES) - margin
    high_z = max(d.centre[1] + d.radius for d in DOMES) + margin
    low_y = min(d.floor_y for d in DOMES) - margin
    high_y = max(DOCK[1], *(d.top_y for d in DOMES)) + margin
    return (low_x, low_y, low_z), (high_x, high_y, high_z)


BOUNDS: tuple[Pos, Pos] = station_bounds()


def in_station(x: float, y: float, z: float) -> bool:
    """is a position inside the station's box?"""
    low, high = BOUNDS
    return all(lo <= v <= hi for lo, v, hi in zip(low, (x, y, z), high, strict=True))


def station_chunks() -> tuple[tuple[int, int], tuple[int, int]]:
    """the chunks (x, z) of the low and high corners of the station's box"""
    low, high = BOUNDS
    return (low[0] >> 4, low[2] >> 4), (high[0] >> 4, high[2] >> 4)


# ----------------------------------------------------------------------------
# the offline check


def check_layout(
    domes: tuple[Dome, ...] = DOMES, tunnels: tuple[Tunnel, ...] | None = None
) -> list[str]:
    """
    Check a layout against the rules of the plan, without a server.

    :returns: the problems found, one line each; empty if there are none
    """
    if tunnels is None:
        tunnels = TUNNELS if domes is DOMES else make_tunnels(domes)
    problems = []
    count = len(domes)

    if [d.index for d in domes] != list(range(count)):
        problems.append("dome indexes are not 0, 1, 2 ... in order")
    if len({d.key for d in domes}) != count:
        problems.append("two domes share a key")
    for d in domes:
        if d.diameter % 2 or d.diameter not in (32, 48, 64):
            problems.append(f"dome {d.key}: diameter {d.diameter} is not 32, 48 or 64")

    # the ring: a tunnel from each dome to the next, the last back to the first
    if len(tunnels) != count:
        problems.append(f"{len(tunnels)} tunnels for {count} domes: ring not closed")
    for i, t in enumerate(tunnels):
        if (t.start, t.end) != (i, (i + 1) % count):
            problems.append(f"tunnel {i} joins {t.start} to {t.end}: ring not closed")
            continue
        name = f"tunnel {i} ({domes[t.start].key} to {domes[t.end].key})"
        if not TUNNEL_MIN <= t.length <= TUNNEL_MAX:
            problems.append(
                f"{name} is {t.length} long, not {TUNNEL_MIN} to {TUNNEL_MAX}"
            )
        if (t.a[0] != t.b[0]) == (t.a[2] != t.b[2]):
            problems.append(f"{name} does not run along x or z")
        for end, d in ((t.a, domes[t.start]), (t.b, domes[t.end])):
            away = abs(end[0] - d.centre[0]) + abs(end[2] - d.centre[1])
            on_axis = end[0] == d.centre[0] or end[2] == d.centre[1]
            if away != d.radius or not on_axis or end[1] != d.floor_y:
                problems.append(f"{name}: end {end} is not on the shell of {d.key}")
        # it must not pass through (or close by) any other dome
        for d in domes:
            if d.index in (t.start, t.end):
                continue
            near_x = min(max(d.centre[0], min(t.a[0], t.b[0])), max(t.a[0], t.b[0]))
            near_z = min(max(d.centre[1], min(t.a[2], t.b[2])), max(t.a[2], t.b[2]))
            gap = ((near_x - d.centre[0]) ** 2 + (near_z - d.centre[1]) ** 2) ** 0.5
            if gap < d.radius + DOME_GAP_MIN / 2:
                problems.append(f"{name} passes too close to dome {d.key}")

    # domes must not overlap: joined ones are a tunnel apart, others further
    for i, d in enumerate(domes):
        for e in domes[i + 1 :]:
            apart = (
                (d.centre[0] - e.centre[0]) ** 2 + (d.centre[1] - e.centre[1]) ** 2
            ) ** 0.5
            gap = apart - d.radius - e.radius
            joined = (e.index - d.index) % count in (1, count - 1)
            least = TUNNEL_MIN - 1 if joined else DOME_GAP_MIN
            if gap < least:
                problems.append(
                    f"domes {d.key} and {e.key} are {gap:.0f} apart, less than {least}"
                )

    for d in domes:
        if d.floor_y >= SEA_LEVEL - 1:
            problems.append(f"dome {d.key}: floor y {d.floor_y} is not under the sea")
    return problems


def describe() -> str:
    """the layout as a table of text, for logs and reports"""
    lines = [
        f"spawn {SPAWN}, shore landing {SHORE_LANDING}, dock {DOCK}, "
        f"lift at {LIFT_XZ} from y {LIFT_TOP_Y} down to y {LIFT_BOTTOM_Y}",
        f"station box {BOUNDS[0]} to {BOUNDS[1]}",
    ]
    for d in DOMES:
        lines.append(
            f"dome {d.index} {d.name} ({d.key}): centre {d.centre}, "
            f"diameter {d.diameter}, floor y {d.floor_y}, top y {d.top_y}, "
            f"water above {d.water_above}"
        )
    for t in TUNNELS:
        lines.append(
            f"tunnel {t.index} {DOMES[t.start].key} to {DOMES[t.end].key}: "
            f"{t.a} to {t.b}, along {t.axis}, length {t.length}, rise {t.rise}"
        )
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# the check against a survey of the site

#: the survey that `survey_site.py` writes, beside this file
SURVEY_FILE = "site_survey.npz"
#: sea floor this far below the middle sea floor under a dome is a ravine
RAVINE_DROP = 5
#: a dome's floor may stand this far above the middle sea floor under it
FLOOR_ABOVE_MAX = 3
#: the row may cross land only within this many blocks of the shore landing
SHORE_REACH = 6


def survey_site(survey_path: str | None = None) -> tuple[list[str], list[str]]:
    """
    Compare the layout with a survey of the sea (the file `survey_site.py`
    writes): does the station fit this site?

    :param survey_path: the survey file; by default `SURVEY_FILE` beside
        this module
    :returns: the problems found, and notes: what a builder should know
        that is not wrong (how deep each dome lies, ravines to fill,
        structures under the site)
    :raises FileNotFoundError: if there is no such file
    """
    from pathlib import Path

    import numpy as np  # only this check needs numpy

    path = Path(survey_path) if survey_path else Path(__file__).with_name(SURVEY_FILE)
    data = np.load(path)
    floor = data["floor"].astype(int)
    wet = data["wet"] > 0
    bubbles = data["wet"] == 2
    x0, z0 = (int(v) for v in data["origin"])
    x9, z9 = x0 + floor.shape[0] - 1, z0 + floor.shape[1] - 1
    problems: list[str] = []
    notes: list[str] = []

    def inside(x: int, z: int) -> bool:
        return x0 <= x <= x9 and z0 <= z <= z9

    (bx1, by1, bz1), (bx2, _, bz2) = BOUNDS
    points = {"the station's box": [(bx1, bz1), (bx2, bz2)]}
    points["the shore landing"] = [(SHORE_LANDING[0], SHORE_LANDING[2])]
    outside = [what for what, at in points.items() if not all(inside(*p) for p in at)]
    if outside:
        return [
            f"{' and '.join(outside)}: outside the survey "
            f"(x {x0}..{x9}, z {z0}..{z9}): survey a larger area"
        ], notes

    surface = SEA_LEVEL - 1
    for d in DOMES:
        (cx, cz), r = d.centre, d.radius
        xs, zs = np.arange(cx - r, cx + r + 1), np.arange(cz - r, cz + r + 1)
        disc = (xs[:, None] - cx) ** 2 + (zs[None, :] - cz) ** 2 <= r * r
        cut = np.s_[cx - r - x0 : cx + r + 1 - x0, cz - r - z0 : cz + r + 1 - z0]
        under, water = floor[cut][disc], wet[cut][disc]
        middle = int(np.median(under))
        name = f"dome {d.index} ({d.key})"
        if not water.all():
            problems.append(f"{name}: {1 - water.mean():.0%} of its footprint is land")
        if d.top_y > surface:
            problems.append(
                f"{name}: its top (y {d.top_y}) is {d.top_y - surface} above the "
                f"sea's surface (y {surface}); it needs a floor that much lower"
            )
        if d.floor_y > middle + FLOOR_ABOVE_MAX:
            problems.append(
                f"{name}: its floor (y {d.floor_y}) is {d.floor_y - middle} above "
                f"the sea floor (y {middle}): it would not stand on it"
            )
        ravine = (under < middle - RAVINE_DROP).mean()
        notes.append(
            f"{name}: top {surface - d.top_y} below the surface; sea floor under "
            f"it y {under.min()}..{under.max()}, middle {middle}; floor y "
            f"{d.floor_y} is {middle - d.floor_y} below that; {ravine:.0%} ravine"
        )

    for t in TUNNELS:
        (dx, dz), steps = t.step, range(t.length + 1)
        xs = np.array([t.a[0] + dx * i for i in steps]) - x0
        zs = np.array([t.a[2] + dz * i for i in steps]) - z0
        under, low = floor[xs, zs], min(t.a[1], t.b[1])
        name = f"tunnel {t.index} ({DOMES[t.start].key} to {DOMES[t.end].key})"
        if not wet[xs, zs].all():
            problems.append(f"{name} crosses land")
        gap = (under < low - RAVINE_DROP).mean()
        notes.append(
            f"{name}: sea floor under it y {under.min()}..{under.max()}, its "
            f"floor y {t.a[1]} to {t.b[1]}; {gap:.0%} of it over a ravine"
        )

    # the shore landing, and the row from it to the dock
    sx, sy, sz = SHORE_LANDING
    if wet[sx - x0, sz - z0] or floor[sx - x0, sz - z0] != sy:
        problems.append(
            f"the shore landing {SHORE_LANDING} is not the top of the ground "
            f"(the survey has {'water over ' if wet[sx - x0, sz - z0] else ''}"
            f"y {floor[sx - x0, sz - z0]} there)"
        )
    row = ((DOCK[0] - sx) ** 2 + (DOCK[2] - sz) ** 2) ** 0.5
    count = int(row) + 1
    xs = np.linspace(sx, DOCK[0], count).round().astype(int)
    zs = np.linspace(sz, DOCK[2], count).round().astype(int)
    away = ((xs - sx) ** 2 + (zs - sz) ** 2) ** 0.5
    dry = ~wet[xs - x0, zs - z0]
    if not (dry & (away <= SHORE_REACH)).sum() < (away <= SHORE_REACH).sum():
        problems.append(f"no water within {SHORE_REACH} of the shore landing's row")
    if (dry & (away > SHORE_REACH)).any():
        first = int(np.argmax(dry & (away > SHORE_REACH)))
        problems.append(
            f"the row from the shore landing to the dock crosses land at "
            f"({xs[first]}, {zs[first]})"
        )
    if bubbles[xs - x0, zs - z0].any():
        problems.append(
            "the row to the dock crosses a bubble column, which sinks boats"
        )
    depth = (surface - floor[xs - x0, zs - z0])[~dry]
    notes.append(
        f"the row from the shore landing to the dock is {row:.0f} blocks, "
        f"least depth {depth.min() if depth.size else 0}"
    )
    box = wet[bx1 - x0 : bx2 + 1 - x0, bz1 - z0 : bz2 + 1 - z0]
    if not box.all():
        notes.append(f"{1 - box.mean():.1%} of the station's box is land")

    # blocks of structures (mineshafts, ruins ...) under or beside the box
    if "suspects" in data:
        names = [str(n) for n in data["suspect_names"]]
        near = [
            row
            for row in data["suspects"].tolist()
            if bx1 - 15 <= row[0] <= bx2
            and bz1 - 15 <= row[1] <= bz2
            and row[3] >= by1 - MARGIN
            and "magma" not in names[row[5]]
        ]
        if near:
            kinds = sorted({names[row[5]].removeprefix("minecraft:") for row in near})
            notes.append(
                f"structure blocks ({', '.join(kinds)}) in "
                f"{len({(row[0], row[1]) for row in near})} cells of 16 x 16 in or "
                f"beside the station's box, y {min(row[2] for row in near)}.."
                f"{max(row[3] for row in near)} (the lowest dome floor is y "
                f"{min(d.floor_y for d in DOMES)})"
            )
    for spawner in MINESHAFT_SPAWNERS:
        if in_station(*spawner) or dome_at(spawner[0], BASE_FLOOR_Y, spawner[2]):
            notes.append(f"a spawner at {spawner} is under the station: remove it")
    return problems, notes


def check_site(survey_path: str | None = None) -> list[str]:
    """
    Check the layout against a survey of the site, without a server: every
    dome over water, standing on the sea floor with its top at or below the
    surface; no tunnel crossing land; the shore landing on the shore and the
    row from it to the dock over water. See `survey_site` for the notes.

    :returns: the problems found, one line each; empty if there are none
    :raises FileNotFoundError: if there is no survey file
    """
    return survey_site(survey_path)[0]


if __name__ == "__main__":
    print(describe())
    found = check_layout()
    try:
        site_problems, site_notes = survey_site()
        print("\n".join(site_notes))
        found += site_problems
    except FileNotFoundError:
        print(f"no {SURVEY_FILE}: the layout is not checked against the site")
    print("\n".join(found) if found else "layout OK")
    raise SystemExit(1 if found else 0)
