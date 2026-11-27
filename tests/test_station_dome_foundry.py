"""
The Foundry (examples/station/dome_foundry.py) with no server: its plan
against the dome and the rules for a room, its build stage against the
example's fake client, and its datapack functions, which are run here by a
small interpreter of the commands a state machine is made of (scores,
``execute if``, blocks set and read, functions and macros, automatons as
sets of tags), so that the fight is played through offline: the switch,
the waves, the trips in both forms, a death, leaving and coming back, the
end and the reset. What the interpreter does not know (titles, sounds,
particles, bossbars, entity data) it passes by.

The example changes sys.path when it is imported and its module names are
short, so each test runs in a Python of its own, in the example's folder.
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


def test_station_foundry_room():
    run(
        r"""
import build_station as B
import dome_foundry as D
N = D.INDEX  # the dome's place in the ring
import domes
import fittings
import game
import rooms
import station_layout as L
import tunnels
import verify_station as V

dome = L.DOMES[D.INDEX]
assert B.STAGES[f"dome_{N}_inside"] is D.build and V.LIVE["foundry"] is D.check
assert "foundry" not in V.todos()
assert not any(m.name == "stub_foundry" for m in B.modules())

# the room's cells: inside the dome, off the reserved cells, in the dome's
# own frame
assert not D.room_problems(dome)
blocks = D.room_blocks(dome)
place = D.room(dome)
fr = D.frame(dome)
cells = domes.dome_cells(dome)
used = set(blocks.above()) | blocks.clear | blocks.swept
assert used <= cells.interior and not used & tunnels.reserved_cells(dome)
assert set(blocks.floor) <= cells.floor
assert not set(blocks.floor) & domes.light_cells(dome)[0]
assert fr.at(0, 0, 0) == dome.floor_centre
x, y, z, _ = domes.entrance(dome)
assert D.fr_of(fr, (x, y, z)) == (-(dome.radius - domes.ENTRANCE_OFFSET), 0, 1)
assert not fittings.placement_problems(dome, used)
assert not rooms.room_problems(dome, blocks.above(), blocks.floor)
assert not rooms.window_problems(dome, blocks.above())

# three levels, and the fight uses all of them: a breaker on each
a, b, c = place.breakers
heights = [x.stand[1] - dome.floor_y for x in place.breakers]
assert heights == [1, D.DECK_H + 1, D.GANTRY_H + 1]
assert [x.level for x in place.breakers] == ["floor", "gallery", "top deck"]
top = max(cell[1] for cell in blocks.solid) - dome.floor_y
assert top >= 20
# the mast: twelve cells of four lamps, the switch at its foot on brass
assert len(place.mast) == 4 and all(len(col) == D.CELLS for col in place.mast)
assert blocks.solid[place.switch_on] == D.BRASS
lamps = {cell for col in place.mast for cell in col}
assert all("copper_bulb[lit=false]" in blocks.solid[cell] for cell in lamps)
# every input is listed, on brass, with a sign; nothing else can be worked
inputs = D.inputs(dome)
assert len(inputs) == 5
found = {cell for cell, block in blocks.above().items() if rooms.is_input(block)}
assert found == inputs
assert not rooms.input_problems(blocks.above(), inputs, floor=blocks.floor)
puzzle, dress = D.puzzle_blocks(dome), D.dressing_blocks(dome)
assert not set(puzzle.everything()) & set(dress.everything())
assert len(dress.everything()) > len(puzzle.everything())
for block in dress.everything().values():
    assert not rooms.is_input(block), block
# the dressing's gold is nil: brass is the mark of an input
assert not [b for b in dress.everything().values() if "gold_block" in b]

# the gallery is a horseshoe: nothing of it in the south-west, where the
# way to the exit and the pouring floor are
deck = {D.fr_of(fr, cell)[:2] for cell in dress.solid
        if cell[1] - dome.floor_y == D.DECK_H and "grate" in dress.solid[cell]}
assert deck and not [fr_ for fr_ in deck if fr_[0] < -2 and fr_[1] < -2]
assert (0, -D.LADDER_R) in deck and (-15, 0) in deck and (15, 0) in deck
assert D.ring_part(-10, -10) == "" and D.ring_part(10, 10) == "deck"
# the decorative machinery: the shared torch clock with plain pistons, on
# the north mould's roof, in a cage; no tally house (no comparator)
machine = place.machine
assert len(machine.lamps) == 4 and len(machine.pistons) == 2
assert all(blocks.solid[p] == "minecraft:piston[facing=up]" for p in machine.pistons)
assert all(cell[1] - dome.floor_y >= D.MOULD_ROOF for cell in machine.cells)
assert not [b for b in blocks.everything().values() if "comparator" in b]
assert not [b for b in blocks.everything().values() if "sticky" in b]
assert list(blocks.late) == list(machine.attached)  # the order that starts it
# the machine's dust touches no full block that would pass its power on
names = {cell: rooms.name(block) for cell, block in blocks.above().items()}
wire = [cell for cell, n in names.items() if n == "minecraft:redstone_wire"]
level = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)]
for x, y, z in wire:
    for dx, _, dz in level:
        beside = (x + dx, y, z + dz)
        if beside in machine.cells:
            continue
        assert names.get(beside, "minecraft:iron_bars") == "minecraft:iron_bars"

# the walks and the sights, and that each check finds a fault
assert not D.walk_problems(dome) and not D.sight_problems(dome)
walks = {**D.walks(dome), **D.gantry_walks(dome)}
wanted = {"the way out", "the main switch", "breaker A", "breaker B", "breaker C",
          "the east ladder's foot", "the west ladder's head"}
assert wanted <= set(walks)
real = D.dressing_blocks
def stopped(dome):  # both stairs gone: no way up to the gallery
    d = real(dome)
    for cell in D.stair_treads(fr):
        del d.solid[cell]
    return d
D.dressing_blocks = stopped
found = D.walk_problems(dome)
assert any("breaker B" in p for p in found) and any("ladder's foot" in p for p in found)
assert not any("breaker A" in p or "breaker C" in p for p in found)
assert D.room_problems(dome)
def unlidded(dome):  # the battery's cage open on top: a pit from the gallery
    d = real(dome)
    for cell, block in list(d.solid.items()):
        if block == D.GRATE and D.fr_of(fr, cell)[2] == D.MOULD_ROOF + 3:
            del d.solid[cell]
    return d
D.dressing_blocks = unlidded
assert any("no way out" in p for p in D.walk_problems(dome))
# the stairs' top tread is level with the gallery's deck: no full step up
assert {D.fr_of(fr, c)[2] for c in D.stair_treads(fr)} == set(range(1, D.DECK_H + 1))
def boxed(dome):
    d = real(dome)
    for f in range(-3, 4):
        for r in range(-3, 4):
            if max(abs(f), abs(r)) == 3:
                for h in (4, 5, 6, 7):
                    d.solid.setdefault(fr.at(f, r, h), D.COPPER)
    return d
D.dressing_blocks = boxed
assert any("cell 1 of the mast is hidden" in p for p in D.sight_problems(dome))
def broken(dome):  # a ladder with a rung gone, and a lever in the dressing
    d = real(dome)
    del d.attached[fr.at(0, D.LADDER_R, D.DECK_H + 3)]
    d.attached[fr.at(5, 5, 1)] = fittings.lever("north", face="floor")
    return d
D.dressing_blocks = broken
found = D.room_problems(dome)
assert any("east ladder is not whole" in p for p in found)
assert any("an input in the dressing" in p for p in found)
assert any("the room does not list" in p for p in found)
D.dressing_blocks = real
assert not D.room_problems(dome)
# a lamp against the switch's brass would be worked by the lever
real_puzzle = D.puzzle_blocks
def lamped(dome):
    b = real_puzzle(dome)
    x, y, z = place.switch_on
    b.solid[x, y + 1, z] = f"{D.BULB}[lit=false]"
    return b
D.puzzle_blocks = lamped
assert any("touches the block of the input" in p for p in D.room_problems(dome))
D.puzzle_blocks = real_puzzle

# the story: Finch's log, four pages at most, each one a page of a book
assert D.LOG_AUTHOR == "O. Finch" and len(D.LOG_PAGES) <= 4
text = " ".join(D.LOG_PAGES)
assert "Chief Engineer" in text and "bad at ladders" in text and "hiring" in text
assert "what a man looks like" in text and "cannot climb" not in text
assert all(len(page) <= 256 for page in D.LOG_PAGES), [len(p) for p in D.LOG_PAGES]
for sign in (*D.PLAQUE_SIGNS, D.SWITCH_SIGN):
    assert len(sign) <= 4 and all(len(line) <= 15 for line in sign), sign

# the stage against the fake client: the stub's post taken away, every
# block where the plan has it, the shell and the pump engine left alone,
# the entities summoned once, the same built twice
stages = ["site", f"dome_{N}", "tunnels", f"dome_{N}_inside"]
rec = B.offline_build(stages=stages, force=False)
assert f"kill @e[tag={game.stub_tag(D.INDEX)}]" in rec.commands
for cell, block in blocks.everything().items():
    assert rec.world.at(cell) == block, (cell, block)
for cell in blocks.clear | blocks.swept:
    assert rec.world.name_at(cell) == "minecraft:air", cell
for cell in game.stub_post(dome).cells - set(blocks.above()):
    assert rec.world.name_at(cell) == "minecraft:air", cell
engine = tunnels.engine_cells(L.TUNNELS[D.INDEX])
assert all(rec.world.name_at(c) != "minecraft:air" for c in list(engine.values())[:9])
assert all(rec.world.name_at(c) != "minecraft:air" for c in cells.shell)
for light in domes.light_cells(dome)[0]:
    assert rec.world.at(light) == domes.LIGHT, light
count = lambda kind: sum(  # noqa: E731
    c.startswith(f"summon minecraft:{kind}") for c in rec.commands)
summoned = [count(k) for k in ("interaction", "text_display", "block_display")]
assert summoned == [1, 4, 4], summoned
assert len(D.summons(dome)) == 9
assert f"function station:dome/{N}/reset" in rec.commands
assert all(len(c.encode()) <= B.MAX_COMMAND for c in rec.commands)
again = B.offline_build(stages=[*stages, f"dome_{N}_inside"], force=False)
assert again.world.dump() == rec.world.dump()
"""
    )


#: the interpreter the fight is played through with (see the module docstring)
SIM = r'''
import re


class Stop(Exception):
    """``return`` in a function"""


class Sim:
    def __init__(self, pack, blocks):
        self.functions = pack.functions
        self.scores = {}
        self.blocks = dict(blocks)
        self.mobs = []  # each a set of tags
        self.players = 1  # how many carry st.in
        self.difficulty = 1
        self.me = None
        self.calls = []  # every function run, in order
        self.passed = set()  # the commands passed by
        for line in pack.setup_lines():
            self.cmd(line)
        for name in pack._load:
            self.function(name.partition(":")[2])

    # -- scores and blocks
    def get(self, name, objective="st"):
        return self.scores.get((name, objective))

    def put(self, name, value, objective="st"):
        self.scores[name, objective] = value

    def fdy(self, name):
        return self.get(f"#fdy.{name}")

    def is_block(self, cell, pattern):
        have = self.blocks.get(cell, "minecraft:air").partition("{")[0]
        name, _, states = pattern.partition("{")[0].partition("[")
        if have.partition("[")[0] != name:
            return False
        mine = have.partition("[")[2].rstrip("]").split(",")
        return all(s in mine for s in states.rstrip("]").split(",") if s)

    # -- entities: automatons by their tags; nobody else
    def select(self, selector):
        if selector.startswith("@s"):
            return [self.me]
        if "type=" in selector or selector.startswith("@a"):
            return []
        tags = re.findall(r"tag=([\w.]+)", selector)
        if "st.in" in tags:
            return [None] * self.players
        return [m for m in self.mobs if all(t in m for t in tags)]

    # -- commands
    def function(self, path, args=None):
        self.calls.append(path)
        try:
            for line in self.functions[path]:
                if line.startswith("$"):
                    line = re.sub(r"\$\((\w+)\)", lambda m: args[m.group(1)], line[1:])
                self.cmd(line)
        except Stop:
            pass

    def cmd(self, line):
        word, _, rest = line.partition(" ")
        if word == "execute":
            return self.execute(rest.split(" "))
        if word == "function":
            name, _, more = rest.partition(" ")
            if more.startswith("with "):
                return None
            found = re.findall(r'(\w+):("[^"]*"|[^,}]+)', more)
            return self.function(
                name.partition(":")[2], {k: v.strip('"') for k, v in found}
            )
        if word == "return":
            raise Stop
        if word == "scoreboard":
            return self.scoreboard(rest.split(" "))
        if word == "setblock":
            x, y, z, block = rest.split(" ", 3)
            self.blocks[int(x), int(y), int(z)] = block
        elif word == "summon":
            listed = re.search(r"Tags:\[([^\]]*)\]", rest)
            if listed and "st.mob" in listed.group(1):
                self.mobs.append(set(re.findall(r'"([^"]+)"', listed.group(1))))
        elif word == "kill":
            gone = self.select(rest)
            self.mobs = [m for m in self.mobs if not any(m is g for g in gone)]
        elif word == "tag" and rest.startswith("@s remove "):
            self.me.discard(rest.rpartition(" ")[2])
        elif word == "difficulty" and not rest:
            return self.difficulty
        else:
            self.passed.add(word)
        return None

    def scoreboard(self, t):
        if t[:2] == ["objectives", "add"]:
            return None
        assert t[0] == "players", t
        verb, name, objective = t[1], t[2], t[3]
        have = self.scores.get((name, objective), 0)
        if verb == "get":
            return self.scores.get((name, objective), 0)
        if verb == "reset":
            self.scores.pop((name, objective), None)
        elif verb in ("set", "add", "remove"):
            n = int(t[4])
            self.scores[name, objective] = {
                "set": n, "add": have + n, "remove": have - n}[verb]
        elif verb == "operation":
            other = self.scores.get((t[5], t[6]), 0)
            self.scores[name, objective] = {
                "=": lambda: other,
                "+=": lambda: have + other,
                "-=": lambda: have - other,
                "*=": lambda: have * other,
                "/=": lambda: have // other,
                "<": lambda: min(have, other),
                ">": lambda: max(have, other),
            }[t[4]]()
        else:
            raise ValueError(t)
        return None

    @staticmethod
    def matches(value, span):
        if value is None:
            return False
        lo, dots, hi = span.partition("..")
        if not dots:
            return value == int(lo)
        return (not lo or value >= int(lo)) and (not hi or value <= int(hi))

    def execute(self, t):
        store, result, i = None, 1, 0
        while i < len(t):
            word = t[i]
            if word == "run":
                result = self.cmd(" ".join(t[i + 1 :]))
                break
            if word in ("if", "unless"):
                kind = t[i + 1]
                if kind == "score":
                    a = self.scores.get((t[i + 2], t[i + 3]))
                    if t[i + 4] == "matches":
                        ok, step = self.matches(a, t[i + 5]), 6
                    else:
                        b = self.scores.get((t[i + 5], t[i + 6]))
                        ok = a is not None and b is not None and {
                            "=": a == b, "<": a < b, "<=": a <= b,
                            ">": a > b, ">=": a >= b}[t[i + 4]]
                        step = 7
                elif kind == "block":
                    cell = tuple(int(v) for v in t[i + 2 : i + 5])
                    ok, step = self.is_block(cell, t[i + 5]), 6
                elif kind == "entity":
                    result = len(self.select(t[i + 2]))
                    ok, step = result > 0, 3
                else:
                    return None
                if ok != (word == "if"):
                    if store and i + step >= len(t):
                        self.scores[store] = 0
                    return None
                i += step
            elif word == "store":
                if t[i + 2] == "score":
                    store, i = (t[i + 3], t[i + 4]), i + 5
                else:
                    i += {"bossbar": 5, "storage": 7}[t[i + 2]]
            elif word in ("as", "at"):
                for one in self.select(t[i + 1]):
                    kept, self.me = self.me, one if one is not None else self.me
                    try:
                        self.execute(t[i + 2 :])
                    finally:
                        self.me = kept
                return None
            else:
                return None
        if store and result is not None:
            self.scores[store] = int(result)
        return result
'''


def test_station_foundry_fight():
    run(
        SIM
        + r"""
import build_station as B
import automatons
import datapack
import dome_foundry as D
N = D.INDEX  # the dome's place in the ring
import fittings
import game
import station_layout as L
import verify_station as V

dome = L.DOMES[D.INDEX]
place = D.room(dome)
plan = D.room_blocks(dome)
a, b, c = place.breakers
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [D.MODULE])

# the pack: the hooks the core calls, one way to solve, nothing aimed wide
for hook in (*game.HOOKS, "died"):
    assert f"dome/{N}/{hook}" in pack.functions, hook
assert f"dome/{N}/leave" not in pack.functions
calls = lambda path, name: any(  # noqa: E731
    line.endswith(f"function station:{name}") for line in pack.functions[path]
)
assert calls(f"dome/{N}/entered", f"dome/{N}/enter")
assert calls("game/tick", f"dome/{N}/tick")
assert calls(f"dome/{N}/form", f"dome/{N}/solo")
assert calls(f"dome/{N}/form", f"dome/{N}/duo")
assert calls("reset/all", f"dome/{N}/reset")
assert calls(f"dome/{N}/left", f"dome/{N}/empty")
assert calls(f"dome/{N}/respawned", f"dome/{N}/died")
assert calls(f"dome/{N}/entered", "kit/foundry")  # the core's kit, not the room's
mine = {n: ls for n, ls in pack.functions.items() if n.startswith(f"dome/{N}/")}
# a trip's title names every breaker of the stage, in one title
assert not any("title" in line for i in range(3) for line in mine[f"dome/{N}/trip/{i}"])
stage = "\n".join(mine[f"dome/{N}/trip_stage"])
assert "BREAKERS A AND B TRIPPED" in stage and "BREAKER C TRIPPED" in stage
solvers = [n for n, ls in mine.items()
           if any(f"function station:dome/{N}/solved" in line for line in ls)]
assert solvers == [f"dome/{N}/done"], solvers
assert not V.function_problems(B.pack_files(pack))
assert not V.name_problems({n: ls for n, ls in mine.items()})
for name, lines in mine.items():
    for line in lines:
        assert "@p" not in line and "@r" not in line, (name, line)
        for at in re.finditer(r"@a", line):
            assert line[at.end():].startswith("[tag=st.in"), (name, line)
        # entities go by their tags, never by where they are (but the
        # core's sweep of arrows and orbs, and the automatons' leash)
        if line.startswith("kill") or " run kill " in line:
            assert "type=#minecraft:arrows" in line or "experience_orb" in line, line
# what the core has, the room does not do again
text = "\n".join(line for lines in mine.values() for line in lines)
for own in ("st.died", "team ", "minecraft:shield", "spectral_arrow", "loot"):
    assert own not in text, own
for core in ("mob/count", "fight/difficulty"):
    assert f"function station:{core}" in text, core
# an unproved particle is behind a macro, so that it cannot take a function
# (and every function that calls it) with it when the pack loads
for name, lines in mine.items():
    for line in lines:
        if "particle " in line and not line.startswith("$"):
            assert "minecraft:cloud" in line or "campfire_cosy_smoke" in line, line
# the machinery: no function of the room touches the battery, and only the
# crane's own functions the ladle
battery = [D._xyz(cell) for cell in place.machine.cells]
for name, lines in mine.items():
    for line in lines:
        assert not any(xyz in line for xyz in battery), (name, line)
        if D.LADLE_TAG in line:
            assert name.startswith(f"dome/{N}/crane"), name
        assert f"tag={D.ENTITY_TAG}]" not in line and f"tag={D.ENTITY_TAG}," not in line
assert calls(f"dome/{N}/reset", f"dome/{N}/rest")
assert calls(f"dome/{N}/empty", f"dome/{N}/rest")
assert len(D.logbook(place.frame).encode()) < B.MAX_COMMAND

# the values of a level: gentle at 1, tuned at 5, hard at 10
one, five, ten = (D.scaled(level) for level in (1, 5, 10))
assert five == {"rate": D.RATE, "gap": D.GAP, "pen": D.PENALTY}
assert D.seconds(5) == 160 and D.seconds(1) < 160 < D.seconds(10) < 240
assert one["gap"] > five["gap"] > ten["gap"] and one["pen"] < five["pen"] < ten["pen"]
assert D.wave(5, 1, 0) == {"cap": 6, "stoker": 2, "stoker_cap": 3, "riveter": 0,
                           "riveter_cap": 2, "husk": 0}
assert D.wave(5, 2, 3) == {"cap": 10, "stoker": 3, "stoker_cap": 5, "riveter": 2,
                           "riveter_cap": 3, "husk": 2}
assert D.wave(5, 4, 0)["cap"] == 14 and D.wave(5, 4, 0)["stoker"] == 5
for level in game.LEVELS:
    for players in (1, 2, 3):
        w = D.wave(level, players, 3)
        assert w["cap"] <= D.MOST and w["stoker_cap"] >= 1, (level, players, w)
        assert w["stoker_cap"] + w["riveter_cap"] + w["husk"] == w["cap"]
    assert D.scaled(level)["gap"] * D.LAST_GAP[0] // D.LAST_GAP[1] > D.WARN
    assert 0 < D.scaled(level)["pen"] < D.QUARTER
assert D.last_quarter(D.QUARTER * 2 + 5) == 2 * D.QUARTER and D.last_quarter(5) == 0
assert D.TRIP[1] == {1: (0,), 2: (1,), 3: (2,)} and D.RELIEF == {1: 1, 2: 2, 3: 0}
assert all(len(set(pair)) == 2 for pair in D.TRIP[2].values())

# ---- the fight, played through
LIT, DARK = f"{D.BULB}[lit=true]", f"{D.BULB}[lit=false]"
ON = fittings.lever(place.switch_facing, True)
OFF = fittings.lever(place.switch_facing)
RIVETER, STOKER, HUSK = (k.tag for k in (automatons.RIVETER, automatons.STOKER,
                                         automatons.SLAG_HUSK))


def new(level=5, players=1):
    sim = Sim(pack, plan.everything())
    sim.put("#level", level)
    sim.function("difficulty/apply")
    sim.put(f"#d{N}", 1)
    come_in(sim, players)
    return sim


def come_in(sim, players=1):
    # as the core does it: the first into an empty dome, then the form
    sim.players = players
    sim.put(f"#occ{N}", players)
    sim.put(f"#form{N}", min(players, 2))
    sim.put("#first", 1)
    sim.function(f"dome/{N}/enter")
    sim.function(f"dome/{N}/duo" if players > 1 else f"dome/{N}/solo")


def leave(sim):
    # as the core does it, 3 s after the last player went
    sim.players = 0
    sim.function(f"dome/{N}/left")


def tick(sim, ticks=1):
    for _ in range(ticks):
        sim.function(f"dome/{N}/tick")


def until(sim, done, limit=20000):
    for n in range(limit):
        if done():
            return n
        tick(sim)
    raise AssertionError("it never came")


def levers(sim):
    return [sim.is_block(x.lever, x.block(True)) for x in place.breakers]


def lamps(sim):
    return [sim.is_block(x.lamp, LIT) for x in place.breakers]


def mast(sim):
    return sum(sim.is_block(cell, LIT) for col in place.mast for cell in col)


def alive(sim, tag=None):
    return sum(tag is None or tag in m for m in sim.mobs)


def as_built(sim):
    wrong = [cell for cell, block in plan.everything().items()
             if cell not in plan.moving and sim.blocks[cell] != block]
    assert not wrong, [(cell, sim.blocks[cell]) for cell in wrong[:5]]
    for name in ("state", "charge", "stage", "floor", "wait", "bus", "live"):
        assert sim.fdy(name) == 0, name
    assert sim.fdy("closed") == 3
    assert not sim.mobs and sim.get(f"#bar{N}") == 0


sim = new()
five = D.scaled(5)
assert {n: sim.fdy(n) for n in five} == five
assert (sim.fdy("live"), sim.fdy("state"), sim.fdy("form")) == (1, 0, 1)
as_built_but_live = dict(sim.blocks)
# nothing starts until the switch is thrown
tick(sim, 30 * 20)
assert (sim.fdy("state"), sim.fdy("charge"), alive(sim)) == (0, 0, 0)
# on Peaceful it will not start, and the switch is thrown back
sim.difficulty = 0
sim.blocks[place.switch] = ON
tick(sim, D.STEP)
assert sim.fdy("state") == 0 and sim.is_block(place.switch, OFF)
assert f"dome/{N}/refuse" in sim.calls and sim.get("#difficulty") == 0
sim.difficulty = 1
# the switch: the fight, its bossbar, the first wave after 5 s
sim.blocks[place.switch] = ON
tick(sim, D.STEP)
assert sim.fdy("state") == 1
assert sim.get(f"#bar{N}") == 1
assert sim.get("#difficulty") == 1
sim.blocks[place.switch] = OFF  # (it will not go back)
tick(sim, D.STEP)
assert sim.is_block(place.switch, ON)
assert alive(sim) == 0
until(sim, lambda: f"dome/{N}/warn" in sim.calls, D.FIRST)
assert all(sim.is_block(cell, LIT) for cell in place.telltales)
warned = len(sim.calls)
until(sim, lambda: alive(sim), D.WARN + 1)
assert sim.calls.index(f"dome/{N}/cast") > warned - 5
assert all(sim.is_block(cell, DARK) for cell in place.telltales)
w = D.wave(5, 1, 0)
cast = [alive(sim, kind) for kind in (STOKER, RIVETER, HUSK)]
assert cast == [w["stoker"], 0, 0], cast
assert not [m for m in sim.mobs if automatons.NEW in m]  # dressed
homes = sorted(t for m in sim.mobs for t in m if t.startswith("st.home"))
assert homes == ["st.home0", "st.home1"]  # the two moulds in turn
assert sim.fdy("next") in range(five["gap"] - D.STEP, five["gap"] + 1)
# the charge climbs with all three closed, and stands with one open
assert 0 < sim.fdy("charge") < D.QUARTER
sim.blocks[a.lever] = a.block(False)
tick(sim, D.STEP)
stood = sim.fdy("charge")
tick(sim, 10 * D.STEP)
assert sim.fdy("charge") == stood and sim.fdy("closed") == 2
assert lamps(sim) == [False, True, True]
sim.blocks[a.lever] = "minecraft:air"  # a lever gone is put back, open
tick(sim, D.STEP)
assert sim.is_block(a.lever, a.block(False))
sim.blocks[a.lever] = a.block(True)
tick(sim, D.STEP)
assert sim.fdy("charge") > stood and lamps(sim) == [True, True, True]

# solo: a breaker trips at each quarter, floor then gallery then top deck,
# and the waves grow; never more alive than the cap, nor Riveters than theirs
most = {"all": 0, RIVETER: 0, STOKER: 0}
kinds = set()


def watch(done):
    def seen():
        most["all"] = max(most["all"], alive(sim))
        for tag in (RIVETER, STOKER):
            most[tag] = max(most[tag], alive(sim, tag))
        kinds.update(t for m in sim.mobs for t in m if t.startswith("st.k."))
        return done()
    return seen


for stage, which in D.TRIP[1].items():
    until(sim, watch(lambda: sim.fdy("stage") == stage))  # noqa: B023
    assert sim.fdy("charge") == stage * D.QUARTER == sim.fdy("floor")
    want = [i not in which for i in range(3)]
    assert levers(sim) == want and lamps(sim) == want, (stage, levers(sim))
    assert mast(sim) == 4 * (stage * D.QUARTER // D.CELL)
    tick(sim, 20 * 20)  # nobody closes it: the charge stands, the waves go on
    assert sim.fdy("charge") == stage * D.QUARTER and sim.fdy("state") == 1
    sim.blocks[place.breakers[which[0]].lever] = place.breakers[which[0]].block(True)
    tick(sim, D.STEP)
    assert sim.fdy("charge") > stage * D.QUARTER, (stage, sim.fdy("charge"))
    assert levers(sim) == [True] * 3, (stage, levers(sim))
w = D.wave(5, 1, 3)  # (nothing was killed: every cap was met, none passed)
want = {"all": w["cap"], RIVETER: w["riveter_cap"], STOKER: w["stoker_cap"]}
assert most == want, most
assert kinds == {STOKER, RIVETER, HUSK}
# in the last quarter the waves come sooner
sim.put("#fdy.next", 1)
tick(sim)
assert sim.fdy("next") == five["gap"] * 3 // 4
# a death costs a cell, and never more than the quarter in progress
sim.put("#fdy.charge", 3 * D.QUARTER + 3 * D.CELL)
sim.function(f"dome/{N}/died")
assert sim.fdy("charge") == 3 * D.QUARTER + 3 * D.CELL - five["pen"]
sim.put("#fdy.charge", 3 * D.QUARTER + 10)
sim.function(f"dome/{N}/died")
assert sim.fdy("charge") == 3 * D.QUARTER
# the end: the twelfth cell
steps = until(sim, lambda: sim.fdy("state") == 2)
assert sim.get(f"#d{N}") == 2 and sim.calls.count(f"dome/{N}/solved") == 1
assert not sim.mobs and mast(sim) == 4 * D.CELLS and sim.get(f"#bar{N}") == 0
assert levers(sim) == [True] * 3 and sim.is_block(place.switch, ON)
# its pump waits for its lever by the airlock
assert sim.get(f"#t{N}") == 0 and sim.get(f"#t{N}.ready") == 1
assert sum(sim.is_block(cell, LIT) for cell in place.bus) < len(place.bus)
tick(sim, 3 * len(place.bus) + 2)
assert all(sim.is_block(cell, LIT) for cell in place.bus)
# the charged room: nothing more is cast, and the switch stays thrown
cast = sim.calls.count(f"dome/{N}/cast")
sim.blocks[place.switch] = OFF
leave(sim)
come_in(sim)
tick(sim, 60 * 20)
assert sim.calls.count(f"dome/{N}/cast") == cast and not sim.mobs
assert sim.fdy("state") == 2 and sim.is_block(place.switch, ON)
assert mast(sim) == 4 * D.CELLS and sim.calls.count(f"dome/{N}/solved") == 1

# the whole fight, breakers closed as soon as they trip: about 160 s
sim = new()
sim.blocks[place.switch] = ON
ticks = 0
while sim.fdy("state") != 2:
    tick(sim)
    ticks += 1
    for x in place.breakers:
        sim.blocks[x.lever] = x.block(True)
    assert ticks < 20 * 300
assert D.seconds(5) * 20 <= ticks <= D.seconds(5) * 20 + 10 * D.STEP, ticks

# duo: two trip at once, on two levels; one can close both
sim = new(players=2)
assert sim.fdy("form") == 2
sim.blocks[place.switch] = ON
for stage, pair in D.TRIP[2].items():
    until(sim, lambda: sim.fdy("stage") == stage)  # noqa: B023
    assert levers(sim) == [i not in pair for i in range(3)], (stage, levers(sim))
    assert sim.get(f"#wave{N}.cap") in (None, D.wave(5, 2, stage)["cap"])
    sim.blocks[place.breakers[pair[0]].lever] = place.breakers[pair[0]].block(True)
    tick(sim, 5 * D.STEP)
    assert sim.fdy("charge") == stage * D.QUARTER  # one closed: not enough
    sim.blocks[place.breakers[pair[1]].lever] = place.breakers[pair[1]].block(True)
    tick(sim, D.STEP)
    assert sim.fdy("charge") > stage * D.QUARTER
assert max(D.wave(5, 2, 3).values()) == D.wave(5, 2, 3)["cap"] == 10
until(sim, lambda: sim.fdy("state") == 2)
assert sim.get(f"#d{N}") == 2

# a second player arriving changes nothing until the next trip and wave
sim = new()
sim.blocks[place.switch] = ON
until(sim, lambda: sim.fdy("stage") == 1)
assert levers(sim) == [False, True, True]
before = (dict(sim.blocks), [set(m) for m in sim.mobs], sim.fdy("charge"))
sim.players = 2
sim.put(f"#occ{N}", 2)
sim.put(f"#form{N}", 2)
sim.function(f"dome/{N}/duo")
assert (dict(sim.blocks), [set(m) for m in sim.mobs], sim.fdy("charge")) == before
sim.blocks[a.lever] = a.block(True)
until(sim, lambda: sim.fdy("stage") == 2)
assert levers(sim) == [True, False, False]  # a pair: B and C
# one of two leaves with a pair out: the second closes itself, at once
sim.players = 1
sim.put(f"#occ{N}", 1)
sim.put(f"#form{N}", 1)
sim.function(f"dome/{N}/solo")
assert levers(sim) == [True, False, True] and sim.fdy("form") == 1
assert sim.fdy("state") == 1 and sim.fdy("charge") == 2 * D.QUARTER
# ... and with one out and one player, nothing is done for them
sim.function(f"dome/{N}/duo")
sim.function(f"dome/{N}/solo")
assert levers(sim) == [True, False, True]

# leaving in the fight is a checkpoint: the charge back to the last
# quarter, the breakers as they were left, the switch thrown, and on again
# 5 s after someone walks in (with C out, once it is closed)
sim.blocks[b.lever] = b.block(True)
until(sim, lambda: sim.fdy("charge") >= 2 * D.QUARTER + 2 * D.CELL)
sim.blocks[c.lever] = c.block(False)
tick(sim, D.STEP)
assert sim.mobs and mast(sim) == 4 * 8
leave(sim)
assert (sim.fdy("state"), sim.fdy("charge"), sim.fdy("stage")) == (1, 2 * D.QUARTER, 2)
assert sim.fdy("wait") == D.RESUME and levers(sim) == lamps(sim) == [True, True, False]
assert sim.is_block(place.switch, ON) and not sim.mobs and sim.get(f"#bar{N}") == 0
assert mast(sim) == 4 * 6
# (a level voted while the dome was left takes force when the fight goes on)
sim.put("#level", 1)
sim.function("difficulty/apply")
come_in(sim)
assert sim.fdy("rate") == five["rate"]  # not set up anew
tick(sim, D.RESUME - 1)
assert sim.fdy("charge") == 2 * D.QUARTER and not sim.mobs and sim.fdy("wait") == 1
tick(sim, 1 + D.STEP)
assert sim.fdy("wait") == 0 and sim.get(f"#bar{N}") == 1
assert {n: sim.fdy(n) for n in five} == D.scaled(1)
assert sim.fdy("charge") == 2 * D.QUARTER  # C is still out
sim.blocks[c.lever] = c.block(True)
tick(sim, 2 * D.STEP)
assert sim.fdy("charge") > 2 * D.QUARTER
sim.put("#level", 5)
sim.function("difficulty/apply")
sim.function(f"dome/{N}/scale")
assert not sim.mobs
until(sim, lambda: sim.mobs, D.FIRST)
# left again at once: no more is lost than the quarter in progress
leave(sim)
assert sim.fdy("charge") == 2 * D.QUARTER
come_in(sim)
until(sim, lambda: sim.fdy("stage") == 3)
assert levers(sim) == [True, True, False]  # solo again: C
# leaving a fight with a breaker tripped: it is still out for whoever comes
leave(sim)
assert levers(sim) == [True, True, False] and sim.fdy("charge") == 3 * D.QUARTER
come_in(sim)
sim.blocks[c.lever] = c.block(True)
until(sim, lambda: sim.fdy("state") == 2)
assert sim.get(f"#d{N}") == 2 and sim.calls.count(f"dome/{N}/solved") == 1

# an idle room left is put back as built; so is any room by the reset
sim = new()
sim.blocks[b.lever] = b.block(False)
tick(sim, 300)  # (the ladle is out, and has poured)
assert not all(sim.is_block(cell, D.COOL) for cell in place.pour)
leave(sim)
as_built(sim)
assert sim.fdy("form") == 1
come_in(sim, 2)
sim.blocks[place.switch] = ON
until(sim, lambda: sim.fdy("stage") == 1)
for x in (a, b):
    sim.blocks[x.lever] = x.block(True)
until(sim, lambda: sim.fdy("stage") == 2)
sim.blocks[b.lever] = b.block(True)  # (C is left out)
sim.put("#fdy.charge", 2 * D.QUARTER + D.CELL + 1)
assert sim.mobs
sim.blocks[place.lectern] = "minecraft:lectern[facing=south,has_book=false]"
tick(sim, D.STEP)
assert "Finch" in sim.blocks[place.lectern]  # a log taken is put back
assert mast(sim) and levers(sim) != [True] * 3 and sim.fdy("form") == 2
sim.function(f"dome/{N}/reset")
as_built(sim)
assert sim.fdy("form") == 2  # (the form is the core's: two are still in)
assert sim.get(f"#d{N}") == 1  # its own dome's room, not the game's progress
# the game's reset calls it, and after it an entry sets the room up anew
sim.function("reset/all")
assert sim.get(f"#d{N}") == 0
as_built(sim)

# the level's values are copied when the room is set up, not in a fight
for level in (1, 10):
    sim = new(level)
    want = D.scaled(level)
    assert {n: sim.fdy(n) for n in want} == want, level
    sim.blocks[place.switch] = ON
    until(sim, lambda: sim.mobs)
    assert alive(sim, STOKER) == D.wave(level, 1, 0)["stoker"]
    sim.put("#level", 5)
    sim.function("difficulty/apply")
    tick(sim, 5 * D.STEP)
    assert {n: sim.fdy(n) for n in want} == want, level
# every command the interpreter passed by is one that changes no state here
assert sim.passed <= {"title", "tellraw", "playsound", "particle", "bossbar", "data",
                      "effect", "attribute", "tp", "fill", "schedule", "spawnpoint",
                      "team", "clear", "tag", "item", "give", "gamemode"}, sim.passed
"""
    )
