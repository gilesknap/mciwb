# Castle Fable

A large, two-ward hillside castle built with mciwb: a lower bailey with a
moat, drum-towered gatehouse and working portcullis, a grand stair up to an
upper ward with a four-turreted keep, chapel and alchemist's tower, and
dungeons, a treasure vault, traps and secret passages underneath. About
140 x 165 blocks and 80 blocks tall, with a road to spawn. A build is
about 30,000 RCON commands (most of them reading the ground under the
earthworks and the road, one command per column) and takes 10-15 seconds
with mciwb on the server's own host, plus about ten seconds waiting for
chunks to load and for the summoned entities to be checked across an
unload; over a network allow a round trip per command.

```
mciwb run build_castle.py                        # everything, in order
STAGES=keep,interiors mciwb run build_castle.py  # just some stages
mciwb run verify_castle.py                       # exercise every mechanism
mciwb run test_modules.py                        # test the mechanism modules alone
python guide.py > GUIDE.md                       # a visitor's guide, with coordinates
```

Pass `--server`, `--port` and `--passwd` for a server that is not the
`mciwb start` one. The scripts forceload the chunks they need while they
run and unload them again when they finish, however they finish.

## Moving it, and building more than one

Where to build, and the castle's name and colour, come from the environment:

```
ORIGIN=-80,82,-230 SPAWN=32,74,-64 NAME=Fable BANNER=red mciwb run build_castle.py
```

- `ORIGIN` is the north-west corner of the outer wall at the lower bailey's
  standing level (ground y + 1). Everything is placed relative to it
  (`castle_layout.py`). The earthworks stage follows the terrain (it fills a
  platform down to the ground and digs the moat and ditch), so the castle
  can go on any site about 150 x 190 blocks where the ground is within ~30
  blocks of the platform levels (the bailey at `ORIGIN.y`, the upper ward
  18 higher).
- `SPAWN` is where the road from the gate leads. The gate faces south; the
  road goes south until it is clear of the site, then round the side of the
  site nearer spawn, then to spawn, with lantern posts along it and a
  signpost at the end. Several castles may share the last leg: the roads
  re-lay the same path, a lamp post is left alone where one (or another
  road) already is, and each castle's signpost stands a different distance
  back from spawn (chosen from its `ORIGIN`, stepping further back if
  another castle's sign is there), so none overwrites another's. Rebuilding
  a road is idempotent: the same posts and sign, once. `verify_castle.py`
  checks the path is continuous, the sign is there, every post is a single
  post, and nothing post-shaped stands within 4 blocks of the road except
  single posts in the lamp lane (3 to the side), where another castle's
  posts may share the leg at its own spacing.
- `NAME` goes on the sign inside the gate, the vault's sign and the
  signpost; `BANNER` is the colour of the castle's banners (the second
  colour, blue, is fixed).
- `verify_castle.py` and `guide.py` take the same variables, so that they
  check and describe the right castle.

Every entity the castle summons (horses, armour stands, item frames, the
golem and the cat) is tagged `castle_<x>_<z>` of its origin, and with its
stage. A stage removes its own entities before it runs and the earthworks
stage (a fresh site) removes every entity in the site, so rebuilding all or
part of a castle never duplicates them. Mobs are summoned with
`PersistenceRequired`, so they do not despawn, and the horses are fenced in
their stalls. Before it finishes, the build unloads and reloads the site,
counts what each stage summoned (`castle_layout.SUMMONED`) and runs a stage
again if anything is missing: now and then one horse was gone by the first
check after a build (observed, not explained: gilesknap/mciwb#166, item 9).

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

The site that is cleared and forceloaded is x -10..130, z -10..156 (the
moat, ditch and bridge included); the castle itself spans y -16 (the
catacombs' floor) to 62 (the keep's lightning rod). Everything underground
is cut out of a lining of brick or cobble, so a cave or an aquifer in the
hill cannot break into it.

The bailey's buildings, wall stairs, paths and signs are placed by
constants in `castle_layout.py` (`STABLES`, `BARRACKS`, `SMITHY`,
`WALL_STAIRS` ...), and `castle_layout.layout_problems()` checks them
against every round tower on the wards' ground (`ROUND_TOWERS`: the
bailey's, the gatehouse's drum towers, the upper ward's, the alchemist's
tower and the keep's turrets, out to radius + 1, so the walls and the
ground doors stay clear) and against each other; the paths must stop short
of the buildings (the well stands where the two paths cross, and each
stops at its rim), and each wall stair's top must be at its walk's level.
`build_castle.py` refuses to build a layout that fails it; `test_modules.py`
and `verify_castle.py` run it too.

## Mechanisms

All plain redstone, so they work for players without mciwb running. Their
positions are in `castle_layout.py`; `castle_lib` has a `*_cells` function
for each that gives the positions of its parts, used by the build and by
`verify_castle.py` alike:

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
- **Cell doors** (`castle_lib.cell`): each dungeon cell's front is a
  grille of two open iron trapdoors beside an iron door, both panels on the
  corridor edge of the front (iron bars would stand mid-block, a quarter
  block behind the door), and a brick frame that carries a stone button on
  both sides, so nobody gets shut in.

`verify_castle.py` toggles each of them over RCON and reads the result
back (the arrow trap by its dispensers' stock going down: an arrow that
hits the armour stand on the wire breaks it and vanishes; each cell door
by setting a redstone block in place of its frame, a stand-in for a button
press, since a button placed with `setblock` does not update its
neighbours), checks that the levers, buttons, torches and
banners are mounted on solid blocks and that every roofed tower's banner
hangs in the open beside its top, that the layout check passes, the
mid-wall towers stand whole, every wall stair's top step is at its walk
with headroom and the walk goes on beyond it, and every standing sign
stands on a solid block, then checks the passages, the treasure,
the teleport targets of the guide, the road to spawn and its signpost, and
that the castle's entities are exactly the ones it summoned. A portcullis
a visitor left closed is reported as found, tested, and left closed. It clears hostile mobs from the site and anything from
the tripwires first, and leaves everything as it found it: the levers off,
the bookshelf untouched, the dispensers reloaded. Two things it has to work round: the server pauses
when nobody is online (ticks are advanced with `tick sprint`), and a lever
or hook set with `setblock` only updates its own neighbours, so levers get a
dust block beside them and tripwires are tripped by summoning an armour
stand onto them.

`test_modules.py` builds each mechanism in a 70 x 22 x 30 block of stone in
the air at `RIG=x,y,z` (its north-west bottom corner, default `0,160,-40`),
toggles it and reads it back. It refuses to run unless the rig's box is
empty, and always clears the rig again.

## Workarounds

The Minecraft server keeps one output buffer for all its RCON connections,
so when another client (a dashboard polling `list`, say) runs a command at
the same moment, a reply comes back empty or with the other client's output
in front of ours: about one command in 10k (gilesknap/mciwb#166, item 2).
`build_outer.py` wraps mciwb's `ground_heights`, `Placer.fill` and
`Placer.setblock` to accept a polluted reply and retry an empty one;
`castle_lib.run` does the same for summons and signs, and the checks read
a block again when the reply is empty. Signs are placed with a raw
`setblock`, which works, but `Placer.setblock` now takes block-entity NBT
and could place them instead (item 3). The
chapel's bell tower fills the hole that `hip_roof` used to leave in its top
ring (item 5); `hip_roof` no longer leaves it, so that fill is now harmless
but redundant. Each workaround is marked in the code with the issue; delete them when
the fixes are released.

The ticks that the checks sprint through also bring night, and hostile
mobs spawn wherever the light is 0. The castle lights every dark place of
its own: lantern posts on a 16-block grid over both wards, lanterns in the
dry ditch, on the moat's bank, on the flat tops, on every tower floor and
roofed tower's steps, along the keep's string courses, in the attics under
the gable roofs and in the dungeons' corners; arrow slits are one block
high so nothing fits in them. That covers the castle, not the natural caves
in the hill under it (the dungeons and tunnels are sealed from them, but
the caves stay dark): hostile mobs go on spawning in those caves, and a
count of mobs in the site will find them there, below the castle's floors. The build's cleanup and the checks kill whatever has
spawned in the site anyway.

With a player online the scripts never `tick sprint` (it would run the
player's game at speed): they wait for the game's own ticks, which makes
the checks slower. They refuse to build, test or verify while a player is
within 200 blocks of the site (`FORCE=1` overrides), and the checks' trap
clearing only touches hostile mobs, stray armour stands and arrows.

Two more things about a server with no players on it: it does not tick, so
after a `forceload` the scripts wait for the chunks and make it tick a
little before they look for entities (`build_outer.wait_loaded`); and the
ticks that `verify_castle.py` sprints through age copper, so the keep's
lightning rod may be `exposed_lightning_rod` by the time you visit.

## Files

- `castle_layout.py`: `ORIGIN`, `SPAWN`, `NAME` and `BANNER` from the
  environment, and where everything is, including the mechanisms and the
  teleport targets.
- `castle_lib.py`: fills, round towers, battlements, tagged summoning, the
  mechanisms and their `*_cells`.
- `build_outer.py`: earthworks, walls, towers, gatehouse, bridge, road,
  grand stair, keep shell; the site's forceload and the road's route.
- `build_inner.py`: rooms, chapel and crypt, alchemist's tower, bailey
  buildings, dungeons, vault, details.
- `build_castle.py`: the staged driver. `verify_castle.py`: the checks.
- `test_modules.py`: the mechanism modules alone. `guide.py`: the guide.
