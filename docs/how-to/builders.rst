Build with Roofs, Arches, Stairways and Schematics
==================================================

The `mciwb.builders` package has higher level building blocks than
single blocks and boxes: roofs, arches, columns, stairways, roads,
foundations that follow the terrain, and Sponge schematic (``.schem``) files.
They are all in ``mciwb.imports``, so ``mciwb shell`` and scripts run with
``mciwb run`` have them already.

How they work
-------------

- Positions are ``Vec3(x, y, z)``: Y is up, north is -z, east is +x (see
  :ref:`coordinates`).
- Blocks are ``Item`` members (``Item.OAK_STAIRS``), block state strings
  (``"minecraft:oak_stairs[facing=east]"``) or `mciwb.builders.BlockState`
  objects.
- A block state string or ``BlockState`` may end with block entity data in
  SNBT, as ``setblock`` takes it: a sign's text or a chest's contents.
  ``Placer().setblock`` and ``Placer().fill`` send it with the block::

      sign = BlockState.of(Item.OAK_SIGN, rotation=4).with_nbt(
          """{front_text:{messages:["Hi","","",""]}}""")
      Placer().setblock(Vec3(0, 70, 0), sign)
      Placer().setblock(Vec3(1, 70, 0),
                        'chest[facing=west]{Items:[{Slot:0b,id:"minecraft:apple",count:3}]}')
- Each function builds with ``setblock`` and ``fill`` commands over RCON,
  using one ``fill`` for each rectangle of the same block where it can.
- Each function returns the bounding box of the blocks it placed, as a
  ``Volume``. Use it to read the build back, save it, or clear it again::

      box = gable_roof(Vec3(0, 70, 0), Vec3(8, 70, 6))
      print(box.start, box.end, box.size)
      Volume.from_corners(box.start, box.end).fill(get_client(), Item.AIR)

- A command that the server rejects (an unknown block, or a position in a
  chunk that is not loaded) raises `mciwb.builders.BuildError`. Build near a
  player, or ``world.cmd("forceload add X1 Z1 X2 Z2")`` first.
- Stairs and slabs get explicit block states. Minecraft works out the
  ``shape`` of stairs (straight, or an inner or outer corner) from their
  neighbours, and the builders work out the same shapes, so what they send is
  what the world ends up with.

A small house
-------------

This script builds a house on uneven ground: a foundation, walls, an arched
doorway, a hip roof, columns either side of the door and a path to it.
Run it with ``mciwb run house.py``::

    from mciwb.imports import (
        Direction, Item, Vec3, Volume, arch, column, foundation, get_client,
        hip_roof, road,
    )

    client = get_client()
    floor = Vec3(640, 70, -1650)           # the north west corner of the floor
    far = floor + Vec3(10, 0, 8)            # the south east corner

    # level the site, with a porch to the south: a platform at floor.y,
    # filled down to the ground
    foundation(floor, far + Direction.SOUTH * 4, Item.COBBLESTONE)

    # hollow walls 4 high, on top of the platform
    walls = Volume.from_corners(floor + Direction.UP, far + Direction.UP * 4)
    walls.walls(client, Item.STONE_BRICKS, top=False, bottom=False)

    # an arched doorway through the south wall
    door = Vec3(643, 71, far.z)
    arch(door, door + Direction.EAST * 4, Item.STONE_BRICKS, clear=True)

    # a hip roof sitting on the walls, overhanging by one block
    hip_roof(floor + Direction.UP * 4, far + Direction.UP * 4,
             Item.DARK_OAK_STAIRS, overhang=1)

    # columns on the porch, either side of the door
    for x in (642, 648):
        column(Vec3(x, 71, far.z + 2), 4, Item.QUARTZ_PILLAR,
               plinth=Item.SMOOTH_QUARTZ)

    # a road from the porch south over the ground (it starts beyond the
    # roof's overhang, which would otherwise count as the ground)
    road([Vec3(645, 0, far.z + 2), Vec3(645, 0, far.z + 20)], Item.DIRT_PATH)

Check what you built
--------------------

Each builder returns the ``Volume`` it placed, so you can render exactly that
region to an image (see :ref:`render_howto`) and look at it, then fix the
script and build again::

    roof = hip_roof(floor + Direction.UP * 4, far + Direction.UP * 4,
                    Item.DARK_OAK_STAIRS, overhang=1)
    world.render(roof.start, roof.end, "roof.png", views=["top", "iso", "south"])

Or render the whole site from the command line with ``mciwb render``. The
images show blocks as flat colours and draw stairs and slabs as full blocks,
so to check the facing or shape of stairs read them back with
``Schematic.from_world(volume)`` (see `Schematics`_).

Roofs
-----

The roofs cover the rectangle between two opposite corners, which are usually
the top corners of the walls. The roof starts one block above them.

`mciwb.builders.gable_roof`
    two slopes of stairs meeting at a ridge, which runs along the longer
    side unless you give ``axis="x"`` or ``axis="z"``. Give ``gable=`` a
    block to fill in the triangular ends::

        gable_roof(Vec3(0, 70, 0), Vec3(8, 70, 6), Item.SPRUCE_STAIRS,
                   gable=Item.SPRUCE_PLANKS, overhang=1)

`mciwb.builders.hip_roof`
    four slopes, with outer corner stairs where they meet.

Over an odd width, both sloping roofs finish with a ridge of slabs (or the
``ridge`` block), on a full block (a double slab) that fills the gap between
the top stairs.

`mciwb.builders.flat_roof`
    one layer of a block or slab, with an optional ``parapet`` around the
    edge. Walls, fences and panes in the parapet join up by themselves.

Arches and columns
------------------

`mciwb.builders.arch` builds an arch standing in a wall. Its two feet are the
outermost blocks at the bottom, in a line along x or z. ``style`` is
``"round"`` or ``"pointed"``, ``thickness`` is the thickness of the ring,
``depth`` the thickness through the wall (going south or east), and
``clear=True`` also sets the opening under the arch to air, to cut a doorway
through an existing wall. `mciwb.builders.arch_profile` gives the shape of an
arch without building it, which helps to plan the wall around it.

`mciwb.builders.column` builds a square column, with an optional wider
``plinth`` at the bottom and ``capital`` at the top.

Stairways and roads
-------------------

Both follow a path: a list of points where each straight section runs along x
or along z. Add a point at each corner.

`mciwb.builders.stairway` climbs between the heights of its points. Each point
is a block that people stand on; a section can climb at most one block for
each block along it. Where it climbs there are stairs facing up the slope,
elsewhere level ``landing`` blocks (by default the full block that matches
the stairs, e.g. stone bricks for stone brick stairs). Points at the same
height give a level path. ``support`` fills the space under the stairway and
``clearance`` cuts headroom through the terrain::

    stairway([Vec3(0, 64, 0), Vec3(10, 70, 0), Vec3(10, 72, 6)],
             Item.STONE_BRICK_STAIRS, width=3, support=Item.STONE_BRICKS,
             clearance=3)

Round a corner that climbs, the middle and the outside of a wide stairway
climb one block at a time, but the inside of the corner is shorter and too
steep to walk up. To make every part of a wide stairway easy to walk, keep it
level for a few blocks either side of each corner.

A stairway can pass over itself, like a spiral staircase round a tower or a
switchback: every pass is built, and ``support`` under a higher pass stops
above the headroom of the pass below it (``clearance``, or at least 2
blocks)::

    stairway([Vec3(0, 64, 0), Vec3(6, 67, 0), Vec3(6, 70, 6),
              Vec3(0, 73, 6), Vec3(0, 76, 0), Vec3(6, 79, 0)],
             Item.OAK_STAIRS)

`mciwb.builders.road` ignores the heights of its points and lays the road
on the ground, replacing the top block of each column, with an optional
``border``. The ground is the highest block in the column (see below), so
keep roads out from under roofs and overhangs.

Foundations and the ground
--------------------------

`mciwb.builders.foundation` fills each column of a footprint from the ground
up to a level platform. Build it before anything else on the site: the ground
is the highest block in each column, so a building already there would count
as the ground.

`mciwb.builders.ground_height` and `mciwb.builders.ground_heights` give the y
of the top ground block in a column, using Minecraft's heightmaps (one RCON
command per column). `mciwb.builders.Heightmap` chooses what counts as the
ground: ``OCEAN_FLOOR`` ignores water, ``MOTION_BLOCKING_NO_LEAVES`` ignores
leaves and plants but stops at water, ``WORLD_SURFACE`` stops at anything::

    y = ground_height(640, -1650)
    world.set_block(Vec3(640, y + 1, -1650), Item.TORCH)

Schematics
----------

`mciwb.builders.Schematic` holds a box of blocks with their block states, and
loads and saves Sponge schematic (``.schem``) files, the format that
WorldEdit and other Minecraft tools use::

    house = Schematic.from_world(Volume.from_corners(corner1, corner2))
    house.save("house.schem")

    copy = Schematic.load("house.schem").rotate(1)   # a quarter turn clockwise
    copy.paste(Vec3(700, 70, -1650))

``world.save("house.schem", volume)`` and ``world.load("house.schem",
position)`` do the same through the `Iwb` object.

A schematic's blocks are a numpy array of `mciwb.builders.BlockState`,
indexed ``[x][y][z]`` from its bottom north west corner, the same as the
cuboids of ``Item`` that ``grab`` returns. Convert with
``Schematic.from_cuboid(cuboid)`` and ``schematic.to_cuboid()``. ``rotate``
and ``mirror`` turn the block states with the blocks: stairs, doors, logs,
signs, fences, walls and rails all face the right way afterwards.

Reading the world back is slow: one RCON command per block, plus a few more
to find the ``facing``, ``half``, ``shape``, ``type`` and ``axis`` of stairs,
slabs and log-like blocks. Other block states (the facing of a door or a
furnace, say) cannot be read over RCON, so those blocks come back in their
default state. Block entity data (chest contents, sign text) is kept when
loading and saving files, but it is not pasted into the world, nor read from
it.
