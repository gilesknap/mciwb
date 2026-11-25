"""
Can a visitor walk to every room? A flood fill over the castle's blocks,
from the bridge outside the main gate.

The blocks come from the world's region files (``WORLD_FOLDER``, read after
a ``save-all``; RCON is far too slow for the ~3 million blocks of a site) or
from a dump made with `dump`. ``verify_castle.py`` runs `problems` when
``WORLD_FOLDER`` is set; standalone, on a dump::

    ORIGIN=-300,92,-40 DUMP=site.npz python reach.py

A visitor is a block wide and two high. They walk between cells with free
feet and head and something to stand on, climb one block (a jump, with
headroom), drop at most `MAX_DROP` blocks (more hurts), climb ladders, swim
up and down water, open every door, fence gate and wooden trapdoor (iron
doors here all have buttons), and walk through a hidden door as if its
mechanism had opened it (`secret_doors`). Each space in `spaces` (its
standing cells) must have a cell the fill reached; `doors` checks every
round tower's doorways on their own, and `stair_top_problems` that each
tower's stair or ladder comes out on its top floor with headroom.
"""

from __future__ import annotations

import os
import sys
from collections import deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

import castle_lib as L  # noqa: E402
from castle_layout import (  # noqa: E402
    ALCH,
    BAILEY_TOWERS,
    BARRACKS,
    CELL_DOOR,
    CELL_LEVER,
    CELL_ROWS,
    CHAPEL,
    CRYPT_DOOR,
    DUNGEON_Y,
    GATE_TOWERS,
    GATEHOUSE,
    KEEP,
    KEEP_FLOORS,
    KEEP_ROOF,
    LIBRARY_DOOR,
    MAIN_GATE,
    SMITHY,
    STABLES,
    TELEPORTS,
    TOWER_DOORS,
    TOWER_LEVELS,
    UD,
    UPPER_TOWERS,
    VAULT,
    VAULT_Y,
    WALL_H,
    WELL_TUNNEL_X,
    XG,
    YU,
    ZS,
    V,
    W,
    site_box,
)
from mcwb import Vec3

MAX_DROP = 3  # the furthest a visitor drops without getting hurt

# how a visitor gets on with each kind of block
OPEN, SOLID, BLOCK, CLIMB, SWIM, DOOR, HATCH, PANE = range(8)
_OPEN = {
    "air", "cave_air", "void_air", "redstone_wire", "repeater", "comparator",
    "tripwire", "tripwire_hook", "lever", "stone_button", "torch", "wall_torch",
    "redstone_torch", "redstone_wall_torch", "lantern", "soul_lantern",
    "cobweb", "snow", "end_rod", "lightning_rod", "skeleton_skull",
    "amethyst_cluster", "bell", "white_candle", "short_grass", "tall_grass",
    "fern", "bush", "leaf_litter", "glow_lichen", "brown_mushroom",
    "red_mushroom", "dandelion", "poppy", "cornflower", "lilac", "peony",
}  # fmt: skip
_BLOCK = {"lava"}
# thin, but something to stand on (the portcullis's bars sink into the floor)
_PANE = {"iron_bars", "iron_chain", "glass_pane"}


def kind(name: str) -> int:
    """the class of a block state (``minecraft:oak_stairs[facing=east]``)"""
    base = name.split("[")[0].removeprefix("minecraft:")
    state = name.partition("[")[2]
    if (
        base in _OPEN
        or base.endswith(("_carpet", "_sign", "_banner", "_pressure_plate"))
        or "lightning_rod" in base
    ):
        return OPEN
    if base in ("ladder", "vine"):
        return CLIMB
    if base in ("water", "bubble_column"):
        return SWIM
    if base.endswith(("_door", "_fence_gate")):
        return DOOR
    if base.endswith("_trapdoor"):
        # an iron one opens only by redstone: a closed one is floor (the
        # pit's), an open one a grille (a cell's front)
        if base == "iron_trapdoor":
            return BLOCK if "open=true" in state else SOLID
        return HATCH
    if base in _PANE or base.endswith("_pane"):
        return PANE
    if base in _BLOCK or base.endswith(("_fence", "_wall")):
        return BLOCK
    return SOLID


PASS = (OPEN, CLIMB, SWIM, DOOR, HATCH)  # room for feet or head
FLOOR = (SOLID, HATCH, PANE)  # something to stand on


class Grid:
    """the blocks of a box: ``k[x, y, z]`` is the class of the block at
    ``origin + (x, y, z)``"""

    def __init__(self, ids: np.ndarray, names: list[str], origin: Vec3):
        self.names = [str(n) for n in names]
        self.ids = ids
        self.origin = Vec3(*(int(v) for v in origin))
        lookup = np.array([kind(n) for n in self.names], dtype=np.uint8)
        self.k = lookup[ids]
        self.shape = ids.shape

    def name(self, p: Vec3) -> str:
        i = self.index(p)
        return self.names[self.ids[i]] if i else "outside"

    def index(self, p: Vec3) -> tuple[int, int, int] | None:
        i = (
            int(p.x) - self.origin.x,
            int(p.y) - self.origin.y,
            int(p.z) - self.origin.z,
        )
        if all(0 <= a < n for a, n in zip(i, self.shape, strict=True)):
            return i
        return None

    def open_cells(self, cells: list[Vec3]) -> None:
        """treat these cells as air (a hidden door, opened)"""
        for p in cells:
            i = self.index(p)
            if i:
                self.k[i] = OPEN


def load_dump(path: str | Path) -> Grid:
    d = np.load(path)
    return Grid(d["ids"], list(d["names"]), Vec3(*d["origin"]))


def _state_name(entry) -> str:
    """a palette entry as a block state string, properties included"""
    if isinstance(entry, str):
        return entry if ":" in entry.split("[")[0] else "minecraft:" + entry
    name = entry.get("id") or entry.get("Name") or entry.get("")
    props = entry.get("properties") or entry.get("Properties") or {}
    if ":" not in name:
        name = "minecraft:" + name
    if props:
        name += "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"
    return name


def _indices(data, size: int) -> np.ndarray:
    """a chunk section's 4096 palette indices (y, z, x order): each 64-bit
    long holds as many whole indices as fit, lowest first, at least 4 bits"""
    if data is None or size == 1:
        return np.zeros(4096, dtype=np.int64)
    bits = max(4, (size - 1).bit_length())
    longs = np.asarray(data).astype(">i8").view(">u8").astype(np.uint64)
    shifts = np.arange(64 // bits, dtype=np.uint64) * np.uint64(bits)
    values = (longs[:, np.newaxis] >> shifts) & np.uint64((1 << bits) - 1)
    return values.ravel()[:4096].astype(np.int64)


def load_world(world_folder: str | Path) -> Grid:
    """the site's blocks from the world's region files, with their states
    (mciwb's reader keeps only the names: the states say which trapdoors are
    open, and which way the stairs face)"""
    from mciwb.anvil import RegionFile, region_folder

    a, b = site_box()
    lo = Vec3(min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))
    hi = Vec3(max(a.x, b.x), max(a.y, b.y), max(a.z, b.z))
    folder = region_folder(Path(world_folder))
    names: dict[str, int] = {"minecraft:air": 0}
    ids = np.zeros((hi.x - lo.x + 1, hi.y - lo.y + 1, hi.z - lo.z + 1), np.uint16)
    regions: dict[tuple[int, int], RegionFile] = {}
    for cx in range(lo.x >> 4, (hi.x >> 4) + 1):
        for cz in range(lo.z >> 4, (hi.z >> 4) + 1):
            key = (cx >> 5, cz >> 5)
            if key not in regions:
                regions[key] = RegionFile(folder / f"r.{key[0]}.{key[1]}.mca")
            chunk = regions[key].chunk(cx, cz)
            if chunk is None:
                continue
            x0, x1 = max(lo.x, cx * 16), min(hi.x, cx * 16 + 15)
            z0, z1 = max(lo.z, cz * 16), min(hi.z, cz * 16 + 15)
            for section in chunk.get("sections", []):
                states = section.get("block_states")
                sy = section["Y"]
                y0, y1 = max(lo.y, sy * 16), min(hi.y, sy * 16 + 15)
                if states is None or y0 > y1:
                    continue
                palette = [
                    names.setdefault(_state_name(e), len(names))
                    for e in states["palette"]
                ]
                local = _indices(states.get("data"), len(palette))
                blocks = np.asarray(palette)[local].reshape(16, 16, 16)
                blocks = blocks.transpose(2, 0, 1)  # [y][z][x] -> [x][y][z]
                ids[
                    x0 - lo.x : x1 - lo.x + 1,
                    y0 - lo.y : y1 - lo.y + 1,
                    z0 - lo.z : z1 - lo.z + 1,
                ] = blocks[
                    x0 - cx * 16 : x1 - cx * 16 + 1,
                    y0 - sy * 16 : y1 - sy * 16 + 1,
                    z0 - cz * 16 : z1 - cz * 16 + 1,
                ]
    return Grid(ids, list(names), lo)


def dump(world_folder: str | Path, out: str | Path) -> None:
    g = load_world(world_folder)
    np.savez_compressed(
        out, ids=g.ids, names=np.array(g.names), origin=np.array(tuple(g.origin))
    )


# ---------------------------------------------------------------- walking

UP = (0, 1, 0)


def _flood(g: Grid, start: tuple[int, int, int]) -> np.ndarray:
    """every cell (grid index) where a visitor's feet can be, from start"""
    k = g.k
    nx, ny, nz = k.shape
    seen = np.zeros(k.shape, dtype=bool)

    def at(x, y, z):
        if 0 <= x < nx and 0 <= y < ny and 0 <= z < nz:
            return k[x, y, z]
        return OPEN if y >= ny else SOLID  # open sky above the box

    def free(x, y, z):  # feet and head
        return at(x, y, z) in PASS and at(x, y + 1, z) in PASS

    def held(x, y, z):  # does the visitor stay here?
        here = at(x, y, z)
        if here in (CLIMB, SWIM):
            return True
        below = at(x, y - 1, z)
        return below in FLOOR

    def settle(x, y, z):
        """where a visitor stepping into a free cell ends up: here, or as far
        as they fall (None if further than MAX_DROP onto something hard)"""
        for drop in range(0, 64):
            if held(x, y - drop, z):
                if drop > MAX_DROP and at(x, y - drop, z) != SWIM:
                    return None
                return (x, y - drop, z)
            if at(x, y - drop - 1, z) not in PASS:
                return None
        return None

    q = deque()
    s = settle(*start)
    if s is None:
        raise ValueError(f"nowhere to stand at the start {start}")
    seen[s] = True
    q.append(s)
    while q:
        x, y, z = q.popleft()
        nxt = []
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, c = x + dx, z + dz
            if free(a, y, c):
                nxt.append(settle(a, y, c))
            # a step (or jump) up one block, with headroom for the jump
            elif at(a, y, c) in FLOOR and free(a, y + 1, c) and at(x, y + 2, z) in PASS:
                nxt.append((a, y + 1, c))
        here = at(x, y, z)
        if here in (CLIMB, SWIM) and free(x, y + 1, z):
            nxt.append((x, y + 1, z))  # up a ladder or through water
        below = at(x, y - 1, z)
        if below in (CLIMB, SWIM, HATCH, OPEN, DOOR) and at(x, y - 1, z) in PASS:
            nxt.append(settle(x, y - 1, z))  # down a ladder, through a hatch
        for n in nxt:
            if n is not None and not seen[n]:
                seen[n] = True
                q.append(n)
    return seen


def secret_doors() -> list[Vec3]:
    """the cells of the hidden doors, as if their mechanisms had opened them"""
    east, south, west = Vec3(1, 0, 0), Vec3(0, 0, 1), Vec3(-1, 0, 0)
    cells = L.hidden_door_cells(V(*LIBRARY_DOOR), east, south)["door"]
    for base, lever_b in ((CELL_DOOR, CELL_LEVER), (CRYPT_DOOR, -1)):
        d = L.hidden_door_cells(V(*base), west, south, trigger="lever", lever_b=lever_b)
        cells += d["door"]
    return cells


# ---------------------------------------------------------------- the spaces


def _box(x1, z1, x2, z2, y) -> list[tuple[int, int, int]]:
    return [(x, y, z) for x in range(x1, x2 + 1) for z in range(z1, z2 + 1)]


def _disc(cx, cz, r, y) -> list[tuple[int, int, int]]:
    return [(x, y, z) for x, z in L.disc(cx, cz, r)]


def spaces() -> dict[str, list[tuple[int, int, int]]]:
    """every room and interior space: its standing cells (local); a space
    counts as reached if the visitor can stand in any of them"""
    out: dict[str, list[tuple[int, int, int]]] = {}
    kx1, kz1, kx2, kz2 = KEEP
    ix1, iz1, ix2, iz2 = kx1 + 3, kz1 + 3, kx2 - 3, kz2 - 3
    f1, f2, f3 = KEEP_FLOORS
    out["keep: great hall"] = _box(ix1, iz1, 66, iz2, f1)
    out["keep: kitchen"] = _box(68, iz1, ix2, 27, f1)
    out["keep: ground-floor stair hall"] = _box(68, 29, ix2, iz2, f1)
    out["keep: library"] = _box(ix1, iz1, 57, iz2, f2)
    out["keep: gallery"] = _box(63, iz1, 66, iz2, f2)
    out["keep: armoury"] = _box(68, iz1, ix2, 27, f2)
    out["keep: first-floor stair hall"] = _box(68, 29, ix2, iz2, f2)
    out["keep: lord's chamber"] = _box(ix1, iz1, 57, iz2, f3)
    out["keep: map room"] = _box(59, iz1, 66, iz2, f3)
    out["keep: guest rooms"] = _box(69, iz1, ix2, 27, f3)
    out["keep: second-floor stair hall"] = _box(68, 29, ix2, iz2, f3)
    out["keep: roof terrace"] = _box(ix1, iz1, ix2, iz2, KEEP_ROOF)
    out["keep: lantern tower"] = _disc(XG, (kz1 + kz2) // 2, 1, KEEP_ROOF)
    for x in (kx1, kx2):
        for z in (kz1, kz2):
            for fy in (*KEEP_FLOORS, KEEP_ROOF):
                out[f"keep turret {x},{z} at {fy}"] = _disc(x, z, 2, fy)
    towers = {
        **{n: (cx, cz, r, [0, WALL_H]) for n, (cx, cz, r) in BAILEY_TOWERS.items()},
        **{n: (cx, cz, r, [0, 16]) for n, (cx, cz, r) in GATE_TOWERS.items()},
        **{
            n: (cx, cz, r, [YU, YU + WALL_H] + ([YU + WALL_H + 6] if r == 6 else []))
            for n, (cx, cz, r) in UPPER_TOWERS.items()
        },
    }
    for n in ("west junction tower", "east junction tower"):
        cx, cz, r = BAILEY_TOWERS[n]
        towers[n] = (cx, cz, r, [0, WALL_H, YU, YU + WALL_H])
    for n, (cx, cz, r, floors) in towers.items():
        for fy in floors:
            out[f"{n} at {fy}"] = _disc(cx, cz, r - 2, fy)
    # the tops of the towers with battlements, up their stairs or ladders
    for n, (_y0, _floors, y_top, roofed, _stair) in TOWER_LEVELS.items():
        if not roofed:
            cx, cz, r, _wall, _doors = TOWER_DOORS[n]
            out[f"{n}'s top at {y_top}"] = _disc(cx, cz, r - 1, y_top)
    for i, fy in enumerate((YU, YU + 8, YU + 16, YU + 24)):
        out[f"alchemist's tower floor {i + 1}"] = _disc(*ALCH, 4, fy)
    cx1, cz1, cx2, cz2 = CHAPEL
    out["chapel"] = _box(cx1 + 1, cz1 + 1, cx2 - 1, cz2 - 1, YU)
    out["chapel bell tower"] = _box(cx1 - 1, cz2, cx1 + 3, cz2 + 4, YU)
    out["chapel belfry"] = _box(cx1 - 1, cz2, cx1 + 3, cz2 + 4, YU + 22)
    out["crypt"] = _box(89, 17, 107, 29, 8)
    out["crypt's end chamber"] = _box(72, 20, 75, 26, 8)
    x1, z1, x2, z2 = VAULT
    out["vault"] = _box(x1, z1, x2, z2, VAULT_Y)
    out["library's hidden room"] = _box(59, 15, 61, 24, f2)
    gx1, gz1, gx2, gz2 = GATEHOUSE
    out["gatehouse guard room"] = _box(gx1 + 7, gz1 + 1, MAIN_GATE[0] - 2, gz2 - 2, 0)
    out["gatehouse winch room"] = _box(gx1 + 7, gz1 + 1, MAIN_GATE[1] + 3, gz2 - 2, 4)
    out["gatehouse roof"] = _box(gx1 + 1, gz1 + 1, gx2 - 1, gz2 - 1, 16)
    out["middle gate winch room"] = _box(XG - 2, UD - 3, XG + 3, UD - 1, YU + 4)
    out["bailey: west wall walk"] = _box(1, UD + 8, 2, ZS - 8, WALL_H)
    out["bailey: east wall walk"] = _box(W - 3, UD + 8, W - 2, ZS - 8, WALL_H)
    out["bailey: south wall walk, west"] = _box(10, ZS - 2, gx1 - 6, ZS - 1, WALL_H)
    out["bailey: south wall walk, east"] = _box(gx2 + 6, ZS - 2, W - 10, ZS - 1, WALL_H)
    out["upper ward: west wall walk"] = _box(1, 10, 2, UD - 10, YU + WALL_H)
    out["upper ward: east wall walk"] = _box(W - 3, 10, W - 2, UD - 10, YU + WALL_H)
    out["upper ward: north wall walk"] = _box(10, 1, W - 10, 2, YU + WALL_H)
    out["upper ward: south wall walk, west"] = _box(
        10, UD - 3, XG - 11, UD - 2, YU + WALL_H
    )
    out["upper ward: south wall walk, east"] = _box(
        XG + 11, UD - 3, W - 10, UD - 2, YU + WALL_H
    )
    sx1, sz1, sx2, sz2 = STABLES
    for z in range(sz1, sz2, 5):
        out[f"stables: stall {z}"] = _box(sx1 + 1, z + 1, sx2 - 1, z + 4, 0)
    bx1, bz1, bx2, bz2 = BARRACKS
    out["barracks"] = _box(bx1 + 1, bz1 + 1, bx2 - 1, bz2 - 1, 0)
    mx1, mz1, mx2, mz2 = SMITHY
    out["smithy"] = _box(mx1 + 1, mz1 + 1, mx2 - 1, mz2 - 1, 0)
    y = DUNGEON_Y
    out["dungeon: pit corridor"] = _box(95, 121, 95, 133, y)
    out["dungeon: guard room"] = _box(91, 135, 99, 139, y)
    out["dungeon: cell corridor"] = _box(70, 136, 90, 138, y)
    for zc, _zdoor, _into, xs in CELL_ROWS:
        for x in xs:
            out[f"dungeon: cell {x},{zc}"] = _box(x, zc, x + 2, zc + 2, y)
    out["dungeon: hidden chamber"] = _box(66, 133, 68, 139, y)
    out["well tunnel"] = _box(WELL_TUNNEL_X, 106, WELL_TUNNEL_X, 138, -8)
    out["catacombs: oubliette"] = _box(92, 124, 98, 131, -15)
    out["catacombs: trap corridor"] = _box(94, 109, 96, 123, -15)
    out["catacombs: lower treasury"] = _box(101, 105, 109, 113, -15)
    return out


# rooms behind a hidden door, which the fill reaches only through it
SECRET = (
    "library's hidden room",
    "crypt's end chamber",
    "dungeon: hidden chamber",
    "vault",
)


def reached(g: Grid, secrets_open: bool = True) -> np.ndarray:
    if secrets_open:
        g.open_cells(secret_doors())
    x, y, z = TELEPORTS["outside the main gate, on the bridge"]
    start = g.index(V(x, y, z))
    return _flood(g, start)


def problems(g: Grid) -> list[str]:
    """the spaces a visitor cannot walk to (secret doors opened), and why
    each looks closed off"""
    seen = reached(g)
    out = []
    for name, cells in spaces().items():
        idx = [g.index(V(*c)) for c in cells]
        idx = [i for i in idx if i is not None]
        if not any(seen[i] for i in idx):
            out.append(f"{name}: not reached (e.g. {_where(cells)})")
    return out


def _where(cells) -> str:
    x, y, z = cells[len(cells) // 2]
    p = V(x, y, z)
    return f"{p.x} {p.y} {p.z}"


# ---------------------------------------------------------------- tower doors


def door_cells(cx, cz, r, wall, dy, d, offset):
    """a round tower's doorway (as castle_lib.round_tower carves it): the
    carved cells, the cell inside it and the cell outside it (local)"""
    side = Vec3(-d.z, 0, d.x) * offset
    inner = L.disc(cx, cz, r - wall)
    carved = []
    for k in range(0, r + 1):
        q = Vec3(cx, 0, cz) + d * k + side
        if (q.x, q.z) in inner and k < r - wall:
            continue
        carved.append(Vec3(q.x, dy, q.z))
    first = carved[0]
    inside = Vec3(first.x - d.x, dy, first.z - d.z)
    out = Vec3(cx, dy, cz) + d * (r + 1) + side
    return carved, inside, out


def door_problems(kind_at, describe=None) -> list[str]:
    """
    Every round tower doorway: the cells it is cut through are clear, and
    on both sides a visitor can stand at its level (feet and head free, a
    floor under them): so it opens onto the walk, floor or ground it is
    for, not into masonry or a drop. ``kind_at(p)`` is the class (`kind`)
    of the block at world position p: `grid_kind` for a `Grid`, or
    verify_castle's reading over RCON; ``describe(p)`` names a block.
    """

    def free(p: Vec3) -> bool:
        return all(kind_at(Vec3(p.x, p.y + h, p.z)) in PASS for h in (0, 1))

    def stand(p: Vec3) -> bool:
        return free(p) and kind_at(Vec3(p.x, p.y - 1, p.z)) in FLOOR

    bad = []
    for name, (cx, cz, r, wall, doors) in TOWER_DOORS.items():
        for dy, d, offset in doors:
            carved, inside, out = door_cells(cx, cz, r, wall, dy, d, offset)
            what = []
            for label, q in (("inside", inside), ("outside", out)):
                p = V(*q)
                if not stand(p):
                    under = Vec3(p.x, p.y - 1, p.z)
                    seen = (
                        f": {describe(under)} under, {describe(p)}" if describe else ""
                    )
                    what.append(f"nowhere to stand {label}{seen}")
            if not all(free(V(*q)) for q in carved):
                what.append("the doorway is blocked")
            if what:
                o = V(*out)
                bad.append(
                    f"{name}, door {_compass(d)} at y {o.y} ({o.x} {o.y} {o.z}): {'; '.join(what)}"
                )
    return bad


def stair_top_problems(kind_at) -> list[str]:
    """
    Every round tower's way up (castle_lib.tower_stair_top): over its last
    steps or rungs a visitor has their feet and head free, and beside the
    last one a floor to step onto, so the stair does not end under a
    ceiling. ``kind_at`` as for `door_problems`.
    """

    def free(p: Vec3, height: int = 2) -> bool:
        return all(kind_at(Vec3(p.x, p.y + h, p.z)) in PASS for h in range(height))

    bad = []
    for name, (_y0, floors, y_top, roofed, stair) in TOWER_LEVELS.items():
        cx, cz, r, wall, _doors = TOWER_DOORS[name]
        up = L.tower_stair_top(
            cx, cz, r, wall, floors, y_top, roofed=roofed, stair=stair
        )
        if up is None:
            continue
        what = []
        shut = [V(*c) for c, height in up["climb"] if not free(V(*c), height)]
        if shut:
            what.append(
                "no headroom over the last steps at "
                + ", ".join(f"{p.x} {p.y} {p.z}" for p in shut)
            )
        exits = [V(*e) for e in up["exits"]]
        if not any(
            free(e) and kind_at(Vec3(e.x, e.y - 1, e.z)) in FLOOR for e in exits
        ):
            e = exits[0]
            what.append(f"nowhere to step off at {e.x} {e.y} {e.z}")
        if what:
            bad.append(f"{name}, up to y {exits[0].y}: {'; '.join(what)}")
    return bad


def _compass(d: Vec3) -> str:
    return {(0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west"}[
        (int(d.x), int(d.z))
    ]


def grid_kind(g: Grid):
    """`kind_at` for `door_problems`, from a grid"""
    return lambda p: _k(g, p)


def _k(g: Grid, p: Vec3) -> int:
    i = g.index(p)
    return g.k[i] if i else SOLID


def main() -> None:
    """print the problems, from a dump (DUMP=site.npz) or the world files"""
    dumped = os.environ.get("DUMP")
    g = load_dump(dumped) if dumped else load_world(os.environ["WORLD_FOLDER"])
    for line in door_problems(grid_kind(g), g.name):
        print("DOOR", line)
    for line in stair_top_problems(grid_kind(g)):
        print("STAIR", line)
    for line in problems(g):
        print("REACH", line)
    print("done")


if __name__ == "__main__":
    main()
