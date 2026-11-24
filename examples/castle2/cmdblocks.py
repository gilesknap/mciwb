"""
Hidden command blocks for castle2: the castle's own rules, which run in the
world without mciwb (the adventure zone and the books that come back,
protect.py; the reset, the fight, the purse and the machines' feedback,
play.py).

They all stand in the command bank (`castle2_layout.COMMAND_BANK`): a box of
stone bricks inside one chunk, deep in the upper ward's fill, which the
protect stage keeps forceloaded so that they run wherever the players are.
A `Bank` is the plan of what stands in it, made without touching the world:

- ``bank.row(name, commands)``: a row of blocks running east, a repeating
  block and then chain blocks, all always active, so the commands run in
  order every tick. ``first="impulse"`` starts the row with an impulse block
  that needs redstone instead (no row uses one). Each feature has its
  own row (`ROWS`): add a name there for a new one.
- ``bank.rows(name, commands)``: the same for more commands than one row
  holds: rows ``name 1``, ``name 2`` ..., each a chain of its own. The rows
  of one tick run in no known order, so a command must not lean on one in
  another row having run first.
- ``bank.store(name)``: a cell of the store, the bank's top layer, for a
  master copy of a block that a command clones back into the castle.
- ``bank.score(name)``: a number the commands keep (a fake player's score
  in the castle's own scoreboard objective, `OBJECTIVE`), set to 0 when
  the bank is built.
- `start_timer` and `timer`: a timer is an area effect cloud in the bank's
  chunk, which the game ages and removes by itself: a command starts one
  and others test that it is there, or its age. Nothing has to count, so
  nothing succeeds (and is logged) every tick while it runs.

A feature adds a function to `PLANNERS` that plans its rows and masters on
a Bank; `plan()` runs them all. The protect stage places the whole plan
(``plan().place()``, which builds the bank afresh) and verify reads every
block back (``plan().problems()``), so both work from the same plan, as
the machines' ``*_cells`` do. Write commands so that they fail while there is
nothing to do: a command block's success is logged to the server's console
(`command_block_output`), a failure is not.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

import castle_lib as L
from castle2_layout import COMMAND_BANK, V
from mcipc.rcon.exceptions import (
    InvalidArgument,
    InvalidInteger,
    InvalidNameOrUUID,
    NoPlayerFound,
    UnexpectedTrailingData,
    UnknownCommand,
)

from mciwb.imports import Vec3

KINDS = {
    "repeating": "minecraft:repeating_command_block",
    "chain": "minecraft:chain_command_block",
    "impulse": "minecraft:command_block",
}
SHELL = L.BRICK
# each feature's row in the bank: rows are two apart (north to south, then
# the next layer up), so a new feature takes the next free number
ROWS = {
    name: k
    for k, name in enumerate(
        ["zone", "books", "notes", "purse", "organ", "archery", "lectern"]
        + [f"fight {k}" for k in range(1, 5)]
        + [f"reset {k}" for k in range(1, 8)]
    )
}
# the masters in the store, in order (`Bank.store`)
STORE = [
    "book of hours",
    "tavern",
    "fletcher",
    "prisoner",
    "founder",
    "alchemist",
    "cantor",
    "steward",
    "last",
    "library shelf",
]
# the scoreboard objective that holds the bank's numbers (`Bank.score`)
OBJECTIVE = L.TAG
TIMER = "minecraft:area_effect_cloud"


# the features' planners: each takes the Bank and adds its rows and masters
PLANNERS: list[Callable[[Bank], None]] = []


def plan() -> Bank:
    """the whole bank, as every feature plans it"""
    bank = Bank()
    for planner in PLANNERS:
        planner(bank)
    return bank


@dataclass
class CommandBlock:
    name: str  # its row's name and its place in it, for messages
    pos: Vec3
    kind: str  # a key of KINDS
    command: str
    facing: str = "east"
    auto: bool = True  # always active (an impulse block waits for redstone)

    def state(self) -> str:
        """the block with its data, as setblock takes it"""
        return (
            f"{KINDS[self.kind]}[facing={self.facing}]"
            f"{{Command:{L.snbt_string(self.command)},auto:{int(self.auto)}b}}"
        )


def bank_box(pos=V) -> tuple[Vec3, Vec3]:
    """the bank's corners in the world"""
    x1, y1, z1, x2, y2, z2 = COMMAND_BANK
    return pos(x1, y1, z1), pos(x2, y2, z2)


def bank_chunk(pos=V) -> tuple[int, int]:
    """the chunk the bank stands in (the one chunk left forceloaded)"""
    a, _ = bank_box(pos)
    return int(a.x) // 16, int(a.z) // 16


def layout_problems() -> list[str]:
    """the bank must fit in one chunk, the rows and the store in the bank"""
    a, b = bank_box()
    problems = []
    if (int(a.x) // 16, int(a.z) // 16) != (int(b.x) // 16, int(b.z) // 16):
        problems.append(f"the command bank {a}..{b} is not inside one chunk")
    x1, y1, z1, x2, y2, z2 = COMMAND_BANK
    # (rows two apart from y1 + 1 up, under the store's layer at y2 - 1)
    rows = ((z2 - z1 - 1) // 2 + 1) * ((y2 - y1 - 3) // 2 + 1)
    if max(ROWS.values()) >= rows:
        problems.append(f"the command bank has room for {rows} rows only")
    if len(STORE) > x2 - x1 - 1:
        problems.append("the command bank's store is full")
    return problems


@dataclass
class Bank:
    """the plan of the command bank: its command blocks and its store"""

    pos: object = V
    blocks: list[CommandBlock] = field(default_factory=list)
    masters: dict[str, tuple[Vec3, str]] = field(default_factory=dict)
    scores: list[str] = field(default_factory=list)

    def _cell(self, x: int, y: int, z: int) -> Vec3:
        return self.pos(x, y, z)  # type: ignore[operator]

    def row(
        self, name: str, commands: list[str], first: str = "repeating"
    ) -> list[CommandBlock]:
        """plan a row of command blocks: ``first`` and then chain blocks"""
        x1, y1, z1, x2, _y2, z2 = COMMAND_BANK
        per_layer = (z2 - z1 - 1) // 2 + 1
        r = ROWS[name]
        y, z = y1 + 1 + 2 * (r // per_layer), z1 + 1 + 2 * (r % per_layer)
        if len(commands) > x2 - x1 - 1:
            raise ValueError(f"the {name} row has room for {x2 - x1 - 1} commands")
        row = [
            CommandBlock(
                f"{name} {k + 1}",
                self._cell(x1 + 1 + k, y, z),
                "chain" if k else first,
                command,
                auto=bool(k) or first != "impulse",
            )
            for k, command in enumerate(commands)
        ]
        self.blocks += row
        return row

    def rows(self, name: str, commands: list[str]) -> list[CommandBlock]:
        """plan as many rows as the commands need: ``name 1``, ``name 2`` ..."""
        x1, _y1, _z1, x2, _y2, _z2 = COMMAND_BANK
        n = x2 - x1 - 1
        out = []
        for k in range(0, len(commands), n):
            out += self.row(f"{name} {k // n + 1}", commands[k : k + n])
        return out

    def score(self, name: str) -> str:
        """a number kept in the bank's objective, as commands name it
        (``#wave castle_...``); 0 when the bank is built"""
        if name not in self.scores:
            self.scores.append(name)
        return f"{name} {OBJECTIVE}"

    def store(self, name: str, block: str = "") -> Vec3:
        """the store's cell for a master copy; give its block to plan it"""
        x1, _y1, z1, _x2, y2, _z2 = COMMAND_BANK
        p = self._cell(x1 + 1 + STORE.index(name), y2 - 1, z1 + 1)
        if block:
            self.masters[name] = (p, block)
        return p

    def place(self) -> None:
        """build the bank: solid, then its masters and its command blocks.
        The blocks go in from each row's far end, so that no chain runs
        before it is whole. Its numbers start at 0 and its timers stop"""
        a, b = bank_box(self.pos)
        L.fill(a, b, SHELL)
        L.cmd(f"kill @e[type={TIMER},{L.box_selector(a, b)}]")
        L.cmd(f"scoreboard objectives add {OBJECTIVE} dummy")
        for name in self.scores:
            L.cmd(f"scoreboard players set {name} {OBJECTIVE} 0")
        for p, block in self.masters.values():
            L.set_block(p, block)
        for cb in reversed(self.blocks):
            L.set_block(cb.pos, cb.state())

    def problems(self) -> list[str]:
        """what is not as planned, read back from the world"""
        bad = []
        for cb in self.blocks:
            p = cb.pos
            if not L.is_block(p, f"{KINDS[cb.kind]}[facing={cb.facing}]"):
                bad.append(f"{cb.name}: no {cb.kind} command block at {tuple(p)}")
                continue
            found = block_data(p, "Command")
            if found != cb.command:
                bad.append(f"{cb.name}: its command is {found!r}")
            if ("1b" in L.cmd(f"data get block {p.x} {p.y} {p.z} auto")) != cb.auto:
                bad.append(f"{cb.name}: auto is not {int(cb.auto)}")
        for name, (p, block) in self.masters.items():
            if not L.is_block(p, block.split("{")[0]):
                bad.append(f"the store's {name} is not at {tuple(p)}")
        for name in self.scores:
            if score(name) is None:
                bad.append(f"the score {name} is not set")
        return bad


def score(name: str) -> int | None:
    """a number of the bank's (`Bank.score`), or None if it is not set"""
    m = re.search(r"has (-?\d+) ", L.cmd(f"scoreboard players get {name} {OBJECTIVE}"))
    return int(m.group(1)) if m else None


def timer_at(pos=V) -> Vec3:
    """where the timers stand: inside the bank, so in its loaded chunk"""
    x1, _y1, z1, _x2, y2, _z2 = COMMAND_BANK
    return pos(x1 + 1, y2, z1 + 1)


def timer(name: str, age: int | None = None) -> str:
    """the selector of a running timer; with ``age``, only in the one tick
    in which it is that many ticks old (1 .. its length - 1)"""
    at = "" if age is None else f",nbt={{Age:{age}}}"
    return f"@e[type={TIMER},tag={L.TAG}.{name}{at}]"


def start_timer(name: str, ticks: int, pos=V) -> str:
    """the command that starts a timer of ``ticks`` ticks"""
    p = timer_at(pos)
    return (
        f"summon {TIMER} {p.x} {p.y} {p.z} "
        f'{{Tags:["{L.TAG}.{name}"],Duration:{ticks},Radius:0f,WaitTime:0}}'
    )


def block_data(p: Vec3, path: str) -> str:
    """a string of a block's data, unescaped ('' if it is not there)"""
    r = L.cmd(f"data get block {p.x} {p.y} {p.z} {path}")
    m = re.search(r'data: "((?:[^"\\]|\\.)*)"', r) or re.search(
        r"data: '((?:[^'\\]|\\.)*)'", r
    )
    return re.sub(r"\\(.)", r"\1", m.group(1)) if m else ""


def last_run(cb: CommandBlock) -> int:
    """the game time a command block last ran at (-1 if never)"""
    p = cb.pos
    m = re.search(
        r"data: (-?\d+)L", L.cmd(f"data get block {p.x} {p.y} {p.z} LastExecution")
    )
    return int(m.group(1)) if m else -1


def parses(command: str) -> bool:
    """does the server accept a command? (It is run: use it for commands
    that do nothing when there is nothing to do)"""
    try:
        r = L.cmd(command)
    except NoPlayerFound:
        return True  # nobody to act on: accepted all the same
    except (
        InvalidArgument,
        InvalidInteger,
        InvalidNameOrUUID,
        UnexpectedTrailingData,
        UnknownCommand,
    ):
        return False
    return "<--[HERE]" not in r


def forceloaded() -> list[tuple[int, int]]:
    """the overworld's forceloaded chunks"""
    r = L.cmd("forceload query")
    return [(int(x), int(z)) for x, z in re.findall(r"\[(-?\d+), (-?\d+)\]", r)]
