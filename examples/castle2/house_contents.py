"""
The furniture of `house.medieval_house`, by its ``contents`` preset: a home
(a kitchen and a table by the hearth, bedrooms above), a shop (a counter on
the ground floor with its keeper's workstation, the tools of the trade and
goods on shelves and in item frames, a workshop and the living rooms
above), or the tavern (a bar with kegs, tables with seats, rooms for
lodgers upstairs). Every storey is furnished.

Everything is drawn on the house's `Canvas`, in the house's own frame (the
street to the south). A `Room` places a piece only where the floor is free
and only if the room's key cells (the way in from the door or the stairs,
the stands) stay joined on foot and every piece placed before can still be
reached, so furniture never blocks a way through.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence

from house import (
    AIR,
    LANTERN,
    OPP,
    STEP,
    Canvas,
    _Plan,
    passable,
)

TABLE = "minecraft:spruce_slab[type=top]"  # a table top, at seat height
SEAT = "minecraft:spruce_stairs"
SHELF = "minecraft:spruce_shelf"
PARTITION = "minecraft:spruce_planks"
COLOURS = ("red", "blue", "green", "yellow", "white", "light_blue", "orange", "cyan")
RUGS = ("red", "brown", "green", "blue", "cyan", "purple", "gray", "orange")
ON_TABLE = (
    "minecraft:candle[candles=3,lit=true]",
    "minecraft:cake",
    "minecraft:potted_red_tulip",
    "minecraft:white_candle[candles=2,lit=true]",
    "minecraft:potted_azure_bluet",
)

# each shop: the goods it sells (shelves and frames), its keeper's
# workstation, and the tools of its trade (``{f}``: the way a block faces)
TRADES: dict[str, dict] = {
    "baker": {
        "goods": ["bread", "cake", "cookie", "pumpkin_pie", "wheat"],
        "station": "minecraft:composter",
        "tools": [
            "minecraft:furnace[facing={f},lit=true]",
            "minecraft:smoker[facing={f}]",
            "minecraft:hay_block",
        ],
        "workshop": [
            "minecraft:hay_block",
            "minecraft:barrel[facing={f}]",
            "minecraft:furnace[facing={f}]",
            "minecraft:crafting_table",
        ],
    },
    "butcher": {
        "goods": ["porkchop", "beef", "mutton", "chicken", "rabbit"],
        "station": "minecraft:smoker[facing={f}]",
        "tools": [
            "minecraft:stripped_oak_log[axis=y]",
            "minecraft:barrel[facing={f}]",
            "minecraft:water_cauldron[level=3]",
        ],
        "workshop": [
            "minecraft:smoker[facing={f}]",
            "minecraft:barrel[facing={f}]",
            "minecraft:barrel[facing=up]",
        ],
    },
    "tailor": {
        "goods": ["white_wool", "red_wool", "leather_chestplate", "shears", "string"],
        "station": "minecraft:loom[facing={f}]",
        "tools": [
            "minecraft:white_wool",
            "minecraft:red_wool",
            "minecraft:chest[facing={f}]",
        ],
        "workshop": [
            "minecraft:loom[facing={f}]",
            "minecraft:blue_wool",
            "minecraft:yellow_wool",
            "minecraft:crafting_table",
        ],
    },
    "apothecary": {
        "goods": [
            "potion",
            "glass_bottle",
            "nether_wart",
            "redstone",
            "glowstone_dust",
        ],
        "station": "minecraft:brewing_stand",
        "tools": [
            "minecraft:water_cauldron[level=3]",
            "minecraft:potted_fern",
            "minecraft:barrel[facing={f}]",
        ],
        "workshop": [
            "minecraft:brewing_stand",
            "minecraft:cauldron",
            "minecraft:potted_brown_mushroom",
            "minecraft:chest[facing={f}]",
        ],
    },
    "candlemaker": {
        "goods": ["candle", "white_candle", "yellow_candle", "honeycomb", "red_candle"],
        "station": "minecraft:beehive[facing={f}]",
        "tools": [
            "minecraft:honeycomb_block",
            "minecraft:cauldron",
            "minecraft:barrel[facing={f}]",
        ],
        "workshop": [
            "minecraft:beehive[facing={f}]",
            "minecraft:honeycomb_block",
            "minecraft:crafting_table",
        ],
    },
    "carpenter": {
        "goods": ["oak_planks", "iron_axe", "stick", "spruce_log", "oak_door"],
        "station": "minecraft:stonecutter[facing={f}]",
        "tools": [
            "minecraft:crafting_table",
            "minecraft:oak_log[axis=y]",
            "minecraft:grindstone[face=floor,facing={f}]",
        ],
        "workshop": [
            "minecraft:spruce_log[axis=y]",
            "minecraft:oak_planks",
            "minecraft:crafting_table",
            "minecraft:barrel[facing={f}]",
        ],
    },
    "fletcher": {
        "goods": ["bow", "arrow", "feather", "flint", "crossbow"],
        "station": "minecraft:fletching_table",
        "tools": [
            "minecraft:target",
            "minecraft:hay_block",
            "minecraft:barrel[facing={f}]",
        ],
        "workshop": [
            "minecraft:fletching_table",
            "minecraft:target",
            "minecraft:crafting_table",
        ],
    },
    "cartographer": {
        "goods": ["map", "compass", "paper", "filled_map", "spyglass"],
        "station": "minecraft:cartography_table",
        "tools": [
            "minecraft:bookshelf",
            "minecraft:chest[facing={f}]",
            "minecraft:bookshelf",
        ],
        "workshop": [
            "minecraft:cartography_table",
            "minecraft:bookshelf",
            "minecraft:bookshelf",
            "minecraft:chest[facing={f}]",
        ],
    },
    "cobbler": {
        "goods": [
            "leather_boots",
            "leather",
            "rabbit_hide",
            "iron_boots",
            "chainmail_boots",
        ],
        "station": "minecraft:cauldron",
        "tools": [
            "minecraft:crafting_table",
            "minecraft:barrel[facing={f}]",
            "minecraft:chest[facing={f}]",
        ],
        "workshop": [
            "minecraft:cauldron",
            "minecraft:crafting_table",
            "minecraft:barrel[facing={f}]",
        ],
    },
    "weaver": {
        "goods": ["white_wool", "blue_wool", "yellow_wool", "string", "white_carpet"],
        "station": "minecraft:loom[facing={f}]",
        "tools": [
            "minecraft:loom[facing={f}]",
            "minecraft:white_wool",
            "minecraft:light_blue_wool",
        ],
        "workshop": [
            "minecraft:loom[facing={f}]",
            "minecraft:loom[facing={f}]",
            "minecraft:white_wool",
            "minecraft:chest[facing={f}]",
        ],
    },
}
KITCHEN = (
    "minecraft:smoker[facing={f}]",
    "minecraft:furnace[facing={f}]",
    "minecraft:barrel[facing={f}]",
    "minecraft:water_cauldron[level=3]",
    "minecraft:crafting_table",
    "minecraft:composter",
)
PANTRY = ["bread", "apple", "carrot", "potato", "beetroot", "cookie", "pumpkin_pie"]
BOOKS = ["book", "writable_book", "candle", "flower_pot", "clock", "compass"]
BOTTLES = ["honey_bottle", "potion", "glass_bottle", "experience_bottle"]


def _shelf(facing: str, items: list[str]) -> str:
    slots = ",".join(
        f'{{Slot:{k}b,id:"minecraft:{item}",count:1}}'
        for k, item in enumerate(items[:3])
    )
    return f"{SHELF}[facing={facing}]{{Items:[{slots}]}}"


Cell = tuple[int, int]


class Room:
    """
    The floor of one storey (or of a room on it), and how to furnish it.

    ``keys`` are the cells that must stay joined on foot (the first is
    where the walk starts), ``core`` cells are never furnished (the stairs,
    rails, the hearth, the landing).
    """

    def __init__(
        self,
        c: Canvas,
        plan: _Plan,
        i: int,
        keys: Iterable[Cell],
        core: Iterable[Cell] = (),
        bounds: tuple[int, int, int, int] | None = None,
    ):
        self.c, self.plan, self.i = c, plan, i
        self.x1, self.z1, self.x2, self.z2 = bounds or plan.inner(i)
        self.y = plan.stand(i)
        self.keys = list(dict.fromkeys(keys))
        self.core = set(core)
        self.reserved = set(core) | set(self.keys)
        self.access: list[list[Cell]] = []  # pieces that need a free side
        self.behind_seats: set[Cell] = set()  # no table may stand here
        self.tables: list[Cell] = []
        self.lit: list[Cell] = []
        self.pieces = 0

    # ---- the floor
    def inside(self, x: int, z: int) -> bool:
        return self.x1 <= x <= self.x2 and self.z1 <= z <= self.z2

    def walkable(self, x: int, z: int) -> bool:
        c, y = self.c, self.y
        return (
            self.inside(x, z)
            and passable(c.get(x, y, z))
            and passable(c.get(x, y + 1, z))
            and not passable(c.get(x, y - 1, z))
        )

    def free(self, x: int, z: int) -> bool:
        """free floor that may be furnished"""
        return (x, z) not in self.reserved and self.walkable(x, z)

    def reach(self, blocked: set[Cell]) -> set[Cell]:
        if not self.keys:
            return set()
        start = self.keys[0]
        seen, todo = {start}, [start]
        while todo:
            x, z = todo.pop()
            for dx, dz in STEP.values():
                q = (x + dx, z + dz)
                if q not in seen and q not in blocked and self.walkable(*q):
                    seen.add(q)
                    todo.append(q)
        return seen

    def ok(self, blocked: set[Cell], need: list[list[Cell]] | None = None) -> bool:
        """do the keys stay joined, and every piece reachable (and the new
        ones: ``need``, default all the blocked cells as one), with these
        cells blocked?"""
        if blocked & set(self.keys):
            return False
        r = self.reach(blocked)
        if not all(k in r for k in self.keys):
            return False
        for group in self.access + (need if need is not None else [sorted(blocked)]):
            if not any(
                (x + dx, z + dz) in r for x, z in group for dx, dz in STEP.values()
            ):
                return False
        return True

    def wall_side(self, x: int, z: int) -> str | None:
        """the side (north, south ...) on which (x, z) touches a wall"""
        for side, (dx, dz) in STEP.items():
            if not self.inside(x + dx, z + dz):
                return side
        return None

    def corner(self, x: int, z: int) -> bool:
        return sum(not self.inside(x + dx, z + dz) for dx, dz in STEP.values()) >= 2

    def cells(self, by_wall: bool | None = None, rng=None) -> list[Cell]:
        out = [
            (x, z)
            for z in range(self.z1, self.z2 + 1)
            for x in range(self.x1, self.x2 + 1)
            if self.free(x, z)
        ]
        if by_wall is not None:
            out = [p for p in out if (self.wall_side(*p) is not None) == by_wall]
        if rng is not None:
            rng.shuffle(out)
        return out

    # ---- placing
    def put(
        self,
        items: list[tuple[int, int, str, int]],
        access: bool = True,
        check: bool = True,
        need: list[list[Cell]] | None = None,
    ) -> bool:
        """place (x, z, state, h) items at once if their floor cells are
        free and the room stays walkable (``need``: groups of cells that
        must each be reachable); h is the height above the floor"""
        base = {(x, z) for x, z, s, h in items if h == 0}
        if not all(self.free(*p) for p in base):
            return False
        blocked = {(x, z) for x, z, s, h in items if h == 0 and not passable(s)}
        if check and blocked and not self.ok(blocked, need):
            return False
        for x, z, s, h in items:
            self.c.set(x, self.y + h, z, s)
        self.reserved |= base
        if access and blocked:
            self.access.append(sorted(blocked))
        self.pieces += 1
        return True

    def along_wall(
        self, states: Sequence[str], rng: random.Random, gap: bool = False
    ) -> list[Cell]:
        """a run of blocks side by side against one wall, each facing into
        the room (``{f}`` in a state); the cells used"""
        n = len(states)
        for x, z in self.cells(by_wall=True, rng=rng):
            side = self.wall_side(x, z)
            assert side is not None
            # run along the wall, perpendicular to the way out
            ax, az = (1, 0) if side in ("north", "south") else (0, 1)
            run = [(x + ax * k, z + az * k) for k in range(n)]
            if not all(self.wall_side(*p) == side for p in run):
                continue
            f = OPP[side]
            if self.put(
                [
                    (px, pz, s.replace("{f}", f), 0)
                    for (px, pz), s in zip(run, states, strict=True)
                ]
            ):
                return run
        return []

    def against_wall(self, state: str, rng: random.Random, h: int = 1) -> Cell | None:
        """a block (h high) against a wall, facing into the room"""
        for x, z in self.cells(by_wall=True, rng=rng):
            side = self.wall_side(x, z)
            assert side is not None
            if any(self.c.get(x, self.y + k, z) != AIR for k in range(h)):
                continue
            s = state.replace("{f}", OPP[side])
            if self.put([(x, z, s, k) for k in range(h)]):
                return (x, z)
        return None

    def shelves_above(self, cells: list[Cell], items: list[str], rng) -> None:
        """a shelf of items on the wall over each low piece against a wall"""
        for x, z in cells:
            side = self.wall_side(x, z)
            if side is None or self.c.get(x, self.y + 1, z) != AIR:
                continue
            if passable(self.c.get(x, self.y, z)):
                continue
            self.c.set(x, self.y + 1, z, _shelf(OPP[side], rng.sample(items, 3)))

    @staticmethod
    def seat(x: int, z: int, looks: str) -> tuple[int, int, str, int]:
        """a seat (a stair, its back behind the sitter) looking ``looks``"""
        return (x, z, f"{SEAT}[facing={OPP[looks]},half=bottom]", 0)

    def seated(self, info: dict, x: int, z: int, looks: str) -> None:
        """record a placed seat: its sitter must reach it, and no table may
        stand behind it"""
        info["seats"].append(((x, self.y, z), looks))
        self.access.append([(x, z)])
        dx, dz = STEP[OPP[looks]]
        self.behind_seats.add((x + dx, z + dz))

    def table(
        self,
        info: dict,
        rng: random.Random,
        seats: int = 2,
        at_wall: bool | None = None,
        cells: list[Cell] | None = None,
    ) -> Cell | None:
        """a table with up to ``seats`` seats round it (at least one), each
        looking at it; no seat has its back to another table"""
        candidates = cells if cells is not None else self.cells(at_wall, rng)
        for want in range(seats, 0, -1):
            for x, z in candidates:
                if not self.free(x, z) or (x, z) in self.behind_seats:
                    continue
                sides = []
                for side, (dx, dz) in STEP.items():
                    sx, sz = x + dx, z + dz
                    back = (sx + dx, sz + dz)
                    if (
                        self.free(sx, sz)
                        and back not in self.tables
                        and not self._table_at(*back)
                    ):
                        sides.append((side, sx, sz))
                if len(sides) < want:
                    continue
                rng.shuffle(sides)
                chosen = sides[:want]
                items = [(x, z, TABLE, 0)]
                items += [self.seat(sx, sz, OPP[side]) for side, sx, sz in chosen]
                need = [[(sx, sz)] for _side, sx, sz in chosen]
                if not self.put(items, access=False, need=need):
                    continue
                for side, sx, sz in chosen:
                    self.seated(info, sx, sz, OPP[side])
                self.tables.append((x, z))
                self.c.set(x, self.y + 1, z, rng.choice(ON_TABLE))
                return (x, z)
        return None

    def _table_at(self, x: int, z: int) -> bool:
        return self.c.get(x, self.y, z) == TABLE

    def bed(
        self, info: dict, rng: random.Random, colour: str, stand: str | None = "bed"
    ) -> bool:
        """a bed, its head against a wall, with a side table (a candle or a
        flower on it) beside its head, and a chest at its foot if there is room"""
        for x, z in self.cells(by_wall=True, rng=rng):
            side = self.wall_side(x, z)
            assert side is not None
            dx, dz = STEP[OPP[side]]
            fx, fz = x + dx, z + dz
            if not self.free(fx, fz) or self.wall_side(fx, fz) == OPP[side]:
                continue
            items = [
                (x, z, f"minecraft:{colour}_bed[facing={side},part=head]", 0),
                (fx, fz, f"minecraft:{colour}_bed[facing={side},part=foot]", 0),
            ]
            if not self.put(items):
                continue
            # a side table beside the head, against the same wall
            ax, az = (1, 0) if side in ("north", "south") else (0, 1)
            for k in (1, -1):
                tx, tz = x + ax * k, z + az * k
                if self.wall_side(tx, tz) == side and self.put(
                    [
                        (tx, tz, TABLE, 0),
                        (
                            tx,
                            tz,
                            rng.choice(ON_TABLE[::2] + (f"{LANTERN}[hanging=false]",)),
                            1,
                        ),
                    ],
                    access=False,
                ):
                    self.tables.append((tx, tz))
                    break
            # a chest at the foot
            cx, cz = fx + dx, fz + dz
            self.put([(cx, cz, f"minecraft:chest[facing={OPP[side]}]", 0)])
            if stand:
                reach = self.reach(set())
                for sdx, sdz in STEP.values():
                    p = (fx + sdx, fz + sdz)
                    if self.free(*p) and p in reach:
                        key = (
                            stand if stand not in info["stands"] else f"{stand}{self.i}"
                        )
                        info["stands"][key] = (p[0], self.y, p[1])
                        self.reserved.add(p)
                        self.keys.append(p)
                        break
            return True
        return False

    def wardrobe(self, rng: random.Random) -> bool:
        """a wardrobe: two stacked barrels against a wall, a shelf of hats
        and books over it"""
        cell = self.against_wall("minecraft:barrel[facing={f}]", rng, h=2)
        if cell is None:
            return False
        side = self.wall_side(*cell)
        assert side is not None
        x, z = cell
        if self.c.get(x, self.y + 2, z) == AIR:
            self.c.set(
                x,
                self.y + 2,
                z,
                _shelf(OPP[side], ["leather_helmet", "book", "white_wool"]),
            )
        return True

    def rug(self, colour: str, size: int = 2) -> None:
        """a carpet rug on the open floor, round the room's middle"""
        mx, mz = (self.x1 + self.x2) // 2, (self.z1 + self.z2) // 2
        cells = sorted(
            self.cells(by_wall=False),
            key=lambda p: abs(p[0] - mx) + abs(p[1] - mz),
        )
        laid = 0
        for x, z in cells:
            if abs(x - mx) <= size and abs(z - mz) <= size - 1:
                self.c.set(x, self.y, z, f"minecraft:{colour}_carpet")
                self.reserved.add((x, z))
                laid += 1
        if laid:
            self.pieces += 1

    def lights(self, n: int = 1) -> None:
        """lanterns hanging from the ceiling: over the tables, else over the
        middle of the room, never over a way through or the stairs"""
        spots = list(self.tables)
        mx, mz = (self.x1 + self.x2) // 2, (self.z1 + self.z2) // 2
        spots += sorted(
            (
                (x, z)
                for x in range(self.x1, self.x2 + 1)
                for z in range(self.z1, self.z2 + 1)
            ),
            key=lambda p: abs(p[0] - mx) + abs(p[1] - mz),
        )
        hung = 0
        for x, z in spots:
            if hung == n:
                break
            if (x, z) in self.keys or (x, z) in self.core:
                continue
            y = self.y + 2
            if self.c.get(x, y, z) != AIR or self.c.get(x, y + 1, z) == AIR:
                continue
            if any(abs(x - tx) + abs(z - tz) < 3 for tx, tz in self.lit):
                continue
            self.c.set(x, y, z, f"{LANTERN}[hanging=true]")
            self.lit.append((x, z))
            hung += 1

    def frames(self, info: dict, items: list[str], n: int = 2) -> None:
        """goods in item frames on the walls, above head height"""
        y = self.y + 2
        hung = 0
        for x in range(self.x1, self.x2 + 1):
            for z in range(self.z1, self.z2 + 1):
                side = self.wall_side(x, z)
                if hung == n or side is None or self.c.get(x, y, z) != AIR:
                    continue
                dx, dz = STEP[side]
                wall = self.c.get(x + dx, y, z + dz)
                if passable(wall) or "pane" in wall or "door" in wall:
                    continue
                if (x - self.x1 + z - self.z1) % 3:
                    continue
                info["frames"].append(((x, y, z), OPP[side], items[hung % len(items)]))
                hung += 1


def _room(c: Canvas, plan: _Plan, i: int, keys, core, bounds=None) -> Room:
    return Room(c, plan, i, keys, core, bounds)


# ---------------------------------------------------------------- the presets


def furnish(
    c: Canvas, plan: _Plan, contents: str, door_x: int, info: dict, rng: random.Random
) -> None:
    """furnish every storey for ``contents``; records the stands, seats,
    frames and the clue spot in info"""
    front = plan.rect(0)[3]
    door_in = (door_x, front - 1)
    ground = _room(c, plan, 0, [door_in] + info["keys"][0], info["core"][0])
    # keep the way in from the door clear
    ground.reserved.add((door_x, front - 2))
    if contents == "home":
        info["clue"] = _clue_spot(ground, door_in)
        _hall(ground, info, rng, cottage=plan.n == 1)
    elif contents == "tavern":
        _tavern(ground, info, rng)
    else:
        _shop(ground, contents, info, rng)
    if info["clue"] is None:
        info["clue"] = _clue_spot(ground, door_in)
    _fill(ground, rng)
    for i, role in enumerate(_roles(contents, plan.n), start=1):
        room = _room(c, plan, i, info["keys"][i], info["core"][i])
        if role == "lodgings":
            _lodgings(room, info, rng)
        elif role == "children":
            _bedroom(room, info, rng, beds=2, desk=False)
        elif role == "parlour":
            _parlour(room, info, rng)
        elif role == "workshop":
            _workshop(room, contents, info, rng)
        else:
            _bedroom(room, info, rng, beds=1, desk=True)
        _fill(room, rng)


def _roles(contents: str, n: int) -> list[str]:
    """what each upper storey is"""
    if n == 1:
        return []
    if contents == "tavern":
        return ["lodgings"] * (n - 2) + (["innkeeper"] if n > 2 else ["lodgings"])
    if contents == "home":
        return {2: ["bedroom"], 3: ["bedroom", "children"]}.get(
            n, ["parlour", "bedroom", "children"]
        )
    return {2: ["bedroom"], 3: ["workshop", "bedroom"]}.get(
        n, ["parlour", "workshop", "bedroom"]
    )


def _fill(room: Room, rng: random.Random) -> None:
    """the last touches: a rug, a lantern"""
    room.rug(rng.choice(RUGS), 2 if room.x2 - room.x1 >= 5 else 1)
    room.lights(2 if (room.x2 - room.x1) * (room.z2 - room.z1) > 30 else 1)


def _clue_spot(room: Room, door_in: Cell) -> Cell | None:
    """a free floor cell against a wall where a lectern blocks nothing: not
    a key, not by the door; corners first, far from the door"""
    best = None
    for x, z in room.cells(by_wall=True):
        if abs(x - door_in[0]) + abs(z - door_in[1]) <= 1:
            continue
        if not room.ok({(x, z)}):
            continue
        score = (room.corner(x, z), abs(x - door_in[0]) + abs(z - door_in[1]))
        if best is None or score > best[0]:
            best = (score, (x, z))
    if best is None:
        return None
    spot = best[1]
    room.reserved.add(spot)
    room.access.append([spot])
    return spot


def _hall(room: Room, info: dict, rng: random.Random, cottage: bool) -> None:
    """a home's ground floor: a kitchen along a wall with a shelf of food,
    a table with seats by the hearth, a chest, a bookshelf"""
    kitchen = rng.sample(KITCHEN, 3)
    run = room.along_wall(kitchen, rng) or room.along_wall(kitchen[:2], rng)
    room.shelves_above(run, PANTRY, rng)
    if not room.table(info, rng, seats=4, at_wall=False):
        room.table(info, rng, seats=2)
    room.against_wall("minecraft:chest[facing={f}]", rng)
    if cottage:
        room.bed(info, rng, rng.choice(COLOURS))
    room.against_wall("minecraft:bookshelf", rng)
    room.against_wall("minecraft:barrel[facing={f}]", rng)


def _shop(room: Room, contents: str, info: dict, rng: random.Random) -> None:
    """a shop's ground floor: the keeper behind the counter window with the
    workstation beside them, the tools of the trade, shelves of goods, a
    chest of stock, goods in frames"""
    trade = TRADES[contents]
    front = room.plan.rect(0)[3]
    door_x = room.keys[0][0]
    kx = max(room.x1, (room.x1 + door_x - 2) // 2)
    keeper = (kx, front - 1)
    info["stands"]["counter"] = (keeper[0], room.y, keeper[1])
    room.keys.append(keeper)
    room.reserved.add(keeper)
    beside = [(kx + 1, front - 1), (kx - 1, front - 1), (kx, front - 2)]
    if contents == "cartographer":
        # the clue goes on the counter, beside the keeper
        for p in beside[:2]:
            if room.free(*p) and room.ok({p}):
                info["clue"] = p
                room.reserved.add(p)
                room.access.append([p])
                break
    station = trade["station"].replace("{f}", "south")
    for p in beside:
        if room.put([(p[0], p[1], station, 0)]):
            break
    if info["clue"] is None:
        info["clue"] = _clue_spot(room, room.keys[0])
    run = room.along_wall(list(trade["tools"]), rng) or room.along_wall(
        list(trade["tools"][:2]), rng
    )
    room.shelves_above(run, trade["goods"], rng)
    for _ in range(2):
        cell = room.against_wall(_shelf("{f}", rng.sample(trade["goods"], 3)), rng)
        if cell is None:
            break
    room.against_wall("minecraft:chest[facing={f}]", rng)
    room.frames(info, trade["goods"], 3)
    room.table(info, rng, seats=1, at_wall=True)  # a bench for a customer
    info["sign"] = contents


def _tavern(room: Room, info: dict, rng: random.Random) -> None:
    """the tavern: a bar along a side wall (kegs against the wall, the
    innkeeper behind a counter with stools before it), the drunk's table
    by a wall with the clue spot beside it, more tables, the hearth"""
    hearth_on_back = room.plan.w >= 10
    wall_x = room.x2 if hearth_on_back else room.x1 + 0
    inward = -1 if hearth_on_back else 1
    z_a, z_b = 3, room.z2 - 1
    if not hearth_on_back:
        z_a = 4  # clear of the stairs on the left
    kx, bx, cx = wall_x, wall_x + inward, wall_x + 2 * inward
    looks_wall = "east" if inward == -1 else "west"
    items = []
    for z in range(z_a, z_b + 1):
        items.append((kx, z, f"minecraft:barrel[facing={OPP[looks_wall]}]", 0))
        items.append((kx, z, f"minecraft:barrel[facing={OPP[looks_wall]}]", 1))
        if z > z_a:
            items.append((cx, z, TABLE, 0))
    if not room.put(items, access=False, check=False):
        raise ValueError("the tavern's bar does not fit")
    for z in range(z_a, z_b + 1):
        if room.c.get(kx, room.y + 2, z) == AIR:
            room.c.set(
                kx, room.y + 2, z, _shelf(OPP[looks_wall], rng.sample(BOTTLES, 3))
            )
    for z in range(z_a + 1, z_b + 1):
        room.tables.append((cx, z))
        room.c.set(
            cx, room.y + 1, z, "minecraft:candle[candles=1,lit=true]" if z % 2 else AIR
        )
    keep = (bx, (z_a + z_b) // 2)
    info["stands"]["counter"] = (keep[0], room.y, keep[1])
    room.keys.append(keep)
    room.reserved |= {(bx, z) for z in range(z_a, z_b + 1)} | {(cx, z_a)}
    # the drunk's table against the wall opposite the bar, the clue beside it
    _drunks_table(room, info, rng, "west" if hearth_on_back else "east")
    # stools at the bar, looking at the counter
    stools = 0
    for z in range(z_a + 1, z_b + 1, 2):
        sx = cx + inward
        if stools < 2 and room.put([room.seat(sx, z, looks_wall)], need=[[(sx, z)]]):
            room.seated(info, sx, z, looks_wall)
            stools += 1
    tables = 0
    while tables < 3 and room.table(info, rng, seats=3 if tables else 4, at_wall=False):
        tables += 1
    room.against_wall("minecraft:barrel[facing=up]", rng)
    info["sign"] = "tavern"


def _drunks_table(room: Room, info: dict, rng: random.Random, wall: str) -> None:
    """a table against ``wall`` with a seat before it, and a free cell
    beside it along the wall for the drunk's book (the clue spot)"""
    dx, dz = STEP[OPP[wall]]  # into the room
    ax, az = (0, 1) if wall in ("east", "west") else (1, 0)
    for x, z in room.cells(by_wall=True, rng=rng):
        if room.wall_side(x, z) != wall:
            continue
        sx, sz = x + dx, z + dz
        for k in (1, -1):
            clue = (x + ax * k, z + az * k)
            if room.wall_side(*clue) != wall or not room.free(*clue):
                continue
            if not room.free(sx, sz) or not room.ok({(x, z), (sx, sz), clue}):
                continue
            if room.put(
                [(x, z, TABLE, 0), room.seat(sx, sz, wall)],
                access=False,
                need=[[(sx, sz)], [clue]],
            ):
                room.seated(info, sx, sz, wall)
                room.access.append([clue])
                room.tables.append((x, z))
                room.c.set(x, room.y + 1, z, "minecraft:candle[candles=1,lit=true]")
                info["clue"] = clue
                room.reserved.add(clue)
                return


def _bedroom(room: Room, info: dict, rng: random.Random, beds: int, desk: bool) -> None:
    """beds with side tables and chests, a wardrobe, a desk with a seat"""
    colour = rng.choice(COLOURS)
    for k in range(beds):
        room.bed(
            info,
            rng,
            colour if k == 0 else rng.choice(COLOURS),
            "bed" if k == 0 else None,
        )
    room.wardrobe(rng)
    if desk:
        room.table(info, rng, seats=1, at_wall=True)
    room.against_wall("minecraft:bookshelf", rng)
    room.against_wall("minecraft:potted_oxeye_daisy", rng)


def _parlour(room: Room, info: dict, rng: random.Random) -> None:
    """a sitting room: a table with seats, bookshelves, a barrel, shelves"""
    if not room.table(info, rng, seats=4, at_wall=False):
        room.table(info, rng, seats=2)
    run = room.along_wall(["minecraft:bookshelf", "minecraft:bookshelf"], rng)
    room.shelves_above(run, BOOKS, rng)
    cell = room.against_wall("minecraft:barrel[facing={f}]", rng)
    room.shelves_above([cell] if cell else [], PANTRY, rng)
    room.against_wall("minecraft:potted_red_tulip", rng)


def _workshop(room: Room, contents: str, info: dict, rng: random.Random) -> None:
    """the shop's workshop: the tools of the trade, a workbench with a seat,
    a chest of stock"""
    trade = TRADES[contents]
    run = room.along_wall(list(trade["workshop"]), rng) or room.along_wall(
        list(trade["workshop"][:2]), rng
    )
    room.shelves_above(run, trade["goods"], rng)
    if not room.table(info, rng, seats=2, at_wall=False):
        room.table(info, rng, seats=1)
    room.against_wall("minecraft:chest[facing={f}]", rng)
    room.against_wall("minecraft:barrel[facing={f}]", rng)
    room.frames(info, trade["goods"], 1)


def _lodgings(room: Room, info: dict, rng: random.Random) -> None:
    """rooms for lodgers: a passage behind a plank partition with a door
    into each room, a bed, side table and chest in each; in a small house,
    beds in one room"""
    x1, x2, z2 = room.x1, room.x2, room.z2
    zp = 5  # the partition: the passage is rows 3..4, in front of the stairs
    width = x2 - x1 + 1
    if width < 7 or z2 - zp < 3:
        _bedroom(room, info, rng, beds=3, desk=True)
        return
    n = max(2, (width + 1) // 5)
    w = (width - (n - 1)) // n
    rooms, x = [], x1
    for k in range(n):
        rx2 = x + w - 1 if k < n - 1 else x2
        rooms.append((x, rx2))
        x = rx2 + 2
    c, y = room.c, room.y
    for h in range(3):
        for x in range(x1, x2 + 1):
            c.set(x, y + h, zp, PARTITION)
        for _a, b in rooms[:-1]:
            for z in range(zp + 1, z2 + 1):
                c.set(b + 1, y + h, z, PARTITION)
    doors = []
    for a, b in rooms:
        dx = (a + b) // 2
        c.set(dx, y, zp, "minecraft:spruce_door[facing=north,half=lower,hinge=left]")
        c.set(
            dx, y + 1, zp, "minecraft:spruce_door[facing=north,half=upper,hinge=left]"
        )
        doors.append(dx)
    # the passage: the stairs' landing joined to every door
    passage = _room(
        c,
        room.plan,
        room.i,
        room.keys + [(dx, zp - 1) for dx in doors],
        room.reserved,
        (x1, room.z1, x2, zp - 1),
    )
    passage.against_wall("minecraft:chest[facing={f}]", rng)
    passage.against_wall("minecraft:barrel[facing={f}]", rng)
    passage.lights(1)
    for (a, b), dx in zip(rooms, doors, strict=True):
        lodger = _room(c, room.plan, room.i, [(dx, zp + 1)], (), (a, zp + 1, b, z2))
        lodger.bed(
            info,
            rng,
            rng.choice(COLOURS),
            "bed" if "bed" not in info["stands"] else None,
        )
        lodger.against_wall("minecraft:barrel[facing={f}]", rng)
        lodger.rug(rng.choice(RUGS), 1)
        lodger.lights(1)
    room.pieces += 1
    # the outer room's free floor is now the passage's: furnish nothing more
    room.reserved |= {(x, z) for x in range(x1, x2 + 1) for z in range(room.z1, z2 + 1)}
