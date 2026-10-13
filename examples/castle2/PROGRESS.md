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
- **Docs**: README.md; `guide2.py` (castle's guide for castle2, plus the
  village, shops and keepers, pens and people); castle2's teleports are
  added to castle's `TELEPORTS` (checked by castle's verify, listed in the
  guide).

## In the world (mciwb-test, Minecraft 26.3)

Castle Fable II is built at ORIGIN 560,68,-190: site x 550..690,
z -200..47, entities tagged `castle_560_-190`; its road runs south from
the bridge, west along z ~52 / x 545, then along z -64 to spawn
(32,74,-64), sharing the last leg with the castle at 148,-262. Built with
mciwb 694358f (origin/main with #167, #169, #170 and #174), from
this branch's examples copied to nuc2:~/castle2-run/{castle,castle2}.

Last full verify (`verify_castle2.py`, all checks: castle's 140-odd and
castle2's seats, houses, pens and people), after a full build and stage
rebuilds of keep/interiors and pens on the rebased branch, nobody online:
**167/167 passed**. The house rig: 13/13 offline and (earlier) in the world.

## How to run (from this sandbox)

- RCON only from nuc2 at 127.0.0.1:30600. Password: `kubectl get secret
  mciwb-test-rcon -n minecraft -o jsonpath='{.data.rcon-password}' | base64
  -d`; pass it to nuc2 only in `MCIWB_PASSWORD` on the ssh command line.
- Copy: `tar czf - castle castle2 | ssh nuc2 'cd ~/castle2-run && rm -rf
  castle castle2 && tar xzf -'` (from examples/, excluding __pycache__).
- Build: `cd ~/castle2-run/castle2 && FORCE=1 mciwb run build_castle2.py
  --server 127.0.0.1 --port 30600` (about 75 s). FORCE=1 only because the
  watching player hovers about 100 blocks above the site (y 163..170);
  check where they are first (`data get entity NAME Pos`).
- Verify: same with `verify_castle2.py` (20+ minutes with a player online:
  the ticks are real time). `CHECKS=pens,people` for a subset.
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
- The mobile villagers can walk out of the open main gate; none had after
  a few minutes, but PLAN says the gate should be "portcullised". Not done.
- The castle's own great hall carpet covers the dais step and cuts the
  benches (castle quirk, kept in castle; castle2's phase 5 should redo it).

## Next steps

1. Phase 6: the ten machines and the clue trail. Build each in a rig
   first (as castle's test_modules.py: a stone block in the air over the
   site, toggled over RCON and read back), with a `*_cells` function used
   by the build and verify alike, then place it. `SECRETS` in the layout
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
2. The gate: PLAN wants it "portcullised" against wandering villagers;
   none have left so far (checked), but nothing stops them.
3. A docs image of castle2 (top render of the site).
