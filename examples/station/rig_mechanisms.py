"""
Prove the mechanisms The Drowned Station leans on, in a rig far from the
game, on the live server (Minecraft Java 26.3)::

    STATION_DATAPACKS_DIR=/path/to/world/datapacks mciwb run rig_mechanisms.py

It must run where the world's ``datapacks`` folder can be written (the rig's
own pack, ``station_rig``, goes there and is removed again). RIG=x,y,z moves
the rig (default 2440,42,1544: the centre of the dome's floor, in a deep
cold ocean whose bed is at about y=40). WHICH=1,3 runs some of the checks.

The checks, each worked over RCON and judged by what is read back:

1. a generated datapack loads and ticks: load and tick tags, a function
   called by name, macros, ``schedule``, box selectors, and what an unloaded
   chunk does to a block change
2. a flooded glass tube is drained section by section and refilled by
   functions, behind a moving bulkhead
3. a glass dome built in the sea is cleared of water and stays dry
4. a text display showing mm:ss from a scoreboard, updated each second
5. bossbars
6. items with ``can_place_on`` and ``can_break``
7. a boat that is replaced when taken
8. names this version changed: game rules, entities, blocks, commands
   that need a player (only that they parse)

The sea round the rig is copied aside first and put back at the end, the
rig's entities, bossbar, scores, storage and datapack are removed, and its
forceloaded chunks released.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import datapack as dp  # noqa: E402

NS = "station_rig"
OBJ = "rig"
STORE = f"{NS}:rig"
GLASS = "minecraft:glass"
WATER = "minecraft:water"
AIR = "minecraft:air"
BULKHEAD = "minecraft:barrier"
WET = '{type:"minecraft:location_check",predicate:{fluid:{fluids:"#minecraft:water"}}}'
RADIUS = 16  # the dome is 32 across
SEA = 62  # the top layer of water
TUBE_LEN, SECTION = 24, 4
STATES = TUBE_LEN // SECTION  # sections drained: 0 (flooded) .. 6 (dry)

Cell = tuple[int, int, int]


def runs(cells: set[Cell]) -> list[tuple[Cell, Cell]]:
    """the cells as rows along x: (first, last) of each unbroken row"""
    out = []
    rows: dict[tuple[int, int], list[int]] = {}
    for x, y, z in cells:
        rows.setdefault((y, z), []).append(x)
    for (y, z), xs in sorted(rows.items()):
        xs.sort()
        start = prev = xs[0]
        for x in xs[1:]:
            if x != prev + 1:
                out.append(((start, y, z), (prev, y, z)))
                start = x
            prev = x
        out.append(((start, y, z), (prev, y, z)))
    return out


def box_cells(a: Cell, b: Cell) -> set[Cell]:
    return {
        (x, y, z)
        for x in range(a[0], b[0] + 1)
        for y in range(a[1], b[1] + 1)
        for z in range(a[2], b[2] + 1)
    }


def dome_cells(centre: Cell, r: int) -> tuple[set[Cell], set[Cell], set[Cell]]:
    """a dome of diameter 2r standing on the level of ``centre``: its glass
    shell, the cells inside it, and the floor under both (one level down)"""
    ox, oy, oz = centre
    inside = {
        (dx, dy, dz)
        for dx in range(-r, r)
        for dz in range(-r, r)
        for dy in range(r)
        if (dx + 0.5) ** 2 + dy**2 + (dz + 0.5) ** 2 <= r * r
    }
    # water passes through faces only, so a shell cell is one with a face
    # (sideways or up) on the outside
    faces = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0)]
    shell = {
        c
        for c in inside
        if any((c[0] + f[0], c[1] + f[1], c[2] + f[2]) not in inside for f in faces)
    }

    def world(cells: set[Cell]) -> set[Cell]:
        return {(ox + x, oy + y, oz + z) for x, y, z in cells}

    floor = {(ox + x, oy - 1, oz + z) for x, y, z in inside if y == 0}
    return world(shell), world(inside - shell), floor


class Rig:
    def __init__(self, world, datapacks_dir: Path) -> None:
        self.world = world
        self.dir = datapacks_dir
        self.results: list[tuple[str, bool]] = []
        x, y, z = (int(v) for v in os.environ.get("RIG", "2440,42,1544").split(","))
        self.o = (x, y, z)
        # the chunks the rig works in
        self.load_box = (x - 88, z - 24, x + 39, z + 103)
        # dome: the box copied aside reaches from under its floor to the sea's top
        self.shell, self.interior, self.floor = dome_cells(self.o, RADIUS)
        self.dome_box = ((x - RADIUS, y - 1, z - RADIUS), (x + 15, SEA, z + 15))
        # tube: 5 x 5 inside, 24 long along x, glass all round and at both ends
        tx, ty, tz = x - 64, y + 8, z - 16
        self.tube_in = ((tx, ty + 1, tz + 1), (tx + TUBE_LEN - 1, ty + 5, tz + 5))
        self.tube_out = ((tx - 1, ty, tz), (tx + TUBE_LEN, ty + 6, tz + 6))
        self.tube_shell = box_cells(*self.tube_out) - box_cells(*self.tube_in)
        # things in the air above the dome, and the boat's spot on the sea
        self.desk = (x, 90, z)
        self.boat = (x - 20, SEA + 1, z + 46)
        self.saved: list[tuple[Cell, Cell, int]] = []
        self.pack = self.make_pack()

    # -- talking to the server ---------------------------------------------

    def cmd(self, command: str, expect: str | None = None) -> str:
        """run a command; with ``expect`` (a pattern the reply must contain)
        it is sent again if another client garbled the reply, so only for
        commands that are safe to send twice"""
        if expect is None:
            return self.world.cmd(command)
        return self.world.cmd(command, f"(?s).*(?:{expect}).*")

    def check(self, name: str, ok: bool, detail: object = "") -> bool:
        self.results.append((name, bool(ok)))
        tail = f"  [{detail}]" if detail != "" else ""
        print(("PASS " if ok else "FAIL ") + name + tail, flush=True)
        return bool(ok)

    def note(self, text: str) -> None:
        print("     " + text, flush=True)

    def gametime(self) -> int:
        r = self.cmd("time query gametime", r"\d+ tick")
        return int(re.search(r"(\d+) tick", r).group(1))  # type: ignore[union-attr]

    def tick(self, ticks: int) -> None:
        """let the game run at least ``ticks`` ticks (sprinted: the server
        may be paused with nobody online, or may be running)"""
        end = self.gametime() + ticks
        left = ticks
        stop = time.time() + 60
        while left > 0:
            if time.time() > stop:
                raise RuntimeError(f"the game did not advance {ticks} ticks")
            step = min(left, 150)
            self.cmd(f"tick sprint {step}")
            deadline = time.time() + 10
            while time.time() < deadline:
                time.sleep(0.05)
                if "sprinting" not in self.cmd("tick query", "game is"):
                    break
            left = end - self.gametime()

    def score(self, name: str) -> int | None:
        r = self.cmd(
            f"scoreboard players get {name} {OBJ}", r"has -?\d+|Can't get|Unknown"
        )
        m = re.search(r"has (-?\d+)", r)
        return int(m.group(1)) if m else None

    def set_score(self, name: str, value: int) -> None:
        self.cmd(f"scoreboard players set {name} {OBJ} {value}", "Set ")

    def is_block(self, p: Cell, block: str) -> bool:
        r = self.cmd(f"execute if block {p[0]} {p[1]} {p[2]} {block}", "Test ")
        return "Test passed" in r

    def count(self, selector: str) -> int:
        r = self.cmd(f"execute if entity {selector}", r"Test (passed|failed)")
        m = re.search(r"Count: (\d+)", r)
        return int(m.group(1)) if m else (1 if "passed" in r else 0)

    def fill(self, a: Cell, b: Cell, block: str, how: str = "") -> str:
        return self.cmd(dp.fill(a, b, block, how), "fill|Fill|No blocks|not loaded")

    def fill_cells(self, cells: set[Cell], block: str) -> None:
        for a, b in runs(cells):
            self.fill(a, b, block)

    # -- copying the site aside and putting it back -------------------------

    def save(self, a: Cell, b: Cell, lift: int) -> None:
        """copy the box a..b into a glass case ``lift`` blocks higher"""
        ca = (a[0] - 1, a[1] + lift - 1, a[2] - 1)
        cb = (b[0] + 1, b[1] + lift + 1, b[2] + 1)
        print(self.fill(ca, cb, GLASS))
        self.saved.append((a, b, lift))
        print(
            self.cmd(
                f"clone {a[0]} {a[1]} {a[2]} {b[0]} {b[1]} {b[2]} "
                f"{a[0]} {a[1] + lift} {a[2]}"
            )
        )

    def restore(self, a: Cell, b: Cell, lift: int) -> bool:
        """put the copy back, see that the two match, remove the case"""
        box = f"{a[0]} {a[1] + lift} {a[2]} {b[0]} {b[1] + lift} {b[2]}"
        print(self.cmd(f"clone {box} {a[0]} {a[1]} {a[2]}"))
        r = self.cmd(f"execute if blocks {box} {a[0]} {a[1]} {a[2]} all", "Test ")
        ca = (a[0] - 1, a[1] + lift - 1, a[2] - 1)
        cb = (b[0] + 1, b[1] + lift + 1, b[2] + 1)
        self.fill(ca, cb, AIR)
        return "passed" in r

    # -- the rig's datapack --------------------------------------------------

    def make_pack(self) -> dp.Pack:
        pack = dp.Pack(NS, NS, "The Drowned Station: mechanism rig")
        pack.objectives({OBJ: "dummy"})
        pack.constants(OBJ, 10, 60)
        add = f"run scoreboard players add {{}} {OBJ} 1"

        # 1: the basics
        pack.function("on_load", [f"scoreboard players add #loads {OBJ} 1"], load=True)
        pack.function(
            "tick",
            [
                f"scoreboard players add #ticks {OBJ} 1",
                f"execute if score #timer_on {OBJ} matches 1 "
                f"run function {NS}:timer/tick",
                f"execute if score #boat_on {OBJ} matches 1 "
                f"run function {NS}:boat/keep",
            ],
            tick=True,
        )
        pack.function("hello", [f"scoreboard players set #hello {OBJ} 42"])
        pack.function("macro/set", [f"$scoreboard players set #macro {OBJ} $(value)"])
        pack.function("sched/later", [f"scoreboard players set #sched {OBJ} 1"])
        x, y, z = self.desk
        sel = dp.box_selector((x, y, z), (x + 4, y + 2, z + 4))
        pack.function(
            "sel/count",
            [
                f"execute store result score #sel {OBJ} "
                f"if entity @e[type=minecraft:marker,tag=rig_sel,{sel}]",
                f"execute store result score #players {OBJ} "
                f"if entity @a[gamemode=adventure,{sel}]",
                f"scoreboard players set #sel_ran {OBJ} 1",
            ],
        )
        pack.function(
            "far",
            [
                f"execute store success score #far {OBJ} "
                "run setblock 30000 100 30000 minecraft:stone",
                f"execute store success score #near {OBJ} "
                f"run setblock {x} {y + 4} {z} minecraft:stone",
            ],
        )

        # 2: the tube. State d = the first d sections are dry; a bulkhead
        # fills the first slice of the flooded part. Every state is written
        # whole, in one tick, so each can follow any other.
        (x1, y1, z1), (x2, y2, z2) = self.tube_in
        for d in range(STATES + 1):
            cut = x1 + d * SECTION
            lines = [f"scoreboard players set #tube {OBJ} {d}"]
            if d < STATES:
                wet = ((cut, y1, z1), (x2, y2, z2))
                lines += [
                    dp.fill(*wet, WATER, f"replace {WATER}"),  # flowing -> source
                    dp.fill(*wet, WATER, f"replace {AIR}"),
                    dp.fill(*wet, WATER, f"replace {BULKHEAD}"),
                ]
            if d > 0:
                dry = ((x1, y1, z1), (cut - 1, y2, z2))
                lines += [
                    dp.fill(*dry, AIR, f"replace {WATER}"),
                    dp.fill(*dry, AIR, f"replace {BULKHEAD}"),
                ]
            if 0 < d < STATES:
                lines.append(
                    dp.fill((cut, y1, z1), (cut, y2, z2), BULKHEAD, f"replace {WATER}")
                )
            pack.function(f"tube/state_{d}", lines)
        pack.function(
            "tube/drain",
            [f"function {NS}:tube/state_1"]
            + [
                f"schedule function {NS}:tube/state_{d} {(d - 1) * 10}t"
                for d in range(2, STATES + 1)
            ],
        )
        pack.function(
            "tube/refill",
            [f"function {NS}:tube/state_{STATES - 1}"]
            + [
                f"schedule function {NS}:tube/state_{d} {(STATES - 1 - d) * 10}t"
                for d in range(STATES - 2, -1, -1)
            ],
        )
        # drain a section with no bulkhead, to see what the water does
        pack.function(
            "tube/bare",
            [
                dp.fill(
                    (x1, y1, z1), (x1 + SECTION - 1, y2, z2), AIR, f"replace {WATER}"
                )
            ],
        )
        names = ["#t_water", "#t_source", "#t_air", "#t_bulk", "#t_shell"]
        lines = [f"scoreboard players set {n} {OBJ} 0" for n in names]
        for cx, cy, cz in sorted(box_cells(*self.tube_in)):
            at = f"execute if block {cx} {cy} {cz}"
            lines += [
                f"{at} {WATER} {add.format('#t_water')}",
                f"{at} {WATER}[level=0] {add.format('#t_source')}",
                f"{at} {AIR} {add.format('#t_air')}",
                f"{at} {BULKHEAD} {add.format('#t_bulk')}",
            ]
        for cx, cy, cz in sorted(self.tube_shell):
            lines.append(
                f"execute if block {cx} {cy} {cz} {GLASS} {add.format('#t_shell')}"
            )
        pack.function("tube/count", lines)

        # 3: the dome: counts over every cell inside it
        names = ["#d_notair", "#d_wet", "#d_shell", "#d_floor"]
        lines = [f"scoreboard players set {n} {OBJ} 0" for n in names]
        for cx, cy, cz in sorted(self.interior):
            lines += [
                f"execute unless block {cx} {cy} {cz} {AIR} {add.format('#d_notair')}",
                f"execute positioned {cx} {cy} {cz} if predicate {WET} "
                f"{add.format('#d_wet')}",
            ]
        for cx, cy, cz in sorted(self.shell):
            lines.append(
                f"execute if block {cx} {cy} {cz} {GLASS} {add.format('#d_shell')}"
            )
        for cx, cy, cz in sorted(self.floor):
            lines.append(
                f"execute if block {cx} {cy} {cz} minecraft:polished_deepslate "
                f"{add.format('#d_floor')}"
            )
        pack.function("dome/count", lines)
        census = {
            "#c_water": [WATER],
            "#c_kelp": ["minecraft:kelp", "minecraft:kelp_plant"],
            "#c_grass": ["minecraft:seagrass", "minecraft:tall_seagrass"],
            "#c_loose": ["minecraft:sand", "minecraft:gravel"],
        }
        lines = [f"scoreboard players set {n} {OBJ} 0" for n in census]
        for cx, cy, cz in sorted(self.interior | self.shell):
            for name, blocks in census.items():
                lines += [
                    f"execute if block {cx} {cy} {cz} {b} {add.format(name)}"
                    for b in blocks
                ]
        pack.function("dome/census", lines)

        # 4: the timer: every 20 ticks add a second and rewrite the display
        pack.function(
            "timer/tick",
            [
                f"scoreboard players add #sub {OBJ} 1",
                f"execute if score #sub {OBJ} matches 20.. "
                f"run function {NS}:timer/second",
            ],
        )
        pack.function(
            "timer/second",
            [
                f"scoreboard players set #sub {OBJ} 0",
                f"scoreboard players add #secs {OBJ} 1",
                *dp.mmss_lines("#secs", OBJ, STORE, "time"),
                f"function {NS}:timer/show with storage {STORE} time",
                f"execute store result bossbar {NS}:bar value "
                f"run scoreboard players get #mm.s {OBJ}",
            ],
        )
        pack.function(
            "timer/show",
            [
                "$data modify entity @e[type=minecraft:text_display,tag=rig_timer,"
                'limit=1] text set value "$(m):$(t)$(o)"'
            ],
        )

        # 7: the boat
        pack.function(
            "boat/keep",
            [
                "execute at @e[type=minecraft:marker,tag=rig_boat_spot] "
                "unless entity @e[type=#minecraft:boat,distance=..4] "
                'run summon minecraft:oak_boat ~ ~ ~ {Tags:["rig_boat"]}'
            ],
        )
        return pack

    # -- 1 -------------------------------------------------------------------

    def check_datapack(self) -> None:
        print("-- 1 datapack", flush=True)
        log = dp.server_log(self.dir)
        size = log.stat().st_size if log else 0
        before = self.cmd("datapack list")
        folder = dp.install(self.world, self.pack, self.dir)
        listing = self.cmd("datapack list enabled")
        self.check(
            "1a pack written, found and enabled by reload alone",
            f"file/{NS}" in listing and f"file/{NS}" not in before,
            listing,
        )
        n = sum(len(v) for v in self.pack.functions.values())
        self.note(f"{len(self.pack.functions)} functions, {n} lines, in {folder.name}/")
        if log:
            errors = dp.load_errors(log, size)
            self.check("1b no data pack errors in the server log", not errors, errors)
        else:
            self.note("server log not found beside the world: not checked")
        self.check("1c load function ran once", self.score("#loads") == 1)

        t0 = self.score("#ticks") or 0
        time.sleep(1.0)
        idle = (self.score("#ticks") or 0) - t0
        self.note(
            f"with nobody online the tick function ran {idle} times in 1 s "
            "of doing nothing"
        )
        t0 = self.score("#ticks") or 0
        g0 = self.gametime()
        self.tick(40)
        t1, g1 = self.score("#ticks") or 0, self.gametime()
        self.check(
            "1d tick function runs once a game tick (tick sprint 40)",
            t1 - t0 >= 40 and abs((t1 - t0) - (g1 - g0)) <= 3,
            f"score +{t1 - t0}, game time +{g1 - g0}",
        )

        self.cmd(f"function {NS}:hello")
        self.check("1e function called by name", self.score("#hello") == 42)

        self.cmd(f"function {NS}:macro/set {{value:7}}")
        inline = self.score("#macro")
        self.cmd(f"data modify storage {STORE} args set value {{value:11}}")
        self.cmd(f"function {NS}:macro/set with storage {STORE} args")
        self.check(
            "1f macro function, inline arguments and 'with storage'",
            inline == 7 and self.score("#macro") == 11,
            f"{inline}, {self.score('#macro')}",
        )

        self.set_score("#sched", 0)
        r = self.cmd(f"schedule function {NS}:sched/later 60t")
        early = self.score("#sched")
        self.tick(65)
        self.check(
            "1g schedule function runs later, not at once",
            early == 0 and self.score("#sched") == 1,
            r,
        )

        x, y, z = self.desk
        for px, tag in ((x + 2, "in"), (x + 9, "out")):
            self.cmd(
                f"summon minecraft:marker {px}.5 {y + 1} {z + 2}.5 "
                f'{{Tags:["rig_sel","rig_{tag}"]}}'
            )
        self.tick(2)
        self.cmd(f"function {NS}:sel/count")
        self.check(
            "1h box selectors (x,y,z,dx,dy,dz) parse and count what is inside",
            self.score("#sel") == 1
            and self.score("#players") == 0
            and self.score("#sel_ran") == 1,
            f"markers in box {self.score('#sel')} of 2, players {self.score('#players')}",
        )

        self.cmd(f"function {NS}:far")
        near = self.is_block((x, y + 4, z), "minecraft:stone")
        self.check(
            "1i a function's block change works in a loaded chunk, "
            "fails in an unloaded one",
            self.score("#far") == 0 and self.score("#near") == 1 and near,
            f"far {self.score('#far')}, near {self.score('#near')}",
        )

        # replacing the pack: a rebuilt pack takes over on reload
        old = self.pack.stamp
        self.pack.stamp = old + "b"
        self.pack.functions["hello"] = [f"scoreboard players set #hello {OBJ} 43"]
        dp.install(self.world, self.pack, self.dir)
        self.cmd(f"function {NS}:hello")
        # other packs (the station's own) may be installed beside the rig's
        only = sorted(p.name for p in self.dir.iterdir() if p.name.startswith(NS))
        self.check(
            "1j a rebuilt pack replaces the old one (reload runs load again)",
            self.score("#hello") == 43 and self.score("#loads") == 2 and only == [NS],
            f"hello {self.score('#hello')}, loads {self.score('#loads')}, {only}",
        )

        # a pack with a bad line: the game loads the rest and says nothing
        # over RCON; install reads the server's log and refuses it
        if log:
            broken = dp.Pack(NS, NS, "broken on purpose")
            broken.function("ticker", ["notacommand 1"], tick=True)
            try:
                dp.install(self.world, broken, self.dir)
                said = "installed without complaint"
            except dp.PackError as e:
                said = str(e)
            self.pack.stamp = old + "c"
            dp.install(self.world, self.pack, self.dir)
            self.check(
                "1k a pack with a bad function is caught by install (from the log)",
                "Failed to load function" in said and "minecraft:tick" in said,
                said.replace("\n", " "),
            )

    # -- 2 -------------------------------------------------------------------

    def tube_counts(self) -> dict[str, int | None]:
        self.cmd(f"function {NS}:tube/count")
        return {
            k: self.score(f"#t_{k}")
            for k in ("water", "source", "air", "bulk", "shell")
        }

    def tube_state_ok(self, c: dict, d: int) -> bool:
        cells = 25 * TUBE_LEN
        bulk = 25 if 0 < d < STATES else 0
        return (
            c["air"] == 100 * d
            and c["bulk"] == bulk
            and c["source"] == cells - 100 * d - bulk
            and c["water"] == c["source"]
            and c["shell"] == len(self.tube_shell)
        )

    def check_tube(self) -> None:
        print("-- 2 flooded tube", flush=True)
        self.save(*self.tube_out, 100)
        self.fill(*self.tube_out, GLASS)
        self.fill(*self.tube_in, WATER)
        self.tick(10)
        c = self.tube_counts()
        self.check("2a tube built full of water sources", self.tube_state_ok(c, 0), c)

        # what happens with no bulkhead
        self.cmd(f"function {NS}:tube/bare")
        self.tick(60)
        c = self.tube_counts()
        self.note(
            "one section drained with no bulkhead, 60 ticks on: "
            f"{c['water'] - c['source']} flowing water, {c['air']} air of 100"  # type: ignore[operator]
        )
        self.check(
            "2b without a bulkhead the flooded part runs into the drained section",
            (c["water"] or 0) > (c["source"] or 0),
            c,
        )
        self.cmd(f"function {NS}:tube/state_0")
        self.tick(10)
        c = self.tube_counts()
        self.check(
            "2c state 0 puts it right (all sources again)", c["source"] == 600, c
        )

        self.cmd(f"function {NS}:tube/drain")
        self.tick(25)
        d, c = self.score("#tube"), self.tube_counts()
        d2 = self.score("#tube")
        ok = d == d2 and d is not None and 0 < d < STATES and self.tube_state_ok(c, d)
        if d != d2:  # a step ran between the two reads: look again
            self.tick(1)
            d, c = self.score("#tube"), self.tube_counts()
            ok = d is not None and self.tube_state_ok(c, d)
        self.check(
            f"2d part drained ({d} of {STATES} sections): dry part all air, "
            "no flowing water, bulkhead in place",
            ok,
            c,
        )
        self.tick(40)
        d, c = self.score("#tube"), self.tube_counts()
        self.check(
            "2e drained by schedule: every cell air, shell whole",
            d == STATES and self.tube_state_ok(c, STATES),
            c,
        )
        self.tick(150)
        c = self.tube_counts()
        (x1, y1, z1), (x2, y2, z2) = self.tube_in
        line = [self.is_block((x, y1 + 2, z1 + 2), AIR) for x in range(x1, x2 + 1)]
        ends = self.is_block((x2 + 2, y1 + 2, z1 + 2), WATER)
        self.check(
            "2f still dry 150 ticks later, with the sea outside its end",
            self.tube_state_ok(c, STATES) and all(line) and ends,
            f"{c}, centre line air {sum(line)} of {len(line)}, sea beyond end {ends}",
        )

        self.cmd(f"function {NS}:tube/refill")
        self.tick(25)
        d, c = self.score("#tube"), self.tube_counts()
        if d != self.score("#tube"):
            self.tick(1)
            d, c = self.score("#tube"), self.tube_counts()
        self.check(
            f"2g part refilled ({d} of {STATES} dry): no flowing water",
            d is not None and self.tube_state_ok(c, d),
            c,
        )
        self.tick(40)
        self.tick(100)
        d, c = self.score("#tube"), self.tube_counts()
        line = [
            self.is_block((x, y1 + 2, z1 + 2), f"{WATER}[level=0]")
            for x in range(x1, x2 + 1)
        ]
        self.check(
            "2h refilled: every cell a water source, no bulkhead left",
            d == 0 and self.tube_state_ok(c, 0) and all(line),
            f"{c}, centre line sources {sum(line)} of {len(line)}",
        )

    # -- 3 -------------------------------------------------------------------

    def dome_counts(self) -> dict[str, int | None]:
        self.cmd(f"function {NS}:dome/count")
        return {k: self.score(f"#d_{k}") for k in ("notair", "wet", "shell", "floor")}

    def check_dome(self) -> None:
        print("-- 3 dry dome", flush=True)
        ox, oy, oz = self.o
        (ax, ay, az), (bx, by, bz) = self.dome_box
        self.save(*self.dome_box, 100)
        self.cmd(f"function {NS}:dome/census")
        census = {k: self.score(f"#c_{k}") for k in ("water", "kelp", "grass", "loose")}
        cells = len(self.interior) + len(self.shell)
        top = (ox, oy + RADIUS, oz)
        self.check(
            "3a the site is under water",
            (census["water"] or 0) > cells // 2 and self.is_block(top, WATER),
            f"of {cells} cells before the build: {census}",
        )

        box = f"x={ax},y={ay},z={az},dx={bx - ax},dy={by - ay},dz={bz - az}"
        self.fill_cells(self.floor, "minecraft:polished_deepslate")
        self.fill_cells(self.shell, GLASS)
        c = self.dome_counts()
        self.note(f"floor and shell placed, inside not yet cleared: {c}")
        # the obvious way: clear the inside row by row. The game ticks
        # between the commands, the water left runs into the rows already
        # cleared, and where two sources meet it makes new sources
        rows = runs(self.interior)
        for n, (a, b) in enumerate(rows):
            self.fill(a, b, AIR)
            if n == len(rows) // 2:
                self.tick(10)  # as a slow build would let pass
        self.tick(40)
        naive = self.dome_counts()
        self.note(
            "inside cleared to air row by row, 40 ticks on: "
            f"{naive['wet']} cells wet again (0 only if the game did not tick)"
        )
        # the way that works whatever the game does meanwhile: make the
        # dome solid glass first (nothing to flow into), then hollow it
        t = time.time()
        self.fill_cells(self.shell | self.interior, GLASS)
        self.fill_cells(self.interior, AIR)
        n = len(runs(self.shell | self.interior)) + len(runs(self.interior))
        self.note(
            f"made solid then hollowed: {n} fill commands in {time.time() - t:.1f} s"
        )
        self.tick(5)
        c = self.dome_counts()
        ok = (
            c["notair"] == 0
            and c["wet"] == 0
            and c["shell"] == len(self.shell)
            and c["floor"] == len(self.floor)
        )
        self.check(
            f"3b dome made solid then hollowed: {len(self.interior)} cells all "
            "air, none wet or waterlogged",
            ok,
            c,
        )
        self.tick(150)
        self.tick(50)
        c2 = self.dome_counts()
        items = self.count(f"@e[type=minecraft:item,{box}]")
        falling = self.count(f"@e[type=minecraft:falling_block,{box}]")
        self.check(
            "3c nothing leaks in 200 ticks, with the sea over the top",
            c2 == c and ok and self.is_block(top, WATER),
            c2,
        )
        self.note(
            f"dropped items in the dome's box afterwards: {items}; "
            f"falling blocks: {falling}"
        )

        # the wet count sees a waterlogged block, and what it leaks
        p = (ox, oy + 3, oz)
        self.cmd(f"setblock {p[0]} {p[1]} {p[2]} minecraft:oak_slab[waterlogged=true]")
        c = self.dome_counts()
        one = c["wet"] == 1 and c["notair"] == 1
        self.tick(40)
        leak = self.dome_counts()
        self.cmd(f"setblock {p[0]} {p[1]} {p[2]} {AIR}")
        self.tick(100)
        after = self.dome_counts()
        self.check(
            "3d a waterlogged block inside is counted, leaks, and the leak "
            "dries up once it is removed",
            one
            and (leak["wet"] or 0) > 1
            and after["wet"] == 0
            and after["notair"] == 0,
            f"placed {c['wet']}, 40 ticks on {leak['wet']}, removed {after['wet']}",
        )

        r = self.cmd(
            f"fill {ox} 200 {oz} {ox + 32} 232 {oz + 32} {AIR} replace minecraft:bedrock"
        )
        rule = self.cmd("gamerule max_block_modifications")
        self.check(
            "3e fill refuses more than 32768 blocks (33 x 33 x 33 asked)",
            "Too many blocks" in r and "32768" in r and "32768" in rule,
            f"{r} / {rule}",
        )

    # -- 4 -------------------------------------------------------------------

    def check_text(self) -> None:
        print("-- 4 text display timer", flush=True)
        x, y, z = self.desk
        r = self.cmd(
            f"summon minecraft:text_display {x} {y + 2} {z} "
            '{Tags:["rig_timer"],text:"--:--",billboard:"center"}'
        )
        self.tick(2)
        get = (
            "data get entity @e[type=minecraft:text_display,tag=rig_timer,limit=1] text"
        )
        first = self.cmd(get, "entity data|No entity")
        self.set_score("#sub", 0)
        self.set_score("#secs", 754)
        self.set_score("#timer_on", 1)
        seen = []
        for _ in range(3):
            self.tick(20)
            a = self.score("#secs") or 0
            text = self.cmd(get, "entity data|No entity")
            b = self.score("#secs") or 0
            want = {f'"{s // 60}:{s % 60 // 10}{s % 10}"' for s in (a, b)}
            seen.append((a, text.split(": ", 1)[-1], any(w in text for w in want)))
        self.set_score("#timer_on", 0)
        self.check(
            "4a text display rewritten as m:ss from a score each second",
            "--:--" in first and all(s[2] for s in seen) and seen[-1][0] >= 757,
            f"{r}; (seconds, text read back) {[(s[0], s[1]) for s in seen]}",
        )
        self.cmd(f"scoreboard players set #secs {OBJ} 59")
        self.cmd(f"function {NS}:timer/second")
        text = self.cmd(get, "entity data|No entity")
        self.check("4b the minute rolls over (59 s + 1)", '"1:00"' in text, text)

    # -- 5 -------------------------------------------------------------------

    def check_bossbar(self) -> None:
        print("-- 5 bossbars", flush=True)
        bar = f"{NS}:bar"
        replies = [
            self.cmd(f'bossbar add {bar} "Reset"'),
            self.cmd(f'bossbar set {bar} name {{text:"Reset: 1 of 2",color:"gold"}}'),
            self.cmd(f"bossbar set {bar} max 60"),
            self.cmd(f"bossbar set {bar} value 45"),
            self.cmd(f"bossbar set {bar} color yellow"),
            self.cmd(f"bossbar set {bar} style notched_6"),
            self.cmd(f"bossbar set {bar} visible false"),
        ]
        players = self.cmd(f"bossbar set {bar} players @a[gamemode=adventure]")
        got = {
            k: self.cmd(f"bossbar get {bar} {k}", "bossbar")
            for k in ("value", "max", "visible", "players")
        }
        listing = self.cmd("bossbar list")
        ok = (
            "Created" in replies[0]
            and "renamed" in replies[1]
            and "value of 45" in got["value"]
            and "maximum of 60" in got["max"]
            and "hidden" in got["visible"]
            and "Reset: 1 of 2" in listing
        )
        self.check("5a bossbar made, set and read back", ok, f"{got}; {listing}")
        self.note(f"set players with nobody online replies: {players}")
        self.cmd(f"scoreboard players set #secs {OBJ} 83")
        self.cmd(f"function {NS}:timer/second")
        r = self.cmd(f"bossbar get {bar} value", "bossbar")
        self.check(
            "5b a function sets the bar's value from a score (execute store)",
            "value of 24" in r,
            r,
        )
        r = self.cmd(f"bossbar remove {bar}")
        listing = self.cmd("bossbar list")
        self.check(
            "5c bossbar removed", "Removed" in r and "no custom bossbars" in listing, r
        )

    # -- 6 -------------------------------------------------------------------

    def check_items(self) -> None:
        print("-- 6 can_place_on and can_break", flush=True)
        x, y, z = self.desk
        at = f"{x} {y} {z}"
        sign = (
            'minecraft:oak_sign[minecraft:can_place_on={blocks:"minecraft:gold_block"}]'
        )
        pick = (
            "minecraft:iron_pickaxe[minecraft:can_break="
            '{blocks:["minecraft:cut_copper","minecraft:waxed_cut_copper"]},'
            'minecraft:tooltip_display={hidden_components:["minecraft:can_break"]}]'
        )
        self.cmd(f"setblock {at} minecraft:barrel")
        a = self.cmd(f"item replace block {at} container.0 with {sign}")
        b = self.cmd(f"item replace block {at} container.1 with {pick}")
        old = self.cmd(
            f"item replace block {at} container.2 with minecraft:oak_sign"
            '[can_place_on={predicates:[{blocks:"minecraft:gold_block"}]}]'
        )
        items = self.cmd(f"data get block {at} Items", "block data")
        self.check(
            "6a item argument with can_place_on / can_break is taken and stored",
            'id: "minecraft:oak_sign"' in items
            and '"minecraft:can_place_on": {blocks: "minecraft:gold_block"}' in items
            and '"minecraft:can_break": {blocks: ["minecraft:cut_copper", '
            '"minecraft:waxed_cut_copper"]}'
            in items,
            items,
        )
        self.check(
            "6b the form before 1.21.5 ({predicates:[...]}) is refused",
            "Replaced" in a and "Replaced" in b and "Replaced" not in old,
            old,
        )
        self.cmd(
            f"summon minecraft:item {x} {y + 1} {z} "
            '{Tags:["rig_item"],NoGravity:1b,PickupDelay:32767,Item:{id:'
            '"minecraft:oak_sign",count:1,components:{"minecraft:can_place_on":'
            '{blocks:"minecraft:gold_block"}}}}'
        )
        self.tick(2)
        r = self.cmd(
            "data get entity @e[type=minecraft:item,tag=rig_item,limit=1] Item",
            "entity data|No entity",
        )
        self.check(
            "6c the same component as NBT on a summoned item",
            '"minecraft:can_place_on": {blocks: "minecraft:gold_block"}' in r,
            r,
        )
        r = self.cmd(f"give @a[gamemode=adventure] {sign}")
        self.check(
            "6d give with the component parses (no player to take it)",
            "No player was found" in r,
            r,
        )

    # -- 7 -------------------------------------------------------------------

    def check_boat(self) -> None:
        print("-- 7 boat replaced when taken", flush=True)
        x, y, z = self.boat
        sea = self.is_block((x, SEA, z), WATER) and self.is_block((x, y, z), AIR)
        r = self.cmd(f"summon minecraft:boat {x} {y} {z}")
        self.check(
            "7a minecraft:boat is gone; the tag #minecraft:boat and "
            "minecraft:oak_boat exist",
            "Can't find element" in r and sea,
            r,
        )
        self.cmd(f'summon minecraft:marker {x}.5 {y} {z}.5 {{Tags:["rig_boat_spot"]}}')
        self.tick(2)
        near = f"@e[type=#minecraft:boat,x={x}.5,y={y},z={z}.5,distance=..4]"
        every = "@e[type=minecraft:oak_boat,tag=rig_boat]"
        before = self.count(every)
        self.set_score("#boat_on", 1)
        self.tick(5)
        first = (self.count(near), self.count(every))
        self.tick(150)
        later = (self.count(near), self.count(every))
        self.check(
            "7b one boat appears at the marker, and only one, 150 ticks on",
            before == 0 and first == (1, 1) and later == (1, 1),
            f"(near, all) at 5 ticks {first}, at 155 {later}",
        )
        self.cmd(f"tp {near} {x + 30}.5 {y} {z}.5")
        self.tick(5)
        moved = (self.count(near), self.count(every))
        self.check(
            "7c boat taken 30 blocks away: a new one at the marker",
            moved == (1, 2),
            f"(near, all) {moved}",
        )
        self.cmd(f"kill {near}")
        self.tick(5)
        killed = (self.count(near), self.count(every))
        self.check(
            "7d boat destroyed: a new one at the marker",
            killed == (1, 2),
            f"(near, all) {killed}",
        )
        self.set_score("#boat_on", 0)

    # -- 8 -------------------------------------------------------------------

    def check_names(self) -> None:
        print("-- 8 names in this version", flush=True)
        rules = {
            "keep_inventory": "keepInventory",
            "mob_griefing": "mobGriefing",
            "spawn_monsters": "doMobSpawning",
            "spawn_mobs": "doMobSpawning",
            "fire_spread_radius_around_player": "doFireTick",
            "max_block_modifications": "commandModificationBlockLimit",
            "max_command_sequence_length": "maxCommandChainLength",
            "immediate_respawn": "doImmediateRespawn",
            "advance_time": "doDaylightCycle",
            "advance_weather": "doWeatherCycle",
        }
        now, old = {}, {}
        for new, was in rules.items():
            r = self.cmd(f"gamerule {new}", "Game rule|Incorrect|Unknown")
            m = re.search(r"currently set to (\S+)", r)
            now[new] = m.group(1) if m else None
            old[was] = "currently set" in self.cmd(f"gamerule {was}")
        self.check(
            "8a game rules have snake_case names; the camelCase ones are refused",
            all(v is not None for v in now.values()) and not any(old.values()),
            now,
        )
        self.rules_seen = now

        x, y, z = self.desk
        blocks = [
            "waxed_copper_block", "waxed_exposed_copper", "waxed_weathered_copper",
            "waxed_oxidized_copper", "waxed_cut_copper", "waxed_copper_grate",
            "waxed_copper_door", "waxed_copper_trapdoor", "waxed_copper_bulb",
            "lightning_rod", "iron_chain", "copper_chain", "copper_bars",
            "copper_lantern", "dark_oak_planks", "deepslate_tiles",
            "polished_blackstone", "iron_bars", "gold_block", "glass",
            "tinted_glass", "light_blue_stained_glass", "sea_lantern", "barrier",
            "light", "oak_wall_sign", "lectern", "polished_deepslate",
        ]  # fmt: skip
        bad = [
            b
            for b in blocks
            if "Test"
            not in self.cmd(
                f"execute if block {x} 300 {z} minecraft:{b}", "Test|Unknown"
            )
        ]
        gone = self.cmd(f"execute if block {x} 300 {z} minecraft:chain")
        self.check(
            f"8b the {len(blocks)} block names of the plan's look exist",
            not bad and "Unknown block" in gone,
            f"missing {bad}; minecraft:chain: {gone[:40]}",
        )

        # an automaton and the boss's mount, as the plan summons them
        self.cmd(
            f"summon minecraft:zombie {x} {y + 6} {z} "
            '{Tags:["rig_mob"],NoAI:1b,NoGravity:1b,IsBaby:0b,CanPickUpLoot:0b,'
            'PersistenceRequired:1b,CustomName:"Automaton",'
            'equipment:{head:{id:"minecraft:copper_helmet",count:1},'
            'mainhand:{id:"minecraft:iron_sword",count:1}},'
            "drop_chances:{head:0f,mainhand:0f}}"
        )
        self.cmd(
            f"summon minecraft:ravager {x + 3} {y + 6} {z} "
            '{Tags:["rig_mob"],NoAI:1b,NoGravity:1b,Passengers:[{id:'
            '"minecraft:vindicator",Tags:["rig_mob","rig_rider"],NoAI:1b}]}'
        )
        self.tick(2)
        eq = self.cmd(
            "data get entity @e[type=minecraft:zombie,tag=rig_mob,limit=1] equipment",
            "entity data|No entity",
        )
        name = self.cmd(
            "data get entity @e[type=minecraft:zombie,tag=rig_mob,limit=1] CustomName",
            "entity data|No entity",
        )
        riders = self.count("@e[type=minecraft:vindicator,tag=rig_rider]")
        difficulty = self.cmd("difficulty")
        self.check(
            "8c a mob summoned with 'equipment' and a name, a ravager with a rider",
            "copper_helmet" in eq and "Automaton" in name and riders == 1,
            f"{eq.split(': ', 1)[-1]}; {name.split(': ', 1)[-1]}; {difficulty}",
        )
        self.cmd("kill @e[tag=rig_mob]")

        who = "@a[gamemode=adventure,x=0,y=0,z=0,dx=5,dy=5,dz=5]"
        probes = [
            f"spawnpoint {who} {x} {y} {z}",
            f"tp {who} {x} {y} {z}",
            f"gamemode adventure {who}",
            f'title {who} title {{text:"The Drowned Station",color:"gold"}}',
            f'title {who} actionbar [{{text:"Domes "}},{{score:{{name:"#d",'
            f'objective:"{OBJ}"}}}}]',
            f"playsound minecraft:block.bell.use master {who} {x} {y} {z} 1 1",
            f"clear {who}",
            f"tag {who} add rig_kit",
            f"effect give {who} minecraft:regeneration 5 1 true",
            f"item replace entity {who} armor.head with minecraft:iron_helmet",
            f"execute as {who} at @s run particle minecraft:cloud ~ ~ ~",
            f"execute as {who} run attribute @s minecraft:max_health base set 20",
        ]
        replies = [self.cmd(p) for p in probes]
        bad = [
            (p, r)
            for p, r in zip(probes, replies, strict=True)
            if not re.search(r"No (player|entity) was found|^$", r)
        ]
        self.check(
            f"8d {len(probes)} commands the game aims at players parse "
            "(no player: none ran)",
            not bad,
            bad or "each replied 'No player was found', or nothing",
        )
        after = {
            new: (re.search(r"set to (\S+)", self.cmd(f"gamerule {new}", "Game rule")))
            for new in rules
        }
        same = all(m and m.group(1) == now[k] for k, m in after.items())
        self.check("8e no game rule was changed by the rig", same)

    # -- running and cleaning up ----------------------------------------------

    def forceload(self, add: bool) -> None:
        x1, z1, x2, z2 = self.load_box
        print(self.cmd(f"forceload {'add' if add else 'remove'} {x1} {z1} {x2} {z2}"))
        if add:
            deadline = time.time() + 60
            for x, z in ((x1, z1), (x2, z2), (x1, z2), (x2, z1), self.o[::2]):
                while "not loaded" in self.cmd(f"execute if block {x} 0 {z} {AIR}"):
                    if time.time() > deadline:
                        raise RuntimeError(f"chunk at {x}, {z} did not load")
                    time.sleep(0.5)
            time.sleep(2)
            self.tick(20)

    def cleanup(self) -> None:
        print("-- cleaning up", flush=True)
        for path in self.pack.functions:
            self.cmd(f"schedule clear {NS}:{path}")
        self.cmd(f"scoreboard players set #boat_on {OBJ} 0")
        self.cmd(f"scoreboard players set #timer_on {OBJ} 0")
        self.tick(2)
        tags = (
            "rig_sel",
            "rig_timer",
            "rig_item",
            "rig_boat",
            "rig_boat_spot",
            "rig_mob",
        )
        for tag in tags:
            self.cmd(f"kill @e[tag={tag}]")
        x, y, z = self.desk
        self.fill((x - 1, y, z - 1), (x + 10, y + 8, z + 5), AIR)
        for a, b, lift in reversed(self.saved):
            self.check(
                f"site put back as it was ({a} to {b})", self.restore(a, b, lift)
            )
        (ax, ay, az), (bx, by, bz) = self.dome_box
        box = f"x={ax},y={ay},z={az},dx={bx - ax},dy={by - ay + 2},dz={bz - az}"
        print(self.cmd(f"kill @e[type=minecraft:item,{box}]"))
        self.tick(2)
        left = sum(self.count(f"@e[tag={t}]") for t in tags)
        self.check("no rig entity left", left == 0, left)
        self.cmd(f"bossbar remove {NS}:bar")
        for key in ("args", "time"):
            self.cmd(f"data remove storage {STORE} {key}")
        dp.uninstall(self.world, self.pack, self.dir)
        self.forceload(False)
        for q in ("forceload query", "datapack list", "bossbar list"):
            print(f"{q}: {self.cmd(q)}", flush=True)
        print(f"scoreboard objectives list: {self.cmd('scoreboard objectives list')}")
        print(f"datapacks folder: {sorted(p.name for p in self.dir.iterdir())}")

    def run(self) -> None:
        checks = {
            "1": self.check_datapack,
            "2": self.check_tube,
            "3": self.check_dome,
            "4": self.check_text,
            "5": self.check_bossbar,
            "6": self.check_items,
            "7": self.check_boat,
            "8": self.check_names,
        }
        which = os.environ.get("WHICH", ",".join(checks)).split(",")
        if "1" not in which:
            which.insert(0, "1")  # the others use the pack it installs
        try:
            self.forceload(True)
            for key in which:
                try:
                    checks[key]()
                except Exception as e:  # one broken check must not stop the rest
                    self.check(f"check {key} ran to its end", False, repr(e))
        finally:
            self.cleanup()
        failed = [name for name, ok in self.results if not ok]
        print(
            f"{len(self.results) - len(failed)} passed, {len(failed)} failed"
            + "".join(f"\n  FAILED {name}" for name in failed),
            flush=True,
        )


def main(world) -> None:
    online = world.cmd("list", r"There are \d+ of a max.*")
    if not re.search(r"There are 0 ", online):
        print(f"a player is online ({online}): the rig sprints time, so not run")
        return
    where = os.environ.get(dp.DATAPACKS_ENV)
    if where is None and getattr(world, "world_folder", None):
        where = str(world.world_folder / "datapacks")
    if where is None:
        print(f"set {dp.DATAPACKS_ENV} to the world's datapacks folder")
        return
    Rig(world, Path(where)).run()


if __name__ == "__main__":
    main(globals()["world"])  # `world` is given by `mciwb run`
