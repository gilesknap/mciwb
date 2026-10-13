# Castle 2: Fable II

Castle Fable (`examples/castle`) with a lower bailey twice as deep, filled
with a timber-framed village, farm animals in pens and the people who live
there. It reuses castle's modules rather than forking them: castle2 sets a
bigger layout, adds its own stages to castle's and checks them. The plan
is in [PLAN.md](PLAN.md) (gilesknap/mciwb#173), and how far it has got in
[PROGRESS.md](PROGRESS.md).

```
mciwb run build_castle2.py                        # everything, in order
STAGES=village,pens mciwb run build_castle2.py    # just some stages
mciwb run verify_castle2.py                       # castle's checks and castle2's
CHECKS=pens,people mciwb run verify_castle2.py    # some of castle2's checks only
python house_rig.py rig.png                       # every house variant, offline
mciwb run house_rig.py                            # the same in the air over the site
```

`examples/castle` must sit beside this folder. Pass `--server` and
`--port` for a server that is not the `mciwb start` one, and the password
in `$MCIWB_PASSWORD` (or `--password-file`).

## Where and what

The defaults are in `castle2_layout.DEFAULTS` and the environment
overrides them (as castle's): `BAILEY_DEPTH=162`, `ORIGIN=560,68,-190` (a
flat, dry site at x 550..700, z -200..70, ground 62..72), `SPAWN=32,74,-64`,
`NAME=Fable II`, `BANNER=cyan`. Import `castle2_layout` before any of
castle's modules: it sets these before castle's layout reads them.

In castle's local coordinates (x east, z south, y above the bailey floor)
the bailey is x 0..120, z 65..226, in three parts:

| Part | Local z | What |
| --- | --- | --- |
| North | 65..120 | castle's barracks, stables, smithy, well and cross paths, as in castle |
| Village | 120..190 | the market square (x 44..76, z 147..165) with a market cross and a bell, a ring of lanes, 28 houses |
| South | 190..226 | the pens, the allotments, a frog pond, castle's market stalls by the gate |

The second pair of mid-wall towers stands at z 164. Everything under the
bailey (dungeons, catacombs, lower treasury) is where castle has it,
counted from the junction: it hangs off the smithy's hatch and the well's
tunnel.

## Stages

castle2 runs castle's stages (see castle's README) with three of its own:

- `village` (after `bailey_buildings`): the lanes, the square, the market
  cross and the houses of `castle2_layout.HOUSES`.
- `pens` (after `village`): seven pens of animals (cows, sheep, pigs,
  chickens, goats, rabbits, frogs), the allotments with a scarecrow and
  bee hives by the upper ward's garden.
- `people` (after castle's `details`): the castle's people (king and queen
  on their thrones, cook, librarian, monk, alchemist, smith, jailer), the
  shopkeepers with trades that match their shops, drinkers in the tavern,
  villagers and children round the square, cats, loose chickens, a copper
  golem at the market and guards with spears on the walls.

castle2 also only puts castle's lantern posts where the sky is clear (not
under a house's eaves or between the chapel's pews).

## The house

`house.medieval_house(corner, width, depth, floors, facing, jetty,
jetty_sides, ground, frame, roof, roof_block, chimney, windows,
window_boxes, contents, seed)` builds a timber-framed house: stripped dark
oak beams with calcite infill (close studding, square panels or braced),
a stone or timber ground storey, upper storeys jettied over the street on
upside-down stair joists, a gable, cross-gable or hip roof, a brick
chimney with a fireplace and a campfire for smoke, plank floors, a stair
(a ladder in a narrow house), lanterns, and the furniture of `contents`
(`house_contents.py`): a home, eleven shops (a counter window, shelves of
goods, item frames and a hanging sign) or the tavern. It is drawn on a
canvas in its own frame and turned to face its street, so `house_blocks`
gives the blocks without placing them. It returns a `House`: its volume,
door, the stands of its people (counter, bedside, hearth) and its seats.

`house_rig.py` builds every variant in `VARIANTS` (every option value at
least once) and checks each: nothing outside its volume, the door clear
on both sides, every storey reachable on foot from the street, joists
under every jetty, the seats facing their tables, the stands free floor.

## Checks

`verify_castle2.py` runs all of castle's checks (`verify_castle.checks`),
then castle2's:

- seats: every seat (castle's `castle_lib.seat` and the houses') is read
  back from the world and must face the way its sitter looks, its back to
  no table and with a table, altar, lectern or open floor in front;
- houses: each door, the floor either side of it, and every stand;
- pens: each fence ring closed and all its animals inside it;
- people: every static person at their spot, every villager inside the
  walls (stray cats and iron golems, which villages bring, are removed).

castle's entity check counts what every stage summoned, castle2's
included (`castle_layout.SUMMONED`).

## Tools

- `record_build.py`: runs a build against a fake client and writes every
  command and the final blocks, to diff two builds without a server (how
  phase 0 proved castle unchanged), or to render a build offline
  (`RECORD_PNG`). `dry_run` lets the checks learn what a build places.
- `top_render.py`: a plan view of a large region over RCON (two commands
  per column), for servers whose world files are not on this machine.
- `render_rcon.py`: renders a small region over RCON, forceloading it.

## Files

- `castle2_layout.py`: the defaults, the village, the pens and their checks.
- `build_castle2.py`: castle's build with castle2's stages and checks.
- `house.py`, `house_contents.py`, `house_rig.py`: the house.
- `village.py`, `pens.py`, `people.py`: castle2's stages.
- `verify_castle2.py`: the checks.
