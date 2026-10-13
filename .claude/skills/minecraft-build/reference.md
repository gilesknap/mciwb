# mciwb build reference

Details for the `minecraft-build` skill. Everything here is in
`mciwb.imports`, so `mciwb run` scripts can use it without importing (the
template imports it anyway, to keep linters and editors happy).

## Contents

- [Scripts and the world object](#scripts-and-the-world-object)
- [Placing blocks](#placing-blocks)
- [Bulk building](#bulk-building)
- [Reading blocks back](#reading-blocks-back)
- [Rendering](#rendering)
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
  works with `client.fill` and `client.setblock`. `Volume.fill`, `polygon`
  and `Volume.walls` need an `Item`.
- Facing: stairs, doors, chests, furnaces and the like take `facing=` a
  `Direction` (`NORTH` -z, `SOUTH` +z, `EAST` +x, `WEST` -x). Stairs face
  the way you walk up them. Slabs take `nbt=["type=top"]`, logs
  `nbt=["axis=x"]`, lanterns `nbt=["hanging=true"]`.
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
  `.size`, `.inside(pos)`, `.fill(client, item)` (any size: splits into
  several `/fill`s), `.walls(client, item, top=False, bottom=False)`.
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
- `world.save("piece.json", vol)` and `world.load("piece.json", position)`:
  copy a structure to a file and place it elsewhere (or many times).
- Higher level builders may be added: check `mciwb.imports` and `CLAUDE.md`
  for what this version has.

Write each part of a build as a function taking a position, so it can be
moved, repeated and rebuilt. The demos in `src/mciwb/demo` of the mciwb
repository (`pagoda.py`, `house.py`, `village.py`) are worked examples.

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
  slabs look like full blocks): check orientation in code or by placing a
  test block, not from the image.
- Blocks are read from the world files after `save-all flush` (fast, needs
  the world folder on this machine: `~/mciwb-server/world` for `mciwb start`,
  or `--folder`). Otherwise, or with `--rcon`, over RCON at most 32768
  blocks. In a script set `world.world_folder = Path(".../world")` for a
  server in another folder.

## Server, backups and options

| Command | What it does |
| --- | --- |
| `mciwb start [--world-type flat]` | start (or reuse) the server in podman, RCON on localhost:20100 |
| `mciwb stop` | stop it |
| `mciwb backup [--backup-name NAME]` | zip the world to `~/mciwb-backups` (flushes it first) |
| `mciwb restore [NAME]` | stop, restore the backup (default: the latest), start |
| `mciwb run SCRIPT [--player NAME]` | run a build script |
| `mciwb render ...` | render a region to PNG |

The server's files are in `~/mciwb-server` (`--folder`). Pass the
`--port`/`--password` of `mciwb start` to `backup`, `restore`, `render` and
`run` (`run` spells it `--passwd`). `mciwb restore` takes all the options
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
| `Wrong RCON password` | use the `--password` given to `mciwb start` (`rcon.password` in `~/mciwb-server/server.properties`) |
| `set_block` returns False with a "not loaded" error | the chunk is unloaded: build near a player or `forceload add` |
| Fill: "Too many blocks" | over 32768 blocks: use `Volume.fill` or split the box |
| Render warns "no server ... recent changes may be missing" | pass the `--port`/`--password` of `mciwb start` so it can flush the world first |
| Render is all pale blue | the region is air, or chunks were never generated: check coordinates with the survey |
| Build has floating or buried parts | re-survey: ground height varies; build on ground y + 1 per column, or level the site first with a `fill` |
