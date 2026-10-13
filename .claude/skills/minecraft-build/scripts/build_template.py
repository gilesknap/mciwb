"""
Build a small stone hut with a door, windows and a slab roof.

A template for build scripts: copy it, set ORIGIN from the survey, replace
build() and check(), then run it with::

    mciwb run build.py

It clears the site, builds, then renders the result to a PNG beside this
script (read it to check the build) and checks the blocks in code. It
refuses to build over a player unless FORCE is set.
"""

from pathlib import Path

from mciwb.imports import (
    Direction,
    FillMode,
    Item,
    Player,
    Vec3,
    Volume,
    get_client,
    get_world,
)

# the north west corner of the floor: ground y + 1 from survey.py
ORIGIN = Vec3(632, 73, -1658)
# x (east), y (up), z (south): the space the build takes, cleared first
SIZE = Vec3(7, 6, 6)
# build even if a player stands in the build space
FORCE = False
# the render of the build, beside this script
PNG = Path(__file__).with_suffix(".png")


def players_inside(vol: Volume) -> list[str]:
    """the names of the players online in vol, or within 2 blocks of it"""
    names = [p.name for p in get_client().players.players]
    return [name for name in names if vol.inside(Player(name).pos, 2, 2, 2)]


def clear(vol: Volume) -> None:
    """replace everything in the build space with air"""
    vol.fill(get_client(), Item.AIR)


def build(origin: Vec3) -> None:
    """build the hut: replace this with your own build"""
    world = get_world()
    client = get_client()
    far = origin + SIZE - 1  # the south east top corner of the build space

    # a hollow box of cobblestone (HOLLOW fills its inside with air) gives
    # the walls, floor and ceiling in one command. One /fill places up to
    # 32768 blocks: far faster than a loop of set_block calls
    roof = far.y
    client.fill(origin, Vec3(far.x, roof - 1, far.z), Item.COBBLESTONE, FillMode.HOLLOW)
    # a plank floor inside the walls
    client.fill(
        origin + Vec3(1, 0, 1), Vec3(far.x - 1, origin.y, far.z - 1), Item.SPRUCE_PLANKS
    )
    # a roof of slabs, one block wider all round
    client.fill(
        Vec3(origin.x - 1, roof, origin.z - 1),
        Vec3(far.x + 1, roof, far.z + 1),
        Item.SPRUCE_SLAB,
    )

    # a door in the middle of the south wall, opening onto the outside
    middle_x = (origin.x + far.x) // 2
    world.place_door(
        Vec3(middle_x, origin.y + 1, far.z), Item.OAK_DOOR, Direction.SOUTH
    )
    # glass windows in the east and west walls
    for x in (origin.x, far.x):
        client.fill(
            Vec3(x, origin.y + 2, origin.z + 2),
            Vec3(x, origin.y + 2, far.z - 2),
            Item.GLASS_PANE,
        )
    # a lantern hanging from the middle of the ceiling
    world.set_block(
        Vec3(middle_x, roof - 2, (origin.z + far.z) // 2),
        Item.LANTERN,
        nbt=["hanging=true"],
    )


def check(vol: Volume) -> None:
    """render the build to PNG, and check it in code"""
    # include the roof overhang and a layer of the ground under the build
    low = vol.start - Vec3(1, 1, 1)
    high = vol.end + Vec3(1, 0, 1)
    grid = get_world().render(low, high, PNG, ["top", "iso", "south"])
    counts = grid.counts()
    print(f"rendered {PNG}: {counts}")

    far = vol.end
    start = vol.start
    assert grid[start + Vec3(1, 1, 1)] == "minecraft:air"
    assert grid[start + Vec3(1, 0, 1)] == "minecraft:spruce_planks"
    assert grid[start + Vec3(0, 1, 0)] == "minecraft:cobblestone"
    assert grid[Vec3(start.x, far.y, start.z)] == "minecraft:spruce_slab"
    assert counts["minecraft:spruce_slab"] == (SIZE.x + 2) * (SIZE.z + 2)
    assert counts["minecraft:oak_door"] == 2


def main() -> None:
    vol = Volume.from_corners(ORIGIN, ORIGIN + SIZE - 1)
    inside = players_inside(vol)
    if inside and not FORCE:
        raise SystemExit(f"{', '.join(inside)} inside {vol.start}..{vol.end}")
    clear(vol)
    build(ORIGIN)
    check(vol)


if __name__ == "__main__":
    main()
