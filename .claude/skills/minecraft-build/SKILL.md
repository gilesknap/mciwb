---
name: minecraft-build
description: Build in a Minecraft Java Edition world with mciwb (Minecraft Interactive World Builder) - start the podman server, back up the world, survey the site, write a Python build script and run it with `mciwb run`, render the result to PNG to check it, and restore a backup if it went wrong. Use when the user asks to build, place, generate, clear or change anything in a Minecraft world (houses, towers, villages, terrain), or mentions mciwb, `mciwb start` or building over RCON.
---

# Building in Minecraft with mciwb

mciwb drives a Minecraft server over RCON from Python. You cannot see the
game: survey with text and images, build with scripts, render to PNG and read
the image to check every step.

## The loop

1. **Server.** `mciwb start` (safe to repeat: it reuses a running server;
   `--world-type flat` for a flat test world). It needs the Podman service:
   on "No Podman socket found" ask the user to run
   `systemctl --user enable --now podman.socket`. Give the same `--port` and
   password to every other mciwb command if `mciwb start` had them; pass a
   password as `--password-file FILE` or `$MCIWB_PASSWORD`, not
   `--password` (visible in `ps`).
2. **Backup** before any big or risky change:
   `mciwb backup --backup-name before-<what>`.
3. **Survey** the site, around a point (`X Z RADIUS`) or a player:

   ```bash
   SURVEY="632 -1658 24" mciwb run ${CLAUDE_SKILL_DIR}/scripts/survey.py
   mciwb run ${CLAUDE_SKILL_DIR}/scripts/survey.py --player NAME
   ```

   Use the `SURVEY` form when the user gave coordinates: `--player` (on any
   `mciwb run`) makes that player an operator, switches them to creative
   mode and gives them action signs, so only use it when the user asked to
   build around them and is happy with that. It prints where the players are, the ground height (min, median, max), the
   ground blocks and a text height map, and writes `survey.png` (top and iso
   views): read it. Build on ground y + 1. With no world files on this
   machine it reads over RCON, near the ground only: if that is too many
   blocks give a smaller RADIUS or a Y range, `SURVEY="X Z RADIUS YMIN YMAX"`.
4. **Write a build script.** Copy
   `${CLAUDE_SKILL_DIR}/scripts/build_template.py` into the user's project,
   set `ORIGIN` and `SIZE`, and replace `build()` and `check()`. It clears
   the site, refuses to build over a player, builds a hut (foundation,
   walls, door, gable roof), renders it beside the script and asserts on the
   blocks and the roof's stair states.
5. **Run it:** `mciwb run build.py`. It exits non-zero if a check fails.
6. **Look.** Read the PNG. Render other angles if needed:
   `mciwb render X1 Y1 Z1 X2 Y2 Z2 --view top --view iso --view south`
   (or `--centre X Y Z --size DX DY DZ`).
7. **Iterate**: fix the script and run it again. Scripts clear their site
   first, so re-running is safe.
8. **Undo** if it went badly wrong: `mciwb restore before-<what>` (it stops
   the server, restores the world and starts it again; give the same options
   as `mciwb start`). Tell the user before you restore.

## Rules

- Coordinates are `Vec3(x, y, z)`, y up. North is -z, south +z, east +x,
  west -x. In renders, `top` has north up and x increasing to the right.
- Flat world (`--world-type flat`): the top grass block is y = -61, so build
  from y = -60. Default world (seed 0): spawn is (632, 73, -1658).
- Blocks are `Item.NAME` (`Item.STONE_BRICKS`) or `"minecraft:name"` strings;
  states go in brackets (`"minecraft:oak_stairs[facing=east,half=top]"`) or
  `world.set_block(pos, item, facing=Direction.EAST, nbt=["half=top"])`.
- Prefer `/fill` to loops of `set_block`: one `client.fill(a, b, item)`
  places up to 32768 blocks in one RCON command;
  `Volume.from_corners(a, b).fill(client, item)` fills a box of any size,
  replacing everything in it (`Item.AIR` clears a site), and
  `Placer().fill(a, b, item, filter="minecraft:stone")` replaces only some
  blocks in a box of any size. Use `FillMode.HOLLOW`/`OUTLINE` for walls and shells, `polygon` for
  towers, `Blocks` for a 3D array. Each `set_block` is an RCON round trip,
  so keep per-block loops for details.
- Use the builders rather than placing stairs by hand: `gable_roof`,
  `hip_roof`, `flat_roof`, `arch`, `column`, `stairway`, `road`. On uneven
  ground, build a `foundation` first (a level platform filled down to the
  ground); `ground_height(x, z)` gives the ground under one column. Each
  builder returns the `Volume` it placed: render or check that.
- Save a finished piece with `world.save("piece.schem", vol)` and place
  copies with `world.load("piece.schem", pos)`, or `Schematic.load(...)`
  `.rotate(1)` / `.mirror("x")` then `.paste(pos)` for turned copies.
- Safety: never build where a player is without checking (the survey and
  the template report players in the site). Never clear or fill a region you
  have not surveyed. Keep builds inside chunks near a player, or
  `world.cmd("forceload add X1 Z1 X2 Z2")` first: commands fail in unloaded
  chunks.
- Check facts in code, not by eye: `grid = world.scan(a, b)`, then
  `grid[pos]` is a block name and `grid.counts()` counts blocks.
- Renders show average colours, not textures, and not block states (stairs
  and slabs look like full blocks): check stairs with
  `Schematic.from_world(vol).blocks[x, y, z].props["facing"]` on a small
  region. Keep renders under about 100 blocks across.

## More

- [reference.md](reference.md): the build API (`world`, `Volume`, `polygon`,
  `Blocks`, `Wall`), the builders (roofs, arches, stairways, roads,
  foundations, schematics) with their arguments, render views and options,
  performance numbers and troubleshooting.
- For other helpers, read `CLAUDE.md` in the mciwb repository and the API
  docs at https://gilesknap.github.io/mciwb/main/_api/mciwb.html. Every
  name in `mciwb.imports` is available to `mciwb run` scripts.
