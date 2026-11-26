"""
The Flooded Dome (examples/station/dome_flooded.py) with no server: its
plan and the checks of it, its build against the example's fake client,
its datapack functions, and the functions run in a small simulation of the
game's commands, in which its live check is worked from end to end. As in
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
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


# A simulation of the commands the room's functions are made of (scores,
# setblock, fill, execute if/unless/store/positioned, function, schedule,
# summon, kill, tp) over the fake world's blocks, and of what the core does
# for one dome (who is in it, its hooks, its tick). It is not the game: no
# water runs, no redstone works, nothing is aimed at a player.
SIM = r'''
import math
import re
import sys

sys.path.insert(0, ".")
import build_station as B
import datapack
import dome_flooded as D
import domes
import game
import station_layout as L

DEFAULTS = {
    "level": "0",
    "waterlogged": "false",
    "has_book": "false",
    "lit": "false",
    "powered": "false",
    "extended": "false",
}
OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "=": lambda a, b: a == b,
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
}
REPLACEABLE = ("minecraft:air", "minecraft:water")


def parts(block):
    name, _, rest = block.partition("{")[0].partition("[")
    states = dict(kv.split("=") for kv in rest.rstrip("]").split(",") if kv)
    return (
        name if ":" in name or name.startswith("#") else "minecraft:" + name
    ), states


def in_range(value, text):
    lo, sep, hi = text.partition("..")
    if not sep:
        return value == int(lo)
    return (not lo or value >= int(lo)) and (not hi or value <= int(hi))


class Return(Exception):
    pass


class Sim:
    """the pack's functions run against the fake world: the commands a
    room's logic is made of, and nothing of what players see"""

    def __init__(self, pack, world):
        self.f, self.world = pack.functions, world
        self.s, self.ents, self.queue, self.other = {}, [], [], []
        self.time = 0
        self.words = {}
        for line in pack.setup_lines():
            self.line(line)

    # -- blocks
    def is_block(self, pos, block):
        have, hs = parts(self.world.at(pos) or "minecraft:air")
        want, ws = parts(block)
        if want == "#minecraft:pressure_plates":
            ok = "pressure_plate" in have
        elif want == "#minecraft:replaceable":
            ok = have in REPLACEABLE
        else:
            ok = have == want
        return ok and all(hs.get(k, DEFAULTS.get(k)) == v for k, v in ws.items())

    def wet(self, pos):
        block = self.world.at(pos)
        return block.startswith("minecraft:water") or "waterlogged=true" in block

    # -- entities
    def select(self, selector):
        m = re.match(r"@(\w)(?:\[(.*)\])?$", selector)
        if m.group(1) != "e":
            return []  # nobody is online
        args = {}
        tags = []
        for part in re.split(r",(?![^{]*\})", m.group(2) or ""):
            key, _, value = part.partition("=")
            (tags.append(value) if key == "tag" else args.__setitem__(key, value))
        if "scores" in args or "nbt" in args:
            return []
        found = []
        for e in self.ents:
            x, y, z = e["pos"]
            if "type" in args and e["type"] != args["type"]:
                continue
            if any(
                (t[1:] in e["tags"]) if t[0] == "!" else (t not in e["tags"])
                for t in tags
            ):
                continue
            if "dx" in args:
                lo = [float(args[k]) for k in "xyz"]
                hi = [a + float(args[k]) + 1 for a, k in zip(lo, ("dx", "dy", "dz"))]
                if not all(a <= v < b for a, v, b in zip(lo, (x, y, z), hi)):
                    continue
            if "distance" in args:
                centre = [float(args[k]) for k in "xyz"]
                if math.dist(centre, (x, y, z)) > float(args["distance"].lstrip(".")):
                    continue
            found.append(e)
        return found[: int(args["limit"])] if "limit" in args else found

    # -- commands
    def xyz(self, toks, at):
        return tuple(
            at[i] + int(t[1:] or 0) if t.startswith("~") else math.floor(float(t))
            for i, t in enumerate(toks)
        )

    def run(self, path, at=None):
        try:
            for line in self.f[path]:
                self.line(line, at)
        except Return:
            pass
        return 1

    def line(self, line, at=None):
        w = self.words.get(line)
        if w is None:
            w = self.words[line] = line.split(" ")
        c = w[0]
        if c == "execute":
            return self.execute(w, 1, at)
        if c == "function":
            return self.run(w[1].split(":", 1)[1], at)
        if c == "scoreboard":
            return self.scoreboard(w)
        if c == "setblock":
            self.world.setblock(self.xyz(w[1:4], at), " ".join(w[4:]))
        elif c == "fill":
            keep = w[9] if len(w) > 9 and w[8] == "replace" else None
            self.world.fill(
                self.xyz(w[1:4], at), self.xyz(w[4:7], at), w[7], None, keep
            )
        elif c == "return":
            if w[1] == "run":
                self.line(" ".join(w[2:]), at)
            raise Return
        elif c == "schedule":
            path = w[2].split(":", 1)[1]
            self.queue = [q for q in self.queue if q[1] != path]
            if w[1] == "function":
                self.queue.append((self.time + int(w[3].rstrip("t")), path))
        elif c == "summon":
            tags = re.search(r"Tags:\[([^\]]*)\]", line)
            self.ents.append(
                {
                    "type": w[1],
                    "pos": tuple(float(v) for v in w[2:5]),
                    "tags": set(re.findall(r'"([^"]+)"', tags.group(1)))
                    if tags
                    else set(),
                }
            )
        elif c == "kill":
            gone = self.select(w[1])
            self.ents = [e for e in self.ents if not any(e is g for g in gone)]
        elif c == "tp":
            for e in self.select(w[1]):
                e["pos"] = tuple(float(v) for v in w[2:5])
        else:
            self.other.append(line)
        return 1

    def execute(self, w, i, at):
        store = count = None
        while i < len(w):
            k = w[i]
            if k == "run":
                result = self.line(" ".join(w[i + 1 :]), at)
                if store:
                    self.s[store] = result or 0
                return True
            if k == "positioned":
                at = self.xyz(w[i + 1 : i + 4], at)
                i += 4
            elif k in ("as", "at", "on"):
                # (commands aimed at players: nobody is online)
                if k == "on" or not self.select(w[i + 1]) and w[i + 1] != "@s":
                    return False
                i += 2
            elif k == "in":
                i += 2
            elif k == "store" and w[i + 2] == "score":
                store = (w[i + 3], w[i + 4])
                i += 5
            elif k == "store":
                i += 7  # (into storage: not kept)
            elif k in ("if", "unless"):
                kind = w[i + 1]
                if kind == "score":
                    a = self.s.get((w[i + 2], w[i + 3]))
                    if w[i + 4] == "matches":
                        ok = a is not None and in_range(a, w[i + 5])
                        i += 6
                    else:
                        b = self.s.get((w[i + 5], w[i + 6]))
                        ok = a is not None and b is not None and OPS[w[i + 4]](a, b)
                        i += 7
                elif kind == "block":
                    ok = self.is_block(self.xyz(w[i + 2 : i + 5], at), w[i + 5])
                    i += 6
                elif kind == "entity":
                    count = len(self.select(w[i + 2]))
                    ok = count > 0
                    i += 3
                elif kind == "predicate":
                    ok = "light" in w[i + 2] or self.wet(at)
                    i += 3
                else:
                    raise ValueError(" ".join(w))
                if ok != (k == "if"):
                    if store:
                        self.s[store] = 0
                    return False
            else:
                raise ValueError(" ".join(w))
        if store:
            self.s[store] = count if count is not None else 1
        return True

    def scoreboard(self, w):
        if w[1] != "players":
            return 1
        key = (w[3], w[4]) if len(w) > 4 else None
        if w[2] == "set":
            self.s[key] = int(w[5])
        elif w[2] in ("add", "remove"):
            self.s[key] = self.s.get(key, 0) + int(w[5]) * (1 if w[2] == "add" else -1)
        elif w[2] == "operation":
            a, b = self.s.get(key, 0), self.s.get((w[6], w[7]), 0)
            self.s[key] = {
                "=": b,
                "+=": a + b,
                "-=": a - b,
                "*=": a * b,
                "/=": a // b if b else a,
                "<": min(a, b),
                ">": max(a, b),
            }[w[5]]
        return self.s.get(key, 0)


class Ctx:
    """
    What a live check is given, over the simulation in place of a server:
    the build's context as far as dome 3's check uses it. ``advance`` runs
    the game's ticks as the core would for this one dome: who is in it (the
    stand-ins, by where they are), its hooks (enter with #first, solo, duo,
    empty) at the core's times, its tick, scheduled functions; and a plate
    is down while a stand-in is in its cell. No redstone runs.
    """

    def __init__(self, sim, dome):
        self.sim, self.dome, self.layout, self.pack = sim, dome, L, None
        self.n = dome.index
        self.inside = set()  # the stand-ins the core has in the dome
        self.plates = [s.plate for s in D.room(dome).sluices]

    def cmd(self, command, expect=None):
        self.sim.line(command)
        return ""

    def setblock(self, pos, block):
        self.sim.world.setblock(pos, block)

    def function(self, path, args=""):
        self.sim.run(path)

    def test(self, command):
        return bool(self.sim.execute(command.split(" "), 1, None))

    def is_block(self, pos, block):
        return self.sim.is_block(pos, block)

    def count(self, selector):
        return len(self.sim.select(selector))

    def score(self, name, objective="st"):
        return self.sim.s.get((name, objective))

    def set_score(self, name, value, objective="st"):
        self.sim.s[name, objective] = value

    def data(self, what):
        w = what.split(" ")
        return (
            self.sim.world.at(tuple(int(v) for v in w[1:4])) if w[0] == "block" else ""
        )

    def advance(self, ticks):
        for _ in range(ticks):
            self.tick()

    def score_(self, name):
        return self.sim.s.get((name, "st"), 0)

    def scan(self):
        sim, n = self.sim, self.n
        x, y, z = self.dome.floor_centre
        here = f"x={x + 0.5},y={y},z={z + 0.5},distance=..{self.dome.radius + 1}"
        assert here == domes.sphere(self.dome)
        stands = sim.select(f"@e[tag={game.STANDIN}]")
        for e in stands:
            e["tags"].add("st.in")
        now = {id(e) for e in sim.select(f"@e[tag={game.STANDIN},{here}]")}
        sim.s["#players", "st"] = len(stands)
        for e in stands:  # the comers-in (nothing here has a leave hook)
            if id(e) in now and id(e) not in self.inside:
                sim.run("difficulty/apply")
                sim.s["#first", "st"] = 0 if self.score_(f"#was{n}") == 1 else 1
                sim.s[f"#was{n}", "st"] = 1
                sim.run(f"dome/{n}/enter")
        self.inside = now
        occ = len(now)
        sim.s[f"#occ{n}", "st"] = occ
        form, grace = self.score_(f"#form{n}"), self.score_(f"#grace{n}")
        if occ >= 2:
            form, grace = 2, 0
        if occ == 1 and form == 2:
            grace += 1
        if occ == 1 and form != 2:
            form = 1
        if grace >= game.SOLO_AFTER:
            form = 1
        if form == 1:
            grace = 0
        sim.s[f"#form{n}", "st"], sim.s[f"#grace{n}", "st"] = form, grace
        if occ and self.score_(f"#d{n}") == 1 and self.score_(f"#shown{n}") != form:
            sim.s[f"#shown{n}", "st"] = form
            sim.run(f"dome/{n}/{'solo' if form == 1 else 'duo'}")
        gone = self.score_(f"#gone{n}")
        if occ:
            gone = 0
        elif self.score_(f"#was{n}") == 1:
            gone += 1
        sim.s[f"#gone{n}", "st"] = gone
        if gone >= game.EMPTY_AFTER:
            for name in ("was", "form", "shown", "grace", "gone"):
                sim.s[f"#{name}{n}", "st"] = 0
            sim.run(f"dome/{n}/empty")
        if occ:
            sim.s[f"#was{n}", "st"] = 1

    def tick(self):
        sim = self.sim
        sim.time += 1
        due = [q for q in sim.queue if q[0] <= sim.time]
        sim.queue = [q for q in sim.queue if q[0] > sim.time]
        for _, path in due:
            sim.run(path)
        feet = {
            tuple(math.floor(v) for v in e["pos"])
            for e in sim.select(f"@e[tag={game.STANDIN}]")
        }
        for cell in self.plates:
            if "pressure_plate" in sim.world.at(cell):
                down = "true" if cell in feet else "false"
                sim.world.setblock(cell, f"{D.PLATE}[powered={down}]")
        sim.s["#scan", "st"] = self.score_("#scan") + 1
        if self.score_("#scan") >= game.SCAN_TICKS:
            sim.s["#scan", "st"] = 0
            self.scan()
        if self.score_(f"#occ{self.n}") >= 1:
            sim.run(f"dome/{self.n}/tick")
        sim.run(f"dome/{self.n}/guard")  # (its own entry in the tick tag)
        sim.run("tunnel/tick")  # the core's: a pump lever pulled


def simulated():
    """the dome built against the fake client, the game's pack, and the
    two together"""
    dome = L.DOMES[D.INDEX]
    rec = B.offline_build(
        stages=["site", "dome_3", "tunnels", "dome_3_inside"], force=False
    )
    pack = B.new_pack("t")
    sim = Sim(pack, rec.world)
    for command in rec.commands:
        if command.startswith("summon"):
            sim.line(command)
    sim.run("game/load")
    x, _, z = dome.floor_centre
    rec.world.setblock((x, dome.top_y + 1, z), D.WATER)  # the sea over the dome
    return dome, rec, pack, sim
'''


def test_station_flooded_plan():
    run(
        r"""
import build_station as B
import dome_flooded as D
import domes
import game
import rooms
import station_layout as L
import tunnels
import verify_station as V

dome = L.DOMES[D.INDEX]
assert B.STAGES["dome_3_inside"] is D.build and V.LIVE["flooded_dome"] is D.check
assert "flooded_dome" not in V.todos()

# the plan: nothing wrong with it; its cells inside the dome and off the
# reserved cells, the same room in the dome's own frame
assert not D.room_problems(dome)
b = D.room_blocks(dome)
place = D.room(dome)
cells = domes.dome_cells(dome)
gates = {c for s in place.sluices for c in s.gate}
used = set(b.above()) | b.clear | b.swept | set(place.door) | gates
assert used <= cells.interior and not used & tunnels.reserved_cells(dome)
assert set(b.floor) <= cells.floor
fr = D.frame(dome)
assert fr.at(0, 0, 0) == dome.floor_centre
x, y, z, _ = domes.entrance(dome)
assert fr.at(-(dome.radius - domes.ENTRANCE_OFFSET), 0, 1) == (x, y, z)
assert D.fr_of(fr, fr.at(-4, 9, 3)) == (-4, 9, 3)

# the basin is registered with the core as wet on purpose and the dam as a
# named exception: the core's wet check counts the hall and everything
# over the water, and none of the basin
basin = D.basin(dome)
assert domes.WET_OK[D.INDEX] == basin and "the dam" in domes.ALLOWED[D.INDEX]
assert not rooms.window_problems(dome, D.plan(dome))
hall, deep = fr.at(D.DAM_F - 1, 0, 1), fr.at(D.DAM_F + 1, 0, 1)
over = fr.at(0, 10, D.TOP + 1)
assert deep in basin and fr.at(0, 10, D.TOP) in basin
assert hall not in basin and over not in basin
core = {
    (x, lo[1], lo[2])
    for part in domes.check_parts(dome)
    for lo, hi in part
    for x in range(lo[0], hi[0] + 1)
}
assert not core & basin and {hall, over} <= core

# the water by layers: every cell of the basin is water, a fitting that
# says whether it is waterlogged, a gate's, or a full block; the pump
# engine's rod is a fitting and its two empty cells are water
layers = D.layers(dome)
assert sorted(layers) == list(range(1, D.TOP + 1))
water = sum(len(layer.open) for layer in layers.values())
assert 12000 < water < 15000 and D.expected(dome)["water"] == water
engine = tunnels.engine_cells(L.TUNNELS[D.INDEX])
assert engine[1, 3] in layers[4].fittings
assert {engine[0, 3], engine[2, 3]} <= layers[4].open
for layer in layers.values():
    for block in layer.fittings.values():
        assert D.DRY in block and D.holds_water(block), block
    assert "waterlogged=true" in D.wet(next(iter(layer.fittings.values())))
    for a_, b_ in domes.boxes(layer.open):
        assert {
            (x, y, z)
            for x in range(a_[0], b_[0] + 1)
            for y in range(a_[1], b_[1] + 1)
            for z in range(a_[2], b_[2] + 1)
        } <= layer.open
assert not any(D.holds_water(blk) for c, blk in b.solid.items() if c in basin)
count = D.expected(dome, D.State(w=7, stage=1))
assert count["water"] == sum(len(layers[h].open) for h in range(1, 8))
# (stage B's lever, plate cell's sign and pump lever stand in what was water)
assert count["air"] == water - count["water"] - 4 and count["under"] == 0
assert D.expected(dome, D.SOLVED)["water"] == D.expected(dome, D.SOLVED)["fit"] == 0

# three stages, top to bottom; each input stands on brass, above the water
# that uncovers it, and the handle is never where the pump is
a, bb, c = place.sluices
assert [s.start for s in place.sluices] == list(D.STARTS) == [11, 7, 3]
assert [s.target for s in place.sluices] == list(D.TARGETS) == [7, 3, 0]
for s in place.sluices:
    for cell in (s.lever, s.plate, s.sign, s.pump, s.pump_sign):
        assert D.fr_of(fr, cell)[2] > s.start
    assert abs(s.plate[0] - s.pump[0]) + abs(s.plate[2] - s.pump[2]) >= 8
    assert len(s.line) == D.LINE and s.plate != s.lever
    under = (s.plate[0], s.plate[1] - 1, s.plate[2])
    assert b.solid[under] == b.solid[s.pump_brass] == D.BRASS
    assert all(cell not in b.solid and cell not in b.parts for cell in s.gate)
    assert not D.inner_cells(dome, s) - set(s.gate) & set(s.gate)
assert not set(a.gate) & basin and set(bb.gate) | set(c.gate) <= basin
# what stands in a state: nothing of a stage still under water, a finished
# stage's levers thrown, the live control a lever or a plate
assert set(D.fixtures(dome, D.START)) == {a.lever, a.sign, a.pump, a.pump_sign}
duo = D.fixtures(dome, D.State(form=2))
assert duo[a.plate] == D.PLATE and a.lever not in duo and "Swap next" in duo[a.sign]
later = D.fixtures(dome, D.State(w=7, stage=1, form=2))
assert "powered=true" in later[a.lever] and "powered=true" in later[a.pump]
assert later[bb.plate] == D.PLATE and c.pump not in later
assert not set(D.fixtures(dome, D.State(w=9, stage=1))) & {bb.lever, bb.pump}
assert all(
    "powered=true" in block
    for cell, block in D.fixtures(dome, D.SOLVED).items()
    if "lever" in block
)
for form in (1, 2):
    assert not rooms.input_problems(
        D.plan(dome, form), D.inputs(dome, form), floor=b.floor
    )
    assert len(D.inputs(dome, form)) == 7

# the machinery that only ticks: no input in it, on no cell of the room's,
# plain pistons with nothing on them; the tide clock in the hall, never
# wet; the beam engine above the flood and built still
room_, dress = D.structure(dome), D.dressing(dome)
for block in dress.everything().values():
    assert not rooms.is_input(block), block
assert len(dress.everything()) > 150
for machine in (place.engine, place.tide):
    assert len(machine.lamps) == 4 and len(machine.pistons) == 2
    assert all(b.parts[p] == "minecraft:piston[facing=up]" for p in machine.pistons)
assert place.engine_torch in b.clear and place.engine_torch not in b.attached
assert all(D.fr_of(fr, cell)[0] < D.DAM_F for cell in place.tide.cells)
assert all(D.fr_of(fr, cell)[2] >= D.CROWN_H for cell in place.engine.cells)
assert sum(D.TORCH in block for block in b.attached.values()) == 1
assert len(place.lamps) == 14 and set(place.lamps) <= b.moving
top = max(cell[1] for cell in b.solid) - dome.floor_y
assert top >= 20 and len({D.WALK_H, D.CROWN_H, D.MID_H, D.LOW_H}) == 4

# the walks, the routes by ladder and water, and what must be seen
assert not D.walk_problems(dome) and not D.sight_problems(dome)
assert not D.route_problems(dome) and not D.lock_problems(dome)
assert {"sluice A's control", "the dam's crest", "the logbook"} <= set(D.walks(dome))
assert {"the way out", "sluice C's control"} <= set(D.dry_walks(dome))
# a body in the water gets out at every level, and the two swims are short
for i, s in enumerate(place.sluices):
    sh = D.shape(dome, D.State(w=s.start, stage=i, gate=1))
    path = D.way(D.reach(sh, s.plate, falls=False) | D._wet_only(sh, s.plate), s.stand)
    assert path[0] == s.plate and path[-1] == s.stand
    assert D.dive(sh, path) <= D.MAX_DIVE and (i > 0) == (D.dive(sh, path) > 0)
for w in range(D.TOP, 0, -1):
    sh = D.shape(dome, D.State(w=w, stage=0))
    start = fr.at(-8, -18, w)
    assert sh.floats(start) and (x, y, z) in D.reach(sh, start, falls=False), w

# each check finds a fault
real_dressing, real_structure = D.dressing, D.structure


def changed(dressing=None, structure=None):
    def wrap(real, change):
        def blocks(dome):
            got = real(dome)
            if change:
                change(got)
            return got

        return blocks

    D.dressing = wrap(real_dressing, dressing)
    D.structure = wrap(real_structure, structure)
    D.forget()


def wall(d):  # across the hall, between the door and the stair
    for r in range(-dome.radius, dome.radius + 1):
        for h in (1, 2, 3):
            cell = fr.at(-17, r, h)
            if cell in cells.interior and cell not in d.everything():
                d.solid[cell] = D.COPPER


changed(wall)
assert any("the foot of the stair" in p for p in D.walk_problems(dome))
assert any("sluice A's control" in p for p in D.route_problems(dome))
assert D.room_problems(dome)
changed(lambda d: d.solid.update({fr.at(-5, 0, 6): D.COPPER}))
assert any("lamp" in p and "hidden" in p for p in D.sight_problems(dome))
changed(
    lambda d: d.solid.update(
        {fr.at(9, r, h): D.COPPER for r in (0, 1, 2) for h in (14, 15, 16)}
    )
)
assert any("gate A is hidden" in p for p in D.sight_problems(dome))


def no_ladders(s):
    for cell in [cell for cell, block in s.parts.items() if "ladder" in block]:
        del s.parts[cell]


changed(structure=no_ladders)
assert any("pump B" in p for p in D.route_problems(dome))


def a_pit(s):  # no ladder and no stair out of the bottom three layers
    no_ladders(s)
    for cell in [cell for cell, block in s.parts.items() if "stairs" in block]:
        if cell in basin and D.fr_of(fr, cell)[2] < D.LOW_H:
            del s.parts[cell]


changed(structure=a_pit)
assert any("no way back" in p and "stage 2" in p for p in D.lock_problems(dome))
changed(structure=lambda s: s.solid.pop(fr.at(D.DAM_F, 5, 4)))
assert any("leaks sideways" in p for p in D.basin_problems(dome))
changed(lambda d: d.solid.update({fr.at(-5, 5, 5): "minecraft:waxed_copper_grate"}))
assert any("water stands in it" in p for p in D.basin_problems(dome))
lever = "minecraft:lever[face=floor,facing=north,powered=false]"
changed(lambda d: d.attached.update({fr.at(-17, 5, 1): lever}))
assert any("does not list" in p for p in D.room_problems(dome))
changed(structure=lambda s: s.solid.update({bb.pump_brass: D.COPPER}))
assert any("not on gold" in p for p in D.room_problems(dome))
changed(lambda d: d.solid.update({fr.at(-22, 0, 1): D.COPPER}))
assert any("reserved" in p for p in D.room_problems(dome))
changed()
assert not D.room_problems(dome)

# the values of a level: at a low one the water falls faster and the
# spring holds longer; at the tuned one a layer goes every 1.5 s and each
# spring outlasts its stage's drain with time for the way there
one, five, ten = (D.scaled(level) for level in (1, 5, 10))
assert five == {"per": 30, "ta": 220, "tb": 320, "tc": 280}
assert one["per"] < five["per"] < ten["per"] and one["ta"] > five["ta"] > ten["ta"]
for key, s in zip("abc", place.sluices):
    drain = (s.start - s.target) * five["per"]
    assert five[f"t{key}"] * D.STEP >= drain + 200
    assert all(D.scaled(level)[f"t{key}"] >= 100 for level in game.LEVELS)
assert all(D.scaled(level)["per"] >= 2 * D.STEP for level in game.LEVELS)
assert 11 * five["per"] <= 20 * 20  # the pumping itself: under 20 s of a run

# the log: Finch's, four pages at most, a page a command over RCON
assert D.LOG_AUTHOR == "O. Finch" and len(D.LOG_PAGES) <= 4
assert "Chief Engineer" in D.LOG_PAGES[0] and "If two of you come" in D.LOG_PAGES[2]
assert "The lift came down again" in D.LOG_PAGES[3]
assert all('"' not in page and len(page) <= 256 for page in D.LOG_PAGES)
assert all(len(c.encode()) < B.MAX_COMMAND for c in D.book_commands(dome))
assert len(D.labels(dome)) == 6
"""
    )


def test_station_flooded_build():
    out = run(
        r"""
import build_station as B
import dome_flooded as D
import domes
import game
import station_layout as L
import tunnels
import verify_station as V

dome = L.DOMES[D.INDEX]
place = D.room(dome)
b = D.room_blocks(dome)

# the stage against the fake client: every block where the plan has it,
# the basin full to the top layer and the hall dry, the dome's shell and
# the pump engine left alone, the stub's bypass gone, the same built twice
stages = ["site", "dome_3", "tunnels", "dome_3_inside"]
rec = B.offline_build(stages=stages, force=False)
world = rec.world
fixed, fluid = D.fixed_blocks(dome), D.fluid_blocks(dome)
for cell, block in fixed.items():
    if cell != place.lectern:
        assert world.at(cell) == block or world.name_at(cell) == block, (cell, block)
assert "Finch" in world.at(place.lectern)
standing = D.fixtures(dome, D.START)
for cell, block in fluid.items():
    if cell not in standing:
        assert world.name_at(cell) == block, (cell, block)
assert sum(block == D.WATER for block in fluid.values()) == D.expected(dome)["water"]
cells = domes.dome_cells(dome)
wet = [
    c
    for c in cells.interior - D.basin(dome)
    if world.name_at(c) == D.WATER or "waterlogged=true" in world.at(c)
]
assert not wet, wet[:5]
assert all("waterlogged=true" in world.at(c) for c in D.layers(dome)[4].fittings)
for s in place.sluices:
    assert all(world.name_at(c) == D.BARS for c in s.gate)
assert all(world.name_at(c) == D.CHISELED for c in place.door)
engine = tunnels.engine_cells(L.TUNNELS[D.INDEX])
assert all(world.name_at(c) != domes.AIR for c in list(engine.values())[:9])
assert world.at(engine[1, 3]) == f"{D.ROD}[{D.WET}]"
assert all(world.name_at(c) != domes.AIR for c in cells.shell | cells.floor)
post = game.stub_post(dome)
assert all("lever" not in world.at(c) and "sign" not in world.at(c) for c in post.cells)
assert f"kill @e[tag={game.stub_tag(D.INDEX)}]" in rec.commands
summons = [c for c in rec.commands if c.startswith("summon")]
assert sum("minecraft:interaction" in c for c in summons) == 1
assert sum("minecraft:text_display" in c for c in summons) == 6
assert all(D.ENTITY_TAG in c for c in summons)
assert "function station:dome/3/reset" in rec.commands
# the tide clock's torch goes in after the rest of it; the beam engine has none
torch = next(c for c, block in b.attached.items() if D.TORCH in block)
placed = [i for i, c in enumerate(rec.commands) if D.TORCH in c]
assert len(placed) == 1 and world.name_at(place.engine_torch) == domes.AIR
assert all(i < placed[0] for i, c in enumerate(rec.commands) if "repeater" in c)
again = B.offline_build(stages=[*stages, "dome_3_inside"], force=False)
assert again.world.dump() == world.dump()

# a room with a fault is not built
real = D.dressing


def bad(dome):
    d = real(dome)
    d.solid[D.frame(dome).at(-22, 0, 1)] = D.COPPER
    return d


D.dressing = bad
D.forget()
try:
    B.offline_build(stages=stages, force=False)
except RuntimeError as e:
    assert "reserved" in str(e)
else:
    raise AssertionError("a room on reserved cells was built")
D.dressing = real
D.forget()

# the example's own offline checks, with this room in the build
results = V.offline_checks()
failed = {name: problems for name, problems in results.items() if problems}
assert not failed, failed
V.main()
"""
    )
    assert "FAIL" not in out and "TODO flooded_dome" not in out


def test_station_flooded_pack():
    run(
        r"""
import build_station as B
import datapack
import dome_flooded as D
import domes
import game
import station_layout as L
import verify_station as V

dome = L.DOMES[D.INDEX]
place = D.room(dome)

# the pack: the hooks the core calls, one way to solve, nothing aimed wide
pack = datapack.Pack(stamp="t")
game.add_functions(pack, [D.MODULE])
own = datapack.Pack(stamp="t")
D.functions(own)  # (the core adds functions of its own under dome/3/)
mine = {n: lines for n, lines in own.functions.items() if n.startswith("dome/3/")}
assert all(pack.functions[n] == lines for n, lines in own.functions.items())
for hook in game.HOOKS:
    assert f"dome/3/{hook}" in mine, hook
assert "dome/3/leave" not in mine and "dome/3/died" not in mine  # (nothing lent)
calls = lambda path, name: any(  # noqa: E731
    line.endswith(f"function station:{name}") for line in pack.functions[path]
)
assert calls("dome/3/entered", "dome/3/enter") and calls("game/tick", "dome/3/tick")
assert calls("dome/3/form", "dome/3/solo") and calls("dome/3/form", "dome/3/duo")
assert calls("reset/all", "dome/3/reset") and calls("dome/3/left", "dome/3/empty")
solvers = [
    n
    for n, ls in mine.items()
    if any("function station:dome/3/solved" in line for line in ls)
]
assert solvers == ["dome/3/done"], solvers
assert not V.function_problems(B.pack_files(pack))
for name, lines in mine.items():
    for line in lines:
        assert "@p" not in line and "@a[" not in line.replace("@a[tag=st.in", ""), line
        assert "@e[" not in line.replace("@e[tag=st.in", "").replace(
            "@e[type=minecraft:item", ""
        ), line
# the game's reset: tunnel 3 put back before the room is flooded round its
# engine; the room's reset does all that ``empty`` does
order = pack.functions["reset/all"]
assert order.index("function station:tunnel/3/reset") < order.index(
    "function station:dome/3/reset"
)
reset, empty = mine["dome/3/reset"], mine["dome/3/empty"]
assert calls("dome/3/reset", "dome/3/zero") and calls("dome/3/reset", "dome/3/draw")
assert calls("dome/3/reset", "dome/3/engine_off") and calls(
    "dome/3/empty", "dome/3/engine_off"
)
assert calls("dome/3/draw", "dome/3/fixtures") and calls("dome/3/draw", "dome/3/gates")
assert calls("dome/3/empty", "dome/3/fixtures") and calls(
    "dome/3/empty", "dome/3/gates"
)
assert not any(
    "#fl.w " in line or "#fl.stage " in line or "#fl.pump " in line for line in empty
)
# the solo and duo hooks only say what is wanted: the change waits for swap
assert mine["dome/3/solo"] == ["scoreboard players set #fl.want st 1"]
assert mine["dome/3/duo"] == ["scoreboard players set #fl.want st 2"]
assert any(
    "#fl.ctl st matches 0" in line and "to_duo" in line for line in mine["dome/3/swap"]
)
# the rig's two rules. Levers, plates and signs out before any water is
# written; every layer's function writes each of its fittings, wet or dry;
# no function of the room but those and the gates' touches the water
draw = mine["dome/3/draw"]
assert draw[0] == "function station:dome/3/fixtures_clear"
assert len(mine["dome/3/fixtures_clear"]) == len(D.fixture_cells(dome)) == 15
layers = D.layers(dome)
for h, layer in layers.items():
    wet_, dry = mine[f"dome/3/layer_{h}/wet"], mine[f"dome/3/layer_{h}/dry"]
    assert any(f"function station:dome/3/layer_{h}/wet" in line for line in draw)
    assert any(f"function station:dome/3/layer_{h}/dry" in line for line in draw)
    assert any(
        f"matches {h} run function station:dome/3/layer_{h}/dry" in line
        for line in mine["dome/3/layer_down"]
    )
    for cell, block in layer.fittings.items():
        at = f"setblock {cell[0]} {cell[1]} {cell[2]} "
        assert at + D.wet(block) in wet_ and at + block in dry
    assert sum(line.startswith("fill") for line in wet_) == 2 * len(
        domes.boxes(layer.open)
    )
    assert all(
        line.endswith("replace minecraft:water")
        or line.endswith("replace minecraft:air")
        for line in wet_ + dry
        if line.startswith("fill")
    )
    # the fittings go dry before the water is taken, wet after it is put
    assert dry.index(next(line for line in dry if line.startswith("fill"))) == len(
        layer.fittings
    )
    assert f"check/dome/3/layer_{h}" in pack.functions
watery = {
    n
    for n, lines in mine.items()
    if any("minecraft:water" in line or "waterlogged" in line for line in lines)
}
assert watery == {
    f"dome/3/layer_{h}/{how}" for h in layers for how in ("wet", "dry")
} | {
    "dome/3/gate_b/open",
    "dome/3/gate_b/shut",
    "dome/3/gate_c/open",
    "dome/3/gate_c/shut",
    "dome/3/gate_a/shut",
}, watery
assert max(len(lines) for lines in mine.values()) < 400
# the machinery runs whether or not there is a puzzle, and no function of
# the puzzle reads it; the beam engine's torch is the pack's
tick = mine["dome/3/tick"]
at = lambda end: next(i for i, l in enumerate(tick) if l.endswith(end))  # noqa: E731
assert at("function station:dome/3/deco") < at("function station:dome/3/step")
machine = [D._xyz(c) for m in (place.engine, place.tide) for c in m.cells]
machine += [D._xyz(c) for c in place.lamps]
torch = D._xyz(place.engine_torch)
for name, lines in mine.items():
    if name.startswith("dome/3/deco") or "engine" in name:
        continue
    for line in lines:
        assert not any(f" {xyz} " in line for xyz in machine), (name, line)
assert all(
    torch in line for n in ("engine_on", "engine_off") for line in mine[f"dome/3/{n}"]
)
# three hints, one a stage
assert sum(n.endswith("/say") for n in mine) == 3
"""
    )


def test_station_flooded_simulated():
    run(
        SIM
        + r"""
import contextlib
import io

with contextlib.redirect_stdout(io.StringIO()):
    dome, rec, pack, sim = simulated()
world = rec.world
place = D.room(dome)
b = D.room_blocks(dome)
a, bb, c = place.sluices
quiet = (
    b.moving
    - {x for col in place.gauge for x in col}
    - {x for s in place.sluices for x in s.line}
)

# rule 2 of the rig, watched: whenever water is written, no lever, plate or
# sign stands anywhere in the layer written
fixture_cells = D.fixture_cells(dome)
real_fill = world.fill


def watched_fill(lo, hi, block, mode=None, filter=None):
    if block == D.WATER:
        for x, y, z in fixture_cells:
            if lo[1] <= y <= hi[1]:
                assert not any(
                    w in world.at((x, y, z)) for w in ("lever", "plate", "sign")
                ), (x, y, z)
    real_fill(lo, hi, block, mode, filter)


world.fill = watched_fill


def differs(state):
    standing = D.fixtures(dome, state)
    want = D.fixed_blocks(dome, state)
    want |= {
        x: blk for x, blk in D.fluid_blocks(dome, state).items() if x not in standing
    }
    out = []
    for cell, block in want.items():
        have = world.at(cell) or D.AIR
        if cell in quiet or cell == place.lectern:
            block, have = D._name(block), D._name(have)
        if have != block:
            out.append((D.fr_of(place.frame, cell), block, have))
    return out


def put(**scores):
    for name, value in scores.items():
        sim.s[f"#fl.{name}", "st"] = value


# reset, from a room in a mess: full, shut, stage A's control at rest
assert not differs(D.START)
for cell in list(D.layers(dome)[6].open)[:200]:
    world.setblock(cell, D.AIR)
world.setblock(a.lever, D.lever(a.facing, True))
world.setblock(bb.lever, D.lever(bb.facing))
world.setblock(c.gate[0], D.AIR)
put(w=4, stage=1, form=2, ctl=1, pump=1, gate=1)
assert differs(D.START)
sim.run("dome/3/reset")
assert not differs(D.START), differs(D.START)[:5]
assert (sim.time + 20, "dome/3/draw") in sim.queue  # (and once more a second on)

# draw: any state can follow any other, written whole from the scores
jumps = [
    D.State(w=9, stage=0, ctl=1, gate=1, lit=8),
    D.State(w=7, stage=1, form=2),
    D.State(w=0, stage=3),
    D.State(w=11, stage=0, form=2),
    D.State(w=5, stage=1, pump=1),
    D.State(w=3, stage=2, form=2, ctl=1, gate=1, lit=8),
    D.State(w=1, stage=2, pump=1, ctl=1, gate=1, lit=8),
    D.State(w=10, stage=0),
    D.State(w=2, stage=2),
    D.State(w=9, stage=1),  # (scores that the game never makes: B stays under water)
    D.State(w=6, stage=1, gate=1),
    D.State(w=11, stage=0),
]
for state in jumps:
    put(
        w=state.w,
        stage=state.stage,
        form=state.form,
        ctl=state.ctl,
        pump=state.pump,
        gate=state.gate,
    )
    sim.run("dome/3/target")
    put(t=sim.s["#fl.tt", "st"])
    sim.run("dome/3/draw")
    assert not differs(state), (state, differs(state)[:5])
    assert sim.is_block(place.door[0], D.AIR) == (state.stage == 3)

# the pumps' own way down: a layer at a time from the top, the gauge and
# the gates' bars with it, each state whole
put(tgt=0)
for w in range(D.TOP - 1, -1, -1):
    sim.run("dome/3/layer_down")
    assert sim.s["#fl.w", "st"] == w and not differs(D.State(w=w)), (
        w,
        differs(D.State(w=w))[:5],
    )
sim.run("dome/3/reset")

# the check's own counts, by its functions: right when the room is right
# (full, and part drained with a gate open), wrong when it is not
ctx = Ctx(sim, dome)
assert D.counts(ctx) == D.expected(dome) | {"ran": D.TOP}
state = D.State(w=6, stage=1, pump=1, gate=1)
put(w=6, stage=1, pump=1, gate=1)
sim.run("dome/3/draw")
assert D.counts(ctx) == D.expected(dome, state) | {"ran": D.TOP}
x, y, z = next(iter(D.layers(dome)[3].open))
world.setblock((x, y, z), D.AIR)
got = D.counts(ctx)
assert got["air"] == D.expected(dome, state)["air"] + 1 and got["under"] == 1
world.setblock(bb.gate[0], f"{D.BARS}[{D.DRY}]")
assert D.counts(ctx)["fit"] == D.expected(dome, state)["fit"] - 1
world.setblock(place.frame.at(D.DAM_F - 1, 0, 1), D.WATER)  # water in the hall
assert any("wet" in p for p in domes.check_shell(ctx, dome, False))
world.setblock(place.frame.at(D.DAM_F - 1, 0, 1), D.AIR)
sim.run("dome/3/reset")
assert not domes.check_shell(ctx, dome, False)

# the live check, worked from end to end against the simulation: the
# functions do what it asks of them in every path it takes (solo straight
# through, at rest part way, nobody shut in, duo, the form changing both
# ways, leaving and coming back, the levels, the reset). Redstone does not
# run here, so of its findings only those are left
sim.s["#d3", "st"] = 0
problems = D.check(ctx)
left = [
    p for p in problems if "tide clock" not in p and "pistons while pumping" not in p
]
assert not left, left
assert len(problems) == 2, problems
assert not sim.select(f"@e[tag={game.STANDIN}]") and not differs(D.START)
assert sim.s["#d3", "st"] == 0 and sim.s["#fl.live", "st"] == 0
told = [line for line in sim.other if line.startswith("tellraw")]
assert any("plate now" in line for line in told) and any(
    "on a spring" in line for line in told
)
assert sum("Pump clear" in line for line in sim.other) == 4
assert not any("hint" in line for line in told)  # (nobody dawdled)

# a few paths the check does not take. A second player comes in while the
# first is beyond the gate with the spring run out: the plate comes, and
# the gate stays open for as long as the first is there
sim.s["#d3", "st"] = 1
sim.line(
    f"summon minecraft:armor_stand {D.middle(domes.entrance(dome)[:3])} "
    '{Tags:["st.standin","st.x1"]}'
)
ctx.advance(14)
assert sim.s["#fl.live", "st"] == 1 and sim.s["#fl.form", "st"] == 1
sim.line(f"tp @e[tag=st.x1] {D.middle(a.stand)}")
ctx.advance(6)
bars = lambda s: sum(sim.is_block(x, D.BARS) for x in s.gate)  # noqa: E731
assert sim.s["#fl.in", "st"] == 1 and bars(a) == 0
sim.line(
    f"summon minecraft:armor_stand {D.middle(domes.entrance(dome)[:3])} "
    '{Tags:["st.standin","st.x2"]}'
)
ctx.advance(20)
assert sim.s["#fl.form", "st"] == 2 and sim.is_block(a.plate, D.PLATE) and bars(a) == 0
# the pump thrown from inside, nobody on the plate: no water moves
world.setblock(a.pump, D.lever(a.pump_facing, True))
ctx.advance(80)
assert sim.s["#fl.pump", "st"] == 1 and sim.s["#fl.w", "st"] == D.TOP
# a lever moved back by hand while it is held is put over again
world.setblock(a.pump, D.lever(a.pump_facing))
ctx.advance(4)
assert sim.is_block(a.pump, "minecraft:lever[powered=true]")
# the hint comes when nothing happens for its time, once
ctx.advance(D.HINT_SECONDS * 20)
hints = [
    line for line in sim.other if line.startswith("tellraw") and "standpipe" in line
]
assert len(hints) == 1, hints
ctx.advance(D.HINT_SECONDS * 20)
assert len([l for l in sim.other if l.startswith("tellraw") and "standpipe" in l]) == 1
# the game's reset with players in the room
sim.run("reset/all")
assert not differs(D.START) and sim.s["#fl.pump", "st"] == 0

# the guard, with nobody in the dome: tunnel 3 opened by anything but the
# room (the core's tunnel check does) finds the basin dry a tick later,
# 20 s before its doors open; a room found dry by a player is solved only
# while the tunnel is pumping or open
assert "station:dome/3/guard" in pack._tick
sim.line("kill @e[tag=st.standin]")
ctx.advance(80)
assert sim.s["#occ3", "st"] == 0 and sim.s["#d3", "st"] == 0
sim.run("tunnel/3/open")
ctx.tick()
assert not differs(D.SOLVED), differs(D.SOLVED)[:5]
assert D.counts(ctx) == D.expected(dome, D.SOLVED) | {"ran": D.TOP}
doors = [x for _, x in domes.door_cells(dome, L.TUNNELS[3])]
assert not any(sim.is_block(x, D.AIR) for x in doors)
sim.run("tunnel/3/reset")
sim.s["#d3", "st"] = 1
sim.line(
    f"summon minecraft:armor_stand {D.middle(domes.entrance(dome)[:3])} "
    '{Tags:["st.standin","st.x1"]}'
)
ctx.advance(14)
# the tunnel shut again since (its check reset it): flooded, not solved
assert sim.s["#d3", "st"] == 1 and sim.s["#t3", "st"] == 0
assert sim.s["#fl.stage", "st"] == 0 and sim.s["#fl.w", "st"] == D.TOP
assert sim.s["#fl.live", "st"] == 1
# and with the tunnel pumping (the core's ring check calls ``solved``)
sim.run("tunnel/3/open")
ctx.advance(14)
assert sim.s["#fl.w", "st"] == 0 and sim.s["#d3", "st"] == 2
sim.line("kill @e[tag=st.standin]")
sim.run("reset/all")
assert not differs(D.START)
"""
    )
