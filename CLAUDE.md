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
uv run pytest -m "not system"    # unit tests, no docker needed
uv run pytest                    # plus system tests: need a docker daemon
uv run tox -e docs               # docs build, warnings are errors
```

- Unit tests use `tests/mockclient.py`, a fake RCON client with a 100^3 mock
  world. MockClients with the same host/port share one world, so Monitor
  threads see it too. Extend it when you use new client commands.
- System tests (`tests/test_system`) start a real server in docker on RCON
  port 20401. Set `MCIWB_KEEP_SERVER=1` to keep it between runs.
- The Minecraft release (`MINECRAFT_VERSION`, `SERVER_IMAGE` in
  `src/mciwb/server.py`) must match `mcwb.MINECRAFT_VERSION`, the release that
  `mcwb.Item` was generated from. A unit test checks this.
- Commit in small logical steps; never commit to main.

## Building something

Start a server (Minecraft 26.3 in docker, RCON on localhost:20100) with
`mciwb start`. Then either run a script, or use `mciwb shell` for IPython:

```bash
mciwb run build.py --player NAME   # NAME is optional: a player in the world
```

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
- `world.save(file, vol)` / `world.load(file, position)`: save blocks to
  JSON and load them elsewhere. `grab(client, vol)` reads blocks as a cuboid.
- `Wall(height=3, item=...)` or `Wall(profile=[...])`, then `set_start(pos)`
  and `draw(end)`: walls with repeating profiles, e.g. battlements.
- `Switch(pos, Item.LEVER, callback)`, `world.signs.add_sign(text, callback)`:
  interactive levers and action signs.

## Examples

The demos in `src/mciwb/demo` are the idiomatic examples: `pagoda.py`
(polygon and fill), `house.py` (Wall profiles and signs), `walls.py`,
`gate.py` (load a saved structure, add a lever), `village.py` (all of them
together), `follow.py` and `background.py` (Monitor threads).
