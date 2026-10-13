"""
`medieval_house`: a timber-framed house with options, for castle2's village.

The house is drawn on a `Canvas` in its own frame, with the street to the
south, then turned to face its street and placed in the world. The frame
(local coordinates, before the turn):

- x runs along the street, 0..width-1 on the ground floor;
- z runs from the back wall (0) to the front wall (depth-1) on the street;
- y is up from the ground floor's standing level (0). Storey i stands at
  ``4 * i``; its walls are 3 high and the beams of the floor above are at
  ``4 * i + 3``. Each upper storey overhangs the one below (a jetty) on the
  street side, and also on the sides or all round if asked.

Everything a house places lies inside the `House.volume` it returns, and it
reports where its people should stand (`House.stands`) and its seats.
`house_blocks` gives the blocks without placing them, for tests and renders.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from mcipc.rcon.enumerations import FillMode
from mcwb import Item, Vec3, Volume

from mciwb.builders import BlockState, gable_roof, hip_roof, stairway
from mciwb.builders.placer import Placer
from mciwb.threads import get_client, set_client

AIR = "minecraft:air"
BEAM = "minecraft:stripped_dark_oak_log"
INFILL = "minecraft:calcite"
FLOOR = "minecraft:spruce_planks"
STONE = "minecraft:cobblestone"
QUOIN = "minecraft:stone_bricks"
BRICK = "minecraft:bricks"
PANE = "minecraft:glass_pane"
SHUTTER = "minecraft:spruce_trapdoor"
DOOR = "minecraft:dark_oak_door"
JOIST = "minecraft:dark_oak_stairs"
LANTERN = "minecraft:lantern"

STOREY = 4  # standing levels are 4 apart: 3 of wall, 1 of beams and floor

# the contents presets: what each furnishes, and the villager profession of
# the shopkeeper it wants (None: no shop)
KEEPERS = {
    "home": None,
    "baker": "farmer",
    "butcher": "butcher",
    "tailor": "shepherd",
    "tavern": "nitwit",
    "apothecary": "cleric",
    "candlemaker": "cleric",
    "carpenter": "mason",
    "fletcher": "fletcher",
    "cartographer": "cartographer",
    "cobbler": "leatherworker",
    "weaver": "shepherd",
}
SIGN_TEXT = {
    "baker": "The Baker",
    "butcher": "The Butcher",
    "tailor": "The Tailor",
    "tavern": "The Tavern",
    "apothecary": "Apothecary",
    "candlemaker": "Candles",
    "carpenter": "Carpenter",
    "fletcher": "Bows & Arrows",
    "cartographer": "Maps",
    "cobbler": "The Cobbler",
    "weaver": "The Weaver",
}

COMPASS = ("north", "east", "south", "west")  # clockwise from above
# blocks that hang on or stand on another, placed after everything else
ATTACHED = (
    "ladder",
    "lantern",
    "torch",
    "sign",
    "_door",
    "carpet",
    "candle",
    "flower_pot",
    "potted_",
    "_button",
    "lever",
    "banner",
    "bell",
    "cake",
    "_pressure_plate",
)


def _name(state: str) -> str:
    return state.partition("[")[0].partition("{")[0]


def _attached(state: str) -> bool:
    name = _name(state)
    return any(a in name for a in ATTACHED)


class Canvas:
    """
    Blocks in a house's own frame, keyed by (x, y, z): later blocks replace
    earlier ones. It also answers ``setblock`` and ``fill`` like an RCON
    client, so that mciwb's builders (roofs, stairways) can draw on it.
    """

    def __init__(self) -> None:
        self.blocks: dict[tuple[int, int, int], str] = {}

    def set(self, x: float, y: float, z: float, state: str) -> None:
        self.blocks[(int(x), int(y), int(z))] = str(state)

    def get(self, x: float, y: float, z: float) -> str:
        return self.blocks.get((int(x), int(y), int(z)), AIR)

    def box(self, x1, y1, z1, x2, y2, z2, state: str, keep: bool = False) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if not keep or self.get(x, y, z) == AIR:
                        self.set(x, y, z, state)

    # ---- the client interface, for the builders
    def setblock(self, pos: Vec3, block, mode=None) -> str:
        self.set(pos.x, pos.y, pos.z, str(block))
        return "Changed the block"

    def fill(self, a: Vec3, b: Vec3, block, mode=None, filter=None) -> str:
        keep = mode is not None and FillMode(mode) == FillMode.KEEP
        x1, y1, z1 = int(a.x), int(a.y), int(a.z)
        x2, y2, z2 = int(b.x), int(b.y), int(b.z)
        if filter:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    for z in range(min(z1, z2), max(z1, z2) + 1):
                        if _name(self.get(x, y, z)) == _name(filter):
                            self.set(x, y, z, str(block))
        else:
            self.box(x1, y1, z1, x2, y2, z2, str(block), keep)
        return "Successfully filled"

    def run(self, command: str, *args: str) -> str:
        return ""

    def draw(self, func: Callable[[], object]) -> None:
        """run a builder (which uses the thread's client) on this canvas"""
        try:
            real = get_client()
        except AttributeError:
            real = None
        set_client(self)  # type: ignore[arg-type]
        try:
            func()
        finally:
            if real is not None:
                set_client(real)


@dataclass
class House:
    """what `medieval_house` built, in world coordinates"""

    volume: Volume
    door: Vec3  # the door's lower half
    outside: Vec3  # the street block in front of the door, at standing level
    floors: list[int]  # the standing level of each storey
    stands: dict[str, Vec3] = field(default_factory=dict)  # counter, bed, hearth ...
    seats: list[tuple[Vec3, str]] = field(default_factory=list)  # (seat, looks)
    keeper: str | None = None  # the profession of the shopkeeper it wants
    contents: str = "home"
    facing: str = "south"
    footprint: set[tuple[int, int]] = field(default_factory=set)  # (x, z) cells
    blocks: dict[tuple[int, int, int], str] = field(default_factory=dict)
    frames: list[tuple[Vec3, int, str]] = field(default_factory=list)  # item frames


class _Plan:
    """the geometry of one house, in its own frame"""

    def __init__(
        self,
        width: int,
        depth: int,
        floors: int,
        jetty: int,
        jetty_sides: str,
    ) -> None:
        if not 5 <= width <= 11 or not 5 <= depth <= 13:
            raise ValueError(
                f"a house is 5..11 wide and 5..13 deep, not {width}x{depth}"
            )
        if not 1 <= floors <= 4:
            raise ValueError(f"a house has 1..4 storeys, not {floors}")
        if jetty_sides not in ("front", "front+sides", "all"):
            raise ValueError(f"jetty_sides is front, front+sides or all: {jetty_sides}")
        if not 0 <= jetty <= 2:
            raise ValueError(f"a jetty overhangs 0..2 blocks, not {jetty}")
        self.w, self.d, self.n, self.j = width, depth, floors, jetty
        self.sides = jetty if jetty_sides != "front" else 0
        self.back = jetty if jetty_sides == "all" else 0

    def rect(self, i: int) -> tuple[int, int, int, int]:
        """storey i's outer walls: x1, z1, x2, z2"""
        return (
            -self.sides * i,
            -self.back * i,
            self.w - 1 + self.sides * i,
            self.d - 1 + self.j * i,
        )

    @staticmethod
    def stand(i: int) -> int:
        return STOREY * i

    @staticmethod
    def beam(i: int) -> int:
        """the level of the beams and floor under storey i (i = n: the roof plate)"""
        return STOREY * i - 1


def _ring(x1: int, z1: int, x2: int, z2: int) -> list[tuple[int, int, str, int]]:
    """the cells of a rectangle's edge: (x, z, side, t), t counting along the
    side from its west or north end (corners are side 'corner')"""
    cells = []
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            on_x = x in (x1, x2)
            on_z = z in (z1, z2)
            if on_x and on_z:
                cells.append((x, z, "corner", 0))
            elif on_z:
                cells.append((x, z, "back" if z == z1 else "front", x - x1))
            elif on_x:
                cells.append((x, z, "left" if x == x1 else "right", z - z1))
    return cells


def _log(axis: str) -> str:
    return f"{BEAM}[axis={axis}]"


def _along(side: str) -> str:
    """the axis that runs along a wall side"""
    return "x" if side in ("front", "back") else "z"


def _outward(side: str) -> tuple[int, int]:
    return {"front": (0, 1), "back": (0, -1), "left": (-1, 0), "right": (1, 0)}[side]


def _face(side: str) -> str:
    """the compass name (in the house's frame) of the way a side faces out"""
    return {"front": "south", "back": "north", "left": "west", "right": "east"}[side]


def house_blocks(
    corner: Vec3,
    width: int,
    depth: int,
    floors: int = 2,
    facing: Vec3 | str = "south",
    jetty: int = 1,
    jetty_sides: str = "front",
    ground: str = "stone",
    frame: str = "close_studding",
    roof: str = "gable",
    roof_block: str | Item = Item.SPRUCE_STAIRS,
    chimney: bool = True,
    windows: str = "leaded",
    window_boxes: bool = False,
    contents: str = "home",
    seed: int | None = None,
) -> House:
    """
    The blocks of a house, in world coordinates, without placing them: see
    `medieval_house` for the arguments.
    """
    if ground not in ("stone", "timber"):
        raise ValueError(f"ground is stone or timber, not {ground}")
    if frame not in ("close_studding", "square_panel", "braced"):
        raise ValueError(f"frame is close_studding, square_panel or braced: {frame}")
    if roof not in ("gable", "gable_cross", "hip"):
        raise ValueError(f"roof is gable, gable_cross or hip, not {roof}")
    if windows not in ("leaded", "shuttered", "shop"):
        raise ValueError(f"windows are leaded, shuttered or shop, not {windows}")
    if contents not in KEEPERS:
        raise ValueError(f"contents is one of {list(KEEPERS)}, not {contents}")
    plan = _Plan(width, depth, floors, jetty, jetty_sides)
    rng = random.Random(seed if seed is not None else hash((width, depth, floors)))
    c = Canvas()
    info: dict = {"stands": {}, "seats": [], "frames": []}
    door_x = _door_x(plan, contents, windows)
    shop = windows == "shop" or KEEPERS[contents] not in (None, "nitwit")
    _shell(c, plan, ground, frame, rng)
    _windows(c, plan, windows, window_boxes, door_x, shop, rng)
    _door(c, plan, door_x)
    _floors_and_stairs(c, plan, info)
    if chimney:
        _chimney(c, plan, info)
    _roof(c, plan, roof, str(roof_block))
    if chimney:
        _chimney_top(c, plan)
    _lights(c, plan)
    from house_contents import furnish  # the presets (a separate module)

    furnish(c, plan, contents, door_x, info, rng)
    if info.get("sign"):
        _hanging_sign(c, plan, door_x, SIGN_TEXT[info["sign"]])
    return _to_world(c, plan, corner, _facing_name(facing), door_x, contents, info)


def _facing_name(facing: Vec3 | str) -> str:
    if isinstance(facing, str):
        if facing not in COMPASS:
            raise ValueError(f"facing is one of {COMPASS}, not {facing}")
        return facing
    v = Vec3(*facing)
    return {(0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west"}[
        (int(v.x), int(v.z))
    ]


def _door_x(plan: _Plan, contents: str, windows: str) -> int:
    """the x of the front door: right of centre for a shop (its counter
    window is on the left), else in the middle"""
    if windows == "shop" or KEEPERS[contents] is not None:
        return max(plan.w - 3, plan.w // 2 + 1)
    return plan.w // 2


def _shell(c: Canvas, plan: _Plan, ground: str, frame: str, rng: random.Random) -> None:
    """every storey's walls, floor beams and interior air"""
    for i in range(plan.n):
        x1, z1, x2, z2 = plan.rect(i)
        s, top = plan.stand(i), plan.beam(i + 1)
        # clear the inside, from the floor up to under the next beams
        c.box(x1 + 1, s, z1 + 1, x2 - 1, top - 1, z2 - 1, AIR)
        # the beams the storey stands on (the ground floor's are its plinth)
        b = plan.beam(i)
        for x, z, side, _t in _ring(x1, z1, x2, z2):
            if i == 0:
                c.set(
                    x,
                    b,
                    z,
                    QUOIN
                    if ground == "stone"
                    else _log(_along(side) if side != "corner" else "y"),
                )
            else:
                c.set(x, b, z, _log(_along(side) if side != "corner" else "x"))
        stone = i == 0 and ground == "stone"
        for x, z, side, t in _ring(x1, z1, x2, z2):
            for h in range(3):
                c.set(
                    x,
                    s + h,
                    z,
                    _wall_cell(
                        side,
                        t,
                        h,
                        x2 - x1 if side in ("front", "back") else z2 - z1,
                        frame,
                        stone,
                        rng,
                    ),
                )
    # the top plate under the roof
    x1, z1, x2, z2 = plan.rect(plan.n - 1)
    top = plan.beam(plan.n)
    for x, z, side, _t in _ring(x1, z1, x2, z2):
        c.set(x, top, z, _log(_along(side) if side != "corner" else "x"))
    c.box(x1 + 1, top, z1 + 1, x2 - 1, top, z2 - 1, FLOOR)


def _wall_cell(
    side: str, t: int, h: int, length: int, frame: str, stone: bool, rng
) -> str:
    """the block of a wall at t along its side (0..length) and h above its floor"""
    if stone:
        if side == "corner":
            return QUOIN
        return rng.choice((STONE, STONE, STONE, "minecraft:mossy_cobblestone"))
    if side == "corner":
        return _log("y")
    along = _along(side)
    if frame == "close_studding":
        return _log("y") if t % 2 == 0 else INFILL
    if frame == "square_panel":
        if t % 3 == 0 or t == length:
            return _log("y")
        return _log(along) if h == 1 else INFILL
    # braced: posts every 4, a diagonal brace climbing across each panel
    if t % 4 == 0 or t == length:
        return _log("y")
    k = t % 4
    return _log(along) if (k - 1) == h else INFILL


def _window_cells(plan: _Plan, i: int, side: str, door_x: int) -> list[int]:
    """the t (along the side) of each window on a side of storey i"""
    x1, z1, x2, z2 = plan.rect(i)
    length = (x2 - x1) if side in ("front", "back") else (z2 - z1)
    ts = list(range(2, length - 1, 3)) if length >= 4 else []
    if i == 0 and side == "front":
        ts = [t for t in ts if abs((x1 + t) - door_x) > 1]
    return ts


def _windows(
    c: Canvas,
    plan: _Plan,
    windows: str,
    boxes: bool,
    door_x: int,
    shop_front: bool,
    rng,
) -> None:
    for i in range(plan.n):
        x1, z1, x2, z2 = plan.rect(i)
        s = plan.stand(i)
        shop = shop_front and i == 0
        for side in ("front", "back", "left", "right"):
            if shop and side == "front":
                _shop_front(c, plan, door_x)
                continue
            for t in _window_cells(plan, i, side, door_x):
                x, z = (
                    (x1 + t, z1 if side == "back" else z2)
                    if side in ("front", "back")
                    else (x1 if side == "left" else x2, z1 + t)
                )
                c.set(x, s + 1, z, PANE)
                c.set(x, s + 2, z, PANE)
                ox, oz = _outward(side)
                if windows == "shuttered":
                    # open shutters either side of the window, on the wall's face
                    for dt in (-1, 1):
                        sx, sz = (
                            (x + dt, z + oz)
                            if side in ("front", "back")
                            else (x + ox, z + dt)
                        )
                        for h in (1, 2):
                            c.set(
                                sx,
                                s + h,
                                sz,
                                f"{SHUTTER}[facing={_face(side)},half={'bottom' if h == 1 else 'top'},open=true]",
                            )
                if boxes and (i > 0 or side != "front"):
                    flower = rng.choice(
                        (
                            "red_tulip",
                            "poppy",
                            "dandelion",
                            "azure_bluet",
                            "oxeye_daisy",
                        )
                    )
                    c.set(
                        x + ox,
                        s,
                        z + oz,
                        f"{SHUTTER}[facing={_face(side)},half=top,open=false]",
                    )
                    c.set(x + ox, s + 1, z + oz, f"minecraft:potted_{flower}")


def _shop_front(c: Canvas, plan: _Plan, door_x: int) -> None:
    """an open counter across the ground floor's front, left of the door:
    a counter slab, an opening above it and, without a jetty over it, a
    shutter for an awning"""
    x1, _z1, _x2, z2 = plan.rect(0)
    for x in range(x1 + 1, door_x - 1):
        if (x - x1) % 4 == 0:
            continue  # a post
        c.set(x, 0, z2, "minecraft:spruce_slab[type=top]")
        c.set(x, 1, z2, AIR)
        if plan.j == 0 or plan.n == 1:
            c.set(x, 2, z2 + 1, f"{SHUTTER}[facing=south,half=top,open=false]")


def _hanging_sign(c: Canvas, plan: _Plan, door_x: int, text: str) -> None:
    """a shop's sign hanging beside its door, square to the street, from
    the jetty above it (or from a bracket when there is none)"""
    z2 = plan.rect(0)[3]
    # beside the door, between two joists (they stand at every other x)
    near = (door_x - 1, door_x + 1, door_x - 2, door_x + 2)
    x = next((x for x in near if 0 < x < plan.w - 1 and x % 2 == 1), door_x - 1)
    z = z2 + 1
    if c.get(x, 3, z) == AIR:
        c.set(x, 3, z, _log("z"))  # a bracket out of the wall
    words = text.split(" ", 1) if len(text) > 12 else [text]
    lines = ",".join(f"'\"{w}\"'" for w in (*words, "", "", "")[:4])
    msgs = f"{{messages:[{lines}]}}"
    c.set(
        x,
        2,
        z,
        f"minecraft:spruce_hanging_sign[rotation=4,attached=false]"
        f"{{front_text:{msgs},back_text:{msgs}}}",
    )


def _door(c: Canvas, plan: _Plan, door_x: int) -> None:
    z = plan.rect(0)[3]
    c.set(door_x, 0, z, f"{DOOR}[facing=north,half=lower,hinge=left]")
    c.set(door_x, 1, z, f"{DOOR}[facing=north,half=upper,hinge=left]")
    c.set(door_x, 2, z, _log("x"))  # the lintel
    c.set(door_x, -1, z, QUOIN)  # the threshold


def _stairs_fit(plan: _Plan) -> bool:
    """a stair (two rows along the back wall, x 1..5) or a ladder"""
    return plan.w >= 8 or (plan.w == 7 and plan.d >= 6)


def _chimney_cell(plan: _Plan) -> tuple[int, int]:
    """the inner back corner on the right, or further forward if the
    stairs need the back rows"""
    return (plan.w - 2, 1 if plan.w >= 8 or not _stairs_fit(plan) else 3)


def _floors_and_stairs(c: Canvas, plan: _Plan, info: dict) -> None:
    for i in range(plan.n):
        x1, z1, x2, z2 = plan.rect(i)
        b = plan.beam(i)
        c.box(
            x1 + 1,
            b,
            z1 + 1,
            x2 - 1,
            b,
            z2 - 1,
            FLOOR if i else "minecraft:spruce_planks",
        )
        if i:  # joist ends under each overhang
            lx1, lz1, lx2, lz2 = plan.rect(i - 1)
            for x in range(lx1, lx2 + 1, 2):
                if z2 > lz2:
                    for z in range(lz2 + 1, z2 + 1):
                        c.set(x, b - 1, z, f"{JOIST}[facing=north,half=top]")
                if z1 < lz1:
                    for z in range(z1, lz1):
                        c.set(x, b - 1, z, f"{JOIST}[facing=south,half=top]")
            for z in range(lz1, lz2 + 1, 2):
                if x1 < lx1:
                    for x in range(x1, lx1):
                        c.set(x, b - 1, z, f"{JOIST}[facing=east,half=top]")
                if x2 > lx2:
                    for x in range(lx2 + 1, x2 + 1):
                        c.set(x, b - 1, z, f"{JOIST}[facing=west,half=top]")
    if plan.n == 1:
        return
    if _stairs_fit(plan):
        for i in range(plan.n - 1):
            if i % 2 == 0:
                points = [Vec3(1, plan.beam(i), 1), Vec3(5, plan.beam(i + 1), 1)]
            else:
                points = [Vec3(5, plan.beam(i), 2), Vec3(1, plan.beam(i + 1), 2)]
            c.draw(lambda p=points: stairway(p, "minecraft:spruce_stairs", clearance=2))
            # a rail along the stairwell's open side, on the floor above
            row = 2 if i % 2 == 0 else 1
            for x in range(2, 5):
                if c.get(x, plan.beam(i + 1), row) != AIR:
                    c.set(x, plan.stand(i + 1), row, "minecraft:spruce_fence")
        info["climb"] = "stairs"
    else:
        # a ladder up the back wall at x 1, through every floor
        for y in range(0, plan.beam(plan.n - 1) + 1):
            c.set(1, y, 1, "minecraft:ladder[facing=south]")
        info["climb"] = "ladder"


def _chimney(c: Canvas, plan: _Plan, info: dict) -> None:
    """a brick stack in an inner corner with a fireplace on the ground floor"""
    x, z = _chimney_cell(plan)
    top = plan.beam(plan.n)
    c.box(x, -1, z, x, top, z, BRICK)
    c.set(x, 0, z, "minecraft:campfire[lit=true,signal_fire=false]")
    c.set(x, 1, z, AIR)
    c.set(x, -1, z, BRICK)
    info["stands"]["hearth"] = (x - 1, 0, z + 1)


def _chimney_top(c: Canvas, plan: _Plan) -> None:
    """carry the stack up through the roof, with a campfire on top for smoke"""
    x, z = _chimney_cell(plan)
    y = plan.beam(plan.n) + 1
    x1, z1, x2, z2 = plan.rect(plan.n - 1)
    ridge = plan.beam(plan.n) + (z2 - z1) // 2 + 2  # one above the ridge
    while y < ridge or c.get(x, y, z) != AIR or c.get(x, y + 1, z) != AIR:
        c.set(x, y, z, BRICK)
        y += 1
    c.set(x, y, z, BRICK)
    c.set(x, y + 1, z, "minecraft:campfire[lit=true,signal_fire=false]")


def _roof(c: Canvas, plan: _Plan, roof: str, stairs: str) -> None:
    x1, z1, x2, z2 = plan.rect(plan.n - 1)
    y = plan.beam(plan.n)
    a, b = Vec3(x1, y, z1), Vec3(x2, y, z2)
    if roof == "hip":
        c.draw(lambda: hip_roof(a, b, stairs, overhang=1))
    else:
        c.draw(lambda: gable_roof(a, b, stairs, gable=INFILL, axis="x", overhang=1))
        _gable_timbers(c, x1, x2, z1, z2, y)
    if roof == "gable_cross":
        # a gable to the street over the middle of the front, half the depth
        half = max(1, (x2 - x1) // 4)
        mid = (x1 + x2) // 2
        a2, b2 = Vec3(mid - half, y, (z1 + z2) // 2), Vec3(mid + half, y, z2)
        c.draw(lambda: gable_roof(a2, b2, stairs, gable=INFILL, axis="z", overhang=1))
        # its gable: a post and a small window
        for h in range(1, half + 1):
            if c.get(mid, y + h, z2) == INFILL:
                c.set(mid, y + h, z2, PANE if h == 1 else _log("y"))
    # the attic is a dark room under the roof: light it
    c.set((x1 + x2) // 2, y + 1, (z1 + z2) // 2, f"{LANTERN}[hanging=false]")


def _gable_timbers(c: Canvas, x1: int, x2: int, z1: int, z2: int, y: int) -> None:
    """a king post and a collar beam on each gable end"""
    mid = (z1 + z2) // 2
    for x in (x1, x2):
        for h in range(1, (z2 - z1) // 2 + 1):
            if c.get(x, y + h, mid) == INFILL:
                c.set(x, y + h, mid, _log("y"))
        for z in range(z1, z2 + 1):
            if c.get(x, y + 2, z) == INFILL:
                c.set(x, y + 2, z, _log("z"))


def _lights(c: Canvas, plan: _Plan) -> None:
    """a lantern under every ceiling"""
    for i in range(plan.n):
        x1, z1, x2, z2 = plan.rect(i)
        x, z = (x1 + x2) // 2, (z1 + z2) // 2
        if (
            c.get(x, plan.beam(i + 1), z) not in (AIR,)
            and c.get(x, plan.stand(i) + 2, z) == AIR
        ):
            c.set(x, plan.stand(i) + 2, z, f"{LANTERN}[hanging=true]")


# ---------------------------------------------------------------- to the world


def _turn(steps: int, x: int, z: int) -> tuple[int, int]:
    """turn (x, z) clockwise (from above) by quarter turns"""
    for _ in range(steps % 4):
        x, z = -z, x
    return x, z


def _to_world(
    c: Canvas,
    plan: _Plan,
    corner: Vec3,
    facing: str,
    door_x: int,
    contents: str,
    info: dict,
) -> House:
    steps = (COMPASS.index(facing) - COMPASS.index("south")) % 4
    # the ground floor's footprint turned: its north-west corner goes to `corner`
    turned = [_turn(steps, x, z) for x in (0, plan.w - 1) for z in (0, plan.d - 1)]
    ox = int(corner.x) - min(x for x, _ in turned)
    oz = int(corner.z) - min(z for _, z in turned)
    oy = int(corner.y)

    def world(x: float, y: float, z: float) -> Vec3:
        tx, tz = _turn(steps, int(x), int(z))
        return Vec3(tx + ox, int(y) + oy, tz + oz)

    blocks = {}
    for (x, y, z), state in c.blocks.items():
        p = world(x, y, z)
        s = BlockState.parse(state)
        blocks[(p.x, p.y, p.z)] = str(s.rotate(steps) if steps else s)
    xs = [k[0] for k in blocks]
    ys = [k[1] for k in blocks]
    zs = [k[2] for k in blocks]
    volume = Volume.from_corners(
        Vec3(min(xs), min(ys), min(zs)), Vec3(max(xs), max(ys), max(zs))
    )
    front = plan.rect(0)[3]
    dx, dz = _turn(steps, 0, 1)
    seats = []
    for (x, y, z), looks in info["seats"]:
        seats.append((world(x, y, z), COMPASS[(COMPASS.index(looks) + steps) % 4]))
    frames = []
    for (x, y, z), side, item in info["frames"]:
        f = COMPASS[(COMPASS.index(side) + steps) % 4]
        frames.append(
            (world(x, y, z), {"north": 2, "south": 3, "west": 4, "east": 5}[f], item)
        )
    return House(
        volume=volume,
        door=world(door_x, 0, front),
        outside=world(door_x, 0, front) + Vec3(dx, 0, dz),
        floors=[oy + plan.stand(i) for i in range(plan.n)],
        stands={k: world(*v) for k, v in info["stands"].items()},
        seats=seats,
        keeper=KEEPERS[contents],
        contents=contents,
        facing=facing,
        footprint={(k[0], k[2]) for k in blocks},
        blocks=blocks,
        frames=frames,
    )


def place(house: House, summon: Callable[[str, Vec3, str], None] | None = None) -> None:
    """
    Place a house's blocks: everything solid bottom up, then what hangs on
    or stands on it (ladders, lanterns, doors, carpets ...), so that nothing
    is placed before what holds it up. ``summon(kind, pos, nbt)`` places its
    item frames, if given.
    """
    p = Placer(get_client())
    for attached in (False, True):
        layers: dict[int, dict[tuple[int, int], str]] = {}
        for (x, y, z), state in house.blocks.items():
            if _attached(state) == attached:
                layers.setdefault(y, {})[(x, z)] = state
        for y in sorted(layers):
            if attached:
                # doors: the lower half first
                for (x, z), state in sorted(
                    layers[y].items(), key=lambda kv: "upper" in kv[1]
                ):
                    p.setblock(Vec3(x, y, z), state)
            else:
                p.layer(y, layers[y])
    if summon is not None:
        for pos, facing, item in house.frames:
            summon(
                "item_frame",
                pos,
                f'Facing:{facing}b,Item:{{id:"minecraft:{item}",count:1}}',
            )


def medieval_house(
    corner: Vec3,
    width: int,
    depth: int,
    floors: int = 2,
    facing: Vec3 | str = "south",
    jetty: int = 1,
    jetty_sides: str = "front",
    ground: str = "stone",
    frame: str = "close_studding",
    roof: str = "gable",
    roof_block: str | Item = Item.SPRUCE_STAIRS,
    chimney: bool = True,
    windows: str = "leaded",
    window_boxes: bool = False,
    contents: str = "home",
    seed: int | None = None,
    summon: Callable[[str, Vec3, str], None] | None = None,
) -> House:
    """
    Build a timber-framed house: stripped dark oak beams with white infill,
    a beam at every floor, each upper storey jettied out over the street on
    upside-down stair joists, a steep roof, a brick chimney with a fireplace
    and a campfire on top for smoke, plank floors, a stair (or a ladder in
    a narrow house), lanterns, and the furniture of ``contents``.

    :param corner: the north-west corner of the ground floor (its outer
        walls), at the standing level of the ground floor
    :param width: the ground floor along the street, 5..11
    :param depth: the ground floor back from the street, 5..13 (turned with
        the house: for an east or west facing house width runs along z)
    :param floors: 1..4 storeys
    :param facing: the street side: the door, the jetties, the shop front
    :param jetty: how far each upper storey overhangs the one below, 0..2
    :param jetty_sides: "front", "front+sides" or "all"
    :param ground: "stone" (a stone ground storey) or "timber"
    :param frame: "close_studding", "square_panel" or "braced"
    :param roof: "gable" (the ridge along the street), "gable_cross" (with a
        gable to the street) or "hip"
    :param roof_block: the roof's stairs
    :param chimney: a brick chimney with a fireplace
    :param windows: "leaded" (glass panes), "shuttered" (panes with open
        shutters) or "shop" (an open counter on the ground floor's front)
    :param window_boxes: flowers under the windows
    :param contents: the furniture: one of `KEEPERS`
    :param seed: varies the small things (stone, flowers ...) repeatably
    :param summon: ``summon(kind, pos, nbt)`` for the item frames (none if
        not given), e.g. castle_lib.summon to tag them
    :returns: a `House`: its volume, door, the stands of its people, seats
    """
    house = house_blocks(
        corner,
        width,
        depth,
        floors,
        facing,
        jetty,
        jetty_sides,
        ground,
        frame,
        roof,
        roof_block,
        chimney,
        windows,
        window_boxes,
        contents,
        seed,
    )
    place(house, summon)
    return house


def footprint_cells(houses: Iterable[House]) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    for h in houses:
        out |= h.footprint
    return out
