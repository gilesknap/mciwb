"""
The Gearworks (examples/station/dome_gearworks.py) with no server: its
plan against the dome, its build against the example's fake client, its
datapack functions well formed, and its state machine run in a small
model of the game (``MODEL``: the scores, the blocks and the commands the
steam is made of; whatever is aimed at a player or an entity does
nothing there). As in test_station_example.py, each test runs in a Python
of its own, in the example's folder.
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


PRELUDE = """
import build_station as B
import datapack
import dome_gearworks as D
import domes
import fittings
import game
import rooms
import station_layout as L
import tunnels
import verify_station as V

dome = L.DOMES[D.INDEX]
place = D.room(dome)
fr = place.frame
every = D.lengths(dome)
blocks = D.room_blocks(dome)
short, round_ = D.line_to_pump(dome, True), D.line_to_pump(dome, False)
"""

MODEL = r"""
import re

AIR = "minecraft:air"
SOLVED = f"dome/{D.INDEX}/solved"
#: commands that only show or sound, or are aimed at players and entities
IGNORED = ("playsound", "tellraw", "particle", "title", "tag", "kill", "data",
           "give", "clear")


def parts(block):
    block = block.partition("{")[0]
    name, _, states = block.partition("[")
    return name, dict(s.split("=") for s in states.rstrip("]").split(",") if s)


class Model:
    def __init__(self, functions, world):
        self.functions = functions
        self.world = {c: b.partition("{")[0] for c, b in world.items()}
        self.scores = {}
        self.called = []

    # -- blocks
    def is_block(self, cell, pattern):
        name, states = parts(self.world.get(cell, AIR))
        want, wanted = parts(pattern)
        # (a state not given when the block was set is its default)
        return name == want and all(
            states.get(k, "false") == v for k, v in wanted.items()
        )

    def setblock(self, cell, block):
        self.world[cell] = block.partition("{")[0]
        if parts(block)[0] == AIR:
            del self.world[cell]  # (air is no block here)

    # -- running
    def run(self, path):
        self.called.append(path)
        if path == SOLVED:  # the core's: the dome marked solved, once
            assert self.scores.get(f"#d{D.INDEX}") == 1, "solved twice"
            self.scores[f"#d{D.INDEX}"] = 2
            return
        for line in self.functions[path]:
            if not line.startswith("$") and self.line(line.split(" ")) == "return":
                return

    def ticks(self, n=1):
        for _ in range(n):
            self.run(f"dome/{D.INDEX}/tick")

    def line(self, w):
        if w[0] == "execute":
            return self.execute(w[1:])
        if w[0] == "scoreboard":
            return self.scoreboard(w[2:])
        if w[0] == "setblock":
            return self.setblock(tuple(map(int, w[1:4])), w[4])
        if w[0] == "fill":
            return self.fill(w)
        if w[0] == "function":
            return self.run(w[1].partition(":")[2])
        if w[0] == "return":
            return "return"
        assert w[0] in IGNORED, w

    def scoreboard(self, w):
        get = lambda name: self.scores.get(name, 0)  # noqa: E731
        if w[0] == "set":
            self.scores[w[1]] = int(w[3])
        elif w[0] in ("add", "remove"):
            sign = 1 if w[0] == "add" else -1
            self.scores[w[1]] = get(w[1]) + sign * int(w[3])
        elif w[0] == "operation":
            a, b = get(w[1]), get(w[4])
            self.scores[w[1]] = {
                "=": b, "+=": a + b, "-=": a - b, "*=": a * b,
                "/=": a // b if b else a, "<": min(a, b), ">": max(a, b),
            }[w[3]]
        else:
            assert w[0] == "get", w

    def fill(self, w):
        lo, hi = tuple(map(int, w[1:4])), tuple(map(int, w[4:7]))
        assert w[8] == "replace" and parts(w[7])[0] == AIR, w
        for cell in [c for c, b in self.world.items() if parts(b)[0] == w[9]]:
            if all(lo[k] <= cell[k] <= hi[k] for k in range(3)):
                del self.world[cell]

    def execute(self, w):
        i, store = 0, None
        while i < len(w) and w[i] != "run":
            if w[i] in ("as", "at", "on") or w[i + 1] in ("entity", "items", "data"):
                return None  # aimed at a player or an entity: nobody here
            if w[i] == "store" and w[i + 2] == "score":
                store, i = w[i + 3], i + 5
            elif w[i] == "store":
                return None  # (into storage, for a text)
            elif w[i + 1] == "score":
                a = self.scores.get(w[i + 2])
                if w[i + 4] == "matches":
                    lo, dots, hi = w[i + 5].partition("..")
                    hi = hi if dots else lo
                    ok = a is not None and (not lo or a >= int(lo))
                    ok = ok and (not hi or a <= int(hi))
                    step = 6
                else:
                    b = self.scores.get(w[i + 5])
                    ok = a is not None and b is not None and {
                        "<": lambda: a < b, "<=": lambda: a <= b, "=": lambda: a == b,
                        ">=": lambda: a >= b, ">": lambda: a > b,
                    }[w[i + 4]]()
                    step = 7
                if ok != (w[i] == "if"):
                    return self.stored(store, 0)
                i += step
            else:
                assert w[i + 1] == "block", w
                ok = self.is_block(tuple(map(int, w[i + 2:i + 5])), w[i + 5])
                if ok != (w[i] == "if"):
                    return self.stored(store, 0)
                i += 6
        if i == len(w):  # no command: the test itself is the result
            return self.stored(store, 1)
        return self.line(w[i + 1:])

    def stored(self, store, value):
        if store:
            self.scores[store] = value


pack = datapack.Pack(stamp="t")
game.add_functions(pack, [D.MODULE])


def new_model(level=game.DEFAULT_LEVEL):
    # a room as built, the dome open, a first player in
    m = Model(pack.functions, blocks.everything())
    m.scores.update({"#10": 10, "#35": 35, "#100": 100, "#first": 1})
    m.scores.update(game.scaled(level))
    m.run(f"dome/{D.INDEX}/reset")
    m.scores[f"#d{D.INDEX}"] = 1
    m.run(f"dome/{D.INDEX}/enter")
    m.run(f"dome/{D.INDEX}/solo")
    return m


def score(m, name):
    return m.scores.get(f"#gear.{name}")


def lay(m, numbers):
    laid = {i for i in numbers if every[i].laid}
    for i in laid:
        m.setblock(every[i].cell, f"{D.PIPE}[lit=false]")
    return laid


def lit(m):
    return {
        i for i, ln in enumerate(every)
        if m.is_block(ln.cell, f"{D.PIPE if ln.laid else D.BUILT}[lit=true]")
    }


def want(m, laid, along):
    n = score(m, "n")
    return {i for i, d in D.steam(dome, laid, along).items() if d <= n}


def throw_clutch(m):
    m.setblock(place.lever, D.lever_block(fr, True))
    m.ticks(D.TURN_TICKS + 2)
    assert score(m, "gear") == 2


def solved(m):
    return m.scores[f"#d{D.INDEX}"] == 2


CREEP = D.STEP * (len(round_) + 12)
COUNT = D.STEP * D.SINK_STEPS * D.INTAKE_LAMPS + 4
"""


def test_station_gearworks_plan():
    run(
        PRELUDE
        + """
assert B.STAGES["dome_2_inside"] is D.build and V.LIVE["gearworks"] is D.check
assert "gearworks" not in V.todos()

# the room's cells: inside the dome, off the reserved cells, laid out in
# the dome's own frame
assert not D.room_problems(dome)
used = blocks.used()
assert used <= domes.dome_cells(dome).interior | domes.dome_cells(dome).floor
assert not used & tunnels.reserved_cells(dome)
assert set(blocks.floor) <= domes.dome_cells(dome).floor
assert not fittings.placement_problems(dome, used - set(blocks.floor))
x, y, z, _ = domes.entrance(dome)
assert fr.at(-(dome.radius - domes.ENTRANCE_OFFSET), 0, 1) == (x, y, z)
levels = {c[1] - dome.floor_y for c in blocks.solid}
assert max(levels) >= D.WALK_H + 3 and len(blocks.everything()) > 2000

# the main: the short way and the way round, what is laid and what is built
# in, the metals of the short way shared between two
assert len(short) == D.ROUTE == 63 and len(round_) == 77
laying = [every[i] for i in short if every[i].laid]
assert len(laying) == D.TO_LAY == 38 and D.ROUTE - D.TO_LAY == 7 + 7 + 10 + 1
by_part = [(p, sum(ln.part == p for ln in laying)) for p in dict.fromkeys(
    ln.part for ln in laying)]
assert by_part == [("chest", 4), ("ring", 12), ("back", 6), ("along", 10),
                   ("front", 6)], by_part
metals = [ln.metal for ln in laying]
assert metals.count("brass") == 21 and metals.count("copper") == 17
runs = [1]
for a, b in zip(metals, metals[1:]):
    runs = runs + [1] if a != b else runs[:-1] + [runs[-1] + 1]
assert max(runs) <= 6 and len(runs) == 7, runs  # 4 6 6 5 5 6 6
assert every[D.source(dome)].part == "chest" and every[D.sink(dome)].part == "door"
engine = set(tunnels.engine_cells(L.TUNNELS[D.INDEX]).values())
sx, sy, sz = every[D.sink(dome)].cell
assert any((sx + dx, sy, sz + dz) in engine for dx, dz in domes.COMPASS)
# every length to lay has a block of the track behind it and air in it; a
# built-in one is a bulb the wrench cannot break
for ln in every:
    if ln.laid:
        at = blocks.floor if ln.on[1] == dome.floor_y else blocks.solid
        found = at[ln.on]
        assert found == (D.CUT if ln.line == D.ALONG else D.TRACK[ln.metal])
        assert ln.cell in blocks.clear
    else:
        assert blocks.solid[ln.cell] == f"{D.BUILT}[lit=false]"
assert not D.stray_cells(dome)
# the left side of the ring is torn: no line that way
left = [i for i in D.part(dome, "ring") if D.fr_of(fr, every[i].cell)[1] == -D.LANE]
assert len(left) == 2 * D.LANE + 1 - len(D.TORN)
# the track is rough brass and rough copper, the pipe the exposed bulb,
# and no other dome may use them; smooth brass carries only inputs' posts
for block in (*D.TRACK.values(), D.PIPE):
    assert rooms.MEANINGS[block] == D.INDEX
assert D.PIPE not in "".join(blocks.everything().values())

# the levels: 4 to spare at the tuned level, none at the top, the way
# round enough at 1 and 2 only
reach = [D.scaled(level)["n"] for level in game.LEVELS]
assert reach == [81, 77, 74, 70, 67, 66, 65, 64, 63, 63], reach

# the rule of steam: nothing laid, nothing lit; the feed lights riser 1;
# a branch that leads nowhere costs nothing
assert D.steam(dome, [], True) == {}
feed = D.part(dome, "chest")
assert len(D.steam(dome, feed, False)) == 4 + 7
whole = D.steam(dome, short, True)
assert whole[D.sink(dome)] == D.ROUTE
extra = D.steam(dome, [*short, *round_, *D.part(dome, "left", "right")], True)
assert all(extra[i] == whole[i] for i in short)
assert D.sink(dome) not in D.steam(dome, short, False)  # the gear across

# the decoration: nothing of it can be worked by hand or is a block of the
# puzzle, and it leaves the walks and the sights clear
dress = D.dressing(dome)
assert len(dress) > 1500
for block in dress.values():
    for word in ("lever", "button", "pressure_plate", "copper_bulb", "raw_"):
        assert word not in block, block
assert D.inputs(dome) <= blocks.puzzle and len(D.inputs(dome)) == 4
assert not rooms.input_problems(
    {**blocks.solid, **blocks.attached}, D.inputs(dome), place.clutch_lamps,
    blocks.floor)
machine = place.tappets
assert len(machine.pistons) == 2 and not machine.lamps
assert all("sticky" not in b for b in machine.solid.values())
assert not D.walk_problems(dome) and not D.sight_problems(dome)
spots = D.walks(dome)
assert {"the way out", "the clutch", "the Great Gear", "the brass bay"} <= set(spots)
assert spots["the clutch"][1] - dome.floor_y == D.WALK_H + 1
# both checks find a fault: the stair to the catwalk walled off, the far
# door walled off, a block before the steam board
sf, sr = D.CATWALK_STAIR
wall = [fr.at(sf + 2, sr + dr, h)
        for dr in (-1, 0, 1) for h in range(D.DECK_H + 1, D.WALK_H + 4)]
found = D.walk_problems(dome, wall)
assert any("the clutch" in p for p in found) and len(found) == 6, found
wall = [fr.at(dome.radius - 6, r, h)
        for r in range(-dome.radius, dome.radius + 1) for h in (1, 2, 3, 4)]
assert any("the way out" in p for p in D.walk_problems(dome, wall))
assert any("window" in p for p in D.sight_problems(dome, wall))
bx, by, bz = place.board
assert any("steam board" in p for p in D.sight_problems(
    dome, [(bx + dx, by + dy, bz + dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
           for dz in (-1, 0, 1) if (dx, dy, dz) != (0, 0, 0)]))

# the log: four pages at most, by the Chief Engineer, each a page's worth
assert len(D.LOG_PAGES) <= 4 and D.LOG_AUTHOR == "O. Finch"
assert all(len(page) <= 256 for page in D.LOG_PAGES), [len(p) for p in D.LOG_PAGES]
assert len(D.logbook(fr).encode()) < B.MAX_COMMAND
for signs in (D.plaque_signs(67), (D.CLUTCH_SIGN,)):
    assert all(len(line) <= 15 for sign in signs for line in sign), signs
"""
    )


def test_station_gearworks_build_and_pack():
    run(
        PRELUDE
        + """
# the stage against the fake client: every block where the plan has it,
# the stub's bypass gone, the shell and the pump engine left alone, the
# same built twice
stages = ["site", "dome_2", "tunnels", "dome_2_inside"]
rec = B.offline_build(stages=stages, force=False)
for cell, block in blocks.everything().items():
    assert rec.world.at(cell) == block, (cell, block)
for cell in blocks.clear | blocks.swept:
    assert rec.world.name_at(cell) == "minecraft:air", cell
stub = game.stub_post(dome)
assert f"kill @e[tag={game.stub_tag(D.INDEX)}]" in rec.commands
assert all(rec.world.at(c) == blocks.everything().get(c, "minecraft:air")
           for c in stub.cells)
engine = tunnels.engine_cells(L.TUNNELS[D.INDEX])
assert all(rec.world.name_at(c) != "minecraft:air" for c in list(engine.values())[:9])
shell = domes.dome_cells(dome).shell
assert all(rec.world.name_at(c) != "minecraft:air" for c in shell)
summoned = [c for c in rec.commands if c.startswith("summon ") and D.ENTITY_TAG in c]
assert sorted(c.split()[1] for c in summoned) == [
    "minecraft:interaction", "minecraft:text_display", "minecraft:text_display"]
assert sum(fittings.RECALL_TAG in c for c in summoned) == 1
assert "function station:dome/2/reset" in rec.commands
again = B.offline_build(stages=[*stages, "dome_2_inside"], force=False)
assert again.world.dump() == rec.world.dump()

# the pack: the hooks the core calls, one way to solve, nothing aimed wide
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [D.MODULE])
mine = {n: ls for n, ls in pack.functions.items() if n.startswith("dome/2/")}
for hook in (*game.HOOKS, "leave"):
    assert f"dome/2/{hook}" in mine, hook
assert "dome/2/died" not in mine  # (nothing is lost by dying here)
calls = lambda path, name: any(  # noqa: E731
    line.endswith(f"function station:{name}") for line in pack.functions[path]
)
assert calls("dome/2/entered", "dome/2/enter") and calls("game/tick", "dome/2/tick")
assert calls("dome/2/form", "dome/2/solo") and calls("dome/2/form", "dome/2/duo")
assert calls("reset/all", "dome/2/reset") and calls("dome/2/left", "dome/2/empty")
assert calls("dome/2/exited", "dome/2/leave") and calls("reset/all", "dome/2/leave")
solvers = [n for n, ls in mine.items()
           if any("function station:dome/2/solved" in line for line in ls)]
assert solvers == ["dome/2/done"], solvers
assert not V.function_problems(B.pack_files(pack))
for path, lines in mine.items():
    for line in lines:
        assert "@p" not in line, (path, line)
        assert line.count("@a") == line.count("@a[tag=st.in"), (path, line)
# a function of the room for every length of the main
for name in ("scan", "relax", "show", "stats", "restart", "dark"):
    assert len(mine[f"dome/2/{name}"]) >= sum(ln.laid for ln in every), name
assert len(mine["dome/2/relax"]) < 1000 and len(mine) < 70

# what is lent: pipe that sticks to the track, to one metal each for two;
# a wrench that breaks the laid pipe only; all of it taken back on leaving,
# on solving and by the reset, and none of it by the room emptying
gold, copper = D.TRACK["brass"], D.TRACK["copper"]
both, brass = D.pipe_item("both"), D.pipe_item("brass")
assert f'can_place_on={{blocks:["{gold}","{copper}"]}}' in both
assert f'can_place_on={{blocks:["{gold}"]}}' in brass and copper not in brass
assert "tooltip_display" not in both  # what it sticks to is a hint
wrench = D.wrench_item()
assert f'can_break={{blocks:"{D.PIPE}"}}' in wrench and "unbreakable" in wrench
assert D.BUILT not in wrench
given = "".join(line for ls in mine.values() for line in ls if " give @s " in line)
for key in D.KEYS.values():
    assert f'{fittings.LENT}:"{key}"' in given, key
    assert fittings.take_back_line(key) in mine["dome/2/leave"]
    assert fittings.take_back_line(key, game.PLAYERS) in mine["dome/2/reset"]
assert calls("dome/2/restored", "dome/2/leave")
assert not any("clear " in line for line in mine["dome/2/empty"])
# the pipe is taken up by the reset alone
takes = [n for n, ls in mine.items()
         if any(line.startswith("fill ") and D.PIPE in line for line in ls)]
assert takes == ["dome/2/reset"], takes
# the decoration runs whether or not there is a puzzle, and no function of
# the steam reads or writes a cell of it
tick = mine["dome/2/tick"]
at = lambda end: next(i for i, l in enumerate(tick) if l.endswith(end))  # noqa: E731
assert at("function station:dome/2/decor/beat") < at("run return 0")
# a step that solves lends nothing after it in the same tick; the bays are
# read every tick; the logbook is put back after the solve too
returns = [i for i, l in enumerate(tick) if l.endswith("run return 0")]
assert returns[0] < at("function station:dome/2/step") < returns[1]
assert returns[1] < at("function station:dome/2/second")
assert returns[1] < at("function station:dome/2/bay/brass")
assert at("function station:dome/2/book") < returns[0]
assert not any("bay/" in l for l in mine["dome/2/second"])
assert not any("kill @e[type=minecraft:item" in l for l in mine["dome/2/step"])
# the sign at the gear's edge names the clutch
assert any("CLUTCH:" in b for b in D.room_blocks(dome).attached.values())
decor = [D._xyz(c) for c in (*place.lights, *place.pinions[0], *place.pinions[1],
                              *place.tappets.cells)]
for name in ("scan", "relax", "show", "stats", "restart", "dark", "intake",
             "second", "reset", "empty", "arm"):
    for line in mine[f"dome/2/{name}"]:
        assert not any(f" {xyz} " in line for xyz in decor), (name, line)
"""
    )


def test_station_gearworks_steam():
    run(
        PRELUDE
        + MODEL
        + """
# the reset leaves the room as built, and the level's reach is the plan's
m = new_model()
as_built = {c: b.partition("{")[0] for c, b in blocks.everything().items()}
assert m.world == as_built
assert score(m, "n") == D.scaled(game.DEFAULT_LEVEL)["n"] and score(m, "live") == 1
for level in game.LEVELS:
    assert score(new_model(level), "n") == D.scaled(level)["n"], level

# solo, the success path. The feed lights a length a step, riser 1 after it
m.ticks(40)
assert not lit(m) and score(m, "far") == 0 and score(m, "form") == 1
laid = lay(m, D.part(dome, "chest"))
m.ticks(D.STEP)
assert len(lit(m)) == 1
m.ticks(D.STEP * 3)
assert len(lit(m)) == 4
m.ticks(CREEP)
assert lit(m) == want(m, laid, False) and len(lit(m)) == 11 == score(m, "far")
# on to the gear, which lies across: the steam stops at its edge
laid |= lay(m, [i for i in short if every[i].part in ("ring", "back")])
m.ticks(CREEP)
assert lit(m) == want(m, laid, False) and score(m, "far") == 23
assert score(m, "spent") == 0 and not solved(m)
assert m.scores["#hint2.gear"] > 10 and m.scores["#hint2.short"] < 3
# pipe laid on the gear as found is thrown off when the clutch is thrown,
# the gear's track is taken up and laid the other way, and the lever latches
on_gear = lay(m, D.part(dome, "across"))
m.ticks(CREEP)
# (it joins the side bridges, not the line: none of it fills)
assert lit(m) == want(m, laid | on_gear, False) and len(lit(m)) == 23
m.setblock(place.lever, D.lever_block(fr, True))
m.ticks(2)
assert score(m, "gear") == 1 and score(m, "turn") > 0
assert all(not m.is_block(every[i].cell, D.PIPE) for i in on_gear)
assert all(m.is_block(c, D.CUT) for c, _ in place.gear_track[D.ACROSS])
assert all(m.is_block(c, f"{D.LAMP}[lit=true]") for c in place.clutch_lamps)
m.ticks(D.TURN_TICKS)
assert score(m, "gear") == 2 and score(m, "turn") == 0
assert all(m.is_block(c, b) for c, b in place.gear_track[D.ALONG])
m.setblock(place.lever, D.lever_block(fr))
m.ticks(1)
assert m.is_block(place.lever, D.lever_block(fr, True)) and score(m, "gear") == 2
assert lit(m) == want(m, laid, True)
# the rest of the short way: the intake's lamps count up, and it is solved
laid |= lay(m, short)
m.ticks(D.STEP * 45)
assert lit(m) == want(m, laid, True) and len(lit(m)) == D.ROUTE and not solved(m)
seen = set()
for _ in range(COUNT):
    m.ticks(1)
    seen.add(sum(m.is_block(c, D.INTAKE_LIT) for c in place.intake))
assert solved(m) and seen == {0, 1, 2, 3}, seen
assert m.called.count(SOLVED) == 1 and score(m, "live") == 0
# solved: steady, the pipe lit as it lies, whatever is done to it after
m.setblock(every[short[12]].cell, AIR)
m.ticks(100)
assert len(lit(m)) == D.ROUTE - 1 and m.called.count(SOLVED) == 1
m.run("dome/2/empty")
assert len(lit(m)) == D.ROUTE - 1

# the limit: the way round the gallery is too long at the tuned level
m = new_model()
laid = lay(m, round_)
m.ticks(CREEP + COUNT)
n = score(m, "n")
assert lit(m) == want(m, laid, False) and len(lit(m)) == n == score(m, "far")
assert score(m, "spent") == 1 and not solved(m) and m.scores["#hint2.short"] > 10
assert not any(m.is_block(c, D.INTAKE_LIT) for c in place.intake)
# the gentle rule: the short way laid beside it solves, the long one left
throw_clutch(m)
laid |= lay(m, short)
m.ticks(CREEP + COUNT)
assert solved(m) and lit(m) == want(m, laid, True)
# at the two gentlest levels the way round is enough; at the top level the
# short way is exact
for level in (1, 2):
    m = new_model(level)
    lay(m, round_)
    m.ticks(CREEP + COUNT)
    assert solved(m), level
m = new_model(10)
throw_clutch(m)
laid = lay(m, short)
m.ticks(CREEP + COUNT)
assert solved(m) and score(m, "n") == D.ROUTE

# a lit length taken out: dark beyond it and never before it; put back, it
# fills again. A dark length taken out changes nothing
m = new_model()
throw_clutch(m)
laid = lay(m, short) - {short[-1]}
cut = next(i for i in short if every[i].part == "back")
before = set(short[: short.index(cut)])
m.ticks(D.STEP * (short.index(cut) + 6))
assert cut in lit(m) and not solved(m)
m.setblock(every[cut].cell, AIR)
for _ in range(3 * D.STEP):
    m.ticks(1)
    assert before <= lit(m)
assert lit(m) == before == want(m, laid - {cut}, True)
far = short[short.index(cut) + 8]
calls = len(m.called)
m.setblock(every[far].cell, AIR)
m.ticks(3 * D.STEP)
assert lit(m) == before and "dome/2/restart" not in m.called[calls:]
lay(m, [cut, far])
m.ticks(CREEP + COUNT)
assert solved(m) and lit(m) == want(m, laid, True)

# leaving: the room empties, the pipe is kept and goes dark; the first
# back in finds it filling again, with the reach of the level then in force
m = new_model()
throw_clutch(m)
laid = lay(m, short[:40])
m.ticks(CREEP)
assert len(lit(m)) == 40
m.run("dome/2/empty")
assert not lit(m) and score(m, "live") == 0 and score(m, "far") == 0
assert all(m.is_block(every[i].cell, D.PIPE) for i in laid)
assert score(m, "gear") == 2 and m.is_block(place.lever, D.lever_block(fr, True))
m.scores.update(game.scaled(8))
m.run("dome/2/enter")
assert score(m, "n") == D.scaled(8)["n"] and score(m, "live") == 1
m.ticks(CREEP)
assert lit(m) == want(m, laid, True) and len(lit(m)) == 40 and not solved(m)
# one who is not the first in changes nothing
m.scores["#first"] = 0
m.scores.update(game.scaled(1))
m.run("dome/2/enter")
m.ticks(4)
assert score(m, "n") == D.scaled(8)["n"] and len(lit(m)) == 40

# a change of form is taken up at the next second's beat and changes no
# block: the laid pipe, the steam and the gear are as they were
def still(m):  # (but the decoration, which steps as it likes)
    return {c: b for c, b in m.world.items() if c not in blocks.either}
world = still(m)
m.run("dome/2/duo")
assert score(m, "form") == 1
m.ticks(21)
assert score(m, "form") == 2 and still(m) == world
m.run("dome/2/solo")
m.ticks(21)
assert score(m, "form") == 1 and still(m) == world and len(lit(m)) == 40

# the reset, from a scrambled room: pipe everywhere, the gear half way
# through its turn, the lever over, the duo form, a count at the intake
m = new_model()
lay(m, range(len(every)))
m.ticks(CREEP)
m.run("dome/2/duo")
m.setblock(place.lever, D.lever_block(fr, True))
m.ticks(D.TURN_TICKS // 2)
m.setblock(place.intake[0], D.INTAKE_LIT)
m.scores["#gear.sink"] = 7
assert score(m, "gear") == 1 and len(lit(m)) > 60
m.run("dome/2/reset")
steps = set(blocks.either)  # (the decoration is left as it stands)
assert {c: b for c, b in m.world.items() if c not in steps} == {
    c: b for c, b in as_built.items() if c not in steps}
for name in ("far", "spent", "sink", "gear", "turn", "live"):
    assert score(m, name) == 0, name
assert score(m, "form") == 1 and score(m, "want") == 1

# the decoration: two running lights at a time going round, the pinions
# stepping; four times the pace once solved, the gear's teeth joining in
m = new_model()
frames, teeth = [], set()
for _ in range(8 * D.DECOR_AT):
    m.ticks(1)
    frames.append(score(m, "frame") or 0)
    teeth.add(m.is_block(place.teeth[0][0], D.TOOTH[0]))
    glowing = [c for c in place.lights if m.is_block(c, D.GLOW)]
    assert len(glowing) in (0, 2)
assert sorted(set(frames)) == list(range(8)) and teeth == {True}
slow = sum(a != b for a, b in zip(frames, frames[1:]))
m.scores["#d2"] = 2
frames, pinion = [], set()
for _ in range(8 * D.DECOR_AT):
    m.ticks(1)
    frames.append(score(m, "frame") or 0)
    teeth.add(m.is_block(place.teeth[0][0], D.TOOTH[0]))
    pinion.add(m.is_block(place.pinions[0][0], D.TOOTH[0]))
fast = sum(a != b for a, b in zip(frames, frames[1:]))
assert fast >= 4 * slow - 1 and teeth == {True, False} == pinion
for cell, pair in blocks.either.items():
    assert m.world[cell] in pair, cell
"""
    )
