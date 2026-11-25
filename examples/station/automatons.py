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

The fights must not be played on Peaceful, where the game removes
monsters as they are summoned: a fight that starts should see that its
first automaton is still there a moment later.
"""

from __future__ import annotations

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


# ----------------------------------------------------------------------- check


def check(ctx: Any) -> list[str]:
    """
    Live, in an empty dome (the last but one of the ring, away from the
    built rooms): an automaton summoned and dressed is as the plan wants
    it and scaled by the level's values; it drops nothing; the count
    follows the dome's form and the level; the automatons go when the
    dome empties. Players are stood in for (``game_checks``). Not proved:
    that automatons leave each other alone and fight a player, which
    needs a player.
    """
    import game_checks

    dome = ctx.layout.DOMES[-2]
    n = dome.index
    problems: list[str] = []
    x, y, z, _ = domes.entrance(dome)
    spot = domes.middle((x, y, z))
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
    game_checks.clear_stand_ins(ctx)
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
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    ctx.cmd(f"kill {selector(n)}")
    ctx.advance(30)
    expect(
        "items dropped by a killed automaton",
        ctx.count(f"@e[type=minecraft:item,{domes.sphere(dome)}]"),
        0,
    )

    # the count: by the dome's form and the level
    ctx.set_score("#diff.count", 100)
    args = f"{{dome:{n},solo:2,duo:3,more:1}}"
    game_checks.stand_in(ctx, "st.a1", n)
    ctx.function("mob/count", args)
    expect("the count, one in the dome", ctx.score("#mob.n"), 2)
    game_checks.stand_in(ctx, "st.a2", n)
    ctx.function("mob/count", args)
    expect("the count, two in the dome", ctx.score("#mob.n"), 3)
    game_checks.stand_in(ctx, "st.a3", n)
    ctx.set_score("#diff.count", 160)
    ctx.function("mob/count", args)
    expect("the count, three in the dome at 160%", ctx.score("#mob.n"), 6)
    for line in room_lines(n, 4):
        ctx.cmd(line)
    got = {name: ctx.score(name) for name in ("#mob.alive", "#mob.room", "#mob.n")}
    expect(
        "a cap of 4, none alive", got, {"#mob.alive": 0, "#mob.room": 4, "#mob.n": 4}
    )

    # they go when the dome empties
    for _ in range(3):
        ctx.cmd(summon("minecraft:skeleton", "Riveter", spot, n, IRON))
    ctx.cmd(dress_line(n, 20, 20))
    ctx.cmd(alive_line(n))
    expect("three summoned", ctx.score("#mob.alive"), 3)
    ctx.advance(game_checks.SCAN)
    expect("still there with players in the dome", ctx.count(selector(n)), 3)
    game_checks.clear_stand_ins(ctx)
    ctx.advance(game_checks.SCAN)
    expect("left when the dome emptied", ctx.count(selector(n)), 0)
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(dome)}]")
    for name, value in saved.items():
        if value is not None:
            ctx.set_score(name, value)
    return problems
