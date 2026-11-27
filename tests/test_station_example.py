"""
Run the offline checks of examples/station and its whole build against the
example's fake client, so that a change that breaks the example fails the
unit tests: no server is needed. The example changes sys.path when it is
imported and its module names are short (``datapack``, ``fake_client``), so
each test runs in a Python of its own, in the example's folder.
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


def test_station_offline_checks():
    out = run(
        """
import verify_station

results = verify_station.offline_checks()
assert set(results) == set(verify_station.OFFLINE)
failed = {name: problems for name, problems in results.items() if problems}
assert not failed, failed
# the checks that are not written are not passes
assert set(verify_station.todos()) <= set(verify_station.LIVE)
verify_station.main()
"""
    )
    assert "FAIL" not in out
    assert "TODO" not in out


def test_station_checks_find_faults():
    run(
        """
import verify_station as V

pack = {
    "pack.mcmeta": '{"pack": {"pack_format": 1}}',
    "data/station/function/a.mcfunction": "say hello\\nfunction station:b\\n",
    "data/minecraft/tags/function/tick.json": '{"values": ["station:c"]}',
}
problems = V.function_problems(pack)
assert len(problems) == 2, problems
assert any("station:b" in p for p in problems)
assert any("station:c" in p for p in problems)
assert V.function_problems({k: v for k, v in pack.items() if "tags" in k})

commands = {
    "here": [
        "setblock 1 2 3 minecraft:waxed_copper_bulb[lit=true]",
        "execute if block ~ ~-1 ~ gold_block run give @a[tag=x] minecraft:bow 1",
        "fill 1 2 3 4 5 6 air replace #minecraft:logs",
        "fill 1 2 3 4 5 6 minecraft:brass_block replace water",
    ]
}
assert V.names_in(commands["here"][1]) == {"minecraft:gold_block", "minecraft:bow"}
problems = V.name_problems(commands)
assert len(problems) == 1 and "brass_block" in problems[0], problems
"""
    )


def test_station_offline_build(tmp_path):
    out = run(
        """
import sys

import build_station as B
import shore
from fake_client import Recorder, World

assert list(B.STAGES)[:3] == ["site", "datapack", "rules"] == B.written()[:3]
last = len(B.station_layout.DOMES) - 1
assert {"start_dome", f"dome_{last}", "tunnel_0", f"tunnel_{last}"} <= set(B.written())
# the last dome has its module (a dome without one is a stub with a bypass)
assert "boss" in {m.name for m in B.modules()}
assert f"dome_{last}_inside" in B.written()

# the whole build: the site loaded for it, and left loaded for the game;
# the pack installed
rec = B.offline_build(stages=list(B.STAGES), datapacks_dir=sys.argv[1], force=False)
assert any(c.startswith("forceload add") for c in rec.commands)
# (the shore, outside the station's box, is loaded only while it is built)
removes = [c for c in rec.commands if c.startswith("forceload remove")]
released = {c.split(" ", 2)[2] for c in removes}
assert released == {f"{x * 16} {z * 16}" for x, z in shore.shore_chunks()}
assert rec.forceloaded == B.site_chunks()
assert "reload" in rec.commands
assert rec.storage["station:pack", "stamp"] == '"offline"'
assert all(len(c.encode()) <= B.MAX_COMMAND for c in rec.commands)
stubs = [m for m in B.modules() if m.name.startswith("stub_")]
here = B.Path(B.__file__).parent
missing = [
    d for d in B.station_layout.DOMES[1:] if not (here / f"dome_{d.key}.py").is_file()
]
assert [m.name for m in stubs] == [f"stub_{d.key}" for d in missing]
print(f"stubs built: {len(stubs)}")

# some stages, and a stage that does not exist
rec = B.offline_build(stages=["site"], force=False)
assert "reload" not in rec.commands
try:
    B.offline_build(stages=["moon"], force=False)
except SystemExit as e:
    assert "moon" in str(e)
else:
    raise AssertionError("an unknown stage was accepted")

# a player online: no build, and nothing sent but the question
box = B.station_box()
rec = Recorder(World(*box), players=("Alex",))
try:
    B.offline_build(recorder=rec, force=False)
except SystemExit as e:
    assert "Alex" in str(e)
else:
    raise AssertionError("built with a player online")
assert rec.commands == ["list"], rec.commands
rec = Recorder(World(*box), players=("Alex",))
B.offline_build(recorder=rec, force=True)
assert not any(c.startswith("tick sprint") for c in rec.commands)

# a stage that fails: the site stays loaded, and so does what was before
def broken(ctx):
    raise RuntimeError("broken")

B.STAGES["dock"] = broken
rec = Recorder(World(*box))
kept = {(box[0][0] // 16, box[0][2] // 16), (10**6, 0)}
rec.forceloaded |= kept
try:
    B.offline_build(recorder=rec, stages=["site", "dock"], force=False)
except RuntimeError:
    pass
else:
    raise AssertionError("the broken stage did not stop the build")
assert rec.forceloaded == kept | B.site_chunks(), rec.forceloaded

# a command too long for RCON is refused before it is sent
sent = len(rec.commands)
try:
    B.cmd("say " + "x" * B.MAX_COMMAND)
except ValueError:
    assert len(rec.commands) == sent
else:
    raise AssertionError("a long command was sent")
""",
        str(tmp_path),
    )
    # a stub with a bypass is built for each dome with no module yet (the
    # script checks which), and none when every dome has its module
    stubs = int(out.split("stubs built: ")[1].split()[0])
    assert ("a stub, its BYPASS lever" in out) == (stubs > 0)
    assert (tmp_path / "station" / "pack.mcmeta").is_file()


def test_station_fake_client():
    run(
        """
from fake_client import NOT_LOADED, Recorder, World

rec = Recorder(World((0, 0, 0), (40, 20, 40)))
# nothing is loaded until it is forceloaded, 256 chunks a command at most
assert rec.setblock((1, 2, 3), "minecraft:stone") == NOT_LOADED
assert "Too many" in rec.run("forceload add 0 0 271 255")
assert rec.run("forceload add 0 0 40 40").startswith("Marked 9 chunks")
assert rec.setblock((1, 2, 3), "minecraft:glass").startswith("Changed")
rec.fill((0, 0, 0), (9, 9, 9), "minecraft:water", "keep")
assert rec.world.at((1, 2, 3)) == "minecraft:glass"
assert rec.world.name_at((2, 2, 3)) == "minecraft:water"
# a tube drained: only the water goes
rec.run("fill 0 0 0 9 9 9 minecraft:air replace minecraft:water")
assert rec.world.name_at((2, 2, 3)) == "minecraft:air"
assert rec.run("execute if block 1 2 3 minecraft:glass") == "Test passed"
assert rec.run("execute if block 1 2 3 minecraft:water") == "Test failed"
assert rec.world.dump()[0] == "0 0 0 minecraft:air"
rec.run("forceload remove 0 0 40 40")
assert not rec.forceloaded
assert rec.run("execute if block 1 2 3 minecraft:glass") == NOT_LOADED
"""
    )


def test_station_structures():
    run(
        """
import build_station as B
import domes
import station_layout as L
import tunnels
from fake_client import AIR

rec = B.offline_build(stages=["site", "start_dome", "dome_1", "tunnels"], force=False)
at = rec.world.name_at
start, boiler = L.DOMES[0], L.DOMES[1]
cells = domes.dome_cells(start)
# the shell whole, the inside empty but for the engine, the floor laid
doors = set().union(*domes.openings(start).values())
assert all(at(c) != AIR for c in cells.shell | cells.floor)
engine = set(tunnels.engine_cells(L.TUNNELS[0]).values())
assert all(at(c) == AIR for c in cells.interior - engine)
assert at(start.floor_centre) in (domes.FLOOR, domes.LIGHT)
closed = domes.door_blocks(start, L.TUNNELS[0])
assert all(at(c) == block for c, block in closed.items())
assert sum(block == domes.GLASS for block in closed.values()) == 9  # the window
assert set(closed) <= doors
x, y, z, _ = domes.entrance(boiler)
assert boiler.contains(x, y, z) and (x, y, z) in domes.dome_cells(boiler).interior
# the tunnel: flooded, between the two doors, its lamps dark
tube = tunnels.tunnel_cells(L.TUNNELS[0])
assert all(at(c) == "minecraft:water" for c in tube.inside)
assert all(at(c) == domes.GLASS for c in tube.ring)
assert all(rec.world.at(c).endswith("[lit=false]") for c in tube.lamps)
assert not tube.inside & (cells.all | domes.dome_cells(boiler).all)
# built twice: the same blocks
again = B.offline_build(
    stages=["site", "start_dome", "dome_1", "tunnels", "dome_1", "tunnels"], force=False
)
assert again.world.dump() == rec.world.dump()
# the drain goes by layers from the top: 4 in a level tunnel, and in a
# sloping one a layer for every y, so that the surface is level
assert len(tube.layers) == 4
assert sum(len(layer) for layer in tube.layers) == len(tube.inside)
assert tunnels.state_lines(L.TUNNELS[0], 4)[1:] == [
    line for line in tunnels.state_lines(L.TUNNELS[0], 4)[1:] if "air replace" in line
]
# a sloping tunnel's floor steps from one dome's floor to the other's
slope = next(t for t in L.TUNNELS if t.rise)
ys = [tunnels.floor_y(slope, s) for s in range(slope.length + 1)]
assert ys[0] == slope.a[1] and ys[-1] == slope.b[1]
assert all(abs(q - p) <= 1 for p, q in zip(ys, ys[1:]))
sloping = tunnels.tunnel_cells(slope)
assert len(sloping.layers) == abs(slope.rise) + 3  # (stairs take the lowest)
assert len(sloping.stairs) == 5 * abs(slope.rise)
assert not set(sloping.stairs) & sloping.inside
assert all(len({c[1] for c in layer}) == 1 for layer in sloping.layers)
assert domes.middle((-117, 5, 3), 0.5) == "-116.5 5.5 3.5"
x, _, z = L.DOMES[0].floor_centre
assert f"x={x + 0.5},y=" in domes.sphere(L.DOMES[0])
assert f"z={z + 0.5}," in domes.sphere(L.DOMES[0])
"""
    )


def test_station_game_pack():
    run(
        """
import build_station as B
import datapack
import game
import verify_station as V

# the functions other modules and the start dome's buttons call
pack = B.new_pack("t")
for path in (
    "run/start", "dome/0/solved", "dome/7/solved", "tunnel/0/open",
    "tunnel/0/reset", "tunnel/7/open", "tunnel/7/reset", "vote/reset",
    "vote/difficulty", "vote/confirm", "reset/all", "recall", "kit/start",
    "difficulty/apply", "players/scan",
):
    assert path in pack.functions, path
assert game.scaled(5) == dict.fromkeys(game.SCALED, 100)
assert game.scaled(1)["#diff.timer"] > 100 > game.scaled(1)["#diff.count"]
# nothing aims at the nearest player or at everyone
for name, lines in pack.functions.items():
    for line in lines:
        assert "@p" not in line and "@a " not in line and not line.endswith("@a"), (
            name, line)

# a module: its functions are added, its hooks called, its reset registered
def functions(pack):
    pack.function("dome/3/enter", ["say in"])
    pack.function("dome/3/tick", ["say tick"])
    pack.function("dome/3/duo", ["say two"])
    pack.function("dome/3/reset", ["say reset"])
    pack.function("mine/reset", ["say mine"])

module = game.Module("test", functions=functions, resets=("mine/reset",))
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [module])
called = lambda path, name: any(  # noqa: E731
    line.endswith(f"function station:{name}") for line in pack.functions[path]
)
assert called("dome/3/entered", "dome/3/enter")
assert called("game/tick", "dome/3/tick")
assert called("dome/3/form", "dome/3/duo")
assert not any("dome/3/solo" in line for line in pack.functions["dome/3/form"])
assert called("reset/all", "dome/3/reset") and called("reset/all", "mine/reset")
assert "dome/4/form" not in pack.functions
assert not V.function_problems(B.pack_files(pack))
"""
    )


def test_station_start_dome():
    run(
        """
import build_station as B
import dome_start as S
import domes
import station_layout as L
import tunnels
import verify_station as V
from fake_client import AIR

assert B.STAGES["start_dome_inside"] is S.build and "start_dome" in V.LIVE
dome = L.DOMES[0]
solid, fit = S.blocks()
# nothing in the lift's column, the reserved cells or the shell
used = set(solid) | set(fit)
assert used <= domes.dome_cells(dome).interior
assert not used & (tunnels.reserved_cells(dome) | S.lift_column())
assert set(S.floor_blocks()) <= domes.dome_cells(dome).floor
assert not set(S.floor_blocks()) & (domes.light_cells(dome)[0] | S.lift_column())
# a clear walk at foot and head height from where a player arrives and
# from every side of the lift's shaft to the east mouth, to everything a
# player uses and up to the gallery: the test the live check runs too
assert S.walk_problems() == [], S.walk_problems()
x, y, z, _ = domes.entrance(dome)
standing = S.standing_cells()
assert (x, y, z) in standing and not standing & set(solid)
# the reset button is behind its door: reached only through the door's cell
rx, _, rz = S.RESET
beside = [(rx + dx, y, rz + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
assert [c for c in beside if c in standing] == [S.door_cells()[0]]

# the dressing: in nobody's way, nothing in it to work, and the machine
# in its cage out of reach of every place a player can stand
extra_solid, extra_fit = S.dressing()
extra = {**extra_solid, **extra_fit}
assert len(extra) > 800 and set(extra) <= used
for word in ("lever", "button", "pressure_plate", "door", "chest", "target"):
    assert not any(word in block for block in extra.values()), word
bars = {c for c, b in extra.items() if S.BARS in b}
(e1, n1), (e2, n2) = S.CAGE
works = {c for c, b in extra.items() if "repeater" in b or "redstone" in b}
works |= set(S.G_PISTONS) | S.moving_cells()
for e in range(e1, e2 + 1):
    for n in range(n1, n2 + 1):
        assert extra[S.at(e, n, S.CAGE_ROOF)] == S.GRATE
        for h in range(1, S.CAGE_ROOF):
            cell = S.at(e, n, h)
            if e in (e1, e2) or n in (n1, n2):
                assert cell in bars, cell
            else:
                works.discard(cell)
assert not works  # every working part is inside the bars and under the roof
walked = S.reach((x, y, z))
inside_cage = {
    S.at(e, n, h)
    for e in range(e1 + 1, e2)
    for n in range(n1 + 1, n2)
    for h in range(1, S.CAGE_ROOF)
}
assert not inside_cage & walked
g = S.gallery()
assert all((S.at(e, n, S.DECK + 1) in walked) for e, n in g.walk)
assert all(S.at(e, n, S.DECK + 1) in bars for e, n in g.rails)
assert not S.moving_cells() & set(fit) and S.changing_cells() <= set(solid)

# the map is the layout's ring: a lamp a dome, a line a tunnel, each line
# straight between its two domes' lamps, and the start dome's lamp open
m = S.map_cells()
assert set(m.lamps) == {d.index for d in L.DOMES}
assert set(m.lines) == {t.index for t in L.TUNNELS} and all(m.lines.values())
drawn = [c for shape in m.shapes.values() for c in shape]
assert len(drawn) == len(set(drawn))  # no two domes share a block
for d in L.DOMES:
    assert m.places[d.index] in m.shapes[d.index]
    assert m.lamps[d.index] == S.MAP.front(*m.places[d.index])
# a bigger dome is drawn no smaller
by_size = sorted(L.DOMES, key=lambda d: d.diameter)
sizes = [len(m.shapes[d.index]) for d in by_size]
assert sizes == sorted(sizes) and sizes[0] < sizes[-1]
# a tunnel's pipe joins its two domes' discs, in a straight line
for t in L.TUNNELS:
    cells = set(m.lines[t.index])
    assert len({c[1] for c in cells}) == 1 or len({(c[0], c[2]) for c in cells}) == 1
    for end in (t.start, t.end):
        disc = {S.MAP.front(*c) for c in m.shapes[end]}
        assert any(
            abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) == 1
            for a in cells
            for b in disc
        )
# "you are here" is over the start dome, and the shore is drawn
assert m.pin[0] == m.places[0][0] and m.pin not in drawn and m.shore and m.route
assert solid[S.MAP.front(*m.pin)] == S.PIN[0]
# facing the wall, a dome that lies to the left in the station is to the
# left on the map
right = S.MAP.right
side = lambda d: d.centre[0] * right[0] + d.centre[1] * right[1]  # noqa: E731
for a in L.DOMES:
    for b in L.DOMES:
        if side(a) < side(b):
            assert m.places[a.index][0] <= m.places[b.index][0]
assert solid[m.lamps[0]] == S.DOME_LAMP[1] and solid[m.lamps[1]] == S.DOME_LAMP[0]
# the trophy wall's block is the wall's alone
assert S.TROPHY not in {domes.door_block(0, 1), domes.door_block(1, 1), domes.FRAME}
assert {c for c, b in solid.items() if b == S.TROPHY} == S.trophy_cells()
assert not S.trophy_cells() & S.clear_cells()
# the trophy dispenser: in the Wall's brass border, clear of the trophies'
# blocks and of the cells their signs go in
signs = {S.FAME.front(k, h) for k in range(1, S.FAME.width - 1)
         for h in range(1, S.FAME.height)}
prize = {S.DISPENSER, S.PRIZE_LAMP, S.PRIZE_BUTTON}
assert not prize & (S.trophy_cells() | signs)
assert solid[S.DISPENSER].startswith("minecraft:dispenser[")
assert solid[S.PRIZE_LAMP] == S.UNLIT and "button" in fit[S.PRIZE_BUTTON]

# built against the fake client: every block where the plan has it, the
# same built twice, and the trophies' wall never emptied
stages = ["site", "start_dome", "start_dome_inside", "tunnels"]
rec = B.offline_build(stages=stages, force=False)
want = {**S.floor_blocks(), **solid, **fit}
for cell, block in want.items():
    got = rec.world.at(cell)
    assert got == block or got.startswith(block + "{"), (cell, got, block)
assert rec.world.at(S.LECTERN).count("Good luck") == 0  # a page a command
summons = [c for c in rec.commands if c.startswith("summon ")]
assert summons == list(S.entities()) and len(summons) > 40
assert sum("minecraft:interaction" in c for c in summons) == 3
engine = set(tunnels.engine_cells(L.TUNNELS[0]).values())
inside = domes.dome_cells(dome).interior
assert all(rec.world.name_at(c) == AIR for c in inside - used - engine)
again = B.offline_build(stages=[*stages, "start_dome_inside"], force=False)
assert again.world.dump() == rec.world.dump()
start = rec.commands.index(f"kill @e[tag={S.TAG}]")
emptied = [c for c in rec.commands[start:] if c.endswith(" minecraft:air")]
x1 = min(c[0] for c in S.trophy_cells())
assert emptied and not any(f"fill {x1} " in c and "replace" in c for c in emptied)

# the pack: the core's hooks, the vote reached as the player who clicked,
# never as whoever is nearest
pack = B.new_pack("t")
f = pack.functions
assert {"dome/0/tick", "dome/0/reset", "dome/0/show"} <= set(f)
assert any(l.endswith("function station:dome/0/tick") for l in f["game/tick"])
assert any(l.endswith("function station:dome/0/reset") for l in f["reset/all"])
assert any("function station:run/start" in l for l in f["dome/0/lever/pull"])
assert any(
    l == "execute on target run function station:dome/0/press/reset"
    for l in f["dome/0/click/reset"]
)
assert f["dome/0/press/reset"][-1] == "function station:vote/reset"
confirm = " ".join(f["dome/0/press/confirm"])
assert "function station:vote/confirm" in confirm
assert "function station:vote/difficulty with storage" in confirm
for name, lines in f.items():
    if name.startswith("dome/0/"):
        assert not any("sort=nearest" in l or "@p" in l for l in lines), name
for i, cell in m.lamps.items():
    at = f"setblock {cell[0]} {cell[1]} {cell[2]} "
    assert sum(at in l and f"#d{i} " in l for l in f["dome/0/show"]) == 3
# the machinery: stepped by the tick, and no reset touches the dressing
assert {"dome/0/machine/step", "dome/0/machine/gauge"} <= set(f)
assert any("dome/0/machine/step" in l for l in f["dome/0/tick"])
import re
touched = {
    tuple(int(v) for v in found)
    for l in f["dome/0/reset"]
    for found in re.findall(r"setblock (-?\\d+) (-?\\d+) (-?\\d+) ", l)
}
assert touched and not touched & (set(extra) | S.moving_cells())
assert not touched & (S.trophy_cells() | signs)  # the Wall of Fame left alone
# the trophy: armed at the win, made at a press for the presser alone, one
# a player a run, never given silently, never stocked in the dispenser
assert "function station:dome/0/trophy/arm" in f["run/win"]
arm = " ".join(f["dome/0/trophy/arm"])
assert f"tag @e[tag=st.in] add {S.DUE}" in arm and "trophy/title" in arm
assert "Your trophy waits by the Wall of Fame" in " ".join(f["dome/0/trophy/title"])
press = f["dome/0/press/trophy"]
paid = press.index(f"tag @s remove {S.DUE}")
assert paid < next(i for i, l in enumerate(press) if "trophy/drop" in l)
assert all(S.DUE in l or "#runid" in l or "st.in" in l for l in press[:paid])
drop = " ".join(f["dome/0/trophy/drop"])
for part in (S.TROPHY, S.LORE[0], "Place on the Wall of Fame (gilded blackstone)",
             "Owner set from entity @s UUID", "Age:-32768s", "Trophy: level $(level)"):
    assert part in drop, part
assert not any(S.SIGN in l and ("give " in l or "item replace block" in l)
               for lines in f.values() for l in lines)
reset = f["dome/0/reset"]
for line in (f"kill @e[type=minecraft:item,tag={S.ITEM_TAG}]",
             f"tag @e[tag={S.DUE}] remove {S.DUE}",
             "function station:dome/0/trophy/show"):
    assert line in reset, line
assert any("click/trophy" in l for l in f["dome/0/tick"])
assert any("trophy/show" in l for l in f["dome/0/refresh"])
book = S.lectern(S.PAGES)
assert all(len(c.encode()) <= B.MAX_COMMAND for c in S.book_commands())
assert S.TITLE in book and book.count('","') == len(S.PAGES) - 1
"""
    )


def test_station_boiler_room():
    run(
        """
import build_station as B
import datapack
import dome_boiler as D
import domes
import game
import station_layout as L
import tunnels
import verify_station as V

dome = L.DOMES[D.INDEX]
assert B.STAGES["dome_1_inside"] is D.build and V.LIVE["boiler_room"] is D.check
assert "boiler_room" not in V.todos()

# the room's cells: inside the dome, off the reserved cells, and the same
# room in the dome's own frame whichever way the dome is entered
assert not D.room_problems(dome)
blocks = D.room_blocks(dome)
place = D.room(dome)
used = set(blocks.solid) | set(blocks.attached) | blocks.clear
assert used <= domes.dome_cells(dome).interior
assert not used & tunnels.reserved_cells(dome)
assert set(blocks.floor) <= domes.dome_cells(dome).floor
fr = D.frame(dome)
assert fr.at(0, 0, 0) == dome.floor_centre
x, y, z, _ = domes.entrance(dome)
assert fr.at(-(dome.radius - domes.ENTRANCE_OFFSET), 0, 1) == (x, y, z)
turned = D.Frame((0, 0, 0), (0, 1), domes.across((0, 1)))
assert turned.at(2, 3, 1) == (-3, 1, 2) and turned.facing(1, 0) == "south"
# the two valves are far apart, and the plates are not where the levers are
a, b = place.valves
apart = abs(a.plate[0] - b.plate[0]) + abs(a.plate[2] - b.plate[2])
assert apart >= 12 and a.plate != a.lever

# the boiler house round the puzzle: nothing of it can be worked by hand,
# it shares no cell with the puzzle, and it leaves every walk the puzzle
# needs clear at foot and head height in both forms, and the gauge in sight
puzzle, dress = D.puzzle_blocks(dome), D.dressing_blocks(dome)
assert not set(puzzle.everything()) & set(dress.everything())
assert len(dress.everything()) > len(puzzle.everything())
for block in dress.everything().values():
    assert not any(w in block for w in ("lever", "button", "pressure_plate")), block
assert D.fr_of(fr, fr.at(-4, 9, 3)) == (-4, 9)
assert not D.walk_problems(dome) and not D.sight_problems(dome)
assert {"the gantry", "valve A", "valve B", "the way out"} <= set(D.walks(dome))
top = max(c[1] for c in dress.solid) - dome.floor_y
assert top >= 12 and D.walks(dome)["the gantry"][1] - dome.floor_y == D.DECK_H + 1
# both checks find a fault: a wall across the dome, a block before the gauge
real = D.dressing_blocks
def walled(dome):
    d = real(dome)
    for r in range(-dome.radius, dome.radius + 1):
        for h in (1, 2, 3):
            if fr.at(4, r, h) in domes.dome_cells(dome).interior:
                d.solid.setdefault(fr.at(4, r, h), D.COPPER)
    return d
D.dressing_blocks = walled
assert any("valve A" in p for p in D.walk_problems(dome))
assert any("the way out" in p for p in D.walk_problems(dome))
assert any("valve B" in p for p in D.sight_problems(dome))
assert D.room_problems(dome)
D.dressing_blocks = real

# the stage against the fake client: every block where the plan has it,
# the dome's shell and the pump engine left alone, the same built twice
stages = ["site", "dome_1", "tunnels", "dome_1_inside"]
rec = B.offline_build(stages=stages, force=False)
for cell, block in blocks.everything().items():
    assert rec.world.at(cell) == block, (cell, block)
engine = tunnels.engine_cells(L.TUNNELS[D.INDEX])
assert all(rec.world.name_at(c) != "minecraft:air" for c in list(engine.values())[:9])
shell = domes.dome_cells(dome).shell
assert all(rec.world.name_at(c) != "minecraft:air" for c in shell)
assert sum(c.startswith("summon minecraft:interaction") for c in rec.commands) == 1
assert "function station:dome/1/reset" in rec.commands
again = B.offline_build(stages=[*stages, "dome_1_inside"], force=False)
assert again.world.dump() == rec.world.dump()

# the values of a level: gentle at 1, tuned at 5, hard at 10
one, five, ten = (D.scaled(level) for level in (1, 5, 10))
assert five == {"lo": 7000, "leak": D.LEAK, "need": D.HOLD_STEPS, "fuel": D.FUEL_STEPS}
assert one["lo"] < five["lo"] < ten["lo"] < D.BAND_HI
assert one["leak"] < five["leak"] < ten["leak"]
assert one["need"] < five["need"] < ten["need"] and one["fuel"] > ten["fuel"]
for level in game.LEVELS:
    v = D.scaled(level)
    assert v["lo"] % D.LAMP == 0 and D.BAND_HI - v["lo"] >= D.LAMP
    assert 4 * v["fuel"] * 2 * D.RISE >= D.BAND_HI  # four coals a boiler climb it
# at the tuned level one coal in each boiler outlasts the climb to the band
assert five["fuel"] * 2 * D.RISE >= D.BAND_HI

# the pack: the hooks the core calls, one way to solve, nothing aimed wide
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [D.MODULE])
for hook in game.HOOKS:
    assert f"dome/1/{hook}" in pack.functions, hook
calls = lambda path, name: any(  # noqa: E731
    line.endswith(f"function station:{name}") for line in pack.functions[path]
)
assert calls("dome/1/entered", "dome/1/enter") and calls("game/tick", "dome/1/tick")
assert calls("dome/1/form", "dome/1/solo") and calls("dome/1/form", "dome/1/duo")
assert calls("reset/all", "dome/1/reset") and calls("dome/1/left", "dome/1/empty")
solvers = [n for n, ls in pack.functions.items() if n.startswith("dome/1/")
           and any("function station:dome/1/solved" in line for line in ls)]
assert solvers == ["dome/1/done"], solvers
assert any("on target run function station:recall" in line
           for line in pack.functions["dome/1/recall"])
assert not V.function_problems(B.pack_files(pack))
# the machinery runs whether or not there is a puzzle, is stilled by the
# reset and when the room empties, and no function of the puzzle reads it
tick = pack.functions["dome/1/tick"]
at = lambda end: next(i for i, l in enumerate(tick) if l.endswith(end))  # noqa: E731
assert at("function station:dome/1/dress") < at("function station:dome/1/step")
assert calls("dome/1/reset", "dome/1/rest") and calls("dome/1/empty", "dome/1/rest")
machine = [D._xyz(c) for c in (*place.governor, *place.gov_power, place.gov_lamp,
                               place.bell, place.bell_power, *place.chaser)]
for name in ("fires", "valves", "pressure", "hold", "show", "gauge", "solo", "duo"):
    for line in pack.functions[f"dome/1/{name}"]:
        assert not any(xyz in line for xyz in machine), (name, line)
# the logbook goes over RCON in the build
assert len(D.logbook(fr).encode()) < B.MAX_COMMAND
"""
    )


def test_station_way_in():
    run(
        """
import build_station as B
import datapack
import domes
import game
import shore as S
import station_layout as L
import tunnels
import verify_station as V

assert {"shore", "dock", "lift"} <= set(B.written())
assert {"shore", "dock", "lift"} <= set(V.LIVE) - set(V.todos())

# where things are: the jetty leaves the landing towards the dock and
# leaves the landing block alone; the lift is the layout's, 5 x 5 in the
# middle of the start dome, clear of what the dome reserves
start = L.START
cells = domes.dome_cells(start)
assert L.SHORE_LANDING not in S.jetty_cells()
assert all(c[1] == L.SHORE_LANDING[1] for c in S.jetty_cells())
assert (S.CX, S.CZ) == L.LIFT_XZ == start.centre
column = S.column_cells()
assert len(column) == 25 * (L.LIFT_TOP_Y - L.LIFT_BOTTOM_Y + 1)
fixed, signs = S.lift_blocks(), dict(S.lift_signs())
moving = S.lift_state(S.TOP) | S.lift_state(S.BOTTOM)
in_dome = {c for c in [*fixed, *signs, *moving] if c[1] <= start.top_y}
assert in_dome <= column and not in_dome & tunnels.reserved_cells(start)
# the shaft cuts the shell only at the top, and those cells are registered
opening = S.opening_cells()
assert len(opening) == 25 and opening <= cells.shell
assert domes.OPENINGS[start.index] == opening
assert (set(fixed) | set(moving)) & cells.shell <= opening
# the dock stands clear of the shaft and of the dome
dock = S.dock_blocks()
low_dock = {c[::2] for c in dock if c[1] <= L.LIFT_TOP_Y}
assert not low_dock & {c[::2] for c in column}
assert all(c[1] > start.top_y for c in dock)
assert len(S.moorings("shore")) == len(S.moorings("dock")) == 2
for place in ("shore", "dock"):
    a, b = S.moorings(place)
    assert abs(a[0] - b[0]) + abs(a[2] - b[2]) > 2 * S.BOAT_NEAR

# the stages against the fake client: the shore's chunks loaded for the
# build and released, every block in place, the dome whole but for the
# hole, the same built twice
stages = ["site", "start_dome", "shore", "dock", "lift"]
rec = B.offline_build(stages=stages, force=False)
assert rec.forceloaded == B.site_chunks()
assert not [r for r in rec.replies if "not loaded" in r]
world = rec.world
assert L.dome_at(*L.DOCK) is None and world.name_at(L.DOCK) == S.GRATE


def missing(blocks):
    return {c: b for c, b in blocks.items() if c[1] <= B.station_box()[1][1]
            and world.at(c) != b and world.name_at(c) != b}


assert not missing(dock) and not missing(fixed) and not missing(signs)
assert not missing(S.lift_state(S.TOP))
hole = opening - S.ring_cells(S.APEX)
assert {c for c in cells.shell | cells.floor if world.name_at(c) == domes.AIR} == hole
assert all(world.name_at(c) == domes.AIR for c in tunnels.reserved_cells(start))
summoned = [c for c in rec.commands if c.startswith("summon minecraft:marker")]
assert len(summoned) == 4, summoned
again = B.offline_build(stages=[*stages, "shore", "dock", "lift"], force=False)
assert again.world.dump() == world.dump()

# the pack: the boats kept and reset, the lift's functions; the cage sent
# down and up by the functions' own block commands, a block at a time
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [S.MODULE])
assert not V.function_problems(B.pack_files(pack))
reset = pack.functions["reset/all"]
assert {"function station:shore/reset", "function station:lift/reset"} <= set(reset)
assert sum("summon" in line for line in pack.functions["shore/boats"]) == 2


def run(path, f=None):
    for line in pack.functions[path]:
        words = line.split()
        if words[0] not in ("fill", "setblock"):
            continue
        n = 7 if words[0] == "fill" else 4
        for i in range(1, n):
            if words[i].startswith("~"):
                words[i] = str((S.CX, f, S.CZ)[(i - 1) % 3] + int(words[i][1:] or 0))
        rec.run(" ".join(words))


run("lift/leave/top")
assert world.name_at(L.DOCK) == domes.AIR
for f in range(S.TOP, S.BOTTOM, -1):
    run("lift/pay", f)
run("lift/here/bottom")
assert not missing(S.lift_state(S.BOTTOM)) and not missing(fixed)
assert world.name_at(start.floor_centre) != domes.AIR
run("lift/leave/bottom")
for f in range(S.BOTTOM + 1, S.TOP + 1):
    run("lift/reel", f)
run("lift/here/top")
assert not missing(S.lift_state(S.TOP)) and not missing(fixed)
run("lift/leave/top")
for f in range(S.TOP, S.TOP - 9, -1):
    run("lift/pay", f)
run("lift/reset")
# the trip is slow, and what travels is made and removed by the pack
assert 9 * 20 <= S.TRIP + S.LEAD <= 13 * 20
leave = pack.functions["lift/leave/top"]
assert sum("block_display" in line for line in leave) == 18
here = pack.functions["lift/here/bottom"]
assert any("kill @e[tag=st.lift.car]" in line for line in here)
assert not missing(S.lift_state(S.TOP)) and not missing(fixed)
"""
    )


def test_station_ring_helpers():
    run(
        """
import automatons
import build_station as B
import domes
import fittings
import game

pack = B.new_pack("t")
f = pack.functions
# every tunnel is built: its states, and no stub
assert all(f"tunnel/{n}/state_1" in f for n in range(len(B.station_layout.TUNNELS)))
# the kits after the start kit, on entering their domes
for n, name in game.KITS.items():
    given = f"function station:kit/{name}"
    assert any(line.endswith(given) for line in f[f"dome/{n}/entered"])
# the last dome is the win, and a module's win function is called
last = len(B.station_layout.DOMES) - 1
assert "function station:run/win" in f[f"dome/{last}/solved"]
assert f"function station:tunnel/{last}/ready" in f[f"dome/{last}/solved"]
# solving wakes a pump; its lever by the airlock starts it (tunnel 0: the
# master lever, at once)
import tunnels
assert f["tunnel/0/ready"] == ["function station:tunnel/0/open"]
assert "function station:tunnel/tick" in f["game/tick"]
for n in tunnels.LEVERED:
    t = B.station_layout.TUNNELS[n]
    assert not tunnels.lever_problems(t), n
    x, y, z = tunnels.lever_cell(t)
    assert f"setblock {x} {y} {z} {tunnels.lever_block(t)}" in f[f"tunnel/{n}/ready"]
    gone = f"setblock {x} {y} {z} minecraft:air"
    assert gone in f[f"tunnel/{n}/reset"] and gone in f[f"tunnel/{n}/door_2"]
    assert any(f"if block {x} {y} {z} minecraft:lever[powered=true]" in line
               and line.endswith(f"tunnel/{n}/open") for line in f["tunnel/tick"])
    assert f"scoreboard players set #t{n}.ready st 0" in f[f"tunnel/{n}/begin"]
import datapack
module = game.Module(
    "t",
    functions=lambda p: [p.function("dome/7/trophy", ["say won"]),
                         p.function("dome/2/leave", ["clear @s minecraft:stick"])],
    wins=("dome/7/trophy",),
)
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [module])
assert pack.functions["run/win"][-1] == "function station:dome/7/trophy"
assert pack.functions["dome/2/exited"][-1] == "function station:dome/2/leave"
assert "data/station/loot_table/empty.json" in pack.files()
# automatons: the plan's rules in the summon, and gone when a dome empties
line = automatons.summon(
    "minecraft:zombie", "Stoker", "1.5 2 3.5", 4, automatons.COPPER
)
for part in ("IsBaby:0b", "CanPickUpLoot:0b", "PersistenceRequired:1b",
             "station:empty", "spawn_reinforcements", "st.mob4", "head:0f"):
    assert part in line, part
assert "spawn_reinforcements" not in automatons.summon(
    "minecraft:skeleton", "Riveter", "1 2 3", 4)
assert automatons.remove_line(4) in pack.functions["dome/4/left"]
assert len(line.encode()) < B.MAX_COMMAND
# restricted items
item = fittings.restricted("minecraft:oak_sign", place_on="minecraft:gold_block")
assert 'minecraft:can_place_on={blocks:"minecraft:gold_block"}' in item
# water that is meant: left out of the wet check, and only there
dome = B.station_layout.DOMES[3]
cells = sorted(domes.dome_cells(dome).interior)[:50]
def looked_at():
    return sum(b[0] - a[0] + 1 for p in domes.check_parts(dome) for a, b in p)

before = looked_at()
domes.add_wet(3, cells)
assert looked_at() == before - 50
"""
    )


def test_station_shared_room_helpers():
    run(
        """
import automatons
import build_station as B
import datapack
import domes
import fittings as F
import game
import rooms
import station_layout as L
import tunnels

dome = L.dome("signal")  # a small dome, which a wall can cut across
fr = F.frame(dome)
cells = domes.dome_cells(dome)

# a stub: its post is inside the dome, off the reserved cells, its lever
# on gold with a sign, and its functions solve the dome and put it back
post = game.stub_post(dome)
blocks = {**post.solid, **post.attached}
assert not rooms.room_problems(dome, blocks)
assert not rooms.input_problems(blocks, {post.input})
stub = datapack.Pack(stamp="t")
game.stub_module(dome).functions(stub)
n = dome.index
assert f"function station:dome/{n}/solved" in stub.functions[f"dome/{n}/tick"][0]
assert stub.functions[f"dome/{n}/reset"][0].endswith("minecraft:air")
pack = B.new_pack("t")
reset = pack.functions["reset/all"]
assert reset.index("function station:tunnel/7/reset") < reset.index(
    "function station:dome/1/reset"
)
assert not any(line.startswith("kill") and "distance" in line for line in reset)

# the room checks find faults
assert rooms.room_problems(dome, {dome.floor_centre: "minecraft:stone"})
x, y, z, _ = domes.entrance(dome)
assert any("reserved" in p for p in rooms.room_problems(dome, {(x, y, z): "a"}))
assert any(
    "dome 2" in p
    for p in rooms.room_problems(dome, {fr.at(0, 0, 1): "minecraft:raw_gold_block"})
)
track = {F.frame(L.DOMES[2]).at(0, 0, 1): "minecraft:raw_gold_block"}
assert not rooms.room_problems(L.DOMES[2], track)
# an input nobody listed, one not on gold, one with a piston on its block
lever = F.lever("east")
at = fr.at(0, 0, 1)
bad = {at: "minecraft:stone", (at[0] + 1, at[1], at[2]): lever}
found = rooms.input_problems(bad, set())
assert any("does not list" in p for p in found)
found = rooms.input_problems(bad, {(at[0] + 1, at[1], at[2])})
assert any("not on gold" in p for p in found) and any("no sign" in p for p in found)
good = F.input_post(at, "east", lever, ("VALVE",))
blocks = {**good.solid, **good.attached}
assert not rooms.input_problems(blocks, {good.input})
blocks[at[0], at[1] + 1, at[2] + 1] = "minecraft:piston[facing=up]"
assert any("touches" in p for p in rooms.input_problems(blocks, {good.input}))
# a walk: a wall across the dome stops it, a gap in the wall lets it by
far = fr.at(8, 0, 1)
wall = {fr.at(4, r, h): "minecraft:stone" for r in range(-20, 21) for h in (1, 2, 3)}
wall = {c: b for c, b in wall.items() if c in cells.interior}
assert rooms.walk_problems(dome, wall, {"the far side": far})
del wall[fr.at(4, 0, 1)], wall[fr.at(4, 0, 2)]
assert not rooms.walk_problems(dome, wall, {"the far side": far})
# sight: stone hides, glass does not
eye, lamp = fr.at(-2, 0, 1), fr.at(6, 0, 2)
here, there, mid = {"here": eye}, {"lamp": lamp}, fr.at(2, 0, 2)
assert rooms.sight_problems({mid: "minecraft:stone"}, here, there)
assert not rooms.sight_problems({mid: "minecraft:glass"}, here, there)
# the window: a wall before the entrance hides it, unless the dome says so
screen = {
    fr.at(-6, r, h): "minecraft:stone" for r in range(-6, 7) for h in range(1, 6)
}
assert rooms.window_problems(dome, screen) and not rooms.window_problems(dome, {})
domes.allow(dome.index, "the screen", "a test")
assert not rooms.window_problems(dome, screen)

# fittings give what the game takes
clock = F.torch_clock(fr, 0, 6, lamps=True, pistons=True)
assert len(clock.lamps) == 4 and len(clock.pistons) == 2
assert sum("repeater" in b for b in clock.attached.values()) == 2
assert all("sticky" not in b for b in clock.solid.values())
lines = F.gauge_lines([(1, 2, 3), (1, 3, 3)], "#p st", 10, "a[on]", "a[off]")
assert len(lines) == 4 and "matches 20.." in lines[2]
item = F.lent(F.restricted("minecraft:stick", place_on="minecraft:gold_block"), "k")
assert item.endswith('minecraft:custom_data={st_lent:"k"}]') and item.count("[") == 2
plain = F.lent("minecraft:stick", "k")
assert plain == 'minecraft:stick[minecraft:custom_data={st_lent:"k"}]'

# fights: the three kinds, waves, a death, a bar
assert [k.name for k in automatons.KINDS] == ["Stoker", "Riveter", "Slag Husk"]
pack = datapack.Pack(stamp="t")

def functions(p):
    w = automatons.waves(p, 4, [fr.at(0, 0, 1), fr.at(3, 0, 1)], cap=6)
    b = automatons.bar(p, 4, "Accumulator")
    p.function("dome/4/tick", [w.tick, w.leash])
    p.function("dome/4/died", ["say ouch"])
    p.function("dome/4/enter", [w.arm, b.show])

game.add_functions(pack, [game.Module("t", functions=functions)])
f = pack.functions
assert f["dome/4/respawned"][-1] == "function station:dome/4/died"
assert automatons.respawn_lines(L.DOMES[4])[0] in f["dome/4/respawned"]
# the checks' cell: in the station's box, clear of every dome, tunnel,
# the dock and its lift, and the test bench (all near the ring's edges)
cell = F.check_cell()
box = {(x, y, z) for x in (cell.low[0], cell.high[0])
       for y in (cell.low[1], cell.high[1]) for z in (cell.low[2], cell.high[2])}
assert all(L.in_station(*c) for c in box)
(x1, y1, z1), (x2, y2, z2) = cell.low, cell.high
def clear(x, z, reach):
    dx = max(x1 - x, 0, x - x2)
    dz = max(z1 - z, 0, z - z2)
    return dx * dx + dz * dz > reach * reach
assert all(clear(*d.centre, d.radius + 2) for d in L.DOMES)
assert all(
    clear(t.a[0] + s * t.step[0], t.a[2] + s * t.step[1], 6)
    for t in L.TUNNELS for s in range(t.length + 1)
)
assert clear(L.DOCK[0], L.DOCK[2], 64)  # the dock, its lift and the bench
assert y2 < L.SEA_LEVEL - 1 and F.CHECK_INDEX not in {d.index for d in L.DOMES}
assert any("fight/respawned" in line for line in f["game/tick"])
shown = "station:d4 players @a[tag=st.in,scores={st.dome=4}]"
assert any(shown in line for line in f["game/second"])
assert "function station:dome/4/bar/hide" in f["reset/all"]
assert sum("spawn/stoker" in l for l in f["dome/4/wave/cast/stoker"]) == 12
assert all(len(l.encode()) < B.MAX_COMMAND for l in f["dome/4/wave/spawn/stoker_0"])
"""
    )


def test_station_checks_keep_best_times():
    run(
        """
import build_station as B
import game
import game_checks as G
import verify_station as V

# every level's best time is saved with the level, and put back
assert set(G.BEST_SCORES) == {f"#best{level}" for level in game.LEVELS}
assert set(G.BEST_SCORES) <= set(G.LEVEL_SCORES)


class Ctx:
    def __init__(self, scores):
        self.scores = dict(scores)

    def score(self, name, objective=None):
        return self.scores.get(name)

    def set_score(self, name, value):
        self.scores[name] = value


# a check that wins a run (the ring did: #best5 left at 135 s) and one
# that raises after changing the level: both put back by the runner
before = {"#run": 0, "#level": 7, "#run.level": 0, "#best5": 0, "#best7": 600}
ctx = Ctx(before)


def wins(c):
    c.set_score("#run.level", 5)
    c.set_score("#best5", 135)
    c.set_score("#best7", 90)
    return []


def raises(c):
    c.set_score("#level", 2)
    c.set_score("#best2", 42)  # a level that had no best time at all
    raise RuntimeError("garbled")


B.players_online = lambda: []
B.Context = lambda **kw: ctx
B.new_pack = lambda: None
B.forceload = lambda c: None
V.LIVE = {"wins": wins, "raises": raises}
results = V.live_checks(None)
assert results["wins"] == [] and "garbled" in results["raises"][0], results
want = before | {f"#best{level}": 0 for level in game.LEVELS} | {"#best7": 600}
assert ctx.scores == want, ctx.scores
"""
    )


def test_station_vote_alone():
    run(
        """
import build_station as B

f = B.new_pack("t").functions
# the press that opens a vote is marked, and only that press
assert "scoreboard players set #vote.new st 1" in f["vote/open"]
for path in ("vote/reset", "vote/difficulty"):
    assert f[path][-1] == "scoreboard players set #vote.new st 0", path
# a player alone: that press is no yes (st.vote 2 is not counted), so a
# scan's count cannot pass it; a second press sets the yes
tally = f["vote/tally"]
alone = next(i for i, l in enumerate(tally) if "vote/alone" in l)
passing = next(i for i, l in enumerate(tally) if "vote/pass" in l)
assert alone < passing and "#vote.new st matches 1" in tally[alone]
assert "#vote.need st matches 1" in tally[alone] and "return run" in tally[alone]
assert "scoreboard players set @s st.vote 2" in f["vote/alone"]
assert all("st.vote=2" not in l for l in f["vote/count"])
assert f["vote/yes"][0] == "scoreboard players set @s st.vote 1"
# the bar: the seconds shown, and "press again" for one alone
assert "press again to confirm, $(left) s" in f["vote/show_alone"][0]
assert "$(yes) of $(need), $(left) s" in f["vote/show_all"][0]
assert "function station:vote/show" in f["vote/second"]
"""
    )
