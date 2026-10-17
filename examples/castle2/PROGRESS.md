# Castle 2: progress

The state of the work on castle2 (gilesknap/mciwb#173, plan in
[PLAN.md](PLAN.md)), for whoever picks it up next. Branch
`examples/castle2`.

## Done

- **Phase 0** (castle resizable, unchanged at its default size):
  `BAILEY_DEPTH` (default 81) in `castle_layout`; mid-wall towers are a
  list (`MID_ZS`, one pair per 81 of depth) with their wall stairs; the
  market follows the gate. The stages that mix structure and furniture are
  split: `keep_interiors` = `interiors_shell` + `interiors_furnishing` +
  `interiors_lights`, `chapel` = `chapel_shell` + `chapel_furnishing`,
  `bailey_buildings` = `bailey_shell` + `bailey_furnishing`, `details` =
  `details_fixtures` + `details_people`. Every seat goes through
  `castle_lib.seat(pos, faces)` (faces = the way the sitter looks) and is
  recorded in `castle_lib.PLACED_SEATS` (castle's own `castle_layout.SEATS`
  from #174 lists castle's seats for its verify). The branch was rebuilt on
  694358f (#174, which reworked castle: tower doors, levers by the gates,
  pit trap, seats): the refactor was redone on top of it, dropping our own
  seat fix (#174 has it). Proof: `record_build.py` records a full castle
  build against a fake client; the sorted commands and the final blocks
  are identical to 694358f's. Re-check after touching castle with
  `python record_build.py ../castle /tmp/after` and diffing against a
  recording of `git archive 694358f examples/castle` (the old branch, before
  the rebuild, is the local branch `castle2-pre174`).
  Decision taken: the underground complex (dungeons, catacombs, lower
  treasury) does NOT move with the gate: it hangs off the smithy's hatch and
  the well's tunnel, so it is counted from the junction. (PLAN.md put the
  dungeon hut in the south: deviation.)
- **Phase 1** (doubled bailey): `castle2_layout` (defaults ORIGIN
  560,68,-190, BAILEY_DEPTH 162, NAME "Fable II", BANNER cyan; Fable is
  red, the castle at 148,-262 purple, the one at -300,-40 yellow),
  `build_castle2` (castle's build plus castle2's stages and layout check),
  `verify_castle2` (castle's checks + castle2's).
- **Phase 2** (`medieval_house`): `house.py`, `house_contents.py`,
  `house_rig.py`. All 13 rig variants pass offline and in the world (the
  rig was built over the site at y 150+ and cleared).
- **Village layout**: `castle2_layout.HOUSES` (28 houses), `LANES`,
  `SQUARE`, `MARKET_CROSS`, `CLOCK_TOWER` plot (empty, for phase 6);
  `village_problems()` checks houses against towers, castle's buildings,
  paths, stairs, signs, lanes, the square and each other.
- **Phase 3** (pens): `pens.py`; `PENS`, `GARDEN`, `BEEHIVES` in the layout.
- **Phase 4** (people): `people.py`.
- **Phase 5** (rooms in full detail): `rooms.py` replaces castle's
  furniture in the `interiors`, `chapel` and `bailey_buildings` stages
  (castle's shells kept; see `build_castle2`), and a new `furnish` stage
  (after `dungeons`) adds detail where castle furnishes as it builds
  (alchemist's tower, dungeon prisoners, vault treasure, winch-room guard).
  All seats go through `castle_lib.seat`. What each castle2 stage summons
  is counted by running it against a fake client
  (`record_build.summon_counts`), so `SUMMONED` stays right.
- **Phase 6** (machines and the clue trail): all ten machines, each with
  its `*_cells` and a check that works it in place: `machines_upper.py`
  (lectern lock, copper puzzle, astrolabe, engine bell, transmuter),
  `organ.py`, `machines_bailey.py` (clock tower, archery lock, mill,
  listening door); `SECRETS` in the layout. `clues.py` (stage `clues`,
  after `people`) lays the trail: books on lecterns (tavern, fletcher, the
  prisoner's cell) and in the secrets' reward chests (slot 13), a plaque in
  the smithy, and Mercator's chart (his last trade). `clues.TRAIL` orders
  it and adds each book to its secrets' `clues`; every secret has 2+.
  `guide2.py` prints Rumours, then the whole trail as Spoilers.
- **Docs**: README.md; `guide2.py` (castle's guide for castle2, plus the
  village, shops and keepers, pens and people); castle2's teleports are
  added to castle's `TELEPORTS` (checked by castle's verify, listed in the
  guide).

## In the world (mciwb-test, Minecraft 26.3)

Castle Fable II is built at ORIGIN 560,68,-190: site x 550..690,
z -200..47, entities tagged `castle_560_-190`; its road runs south from
the bridge, west along z ~52 / x 545, then along z -64 to spawn
(32,74,-64), sharing the last leg with the castle at 148,-262. Rebuilt
2026-10-17 in full from this branch (machines and clues included) on
mciwb 694358f.

Last full verify (2026-10-17, all checks, nobody online, from the dev
pod): **259/259 passed** in 105 s, after a full build (63 s). The clock
tower's dawn check was flaky (2 of 4 runs) at time 23500, on the edge of
sunrise: it now rings at 1000 (6/6 since).

## How to run (the dev pod on nuc2)

- The kubeconfig is `.devcontainer/config` (cluster-admin; kept out of git
  by `.git/info/exclude`). There is no kubectl in the sandbox: the helper
  `/cache/mciwb-devpod/kpod.py` (Python `kubernetes` client) drives a pod
  `minecraft/mciwb-dev` on nuc2 with hostNetwork, so RCON is
  `127.0.0.1:30600` (about 0.05 ms a command), `MCIWB_PASSWORD` comes from
  the `mciwb-test-rcon` secret, and the world's PVC is mounted read-only
  at `/data` (region files under `/data/world/dimensions/...`).
  `K="uv run --python 3.13 --no-project --with kubernetes python
  /cache/mciwb-devpod/kpod.py"`, then:
  - `$K create`, then once: `$K sync src examples pyproject.toml uv.lock
    README.md LICENSE` and `$K sh 'apt-get update -qq && apt-get install -y
    -qq git && SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0+dev uv sync --python
    3.13 --no-dev'`. `$K delete` when done.
  - After each edit: `$K sync examples`.
  - Build: `$K bg build 'cd /work/examples/castle2 && ../../.venv/bin/mciwb
    run build_castle2.py --server 127.0.0.1 --port 30600'` (about 63 s),
    then `$K log build`. Long jobs must go through `bg`: an exec stream
    that is quiet for a minute times out and kills its command.
  - Verify: the same with `verify_castle2.py` (about 100 s with nobody
    online; 20+ minutes with a player on, the ticks are real time).
    `CHECKS=clues,signs` for a subset; FORCE=1 if a player is near.
  - Look: `peek.py X1 Y1 Z1 X2 Y2 Z2` (copy it into /work) prints block
    names from the region files, a table per y; the chunks are not loaded
    outside a build or verify, so RCON block tests fail there.
- The sandbox's Python is 3.13 (`.python-version` says 3.11): use
  `uv run --python 3.13 ...` for ruff, pyright and `record_build.py`.
- See: `top_render.py` (plan of a large area, ~10 s), `render_rcon.py`
  (a small region), or offline `RECORD_PNG=x.png python record_build.py .
  /tmp/c2 build_castle2`.

## Known problems / notes

- Goats and frogs leap any fence: their pens have an invisible barrier
  ring (5 high) over a 3-high fence. Animals step over a fence from any
  block beside it, so nothing in a pen stands next to its fence.
- RCON replies get mixed with the dashboard's (`list`) now and then
  (#166 item 2): mciwb now retries setblock/fill/loot/ground reads (#170);
  castle2's checks read a failing block again.
- Wild animals wander into the site (it reaches 10 blocks outside the
  walls): `people.kill_strays` (run by the people stage and before the
  checks) removes untagged animals of the kinds castle2 keeps, and stray
  cats and iron golems.
- castle's verify leaves out marker armour stands from its "no armour
  stand in a block" check (castle2's seated people ride markers in their
  seats); castle's own seat check is given castle2's seats by
  verify_castle2.
- Hostile mobs still spawn somewhere in the site at night (cleanup kills
  ~10): probably natural caves under the platform, as castle notes. Not
  investigated.
- The main gate is closed to villagers by a row of fence gates outside
  castle's portcullis (main_gate.py; villagers cannot open them). verify's
  `roam` check sprints ROAM_TICKS (6000) and counts the villagers inside
  again: all 31 (9 of them mobile, which do move: ~20 blocks in 1200
  ticks) stayed in over 6000 and over 24000 ticks.
- The castle's own great hall carpet covers the dais step and cuts the
  benches (castle quirk, kept in castle; castle2's phase 5 should redo it).

## Next steps

1. Done (the notes kept for reference): phase 6, the ten machines and
   the clue trail. Build each in a rig first (as castle's
   test_modules.py: a stone block in the air over the site, toggled
   over RCON and read back), with a `*_cells` function used by the build
   and verify alike, then place it. `SECRETS` in the layout
   lists each secret, its machine and its clues; verify checks the clues
   (book on lectern, sign text, map in a trade) and works each machine.
   Formats tested in 26.3 (all work through Placer, NBT included):
   written books on lecterns
   (`lectern[...]{Book:{id:"minecraft:written_book",count:1,components:
   {"minecraft:written_book_content":{title:"T",author:"A",pages:["p1","p2"]}}}}`),
   patterned banners (`{patterns:[{color:"yellow",pattern:"minecraft:border"}]}`),
   chiseled bookshelves with Items, shelves with Items, hanging signs with
   front_text/back_text, villagers with VillagerData and Offers, a
   villager riding a marker armour stand. Paintings' `facing` is 0 south,
   1 west, 2 north, 3 east (item frames' 3D: 2 north, 3 south, 4 west,
   5 east). Ideas for the hard ones:
   - lectern lock: a comparator reads the page (a 15-page book gives
     page = signal); exact match with two subtract-mode comparators
     against constant signals (dust from a redstone block, 16 - c long)
     ANDed, or "≥ P" by dust length with "≥ P+1" cutting it via a torch;
     the result drives a castle_lib.hidden_door (its lever-variant dust).
   - astrolabe: an item frame's comparator output is its rotation + 1;
     three frames each through an exact-match, ANDed, open a floor panel.
   - organ: buttons as keys beside the note blocks (a hit note block gives
     no signal); a sequence lock from copper bulbs (they toggle on each
     pulse and a comparator reads them), a wrong key resetting them.
   - copper puzzle (lights-out): copper bulbs toggled by buttons wired to
     their neighbours; all lit, ANDed by comparators, opens the inner door.
   - archery lock: a target's output is 15 only for a bullseye: a dust
     line 15 long passes only that to a hatch.
   - clock tower (the plot at `CLOCK_TOWER`, 5x5 in the square):
     daylight detector and its inverse, observers pulsing a bell at dawn
     and dusk, lamps at night. The mill: an observer chain moving pistons.
   - verify over RCON: lectern page by `data modify block ... Page`, frame
     rotation by `data modify entity ... ItemRotation`, arrows summoned at
     the target, redstone blocks in place of button presses.
2. Done: the gate (fence gates, main_gate.py) and the `roam` check that
   the villagers stay in.
3. Done: the docs image (docs/images/castle2.png: `mciwb render 545 48 -205
   695 161 52 --view iso_sw --no-labels --scale 4 --folder /data`, in the
   pod, cropped), shown in docs/how-to/claude-skill.rst and the README.
