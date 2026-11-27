# The Drowned Station

An adventure game built with mciwb: a ring of glass domes on the floor of
an ocean, each with a puzzle or a battle, joined by glass tunnels that pump
dry as the players restore the station. For one or two players (more may
come along), about an hour a run. The design and the order of work are in
[PLAN.md](PLAN.md), and how far it has got in [PROGRESS.md](PROGRESS.md).

It is a self-contained example: nothing here imports another example. The
blocks and the redstone are placed over RCON by mciwb; the game's logic is
a datapack of functions that the build generates and installs.

Where it stands: the ring has ten domes, and all ten are built and
checked live (the shore and its boats, the dock, the lift, the Pump
House, the Boiler Room, the Gearworks, the Cargo Hold, the Flooded Dome,
the Foundry, Hull Breach, the Signal Room, the Clockwork Maze and the
Engine) over the game core (who is playing, progress, the clock, kit and
respawn, the vote, difficulty, reset); the two of round 3, the Cargo
Hold and Hull Breach, stand where the Flooded Dome and the Foundry
stood, which moved a column east. All
ten tunnels pump dry. The Engine's second phase, the Master, is on
(`PHASE_2` in `dome_boss.py`). Play-testing continues; PROGRESS.md says
what it has found and what is still to do.

## The world

The station is laid out for one world, not any world: `ANCHOR` (63,
-109), `SPAWN` (-32, 63, 81) and the mineshaft's spawners in
`station_layout.py` were surveyed in a **Minecraft Java 26.3** world with
the seed **4578111213919200824** (normal terrain). Make a world from that
seed on a 26.3 server; the build and the datapack need 26.3.

- **The build overwrites the box (16, 21, -240) to (383, 72, -65)**,
  whatever is in it, and keeps it forceloaded for good.
- **The `rules` stage sets world-wide game rules**: keep inventory on, mob
  griefing off, monster spawning off, fire spread off and block drops off
  (`RULES` in `build_station.py`); the live checks expect the difficulty
  Easy. Use the world for this game only.

To put the station somewhere else, see
[Putting the station somewhere else](#putting-the-station-somewhere-else)
below.

```
python verify_station.py                         # the offline checks, no server
python build_station.py                          # the whole build against a fake client
STATION_DATAPACKS_DIR=~/mciwb-server/world/datapacks \
  mciwb run build_station.py                     # build into the world, with its datapack
STAGES=site,datapack mciwb run build_station.py  # just some stages
mciwb run verify_station.py                      # offline checks, then the live ones
CHECKS=layout,names python verify_station.py     # some checks only
```

`STATION_DATAPACKS_DIR` is the world's `datapacks` folder
(`~/mciwb-server/world/datapacks` for an `mciwb start` server). Without
it the build carries on but installs no datapack, so the station has no
game logic. Pass `--server` and `--port` for a server that is not the
`mciwb start` one, and the password in `$MCIWB_PASSWORD` (or
`--password-file`).

## The files

| File | What |
| --- | --- |
| `station_layout.py` | where everything is: the shore, the dock, the lift, the domes, the tunnels, the station's box. Plain data, and its own check |
| `datapack.py` | the datapack generator: a pack built in memory, written to a folder, installed in a world |
| `domes.py` | a dome's cells, the build of its shell, its mouths and entrance, and the check that it is dry and whole |
| `tunnels.py` | a tunnel's cells, its build, its drain, refill and pump event as functions, and its check |
| `seabed.py`, `render_seabed.py` | the sea floor round the station dressed (lights, coral, seagrass, the water's biome): its plan, stages and checks, and the plan drawn (`seabed_plan.png`) |
| `game.py` | the game core's functions, and `Module`: how a part of the station adds its stages, functions and checks |
| `fittings.py` | what every dome has: a frame to place things by, input posts and readers, gauges, displays, hints, machinery that runs by itself, signs and plaques, a lectern and its book, the recall post, lent and restricted items |
| `automatons.py` | the mobs of the fights, made to the plan's rules: the three kinds, waves, leash and fence, a dome's bossbar, the difficulty |
| `rooms.py` | offline checks of a room's plan: placement, walks, sight lines, inputs on gold, blocks with a meaning |
| `shore.py`, `dome_start.py`, `dome_boiler.py`, `dome_gearworks.py`, `dome_flooded.py`, `dome_foundry.py`, `dome_signal.py`, `dome_maze.py`, `dome_boss.py` | the modules: the way in (shore, boats, dock, lift), then the domes in ring order: the Pump House, the Boiler Room, the Gearworks, (the Cargo Hold), the Flooded Dome, the Foundry, (Hull Breach), the Signal Room, the Clockwork Maze, the Engine |
| `game_checks.py` | the live checks of the game core, with stand-ins for players |
| `build_station.py` | the build, stage by stage |
| `resite.py` | what the build takes away when the ring changes under a station already built (the ring of eight before round 3), and the rollback to it |
| `verify_station.py` | the checks: offline ones, and live ones over RCON |
| `fake_client.py` | a fake RCON client and a simulated box of blocks, for building with no server |
| `survey_site.py`, `render_layout.py`, `rig_mechanisms.py` | the tools of stage 0: the survey of the ocean, the plan drawn, each mechanism proved in a rig |
| `rig_domes.py` | the rig's second round: the mechanics the later domes rest on, each worked on a live server away from the station, and the hand test bench |
| `render_start.py` | the Pump House drawn from its plan, with no server |

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
| `resite` | the sea put back where the previous ring (of eight) had a tunnel that this one has not: see `resite.py` |
| `start_dome`, `dome_1` ... `dome_9` | each dome's empty, lit shell on its foundation, its mouths plugged with windowed brass doors |
| `lift` | the lift from the dock down into the start dome (after that dome's shell, which would wipe its shaft) |
| `start_dome_inside`, `dome_1_inside` | the Pump House; the Boiler Room |
| `dome_2_inside` | the Gearworks (after `datapack`: it ends with the pack's `dome/2/reset`) |
| `dome_3_inside` | the Cargo Hold (after `datapack`; `dome_cargo.py`) |
| `dome_6_inside` | Hull Breach (after `datapack`; `dome_hullbreach.py`) |
| `dome_4_inside` | the Flooded Dome (after `datapack`: it ends with the pack's `dome/4/reset`) |
| `dome_5_inside` | the Foundry |
| `dome_7_inside` | the Signal Room |
| `dome_8_inside` | the Clockwork Maze (after `datapack`: it ends with the pack's `dome/8/reset`; the gate plan and the lifts are in `dome_maze.py`) |
| `dome_9_inside` | the Engine (phase 1, and phase 2, the Master, behind `PHASE_2` in `dome_boss.py`: on) |
| `tunnel_0` ... `tunnel_9` | each tunnel, flooded and shut, with its pump engine; the two that slope have stairs. `STAGES=tunnels` is short for all ten |
| `seabed` | last: the sea floor round the station dressed from the survey, with sea lanterns, reefs of coral, sea pickles and seagrass (what an earlier run placed taken away first; `seabed.py`) |
| `seabed_water` | the station's box set to the warm-ocean biome from the sea floor up: lighter, turquoise water and tropical fish (a player online may need to rejoin to see it) |

A dome's number is its place in the ring (`station_layout.index_of(key)`),
which changes when the ring does: round 3 moved the Flooded Dome from 3 to
4, the Foundry from 4 to 5, the Signal Room from 5 to 7, the Maze from 6 to
8 and the Engine from 7 to 9. One more stage, `rollback`, runs only when
`STAGES` names it: it takes away what the ring of ten has and the ring of
eight had not, before a rebuild of the eight (PROGRESS.md, "Re-site
runbook").

A stage not written yet would say so and do nothing; every stage is
written now. A shell stage wipes what is inside its dome (the pump
engine and the lift's shaft too) and shuts its doors: run `lift` (for
the start dome), the dome's `_inside` stage and its outgoing tunnel's stage after it, as
the whole build does. Every stage gives the same result run twice.
Rebuilding a dome also shuts the doors of the tunnels that meet it, and
an open tunnel stays open behind a shut door: run `function
station:reset/all` after rebuilding a dome during a game.

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
- The datapack **adds `minecraft:husk` to the game's own
  `#minecraft:raiders` entity tag**, so that the Engine's Master (a husk)
  can ride the ravager and have it fight; the tag holds for the whole
  world, not just the station.
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
    that solves the dome, so the ring always plays end to end. No dome is
    a stub now. The module's file replaces the stub; its
    build stage runs `game.clear_stub_commands(dome)`.
  - *Two rules*: leaving a dome never costs more than the stage in
    progress; a change of form never shuts, removes or restarts
    something a player is using (it waits for the room's next safe
    point).
  - *Progress*: call `station:dome/<n>/solved` and the core does the
    rest (the title, tunnel n's pump woken for its lever by the airlock, the next dome opened, respawn
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
    the Foundry, brass armour and a sabre on entering the Engine. A dome lends
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
| `seabed` | the sea floor's plan against its rules: in the box, in free columns, clear of every dome and tunnel, standing on the surveyed floor or the reef, living coral touching water |
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
| `shell_0` ... `shell_9` | a dome: nothing inside or in its mouths wet (but where a module has registered water that is meant), no hole in shell or floor, ground under the floor, the sea above; while it is empty, the light at head height and no stray entities |
| `tunnel_0` ... `tunnel_9` | a tunnel reset, opened, read at every state as its water falls layer by layer and its lamps come on, open and dry with both domes dry, reset and flooded again (`CHECKS=tunnels`: all ten) |
| `player_count` | the count, which dome a player is in, and each dome's own solo or duo form by who is in it, with the fall back to solo |
| `vote` | both kinds of vote: proposed, counted, shown, running out, passing |
| `difficulty` | the level taking force on entering a dome, the scaled values, the level kept through a reset |
| `progress` | the run started, the clock, a dome solved, the win, the best time |
| `reset` | the reset from a run with tunnels open and draining and a vote open |
| `automatons` | an automaton summoned and dressed as the plan wants it, scaled by the level; nothing dropped; the count by the dome's form; gone when the dome empties |
| `restricted_items` | the items `fittings.restricted` writes are taken by the game and keep their rules |
| `fights` | the difficulty read; waves cast where a player is, to the cap, refilled; leash and fence; a death answered; the sweep; a dome's bossbar |
| `fittings` | the torch clock, its lamp chase and pistons seen running; a gauge; a lever put back and held; a button read once; a plate that wants a player; a display; a lent item; a hint |
| `ring` | the whole ring's progress walked by a stand-in from the master lever to the win (throwing a stub's BYPASS lever, if any dome were still a stub), and the reset |
| `seabed_live` | a sample of the sea floor's plan read back (coral that has died is reported) and the water's biome inside the box |
| `shore`, `dock`, `lift`, `start_dome`, `boiler_room`, `gearworks`, `flooded_dome`, `foundry`, `signal_room`, `clockwork_maze`, `boss`, `cargo_hold`, `hull_breach` | the modules' own checks (see each module) |
| `hull_breach_rig` | only when named: the Breacher in the check cell by day or night, with two golems for prey (see `dome_hullbreach.rig`) |

A check of a part not built would be listed as `TODO`, and a TODO is not
a pass; none is left. Players are stood in for by armour stands
(`game_checks.py` says what that proves and what it does not).

What RCON cannot stand in for (an item in a real hand, a jump, whether a
fight is fair, sounds and titles) is listed in PROGRESS.md for a person to
try.

## Putting the station somewhere else

Another world, or another part of this sea. Every position is an offset
from one anchor, so the layout moves as a whole:

1. Survey the sea there with `survey_site.py`; it writes
   `site_survey.npz`.
2. Set the site block at the top of `station_layout.py`, and nothing
   else: `ANCHOR` (the x, z of the middle of the start dome),
   `BASE_FLOOR_Y` (the y of its floor), `SEA_LEVEL`, `SPAWN`,
   `SHORE_LANDING` and the site's hazards (`MINESHAFT_SPAWNERS`, empty if
   there are none). The shape block (`RING`: each dome's offset from the
   anchor, its size, how far its floor is sunk) stays as it is.
3. Run `python station_layout.py`: it prints the layout, runs
   `check_layout()` and then `check_site()` against the survey. The site
   check fails if a dome's footprint has land in it, a dome's top is above
   the surface or its floor more than 3 above the sea floor, a tunnel
   crosses land, the shore landing is not the top of the ground, or the
   row to the dock crosses land or a bubble column. Its notes say how far
   each dome's top is below the surface, how much of each dome and tunnel
   is over a ravine, and what structure blocks lie under the box. The
   same check is `site` in `verify_station.py`'s offline checks (skipped
   if there is no survey file).
4. Run `python render_layout.py` and read the picture.

What that does not do: choose the anchor for you (the search that chose
this one was done by hand and is not in the example), or change the
shape to fit a sea of another size; and the site check knows only what
the survey holds.
