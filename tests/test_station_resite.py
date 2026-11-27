"""
The offline tests of the re-site (examples/station/resite.py): what the ring
of ten has that the ring of eight had not, and the other way round; the
``resite`` stage puts the sea back where the eight's tunnel 3 ran, and is
the same run twice; the ``rollback`` stage takes the new column away and
its chunks off the forceload. No server is needed. As in
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


def test_resite_plan():
    """what changed between the rings, and that what goes is clear of
    what stays"""
    run(
        """
import domes
import resite as R
import station_layout as L
import tunnels

# the ring: the new domes where the Flooded Dome and the Foundry were,
# which moved a column east
assert [d.key for d in L.DOMES] == [
    "start", "boiler", "gearworks", "cargo", "flooded", "foundry",
    "hullbreach", "signal", "maze", "boss",
]
assert all(L.index_of(d.key) == d.index for d in L.DOMES)
old = {d.key: d for d in R.PREVIOUS_DOMES}
assert R.same_place(L.dome("cargo"), old["flooded"])
assert R.same_place(L.dome("hullbreach"), old["foundry"])
assert [d.key for d in R.new_domes()] == ["flooded", "foundry"]
assert [d.key for d in R.renamed_domes()] == ["cargo", "hullbreach"]
assert R.former_domes() == []
assert [t.index for t in R.new_tunnels()] == [3, 4, 5]
gone = R.former_tunnels()
assert len(gone) == 1 and gone[0].axis == "z"
assert {gone[0].start, gone[0].end} == {L.index_of("cargo"), L.index_of("hullbreach")}

def tube(t):
    c = tunnels.tunnel_cells(t)
    return c.ring | c.floor | c.inside | set(c.stairs) | c.piers

# what goes touches nothing of the ring that stays
staying = set().union(*(domes.dome_cells(d).all for d in L.DOMES))
staying |= set().union(*(tube(t) for t in L.TUNNELS))
assert not tube(gone[0]) & staying
# ... and the other way round: the new column and its tunnels touch
# nothing of the eight's domes (the eight's tunnels are as the ten's, but
# the one that goes)
before = set().union(*(domes.dome_cells(d).all for d in R.PREVIOUS_DOMES))
new = set().union(*(domes.dome_cells(d).all for d in R.new_domes()))
new |= set().union(*(tube(t) for t in R.new_tunnels()))
assert not new & before
# the eight's box is in the ten's: the rollback only takes chunks away
(cx1, cz1), (cx2, cz2) = L.station_chunks()
ours = {(x, z) for x in range(cx1, cx2 + 1) for z in range(cz1, cz2 + 1)}
assert R.previous_chunks() < ours
assert len(R.previous_chunks()) == 198 and len(ours) == 253
"""
    )


def test_resite_stages():
    """the two stages against the fake client"""
    run(
        """
import io
from contextlib import redirect_stdout

import build_station as B
import domes
import resite as R
import seabed
import tunnels
from fake_client import Recorder, World

# the full build has resite before any dome, and no rollback
names = list(B.STAGES)
assert names.index("resite") < names.index("start_dome")
assert "rollback" not in names and "rollback" in B.MANUAL_STAGES

# the eight's tunnel 3, as it stands in the world, then the re-site
gone = R.former_tunnels()[0]
B.STAGES["old"] = lambda ctx: tunnels.build_tunnel(ctx, gone)
c = tunnels.tunnel_cells(gone)
cells = c.ring | c.floor | c.inside | set(c.stairs)
with redirect_stdout(io.StringIO()):
    rec = B.offline_build(stages=["site", "old"], force=False)
    assert any(rec.world.at(x) == domes.GLASS for x in cells)
    rec = B.offline_build(stages=["site", "old", "resite"], force=False)
where = seabed.site()
for x, y, z in cells:
    want = R.WATER if y > where.surveyed_at(x, z) else R.SAND
    assert rec.world.at((x, y, z)) == want, (x, y, z)
for x, y, z in c.piers:
    for k in range(domes.FOUNDATION_DEPTH + 1):
        assert rec.world.at((x, y - k, z)) != tunnels.PIER
# the craters: carved to water, sand at the bottom
water, bed = seabed.crater_cells()
assert all(rec.world.at(c) == R.WATER for c in water)
assert all(rec.world.at(c) == R.SAND for c in bed)
# the same run twice (a rerun of resite carves the craters' dressing away
# again: the seabed stage after it, as in the full build, puts it back)
with redirect_stdout(io.StringIO()):
    once = B.offline_build(stages=["site", "old", "resite", "seabed"], force=False)
    twice = B.offline_build(
        stages=["site", "old", "resite", "seabed", "resite", "seabed"], force=False
    )
assert once.world.dump() == twice.world.dump()

# the rollback: the new column and its tunnels gone, its chunks released
built = ["site", "resite", "dome_4", "dome_5", "tunnel_3", "tunnel_4", "tunnel_5"]
built.append("seabed")
with redirect_stdout(io.StringIO()):
    rec = B.offline_build(stages=[*built, "rollback"], force=False)
assert rec.forceloaded == R.previous_chunks()
# the craters filled with sand to the surveyed floor
assert all(rec.world.at(c) == R.SAND for c in water | bed)
left = {tunnels.PIER, domes.FOUNDATION, *R.TUBE} - {R.WATER, domes.AIR}
for d in R.new_domes():
    for x in domes.dome_cells(d).all:
        assert rec.world.at(x) in (R.WATER, R.SAND), (x, rec.world.at(x))
    for a, b in domes.foundation_boxes(d):
        assert rec.world.at(a) != domes.FOUNDATION
for t in R.new_tunnels():
    c = tunnels.tunnel_cells(t)
    for x in c.ring | c.floor | c.inside | set(c.stairs) | c.piers:
        assert rec.world.at(x) not in left, (x, rec.world.at(x))
# (all of the dressing but the seagrass, which the sea grows anyway)
dressing = {seabed.name(b) for b in seabed.plan().values()}
dressing -= {seabed.SAND, seabed.SEAGRASS}
assert not [x for x in seabed.plan() if seabed.name(rec.world.at(x)) in dressing]
"""
    )


def test_resite_craters():
    """the craters round the domes dug deep into the sea floor: where, how
    deep, how steep, clear of every dome and tunnel, and dressed"""
    run(
        """
import numpy as np

import domes
import seabed as S
import station_layout as L
import tunnels

where = S.site()
cut, was = where.floor, where.surveyed
# the moved Flooded Dome and Foundry, and the tunnels to them; not the
# Engine, sunk on purpose (its glass stands in the ground, as before)
assert [d.key for d in S.crater_domes(was)] == ["flooded", "foundry"]
assert [t.index for t in S.trench_tunnels(was)] == [3, 4, 5]
assert (cut <= was).all() and (cut[cut < was] > S.CARVE_ABOVE).all()
assert ((cut < was).sum()) > 1000
# down to the floor's level next to the shell, all round
for d in S.crater_domes(was):
    for angle in np.linspace(0, 2 * np.pi, 72, endpoint=False):
        out = d.radius + 2
        x = round(d.centre[0] + out * np.cos(angle))
        z = round(d.centre[1] + out * np.sin(angle))
        assert where.floor_at(x, z) == min(d.floor_y, where.surveyed_at(x, z)), (x, z)
# terraces: the carving adds no step of more than CRATER_RISE between
# neighbours, and at the box's edge the floor is the survey's
for axis in (0, 1):
    added = np.abs(np.diff(cut, axis=axis)) - np.abs(np.diff(was, axis=axis))
    assert added.max() <= S.CRATER_RISE
assert (cut[0] == was[0]).all() and (cut[-1] == was[-1]).all()
assert (cut[:, 0] == was[:, 0]).all() and (cut[:, -1] == was[:, -1]).all()
# the cells: none of a dome or a tunnel (piers too), none at or below the
# mineshaft's limit, the bed under the water
water, bed = S.crater_cells()
taken = set(S.structure_cells())
for t in L.TUNNELS:
    taken |= tunnels.tunnel_cells(t).piers
assert not (water | bed) & taken
assert min(y for _, y, _ in water | bed) > S.CARVE_ABOVE
assert all(where.floor_at(x, z) == y for x, y, z in bed)
# the dressing reaches the crater floors and sides, at the carved heights
# (the plan's own rules, which use the carved floor, hold)
def dug(c):
    return where.floor_at(c[0], c[2]) < where.surveyed_at(c[0], c[2])


carved = [c for c in S.plan() if dug(c)]
assert len(carved) > 100
assert any(b == S.LANTERN for c, b in S.plan().items() if c in set(carved))
assert not S.problems()
"""
    )
