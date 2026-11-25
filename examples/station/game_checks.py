"""
Live checks of the game core (game.py), worked over RCON on the built
station. Each takes the build's context and returns the problems it found;
``verify_station.py`` runs them. They reset the game (``station:reset/all``)
before and after: do not run them over a game someone means to carry on.

**Stand-ins.** Nobody is online when these run, so a player is stood in
for by an armour stand tagged ``st.standin`` (``game.STANDIN``), which the
core counts as a player in the game wherever it stands, and a function is
run as one with ``execute as``. That proves what the core does with the
count of players, with where they are, and with who called a function.

It does not prove: that a real adventure-mode player in the station's box
or on the route is found (the two ``@a[gamemode=adventure,...]`` lines of
``players/scan``), nor that a survival player is put in adventure mode;
anything aimed at ``@a``: titles, the on-screen line, sounds, the bossbar
being shown, teleports (reset to the shore, recall), respawn points, the
kit and its topping up, inventories cleared. Those lines are known to
load (the pack's install reads the server's log) and no more. They are in
PROGRESS.md for the owner's play-test.
"""

from __future__ import annotations

from typing import Any

import domes
import game
import station_layout as layout
import tunnels

SCAN = game.SCAN_TICKS + 2  # ticks that are sure to hold a scan


def stand_at(ctx: Any, tag: str, where: str, gravity: bool = False) -> None:
    """
    Put a stand-in (an armour stand with this tag too) at a position (the
    ``x y z`` of a command: ``domes.middle(cell)``), moving it if it is
    there already, and let a scan pass. Without ``gravity`` it is a
    marker that hangs where it is put and touches nothing; with it, it
    has a body and falls, so it presses a pressure plate it stands on (a
    marker, or a stand that does not fall, does not).
    """
    if ctx.count(f"@e[tag={tag}]"):
        ctx.cmd(f"tp @e[tag={tag}] {where}")
    else:
        body = "" if gravity else "NoGravity:1b,Marker:1b,"
        ctx.cmd(
            f"summon minecraft:armor_stand {where} "
            f'{{Tags:["{game.STANDIN}","{tag}"],{body}Invisible:1b}}'
        )
    ctx.advance(SCAN)


def stand_in(ctx: Any, tag: str, dome_index: int, gravity: bool = False) -> None:
    """put a stand-in at a dome's entrance (see ``stand_at``)"""
    cell = domes.entrance(layout.DOMES[dome_index])[:3]
    stand_at(ctx, tag, domes.middle(cell), gravity)


def clear_stand_ins(ctx: Any) -> None:
    ctx.cmd(f"kill @e[type=minecraft:armor_stand,tag={game.STANDIN}]")
    ctx.advance(SCAN)


def as_stand_in(ctx: Any, tag: str, path: str, args: str = "") -> None:
    """run a function of the pack as a stand-in"""
    tail = f" {args}" if args else ""
    ctx.cmd(f"execute as @e[tag={tag},limit=1] run function {ctx.pack.id(path)}{tail}")


def fresh(ctx: Any) -> None:
    """the game reset, no stand-ins"""
    ctx.cmd(f"kill @e[type=minecraft:armor_stand,tag={game.STANDIN}]")
    ctx.function("reset/all")
    ctx.advance(SCAN)


def scores(ctx: Any, *names: str) -> dict[str, int | None]:
    return {name: ctx.score(name) for name in names}


def expect(problems: list[str], what: str, got: Any, want: Any) -> None:
    if got != want:
        problems.append(f"{what}: read {got}, expected {want}")


def check_players(ctx: Any) -> list[str]:
    """the count, which dome each is in, and each dome's own form: solo
    or duo by who is in that dome, falling back to solo"""
    problems: list[str] = []
    fresh(ctx)
    got = scores(ctx, "#players", "#form1")
    expect(problems, "nobody", got, {"#players": 0, "#form1": 0})
    stand_in(ctx, "st.s1", 1)
    got = scores(ctx, "#players", "#occ1", "#occ0", "#form1")
    want = {"#players": 1, "#occ1": 1, "#occ0": 0, "#form1": 1}
    expect(problems, "one in dome 1", got, want)
    # a second player elsewhere in the game (on the dock: the shore is not
    # loaded with nobody online) leaves dome 1 in its solo form
    stand_at(ctx, "st.s2", domes.middle(layout.DOCK, 1))
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS)
    got = scores(ctx, "#players", "#occ1", "#form1", "#form0")
    want = {"#players": 2, "#occ1": 1, "#form1": 1, "#form0": 0}
    expect(problems, "one in dome 1, one on the dock", got, want)
    stand_in(ctx, "st.s2", 0)
    got = scores(ctx, "#players", "#occ0", "#form0", "#form1")
    want = {"#players": 2, "#occ0": 1, "#form0": 1, "#form1": 1}
    expect(problems, "two, in domes 1 and 0", got, want)
    where = [ctx.score(f"@e[tag={t},limit=1]", "st.dome") for t in ("st.s1", "st.s2")]
    expect(problems, "st.dome of the two", where, [1, 0])
    # the second comes into dome 1: duo at once
    stand_in(ctx, "st.s2", 1)
    got = scores(ctx, "#occ0", "#form0", "#occ1", "#form1")
    want = {"#occ0": 0, "#form0": 0, "#occ1": 2, "#form1": 2}
    expect(problems, "both in dome 1", got, want)
    # and walks on into the tunnel: in no dome, still in the game, and
    # dome 1 solo again within a few seconds, not at once
    t = layout.TUNNELS[1]
    stand_at(ctx, "st.s2", domes.middle(tunnels.at(t, t.length // 2, 0, 1)))
    there = ctx.score("@e[tag=st.s2,limit=1]", "st.dome")
    got = scores(ctx, "#players", "#occ1", "#form1")
    expect(problems, "one in a tunnel", there, -1)
    want = {"#players": 2, "#occ1": 1, "#form1": 2}
    expect(problems, "one left dome 1, half a second on", got, want)
    ctx.advance(game.SOLO_AFTER * game.SCAN_TICKS + SCAN)
    seconds = (game.SOLO_AFTER * game.SCAN_TICKS + 2 * SCAN) / 20
    expect(problems, f"one left dome 1, {seconds:.1f} s on", ctx.score("#form1"), 1)
    # on into the next dome; then one leaves the game
    stand_in(ctx, "st.s2", 2)
    got = scores(ctx, "#occ1", "#occ2", "#form2")
    expect(problems, "one in dome 2", got, {"#occ1": 1, "#occ2": 1, "#form2": 1})
    ctx.cmd("kill @e[tag=st.s1]")
    ctx.advance(SCAN)
    got = scores(ctx, "#players", "#occ1", "#form1", "#form2")
    want = {"#players": 1, "#occ1": 0, "#form1": 0, "#form2": 1}
    expect(problems, "one left the game", got, want)
    clear_stand_ins(ctx)
    expect(problems, "all gone", ctx.score("#players"), 0)
    return problems


def bar(ctx: Any) -> tuple[str, int | None, bool]:
    """the vote's bossbar: its name, value, and whether it is shown"""
    import re

    value = ctx.cmd(f"bossbar get {game.BAR} value", "has a value")
    shown = ctx.cmd(f"bossbar get {game.BAR} visible", "currently")
    name = re.search(r"\[(.*)\]", value)
    number = re.search(r"value of (\d+)", value)
    return (
        name.group(1) if name else value,
        int(number.group(1)) if number else None,
        "currently visible" in shown,
    )


def check_vote(ctx: Any) -> list[str]:
    """the vote: proposed, counted, expiring, passing; both kinds"""
    problems: list[str] = []
    fresh(ctx)
    level = ctx.score("#level")
    stand_in(ctx, "st.s1", 0)
    stand_in(ctx, "st.s2", 0)
    ctx.set_score("#solved", 3)  # something for a reset to put back

    # a reset proposed by one of two: counted, shown, not passed
    as_stand_in(ctx, "st.s1", "vote/reset")
    got = scores(ctx, "#vote.kind", "#vote.yes", "#vote.need")
    expect(
        problems,
        "reset proposed",
        got,
        {"#vote.kind": 1, "#vote.yes": 1, "#vote.need": 2},
    )
    name, value, shown = bar(ctx)
    expect(problems, "the bar's name", name, "Reset: 1 of 2")
    if not shown or value is None or not game.VOTE_SECONDS - 3 <= value:
        problems.append(f"the bar after a proposal: value {value}, shown {shown}")
    # the proposer pressing again, and another proposal, change nothing
    as_stand_in(ctx, "st.s1", "vote/reset")
    as_stand_in(ctx, "st.s2", "vote/difficulty", "{level:9}")
    got = scores(ctx, "#vote.kind", "#vote.yes", "#solved")
    expect(
        problems,
        "pressed again, and another proposal",
        got,
        {"#vote.kind": 1, "#vote.yes": 1, "#solved": 3},
    )
    ctx.advance(200)
    left, (_, value, _) = ctx.score("#vote.left"), bar(ctx)
    if left is None or not 45 <= left <= 51 or value != left:
        problems.append(f"10 s into the vote: {left} s left, the bar at {value}")
    # it runs out: closed, nothing reset
    ctx.advance(20 * game.VOTE_SECONDS)
    got = scores(ctx, "#vote.kind", "#solved")
    expect(problems, "the vote run out", got, {"#vote.kind": 0, "#solved": 3})
    expect(problems, "the bar shown after it ran out", bar(ctx)[2], False)
    confirmed = ctx.count("@e[tag=st.in,scores={st.vote=1}]")
    expect(problems, "confirmations left after it ran out", confirmed, 0)

    # proposed again and confirmed by the other: passes, and resets
    as_stand_in(ctx, "st.s2", "vote/reset")
    expect(problems, "proposed by the other", ctx.score("#vote.yes"), 1)
    as_stand_in(ctx, "st.s1", "vote/confirm")
    got = scores(ctx, "#vote.kind", "#solved")
    expect(problems, "reset confirmed by both", got, {"#vote.kind": 0, "#solved": 0})
    expect(problems, "the bar shown after it passed", bar(ctx)[2], False)

    # difficulty: a level out of range is no proposal; 7 proposed and passed
    as_stand_in(ctx, "st.s1", "vote/difficulty", "{level:11}")
    expect(problems, "level 11 proposed", ctx.score("#vote.kind"), 0)
    as_stand_in(ctx, "st.s1", "vote/difficulty", "{level:7}")
    expect(problems, "the bar's name", bar(ctx)[0], "Difficulty 7: 1 of 2")
    as_stand_in(ctx, "st.s2", "vote/difficulty", "{level:8}")  # not the level proposed
    expect(problems, "another level pressed", ctx.score("#vote.yes"), 1)
    as_stand_in(ctx, "st.s2", "vote/difficulty", "{level:7}")
    got = scores(ctx, "#vote.kind", "#level")
    expect(
        problems, "difficulty 7 confirmed by both", got, {"#vote.kind": 0, "#level": 7}
    )

    # a player leaving a vote: those left decide
    as_stand_in(ctx, "st.s1", "vote/difficulty", "{level:3}")
    ctx.cmd("kill @e[tag=st.s2]")
    ctx.advance(SCAN)
    got = scores(ctx, "#vote.kind", "#level")
    expect(
        problems,
        "the one who had not confirmed left",
        got,
        {"#vote.kind": 0, "#level": 3},
    )
    # one player: one press
    as_stand_in(ctx, "st.s1", "vote/difficulty", f"{{level:{level}}}")
    got = scores(ctx, "#vote.kind", "#level")
    expect(problems, "one player, one press", got, {"#vote.kind": 0, "#level": level})
    # someone not in the game cannot propose
    ctx.cmd(
        f"execute as @e[type=!minecraft:armor_stand,limit=1] "
        f"run function {ctx.pack.id('vote/reset')}"
    )
    expect(problems, "proposed by one not in the game", ctx.score("#vote.kind"), 0)
    fresh(ctx)
    return problems


def check_difficulty(ctx: Any) -> list[str]:
    """the level takes force on entering a dome, and scales the values"""
    problems: list[str] = []
    fresh(ctx)
    level = ctx.score("#level")
    names = tuple(game.SCALED)
    expect(
        problems,
        "the scaled values at level 5",
        game.scaled(5),
        dict.fromkeys(names, 100),
    )
    stand_in(ctx, "st.s1", 0)
    for new in (1, 10, 5):
        as_stand_in(ctx, "st.s1", "vote/difficulty", f"{{level:{new}}}")
        expect(problems, f"level {new} voted", ctx.score("#level"), new)
        before = ctx.score("#active")
        stand_in(ctx, "st.s1", 1 if ctx.score("#occ0") else 0)  # enter a dome
        got = scores(ctx, "#active", *names)
        expect(
            problems, f"level {new} in force", got, {"#active": new, **game.scaled(new)}
        )
        if before == new and new != level:
            problems.append(f"level {new} was in force before a dome was entered")
    # it survives a reset
    as_stand_in(ctx, "st.s1", "vote/difficulty", "{level:8}")
    ctx.function("reset/all")
    expect(problems, "the level after a reset", ctx.score("#level"), 8)
    ctx.set_score("#level", level if level is not None else game.DEFAULT_LEVEL)
    fresh(ctx)
    return problems


def check_progress(ctx: Any) -> list[str]:
    """the run: start, the clock, a dome solved, the win and the best time"""
    problems: list[str] = []
    fresh(ctx)
    level = ctx.score("#active")
    best_name = f"#best{level}"
    best = ctx.score(best_name)
    # a locked dome cannot be solved
    ctx.function("dome/1/solved")
    expect(
        problems,
        "a locked dome solved",
        scores(ctx, "#d1", "#solved"),
        {"#d1": 0, "#solved": 0},
    )
    ctx.function("run/start")
    got = scores(ctx, "#run", "#d0", "#d1", "#t0", "#solved")
    expect(
        problems,
        "run started",
        got,
        {"#run": 1, "#d0": 2, "#d1": 1, "#t0": 1, "#solved": 0},
    )
    ctx.advance(100)
    secs = ctx.score("#secs")
    if secs is None or not 4 <= secs <= 6:
        problems.append(f"the clock 100 ticks into the run: {secs} s")
    ctx.function("run/start")  # a second pull of the lever
    after = ctx.score("#secs")
    if secs is None or after is None or after < secs:
        problems.append(f"the clock after the lever was pulled again: {after} s")
    ctx.set_score("#secs", 754)
    ctx.advance(22)
    time = ctx.data(f"storage {game.STORE} time").replace(" ", "")
    for digits in ("m:12", "t:3"):
        if digits not in time:
            problems.append(f"the clock at 755 s or so reads {time}")
    ctx.function("dome/1/solved")
    ctx.function("dome/1/solved")
    got = scores(ctx, "#d1", "#d2", "#solved", "#t1")
    expect(
        problems,
        "dome 1 solved, twice",
        got,
        {"#d1": 2, "#d2": 1, "#solved": 1, "#t1": 1},
    )
    # the win: the last dome solved
    last = layout.DOMES[-1].index
    ctx.set_score(f"#d{last}", 1)
    ctx.set_score(best_name, 0)
    ctx.set_score("#secs", 900)
    ctx.function(f"dome/{last}/solved")
    # the run is won at once; the tunnel home starts its pump event (a
    # built tunnel: 1 while it pumps) and is open when the event is over
    got = scores(ctx, "#run", best_name, f"#t{last}")
    expect(problems, "the win", got, {"#run": 2, best_name: 900, f"#t{last}": 1})
    ctx.advance(tunnels.event_ticks(layout.TUNNELS[last]) + 20)
    expect(problems, "the tunnel home after its pump event", ctx.score(f"#t{last}"), 2)
    expect(problems, "the clock after the win", ctx.score("#secs"), 900)
    for secs, want in ((950, 900), (800, 800)):
        ctx.set_score("#run", 1)
        ctx.set_score(f"#d{last}", 1)
        ctx.set_score("#secs", secs)
        ctx.function(f"dome/{last}/solved")
        expect(
            problems,
            f"the best time after a run of {secs} s",
            ctx.score(best_name),
            want,
        )
    ctx.advance(22)
    expect(problems, "#best", ctx.score("#best"), 800)
    ctx.function("reset/all")
    expect(problems, "the best time after a reset", ctx.score(best_name), 800)
    ctx.set_score(best_name, best or 0)
    fresh(ctx)
    return problems


def check_reset(ctx: Any) -> list[str]:
    """the reset, from a scrambled state: tunnels open and half open, a
    vote open, progress made, players in"""
    problems: list[str] = []
    fresh(ctx)
    runid, level = ctx.score("#runid"), ctx.score("#level")
    stand_in(ctx, "st.s1", 0)
    stand_in(ctx, "st.s2", 1)
    ctx.function("run/start")
    first = layout.TUNNELS[tunnels.BUILT[0]]
    wait = tunnels.event_ticks(first) + 40
    ctx.advance(wait)
    expect(problems, "tunnel 0 after the run started", ctx.score("#t0"), 2)
    ctx.function("dome/1/solved")
    second = layout.TUNNELS[tunnels.BUILT[1]]
    ctx.advance(tunnels.PUMP_LEAD + tunnels.layer_step(second) + 5)  # part drained
    as_stand_in(ctx, "st.s1", "vote/difficulty", "{level:2}")
    ctx.cmd("tag @e[tag=st.s1] add st.kit")
    got = scores(ctx, "#run", "#solved", "#t0", "#t1", "#vote.kind", "#d2")
    want = {"#run": 1, "#solved": 1, "#t0": 2, "#t1": 1, "#vote.kind": 2, "#d2": 1}
    expect(problems, "scrambled", got, want)
    dry = ctx.score("#t1.dry")
    if not dry or dry >= len(tunnels.tunnel_cells(second).layers):
        problems.append(f"tunnel 1 was not part drained before the reset: {dry}")

    ctx.function("reset/all")
    ctx.advance(tunnels.event_ticks(second))  # nothing left scheduled
    names = ["#run", "#secs", "#solved", "#vote.kind"]
    names += [f"#d{d.index}" for d in layout.DOMES]
    names += [f"#t{t.index}" for t in layout.TUNNELS]
    want = dict.fromkeys(names, 0) | {"#d0": 1}
    expect(problems, "after the reset", scores(ctx, *names), want)
    expect(problems, "the run's number", ctx.score("#runid"), (runid or 0) + 1)
    expect(problems, "the level", ctx.score("#level"), level)
    expect(problems, "the bar shown", bar(ctx)[2], False)
    for index in tunnels.BUILT:
        tunnel = layout.TUNNELS[index]
        got, want_counts = tunnels.counts(ctx, tunnel), tunnels.expected(tunnel, 0)
        expect(problems, f"tunnel {index} after the reset", got, want_counts)
    # the players are still in the game, and come into their domes anew
    got = scores(ctx, "#players", "#occ0", "#occ1")
    expect(
        problems,
        "players after the reset",
        got,
        {"#players": 2, "#occ0": 1, "#occ1": 1},
    )
    kit = ctx.score("@e[tag=st.s1,limit=1]", "st.kitrun")
    expect(
        problems, "a player's kit run after coming in again", kit, ctx.score("#runid")
    )
    fresh(ctx)
    return problems


def check_restricted(ctx: Any) -> list[str]:
    """``fittings.restricted``: the items it writes are taken by the game
    and keep their rules (read back from a barrel: there is no hand to
    hold them, so that they bind an adventure-mode player is not proved)"""
    import fittings

    problems: list[str] = []
    x, y, z, _ = domes.entrance(layout.DOMES[-2])
    at = f"{x} {y} {z}"
    ctx.cmd(f"setblock {at} minecraft:barrel")
    items = {
        0: fittings.restricted(
            "minecraft:waxed_cut_copper", place_on="minecraft:gold_block", name="Pipe"
        ),
        1: fittings.restricted(
            "minecraft:iron_pickaxe",
            breaks="minecraft:waxed_cut_copper,minecraft:cut_copper",
        ),
        2: fittings.restricted("minecraft:oak_sign", place_on="#minecraft:planks"),
    }
    for slot, item in items.items():
        reply = ctx.cmd(f"item replace block {at} container.{slot} with {item}")
        expect(problems, f"slot {slot} taken: {reply!r}", "Replaced" in reply, True)
    held = ctx.data(f"block {at} Items")
    for word in (
        "can_place_on",
        "can_break",
        "gold_block",
        "#minecraft:planks",
        "Pipe",
        "hidden_components",
    ):
        expect(problems, f"{word} in what the barrel holds", word in held, True)
    ctx.cmd(f"setblock {at} minecraft:air")
    ctx.cmd(f"kill @e[type=minecraft:item,{domes.sphere(layout.DOMES[-2])}]")
    return problems
