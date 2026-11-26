# The Drowned Station

An adventure game built with mciwb: a ring of glass domes on the floor of
an ocean, each with a puzzle or a battle, joined by glass tunnels that pump
dry as the players restore the station. For one or two players (more may
come along), about an hour a run. The design and the order of work are in
[PLAN.md](PLAN.md), and how far it has got in [PROGRESS.md](PROGRESS.md).

It is a self-contained example: nothing here imports another example. The
blocks and the redstone are placed over RCON by mciwb; the game's logic is
a datapack of functions that the build generates and installs.

So far the plan's stage 1 is here, the playable slice: the shore and its
boats, the dock, the lift, the Pump House (the start dome), the Boiler
Room (the first puzzle), and the structure of the whole ring: all eight
domes' shells and all eight tunnels that pump dry (domes 2 to 7 are empty
shells so far), over the game core (who is playing, progress, the
clock, kit and respawn, the vote, difficulty, reset). The owner has played
it once; PROGRESS.md says what that asked for and what is still to do.

```
python verify_station.py                         # the offline checks, no server
python build_station.py                          # the whole build against a fake client
mciwb run build_station.py                       # build into the world
STAGES=site,datapack mciwb run build_station.py  # just some stages
mciwb run verify_station.py                      # offline checks, then the live ones
CHECKS=layout,names python verify_station.py     # some checks only
```

Pass `--server` and `--port` for a server that is not the `mciwb start`
one, and the password in `$MCIWB_PASSWORD` (or `--password-file`).

## The files

| File | What |
| --- | --- |
| `station_layout.py` | where everything is: the shore, the dock, the lift, the domes, the tunnels, the station's box. Plain data, and its own check |
| `datapack.py` | the datapack generator: a pack built in memory, written to a folder, installed in a world |
| `domes.py` | a dome's cells, the build of its shell, its mouths and entrance, and the check that it is dry and whole |
| `tunnels.py` | a tunnel's cells, its build, its drain, refill and pump event as functions, and its check |
| `game.py` | the game core's functions, and `Module`: how a part of the station adds its stages, functions and checks |
| `fittings.py` | what every dome has: a frame to place things by, input posts and readers, gauges, displays, hints, machinery that runs by itself, signs and plaques, a lectern and its book, the recall post, lent and restricted items |
| `automatons.py` | the mobs of the fights, made to the plan's rules: the three kinds, waves, leash and fence, a dome's bossbar, the difficulty |
| `rooms.py` | offline checks of a room's plan: placement, walks, sight lines, inputs on gold, blocks with a meaning |
| `shore.py`, `dome_start.py`, `dome_boiler.py` | the modules: the way in (shore, boats, dock, lift), the Pump House, the Boiler Room |
| `game_checks.py` | the live checks of the game core, with stand-ins for players |
| `build_station.py` | the build, stage by stage |
| `verify_station.py` | the checks: offline ones, and live ones over RCON |
| `fake_client.py` | a fake RCON client and a simulated box of blocks, for building with no server |
| `survey_site.py`, `render_layout.py`, `rig_mechanisms.py` | the tools of stage 0: the survey of the ocean, the plan drawn, each mechanism proved in a rig |

## Building

`build_station.py` runs its stages in order (`STAGES` in the script), or
those named in `STAGES=a,b`. A stage is a function of a context: the
world, the layout and the datapack under construction.

| Stage | What |
| --- | --- |
| `site` | the station's box is where the layout says, and loaded |
| `datapack` | the datapack installed in the world's `datapacks` folder and reloaded |
| `rules` | the game rules of the plan; the mineshaft's two spawners removed |
| `shore`, `dock` | the landing, its jetty and boats; the dock offshore |
| `start_dome`, `dome_1` ... `dome_7` | each dome's empty, lit shell on its foundation, its mouths plugged with windowed brass doors |
| `lift` | the lift from the dock down into the start dome (after that dome's shell, which would wipe its shaft) |
| `start_dome_inside`, `dome_1_inside` | the Pump House; the Boiler Room |
| `dome_3_inside` | the Flooded Dome (after `datapack`: it ends with the pack's `dome/3/reset`) |
| `dome_4_inside` | the Foundry |
| `dome_5_inside` | the Signal Room |
| `dome_7_inside` | the Engine (phase 1; phase 2, the Master, behind `PHASE_2` in `dome_boss.py`, off) |
| `dome_6_inside` | the Clockwork Maze (after `datapack`: it ends with the pack's `dome/6/reset`; lifts on, behind `LIFTS` in `dome_maze.py`) |
| `dome_2_inside` | the Gearworks (after `datapack`: it ends with the pack's `dome/2/reset`) |
| `tunnel_0` ... `tunnel_7` | each tunnel, flooded and shut, with its pump engine; the two that slope have stairs. `STAGES=tunnels` is short for all eight |

A stage that is not written says so and does nothing: the list is the
order of work. A shell stage wipes what is inside its dome (the pump
engine and the lift's shaft too) and shuts its doors: run `lift` (for
the start dome), the dome's `_inside` stage and its outgoing tunnel's stage after it, as
the whole build does. Every stage gives the same result run twice.

- The build **refuses to run while a player is online**, unless `FORCE=1`.
  With nobody online the server does not tick, so the build sprints the
  ticks it needs (`tick sprint`), which would wreck a player's game; with
  `FORCE=1` and a player online it waits for the game's own ticks instead.
- The station's box (the dock, the domes and the tunnels) is
  **forceloaded by the build, for good** (in commands of at most 256
  chunks, the server's limit): the game's functions change blocks all
  over it, and a function's block change fails in a chunk that is not
  loaded. It is the one area the game keeps loaded.
- The **datapack** is made in full from the layout whichever stages run,
  and the `datapack` stage writes it to the folder that
  `STATION_DATAPACKS_DIR` names: the world's `datapacks` folder, which the
  build must be able to write. It then sends `reload` and checks that this
  build of the pack loaded. Without the variable the pack is generated but
  not installed, and the stage says so.
- A command longer than 1446 bytes is refused before it is sent: RCON
  drops the connection on one.

`python build_station.py OUT` runs the same build with no server and
writes `OUT.commands` (every command, in order) and `OUT.blocks` (the
final block of every cell the build set). Record a build before and after
a change and `diff` the two to see exactly what the change does. The fake
world has no sea and no sea bed (a cell nothing has set is air), so this
shows the build's logic, not how it meets the terrain.

## Adding a part: modules

The way in and the inside of each dome are modules: a file `shore.py` or
`dome_<key>.py` (`dome_start.py`, `dome_boiler.py` ...) that defines
`MODULE = game.Module(...)`. The build finds the file; nothing else is
edited.

```python
import game


def build(ctx):  # a build stage
    ctx.fill((x1, y1, z1), (x2, y2, z2), "minecraft:waxed_copper_block")
    return "what was built"


def functions(pack):  # the module's datapack functions
    pack.function("dome/1/enter", ["say someone came in"])
    pack.function("dome/1/reset", ["..."])
    pack.function("dome/1/valve", [..., "function station:dome/1/solved"])


def check(ctx):  # a live check: the problems found
    ctx.function("dome/1/valve")
    return [] if ctx.score("#d1") == 2 else ["not solved"]


MODULE = game.Module(
    "boiler",
    stages={"dome_1_inside": build},
    functions=functions,
    checks={"boiler_room": check},
)
```

- A stage's name must be one of the placeholders. It gets the build's
  context: `ctx.fill`, `ctx.fill_cells`, `ctx.fill_boxes`, `ctx.setblock`,
  `ctx.cmd`, `ctx.function`, `ctx.advance(ticks)`, and for checks
  `ctx.score`, `ctx.set_score`, `ctx.is_block`, `ctx.test`, `ctx.count`,
  `ctx.data`. Positions come from `station_layout`, `domes` and
  `tunnels`, never from numbers in the module.
- What the core calls and what a module may call are in `game.py`'s
  docstring; where a dome's floor, mouths, entrance and reserved cells
  are, and the rules for dressing a dome, in `domes.py`'s; the tunnels'
  functions in `tunnels.py`'s; the shared fittings in `fittings.py`'s.
- **The builders' contract**: what a dome's module gets from the core,
  and what it must not do for itself.
  - *Until it exists*, its dome is a stub: a BYPASS lever by the exit
    that solves the dome, so the ring always plays end to end. The
    module's file replaces the stub; its build stage runs
    `game.clear_stub_commands(dome)`.
  - *Two rules*: leaving a dome never costs more than the stage in
    progress; a change of form never shuts, removes or restarts
    something a player is using (it waits for the room's next safe
    point).
  - *Progress*: call `station:dome/<n>/solved` and the core does the
    rest (the title, tunnel n's pump event, the next dome opened, respawn
    points). The last dome's is the win, and functions named in
    `Module(wins=...)` run then (`#won.best`: the run set the level's
    best time).
  - *Hooks* (define the function, the core calls it): `enter` (with
    `#first`: first into an empty dome), `leave` (as each player who goes
    out, by any way), `tick`, `solo` and `duo` (by `#form<n>`: who is in
    this dome), `died` (as a player alive again after dying: the room's
    penalty), `empty` (3 s after the last player went), `reset`.
  - *The level*: `#diff.count`, `.health`, `.damage`, `.timer`, `.seq`,
    percentages; copy what you need when the room is set up.
  - *Kits* are the core's alone: a shield and spectral arrows on entering
    dome 4, brass armour and a sabre on entering dome 7. A dome lends
    with `fittings.lend_line` and takes back with `take_back_line` in
    `leave` and `reset`.
  - *Fights* (`automatons.py`): the three kinds `STOKER`, `RIVETER`,
    `SLAG_HUSK` (`summon_kind`, `dress_kind_line`); `waves(pack, n,
    points, ...)` for casting them at spawn points where a player is, up
    to a cap and a kind's cap, with a leash; `fence_lines`;
    `station:mob/count`; `bar(pack, n, title)` for a bossbar shown to the
    dome's players; `sweep_lines`; `#difficulty` (0 is Peaceful: do not
    start a fight). The core removes a dome's automatons when it empties,
    clears them from round the entrance when a player respawns, and gives
    that player 5 s of Resistance.
  - *Fittings* (`fittings.py`): `frame`; `input_post` (an input on brass
    with its sign and label); `lever`, `lever_put_lines`,
    `lever_hold_line`, `button_line`, `plate_held`, `interaction` and
    `click_line` (who pressed); `gauge_lines`; `display`, `text_line`,
    `turn_line`; `hint`; `torch_clock` (machinery that runs by itself: a
    clock, a lamp chase, two plain pistons); signs, `plaque_blocks`,
    `lectern_with_book`; the recall post (place it; the core answers the
    click); `restricted` and `lent` items.
  - *Offline checks of a room's plan* (`rooms.py`): `room_problems`,
    `walk_problems`, `sight_problems`, `window_problems`,
    `input_problems`; `rooms.mean(block, n)` for a block that means
    something in one dome only.
  - *Exceptions, said by name when the module is imported*:
    `domes.add_opening` (a hole cut in a shell), `domes.add_wet` (water
    held on purpose), `domes.allow` (a rule for dressing broken on
    purpose).
  - *Live checks* (`game_checks`): `stand_at`/`stand_in` (stand-ins for
    players; `gravity=True` to press a plate), `as_stand_in`, `scores`,
    `expect`, `SCAN` and `EMPTY` (ticks to wait for a scan, and for a
    dome to count as empty). A module's check resets its own dome, not
    the game. **Required**: its first line is `game_checks.no_run(ctx)`,
    which refuses (unless `FORCE=1`) while a run is in progress: a run
    parked by players who logged off would be wiped. A check that changes
    the level saves and puts back `#run.level` as well as `#level`
    (`game_checks.save_level`, `restore_level`): during a run
    `difficulty/apply` lowers `#run.level`, and the best time is kept
    under it. The core's checks build what they try out in a glass cell
    of their own in the sea in the middle of the ring
    (`fittings.check_cell`), never in a dome.
- One stage: `STAGES=site,dome_1_inside mciwb run build_station.py`
  (with `datapack` too, and `STATION_DATAPACKS_DIR`, if the functions
  changed). One check: `CHECKS=boiler_room mciwb run verify_station.py`.

## Checking

`verify_station.py` has two kinds of check.

**Offline checks** need no server, and the unit test
(`tests/test_station_example.py`) runs them all:

| Check | What |
| --- | --- |
| `layout` | the layout's own check |
| `stages` | the build has a stage for every dome of the layout, in ring order |
| `forceload` | the station's box splits into forceload commands of at most 256 chunks, which cover it |
| `geometry` | every dome's and tunnel's cells (built yet or not, the sloping tunnels too): no inside cell has a face on the sea, the mouths are in the shells, the reserved cells are inside |
| `datapack` | the datapack's own checks of every function line and name |
| `functions` | `pack.mcmeta` and the tags read as JSON; every function a tag or a line names exists |
| `build` | the whole build runs against the fake client, the datapack is installed and seen to load, no command is too long for RCON or outside the loaded box, and the station's box is left forceloaded |
| `names` | every block and item named by the pack's functions and the build's commands is one that mcwb's `Item` knows, for the Minecraft release `Item` was made from |

**Live checks** work each mechanism in place over RCON. They refuse to
run with a player online or with a run in progress (`FORCE=1` overrides),
since the core's checks reset the game before and after.

| Check | What |
| --- | --- |
| `forceloaded` | the station's box is forceloaded (expected), and what else is |
| `rules` | the game rules, the difficulty Easy, the spawners gone |
| `shell_0` ... `shell_7` | a dome: nothing inside or in its mouths wet (but where a module has registered water that is meant), no hole in shell or floor, ground under the floor, the sea above; while it is empty, the light at head height and no stray entities |
| `tunnel_0` ... `tunnel_7` | a tunnel reset, opened, read at every state as its water falls layer by layer and its lamps come on, open and dry with both domes dry, reset and flooded again (`CHECKS=tunnels`: all eight) |
| `player_count` | the count, which dome a player is in, and each dome's own solo or duo form by who is in it, with the fall back to solo |
| `vote` | both kinds of vote: proposed, counted, shown, running out, passing |
| `difficulty` | the level taking force on entering a dome, the scaled values, the level kept through a reset |
| `progress` | the run started, the clock, a dome solved, the win, the best time |
| `reset` | the reset from a run with tunnels open and draining and a vote open |
| `automatons` | an automaton summoned and dressed as the plan wants it, scaled by the level; nothing dropped; the count by the dome's form; gone when the dome empties |
| `restricted_items` | the items `fittings.restricted` writes are taken by the game and keep their rules |
| `fights` | the difficulty read; waves cast where a player is, to the cap, refilled; leash and fence; a death answered; the sweep; a dome's bossbar |
| `fittings` | the torch clock, its lamp chase and pistons seen running; a gauge; a lever put back and held; a button read once; a plate that wants a player; a display; a lent item; a hint |
| `ring` | the whole ring's progress walked by a stand-in from the master lever to the win, each stub's BYPASS lever thrown, and the reset |
| `shore`, `dock`, `lift`, `start_dome`, `boiler_room`, `gearworks`, `flooded_dome`, `foundry`, `signal_room`, `clockwork_maze`, `boss` | the modules' own checks (see each module) |

The checks of the parts not built yet are listed as `TODO`, and a TODO is
not a pass. Players are stood in for by armour stands
(`game_checks.py` says what that proves and what it does not).

What RCON cannot stand in for (an item in a real hand, a jump, whether a
fight is fair, sounds and titles) is listed in PROGRESS.md for a person to
try.
