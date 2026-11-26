"""
The Clockwork Maze (examples/station/dome_maze.py) with no server: its
plan against the dome, the gate table and the two searches for soft locks,
its build against the example's fake client, and its datapack functions,
read line by line and driven by a small interpreter of the scoreboard.
As tests/test_station_example.py does, each test runs in a Python of its
own, in the example's folder.
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


def test_maze_plan():
    run(
        """
import build_station as B
import dome_maze as D
import domes
import game
import rooms
import station_layout as L
import tunnels
import verify_station as V

dome = L.DOMES[D.INDEX]
assert B.STAGES["dome_6_inside"] is D.build and V.LIVE["clockwork_maze"] is D.check
assert "clockwork_maze" not in V.todos()
assert "stub_maze" not in {m.name for m in B.modules()}

# the plan in every shape it takes: inside the dome, off the reserved
# cells, its inputs listed, on gold and signed, nothing decorative an input
assert not D.room_problems(dome), D.room_problems(dome)[:5]
fr = D.frame(dome)
x, y, z, _ = domes.entrance(dome)
assert fr.at(-(dome.radius - domes.ENTRANCE_OFFSET), 0, 1) == (x, y, z)
for form, keys, free in D.SHAPES:
    b = D.room_blocks(dome, form, keys, free)
    used = set(b.above()) | b.clear
    assert used <= domes.dome_cells(dome).interior
    assert not used & tunnels.reserved_cells(dome)
    assert set(b.floor) <= domes.dome_cells(dome).floor
    listed = D.inputs(dome, form, keys)
    assert {c for c, block in b.above().items() if rooms.is_input(block)} == listed
assert len(D.inputs(dome)) == 2 and len(D.inputs(dome, 2, True)) == 5
dress = D.dressing_blocks(dome).everything()
assert len(dress) > 500
assert not any(rooms.is_input(block) for block in dress.values())
b = D.room_blocks(dome)
assert max(c[1] for c in b.solid) - dome.floor_y >= 20  # three decks and a crown
# the outgoing door's window is behind the tower, and the dome says so
assert D.INDEX in domes.ALLOWED and not rooms.window_problems(dome, b.above())

# the gate table: 39 gates, each in the lattice, no cell used twice
assert len(D.GATES) == 39 and not D.table_problems()
kinds = [g.kind for g in D.GATES]
special = (D.DOOR, D.FK, D.RAM, D.GREAT, D.LIFT)
assert [kinds.count(k) for k in special] == [1, 1, 1, 1, 3]
real = D.GATES
bad = D.Gate(1, D.GREEN, (-8, -2), (-10, -2), (-10, 1))  # its slot in a leaf
D.GATES = (*real[:1], bad, *real[2:])
assert D.table_problems()
D.GATES = real
# every gate as built is open: leaves parked, doorway clear, slot not powered
for g in D.GATES:
    part = {k: [fr.at(*p) for p in v] for k, v in D.gate_places(g).items()}
    assert all(b.solid[c] == D.LEAF for c in part["leaf"])
    assert all(c in b.clear and c not in b.solid for c in part["door"])
    assert all(b.solid[c] == D.SLOT_OPEN for c in part["slot"])
    assert all("sticky_piston[extended=false" in b.solid[c] for c in part["piston"])
# an open slot is not a way through the wall
assert D.SLOT_OPEN != D.AIR

# no soft lock, alone or as a pair, at one gate an hour; the searches use
# the table the build uses, and find a fault put into it
assert not D.solo_problems() and not D.pair_problems()
assert len(D.pair_steps()) == 3 * len(D.nodes()) ** 2
route = D.solo_route()
assert route[-1][0] == "crown" and len(route) == 27, len(route)
steps = D.solo_steps()
state = ("out", D.GREEN)
for to in route:
    assert to in steps[state], (state, to)
    state = to
# (the held gates: a pair outside needs one on the plate; one inside frees it)
assert D.moves("out", 0, "out")[(1, 0, 2)] is True
assert D.moves("out", 0, (1, 0, 2))[(1, 0, 2)] is False
assert (2, 2, 0) not in D.moves(D.F_CELL, D.GREEN, "out")  # held, nobody on the plate
assert D.moves(D.F_CELL, D.IRON, D.F_CELL)[(2, 2, 0)] is True
assert (2, 2, 0) in D.moves(D.F_CELL, D.GREEN, (2, 1, 1))  # one beyond: the clock
assert (2, 2, 0) not in D.moves(D.F_CELL, D.IRON, (2, 1, 1))
# (a timed floor that is not out is a fall to the cell below)
t2 = D.FLOORS[0]
assert D.strike(t2.node, D.GREEN) == t2.below and D.strike(t2.node, D.IRON) == t2.node
# (no ladders: a lift takes whoever stands on it, up at Green, down at Gold;
# its lower cell is got into in Gold and out of in any hour)
a = D.LIFT_LIST[0]
assert D.strike(a.low, D.GREEN) == a.high and D.strike(a.high, D.GOLD) == a.low
assert D.strike(a.low, D.GOLD) == a.low and D.strike("crown", D.GOLD) == "crown"
assert a.low in D.moves((1, 4, 1), D.GOLD) and a.low not in D.moves((1, 4, 1), D.IRON)
assert (1, 4, 1) in D.moves(a.low, D.IRON)
assert D.LIFT_LIST[2].low in D.moves("crown", D.IRON)
assert not any("ladder" in block for block in b.everything().values())
assert not any(rule == "ladder" for _, _, rule in D.edges())
# (an arch has no door and takes no time: lift A's top, F and on through
# the held gate in one hour)
assert (2, 2, 0) in D.moves(a.high, D.GREEN) and D.room(a.high) == {a.high, D.F_CELL}

# the puzzle is one: no room has two gates of an hour, most have a choice,
# and on each deck of gates the walker who takes whatever opens first is
# far behind the route that plans, there are dead ends, and the best route
# lets gates go by that open first
assert not D.puzzle_problems(), D.puzzle_problems()
numbers = D.puzzle()
assert numbers[1]["best"] == [9, 8, 10] and numbers[1]["naive"] == [24, 17, 25]
assert numbers[2]["best"] == [12, 14, 13] and numbers[2]["naive"] == [21, 56, 22]
assert numbers[1]["dead"] == [(1, 1, 0), (1, 1, 3), (1, 1, 4)]
assert numbers[2]["dead"] == [(2, 0, 1), (2, 0, 3), (2, 3, 1)]
assert [len(n["ahead"]) for n in numbers.values()] == [3, 2]
assert all(cost >= 3 for n in numbers.values() for _, _, cost in n["ahead"])
# (the timed floor is a short cut one way and a fall the other: the walker
# with no plan who starts deck 2 in Iron goes through it to deck 1)
assert D.naive_step((2, 2, 0), D.GOLD)[0][0] == 2
assert D.land((2, 1, 0), D.GREEN) == (1, 1, 0)
# (and the searches find a deck made easy: every gate of deck 1 Green)
D.GATES = tuple(
    D.Gate(g.deck, D.GREEN, g.door, g.piston, g.slot)
    if g.deck == 1 and g.kind in (D.IRON, D.GOLD) else g
    for g in real
)
D.edges.cache_clear()
assert any("two gates of one hour" in p for p in D.puzzle_problems())
D.GATES = real
D.edges.cache_clear()
D.GATES = tuple(g for g in real if g.kind != D.LIFT)
D.edges.cache_clear()
assert D.solo_problems()
D.GATES = real
D.edges.cache_clear()

# the walks and the sight lines pass, and find a wall round the entrance
assert not D.walk_problems(dome) and not D.sight_problems(dome)
# nobody gets into a machine cell or anywhere with no way back: the lifts
# ridden, falls that drift, a timed floor going; and the search finds the
# review's trap when the bars over the wall beside T2 and the lid of the
# machine cell below are taken out
assert not D.trap_problems(dome), D.trap_problems(dome)
seen, _ = D.traps(dome)
assert all(cell in seen for cell in D.walks(dome).values())
whole = D.room_blocks
def opened(dome, *args, **kw):
    b = whole(dome, *args, **kw)
    gone = [(-6, r, 4) for r in (-9, -8, -7)]
    for at in gone + [(f, r, 4) for f in (-9, -8, -7) for r in (-9, -8, -7)]:
        b.solid.pop(fr.at(*at))
    return b
D.room_blocks = opened
found = D.trap_problems(dome)
assert any("machine cells reachable" in p for p in found), found
assert any("no way back" in p for p in found), found
D.room_blocks = whole
wanted = {"the Regulator", "the Walk", "the way out", "cell (3, 3, 1)"}
assert wanted <= set(D.walks(dome))
assert not D.gantry_problems(dome) and not D.plan_problems(dome)
plain = D.dressing_blocks
def walled(dome):
    d = plain(dome)
    for r in range(-dome.radius, dome.radius + 1):
        for h in (1, 2, 3):
            if fr.at(-16, r, h) in domes.dome_cells(dome).interior:
                d.solid.setdefault(fr.at(-16, r, h), D.COPPER)
    return d
D.dressing_blocks = walled
assert any("the Regulator" in p for p in D.walk_problems(dome))
assert any("the way out" in p for p in D.walk_problems(dome))
assert any("the dial" in p for p in D.sight_problems(dome))
assert D.room_problems(dome)
D.dressing_blocks = plain

# the values of a level: an hour is 6 s at level 5
one, five, seven, ten = (D.scaled(level) for level in (1, 5, 7, 10))
assert five == {"qlen": 30, "early": 0} and 4 * five["qlen"] == 6 * 20
assert one == {"qlen": 42, "early": 0} and ten == {"qlen": 15, "early": 2}
assert seven["early"] == 1
assert all(D.scaled(lv)["qlen"] >= D.scaled(lv + 1)["qlen"] for lv in range(1, 10))
# the clock made plain: a light of the hour on every post, the dial's rim
# in the hours' blocks with a lamp on each, a plan of each deck with every
# gate on it in its own block, and the plaque's rule
lights = [c for c, block in b.solid.items() if block == D.HOUR_LIGHT[D.GREEN]]
assert len(lights) > 60 and not any("ochre" in v for v in b.solid.values())
lamps, disc = D.dial_places()
assert set(lamps) <= set(disc) and lamps[0] == (-11, 0, 13)
assert all(disc[f, round(r * 1.25), 9 + round((h - 9) * 1.25)] == D.HOUR_BLOCK[n // 4]
           for n, (f, r, h) in enumerate(lamps))
marks = D.plan_marks()
for deck in (1, 2, 3):
    gates = [g for g in D.GATES if g.deck == deck and g.kind not in (D.RAM, D.GREAT)]
    f, r, h = D.PLAN_AT[deck]
    on = [m for m in marks
          if m[1] and r - 1 <= m[0][1] <= r + 5 and h <= m[0][2] < h + 5]
    blocks = sorted(m[1] for m in on if m[1] != D.ARCH_MARK)
    assert blocks == sorted(D.lintel(g)[0] for g in gates), deck
    assert sum(m[1] == D.ARCH_MARK for m in on) == len(D.ARCHES[deck])
assert len({m[0] for m in marks}) == len(marks)
assert all(fr.at(*at) in b.solid for at in D.plan_blocks())
signs = " ".join(v for v in b.attached.values() if "sign" in v)
for words in ("Each gate opens", "in its hour:", "I GREEN", "II IRON", "III GOLD",
              "Plan your", "way up."):
    assert words in signs, words
# the hand: from twelve o'clock clockwise, a twelfth of a turn a quarter
assert D.hand_turn(0) == (0.0, 1.0) and abs(D.hand_turn(6)[0] - 1) < 1e-9
assert D.HAND_TAG in D.hand_summon(fr) and "block_display" in D.hand_summon(fr)

# the logbook: four pages, by Finch, and it goes over RCON in the build
assert len(D.LOG_PAGES) <= 4 and "Finch" in D.LOG_AUTHOR
assert all(len(page) <= 256 for page in D.LOG_PAGES)
assert len(D.logbook(fr).encode()) < B.MAX_COMMAND
"""
    )


def test_maze_build():
    run(
        """
import build_station as B
import dome_maze as D
import domes
import game
import station_layout as L
import tunnels

dome = L.DOMES[D.INDEX]
b = D.room_blocks(dome)
# the stage against the fake client: every block where the plan has it,
# the stub's bypass gone, the shell and the pump engine left alone, the
# same built twice
stages = ["site", B.dome_stage_name(D.INDEX), "tunnels", "dome_6_inside"]
rec = B.offline_build(stages=stages, force=False)
for cell, block in b.everything().items():
    assert rec.world.at(cell) == block, (cell, block, rec.world.at(cell))
assert all(rec.world.name_at(c) == "minecraft:air" for c in b.clear)
for cell in game.stub_post(dome).cells:
    assert rec.world.name_at(cell) == "minecraft:air", cell
engine = tunnels.engine_cells(L.TUNNELS[D.INDEX])
assert all(rec.world.name_at(c) != "minecraft:air" for c in list(engine.values())[:9])
shell = domes.dome_cells(dome).shell
assert all(rec.world.name_at(c) != "minecraft:air" for c in shell)
count = lambda start: sum(c.startswith(start) for c in rec.commands)  # noqa: E731
assert count("summon minecraft:interaction") == 1
marks = D.plan_marks()
assert count("summon minecraft:block_display") == 2 + sum(bool(m[1]) for m in marks)
words = sum(bool(m[2]) for m in marks)
assert count("summon minecraft:text_display") == 2 * len(D.GATES) + 4 + words
assert sum(bool(m[1]) for m in marks) == 44 and words == 51, (words,)
assert "function station:dome/6/reset" in rec.commands
assert all(len(c.encode()) <= B.MAX_COMMAND for c in rec.commands)
again = B.offline_build(stages=[*stages, "dome_6_inside"], force=False)
assert again.world.dump() == rec.world.dump()
# the build refuses a plan with a problem
real = D.room_problems
D.room_problems = lambda dome: ["a problem"]
try:
    B.offline_build(stages=stages, force=False)
except RuntimeError as e:
    assert "a problem" in str(e)
else:
    raise AssertionError("built a room with a problem")
D.room_problems = real
"""
    )


def test_maze_pack():
    run(
        """
import re

import build_station as B
import datapack
import dome_maze as D
import game
import station_layout as L
import verify_station as V

dome = L.DOMES[D.INDEX]
fr = D.frame(dome)
xyz = lambda place: D._xyz(fr.at(*place))  # noqa: E731


def packed():
    pack = datapack.Pack(stamp="t")
    game.add_functions(pack, [D.MODULE])
    return pack


# (the core's own functions for the dome are not the module's)
core = datapack.Pack(stamp="t")
game.add_functions(core, [])
for _ in (0,):
    pack = packed()
    F = pack.functions
    mine = {n: lines for n, lines in F.items()
            if n.startswith("dome/6/") and n not in core.functions}
    # the hooks the core calls, every function referenced there, every
    # block and item named known
    for hook in game.HOOKS:
        assert f"dome/6/{hook}" in F, hook
    assert not V.function_problems(B.pack_files(pack))
    assert not V.name_problems(mine)
    calls = lambda path, name: any(  # noqa: E731
        line.endswith(f"function station:{name}") for line in F[path]
    )
    assert calls("dome/6/entered", "dome/6/enter") and calls("game/tick", "dome/6/tick")
    assert calls("dome/6/form", "dome/6/solo") and calls("dome/6/form", "dome/6/duo")
    assert calls("reset/all", "dome/6/reset") and calls("dome/6/left", "dome/6/empty")
    solvers = [n for n, ls in mine.items()
               if any("function station:dome/6/solved" in line for line in ls)]
    assert solvers == ["dome/6/done"], solvers
    # the lifts run on the clock: up at the strike of Green, down at Gold
    assert calls("dome/6/work", "dome/6/lifts")
    assert any("la.to st 1" in line for line in F["dome/6/strike/0"])
    assert any("la.to st 0" in line for line in F["dome/6/strike/2"])
    assert not any(".to" in line for line in F["dome/6/strike/1"])
    assert any("settle" in line for line in F["dome/6/empty"])
    assert "dome/6/lift/ram/at_18" in F and "dome/6/lift/a/leave_6" in F
    # a platform glides: at rest it is blocks, on its way nine block
    # displays moved a quarter of a block a tick, its riders on seats that
    # move with them, set down at the end; no ladder anywhere
    for lift in D.LIFT_LIST:
        base = f"dome/6/lift/{lift.name}"
        for k in (0, lift.travel):
            leave, arrive = F[f"{base}/leave_{k}"], F[f"{base}/arrive_{k}"]
            cars = [line for line in leave
                    if line.startswith("summon minecraft:block_display")]
            assert len(cars) == 9 and all("teleport_duration:1" in c for c in cars)
            assert leave[0].endswith(f"{base}/air_{k}")
            assert arrive[0].endswith(f"{base}/at_{k}")
            assert any(line.endswith(f"{base}/seat") and "@e[tag=st.in," in line
                       for line in leave)
            assert any("on passengers" in line and line.endswith(f"{base}/off")
                       for line in arrive)
            assert f"kill @e[tag={lift.car}]" in arrive
            assert not any(D.COPPER in line for line in F[f"{base}/air_{k}"])
            assert sum(D.COPPER in line for line in F[f"{base}/at_{k}"]) == 1
        glide = F[f"{base}/glide"]
        assert sum(f"tp @s ~ ~{sign}0.25 ~" in line
                   for sign in ("", "-") for line in glide) == 2
        assert any("ride @s mount" in line for line in glide)
        assert any("ride @s mount" in line for line in F[f"{base}/seat"])
        assert F[f"{base}/off"][0] == "ride @s dismount"
        # going down it waits while anyone is under it, and does not leave
        # the top over anybody
        assert len(F[f"{base}/aim"]) == 3 + lift.travel - 1
        assert any("unless entity @e[tag=st.in," in line for line in F[f"{base}/move"])
    assert not any("ladder" in line for ls in mine.values() for line in ls)
    assert D.LIFT_STEP * D.LIFT_LIST[0].travel == 24  # ticks a ride
    # a lift's gate: open while its platform stands at the bottom, and for
    # anyone found inside
    assert sum("#maze.la st matches 0 if score #maze.la.m st matches 0" in line
               for line in F["dome/6/held"]) == 1
    # the clock made plain. The bell: at each ear, a stroke for Green, two
    # for Iron, three for Gold, each hour at its own pitch
    for h in range(3):
        strike = F[f"dome/6/strike/{h}"]
        bell = [line for line in strike if "block.bell.use" in line]
        assert len(bell) == 1 and " at @s run playsound " in bell[0]
        assert bell[0].endswith(f"@s ~ ~ ~ 1 {D.BELL_PITCH[h]}")
        assert f"scoreboard players set #maze.bells st {h}" in strike
        assert calls(f"dome/6/strike/{h}", f"dome/6/lights/{h}")
        # every post's light to the hour's colour: three decks, from each
        # of the other two colours
        lights = F[f"dome/6/lights/{h}"]
        assert len(lights) == 6 and all(
            line.startswith("fill ") and f"{D.HOUR_LIGHT[h]} replace minecraft:" in line
            for line in lights)
    assert len(set(D.BELL_PITCH)) == 3
    # the warning through an hour's last quarter: a clank at each ear and
    # the lights to the colour of the hour to come and back
    warn = F["dome/6/warn"]
    assert sum("playsound" in line and " at @s run " in line for line in warn) == 2
    assert sum(line.endswith(f"dome/6/lights/{n}")
               for n in range(3) for line in warn) == 6
    assert any("#maze.last st matches 1" in line and line.endswith("dome/6/warn")
               for line in F["dome/6/clock"])
    # the hand: made anew if it is gone, a quarter's sweep to the next lamp
    go = F["dome/6/hand/go"]
    assert go[0].startswith(f"execute unless entity @e[tag={D.HAND_TAG}]")
    assert "interpolation_duration int 1 run scoreboard players get #maze.qlen" in go[1]
    assert len(go) == 14 and all("start_interpolation:0" in line for line in go[2:])
    assert D.hand(fr, 12) in go[13] and D.hand(fr, 1) in go[2]
    assert F["dome/6/hand/put"] == [f"kill @e[tag={D.HAND_TAG}]", D.hand_summon(fr)]
    assert calls("dome/6/park", "dome/6/hand/put")
    assert calls("dome/6/quarter", "dome/6/hand/go")
    assert calls("dome/6/arm", "dome/6/hand/go")
    assert calls("dome/6/park", "dome/6/lights/0")

    # every execute line is well formed: known clauses of the right length
    def clauses(line, where):
        t = line.split(" ")
        i = 1
        while i < len(t) and t[i] != "run":
            if t[i] in ("if", "unless"):
                kind = t[i + 1]
                if kind == "score":
                    step = 6 if t[i + 4] == "matches" else 7
                    fine = step == 6 or t[i + 4] in ("<", ">=", "=")
                    assert t[i + 3] == "st" and fine, (where, line)
                else:
                    step = {"block": 6, "entity": 3, "data": 5}[kind]
                    if kind == "block":
                        assert all(re.fullmatch(r"-?\\d+", n) for n in t[i + 2:i + 5])
                        assert re.match(r"#?minecraft:[a-z_]+", t[i + 5]), (where, line)
                i += step
            elif t[i] in ("as", "at", "on"):
                i += 2
            elif t[i] == "positioned":
                i += 4
            elif t[i] == "store" and t[i + 2] == "entity":
                assert t[i + 4:i + 7] == ["interpolation_duration", "int", "1"], line
                i += 7
            elif t[i] == "store":
                assert t[i + 1:i + 3] == ["result", "score"], (where, line)
                i += 5
            else:
                raise AssertionError(f"{where}: {t[i]!r} in {line}")
        assert i == len(t) or t[i + 1] in (
            "function", "scoreboard", "setblock", "fill", "return", "playsound",
            "tellraw", "tp", "effect", "particle", "ride", "data",
        ), (where, line)

    for name, lines in mine.items():
        for line in lines:
            if line.startswith("execute "):
                clauses(line, name)

    # the rig's rules for the piston gates. Nothing ever writes a piston:
    writes = [
        line for lines in mine.values() for line in lines
        if re.search(r"(setblock|fill) .*piston", line.split(" run ")[-1])
    ]
    assert not writes, writes[:2]
    # shut is the slot filled, never with someone in the doorway; open is
    # the slot cleared; an hour's function is the whole table
    hour_gates = [g for g in D.GATES if g.kind in (0, 1, 2)]
    for h in range(3):
        lines = F[f"dome/6/gates/{h}"]
        assert len(lines) == len(hour_gates) == 32
        for g, line in zip(hour_gates, lines):
            a, b = (xyz(p) for p in D.gate_places(g)["slot"])
            door = fr.at(*D.gate_places(g)["door"][0])
            if g.kind == h:
                assert line == (f"execute if block {a} {D.POWER} "
                                f"run fill {a} {b} {D.SLOT_OPEN}"), line
            else:
                assert line.endswith(f"run fill {a} {b} {D.POWER}")
                assert f"unless block {a} {D.POWER} unless entity @e[tag=st.in," in line
                assert f"x={door[0]},y={door[1]},z={door[2]},dx=0,dy=1,dz=0]" in line
    assert len(F["dome/6/gates/free"]) == len(D.GATES)
    assert all(D.SLOT_OPEN in line for line in F["dome/6/gates/free"])
    # the mend reads each piston and writes only leaves and doorways
    mend = F["dome/6/mend"]
    assert len(mend) == 3 * 2 * len(D.GATES)
    cells = {xyz(p) for g in D.GATES for k in ("leaf", "door")
             for p in D.gate_places(g)[k]}
    for line in mend:
        assert line.startswith("execute if block ")
        assert "sticky_piston[extended=" in line
        done = line.split(" run setblock ")[1].split(" ")
        assert " ".join(done[:3]) in cells and done[3] in (D.LEAF, D.AIR), line
    out = [line for line in mend if "extended=true" in line]
    assert len(out) == 2 * len(D.GATES) and all("piston_head" in line for line in out)
    assert calls("dome/6/work", "dome/6/mend") and calls("dome/6/mend_a", "dome/6/mend")
    # reset is all that empty is and more: both park, park clears every
    # slot and has the mend run with nobody there to tick
    assert calls("dome/6/reset", "dome/6/park")
    assert calls("dome/6/park", "dome/6/gates/free")
    assert any(line.endswith("run function station:dome/6/park")
               for line in F["dome/6/empty"])
    assert any(line.startswith("schedule function station:dome/6/mend_a")
               for line in F["dome/6/park"])
    # a held gate, and the keys, only while two are really there
    held = F["dome/6/held"]
    assert any("#maze.form st matches 2 if score #maze.in st matches 0" in line
               for line in held)
    assert any("#maze.form st matches 2 if score #maze.beyond st matches ..0" in line
               for line in held)
    assert any("#maze.form st matches 2 if score #maze.top st matches 2.." in line
               for line in F["dome/6/keys"])
    # solo and duo change the two plates and the signs and nothing else
    for hook in ("solo", "duo"):
        for line in F[f"dome/6/{hook}"]:
            assert line.split(" ")[0] in ("scoreboard", "setblock", "data", "execute",
                                          "tellraw"), line
            assert D.POWER not in line and "function" not in line
    # the decoration: no function touches a block of the Tally Engine
    machine, lamps = D.tally(fr)
    for cell in machine.cells | set(lamps):
        at = D._xyz(cell)
        assert not any(f" {at} " in line for ls in mine.values() for line in ls), at


# ---- the state machine, driven: a small interpreter of the scoreboard
# lines (blocks and entities are not there: every test of one fails)
pack = packed()
F = pack.functions
score, trace = {}, []


def matches(value, span):
    if value is None:
        return False
    lo, _, hi = span.partition("..") if ".." in span else (span, "", span)
    return (lo == "" or value >= int(lo)) and (hi == "" or value <= int(hi))


def do(line):
    t = line.split(" ")
    if t[0] == "execute":
        i = 1
        while t[i] != "run":
            if t[i] == "store":  # a count of entities: nobody
                score[t[i + 3]] = 0
                return None
            if t[i] in ("as", "at"):
                return None  # nobody to run as
            want, kind = t[i] == "if", t[i + 1]
            if kind == "score" and t[i + 4] == "matches":
                ok, step = matches(score.get(t[i + 2]), t[i + 5]), 6
            elif kind == "score":
                a, b = score.get(t[i + 2]), score.get(t[i + 5])
                ok = a is not None and b is not None and {
                    ">=": a >= b, "<": a < b, "=": a == b}[t[i + 4]]
                step = 7
            else:
                ok, step = False, {"block": 6, "entity": 3, "data": 5}[kind]
            if ok != want:
                return None
            i += step
        return do(" ".join(t[i + 1:]))
    if t[0] == "function":
        return call(t[1].split(":")[1])
    if t[0] == "return":
        return "return"
    if t[:2] == ["scoreboard", "players"]:
        op, name = t[2], t[3]
        if op == "set":
            score[name] = int(t[5])
        elif op in ("add", "remove"):
            score[name] = score.get(name, 0) + int(t[5]) * (1 if op == "add" else -1)
        elif op == "operation":
            a, b = score.get(name, 0), score.get(t[6], 0)
            score[name] = {"=": b, "+=": a + b, "-=": a - b, "*=": a * b,
                           "/=": a // b if b else a, "%=": a % b if b else a}[t[5]]
    return None


def call(name):
    trace.append(name)
    if name not in mine:
        return None  # the core's: named, not run
    for line in F[name]:
        if do(line) == "return":
            break
    return None


score.update({"#10": 10, "#100": 100, "#d6": 1, "#first": 1, "#form6": 1})
for level in (1, 5, 10):
    score["#diff.timer"] = game.scaled(level)["#diff.timer"]
    call("dome/6/scale")
    assert {n: score[f"#maze.{n}"] for n in ("qlen", "early")} == D.scaled(level)
score["#diff.timer"] = 100
# the first player in: the room armed, the clock at the strike of Green
call("dome/6/enter")
assert "dome/6/arm" in trace and "dome/6/park" in trace and "dome/6/strike/0" in trace
get = lambda n: score.get(f"#maze.{n}")  # noqa: E731
assert (get("live"), get("form"), get("free"), get("q"), get("hour")) == (1, 1, 0, 0, 0)
assert get("la") == 6 and get("lram") == 18 and get("qlen") == 30
# a full turn of the clock, a tick at a time
struck, seen = [], set()
for tick in range(1, 12 * 30 + 1):
    trace.clear()
    call("dome/6/tick")
    assert trace[:3] == ["dome/6/tick", "dome/6/work", "dome/6/clock"]
    assert "dome/6/mend" in trace and "dome/6/held" in trace and "dome/6/keys" in trace
    assert f"dome/6/gates/{get('hour')}" in trace and "dome/6/gates/free" not in trace
    assert "dome/6/floors/e0" in trace
    assert get("q") == (tick // 30) % 12 and get("hour") == get("q") // 4
    struck += [n for n in trace if n.startswith("dome/6/strike")]
    seen |= {n for n in trace if n.startswith("dome/6/pend")}
    if tick % 30 == 0:
        assert "dome/6/dial" in trace
    assert get("last") == (get("q") % 4 == 3)
assert struck == ["dome/6/strike/1", "dome/6/strike/2", "dome/6/strike/0"]
assert seen == {"dome/6/pend/0", "dome/6/pend/1"}
# the lifts follow the strikes: down at Gold, up again at Green
assert get("la.to") == 1 and get("la") < 6
for _ in range(6 * D.LIFT_STEP + 3):
    call("dome/6/tick")
assert (get("la.to"), get("la")) == (1, 6)
for _ in range(8 * 30):
    call("dome/6/tick")
assert get("hour") == 2 and (get("la.to"), get("la"), get("lram")) == (0, 0, 18)
# the form changes: nothing but the form (nobody is up top: the lever stays)
trace.clear()
call("dome/6/duo")
call("dome/6/tick")
assert get("form") == 2 and get("keys") == 0 and "dome/6/keys/on" not in trace
score["#maze.top"] = 2  # two up top (the count is of entities: set by hand)
call("dome/6/keys")
assert get("keys") == 1 and trace[-1] == "dome/6/keys/held" and get("hold") == 0
score["#maze.top"] = 1
call("dome/6/keys")
assert get("keys") == 0
# solved: once, the room tamed and steady, the Ram on its way down
trace.clear()
call("dome/6/done")
assert trace.count("dome/6/solved") == 1 and get("free") == 1
assert get("ramwait") == D.RAM_WAIT and get("qlen") == D.scaled(1)["qlen"]
score["#d6"] = 2
trace.clear()
for _ in range(D.RAM_WAIT + 18 * D.LIFT_STEP + 6):
    call("dome/6/tick")
assert "dome/6/gates/free" in trace and "dome/6/held" not in trace
assert "dome/6/keys" not in trace and "dome/6/floors/e0" not in trace
assert (get("lram"), get("ramwait")) == (0, -1)
# everyone out of the solved room: it stays tamed; the game's reset: as built
call("dome/6/empty")
assert get("free") == 1 and get("live") == 0
call("dome/6/reset")
state = (get("free"), get("live"), get("form"), get("q"), get("lram"))
assert state == (0, 0, 1, 0, 18)
# an unsolved room emptied is parked, and the next in arms it anew
score["#d6"] = 1
call("dome/6/tick")
assert get("live") == 1
for _ in range(100):
    call("dome/6/tick")
trace.clear()
call("dome/6/empty")
assert "dome/6/park" in trace and (get("live"), get("q"), get("la")) == (0, 0, 6)
"""
    )
