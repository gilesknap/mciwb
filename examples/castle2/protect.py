"""
The protect stage: what keeps Castle 2 as it was built while visitors play
in it. It is the last stage: rebuild it after any stage it reaches into
(``machines``, ``clues``, castle's ``alchemist``).

- **The adventure zone.** Command blocks in the command bank (cmdblocks.py)
  run every tick: a player in survival mode inside the zone
  (`castle2_layout.zone_box`: the site and ZONE_MARGIN round it, at any
  height) is tagged ZONE_TAG and put in adventure mode, where blocks cannot
  be broken or placed; a tagged player who is no longer in the zone (walked
  out, died and came back at the world's spawn, or gone to another
  dimension) is put back in survival and loses the tag. Only tagged players
  are ever given survival back, and only survival players are tagged, so
  creative and spectator players are never touched. The bank's chunk stays
  forceloaded (`keep_loaded`), the only one that does: the zone must work
  wherever its players are.
- **The books come back.** The Book of Hours and the three clue books on
  lecterns (tavern, fletcher, prisoners' cell) each have a master copy of
  their lectern in the bank's store; a command clones it over a lectern
  that has lost its book, so the book is the same and the lectern lock
  still reads its pages.
- **The engine's hoppers** are locked (`machines_upper.LOCK`): they pass
  their shards round as before but open to nobody. (The transmuter's
  dropper is built locked, by machines_upper.)

The stage places the whole command bank, the rows of play.py included
(the reset, the fight, the purse, the feedback: `cmdblocks.PLANNERS`).

What else protects the castle is built where it belongs: every armour
stand, item frame, person and pet is summoned invulnerable
(castle_lib.protected), the secrets have buttons inside (machines_upper,
organ), the gate has a postern (main_gate), the goats and frogs a lid
(pens).

Every command fails while it has nothing to do, so the server's console
only hears from the bank when a visitor's game mode changes or a book is
put back. `cells` gives what the stage places and `checks` what verify
reads back and works.
"""

from __future__ import annotations

import re
import time

import castle2_layout as C
import castle_lib as L
import clues
import cmdblocks
import machines_upper as M
import play  # noqa: F401  (its rows of the command bank)
from castle2_layout import V
from castle_layout import ENGINE

from mciwb.imports import Vec3

# the engine's ring of hoppers, round its centre (castle's build_inner.engine)
ENGINE_RING = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]


def zone_commands() -> list[str]:
    """the adventure zone, in the order the bank runs it every tick"""
    tag, box, dim = C.ZONE_TAG, C.zone_selector(), C.DIMENSION
    out = f"execute as @a[tag={tag}] unless entity @s[{box}] run"
    # (a box selects in the command block's dimension only, but "@s[box]"
    # does not look at the dimension: elsewhere is a test of its own)
    away = f"execute as @a[tag={tag}] at @s unless dimension {dim} run"
    return [
        f"tag @a[gamemode=survival,{box}] add {tag}",
        f"gamemode adventure @a[tag={tag},gamemode=survival,{box}]",
        f"{out} gamemode survival @s[gamemode=adventure]",
        f"{out} tag @s remove {tag}",
        f"{away} gamemode survival @s[gamemode=adventure]",
        f"{away} tag @s remove {tag}",
    ]


def lecterns() -> dict[str, tuple[Vec3, str, str]]:
    """the lecterns whose books come back: (where, the lectern as built,
    its book's title), by its name in the bank's store"""
    hours = M.lectern_cells()
    out = {"book of hours": (hours["trigger"], hours["lectern"], M.LECTERN_BOOK_TITLE)}
    for key, (p, facing) in clues.lecterns().items():
        out[key] = (p, clues.lectern_block(facing, key), clues.BOOKS[key][0])
    return out


def book_command(p: Vec3, master: Vec3) -> str:
    """clone a lectern's master over it when it has no book"""
    here = f"{p.x} {p.y} {p.z}"
    m = f"{master.x} {master.y} {master.z}"
    return (
        f"execute if block {here} minecraft:lectern[has_book=false] "
        f"run clone {m} {m} {here}"
    )


def plan_rows(b: cmdblocks.Bank) -> None:
    """protect's part of the command bank: the zone's row, the books' row
    and the lecterns' masters"""
    b.row("zone", zone_commands())
    b.row(
        "books",
        [
            book_command(p, b.store(name, block))
            for name, (p, block, _title) in lecterns().items()
        ],
    )


cmdblocks.PLANNERS.append(plan_rows)


def bank() -> cmdblocks.Bank:
    """the plan of the whole command bank (every feature's rows)"""
    return cmdblocks.plan()


def cells() -> dict:
    cx, cz, ey = ENGINE
    return {
        "bank": bank(),
        "chunk": cmdblocks.bank_chunk(),
        "hoppers": [V(cx + dx, ey, cz + dz) for dx, dz in ENGINE_RING],
    }


def installed() -> bool:
    """is the bank built? (its chunk must be loaded to tell)"""
    first = bank().blocks[0]
    return L.is_block(first.pos, cmdblocks.KINDS[first.kind])


def keep_loaded() -> None:
    """forceload the bank's chunk: the one chunk the castle leaves loaded"""
    a, _ = cmdblocks.bank_box()
    L.cmd(f"forceload add {a.x} {a.z}")


def protect() -> str:
    """castle2's protect stage"""
    c = cells()
    c["bank"].place()
    for p in c["hoppers"]:
        L.cmd(f"data merge block {p.x} {p.y} {p.z} {{{M.LOCK}}}")
    keep_loaded()
    n = len(c["bank"].blocks)
    return f"{n} command blocks in the bank (chunk {c['chunk']}), the engine locked"


# ---------------------------------------------------------------- the checks


def take_book(p: Vec3, block: str) -> None:
    """empty a lectern, as a visitor who takes its book does"""
    facing = re.search(r"facing=(\w+)", block)
    assert facing, block
    L.set_block(p, f"minecraft:lectern[facing={facing.group(1)},has_book=false]")


def has_book(p: Vec3, title: str) -> bool:
    return L.is_block(p, "minecraft:lectern[has_book=true]") and (
        clues.title_at(f"block {p.x} {p.y} {p.z} Book") == title
    )


def entity_problems() -> list[str]:
    """the summoned entities that a visitor could still harm or strip"""
    tag = f"tag={C.TAG}"
    bad = []
    for kind in L.PROTECTED:
        n = L.count_entities(f"type=minecraft:{kind},{tag}")
        safe = L.count_entities(f"type=minecraft:{kind},{tag},nbt={{Invulnerable:1b}}")
        if safe != n:
            bad.append(f"{safe} of {n} {kind} invulnerable")
    frames = L.count_entities(f"type=minecraft:item_frame,{tag}")
    fixed = L.count_entities(f"type=minecraft:item_frame,{tag},nbt={{Fixed:1b}}")
    if fixed != frames:
        bad.append(f"{fixed} of {frames} item frames fixed")
    # every armour stand but the seats' markers wears or holds something
    stands = L.count_entities(f"type=minecraft:armor_stand,{tag},nbt=!{{Marker:1b}}")
    shut = L.count_entities(
        f"type=minecraft:armor_stand,{tag},nbt={{DisabledSlots:{L.ALL_SLOTS_DISABLED}}}"
    )
    if shut != stands:
        bad.append(f"{shut} of {stands} armour stands with their slots disabled")
    golems = L.count_entities(f"type=minecraft:copper_golem,{tag}")
    waxed = L.count_entities(
        f"type=minecraft:copper_golem,{tag},nbt={{next_weather_age:-2L}}"
    )
    if waxed != golems:
        bad.append(f"{waxed} of {golems} copper golems waxed")
    return bad


def checks(check) -> None:
    """the bank as planned and running, its commands accepted, every book
    put back when it is taken (and the lectern lock still working), the
    engine's hoppers locked, the entities safe. (The forceloaded chunk is
    checked by verify's main, once the site is unloaded.) The zone's change
    of game mode needs a player: it is not tested here."""
    c = cells()
    b: cmdblocks.Bank = c["bank"]
    bad = b.problems()
    check(
        f"protect: the bank's {len(b.blocks)} command blocks and {len(b.masters)}"
        " masters are as planned" + (f" (not: {bad[:4]})" if bad else ""),
        not bad,
    )
    refused = [cb.name for cb in b.blocks if not cmdblocks.parses(cb.command)]
    check(
        f"protect: the server accepts every command (refused: {refused})",
        not refused,
    )
    ends = {cb.name: cb for cb in b.blocks}  # the last of each row wins below
    rows = {name.rsplit(" ", 1)[0]: cb for name, cb in ends.items()}
    before = {name: cmdblocks.last_run(cb) for name, cb in rows.items()}
    L.tick(5)
    idle = [name for name, cb in rows.items() if cmdblocks.last_run(cb) <= before[name]]
    check(
        f"protect: every row of the bank runs to its end as the game ticks"
        f" (idle: {idle})",
        not idle,
    )
    for name, (p, block, title) in lecterns().items():
        # (a sprinted tick can still be on its way: one that came after the
        # book was taken would put it back before it was seen to be gone)
        time.sleep(0.3)
        there = has_book(p, title)
        take_book(p, block)
        gone = not has_book(p, title)
        back = L.wait_until(lambda p=p, title=title: has_book(p, title), 10)
        check(
            f"protect: the {name} lectern's book ({title}) is there ({there}),"
            f" and is put back when taken (taken {gone}, back {back})",
            there and gone and back,
        )
    hours = M.lectern_cells()
    try:
        M.set_page(hours["trigger"], C.LECTERN_PAGE)
        opened = M.wait_for(lambda: M.door_open(hours), 20)
    finally:
        M.set_page(hours["trigger"], 1)
    shut = M.wait_for(lambda: M.door_shut(hours, hours["material"]), 20)
    check(
        "protect: the Book of Hours put back still works the lectern lock"
        f" (opened {opened}, shut again {shut})",
        opened and shut,
    )
    unlocked = [tuple(p) for p in c["hoppers"] if not M.locked(p)]
    check(
        f"protect: the engine's {len(c['hoppers'])} hoppers are locked"
        f" (not: {unlocked})",
        not unlocked,
    )
    bad = entity_problems()
    check(
        "protect: every armour stand, item frame, painting, person and pet is"
        " invulnerable, the frames fixed, the stands' slots disabled"
        + (f" (not: {bad})" if bad else ""),
        not bad,
    )
    print(
        "INFO protect: the zone's change of game mode needs a player in"
        " survival mode: not tested"
    )
