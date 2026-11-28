"""
Hull Breach (examples/station/dome_hullbreach.py) with no server: its plan
and the offline proofs of it (the basin closed, headroom, a way out at
every level, no pits), its build against the example's fake client, its
datapack functions, and the functions run in a small simulation of the
game's commands, in which its live check is worked from end to end. As in
test_station_example.py, each test runs in a Python of its own, in the
example's folder.

On a branch whose ring has no ``hullbreach`` yet, each test first puts
the room at the Clockwork Maze's site (``SITE``): the same size, entered
from the east with its exit straight ahead, as the design assumes; the
Maze's own module is left out of the pack there.
"""

import os
import subprocess
import sys
from pathlib import Path

STATION = Path(__file__).parents[1] / "examples" / "station"
# what the example reads from the environment
SETTINGS = ("STAGES", "CHECKS", "FORCE", "STATION_DATAPACKS_DIR")

SITE = r"""
import sys

sys.path.insert(0, ".")
import station_layout as L

if "hullbreach" not in [d.key for d in L.DOMES]:
    import game

    _SITE, _REAL = L.index_of("maze"), L.index_of
    L.index_of = lambda key: _SITE if key == "hullbreach" else _REAL(key)
    game.MODULE_FILES = tuple(
        "dome_hullbreach" if m == "dome_maze" else m for m in game.MODULE_FILES
    )
"""


def run(code: str, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in SETTINGS}
    result = subprocess.run(
        [sys.executable, "-c", SITE + code, *args],
        cwd=STATION,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_station_hullbreach_plan():
    run(
        r"""
import math

import build_station as B
import dome_hullbreach as H
import domes
import fittings
import game
import rooms
import station_layout as L
import tunnels
import verify_station as V

dome = L.DOMES[H.INDEX]
assert H.INDEX == L.index_of("hullbreach")
assert B.STAGES[f"dome_{H.INDEX}_inside"] is H.build
assert V.LIVE["hull_breach"] is H.check and "hull_breach_rig" not in V.LIVE

# the plan: nothing wrong with it, in the dome's own frame
assert not H.room_problems(dome), H.room_problems(dome)
b = H.room_blocks(dome)
place = H.room(dome)
fr = place.frame
cells = domes.dome_cells(dome)
holes = {c for br in place.breaches for c in br.holes}
used = set(b.above()) | b.clear | b.swept | set(place.door) | holes
assert used <= cells.interior and not used & tunnels.reserved_cells(dome)
assert set(b.floor) <= cells.floor
assert fr.at(0, 0, 0) == dome.floor_centre
assert H.fr_of(fr, fr.at(-4, 9, 3)) == (-4, 9, 3)
assert len(b.everything()) > 4000

# the two blocks that mean something here, and nowhere else
assert rooms.MEANINGS[H.FRAME] == rooms.MEANINGS[H.PLATE] == H.INDEX
other = L.DOMES[(H.INDEX + 1) % len(L.DOMES)]
inside = (other.floor_centre[0], other.floor_centre[1] + 3, other.floor_centre[2])
found = rooms.room_problems(other, {inside: H.FRAME})
assert any("means something" in p for p in found)

# the basin: registered with the core as wet on purpose, between the dams
# up to the line; the halls and the ways in hold none of it
basin = H.basin(dome)
assert domes.WET_OK[H.INDEX] == H.wet_cells(dome) >= basin
assert "the test column" in domes.ALLOWED[H.INDEX]
assert {H.fr_of(fr, c)[2] for c in basin} == set(range(1, H.MAX + 1))
assert all(H.ENTRY_F < H.fr_of(fr, c)[0] < H.EXIT_F for c in basin)
core = {
    (x, lo[1], lo[2])
    for part in domes.check_parts(dome)
    for lo, hi in part
    for x in range(lo[0], hi[0] + 1)
}
assert not core & basin and fr.at(-19, 0, 1) in core and fr.at(0, 8, 12) in core
layers = H.layers(dome)
water = sum(len(layer.open) for layer in layers.values())
assert 10000 < water < 14000, water
sound = H.expected(dome, H.State(w=H.MAX))
assert sound["water"] == water - 4 * 8 and sound["glass"] == 4 * 8  # low, mid
assert H.expected(dome, H.State(w=H.MAX, open=H.ALL_OPEN))["water"] == water
some = H.State(w=0, open=frozenset({1}), patched=frozenset({2, 9}))
got = H.expected(dome, some)  # an open hole is the sea whatever the level
assert (got["source"], got["plate"], got["glass"]) == (4, 4, 4 * 6)
assert "air" not in H.steady(some) and "air" in H.steady(H.START)
for layer in layers.values():
    for block in layer.fittings.values():
        assert H.DRY in block and H.holds_water(block), block
assert not any(H._waterloggable(blk) for c, blk in b.solid.items() if c in basin)

# the breaches: twelve, four on each level (two a side), in frames of raw
# iron, each hole touching two frame blocks with the room's own glass
# behind it (which a burst floods) and a ring of glass round that to
# crack; no frame is only dressing
assert [br.number for br in place.breaches] == list(range(1, 13))
for level in ("low", "mid", "high"):
    sides = [br.side for br in place.breaches if br.level == level]
    assert sorted(sides) == [-1, -1, 1, 1], level
assert not hasattr(place, "dressing")
assert set(b.solid.values()).isdisjoint({"minecraft:iron_block"})
for br in place.breaches:
    assert len(br.holes) == 4 and len(br.frame) == 12
    assert all(b.solid[c] == H.FRAME for c in br.frame)
    assert all(c not in b.everything() for c in br.holes)
    assert (br.level == "high") == (not set(br.holes) <= basin)
    assert br.spawn not in br.holes
    assert len(br.flooded) == 4 and len(br.cracks) >= 6
    assert all(b.solid[c] == H.GLASS for c in (*br.flooded, *br.cracks))
    assert len(br.sources) == (2 if br.level == "high" else 4)
    assert br.sources == br.holes[: len(br.sources)]  # the lower row first
# a state's blocks: sound glass; open, the sea in the holes (over the walk
# the lower two) and in the hull behind, cracked round; patched, plates
sound_, burst, patch = (
    H.fixed_blocks(dome, s_)
    for s_ in (H.START, H.State(open=H.ALL_OPEN), H.State(patched=H.ALL_OPEN))
)
for br in place.breaches:
    assert all(sound_[c] == H.GLASS for c in (*br.holes, *br.flooded, *br.cracks))
    assert all(burst[c] == H.WATER for c in br.sources)
    assert all(burst[c] == H.AIR for c in set(br.holes) - set(br.sources))
    assert all(patch[c] == H.PLATE for c in br.holes)
    for blocks in (burst, patch):
        assert all(blocks[c] == H.SEA for c in br.flooded)
        assert all(blocks[c] == H.CRACKED for c in br.cracks)
assert not H.breach_problems(dome)
# every breach has a label of its own over it and a Breacher's casting
# point of its own in front of it (on its feet: breach_problems)
assert len({br.tag for br in place.breaches}) == 12
assert len({br.label for br in place.breaches}) == 12
assert len({br.spawn for br in place.breaches}) == 12
assert place.points[:12] == tuple(br.spawn for br in place.breaches)
# every stage's order: four breaches of its own, the first two on two
# levels and two sides; the three orders are all twelve between them
for order in H.ORDERS:
    assert len(set(order)) == len(order) == H.STAGE_CAP == 4
    one, two = (place.breach(n) for n in order[:2])
    assert one.level != two.level and one.side != two.side
assert sorted(n for order in H.ORDERS for n in order) == list(range(1, 13))
# no breach bursts twice in a run, at any level, solo or duo: a stage
# bursts a run of its own order, never more than the order has (the cap,
# which only levels 9 and 10 with two players meet)
for level in game.LEVELS:
    for form in (1, 2):
        per_stage = H.stage_bursts(level, form)
        want = tuple(n + form - 1 for n in H.BURSTS[level])
        capped = level >= 9 and form == 2
        assert (per_stage != want) == capped, (level, form)
        assert all(1 <= n <= H.STAGE_CAP for n in per_stage)
        burst = H.run_bursts(level, form)
        assert len(burst) == sum(per_stage) == len(set(burst)), (level, form)
assert set(game.LEVELS) == set(H.BURSTS) == set(range(1, 11))
assert H.stage_bursts(10, 2) == (4, 4, 4) and H.stage_bursts(9, 2) == (4, 4, 4)
assert len(H.run_bursts(5, 1)) == 7 and len(H.run_bursts(10, 1)) == 11

# the inputs: the valve and the recall button, on brass with signs
assert not rooms.input_problems(H.plan(dome), H.inputs(dome), floor=b.floor)
assert len(H.inputs(dome)) == 2
assert H.fr_of(fr, place.valve.input)[2] > H.WALK_H  # above the line, in the hall
assert H.fr_of(fr, place.valve.input)[0] < H.ENTRY_F
for block in b.everything().values():
    assert not rooms.is_input(block) or "lever" in block or "button" in block

# the proofs, each on its own, and what each one finds
assert not H.basin_problems(dome) and not H.headroom_problems(dome)
assert not H.walk_problems(dome) and not H.escape_problems(dome)
# running water: from the sources, down and FLOW along; never at or behind
# the entry dam, never under the exit hall's roof, washing nothing away
wet = H.stream(dome)
assert not H.stream_problems(dome)
assert {c for br in place.breaches for c in br.sources} <= wet
assert all(H.fr_of(fr, c)[0] > H.ENTRY_F for c in wet)
assert all(H.fr_of(fr, c)[0] > H.ENTRY_F + 3 for c in H.mop_cells(dome))
assert fr.at(0, 0, H.GANTRY_H + 1) not in wet  # nothing runs up
assert any(H.fr_of(fr, c)[2] == 1 for c in wet)  # it falls to the floor
assert any(H.fr_of(fr, c)[2] == H.WALK_H + 1 for c in wet)  # and wets the walk
assert H.mop_cells(dome) == {c for c in wet if H.fr_of(fr, c)[2] > H.MAX}
assert not wet & set(b.everything()) and wet <= domes.WET_OK[H.INDEX]
# the ring walk goes on past every high breach, and the gantry's ladders
# come out on its deck
sh = H.shape(dome, H.START)
deck = H.WALK_H + 1
ring, edge = set(), [fr.at(H.ENTRY_F, 8, deck)]
while edge:
    c = edge.pop()
    if c not in ring:
        ring.add(c)
        edge += [to for to in sh.moves(c, falls=False) if to[1] == c[1]]
for br in place.breaches:
    assert (br.spawn in ring) == (br.level == "high"), br.number
for f, r in ((0, 19), (0, -19), (H.EXIT_F, 0), (H.VALVE[0] - 1, H.VALVE[1] + 1)):
    assert fr.at(f, r, deck) in ring, (f, r)
for side in (1, -1):
    top = fr.at(0, side * H.LADDER_R, H.GANTRY_H)
    assert fr.at(0, side * (H.LADDER_R - 1), H.GANTRY_H + 1) in sh.moves(top)
real = H.structure


def changed(change):
    def blocks(d):
        got = real(d)
        change(got)
        return got

    H.structure = blocks
    H.forget()


# a hole in the entry dam under the line: the basin leaks into the hall
changed(lambda s: s.solid.pop(fr.at(H.ENTRY_F, 5, 3)))
assert any("leaks sideways" in p for p in H.basin_problems(dome))
# a rail in the basin: water would stand in it unwritten
changed(lambda s: s.parts.update({fr.at(0, 8, 4): H.BARS}))
assert any("not written by its layer" in p for p in H.basin_problems(dome))
# a deck over the water five wide: no air for a swimmer under its middle
changed(
    lambda s: s.solid.update(
        {fr.at(f, r, 8): H.CUT for f in range(-6, -1) for r in range(4, 11)}
    )
)
assert any("no air within two" in p for p in H.headroom_problems(dome))


def no_way_up(s):  # no stair, no ladder out of the water
    for cell in [c for c, blk in s.parts.items() if "ladder" in blk or "stairs" in blk]:
        if cell in basin:
            del s.parts[cell]


changed(no_way_up)
assert any("no way back" in p for p in H.escape_problems(dome))
# a lid off the compressor's cage: a pit on the gantry
changed(
    lambda s: [
        s.solid.pop(fr.at(f, r, H.GANTRY_H + 3), None)
        for f in range(2, 7)
        for r in range(-3, 4)
    ]
)
assert any("no way out" in p for p in H.walk_problems(dome))
# a lever by a frame: in the bay, and in the stream
lever = "minecraft:lever[face=floor,facing=north,powered=false]"
changed(lambda s: s.attached.update({place.breach(7).spawn: lever}))
assert any("in its bay" in p for p in H.breach_problems(dome))
assert any("washes away" in p for p in H.stream_problems(dome))
# the hull behind a hole not plain glass
changed(lambda s: s.solid.update({place.breach(2).flooded[0]: H.COPPER}))
assert any("not plain glass" in p for p in H.breach_problems(dome))
# a pane out of the exit hall's roof where breach 9's stream crosses it:
# the rail that goes up round the gap keeps the stream out; with no rail
# it falls into the hall
roof = min(c for c in wet if H.fr_of(fr, c)[0] > H.EXIT_F)
changed(lambda s: s.solid.pop((roof[0], roof[1] - 1, roof[2])))
assert not H.stream_problems(dome)
rails, H.rails = H.rails, lambda *_: {}
H.forget()
assert any("into the exit hall" in p for p in H.stream_problems(dome))
H.rails = rails
# water that ran four times as far along the walk would be on the entry
# dam's crest, over the hall
H.structure = real
H.FLOW = 28
H.forget()
assert any("entry hall's side" in p for p in H.stream_problems(dome))
H.FLOW = 7
H.structure = real
H.forget()
assert not H.room_problems(dome)

# the values of a level, as section 7 of the design has them
five, one, ten = (H.scaled(level) for level in (5, 1, 10))
assert five["per"] * H.STEP == 280 and five["stag"] == 300 and five["hold0"] == 200
assert one["per"] * H.STEP == 392 and ten["per"] * H.STEP == 140
assert (five["n1"], five["n2"], five["n3"]) == (2, 2, 3)
assert (five["bsolo"], five["bduo"], five["rsolo"], five["rduo"]) == (3, 5, 1, 2)
assert [H.scaled(level)["wb"] for level in game.LEVELS] == [1, 1, 1] + [0] * 7

# the story: Finch's log, four pages, Marsh's hand; the plaque's three signs
assert H.LOG_AUTHOR == "O. Finch" and len(H.LOG_PAGES) == 4
text = " ".join(H.LOG_PAGES)
assert "Marsh was here before me" in text and "Signal Room is next" in text
assert all('"' not in page and len(page) <= 256 for page in H.LOG_PAGES)
assert all(len(c.encode()) < B.MAX_COMMAND for c in H.book_commands(dome))
for sign in (*H.PLAQUE_SIGNS, H.VALVE_SIGN):
    assert len(sign) <= 4 and all(len(line) <= 15 for line in sign), sign
assert len(H.labels(dome)) == 12 + 1 + 2
# the BREACH labels three times the size, turning to the eye, no backing
breach_labels = H.labels(dome)[len(H.room(dome).valve.summons) :][:12]
assert all(br.tag in c for br, c in zip(place.breaches, breach_labels, strict=True))
for c in breach_labels:
    assert "scale:[3.0f,3.0f,3.0f]" in c and "background:0" in c, c
    assert 'billboard:"center"' in c, c
# a Breacher notices players within 8 blocks; no other kind's summon changes
import automatons as A

follow = '{id:"minecraft:follow_range",base:8.0d}'
for kind in (A.BREACHER, H.BREACHER_MELEE):
    assert follow in A.summon_kind(kind, "0 0 0", H.INDEX)
assert all("follow_range" not in A.summon_kind(k, "0 0 0", H.INDEX) for k in A.KINDS)
import dome_foundry

assert "hull test chamber" in dome_foundry.LOG_PAGES[-1]
assert "sending" not in dome_foundry.LOG_PAGES[-1]
# the rig is a check only when named
assert "hull_breach_rig" not in H.MODULE.checks
"""
    )


def test_station_hullbreach_build():
    run(
        r"""
import build_station as B
import dome_hullbreach as H
import domes
import game
import station_layout as L

dome = L.DOMES[H.INDEX]
place = H.room(dome)
stages = ["site", f"dome_{H.INDEX}", "tunnels", f"dome_{H.INDEX}_inside"]
rec = B.offline_build(stages=stages, force=False)
world = rec.world
want = H.fixed_blocks(dome, H.START)
wrong = [
    c
    for c, blk in want.items()
    if "{" not in blk
    and c != place.lectern
    and (world.at(c) or H.AIR).partition("[")[0] != blk.partition("[")[0]
]
assert not wrong, wrong[:5]
# dry, every breach sound, the dam door shut, the stub's bypass gone
for c in H.basin(dome):
    block = world.at(c) or ""
    assert not block.startswith("minecraft:water"), c
    assert "waterlogged=true" not in block, c
assert all(world.at(c) == H.GLASS for br in place.breaches for c in br.holes)
assert not any(
    (world.at(c) or "").startswith(("minecraft:barrier", H.CRACKED))
    for c in domes.dome_cells(dome).interior
)
assert all(world.at(c) == H.CHISELED for c in place.door)
for c in game.stub_post(dome).cells:
    assert (world.at(c) or H.AIR) == H.AIR or c in want, c
assert all(len(c.encode()) <= B.MAX_COMMAND for c in rec.commands)
summons = [c for c in rec.commands if c.startswith("summon")]
assert sum("text_display" in c for c in summons) == len(H.labels(dome))
assert sum("interaction" in c for c in summons) == 1
# built twice, the same
again = B.offline_build(stages=stages, force=False)
assert (again.world.blocks == world.blocks).all()
"""
    )


def test_station_hullbreach_pack():
    run(
        r"""
import build_station as B
import datapack
import dome_hullbreach as H
import game
import station_layout as L

dome = L.DOMES[H.INDEX]
pack = B.new_pack("t")
n = H.INDEX
fs = pack.functions
for hook in (*game.HOOKS, "leave", "died"):
    assert f"dome/{n}/{hook}" in fs, hook
assert f"dome/{n}/guard" in fs and pack.id(f"dome/{n}/guard") in pack._tick
assert not B.pack_problems()
# the temper's follow range of 40 is the Riveters', never a Breacher's
reach = [line for line in fs[f"dome/{n}/temper"] if "follow_range" in line]
assert len(reach) == 1 and "tag=!st.k.breacher" in reach[0]
for h in range(1, H.MAX + 1):
    assert f"dome/{n}/layer_{h}/wet" in fs and f"check/dome/{n}/layer_{h}" in fs
for br in H.room(dome).breaches:
    for name in ("burst", "seal", "plug", "cast_at", "hole", "crack"):
        assert any(p.startswith(f"dome/{n}/{name}/{br.number}") for p in fs), name
    for name in ("open", "patch", "shut"):
        assert f"dome/{n}/hole/{br.number}/{name}" in fs
    burst = fs[f"dome/{n}/burst/{br.number}"]
    wet = [line for line in burst if "setblock" in line and H.WATER in line]
    assert len(wet) == (2 if br.level == "high" else 4), br.number
    assert sum(H.SEA in line for line in burst) == 4
    assert sum("glass.break" in line for line in burst) == 2
    assert not any(H.WATER in line for line in fs[f"dome/{n}/hole/{br.number}/shut"])
    # only sound glass bursts or cracks: a patch holds
    assert "unless score #hb.b%d st matches 0 run return 0" % br.number in burst[0]
# a patch stays: the reset shuts every hole; a failed stage (and its
# pump-down, where a hole with a body in it waits) makes its own breaches
# sound and no others; a stage held restores nothing; a test left has its
# live stage's own breaches zeroed and drawn
def calls(path, name):
    return any(line.endswith(pack.id(f"dome/{n}/{name}")) for line in fs[path])


for br in H.room(dome).breaches:
    assert calls(f"dome/{n}/reset", f"hole/{br.number}/shut")
    # solved: a breach still open made sound, a patch kept (till the reset)
    b = f"#hb.b{br.number} st"
    assert (f"execute if score {b} matches 1 run scoreboard players set {b} 0"
            in fs[f"dome/{n}/restored"])
    assert not any(line.endswith(f"set {b} 0") and "matches 1" not in line
                   for line in fs[f"dome/{n}/restored"])
restore = fs[f"dome/{n}/restore_stage"]
assert len(restore) == 12
for s, order in enumerate(H.ORDERS):
    for i in order:
        live = f"execute if score #hb.stage st matches {s}"
        want = f"{live} unless score #hb.b{i} st matches 0 run function "
        assert want + pack.id(f"dome/{n}/plug/{i}") in restore
        zero = f"{live} run scoreboard players set #hb.b{i} st 0"
        assert zero in fs[f"dome/{n}/checkpoint"]
assert not any("hole/" in line for line in fs[f"dome/{n}/checkpoint"])
pumping = [line for line in fs[f"dome/{n}/water/pumping"] if "restore_stage" in line]
assert len(pumping) == 1 and "if score #hb.again st matches 1" in pumping[0]
# pumping waits only on a failed stage's breaches: the patches held stay
waits = [line for line in fs[f"dome/{n}/water/pumping"] if "return 0" in line]
assert len(waits) == 12 and all("#hb.again st matches 1" in w for w in waits)
assert calls(f"dome/{n}/fail", "restore_stage") and calls(f"dome/{n}/draw", "mop")
assert not calls(f"dome/{n}/held", "restore_stage")
assert calls(f"dome/{n}/empty", "checkpoint") and calls(f"dome/{n}/checkpoint", "draw")
# a stage bursts no more than its four
cap = "execute if score #hb.due st matches 5.. run scoreboard players set #hb.due st 4"
assert cap in fs[f"dome/{n}/start_stage"]
# no lever, button or sign is ever written into the basin by a function
basin = H.basin(dome)
for path, lines in fs.items():
    if not path.startswith(f"dome/{n}/"):
        continue
    for line in lines:
        assert datapack.MAX_LINE >= len(line)
        if "setblock" in line and any(w in line for w in ("lever", "button", "sign")):
            w = line.split("setblock ")[1].split(" ")
            assert (int(w[0]), int(w[1]), int(w[2])) not in basin, line
# the lent plate: placeable only on the frames, marked lent
item = H.plate_base()
assert 'can_place_on={blocks:"minecraft:raw_iron_block"}' in item
assert any(f"plate{n}" in line for line in fs[f"dome/{n}/leave"])
"""
    )


# A simulation of the commands the room's functions are made of (scores,
# setblock, fill, execute if/unless/store/as/at/positioned, function,
# return, summon, kill, tp) over the fake world's blocks, and of what the
# core does for one dome (who is in it, its hooks, its tick). It is not
# the game: no water runs, no redstone works, no mob moves, nothing is
# aimed at a player.
SIM = r'''
import math
import re

import build_station as B
import dome_hullbreach as H
import domes
import game
import station_layout as L

DEFAULTS = {"level": "0", "waterlogged": "false", "has_book": "false",
            "lit": "false", "powered": "false", "extended": "false"}
OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "=": lambda a, b: a == b,
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
}


def parts(block):
    name, _, rest = block.partition("{")[0].partition("[")
    states = dict(kv.split("=") for kv in rest.rstrip("]").split(",") if kv)
    return (name if ":" in name else "minecraft:" + name), states


def in_range(value, text):
    lo, sep, hi = text.partition("..")
    if not sep:
        return value == int(lo)
    return (not lo or value >= int(lo)) and (not hi or value <= int(hi))


class Return(Exception):
    pass


class Sim:
    def __init__(self, pack, world):
        self.f, self.world = pack.functions, world
        self.s, self.ents = {}, []
        self.words = {}
        for line in pack.setup_lines():
            self.line(line)

    def is_block(self, pos, block):
        have, hs = parts(self.world.at(pos) or "minecraft:air")
        want, ws = parts(block)
        ok = have == want or (want == "#minecraft:pressure_plates" and "plate" in have)
        return ok and all(hs.get(k, DEFAULTS.get(k)) == v for k, v in ws.items())

    def select(self, selector, me=None):
        m = re.match(r"@(\w)(?:\[(.*)\])?$", selector)
        who = m.group(1)
        if who == "s":
            pool = [me] if me is not None else []
        elif who == "e":
            pool = self.ents
        else:
            return []  # nobody is online
        args, tags = {}, []
        for part in re.split(r",(?![^{]*\})", m.group(2) or ""):
            key, _, value = part.partition("=")
            (tags.append(value) if key == "tag" else args.__setitem__(key, value))
        if "scores" in args or "nbt" in args and "inGround" not in args["nbt"]:
            return []
        found = []
        for e in pool:
            x, y, z = e["pos"]
            if "type" in args and e["type"] != args["type"]:
                continue
            if "nbt" in args and not e.get("inGround"):
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
                # a marker's hitbox is a point: on the box's face is out
                if e.get("marker") and any(v == a for a, v in zip(lo, (x, y, z))):
                    continue
            if "distance" in args:
                centre = [float(args[k]) for k in "xyz"]
                if math.dist(centre, (x, y, z)) > float(args["distance"].lstrip(".")):
                    continue
            found.append(e)
        return found[: int(args["limit"])] if "limit" in args else found

    def xyz(self, toks, at):
        return tuple(
            at[i] + int(float(t[1:] or 0))
            if t.startswith("~")
            else math.floor(float(t))
            for i, t in enumerate(toks)
        )

    def run(self, path, at=None, me=None):
        try:
            for line in self.f[path]:
                self.line(line, at, me)
        except Return:
            pass
        return 1

    def line(self, line, at=None, me=None):
        w = self.words.get(line)
        if w is None:
            w = self.words[line] = line.split(" ")
        c = w[0]
        if c == "execute":
            return self.execute(w, 1, at, me)
        if c == "function":
            return self.run(w[1].split(":", 1)[1], at, me)
        if c == "scoreboard":
            return self.scoreboard(w)
        if c == "setblock":
            block = " ".join(w[4:])
            for tail in (" destroy", " replace", " keep"):
                block = block.removesuffix(tail)
            self.world.setblock(self.xyz(w[1:4], at), block)
        elif c == "fill":
            keep = w[9] if len(w) > 9 and w[8] == "replace" else None
            a, b = self.xyz(w[1:4], at), self.xyz(w[4:7], at)
            self.world.fill(a, b, w[7], None, keep)
        elif c == "return":
            if w[1] == "run":
                self.line(" ".join(w[2:]), at, me)
            raise Return
        elif c == "summon":
            tags = re.search(r"Tags:\[([^\]]*)\]", line)
            self.ents.append({
                "type": w[1],
                "pos": tuple(float(v) for v in w[2:5]),
                "tags": set(re.findall(r'"([^"]+)"', tags.group(1))) if tags else set(),
                # a trident dropped onto the floor lands and sticks
                "inGround": "inGround:1b" in line
                or (w[1] == "minecraft:trident" and "Motion:" in line),
                "marker": "Marker:1b" in line,
                "attrs": {
                    k: float(v)
                    for k, v in re.findall(r'id:"minecraft:(\w+)",base:([\d.]+)d', line)
                },
            })
        elif c == "attribute" and w[3:5] == ["base", "set"]:
            for e in self.select(w[1], me):
                e["attrs"][w[2].removeprefix("minecraft:")] = float(w[5])
        elif c == "kill":
            gone = self.select(w[1], me)
            self.ents = [e for e in self.ents if not any(e is g for g in gone)]
        elif c == "tp":
            for e in self.select(w[1], me):
                if w[2].startswith("~"):
                    x, y, z = e["pos"]
                    e["pos"] = (x, y + float(w[3][1:] or 0), z)
                else:
                    e["pos"] = tuple(float(v) for v in w[2:5])
        return 1

    def execute(self, w, i, at, me):
        store = count = None
        while i < len(w):
            k = w[i]
            if k == "run":
                result = self.line(" ".join(w[i + 1:]), at, me)
                if store:
                    self.s[store] = result or 0
                return True
            if k == "positioned":
                at = self.xyz(w[i + 1:i + 4], at)
                i += 4
            elif k == "as":
                who = self.select(w[i + 1], me)
                rest = w[:1] + w[i + 2:]
                for e in who:
                    self.execute(rest, 1, at, e)
                return bool(who)
            elif k == "at":
                who = self.select(w[i + 1], me)
                if not who:
                    return False
                at = tuple(math.floor(v) for v in who[0]["pos"])
                i += 2
            elif k == "on":
                return False
            elif k == "in":
                i += 2
            elif k == "store" and w[i + 2] == "score":
                store = (w[i + 3], w[i + 4])
                i += 5
            elif k == "store":
                i += 5 if w[i + 2] == "bossbar" else 7
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
                    ok = self.is_block(self.xyz(w[i + 2:i + 5], at), w[i + 5])
                    i += 6
                elif kind == "entity":
                    count = len(self.select(w[i + 2], me))
                    ok = count > 0
                    i += 3
                elif kind == "predicate":
                    block = self.world.at(at) or ""
                    ok = block.startswith("minecraft:water")
                    ok = ok or "waterlogged=true" in block
                    i += 3
                elif kind == "items":
                    ok = False
                    i += 5
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
        elif w[2] == "reset":
            self.s.pop(key, None)
        elif w[2] == "get":
            return self.s.get(key, 0)
        elif w[2] == "operation":
            a, b = self.s.get(key, 0), self.s.get((w[6], w[7]), 0)
            self.s[key] = {
                "=": b, "+=": a + b, "-=": a - b, "*=": a * b,
                "/=": a // b if b else a, "<": min(a, b), ">": max(a, b),
            }[w[5]]
        return self.s.get(key, 0)


class Ctx:
    """what a live check is given, over the simulation: the core's ticks
    for this one dome (who is in it by the stand-ins' places, its hooks at
    the core's times, its tick, the guard and the tunnels' tick)"""

    def __init__(self, sim, dome, pack):
        self.sim, self.dome, self.layout, self.pack = sim, dome, L, pack
        self.n = dome.index
        self.inside = set()
        self.run_checked = False

    def cmd(self, command, expect=None):
        w = command.split(" ")
        if w[0] == "time":
            return "The time is 1000"
        if w[0] == "attribute" and w[3:] == ["base", "get"]:
            (e,) = self.sim.select(w[1])
            name = w[2].removeprefix("minecraft:")
            return f"Base value of attribute {name} for x is {e['attrs'][name]}"
        self.sim.line(command)
        return ""

    def fill(self, a, b, block, how=""):
        box = f"{a[0]} {a[1]} {a[2]} {b[0]} {b[1]} {b[2]}"
        self.sim.line(f"fill {box} {block} {how}".strip())

    def setblock(self, pos, block):
        self.sim.world.setblock(pos, block)

    def function(self, path, args=""):
        self.sim.run(path)

    def test(self, command):
        return bool(self.sim.execute(command.split(" "), 1, None, None))

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
        if w[0] == "block":
            return self.sim.world.at(tuple(int(v) for v in w[1:4])) or ""
        found = self.sim.select(w[1])
        if not found:
            return ""
        e, key = found[0], w[2]
        if key == "text":
            return e.get("text", "")
        if key in ("IsBaby", "CanPickUpLoot"):
            return "0b"
        if key == "PersistenceRequired":
            return "1b"
        if key == "equipment.mainhand.id":
            return '"minecraft:trident"'
        return ""

    def advance(self, ticks):
        for _ in range(ticks):
            self.tick()

    def _s(self, name):
        return self.sim.s.get((name, "st"), 0)

    def scan(self):
        sim, n = self.sim, self.n
        here = domes.sphere(self.dome)
        stands = sim.select(f"@e[tag={game.STANDIN}]")
        for e in stands:
            e["tags"].add("st.in")
        now = {id(e) for e in sim.select(f"@e[tag={game.STANDIN},{here}]")}
        sim.s["#players", "st"] = len(stands)
        for e in stands:
            if id(e) in now and id(e) not in self.inside:
                sim.run("difficulty/apply")
                sim.s["#first", "st"] = 0 if self._s(f"#was{n}") == 1 else 1
                sim.s[f"#was{n}", "st"] = 1
                sim.run(f"dome/{n}/enter", None, e)
            if id(e) not in now and id(e) in self.inside:
                sim.run(f"dome/{n}/leave", None, e)
        self.inside = now
        occ = len(now)
        sim.s[f"#occ{n}", "st"] = occ
        form, grace = self._s(f"#form{n}"), self._s(f"#grace{n}")
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
        if occ and self._s(f"#d{n}") == 1 and self._s(f"#shown{n}") != form:
            sim.s[f"#shown{n}", "st"] = form
            sim.run(f"dome/{n}/{'solo' if form == 1 else 'duo'}")
        gone = self._s(f"#gone{n}")
        if occ:
            gone = 0
        elif self._s(f"#was{n}") == 1:
            gone += 1
        sim.s[f"#gone{n}", "st"] = gone
        if gone >= game.EMPTY_AFTER:
            sim.run(f"dome/{n}/left")
        if occ:
            sim.s[f"#was{n}", "st"] = 1

    def tick(self):
        sim = self.sim
        sim.s["#scan", "st"] = self._s("#scan") + 1
        if self._s("#scan") >= game.SCAN_TICKS:
            sim.s["#scan", "st"] = 0
            self.scan()
        if self._s(f"#occ{self.n}") >= 1:
            sim.run(f"dome/{self.n}/tick")
        sim.run(f"dome/{self.n}/guard")
        sim.run("tunnel/tick")


def text_displays(sim):
    """text displays keep their text: ``data modify ... text set value``"""
    real = sim.line

    def line(command, at=None, me=None):
        m = re.match(r"data modify entity (@e\[[^ ]*\]) text set value (.*)$", command)
        if m:
            for e in sim.select(m.group(1), me):
                e["text"] = m.group(2)
            return 1
        return real(command, at, me)

    sim.line = line


def simulated():
    dome = L.DOMES[H.INDEX]
    stages = ["site", f"dome_{H.INDEX}", "tunnels", f"dome_{H.INDEX}_inside"]
    rec = B.offline_build(stages=stages, force=False)
    pack = B.new_pack("t")
    sim = Sim(pack, rec.world)
    text_displays(sim)
    for command in rec.commands:
        if command.startswith("summon"):
            sim.line(command)
    sim.run("game/load")
    sim.s["#difficulty", "st"] = 1
    for n in range(len(L.DOMES)):
        sim.s.setdefault((f"#d{n}", "st"), 1)
    x, _, z = dome.floor_centre
    rec.world.setblock((x, dome.top_y + 1, z), "minecraft:water")
    return dome, rec, pack, sim
'''


def test_station_hullbreach_simulated():
    out = run(
        SIM
        + r"""
dome, rec, pack, sim = simulated()
ctx = Ctx(sim, dome, pack)
place = H.room(dome)
n = H.INDEX
fr = place.frame

# the water by layers, as draw writes it, from the level alone: rising one
# layer at a time and jumping, every basin cell right each time
def wet_cells():
    blocks = {c: rec.world.at(c) or "" for c in H.basin(dome)}
    return {
        c for c, blk in blocks.items()
        if blk.startswith("minecraft:water") or "waterlogged=true" in blk
    }

sim.run(f"dome/{n}/reset")
assert not wet_cells()
layers = H.layers(dome)
for w in (1, 2, 3, 9, 4, 0, 6):
    sim.s["#hb.w", "st"] = w
    sim.run(f"dome/{n}/draw")
    want = {
        c
        for h, layer in layers.items()
        if h <= w
        for c in layer.open | set(layer.fittings)
    }
    want -= {c for br in place.breaches for c in br.holes}
    assert wet_cells() == want, (w, len(wet_cells() ^ want))
# a burst puts the sea in its hole whatever the level (over the walk in
# the lower two cells) and in the hull behind; four plates patch it, the
# sea still behind; restore_stage makes the live stage's own, open and
# patched, sound again, and leaves the patch of a stage held before
sim.s["#hb.w", "st"] = 3
sim.run(f"dome/{n}/draw")
low = next(br for br in place.breaches if br.level == "low")
high = next(br for br in place.breaches if br.level == "high")
sim.s["#hb.phase", "st"] = 0
for br in (low, high):
    sim.run(f"dome/{n}/crack/{br.number}/1")
    assert [rec.world.at(c) for c in br.cracks].count(H.CRACKED) == 2
    sim.run(f"dome/{n}/crack/{br.number}/3")
    assert all(rec.world.at(c) == H.CRACKED for c in br.cracks)
    assert all(rec.world.at(c) == H.GLASS for c in (*br.holes, *br.flooded))
    sim.run(f"dome/{n}/burst/{br.number}")
    assert all(rec.world.at(c) == "minecraft:water" for c in br.sources)
    dry = set(br.holes) - set(br.sources)
    assert all((rec.world.at(c) or H.AIR) == H.AIR for c in dry)
    assert all(rec.world.at(c) == H.SEA for c in br.flooded)
    sim.run(f"dome/{n}/crack/{br.number}/1")  # (no cracking an open one)
for c in high.holes:
    rec.world.setblock(c, H.PLATE)
sim.s["#hb.state", "st"], sim.s["#hb.phase", "st"] = 1, 1
sim.s["#hb.due", "st"] = 1
sim.run(f"dome/{n}/read")
assert sim.s["#hb.open", "st"] == 1 and sim.s[f"#hb.b{high.number}", "st"] == 2
sim.run(f"dome/{n}/draw")
assert all(rec.world.at(c) == H.PLATE for c in high.holes)
assert all(rec.world.at(c) == H.SEA for c in high.flooded)
assert all(rec.world.at(c) == "minecraft:water" for c in low.holes)
assert {low.number, high.number} <= set(H.ORDERS[0])
held = place.breach(H.ORDERS[1][0])
sim.s["#hb.phase", "st"] = 0
sim.run(f"dome/{n}/burst/{held.number}")
for c in held.holes:
    rec.world.setblock(c, H.PLATE)
sim.s["#hb.phase", "st"] = 1
sim.run(f"dome/{n}/read")
assert sim.s[f"#hb.b{held.number}", "st"] == 2 and sim.s["#hb.stage", "st"] == 0
sim.run(f"dome/{n}/restore_stage")
for br in (low, high):
    assert all(rec.world.at(c) == H.GLASS for c in (*br.holes, *br.flooded, *br.cracks))
    assert sim.s[f"#hb.b{br.number}", "st"] == 0
# the patch of another stage is kept, through the pump-down's redraw too,
# and neither cracks nor bursts again
for name in ("draw", "uncrack", f"crack/{held.number}/3", f"burst/{held.number}"):
    sim.run(f"dome/{n}/{name}")
    assert sim.s[f"#hb.b{held.number}", "st"] == 2, name
    assert all(rec.world.at(c) == H.PLATE for c in held.holes), name
    assert all(rec.world.at(c) == H.SEA for c in held.flooded), name
# a crack begun and its burst struck off: sound again
sim.run(f"dome/{n}/crack/{low.number}/2")
sim.run(f"dome/{n}/uncrack")
assert all(rec.world.at(c) == H.GLASS for c in low.cracks)
# a partner leaving mid-crack, with bursts still due: the crack goes too
sim.run(f"dome/{n}/crack/{low.number}/2")
sim.s["#hb.due", "st"], sim.s["#hb.form", "st"] = 3, 2
sim.run(f"dome/{n}/strike")
assert sim.s["#hb.form", "st"] == 1
assert all(rec.world.at(c) == H.GLASS for c in low.cracks)
sim.run(f"dome/{n}/reset")

# the live check, from end to end
problems = H.check(ctx)
print("PROBLEMS", problems)
assert not problems, problems
"""
    )
    assert "PROBLEMS []" in out
