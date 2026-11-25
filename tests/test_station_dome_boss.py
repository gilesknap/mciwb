"""
The Engine (dome 7) of examples/station, with no server: its room's plan
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
import dome_start
import domes
import fittings
import game
import rooms
import station_layout as L
import tunnels
import verify_station as V

dome = L.DOMES[D.INDEX]
assert dome.key == "boss" and D.PHASE_2 is False
# the module takes the stub's place: its stage, its check under the name the
# verify script lists, its trophy at the win
assert B.STAGES["dome_7_inside"] is D.build and V.LIVE["boss"] is D.check
assert "boss" not in V.todos()
assert "boss" in {m.name for m in B.modules()}
assert "stub_boss" not in {m.name for m in B.modules()}
assert D.MODULE.wins == ("dome/7/trophy",) and D.TROPHY == dome_start.TROPHY
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
    d.solid[fr.at(2, 23, 2)] = D.COPPER
    return d
D.dressing_blocks = screened
assert any("main A's deck" in p for p in D.sight_problems(dome))
D.dressing_blocks = real
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
assert [D.cap(5, 1, n) for n in range(3)] == [3, 4, 5]
assert [D.cap(5, 2, n) for n in range(3)] == [5, 6, 7]
assert D.cap(1, 1, 0) == 2 and D.cap(10, 2, 2) == 11
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
import domes
import game
import station_layout as L
import tunnels

dome = L.DOMES[D.INDEX]
blocks = D.room_blocks(dome)
place = D.room(dome)

# the stage against the fake client: every block where the plan has it, the
# dome's shell and the pump engine left alone, the same built twice
stages = ["site", "dome_7", "tunnels", "dome_7_inside"]
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
assert "function station:dome/7/reset" in rec.commands
again = B.offline_build(stages=[*stages, "dome_7_inside"], force=False)
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
print(B.STAGES["dome_7_inside"].__name__)
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
        assert f"dome/7/{hook}" in f, hook
    calls = lambda path, name: any(  # noqa: E731
        line.endswith(f"function station:{name}") for line in f[path]
    )
    assert calls("dome/7/entered", "dome/7/enter") and calls("game/tick", "dome/7/tick")
    assert calls("dome/7/form", "dome/7/solo") and calls("dome/7/form", "dome/7/duo")
    assert calls("reset/all", "dome/7/reset") and calls("dome/7/left", "dome/7/empty")
    assert calls("dome/7/exited", "dome/7/leave")
    assert calls("dome/7/respawned", "dome/7/died")
    assert calls("run/win", "dome/7/trophy")
    # the core's kit on entering, and none of the module's own
    assert calls("dome/7/entered", "kit/boss")
    mine = {n: ls for n, ls in f.items() if n.startswith("dome/7/")}
    core = {"entered", "exited", "left", "form", "respawned", "solved", "check"}
    mine = {n: ls for n, ls in mine.items() if n.split("/")[2] not in core}
    assert not any(" armor." in line for ls in mine.values() for line in ls)
    # one call of the core's solved, in ``won``
    solvers = [n for n, ls in mine.items()
               if any("function station:dome/7/solved" in line for line in ls)]
    assert solvers == ["dome/7/won"], solvers
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
    quiet = [l for l in f["dome/7/empty"] if "run function" not in l
             and not l.endswith("dome/7/signs")]
    assert quiet and all(line in f["dome/7/reset"] for line in quiet)
    assert calls("dome/7/reset", "dome/7/face/shut")
    assert all(calls("dome/7/reset", f"dome/7/main/open_{k}") for k in "abc")
    gone = "execute as @e[tag=st.mob7] run function station:mob/remove"
    assert gone in f["dome/7/reset"]
    # nothing reads, sets or kills the cylinders: no function names a cell
    # of theirs, and nothing kills by position
    machine = set()
    for m in place.cylinders:
        machine |= set(m.bed) | set(m.solid) | set(m.attached) | m.moving
    cells = {D._xyz(c) for c in machine}
    for name, lines in mine.items():
        for line in lines:
            assert not any(f" {xyz} " in f"{line} " for xyz in cells), (name, line)
            assert not line.startswith("kill"), (name, line)
    # the machinery runs whether or not there is a fight
    step = f["dome/7/step"]
    at = lambda end: next(  # noqa: E731
        i for i, l in enumerate(step) if l.endswith(end)
    )
    assert at("function station:dome/7/dress") < at("run return 0")
    # the automatons are the core's: its kinds, its dress, its team
    spawn = " ".join(f["dome/7/pour/at_0"])
    for part in ("Stoker", "Riveter", "Slag Husk", "st.automaton", "station:mob/dress",
                 "st.mob7", "st.home0", "IsBaby:0b"):
        assert part in spawn, part
    # the trophy sign goes only on the trophy wall
    sign = f["dome/7/trophy/sign"][0]
    assert sign.startswith("$give @a[tag=st.in] minecraft:bamboo_sign[")
    assert 'can_place_on={blocks:"minecraft:gilded_blackstone"}' in sign
    assert "$(level)" in sign and "$(m):$(t)$(o)" in sign

off, on = packs[False].functions, packs[True].functions
# phase 2 is in the pack only with the switch on
extra = sorted(set(on) - set(off))
assert extra and all(n.startswith(("dome/7/breach/", "dome/7/master/", "dome/7/p3",
                                   "dome/7/p4")) for n in extra), extra
assert off["dome/7/all_shut"] == ["function station:dome/7/won"]
assert on["dome/7/all_shut"] == ["function station:dome/7/breach/start"]
for name, lines in off.items():
    if name.startswith("dome/7/"):
        text = " ".join(lines)
        assert "ravager" not in text and "damage @s" not in text, name
# the pair: summoned here with the core's rules, on the automatons' team,
# and not swept by the core as automatons are
summon = D.master_summon(place.spot)
assert summon in on["dome/7/master/out"]
assert summon.count('Team:"st.automaton"') == 2 and summon.count("station:empty") == 2
assert summon.count("PersistenceRequired:1b") == 2 and "Passengers:[{id:" in summon
assert "st.mob" not in summon and len(summon.encode()) < B.MAX_COMMAND
D.PHASE_2 = False
"""
    )


#: a small interpreter of the commands the Engine's functions use, over the
#: fake client's world: scores, blocks, entities with tags and places. A
#: command it does not know is an error, so nothing is passed over unseen.
SIM = r'''
import re

IGNORED = ("particle", "playsound", "title", "tellraw", "bossbar", "attribute",
           "give", "damage", "spawnpoint", "item")


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
        """a stand-in in dome 7, standing in a cell"""
        e = self.add("minecraft:armor_stand", (0, 0, 0), {"st.standin", "st.in", tag})
        e["scores"]["st.dome"] = 7
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
            for tags in re.findall(r"Tags:\[([^\]]*)\]", nbt):
                rider = re.search(r'id:"([^"]+)",Tags:\[' + re.escape(tags), nbt)
                e = self.add(rider.group(1) if rider and not first else kind,
                             (float(x), float(y), float(z)),
                             set(tags.replace('"', "").split(",")),
                             team=team.group(1) if team else None, health=1, nbt=nbt)
                first = False
            return 1
        if word == "tp":
            selector, tail = split_selector(rest)
            if "~" not in tail:
                for e in self.select(selector, me):
                    e["pos"] = tuple(float(v) for v in tail.split(" ")[:3])
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
            elif rest.startswith("modify entity"):
                self.said.append(("entity", rest))
            else:
                raise ValueError(line)
            return None
        if word == "difficulty":
            return self.difficulty
        if word == "team":
            return None
        if word in IGNORED:
            if word in ("tellraw", "title"):
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
import game
import station_layout as L

D.PHASE_2 = {phase_2}
dome = L.DOMES[D.INDEX]
place = D.room(dome)
a, b, c = place.mains
stages = ["site", "dome_7", "tunnels", "dome_7_inside"]
rec = B.offline_build(stages=stages, force=False)
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [D.MODULE])
sim = Sim(pack, rec.world)
LIT = (D.BULB + "[lit=true]", D.GREEN_BULB + "[lit=true]")


def steps(n=1):
    for _ in range(n * D.STEP):
        # (the core's count of who is in the dome)
        sim.scores["#occ7", "st"] = len(sim.select("@e[tag=st.standin]", None))
        sim.run("dome/7/tick")


def throw(main, on=True):
    sim.world.setblock(main.lever, main.lever_on if on else main.lever_off)


def lamps(cells):
    return sum(any(sim.is_block(x, kind) for kind in LIT) for x in cells)


def mobs():
    return [e for e in sim.entities if "st.mob7" in e["tags"]]


def enter(tag, cell, first=1):
    sim.scores["#first", "st"] = first
    e = sim.player(tag, cell)
    sim.run("dome/7/enter", e)
    return e


def leave_all():
    for e in [e for e in sim.entities if "st.standin" in e["tags"]]:
        sim.run("dome/7/leave", e)
        sim.entities.remove(e)
    sim.entities[:] = [e for e in sim.entities if "st.mob7" not in e["tags"]]
    sim.run("dome/7/empty")


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


entrance = D.domes.entrance(dome)[:3]
sim.scores["#d7", "st"] = 1
sim.run("dome/7/reset")
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
# on the deck it winds: a lamp every 3 s at level 5
sim.move(p, a.stand)
steps(6)
assert sim.b7("ga") == D.LAMP and lamps(a.gauge) == 1
steps(6)
assert sim.b7("ga") == 2 * D.LAMP and lamps(a.gauge) == 2
# its telltales blink while it winds; the others' stay lit
seen = set()
for _ in range(4):
    steps(1)
    seen.add(lamps(a.telltales))
    assert lamps(b.telltales) == 4 and lamps(c.telltales) == 4
assert seen == {0, 4}
# off the deck it runs down a lamp every 2 s; back on, up from where it is
sim.put("ga", 3 * D.LAMP)
sim.move(p, place.back)
steps(4)
assert sim.b7("ga") == 2 * D.LAMP and lamps(a.gauge) == 2
sim.move(p, a.stand)
steps(1)
assert sim.b7("ga") == 2 * D.LAMP + D.WIND
# the lever put back: down again, never under nothing
throw(a, False)
steps(40)
assert sim.b7("ga") == 0 and lamps(a.gauge) == 0 and sim.b7("la") == 0
# held to the fifth lamp it is shut for good
throw(a)
steps(D.FULL // D.WIND)
assert (sim.b7("la"), sim.b7("shut"), sim.b7("ga")) == (1, 1, D.FULL)
assert sim.is_block(a.lever, "minecraft:air")
assert all(sim.is_block(x, D.GREEN_BULB + "[lit=true]") for x in a.gauge)
assert lamps(a.telltales) == 0 and lamps(b.telltales) == 4
assert any(cell == a.sign and "SHUT" in nbt for cell, nbt in sim.said)
assert sim.get("#d7") == 1
steps(4)
assert sim.b7("ga") == D.FULL  # a shut main does not drain

# ---- the automatons: one at a time, up to the cap, and no further
sim.move(p, place.back)
limit = D.cap(5, 1, 1)
steps(60)
assert len(mobs()) == limit == sim.b7("cap"), (len(mobs()), limit)
assert all(e["team"] == "st.automaton" and "st.new" not in e["tags"] for e in mobs())
assert all(e["health"] >= 20 for e in mobs())
# they come from more than one hatch, each with a player in reach
homes = {t for e in mobs() for t in e["tags"] if t.startswith("st.home")}
assert len(homes) >= 2
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
"""

END_PHASE_1 = (
    SOLO
    + """
# ---- the third main is the win: the one call of the core's solved
sim.move(p, c.stand)
throw(c)
steps(D.FULL // D.WIND - 1)
assert sim.b7("phase") == 1 and sim.get("#d7") == 1
steps(2)
assert sim.b7("phase") == 5 and sim.get("#d7") == 2 and sim.get("#run") == 2
assert sim.called.count("dome/7/won") == 1 and "tunnel/7/open" in sim.called
assert not mobs()
# the trophy: named with the level and the time
assert sim.called.count("dome/7/trophy") == 1
args = next(args for path, args in sim.said if path == "dome/7/trophy/sign")
assert set(args) == {"level", "m", "t", "o"}
# the Engine stops: eyes out, the governor run down, the way out lit
assert lamps(place.eyes) == 0
steps(len(place.way_out) + 2)
assert lamps(place.way_out) == len(place.way_out) and sim.b7("spin") == 0
# nothing more happens, and nothing solves it twice
steps(20)
assert sim.called.count("dome/7/won") == 1 and not mobs()
# a second entry into the solved room changes nothing
leave_all()
p = enter("p1", entrance)
steps(4)
assert sim.b7("phase") == 5 and lamps(place.way_out) == len(place.way_out)

# ---- reset: everything as built
sim.run("dome/7/reset")
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
sim.run("dome/7/reset")
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
sim.run("dome/7/duo")  # the core's hook: two in the dome
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
sim.run("dome/7/reset")
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
sim.run("dome/7/reset")
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
sim.run("dome/7/leave", q)
sim.entities.remove(q)
steps(D.SOLO_STEPS - 2)
assert sim.b7("form") == 2 and sim.b7("ga") == part  # held, not lost
steps(4)
assert sim.b7("form") == 1 and sim.b7("ga") > part and sim.b7("gb") < part
# a partner who dies is out of the arena (the core calls ``died`` at the
# entrance, in the pavilion)
p["tags"].add(D.ARENA)
sim.run("dome/7/died", p)
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
sim.run("dome/7/reset")
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

# ---- the third main starts the breach: no win yet
sim.move(p, place.porch[0])
q = sim.player("p2", c.stand)
throw(c)
steps(D.FULL // D.WIND + 1)
assert sim.b7("phase") == 2 and sim.get("#d7") == 1 and not mobs()
assert "dome/7/won" not in sim.called
# one standing in the porch is put back from the doors
assert p["pos"][0] == place.back[0] + 0.5
# the doors are forced from the middle outwards
order = [gone()]
for _ in range(D.BREACH[-1] + 1):
    steps(1)
    if gone() != order[-1]:
        order.append(gone())
assert order == [[False] * 3, [True, False, False], [True, True, False], [True] * 3]
# the pair comes out: a ravager with the Master on it, on the team
assert sim.b7("phase") == 3 and len(pair()) == 2
kinds = sorted(e["type"] for e in pair())
assert kinds == ["minecraft:ravager", "minecraft:vindicator"]
assert all(e["team"] == "st.automaton" and "st.mob7" not in e["tags"] for e in pair())
# health for two in the dome: 170%
full = (D.RAVAGER_HP + D.MASTER_HP) * D.TWO_PLAYERS // 100
assert sim.b7("hmax") == full and sim.b7("hsum") == full
# lost inside five seconds: out again, and no win
for e in pair():
    sim.entities.remove(e)
steps(1)
assert sim.b7("phase") == 3 and len(pair()) == 2 and sim.get("#d7") == 1
steps(D.EARLY + 2)
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
p = enter("p1", entrance, first=1)
steps(D.ROAR + 4)
assert sim.b7("phase") == 4 and not pair()  # in the pavilion: he waits
assert sim.b7("shut") == 3 and sim.b7("rate") == D.WIND  # and nothing is set up anew
sim.move(p, place.back)
steps(D.ROAR + 1)
assert sim.b7("phase") == 3 and len(pair()) == 2
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
assert sim.b7("phase") == 5 and sim.get("#d7") == 2 and sim.get("#run") == 2
assert sim.called.count("dome/7/won") == 1 and "tunnel/7/open" in sim.called
assert sim.called.count("dome/7/trophy") == 1
steps(len(place.way_out) + 2)
assert lamps(place.way_out) == len(place.way_out) and lamps(place.eyes) == 0

# ---- reset: the doors shut again, the firebox empty
sim.run("dome/7/reset")
as_built("reset after the Master")

# ---- emptied in the breach itself: phase 4, the doors open
leave_all()
sim.scores["#d7", "st"] = 1  # (the game's reset opens the dome again)
p2 = enter("p1", entrance)
for name in ("la", "lb"):
    sim.put(name, 1)
sim.put("shut", 2)
sim.move(p2, c.stand)
throw(c)
steps(D.FULL // D.WIND + 3)
assert sim.b7("phase") == 2
leave_all()
assert sim.b7("phase") == 4 and gone() == [True] * 3 and not pair()

# ---- the escort, from level 6: an automaton or two beside him
leave_all()
sim.run("dome/7/reset")
sim.scores["#level", "st"] = 8
sim.run("difficulty/apply")
p3 = enter("p1", entrance)
assert sim.b7("hp") == D.scaled(8)["hp"] >= D.ESCORT_FROM
for name in ("la", "lb", "lc"):
    sim.put(name, 1)
sim.put("shut", 3)
sim.put("phase", 2)
sim.move(p3, place.back)
steps(D.BREACH[-1] + 2)
assert sim.b7("phase") == 3 and sim.b7("esc") == 1
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
        sim.stubs["station:tunnel/7/open"] = self.opened

    def opened(self, me, args):
        sim.scores["#t7", "st"] = 2
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
            if e["scores"].get("st.dome") == 7 and not self.inside(e):
                e["scores"]["st.dome"] = -1
                sim.run("dome/7/leave", e)
        for e in stands:
            if self.inside(e) and e["scores"].get("st.dome") != 7:
                e["scores"]["st.dome"] = 7
                sim.run("difficulty/apply")
                sim.scores["#first", "st"] = 0 if st["was"] else 1
                st["was"] = 1
                sim.run("dome/7/enter", e)
        occ = sum(e["scores"].get("st.dome") == 7 for e in stands)
        sim.scores["#occ7", "st"] = occ
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
        if occ and sim.get("#d7") == 1 and st["shown"] != st["form"]:
            st["shown"] = st["form"]
            sim.run("dome/7/solo" if st["form"] == 1 else "dome/7/duo")
        if occ:
            st["gone"] = 0
        elif st["was"]:
            st["gone"] += 1
        if st["gone"] >= game.EMPTY_AFTER:
            st.update(was=0, form=0, shown=0, grace=0, gone=0)
            for e in mobs():
                sim.drop(e)
            sim.run("dome/7/empty")
        if occ:
            st["was"] = 1
        sim.scores["#form7", "st"] = st["form"]

    def advance(self, ticks):
        for _ in range(ticks):
            self.t += 1
            if self.t % game.SCAN_TICKS == 0:
                self.scan()
            if sim.get("#occ7"):
                sim.run("dome/7/tick")

    def cmd(self, command, expect=None):
        if command.startswith("bossbar get"):
            shown = sim.get("#bar7") == 1
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

    def function(self, path, args=""):
        if path == "tunnel/7/reset":
            sim.scores["#t7", "st"] = 0
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
        return {"Passengers": e.get("nbt", ""), "active_effects": effects}[path]


for command in rec.commands:  # what the build summoned
    if command.startswith("summon"):
        sim.command(command, None)
domes.check_shell = lambda ctx, dome, empty=True: []
tunnels.counts = lambda ctx, tunnel: tunnels.expected(tunnel, 0)
sim.scores["#t7", "st"] = 0
sim.scores["#run", "st"] = 1
sim.scores["#solved", "st"] = 6
ctx = Ctx()
problems = D.check(ctx)
# (nothing moves the cylinders' pistons here: real redstone does)
real = [p for p in problems if "cylinders stood still" not in p]
assert not real, real
assert len(problems) == 2, problems
# it leaves the game as it found it, and no stand-in behind
assert sim.get("#run") == 1 and sim.get("#solved") == 6 and sim.get("#d7") == 1
assert not sim.select("@e[tag=st.standin]", None) and not mobs()
print(ctx.t)
"""


def test_station_boss_live_check_logic():
    for phase_2 in (False, True):
        out = run(state_machine(phase_2, LIVE))
        assert int(out.split()[-1]) > 3000  # ticks: it was worked, not skipped
