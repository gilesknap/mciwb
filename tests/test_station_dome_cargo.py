"""
The Cargo Hold (examples/station/dome_cargo.py) with no server: the
manifests and their searches, the plan against the dome, its build
against the example's fake client, and its datapack functions, read line
by line and driven through whole solves by a small interpreter of the
scoreboard. As tests/test_station_example.py does, each test runs in a
Python of its own, in the example's folder.
"""

import os
import subprocess
import sys
from pathlib import Path

STATION = Path(__file__).parents[1] / "examples" / "station"
# what the example reads from the environment
SETTINGS = ("STAGES", "CHECKS", "FORCE", "STATION_DATAPACKS_DIR")


def run(code: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in SETTINGS}
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=STATION,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_cargo_puzzle():
    run(
        """
import random

import dome_cargo as D

# the fifteen manifests: legal, solvable in the table's moves, no soft
# lock, and the player with no plan much slower
assert not D.manifest_problems(), D.manifest_problems()
found = D.puzzle()
states = [found[b, 0]["states"] for b in range(5)]
assert states == [3968, 13312, 24576, 64896, 24648], states
assert all(v["locks"] == 0 for v in found.values())
best = [[found[b, m]["best"] for m in range(3)] for b in range(5)]
assert best == [[5, 5, 5], [7, 7, 7], [9, 9, 9], [11, 11, 10], [12, 12, 11]], best
for b in range(5):
    assert max(best[b]) - min(best[b]) <= 1  # fair whichever is drawn
naive = {k: v["naive"] for k, v in found.items()}
assert all(naive[b, m] >= best[b][m] + 2 for b in range(5) for m in range(3)), naive
assert all(
    naive[b, m] >= 1.5 * best[b][m] for b in range(1, 5) for m in range(3)
), naive
# the route is legal move by move and ends at the plan
for (b, m), v in found.items():
    band = D.BANDS[b]
    hold = D.Hold(band.limit, band.shut)
    s = D.encode(D.parse(band.manifests[m][0]))
    for a, z in v["route"]:
        nxt = {(x, y): n for x, y, n, _ in hold.moves(s, hold.trim(s))}
        s = nxt[a, z]
    assert s == D.encode(D.parse(band.manifests[m][1]))

# the rules, one at a time, on a small hold
hold = D.Hold(2)
s = D.encode(D.parse("W . . . | . . . ."))
moves = {(a, b) for a, b, _, _ in hold.moves(s, hold.trim(s))}
assert (0, 1) in moves and (0, 2) in moves  # a bale across: a swing of 2
s = D.encode(D.parse("B . . . | . . . ."))
moves = {(a, b) for a, b, _, _ in hold.moves(s, hold.trim(s))}
assert (0, 2) in moves  # a barrel crosses while she leans 2 its way
s = D.encode(D.parse("B . . . | . . . W"))
moves = {(a, b) for a, b, _, _ in hold.moves(s, hold.trim(s))}
assert (0, 2) not in moves and (0, 5) in moves  # but not from level
s = D.encode(D.parse("W I . . | . . . ."))
moves = {(a, b) for a, b, _, _ in D.Hold(5).moves(s, -4)}
assert (1, 0) not in moves and (0, 1) in moves  # never on a lighter one
s = D.encode(D.parse("W IBH . . | . . . ."))
big, shut = D.Hold(10), D.Hold(10, 4)
assert (0, 1) not in {(a, b) for a, b, _, _ in big.moves(s, big.trim(s))}  # full
assert (0, 5) in {(a, b) for a, b, _, _ in shut.moves(s, shut.trim(s))}
assert (0, 4) not in {(a, b) for a, b, _, _ in shut.moves(s, shut.trim(s))}  # shut
for text in ("IBH W . B | . . H .", ". . . . | . . . ."):
    assert D.decode(D.encode(D.parse(text))) == D.parse(text)
    assert D.show(D.parse(text)).split() == text.split()

# a fault put in the table is found
real = D.BANDS
band = real[0]
D.BANDS = (D.Band(band.levels, band.limit, band.shut,
                  ((band.manifests[0][0], band.manifests[0][1], 4),
                   *band.manifests[1:])), *real[1:])
D.puzzle.cache_clear()
assert any("4" in p for p in D.manifest_problems())
D.BANDS = real
"""
    )


def test_cargo_plan():
    run(
        """
import math

import domes
import dome_cargo as D
import rooms
import station_layout as L
import tunnels

D.manifest_problems = lambda: []  # (test_cargo_puzzle's)
dome = L.DOMES[D.INDEX]
assert dome.key == "cargo" and D.INDEX == L.index_of("cargo")
fr = D.frame(dome)
# the exit straight ahead, the pump engine to its right
assert L.TUNNELS[D.INDEX].axis == L.TUNNELS[D.INDEX - 1].axis
assert not D.room_problems(dome), D.room_problems(dome)[:5]
b = D.room_blocks(dome)
used = set(b.above()) | b.clear
assert used <= domes.dome_cells(dome).interior
assert not used & tunnels.reserved_cells(dome)
assert len(b.everything()) > 2600
# nine buttons on the pulpit and the lever, and the recall
assert len(D.inputs(dome)) == 11
assert {c for c, block in b.above().items() if rooms.is_input(block)} == D.inputs(dome)
assert D.INDEX in domes.ALLOWED
# nobody gets into the aft hold, or onto the roof; the fore hold by its stair
seen = D.reach(dome, b)
assert fr.at(-7, 0, 1) not in seen and fr.at(6, 0, 1) in seen
assert fr.at(0, 3, D.HOUSE_TOP + 1) not in seen
# the keys lie the way the crane goes, before the driver's platform (a
# slab: the eye half a block over the deck's), in reach
assert D.DRIVER[2] == 7 and D.DRIVER_EYE == D.DECK_H + 1.5 + 1.62
assert "slab" in b.solid[fr.at(*D.DRIVER[:2], D.DECK_H + 1)]
assert D.TRAVEL["FORE"][0] > D.TRAVEL["AFT"][0]
assert D.TRAVEL["PORT"][1] < D.TRAVEL["STARBOARD"][1]
assert D.HOOK["HOOK UP"][0] > D.HOOK["HOOK DOWN"][0]
eye = (D.DRIVER[0] + 0.5, D.DRIVER[1], D.DRIVER_EYE)  # the platform's middle
for f, r in {**D.TRAVEL, **D.HOOK}.values():
    assert f > D.DRIVER[0]
    assert math.dist(eye, (f + 0.5, r + 0.5, D.DECK_H + 1.1)) <= 4.5
posts = D.posts(fr)
assert all("face=floor" in posts[k].attached[posts[k].input] for k in D.TRAVEL)
assert "face=wall" in posts["UNDO"].attached[posts["UNDO"].input]
# the aft hold: no way in, and a way out all the same. The trap check
# is honest: it flags the hold with no ladder, and the gantry walk's
# end rails left open at the corners (a slip between the bars to the canopy)
assert not D.trap_problems(dome)
real = D.room_blocks
def stairless(d):
    got = real(d)
    for cell in D.ladders(got):
        got.attached.pop(cell)
    return got
def open_corners(d):
    got = stairless(d)
    for side in (-1, 1):
        for end in (D.WALK_F[0] - 1, D.WALK_F[1] + 1):
            for r in (10 * side, 13 * side):
                for h in (11, 12):
                    got.solid.pop(fr.at(end, r, h), None)
    return got
D.room_blocks = stairless
found = D.trap_problems(dome)
assert len(found) == 1 and "no way out" in found[0], found
D.room_blocks = open_corners
found = D.trap_problems(dome)
assert any("on the crates or the roof" in p for p in found), found
assert any("no way out" in p for p in found), found
D.room_blocks = real
assert len(D.ladders(b)) == D.NOTCH_H - 1
f, r = D.AFT_LADDER
assert fr.at(f, r + 1, D.NOTCH_H) not in b.solid  # the notch
assert fr.at(f, r + 1, D.NOTCH_H - 1) in b.solid
# afloat: the basin holds and lets go, and the check is honest: it flags
# a basin with no bed, and one walled in
assert not D.afloat_problems(dome)
wet = D.basin(dome)
assert wet <= domes.dome_cells(dome).floor and wet <= domes.OPENINGS[D.INDEX]
assert all(b.floor[c] == D.WATER for c in wet)
assert not D.over_water(dome) & seen  # no walk is through the water
def bedless(d):
    got = real(d)
    got.bed.clear()
    return got
def walled(d):
    got = real(d)
    for x, y, z in wet:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y, z + dz) not in wet:
                got.solid.setdefault((x + dx, y + 1, z + dz), D.CUT)
                got.solid.setdefault((x + dx, y + 2, z + dz), D.CUT)
    return got
D.room_blocks = bedless
assert any("no bed" in p for p in D.afloat_problems(dome))
D.room_blocks = walled
assert any("no way out" in p for p in D.afloat_problems(dome))
D.room_blocks = real
# the list gauge: a needle a face, upright at none, to starboard for more
assert "angle:0f" in D.needle_pose(fr, 0)
assert D.needle_pose(fr, 2) != D.needle_pose(fr, -2)
assert [D.zone_limit(j) for j in range(D.ZONES)] == [6, 5, 4, 3, 2, 1, 1, 2, 3, 4, 5, 6]
plate = [fr.at(*p) for face in (-1, 1) for p in D.gauge_cells(face)]
assert all(b.solid[c] == D.BRASS for c in plate)
assert max(p[2] for p in D.gauge_cells(-1)) == D.HOUSE_TOP == 8
# the deckhouse is what hides each hold: lower it and the pulpit sees
real = D.room_blocks
def low(d):
    got = real(d)
    for cell in list(got.solid):
        dx, dz = cell[0] - fr.origin[0], cell[2] - fr.origin[2]
        f = dx * fr.forward[0] + dz * fr.forward[1]
        if -4 <= f <= 4 and cell[1] - dome.floor_y >= 6:
            got.solid.pop(cell)
    return got
D.room_blocks = low
assert D.blind_problems(dome)
D.room_blocks = real
# the crane: every place it goes is inside and clear
assert not D.crane_problems(dome)
assert len(D.crane_boxes()) + 1 == D.PARTS
# the four crate blocks only in the bays and on the tables
assert not D.dressing_problems(dome)
# the log: four pages, the fourth the manifest drawn
pages = D.logbook_pages(2, 0)
assert len(pages) == 4 and "MANIFEST No. 1" in pages[3]
assert "AFT 1: iron, barrel on it." in pages[3] and "FORE 3: hay." in pages[3]
assert "Finch" in pages[0] and "Marsh" not in "".join(pages)
"""
    )


def test_cargo_build():
    run(
        """
import build_station as B
import dome_cargo as D
import game
import station_layout as L
import verify_station as V

D.manifest_problems = lambda: []  # (test_cargo_puzzle's)
dome = L.DOMES[D.INDEX]
assert B.STAGES[f"dome_{D.INDEX}_inside"] is D.build and V.LIVE["cargo_hold"] is D.check
assert "cargo_hold" not in V.todos()
assert "stub_cargo" not in {m.name for m in B.modules()}
b = D.room_blocks(dome)
lectern = D.frame(dome).at(*D.LECTERN)
stages = ["site", B.dome_stage_name(D.INDEX), "tunnels", f"dome_{D.INDEX}_inside"]
rec = B.offline_build(stages=stages, force=False)
for cell, block in b.everything().items():
    if cell != lectern:
        assert rec.world.at(cell) == block, (cell, block, rec.world.at(cell))
assert rec.world.name_at(lectern) == "minecraft:lectern"
for cell in game.stub_post(dome).cells - set(b.everything()):
    assert rec.world.name_at(cell) == "minecraft:air", cell
assert all(len(c.encode()) <= B.MAX_COMMAND for c in rec.commands)
count = lambda start: sum(c.startswith(start) for c in rec.commands)  # noqa: E731
assert count("summon minecraft:interaction") == 1
# labels of ten inputs, eight bay names, the gauges' words, the board,
# docket, legend, three titles, the dark notice, the jam, her name twice
assert count("summon minecraft:text_display") == 10 + 8 + 6 + 3 + 3 + 1 + 1 + 2
# the crane is the pack's; the list gauges' marks, hubs and needles
assert count("summon minecraft:block_display") == 2 * (D.ZONES + 2)
# the basin: its bed under the floor, laid before any water
for cell, block in b.bed.items():
    assert rec.world.at(cell) == block, (cell, block)
assert len(b.bed) >= len(D.basin(dome)) > 150
def first(cell, block):
    for i, c in enumerate(rec.commands):
        w = c.split()
        if w[0] == "fill" and w[7] == block:
            lo, hi = [int(n) for n in w[1:4]], [int(n) for n in w[4:7]]
            if all(a <= k <= z for a, k, z in zip(lo, cell, hi)):
                return i
x, y, z = min(D.basin(dome))
assert first((x, y - 1, z), "minecraft:deepslate") < first((x, y, z), D.WATER)
assert f"function station:dome/{D.INDEX}/reset" in rec.commands
again = B.offline_build(stages=[*stages, f"dome_{D.INDEX}_inside"], force=False)
assert again.world.dump() == rec.world.dump()
D.room_problems = lambda dome: ["a problem"]
try:
    B.offline_build(stages=stages, force=False)
except RuntimeError as e:
    assert "a problem" in str(e)
else:
    raise AssertionError("built a room with a problem")
""",
    )


def test_cargo_pack():
    run(
        INTERPRETER
        + """
n = D.INDEX
base = f"dome/{n}"
for hook in game.HOOKS:
    assert f"{base}/{hook}" in F, hook
assert f"{base}/leave" not in F and f"{base}/died" not in F
assert not V.function_problems(B.pack_files(pack))
assert not V.name_problems(mine)
solved = f"function station:{base}/solved"
solvers = [k for k, ls in mine.items() if any(solved in x for x in ls)]
assert solvers == [f"{base}/stowed"], solvers
# the glide: a quarter block a tick along the frame's axes; every display
# summoned to glide
fx, fz = fr.forward
rx, rz = fr.right
q = lambda d: f"~{d:g}" if d else "~"  # noqa: E731
bridge, trolley = F[f"{base}/crane/bridge"], F[f"{base}/crane/trolley"]
assert any(f"tp @s {q(fx / 4)} ~ {q(fz / 4)}" in x for x in bridge)
assert any(f"tp @s {q(-rx / 4)} ~ {q(-rz / 4)}" in x for x in trolley)
assert any("tp @s ~ ~-0.25 ~" in x for x in F[f"{base}/crane/hook"])
summon = "summon minecraft:block_display"
displays = [x for ls in mine.values() for x in ls if summon in x]
assert all("interpolation_duration" in x for x in F[f"{base}/trim/show"])
assert displays and all("teleport_duration:1" in x for x in displays)
make = F[f"{base}/crane/make"]
assert sum("summon" in x for x in make) == D.PARTS + 2  # and two links
for i in range(8):
    for t in range(3):
        lift = F[f"{base}/bay/{i}/lift/{t}"]
        assert sum("summon" in x for x in lift) == 8 * 4
        assert lift[-1].startswith("fill ")
assert all("st.cargo.crate" in x for x in F[f"{base}/bay/0/lift/0"][:-1])

# the manifests in the pack are the search's
for b, band in enumerate(D.BANDS):
    for m in range(3):
        score.clear()
        call(f"{base}/lay/{b}/{m + 1}")
        assert hold() == D.parse(band.manifests[m][0])
        plan = tuple(
            tuple(k for k in (score.get(f"#cargo.g{i}.t{t}") for t in range(3)) if k)
            for i in range(8)
        )
        assert plan == D.parse(band.manifests[m][1])
        shut = -1 if band.shut is None else band.shut
        assert get("lim") == band.limit and get("shut") == shut

# armed at level 5, manifest 1
fresh(5, 1)
start, goal = (D.parse(t) for t in D.BANDS[2].manifests[0][:2])
assert hold() == start and get("trim") == D.trim(start) == 2
assert (get("live"), get("m"), get("band"), get("lim"), get("hy")) == (1, 1, 2, 2, 12)
# the buttons: STARBOARD three times sends the trolley three columns
for _ in range(3):
    call(f"{base}/press/starboard")
assert get("colto") == 3
call(f"{base}/press/starboard")
assert get("colto") == 3  # past the end: a clunk
ticks = settle()
assert get("col") == 3 and ticks == 3 * D.TROLLEY_TICKS, ticks
call(f"{base}/press/fore")
assert settle() == D.BRIDGE_TICKS and get("row") == 1
# the hook down on a stack of two: F3's iron and wool
call(f"{base}/press/port")
settle()
call(f"{base}/press/down")
assert settle() == (12 - 5) * D.STEP and get("hy") == 5
call(f"{base}/press/grab")
assert (get("load"), get("from"), get("hyto")) == (D.WOOL, 6, 12)
settle()
call(f"{base}/press/port")
settle()
call(f"{base}/press/down")
settle()
assert get("hy") == 5  # on F2's iron, with the wool under the spreader
call(f"{base}/press/release")
assert get("load") == 0 and hold()[5] == (D.IRON, D.WOOL) and hold()[6] == (D.IRON,)
assert get("trim") == 0 and get("moves") == 1 and get("hn") == 1
# UNDO: the start again; nothing to undo: nothing
settle()
call(f"{base}/press/undo")
assert hold() == start and get("trim") == 2 and get("moves") == 0 and get("hn") == 0
call(f"{base}/press/undo")
assert hold() == start
# GRAB with nothing under: refused; RELEASE with nothing on: refused
call(f"{base}/press/grab")
assert get("why") == D.NOT_ON and get("load") == 0
call(f"{base}/press/release")
assert get("why") == D.NOT_ON

# refusals: a barrel over the wool (crush), across her level (trim)
fresh(5, 1)
move_part(0)  # the barrel from A1 on the hook
goto(6)
call(f"{base}/press/down")
assert (get("why"), get("hyto"), get("load")) == (D.CRUSH, 12, D.BARREL)
goto(2)
call(f"{base}/press/down")
assert (get("why"), get("hyto"), get("ta")) == (D.TRIM, 12, 6)
assert get("flash") == D.FLASH_TICKS
# the needle is kicked to where she would have gone, and comes back
kick = [x for x in F[f"{base}/trim/flash"] if "data merge" in x]
assert len(kick) == 2 * D.GAUGE_STOP + 1 and D.NEEDLE_TAG in kick[0]
assert any(f"{base}/trim/show" in x and "flash" in x for x in F[f"{base}/tick"])
assert any("She'd list too far to starboard" in x for x in F[f"{base}/bay/2/check"])
said = " ".join(x.lower() for ls in mine.values() for x in ls)
assert "heel" not in said and "trim lamp" not in said
# back where it came from is always welcome
goto(0)
call(f"{base}/press/down")
assert get("why") == 0 and get("hyto") == 3
settle()
call(f"{base}/press/release")
assert hold() == start and get("moves") == 0 and get("hn") == 0
# UNDO with a crate on the hook puts it back
move_part(0)
call(f"{base}/press/undo")
assert hold() == start and get("load") == 0
# full: three laid in A3 by the scores
for t, k in enumerate((D.IRON, D.BARREL, D.HAY)):
    score[f"#cargo.b2.t{t}"] = k
score["#cargo.b2.n"] = 3
call(f"{base}/trim/count")
move_part(3)  # the hay from A4
goto(2)
call(f"{base}/press/down")
assert get("why") == D.FULL
# stand clear: someone in F3's column
fresh(5, 1)
goto(6)
crowd.add(6)
call(f"{base}/press/down")
assert get("why") == D.CLEAR and get("hyto") == 12
crowd.clear()
call(f"{base}/press/down")
tick(10)
crowd.add(6)
tick(8)
waiting = (get("wait"), get("hy"))
tick(40)
assert waiting[0] == 1 and (get("wait"), get("hy")) == waiting
crowd.clear()
settle()
assert get("hy") == 5 and get("wait") == 0

# whole solves along the search's routes, at every level's band
for level in (1, 3, 5, 7, 9):
    b = D.band_of(level)
    for m in range(3):
        fresh(level, m + 1)
        before = trace.count(f"{base}/solved")
        for a, z in D.puzzle()[b, m]["route"]:
            move(a, z)
            assert get("why") == 0
        assert hold() == D.parse(D.BANDS[b].manifests[m][1]), (level, m)
        assert get("free") == 1 and trace.count(f"{base}/solved") == before + 1
        assert get("moves") == D.puzzle()[b, m]["best"]
# played with after: moves call nothing more
before = trace.count(f"{base}/solved")
a, z = D.puzzle()[4, 2]["route"][-1]
move(z, a)
move(a, z)
assert trace.count(f"{base}/solved") == before and get("free") == 1

# shut at level 9: F1 refuses
fresh(9, 1)
move_part(0)
goto(4)
call(f"{base}/press/down")
assert get("why") == D.SHUT and get("shut") == 4

# three moves, three UNDOs: the start exactly
fresh(5, 1)
route = D.puzzle()[2, 0]["route"]
for a, z in route[:3]:
    move(a, z)
assert get("hn") == 3
for _ in range(3):
    call(f"{base}/press/undo")
assert hold() == start and (get("moves"), get("hn")) == (0, 0)
# the ring keeps thirty: 31 there-and-backs, then thirty UNDOs and no more
for _ in range(16):
    move(0, 1)
    move(1, 0)
assert get("hn") == 30
for _ in range(31):
    call(f"{base}/press/undo")
assert hold() == start and get("hn") == 0

# RESET HOLD: one pull and its time out, nothing; two pulls, the start
move(*route[0])
moved = hold()
call(f"{base}/lever")
assert get("ask") == D.ASK_TICKS
tick(D.ASK_TICKS + 1)
assert hold() == moved and get("ask") == 0
call(f"{base}/lever")
call(f"{base}/lever")
assert hold() == start and get("moves") == 0 and get("hn") == 0
# not with anyone in the hold
move(*route[0])
crowd.add(6)
call(f"{base}/lever")
call(f"{base}/lever")
assert hold() == moved and get("why") == D.CLEAR
crowd.clear()

# leaving with a crate on the hook: back where it came from, the hook up
fresh(5, 1)
move_part(0)
call(f"{base}/empty")
assert hold() == start and (get("load"), get("hy"), get("hyto")) == (0, 12, 12)
score["#first"] = 1
trace.clear()
call(f"{base}/enter")
assert get("live") == 1 and f"{base}/arm" not in trace

# the forms: duo is taken at the next safe point, never with a crate up
fresh(5, 1)
move_part(0)
call(f"{base}/duo")
tick(1)
assert (get("want"), get("form")) == (2, 1)
call(f"{base}/press/undo")
tick(1)
assert get("form") == 2
call(f"{base}/solo")
tick(1)
assert get("form") == 1

# the game's reset: everything zero, the crane made anew at home
call(f"{base}/reset")
state = [get(k) for k in ("live", "free", "load", "row", "col", "hy")]
assert state == [0, 0, 0, 0, 0, 12], state
assert hold() == ((),) * 8

# armed only on entry (a tick after the game's reset would use a stale
# level), and the hatch cleared only where a trapdoor is (not F1's crate)
assert not any(f"{base}/arm" in line for line in F[f"{base}/tick"])
for line in F[f"{base}/hatch"]:
    if line.startswith("setblock") or " run setblock " in line:
        assert line.startswith("execute if block") and D.HATCH in line, line
""",
    )


INTERPRETER = """
import build_station as B
import datapack
import dome_cargo as D
import game
import station_layout as L
import verify_station as V

dome = L.DOMES[D.INDEX]
fr = D.frame(dome)
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [D.MODULE])
core = datapack.Pack(stamp="t")
game.add_functions(core, [])
F = pack.functions
mine = {
    k: ls
    for k, ls in F.items()
    if k.startswith(f"dome/{D.INDEX}/") and k not in core.functions
}

# a small interpreter of the scoreboard lines: blocks are never there,
# entities only in the bays named in ``crowd`` (a stand-in in a column)
score, trace, crowd = {}, [], set()
columns = {D.column(fr, i): i for i in range(8)}


def matches(value, span):
    if value is None:
        return False
    lo, _, hi = span.partition("..") if ".." in span else (span, "", span)
    return (lo == "" or value >= int(lo)) and (hi == "" or value <= int(hi))


def entity(selector):
    return columns.get("entity " + selector) in crowd


def do(line):
    t = line.split(" ")
    if t[0] == "execute":
        i = 1
        while t[i] != "run":
            if t[i] == "store":
                target = t[i + 3]
                rest = t[i + 5:]
                if rest[:2] == ["if", "entity"]:
                    score[target] = int(entity(rest[2]))
                elif rest[:3] == ["run", "random", "value"]:
                    score[target] = 1
                return None
            if t[i] in ("as", "at", "on", "positioned"):
                return None  # nobody to run as
            want, kind = t[i] == "if", t[i + 1]
            if kind == "score" and t[i + 4] == "matches":
                ok, step = matches(score.get(t[i + 2]), t[i + 5]), 6
            elif kind == "score":
                a, b = score.get(t[i + 2]), score.get(t[i + 5])
                ok = a is not None and b is not None and {
                    ">=": a >= b, "<": a < b, "=": a == b, ">": a > b, "<=": a <= b,
                }[t[i + 4]]
                step = 7
            elif kind == "entity":
                ok, step = entity(t[i + 2]), 3
            else:
                ok, step = False, {"block": 6, "data": 5}[kind]
            if ok != want:
                return None
            i += step
        return do(" ".join(t[i + 1:]))
    if t[0] == "function":
        return call(t[1].split(":")[1])
    if t[0] == "return":
        if t[1] == "run":
            do(" ".join(t[2:]))
        return "return"
    if t[0] == "tellraw":
        trace.append(line)
    if t[:2] == ["scoreboard", "players"]:
        op, name = t[2], t[3]
        if op == "set":
            score[name] = int(t[5])
        elif op in ("add", "remove"):
            score[name] = score.get(name, 0) + int(t[5]) * (1 if op == "add" else -1)
        elif op == "operation":
            a, b = score.get(name, 0), score.get(t[6], 0)
            score[name] = {"=": b, "+=": a + b, "-=": a - b, "*=": a * b,
                           "/=": a // b if b else a, "%=": a % b if b else a,
                           "<": min(a, b), ">": max(a, b)}[t[5]]
    return None


def call(name):
    trace.append(name)
    if name not in mine:
        return None  # the core's: named, not run
    for line in F[name]:
        if line.startswith("$"):
            continue
        if do(line) == "return":
            break
    return None


def get(name):
    return score.get(f"#cargo.{name}")


def hold():
    return tuple(
        tuple(score.get(f"#cargo.b{i}.t{t}", 0) for t in range(get(f"b{i}.n") or 0))
        for i in range(8)
    )


def tick(n=1):
    for _ in range(n):
        call(f"dome/{D.INDEX}/tick")


def settle(limit=3000):
    for k in range(limit):
        call(f"dome/{D.INDEX}/moving")
        if get("moving") == 0 and get("down") == 0:
            return k
        tick()
    raise AssertionError("the crane never came to rest")


def fresh(level, m):
    score.clear()
    crowd.clear()
    for c in (2, 4, 8, 10, 30, 60, 100):
        score[f"#{c}"] = c
    score.update({"#active": level, "#diff.timer": 100, f"#d{D.INDEX}": 1,
                  "#first": 1, "#cargo.force": m})
    call(f"dome/{D.INDEX}/enter")


def goto(i):
    row, col = divmod(i, 4)
    call(f"dome/{D.INDEX}/press/{'fore' if row else 'aft'}")
    while get("colto") != col:
        call(f"dome/{D.INDEX}/press/{'starboard' if col > get('colto') else 'port'}")
    settle()


def move_part(a):
    goto(a)
    call(f"dome/{D.INDEX}/press/down")
    settle()
    call(f"dome/{D.INDEX}/press/grab")
    assert get("load"), (a, get("why"))
    settle()


def move(a, b):
    move_part(a)
    goto(b)
    call(f"dome/{D.INDEX}/press/down")
    assert get("why") == 0, (a, b, get("why"))
    settle()
    call(f"dome/{D.INDEX}/press/release")
    assert get("load") == 0, (a, b, get("why"))
    settle()
"""
