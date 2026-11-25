"""
Verify The Drowned Station::

    python verify_station.py                        # the offline checks
    mciwb run verify_station.py                     # those, then the live ones
    CHECKS=layout,names python verify_station.py    # some checks only

Two kinds of check.

Offline checks need no server (``offline_checks()``, which the unit test
runs):

- layout: the layout's own check (``station_layout.check_layout``);
- site: the layout against the survey of the sea it was sited by
  (``station_layout.check_site``); skipped if the survey file is absent;
- stages: the build has a stage for every dome of the layout, in ring
  order, and no other dome stage;
- forceload: the station's box splits into forceload commands of at most
  256 chunks each, which cover it;
- datapack: the datapack's own checks (``datapack.py``: every function
  line and name, as the pack is made);
- functions: the pack has a readable ``pack.mcmeta``; its tags are JSON
  and name functions that exist; every ``function`` a line calls exists;
- build: the whole build runs against the fake client (fake_client.py),
  the datapack installed in a folder of its own and seen to load, with
  every command inside RCON's length, and leaves forceloaded only what
  was before;
- names: every block and item the pack's functions and the build's
  commands name (in setblock, fill, ``if block`` and give) is one that
  mcwb's ``Item`` knows, for the Minecraft release Item was made from.

Live checks work each mechanism in place over RCON, with the station's box
forceloaded and released again afterwards. None is written yet: each is
listed as TODO with the plan's stage that brings it, and a TODO is not a
pass. What RCON cannot stand in for is in PROGRESS.md, for the owner's
play-test.

Refuses to run the live checks while a player is online or a run is in
progress (someone's parked game: the checks reset it), unless FORCE=1.
Exits non-zero if any check fails.
"""

from __future__ import annotations

import functools
import io
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import automatons  # noqa: E402
import build_station as B  # noqa: E402
import domes  # noqa: E402
import game_checks  # noqa: E402
import mcwb  # noqa: E402
import tunnels  # noqa: E402
from fake_client import Recorder  # noqa: E402

NAMESPACE = "station"

# ---------------------------------------------------------------- offline checks
# Each returns the problems it found: none is a pass.


@functools.cache
def recorded() -> Recorder:
    """the whole build, run once against the fake client"""
    with tempfile.TemporaryDirectory() as datapacks, redirect_stdout(io.StringIO()):
        return B.offline_build(
            stages=list(B.STAGES), datapacks_dir=datapacks, force=False
        )


@functools.cache
def pack() -> dict[str, str]:
    """the datapack's files"""
    return B.pack_files(B.new_pack("check"))


def functions(pack: dict[str, str]) -> dict[str, list[str]]:
    """a pack's functions: "namespace:path" -> its command lines"""
    found = {}
    for path, text in pack.items():
        if m := re.fullmatch(r"data/([^/]+)/function/(.+)\.mcfunction", path):
            found[f"{m.group(1)}:{m.group(2)}"] = [
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
    return found


def stage_problems() -> list[str]:
    """a shell stage and an inside stage for every dome, in ring order"""
    wanted = []
    for i in range(len(B.dome_names())):
        name = B.dome_stage_name(i)
        wanted += [name, f"{name}_inside"]
    found = [name for name in B.STAGES if "dome" in name]
    if found != wanted:
        return [f"the dome stages are {found}, the layout's domes want {wanted}"]
    return []


def forceload_problems() -> list[str]:
    (x1, _, z1), (x2, _, z2) = B.station_box()
    pieces = B.site_pieces()
    chunks = set()
    problems = []
    for px1, pz1, px2, pz2 in pieces:
        piece = {
            (cx, cz)
            for cx in range(px1 // 16, px2 // 16 + 1)
            for cz in range(pz1 // 16, pz2 // 16 + 1)
        }
        if len(piece) > B.FORCELOAD_LIMIT:
            problems.append(f"forceload {px1} {pz1} {px2} {pz2}: {len(piece)} chunks")
        chunks |= piece
    wanted = {
        (cx, cz)
        for cx in range(x1 // 16, x2 // 16 + 1)
        for cz in range(z1 // 16, z2 // 16 + 1)
    }
    if chunks != wanted:
        problems.append(f"the forceload boxes miss {len(wanted - chunks)} chunks")
    return problems


def function_problems(pack: dict[str, str]) -> list[str]:
    """a pack's files read and its function references followed"""
    problems = []
    try:
        json.loads(pack["pack.mcmeta"])["pack"]
    except (KeyError, ValueError) as e:
        problems.append(f"pack.mcmeta: {e!r}")
    funcs = functions(pack)
    if not funcs:
        problems.append("no functions")
    for path, text in pack.items():
        if not re.fullmatch(r"data/[^/]+/tags/function/.+\.json", path):
            continue
        try:
            values = json.loads(text)["values"]
        except (KeyError, ValueError) as e:
            problems.append(f"{path}: {e!r}")
            continue
        for value in values:
            name = value if isinstance(value, str) else value.get("id")
            if name not in funcs:
                problems.append(f"{path}: no function {name}")
    for name, lines in funcs.items():
        for n, line in enumerate(lines, 1):
            for called in re.findall(
                r"\bfunction (#?[a-z0-9_.-]+:[a-z0-9_./-]+)", line
            ):
                if not called.startswith("#") and called not in funcs:
                    problems.append(f"{name} line {n}: no function {called}")
    return problems


# where a command names a block or an item: the argument after these
_NAMED = (
    re.compile(r"\bsetblock(?: \S+){3} (\S+)"),
    re.compile(r"\bfill(?: \S+){6} (\S+)"),
    re.compile(r"\bfill(?: \S+){6} \S.* replace (\S+)"),
    re.compile(r"\b(?:if|unless) block(?: \S+){3} (\S+)"),
    re.compile(r"(?<!effect )\bgive (?:@\w(?:\[[^\]]*\])?|\w+) (\S+)"),
)


def names_in(command: str) -> set[str]:
    """the blocks and items a command names (tags left out), as Item has them"""
    found = set()
    for pattern in _NAMED:
        for arg in pattern.findall(command):
            name = arg.partition("[")[0].partition("{")[0]
            if name and not name.startswith("#"):
                found.add(name if ":" in name else f"minecraft:{name}")
    return found


def name_problems(commands: dict[str, list[str]]) -> list[str]:
    """the names that mcwb's Item does not know; ``commands`` is source ->
    its commands"""
    known = {str(item.value) for item in mcwb.Item}
    unknown: dict[str, str] = {}
    for source, lines in commands.items():
        for line in lines:
            for name in names_in(line) - known:
                unknown.setdefault(name, source)
    return [
        f"{name} (in {source}) is not in Minecraft {mcwb.MINECRAFT_VERSION}"
        for name, source in sorted(unknown.items())
    ]


def build_problems() -> list[str]:
    rec = recorded()
    problems = [
        f"command of {len(c.encode())} bytes: {c[:60]}..."
        for c in rec.commands
        if len(c.encode()) > B.MAX_COMMAND
    ]
    if rec.forceloaded != B.site_chunks():
        problems.append(
            f"{len(rec.forceloaded)} chunks left forceloaded, not the "
            f"{len(B.site_chunks())} of the station's box"
        )
    refused = [
        c for c, r in zip(rec.commands, rec.replies, strict=True) if "not loaded" in r
    ]
    if refused:
        problems.append(f"{len(refused)} commands outside the loaded box: {refused[0]}")
    return problems


def geometry_problems() -> list[str]:
    """the domes' and tunnels' cells, for every dome and tunnel of the
    layout, built yet or not: watertight by construction"""
    problems = []
    faces = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0)]

    def beside(cell):
        return {(cell[0] + f[0], cell[1] + f[1], cell[2] + f[2]) for f in faces}

    for dome in B.station_layout.DOMES:
        cells = domes.dome_cells(dome)
        solid = cells.shell | cells.floor
        if any(not beside(c) <= cells.all for c in cells.interior):
            problems.append(f"{dome.name}: an inside cell has a face on the sea")
        if len(domes.openings(dome)) != 2:
            problems.append(f"{dome.name}: not two mouths")
        for index, mouth in domes.openings(dome).items():
            if not mouth or not mouth <= cells.shell:
                problems.append(f"{dome.name}: mouth {index} is not in its shell")
        x, y, z, _ = domes.entrance(dome)
        reserved = tunnels.reserved_cells(dome)
        if not reserved <= cells.interior or (x, y - 1, z) not in solid:
            problems.append(f"{dome.name}: a reserved cell is not inside it")
    for tunnel in B.station_layout.TUNNELS:
        cells = tunnels.tunnel_cells(tunnel)
        a, b = tunnels.ends(tunnel)
        closed = cells.ring | cells.floor | cells.inside | set(cells.stairs)
        if tunnel.rise and len(cells.stairs) != 5 * abs(tunnel.rise):
            problems.append(f"tunnel {tunnel.index}: not a row of stairs a step")
        closed |= domes.dome_cells(a).all | domes.dome_cells(b).all
        if any(not beside(c) <= closed for c in cells.inside):
            problems.append(
                f"tunnel {tunnel.index}: an inside cell has a face on the sea"
            )
        if sum(len(s) for s in cells.sections) != len(cells.inside):
            problems.append(f"tunnel {tunnel.index}: sections overlap")
        if any(not s for s in cells.sections):
            problems.append(f"tunnel {tunnel.index}: an empty section")
        if sum(len(layer) for layer in cells.layers) != len(cells.inside):
            problems.append(f"tunnel {tunnel.index}: layers overlap")
        # every state of the drain: no water beside or over an empty cell,
        # so none can flow (the surface is level, in a sloping tunnel too)
        flows = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)]
        for d in range(len(cells.layers) + 1):
            tunnels.state_lines(tunnel, d)
            dry = set().union(*cells.layers[:d])
            if any(
                (x + i, y + j, z + k) in dry
                for layer in cells.layers[d:]
                for x, y, z in layer
                for i, j, k in flows
            ):
                problems.append(f"tunnel {tunnel.index}: water can flow in state {d}")
        tunnels.engine_cells(tunnel)
    return problems


def site_problems() -> list[str]:
    """the layout against the survey of its site, if the survey is there"""
    try:
        return list(B.station_layout.check_site())
    except FileNotFoundError:
        print(f"site: skipped, no {B.station_layout.SURVEY_FILE}")
        return []


OFFLINE: dict[str, Callable[[], list[str]]] = {
    "layout": B.layout_problems,
    "site": site_problems,
    "stages": stage_problems,
    "forceload": forceload_problems,
    "geometry": geometry_problems,
    "datapack": B.pack_problems,
    "functions": lambda: function_problems(pack()),
    "build": build_problems,
    "names": lambda: name_problems(
        {**functions(pack()), "the build": recorded().commands}
    ),
}


def offline_checks(wanted: list[str] | None = None) -> dict[str, list[str]]:
    """run the offline checks (all, or those named): name -> its problems"""
    results = {}
    for name, check in OFFLINE.items():
        if wanted is None or name in wanted:
            try:
                results[name] = check()
            except SystemExit as e:  # the build refused to start
                results[name] = [f"the offline build did not run: {e}"]
    return results


# ------------------------------------------------------------------- live checks
# Each takes the build's context and returns its problems. Those not
# written yet are listed here by name, from the plan's "Checks".


def todo(what: str, plan_stage: int) -> Callable[[B.Context], list[str]]:
    """a live check that is in the plan and not written yet"""

    def check(ctx: B.Context) -> list[str]:
        raise NotImplementedError

    check.todo = f"{what} (plan stage {plan_stage})"  # type: ignore[attr-defined]
    return check


def forceload_check(ctx: B.Context) -> list[str]:
    """the station's box is forceloaded: the one deliberate forceload"""
    loaded, wanted = B.forceloaded(), B.site_chunks()
    extra = loaded - wanted
    print(
        f"     forceloaded: the station's {len(loaded & wanted)} of {len(wanted)} "
        f"chunks (expected), and {len(extra)} others: {sorted(extra)}"
    )
    if missing := wanted - loaded:
        return [f"{len(missing)} chunks of the station's box are not forceloaded"]
    return []


def rules_check(ctx: B.Context) -> list[str]:
    """the game rules, the difficulty, and the mineshaft's spawners gone"""
    problems = []
    for rule, value in B.RULES.items():
        reply = ctx.cmd(f"gamerule {rule}", "Game rule")
        if f"set to {value}" not in reply and f"set to: {value}" not in reply:
            problems.append(f"gamerule {rule}: {reply!r}, not {value}")
    if "Easy" not in (reply := ctx.cmd("difficulty", "difficulty is")):
        problems.append(f"the difficulty is not Easy: {reply!r}")
    for pos in ctx.layout.MINESHAFT_SPAWNERS:
        if ctx.is_block(pos, "minecraft:spawner"):
            problems.append(f"a spawner is still at {pos}")
    return problems


def shell_check(index: int) -> Callable[[B.Context], list[str]]:
    def check(ctx: B.Context) -> list[str]:
        inside = B.STAGES[f"{B.dome_stage_name(index)}_inside"]
        empty = getattr(inside, "placeholder", False)
        return domes.check_shell(ctx, ctx.layout.DOMES[index], empty)

    return check


def tunnel_check(index: int) -> Callable[[B.Context], list[str]]:
    def check(ctx: B.Context) -> list[str]:
        return tunnels.check_tunnel(ctx, ctx.layout.TUNNELS[index])

    return check


LIVE: dict[str, Callable[[B.Context], list[str]]] = {
    "forceloaded": forceload_check,
    "rules": rules_check,
    **{f"shell_{i}": shell_check(i) for i in domes.BUILT},
    **{f"tunnel_{i}": tunnel_check(i) for i in tunnels.BUILT},
    "player_count": game_checks.check_players,
    "vote": game_checks.check_vote,
    "difficulty": game_checks.check_difficulty,
    "progress": game_checks.check_progress,
    "reset": game_checks.check_reset,
    "automatons": automatons.check,
    "fights": automatons.check_fights,
    "fittings": game_checks.check_fittings,
    "ring": game_checks.check_ring,
    "restricted_items": game_checks.check_restricted,
    "boiler_room": todo("the Boiler Room solved and failed, solo and two-player", 1),
    "gearworks": todo("the Gearworks solved and failed, an old attempt cleared", 2),
    "flooded_dome": todo("the Flooded Dome drained, solo and two-player", 2),
    "foundry": todo("the Foundry's waves raised, killed and counted", 3),
    "signal_room": todo("the Signal Room solved and failed, solo and two-player", 3),
    "clockwork_maze": todo("the Clockwork Maze's walls and lifts", 4),
    "boss": todo("the boss's phases, solo and two-player, and the win", 4),
}
# a module's checks take the place of a TODO of the same name, or are added
for _module in B.modules():
    LIVE.update(_module.checks)


def todos() -> dict[str, str]:
    """the live checks not written yet: name -> what it will check"""
    return {n: f.todo for n, f in LIVE.items() if hasattr(f, "todo")}  # type: ignore[attr-defined]


def live_checks(world, wanted: list[str] | None = None) -> dict[str, list[str]]:
    """run the written live checks (all, or those named): name -> its
    problems. The station's box is forceloaded for good by the build; this
    loads it if it is not, and leaves it loaded. A check that raises is a
    failure, and the rest still run"""
    names = [n for n in LIVE if n not in todos() and (wanted is None or n in wanted)]
    if not names:
        return {}
    online = B.players_online()
    if online and not os.environ.get("FORCE"):
        raise SystemExit(f"{', '.join(online)} online: not verifying (FORCE=1 to)")
    ctx = B.Context(world=world, layout=B.station_layout, pack=B.new_pack())
    # a run that is parked (started, nobody online) is somebody's game: the
    # core's checks reset the game, and every check sprints the clock
    if ctx.score("#run") == 1 and not os.environ.get("FORCE"):
        raise SystemExit(
            "a run is in progress (#run is 1): not verifying, which would "
            "reset it (FORCE=1 to)"
        )
    B.forceload(ctx)
    results = {}
    for name in names:
        print(f"-- {name}", flush=True)
        try:
            results[name] = LIVE[name](ctx)
        except Exception as e:  # noqa: BLE001
            results[name] = [f"the check failed to run: {e!r}"]
    return results


def main(world=None) -> None:
    named = os.environ.get("CHECKS")
    wanted = named.split(",") if named else None
    if wanted and "tunnels" in wanted:  # short for every tunnel's check
        wanted += [f"tunnel_{i}" for i in tunnels.BUILT]
        wanted.remove("tunnels")
    if unknown := [n for n in wanted or [] if n not in OFFLINE and n not in LIVE]:
        raise SystemExit(f"unknown checks {unknown}: choose from {[*OFFLINE, *LIVE]}")
    results = offline_checks(wanted)
    if world is not None:
        results.update(live_checks(world, wanted))
    for name, problems in results.items():
        print(("FAIL " if problems else "PASS ") + name)
        for problem in problems:
            print(f"     {problem}")
    for name, what in todos().items():
        if wanted is None or name in wanted:
            print(f"TODO {name}: {what}")
    passed = sum(not p for p in results.values())
    print(f"{passed}/{len(results)} checks passed")
    if passed < len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main(globals().get("world"))
