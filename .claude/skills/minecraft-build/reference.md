# mciwb build reference

Details for the `minecraft-build` skill. Everything here is in
`mciwb.imports`, so `mciwb run` scripts can use it without importing (the
template imports it anyway, to keep linters and editors happy).

## Contents

- [Scripts and the world object](#scripts-and-the-world-object)
- [Placing blocks](#placing-blocks)
- [Bulk building](#bulk-building)
- [Builders: roofs, arches, stairways, roads](#builders-roofs-arches-stairways-roads)
- [Terrain: ground heights and foundations](#terrain-ground-heights-and-foundations)
- [Schematics: saving and reusing pieces](#schematics-saving-and-reusing-pieces)
- [Reading blocks back](#reading-blocks-back)
- [Rendering](#rendering)
- [Redstone, entities and paused servers](#redstone-entities-and-paused-servers)
- [Big builds: layout and stages](#big-builds-layout-and-stages)
- [Server, backups and options](#server-backups-and-options)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)

## Scripts and the world object

`mciwb run build.py [--player NAME]` connects to the server, gives the
script `world` (an `Iwb`) and runs it as `__main__`, then stops background
threads. `get_world()` returns the same object, and `get_client()` the RCON
client of the current thread. `--player NAME` sets `world.player` (its
`.pos` is the player's position, `.facing` the direction they face) and
makes the player an operator in creative mode.

`mciwb shell` is the same in IPython, for trying things out by hand.

A script that is not run by `mciwb run` connects itself:
`world = Iwb()` (`Iwb(server, port, passwd)` for another server), and calls
`world.stop()` at the end.

## Placing blocks

```python
world.set_block(pos, Item.OAK_STAIRS, facing=Direction.EAST, nbt=["half=top"])
world.place_door(pos, Item.OAK_DOOR, Direction.SOUTH)  # both halves
world.get_block(pos)  # an Item, e.g. Item.GOLD_BLOCK
world.cmd("time set day")  # any console command, without the /
```

- `set_block` returns False and logs the server's error if it is rejected,
  e.g. an unknown block or state, or an unloaded chunk.
- Blocks: `Item.<NAME>` has every block of the server's Minecraft release
  (`Item.CHERRY_PLANKS`, `Item.RED_WOOL`). A string `"minecraft:name[state]"`
  works with `client.fill`, `client.setblock` and the builders (which also
  take a `BlockState`). `Volume.fill`, `polygon` and `Volume.walls` need an
  `Item`.
- Facing: stairs, doors, chests, furnaces and the like take `facing=` a
  `Direction` (`NORTH` -z, `SOUTH` +z, `EAST` +x, `WEST` -x). A stair's
  facing is the side of its tall back: it faces the way you walk up it, and
  someone sitting on it faces the opposite way (a chair facing a table to
  its north is `facing=south`). Slabs take `nbt=["type=top"]`, logs
  `nbt=["axis=x"]`, lanterns `nbt=["hanging=true"]`.
- Thin panels: a closed door's panel and an open trapdoor's lie against
  the edge of their block opposite their `facing`; iron bars, glass panes
  and fences stand in the middle of the block. To make a door flush with a
  grille beside it, use open iron trapdoors with the door's facing. An iron
  trapdoor follows its redstone power, so a lever or button touching it
  closes it when the power goes.
- Vec3 arithmetic: `pos + Direction.UP * 3`, `a - b`, `pos.with_ints()`.
  `Direction.cardinals()` lists the four compass directions.

## Bulk building

The RCON client (`client = get_client()`) has the Minecraft commands as
methods:

```python
client.fill(a, b, Item.STONE)  # a box, up to 32768 blocks
client.fill(a, b, Item.STONE, FillMode.HOLLOW)  # shell, inside -> air
client.fill(a, b, Item.STONE, FillMode.OUTLINE)  # shell, inside untouched
client.fill(a, b, Item.GLASS, FillMode.KEEP)  # only where there is air
client.fill(a, b, Item.AIR, FillMode.REPLACE, "minecraft:water")  # filter
client.setblock(pos, "minecraft:chest[facing=west]")
```

From mcwb (geometry) and mciwb:

- `Volume.from_corners(a, b)`: a box. `.start` (lowest corner), `.end`,
  `.size`, `.inside(pos)`, `.fill(client, item)` (replaces every block in
  the box, of any size: splits it into several `/fill`s; `Item.AIR` clears
  it), `.walls(client, item, top=False, bottom=False)`.
- `Placer().fill(a, b, item, mode=None, filter=None)`: a `/fill` of any
  size that raises `BuildError` if the server rejects it; with
  `filter="minecraft:stone"` (or a tag like `"#minecraft:logs"`) it replaces
  only those blocks, e.g. `Placer().fill(a, b, Item.AIR, filter="minecraft:water")`
  drains a box.
- `Volume.from_anchor(pos, size, Anchor3.BOTTOM_MIDDLE)`: a box positioned
  by a corner or face centre.
- `polygon(client, center, height, diameter, sides=4, item=..., mode=...)`:
  a hollow prism centred on `center`, `height` blocks long in `direction`
  (default up): towers, round rooms (`sides=16` looks round). Its default mode is `FillMode.KEEP`, which leaves existing
  blocks alone: pass `mode=FillMode.REPLACE` to build through terrain, and
  `item=Item.AIR, mode=FillMode.REPLACE` to clear a disc.
- `make_tunnel(client, profile, start, direction=..., length=...)`: extrude
  a 2D profile (rows of Items) along a direction: tunnels, roads, roof
  ridges.
- `Blocks(client, position, cuboid)`: place a 3D array of Items indexed
  `[x][y][z]` (lists or a numpy array), with its north west bottom corner at
  `position`. Good for small detailed pieces drawn in code.
- `Wall(height=3, item=Item.STONE_BRICKS)` or `Wall(profile=[col, col, ...])`
  (each column listed top down, repeated along the wall):
  `wall.set_start(ground)`, `wall.draw(ground2)`, `wall.draw(ground3)` ...
  draws connected walls standing on those ground blocks.

Write each part of a build as a function taking a position, so it can be
moved, repeated and rebuilt. The demos in `src/mciwb/demo` of the mciwb
repository (`pagoda.py`, `house.py`, `village.py`) are worked examples.

## Builders: roofs, arches, stairways, roads

Each builder sends `setblock`/`fill` commands with the stair and slab states
worked out, returns the bounding `Volume` of what it placed (to render,
check, save or clear) and raises `BuildError` if the server rejects a
command (unknown block, unloaded chunk). Blocks may be an `Item`, a state
string or a `BlockState`. Arguments after the block are keyword only.

```python
# roofs: start/end are opposite corners of the footprint, usually the top
# corners of the walls; the roof starts at start.y + 1
gable_roof(start, end, Item.SPRUCE_STAIRS, gable=Item.SPRUCE_PLANKS, overhang=1)
hip_roof(start, end, Item.DARK_OAK_STAIRS, overhang=1)
flat_roof(start, end, Item.SMOOTH_STONE, parapet=Item.STONE_BRICK_WALL)

# an arch in a wall: start/end are its two feet, in line along x or z
arch(foot1, foot2, Item.STONE_BRICKS, style="pointed", depth=2, clear=True)
column(
    base,
    6,
    Item.QUARTZ_PILLAR,
    plinth=Item.SMOOTH_QUARTZ,
    capital=Item.CHISELED_QUARTZ_BLOCK,
)

# paths: a list of points, each straight section along x or z
stairway(
    [Vec3(0, 64, 0), Vec3(10, 70, 0), Vec3(10, 72, 6)],
    Item.STONE_BRICK_STAIRS,
    width=3,
    support=Item.STONE_BRICKS,
    clearance=3,
)
road(
    [Vec3(0, 0, 0), Vec3(30, 0, 0), Vec3(30, 0, 20)],
    Item.DIRT_PATH,
    width=3,
    border=Item.COBBLESTONE,
)
```

- `gable_roof(start, end, stairs=OAK_STAIRS, *, ridge=None, gable=None,
  axis=None, overhang=0)`: two slopes; the ridge runs along the longer side
  (or `axis="x"`/`"z"`), with a slab ridge over an odd width; `gable=` fills
  the triangular ends. A footprint W across the ridge is about W/2 high.
- `hip_roof(start, end, stairs=OAK_STAIRS, *, ridge=None, overhang=0)`:
  four slopes. `flat_roof(start, end, block=SMOOTH_STONE, *, parapet=None,
  parapet_height=1, overhang=0)`.
- `arch(start, end, block=STONE_BRICKS, *, style="round"|"pointed",
  thickness=1, depth=1, clear=False)`: `depth` goes south or east;
  `clear=True` cuts the opening to air (a doorway through an existing
  wall). Its legs are short: put it on a wall or columns for a taller
  opening. `arch_profile(span, thickness, style)` gives its cells without
  building.
- `column(base, height, block=QUARTZ_PILLAR, *, width=1, plinth=None,
  capital=None)`: `height` includes the plinth and capital, which are one
  block wider all round.
- `stairway(points, stairs=STONE_BRICK_STAIRS, *, landing=None, width=1,
  support=None, clearance=0)`: points are the blocks people stand on, at
  the start, each corner and the end; a section climbs at most 1 per block.
  Stairs face up the slope, level parts are `landing` (default: the stairs'
  full block). It may pass over itself (spiral round a tower, switchback).
  Wide stairways: keep corners level, as the inside of a climbing corner is
  too steep.
- `road(points, block=DIRT_PATH, *, width=3, border=None, clearance=2,
  heightmap=...)`: ignores the points' y and replaces the top ground block of
  each column, stepping with the terrain. Keep it out from under roofs and
  overhangs, which count as the ground.
- Widths are centred on the points (even widths have the extra lane on the
  right of the direction of travel).

## Terrain: ground heights and foundations

- `ground_height(x, z, heightmap=Heightmap.MOTION_BLOCKING_NO_LEAVES)`: the
  y of the top ground block of a column (build on y + 1). `ground_heights(
  [(x, z), ...], heightmap)` returns a dict keyed by `(x, z)`. One RCON
  command per column, so sample a grid for big sites. `Heightmap`:
  `OCEAN_FLOOR` ignores water, `MOTION_BLOCKING_NO_LEAVES` ignores leaves and
  plants but stops at water, `WORLD_SURFACE` stops at anything.
- `foundation(start, end, block=COBBLESTONE, *, heightmap=OCEAN_FLOOR,
  max_depth=64)`: fills each column of the footprint from the ground up to a
  level platform at `start.y`; build on `start.y + 1`. Build it first:
  anything standing on the site counts as the ground.
- A building on a slope: pick the floor y from the survey's median ground
  (or `ground_height` at the door), lay a `foundation` under the whole
  footprint, then build on it. For a terraced site, one foundation per
  terrace, joined with a `stairway`.

## Schematics: saving and reusing pieces

```python
world.save("tower.schem", vol)  # Sponge .schem, with stair/slab/log states
world.load("tower.schem", pos)  # pos is the bottom SOUTH west corner
piece = Schematic.load("tower.schem").rotate(1)  # a quarter turn clockwise
piece.paste(pos)  # pos is the bottom NORTH west corner; returns the Volume
Schematic.from_world(vol).blocks[x, y, z]  # a BlockState, from vol.start
```

- `.schem` files are the format of WorldEdit and other tools. A filename
  ending `.json` saves the older mcwb format (blocks only, no states).
- `rotate(steps)` and `mirror("x"|"z")` turn block states too (stairs,
  doors, logs, fences). `paste(pos, air=False)` leaves the world alone where
  the schematic has air; `air=True` clears the box.
- Reading the world is slow (a few RCON commands per block) and only reads
  the states of stairs, slabs and log-like blocks; other blocks come back
  in their default state.
- Checking stairs: renders draw stairs as full blocks, so read a small
  region back and look at `state.name` and `state.props` (`facing`, `half`,
  `shape`). Stairs `facing` is the side of the tall step, the way you walk
  up them.
- `BlockState.parse("minecraft:oak_stairs[facing=east]")`,
  `BlockState.of(Item.OAK_STAIRS, facing=Direction.EAST, half="top")`,
  `.with_props(...)` and `str(state)` build state strings for `setblock`.
  A trailing SNBT block entity suffix is kept (`state.nbt`, `.with_nbt(...)`),
  so `Placer().setblock(pos, "oak_sign[rotation=4]{front_text:{...}}")` and
  `Placer().fill` place signs, filled chests and lecterns without `cmd()`.

## Reading blocks back

```python
grid = world.scan(a, b)  # a BlockGrid of the region
grid[pos]  # "minecraft:stone_bricks"
grid.counts()  # {"minecraft:stone_bricks": 412, ...}, no air
grid.to_names()  # numpy array of names, [x][y][z]
grid.origin, grid.size  # the lowest corner, and the size
```

`grab(client, vol)` reads a region as a `Cuboid` of Items over RCON (slow:
small regions only).

## Rendering

```bash
mciwb render X1 Y1 Z1 X2 Y2 Z2 --view top --view iso --output out.png
mciwb render --centre X Y Z --size DX DY DZ
```

In a script `world.render(a, b, "out.png", views=["top", "iso"])` returns the
`BlockGrid` it drew.

- Views: `top` (plan, north up, x to the right, higher blocks lighter),
  `north`, `south`, `east`, `west` (elevations seen from that side, e.g.
  `south` looks north at the south face), `iso` (3D from the south east) and
  `iso_ne`, `iso_nw`, `iso_sw`.
- Each view is labelled with world coordinates; a label is centred on its
  row or column of blocks. The pale blue background is air. Glass, water,
  torches and fences are drawn see-through.
- The image is sized to stay under 1500 px wide (about 512 px per view,
  three views per row). For detail, render a smaller region or fewer views;
  `--scale N` sets pixels per block with no width limit.
- Colours are averages, with no textures and no block states (stairs and
  slabs look like full blocks): check their states with
  `Schematic.from_world` (see above), not from the image.
- Blocks are read from the world files after `save-all flush` (fast, needs
  the world folder on this machine: `~/mciwb-server/world` for `mciwb start`,
  or `--folder SERVER_FOLDER`, the folder that holds `world/`). Otherwise, or
  with `--rcon`, over RCON at most 32768 blocks (e.g. 32 x 32 x 32): a
  larger region fails, so render a large build in pieces, or from the world
  files. In a script set `world.world_folder = Path(".../world")` for a
  server in another folder.

## Redstone, entities and paused servers

### Paused servers

The server of `mciwb start` keeps ticking with nobody online. Other
servers usually pause: `pause-when-empty-seconds` in `server.properties`
(default 60) stops the game that long after the last player leaves.
Commands still run and `setblock`/`fill` still change blocks, but nothing
moves: no redstone, pistons, hoppers, falling sand or flowing water, and
mobs stand still. So on a paused server:

- To see a mechanism work, advance the game by hand:
  `world.cmd("tick sprint 40")` runs 40 ticks (2 s of game time) as fast
  as it can. The command returns at once and the sprint runs after it, so
  wait a moment (about 0.2 s plus 0.01 s per tick) before reading blocks.
  Only sprint when no player is online (`get_client().players.players` is
  empty): with a player online the server ticks anyway, and a sprint would
  run their game at speed; wait `ticks / 20` seconds instead.
- `execute if loaded X Y Z` never reports true, even for forceloaded
  chunks: do not wait on it.
- Entities in freshly forceloaded chunks cannot be selected (`kill @e[...]`
  and `execute if entity` find nothing) until the server has ticked them.
- Many sprinted ticks (thousands, over repeated checks) also bring night,
  so hostile mobs spawn in the dark parts of the site, and copper ages:
  light the build, and kill hostile mobs in the site before you check it.

### Loading chunks

`forceload add X1 Z1 X2 Z2` only asks for the chunks; they load in the
background, and a script is faster. Commands sent at once fail with "not
loaded", or find no entities. What works on any server: poll a block in
each chunk until it is loaded, then tick a little so that its entities are
there too.

```python
import time


def wait_loaded(points, timeout=60):
    """wait for the chunks at these (x, z) and their entities"""
    deadline = time.time() + timeout
    for x, z in points:  # e.g. one point in each forceloaded chunk
        while "not loaded" in world.cmd(f"execute if block {x} 0 {z} minecraft:air"):
            if time.time() > deadline:
                raise TimeoutError(f"chunk at {x}, {z} not loaded")
            time.sleep(0.5)
    if not get_client().players.players:
        world.cmd("tick sprint 20")  # let the entities load: see above
    time.sleep(1)
```

Forceload at most 256 chunks per command, and `forceload remove` them when
the script ends (in a `finally`), so the server does not keep them loaded.

### Redstone placed by commands

- A lever or tripwire hook placed or switched with `setblock` updates only
  its own neighbours, not the blocks next to the block it is attached to,
  as a click would. Put a redstone dust beside the lever, and after
  switching it re-place the dust (`setblock` to `air`, then to
  `redstone_wire`) so that it picks up the new power. A button placed with
  `setblock` does not press: to test the circuit, set a `redstone_block` in
  place of the block the button is on, as a stand-in for a press, then put
  that block back.
  When the lever's block carries a redstone torch (to take the signal up),
  re-placing dust is no help: change the lever's block to another block and
  back instead. A redstone torch set by command keeps the `lit` state it is
  given until a neighbour changes, so give it the state its power implies.
- A tripwire is only tripped by an entity moving on it: summon one onto
  the wire (an `Invulnerable:1b` armour stand, so arrows from a trap do not
  break it; not `NoGravity:1b`, which never touches the blocks it is in),
  tick, check, then kill it.
- Tripwire timing: the hooks hold their signal 10 ticks from the first
  touch, and a walking player is on the string for about 7, so whatever the
  wire sets off must act on them while they are on it (a pit's trapdoors
  under the wire, not two blocks on). A test stand that stays on the wire
  hides this: move it off as soon as the trap fires.
- Block entity data is not a block state: a chiseled bookshelf's
  `last_interacted_slot` (what its comparator reads), a sign's text or a
  container's items are set with
  `world.cmd("data merge block X Y Z {last_interacted_slot:5}")`, not in
  `[...]`.
- Test each mechanism on its own (in an empty box in the air, say) before
  building it into the real thing, toggling it and reading the blocks back.

### Entities

Clearing a site removes blocks, not entities, so running a build script
again adds a second horse, armour stand or item frame on top of the first.
Tag everything you summon, and kill the tagged ones before summoning again:

```python
TAG = "mybuild"  # one per build; add a second tag per stage to rebuild one stage
world.cmd(f"kill @e[tag={TAG}]")  # first: wherever they have wandered to
world.cmd(
    f'summon minecraft:horse {x} {y} {z} {{Tags:["{TAG}"],PersistenceRequired:1b}}'
)
```

The chunks must be loaded, with their entities (see above), or the kill
finds nothing. `PersistenceRequired:1b` stops a mob despawning; fence it in
too, and keep doorways out of its pen, or it wanders off. Count them back
with `world.cmd(f"execute if entity @e[tag={TAG}]")` (the reply ends with
the count).

## Big builds: layout and stages

`examples/castle/` in the mciwb repository
(https://github.com/gilesknap/mciwb/tree/main/examples/castle) is a large
worked example: a castle with working redstone, built in stages and checked
by a separate verify script. Its lessons:

- Put every position in one layout module (`castle_layout.py`): the
  buildings, the mechanisms and their parts, and teleport targets. The
  build, the checks and any guide all import it, so they cannot disagree.
  Give each mechanism a function that returns the positions of its parts,
  used by the build and the checks alike.
- Check the layout in code before building: buildings must not overlap
  towers (out to the tower's radius + 1, so walls and tower doors stay
  clear) or each other, paths must stop short of buildings, and stair tops
  must meet their floors. Refuse to build a layout that fails.
- Build in stages that can be rerun on their own, each killing its own
  tagged entities first.
- Keep the verify script separate from the build, and have it leave the
  world as it found it (levers back, entities it summoned killed).

## Server, backups and options

| Command | What it does |
| --- | --- |
| `mciwb start [--world-type flat]` | start (or reuse) the server in podman, RCON on localhost:20100 |
| `mciwb stop` | stop it |
| `mciwb backup [--backup-name NAME]` | zip the world to `~/mciwb-backups` (flushes it first) |
| `mciwb restore [NAME]` | stop, restore the backup (default: the latest), start |
| `mciwb run SCRIPT [--player NAME]` | run a build script; `--player` makes NAME an operator in creative mode |
| `mciwb render ...` | render a region to PNG |

The server's files are in `~/mciwb-server` (`--folder`). Pass the
`--port` and password of `mciwb start` to `backup`, `restore`, `render` and
`run`: the password goes in `--password-file FILE` or `$MCIWB_PASSWORD`
(`--password` also works, but shows in `ps`). `mciwb restore` takes all the options
of `mciwb start`, as it starts the server again. Existing backups:
`ls ~/mciwb-backups`.

## Performance

- One `/fill` of up to 32768 blocks is one RCON round trip, like one
  `setblock`. Fill boxes and shells, then add details block by block.
- Each RCON command is a round trip: tens of thousands of `set_block` calls
  take minutes. Group runs of the same block into `fill`s.
- Reading blocks from the world files is fast (millions of blocks in well
  under a second); over RCON about 0.6 ms per block.
- Large builds: build in chunks near a player, or `forceload` the area
  first and `forceload remove` it after.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `No Podman socket found` / `not responding` | ask the user to run `systemctl --user enable --now podman.socket`, then `mciwb start` |
| `Could not connect to server localhost:20100` | the server is not running: `mciwb start`, or wrong `--port` |
| `Wrong RCON password` | use the password given to `mciwb start` (`--password-file`, `$MCIWB_PASSWORD`) (`rcon.password` in `~/mciwb-server/server.properties`) |
| `set_block` returns False with a "not loaded" error | the chunk is unloaded: build near a player or `forceload add` |
| Fill: "Too many blocks" | over 32768 blocks: use `Volume.from_corners(a, b).fill(client, item)`, or `Placer().fill(a, b, item, mode, filter)` for a mode or filter; both split the box |
| Render warns "no server ... recent changes may be missing" | pass the `--port` and password of `mciwb start` so it can flush the world first |
| Render is all pale blue | the region is air, or chunks were never generated: check coordinates with the survey |
| Build has floating or buried parts | re-survey: ground height varies; lay a `foundation` under it, or place each column at `ground_height(x, z) + 1` |
| `BuildError` from a builder | the message has the server's reply: an unknown block or state, or an unloaded chunk |
| Stairs face the wrong way | `facing` is the side of the tall step: read them back with `Schematic.from_world` and fix the `facing` you sent |
| Redstone does nothing, nothing moves | the server is paused with nobody online: `tick sprint N` (see [Paused servers](#paused-servers)); a lever set with `setblock` needs its dust re-placed |
| `kill @e[...]` or a count finds no entities that should be there | the chunks are not loaded, or not yet ticked: [Loading chunks](#loading-chunks) |
| Unknown block, e.g. `minecraft:chain` | the id was renamed: `iron_chain`. Look for the name in `Item` |
| Duplicate mobs or armour stands after a rerun | tag what you summon and kill the tagged ones first: [Entities](#entities) |
| Render or scan: too many blocks over RCON | over 32768 blocks: render from the world files (`--folder`), or smaller pieces |
