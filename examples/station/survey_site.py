"""
Survey the sea round the Drowned Station's site: the height of the sea floor
and where the water is, over a rectangle of whole chunks. It only reads the
world. The result is a small ``.npz`` file that `render_layout.py` draws and
that the positions in `station_layout.py` were chosen from.

Run it with ``mciwb run`` against the server::

    STATION_WORLD=/path/to/server/world mciwb run survey_site.py \
        --server HOST --port PORT

- ``STATION_WORLD``: the server's world folder (the one holding
  ``level.dat``), if this machine can read it. The blocks are then read from
  the region files, every column, in seconds. Without it the floor is sampled
  over RCON, one column in ``RCON_STEP`` each way, which is slow and coarse.
- ``STATION_SURVEY``: ``X1 Z1 X2 Z2``, the corners of the area (widened to
  whole chunks). Default `DEFAULT_AREA`.
- ``STATION_SURVEY_OUT``: the file to write. Default ``site_survey.npz``.

The area is unlikely to be loaded (or even generated), so it is force loaded
a batch of chunks at a time, saved, read, and released again. Chunks that
were force loaded before the survey are left as they were. It refuses to run
while a player is online.

The file holds ``floor`` (int8, indexed ``[x - x0][z - z0]``: the y of the
highest solid block of each column, clipped to 127), ``wet`` (uint8: 1 where
water lies on that block, 2 where that water is a bubble column right up to
the surface, which sinks boats; only a survey from the files finds those),
``origin`` (``x0, z0``), ``spawn`` (the world
spawn, if it was found), ``step`` (1, or ``RCON_STEP`` for a sampled
survey, whose columns are repeated to fill the array), and ``suspects`` with
``suspect_names``: where blocks that give away a structure (a mineshaft, a
ruin, a wreck, a monument) or magma were found, in cells of 16 x 16 columns
(see `suspect_cells`; only a survey from the files finds those).
"""

import gzip
import os
import re
import time
from pathlib import Path

import numpy as np

from mciwb.anvil import read_nbt, read_world_blocks
from mciwb.imports import Vec3, Volume, get_client, get_world, ground_heights
from mciwb.threads import reply_matches, retry_command

# the default area: 576 x 576 blocks round the nearest deep ocean to spawn
DEFAULT_AREA = (-256, -320, 319, 255)
SEA_LEVEL = 63  # the top layer of sea water is at y = SEA_LEVEL - 1
# a forceload command marks at most 256 chunks: batches of 16 x 16
BATCH_CHUNKS = 16
LOAD_TIMEOUT = 180.0  # seconds to wait for a batch of chunks to load
# the heights read from the files: the sea floor is far above the bottom
Y_LOW, Y_HIGH = 0, 127
RCON_STEP = 4

# what lies on the sea floor without being it
WATERY = {
    "minecraft:water",
    "minecraft:bubble_column",
    "minecraft:kelp",
    "minecraft:kelp_plant",
    "minecraft:seagrass",
    "minecraft:tall_seagrass",
    "minecraft:ice",
}
NOT_FLOOR = WATERY | {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
# blocks that give away a structure (a monument, wreck, ruin or mineshaft),
# and magma, whose bubble columns drag swimmers and boats down
SUSPECT = re.compile(
    r"prismarine|sea_lantern|sponge|_planks|chest|stone_bricks|_fence|"
    r"sandstone_stairs|magma_block|obsidian|spawner"
)

CHUNK = re.compile(r"\[(-?\d+), (-?\d+)\]")
# the whole reply of forceload query, with its list of chunks if any
FORCELOADED = (
    r"(No|A|\d+) force loaded chunks? (was|were) found in minecraft:overworld"
    r"( at: [-\d\[\], ]+)?"
)


def ask(command: str, pattern: str) -> str:
    """
    Send a command until its reply contains *pattern* (another RCON client
    can garble a reply). Returns the matching part, or the last reply.
    Only for commands that are safe to send twice.
    """
    client = get_client()
    return retry_command(
        lambda: client.run_raw(command), reply_matches(pattern), command
    )


def players_online() -> int:
    reply = ask("list", r"There are \d+ of a max")
    found = re.search(r"There are (\d+) of a max", reply)
    if not found:
        raise SystemExit(f"could not read the player list: {reply!r}")
    return int(found.group(1))


def forceloaded() -> set[tuple[int, int]]:
    """the overworld's force loaded chunks: read until two replies agree"""
    previous = None
    for _ in range(10):
        reply = ask("forceload query", FORCELOADED)
        chunks = {(int(x), int(z)) for x, z in CHUNK.findall(reply)}
        if chunks == previous:
            return chunks
        previous = chunks
    raise SystemExit("forceload query keeps changing: is something else running?")


def release(chunks: set[tuple[int, int]], keep: set[tuple[int, int]]) -> None:
    """
    Stop force loading a batch of chunks, except those in *keep*: row by row
    of chunks, splitting a row round a kept chunk.
    """
    for cz in sorted({cz for _, cz in chunks}):
        row = sorted(cx for cx, z in chunks if z == cz and (cx, cz) not in keep)
        runs: list[list[int]] = []
        for cx in row:
            if runs and runs[-1][1] == cx - 1:
                runs[-1][1] = cx
            else:
                runs.append([cx, cx])
        for first, last in runs:
            ask(
                f"forceload remove {first * 16} {cz * 16} {last * 16} {cz * 16}",
                r"Unmarked|No chunks were removed",
            )


def wait_loaded(chunks: set[tuple[int, int]]) -> None:
    """wait until every chunk of a batch is generated and loaded"""
    waiting = set(chunks)
    deadline = time.monotonic() + LOAD_TIMEOUT
    while waiting:
        for cx, cz in sorted(waiting):
            reply = ask(
                f"execute if loaded {cx * 16} 0 {cz * 16}", r"Test (passed|failed)"
            )
            if "passed" in reply:
                waiting.discard((cx, cz))
        if not waiting:
            return
        if time.monotonic() > deadline:
            raise SystemExit(f"{len(waiting)} chunks did not load, e.g. {min(waiting)}")
        # an empty server pauses, and then loads nothing until it is made to tick
        get_client().run_raw("tick sprint 20")
        time.sleep(1)


def world_spawn(folder: Path | None) -> tuple[int, int, int] | None:
    """the world spawn from level.dat, or None if it cannot be read"""
    if folder is None:
        return None
    try:
        data = read_nbt(gzip.decompress((folder / "level.dat").read_bytes()))
        data = data.get("Data", data)
        if "spawn" in data:  # Minecraft 26
            x, y, z = (int(v) for v in data["spawn"]["pos"])
        else:
            x, y, z = (int(data[k]) for k in ("SpawnX", "SpawnY", "SpawnZ"))
        return x, y, z
    except (OSError, KeyError, ValueError) as e:
        print(f"could not read the spawn from level.dat: {e}")
        return None


def read_files(
    folder: Path, x0: int, z0: int, x1: int, z1: int, suspects: dict
) -> tuple[np.ndarray, np.ndarray]:
    """the floor and wet arrays of a tile, from the region files"""
    vol = Volume.from_corners(Vec3(x0, Y_LOW, z0), Vec3(x1, Y_HIGH, z1))
    grid = read_world_blocks(folder, vol)
    names = grid.names
    ids = grid.ids  # [x][y][z]
    solid = np.array([n not in NOT_FLOOR for n in names])[ids]
    watery = np.array([n in WATERY for n in names])[ids]
    from_top = np.argmax(solid[:, ::-1, :], axis=1)
    top = ids.shape[1] - 1 - from_top
    has_floor = solid.any(axis=1)
    floor = np.where(has_floor, top + Y_LOW, Y_LOW - 1)
    above = np.minimum(top + 1, ids.shape[1] - 1)
    xi, zi = np.indices(top.shape)
    wet = watery[xi, above, zi] & has_floor & (above > top)
    # a column with no solid block at all in the range but water in it
    wet |= ~has_floor & watery.any(axis=1)
    wet = wet.astype(np.uint8)
    if "minecraft:bubble_column" in names:
        bubbles = ids[:, SEA_LEVEL - 1 - Y_LOW, :] == names.index(
            "minecraft:bubble_column"
        )
        wet[bubbles] = 2
    for index, name in enumerate(names):
        if SUSPECT.search(name):
            for x, y, z in np.argwhere(ids == index)[:2000]:
                suspects.setdefault(name, []).append(
                    (int(x) + x0, int(y) + Y_LOW, int(z) + z0)
                )
    if not has_floor.all() and not wet.any():
        print(f"  tile {x0},{z0}: columns with no blocks (chunks not saved?)")
    return floor, wet


def read_rcon(x0: int, z0: int, x1: int, z1: int) -> tuple[np.ndarray, np.ndarray]:
    """the floor and wet arrays of a tile, sampled over RCON"""
    xs = range(x0, x1 + 1, RCON_STEP)
    zs = range(z0, z1 + 1, RCON_STEP)
    columns = [(x, z) for x in xs for z in zs]
    floors = ground_heights(columns, "ocean_floor")
    tops = ground_heights(columns, "motion_blocking")
    floor = np.zeros((x1 - x0 + 1, z1 - z0 + 1), dtype=np.int64)
    wet = np.zeros(floor.shape, dtype=bool)
    for x, z in columns:
        cell = np.s_[x - x0 : x - x0 + RCON_STEP, z - z0 : z - z0 + RCON_STEP]
        floor[cell] = floors[x, z]
        # liquid (or ice ...) above the floor, up to sea level: the sea
        wet[cell] = floors[x, z] < tops[x, z] <= SEA_LEVEL - 1
    return floor, wet


def suspect_cells(suspects: dict) -> tuple[np.ndarray, np.ndarray]:
    """
    The suspect blocks gathered into cells of 16 x 16 columns: rows of
    ``cell x, cell z, lowest y, highest y, count, index of the name``
    (the cell's corner of least x and z), and the names
    """
    names = sorted(suspects)
    rows = []
    for index, name in enumerate(names):
        cells: dict[tuple[int, int], list[int]] = {}
        for x, y, z in suspects[name]:
            cells.setdefault((x >> 4 << 4, z >> 4 << 4), []).append(y)
        for (x, z), ys in sorted(cells.items()):
            rows.append((x, z, min(ys), max(ys), len(ys), index))
    return np.array(rows, dtype=np.int32).reshape(-1, 6), np.array(names, dtype=str)


def report_suspects(cells: np.ndarray, names: np.ndarray) -> None:
    if not len(cells):
        print("no structure blocks or magma found")
        return
    print("blocks that may belong to a structure (and magma), in 16 block cells:")
    for index, name in enumerate(names):
        mine = cells[cells[:, 5] == index]
        print(
            f"  {name}: {mine[:, 4].sum()} in {len(mine)} cells, "
            f"y {mine[:, 2].min()}..{mine[:, 3].max()}, "
            f"x {mine[:, 0].min()}..{mine[:, 0].max() + 15}, "
            f"z {mine[:, 1].min()}..{mine[:, 1].max() + 15}"
        )


def locate(x: int, z: int) -> None:
    """print the nearest ocean structures to the middle of the area"""
    for what in (
        "structure minecraft:monument",
        "structure minecraft:shipwreck",
        "structure #minecraft:ocean_ruin",
        "biome minecraft:deep_ocean",
    ):
        reply = ask(
            f"execute positioned {x} 0 {z} run locate {what}",
            r"The nearest .* is at \[.*\] \(\d+ blocks away\)|Could not find",
        )
        print(f"  locate {what}: {reply}")


def survey(area: tuple[int, int, int, int], folder: Path | None, out: Path) -> None:
    if players_online():
        raise SystemExit("a player is online: not surveying")
    cx0, cz0 = min(area[0], area[2]) >> 4, min(area[1], area[3]) >> 4
    cx1, cz1 = max(area[0], area[2]) >> 4, max(area[1], area[3]) >> 4
    x0, z0 = cx0 * 16, cz0 * 16
    size = ((cx1 - cx0 + 1) * 16, (cz1 - cz0 + 1) * 16)
    print(
        f"survey x {x0}..{x0 + size[0] - 1}, z {z0}..{z0 + size[1] - 1} "
        f"({(cx1 - cx0 + 1) * (cz1 - cz0 + 1)} chunks), "
        + (f"from the files of {folder}" if folder else "sampled over RCON"),
        flush=True,
    )
    floor = np.zeros(size, dtype=np.int64)
    wet = np.zeros(size, dtype=np.uint8)
    suspects: dict[str, list[tuple[int, int, int]]] = {}
    keep = forceloaded()
    print(f"force loaded before the survey (left alone): {sorted(keep)}")
    batch: set[tuple[int, int]] = set()
    try:
        for bx in range(cx0, cx1 + 1, BATCH_CHUNKS):
            for bz in range(cz0, cz1 + 1, BATCH_CHUNKS):
                ex = min(bx + BATCH_CHUNKS - 1, cx1)
                ez = min(bz + BATCH_CHUNKS - 1, cz1)
                batch = {
                    (cx, cz) for cx in range(bx, ex + 1) for cz in range(bz, ez + 1)
                }
                began = time.monotonic()
                ask(
                    f"forceload add {bx * 16} {bz * 16} {ex * 16} {ez * 16}",
                    r"Marked|No chunks were marked",
                )
                wait_loaded(batch)
                tile = (bx * 16, bz * 16, ex * 16 + 15, ez * 16 + 15)
                if folder:
                    ask("save-all flush", r"Saved the game")
                    part = read_files(folder, *tile, suspects)
                else:
                    part = read_rcon(*tile)
                cell = np.s_[
                    tile[0] - x0 : tile[2] - x0 + 1, tile[1] - z0 : tile[3] - z0 + 1
                ]
                floor[cell], wet[cell] = part
                release(batch, keep)
                batch = set()
                print(
                    f"  chunks {bx},{bz} to {ex},{ez}: floor y "
                    f"{part[0].min()}..{part[0].max()}, {(part[1] > 0).mean():.0%} water, "
                    f"{time.monotonic() - began:.0f} s",
                    flush=True,
                )
    finally:
        release(batch, keep)
        left = forceloaded()
        print(f"force loaded after the survey: {sorted(left)}")
        if left != keep:
            print(f"WARNING: not as before the survey: {sorted(left ^ keep)}")

    spawn = world_spawn(folder)
    cells, cell_names = suspect_cells(suspects)
    np.savez_compressed(
        out,
        floor=np.clip(floor, -128, 127).astype(np.int8),
        wet=wet,
        origin=np.array([x0, z0]),
        spawn=np.array(spawn if spawn else []),
        step=np.array(1 if folder else RCON_STEP),
        suspects=cells,
        suspect_names=cell_names,
    )
    sea = floor[wet > 0]
    print(f"world spawn: {spawn}")
    print(
        f"water over {(wet > 0).mean():.0%} of the area, "
        f"{(wet == 2).sum()} columns of bubbles reach the surface"
    )
    if sea.size:
        print(
            f"sea floor y {sea.min()}..{sea.max()}, median {int(np.median(sea))}; "
            f"depth below sea level {SEA_LEVEL}: "
            + ", ".join(
                f">={d}: {(SEA_LEVEL - 1 - sea >= d).sum() / floor.size:.0%}"
                for d in (10, 20, 25, 30)
            )
        )
    if folder:
        report_suspects(cells, cell_names)
    else:
        print("structures, magma and bubble columns are not looked for over RCON")
    locate(x0 + size[0] // 2, z0 + size[1] // 2)
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    get_world()  # connected by `mciwb run`
    text = os.environ.get("STATION_SURVEY", "").split()
    if len(text) not in (0, 4):
        raise SystemExit('give the area as STATION_SURVEY="X1 Z1 X2 Z2"')
    chosen = tuple(int(v) for v in text) if text else DEFAULT_AREA
    world_dir = os.environ.get("STATION_WORLD")
    survey(
        chosen,  # type: ignore[arg-type]
        Path(world_dir) if world_dir else None,
        Path(os.environ.get("STATION_SURVEY_OUT", "site_survey.npz")),
    )
