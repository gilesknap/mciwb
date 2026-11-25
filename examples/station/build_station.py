"""
Build The Drowned Station, stage by stage::

    mciwb run build_station.py                         # everything, in order
    STAGES=site,datapack mciwb run build_station.py    # some stages
    python build_station.py [OUT]                      # offline, no server

Stages, in order (``STAGES``): site, datapack, rules, shore, dock, then
for each dome its shell (start_dome, dome_1 to dome_7) and what is inside
it (start_dome_inside, dome_1_inside ...), with the lift between the start
dome's shell and its inside, then a stage for each tunnel (tunnel_0 to
tunnel_7; ``tunnels`` in ``STAGES`` is short for all of them). Those not written yet are in
the list all the same, so the order of work shows; they say "not built
yet" and do nothing. A dome's shell stage wipes what is inside the dome,
the pump engines and the lift's shaft too: run ``lift`` (the start dome),
its ``_inside`` stage and the stage of the tunnel that leaves it after it, which is the order the
whole build runs them in. The stages of the way in and of the domes'
insides come from modules (``modules()``; see ``game.Module``): a file
``shore.py`` or ``dome_<key>.py`` beside this one.

The station's box (``station_layout``) is forceloaded by the build, at
most 256 chunks a command, and stays forceloaded: the game's functions
change blocks all over it, and a function's block change fails in a chunk
that is not loaded (PROGRESS.md, "Forceload"). The build
refuses to run while a player is online, unless
``FORCE=1``: with nobody online the server does not tick, and the build
sprints the ticks it needs, which would wreck a player's game.

The datapack is made with ``datapack.py`` from the layout alone
(``new_pack``), whatever stages run, and installed by the ``datapack``
stage into the folder ``STATION_DATAPACKS_DIR`` names (the world's
``datapacks`` folder, which this process must be able to write), then
reloaded over RCON. Without it the pack is generated but not installed.

Without a server (``python build_station.py``) the same build runs against
a fake client (fake_client.py). Give ``OUT`` to write ``OUT.commands``
(every command sent, in order) and ``OUT.blocks`` (the final block of every
cell set): two builds can then be compared with ``diff``.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import datapack  # noqa: E402
import domes  # noqa: E402
import game  # noqa: E402
import station_layout  # noqa: E402
import tunnels  # noqa: E402
from fake_client import Recorder, World  # noqa: E402

from mciwb.threads import (  # noqa: E402
    get_client,
    reply_matches,
    retry_command,
    set_client,
)

# RCON drops a command longer than this (the connection breaks, and a build
# that dies then leaves the site forceloaded): found by examples/castle2
MAX_COMMAND = 1446
FORCELOAD_LIMIT = 256  # chunks a forceload command, the server's limit

Cell = tuple[int, int, int]
Box = tuple[Cell, Cell]


# ------------------------------------------------- the layout and the datapack
# All that the build and the checks need of station_layout.py and
# datapack.py goes through these functions, and nothing else here or in
# verify_station.py touches those modules' names.


def layout_problems() -> list[str]:
    """what the layout finds wrong with itself"""
    return list(station_layout.check_layout())


def station_box() -> Box:
    """the two corners (low, high) of the box that holds the dock, the
    domes and the tunnels (not the shore)"""
    return station_layout.BOUNDS


def dome_names() -> list[str]:
    """the domes' names, in ring order: the start dome, then domes 1 to 7"""
    return [d.name for d in station_layout.DOMES]


DATAPACKS_ENV = datapack.DATAPACKS_ENV  # names the world's datapacks folder


def new_pack(stamp: str | None = None) -> datapack.Pack:
    """
    The station's datapack, made in full from the layout: a stage's
    functions are added here, not by the stage, so that the pack is whole
    whichever stages run. ``stamp`` marks this build of the pack (default:
    the time), and is what the install looks for after the reload.
    """
    pack = datapack.Pack(stamp=stamp)
    game.add_functions(pack, modules())
    return pack


_MODULES: list[game.Module] | None = None


def modules() -> list[game.Module]:
    """
    The modules of the station: each file named in ``game.MODULE_FILES``
    (``shore.py``, ``dome_<key>.py``) that exists beside this one, imported
    for its ``MODULE``. A dome with no file yet is a stub
    (``game.stub_module``); the way in with none is a placeholder stage.
    """
    global _MODULES
    if _MODULES is None:
        here = Path(__file__).parent
        _MODULES = [
            importlib.import_module(name).MODULE
            for name in game.MODULE_FILES
            if (here / f"{name}.py").is_file()
        ]
        # a dome with no module yet is a stub with a bypass lever
        _MODULES += [
            game.stub_module(d)
            for d in station_layout.DOMES[1:]
            if not (here / f"dome_{d.key}.py").is_file()
        ]
    return _MODULES


def pack_files(pack: datapack.Pack) -> dict[str, str]:
    """a pack as its files: path in the pack -> text"""
    return pack.files()


def pack_problems() -> list[str]:
    """what the datapack's own checks find wrong: it checks every line and
    name as the pack is made, and refuses the first bad one"""
    try:
        files = pack_files(new_pack("check"))
    except datapack.PackError as e:
        return [str(e)]
    problems = []
    for path, text in files.items():
        if path.endswith(".mcfunction"):
            for n, line in enumerate(text.splitlines(), 1):
                try:
                    datapack.check_line(line, f"{path} line {n}")
                except datapack.PackError as e:
                    problems.append(str(e))
    return problems


def install_pack(pack: datapack.Pack, datapacks_dir: Path) -> Path:
    """write the pack into a world's datapacks folder, reload, and see that
    this build of it loaded; gives back the pack's folder"""
    return datapack.install(SimpleNamespace(cmd=cmd), pack, datapacks_dir)


# ----------------------------------------------------------------- RCON helpers


def cmd(command: str) -> str:
    """send a console command with this thread's client; a command too long
    for RCON is refused here, before it breaks the connection"""
    size = len(command.encode())
    if size > MAX_COMMAND:
        raise ValueError(
            f"command of {size} bytes (RCON takes {MAX_COMMAND}): {command[:60]}..."
        )
    return get_client().run(command)


_LIST = re.compile(r"There are (\d+) of a max of \d+ players online:([^\n]*)")


def players_online() -> list[str]:
    """
    The names of the players online. Another RCON client can empty the
    reply or add its output to it, so ``list`` is sent again until its
    reply reads as one; a reply that never does is an error (not "nobody").
    """
    reply = retry_command(lambda: cmd("list"), reply_matches(_LIST), "list")
    m = _LIST.search(reply)
    if not m:
        raise RuntimeError(f"cannot tell who is online from {reply!r}")
    if int(m.group(1)) == 0:
        return []
    return [n.strip() for n in m.group(2).split(",") if n.strip()] or ["?"]


@dataclass
class Context:
    """
    What every stage and every live check is given: the world, the layout,
    the datapack, and the commands a build or a check needs. All of them
    go through ``cmd`` (the length limit) and those that read are sent
    again if another RCON client garbled the reply.
    """

    world: Any  # the Iwb of `mciwb run`; None offline
    layout: ModuleType  # station_layout
    pack: datapack.Pack  # the datapack under construction
    datapacks_dir: Path | None = None  # where the datapack stage installs it
    pause: Callable[[float], None] = field(default=time.sleep)  # no wait offline

    # -- commands ----------------------------------------------------------

    def cmd(self, command: str, expect: str | None = None) -> str:
        """send a command. With ``expect`` (a pattern its reply must
        contain) it is sent again if the reply does not read as its own:
        only for commands that are safe to send twice"""
        if expect is None:
            return cmd(command)
        whole = reply_matches(f"(?s).*(?:{expect}).*")
        return retry_command(lambda: cmd(command), whole, command)

    def fill(self, a: Cell, b: Cell, block: str, how: str = "") -> str:
        """fill the box a..b (``how``: e.g. ``replace minecraft:water``)"""
        return self.cmd(
            datapack.fill(a, b, block, how), "filled|No blocks|not loaded|Too many"
        )

    def fill_cells(self, cells, block: str, how: str = "") -> None:
        """fill a set of cells, a command a row along x"""
        for a, b in domes.runs(cells):
            self.fill(a, b, block, how)

    def fill_boxes(self, cells, block: str, how: str = "") -> None:
        """fill a set of cells, a command a box: fewer commands than
        ``fill_cells`` where the cells make boxes"""
        for a, b in domes.boxes(cells):
            self.fill(a, b, block, how)

    def setblock(self, pos: Cell, block: str) -> str:
        return self.cmd(
            f"setblock {pos[0]} {pos[1]} {pos[2]} {block}",
            "Changed the block|Could not set|not loaded",
        )

    def function(self, path: str, args: str = "") -> str:
        """run one of the pack's functions (``path`` without the namespace)"""
        return self.cmd(f"function {self.pack.id(path)}{' ' + args if args else ''}")

    # -- reading -----------------------------------------------------------

    def test(self, command: str) -> bool:
        """does an ``execute if ...`` pass?"""
        return "Test passed" in self.cmd(command, "Test (passed|failed)|not loaded")

    def is_block(self, pos: Cell, block: str) -> bool:
        return self.test(f"execute if block {pos[0]} {pos[1]} {pos[2]} {block}")

    def count(self, selector: str) -> int:
        """how many entities a selector finds"""
        reply = self.cmd(f"execute if entity {selector}", "Test (passed|failed)")
        m = re.search(r"Count: (\d+)", reply)
        return int(m.group(1)) if m else int("passed" in reply)

    def score(self, name: str, objective: str = game.OBJ) -> int | None:
        """a score, or None if it was never set"""
        reply = self.cmd(
            f"scoreboard players get {name} {objective}",
            r"has -?\d+|Can't get|Unknown|none is set",
        )
        m = re.search(r"has (-?\d+)", reply)
        return int(m.group(1)) if m else None

    def set_score(self, name: str, value: int, objective: str = game.OBJ) -> None:
        self.cmd(f"scoreboard players set {name} {objective} {value}", "Set ")

    def data(self, what: str) -> str:
        """``data get <what>``: the reply's value, or "" if there is none"""
        reply = self.cmd(f"data get {what}", "following|Found no|has the")
        return reply.partition(": ")[2] if "following" in reply else ""

    # -- time --------------------------------------------------------------

    def gametime(self) -> int | None:
        reply = self.cmd("time query gametime", r"\d+ tick")
        m = re.search(r"(\d+) tick", reply)
        return int(m.group(1)) if m else None

    def tick(self, ticks: int) -> None:
        """
        Let the game run about ``ticks`` ticks. With nobody online the
        server does not tick, so sprint them; with a player online it ticks
        for them, and a sprint would wreck their game, so wait that long.
        """
        if players_online():
            self.pause(ticks / 20 + 0.5)
        else:
            cmd(f"tick sprint {ticks}")
            self.pause(min(0.15 + ticks / 100, 3))

    def advance(self, ticks: int) -> None:
        """
        Let the game run at least ``ticks`` ticks, and see that it did, by
        the game's own clock: a sprint returns before it is done, and a
        second one sent too soon cuts the first short.
        """
        start = self.gametime()
        if start is None or players_online():
            self.tick(ticks)
            return
        deadline = time.time() + 30 + ticks / 10
        while (left := start + ticks - (self.gametime() or 0)) > 0:
            if time.time() > deadline:
                raise RuntimeError(f"the game did not advance {ticks} ticks")
            cmd(f"tick sprint {min(left, 150)}")
            for _ in range(200):
                self.pause(0.05)
                if "sprinting" not in self.cmd("tick query", "game is|The game"):
                    break


# ------------------------------------------------------------------- forceload


def chunk_pieces(
    x1: int, z1: int, x2: int, z2: int, limit: int = FORCELOAD_LIMIT
) -> list[tuple[int, int, int, int]]:
    """a block box split into boxes of at most ``limit`` chunks each"""
    cx1, cx2, cz1, cz2 = x1 // 16, x2 // 16, z1 // 16, z2 // 16
    columns = min(cx2 - cx1 + 1, limit)
    rows = max(1, limit // columns)
    pieces = []
    for cx in range(cx1, cx2 + 1, columns):
        for cz in range(cz1, cz2 + 1, rows):
            ex, ez = min(cx + columns - 1, cx2), min(cz + rows - 1, cz2)
            pieces.append((cx * 16, cz * 16, ex * 16 + 15, ez * 16 + 15))
    return pieces


def site_pieces() -> list[tuple[int, int, int, int]]:
    """the station's box as forceload boxes"""
    (x1, _, z1), (x2, _, z2) = station_box()
    return chunk_pieces(x1, z1, x2, z2)


def probe_points() -> list[tuple[int, int]]:
    """the corners, the edges' middles and the centre of the station's box"""
    (x1, _, z1), (x2, _, z2) = station_box()
    return [(x, z) for x in (x1, (x1 + x2) // 2, x2) for z in (z1, (z1 + z2) // 2, z2)]


def unloaded(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """those of the (x, z) whose chunk is not loaded"""
    return [
        (x, z)
        for x, z in points
        if "not loaded" in cmd(f"execute if block {x} 0 {z} minecraft:air")
    ]


def forceload(ctx: Context) -> None:
    """
    Forceload the station's box, for good, and wait until the chunks have
    their blocks: forceloading only asks for them, and a build is faster
    than the loading. (examples/castle found that ``execute if loaded``
    does not serve: a server with no players does not tick, and never
    calls a chunk fully loaded.) Then tick a little, so that their
    entities are in too.
    """
    for x1, z1, x2, z2 in site_pieces():
        print(f"   {cmd(f'forceload add {x1} {z1} {x2} {z2}')}")
    for _ in range(120):
        if not unloaded(probe_points()):
            break
        ctx.pause(0.5)
    else:
        raise RuntimeError("the station's box is still not loaded after a minute")
    ctx.tick(20)


_FORCELOADED = re.compile(
    r"(No|A|\d+) force loaded chunks? (was|were) found in minecraft:overworld"
    r"( at: [-\d\[\], ]+)?"
)


def forceloaded() -> set[tuple[int, int]]:
    """the overworld's forceloaded chunks, as (chunk x, chunk z)"""
    reply = retry_command(
        lambda: cmd("forceload query"), reply_matches(_FORCELOADED), "forceload query"
    )
    return {(int(x), int(z)) for x, z in re.findall(r"\[(-?\d+), (-?\d+)\]", reply)}


def site_chunks() -> set[tuple[int, int]]:
    """the chunks of the station's box: what the built game keeps loaded"""
    return {
        (cx, cz)
        for x1, z1, x2, z2 in site_pieces()
        for cx in range(x1 // 16, x2 // 16 + 1)
        for cz in range(z1 // 16, z2 // 16 + 1)
    }


# ---------------------------------------------------------------------- stages
# A stage is a function of the context. It returns a line to print, or None.


def site(ctx: Context) -> str:
    """the site is where the layout says, and loaded"""
    lo, hi = station_box()
    if missing := unloaded(probe_points()):
        raise RuntimeError(f"chunks at {missing} are not loaded")
    chunks = sum(
        ((x2 - x1 + 1) // 16) * ((z2 - z1 + 1) // 16)
        for x1, z1, x2, z2 in site_pieces()
    )
    return f"station box {lo}..{hi}: {chunks} chunks loaded"


def install_datapack(ctx: Context) -> str:
    """install the datapack in the world's datapacks folder and reload"""
    files = len(pack_files(ctx.pack))
    if ctx.datapacks_dir is None:
        return (
            f"{files} files generated, NOT INSTALLED: "
            f"set {DATAPACKS_ENV} to the world's datapacks folder"
        )
    folder = install_pack(ctx.pack, ctx.datapacks_dir)
    if datapack.server_log(ctx.datapacks_dir) is None:
        # only the log says that a line did not parse
        return (
            f"{files} files installed in {folder}, and its load function ran; "
            "THE SERVER'S LOG WAS NOT FOUND: lines that do not parse were not looked for"
        )
    return f"{files} files installed in {folder}, and loaded (the server's log read)"


#: the game rules of the plan (Minecraft 26.3 names). The last is a radius
#: round each player within which fire spreads; 0 turns spreading off
#: (PROGRESS.md, "Game rules")
RULES = {
    "keep_inventory": "true",
    "mob_griefing": "false",
    "spawn_monsters": "false",
    "fire_spread_radius_around_player": "0",
}


def rules(ctx: Context) -> str:
    """the game rules of the plan, and the mineshaft's spawners gone"""
    for rule, value in RULES.items():
        reply = ctx.cmd(f"gamerule {rule} {value}", "Game rule")
        if "Game rule" not in reply:
            raise RuntimeError(f"gamerule {rule} {value}: {reply!r}")
    removed = []
    for x, y, z in ctx.layout.MINESHAFT_SPAWNERS:
        if not ctx.layout.in_station(x, y, z):
            continue
        if ctx.is_block((x, y, z), "minecraft:spawner"):
            ctx.setblock((x, y, z), "minecraft:air")
            removed.append((x, y, z))
    return f"{len(RULES)} game rules set; spawners removed at {removed or 'none'}"


def dome_stage(index: int) -> Callable[[Context], str]:
    """the stage that builds a dome's empty shell"""

    def stage(ctx: Context) -> str:
        return domes.build_shell(ctx, ctx.layout.DOMES[index])

    return stage


def tunnel_stage(index: int) -> Callable[[Context], str]:
    """the stage that builds one tunnel, flooded and shut, with its engine"""

    def stage(ctx: Context) -> str:
        line = tunnels.build_tunnel(ctx, ctx.layout.TUNNELS[index])
        # the pack's own idea of the tunnel, if the pack is installed
        ctx.function(f"tunnel/{index}/reset")
        return line

    return stage


def tunnel_stage_names() -> list[str]:
    return [f"tunnel_{index}" for index in tunnels.BUILT]


def not_built(what: str, plan_stage: int) -> Callable[[Context], str]:
    """a stage that is in the plan and not written yet"""

    def stage(ctx: Context) -> str:
        return f"not built yet: {what} (plan stage {plan_stage})"

    stage.placeholder = True  # type: ignore[attr-defined]
    return stage


def dome_stage_name(index: int) -> str:
    return "start_dome" if index == 0 else f"dome_{index}"


#: the plan's stage that brings each dome's inside
_PLAN_STAGE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4, 7: 4}


def make_stages() -> dict[str, Callable[[Context], str | None]]:
    """the stages in order; the modules' stages take their placeholders'
    places"""
    stages: dict[str, Callable[[Context], str | None]] = {
        "site": site,
        "datapack": install_datapack,
        "rules": rules,
        "shore": not_built("the shore landing and its boat", 1),
        "dock": not_built("the dock offshore", 1),
    }
    for d in station_layout.DOMES:
        name = dome_stage_name(d.index)
        stages[name] = (
            dome_stage(d.index)
            if d.index in domes.BUILT
            else not_built(f"the shell of {d.name}", _PLAN_STAGE[d.index])
        )
        if d.index == 0:
            # after the shell, which wipes the part of the shaft inside it
            stages["lift"] = not_built(
                "the lift from the dock down to the start dome", 1
            )
        stages[f"{name}_inside"] = not_built(
            f"the inside of {d.name}", _PLAN_STAGE[d.index]
        )
    for index in tunnels.BUILT:
        stages[f"tunnel_{index}"] = tunnel_stage(index)
    for module in modules():
        for name, stage in module.stages.items():
            if not getattr(stages.get(name), "placeholder", False):
                raise SystemExit(
                    f"module {module.name}: {name!r} is not a placeholder stage"
                )
            stages[name] = stage
    return stages


STAGES: dict[str, Callable[[Context], str | None]] = make_stages()


def written() -> list[str]:
    """the stages that build something"""
    return [n for n, f in STAGES.items() if not getattr(f, "placeholder", False)]


def run_stage(ctx: Context, name: str) -> None:
    t0 = time.time()
    print(f"== {name}")
    result = STAGES[name](ctx)
    if result:
        print(f"   {result}")
    if name in written():
        print(f"   {name} done in {time.time() - t0:.0f} s")


# ------------------------------------------------------------------- the build


def _setting(value, env: str):
    return value if value is not None else os.environ.get(env)


def build(
    world=None,
    stages: list[str] | None = None,
    force: bool | None = None,
    datapacks_dir: Path | str | None = None,
    pause: Callable[[float], None] = time.sleep,
    stamp: str | None = None,
) -> Context:
    """
    Run the stages (default: ``STAGES`` in the environment, else all) with
    this thread's client. ``force`` (default: ``FORCE`` in the environment)
    builds with players online; ``datapacks_dir`` (default:
    ``STATION_DATAPACKS_DIR``) is where the datapack is installed.
    """
    if problems := layout_problems():
        raise SystemExit("the layout:\n  " + "\n  ".join(problems))
    if stages is None:
        named = os.environ.get("STAGES")
        stages = named.split(",") if named else list(STAGES)
    # "tunnels" is short for every tunnel's stage
    stages = [
        name
        for named in stages
        for name in (tunnel_stage_names() if named == "tunnels" else [named])
    ]
    if unknown := [s for s in stages if s not in STAGES]:
        raise SystemExit(f"unknown stages {unknown}: choose from {list(STAGES)}")
    folder = _setting(datapacks_dir, DATAPACKS_ENV)
    ctx = Context(
        world=world,
        layout=station_layout,
        pack=new_pack(stamp),
        datapacks_dir=Path(folder) if folder else None,
        pause=pause,
    )
    online = players_online()
    if online and not _setting(force, "FORCE"):
        raise SystemExit(f"{', '.join(online)} online: not building (FORCE=1 to)")
    t_start = time.time()
    forceload(ctx)
    for name in stages:
        run_stage(ctx, name)
    print(f"station: {len(stages)} stages in {time.time() - t_start:.0f} s")
    return ctx


def offline_build(
    stages: list[str] | None = None,
    datapacks_dir: Path | str | None = None,
    force: bool | None = None,
    recorder: Recorder | None = None,
) -> Recorder:
    """
    Run the build against a fake client and give back its recorder (its
    ``commands``, its ``world`` of blocks, what it ``forceloaded``).
    Nothing is read from the environment but ``STAGES`` and ``FORCE`` when
    not given; the datapack is installed only into a folder given here.
    Give a ``recorder`` of your own to set its players, or to look at it
    after a build that fails. The thread's real client, if any, is put
    back afterwards.
    """
    try:
        real = get_client()
    except AttributeError:
        real = None
    rec = recorder or Recorder(World(*station_box()))
    rec.datapacks_dir = Path(datapacks_dir) if datapacks_dir else None
    set_client(rec)  # type: ignore[arg-type]
    try:
        build(
            stages=stages,
            force=force,
            datapacks_dir=datapacks_dir or "",
            pause=lambda _s: None,
            stamp="offline",  # (not the time: two builds must compare equal)
        )
    finally:
        if real is not None:
            set_client(real)
    return rec


def main(world=None) -> None:
    if world is not None:
        build(world)
        return
    rec = offline_build()
    print(f"offline: {len(rec.commands)} commands")
    if len(sys.argv) > 1:
        out = sys.argv[1]
        Path(f"{out}.commands").write_text("\n".join(rec.commands) + "\n")
        Path(f"{out}.blocks").write_text("\n".join(rec.world.dump()) + "\n")
        print(f"wrote {out}.commands and {out}.blocks")


if __name__ == "__main__":
    main(globals().get("world"))
