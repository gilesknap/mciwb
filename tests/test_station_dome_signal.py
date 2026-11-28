"""
The offline tests of the Signal Room (examples/station/dome_signal.py): the
room's plan against its own checks, its stage built against the example's
fake client, its generated functions, and its state machine driven by a
small interpreter of those functions, since the fake client runs none. No
server is needed. As in test_station_example.py, each test runs in a
Python of its own, in the example's folder.
"""

import os
import subprocess
import sys
from pathlib import Path

STATION = Path(__file__).parents[1] / "examples" / "station"
# what the example reads from the environment
SETTINGS = ("STAGES", "CHECKS", "FORCE", "STATION_DATAPACKS_DIR")

# An interpreter of the function lines the room generates: scores, blocks
# and calls, with the game's rules for a score that was never set. What is
# aimed at players or entities (sounds, chat, the board's words) is only
# noted, and a function outside the room (the core's) is noted, not run.
# Redstone is not simulated: a contact is seen closed, not its lamps lit.
SIM = '''
import random
import re

import datapack
import dome_signal as D
N = D.INDEX  # the dome's place in the ring
import game
import station_layout as L


class Sim:
    def __init__(self, pack, blocks, own):
        self.f = pack.functions
        self.own = own  # the functions to run: the room's
        self.scores = {}
        self.world = {c: b.partition("{")[0] for c, b in blocks.items()}
        self.rng = random.Random(7)
        self.words = ""
        self.said = []
        self.outside = []
        for line in pack.setup_lines():
            if line.startswith("scoreboard players set"):
                self.command(line)

    def get(self, name, obj="st"):
        return self.scores.get((name, obj))

    def put(self, name, value, obj="st"):
        self.scores[name, obj] = value

    def sig(self, *names):
        got = [self.get(f"#sig.{name}") for name in names]
        return got[0] if len(got) == 1 else got

    @staticmethod
    def within(value, rng):
        lo, sep, hi = rng.partition("..")
        if not sep:
            return value == int(lo)
        return (not lo or value >= int(lo)) and (not hi or value <= int(hi))

    def is_block(self, cell, want):
        name, _, states = want.partition("[")
        have, _, has = self.world.get(cell, "minecraft:air").partition("[")
        has = has.rstrip("]").split(",")
        return name == have and all(
            s in has for s in states.rstrip("]").split(",") if s
        )

    def run(self, path):
        for line in self.f[path]:
            if self.line(line) == "return":
                return

    def line(self, line):
        w = line.split(" ")
        if w[0] != "execute":
            return self.command(line)
        i, store = 1, None
        while w[i] != "run":
            if w[i : i + 3] == ["store", "result", "score"]:
                store = (w[i + 3], w[i + 4])
                i += 5
                continue
            assert w[i] in ("if", "unless"), line
            if w[i + 1] == "score":
                a = self.get(w[i + 2], w[i + 3])
                if w[i + 4] == "matches":
                    ok, n = a is not None and self.within(a, w[i + 5]), 6
                else:
                    b = self.get(w[i + 5], w[i + 6])
                    ok, n = False, 7
                    if a is not None and b is not None:  # (unset: no match)
                        ok = {"=": a == b, "<": a < b, ">": a > b,
                              "<=": a <= b, ">=": a >= b}[w[i + 4]]
            else:
                assert w[i + 1] == "block", line
                cell = tuple(int(v) for v in w[i + 2 : i + 5])
                ok, n = self.is_block(cell, w[i + 5]), 6
            if ok != (w[i] == "if"):
                return None
            i += n
        result = self.line(" ".join(w[i + 1 :]))
        if store:
            assert isinstance(result, int), line
            self.scores[store] = result
        return result

    def command(self, line):
        w = line.split(" ")
        if w[:2] == ["scoreboard", "players"] and w[2] in ("set", "add", "remove"):
            key, n = (w[3], w[4]), int(w[5])
            old = self.scores.get(key, 0)
            self.scores[key] = {"set": n, "add": old + n, "remove": old - n}[w[2]]
        elif w[:3] == ["scoreboard", "players", "operation"]:
            key, other = (w[3], w[4]), self.scores.get((w[6], w[7]), 0)
            old = self.scores.get(key, 0)
            self.scores[key] = {
                "=": lambda: other, "+=": lambda: old + other,
                "-=": lambda: old - other, "*=": lambda: old * other,
                "/=": lambda: old // other, "%=": lambda: old % other,
            }[w[5]]()
        elif w[0] == "setblock":
            cell = tuple(int(v) for v in w[1:4])
            self.world[cell] = " ".join(w[4:]).partition("{")[0]
        elif w[0] == "function":
            name = w[1].partition(":")[2]
            if name in self.own:
                self.run(name)
            elif name != f"dome/{N}/solved":
                self.outside.append(name)
            elif self.get(f"#d{N}") == 1:  # the core's part: answered once
                self.put(f"#d{N}", 2)
                self.outside.append(name)
        elif w[0] == "return":
            return "return"
        elif w[0] == "random":
            lo, _, hi = w[2].partition("..")
            return self.rng.randint(int(lo), int(hi))
        elif w[:3] == ["data", "modify", "entity"]:
            self.words = re.search(r'text:"([^"]*)"', line).group(1)
        elif w[0] == "tellraw":
            self.said.append(re.search(r'text:"([^"]*)"', line).group(1))
        else:
            assert w[0] in ("data", "playsound"), line
        return None


dome = L.DOMES[D.INDEX]
place = D.room(dome)
fr = place.frame
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [D.MODULE])
alone = datapack.Pack(stamp="t")
alone.objectives({game.OBJ: "dummy"})
D.functions(alone)
sim = Sim(pack, D.room_blocks(dome).everything(), set(alone.functions))


def level(n):
    sim.put("#active", n)
    for name, value in game.scaled(n).items():
        sim.put(name, value)


def tick(n=1):
    for _ in range(n):
        sim.run(f"dome/{N}/tick")


def enter(first=1):
    """what the core does when a player comes in"""
    sim.put("#first", first)
    sim.run(f"dome/{N}/enter")


def form(n):
    """what the core does when the dome's form changes"""
    sim.put(f"#form{N}", n)
    if sim.get(f"#d{N}") == 1:
        sim.run(f"dome/{N}/solo" if n == 1 else f"dome/{N}/duo")


def press(what, desk=None):
    """a key of the desks as they stand, set pressed and read"""
    keys = [k for k in place.desk(sim.sig("form")) if k.what == what]
    key = next(k for k in keys if desk in (None, k.desk))
    assert sim.is_block(key.cell, D.button(fr)), key
    sim.world[key.cell] = D.button(fr, True)
    tick()
    assert sim.is_block(key.cell, D.button(fr)), key


def throw(cell, on=True):
    sim.world[cell] = D.switch(place, cell, on)
    tick()


def closed():
    return {s.k for s in place.signals if sim.is_block(s.hub, D.POWER)}


def rung():
    return {s.k for s in place.signals if sim.is_block(s.contact, D.POWER)}


def seq():
    return [sim.sig(f"s{j}") for j in range(sim.sig("n"))]


def listen():
    """a sending watched to its end: the signals as their contacts close"""
    for _ in range(D.PAUSE + 2):
        if sim.sig("st") == 2:
            break
        tick()
    assert sim.sig("st") == 2, sim.sig("st")
    sent = []
    for _ in range(400):
        if sim.sig("st") != 2:
            break
        before = closed() | rung()
        tick()
        now = closed() | rung()
        assert len(now) <= 1, now
        if now and now != before:
            sent += sorted(now)
    assert sim.sig("st") == 3 and not closed() | rung()
    assert sim.sig("tx") == D.sent(sent)
    return sent


def buttons(n):
    """are the keys of form n there, and the other form's gone?"""
    there = all(sim.is_block(k.cell, D.button(fr)) for k in place.desk(n))
    gone = all(sim.is_block(k.cell, D.AIR) for k in place.desk(3 - n))
    return there and gone


def begin(lvl=5, first=1):
    """an open, unsolved room, entered by one player"""
    level(lvl)
    sim.put(f"#d{N}", 1)
    enter(first)
    form(1)
    tick()


def power():
    throw(place.battery)
    throw(place.aerial)
    assert sim.sig("st") == 1
'''


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


def test_signal_room_plan():
    run(
        """
import domes
import dome_signal as D
N = D.INDEX  # the dome's place in the ring
import fittings
import game
import rooms
import station_layout as L
import tunnels
import verify_station as V
import build_station as B

dome = L.DOMES[D.INDEX]
assert B.STAGES[f"dome_{N}_inside"] is D.build and V.LIVE["signal_room"] is D.check
assert "signal_room" not in V.todos()
assert "stub_signal" not in {m.name for m in B.modules()}

# the room's cells: inside the dome, off the reserved cells, in both forms
assert not D.room_problems(dome)
place = D.room(dome)
fr = place.frame
inside = domes.dome_cells(dome).interior - tunnels.reserved_cells(dome)
for form in (1, 2):
    blocks = D.room_blocks(dome, form)
    assert set(blocks.above()) | blocks.clear <= inside
    assert set(blocks.floor) <= domes.dome_cells(dome).floor
    assert not set(blocks.floor) & set(domes.light_cells(dome)[0])
    assert not rooms.room_problems(dome, blocks.above(), blocks.floor)
    assert not fittings.placement_problems(dome, set(blocks.above()) | blocks.clear)
    # every lever and button is a listed input on gold with a sign, and
    # nothing redstone would work touches the block that carries it
    keys = D.inputs(dome, form)
    assert not rooms.input_problems(blocks.above(), keys, floor=blocks.floor)
x, y, z, _ = domes.entrance(dome)
assert fr.at(-(dome.radius - domes.ENTRANCE_OFFSET), 0, 1) == (x, y, z)
blocks = D.room_blocks(dome)
assert len(blocks.everything()) > 900

# the two forms differ only by where the keys are and what the signs say
solo, duo = D.room_blocks(dome, 1).everything(), D.room_blocks(dome, 2).everything()
changed = {c for c in set(solo) | set(duo) if solo.get(c) != duo.get(c)}
keys = {k.cell for k in place.keys}
assert changed == keys | set(place.status.values())
assert len(place.desk(1)) == 5 and len(place.desk(2)) == 6
assert sorted(k.what for k in place.desk(1)) == [1, 2, 3, 4, D.CALL]
port = sorted(k.what for k in place.keys if k.desk == "port")
starboard = sorted(k.what for k in place.keys if k.desk == "starboard")
assert port == [1, 2, D.CALL] and starboard == [3, 4, D.CALL]
# the wing desks are far apart, and on a level of their own
a, b = place.key(1, 2).stand, place.key(4, 2).stand
assert abs(a[0] - b[0]) + abs(a[2] - b[2]) >= 20 and a[1] == b[1]
levels = {D.walks(dome)[n][1] - dome.floor_y for n in (
    "the BATTERY SWITCH", "the operator's deck", "CALL of the port desk",
    "the catwalk", "the AERIAL SWITCH")}
assert levels == {1, D.DECK_H + 1, D.WING_H + 1, D.CAT_H + 1, D.LOFT_H + 1}

# the board: four lamps in a row, left to right as the keys are, each in
# a frame of its own colour, the same colour behind each of its keys
across = [D.fr_of(fr, s.hub)[1] for s in place.signals]
assert across == sorted(across) == list(D.LAMP_R)
main = [D.fr_of(fr, place.key(k, 1).cell)[1] for k in (1, 2, 3, 4)]
assert main == sorted(main)
for desk in ("port", "starboard"):
    row = [(D.fr_of(fr, k.cell)[1], k.what) for k in place.keys if k.desk == desk]
    assert [what for _, what in sorted(row) if what != D.CALL] == sorted(
        what for _, what in row if what != D.CALL)
for sig in place.signals:
    f, r = D.fr_of(fr, sig.hub)
    h = sig.hub[1] - dome.floor_y
    frame = {fr.at(f, r + dr, h + dh) for dr in (-1, 0, 1) for dh in (-2, -1, 0, 1, 2)}
    framed = {c for c in frame if blocks.solid[c] == sig.dark}
    assert frame - framed == {sig.hub, *sig.lamps} and len(framed) == 10
    assert all(blocks.solid[c] == f"{D.LAMP}[lit=false]" for c in sig.lamps)
    assert all(blocks.solid[c] == sig.dark for c in sig.pilots) and len(sig.pilots) == 3
    assert sig.colour in blocks.solid[sig.pane]
    # each key of the signal stands on gold, its colour behind it
    for key in (k for k in place.keys if k.what == sig.k):
        x, y, z = key.cell
        assert blocks.solid[x, y - 1, z] == D.BRASS
        kf, kr = D.fr_of(fr, key.cell)
        assert fr.at(kf + 1, kr, y - 1 - dome.floor_y) in sig.pilots
assert len({s.note for s in place.signals}) == 4 == len({s.glow for s in place.signals})

# no bulb or lamp touches a block that carries a button, or the button:
# nothing but the room's own contacts works anything
assert not D.contact_problems(dome)
sensitive = {c for c, b in blocks.everything().items()
             if any(kind in rooms.name(b) for kind in rooms.SENSITIVE)}
for form in (1, 2):
    for cell in D.inputs(dome, form):
        block = D.room_blocks(dome, form).attached[cell]
        on = rooms.carrier(cell, block)
        for dx, dy, dz in rooms.FACES:
            assert (on[0] + dx, on[1] + dy, on[2] + dz) not in sensitive, cell
            assert (cell[0] + dx, cell[1] + dy, cell[2] + dz) not in sensitive, cell

# the exchange round the puzzle: nothing of it can be worked by hand, it
# shares no cell with the puzzle, and none of it is gold
puzzle, dress = D.puzzle_blocks(dome), D.dressing_blocks(dome)
assert not set(puzzle.everything()) & set(dress.everything())
assert len(dress.everything()) > len(puzzle.everything())
for block in dress.everything().values():
    assert not rooms.is_input(block) and "gold" not in block, block
# the relay racks are the shared torch clock, with no pistons: the puzzle
# is played by ear
assert not any("piston" in b for b in blocks.everything().values())
clock = [b for b in dress.attached.values() if "redstone_wall_torch" in b]
assert len(clock) == 2 and len(dress.moving) == 2 * 13 + 15

# the walks and the sight lines, and that both checks find a fault
assert not D.walk_problems(dome) and not D.sight_problems(dome)
assert not rooms.window_problems(dome, blocks.above())
real = D.dressing_blocks
def walled(dome):
    d = real(dome)
    for r in range(-dome.radius, dome.radius + 1):
        for h in range(1, 16):
            cell = fr.at(6, r, h)
            if cell in domes.dome_cells(dome).interior:
                d.solid.setdefault(cell, D.COPPER)
    return d
D.dressing_blocks = walled
found = D.walk_problems(dome)
assert any("the way out" in p for p in found)
assert not any("the AERIAL SWITCH" in p for p in found)
found = D.sight_problems(dome)
assert any("lamp 1" in p and "the main console" in p for p in found)
assert any("LINE lamp 3" in p and "the port desk" in p for p in found)
assert D.room_problems(dome)
def stairless(dome):
    d = real(dome)
    for cell in [c for c, b in d.solid.items() if "stairs" in b]:
        del d.solid[cell]
    return d
D.dressing_blocks = stairless
found = D.walk_problems(dome)
assert any("the AERIAL SWITCH" in p for p in found)
assert any("key 1 of the main desk" in p for p in found)
assert not any("the BATTERY SWITCH" in p for p in found)
D.dressing_blocks = real
# a bulb beside a desk, a lamp beside a switch, a bulb beside a contact
real = D.puzzle_blocks
def bulbed(dome, form=1):
    b = real(dome, form)
    x, y, z = place.key(2, 1).cell
    b.solid[x, y - 1, z] = f"{D.BULB}[lit=false]"
    return b
D.puzzle_blocks = bulbed
assert any("is not on gold" in p for p in D.room_problems(dome))
def lamped(dome, form=1):
    b = real(dome, form)
    x, y, z = place.aerial
    b.solid[x, y + 2, z] = f"{D.BULB}[lit=false]"
    b.solid[x, y - 1, z] = f"{D.LAMP}[lit=false]"
    return b
D.puzzle_blocks = lamped
assert any("touches the input" in p for p in D.contact_problems(dome))
def crossed(dome, form=1):
    b = real(dome, form)
    x, y, z = place.signals[0].contact
    b.solid[x, y + 1, z] = f"{D.BULB}[lit=false]"
    return b
D.puzzle_blocks = crossed
assert any("the contact at" in p for p in D.contact_problems(dome))
D.puzzle_blocks = real
assert not D.room_problems(dome)

# the values of a level: gentle at 1, tuned at 5, hard at 10
one, five, ten = (D.scaled(level) for level in (1, 5, 10))
assert five == {"n": 9, "period": 16, "on": 8, "wait": 160, "ear": 0}
assert one == {"n": 7, "period": 19, "on": 11, "wait": 224, "ear": 0}
assert ten == {"n": 12, "period": 12, "on": 4, "wait": 80, "ear": 1}
before = D.scaled(1)
for level in game.LEVELS:
    v = D.scaled(level)
    assert D.ROUNDS <= v["n"] <= D.MAX_N and v["n"] >= before["n"]
    assert v["on"] >= 4 and v["period"] - v["on"] >= 8  # dark between two
    assert v["wait"] <= before["wait"] and v["wait"] >= 80
    before = v
assert D.sequence_problems([1, 3, 2, 4, 1]) == []
assert D.sequence_problems([1, 1, 3]) and D.sequence_problems([1, 2, 1])
assert D.sequence_problems([3, 4, 3, 1]) and D.sequence_problems([5, 1])
assert D.sent([3, 4, 2]) == 97

# the story: Finch's log, four pages at most, the canon's line, the names
assert D.LOG_AUTHOR == "O. Finch" and len(D.LOG_PAGES) <= 4
text = " ".join(D.LOG_PAGES)
assert "Chief Engineer" in text and "Marsh's hand" in text
assert "BATTERY SWITCH" in text and "AERIAL SWITCH" in text
assert "breaker" not in (text + " ".join(blocks.everything().values())).lower()
for page in D.LOG_PAGES:
    assert len(page) <= 256, len(page)
assert len(f"setblock 0 0 0 {D.logbook(fr)}".encode()) < B.MAX_COMMAND
"""
    )


def test_signal_room_build():
    run(
        """
import build_station as B
import dome_signal as D
N = D.INDEX  # the dome's place in the ring
import domes
import game
import station_layout as L
import tunnels

dome = L.DOMES[D.INDEX]
place = D.room(dome)
blocks = D.room_blocks(dome)

# the stage against the fake client: every block where the plan has it,
# the dome's shell and the pump engine left alone, the stub's bypass gone
stages = ["site", f"dome_{N}", "tunnels", f"dome_{N}_inside"]
rec = B.offline_build(stages=stages, force=False)
for cell, block in blocks.everything().items():
    assert rec.world.at(cell) == block, (cell, block)
for cell in blocks.clear:
    assert rec.world.name_at(cell) == "minecraft:air", cell
engine = tunnels.engine_cells(L.TUNNELS[D.INDEX])
assert all(rec.world.name_at(c) != "minecraft:air" for c in list(engine.values())[:9])
shell = domes.dome_cells(dome).shell
assert all(rec.world.name_at(c) != "minecraft:air" for c in shell)
post = game.stub_post(dome)
kill = f"kill @e[tag={game.stub_tag(D.INDEX)}]"
assert kill in rec.commands
for cell in post.cells:
    assert rec.world.at(cell) == blocks.everything().get(cell, "minecraft:air")
inside = domes.dome_cells(dome).interior - set(engine.values())
built = {c for c in inside if rec.world.name_at(c) != "minecraft:air"}
assert built == set(blocks.above()), sorted(built ^ set(blocks.above()))[:5]
# what it summons: the recall button's entity and the board's words, once
# each however often the stage runs
mine = [c for c in rec.commands if D.ENTITY_TAG in c and c.startswith("summon")]
assert len(mine) == 2
assert sum("minecraft:interaction" in c and D.RECALL_TAG in c for c in mine) == 1
assert sum("minecraft:text_display" in c and "NO LINE" in c for c in mine) == 1
assert f"kill @e[tag={D.ENTITY_TAG}]" in rec.commands
assert f"function station:dome/{N}/reset" in rec.commands
assert max(len(c.encode()) for c in rec.commands) <= B.MAX_COMMAND
again = B.offline_build(stages=[*stages, f"dome_{N}_inside"], force=False)
assert again.world.dump() == rec.world.dump()
# the stage refuses to build a room whose plan has a problem
real = D.room_problems
D.room_problems = lambda dome: ["a wall across the aisle"]
try:
    B.offline_build(stages=["site", f"dome_{N}_inside"], force=False)
except RuntimeError as e:
    assert "a wall across the aisle" in str(e)
else:
    raise AssertionError("built a room with a problem")
D.room_problems = real
"""
    )


def test_signal_room_pack():
    run(
        """
import re

import build_station as B
import datapack
import dome_signal as D
N = D.INDEX  # the dome's place in the ring
import game
import station_layout as L
import verify_station as V

dome = L.DOMES[D.INDEX]
place = D.room(dome)
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [D.MODULE])
# the room's own functions, apart from those the core makes for the dome
alone = datapack.Pack(stamp="t")
alone.objectives({game.OBJ: "dummy"})
D.functions(alone)
mine = alone.functions
assert all(n.startswith(f"dome/{N}/") for n in mine)
assert all(pack.functions[n] == ls for n, ls in mine.items())

# the hooks the core calls, and only those the room needs
for hook in game.HOOKS:
    assert f"dome/{N}/{hook}" in pack.functions, hook
for hook in game.MORE_HOOKS:
    assert f"dome/{N}/{hook}" not in pack.functions, hook
calls = lambda path, name: any(  # noqa: E731
    line.endswith(f"function station:{name}") for line in pack.functions[path]
)
assert calls(f"dome/{N}/entered", f"dome/{N}/enter")
assert calls("game/tick", f"dome/{N}/tick")
assert calls(f"dome/{N}/form", f"dome/{N}/solo")
assert calls(f"dome/{N}/form", f"dome/{N}/duo")
assert calls("reset/all", f"dome/{N}/reset")
assert calls(f"dome/{N}/left", f"dome/{N}/empty")
# one way to solve, and every function a line names exists
solvers = [n for n, ls in mine.items()
           if any(f"function station:dome/{N}/solved" in line for line in ls)]
assert solvers == [f"dome/{N}/tick"], solvers
assert sum(f"station:dome/{N}/solved" in line for line in mine[f"dome/{N}/tick"]) == 1
# only an open, unsolved dome whose line is open (``done``) is solved
assert mine[f"dome/{N}/tick"][0] == (
    f"execute if score #d{N} st matches 1 if score #sig.st st matches 6 "
    f"run function station:dome/{N}/solved"
)
setters = [n for n, ls in mine.items() if "scoreboard players set #sig.st st 6" in ls]
assert setters == [f"dome/{N}/done"], setters
assert not V.function_problems(B.pack_files(pack))
called = {m for ls in pack.functions.values() for line in ls
          for m in re.findall(rf"function station:(dome/{N}/[a-z0-9_./]+)", line)}
unused = set(mine) - called
assert not unused, unused
# the whole pack, with every other module, is as well formed
whole = B.new_pack("t")
assert not V.function_problems(B.pack_files(whole))
assert not V.name_problems({"pack": [l for ls in mine.values() for l in ls]})

# nothing aimed wide: players by the dome they are in, entities by tag
for name, lines in mine.items():
    for line in lines:
        assert "@p" not in line and "@r" not in line, (name, line)
        for sel in re.findall(r"@a(\\[[^\\]]*\\])?", line):
            assert "tag=st.in" in sel and f"st.dome={N}" in sel, (name, line)
        for sel in re.findall(r"@e(\\[[^\\]]*\\])?", line):
            assert "tag=st.d5" in sel, (name, line)
# no function kills or summons: the room's two entities are the build's
own = list(mine)
for name in own:
    for line in mine[name]:
        assert not re.search(r"\\b(kill|summon|tp|clear|give)\\b", line), (name, line)

# what works by itself is no part of the puzzle: no function touches a
# cell of the relay racks, and the reset leaves the recorder's tape alone
at = lambda cell: f"{cell[0]} {cell[1]} {cell[2]}"  # noqa: E731
dress = D.dressing_blocks(dome)
tape = {c for column in place.tape for c in column}
racks = [at(c) for c in dress.moving - tape]
assert len(racks) == 26
for name in own:
    for line in mine[name]:
        assert not any(f" {xyz} " in f" {line} " for xyz in racks), (name, line)
for name in ("reset", "empty", "quiet", "off", "arm", "press", "step", "power"):
    for line in mine[f"dome/{N}/{name}"]:
        assert not any(f" {at(c)} " in f" {line} " for c in tape), (name, line)
# the machinery runs whether or not there is a puzzle: before the tick's
# return for a locked dome
tick = mine[f"dome/{N}/tick"]
assert tick[1] == f"function station:dome/{N}/dress" and "return 0" in tick[2]
# ``reset`` does all that ``empty`` does
assert calls(f"dome/{N}/reset", f"dome/{N}/quiet")
assert calls(f"dome/{N}/empty", f"dome/{N}/quiet")
# a change of form is taken up by the tick alone, and not during a round
users = [n for n, ls in mine.items() if any(
    re.search(rf"function station:dome/{N}/desks(_solo|_duo)?$", l) for l in ls)]
assert sorted(users) == [f"dome/{N}/desks", f"dome/{N}/reset", f"dome/{N}/tick"], users
line = next(l for l in tick if l.endswith(f"function station:dome/{N}/desks"))
assert "unless score #sig.st st matches 2..3" in line
for hook in ("solo", "duo"):
    assert not any("setblock" in l for l in mine[f"dome/{N}/{hook}"])
# the level's values are copied when the room is armed, and read nowhere else
level = lambda line: "#diff." in line or "#active" in line  # noqa: E731
readers = {n for n, ls in mine.items() if any(level(line) for line in ls)}
want = {f"dome/{N}/scale", f"dome/{N}/enter", f"dome/{N}/hint/power/arm"}
assert readers == want, readers
# every key is read by the shared reader and let go in the same function
for key in place.keys:
    lines = mine[f"dome/{N}/{key.path}"]
    assert lines[0] == f"scoreboard players set #sig.key st {key.what}"
    assert lines[-1].startswith(f"setblock {at(key.cell)} minecraft:stone_button")
    assert "powered=false" in lines[-1]
assert len(mine) < 100 and sum(len(ls) for ls in mine.values()) < 800
"""
    )


def test_signal_room_solo():
    run(
        SIM
        + """
# -- a room never entered is as built; the first in arms it
assert sim.sig("live") is None
begin()
assert sim.sig("live", "st", "round", "len", "lvl") == [1, 0, 1, 7, 5]
assert sim.sig("form", "want") == [1, 1]
assert sim.sig(*D.scaled(5)) == list(D.scaled(5).values())
first = seq()
assert len(first) == 9 and not D.sequence_problems(first)
assert sim.words == "NO LINE" and buttons(1)

# -- no line: a key does nothing, and comes back out
press(1)
press(D.CALL)
assert sim.sig("st") == 0 and not closed() and sim.sig("calls") == 0
# either switch first: one is not enough
throw(place.aerial)
assert sim.sig("pa", "pb", "st") == [0, 1, 0] and "ONE SWITCH MORE" in sim.words
press(D.CALL)
assert sim.sig("st") == 0
throw(place.battery)
assert sim.sig("pa", "pb", "st") == [1, 1, 1] and sim.words == "READY: PRESS CALL"
# the cables light lamp by lamp, then the console's pilots
def lit(cells):
    return [sim.is_block(c, f"{D.BULB}[lit=true]") for c in cells]



assert lit(place.cable) == [False, False]
tick(D.RAMP)
assert lit(place.cable) == [True, False] and lit(place.mast) == [True, False]
tick(3 * D.RAMP)
assert all(lit(place.cable) + lit(place.mast))
assert all(sim.is_block(c, D.PILOT_ON) for c in place.power_pilots)
# the sweep turns: one bulb lit, moving on
seen = set()
for _ in range(8):
    tick(D.SWEEP)
    assert sum(lit(place.sweep)) == 1
    seen.add(tuple(lit(place.sweep)))
assert len(seen) == 8

# -- free play: a key closes its contact and lights its pilots, then lets go
for sig in place.signals:
    press(sig.k)
    assert closed() == {sig.k} and sim.sig("st") == 1
    assert all(sim.is_block(c, sig.glow) for c in sig.pilots)
    press(sig.k)  # the same key again: opened and closed, so it rings again
    assert closed() == {sig.k} and sim.sig(f"on{sig.k}") == 2
    tick(D.scaled(5)["on"])
    assert not closed() and all(sim.is_block(c, sig.dark) for c in sig.pilots)

# -- three rounds, each one longer, the same sequence
press(D.CALL)
assert sim.sig("st") == 2 and sim.words == "LISTEN: ROUND 1 OF 3"
press(2)  # a key while it sends is not an answer
assert sim.sig("st") == 2 and not closed()
for won in (1, 2, 3):
    sent = listen()
    assert sent == first[: 6 + won], (sent, first)
    assert sim.words == "ANSWER: KEY 1"
    for j, k in enumerate(sent):
        assert sim.sig("i") == j
        press(k)
        # (the last key of all starts the fanfare in the same tick)
        assert closed() == {k} or sim.sig("st") == 6
    assert sim.sig("line") == won and sim.sig("miss") == 0
    tick()
    assert lit(place.line) == [j < won for j in range(3)]
    if won < 3:
        assert sim.sig("st", "round", "len") == [4, won + 1, 7 + won]
        assert sim.words == f"RIGHT: LINE {won} OF 3"
        assert not sim.outside
# solved: the one call, the fanfare, then a quiet room whose keys play
assert sim.sig("st") == 6 and sim.words == "LINE OPEN"
assert sim.outside == [f"dome/{N}/solved"] and sim.get(f"#d{N}") == 2
ran = []
for _ in range(60):
    tick()
    ran += sorted(closed())
assert sorted(set(ran)) == [1, 2, 3, 4] and sim.sig("fan") == 0 and not closed()
press(3)
assert closed() == {3} and sim.sig("st") == 6
press(D.CALL)
assert sim.sig("st") == 6
# the line stays open: a switch thrown back is held closed
throw(place.battery, False)
assert sim.is_block(place.battery, D.switch(place, place.battery, True))
assert sim.sig("pa", "st") == [1, 6]
# everyone goes and someone comes back: nothing is armed anew, and a
# second run of the solved room cannot call ``solved`` again
sim.run(f"dome/{N}/empty")
enter(1)
tick(5)
assert sim.sig("st", "line", "live") == [6, 3, 1] and seq() == first
assert sim.outside == [f"dome/{N}/solved"] and sim.words == "LINE OPEN"

# -- reset: as built, whatever state it was in
sim.run(f"dome/{N}/on_2")
sim.run(f"dome/{N}/note_4")
sim.run(f"dome/{N}/reset")
built = D.room_blocks(dome)
tape = {c for column in place.tape for c in column}
for cell, block in built.everything().items():
    if cell not in tape:
        assert sim.world[cell] == block.partition("{")[0], (cell, sim.world[cell])
for cell in built.clear:
    assert sim.world.get(cell, D.AIR) == D.AIR
assert sim.sig("st", "live", "pa", "pb", "line") == [0, 0, 0, 0, 0]
assert sim.sig("form", "want") == [1, 1]
assert sim.words == "NO LINE"
# and through all of it no function set a block outside the room's plan
assert set(sim.world) - set(built.everything()) <= built.clear
"""
    )


def test_signal_room_failures():
    run(
        SIM
        + """
begin()
power()
first = seq()
press(D.CALL)
keys = listen()

# -- a key held, or clicked twice, is read once: not a wrong second key
press(keys[0])
press(keys[0])
assert sim.sig("st", "i", "miss") == [3, 1, 0]
# -- a wrong key: this round's presses lost, the same round sent again
wrong = next(k for k in (1, 2, 3, 4) if k not in keys[:2])
press(wrong)
assert sim.sig("st", "miss", "line") == [5, 1, 0] and "WRONG" in sim.words
assert not closed()
press(keys[0])  # a key in the pause is nothing
assert sim.sig("st", "miss") == [5, 1]
assert listen() == keys and seq() == first and sim.sig("i") == 0
# -- no key at all in time: nobody is answering, so the room waits for
# CALL (it does not send for ever to an empty desk), and it is no mistake
tick(D.WAIT - 1)
assert sim.sig("st") == 3
tick()
assert sim.sig("st", "miss") == [1, 1] and "NO ANSWER" in sim.words
press(D.CALL)
assert listen() == keys
# -- the clock run out in the middle of an answer: the same round again
press(keys[0])
tick(D.WAIT - 2)
assert sim.sig("st", "i") == [3, 1]
tick()
assert sim.sig("st", "miss") == [5, 2] and "DROPPED" in sim.words
assert listen() == keys
# each right key starts the clock again
press(keys[0])
tick(D.WAIT - 2)
assert sim.sig("st", "i") == [3, 1]
# -- CALL during an answer: said again from the start, and no mistake
calls = sim.sig("calls")
press(D.CALL)
assert sim.sig("st", "miss") == [2, 2] and sim.sig("calls") == calls + 1
assert listen() == keys and sim.sig("i") == 0
# -- three wrong answers: a hint in chat, once
press(wrong if wrong != keys[0] else keys[1])
assert sim.sig("miss") == 3
assert sum("Press CALL to hear it again" in s for s in sim.said) == 1
assert listen() == keys
for k in keys:
    press(k)
assert sim.sig("line", "round", "miss", "st") == [1, 2, 0, 4]

# -- a switch opened during a round: no line, the round lost, the lamp kept
keys = listen()
press(keys[0])
throw(place.aerial, False)
assert sim.sig("st", "line", "round", "i") == [0, 1, 2, 0] and not closed()
assert "ONE SWITCH MORE" in sim.words
tick(2)
assert not any(sim.is_block(c, f"{D.BULB}[lit=true]") for c in place.sweep)
assert sim.is_block(place.line[0], f"{D.BULB}[lit=true]")
press(D.CALL)
assert sim.sig("st") == 0
throw(place.aerial)
assert sim.sig("st", "line", "round", "len") == [1, 1, 2, 8]
press(D.CALL)
assert listen() == first[:8]

# -- everyone leaves during a round: the round is dropped, and no more
press(keys[0])
assert closed()
sim.put(f"#form{N}", 0)
sim.run(f"dome/{N}/empty")
assert sim.sig("st", "pa", "pb", "live") == [1, 1, 1, 1]
assert sim.sig("line", "round", "len") == [1, 2, 8]
assert not closed() and sim.words == "READY: PRESS CALL"
enter(1)
form(1)
tick(3)
assert seq() == first and sim.sig("line", "st") == [1, 1]
# ... in the pause after a round was won: that round is kept
press(D.CALL)
for k in listen():
    press(k)
assert sim.sig("st", "line", "round") == [4, 2, 3]
sim.run(f"dome/{N}/empty")
assert sim.sig("st", "line", "round", "len") == [1, 2, 3, 9]
# ... and with a contact closed in free play: it is opened
enter(1)
form(1)
press(1)
assert closed() == {1}
sim.run(f"dome/{N}/empty")
assert not closed() and sim.sig("st") == 1

# -- a new level takes force only for the first into an empty room
level(10)
enter(0)
assert sim.sig("lvl", "n", "line") == [5, 9, 2] and seq() == first
enter(1)
# ... the rounds still to win, at the new level: the switches and the LINE
# lamps kept (a vote never costs the rounds won)
got = sim.sig("lvl", "line", "st", "live", "round", "len", "pa", "pb")
assert got == [10, 2, 1, 1, 3, 12, 1, 1], got
assert sim.sig(*D.scaled(10)) == list(D.scaled(10).values())
assert len(seq()) == 12 and not D.sequence_problems(seq()) and seq() != first
assert sim.is_block(place.aerial, D.switch(place, place.aerial, True))
assert sim.words == "READY: PRESS CALL"
# a room set up afresh at level 10
sim.run(f"dome/{N}/reset")
enter(1)
assert sim.sig("lvl", "line", "st", "live", "round", "len") == [10, 0, 0, 1, 1, 10]
assert not sim.is_block(place.aerial, D.switch(place, place.aerial, True))
# at the highest level the first two rounds show their lamps and the
# last is sent by the bells alone: the second contacts, never the first
form(1)
power()
press(D.CALL)
for won in (1, 2):
    sim.put("#sig.ear1", 0)
    keys = listen()
    assert keys == seq()[: 9 + won] and not any(sim.sig(f"ear{k}") for k in (2, 3, 4))
    for k in keys:
        press(k)
before = {k: sim.sig(f"on{k}") for k in (1, 2, 3, 4)}
for _ in range(D.PAUSE + 2):
    tick()
assert sim.sig("st", "byear", "round") == [2, 1, 3]
heard = []
while sim.sig("st") == 2:
    tick()
    assert not closed()
    heard += sorted(rung() - set(heard[-1:]))
assert before == {k: sim.sig(f"on{k}") for k in (1, 2, 3, 4)}
assert sim.sig("tx") == D.sent(seq()) and not rung()
assert sum(sim.sig(f"ear{k}") or 0 for k in (1, 2, 3, 4)) == 12
for k in seq():  # the answer shows its lamps as ever
    press(k)
    assert closed() == {k} or sim.sig("st") == 6
tick()
assert sim.sig("st") == 6 and sim.outside == [f"dome/{N}/solved"]

# -- a room that was never set up arms itself before a key is read
sim.run(f"dome/{N}/reset")
sim.put(f"#d{N}", 1)
assert sim.sig("live") == 0
tick()
assert sim.sig("live", "len") == [1, 10]

# -- the sequence's two rules, and that it differs from run to run
level(10)
rolls = set()
for _ in range(300):
    sim.run(f"dome/{N}/roll")
    assert not D.sequence_problems(seq()) and len(seq()) == 12, seq()
    rolls.add(tuple(seq()))
assert len(rolls) > 250
firsts = {s[0] for s in rolls}
assert firsts == {1, 2, 3, 4} and sim.sig("i") == 0
for lvl in game.LEVELS:
    level(lvl)
    sim.run(f"dome/{N}/scale")
    assert sim.sig(*D.scaled(lvl)) == list(D.scaled(lvl).values()), lvl
"""
    )


def test_signal_room_forms():
    run(
        SIM
        + """
# -- two come in together: the line is split before anything is pressed
level(5)
sim.put(f"#d{N}", 1)
enter(1)
enter(0)
form(2)
assert sim.sig("want", "form") == [2, 1]
tick()
assert sim.sig("want", "form", "st") == [2, 2, 0] and buttons(2)
assert any("line is split" in s for s in sim.said)
first = seq()
power()
# a whole round on the two wing desks, CALL from either
press(D.CALL, "starboard")
keys = listen()
# the desks split: each key is allowed the walk from one wing to the other
assert sim.sig("t") == D.WAIT + D.WALK
for k in keys:
    desk = "port" if k <= 2 else "starboard"
    assert [d.desk for d in place.desk(2) if d.what == k] == [desk]
    press(k)
assert sim.sig("line", "st") == [1, 4]
# a key out of turn, from either desk, fails the round for both
keys = listen()
press(keys[0])
press(next(k for k in (1, 2, 3, 4) if k not in keys[:2]))
assert sim.sig("st", "miss", "line") == [5, 1, 1]

# -- one leaves while the other answers: the keys stay where they are
keys = listen()
press(keys[0])
form(1)
tick(5)
assert sim.sig("want", "form", "st", "i") == [1, 2, 3, 1] and buttons(2)
assert any("when this round is done" in s for s in sim.said)
for k in keys[1:]:
    press(k)
# the round is won on the desks it began on; then they change, in the pause
assert sim.sig("line", "st", "form") == [2, 4, 2]
tick()
assert sim.sig("form", "st", "line", "round") == [1, 4, 2, 3] and buttons(1)
assert any("line is whole" in s for s in sim.said)
# and the last round is answered at the main console
keys = listen()
assert keys == first

# -- a second player walks in during an answer, and out again: nothing
# moves under the first player's hands
press(keys[0])
form(2)
tick(3)
assert sim.sig("want", "form", "st", "i") == [2, 1, 3, 1] and buttons(1)
form(1)
tick(3)
assert sim.sig("want", "form", "st", "i") == [1, 1, 3, 1] and buttons(1)
# in again, and the clock runs out: the desks change in the pause, and
# the same round is sent again to the new desks
form(2)
tick(D.WAIT)
assert sim.sig("st", "form", "miss") == [5, 2, 1] and buttons(2)
assert listen() == first
# during a sending too the keys stay put
press(D.CALL, "port")
assert sim.sig("st") == 2
form(1)
tick(3)
assert sim.sig("form", "want", "st") == [2, 1, 2] and buttons(2)
keys = listen()
assert sim.sig("form") == 2 and buttons(2)
for k in keys:
    press(k)
tick()
assert sim.sig("st") == 6 and sim.outside == [f"dome/{N}/solved"]
assert sim.get(f"#d{N}") == 2

# -- solved: the core calls neither ``solo`` nor ``duo`` again, and the
# room follows who is in it by itself
tick(60)
assert sim.sig("form") == 1 and buttons(1)
form(2)
tick()
assert sim.sig("form", "st") == [2, 6] and buttons(2)
press(4)
assert closed() == {4}
sim.put(f"#form{N}", 0)
sim.run(f"dome/{N}/empty")
assert not closed() and sim.sig("st") == 6
enter(1)
sim.put(f"#form{N}", 1)
tick()
assert sim.sig("form", "st") == [1, 6] and buttons(1)

# -- the game's reset from the duo form: the solo desks, as built
form(2)
tick()
assert buttons(2)
sim.run(f"dome/{N}/reset")
assert buttons(1) and sim.sig("form", "want", "st", "live") == [1, 1, 0, 0]
built = D.room_blocks(dome)
for desk, cell in place.status.items():
    assert sim.world[cell] == built.attached[cell].partition("{")[0]
# a room armed while two are in it keeps the form the core has
sim.put(f"#d{N}", 1)
sim.put(f"#form{N}", 2)
tick()
assert sim.sig("live", "want") == [1, 2]
tick()
assert sim.sig("form") == 2 and buttons(2)
"""
    )
