"""
Build a small cobblestone hut with a door, windows and a gable roof, on a
foundation that follows the ground.

A template for build scripts: copy it, set ORIGIN from the survey, replace
build() and check(), then run it with::

    mciwb run build.py

It clears the site, builds, then renders the result to a PNG beside this
script (read it to check the build) and checks the blocks in code, including
the facing of the roof's stairs (renders draw stairs as full blocks). It
refuses to build over a player unless FORCE is set.
"""

from pathlib import Path

from mciwb.imports import (
    Direction,
    Item,
    Player,
    Schematic,
    Vec3,
    Volume,
    foundation,
    gable_roof,
    get_client,
    get_world,
)

# the north west corner of the floor: the median ground y + 1 from survey.py.
# The foundation fills any dips under the floor down to the ground
ORIGIN = Vec3(632, 73, -1658)
# x (east), y (up), z (south): the space the build takes, cleared first
SIZE = Vec3(9, 9, 8)
# build even if a player stands in the build space
FORCE = False
# the render of the build, beside this script
PNG = Path(__file__).with_suffix(".png")


def players_inside(vol: Volume) -> list[str]:
    """the names of the players online in vol, or within 2 blocks of it"""
    names = [p.name for p in get_client().players.players]
    return [name for name in names if vol.inside(Player(name).pos, 2, 2, 2)]


def clear(vol: Volume) -> None:
    """replace everything in the build space with air: Volume.fill replaces
    every block, in boxes of any size"""
    vol.fill(get_client(), Item.AIR)


def build(origin: Vec3) -> Volume:
    """build the hut and return its roof: replace this with your own build"""
    world = get_world()
    client = get_client()
    far = origin + SIZE - 1  # the south east top corner of the build space

    # a level platform at origin.y over the whole site, filled down to the
    # ground in each column. Build it first: it takes whatever stands on the
    # site as the ground
    foundation(origin, Vec3(far.x, origin.y, far.z), Item.COBBLESTONE)

    # walls 4 high, one block in from the edge of the platform to leave room
    # for the roof's overhang. One /fill places up to 32768 blocks: far
    # faster than a loop of set_block calls
    walls = Volume.from_corners(
        origin + Vec3(1, 1, 1), Vec3(far.x - 1, origin.y + 4, far.z - 1)
    )
    walls.walls(client, Item.COBBLESTONE, top=False, bottom=False)
    # a plank floor inside the walls
    client.fill(
        origin + Vec3(2, 0, 2), Vec3(far.x - 2, origin.y, far.z - 2), Item.SPRUCE_PLANKS
    )
    # a gable roof on the walls (it starts one block above the corners given),
    # its ridge along the longer side, overhanging the walls by one block,
    # with planks filling the triangles at the ends
    roof = gable_roof(
        Vec3(walls.start.x, walls.end.y, walls.start.z),
        walls.end,
        Item.SPRUCE_STAIRS,
        gable=Item.SPRUCE_PLANKS,
        overhang=1,
    )

    # a door in the middle of the south wall, opening onto the outside
    middle_x = (origin.x + far.x) // 2
    world.place_door(
        Vec3(middle_x, origin.y + 1, walls.end.z), Item.OAK_DOOR, Direction.SOUTH
    )
    # glass windows in the east and west walls
    for x in (walls.start.x, walls.end.x):
        client.fill(
            Vec3(x, origin.y + 2, walls.start.z + 2),
            Vec3(x, origin.y + 3, walls.end.z - 2),
            Item.GLASS_PANE,
        )
    return roof


def check(vol: Volume, roof: Volume) -> None:
    """render the build to PNG, and check it in code"""
    # include a layer of the ground under the build
    low = vol.start + Direction.DOWN
    grid = get_world().render(low, vol.end, PNG, ["top", "iso", "south"])
    counts = grid.counts()
    print(f"rendered {PNG}: {counts}")

    inside = vol.start + Vec3(2, 1, 2)
    assert grid[inside] == "minecraft:air"
    assert grid[inside + Direction.DOWN] == "minecraft:spruce_planks"
    assert grid[vol.start + Vec3(1, 1, 1)] == "minecraft:cobblestone"
    assert counts["minecraft:oak_door"] == 2
    assert roof.end.y <= vol.end.y, "the roof is taller than SIZE"

    # renders draw stairs as full blocks, so read back a row of the roof to
    # check which way its stairs face (stairs face the way you walk up them).
    # This costs a few RCON commands per block: keep the region small
    middle_x = (vol.start.x + vol.end.x) // 2
    row = Volume.from_corners(
        Vec3(middle_x, roof.start.y, roof.start.z),
        Vec3(middle_x, roof.start.y, roof.end.z),
    )
    eaves = Schematic.from_world(row).blocks[0, 0]
    print("lowest row of the roof, north to south: " + ", ".join(map(str, eaves)))
    assert eaves[0].props["facing"] == "south"
    assert eaves[-1].props["facing"] == "north"


def main() -> None:
    vol = Volume.from_corners(ORIGIN, ORIGIN + SIZE - 1)
    inside = players_inside(vol)
    if inside and not FORCE:
        raise SystemExit(f"{', '.join(inside)} inside {vol.start}..{vol.end}")
    clear(vol)
    roof = build(ORIGIN)
    check(vol, roof)


if __name__ == "__main__":
    main()
