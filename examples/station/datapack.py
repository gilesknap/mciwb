"""
The datapack generator for The Drowned Station: build a datapack in memory
from Python, write it to a folder, and install it in a running world.

Pure Python: nothing here talks to the server until ``install`` or
``uninstall`` is called with a world (anything with ``cmd(command) -> str``,
such as mciwb's ``Iwb``)::

    pack = Pack("station")
    pack.objectives({"st.timer": "dummy"})
    pack.function("tick", ["scoreboard players add #ticks st.timer 1"], tick=True)
    install(world, pack, datapacks_dir)     # write, reload, check it loaded

The formats are those of Minecraft Java 26.3 (data pack format 121), found
by asking the server (see ``rig_mechanisms.py``, which proves each of them):

- ``pack.mcmeta`` takes ``min_format`` and ``max_format``; with the old
  ``pack_format`` alone the pack still loads, but each scan of the folder
  logs a warning and a stack trace.
- functions live in ``data/<namespace>/function/`` and the tags that run
  them in ``data/minecraft/tags/function/{load,tick}.json`` (both singular:
  the plural folders are ignored, silently).
- a new folder in the world's ``datapacks`` is found and enabled by
  ``reload``; nothing else is needed. ``reload`` takes effect at once, even
  on a server with nobody online.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from collections.abc import Iterable
from pathlib import Path

#: the namespace of the game's functions, storage and bossbars
NAMESPACE = "station"

#: data pack format of Minecraft 26.3 (``pack_version.data_major`` in the
#: server jar's ``version.json``)
PACK_FORMAT = 121

#: the longest command the game takes anywhere else (a command block's
#: limit); a function line has no limit of its own, but a longer one is
#: almost certainly a mistake in the generator
MAX_LINE = 32500

#: the ``max_command_sequence_length`` game rule's default: a function that
#: runs more commands than this in one tick is cut short, silently
MAX_COMMANDS = 65536

#: ``fill`` and ``clone`` refuse a bigger box (the ``max_block_modifications``
#: game rule's default)
MAX_FILL = 32768

#: the environment variable naming the world's ``datapacks`` folder
DATAPACKS_ENV = "STATION_DATAPACKS_DIR"

#: scoreboard objective names are safe with these characters
_OBJECTIVE = re.compile(r"^[A-Za-z0-9_.+-]{1,40}$")
_NAMESPACE = re.compile(r"^[a-z0-9_.-]+$")
_PATH = re.compile(r"^[a-z0-9_.-]+(/[a-z0-9_.-]+)*$")
_MACRO = re.compile(r"\$\([A-Za-z0-9_]+\)")


class PackError(ValueError):
    """a pack that the game would refuse, or load only part of"""


def check_line(line: str, where: str = "") -> None:
    """raise PackError if ``line`` is not one good function line"""
    at = f"{where}: " if where else ""
    if "\n" in line or "\r" in line:
        raise PackError(f"{at}a line break inside a command: {line[:60]!r}")
    if not line.strip():
        raise PackError(f"{at}an empty command")
    if line != line.strip():
        raise PackError(f"{at}space round a command: {line[:60]!r}")
    if line.startswith("/"):
        raise PackError(f"{at}function commands have no leading /: {line[:60]!r}")
    if len(line) > MAX_LINE:
        raise PackError(f"{at}a command of {len(line)} characters (max {MAX_LINE})")
    if line.endswith("\\"):
        raise PackError(f"{at}a trailing backslash joins the next line on")
    if line.startswith("$"):
        if not _MACRO.search(line):
            raise PackError(f"{at}a macro line with no $(name): {line[:60]!r}")
    elif not line.startswith("#") and _MACRO.search(line):
        raise PackError(f"{at}$(name) in a line that does not start with $")


def fill_volume(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    """the number of blocks in the box from a to b, both included"""
    return (abs(a[0] - b[0]) + 1) * (abs(a[1] - b[1]) + 1) * (abs(a[2] - b[2]) + 1)


def fill(
    a: tuple[int, int, int], b: tuple[int, int, int], block: str, how: str = ""
) -> str:
    """a ``fill`` command, refused if its box is over the game's limit.
    ``how`` is the rest of the command, e.g. ``replace minecraft:water``"""
    volume = fill_volume(a, b)
    if volume > MAX_FILL:
        raise PackError(f"fill of {volume} blocks (max {MAX_FILL}): {a} to {b}")
    lo = tuple(min(p, q) for p, q in zip(a, b, strict=True))
    hi = tuple(max(p, q) for p, q in zip(a, b, strict=True))
    text = f"fill {lo[0]} {lo[1]} {lo[2]} {hi[0]} {hi[1]} {hi[2]} {block}"
    return f"{text} {how}" if how else text


def box_selector(a: tuple[int, int, int], b: tuple[int, int, int]) -> str:
    """selector arguments for the entities whose hitbox touches the box of
    blocks from a to b: ``x=..,y=..,z=..,dx=..,dy=..,dz=..`` (put inside
    ``@a[...]``). ``dx=0`` still means one block wide"""
    lo = [min(p, q) for p, q in zip(a, b, strict=True)]
    hi = [max(p, q) for p, q in zip(a, b, strict=True)]
    return (
        f"x={lo[0]},y={lo[1]},z={lo[2]},"
        f"dx={hi[0] - lo[0]},dy={hi[1] - lo[1]},dz={hi[2] - lo[2]}"
    )


def mmss_lines(source: str, objective: str, storage: str, path: str) -> list[str]:
    """commands that turn a number of seconds (the score of ``source`` in
    ``objective``) into the compound ``{m, t, o}`` at ``path`` in
    ``storage``: minutes, and the tens and ones of the seconds, for a macro
    line such as ``$... "$(m):$(t)$(o)"``. Needs the constants ``#60`` and
    ``#10`` in the objective (``Pack.constants``)"""
    o = objective
    store = f"execute store result storage {storage} {path}"
    return [
        f"scoreboard players operation #mm.m {o} = {source} {o}",
        f"scoreboard players operation #mm.m {o} /= #60 {o}",
        f"scoreboard players operation #mm.s {o} = {source} {o}",
        f"scoreboard players operation #mm.s {o} %= #60 {o}",
        f"scoreboard players operation #mm.t {o} = #mm.s {o}",
        f"scoreboard players operation #mm.t {o} /= #10 {o}",
        f"scoreboard players operation #mm.o {o} = #mm.s {o}",
        f"scoreboard players operation #mm.o {o} %= #10 {o}",
        f"{store}.m int 1 run scoreboard players get #mm.m {o}",
        f"{store}.t int 1 run scoreboard players get #mm.t {o}",
        f"{store}.o int 1 run scoreboard players get #mm.o {o}",
    ]


class Pack:
    """
    A datapack being built: functions, the tags that run them on load and
    every tick, and the scoreboard objectives its load function makes.

    ``name`` is the folder in the world's ``datapacks`` (the game calls the
    pack ``file/<name>``); ``namespace`` is where its functions live.
    """

    def __init__(
        self,
        name: str = NAMESPACE,
        namespace: str = NAMESPACE,
        description: str = "The Drowned Station",
        stamp: str | None = None,
    ) -> None:
        if not _NAMESPACE.match(name) or not _NAMESPACE.match(namespace):
            raise PackError(f"bad pack name or namespace: {name!r}, {namespace!r}")
        self.name = name
        self.namespace = namespace
        self.description = description
        #: written to storage by the pack's load function, so ``install``
        #: can see that this build of the pack (not an older one) loaded
        self.stamp = stamp if stamp is not None else f"{time.time():.3f}"
        self.functions: dict[str, list[str]] = {}
        self.loot_tables: dict[str, dict] = {}
        self.tags: dict[tuple[str, str], list[str]] = {}
        self._load: list[str] = []
        self._tick: list[str] = []
        self._objectives: dict[str, str] = {}
        self._constants: dict[str, set[int]] = {}

    # -- names ------------------------------------------------------------

    def id(self, path: str) -> str:
        """the full name of one of this pack's functions (``ns:path``)"""
        if not _PATH.match(path):
            raise PackError(f"bad function name: {path!r}")
        return f"{self.namespace}:{path}"

    @property
    def storage(self) -> str:
        """the command storage this pack's load function stamps"""
        return f"{self.namespace}:pack"

    # -- content ----------------------------------------------------------

    def function(
        self,
        path: str,
        lines: Iterable[str],
        *,
        load: bool = False,
        tick: bool = False,
    ) -> str:
        """add a function and return its full name. ``load`` runs it on
        every ``reload`` (and at server start), ``tick`` every game tick,
        in the order added"""
        name = self.id(path)
        if path in self.functions:
            raise PackError(f"function {name} defined twice")
        if path == "_load":
            raise PackError("_load is the pack's own load function")
        lines = list(lines)
        for n, line in enumerate(lines, 1):
            check_line(line, f"{name} line {n}")
        commands = sum(1 for line in lines if not line.startswith("#"))
        if commands > MAX_COMMANDS:
            raise PackError(f"{name} has {commands} commands (max {MAX_COMMANDS})")
        self.functions[path] = lines
        if load:
            self._load.append(name)
        if tick:
            self._tick.append(name)
        return name

    def loot_table(self, path: str, table: dict) -> str:
        """add a loot table (``data/<namespace>/loot_table/<path>.json``,
        singular as the function folder is) and return its full name"""
        name = self.id(path)
        self.loot_tables[path] = table
        return name

    def tag(self, registry: str, name: str, values: Iterable[str]) -> str:
        """add values to a tag of any namespace, the game's own included
        (``registry`` as the folder under ``tags``: ``entity_type``; ``name``
        as ``minecraft:raiders``). It adds to the tag and replaces nothing.
        Returns the tag as a command names it (``#minecraft:raiders``)"""
        namespace, _, path = name.partition(":")
        if not _NAMESPACE.match(namespace) or not _PATH.match(path):
            raise PackError(f"bad tag name: {name!r}")
        if not _PATH.match(registry) or registry == "function":
            raise PackError(f"bad tag registry: {registry!r}")
        have = self.tags.setdefault((registry, name), [])
        have += [v for v in values if v not in have]
        return f"#{name}"

    def objectives(self, objectives: dict[str, str]) -> None:
        """scoreboard objectives (name -> criterion, usually ``dummy``) that
        the load function makes. Adding one that exists is harmless: it
        fails and keeps its scores"""
        for name, criterion in objectives.items():
            if not _OBJECTIVE.match(name):
                raise PackError(f"bad objective name: {name!r}")
            if self._objectives.get(name, criterion) != criterion:
                raise PackError(f"objective {name} given two criteria")
            self._objectives[name] = criterion

    def constants(self, objective: str, *values: int) -> None:
        """fake players ``#<value>`` holding constants, set on load, for
        ``scoreboard players operation`` (which takes no literal numbers)"""
        if objective not in self._objectives:
            raise PackError(f"constants in an unknown objective: {objective}")
        self._constants.setdefault(objective, set()).update(values)

    def setup_lines(self) -> list[str]:
        """the pack's own load function: objectives, constants, the stamp"""
        lines = [
            f"scoreboard objectives add {name} {criterion}"
            for name, criterion in self._objectives.items()
        ]
        for objective, values in self._constants.items():
            lines += [
                f"scoreboard players set #{v} {objective} {v}" for v in sorted(values)
            ]
        stamp = json.dumps(self.stamp)
        lines.append(f"data modify storage {self.storage} stamp set value {stamp}")
        return lines

    def teardown_lines(self) -> list[str]:
        """commands (for RCON or a function) that remove what the load
        function made: the objectives, with every score in them, and the
        stamp"""
        lines = [f"scoreboard objectives remove {name}" for name in self._objectives]
        lines.append(f"data remove storage {self.storage} stamp")
        return lines

    # -- output -----------------------------------------------------------

    def files(self) -> dict[str, str]:
        """the pack as relative path -> text"""
        meta = {
            "pack": {
                "description": self.description,
                "min_format": PACK_FORMAT,
                "max_format": PACK_FORMAT,
            }
        }
        out = {"pack.mcmeta": json.dumps(meta, indent=2) + "\n"}
        base = f"data/{self.namespace}/function"
        out[f"{base}/_load.mcfunction"] = "\n".join(self.setup_lines()) + "\n"
        for path, lines in self.functions.items():
            out[f"{base}/{path}.mcfunction"] = "\n".join(lines) + "\n"
        for path, table in self.loot_tables.items():
            out[f"data/{self.namespace}/loot_table/{path}.json"] = (
                json.dumps(table, indent=2) + "\n"
            )
        for (registry, name), values in self.tags.items():
            namespace, _, path = name.partition(":")
            out[f"data/{namespace}/tags/{registry}/{path}.json"] = (
                json.dumps({"replace": False, "values": values}, indent=2) + "\n"
            )
        tags = "data/minecraft/tags/function"
        load = [self.id("_load"), *self._load]
        out[f"{tags}/load.json"] = json.dumps({"values": load}, indent=2) + "\n"
        if self._tick:
            out[f"{tags}/tick.json"] = (
                json.dumps({"values": self._tick}, indent=2) + "\n"
            )
        return out

    def write(self, datapacks_dir: str | Path) -> Path:
        """write the pack as ``<datapacks_dir>/<name>``, replacing an older
        copy of this pack and touching nothing else there"""
        folder = pack_folder(datapacks_dir, self.name)
        remove_folder(folder)
        for path, text in self.files().items():
            target = folder / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
        return folder


def pack_folder(datapacks_dir: str | Path, name: str) -> Path:
    """the folder of the pack ``name``; the datapacks folder must exist"""
    root = Path(datapacks_dir)
    if not root.is_dir():
        raise PackError(f"no such datapacks folder: {root}")
    if not _NAMESPACE.match(name):
        raise PackError(f"bad pack name: {name!r}")
    return root / name


def remove_folder(folder: Path) -> bool:
    """delete a pack's folder if it is there. Refuses anything that is not
    a datapack folder (no ``pack.mcmeta``), so a wrong path cannot delete
    something else"""
    if folder.is_symlink() or not folder.exists():
        if folder.is_symlink():
            raise PackError(f"{folder} is a link, not a pack folder")
        return False
    if not (folder / "pack.mcmeta").is_file():
        raise PackError(f"{folder} is not a datapack (no pack.mcmeta): left alone")
    shutil.rmtree(folder)
    return True


def _wait(world, done, tries: int = 40) -> bool:
    """poll ``done()``; the server may be paused with nobody online, and
    then finishes a reload only when made to tick"""
    for n in range(tries):
        if done():
            return True
        if n % 4 == 3:
            world.cmd("tick sprint 2")
        time.sleep(0.25)
    return done()


def enabled_packs(world) -> list[str]:
    """the names of the enabled data packs, e.g. ``file/station``"""
    reply = world.cmd("datapack list enabled")
    return re.findall(r"\[([^\]\s]+)(?: \([^)]*\))?\]", reply)


def server_log(datapacks_dir: str | Path) -> Path | None:
    """the server's log, if it is where a plain server keeps it: beside the
    world folder that holds this ``datapacks`` folder"""
    log = Path(datapacks_dir).resolve().parent.parent / "logs" / "latest.log"
    return log if log.is_file() else None


def install(
    world, pack: Pack, datapacks_dir: str | Path, log_file: str | Path | None = None
) -> Path:
    """
    Write ``pack`` into the world's ``datapacks`` folder (which must be a
    folder this process can write, i.e. the build runs where the world's
    files are), ``reload``, and check that the game enabled it and ran this
    build's load function. Replaces an older copy. Returns the pack's folder.

    The game loads what it can of a pack and says nothing over RCON about
    the rest: a function with a bad line is left out, and the whole tick
    (or load) tag with it if the tag names it. Only the server's log tells,
    so it is read too (``log_file``, or ``server_log`` if that finds it) and
    any error naming this pack raises PackError.
    """
    log = Path(log_file) if log_file else server_log(datapacks_dir)
    size = log.stat().st_size if log else 0
    folder = pack.write(datapacks_dir)
    world.cmd("reload")
    wanted = f'"{pack.stamp}"'

    def loaded() -> bool:
        return wanted in world.cmd(f"data get storage {pack.storage} stamp")

    ok = _wait(world, loaded)
    if not ok and f"file/{pack.name}" not in enabled_packs(world):
        # a new pack is enabled by reload; one disabled by hand is not
        world.cmd(f'datapack enable "file/{pack.name}"')
        ok = _wait(world, loaded)
    errors = []
    if log:
        marks = (f"{pack.namespace}:", f"file/{pack.name}")
        errors = [e for e in load_errors(log, size) if any(m in e for m in marks)]
    if errors or not ok:
        raise PackError(
            f"datapack {pack.name} did not load whole:\n  "
            + "\n  ".join(errors or ["its load function did not run: see the log"])
        )
    return folder


def uninstall(world, pack: Pack, datapacks_dir: str | Path) -> bool:
    """remove the pack's objectives, stamp and folder, and ``reload`` so
    its functions stop. True if there was a folder to remove"""
    for line in pack.teardown_lines():
        world.cmd(line)
    removed = remove_folder(pack_folder(datapacks_dir, pack.name))
    world.cmd("reload")

    def gone() -> bool:
        return f"file/{pack.name}" not in world.cmd("datapack list")

    _wait(world, gone)
    return removed


def load_errors(log_file: str | Path, since: int = 0) -> list[str]:
    """lines of the server log, from byte ``since`` on, that report a data
    pack problem (a function that did not parse, a tag naming a function
    that is missing). Take ``since`` as the log's size before ``reload``"""
    with open(log_file, "rb") as f:
        f.seek(since)
        text = f.read().decode("utf-8", "replace")
    marks = ("Failed to load function", "Couldn't load tag", "Failed to load")
    return [
        line
        for line in text.splitlines()
        if "/ERROR]" in line or any(m in line for m in marks)
    ]
