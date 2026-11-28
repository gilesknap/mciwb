---
name: drowned-station
description: Work on The Drowned Station (examples/station), the mciwb adventure of ten glass domes under the sea - change a dome, build it into the live world, play-test with the owner, bake live hand edits back into the code, and run a round of parallel agents to a merged PR. Use when the user mentions the Drowned Station, a dome by name (Pump House, Boiler Room, Gearworks, Cargo Hold, Flooded Dome, Foundry, Hull Breach, Signal Room, Clockwork Maze, the Engine), the station's datapack, its live checks or a play-test of it.
---

# Working on The Drowned Station

The station is an adventure for one or two players, built by Python over
RCON: each dome is a module (`dome_<key>.py`) that places blocks *and*
writes the datapack functions that run its game. Read `README.md` and
`PROGRESS.md` in `examples/station/` first; every module's docstring
describes its room, rules, state (scoreboard `st`) and functions. For
Minecraft 26.x pitfalls see the `minecraft-26-datapack` skill.

## The shape of the code

- **The ring.** `station_layout.RING` lists the domes in play order; a
  dome's index is its place (`layout.index_of("<key>")`, never a literal),
  and tunnel n runs from dome n to n+1.
- **Frames, not world coordinates.** Every dome places things in its own
  frame (`fittings.frame(dome)`: f forward from the entrance, r right, h up
  from the floor). To turn a world position into a frame one (or back) use
  the frame's origin/forward/right; never hard-code world coordinates
  except in a test that pins what was built live.
- **The core contract** (`game.py`): hooks `enter`, `tick`, `solo`/`duo`,
  `empty`, `leave`, `died`, `reset`; `station:dome/<n>/solved` to finish a
  dome; scores `#d<n>` (0 locked, 1 open, 2 solved), `#t<n>` (tunnel: 0 wet,
  1 pumping, 2 dry), `#run`, `#secs`, `#level`, `#best<level>`.
- **Two forms and ten levels.** Every dome has a solo and a two-player form
  and scales by level through the core's percentages (`game.scaled()`,
  which most domes wrap in their own `scaled()`). A change must keep both forms and all levels working.
- **Proofs.** Each module has offline proofs (`room_problems`, walk,
  reach, trap and sight checks, solvability searches) that the build runs,
  and a live check in `verify_station.py` that drives stand-ins through the
  real game. Keep them honest: a new rule needs a proof that fails without
  it (try the fault once).

## Commands

```bash
# offline (no server): the tests and the build against a fake client
uv run pytest -q -m "not system" tests/test_station_*.py   # ~10 min
python examples/station/verify_station.py
# live, from wherever the mciwb client can reach the server
STATION_DATAPACKS_DIR=<world>/datapacks STAGES=site,datapack,dome_3_inside \
  mciwb run build_station.py
CHECKS=cargo_hold,displays mciwb run verify_station.py
```

Stage names come from `build_station.py` (`dome_<n>_inside`,
`start_dome_inside` for the Pump House, `tunnel_<n>`, `seabed`, ...). A
change to functions only needs the `datapack` stage; a change to blocks
needs that dome's inside stage too. The whole verify takes about 10 minutes.

## Live discipline

- **Nobody online.** Builds and checks refuse to run with a player online
  (the build says "online: not building (FORCE=1 to)"). Never force a block
  build with a player in the world. A *datapack-only* reload is safe with a
  player online (no block changes, a few seconds' pause) but still needs the
  owner's OK each time.
- **One writer at a time.** Wrap every live run in a lock shared by all
  agents (e.g. `flock <lockfile> ...`), and check who is online just before.
- **Sync a clean copy.** When other agents have uncommitted work in a
  worktree, sync from `git archive HEAD examples` (plus any one file you mean
  to try), not the working tree.
- **Long runs in the background.** A build or verify can outlast a tool
  call: run it detached, log to a file, poll the log. In zsh, unquoted
  `$cmd` isn't split (wrap loops in `bash -c`), and `pgrep -f pattern`
  inside `sh -c '...'` matches its own shell (use `ps -eo pid,args | grep
  "[p]attern"`).
- **Scores the owner cares about.** A real best time (`#best<level>`) must
  survive builds and resets; read it before and after, and put it back if
  anything zeroed it. Before risky live work, copy the world's
  `scoreboard.dat` (read-only) so a run can be restored.
- **Timing flakes.** A few live checks (the maze clock, the breach cracks)
  can trip on one tick of overshoot; rerun once if that is the only failure.

## Play-testing with the owner

Useful RCON one-liners while the owner plays (they're in the game; keep to
commands that touch only them or what they asked for):

- **Test mode:** `effect give <player> minecraft:resistance infinite 255 true`
  (plus regeneration, saturation): they can't be hurt; `effect clear` after.
- **Teleport** to a dome's entrance: `domes.entrance(dome)` gives (x, y, z,
  yaw). Teleporting skips the doorway, so a dome may not be "entered":
  check `#occ<n>` and the dome's hook if something doesn't start.
- **Pause:** `tick freeze` / `tick unfreeze`.
- **Pre-open domes** for a short test: set `#d<n>` 1 then run that dome's
  `solved` function, in ring order, with the run not started. Replaying a
  solved dome may need its outgoing tunnel reset too
  (`station:tunnel/<n>/reset`): some rooms restore themselves while their
  tunnel's pump is ready.
- **Find what they mean:** read their `Pos` and `Rotation`, then scan the
  blocks or entities in front of them (`execute if block ... #minecraft:all_signs`,
  `data get block`, nearest `text_display`) rather than guessing.

**Hand edits.** The owner often asks for a change live ("move that sign",
"lower the roof"). Make it with `setblock`/`fill`/`tp` after checking the
target cells, then record it in a list (what, where in world and frame
coordinates, why). Every hand edit must be baked into the code before the
next rebuild of that dome, or the rebuild undoes it. A live move of an
*input* (a button or lever) breaks it until the datapack is rebuilt,
because functions read inputs at fixed cells: say so.

## A round of work

1. **Contract first** for parallel agents: which branch and worktree each
   owns, which files (one owner per shared file; additive edits elsewhere),
   and the owner's decisions. Builders and designers get the bigger model;
   reviews and routine runs the cheaper one.
2. **Each piece on its own branch** from `origin/main`; an **integration
   branch** merges them (`--no-ff`) for one live build and one whole verify.
3. **Build live, then the owner plays** (with a short note of what's new
   and what to watch); fix what they find, bake hand edits.
4. **A fresh local review** of the diff (correctness, and privacy: this is
   a public repo, no names, hosts or private paths) before any PR merge;
   review bots are advisory. Squash a branch full of fix commits.
5. **Keep a handoff** (state, branches, what's live, what's next) up to
   date: rounds outlast a session's context.
