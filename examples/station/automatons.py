"""
The automatons of The Drowned Station: the mobs a dome's fight summons,
made to the plan's rules, and the functions every fight shares. A dome's
module writes the ``summon`` lines (``summon``) and calls the functions;
the core adds the functions to the pack (``add_functions``) and removes a
dome's automatons when its last player leaves and on a reset.

**An automaton** (``summon``) is a zombie, husk, skeleton or the like with
a name, in armour that never drops, that picks nothing up, is never a
baby, calls no reinforcements (a zombie's ``spawn_reinforcements`` is 0),
does not despawn, drops nothing when it dies (its loot table is the
pack's ``station:empty``) and is on the team ``st.automaton``, so that
automatons do not fight each other. It carries the tags ``st.mob``,
``st.mob<n>`` for its dome n and, until dressed, ``st.new``. Never a
creeper, an enderman or anything that damages blocks.

**Functions** (objective ``st``):

- ``station:mob/dress {health:20,damage:30}``, run as a new automaton:
  its health and its melee damage for the level in force. ``health`` is
  its health at level 5 and ``damage`` ten times its damage at level 5
  (30 is a zombie's 3); they are scaled by ``#diff.health`` and
  ``#diff.damage``. Takes ``st.new`` off. ``dress_line(n, health,
  damage)`` is the line that dresses every new automaton of dome n. (A
  skeleton's arrows do not follow ``attack_damage``: its damage is the
  game's.)
- ``station:mob/count {dome:4,solo:2,duo:3,more:1}``: how many to summon,
  into ``#mob.n``: ``solo`` or ``duo`` by the dome's form, ``more`` for
  each player in the dome beyond two, the whole scaled by ``#diff.count``,
  never less than 1.
- ``alive_line(n)``: the line that counts dome n's automatons into
  ``#mob.alive``; with a cap, ``room_lines(n, cap)`` also leaves in
  ``#mob.room`` how many more the cap allows and cuts ``#mob.n`` down to
  it, so a wave never piles up.
- ``station:mob/remove``, run as an automaton: gone, with no death to
  see. ``remove_line(n)`` removes all of dome n's. The core runs it when
  dome n empties and on ``station:reset/all``.

**The three kinds** (``STOKER``, ``RIVETER``, ``SLAG_HUSK``; `Kind`): a
Stoker is a zombie in copper with a shovel, a Riveter a skeleton in a
copper helmet with a bow, a Slag Husk a husk in iron. ``summon_kind``
and ``dress_kind_line`` write them; every fight uses these names.

**Waves** (``waves(pack, n, points, ...)``): the functions of a fight that
casts automatons at fixed spawn points every so often. The dome's module
sets how many of each kind a wave wants (``#wave<n>.<kind>``, perhaps
from ``mob/count``) and calls the lines it is given: ``arm`` when the
fight starts, ``tick`` every tick it runs, ``leash`` every half second or
so. A wave is cast only at spawn points with a player within ``near``
blocks, never beyond the cap of all the dome's automatons alive
(``#wave<n>.cap``) nor a kind's own cap, and the time between waves
(``#wave<n>.gap``) is scaled by ``#diff.timer`` when armed. An automaton
keeps the tag of its spawn point: ``leash`` puts back there any that has
left the dome, and ``fence_lines`` any that has left a box.

**Fight services** (the core calls or generates these):

- ``#difficulty`` (objective ``st``): the game's difficulty, 0 Peaceful
  to 3 Hard, read when the pack loads and by
  ``station:fight/difficulty``. On Peaceful the game removes monsters as
  they are summoned: a fight must not start unless it is 1 or more.
- **A death.** The first tick a player in the game is alive again after
  dying, the core gives them 5 s of Resistance, removes the automatons
  within ``CLEAR_ROUND`` blocks of the entrance spot of the dome they are
  in (so nobody respawns into a mob), calls that dome's hook
  ``dome/<n>/died`` as the player (the room's own penalty), and sets
  their ``st.died`` back to 0. A module does not read ``st.died``.
- ``sweep_lines(dome)``: arrows stuck in things and experience orbs in a
  dome, gone. The core runs them when a dome empties; a fight may too.
- ``bar(pack, n, title)``: a bossbar of the dome's own (``station:d<n>``)
  shown only to the players in that dome while it is on (`Bar`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import datapack as dp
import domes

OBJ = "st"
STORE = "station:game"
TAG = "st.mob"
NEW = "st.new"
TEAM = "st.automaton"
LOOT = "empty"  # the pack's loot table that drops nothing

#: suits of armour: slot -> item
COPPER = {
    "head": "minecraft:copper_helmet",
    "chest": "minecraft:copper_chestplate",
    "legs": "minecraft:copper_leggings",
    "feet": "minecraft:copper_boots",
}
IRON = {
    "head": "minecraft:iron_helmet",
    "chest": "minecraft:iron_chestplate",
    "legs": "minecraft:iron_leggings",
    "feet": "minecraft:iron_boots",
}
#: the mobs that can call reinforcements
ZOMBIES = ("zombie", "husk", "drowned", "zombie_villager")
#: how far round a dome's entrance spot a respawn clears of automatons
CLEAR_ROUND = 7


@dataclass(frozen=True)
class Kind:
    """a kind of automaton: its mob, name and dress, and its health and
    ten times its melee damage at level 5 (see ``mob/dress``)"""

    key: str
    entity: str
    name: str
    equipment: tuple[tuple[str, str], ...]
    health: int
    damage: int

    @property
    def tag(self) -> str:
        return f"st.k.{self.key}"


STOKER = Kind(
    "stoker",
    "minecraft:zombie",
    "Stoker",
    (*COPPER.items(), ("mainhand", "minecraft:iron_shovel")),
    20,
    30,
)
RIVETER = Kind(
    "riveter",
    "minecraft:skeleton",
    "Riveter",
    (("head", COPPER["head"]), ("mainhand", "minecraft:bow")),
    20,
    20,
)
SLAG_HUSK = Kind("husk", "minecraft:husk", "Slag Husk", tuple(IRON.items()), 24, 30)
KINDS = (STOKER, RIVETER, SLAG_HUSK)
#: Hull Breach's: a drowned with a trident (no wave casts it by default)
BREACHER = Kind(
    "breacher",
    "minecraft:drowned",
    "Breacher",
    (("head", COPPER["head"]), ("mainhand", "minecraft:trident")),
    20,
    30,
)


def dome_tag(index: int) -> str:
    """the tag of the automatons of a dome"""
    return f"{TAG}{index}"


def selector(index: int, more: str = "") -> str:
    """the selector of a dome's automatons"""
    return f"@e[tag={dome_tag(index)}{',' + more if more else ''}]"


def summon(
    entity: str,
    name: str,
    where: str,
    dome_index: int,
    equipment: dict[str, str] | None = None,
    tags: tuple[str, ...] = (),
) -> str:
    """
    The command that summons an automaton (see the module docstring).
    ``entity`` is the mob (``minecraft:zombie``), ``where`` the ``x y z``
    (``domes.middle(cell)``), ``equipment`` slot -> item (``head``,
    ``chest``, ``legs``, ``feet``, ``mainhand``, ``offhand``: a suit such
    as ``COPPER`` with a hand added). Dress it in the same tick
    (``dress_line``).
    """
    kit = equipment or {}
    worn = ",".join(f'{slot}:{{id:"{item}",count:1}}' for slot, item in kit.items())
    kept = ",".join(f"{slot}:0f" for slot in kit)
    listed = ",".join(f'"{t}"' for t in (TAG, dome_tag(dome_index), NEW, *tags))
    nbt = [
        f"Tags:[{listed}]",
        f'CustomName:"{name}"',
        f'Team:"{TEAM}"',
        "PersistenceRequired:1b",
        "CanPickUpLoot:0b",
        "IsBaby:0b",
        f'DeathLootTable:"station:{LOOT}"',
        f"equipment:{{{worn}}}",
        f"drop_chances:{{{kept}}}",
    ]
    if entity.removeprefix("minecraft:") in ZOMBIES:
        nbt.append('attributes:[{id:"minecraft:spawn_reinforcements",base:0d}]')
    return f"summon {entity} {where} {{{','.join(nbt)}}}"


def summon_kind(
    kind: Kind, where: str, dome_index: int, tags: tuple[str, ...] = ()
) -> str:
    """the command that summons one of the three kinds"""
    return summon(
        kind.entity,
        kind.name,
        where,
        dome_index,
        dict(kind.equipment),
        (kind.tag, *tags),
    )


def dress_kind_line(dome_index: int, kind: Kind) -> str:
    """the line that dresses every new automaton of a kind in a dome"""
    return dress_line(dome_index, kind.health, kind.damage, f"tag={kind.tag}")


def dress_line(dome_index: int, health: int, damage: int, more: str = "") -> str:
    """the line that dresses every new automaton of a dome (``more``:
    further selector arguments, e.g. a tag for one kind)"""
    new = selector(dome_index, f"tag={NEW}{',' + more if more else ''}")
    return (
        f"execute as {new} run function station:mob/dress "
        f"{{health:{health},damage:{damage}}}"
    )


def alive_line(dome_index: int) -> str:
    """the line that counts a dome's automatons into ``#mob.alive``"""
    return (
        f"execute store result score #mob.alive {OBJ} if entity {selector(dome_index)}"
    )


def room_lines(dome_index: int, cap: int) -> list[str]:
    """lines that count a dome's automatons, leave in ``#mob.room`` how
    many more a cap allows, and cut ``#mob.n`` down to that"""
    return [
        alive_line(dome_index),
        f"scoreboard players set #mob.room {OBJ} {cap}",
        f"scoreboard players operation #mob.room {OBJ} -= #mob.alive {OBJ}",
        f"execute if score #mob.room {OBJ} matches ..-1 "
        f"run scoreboard players set #mob.room {OBJ} 0",
        f"scoreboard players operation #mob.n {OBJ} < #mob.room {OBJ}",
    ]


def remove_line(dome_index: int | None = None) -> str:
    """the line that removes a dome's automatons (or, with no dome, all)"""
    who = selector(dome_index) if dome_index is not None else f"@e[tag={TAG}]"
    return f"execute as {who} run function station:mob/remove"


def add_functions(pack: dp.Pack) -> None:
    """add the automatons' functions, team and loot table to the pack"""
    pack.loot_table(LOOT, {"pools": []})
    pack.constants(OBJ, 100)
    pack.function(
        "mob/load",
        [f"team add {TEAM}", f"team modify {TEAM} friendlyFire false"],
        load=True,
    )
    store = f"execute store result storage {STORE} mob"

    def scaled(score: str, macro: str, percent: str) -> list[str]:
        return [
            f"$scoreboard players set {score} {OBJ} $({macro})",
            f"scoreboard players operation {score} {OBJ} *= {percent} {OBJ}",
            f"scoreboard players operation {score} {OBJ} /= #100 {OBJ}",
            f"execute if score {score} {OBJ} matches ..0 "
            f"run scoreboard players set {score} {OBJ} 1",
        ]

    pack.function(
        "mob/dress",
        [
            *scaled("#mob.h", "health", "#diff.health"),
            *scaled("#mob.d", "damage", "#diff.damage"),
            f"{store}.health int 1 run scoreboard players get #mob.h {OBJ}",
            f"{store}.damage double 0.1 run scoreboard players get #mob.d {OBJ}",
            f"function {pack.id('mob/apply')} with storage {STORE} mob",
            f"tag @s remove {NEW}",
        ],
    )
    pack.function(
        "mob/apply",
        [
            "$attribute @s minecraft:max_health base set $(health)",
            "$attribute @s minecraft:attack_damage base set $(damage)",
            "$data modify entity @s Health set value $(health)f",
        ],
    )
    pack.function(
        "mob/count",
        [
            f"$scoreboard players set #mob.n {OBJ} $(solo)",
            f"$execute if score #form$(dome) {OBJ} matches 2 "
            f"run scoreboard players set #mob.n {OBJ} $(duo)",
            f"$scoreboard players operation #mob.x {OBJ} = #occ$(dome) {OBJ}",
            f"scoreboard players remove #mob.x {OBJ} 2",
            f"$scoreboard players set #mob.m {OBJ} $(more)",
            f"scoreboard players operation #mob.x {OBJ} *= #mob.m {OBJ}",
            f"execute if score #mob.x {OBJ} matches 1.. "
            f"run scoreboard players operation #mob.n {OBJ} += #mob.x {OBJ}",
            f"scoreboard players operation #mob.n {OBJ} *= #diff.count {OBJ}",
            f"scoreboard players operation #mob.n {OBJ} /= #100 {OBJ}",
            f"execute if score #mob.n {OBJ} matches ..0 "
            f"run scoreboard players set #mob.n {OBJ} 1",
        ],
    )
    # out of sight first, so that nothing is seen to die
    pack.function("mob/remove", ["tp @s ~ -120 ~", "kill @s"])
    check_waves(pack)
    pack.function(
        "fight/difficulty",
        [f"execute store result score #difficulty {OBJ} run difficulty"],
        load=True,
    )


# ----------------------------------------------------------------------- waves


def home_tag(point: int) -> str:
    """the tag of the automatons cast at a wave's spawn point"""
    return f"st.home{point}"


def leash_lines(dome_index: int, points, inside: str) -> list[str]:
    """lines that put back at its spawn point any of a dome's automatons
    that is not ``inside`` (selector arguments: ``domes.sphere(dome)``,
    or a box from ``datapack.box_selector``)"""
    return [
        f"execute as {selector(dome_index, f'tag={home_tag(i)}')} "
        f"unless entity @s[{inside}] run tp @s {domes.middle(point)}"
        for i, point in enumerate(points)
    ]


def fence_lines(
    dome_index: int, points, low: domes.Cell, high: domes.Cell
) -> list[str]:
    """lines that put back at its spawn point any of a dome's automatons
    that has left the box of cells from ``low`` to ``high``"""
    return leash_lines(dome_index, points, dp.box_selector(low, high))


@dataclass
class Waves:
    """the lines a fight calls: see the module docstring"""

    arm: str
    tick: str
    cast: str
    leash: str


def waves(
    pack: dp.Pack,
    dome_index: int,
    points,
    kinds: tuple[Kind, ...] = KINDS,
    base: str = "",
    interval: int = 400,
    first: int = 100,
    cap: int = 8,
    caps: dict[str, int] | None = None,
    near: int = 12,
    inside: str = "",
) -> Waves:
    """
    Add a dome's wave functions (``dome/<n>/wave/...``, or under ``base``
    if given) and give the lines
    that call them. ``points``: the spawn points (cells; an automaton
    stands in the cell); ``interval`` and ``first``: ticks between waves
    and before the first, at level 5; ``cap``: the most automatons alive
    in the dome; ``caps``: a kind's key -> the most of that kind alive;
    ``near``: a spawn point is used only with a player this close;
    ``inside``: where the leash keeps them (selector arguments; the
    dome's sphere if not given).
    """
    n = dome_index
    inside = inside or domes.sphere(domes.layout.DOMES[n])
    base = base or f"dome/{n}/wave"
    caps = caps or {}
    left, room, kroom = f"#wave.left {OBJ}", f"#wave.room {OBJ}", f"#wave.kroom {OBJ}"
    clock, gap = f"#wave{n} {OBJ}", f"#wave{n}.gap {OBJ}"
    pack.objectives({OBJ: "dummy"})
    pack.constants(OBJ, 100)
    # a pass over the points casts one at each that has a player by it:
    # as many passes as would fill the cap at a single point
    rounds = cap
    cast = []
    for kind in kinds:
        for i, point in enumerate(points):
            pack.function(
                f"{base}/spawn/{kind.key}_{i}",
                [
                    summon_kind(kind, domes.middle(point), n, (home_tag(i),)),
                    dress_kind_line(n, kind),
                    f"scoreboard players remove {left} 1",
                ],
            )
        want = f"#wave{n}.{kind.key} {OBJ}"
        lines = [
            f"scoreboard players operation {left} = {want}",
            # no more than the dome's cap leaves room for ...
            f"execute store result score #mob.alive {OBJ} if entity {selector(n)}",
            f"scoreboard players operation {room} = #wave{n}.cap {OBJ}",
            f"scoreboard players operation {room} -= #mob.alive {OBJ}",
            f"scoreboard players operation {left} < {room}",
        ]
        if kind.key in caps:
            # ... nor than this kind's own
            lines += [
                f"execute store result score #mob.alive {OBJ} "
                f"if entity {selector(n, f'tag={kind.tag}')}",
                f"scoreboard players set {kroom} {caps[kind.key]}",
                f"scoreboard players operation {kroom} -= #mob.alive {OBJ}",
                f"scoreboard players operation {left} < {kroom}",
            ]
        for _ in range(rounds):
            for i, (x, y, z) in enumerate(points):
                lines.append(
                    f"execute if score {left} matches 1.. if entity @e[tag=st.in,"
                    f"x={x + 0.5},y={y},z={z + 0.5},distance=..{near}] "
                    f"run function {pack.id(f'{base}/spawn/{kind.key}_{i}')}"
                )
        pack.function(f"{base}/cast/{kind.key}", lines)
        cast.append(f"function {pack.id(f'{base}/cast/{kind.key}')}")
    pack.function(f"{base}/cast", cast)
    pack.function(
        f"{base}/go",
        [
            f"function {pack.id(f'{base}/cast')}",
            f"scoreboard players operation {clock} = {gap}",
        ],
    )
    pack.function(
        f"{base}/arm",
        [
            f"scoreboard players set {clock} {first}",
            f"scoreboard players set {gap} {interval}",
            f"scoreboard players operation {gap} *= #diff.timer {OBJ}",
            f"scoreboard players operation {gap} /= #100 {OBJ}",
            f"scoreboard players set #wave{n}.cap {OBJ} {cap}",
            *(f"scoreboard players add #wave{n}.{k.key} {OBJ} 0" for k in kinds),
        ],
    )
    pack.function(
        f"{base}/tick",
        [
            f"scoreboard players remove {clock} 1",
            f"execute if score {clock} matches ..0 run function {pack.id(f'{base}/go')}",
        ],
    )
    pack.function(f"{base}/leash", leash_lines(n, points, inside))
    return Waves(
        arm=f"function {pack.id(f'{base}/arm')}",
        tick=f"function {pack.id(f'{base}/tick')}",
        cast=f"function {pack.id(f'{base}/cast')}",
        leash=f"function {pack.id(f'{base}/leash')}",
    )


# --------------------------------------------------------------- fight services


def sweep_lines(where: Any) -> list[str]:
    """lines that remove the arrows stuck in things and the experience
    orbs in a dome (or where selector arguments say)"""
    here = where if isinstance(where, str) else domes.sphere(where)
    return [
        f"kill @e[type=#minecraft:arrows,nbt={{inGround:1b}},{here}]",
        f"kill @e[type=minecraft:experience_orb,{here}]",
    ]


def clear_round_line(dome_index: int, cell: domes.Cell) -> str:
    """the line that removes a dome's automatons within ``CLEAR_ROUND``
    blocks of a cell"""
    x, y, z = cell
    near = f"x={x + 0.5},y={y},z={z + 0.5},distance=..{CLEAR_ROUND}"
    return f"execute as {selector(dome_index, near)} run function station:mob/remove"


def respawn_lines(dome: Any) -> list[str]:
    """lines that clear the automatons from round a dome's entrance spot"""
    return [clear_round_line(dome.index, domes.entrance(dome)[:3])]


@dataclass
class Bar:
    """a dome's bossbar: lines that show it, hide it, and set its value
    from a score (``#name objective``)"""

    id: str
    show: str
    hide: str

    def value_line(self, score: str) -> str:
        return (
            f"execute store result bossbar {self.id} value "
            f"run scoreboard players get {score}"
        )

    def name_line(self, text: str) -> str:
        return f"bossbar set {self.id} name {text}"


def bar_id(dome_index: int) -> str:
    return f"station:d{dome_index}"


def bar(
    pack: dp.Pack,
    dome_index: int,
    title: str,
    maximum: int = 100,
    color: str = "red",
    style: str = "progress",
) -> Bar:
    """
    Add a dome's own bossbar (``station:d<n>``) and give the lines that
    work it. While it is on (``#bar<n>`` 1) the core shows it, each
    second, to the players in that dome and to nobody else, and hides it
    on ``station:reset/all``.
    """
    n = dome_index
    bid = bar_id(n)
    base = f"dome/{n}/bar"
    players = f"@a[tag=st.in,scores={{st.dome={n}}}]"
    pack.function(
        f"{base}/load",
        [
            f'bossbar add {bid} "{title}"',
            f"bossbar set {bid} max {maximum}",
            f"bossbar set {bid} color {color}",
            f"bossbar set {bid} style {style}",
            f"execute unless score #bar{n} {OBJ} matches 1 "
            f"run bossbar set {bid} visible false",
        ],
        load=True,
    )
    pack.function(
        f"{base}/show",
        [
            f"scoreboard players set #bar{n} {OBJ} 1",
            f"bossbar set {bid} players {players}",
            f"bossbar set {bid} visible true",
        ],
    )
    pack.function(
        f"{base}/hide",
        [
            f"scoreboard players set #bar{n} {OBJ} 0",
            f"bossbar set {bid} visible false",
            f"bossbar set {bid} players",
        ],
    )
    return Bar(
        bid,
        f"function {pack.id(f'{base}/show')}",
        f"function {pack.id(f'{base}/hide')}",
    )


# ----------------------------------------------------------------------- check


def check_points() -> list[domes.Cell]:
    """the spawn points of the check's waves: at the two ends of the check
    cell (``fittings.check_cell``), more than ``CLEAR_ROUND`` apart"""
    import fittings

    fr = fittings.check_cell().fr
    f = fittings.CELL_HALF[0] - 1
    return [fr.at(-f, 0, 1), fr.at(f, 0, 1)]


def check_waves(pack: dp.Pack) -> Waves:
    """the waves the live check casts (``check/wave/...``)"""
    import fittings

    return waves(
        pack,
        fittings.CHECK_INDEX,
        check_points(),
        base="check/wave",
        interval=40,
        first=5,
        cap=4,
        caps={RIVETER.key: 1},
        near=3,
        inside=fittings.check_cell().selector,
    )


def check(ctx: Any) -> list[str]:
    """
    Live, in the check cell (``fittings.check_cell``, built and removed
    here): an automaton summoned and dressed is as the plan wants it and
    scaled by the level's values; it drops nothing; the count follows the
    dome's form and the level (the form and the number in the dome set by
    hand: the scan that sets them is ``game_checks.check_players``'s);
    ``remove_line`` removes them (that the core runs it when a dome
    empties is in the unit test). Not proved: that automatons leave each
    other alone and fight a player, which needs a player.
    """
    import fittings

    n = fittings.CHECK_INDEX
    cell = fittings.check_cell()
    if problems := fittings.build_cell(ctx):
        return problems
    try:
        return _check(ctx, n, cell)
    finally:
        fittings.remove_cell(ctx)


def _check(ctx: Any, n: int, cell: Any) -> list[str]:
    import game_checks

    problems: list[str] = []
    spot = domes.middle(cell.fr.at(0, 0, 1))
    items = f"@e[type=minecraft:item,{cell.selector}]"
    mine = selector(n, "limit=1")

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def number(what: str) -> float | None:
        text = ctx.data(f"entity {mine} {what}").rstrip("bdfsL")
        try:
            return float(text)
        except ValueError:
            return None

    def attribute(name: str) -> float | None:
        import re

        reply = ctx.cmd(f"attribute {mine} minecraft:{name} base get", "is ")
        m = re.search(r"is (-?[\d.]+)", reply)
        return float(m.group(1)) if m else None

    ctx.cmd(f"kill @e[tag={dome_tag(n)}]")
    saved = {
        name: ctx.score(name)
        for name in ("#diff.health", "#diff.damage", "#diff.count")
    }
    ctx.set_score("#diff.health", 150)
    ctx.set_score("#diff.damage", 50)
    kit = {**COPPER, "mainhand": "minecraft:iron_shovel"}
    reply = ctx.cmd(summon("minecraft:zombie", "Stoker", spot, n, kit))
    expect("summoned", "Summoned" in reply, True)
    expect("new, before it is dressed", ctx.count(selector(n, f"tag={NEW}")), 1)
    ctx.cmd(dress_line(n, 20, 30))
    ctx.advance(2)
    got = {
        "max_health": attribute("max_health"),
        "attack_damage": attribute("attack_damage"),
        "reinforcements": attribute("spawn_reinforcements"),
        "Health": number("Health"),
        "IsBaby": number("IsBaby"),
        "CanPickUpLoot": number("CanPickUpLoot"),
        "PersistenceRequired": number("PersistenceRequired"),
    }
    want = {
        "max_health": 30.0,
        "attack_damage": 1.5,
        "reinforcements": 0.0,
        "Health": 30.0,
        "IsBaby": 0.0,
        "CanPickUpLoot": 0.0,
        "PersistenceRequired": 1.0,
    }
    expect("the automaton, dressed at 150% health and 50% damage", got, want)
    expect("still new after dressing", ctx.count(selector(n, f"tag={NEW}")), 0)
    expect("on the team", ctx.count(selector(n, f"team={TEAM}")), 1)
    helmet = ctx.data(f"entity {mine} equipment.head.id")
    expect("its helmet", "copper_helmet" in helmet, True)
    expect("its name", "Stoker" in ctx.data(f"entity {mine} CustomName"), True)
    # killed: nothing drops
    ctx.cmd(f"kill {items}")
    ctx.cmd(f"kill {selector(n)}")
    ctx.advance(30)
    expect("items dropped by a killed automaton", ctx.count(items), 0)

    # the count: by the dome's form, the number in it and the level
    args = f"{{dome:{n},solo:2,duo:3,more:1}}"
    for occ, form, percent, want_n in ((1, 1, 100, 2), (2, 2, 100, 3), (3, 2, 160, 6)):
        ctx.set_score(f"#occ{n}", occ)
        ctx.set_score(f"#form{n}", form)
        ctx.set_score("#diff.count", percent)
        ctx.function("mob/count", args)
        expect(
            f"the count, {occ} in the dome at {percent}%", ctx.score("#mob.n"), want_n
        )
    for line in room_lines(n, 4):
        ctx.cmd(line)
    got = {name: ctx.score(name) for name in ("#mob.alive", "#mob.room", "#mob.n")}
    expect(
        "a cap of 4, none alive", got, {"#mob.alive": 0, "#mob.room": 4, "#mob.n": 4}
    )
    ctx.cmd(f"scoreboard players reset #occ{n} {OBJ}")
    ctx.cmd(f"scoreboard players reset #form{n} {OBJ}")

    # removed
    for _ in range(3):
        ctx.cmd(summon("minecraft:skeleton", "Riveter", spot, n, IRON))
    ctx.cmd(dress_line(n, 20, 20))
    ctx.cmd(alive_line(n))
    expect("three summoned", ctx.score("#mob.alive"), 3)
    ctx.cmd(remove_line(n))
    ctx.advance(2)
    expect("removed", ctx.count(selector(n)), 0)
    expect("items left after they were removed", ctx.count(items), 0)
    for name, value in saved.items():
        if value is not None:
            ctx.set_score(name, value)
    return problems


def check_fights(ctx: Any) -> list[str]:
    """
    Live, in the check cell (``fittings.check_cell``, built and removed
    here): the difficulty read; waves cast only where a player is, up to
    the cap and a kind's cap, refilled after a kill; the leash and the
    fence; a death answered (the score put back) and the clearing round a
    spot that the core runs at a dome's entrance on a respawn; the sweep;
    a dome's bossbar. Players are stood in for: a stand-in's death is its
    ``st.died`` set by hand, so that a real death is found and the
    Resistance given is not proved. The cell is no dome: that the core
    clears round the entrance of the dome the player is in is in the unit
    test.
    """
    import fittings

    cell = fittings.check_cell()
    if problems := fittings.build_cell(ctx):
        return problems
    try:
        return _check_fights(ctx, fittings.CHECK_INDEX, cell)
    finally:
        fittings.remove_cell(ctx)


def _check_fights(ctx: Any, n: int, cell: Any) -> list[str]:
    import fittings
    import game_checks

    fr = cell.fr
    problems: list[str] = []
    points = check_points()
    scratch = dp.Pack(stamp="check")
    lines = check_waves(scratch)

    def expect(what: str, got: Any, want: Any) -> None:
        game_checks.expect(problems, what, got, want)

    def alive(more: str = "") -> int:
        return ctx.count(selector(n, more))

    def near(point: domes.Cell, reach: float = 2.5) -> str:
        return f"x={point[0] + 0.5},y={point[1]},z={point[2] + 0.5},distance=..{reach}"

    ctx.cmd(remove_line(n))
    game_checks.clear_stand_ins(ctx)
    ctx.function("fight/difficulty")
    expect("the difficulty (Easy is 1)", ctx.score("#difficulty"), 1)
    # -- waves: a player at the first spawn point only
    game_checks.stand_at(ctx, "st.a1", domes.middle(points[0]))
    saved = ctx.score("#diff.timer")
    ctx.set_score("#diff.timer", 150)
    ctx.cmd(lines.arm)
    expect("the time between waves at 150%", ctx.score(f"#wave{n}.gap"), 60)
    for kind, want in ((STOKER, 3), (RIVETER, 2), (SLAG_HUSK, 0)):
        ctx.set_score(f"#wave{n}.{kind.key}", want)
    for _ in range(4):
        ctx.cmd(lines.tick)
    expect("before the first wave", alive(), 0)
    ctx.cmd(lines.tick)
    got = {
        "all": alive(),
        "stokers": alive(f"tag={STOKER.tag}"),
        "riveters": alive(f"tag={RIVETER.tag}"),
        "at the first point": alive(f"tag={home_tag(0)}"),
        "new": alive(f"tag={NEW}"),
    }
    want = {"all": 4, "stokers": 3, "riveters": 1, "at the first point": 4, "new": 0}
    expect("the first wave: cap 4, one Riveter at most", got, want)
    expect("the clock set for the next", ctx.score(f"#wave{n}"), 60)
    bow = ctx.data(
        f"entity {selector(n, f'tag={RIVETER.tag},limit=1')} equipment.mainhand.id"
    )
    expect(f"the Riveter's bow {bow!r}", "bow" in bow, True)
    ctx.cmd(lines.cast)
    expect("cast again at the cap", alive(), 4)
    ctx.cmd(f"kill {selector(n, f'tag={STOKER.tag},limit=1')}")
    ctx.cmd(lines.cast)
    expect("refilled after a kill", alive(f"tag={STOKER.tag}"), 3)
    # nobody near either point: nothing cast
    ctx.cmd(remove_line(n))
    game_checks.stand_at(ctx, "st.a1", domes.middle(fr.at(0, fittings.CELL_HALF[1])))
    ctx.cmd(lines.cast)
    expect("cast with nobody by a spawn point", alive(), 0)
    # at the second point: cast there
    game_checks.stand_at(ctx, "st.a1", domes.middle(points[1]))
    ctx.cmd(lines.cast)
    got = {"all": alive(), "at the second point": alive(f"tag={home_tag(1)}")}
    expect("cast where the player is", got, {"all": 4, "at the second point": 4})

    # -- the leash (out of the cell, into the sea above it) and the fence
    out = domes.middle(fr.at(0, 0, fittings.CELL_HEIGHT + 3))
    one = selector(n, "limit=1,sort=nearest")
    ctx.cmd(f"execute positioned {domes.middle(points[1])} run tp {one} {out}")
    ctx.cmd(lines.leash)
    expect("back from the sea on the leash", alive(near(points[1], 6)), 4)
    (px, py, pz) = points[1]
    low, high = (px - 1, py, pz - 1), (px + 1, py + 2, pz + 1)
    ctx.cmd(f"tp {selector(n)} {domes.middle(fr.at(0, 0, 1))}")
    for line in fence_lines(n, points, low, high):
        ctx.cmd(line)
    expect("back inside the fence", alive(near(points[1], 1)), 4)

    # -- a death: the score put back by the core, and a spot cleared
    ctx.cmd(remove_line(n))
    spot = points[0]
    ctx.cmd(summon_kind(STOKER, domes.middle(spot), n))
    ctx.cmd(summon_kind(STOKER, domes.middle(points[1]), n))
    ctx.cmd(dress_kind_line(n, STOKER))
    ctx.cmd(f"execute as {selector(n)} run data merge entity @s {{NoAI:1b}}")
    game_checks.stand_at(ctx, "st.a1", domes.middle(fr.at(0, 0, 1)))
    ctx.cmd("scoreboard players set @e[tag=st.a1] st.died 1")
    ctx.advance(3)
    ctx.cmd(clear_round_line(n, spot))
    got = {
        "died": ctx.score("@e[tag=st.a1,limit=1]", "st.died"),
        "by the spot": alive(near(spot, CLEAR_ROUND)),
        "across the cell": alive(near(points[1], 3)),
    }
    expect("a death answered", got, {"died": 0, "by the spot": 0, "across the cell": 1})

    # -- the sweep
    spot_up = domes.middle(points[0], 1)
    ctx.cmd(f"summon minecraft:arrow {spot_up} {{inGround:1b,NoGravity:1b}}")
    ctx.cmd(f"summon minecraft:experience_orb {spot_up} {{NoGravity:1b}}")
    kinds = "type=#minecraft:arrows", "type=minecraft:experience_orb"
    before = [ctx.count(f"@e[{k},{cell.selector}]") for k in kinds]
    for line in sweep_lines(cell.selector):
        ctx.cmd(line)
    after = [ctx.count(f"@e[{k},{cell.selector}]") for k in kinds]
    expect("an arrow and an orb, then swept", (before, after), ([1, 1], [0, 0]))

    # -- a dome's bossbar
    b = bar(scratch, n, "Charge", 50)
    for line in scratch.functions[f"dome/{n}/bar/load"]:
        ctx.cmd(line)
    hidden = ctx.cmd(f"bossbar get {b.id} visible", "currently")
    for line in scratch.functions[f"dome/{n}/bar/show"]:
        ctx.cmd(line)
    ctx.set_score("#chk.bar", 20)
    ctx.cmd(b.value_line(f"#chk.bar {OBJ}"))
    shown = ctx.cmd(f"bossbar get {b.id} visible", "currently")
    value = ctx.cmd(f"bossbar get {b.id} value", "has a value")
    for line in scratch.functions[f"dome/{n}/bar/hide"]:
        ctx.cmd(line)
    gone = ctx.cmd(f"bossbar get {b.id} visible", "currently")
    got = (
        "hidden" in hidden,
        "visible" in shown,
        "value of 20" in value,
        "hidden" in gone,
    )
    expect("the bar hidden, shown at 20, hidden", got, (True, True, True, True))
    expect("its name", "Charge" in value, True)
    ctx.cmd(f"bossbar remove {b.id}")

    ctx.cmd(remove_line(n))
    game_checks.clear_stand_ins(ctx)
    if saved is not None:
        ctx.set_score("#diff.timer", saved)
    return problems
