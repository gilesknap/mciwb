"""
The offline tests of the dressed sea floor (examples/station/seabed.py):
the plan against its own rules and against what every other stage builds,
its two stages run against the example's fake client, and that it comes
out the same every time. No server is needed. As in
test_station_example.py, each test runs in a Python of its own, in the
example's folder.
"""

import os
import subprocess
import sys
from pathlib import Path

STATION = Path(__file__).parents[1] / "examples" / "station"
# what the example reads from the environment
SETTINGS = ("STAGES", "CHECKS", "FORCE", "STATION_DATAPACKS_DIR")


def run(code: str, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in SETTINGS}
    result = subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=STATION,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_seabed_plan():
    """the plan keeps its rules: on the surveyed floor, coral in water,
    clear of the domes and tunnels, all five colours, and the rules find
    a plan that breaks them"""
    run(
        """
import seabed as S
import station_layout as layout

blocks, where = S.plan(), S.site()
assert S.problems() == []
kinds = S.census()
assert all(kinds[k] > 0 for k in kinds), kinds
assert kinds["lanterns"] > 100 and kinds["coral blocks"] > 500, kinds
for colour in S.COLOURS:
    for block in (S.coral_block(colour), S.coral(colour), S.fan(colour)):
        assert block in blocks.values(), block

# everything is in the box, in a column clear of every dome and tunnel
shut = S.protected()
taken = S.structure_cells()
for (x, y, z), block in blocks.items():
    assert layout.in_station(x, y, z)
    assert not shut[x - where.x0, z - where.z0], (x, y, z)
    assert not S.near((x, y, z), taken, 2), (x, y, z)
    floor = where.floor_at(x, z)
    assert S.FLOOR_LOW <= floor <= S.FLOOR_HIGH
    # on the floor from the survey: a lantern in it, the rest in a pile
    # that stands on it with no gap
    if block == S.LANTERN:
        assert y == floor
    elif "_wall_fan" not in block:
        assert all((x, h, z) in blocks for h in range(floor + 1, y)), (x, y, z)
    else:
        # (a wall fan hangs on a mound beside its column, over the floor)
        i, j = next(d for d, way in S.FACING.items() if f"facing={way}" in block)
        assert y > floor and S.is_coral_block(blocks[x - i, y, z - j])
    assert y <= floor + S.MOUND_MAX + 1 or "_wall_fan" in block
    if S.is_coral_block(block):
        assert S.touches_water(where, blocks, (x, y, z)), (x, y, z)
    elif block not in (S.LANTERN, S.CORE, S.SEAGRASS):
        assert "waterlogged=true" in block, block

# the rules find faults
def faults(change):
    return S.problems({**blocks, **change})

x, y, z = layout.START.floor_centre
assert any("not free" in p for p in faults({(x, y + 30, z): S.LANTERN}))
cell = next(c for c, b in blocks.items() if b == S.LANTERN)
up = (cell[0], cell[1] + 3, cell[2])
assert any("not in the floor" in p for p in faults({up: S.LANTERN}))
assert any("stands on nothing" in p for p in faults({up: S.coral("tube")}))
down = (cell[0], cell[1] - 1, cell[2])
around = {
    (down[0] + i, down[1] + j, down[2] + k): S.CORE
    for i in (-1, 0, 1)
    for j in (-1, 0, 1)
    for k in (-1, 0, 1)
}
around[down] = S.coral_block("fire")
assert any("touches no water" in p for p in faults(around))
assert any("not waterlogged" in p for p in faults({up: "minecraft:tube_coral"}))
"""
    )


def test_seabed_build():
    """the stages against the fake client: only the plan's cells, none of
    them a cell (or within two of a cell) that any other stage writes; the
    same blocks whatever was there before; the biome over the box"""
    run(
        """
import io
from contextlib import redirect_stdout

import build_station as B
import seabed as S
from fake_client import Recorder, World

assert list(B.STAGES)[-2:] == ["seabed", "seabed_water"]
assert {"seabed", "seabed_water"} <= set(B.written())
others = [s for s in B.STAGES if not s.startswith("seabed")]
with redirect_stdout(io.StringIO()):
    rest = B.offline_build(stages=others, force=False)
    rec = B.offline_build(stages=["seabed", "seabed_water"], force=False)
assert all(len(c.encode()) <= B.MAX_COMMAND for c in rec.commands)
assert not any("not loaded" in r or "Too many" in r for r in rec.replies)

# what is built is the plan, and nothing else
plan = S.plan()
built = dict(line.rsplit(" ", 1) for line in rec.world.dump())
assert built == {" ".join(map(str, c)): b for c, b in plan.items()}

# no cell of it is one another stage writes, or within two of one
written = {tuple(map(int, line.split(" ")[:3])) for line in rest.world.dump()}
assert len(written) > 100000
assert not [c for c in plan if S.near(c, written, 2)]

# run again over itself, and over an older dressing: the same blocks
with redirect_stdout(io.StringIO()):
    B.offline_build(stages=["seabed"], force=False, recorder=rec)
assert dict(line.rsplit(" ", 1) for line in rec.world.dump()) == built
old = Recorder(World(*B.station_box()))
free = [c for c in S.clear_boxes()][0][0]
old.world.setblock(free, S.coral_block("tube"))
old.world.setblock((free[0], free[1] + 1, free[2]), S.fan("horn"))
with redirect_stdout(io.StringIO()):
    B.offline_build(stages=["seabed"], force=False, recorder=old)
left = dict(line.rsplit(" ", 1) for line in old.world.dump())
assert {k: v for k, v in left.items() if v != S.WATER} == built

# the water: every column of the box, from its floor to the sea's top
lo, hi = B.station_box()
assert len(rec.biomes) == len(S.biome_boxes()) > 0
assert {b for _, _, b in rec.biomes} == {S.BIOME}
columns = set()
for a, b, _ in rec.biomes:
    assert (a[1], b[1]) == (lo[1], S.layout.SEA_LEVEL - 1)
    assert lo[0] <= a[0] <= b[0] <= hi[0] and lo[2] <= a[2] <= b[2] <= hi[2]
    columns |= {(x, z) for x in range(a[0], b[0] + 1) for z in range(a[2], b[2] + 1)}
assert len(columns) == (hi[0] - lo[0] + 1) * (hi[2] - lo[2] + 1)

# the fake client refuses a fillbiome that the game would
big = Recorder(World(lo, hi), everything_loaded=True)
assert "Too many" in big.run(f"fillbiome 0 0 0 63 63 63 {S.BIOME}")
assert "biome entries set" in big.run(f"fillbiome 0 0 0 31 31 31 {S.BIOME}")
assert "not loaded" in Recorder(World(lo, hi)).run(f"fillbiome 0 0 0 3 3 3 {S.BIOME}")
"""
    )


def test_seabed_deterministic():
    """two Pythons make the same plan (no hash order, no clock in it)"""
    code = """
import hashlib

import seabed as S

lines = "".join(f"{c} {b};" for c, b in S.plan().items())
print(hashlib.sha256(lines.encode()).hexdigest(), len(S.plan()))
"""
    first = run(code)
    assert first == run(code)
    assert int(first.split()[1]) > 1000
