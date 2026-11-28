"""
The game core of The Drowned Station: the datapack functions every dome
shares (who is playing, progress, the clock, kit and respawn, the vote,
difficulty, reset, recall), and the registry a module adds itself by.
``add_functions(pack, modules)`` generates all of it from the layout;
``build_station.new_pack`` calls it.

Everything is in the namespace ``station``. Scores of the game are fake
players (``#name``) in the objective ``st``; read them, and write only
those marked "set".

**Players.** Twice a second ``station:players/scan`` finds who is in the
game: adventure-mode players inside the station's box or on the route to
it (the box round the shore landing and the dock, ``route_box``). A
survival player there is put in adventure mode; creative and spectator
players are left alone and never counted.

- tag ``st.in``: in the game now. Aim at ``@a[tag=st.in]`` (``PLAYERS``),
  or at those in one dome with ``in_dome(n)``; never ``@p`` or bare ``@a``.
- ``#players``: how many, in the whole game.
- objective ``st.dome``: the dome a player is in (its index), or -1.
  ``#occ<n>``: how many are in dome n. ``#form<n>``: the form dome n is
  in: 0 nobody there, 1 solo, 2 duo. It follows the players in that dome
  and no others: duo as soon as two are in it, solo when one is, but only
  ``SOLO_AFTER`` scans (3 s) after there were two, so a player who steps
  out for a moment does not undo the room. A player on the shore or in
  another dome never changes it. (There is no game-wide mode.)
- An armour stand tagged ``st.standin`` anywhere counts as a player in the
  game: the checks' stand-in. The functions that count and locate
  (``players/locate``, ``vote/count``) are macros run twice, for the
  players and for the stand-ins (``WHO``), so the same lines serve both;
  whatever acts on a player (titles, teleports, kit) uses ``@a`` and
  passes a stand-in by. A player who has died and not yet respawned is
  still counted, and still in the dome they died in.

**Progress.** ``#d<n>``: 0 locked, 1 open, 2 solved (the start dome is
open from the first). ``#solved``: how many domes after the start dome
are solved.
``#run``: 0 not started, 1 running, 2 won. ``#secs``: the run's clock in
seconds; storage ``station:game`` ``time`` and ``best`` hold ``{m,t,o}``
(minutes, tens and ones of seconds) of the clock and of the best time at
the level in force, for ``$(m):$(t)$(o)``; ``#best`` is that best time
in seconds (0: none) and ``#best<level>`` each level's.

- ``station:run/start``: the start dome's master lever. Once per run:
  starts the clock and solves the start dome, which opens tunnel 0.
- ``station:dome/<n>/solved``: the one thing a puzzle calls when it is
  solved. Does nothing unless dome n is open and unsolved. Title and
  sound, the dome marked solved, tunnel n's pump engine woken
  (``station:tunnel/<n>/ready``: its lever by the airlock, pulled by
  anyone, starts the pump event; tunnel 0's starts at once), the next
  dome marked open and every
  player's respawn point moved to its entrance. The last dome's opens
  the last tunnel, back to the Pump House's north door, and calls
  ``station:run/win``: the clock stops, the best time for the level is
  kept, and each module's ``wins`` functions run (the trophy, the
  finale).
- Players in the game see "Domes 3 of 9, 12:40" (of the domes after the
  start dome) above the hotbar while a
  run is on, and "Pump ready" after it while a pump waits for its lever.

**Two rules every room follows.**

- *Leaving a dome never costs more than the stage in progress.* What is
  finished (a pump thrown, a quarter of a charge, a round won, pipe laid)
  is kept until the game's reset; ``empty`` puts back at most the stage
  being worked.
- *A change of form never shuts, removes or restarts something a player
  is using.* ``solo`` and ``duo`` say what the room should become; the
  room takes it up at its next safe point (between rounds, with nobody
  in the gate), not under a player's feet.

**Stub domes.** A dome with no module yet has a BYPASS lever on a brass
post by its exit that calls ``dome/<n>/solved`` (``stub_module``): the
ring is always playable end to end. A module's file replaces the stub;
its build stage runs ``clear_stub_commands(dome)`` to take the post away.

**Hooks of a dome.** A module defines any of these functions and the core
calls them; it never calls one that is not defined:

- ``dome/<n>/enter``: as and at a player who has just come into dome n
  (after the core has set the respawn point there, shown the dome's name
  and handed out the kit). ``#first`` is 1 if the dome was empty until
  this player came (the moment to set a room up anew), else 0. It runs in
  the middle of a scan: ``#occ<n>``, ``#form<n>`` and ``#players`` are
  not yet this scan's;
- ``dome/<n>/leave``: as a player who has just gone out of dome n: on
  foot, by the recall, out of the game from it, or by the game's reset;
  and, every dome's, as one back from an earlier run (offline at its
  reset). Take back what the dome lent;
- ``dome/<n>/tick``: every tick while anyone in the game is in dome n;
- ``dome/<n>/solo`` and ``dome/<n>/duo``: when the dome, open and not yet
  solved, gets its first player (after ``enter``, in the same scan), and
  again whenever ``#form<n>`` changes while it is occupied: set the
  puzzle up in that form;
- ``dome/<n>/died``: as a player in dome n who has died and is alive
  again (the core has just given them 5 s of Resistance and cleared the
  automatons from round the entrance spot): the room's own penalty;
- ``dome/<n>/empty``: when dome n has had nobody in it for
  ``EMPTY_AFTER`` scans (3 s: a step into the tunnel or a dropped
  connection is not leaving; until then ``#first`` stays 0 for whoever
  comes back) (the core has
  just removed the dome's automatons, the arrows stuck in it and its
  experience orbs, see automatons.py);
- ``dome/<n>/reset``: put back the blocks and entities that change.
  ``station:reset/all`` calls it and not ``empty``: it must leave the
  room as ``empty`` would, and more.

The level's values (``#diff.*``) change whenever anyone comes into any
dome after a vote: a room copies what it needs when it is set up
(``#first``), and does not read them in the middle of a fight.

**Death and kit.** ``keep_inventory`` is a game rule (the ``rules``
stage). A player's respawn point is the entrance (``domes.entrance``) of
the dome last entered, or of a dome that opens while they play.
``station:kit/start`` gives the start kit, once per player per run (tag
``st.kit`` and the run's number in ``st.kitrun``), on entering any dome,
so a late joiner is kitted on arrival. Food and arrows are topped up
whenever a kitted player has none. Two more kits add to it, each given
once per player per run on entering its dome or any dome after it (one
who fast travels past it is given it on arrival) (``KITS``):
``station:kit/foundry`` (the Foundry: a shield in the off hand, 32 spectral
arrows) and ``station:kit/boss`` (the Engine: an unbreakable brass helm,
cuirass and sabre). A module does not give them; it may give more of its
own in its ``enter`` hook (lent, with ``fittings.lend_line``). A death is
answered by the core (``st.died``, criterion ``deathCount``): see the
``died`` hook.

**The vote** (reset and difficulty). Run these as the player who pressed:

- ``station:vote/reset``: propose a reset, or confirm one;
- ``station:vote/difficulty {level:7}``: propose level 7, or confirm it;
- ``station:vote/confirm``: confirm whatever is proposed.

A proposal starts ``VOTE_SECONDS`` on the bossbar ``station:vote``
("Reset: 1 of 2, 57 s"), shown to the players in the game. It passes when
everyone in the game has confirmed (a player's own presses count once)
and then calls ``station:reset/all`` or sets ``#level``; otherwise it
expires. A player alone confirms with a second press: the first only opens
it ("Reset: press again to confirm, 57 s"), so neither a reset nor a level
is ever one accidental press. While one is open another proposal is
ignored. ``#vote.kind`` (0 none, 1 reset, 2 difficulty), ``#vote.value``,
``#vote.left``, ``#vote.yes``, ``#vote.need``; objective ``st.vote``: 1
for a player who has confirmed, 2 for one alone who has opened it.

**Difficulty.** ``#level``: 1 to 10, 5 by default, kept through a reset.
It takes force (``#active``) the next time anyone enters a dome, and then
these are worked out, as percentages of what the game is tuned for, 100
at level 5: ``#diff.count`` (how many mobs), ``#diff.health``,
``#diff.damage``, ``#diff.timer`` (time allowed: more at low levels),
``#diff.seq`` (the length of a sequence). To scale a score of your own:
``scoreboard players operation #x st *= #diff.count st`` then
``... /= #100 st``.

**Reset and recall.** ``station:reset/all``: every tunnel's reset, then
every dome's and module's (entities killed by tag, never by position), the vote closed, progress, clock and tags
zeroed, kits taken away, players put on the shore. ``station:recall`` (as
a player in the game): to the start dome's entrance, nothing lost. A
module only places a recall post (``fittings.recall_post_blocks`` and
``summon_recall``): the core answers a click on any of them. A player who
was offline when the game was reset is put on the shore with nothing when
they come back (``players/stale``).

**Modules.** A file ``shore.py`` or ``dome_<key>.py`` (``MODULE_FILES``)
beside this one that defines ``MODULE = game.Module(...)`` is found by the
build; see `Module`. Nothing else needs editing to add one.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import automatons
import datapack as dp
import domes
import fittings
import station_layout as layout
import tunnels

OBJ = "st"
STORE = "station:game"
#: the players in the game, for commands that act on players
PLAYERS = "@a[tag=st.in]"
STANDIN = "st.standin"
#: who is counted and located, as the start of a selector to add to: the
#: players in the game (the dead too, which ``@e`` would miss: a player on
#: the death screen has not left), then the checks' stand-ins
WHO = ("@a[tag=st.in", f"@e[type=minecraft:armor_stand,tag={STANDIN}")
BAR = "station:vote"

SCAN_TICKS = 10
SOLO_AFTER = 6  # scans with fewer than two players before duo falls to solo
EMPTY_AFTER = 6  # scans with nobody in a dome before it counts as empty
VOTE_SECONDS = 60
LEVELS = range(1, 11)
DEFAULT_LEVEL = 5
#: the scaled values: name -> (percent at level 0, percent a level)
SCALED = {
    "#diff.count": (40, 12),
    "#diff.health": (50, 10),
    "#diff.damage": (50, 10),
    "#diff.timer": (150, -10),
    "#diff.seq": (40, 12),
}
HOOKS = ("enter", "tick", "solo", "duo", "empty", "reset")
#: a hook few domes need (those that lend a player something)
MORE_HOOKS = ("leave", "died")
#: the kits after the start kit: the dome on entering which each is
#: given -> its name (``kit/<name>``, and the objective ``st.kit.<name>``)
KITS = {layout.index_of(key): key for key in ("foundry", "boss")}
#: how far round the shore landing and the dock the route's box reaches
ROUTE_MARGIN = 24

#: the files a module may be in: the way in, then a file for each dome
MODULE_FILES = ("shore", *(f"dome_{d.key}" for d in layout.DOMES))


@dataclass
class Module:
    """
    What a part of the station adds to the build, the datapack and the
    checks. Put ``MODULE = Module(...)`` in ``shore.py`` or
    ``dome_<key>.py``.

    - ``stages``: build stages, name -> function of the build's context
      (returning a line to print, or None). The names must be among the
      build's placeholders: ``shore``, ``dock``, ``lift``,
      ``start_dome_inside``, ``dome_<n>_inside``.
    - ``functions``: called with the pack, to add the module's functions
      (``pack.function(path, lines)``; a dome's go under ``dome/<n>/``,
      and those named after a hook are called by the core).
    - ``resets``: paths of functions for ``station:reset/all`` to call,
      beyond the ``dome/<n>/reset`` hooks.
    - ``wins``: paths of functions for ``station:run/win`` to call when
      the last dome is solved, after the clock has stopped and the best
      time is kept (``#won.best`` is 1 if this run set it): the Wall of
      Fame's sign, the finale.
    - ``checks``: live checks, name -> function of the context returning
      the problems found; ``verify_station.py`` runs them.
    """

    name: str
    stages: dict[str, Callable[[Any], str | None]] = field(default_factory=dict)
    functions: Callable[[dp.Pack], None] | None = None
    resets: tuple[str, ...] = ()
    wins: tuple[str, ...] = ()
    checks: dict[str, Callable[[Any], list[str]]] = field(default_factory=dict)


# ------------------------------------------------------------------ stub domes

STUB_SIGN = ("BYPASS", "This room is", "not built yet.", "Pull to pass.")


def stub_tag(index: int) -> str:
    return f"st.stub{index}"


def stub_post(dome) -> fittings.Post:
    """
    A stub dome's bypass: a lever on a brass post inside the dome, to the
    left of its outgoing mouth as you leave (the pump engine is on the
    right), as near the wall as leaves it inside, facing the room.
    """
    tunnel = layout.TUNNELS[dome.index]
    out = domes.outward(dome, tunnel)
    facing = domes.COMPASS[-out[0], -out[1]]
    inside = domes.dome_cells(dome).interior - tunnels.reserved_cells(dome)
    for s in range(0, -dome.radius, -1):
        cell = tunnels.at(tunnel, s, -(domes.DOOR_HALF_WIDTH + 2), 1)
        post = fittings.input_post(
            cell,
            facing,
            fittings.lever(facing),
            STUB_SIGN,
            "BYPASS",
            (stub_tag(dome.index),),
        )
        if post.cells <= inside:
            return post
    raise ValueError(f"no room for the bypass of {dome.name}")


def clear_stub_commands(dome) -> list[str]:
    """commands that take a stub's bypass away: for the build stage of the
    module that replaces the stub (unless the dome's shell is rebuilt,
    which wipes it anyway)"""
    post = stub_post(dome)
    return [
        f"kill @e[tag={stub_tag(dome.index)}]",
        *(f"setblock {x} {y} {z} minecraft:air" for x, y, z in sorted(post.cells)),
    ]


def stub_module(dome) -> Module:
    """
    The module of a dome that has none yet: a BYPASS lever by its exit
    that solves the dome (``station:dome/<n>/solved``), so the ring can be
    played end to end whatever is built. It takes the dome's ``_inside``
    stage; a real module (a file ``dome_<key>.py``) takes its place.
    """
    n = dome.index
    post = stub_post(dome)
    x, y, z = post.input
    lever_off = post.attached[post.input]

    def build(ctx: Any) -> str:
        for command in clear_stub_commands(dome):
            ctx.cmd(command)
        for blocks in (post.solid, post.attached):
            for cell, block in blocks.items():
                ctx.setblock(cell, block)
        for command in post.summons:
            ctx.cmd(command)
        return f"{dome.name}: a stub, its BYPASS lever at {post.input}"

    def functions(pack: dp.Pack) -> None:
        pack.function(
            f"dome/{n}/tick",
            [
                f"execute if score #d{n} {OBJ} matches 1 "
                f"if block {x} {y} {z} minecraft:lever[powered=true] "
                f"run function {pack.id(f'dome/{n}/solved')}"
            ],
        )
        pack.function(
            f"dome/{n}/reset", fittings.lever_put_lines(post.input, lever_off)
        )

    stage = "start_dome_inside" if n == 0 else f"dome_{n}_inside"
    return Module(f"stub_{dome.key}", stages={stage: build}, functions=functions)


def in_dome(index: int) -> str:
    """the selector of the players in the game who are in a dome"""
    return f"@a[tag=st.in,scores={{st.dome={index}}}]"


def route_box() -> tuple[domes.Cell, domes.Cell]:
    """the box round the shore landing and the dock: the way to the station"""
    points = (layout.SHORE_LANDING, layout.DOCK)
    m = ROUTE_MARGIN
    lo = tuple(min(p[i] for p in points) - m for i in range(3))
    hi = tuple(max(p[i] for p in points) + m for i in range(3))
    return (lo[0], lo[1], lo[2]), (hi[0], hi[1], hi[2])


def shore_spot() -> domes.Cell:
    """where the feet of a player put on the shore are"""
    x, y, z = layout.SHORE_LANDING
    return (x, y + 1, z)


def scaled(level: int) -> dict[str, int]:
    """the scaled values at a level, as the pack works them out"""
    return {name: base + step * level for name, (base, step) in SCALED.items()}


def _text(*parts: str) -> str:
    return "[" + ",".join(parts) + "]"


def _score(name: str) -> str:
    return f'{{score:{{name:"{name}",objective:"{OBJ}"}}}}'


def add_functions(pack: dp.Pack, modules: list[Module]) -> None:
    """add the whole game to a pack: the modules' functions, the tunnels'
    (built or not), the built domes' checks and the core"""
    pack.objectives(
        {
            OBJ: "dummy",
            "st.dome": "dummy",
            "st.vote": "dummy",
            "st.kitrun": "dummy",
            "st.died": "deathCount",
            **{f"st.kit.{name}": "dummy" for name in KITS.values()},
        }
    )
    automatons.add_functions(pack)
    fittings.add_check_functions(pack)
    pack.constants(OBJ, 10, 60, 100)
    for module in modules:
        if module.functions:
            module.functions(pack)
    for tunnel in layout.TUNNELS:
        if tunnel.index in tunnels.BUILT:
            tunnels.add_functions(pack, tunnel, PLAYERS)
        else:
            tunnels.add_stub_functions(pack, tunnel)
    tunnels.add_tick_function(pack)
    for index in domes.BUILT:
        domes.add_check_functions(pack, layout.DOMES[index], tunnels.BUILT)
    hooks = {
        (d.index, h)
        for d in layout.DOMES
        for h in (*HOOKS, *MORE_HOOKS)
        if f"dome/{d.index}/{h}" in pack.functions
    }
    _players(pack, hooks)
    _progress(pack, hooks, modules)
    _kit(pack)
    _vote(pack)
    _difficulty(pack)
    _reset(pack, modules, hooks)
    _clock(pack, hooks)


def _set(name: str, value: int) -> str:
    return f"scoreboard players set {name} {OBJ} {value}"


def _players(pack: dp.Pack, hooks: set[tuple[int, str]]) -> None:
    station = dp.box_selector(*layout.BOUNDS)
    route = dp.box_selector(*route_box())
    lines = [_set("#scan", 0)]
    for where in (station, route):
        lines.append(f"gamemode adventure @a[gamemode=survival,{where}]")
    lines.append("tag @a[tag=st.in] remove st.in")
    for where in (station, route):
        lines.append(f"tag @a[gamemode=adventure,{where}] add st.in")
    leavers = [d.index for d in layout.DOMES if (d.index, "leave") in hooks]
    lines += [
        f"tag @e[type=minecraft:armor_stand,tag={STANDIN}] add st.in",
        # a player back from an earlier run (offline when it was reset):
        # to the shore, with nothing, like everyone else
        f"execute as @a[tag=st.in,tag=st.kit] unless score @s st.kitrun = "
        f"#runid {OBJ} run function {pack.id('players/stale')}",
        # one who has gone out of the game from a dome has left that dome
        *(
            f"execute as @a[tag=!st.in,scores={{st.dome={n}}}] "
            f"run function {pack.id(f'dome/{n}/exited')}"
            for n in leavers
        ),
        "scoreboard players reset @a[tag=!st.in] st.dome",
        "scoreboard players reset @a[tag=!st.in] st.vote",
        _set("#players", 0),
        *(_set(f"#occ{d.index}", 0) for d in layout.DOMES),
        *(f"function {pack.id('players/locate')} {{who:'{who}'}}" for who in WHO),
    ]
    # those in the game are found twice over by the same lines: the
    # players, then the checks' stand-ins
    locate = [
        f"$execute store result score #n {OBJ} if entity $(who)]",
        f"scoreboard players operation #players {OBJ} += #n {OBJ}",
    ]
    # every dome's leavers before any dome's comers-in: a player who is
    # recalled is in the start dome at once, and must still leave the
    # dome they were in
    arriving = []
    sx, sy, sz = shore_spot()
    pack.function(
        "players/stale",
        [
            # what any dome lent is taken back: they may have been in it
            *(f"function {pack.id(f'dome/{n}/leave')}" for n in leavers),
            "clear @s",
            "tag @s remove st.kit",
            "scoreboard players reset @s st.dome",
            f"spawnpoint @s {sx} {sy} {sz}",
            f"execute in minecraft:overworld run tp @s {sx} {sy} {sz}",
        ],
    )
    for dome in layout.DOMES:
        n = dome.index
        here = domes.sphere(dome)
        occ, was, form = f"#occ{n} {OBJ}", f"#was{n} {OBJ}", f"#form{n} {OBJ}"
        grace, shown = f"#grace{n} {OBJ}", f"#shown{n} {OBJ}"
        gone = ["scoreboard players set @s st.dome -1"]
        if (n, "leave") in hooks:
            gone.append(f"function {pack.id(f'dome/{n}/leave')}")
        pack.function(f"dome/{n}/exited", gone)
        locate.append(
            f"$execute as $(who),scores={{st.dome={n}}}] unless entity @s[{here}] "
            f"run function {pack.id(f'dome/{n}/exited')}"
        )
        arriving += [
            f"$execute as $(who),{here}] unless score @s st.dome matches {n} "
            f"at @s run function {pack.id(f'dome/{n}/entered')}",
            f"$execute store result score #n {OBJ} "
            f"if entity $(who),scores={{st.dome={n}}}]",
            f"scoreboard players operation {occ} += #n {OBJ}",
        ]
        # the dome's form follows who is in it: two or more, duo at once;
        # one, solo, but only SOLO_AFTER scans after there were two
        lines += [
            f"execute if score {occ} matches 2.. run {_set(f'#form{n}', 2)}",
            f"execute if score {occ} matches 2.. run {_set(f'#grace{n}', 0)}",
            f"execute if score {occ} matches 1 if score {form} matches 2 "
            f"run scoreboard players add {grace} 1",
            f"execute if score {occ} matches 1 unless score {form} matches 2 "
            f"run {_set(f'#form{n}', 1)}",
            f"execute if score {grace} matches {SOLO_AFTER}.. "
            f"run {_set(f'#form{n}', 1)}",
            f"execute if score {form} matches 1 run {_set(f'#grace{n}', 0)}",
        ]
        forms = [h for h in ("solo", "duo") if (n, h) in hooks]
        if forms:
            lines.append(
                f"execute if score {occ} matches 1.. if score #d{n} {OBJ} matches 1 "
                f"unless score {shown} = {form} "
                f"run function {pack.id(f'dome/{n}/form')}"
            )
            pack.function(
                f"dome/{n}/form",
                [
                    f"scoreboard players operation {shown} = {form}",
                    *(
                        f"execute if score {form} matches {mode} "
                        f"run function {pack.id(f'dome/{n}/{h}')}"
                        for mode, h in ((1, "solo"), (2, "duo"))
                        if h in forms
                    ),
                ],
            )
        left = [
            _set(f"#{name}{n}", 0) for name in ("was", "form", "shown", "grace", "gone")
        ]
        left.append(automatons.remove_line(n))
        left += automatons.sweep_lines(dome)
        if (n, "empty") in hooks:
            left.append(f"function {pack.id(f'dome/{n}/empty')}")
        pack.function(f"dome/{n}/left", left)
        # a dome is empty EMPTY_AFTER scans after its last player went: a
        # step into the tunnel, or a connection lost for a moment, is not
        # leaving
        gone = f"#gone{n} {OBJ}"
        lines += [
            f"execute if score {occ} matches 1.. run {_set(f'#gone{n}', 0)}",
            f"execute if score {occ} matches 0 if score {was} matches 1 "
            f"run scoreboard players add {gone} 1",
            f"execute if score {gone} matches {EMPTY_AFTER}.. "
            f"run function {pack.id(f'dome/{n}/left')}",
            f"execute if score {occ} matches 1.. run {_set(f'#was{n}', 1)}",
        ]

        x, y, z, yaw = domes.entrance(dome)
        entered = [
            f"scoreboard players set @s st.dome {n}",
            f"function {pack.id('difficulty/apply')}",
            f"spawnpoint @s {x} {y} {z} {yaw} 0",
            "title @s times 10 40 10",
            f'title @s title {{text:"{dome.name}",color:"gold"}}',
            "playsound minecraft:block.note_block.chime master @s ~ ~ ~ 1 0.7",
            f"execute unless score @s st.kitrun = #runid {OBJ} "
            f"run function {pack.id('kit/start')}",
        ]
        # every kit of this dome and those before it: one who fast travels
        # past a kit's dome is given it on arrival
        entered += [
            f"execute unless score @s st.kit.{name} = #runid {OBJ} "
            f"run function {pack.id(f'kit/{name}')}"
            for k, name in sorted(KITS.items())
            if k <= n
        ]
        if (n, "enter") in hooks:
            # #first: this player is the first into an empty dome
            entered += [
                _set("#first", 1),
                f"execute if score {was} matches 1 run {_set('#first', 0)}",
                _set(f"#was{n}", 1),
                f"function {pack.id(f'dome/{n}/enter')}",
            ]
        pack.function(f"dome/{n}/entered", entered)
    lines.append(f"function {pack.id('vote/tally')}")
    # a death answered, the first tick the player is alive again (``@e``
    # does not find the dead)
    respawned = ["effect give @s minecraft:resistance 5 4 true"]
    for dome in layout.DOMES:
        n = dome.index
        after = automatons.respawn_lines(dome)
        if (n, "died") in hooks:
            after.append(f"function {pack.id(f'dome/{n}/died')}")
        pack.function(f"dome/{n}/respawned", after)
        respawned.append(
            f"execute if score @s st.dome matches {n} "
            f"run function {pack.id(f'dome/{n}/respawned')}"
        )
    respawned.append("scoreboard players set @s st.died 0")
    pack.function("fight/respawned", respawned)
    pack.function("players/locate", locate + arriving)
    pack.function("players/scan", lines)
    # a click on any recall post (``fittings.summon_recall``), answered here
    pack.function("recall/click", fittings.recall_lines(pack))


def _progress(
    pack: dp.Pack, hooks: set[tuple[int, str]], modules: list[Module]
) -> None:
    last = layout.DOMES[-1].index
    for dome in layout.DOMES:
        n = dome.index
        lines = [
            f"execute unless score #d{n} {OBJ} matches 1 run return 0",
            _set(f"#d{n}", 2),
        ]
        if n > 0:
            lines.append(f"scoreboard players add #solved {OBJ} 1")
        lines += [
            f"title {PLAYERS} times 10 60 20",
            f'title {PLAYERS} subtitle {{text:"restored",color:"aqua"}}',
            f'title {PLAYERS} title {{text:"{dome.name}",color:"gold"}}',
            f"execute as {PLAYERS} at @s run playsound "
            "minecraft:ui.toast.challenge_complete master @s ~ ~ ~ 1 1",
            f"function {pack.id(f'tunnel/{n}/ready')}",
        ]
        if n < last:
            x, y, z, yaw = domes.entrance(layout.DOMES[n + 1])
            lines += [
                f"execute if score #d{n + 1} {OBJ} matches 0 run {_set(f'#d{n + 1}', 1)}",
                f"spawnpoint {PLAYERS} {x} {y} {z} {yaw} 0",
            ]
        else:
            lines.append(f"function {pack.id('run/win')}")
        pack.function(f"dome/{n}/solved", lines)

    pack.function(
        "run/start",
        [
            f"execute unless score #run {OBJ} matches 0 run return 0",
            _set("#run", 1),
            _set("#secs", 0),
            _set("#second", 0),
            f"scoreboard players operation #run.level {OBJ} = #active {OBJ}",
            f"function {pack.id('dome/0/solved')}",
        ],
    )
    win = [_set("#run", 2), _set("#won.best", 0)]
    for level in LEVELS:
        best = f"#best{level} {OBJ}"
        at = f"execute if score #run.level {OBJ} matches {level}"
        new = f"run {_set('#won.best', 1)}"
        keep = f"run scoreboard players operation {best} = #secs {OBJ}"
        win += [
            f"{at} unless score {best} matches 1.. {new}",
            f"{at} if score #secs {OBJ} < {best} {new}",
            f"{at} if score #won.best {OBJ} matches 1 {keep}",
        ]
    win += [f"function {pack.id(path)}" for m in modules for path in m.wins]
    pack.function("run/win", win)


def _kit(pack: dp.Pack) -> None:
    armour = {
        "head": "iron_helmet",
        "chest": "iron_chestplate",
        "legs": "iron_leggings",
        "feet": "iron_boots",
    }
    pack.function(
        "kit/start",
        [
            "clear @s",
            *(
                f"item replace entity @s armor.{slot} with minecraft:{item}"
                for slot, item in armour.items()
            ),
            "give @s minecraft:iron_sword",
            "give @s minecraft:bow",
            "give @s minecraft:arrow 64",
            "give @s minecraft:cooked_beef 8",
            "tag @s add st.kit",
            f"scoreboard players operation @s st.kitrun = #runid {OBJ}",
        ],
    )
    # the later kits add to the start kit: given on entering their dome
    brass = "minecraft:unbreakable={}"
    extras = {
        "foundry": [
            "item replace entity @s weapon.offhand with minecraft:shield",
            "give @s minecraft:spectral_arrow 32",
        ],
        "boss": [
            "item replace entity @s armor.head with minecraft:golden_helmet"
            f'[minecraft:custom_name="Brass Helm",{brass},'
            'minecraft:enchantments={"minecraft:protection":4}]',
            "item replace entity @s armor.chest with minecraft:golden_chestplate"
            f'[minecraft:custom_name="Brass Cuirass",{brass},'
            'minecraft:enchantments={"minecraft:protection":4}]',
            "give @s minecraft:golden_sword"
            f'[minecraft:custom_name="Brass Sabre",{brass},'
            'minecraft:enchantments={"minecraft:sharpness":4}]',
        ],
    }
    for name in KITS.values():
        pack.function(
            f"kit/{name}",
            [
                *extras[name],
                f"scoreboard players operation @s st.kit.{name} = #runid {OBJ}",
            ],
        )
    kitted = "execute as @a[tag=st.in,tag=st.kit] unless items entity @s container.*"
    pack.function(
        "kit/top_up",
        [
            f"{kitted} minecraft:cooked_beef run give @s minecraft:cooked_beef 8",
            f"{kitted} #minecraft:arrows run give @s minecraft:arrow 32",
        ],
    )


def _vote(pack: dp.Pack) -> None:
    kind, value, left = f"#vote.kind {OBJ}", f"#vote.value {OBJ}", f"#vote.left {OBJ}"
    yes, need = f"#vote.yes {OBJ}", f"#vote.need {OBJ}"
    in_game = "execute unless entity @s[tag=st.in] run return 0"
    open_ = pack.id("vote/open")
    confirm = f"run function {pack.id('vote/yes')}"
    # ``#vote.new`` is 1 only during the press that opens a vote
    pack.function(
        "vote/reset",
        [
            in_game,
            f"execute if score {kind} matches 0 "
            f'run function {open_} {{kind:1,value:0,label:"Reset"}}',
            f"execute if score {kind} matches 1 {confirm}",
            _set("#vote.new", 0),
        ],
    )
    pack.function(
        "vote/difficulty",
        [
            in_game,
            f"$scoreboard players set #vote.arg {OBJ} $(level)",
            f"execute unless score #vote.arg {OBJ} matches "
            f"{LEVELS[0]}..{LEVELS[-1]} run return 0",
            f"$execute if score {kind} matches 0 run function {open_} "
            '{kind:2,value:$(level),label:"Difficulty $(level)"}',
            f"execute if score {kind} matches 2 if score {value} = #vote.arg {OBJ} "
            f"{confirm}",
            _set("#vote.new", 0),
        ],
    )
    pack.function(
        "vote/confirm", [in_game, f"execute if score {kind} matches 1.. {confirm}"]
    )
    pack.function(
        "vote/open",
        [
            f"$scoreboard players set {kind} $(kind)",
            f"$scoreboard players set {value} $(value)",
            f'$data modify storage {STORE} vote.label set value "$(label)"',
            f"scoreboard players set {left} {VOTE_SECONDS}",
            _set("#vote.new", 1),
            "scoreboard players reset * st.vote",
            f"bossbar set {BAR} value {VOTE_SECONDS}",
            f"bossbar set {BAR} players {PLAYERS}",
            f"bossbar set {BAR} visible true",
        ],
    )
    pack.function(
        "vote/yes",
        ["scoreboard players set @s st.vote 1", f"function {pack.id('vote/tally')}"],
    )
    store = f"execute store result storage {STORE} vote"
    pack.function(
        "vote/tally",
        [
            f"execute unless score {kind} matches 1.. run return 0",
            _set("#vote.need", 0),
            _set("#vote.yes", 0),
            *(f"function {pack.id('vote/count')} {{who:'{who}'}}" for who in WHO),
            # a player alone: the press that opened it is not a yes
            f"execute if score #vote.new {OBJ} matches 1 if score {need} matches 1 "
            f"run return run function {pack.id('vote/alone')}",
            f"function {pack.id('vote/show')}",
            f"execute if score {need} matches 1.. if score {yes} >= {need} "
            f"run function {pack.id('vote/pass')}",
        ],
    )
    pack.function(
        "vote/alone",
        [
            "scoreboard players set @s st.vote 2",  # pressed once, not counted
            _set("#vote.yes", 0),
            f"function {pack.id('vote/show')}",
            "tellraw @s "
            + _text('{text:"Press again within the minute to confirm.",color:"gold"}'),
        ],
    )
    pack.function(
        "vote/count",
        [
            f"$execute store result score #n {OBJ} if entity $(who)]",
            f"scoreboard players operation {need} += #n {OBJ}",
            f"$execute store result score #n {OBJ} "
            "if entity $(who),scores={st.vote=1}]",
            f"scoreboard players operation {yes} += #n {OBJ}",
        ],
    )
    pack.function(
        "vote/show",
        [
            f"{store}.yes int 1 run scoreboard players get {yes}",
            f"{store}.need int 1 run scoreboard players get {need}",
            f"{store}.left int 1 run scoreboard players get {left}",
            f"execute if score {need} matches 1 run return run "
            f"function {pack.id('vote/show_alone')} with storage {STORE} vote",
            f"function {pack.id('vote/show_all')} with storage {STORE} vote",
        ],
    )
    pack.function(
        "vote/show_alone",
        [
            f"$bossbar set {BAR} name "
            '{text:"$(label): press again to confirm, $(left) s",color:"gold"}'
        ],
    )
    pack.function(
        "vote/show_all",
        [
            f"$bossbar set {BAR} name "
            '{text:"$(label): $(yes) of $(need), $(left) s",color:"gold"}'
        ],
    )
    pack.function(
        "vote/second",
        [
            f"scoreboard players remove {left} 1",
            f"execute store result bossbar {BAR} value "
            f"run scoreboard players get {left}",
            f"bossbar set {BAR} players {PLAYERS}",
            f"function {pack.id('vote/show')}",
            f"execute if score {left} matches ..0 run function {pack.id('vote/expire')}",
        ],
    )
    pack.function(
        "vote/expire",
        [
            f'tellraw {PLAYERS} {{text:"The vote ran out.",color:"gray"}}',
            f"function {pack.id('vote/close')}",
        ],
    )
    pack.function(
        "vote/close",
        [
            _set("#vote.kind", 0),
            _set("#vote.left", 0),
            "scoreboard players reset * st.vote",
            f"bossbar set {BAR} visible false",
            f"bossbar set {BAR} players",
        ],
    )
    pack.function(
        "vote/pass",
        [
            f"scoreboard players operation #vote.was {OBJ} = {kind}",
            f"function {pack.id('vote/close')}",
            f"execute if score #vote.was {OBJ} matches 2 "
            f"run scoreboard players operation #level {OBJ} = {value}",
            f"execute if score #vote.was {OBJ} matches 2 run tellraw {PLAYERS} "
            + _text(
                '{text:"Difficulty ",color:"gold"}',
                _score("#level"),
                '{text:", from the next dome you enter."}',
            ),
            f"execute if score #vote.was {OBJ} matches 1 "
            f"run function {pack.id('reset/all')}",
        ],
    )


def _difficulty(pack: dp.Pack) -> None:
    lines = [
        f"execute unless score #level {OBJ} matches {LEVELS[0]}..{LEVELS[-1]} "
        f"run {_set('#level', DEFAULT_LEVEL)}",
        f"scoreboard players operation #active {OBJ} = #level {OBJ}",
        f"execute if score #run {OBJ} matches 1 if score #active {OBJ} < "
        f"#run.level {OBJ} run scoreboard players operation #run.level {OBJ} "
        f"= #active {OBJ}",
    ]
    for name, (base, step) in SCALED.items():
        lines += [
            _set("#diff.step", step),
            f"scoreboard players operation {name} {OBJ} = #active {OBJ}",
            f"scoreboard players operation {name} {OBJ} *= #diff.step {OBJ}",
            f"scoreboard players add {name} {OBJ} {base}",
        ]
    pack.function("difficulty/apply", lines)


def _reset(pack: dp.Pack, modules: list[Module], hooks: set[tuple[int, str]]) -> None:
    # the tunnels first (their doors shut and their water back before a
    # dome's reset moves anything), then the domes, then the modules' own.
    # Nothing here kills by position: entities go by their tags
    lines = [f"function {pack.id(f'tunnel/{t.index}/reset')}" for t in layout.TUNNELS]
    lines += [
        f"function {pack.id(f'dome/{n}/reset')}"
        for n, h in sorted(hooks)
        if h == "reset"
    ]
    for module in modules:
        for path in module.resets:
            lines.append(f"function {pack.id(path)}")
    lines += [
        f"function {pack.id(f'dome/{d.index}/bar/hide')}"
        for d in layout.DOMES
        if f"dome/{d.index}/bar/hide" in pack.functions
    ]
    lines.append(f"function {pack.id('vote/close')}")
    lines += [_set(name, 0) for name in ("#run", "#secs", "#solved", "#second")]
    for dome in layout.DOMES:
        n = dome.index
        lines += [
            _set(f"#d{n}", 1 if n == 0 else 0),
            *(
                _set(f"#{name}{n}", 0)
                for name in ("was", "form", "shown", "grace", "gone")
            ),
        ]
    x, y, z = shore_spot()
    lines += [
        automatons.remove_line(),
        "scoreboard players reset * st.died",
        "clear @a[tag=st.kit]",
        "tag @a[tag=st.kit] remove st.kit",
        f"scoreboard players add #runid {OBJ} 1",
        # what a dome lent is taken back from those in it
        *(
            f"execute as @a[scores={{st.dome={n}}}] "
            f"run function {pack.id(f'dome/{n}/leave')}"
            for n, h in sorted(hooks)
            if h == "leave"
        ),
        "scoreboard players reset * st.dome",
        f"spawnpoint {PLAYERS} {x} {y} {z}",
        f"execute in minecraft:overworld run tp {PLAYERS} {x} {y} {z}",
    ]
    pack.function("reset/all", lines)
    x, y, z, yaw = domes.entrance(layout.DOMES[0])
    pack.function(
        "recall",
        [
            "execute if entity @s[tag=st.in] in minecraft:overworld "
            f"run tp @s {x} {y} {z} {yaw} 0"
        ],
    )


def _clock(pack: dp.Pack, hooks: set[tuple[int, str]]) -> None:
    load = [
        f'bossbar add {BAR} ""',
        f"bossbar set {BAR} max {VOTE_SECONDS}",
        f"bossbar set {BAR} color yellow",
        f"bossbar set {BAR} style notched_6",
        f"execute unless score #vote.kind {OBJ} matches 1.. "
        f"run bossbar set {BAR} visible false",
    ]
    # a score that was never set matches nothing: give each its zero
    zeroed = ["#run", "#secs", "#solved", "#vote.kind", "#runid", "#players", "#best"]
    zeroed += [f"#d{d.index}" for d in layout.DOMES]
    zeroed += [f"#t{t.index}" for t in layout.TUNNELS]
    zeroed += [f"#best{level}" for level in LEVELS]
    load += [f"scoreboard players add {name} {OBJ} 0" for name in zeroed]
    load += [
        f"execute if score #d0 {OBJ} matches 0 run {_set('#d0', 1)}",
        f"execute unless score #active {OBJ} matches 1.. "
        f"run function {pack.id('difficulty/apply')}",
    ]
    pack.function("game/load", load, load=True)

    line = (
        '{text:"Domes "}',
        _score("#solved"),
        f'{{text:" of {len(layout.DOMES) - 1}, "}}',
        _score("#mm.m"),
        '{text:":"}',
        _score("#mm.t"),
        _score("#mm.o"),
    )
    ready = '{text:"   Pump ready: pull the lever",color:"aqua"}'
    second = [
        _set("#second", 0),
        f"execute if score #run {OBJ} matches 1 run scoreboard players add #secs {OBJ} 1",
        *dp.mmss_lines("#secs", OBJ, STORE, "time"),
        f"execute if score #run {OBJ} matches 1.. unless score #pumps {OBJ} "
        f"matches 1.. run title {PLAYERS} actionbar " + _text(*line),
        f"execute if score #run {OBJ} matches 1.. if score #pumps {OBJ} "
        f"matches 1.. run title {PLAYERS} actionbar " + _text(*line, ready),
    ]
    second += [
        f"execute if score #active {OBJ} matches {level} "
        f"run scoreboard players operation #best {OBJ} = #best{level} {OBJ}"
        for level in LEVELS
    ]
    second += [
        *dp.mmss_lines("#best", OBJ, STORE, "best"),
        f"execute if score #vote.kind {OBJ} matches 1.. "
        f"run function {pack.id('vote/second')}",
        f"function {pack.id('kit/top_up')}",
    ]
    second += [
        f"execute if score #bar{d.index} {OBJ} matches 1 run bossbar set "
        f"{automatons.bar_id(d.index)} players {in_dome(d.index)}"
        for d in layout.DOMES
        if f"dome/{d.index}/bar/show" in pack.functions
    ]
    pack.function("game/second", second)

    tick = [
        f"function {pack.id('tunnel/tick')}",
        f"scoreboard players add #scan {OBJ} 1",
        f"execute if score #scan {OBJ} matches {SCAN_TICKS}.. "
        f"run function {pack.id('players/scan')}",
        f"scoreboard players add #second {OBJ} 1",
        f"execute if score #second {OBJ} matches 20.. "
        f"run function {pack.id('game/second')}",
    ]
    tick.append(fittings.click_line(fittings.RECALL_TAG, pack.id("recall/click")))
    tick.append(
        "execute as @e[tag=st.in,scores={st.died=1..}] "
        f"run function {pack.id('fight/respawned')}"
    )
    tick += [
        f"execute if score #occ{n} {OBJ} matches 1.. "
        f"run function {pack.id(f'dome/{n}/tick')}"
        for n, h in sorted(hooks)
        if h == "tick"
    ]
    pack.function("game/tick", tick, tick=True)
