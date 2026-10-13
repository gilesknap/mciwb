"""
The furniture of `house.medieval_house`, by its ``contents`` preset: a home,
or a shop (a counter on the ground floor with its keeper's workstation and
goods on shelves and in item frames, and the living room above), or the
tavern. Everything is drawn on the house's `Canvas`, in the house's own
frame (the street to the south), and placed only where the floor is free:
clear of the stairs, the ladder, the door's way in and the hearth.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from house import AIR, KEEPERS, Canvas, _chimney_cell, _Plan, _stairs_fit

# what each shop sells (on its shelves and in its frames), and its keeper's workstation
GOODS = {
    "baker": (
        ["bread", "cake", "cookie", "pumpkin_pie", "wheat"],
        "minecraft:composter",
    ),
    "butcher": (
        ["porkchop", "beef", "mutton", "chicken", "rabbit"],
        "minecraft:smoker[facing=south]",
    ),
    "tailor": (
        ["white_wool", "red_wool", "leather_chestplate", "shears", "string"],
        "minecraft:loom[facing=south]",
    ),
    "apothecary": (
        ["potion", "glass_bottle", "nether_wart", "redstone", "glowstone_dust"],
        "minecraft:brewing_stand",
    ),
    "candlemaker": (
        ["candle", "white_candle", "yellow_candle", "honeycomb", "red_candle"],
        "minecraft:beehive[facing=south]",
    ),
    "carpenter": (
        ["oak_planks", "iron_axe", "stick", "spruce_log", "oak_door"],
        "minecraft:stonecutter[facing=south]",
    ),
    "fletcher": (
        ["bow", "arrow", "feather", "flint", "crossbow"],
        "minecraft:fletching_table",
    ),
    "cartographer": (
        ["map", "compass", "paper", "filled_map", "spyglass"],
        "minecraft:cartography_table",
    ),
    "cobbler": (
        ["leather_boots", "leather", "rabbit_hide", "iron_boots", "chainmail_boots"],
        "minecraft:cauldron",
    ),
    "weaver": (
        ["white_wool", "blue_wool", "yellow_wool", "string", "white_carpet"],
        "minecraft:loom[facing=south]",
    ),
    "tavern": (
        ["honey_bottle", "potion", "bread", "cooked_beef", "apple"],
        "minecraft:barrel[facing=up]",
    ),
}
SHELF = "minecraft:spruce_shelf"
TABLE = "minecraft:spruce_slab[type=top]"  # a table top
SEAT = "minecraft:spruce_stairs"
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
STEP = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def _shelf(facing: str, items: list[str]) -> str:
    slots = ",".join(
        f'{{Slot:{k}b,id:"minecraft:{item}",count:1}}'
        for k, item in enumerate(items[:3])
    )
    return f"{SHELF}[facing={facing}]{{Items:[{slots}]}}"


class Room:
    """the free floor of one storey, and helpers to furnish it"""

    def __init__(self, c: Canvas, plan: _Plan, i: int, reserved: set[tuple[int, int]]):
        self.c, self.plan, self.i = c, plan, i
        x1, z1, x2, z2 = plan.rect(i)
        self.x1, self.z1, self.x2, self.z2 = x1 + 1, z1 + 1, x2 - 1, z2 - 1
        self.y = plan.stand(i)
        self.reserved = set(reserved)

    def free(self, x: int, z: int) -> bool:
        c, y = self.c, self.y
        return (
            self.x1 <= x <= self.x2
            and self.z1 <= z <= self.z2
            and (x, z) not in self.reserved
            and c.get(x, y, z) == AIR
            and c.get(x, y + 1, z) == AIR
            and c.get(x, y - 1, z) != AIR
        )

    def wall_side(self, x: int, z: int) -> str | None:
        """the side (north, south ...) on which (x, z) touches a wall"""
        for side, (dx, dz) in STEP.items():
            if not (self.x1 <= x + dx <= self.x2 and self.z1 <= z + dz <= self.z2):
                return side
        return None

    def cells(self, by_wall: bool | None = None) -> list[tuple[int, int]]:
        out = [
            (x, z)
            for z in range(self.z1, self.z2 + 1)
            for x in range(self.x1, self.x2 + 1)
            if self.free(x, z)
        ]
        if by_wall is not None:
            out = [p for p in out if (self.wall_side(*p) is not None) == by_wall]
        return out

    def put(self, x: int, z: int, state: str, h: int = 0) -> None:
        self.c.set(x, self.y + h, z, state)
        if h == 0:
            self.reserved.add((x, z))

    def against_wall(
        self, state: Callable[[str], str], n: int = 1
    ) -> list[tuple[int, int]]:
        """up to n blocks against the walls, each given the way it faces (away from its wall)"""
        placed = []
        for x, z in self.cells(by_wall=True):
            if len(placed) == n:
                break
            side = self.wall_side(x, z)
            if side is None or self.c.get(x, self.y + 1, z) != AIR:
                continue
            self.put(x, z, state(OPP[side]))
            placed.append((x, z))
        return placed


def _reserved(plan: _Plan, door_x: int, i: int) -> set[tuple[int, int]]:
    """the cells to keep clear on storey i: the way up and the way in"""
    out: set[tuple[int, int]] = set()
    if plan.n > 1 or i > 0:
        if _stairs_fit(plan):
            out |= {(x, z) for x in range(1, 7) for z in range(1, 4)}
        else:
            out |= {(1, 1), (1, 2), (2, 1), (2, 2)}
    cx, cz = _chimney_cell(plan)
    if i == 0:
        z = plan.rect(0)[3]
        out |= {
            (door_x, z - 1),
            (door_x, z - 2),
            (door_x - 1, z - 1),
            (door_x + 1, z - 1),
        }
        out |= {(cx - 1, cz), (cx - 1, cz + 1), (cx, cz + 1), (cx + 1, cz + 1)}
    out.add((cx, cz))
    return out


def furnish(
    c: Canvas, plan: _Plan, contents: str, door_x: int, info: dict, rng: random.Random
) -> None:
    """furnish every storey for ``contents``; records the stands and seats in info"""
    ground = Room(c, plan, 0, _reserved(plan, door_x, 0))
    if contents == "home":
        _living_room(ground, info, rng)
    elif contents == "tavern":
        _tavern(ground, info, rng)
    else:
        _shop(ground, contents, door_x, info, rng)
    for i in range(1, plan.n):
        room = Room(c, plan, i, _reserved(plan, door_x, i))
        if i == plan.n - 1 or i % 2 == 1:
            _bedroom(room, info, rng, first=i == 1)
        else:
            _living_room(room, info, rng)
    if plan.n == 1:  # a cottage: a bed downstairs too
        _bedroom(ground, info, rng, first=True)


def _table_with_seats(room: Room, info: dict, chairs: int = 2) -> bool:
    """a table (a top slab, at the height of the seats beside it, as the
    castle's tables are) in the open floor with seats either side looking
    at it; False if there is no room"""
    for x, z in room.cells(by_wall=False):
        sides = [
            (s, (x + dx, z + dz))
            for s, (dx, dz) in STEP.items()
            if room.free(x + dx, z + dz)
        ]
        if len(sides) < chairs:
            continue
        room.put(x, z, TABLE)
        used = [(x, z)]
        for side, (sx, sz) in sides[:chairs]:
            looks = OPP[side]  # the sitter looks back at the table
            room.put(sx, sz, f"{SEAT}[facing={OPP[looks]}]")
            info["seats"].append(((sx, room.y, sz), looks))
            used.append((sx, sz))
        # keep the next table and its seats a block away: no seat may have
        # its back to another table
        for ux, uz in used:
            room.reserved |= {
                (ux + dx, uz + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)
            }
        room.c.set(x, room.y + 1, z, "minecraft:candle[candles=2,lit=true]")
        return True
    return False


def _living_room(room: Room, info: dict, rng: random.Random) -> None:
    _table_with_seats(room, info, 2)
    room.against_wall(lambda f: f"minecraft:barrel[facing={f}]", 1)
    room.against_wall(
        lambda f: _shelf(
            f, rng.sample(["bread", "apple", "book", "flower_pot", "candle"], 3)
        ),
        1,
    )
    for x, z in room.cells(by_wall=False)[:1]:
        room.c.set(
            x,
            room.y,
            z,
            f"minecraft:{rng.choice(('brown', 'red', 'green', 'blue'))}_carpet",
        )


def _bedroom(room: Room, info: dict, rng: random.Random, first: bool) -> None:
    colour = rng.choice(("red", "blue", "green", "yellow", "white", "light_blue"))
    for x, z in room.cells(by_wall=True):
        # a bed along a wall: its head against it, its foot into the room
        side = room.wall_side(x, z)
        if side is None:
            continue
        dx, dz = STEP[OPP[side]]
        if not room.free(x + dx, z + dz):
            continue
        facing = side  # a bed faces its head
        room.put(x, z, f"minecraft:{colour}_bed[facing={facing},part=head]")
        room.put(x + dx, z + dz, f"minecraft:{colour}_bed[facing={facing},part=foot]")
        # where someone stands at the bedside
        for sdx, sdz in STEP.values():
            if room.free(x + dx + sdx, z + dz + sdz):
                key = "bed" if "bed" not in info["stands"] else f"bed{room.i}"
                info["stands"][key] = (x + dx + sdx, room.y, z + dz + sdz)
                break
        break
    room.against_wall(lambda f: f"minecraft:chest[facing={f}]", 1)
    room.against_wall(lambda f: f"minecraft:barrel[facing={f}]", 1)
    for x, z in room.cells(by_wall=False)[:2]:
        room.c.set(x, room.y, z, f"minecraft:{colour}_carpet")


def _shop(
    room: Room, contents: str, door_x: int, info: dict, rng: random.Random
) -> None:
    goods, station = GOODS[contents]
    front = room.plan.rect(0)[3]
    # the keeper stands behind the counter window, left of the door
    kx = max(room.x1, (room.x1 + door_x - 2) // 2)
    keeper = (kx, front - 1)
    room.reserved.add(keeper)
    info["stands"]["counter"] = (keeper[0], room.y, keeper[1])
    # the workstation beside the keeper
    for x, z in ((kx - 1, front - 1), (kx + 1, front - 1), (kx, front - 2)):
        if room.free(x, z) and x < door_x - 1:
            room.put(x, z, station)
            break
    # shelves of goods round the walls, a barrel and a chest of stock
    room.against_wall(lambda f: _shelf(f, rng.sample(goods, 3)), 3)
    room.against_wall(lambda f: f"minecraft:barrel[facing={f}]", 1)
    # goods in item frames on the back wall, above head height
    x1, z1, x2, _z2 = room.plan.rect(0)
    for k, x in enumerate(range(x1 + 2, x2 - 1, 3)):
        if room.c.get(x, room.y + 2, z1 + 1) == AIR and k < 2:
            info["frames"].append(
                ((x, room.y + 2, z1 + 1), "south", goods[k % len(goods)])
            )
    # the sign over the door is hung by house.py (it needs the facade)
    info["sign"] = contents


def _tavern(room: Room, info: dict, rng: random.Random) -> None:
    # barrels of ale along the back wall behind the bar
    room.against_wall(lambda f: f"minecraft:barrel[facing={f}]", 3)
    tables = 0
    while tables < 3 and _table_with_seats(room, info, 2):
        tables += 1
    cells = room.cells(by_wall=True)
    if cells:
        x, z = cells[0]
        room.reserved.add((x, z))
        info["stands"]["counter"] = (x, room.y, z)
    info["sign"] = "tavern"


KEEPER_OF = KEEPERS
