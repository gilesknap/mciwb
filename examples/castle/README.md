# Castle Fable

A large, two-ward hillside castle built with mciwb: a lower bailey with a
moat, drum-towered gatehouse and working portcullis, a grand stair up to an
upper ward with a four-turreted keep, chapel and alchemist's tower, and
dungeons, a treasure vault, traps and secret passages underneath. About
150 x 190 blocks and 100 blocks tall, built in a few seconds over RCON.

```
mciwb run build_castle.py                 # everything, in order
STAGES=keep,interiors mciwb run build_castle.py   # just some stages
mciwb run verify_castle.py                # exercise every mechanism
mciwb run test_modules.py                 # test the mechanism modules alone
```

Pass `--server`, `--port` and `--passwd` for a server that is not the
`mciwb start` one. The scripts need the chunks loaded: `build_castle.py`
forceloads the site itself and the `cleanup` stage unloads it again
(`STAGES=cleanup`).

## Moving it

Everything is placed relative to `ORIGIN` in `castle_layout.py`, the
north-west corner of the outer wall at the lower bailey's standing level. The
earthworks stage follows the terrain (it fills a platform down to the ground
and digs the moat and ditch), so the castle can go on any site about
150 x 190 blocks where the ground is within ~30 blocks of the platform
levels. The road to spawn in `build_outer.bridge_and_road` has the spawn
point of the world it was built for (32, 74, -64) hard coded.

## Layout (local coordinates, x east, z south, y above the bailey floor)

| Area | Local | Notes |
| --- | --- | --- |
| Upper ward | x 0..120, z 0..64, standing level 18 | keep, chapel, alchemist's tower, garden |
| Lower bailey | x 0..120, z 65..145, standing level 0 | gatehouse, stables, smithy, barracks, well, market |
| Gatehouse | x 46..74, z 137..145 | passage x 59..61; portcullis at z 141; winch room above |
| Grand stair | x 57..63, z 65..83 | up to the middle gate (second portcullis at z 63) |
| Keep | x 40..80, z 12..42 | three storeys and a roof terrace; turrets at the corners |
| Chapel | x 86..110, z 14..40 | crypt underneath (y 8..11) |
| Alchemist's tower | centre (18, 22) | the engine on the top floor |
| Well | (60, 105) | bubble column down to the tunnels |
| Dungeons | x 69..100, z 131..143, standing level -8 | cells, guard room, pit trap |
| Catacombs | x 91..110, z 104..132, standing level -15 | oubliette, arrow trap, lower treasury |
| Vault | x 50..70, z 16..30, standing level 8 | under the keep |

## Mechanisms

All plain redstone, so they work for players without mciwb running:

- **Portcullises** (`castle_lib.portcullis`): sticky pistons above and
  below a 3-wide, 2-high passage drop and raise iron bars. The lever is in
  the winch room above the passage; the wiring runs in a diagonal dust
  channel inside the wall.
- **Hidden doors** (`castle_lib.hidden_door`): two sticky pistons hold a
  2-high section of wall; a redstone torch keeps them extended until its
  block is powered, by a chiseled bookshelf's comparator (only the 6th
  book's signal of 6 reaches the end of a 6-dust line) or by a lever.
- **Pit trap** (`castle_lib.pit_trap`): a tripwire opens two iron
  trapdoors set flush in a corridor floor.
- **Arrow trap** (`castle_lib.arrow_trap`): a tripwire powers dispensers
  in the end wall of a corridor.
- **The engine**: eight hoppers pass amethyst shards round a ring; twelve
  comparators chase lamps, a piston and note blocks.

`verify_castle.py` toggles each of them over RCON and reads the result
back. Two things it has to work round: the server pauses when nobody is
online (ticks are advanced with `tick sprint`), and a lever or hook set with
`setblock` only updates its own neighbours, so levers get a dust block
beside them and tripwires are tripped by summoning an armour stand onto
them.

## Files

- `castle_layout.py`: `ORIGIN` and where everything is.
- `castle_lib.py`: fills, round towers, battlements and the mechanisms.
- `build_outer.py`: earthworks, walls, towers, gatehouse, bridge, road,
  grand stair, keep shell.
- `build_inner.py`: rooms, chapel and crypt, alchemist's tower, bailey
  buildings, dungeons, vault, details.
- `build_castle.py`: the staged driver. `verify_castle.py`: the checks.
- `test_modules.py`: builds each mechanism in a block of stone in the air,
  east of the castle, toggles it and removes it.
