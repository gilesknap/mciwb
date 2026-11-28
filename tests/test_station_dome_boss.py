"""
The Engine (the last dome) of examples/station, with no server: its room's plan
and the offline checks of it, its build stage against the example's fake
client, its datapack functions with phase 2 off and on, and its state
machine driven by a small interpreter of the functions' commands (``SIM``)
over the fake world. As in test_station_example.py, each test runs in a
Python of its own, in the example's folder.
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


def test_station_boss_room():
    run(
        """
import build_station as B
import dome_boss as D
N = D.INDEX  # the dome's place in the ring
import dome_start
import domes
import fittings
import game
import rooms
import station_layout as L
import tunnels
import verify_station as V

dome = L.DOMES[D.INDEX]
assert dome.key == "boss" and D.PHASE_2 is True
# the module takes the stub's place: its stage, its check under the name the
# verify script lists (the trophy at the win is the Pump House's)
assert B.STAGES[f"dome_{N}_inside"] is D.build and V.LIVE["boss"] is D.check
assert "boss" not in V.todos()
assert "boss" in {m.name for m in B.modules()}
assert "stub_boss" not in {m.name for m in B.modules()}
assert D.MODULE.wins == () and not hasattr(D, "TROPHY")
assert "the pavilion" in domes.ALLOWED[D.INDEX]

# the room's plan: no problem found, every cell inside the dome and off the
# reserved cells, in the dome's own frame
assert not D.room_problems(dome)
blocks = D.room_blocks(dome)
place = D.room(dome)
cells = domes.dome_cells(dome)
used = set(blocks.above()) | blocks.clear | blocks.moving
assert used <= cells.interior and not used & tunnels.reserved_cells(dome)
assert set(blocks.floor) <= cells.floor
assert not set(blocks.floor) & domes.light_cells(dome)[0]
fr = D.frame(dome)
assert fr.at(0, 0, 0) == dome.floor_centre
x, y, z, _ = domes.entrance(dome)
assert fr.at(-(dome.radius - domes.ENTRANCE_OFFSET), 0, 1) == (x, y, z)
# the entrance spot is in the pavilion, which is not the arena
(x1, y1, z1), (x2, y2, z2) = place.pavilion
assert min(x1, x2) <= x <= max(x1, x2) and min(z1, z2) <= z <= max(z1, z2)

# three levels, a centrepiece to the glass, and a lot of room
heights = {c[1] - dome.floor_y for c in blocks.solid}
assert {1, D.GALLERY_H, D.HIGH_H, D.CAP_H, D.CHIMNEY_H[1]} <= heights
assert len(blocks.above()) > 3000 and len(blocks.floor) > 2000
feet = {m.name: m.stand[1] - dome.floor_y for m in place.mains}
assert feet == {"A": 1, "B": D.GALLERY_H + 1, "C": D.HIGH_H + 1}

# the inputs: three levers and the recall button, each on gold with a sign;
# nothing else in the room can be worked, and the dressing has none
puzzle, dress = D.puzzle_blocks(dome), D.dressing_blocks(dome)
assert not (set(puzzle.everything()) | puzzle.clear) & set(dress.everything())
assert len(dress.everything()) > 10 * len(puzzle.everything())
levers = {m.lever for m in place.mains}
assert len(D.inputs(dome)) == 4 and levers < D.inputs(dome)
found = {c for c, b in blocks.above().items() if rooms.is_input(b)}
assert found == D.inputs(dome)
assert not rooms.input_problems(blocks.above(), D.inputs(dome), floor=blocks.floor)
for cell, block in dress.everything().items():
    assert not rooms.is_input(block), (cell, block)
    assert "door" not in block and "sticky" not in block, (cell, block)
for main in place.mains:
    on = rooms.carrier(main.lever, main.lever_off)
    assert blocks.solid[on] == D.BRASS
    assert "STEAM MAIN " + main.name in blocks.attached[main.sign]
    assert len(main.gauge) == D.LAMPS and len(main.telltales) == 4
    # facing the Engine at the lever: the lever is on the side of its post
    # away from the Engine, the gauge is a column just beyond the post and
    # beside it (never against it or the lever: a lever works a bulb beside
    # it), nearer the Engine, and its foot is in the valve body
    post = rooms.carrier(main.lever, main.lever_off)
    mid = dome.floor_centre
    far = lambda c: abs(c[0] - mid[0]) + abs(c[2] - mid[2])  # noqa: E731
    assert far(main.lever) > far(post) > far(main.gauge[0])
    gx, gy, gz = main.gauge[0]
    assert max(abs(gx - post[0]), abs(gz - post[2])) == 1
    assert abs(gx - post[0]) + abs(gz - post[2]) == 2
    assert all(c[0] == gx and c[2] == gz for c in main.gauge)
    beside = {(gx + i, gy, gz + j) for i, j in ((1, 0), (-1, 0), (0, 1), (0, -1))}
    body = (D.CUT, D.OXIDIZED, D.CHISELED)
    assert sum(dress.solid.get(c) in body for c in beside) >= 2
    # and the main's steam rises over the valve, in open air
    assert main.steam not in blocks.above()
# an input the room does not list, and one not on gold, are found
extra = dict(blocks.above())
spare = fr.at(-12, 12, 1)
extra[spare] = fittings.lever("north")
assert any("does not list" in p for p in rooms.input_problems(extra, D.inputs(dome)))
assert any(
    "not on gold" in p for p in rooms.input_problems(extra, D.inputs(dome) | {spare})
)
# mains A and B cannot be worked by one player: they are far apart
a, b, c = place.mains
assert abs(a.stand[0] - b.stand[0]) + abs(a.stand[2] - b.stand[2]) >= 40

# the cylinders: the shared torch clock twice, plain pistons, in a cage:
# every cell beside a part of the machine holds a block of the room
assert len(place.cylinders) == 2
above = blocks.above()
for machine in place.cylinders:
    assert len(machine.pistons) == 2 and len(machine.lamps) == 4
    parts = set(machine.solid) | set(machine.attached) | machine.moving
    assert parts <= set(above) | blocks.moving
    # the air round the machine is shut in: a few cells, walled by the cage
    air, edge, wall = set(), list(parts), set()
    while edge:
        px, py, pz = edge.pop()
        for dx, dy, dz in rooms.FACES:
            beside = (px + dx, py + dy, pz + dz)
            if beside in parts or beside in air:
                continue
            if beside in above or beside in cells.floor:
                wall.add(beside)
            else:
                air.add(beside)
                edge.append(beside)
                assert len(air) < 40, "a cylinder's cage is open"
    kinds = {D._name(above[c]) for c in wall if c in above}
    assert kinds <= {D.BARS, D.GRATE, D.CUT}, kinds
# they are in plain view from the pavilion's arch (through the bars)
eye = {"the arch": place.arch}
pistons = {f"a piston at {m.pistons[1]}": m.pistons[1] for m in place.cylinders}
clear = {c: b for c, b in above.items() if "redstone" not in b and "repeater" not in b}
assert not rooms.sight_problems(clear, eye, pistons)

# the walks and the sight lines: clear, and a fault is found
assert not D.walk_problems(dome) and not D.sight_problems(dome)
wanted = {"the way out", "main A's deck", "main B's deck", "main C's deck",
          "the crown deck", "the balcony", "the logbook"}
assert wanted <= set(D.walks(dome))
real = D.dressing_blocks
def walled(dome):
    d = real(dome)
    for r in range(-dome.radius, dome.radius + 1):
        for h in range(1, 16):
            cell = fr.at(-14, r, h)
            if cell in cells.interior and cell not in puzzle.everything():
                d.solid[cell] = D.COPPER
                d.attached.pop(cell, None)
    return d
D.dressing_blocks = walled
problems = D.walk_problems(dome)
assert any("main A's deck" in p for p in problems)
assert any("the way out" in p for p in problems)
assert any("the firebox open" in p and "the firebox at" in p for p in problems)
assert any("the firebox doors" in p for p in D.sight_problems(dome))
assert D.room_problems(dome)
D.dressing_blocks = real
def screened(dome):
    d = real(dome)
    d.solid[fr.at(0, 22, 2)] = D.COPPER  # before main A's gauge and telltales
    d.solid[fr.at(1, 22, 2)] = D.COPPER
    d.solid[fr.at(0, 23, 2)] = D.COPPER
    return d
D.dressing_blocks = screened
assert any("main A's deck" in p for p in D.sight_problems(dome))
D.dressing_blocks = real

# the casing (the doors as displays, from the breach): two halves of two
# columns each and the middle column as plates, which are all the doors'
# cells; shut, each half is exactly its cells; it opens outwards, before
# the face, through no block, and leaves room to ride out between; the
# plates land flat on open floor before the porch
assert not D.casing_problems(dome)
halves, loose = D.leaves(dome), D.plates(dome)
cells = {c for leaf in halves for c, _ in leaf.parts}
assert len(cells) == 20 and len(loose) == D.DOOR_H
assert cells | set(place.door_columns[0]) == set(place.doors)
assert all(place.doors[c] == b for leaf in halves for c, b in leaf.parts)
assert halves[0].swing == -halves[1].swing and D.OPEN == 110 and D.SWING_TICKS == 60
assert D.OUT * D.STEP == D.BLOW + D.SWING_TICKS and D.KNOCKS[-1] + 3 < D.BLOW
fx, fz = fr.forward
ox, oy, oz = dome.floor_centre
ahead = lambda p: (p[0] - ox - 0.5) * fx + (p[2] - oz - 0.5) * fz  # noqa: E731
for leaf in halves:
    shut = D.leaf_points(leaf, 0)
    opened = D.leaf_points(leaf, leaf.swing * D.OPEN)
    assert max(ahead(p) for p in shut) < D.FACE_F + 0.5
    assert min(ahead(p) for p in shut) > D.FACE_F - 0.5
    assert max(ahead(p) for p in opened) < D.FACE_F - 0.4  # all of it before the face
    assert min(ahead(p) for p in opened) > D.FACE_F - 3.2
    wrong = D.leaf_points(leaf, -leaf.swing * D.OPEN)  # (inwards: into the firebox)
    assert max(ahead(p) for p in wrong) > D.FACE_F + 1
for plate in loose:
    assert D.FACE_F - 0.5 < ahead(plate.on) < D.FACE_F - 0.5 + D.PLATE
    assert ahead(plate.land) < D.PORCH_F[0] - 2 and plate.land[1] < oy + 1.2
    assert plate.apex[1] > plate.on[1] and plate.block in (D.CHISELED, D.GRATE)
summoned = D.casing_summons(dome, opened=False)
assert len(summoned) == 25 and all(len(c.encode()) < 500 for c in summoned)
assert all(c.count("{") == c.count("}") for c in summoned)
assert all("Rotation:[0f,0f]" in c for c in summoned)
flat = D.casing_summons(dome, opened=True)
turns = [f"Rotation:[{leaf.swing * D.OPEN}f,0f]" for leaf in halves]
assert sum(turn in c for c in flat for turn in turns) == 20
# a fault is found: halves that open too far strike the plinth beside the
# porch; halves that hardly open leave no room; a plate thrown at a cylinder
keep = D.OPEN, D.PLATE_LANDS
D.OPEN = 140
assert any("degrees open" in p for p in D.casing_problems(dome))
D.OPEN = 60
assert any("no room to ride out" in p for p in D.casing_problems(dome))
D.OPEN = keep[0]
D.PLATE_LANDS = ((D.CYLINDER_F, D.CYLINDER_R, 0), *keep[1][1:])
assert any("in a block" in p for p in D.casing_problems(dome))
D.PLATE_LANDS = ((D.PORCH_F[0], 0, 0), *keep[1][1:])
assert any("off the open floor" in p for p in D.casing_problems(dome))
D.PLATE_LANDS = keep[1]
assert not D.room_problems(dome)
# the lights' wave at the ending: every dimmed lantern once, the first
# sector on the side away from the way out, the last at it
wave = D.light_wave(dome)
assert len(wave) == D.WAVE and all(wave)
assert sorted(c for sector in wave for c in sector) == sorted(D.floor_lights(dome))
ux, uz = domes.outward(dome, L.TUNNELS[D.INDEX])
out = lambda c: (c[0] - ox) * ux + (c[2] - oz) * uz  # noqa: E731
assert max(out(c) for c in wave[0]) < min(out(c) for c in wave[-1])
means = [sum(out(c) for c in sector) / len(sector) for sector in wave]
assert means == sorted(means)
# the stair to main C is one block wide and railed, so a ravager cannot
# climb it; the ramps to the gallery are three wide
stair = []
for i, r in enumerate(D.C_STAIR_R):
    h = D.GALLERY_H + 1 + i
    stair.append(fr.at(D.C_STAIR_F, r, h))
    assert "stairs" in above[stair[-1]]
    for side in (-1, 1):
        assert above[fr.at(D.C_STAIR_F + side, r, h + 1)] == D.BARS, (side, r, h)
assert all(len(row) == 3 for rows, _ in D.RAMPS for row in rows)
# with the ladders taken away the high level is still reached (the stair)
solid, blocked = D._walkable(blocks)
assert not rooms.walk_problems(dome, solid, {"C": c.stand}, blocked)
# and without the stair it is not: the ladders are not walked
no_stair = solid - set(stair)
assert rooms.walk_problems(dome, no_stair, {"C": c.stand}, blocked)

# the values of a level: gentle at 1, tuned at 5, hard at 10
one, five, ten = (D.scaled(level) for level in (1, 5, 10))
assert five["rate"] == D.WIND and five["drain"] == D.DRAIN
assert D.FULL // five["rate"] * D.STEP == 300  # 15 s to shut a main
assert one["rate"] > five["rate"] > ten["rate"] > 0
assert 0 < one["drain"] < five["drain"] < ten["drain"]
assert one["mend"] > five["mend"] > ten["mend"] > 0
assert (one["steam"], five["steam"], ten["steam"]) == (1, 2, 3)
assert [D.cap(5, 1, n) for n in range(3)] == [5, 6, 7]
assert [D.cap(5, 2, n) for n in range(3)] == [8, 9, 10]
assert D.cap(1, 1, 0) == 3 and D.cap(10, 2, 2) == 16
for level in game.LEVELS:
    assert all(D.cap(level, form, 0) >= 1 for form in (1, 2))

# the story: Finch's log, four pages at most, each short; Marsh is the Master
pages = D.log_pages(dome)
assert len(pages) <= 4 and len(D.logbook(dome).encode()) < 32500
# a page of a book is fourteen lines of some nineteen letters
lines = [sum(max(1, -(-len(part) // 19)) for part in p.split("\\n")) for p in pages]
assert all(n <= 14 for n in lines), lines
for flag in (True, False):
    D.PHASE_2 = flag
    assert all(len(p) <= 256 for p in D.log_pages(dome))
text = " ".join(pages)
assert "Marsh" in text and "Master" in text and "mains" in text
assert D.LOG_AUTHOR == "O. Finch" and "Chief Engineer" in pages[0]
assert not any(ch in text for ch in '"\\\\')
assert len(D.plaque_signs()) == 3
assert all(len(line) <= 15 for sign in D.plaque_signs() for line in sign)
for name in "ABC":
    for state in ("solo", "pair", "shut"):
        assert all(len(line) <= 15 for line in D.main_sign(name, state))
"""
    )


def test_station_boss_build():
    out = run(
        """
import build_station as B
import dome_boss as D
N = D.INDEX  # the dome's place in the ring
import domes
import game
import station_layout as L
import tunnels

dome = L.DOMES[D.INDEX]
blocks = D.room_blocks(dome)
place = D.room(dome)

# the stage against the fake client: every block where the plan has it, the
# dome's shell and the pump engine left alone, the same built twice
stages = ["site", f"dome_{N}", "tunnels", f"dome_{N}_inside"]
rec = B.offline_build(stages=stages, force=False)
for cell, block in blocks.everything().items():
    if cell != place.lectern:
        assert rec.world.at(cell) == block, (cell, block)
for cell in blocks.clear:
    assert rec.world.name_at(cell) == "minecraft:air", cell
# the log goes over RCON a page a command
assert rec.world.at(place.lectern) == D.logbook(dome, pages=1)
pages = [c for c in rec.commands if D.fittings.BOOK_PAGES in c]
assert len(pages) == len(D.log_pages(dome)) - 1
assert all(len(c.encode()) <= B.MAX_COMMAND for c in rec.commands)
engine = tunnels.engine_cells(L.TUNNELS[D.INDEX])
assert all(rec.world.name_at(c) != "minecraft:air" for c in list(engine.values())[:9])
shell = domes.dome_cells(dome).shell
assert all(rec.world.name_at(c) != "minecraft:air" for c in shell)
# the stub's bypass is gone, its entities killed
post = game.stub_post(dome)
for cell in post.cells - set(blocks.everything()):
    assert rec.world.name_at(cell) == "minecraft:air", cell
assert f"kill @e[tag={game.stub_tag(D.INDEX)}]" in rec.commands
# what it summons: the recall's interaction, a label a main, the governor
count = lambda start: sum(c.startswith(start) for c in rec.commands)  # noqa: E731
assert count("summon minecraft:interaction") == 1
assert count("summon minecraft:text_display") == 3
assert count("summon minecraft:block_display") == len(D.GOVERNOR_PARTS)
assert not any(c.startswith("summon") and "ravager" in c for c in rec.commands)
assert f"function station:dome/{N}/reset" in rec.commands
again = B.offline_build(stages=[*stages, f"dome_{N}_inside"], force=False)
assert again.world.dump() == rec.world.dump()
# a room with a problem is not built
real = D.dressing_blocks
def stray(dome):
    d = real(dome)
    x, y, z, _ = domes.entrance(dome)
    d.solid[x, y, z] = D.COPPER
    return d
D.dressing_blocks = stray
try:
    B.offline_build(stages=stages, force=False)
except RuntimeError as e:
    assert "reserved" in str(e)
else:
    raise AssertionError("a room on the reserved cells was built")
D.dressing_blocks = real
print(B.STAGES[f"dome_{N}_inside"].__name__)
"""
    )
    assert "build" in out


def test_station_boss_pack():
    run(
        """
import re

import build_station as B
import datapack
import dome_boss as D
N = D.INDEX  # the dome's place in the ring
import domes
import game
import station_layout as L
import verify_station as V

dome = L.DOMES[D.INDEX]
place = D.room(dome)
packs = {}
for phase_2 in (False, True):
    D.PHASE_2 = phase_2
    pack = datapack.Pack(stamp="t")
    game.add_functions(pack, [D.MODULE])
    packs[phase_2] = pack
    f = pack.functions
    # the hooks the core calls, and that it calls them
    for hook in (*game.HOOKS, *game.MORE_HOOKS):
        assert f"dome/{N}/{hook}" in f, hook
    calls = lambda path, name: any(  # noqa: E731
        line.endswith(f"function station:{name}") for line in f[path]
    )
    assert calls(f"dome/{N}/entered", f"dome/{N}/enter")
    assert calls("game/tick", f"dome/{N}/tick")
    assert calls(f"dome/{N}/form", f"dome/{N}/solo")
    assert calls(f"dome/{N}/form", f"dome/{N}/duo")
    assert calls("reset/all", f"dome/{N}/reset")
    assert calls(f"dome/{N}/left", f"dome/{N}/empty")
    assert calls(f"dome/{N}/exited", f"dome/{N}/leave")
    assert calls(f"dome/{N}/respawned", f"dome/{N}/died")
    # the trophy at the win is the Pump House's, none of the module's
    assert not any("trophy" in line for line in f["run/win"])
    # the core's kit on entering, and none of the module's own
    assert calls(f"dome/{N}/entered", "kit/boss")
    mine = {n: ls for n, ls in f.items() if n.startswith(f"dome/{N}/")}
    core = {"entered", "exited", "left", "form", "respawned", "solved", "check"}
    mine = {n: ls for n, ls in mine.items() if n.split("/")[2] not in core}
    assert not any(" armor." in line for ls in mine.values() for line in ls)
    # one call of the core's solved, in ``won``
    solvers = [n for n, ls in mine.items()
               if any(f"function station:dome/{N}/solved" in line for line in ls)]
    assert solvers == [f"dome/{N}/won"], solvers
    # every function referenced exists; every block and item is known
    assert not V.function_problems(B.pack_files(pack))
    assert not V.name_problems(mine)
    # nothing aimed at the nearest player, at everyone, or at random
    for name, lines in mine.items():
        for line in lines:
            assert "@p" not in line and "@r" not in line, (name, line)
            for selector in re.findall(r"@a(?:\\[[^\\]]*\\])?", line):
                assert "tag=st.in" in selector, (name, line)
    # reset does all that empty does, and more
    quiet = [l for l in f[f"dome/{N}/empty"] if "run function" not in l
             and not l.endswith(f"dome/{N}/signs")]
    assert quiet and all(line in f[f"dome/{N}/reset"] for line in quiet)
    assert calls(f"dome/{N}/reset", f"dome/{N}/face/shut")
    assert all(calls(f"dome/{N}/reset", f"dome/{N}/main/open_{k}") for k in "abc")
    gone = f"execute as @e[tag=st.mob{N}] run function station:mob/remove"
    assert gone in f[f"dome/{N}/reset"]
    # nothing reads, sets or kills the cylinders but their clocks' torches,
    # taken out at the win and put back by the reset; nothing kills by
    # position, and nothing kills but the casing's own displays and the
    # label of the fire door's lever, by tag
    torches = D.clock_torches(place)
    assert len(torches) == 2
    machine = set()
    for m in place.cylinders:
        machine |= set(m.bed) | set(m.solid) | set(m.attached) | m.moving
    cells = {D._xyz(c) for c in machine - set(torches)}
    for name, lines in mine.items():
        for line in lines:
            assert not any(f" {xyz} " in f"{line} " for xyz in cells), (name, line)
            if line.startswith("kill"):
                assert phase_2 and ("/casing/" in name or "/fire/" in name), (
                    name, line)
                assert line in (
                    "kill @e[type=minecraft:block_display,tag=" + D.CASE_TAG + "]",
                    "kill @e[type=minecraft:text_display,tag=" + D.FIRE_TAG + "]",
                ), line
            touched = any(f" {D._xyz(c)} " in f"{line} " for c in torches)
            allowed = (f"dome/{N}/won", f"dome/{N}/reset")
            assert not touched or name in allowed, (name, line)
    for c, block in torches.items():
        assert D._setblock(c, "minecraft:air") in f[f"dome/{N}/won"]
        assert any(l.endswith(D._setblock(c, block)) for l in f[f"dome/{N}/reset"])
    # the machinery runs whether or not there is a fight
    step = f[f"dome/{N}/step"]
    at = lambda end: next(  # noqa: E731
        i for i, l in enumerate(step) if l.endswith(end)
    )
    assert at(f"function station:dome/{N}/dress") < at("run return 0")
    # the automatons are the core's: its kinds, its dress, its team
    spawn = " ".join(f[f"dome/{N}/pour/at_0"])
    for part in ("Stoker", "Riveter", "Slag Husk", "st.automaton", "station:mob/dress",
                 f"st.mob{N}", "st.home0", "IsBaby:0b"):
        assert part in spawn, part
    # winding is heard: a bell a lamp, higher each time, and a lower note as
    # each goes out; the fifth lamp is the chord of a main shut, with a
    # clank, a jet from its relief valve and a shudder through the Engine
    wind = f[f"dome/{N}/p1/wind"]
    for main in place.mains:
        k, at = main.key, D._xyz(main.lever)
        rise = [l for l in wind if "note_block.bell" in l and f" {at} " in l]
        fall = [l for l in wind if "note_block.bass" in l and f" {at} " in l]
        assert [float(l.split()[-1]) for l in rise] == list(D.RISE)
        assert [float(l.split()[-1]) for l in fall] == list(D.FALL)
        assert list(D.RISE) == sorted(D.RISE) and list(D.FALL) == sorted(D.FALL)
        assert all(f"#b7.l{k} st matches 0" in l for l in rise + fall)
        shut = f[f"dome/{N}/main/shut_{k}"]
        chord = [l for l in shut if "note_block.chime" in l]
        assert [float(l.split()[-1]) for l in chord] == list(D.CHORD)
        for part in ("block.anvil.land", "block.fire.extinguish", "minecraft:cloud",
                     "campfire_signal_smoke", "entity.iron_golem.damage", "dust_plume"):
            assert any(part in l for l in shut), part
        assert f"scoreboard players set #b7.lmp{k} st 0" in f[f"dome/{N}/main/open_{k}"]
        # an open main's steam and hiss weaken with each lamp
        dress = f[f"dome/{N}/dress"]
        mine_ = [l for l in dress if f"#b7.lmp{k} " in l]
        puffs = [l for l in mine_ if "particle minecraft:cloud" in l]
        hisses = [l for l in mine_ if "block.fire.extinguish" in l]
        assert [int(l.split()[-1]) for l in puffs] == [n for n, _ in D.STEAM]
        assert [float(l.split()[-2]) for l in hisses] == [v for _, v in D.STEAM]
        assert len(D.STEAM) == D.LAMPS
        assert list(D.STEAM) == sorted(D.STEAM, reverse=True)
    # the Engine's heart is a piston's thump, slower with each main shut
    beat = f[f"dome/{N}/beat"]
    assert any("block.piston.extend" in l for l in beat)
    dress = f[f"dome/{N}/dress"]
    periods = [int(l.split()[-1]) for l in dress if l.split()[-4:-1] ==
               ["set", "#b7.per", "st"] and "#b7.shut" in l]
    assert periods == [D.BEAT + n * D.BEAT_SLOWER for n in (1, 2, 3)]
    # a hatch on every level, each with the same smoke and the same sound;
    # the round takes the upper ones twice; a hatch of the round is used
    # only with a player on its own level in reach, and any hatch with a
    # player in reach if the whole round finds none
    assert len(place.hatches) == 6 and place.hatch_levels == (0, 0, 0, 0, 1, 2)
    assert sorted(D.HATCH_ROUND) == [0, 1, 2, 3, 4, 4, 5, 5]
    for i, hatch in enumerate(place.hatches):
        at_ = f[f"dome/{N}/pour/at_{i}"]
        assert any("large_smoke " + domes.middle(hatch, 1) in l for l in at_)
        assert any("block.iron_trapdoor.open" in l and D._xyz(hatch) in l for l in at_)
        assert f"st.home{i}" in " ".join(at_)
        assert any(f"st.home{i}" in l and domes.middle(hatch) in l
                   for l in f[f"dome/{N}/fence"])
    tries = [l for l in f[f"dome/{N}/pour/try"] if "pour/at_" in l]
    assert [int(l.rsplit("_", 1)[1]) for l in tries] == list(D.HATCH_ROUND)
    for l in tries:
        i = int(l.rsplit("_", 1)[1])
        assert f"tag={D.LEVEL_TAG}{place.hatch_levels[i]}," in l
        assert f"distance=..{D.NEAR}" in l
    one = f[f"dome/{N}/pour/one"]
    assert sum(l.endswith("pour/try") for l in one) == len(D.HATCH_ROUND)
    assert one.index(f"function station:dome/{N}/pour/levels") < min(
        i for i, l in enumerate(one) if l.endswith("pour/try"))
    late = [l for l in one if "pour/at_" in l]
    assert len(late) == 6 and not any(D.LEVEL_TAG in l for l in late)
    assert all("#b7.cast st matches 0" in l for l in late)
    assert len(f[f"dome/{N}/pour/levels"]) == 2 * len(D.LEVELS)
    # the ending: after the win the Engine winds down on a falling whine,
    # and a title says the station is saved and where home is
    end = f[f"dome/{N}/end/step"]
    whine = [float(l.split()[-1]) for l in end if "didgeridoo" in l]
    assert len(whine) == D.WHINE and whine == sorted(whine, reverse=True)
    assert whine[-1] >= 0.49  # (a pitch under a half is played as a half)
    saved = " ".join(f[f"dome/{N}/end/title"])
    assert "THE STATION IS SAVED" in saved and "Pump House" in saved
    assert D.exit_name(dome) + " airlock" in saved
    assert any(l.endswith(f"function station:dome/{N}/end/step") for l in dress)
    waves = [l for l in end if "lights/wave_" in l]
    assert len(waves) == (D.WAVE if phase_2 else 0)
    assert D.end_steps(dome) == D.end_title_at() + len(place.way_out)
    assert D.end_title_at() == D.WAVE_AT + (D.WAVE if phase_2 else 0) > D.WHINE

off, on = packs[False].functions, packs[True].functions
# phase 2 is in the pack only with the switch on
extra = sorted(set(on) - set(off))
parts = ("breach/", "master/", "p3", "p4", "lights/", "casing/", "music/", "fire/")
assert extra
assert all(n.startswith(tuple(f"dome/{N}/" + p for p in parts)) for n in extra)
assert off[f"dome/{N}/all_shut"] == [f"function station:dome/{N}/won"]
# with it on, the third main does not start the breach: the fire door's
# lever comes up, and only a pull of it does
shut3 = on[f"dome/{N}/all_shut"]
assert not any("breach/start" in l for l in shut3)
assert shut3[0] == (
    "execute unless score #b7.fire st matches 1 run function "
    f"station:dome/{N}/fire/rise"
)
lever = place.fire_post.input
assert shut3[1] == (
    f"execute if score #b7.fire st matches 1 if block {D._xyz(lever)} "
    f"minecraft:lever[powered=true] run function station:dome/{N}/fire/pulled"
)
assert "actionbar" in shut3[2] and D.FIRE_HINT in shut3[2]
assert [l for l in on[f"dome/{N}/fire/pulled"] if "function" in l] == [
    f"function station:dome/{N}/fire/gone", f"function station:dome/{N}/breach/start"]
callers = [n for n, ls in on.items() if any(l.endswith("breach/start") for l in ls)]
assert callers == [f"dome/{N}/fire/pulled"], callers
rise = on[f"dome/{N}/fire/rise"]
post = place.fire_post
put = [l for l in rise if l.startswith("setblock") and not l.endswith("minecraft:air")]
assert [l.split(" ", 4)[4].partition("[")[0] for l in put] == [
    "minecraft:gold_block", "minecraft:lever", "minecraft:bamboo_sign"]
sign = next(l for l in put if "sign" in l)
assert all(text in sign for text in D.FIRE_SIGN)
assert any(D.FIRE_HINT in l for l in rise) and any("title" in l for l in rise)
assert any("particle minecraft:cloud" in l for l in rise)
assert any("block.anvil.land" in l for l in rise)
assert any(f"st.mob{N}" in l and "mob/remove" in l for l in rise)
gone = on[f"dome/{N}/fire/gone"]
cleared = [l.split(" ")[1:4] for l in gone if l.startswith("setblock")]
assert {tuple(map(int, c)) for c in cleared} == post.cells
# (what hangs on the post goes before the post, so that nothing drops)
assert cleared[:2] == [D._xyz(c).split() for c in post.attached]
assert any(l.startswith("kill") and D.FIRE_TAG in l for l in gone)
assert f"function station:dome/{N}/fire/gone" in on[f"dome/{N}/reset"]
# no automaton is cast while it stands
assert (f"execute unless score #b7.fire st matches 1 run function "
        f"station:dome/{N}/pour") in on[f"dome/{N}/p1"]
# the lever faces the way in, on the centre line before the firebox: its
# player looks along the frame's forward at the doors
fr = place.frame
assert post.input == fr.at(D.FIRE_POST_F - 1, 0, 1)
assert place.fire_stand == fr.at(D.FIRE_POST_F - 2, 0, 1)
assert f"facing={fr.facing(-1, 0)}" in post.attached[post.input]
assert D.FIRE_POST_F < min(f_ for f_, _, _ in D.PLATE_LANDS) - 1
for name, lines in off.items():
    if name.startswith(f"dome/{N}/"):
        text = " ".join(lines)
        assert "ravager" not in text and "minecraft:generic" not in text, name
        assert "block_display,tag=" + D.CASE_TAG not in text and D.MUSIC not in text
# the pair: summoned here with the core's rules, on the automatons' team,
# and not swept by the core as automatons are
summon = D.master_summon(place.spot)
assert summon in on[f"dome/{N}/master/out"]
assert summon.count('Team:"st.automaton"') == 2 and summon.count("station:empty") == 2
assert summon.count("PersistenceRequired:1b") == 2
assert "st.mob" not in summon and len(summon.encode()) < B.MAX_COMMAND
# the Master: a mob that draws armour, in the whole brass suit trimmed with
# copper, a golden axe in hand, bigger than life, his name over him; he
# drops none of it, and is no baby and calls no others
assert D.RIDER_MOB == "minecraft:husk" and not D.rider_is_raider()
assert 'Passengers:[{id:"minecraft:husk",Tags:["st.b7.boss","st.b7.rider"]' in summon
for slot, item in D.MASTER_KIT.items():
    assert slot + ':{id:"' + item + '",count:1,components:{"minecraft:trim":' in summon
assert sorted(D.MASTER_KIT) == ["chest", "feet", "head", "legs"]
assert all(item.startswith("minecraft:golden_") for item in D.MASTER_KIT.values())
assert summon.count('material:"minecraft:copper",pattern:"minecraft:silence"') == 4
assert 'mainhand:{id:"minecraft:golden_axe",count:1}' in summon
assert "drop_chances:{head:0f,chest:0f,legs:0f,feet:0f,mainhand:0f}" in summon
assert '{id:"minecraft:scale",base:1.25d}' in summon and D.MASTER_SCALE > 1
assert 'CustomName:{text:"The Master",color:"gold",bold:true}' in summon
assert "CustomNameVisible:1b" in summon and "IsBaby:0b" in summon
assert '{id:"minecraft:spawn_reinforcements",base:0d}' in summon
assert summon.count("{") == summon.count("}") and summon.count("[") == summon.count("]")
# a ravager fights by itself only under a raider: the pack adds the husk to
# the game's tag, replacing nothing; with the switch off it adds no tag
import json
tag = "data/minecraft/tags/entity_type/raiders.json"
files = {flag: packs[flag].files() for flag in packs}
assert json.loads(files[True][tag]) == {"replace": False, "values": ["minecraft:husk"]}
assert not [path for path in files[False] if "/tags/entity_type/" in path]
assert not V.function_problems(files[True])
# the other rider, the pair the rig proved: a vindicator, a raider already
D.RIDER_MOB = "minecraft:vindicator"
assert D.rider_is_raider()
other = datapack.Pack(stamp="t")
game.add_functions(other, [D.MODULE])
assert tag not in other.files()
assert 'Passengers:[{id:"minecraft:vindicator",Tags:[' in D.master_summon(place.spot)
assert "IsBaby" not in D.master_summon(place.spot)
assert D.master_summon(place.spot) in other.functions[f"dome/{N}/master/out"]
D.RIDER_MOB = "minecraft:husk"
# the transition is plain: when the mains shut the floor's lanterns dim, the
# players are darkened, the Master's bar comes up empty, a title, a sound
start = on[f"dome/{N}/breach/start"]
assert f"function station:dome/{N}/lights/dim" in start
assert f"function station:dome/{N}/bar/show" in start
assert f"bossbar set station:d{N} value 0" in start
players = f"@a[tag=st.in,scores={{st.dome={N}}}]"
assert f"effect give {players} minecraft:darkness {D.DARK} 0 true" in start
assert sum(l.startswith(f"title {players}") for l in start) == 3
assert sum(l.startswith("playsound") for l in start) >= 2
out = on[f"dome/{N}/master/out"]
assert any("THE MASTER" in l for l in out) and any("ravager.roar" in l for l in out)
assert any(l.startswith(f"execute store result bossbar station:d{N} value")
           for l in on[f"dome/{N}/breach/step"])
# the Engine splits open: at the breach the casing's displays take the
# doors' place; three knocks, each harder (the halves start, the plates are
# pushed out, the fire flares, steam and sparks at the seams) and each let
# back; then the blow (a boom that is only sound and particles), the plates
# thrown, and the halves swung out a tick at a time to where they stand open
put = on[f"dome/{N}/casing/put"]
assert put[0].startswith("kill") and put[1:26] == D.casing_summons(dome, opened=False)
assert f"function station:dome/{N}/face/open" in put
assert f"function station:dome/{N}/casing/put" in start
opened = on[f"dome/{N}/casing/open"]
assert opened[1:26] == D.casing_summons(dome, opened=True)
assert any(l.startswith("fill") and l.endswith(D.HOT) for l in opened)
tick = on[f"dome/{N}/breach/tick"]
assert any(l.endswith(f"function station:dome/{N}/breach/tick") and
           "#b7.phase st matches 2 " in l for l in on[f"dome/{N}/tick"])
halves = D.leaves(dome)
for i, (at, degrees) in enumerate(zip(D.KNOCKS, D.BULGE)):
    assert f"execute if score #b7.an st matches {at} run function " \
        f"station:dome/{N}/breach/knock_{i}" in tick
    assert f"execute if score #b7.an st matches {at + 3} run function " \
        f"station:dome/{N}/breach/settle" in tick
    knock = on[f"dome/{N}/breach/knock_{i}"]
    for leaf in halves:
        assert any(leaf.tag in l and l.endswith(f"tp @s ~ ~ ~ {leaf.swing * degrees} 0")
                   for l in knock)
    for part in ("minecraft:cloud", "campfire_signal_smoke", "minecraft:lava",
                 "small_flame", "minecraft:flame", "attack_iron_door"):
        assert any(part in l for l in knock), part
assert list(D.BULGE) == sorted(D.BULGE)
blow = on[f"dome/{N}/breach/blow"]
for part in ("entity.generic.explode", "entity.warden.sonic_boom", "explosion_emitter"):
    assert any(part in l for l in blow), part
for name in ("breach/blow", "breach/tick", "breach/land", "casing/put", "casing/open"):
    for line in on[f"dome/{N}/{name}"]:
        assert "damage" not in line and "summon minecraft:tnt" not in line, line
        assert "creeper" not in line and "fireball" not in line, line
turned = {leaf.tag: 0 for leaf in halves}
for line in tick:
    for leaf in halves:
        if leaf.tag in line:
            span = re.search(r"matches (\\d+)\\.\\.(\\d+)", line)
            lo, hi = int(span.group(1)), int(span.group(2))
            assert D.BLOW < lo <= hi <= D.BLOW + D.SWING_TICKS
            turned[leaf.tag] += (hi - lo + 1) * int(line.split()[-2].lstrip("~"))
assert turned == {leaf.tag: leaf.swing * D.OPEN for leaf in halves}
# all in valid sound ids of the game (read from the 26.3 client)
SOUNDS = {
    "block.anvil.land", "block.beacon.deactivate", "block.bell.use",
    "block.copper_bulb.turn_on", "block.fire.extinguish", "block.iron_door.close",
    "block.iron_door.open", "block.iron_trapdoor.open", "block.lava.extinguish",
    "block.note_block.bass", "block.note_block.bell", "block.note_block.chime",
    "block.note_block.didgeridoo", "block.piston.extend", "entity.generic.explode",
    "entity.iron_golem.damage", "entity.iron_golem.step", "entity.ravager.roar",
    "entity.warden.heartbeat", "entity.warden.sonic_boom", "entity.wither.spawn",
    "entity.zombie.attack_iron_door", "music.dragon", "ui.toast.challenge_complete",
}
PARTICLES = {"cloud", "campfire_signal_smoke", "campfire_cosy_smoke", "lava", "flame",
             "small_flame", "large_smoke", "smoke", "explosion_emitter", "dust_plume",
             "poof"}
for name, lines in on.items():
    if name.startswith(f"dome/{N}/"):
        for line in lines:
            played = r"(?:playsound|stopsound \\S+ \\w+) minecraft:(\\S+)"
            for sound in re.findall(played, line):
                assert sound in SOUNDS, (name, sound)
            for particle in re.findall(r"particle minecraft:(\\w+)", line):
                assert particle in PARTICLES, (name, particle)
# his music: begun as he comes out, to each player in the dome where they
# stand, again when it has run out, and to one who comes in or dies; stopped
# at the win, when the dome empties, on leaving and by the reset
mine = on[f"dome/{N}/music/mine"]
assert mine == [
    f"stopsound @s record {D.MUSIC}", f"playsound {D.MUSIC} record @s ~ ~ ~ 1"]
assert any(l.endswith(f"at @s run function station:dome/{N}/music/mine")
           and players in l for l in on[f"dome/{N}/music/play"])
assert any(l.endswith(f"function station:dome/{N}/music/play") for l in out)
assert any(str(D.MUSIC_STEPS) in l and l.endswith("music/play")
           for l in on[f"dome/{N}/p3"])
for name in ("won", "reset", "p3/abandon"):
    assert f"function station:dome/{N}/music/stop" in on[f"dome/{N}/{name}"], name
assert f"stopsound @s record {D.MUSIC}" in on[f"dome/{N}/leave"]
for name in ("enter", "died"):
    assert any(l.endswith("music/mine") and "#b7.phase st matches 3" in l
               for l in on[f"dome/{N}/{name}"]), name
# (the core runs ``died`` with no position: it plays at the player)
assert any(l.endswith(f"at @s run function station:dome/{N}/music/mine")
           for l in on[f"dome/{N}/died"])
# the lanterns: the core's own in this dome's floor, none that touches the
# room's redstone; dimmed to a copper bulb, back at the win and the reset
lights = D.floor_lights(dome)
floor = domes.light_cells(dome)[0]
assert set(lights) <= floor and len(lights) >= len(floor) - 4 and len(lights) > 60
blocks = D.room_blocks(dome)
live = set(blocks.moving)
for main in place.mains:
    live |= main.post.cells
for x, y, z in lights:
    assert (x, y, z) not in blocks.everything()
    assert not any(abs(x - a) <= 1 and abs(y - b) <= 1 and abs(z - c) <= 1
                   for a, b, c in live), (x, y, z)
assert on[f"dome/{N}/lights/dim"] == [D._setblock(c, D.DIM) for c in lights]
assert on[f"dome/{N}/lights/full"] == [
    D._setblock(c, "minecraft:sea_lantern") for c in lights]
# (at the win they come back in the ending's wave, a sector a step)
assert f"function station:dome/{N}/lights/full" in on[f"dome/{N}/reset"]
assert not any("lights/" in line for line in on[f"dome/{N}/won"])
for name in (f"dome/{N}/won", f"dome/{N}/reset", f"dome/{N}/end/step"):
    assert not any("lights/" in line for line in off[name]), name
wave = D.light_wave(dome)
for k, sector in enumerate(wave):
    lines = on[f"dome/{N}/lights/wave_{k}"]
    lit = [D._setblock(c, "minecraft:sea_lantern") for c in sector]
    assert lines[:len(sector)] == lit
    assert f"execute if score #b7.fin st matches {D.WAVE_AT + k} run function " \
        f"station:dome/{N}/lights/wave_{k}" in on[f"dome/{N}/end/step"]
# the fire at the back of the firebox: dull as built and after the reset,
# alight from the blow, out at the win
assert any(l.startswith("fill") and l.endswith(D.COOL) for l in on[f"dome/{N}/reset"])
assert any(l.startswith("fill") and l.endswith(D.COOL) for l in on[f"dome/{N}/won"])
assert f"function station:dome/{N}/casing/gone" in on[f"dome/{N}/reset"]
# nobody stands where he comes out: the porch and the firebox are cleared
# at every step of the breach and as he is summoned
clear = f"function station:dome/{N}/breach/clear"
assert clear in on[f"dome/{N}/breach/start"] and clear in on[f"dome/{N}/breach/step"]
assert out.index(clear) < out.index(summon)
# the dead respawn in the antechamber: the core's respawn point for this
# dome is its entrance spot, which is in the pavilion, where no mob stays
x, y, z, _ = domes.entrance(dome)
assert any(l.startswith(f"spawnpoint @s {x} {y} {z}") for l in on[f"dome/{N}/entered"])
for box in (place.pavilion, place.fence):
    assert all(min(a, b) <= v <= max(a, b) for v, a, b in zip((x, y, z), *box))
assert any(D.RAVAGER in l and "run tp @s" in l for l in on[f"dome/{N}/fence"])
assert f"function station:dome/{N}/fence" in on[f"dome/{N}/p3"]
# no outlasting him from the pavilion: with nobody in the arena he cannot
# be hurt, and then he mends
p3 = " ".join(on[f"dome/{N}/p3"])
assert "minecraft:resistance 2 4 true" in p3 and "minecraft:regeneration 2 2" in p3
# his health: by who is in the dome, then by the level (the core's dress)
assert any(str(D.TWO_PLAYERS) in l and f"#occ{N}" in l for l in out)
assert sum("function station:mob/dress with storage" in l for l in out) == 2
D.PHASE_2 = True
"""
    )


#: a small interpreter of the commands the Engine's functions use, over the
#: fake client's world: scores, blocks, entities with tags and places. A
#: command it does not know is an error, so nothing is passed over unseen.
SIM = r'''
import math
import re

IGNORED = ("particle", "playsound", "stopsound", "title", "tellraw", "bossbar",
           "attribute", "give", "damage", "spawnpoint", "item")


def split_selector(text):
    """a selector at the start of text, and the rest"""
    if len(text) > 2 and text[2] == "[":
        depth = 0
        for i, ch in enumerate(text):
            depth += ch in "[{"
            depth -= ch in "]}"
            if depth == 0 and i > 1:
                return text[: i + 1], text[i + 2 :]
    return text[:2], text[3:]


def in_range(value, spec):
    if ".." in spec:
        lo, hi = spec.split("..")
        return (lo == "" or value >= int(lo)) and (hi == "" or value <= int(hi))
    return value == int(spec)


def states(block):
    name, _, rest = block.partition("{")[0].partition("[")
    name = name if ":" in name else "minecraft:" + name
    return name, dict(p.split("=") for p in rest.rstrip("]").split(",") if p)


class Sim:
    def __init__(self, pack, world):
        self.f = pack.functions
        self.pack = pack
        self.world = world
        self.scores = {}
        self.storage = {}
        self.entities = []
        self.said = []
        self.called = []
        self.difficulty = 1
        self.raiders = ()  # (the script gives it the game's own)
        self.stubs = {
            "station:mob/remove": lambda me, args: self.drop(me),
            "station:mob/dress": self.dress,
        }
        for line in pack.setup_lines():
            self.command(line, None)
        for name in ("game/load", "fight/difficulty", "mob/load"):
            self.run(name)

    # -- entities
    def add(self, kind, pos, tags, **more):
        e = {"type": kind, "pos": tuple(pos), "tags": set(tags), "scores": {},
             "effects": set(), **more}
        self.entities.append(e)
        return e

    def player(self, tag, cell):
        """a stand-in in the dome, standing in a cell"""
        e = self.add("minecraft:armor_stand", (0, 0, 0), {"st.standin", "st.in", tag})
        e["scores"]["st.dome"] = D.INDEX
        self.move(e, cell)
        return e

    def drop(self, e):
        for i, other in enumerate(self.entities):
            if other is e:
                del self.entities[i]
                return

    @staticmethod
    def move(e, cell):
        e["pos"] = (cell[0] + 0.5, cell[1], cell[2] + 0.5)

    def select(self, selector, me):
        if selector == "@s":
            return [me] if me is not None else []
        kind, args = selector[:2], selector[3:-1] if len(selector) > 2 else ""
        found = list(self.entities)
        if kind == "@a":
            found = [e for e in found if e["type"] == "minecraft:player"]
        elif kind == "@s":
            found = [me]
        box, limit = {}, None
        for part in re.findall(r"(\w+)=((?:\{[^}]*\})|[^,]*)", args):
            key, value = part
            if key == "tag" and value.startswith("!"):
                found = [e for e in found if value[1:] not in e["tags"]]
            elif key == "tag":
                found = [e for e in found if value in e["tags"]]
            elif key == "type" and value.startswith("#"):
                found = [e for e in found if e["type"] in self.types(value[1:])]
            elif key == "type":
                found = [e for e in found if e["type"] == value]
            elif key == "team":
                found = [e for e in found if e.get("team") == value]
            elif key == "scores":
                for obj, spec in re.findall(r"([\w.]+)=([-\d.]+)", value):
                    found = [e for e in found
                             if obj in e["scores"] and in_range(e["scores"][obj], spec)]
            elif key == "limit":
                limit = int(value)
            elif key in ("x", "y", "z", "dx", "dy", "dz", "distance"):
                box[key] = value
            else:
                raise ValueError(f"selector argument {key} in {selector}")
        if "distance" in box:
            reach = float(box["distance"].lstrip("."))
            at = tuple(float(box[k]) for k in "xyz")
            found = [e for e in found
                     if sum((a - b) ** 2 for a, b in zip(e["pos"], at)) <= reach**2]
        elif box:
            for i, k in enumerate("xyz"):
                lo = float(box[k])
                hi = lo + float(box["d" + k]) + 1
                found = [e for e in found if lo <= e["pos"][i] < hi]
        return found[:limit]

    def types(self, tag):
        """the mobs of an entity type tag: the game's raiders, and what the
        pack adds to the tag"""
        assert tag == "minecraft:raiders", tag
        return {"minecraft:" + name for name in self.raiders} | set(
            self.pack.tags.get(("entity_type", tag), []))

    # -- scores
    def get(self, name, obj="st"):
        return self.scores.get((name, obj))

    def b7(self, name):
        return self.scores.get((f"#b7.{name}", "st"), 0)

    def put(self, name, value):
        self.scores[f"#b7.{name}", "st"] = value

    def holder(self, name, me):
        return ("@s", id(me)) if name == "@s" else name

    # -- blocks
    def is_block(self, cell, block):
        have = self.world.at(cell) or "minecraft:air"
        name, want = states(block)
        got_name, got = states(have)
        return name == got_name and all(got.get(k) == v for k, v in want.items())

    # -- functions
    def run(self, path, me=None):
        self.called.append(path)
        for line in self.f[path]:
            if self.command(line, me) == "return":
                return

    def dress(self, me, args):
        """the core's mob/dress: health scaled by the level"""
        health = int(args["health"]) * self.get("#diff.health") // 100
        me["health"] = max(1, health)
        me["tags"].discard("st.new")

    def function(self, rest, me):
        name, _, tail = rest.partition(" ")
        path = name.removeprefix("station:")
        args = {}
        if tail.startswith("with storage"):
            _, _, store, at = tail.split(" ")
            args = {k[len(at) + 1:]: v for (s, k), v in self.storage.items()
                    if s == store and k.startswith(at + ".")}
        elif tail.startswith("{"):
            args = dict(p.split(":") for p in tail.strip("{}").split(","))
        if name in self.stubs:
            return self.stubs[name](me, args)
        if path.startswith("tunnel/"):
            self.called.append(path)
            return None
        assert path in self.f, f"no function {name}"
        if any(line.startswith("$") for line in self.f[path]):
            self.called.append(path)  # a macro: only seen to be called
            self.said.append((path, args))
            return None
        return self.run(path, me)

    def execute(self, rest, me):
        store = None
        while True:
            word, _, tail = rest.partition(" ")
            if word == "run":
                result = self.command(tail, me)
                if store and isinstance(result, int):
                    store(result)
                return result
            if word in ("if", "unless"):
                kind, _, tail = tail.partition(" ")
                if kind == "score":
                    a, obj, op, tail = tail.split(" ", 3)
                    value = self.scores.get((self.holder(a, me), obj))
                    if op == "matches":
                        spec, _, tail = tail.partition(" ")
                        ok = value is not None and in_range(value, spec)
                    else:
                        b, obj2, *more = tail.split(" ", 2)
                        tail = more[0] if more else ""
                        other = self.scores.get((self.holder(b, me), obj2))
                        ok = value is not None and other is not None and {
                            "<": value < other, "<=": value <= other,
                            "=": value == other,
                            ">=": value >= other, ">": value > other}[op]
                    count = int(ok)
                elif kind == "block":
                    x, y, z, block, *more = tail.split(" ", 4)
                    tail = more[0] if more else ""
                    count = int(self.is_block((int(x), int(y), int(z)), block))
                elif kind == "entity":
                    selector, tail = split_selector(tail)
                    count = len(self.select(selector, me))
                else:
                    raise ValueError(f"execute {word} {kind}")
                if (count > 0) != (word == "if"):
                    if store and not tail:
                        store(0)
                    return None
                if not tail:  # a test that ends the command: its count
                    if store:
                        store(count)
                    return count
                rest = tail
            elif word == "store":
                what, target, tail = tail.split(" ", 2)
                assert what == "result"
                if target == "score":
                    a, obj, tail = tail.split(" ", 2)
                    key = (self.holder(a, me), obj)
                    store = lambda v, key=key: self.scores.__setitem__(key, v)
                elif target == "storage":
                    s, at, _, _, tail = tail.split(" ", 4)
                    store = lambda v, key=(s, at): self.storage.__setitem__(key, v)
                else:  # a bossbar
                    _, _, tail = tail.split(" ", 2)
                    store = lambda v: None
                rest = tail
            elif word == "as":
                selector, tail = split_selector(tail)
                for e in self.select(selector, me):
                    if any(e is other for other in self.entities):
                        self.execute(tail, e)
                return None
            elif word == "at":
                rest = tail.partition(" ")[2]
            else:
                raise ValueError(f"execute {word}: {rest}")

    def command(self, line, me):
        word, _, rest = line.partition(" ")
        if word == "execute":
            return self.execute(rest, me)
        if word == "return":
            return "return"
        if word == "function":
            return self.function(rest, me)
        if word == "scoreboard":
            parts = rest.split(" ")
            if parts[0] == "objectives":
                return None
            verb, name, obj = parts[1], self.holder(parts[2], me), parts[3]
            key = (name, obj)
            if verb == "set":
                self.scores[key] = int(parts[4])
            elif verb in ("add", "remove"):
                sign = 1 if verb == "add" else -1
                self.scores[key] = self.scores.get(key, 0) + sign * int(parts[4])
            elif verb == "get":
                return self.scores.get(key, 0)
            elif verb == "operation":
                op = parts[4]
                other = self.scores.get((self.holder(parts[5], me), parts[6]))
                assert other is not None, f"an unset score in: {line}"
                value = self.scores.get(key, 0)
                if op in ("/=", "%="):
                    assert other, f"division by zero in: {line}"
                self.scores[key] = {
                    "=": other, "+=": value + other, "-=": value - other,
                    "*=": value * other, "/=": value // other if other else 0,
                    "%=": value % other if other else 0,
                    "<": min(value, other), ">": max(value, other)}[op]
            else:
                raise ValueError(line)
            return None
        if word == "setblock":
            x, y, z, block = rest.split(" ", 3)
            self.world.setblock((int(x), int(y), int(z)), block)
            return 1
        if word == "fill":
            c = rest.split(" ")
            self.world.fill([int(v) for v in c[:3]], [int(v) for v in c[3:6]], c[6])
            return 1
        if word == "tag":
            selector, tail = split_selector(rest)
            verb, tag = tail.split(" ")
            for e in self.select(selector, me):
                (e["tags"].add if verb == "add" else e["tags"].discard)(tag)
            return None
        if word == "summon":
            kind, x, y, z, nbt = rest.split(" ", 4)
            team = re.search(r'Team:"([^"]+)"', nbt)
            first = True
            turn = re.search(r"Rotation:\[(-?[\d.]+)f", nbt)
            for tags in re.findall(r"Tags:\[([^\]]*)\]", nbt):
                rider = re.search(r'id:"([^"]+)",Tags:\[' + re.escape(tags), nbt)
                e = self.add(rider.group(1) if rider and not first else kind,
                             (float(x), float(y), float(z)),
                             set(tags.replace('"', "").split(",")),
                             team=team.group(1) if team else None, health=1, nbt=nbt,
                             yaw=float(turn.group(1)) if turn else 0.0)
                first = False
            return 1
        if word == "tp":
            selector, tail = split_selector(rest)
            parts = tail.split(" ")
            for e in self.select(selector, me):
                if "~" not in "".join(parts[:3]):
                    e["pos"] = tuple(float(v) for v in parts[:3])
                if len(parts) == 5 and parts[3].startswith("~"):  # a turn
                    e["yaw"] = e.get("yaw", 0.0) + float(parts[3][1:] or 0)
                elif len(parts) == 5:
                    e["yaw"] = float(parts[3])
            return None
        if word == "kill":
            for e in self.select(split_selector(rest)[0], me):
                self.drop(e)
            return None
        if word == "effect":
            _, tail = rest.split(" ", 1)
            selector, tail = split_selector(tail)
            for e in self.select(selector, me):
                e["effects"].add(tail.split(" ")[0])
                if tail.startswith("minecraft:regeneration"):
                    e["health"] = e.get("health", 0) + 1  # (it mends)
            return None
        if word == "data":
            if rest == "get entity @s Health":
                return int(me["health"])
            if rest.startswith("modify storage"):
                _, _, s, at, _, _, value = rest.split(" ", 6)
                self.storage[s, at] = value
            elif rest.startswith("merge block"):
                _, _, x, y, z, nbt = rest.split(" ", 5)
                self.said.append(((int(x), int(y), int(z)), nbt))
            elif rest.startswith(("modify entity", "merge entity")):
                self.said.append(("entity", rest))
            else:
                raise ValueError(line)
            return None
        if word == "difficulty":
            return self.difficulty
        if word == "team":
            return None
        if word in IGNORED:
            if word in ("tellraw", "title", "playsound", "stopsound"):
                self.said.append((word, rest))
            return None
        raise ValueError(f"a command the interpreter does not know: {line}")
'''


def state_machine(phase_2: bool, body: str) -> str:
    """a script: the room built against the fake client, its pack, the
    interpreter over them, and helpers to play it"""
    return (
        SIM
        + f"""
import build_station as B
import datapack
import dome_boss as D
N = D.INDEX  # the dome's place in the ring
import game
import station_layout as L

D.PHASE_2 = {phase_2}
dome = L.DOMES[D.INDEX]
place = D.room(dome)
a, b, c = place.mains
stages = ["site", f"dome_{{N}}", "tunnels", f"dome_{{N}}_inside"]
rec = B.offline_build(stages=stages, force=False)
pack = datapack.Pack(stamp="t")
# the Pump House's trophy at the win, as far as the live check reads it
TROPHY = game.Module(
    "trophy",
    functions=lambda p: p.function("dome/0/trophy/arm", [
        "execute store result storage station:game trophy.level int 1 "
        "run scoreboard players get #run.level st"]),
    wins=("dome/0/trophy/arm",),
)
game.add_functions(pack, [D.MODULE, TROPHY])
sim = Sim(pack, rec.world)
sim.raiders = D.RAIDERS
LIT = (D.BULB + "[lit=true]", D.GREEN_BULB + "[lit=true]")


def ticks(n=1):
    for _ in range(n):
        # (the core's count of who is in the dome)
        sim.scores[f"#occ{{N}}", "st"] = len(sim.select("@e[tag=st.standin]", None))
        sim.run(f"dome/{{N}}/tick")


def steps(n=1):
    ticks(n * D.STEP)


def heard(sound, since=0):
    # the ``playsound`` lines of a sound since a place in what was said
    return [v for k, v in sim.said[since:] if k == "playsound" and sound in v]


def throw(main, on=True):
    sim.world.setblock(main.lever, main.lever_on if on else main.lever_off)


def lamps(cells):
    return sum(any(sim.is_block(x, kind) for kind in LIT) for x in cells)


def mobs():
    return [e for e in sim.entities if f"st.mob{{N}}" in e["tags"]]


def enter(tag, cell, first=1):
    sim.scores["#first", "st"] = first
    e = sim.player(tag, cell)
    sim.run(f"dome/{{N}}/enter", e)
    return e


def leave_all():
    for e in [e for e in sim.entities if "st.standin" in e["tags"]]:
        sim.run(f"dome/{{N}}/leave", e)
        sim.entities.remove(e)
    sim.entities[:] = [e for e in sim.entities if f"st.mob{{N}}" not in e["tags"]]
    sim.run(f"dome/{{N}}/empty")


def as_built(what):
    blocks = D.room_blocks(dome)
    for cell, block in blocks.everything().items():
        if cell in blocks.moving or cell == place.lectern:
            continue
        assert sim.world.at(cell).partition("{{")[0] == block.partition("{{")[0], (
            what, cell, block, sim.world.at(cell))
    for cell in blocks.clear:
        assert sim.is_block(cell, "minecraft:air"), (what, cell)
    for name in ("phase", "shut", "ga", "gb", "gc", "la", "lb", "lc", "live", "out"):
        assert sim.b7(name) == 0, (what, name, sim.b7(name))
    assert not mobs() and not sim.select("@e[tag=" + D.BOSS + "]", None), what
    assert not sim.select("@e[tag=" + D.CASE_TAG + "]", None), what
    assert sim.is_block(place.fire[0], D.COOL) and sim.is_block(place.fire[1], D.COOL)
    for name in ("fin", "open", "mus", "an", "fire"):
        assert sim.b7(name) == 0, (what, name, sim.b7(name))
    # no fire door's lever: its post, lever, sign and label are not there
    assert all(sim.is_block(x, "minecraft:air") for x in place.fire_post.cells), what
    assert not sim.select("@e[tag=" + D.FIRE_TAG + "]", None), what


entrance = D.domes.entrance(dome)[:3]
sim.scores[f"#d{{N}}", "st"] = 1
sim.run(f"dome/{{N}}/reset")
as_built("reset")
"""
        + body
    )


SOLO = """
# ---- in at the entrance: set up with the level's values, in the pavilion
p = enter("p1", entrance)
steps(2)
assert sim.b7("live") == 1 and sim.b7("phase") == 0
assert (sim.b7("na"), sim.b7("form")) == (0, 1)
assert {n: sim.b7(n) for n in D.scaled(5)} == D.scaled(5)
# in the arena: counted, and nothing happens until a lever is thrown
sim.move(p, place.back)
steps(8)
assert (sim.b7("na"), sim.b7("phase"), len(mobs())) == (1, 0, 0)
# on Peaceful a lever does nothing and is put back
sim.difficulty = 0
sim.run("fight/difficulty")
throw(a)
steps(1)
assert sim.b7("phase") == 0 and sim.is_block(a.lever, a.lever_off)
assert any("Peaceful" in str(text) for _, text in sim.said)
sim.difficulty = 1
sim.run("fight/difficulty")
# a lever with nobody on its deck wakes the Engine and winds nothing
throw(a)
steps(3)
assert sim.b7("phase") == 1 and sim.b7("ga") == 0
# the Engine's heart beats every second while no main is shut
since = len(sim.said)
steps(4 * D.BEAT)
assert len(heard("block.piston.extend", since)) == 4
# on the deck it winds: a lamp every 3 s at level 5, each with a bell's
# note, the second higher than the first
at = D._xyz(a.lever)
notes = lambda kind: [  # noqa: E731
    float(v.split()[-1]) for v in heard("note_block." + kind) if at in v]
bells = lambda: notes("bell")  # noqa: E731
sim.move(p, a.stand)
steps(5)
assert bells() == []
steps(1)
assert sim.b7("ga") == D.LAMP and lamps(a.gauge) == 1 and bells() == [D.RISE[0]]
steps(6)
assert sim.b7("ga") == 2 * D.LAMP and lamps(a.gauge) == 2
assert bells() == list(D.RISE[:2]) and sim.b7("lmpa") == 2
# its telltales blink while it winds; the others' stay lit
seen = set()
for _ in range(4):
    steps(1)
    seen.add(lamps(a.telltales))
    assert lamps(b.telltales) == 4 and lamps(c.telltales) == 4
assert seen == {0, 4}
# off the deck it runs down a lamp every 2 s; back on, up from where it is
sim.put("ga", 3 * D.LAMP)
steps(1)  # (the third lamp's note)
sim.put("ga", 3 * D.LAMP)
sim.move(p, place.back)
basses = lambda: notes("bass")  # noqa: E731
assert basses() == []
steps(4)
assert sim.b7("ga") == 2 * D.LAMP and lamps(a.gauge) == 2
# a lamp going out is heard too: a lower note (two lamps left)
assert basses() == [D.FALL[2]]
sim.move(p, a.stand)
steps(1)
assert sim.b7("ga") == 2 * D.LAMP + D.WIND
# the lever put back: down again, never under nothing
throw(a, False)
steps(40)
assert sim.b7("ga") == 0 and lamps(a.gauge) == 0 and sim.b7("la") == 0
assert basses()[-1] == D.FALL[0] and basses() == sorted(basses(), reverse=True)
# held to the fifth lamp it is shut for good: four more bells, rising, and
# then the chord, the clank and the Engine's shudder
since = len(sim.said)
throw(a)
steps(D.FULL // D.WIND)
assert (sim.b7("la"), sim.b7("shut"), sim.b7("ga")) == (1, 1, D.FULL)
rung = [float(v.split()[-1]) for v in heard("note_block.bell", since) if at in v]
assert rung == [*D.RISE, D.CHORD[0]]
assert len(heard("note_block.chime", since)) == len(D.CHORD)
assert heard("block.anvil.land", since) and heard("entity.iron_golem.damage", since)
# and its heart beats slower: every two and a half seconds
steps(D.BEAT + D.BEAT_SLOWER)
since = len(sim.said)
steps(2 * (D.BEAT + D.BEAT_SLOWER))
assert len(heard("block.piston.extend", since)) == 2
assert sim.is_block(a.lever, "minecraft:air")
assert all(sim.is_block(x, D.GREEN_BULB + "[lit=true]") for x in a.gauge)
assert lamps(a.telltales) == 0 and lamps(b.telltales) == 4
assert any(cell == a.sign and "SHUT" in nbt for cell, nbt in sim.said)
assert sim.get(f"#d{N}") == 1
steps(4)
assert sim.b7("ga") == D.FULL  # a shut main does not drain

# ---- the automatons: one at a time, up to the cap, and no further
sim.move(p, place.back)
limit = D.cap(5, 1, 1)
steps(60)
assert len(mobs()) == limit == sim.b7("cap"), (len(mobs()), limit)
assert all(e["team"] == "st.automaton" and "st.new" not in e["tags"] for e in mobs())
assert all(e["health"] >= 20 for e in mobs())
# they come from more than one hatch, each with a player in reach, and all
# from the hatches of the level the player is on: the floor's four
homes = lambda: {int(t[-1]) for e in mobs() for t in e["tags"]  # noqa: E731
                 if t.startswith("st.home")}
assert len(homes()) >= 2 and homes() <= {0, 1, 2, 3}
# one that gets into the pavilion is put back at its hatch
mob = mobs()[0]
sim.move(mob, entrance)
steps(1)
home = int(next(t for t in mob["tags"] if t.startswith("st.home"))[-1])
assert mob["pos"][0] == place.hatches[home][0] + 0.5
# one lost: another after the gap
sim.entities.remove(mob)
steps(D.GAP[1] + 1)
assert len(mobs()) == limit
# with nobody in the arena none comes
for e in mobs():
    sim.entities.remove(e)
sim.move(p, entrance)
steps(30)
assert not mobs() and sim.b7("na") == 0
# Riveters are few, and Slag Husks come once two mains are shut
sim.move(p, b.stand)
throw(b)
steps(D.FULL // D.WIND + 1)
assert (sim.b7("lb"), sim.b7("shut")) == (1, 2)
steps(80)
assert len(mobs()) == D.cap(5, 1, 2)
kinds = [next(t for t in e["tags"] if t.startswith("st.k.")) for e in mobs()]
assert kinds.count("st.k.riveter") <= D.RIVETERS[1] and "st.k.husk" in kinds


# ---- a hatch on each level: automatons are cast on the level a player is on
def cast(n=40):
    # the automatons cast afresh in so many steps: the hatches they came by
    sim.entities[:] = [e for e in sim.entities if f"st.mob{N}" not in e["tags"]]
    steps(n)
    assert mobs()
    return homes()


fr = place.frame
assert cast() == {4}  # on main B's deck: the gallery's hatch
sim.move(p, c.stand)
assert cast() == {5}  # on main C's platform: the high level's
sim.move(p, place.back)
assert cast() == {0, 1, 2, 3}  # on the floor: the plinth's four, in turn
# on the gallery but out of reach of its hatch: any hatch in reach of them
far = fr.at(-10, 22, D.GALLERY_H + 1)
assert math.dist(far, place.hatches[4]) > D.NEAR > math.dist(far, place.hatches[1])
sim.move(p, far)
assert cast() and homes() <= {0, 1, 2, 3}
# two players on two levels: each has automatons cast on their own
sim.move(p, place.back)
other = sim.player("p9", b.stand)
assert cast(60) == {0, 1, 2, 3, 4}
sim.entities.remove(other)
steps(game.SOLO_AFTER + 2)
assert sim.b7("form") == 1
"""

END_PHASE_1 = (
    SOLO
    + """
# ---- the third main is the win: the one call of the core's solved
sim.move(p, c.stand)
throw(c)
steps(D.FULL // D.WIND - 1)
assert sim.b7("phase") == 1 and sim.get(f"#d{N}") == 1
steps(2)
assert sim.b7("phase") == 5 and sim.get(f"#d{N}") == 2 and sim.get("#run") == 2
assert sim.called.count(f"dome/{N}/won") == 1 and f"tunnel/{N}/ready" in sim.called
assert not mobs()
# the win arms the Pump House's trophy dispenser
assert sim.called.count("dome/0/trophy/arm") == 1
# the Engine stops: eyes out; then the ending: it winds down on a falling
# whine, and only then the title and the lamps of the way out, in a run
assert lamps(place.eyes) == 0 and lamps(place.way_out) == 0
assert not any(k == "title" and "SAVED" in v for k, v in sim.said)
while sim.b7("fin") < D.WHINE:
    steps(1)
whine = [float(v.split()[-1]) for v in heard("didgeridoo")]
assert len(whine) == D.WHINE and whine == sorted(whine, reverse=True)
assert lamps(place.way_out) == 0
assert not any(k == "title" and "SAVED" in v for k, v in sim.said)
steps(D.end_title_at() - D.WHINE)
assert any(k == "title" and "THE STATION IS SAVED" in v for k, v in sim.said)
assert any(k == "title" and "Pump House" in v for k, v in sim.said)
assert lamps(place.way_out) == 1
steps(3)
assert lamps(place.way_out) == 4
steps(len(place.way_out))
assert lamps(place.way_out) == len(place.way_out) and sim.b7("spin") == 0
assert sim.b7("fin") == D.end_steps(dome)
# nothing more happens, and nothing solves it twice
steps(20)
assert sim.called.count(f"dome/{N}/won") == 1 and not mobs()
# a second entry into the solved room changes nothing, and says nothing again
leave_all()
said = len(sim.said)
p = enter("p1", entrance)
steps(4)
assert sim.b7("phase") == 5 and lamps(place.way_out) == len(place.way_out)
assert not [k for k, _ in sim.said[said:] if k in ("title", "playsound")]

# ---- reset: everything as built
sim.run(f"dome/{N}/reset")
as_built("reset after the win")
"""
)

LEAVING = """
# ---- leaving costs the gauge being wound, and no more
p = enter("p1", entrance)
sim.move(p, a.stand)
throw(a)
steps(D.FULL // D.WIND + 2)
assert sim.b7("la") == 1
sim.move(p, b.stand)
throw(b)
steps(10)
assert 0 < sim.b7("gb") < D.FULL and mobs()
leave_all()
assert (sim.b7("phase"), sim.b7("la"), sim.b7("shut")) == (0, 1, 1)
assert sim.b7("gb") == 0 and lamps(b.gauge) == 0 and lamps(a.gauge) == D.LAMPS
assert sim.is_block(b.lever, b.lever_off) and sim.is_block(a.lever, "minecraft:air")
# back in: not set up anew, the shut main still shut, and it can be finished
sim.put("rate", 77)
p = enter("p1", entrance)
steps(2)
assert sim.b7("rate") == 77 and sim.b7("la") == 1 and sim.b7("phase") == 0
sim.put("rate", D.WIND)
# an untouched room is set up anew by the first to come in, and only by them
leave_all()
sim.run(f"dome/{N}/reset")
sim.put("rate", 77)
p = enter("p1", entrance)
assert sim.b7("rate") == D.WIND
sim.put("rate", 77)
q = enter("p2", entrance, first=0)
assert sim.b7("rate") == 77
sim.put("rate", D.WIND)
sim.entities.remove(q)

# ---- two players: the form follows who is in the arena, not the dome
q = sim.player("p2", entrance)
sim.run(f"dome/{N}/duo")  # the core's hook: two in the dome
steps(2)
assert (sim.b7("na"), sim.b7("form")) == (0, 1)
# one in the arena, the partner idle in the pavilion: A winds alone
sim.move(p, a.stand)
throw(a)
steps(4)
first = sim.b7("ga")
assert first > 0 and sim.b7("form") == 1
# the partner walks out while A is being wound: the change waits
sim.move(q, place.back)
steps(3)
assert (sim.b7("na"), sim.b7("want"), sim.b7("form")) == (2, 2, 1)
assert sim.b7("ga") > first
# the safe point: nobody winding A or B
sim.move(p, place.back)
steps(2)
assert sim.b7("form") == 2 and sim.b7("pair") == 1
assert any(cell == a.sign and "together" in nbt for cell, nbt in sim.said)
# A ready alone: neither winds nor drains, and its amber lamp blinks
sim.move(p, a.stand)
steps(2)
held = sim.b7("ga")
seen = set()
for _ in range(6):
    steps(1)
    seen.add(sim.is_block(a.amber, D.AMBER))
assert seen == {True, False} and sim.b7("ga") == held and sim.b7("amb") == 1
assert sim.b7("gb") == 0
# both ready: they climb in step, and the amber lamp is dark
sim.move(q, b.stand)
throw(b)
sim.put("gb", held)
steps(4)
assert sim.b7("ga") == sim.b7("gb") == held + 4 * D.WIND and sim.b7("amb") == 0
assert not sim.is_block(a.amber, D.AMBER)
# they shut together; then the cap is the two-player one
steps(D.FULL // D.WIND)
assert (sim.b7("la"), sim.b7("lb"), sim.b7("shut")) == (1, 1, 2)
steps(1)
assert sim.b7("cap") == D.cap(5, 2, 2)
# C winds for one
sim.move(p, c.stand)
throw(c)
steps(4)
assert sim.b7("gc") == 4 * D.WIND

# ---- one of A and B shut solo, then a second player: the other winds alone
leave_all()
sim.run(f"dome/{N}/reset")
p = enter("p1", entrance)
sim.move(p, a.stand)
throw(a)
steps(D.FULL // D.WIND + 2)
q = sim.player("p2", place.back)
sim.move(p, b.stand)
steps(3)
assert sim.b7("form") == 2 and sim.b7("pair") == 0
throw(b)
steps(4)
assert sim.b7("gb") >= 3 * D.WIND

# ---- one leaves in the middle: solo 3 s after, and the one left goes on
leave_all()
sim.run(f"dome/{N}/reset")
p = enter("p1", entrance)
q = sim.player("p2", b.stand)
sim.move(p, a.stand)
steps(2)
assert sim.b7("form") == 2
throw(a)
throw(b)
steps(6)
part = sim.b7("ga")
assert part == sim.b7("gb") > 0
sim.run(f"dome/{N}/leave", q)
sim.entities.remove(q)
steps(D.SOLO_STEPS - 2)
assert sim.b7("form") == 2 and sim.b7("ga") == part  # held, not lost
steps(4)
assert sim.b7("form") == 1 and sim.b7("ga") > part and sim.b7("gb") < part
# a partner who dies is out of the arena (the core calls ``died`` at the
# entrance, in the pavilion)
p["tags"].add(D.ARENA)
sim.run(f"dome/{N}/died", p)
assert D.ARENA not in p["tags"]

# ---- reset from a scrambled state
steps(30)
for cell in place.door_columns[0]:
    sim.world.setblock(cell, "minecraft:air")
sim.world.setblock(place.eyes[0], D.BULB + "[lit=false]")
sim.world.setblock(place.lectern, "minecraft:lectern[has_book=false]")
steps(1)
assert sim.is_block(place.lectern, "minecraft:lectern[has_book=true]")
assert mobs() and sim.b7("ga") > 0
sim.run(f"dome/{N}/reset")
as_built("reset from a scrambled state")
"""


def test_station_boss_phase_1():
    run(state_machine(False, END_PHASE_1))


def test_station_boss_leaving_and_forms():
    run(state_machine(False, LEAVING))
    # the same with the switch on: phase 2 changes nothing of phase 1
    run(state_machine(True, LEAVING))


def test_station_boss_phase_2():
    run(
        state_machine(
            True,
            SOLO
            + """
boss = "@e[tag=" + D.BOSS + "]"
pair = lambda: sim.select(boss, None)  # noqa: E731
gone = lambda: [all(sim.is_block(x, "minecraft:air") for x in col)  # noqa: E731
                for col in place.door_columns]
case = lambda: sim.select("@e[tag=" + D.CASE_TAG + "]", None)  # noqa: E731
halves, loose = D.leaves(dome), D.plates(dome)
cased = sum(len(leaf.parts) for leaf in halves) + len(loose)
yaws = lambda leaf: {e["yaw"] for e in case() if leaf.tag in e["tags"]}  # noqa: E731
plate = lambda q: next(e for e in case() if q.tag in e["tags"])  # noqa: E731
hot = lambda: sim.is_block(place.fire[0], D.HOT)  # noqa: E731

# ---- the third main does not start the breach: the fire door's lever comes
# up before the Engine, with a title and a hint, and the automatons fall
post = place.fire_post
lever_on = D.fittings.lever(place.frame.facing(-1, 0), on=True)
label = lambda: sim.select("@e[tag=" + D.FIRE_TAG + "]", None)  # noqa: E731
up = lambda: [sim.is_block(x, block.partition("{")[0])  # noqa: E731
              for x, block in {**post.solid, **post.attached}.items()]
breached = lambda: f"dome/{N}/breach/start" in sim.called  # noqa: E731
waiting = lambda: (sim.b7("phase"), sim.b7("fire"), sim.b7("shut"))  # noqa: E731
sim.move(p, min(post.solid))  # (one who stands where the post comes up)
q = sim.player("p2", c.stand)
throw(c)
assert mobs() and not any(up())
since = len(sim.said)
steps(D.FULL // D.WIND + 1)
assert waiting() == (1, 1, 3) and sim.get(f"#d{N}") == 1 and not mobs()
assert f"dome/{N}/won" not in sim.called and not breached()
assert all(up()) and len(label()) == 1 and len(up()) == 3
assert p["pos"] == (place.fire_stand[0] + 0.5, place.fire_stand[1],
                    place.fire_stand[2] + 0.5)
said = sim.said[since:]
assert any(k == "title" and "FIRE DOOR lever" in v for k, v in said)
assert any(k == "tellraw" and D.FIRE_HINT in v for k, v in said)
assert any(k == "title" and "actionbar" in v and D.FIRE_HINT in v for k, v in said)
assert not any(k == "title" and "THE MAINS ARE SHUT" in v for k, v in sim.said)
# nothing of the breach yet: the doors are blocks, the lanterns bright, no bar
assert gone() == [False] * 3 and not case() and sim.b7("open") == 0
assert not any(sim.is_block(x, D.DIM) for x in D.floor_lights(dome))
assert not sim.get(f"#bar{N}")
# while it stands no automaton is cast, however long; the Engine's heart
# beats its slowest; and it waits for as long as it takes
steps(4 * D.GAP[1] + D.FIRST)
assert not mobs() and waiting() == (1, 1, 3) and not breached()
assert sim.b7("per") == D.BEAT + 3 * D.BEAT_SLOWER
# a player who dies meanwhile changes nothing
sim.move(q, entrance)
sim.run(f"dome/{N}/died", q)
steps(game.SOLO_AFTER + 2)
assert waiting() == (1, 1, 3) and all(up()) and sim.b7("form") == 1
# the dome emptied: the lever stays up, unthrown (one thrown as the last
# player went starts nothing), and the mains stay shut
sim.world.setblock(post.input, lever_on)
leave_all()
assert waiting() == (1, 1, 3) and all(up()) and len(label()) == 1 and not breached()
assert sim.is_block(post.input, "minecraft:lever[powered=false]")
assert [lamps(m.gauge) for m in place.mains] == [5, 5, 5]
# back in: told what to do, nothing set up anew, and it still waits
since = len(sim.said)
p = enter("p1", entrance, first=1)
told = [v for k, v in sim.said[since:] if k == "tellraw"]
assert len(told) == 1 and D.FIRE_HINT in told[0] and told[0].startswith("@s ")
q = enter("p2", entrance, first=0)
steps(3)
assert waiting() == (1, 1, 3) and sim.b7("rate") == D.WIND and not mobs()
sim.move(q, c.stand)
# the lever pulled (by either of them): post, lever, sign and label go at
# once, and the breach starts: no win yet
sim.move(p, place.porch[0])
steps(2)
assert waiting() == (1, 1, 3)
sim.world.setblock(post.input, lever_on)
steps(1)
assert sim.b7("phase") == 2 and sim.get(f"#d{N}") == 1 and not mobs()
assert sim.called.count(f"dome/{N}/breach/start") == 1
assert sim.b7("fire") == 0 and not label()
assert all(sim.is_block(x, "minecraft:air") for x in post.cells)
assert f"dome/{N}/won" not in sim.called
# one standing in the porch is put back from the doors
assert p["pos"][0] == place.back[0] + 0.5
# it cannot be missed: the floor's lanterns dim, the Master's bar comes up
# empty and fills, a title
lights = D.floor_lights(dome)
dim = lambda: sum(sim.is_block(x, D.DIM) for x in lights)  # noqa: E731
assert dim() == len(lights) > 60 and sim.get(f"#bar{N}") == 1
assert any(k == "title" and "THE MAINS ARE SHUT" in v for k, v in sim.said)
# the Engine's casing: the doors' blocks are gone, and its displays stand
# shut in their place, the fire behind them dull
assert gone() == [True] * 3 and len(case()) == cased and sim.b7("open") == 1
assert all(yaws(leaf) == {0} for leaf in halves) and not hot()
assert all(plate(q)["pos"] == q.on for q in loose)
first = {id(e) for e in case()}
# the breach, a tick at a time: three knocks, the blow, the swing
filling, walked, seen = [], [], {}
while sim.b7("phase") == 2:
    an = sim.b7("an")
    if an == D.KNOCKS[1] + 5:  # one who walks back to the casing is put out again
        sim.move(p, place.porch[1])
        walked.append("porch")
    if an == D.BLOW + 25:  # and one who walks into the opening firebox
        sim.move(p, place.spot)
        walked.append("firebox")
    ticks(1)
    if sim.b7("tick") == 0:  # (a step was taken)
        assert p["pos"][0] == place.back[0] + 0.5
        filling.append(sim.b7("pct"))
    turn = {leaf.tag: yaws(leaf) for leaf in halves}
    seen[sim.b7("an")] = (turn, hot(), plate(loose[0])["pos"], plate(loose[0])["yaw"])
    assert len(case()) == cased
assert walked == ["porch", "firebox"]
assert filling == sorted(filling) and 0 < filling[0] < filling[-1] == 100
for at, degrees in zip(D.KNOCKS, D.BULGE):
    # a knock: the halves start from their seats, outwards, the plates are
    # pushed out and the fire flares; three ticks on all is let back
    for an in (at, at + 2):
        turn, fire, where, _ = seen[an]
        assert turn == {leaf.tag: {leaf.swing * degrees} for leaf in halves}
        assert fire and where == D.plate_bulged(dome, loose[0], degrees) != loose[0].on
    for an in (at - 1, at + 3):
        turn, fire, where, _ = seen[an]
        assert turn == {leaf.tag: {0} for leaf in halves}
        assert not fire and where == loose[0].on
# the blow: the fire alight for good, the plates up and out, then down to
# lie on the floor, turned as they fell
assert seen[D.BLOW][1:3] == (True, loose[0].apex)
assert seen[D.BLOW][0][halves[0].tag] == {0}
assert seen[D.BLOW + D.PLATE_GLIDE - 1][2] == loose[0].apex
assert seen[D.BLOW + D.PLATE_GLIDE][2:] == (loose[0].land, loose[0].yaw)
assert sum(1 for k, v in sim.said if k == "entity" and "merge entity" in v
           and "interpolation_duration" in v) == len(loose)
assert heard("entity.generic.explode") and heard("entity.warden.sonic_boom")
# the halves swing out, each tick further, never back, to where they stand
# open: as the Master comes out, and not before
right = halves[0]
swing = [abs(next(iter(seen[an][0][right.tag])))
         for an in range(D.BLOW, D.BLOW + D.SWING_TICKS + 1)]
assert swing[0] == 0 and swing[-1] == D.OPEN and swing == sorted(swing)
assert all(0 < b - a <= 3 for a, b in zip(swing, swing[1:]))
assert max(seen) == D.BLOW + D.SWING_TICKS == D.OUT * D.STEP
assert all(len(seen[an][0][leaf.tag]) == 1 for an in seen for leaf in halves)
assert all(yaws(leaf) == {leaf.swing * D.OPEN} for leaf in halves)
assert sim.b7("open") == 2 and hot() and {id(e) for e in case()} == first
# the pair comes out: a ravager with the Master on it, on the team
assert sim.b7("phase") == 3 and len(pair()) == 2
# and his music begins
assert sim.called.count(f"dome/{N}/music/play") == 1 and sim.b7("mus") >= 1
kinds = sorted(e["type"] for e in pair())
assert kinds == sorted(["minecraft:ravager", D.RIDER_MOB])
assert all(
    e["team"] == "st.automaton" and f"st.mob{N}" not in e["tags"] for e in pair()
)
assert any(k == "title" and "THE MASTER" in v for k, v in sim.said)
# under a rider of the game's raiders, as a ravager needs to fight by itself
assert len(sim.select("@e[tag=" + D.RIDER + ",type=#minecraft:raiders]", None)) == 1
# health for two in the dome: 170%
full = (D.RAVAGER_HP + D.MASTER_HP) * D.TWO_PLAYERS // 100
assert sim.b7("hmax") == full and sim.b7("hsum") == full
# lost inside five seconds: out again, and no win
for e in pair():
    sim.entities.remove(e)
steps(1)
assert sim.b7("phase") == 3 and len(pair()) == 2 and sim.get(f"#d{N}") == 1
# (the casing is left as it stands, and his music is not begun again)
assert {id(e) for e in case()} == first
assert sim.called.count(f"dome/{N}/music/play") == 1
steps(D.EARLY + 2)
# when it has run out it is played again; one who comes in hears it too
sim.put("mus", D.MUSIC_STEPS - 1)
steps(1)
assert sim.called.count(f"dome/{N}/music/play") == 2 and sim.b7("mus") == 1
since = len(sim.said)
late = enter("p3", entrance, first=0)
assert len(heard(D.MUSIC, since)) == 1
stops = lambda: [v for k, v in sim.said[since:] if k == "stopsound"]  # noqa: E731
assert stops() == ["@s record " + D.MUSIC]
sim.run(f"dome/{N}/leave", late)
assert stops() == ["@s record " + D.MUSIC] * 2
sim.entities.remove(late)
steps(game.SOLO_AFTER + 2)
# wounded: the bar follows
rav = sim.select("@e[tag=" + D.RAVAGER + "]", None)[0]
rav["health"] = rav["health"] // 2
steps(1)
assert 0 < sim.b7("pct") < 100
# nobody in the arena: he cannot be hurt, and after a while he mends
sim.move(p, entrance)
sim.move(q, entrance)
steps(2)
assert all("minecraft:resistance" in e["effects"] for e in pair())
assert not any("minecraft:regeneration" in e["effects"] for e in pair())
steps(D.scaled(5)["mend"])
assert all("minecraft:regeneration" in e["effects"] for e in pair())
# a mob in the pavilion is put out: the ravager, carrying its rider
sim.move(rav, entrance)
steps(1)
assert rav["pos"][0] == place.back[0] + 0.5
# the high level is no safe seat: its steam comes and goes
sim.move(q, c.stand)
seen = set()
for _ in range(D.VENT_AFTER + D.VENT_CYCLE):
    steps(1)
    seen.add((sim.b7("up") >= D.VENT_AFTER, sim.b7("vent") >= D.VENT_WARN))
assert {(True, True), (True, False), (False, False)} <= seen
sim.move(q, place.back)
steps(1)
assert sim.b7("up") == 0 and sim.b7("vent") == 0

# ---- the dome emptied in the fight: he goes, and comes out again whole
leave_all()
assert sim.b7("phase") == 4 and not pair() and gone() == [True] * 3
assert dim() == len(lights) and sim.get(f"#bar{N}") == 0  # still dim, no bar
# the casing stands open as it was, and the music is stopped
assert {id(e) for e in case()} == first and sim.b7("open") == 2 and sim.b7("mus") == 0
p = enter("p1", entrance, first=1)
steps(D.ROAR + 4)
assert sim.b7("phase") == 4 and not pair()  # in the pavilion: he waits
assert sim.b7("shut") == 3 and sim.b7("rate") == D.WIND  # and nothing is set up anew
sim.move(p, place.spot)  # (into the open firebox itself: put out of it)
steps(D.ROAR + 1)
assert sim.b7("phase") == 3 and len(pair()) == 2 and sim.get(f"#bar{N}") == 1
assert p["pos"][0] == place.back[0] + 0.5
assert {id(e) for e in case()} == first and sim.b7("mus") >= 1
solo = D.RAVAGER_HP + D.MASTER_HP
assert sim.b7("hmax") == solo == sim.b7("hsum")

# ---- the ravager dead: the Master fights on; both dead: the win
steps(D.EARLY + 1)
sim.entities.remove(sim.select("@e[tag=" + D.RAVAGER + "]", None)[0])
steps(1)
assert sim.b7("phase") == 3 and sim.b7("pct") == 100 * D.MASTER_HP // solo
# on foot, he is put out of the pavilion by himself
rider = pair()[0]
sim.move(rider, entrance)
steps(1)
assert rider["pos"][0] == place.back[0] + 0.5
sim.entities.remove(rider)
steps(1)
assert sim.b7("phase") == 5 and sim.get(f"#d{N}") == 2 and sim.get("#run") == 2
assert sim.called.count(f"dome/{N}/won") == 1 and f"tunnel/{N}/ready" in sim.called
assert sim.called.count("dome/0/trophy/arm") == 1
# the bar goes, the music stops, the fire dies; the casing stays open
assert sim.get(f"#bar{N}") == 0 and sim.b7("mus") == 0 and not hot()
assert [v for k, v in sim.said if k == "stopsound"][-1].endswith("record " + D.MUSIC)
assert {id(e) for e in case()} == first
# the ending: the Engine winds down in the dim; then the lanterns come back
# in a wave, a sector a step, from the side away from the way out round to
# it; then the title, and the lamps of the way out in a run
assert dim() == len(lights)
while sim.b7("fin") < D.WAVE_AT - 1:
    steps(1)
assert dim() == len(lights) and len(heard("didgeridoo")) == D.WHINE
back = []
for _ in range(D.WAVE):
    steps(1)
    back.append(len(lights) - dim())
assert back == sorted(set(back)) and back[-1] == len(lights) and len(back) == D.WAVE
wave = D.light_wave(dome)
assert back[0] == len(wave[0]) and back[-1] - back[-2] == len(wave[-1])
assert all(sim.is_block(x, "minecraft:sea_lantern") for x in lights)
assert not any(k == "title" and "SAVED" in v for k, v in sim.said)
steps(1)
assert any(k == "title" and "THE STATION IS SAVED" in v for k, v in sim.said)
assert lamps(place.way_out) == 1 and lamps(place.eyes) == 0
steps(len(place.way_out))
assert lamps(place.way_out) == len(place.way_out)
assert sim.b7("fin") == D.end_steps(dome)
assert sim.called.count(f"dome/{N}/won") == 1

# ---- reset: the doors shut again, the firebox empty
sim.run(f"dome/{N}/reset")
as_built("reset after the Master")

# ---- left in the dim, part way through the ending: it is finished at once
sim.put("phase", 5)
sim.put("fin", D.WAVE_AT + 1)
sim.run(f"dome/{N}/lights/dim")
leave_all()
assert dim() == 0 and lamps(place.way_out) == len(place.way_out)
assert sim.b7("out") == len(place.way_out) and sim.b7("fin") == D.end_steps(dome)
sim.run(f"dome/{N}/reset")
as_built("reset after an ending left")

# ---- emptied in the breach itself: phase 4, the doors open
leave_all()
sim.scores[f"#d{N}", "st"] = 1  # (the game's reset opens the dome again)
p2 = enter("p1", entrance)
for name in ("la", "lb"):
    sim.put(name, 1)
sim.put("shut", 2)
sim.move(p2, c.stand)
throw(c)
steps(D.FULL // D.WIND + 1)
assert waiting() == (1, 1, 3) and all(up())
sim.world.setblock(post.input, lever_on)
steps(2)
assert sim.b7("phase") == 2 and sim.b7("open") == 1 and not any(up())
assert all(yaws(leaf) == {0} for leaf in halves)
leave_all()
assert sim.b7("phase") == 4 and gone() == [True] * 3 and not pair()
# the casing is put open at once: the halves out, the plates on the floor,
# the fire alight
assert sim.b7("open") == 2 and len(case()) == cased and hot()
assert all(yaws(leaf) == {leaf.swing * D.OPEN} for leaf in halves)
assert all(plate(q)["pos"] == q.land and plate(q)["yaw"] == q.yaw for q in loose)
# and the game's reset from there: the lanterns back, the doors shut
assert dim() == len(lights)
sim.run(f"dome/{N}/reset")
assert dim() == 0
as_built("reset from the breach")

# ---- the game's reset with the lever up: nothing of it is left
leave_all()
sim.scores[f"#d{N}", "st"] = 1
p2 = enter("p1", entrance)
for name in ("la", "lb", "lc"):
    sim.put(name, 1)
sim.put("shut", 3)
sim.put("phase", 1)
sim.move(p2, place.back)
steps(1)
assert waiting() == (1, 1, 3) and all(up()) and len(label()) == 1
steps(1)
assert len(label()) == 1  # (and it comes up once)
sim.run(f"dome/{N}/reset")
assert not any(up()) and not label()
as_built("reset with the fire door's lever up")

# ---- the escort, from level 6: an automaton or two beside him
leave_all()
sim.run(f"dome/{N}/reset")
sim.scores["#level", "st"] = 8
sim.run("difficulty/apply")
p3 = enter("p1", entrance)
assert sim.b7("hp") == D.scaled(8)["hp"] >= D.ESCORT_FROM
for name in ("la", "lb", "lc"):
    sim.put(name, 1)
sim.put("shut", 3)
sim.put("phase", 2)
sim.move(p3, place.back)
steps(D.OUT + 2)
# (a breach that no ``breach/start`` began: the casing is put open as he comes)
assert sim.b7("phase") == 3 and sim.b7("esc") == 1
assert sim.b7("open") == 2 and len(case()) == cased
steps(3 * D.GAP[1])
assert len(mobs()) == 1
""",
        )
    )


#: the live check itself, run over the interpreter: the build's context
#: with the core's scan of who is in the dome done here in Python (the
#: core's own is a macro), tunnel 7 a stub, and the dome's shell not looked
#: at. It proves the check's own logic against the functions, not the game.
LIVE = """
import math

import domes
import game_checks
import tunnels

TUNNEL = L.TUNNELS[D.INDEX]


class Ctx:
    layout = L

    def __init__(self):
        self.pack = pack
        self.t = 0
        self.st = dict(was=0, form=0, shown=0, grace=0, gone=0)
        self.doors = {
            c: sim.world.at(c)
            for d in tunnels.ends(TUNNEL)
            for _, c in domes.door_cells(d, TUNNEL)
        }
        sim.stubs[f"station:tunnel/{N}/open"] = self.opened
        # the solve wakes the pump: its lever by the airlock, and a pull
        # of it (``game_checks.pull_pump``) opens the tunnel
        self.lever = tunnels.lever_cell(TUNNEL)
        sim.stubs[f"station:tunnel/{N}/ready"] = self.ready

    def ready(self, me, args):
        sim.scores[f"#t{N}.ready", "st"] = 1
        sim.world.setblock(self.lever, tunnels.lever_block(TUNNEL))

    def opened(self, me, args):
        sim.scores[f"#t{N}", "st"] = 2
        for cell in self.doors:
            sim.world.setblock(cell, "minecraft:air")

    def inside(self, e):
        x, y, z = dome.floor_centre
        return math.dist(e["pos"], (x + 0.5, y, z + 0.5)) <= dome.radius + 1

    def scan(self):
        st = self.st
        stands = sim.select("@e[tag=st.standin]", None)
        for e in stands:
            e["tags"].add("st.in")
            if e["scores"].get("st.dome") == N and not self.inside(e):
                e["scores"]["st.dome"] = -1
                sim.run(f"dome/{N}/leave", e)
        for e in stands:
            if self.inside(e) and e["scores"].get("st.dome") != N:
                e["scores"]["st.dome"] = N
                sim.run("difficulty/apply")
                sim.scores["#first", "st"] = 0 if st["was"] else 1
                st["was"] = 1
                sim.run(f"dome/{N}/enter", e)
        occ = sum(e["scores"].get("st.dome") == N for e in stands)
        sim.scores[f"#occ{N}", "st"] = occ
        sim.scores["#players", "st"] = len(stands)
        if occ >= 2:
            st["form"], st["grace"] = 2, 0
        if occ == 1 and st["form"] == 2:
            st["grace"] += 1
        if occ == 1 and st["form"] != 2:
            st["form"] = 1
        if st["grace"] >= game.SOLO_AFTER:
            st["form"] = 1
        if st["form"] == 1:
            st["grace"] = 0
        if occ and sim.get(f"#d{N}") == 1 and st["shown"] != st["form"]:
            st["shown"] = st["form"]
            sim.run(f"dome/{N}/solo" if st["form"] == 1 else f"dome/{N}/duo")
        if occ:
            st["gone"] = 0
        elif st["was"]:
            st["gone"] += 1
        if st["gone"] >= game.EMPTY_AFTER:
            st.update(was=0, form=0, shown=0, grace=0, gone=0)
            for e in mobs():
                sim.drop(e)
            sim.run(f"dome/{N}/empty")
        if occ:
            st["was"] = 1
        sim.scores[f"#form{N}", "st"] = st["form"]

    def advance(self, ticks):
        for _ in range(ticks):
            self.t += 1
            if self.t % game.SCAN_TICKS == 0:
                self.scan()
            if sim.get(f"#occ{N}"):
                sim.run(f"dome/{N}/tick")
            self.fight()

    def fight(self):
        # the one thing of the game's own that the check waits for: a
        # ravager bites a golem set before it, if its rider is a raider
        prey = sim.select("@e[tag=" + D.PREY + "]", None)
        riders = sim.select("@e[tag=" + D.RIDER + ",type=#minecraft:raiders]", None)
        if prey and riders and sim.select("@e[tag=" + D.RAVAGER + "]", None):
            prey[0]["health"] -= 1

    def cmd(self, command, expect=None):
        asked = re.match(
            r"attribute (.+) minecraft:(scale|attack_damage) (get|base [gs]et)(.*)",
            command,
        )
        if asked:
            who, name, verb, value = asked.groups()
            for e in sim.select(who, None):
                if verb == "base set":
                    e[name] = float(value)
                elif name == "scale":
                    size = re.search(r'minecraft:scale",base:([\\d.]+)d', e["nbt"])
                    return "Value of attribute Scale is " + size.group(1)
                else:
                    return "Base value of attribute is " + str(e.get(name, 5.0))
            return ""
        if command.startswith("summon minecraft:iron_golem"):
            sim.command(command, None)
            health = re.search(r"Health:(\\d+)f", command)
            sim.entities[-1]["health"] = int(health.group(1))
            return ""
        if command.startswith("attribute") and "follow_range base get" in command:
            return "Base value of attribute Follow Range for Zombie is 48.0"
        if command.startswith("data remove storage"):
            _, _, _, store, at = command.split(" ")
            for key in [k for k in sim.storage if k[0] == store and
                        k[1].startswith(at + ".")]:
                del sim.storage[key]
            return ""
        if command.startswith("bossbar get"):
            shown = sim.get(f"#bar{N}") == 1
            return "is currently visible" if shown else "is currently hidden"
        health = re.match(r"data modify entity (.+) Health set value (\\d+)f", command)
        if health:
            for e in sim.select(health.group(1), None):
                e["health"] = int(health.group(2))
            return ""
        sim.command(command, None)
        return ""

    def setblock(self, cell, block):
        sim.world.setblock(cell, block)
        if cell == self.lever and block == tunnels.lever_block(TUNNEL, True):
            sim.scores[f"#t{N}.ready", "st"] = 0
            self.opened(None, None)

    def function(self, path, args=""):
        if path == f"tunnel/{N}/reset":
            sim.scores[f"#t{N}", "st"] = 0
            for cell, block in self.doors.items():
                sim.world.setblock(cell, block)
        else:
            sim.function(pack.id(path), None)

    def score(self, name, objective="st"):
        return sim.scores.get((name, objective))

    def set_score(self, name, value, objective="st"):
        sim.scores[name, objective] = value

    def is_block(self, cell, block):
        return sim.is_block(cell, block)

    def count(self, selector):
        return len(sim.select(selector, None))

    def data(self, what):
        kind, rest = what.split(" ", 1)
        if kind == "storage":
            store, at = rest.split(" ")
            return " ".join(f"{k[len(at) + 1:]}:{v}" for (s, k), v in
                            sim.storage.items() if s == store and
                            k.startswith(at + "."))
        if kind == "block":
            x, y, z, path = rest.split(" ")
            cell = (int(x), int(y), int(z))
            merged = [nbt for c, nbt in sim.said if c == cell]
            if merged and path == "front_text":
                return merged[-1]
            return sim.world.at(cell)
        selector, path = split_selector(rest)
        found = sim.select(selector, None)
        if not found or path == "interaction":
            return ""
        e = found[0]
        effects = " ".join(e["effects"])
        nbt = e.get("nbt", "")
        name = re.search(r"CustomName:(\\{[^}]*\\})", nbt)
        return {
            "Rotation[0]": str(e.get("yaw", 0.0)) + "f",
            "Pos[1]": str(e["pos"][1]) + "d",
            "Passengers": nbt,
            "active_effects": effects,
            "equipment": nbt[nbt.find("equipment:"):],
            "CustomName": name.group(1) if name else "",
            "CustomNameVisible": "1b" if "CustomNameVisible:1b" in nbt else "",
            "Health": str(e.get("health", 0)) + "f",
        }[path]


for command in rec.commands:  # what the build summoned
    if command.startswith("summon"):
        sim.command(command, None)
domes.check_shell = lambda ctx, dome, empty=True: []
tunnels.counts = lambda ctx, tunnel: tunnels.expected(tunnel, 0)
sim.scores[f"#t{N}", "st"] = 0
sim.scores["#run", "st"] = 1
sim.scores["#solved", "st"] = 6
ctx = Ctx()
try:  # a run in progress: refused (game_checks.no_run)
    D.check(ctx)
    raise AssertionError("the check ran over a run in progress")
except SystemExit:
    pass
ctx.run_checked = True  # as FORCE=1: what it puts back is tried too
if NO_TAG:  # the pack's addition to the game's raiders did not take
    pack.tags.clear()
problems = D.check(ctx)
# (nothing moves the cylinders' pistons here: real redstone does)
real = [p for p in problems if "cylinders stood still" not in p]
if NO_TAG:  # the check says so, and that the ravager did not bite
    assert len(real) == 2 and "raiders" in real[0] and "did not bite" in real[1], real
else:
    assert not real, real
assert len(problems) - len(real) == 2, problems
# it leaves the game as it found it, and no stand-in behind
assert sim.get("#run") == 1 and sim.get("#solved") == 6 and sim.get(f"#d{N}") == 1
assert not sim.select("@e[tag=st.standin]", None) and not mobs()
print(ctx.t)
"""


def test_station_boss_live_check_logic():
    for phase_2 in (False, True):
        out = run(state_machine(phase_2, "NO_TAG = False\n" + LIVE))
        assert int(out.split()[-1]) > 3000  # ticks: it was worked, not skipped
    # a rider the game does not let a ravager fight under: the check finds it
    run(state_machine(True, "NO_TAG = True\n" + LIVE))
