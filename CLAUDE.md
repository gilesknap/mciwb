# mciwb: guide for AI agents

mciwb (Minecraft Interactive World Builder) builds things in a Minecraft Java
Edition world from Python, over RCON. It is built on
[mcwb](https://github.com/gilesknap/mcwb) (geometry, blocks, bulk building) and
[mcipc](https://github.com/conqp/mcipc) (the RCON client and command wrappers).

## Development

```bash
uv sync                          # create .venv with the dev dependencies
uv run ruff check src tests      # lint (uv run ruff format to format)
uv run pyright src tests         # type check
uv run pytest -m "not system"    # unit tests, no podman needed
uv run pytest                    # plus system tests: need a podman service
uv run tox -e docs               # docs build, warnings are errors
```

- Unit tests use `tests/mockclient.py`, a fake RCON client with a 100^3 mock
  world. MockClients with the same host/port share one world, so Monitor
  threads see it too. Extend it when you use new client commands.
- System tests (`tests/test_system`) start a real server in podman on RCON
  port 20401. Set `MCIWB_KEEP_SERVER=1` to keep it between runs.
- mciwb finds the Podman socket from `CONTAINER_HOST`, then
  `$XDG_RUNTIME_DIR/podman/podman.sock`, then `/run/podman/podman.sock`
  (`podman_client` in `src/mciwb/server.py`). Podman resolves bind mount
  paths on its host, so from the devcontainer only folders mounted at the
  same path work: the system tests use `/tmp/test-mc-servers`.
- The Minecraft release (`MINECRAFT_VERSION`, `SERVER_IMAGE` in
  `src/mciwb/server.py`) must match `mcwb.MINECRAFT_VERSION`, the release that
  `mcwb.Item` was generated from. A unit test checks this.
- Commit in small logical steps; never commit to main.

## Building something

Start a server (Minecraft 26.3 in podman, RCON on localhost:20100) with
`mciwb start`. Then either run a script, or use `mciwb shell` for IPython:

```bash
mciwb run build.py --player NAME   # NAME is optional: a player in the world
```

`mciwb backup [--backup-name NAME]` zips the world to `~/mciwb-backups`
(flushing it first over RCON if the server is running) and `mciwb restore
[NAME]` restores it; give both the `--port`/`--password` used with `mciwb start`.

`mciwb run` and `mciwb shell` provide `world` (an `Iwb`) plus every name in
`mciwb.imports`. A standalone script does the setup itself:

```python
from mciwb.imports import Direction, Item, Iwb, Vec3, get_client, polygon

world = Iwb()                      # connects to the `mciwb start` server
try:
    base = Vec3(632, 73, -1658)    # the spawn point of the default world
    world.set_block(base, Item.GOLD_BLOCK)
    world.set_block(base + Direction.UP, Item.OAK_STAIRS, facing=Direction.EAST)
    world.place_door(base + Direction.NORTH * 3, Item.OAK_DOOR, Direction.SOUTH)
    # a hollow hexagonal tower of stone bricks, 10 high
    polygon(get_client(), base + Direction.EAST * 10, height=10, diameter=9,
            sides=6, item=Item.STONE_BRICKS)
    print(world.get_block(base))   # minecraft:gold_block
    print(world.cmd("time set day"))  # any console command, without the /
finally:
    world.stop()                   # stop background threads
```

## Seeing what you built: build, render, check

You cannot see the game, so render the region you built to a PNG and read
the image. Do this after each build step, and fix what looks wrong:

```bash
mciwb run hut.py                                     # 1. build
mciwb render 620 72 -1670 645 90 -1645 \
    --view top --view iso --view south --output hut.png  # 2. render X Y Z X Y Z
mciwb render --centre 632 80 -1658 --size 26 18 26   #    or a centre and size
```

3. Read the PNG. Each view is titled and labelled with world coordinates
   (the label is centred on its row or column of blocks), so you can relate
   any pixel to a block position. `top` is a plan view with north up and x
   across. `north`/`south`/`east`/`west` are elevations seen from that side.
   `iso` is a 3D view from the south east (`iso_ne`, `iso_nw` and `iso_sw`
   look from the other corners). The pale blue background is air. Glass,
   water, torches, fences etc. are drawn see-through.
4. Check the facts in code rather than by eye. In a script:

```python
grid = world.render(a, b, "hut.png", views=["top", "iso"])  # or world.scan(a, b)
print(grid.counts())          # {'minecraft:stone_bricks': 412, ...}, no air
assert grid[a + Vec3(2, 1, 2)] == "minecraft:gold_block"
```

- Blocks are read from the world's region files after `save-all flush`, which
  is fast (0.06 s for 3.5 million blocks on the CI server). This works when the world
  folder is on this machine: `~/mciwb-server/world` for `mciwb start`, or
  give `--folder`. Otherwise (or with `--rcon`) blocks are read over RCON one
  at a time, which is slow and capped at 32768 blocks.
- Pass the same `--port`/`--password` as `mciwb start`.
- In a script, `world.scan`/`world.render` read the files of
  `world.world_folder`. It is found for the server of `mciwb start` (any
  `--port`) when its `--folder` is the default; otherwise it is `None` and
  blocks are read over RCON, so set it:
  `world.world_folder = pathlib.Path("/my/server/world")`.
- By default each view is about 512 px across, shrunk if needed to keep the
  whole image under 1500 px wide: wider images are scaled down before you see
  them. Small regions render smaller (at most 16 px per block). Three views
  fit in one row; for a closer look at a large region, render fewer views or
  a smaller region. `--scale` sets one pixels-per-block for every view, with
  no width limit.
- Colours are averages (no textures), and block states are not drawn (stairs
  and slabs look like full blocks). `mciwb.palette.set_colour` changes a
  colour.

## Conventions

- Coordinates are `Vec3(x, y, z)`; Y is up. `Direction.NORTH` is (0, 0, -1),
  `SOUTH` (0, 0, 1), `EAST` (1, 0, 0), `WEST` (-1, 0, 0), `UP`, `DOWN`.
  Vec3 supports `+`, `-` and `* number`, e.g. `pos + Direction.UP * 3`.
  `Direction.cardinals()` lists the four compass directions.
- The default flat test world's ground is y = -61; in the default normal
  world (seed 0) the spawn point is (632, 73, -1658).
- Blocks are `mcwb.Item` members (`Item.STONE`, `Item.CHERRY_PLANKS` ...), or
  `"minecraft:..."` strings. `Item` covers every block in
  `mcwb.MINECRAFT_VERSION`. Block states go in `set_block(..., nbt=[...])`,
  e.g. `nbt=["half=top"]`, and `facing=` takes a Direction.
- `world.set_block` returns False (and logs the server error) when the server
  rejects a placement. Commands only work in loaded chunks: near a player, or
  after `world.cmd("forceload add X1 Z1 X2 Z2")`.
- Every thread needs its own RCON client: call `get_client()` inside any
  function that a `Monitor` runs. `Monitor(func, once=True)` runs a job in
  the background; `Monitor.stop_all()` (or `world.stop()`) stops them.

## Building blocks

From `mciwb.imports` (all re-exported from mcwb or mciwb):

- `polygon(client, center, height, diameter, sides=4, direction=UP, item=...,
  mode=FillMode.KEEP)`: a hollow prism. Also good for floors and clearing
  areas (`item=Item.AIR, mode=FillMode.REPLACE`).
- `make_tunnel(client, profile, start, direction=..., length=...)`: extrude a
  2D profile (list of rows of Items).
- `Blocks(client, position, cuboid, anchor=Anchor3.BOTTOM_NW)`: render a 3D
  array of Items, indexed `cuboid[x][y][z]`. `Volume`, `Anchor3` position it.
- `Volume.from_corners(a, b).fill(client, item)`: fill a box of any size.
  Above 32768 blocks it only fills air (mcwb uses keep mode), so it cannot
  clear a big box: `Placer().fill(a, b, Item.AIR)` splits big fills instead;
  add `filter="minecraft:stone"` to replace only those blocks.
- `world.save(file, vol)` / `world.load(file, position)`: save blocks to
  JSON and load them elsewhere. `grab(client, vol)` reads blocks as a cuboid.
- `Wall(height=3, item=...)` or `Wall(profile=[...])`, then `set_start(pos)`
  and `draw(end)`: walls with repeating profiles, e.g. battlements.
- `Switch(pos, Item.LEVER, callback)`, `world.signs.add_sign(text, callback)`:
  interactive levers and action signs.

## Higher-level builders

`mciwb.builders` (all re-exported from `mciwb.imports`). Each one uses the
thread's client, takes blocks as `Item`, block state strings or `BlockState`,
returns the bounding `Volume` of what it placed (to grab, save or clear), and
raises `BuildError` if the server rejects a command (unknown block, unloaded
chunk). Footprints are two opposite corners; their y is the top of the walls
for roofs (the roof starts at y + 1) and the top of the platform for a
foundation. See docs/how-to/builders.rst. To check a build, render the
returned volume (`world.render(box.start, box.end, "out.png")`, see "Seeing
what you built"); renders draw stairs and slabs as full blocks, so check
their states with `Schematic.from_world(box)`.

- `gable_roof(start, end, stairs=OAK_STAIRS, ridge=None, gable=None,
  axis=None, overhang=0)`: two stair slopes; the ridge runs along the longer
  side (or `axis="x"/"z"`), slab ridge for odd widths, `gable=` fills the ends.
- `hip_roof(start, end, stairs, ridge=None, overhang=0)`: four slopes with
  outer corner stairs. `flat_roof(start, end, block, parapet=None,
  parapet_height=1, overhang=0)`.
- `arch(start, end, block, style="round"|"pointed", thickness=1, depth=1,
  clear=False)`: start/end are the two feet, in line along x or z; depth goes
  south/east; `clear=True` cuts the opening to air. `arch_profile(span, ...)`
  gives the (u, v) cells without building. `column(base, height, block,
  width=1, plinth=None, capital=None)`.
- `stairway(points, stairs, landing=None, width=1, support=None,
  clearance=0)`: points are walkway blocks; sections run along x or z and
  climb at most 1 per block; stairs face up the slope, level parts are
  `landing` (default: the stairs' full block). Same-height points make a path.
  The path may pass over itself (spiral, switchback): every pass is built,
  and `support` stops above the headroom (max(clearance, 2)) of a lower pass.
  At a corner that climbs, the middle and outside of a wide stairway climb 1
  per block but the inside is too steep: make wide corners level for a few
  blocks either side if every lane must be walkable.
- `road(points, block=DIRT_PATH, width=3, border=None, clearance=2)`: lays the
  road on the ground (point y ignored), replacing the top ground block.
- `ground_height(x, z, heightmap)`, `ground_heights(columns, heightmap)`: y of
  the top ground block via `execute positioned over <heightmap>` (one command
  per column). `Heightmap.OCEAN_FLOOR` ignores water,
  `MOTION_BLOCKING_NO_LEAVES` (default) ignores leaves and plants.
- `foundation(start, end, block=COBBLESTONE, heightmap=OCEAN_FLOOR,
  max_depth=64)`: fill each column from the ground up to a platform at
  `start.y`, going at most `max_depth` blocks below it. Build it first: anything already standing there counts as ground.
- `Schematic`: Sponge `.schem` v3 (reads v2 too). `Schematic.from_world(vol)`
  reads blocks plus stairs/slab/axis states (other states and block entities
  are not readable over RCON), `.paste(pos, air=False)`, `.rotate(steps)`
  (clockwise from above), `.mirror("x"|"z")`, `.save(file)`,
  `Schematic.load(file)`, `from_cuboid`/`to_cuboid` to convert from/to `grab`
  cuboids. `blocks[x][y][z]` is a numpy array of `BlockState`.
  `world.save("f.schem", vol)` and `world.load("f.schem", pos)` use it too.
- `BlockState.parse("oak_stairs[facing=east]")`, `.with_props(half="top")`,
  `BlockState.of(Item.SNOW, layers=3, waterlogged=False)` (values may be str,
  int, bool or a Direction), `.rotate(1)`, `.mirror("x")`, `str(state)` for commands.

Stairs `facing` is the side of the full height step (people walk up towards
it); Minecraft recomputes stair `shape` from neighbours, and the builders send
the same shapes (`stair_shapes`), so grabbing back gives what was sent.

## Examples

The demos in `src/mciwb/demo` are the idiomatic examples: `pagoda.py`
(polygon and fill), `house.py` (Wall profiles and signs), `walls.py`,
`gate.py` (load a saved structure, add a lever), `village.py` (all of them
together), `follow.py` and `background.py` (Monitor threads).
