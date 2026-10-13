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
  recorded in `castle_lib.SEATS`. Proof: `record_build.py` records a full
  castle build against a fake client; the sorted commands and the final
  blocks are identical to 5096c3c's (also after the rebase onto #167/#169).
  Re-check after touching castle with
  `python record_build.py ../castle /tmp/after` and diffing against a
  recording of the old castle (`git archive 72cedf8 examples/castle`).
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

## In the world (mciwb-test, Minecraft 26.3)

Castle Fable II is built at ORIGIN 560,68,-190: site x 550..690,
z -200..47, entities tagged `castle_560_-190`; its road runs south from
the bridge, west along z ~52 / x 545, then along z -64 to spawn
(32,74,-64), sharing the last leg with the castle at 148,-262. Built with
mciwb 0940fd4 (origin/main with #167 and #169; #170 not merged yet), from
this branch's examples copied to nuc2:~/castle2-run/{castle,castle2}.

Last full verify (`verify_castle2.py`, all checks, player online so real
ticks): 127/128, the one failure (two tavern seats backing onto the next
table) fixed since and re-checked: `CHECKS=seats,houses,people` 4/4,
`CHECKS=pens` 7/7.

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
  (#166 item 2): castle's workarounds are kept; castle2's checks read a
  failing block again. #170 (library retries) should make this go away:
  rebase and reinstall when it lands.
- Hostile mobs still spawn somewhere in the site at night (cleanup kills
  ~10): probably natural caves under the platform, as castle notes. Not
  investigated.
- The mobile villagers can walk out of the open main gate; none had after
  a few minutes, but PLAN says the gate should be "portcullised". Not done.
- The castle's own great hall carpet covers the dais step and cuts the
  benches (castle quirk, kept in castle; castle2's phase 5 should redo it).

## Next steps

1. Phase 5: castle2's own furnishing for the keep (great hall with
   tapestries, high table, minstrels' gallery, fireplace with a spit,
   rushes, hounds, servants), kitchen, library, armoury, chambers, chapel
   and crypt, alchemist's tower, barracks, smithy, stables, dungeons,
   vault, winch room: swap castle's `*_furnishing` functions in
   build_castle2's STAGES (keep the shells), every seat through
   `castle_lib.seat`, and update `SUMMONED` for the swapped stages
   (consider computing it with `record_build.dry_run`, counting summons).
2. Phase 6: the ten machines and the clue trail (`SECRETS` in the layout,
   `*_cells` functions, checks in verify). Test written-book NBT on a
   lectern in 26.3 first.
3. Guide (`guide2.py` with teleports to the village, market and pens, a
   Rumours section and spoilers), a docs image.
