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

The walls are white (calcite) panels in a frame of black beams (stripped
dark oak): posts every few blocks, a beam along each jettied floor and
under the eaves. The stairs climb along the back wall, from the back left
corner, in flights of four steps with a floor opening above each that
leaves the 3 blocks of headroom a player needs to walk up them; narrow
houses have a ladder. The fireplace is three bricks wide with a mantel,
on the right or the back wall, its chimney carried up through the roof.

Everything a house places lies inside the `House.volume` it returns, and it
reports where its people should stand (`House.stands`), its seats, its
stairs' cells (`House.steps`, `House.headroom`, for checks) and a spot for
a clue (`House.clue_spot`). `house_blocks` gives the blocks without placing
them, for tests and renders, and `house_problems` checks a house: a walker
needing 2 free blocks reaches every storey, the doors, stands and seats are
usable, the walls are mostly white and every storey is furnished.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from mcipc.rcon.enumerations import FillMode
from mcwb import Item, Vec3, Volume

from mciwb.builders import BlockState, gable_roof, hip_roof
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
STAIRS = "minecraft:spruce_stairs"
RAIL = "minecraft:spruce_fence"
CAMPFIRE = "minecraft:campfire[lit=true,signal_fire=false]"

STOREY = 4  # standing levels are 4 apart: 3 of wall, 1 of beams and floor
FRAMES = ("square_panel", "close_studding", "braced")

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
STEP = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
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
# blocks a player walks through
PASSABLE = (
    "carpet",
    "_door",
    "ladder",
    "torch",
    "_sign",
    "candle",
    "_pressure_plate",
    "_button",
)


def _name(state: str) -> str:
    return state.partition("[")[0].partition("{")[0]


def _attached(state: str) -> bool:
    name = _name(state)
    return any(a in name for a in ATTACHED)


def passable(state: str) -> bool:
    """can a player walk through this block?"""
    name = _name(state)
    return name == AIR or (any(k in name for k in PASSABLE) and "trapdoor" not in name)


class Canvas:
    """
    Blocks in a house's own frame, keyed by (x, y, z): later blocks replace
    earlier ones. It also answers ``setblock`` and ``fill`` like an RCON
    client, so that mciwb's builders (roofs) can draw on it.
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
    ground: str = "stone"  # the ground storey: stone or timber
    footprint: set[tuple[int, int]] = field(default_factory=set)  # (x, z) cells
    blocks: dict[tuple[int, int, int], str] = field(default_factory=dict)
    frames: list[tuple[Vec3, int, str]] = field(default_factory=list)  # item frames
    # a free floor cell on the ground floor against a wall, off every way
    # through the house, where a lectern can stand (phase 6's clues)
    clue_spot: Vec3 | None = None
    steps: list[Vec3] = field(default_factory=list)  # every stair step or ladder
    # the cells that must stay free for the stairs (or ladder) to be climbed:
    # 3 over each step but the top one (2), and the landings at both ends
    headroom: list[Vec3] = field(default_factory=list)


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
        # a stair core along the back wall (x 1..5, rows z 1..2), or a ladder
        self.stairs = width >= 7 and depth >= 6
        if floors > 1 and not self.stairs and self.back:
            raise ValueError(
                "a narrow house's ladder needs its back wall: no back jetty"
            )

    def rect(self, i: int) -> tuple[int, int, int, int]:
        """storey i's outer walls: x1, z1, x2, z2"""
        return (
            -self.sides * i,
            -self.back * i,
            self.w - 1 + self.sides * i,
            self.d - 1 + self.j * i,
        )

    def inner(self, i: int) -> tuple[int, int, int, int]:
        """storey i's floor inside its walls: x1, z1, x2, z2"""
        x1, z1, x2, z2 = self.rect(i)
        return x1 + 1, z1 + 1, x2 - 1, z2 - 1

    def jettied(self, i: int, side: str) -> bool:
        """does storey i overhang the one below on this side?"""
        if i == 0:
            return False
        return {
            "front": self.j,
            "left": self.sides,
            "right": self.sides,
            "back": self.back,
        }[side] > 0

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


# ---------------------------------------------------------------- the frame


def _posts(length: int, frame: str) -> list[int]:
    """the t of each post along a side 0..length: corner posts and studs
    every 3 (close studding) or 4 (square panels, braced) blocks, with no
    panel narrower than 2"""
    step = 3 if frame == "close_studding" else 4
    posts = list(range(0, length, step))
    if len(posts) > 1 and length - posts[-1] < 3:
        posts.pop()
    return posts + [length]


def _panels(length: int, frame: str) -> list[tuple[int, int]]:
    """the (first, last) t of each panel between two posts"""
    posts = _posts(length, frame)
    return [(a + 1, b - 1) for a, b in zip(posts, posts[1:], strict=False) if b > a + 1]


def _braces(length: int, frame: str) -> dict[tuple[int, int], str]:
    """(t, h) -> log of the braces of a braced side: one diagonal in each end
    panel, climbing away from the corner post"""
    if frame != "braced" or length < 6:
        return {}
    panels = _panels(length, frame)
    out: dict[tuple[int, int], str] = {}
    a, b = panels[0]
    for h in range(3):
        if a + h <= b:
            out[(a + h, h)] = "brace"
    a, b = panels[-1]
    for h in range(3):
        if b - h >= a:
            out[(b - h, h)] = "brace"
    return out


def _wall_cell(side: str, t: int, h: int, length: int, frame: str) -> str:
    """the block of a timber wall at t along its side (0..length) and h above
    its floor: a post, a brace (front and back only) or white infill"""
    if side == "corner" or t in _posts(length, frame):
        return _log("y")
    if side in ("front", "back") and (t, h) in _braces(length, frame):
        return _log(_along(side))
    return INFILL


def _side_length(plan: _Plan, i: int, side: str) -> int:
    x1, z1, x2, z2 = plan.rect(i)
    return (x2 - x1) if side in ("front", "back") else (z2 - z1)


def _shell(c: Canvas, plan: _Plan, ground: str, frame: str, rng: random.Random) -> None:
    """every storey's walls, the beams of its floor, its interior air"""
    for i in range(plan.n):
        x1, z1, x2, z2 = plan.rect(i)
        s, top = plan.stand(i), plan.beam(i + 1)
        c.box(x1 + 1, s, z1 + 1, x2 - 1, top - 1, z2 - 1, AIR)
        b = plan.beam(i)
        for x, z, side, t in _ring(x1, z1, x2, z2):
            if i == 0:
                # the plinth: stone, or a sill beam on a stone footing
                c.set(
                    x,
                    b,
                    z,
                    QUOIN
                    if ground == "stone" or side == "corner"
                    else _log(_along(side)),
                )
            elif side == "corner":
                c.set(x, b, z, _log("y"))
            elif side == "front" and plan.jettied(i, side):
                c.set(x, b, z, _log(_along(side)))  # the bressumer of the jetty
            else:
                length = _side_length(plan, i, side)
                c.set(x, b, z, _log("y") if t in _posts(length, frame) else INFILL)
        stone = i == 0 and ground == "stone"
        for x, z, side, t in _ring(x1, z1, x2, z2):
            length = 0 if side == "corner" else _side_length(plan, i, side)
            for h in range(3):
                if stone:
                    state = (
                        QUOIN
                        if side == "corner"
                        else rng.choice(
                            (STONE, STONE, STONE, "minecraft:mossy_cobblestone")
                        )
                    )
                else:
                    state = _wall_cell(side, t, h, length, frame)
                c.set(x, s + h, z, state)
    # the row under the roof: the posts carried up, white between them
    # (the eaves shade it)
    x1, z1, x2, z2 = plan.rect(plan.n - 1)
    top = plan.beam(plan.n)
    for x, z, side, t in _ring(x1, z1, x2, z2):
        if side == "corner":
            c.set(x, top, z, _log("y"))
        else:
            length = _side_length(plan, plan.n - 1, side)
            c.set(x, top, z, _log("y") if t in _posts(length, frame) else INFILL)
    c.box(x1 + 1, top, z1 + 1, x2 - 1, top, z2 - 1, FLOOR)


def _window_cells(plan: _Plan, i: int, side: str, door_x: int, frame: str) -> list[int]:
    """the t (along the side) of each window on a side of storey i: in the
    middle of every other panel (every panel on a short side), none in a
    braced panel or beside the door"""
    length = _side_length(plan, i, side)
    panels = _panels(length, frame)
    braced = (
        {t for t, _h in _braces(length, frame)} if side in ("front", "back") else set()
    )
    x1 = plan.rect(i)[0]
    ts = []
    for a, b in panels:
        t = (a + b) // 2
        if t in braced or any(a <= u <= b for u in braced):
            continue
        if i == 0 and side == "front" and abs((x1 + t) - door_x) <= 1:
            continue
        ts.append(t)
    if len(ts) > 2:
        # every other panel, symmetric about the middle of the side
        half = ts[: (len(ts) + 1) // 2 : 2]
        ts = sorted(set(half + [ts[len(ts) - 1 - ts.index(t)] for t in half]))
    return ts


def _windows(
    c: Canvas,
    plan: _Plan,
    windows: str,
    boxes: bool,
    door_x: int,
    shop_front: bool,
    frame: str,
    ground: str,
    rng,
) -> None:
    for i in range(plan.n):
        x1, z1, x2, z2 = plan.rect(i)
        s = plan.stand(i)
        shop = shop_front and i == 0
        for side in ("front", "back", "left", "right"):
            if shop and side == "front":
                _shop_front(c, plan, door_x, frame)
                continue
            # a stone storey's windows by the panels of a square frame
            f = "square_panel" if i == 0 and ground == "stone" else frame
            for t in _window_cells(plan, i, side, door_x, f):
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


def _shop_front(c: Canvas, plan: _Plan, door_x: int, frame: str) -> None:
    """an open counter across the ground floor's front, left of the door:
    a counter slab, an opening above it and, without a jetty over it, a
    shutter for an awning"""
    x1, _z1, x2, z2 = plan.rect(0)
    posts = _posts(x2 - x1, frame)
    for x in range(x1 + 1, door_x - 1):
        if (x - x1) in posts:
            continue
        c.set(x, 0, z2, "minecraft:spruce_slab[type=top]")
        c.set(x, 1, z2, AIR)
        if plan.j == 0 or plan.n == 1:
            c.set(x, 2, z2 + 1, f"{SHUTTER}[facing=south,half=top,open=false]")


def _snbt(text: str) -> str:
    """a plain SNBT string (sign lines are text components: a string is one)"""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _hanging_sign(c: Canvas, plan: _Plan, door_x: int, text: str) -> None:
    """a shop's sign hanging beside its door, square to the street, from
    the jetty above it (or from a bracket when there is none)"""
    z2 = plan.rect(0)[3]
    near = (door_x - 1, door_x + 1, door_x - 2, door_x + 2)
    x = next((x for x in near if 0 < x < plan.w - 1 and x % 2 == 1), door_x - 1)
    z = z2 + 1
    if c.get(x, 3, z) == AIR:
        c.set(x, 3, z, _log("z"))  # a bracket out of the wall
    words = text.split(" ", 1) if len(text) > 12 else [text]
    lines = ",".join(_snbt(w) for w in (*words, "", "", "")[:4])
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


# ---------------------------------------------------------------- floors, stairs


def _floors(c: Canvas, plan: _Plan) -> None:
    """the plank floor of every storey, and joist ends under each overhang"""
    for i in range(plan.n):
        x1, z1, x2, z2 = plan.rect(i)
        b = plan.beam(i)
        c.box(x1 + 1, b, z1 + 1, x2 - 1, b, z2 - 1, FLOOR)
        if not i:
            continue
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


def flights(plan: _Plan) -> list[dict]:
    """
    The stair flights of a house with a stair core, one from each storey to
    the next: flight s runs along row z = 1 eastwards (s even) or z = 2
    westwards (s odd), four steps climbing from storey s's floor to the
    next's. Each: ``row``, ``steps`` [(x, y)], ``bottom`` (the floor cell
    the climb starts from), ``top`` (the last step) and ``exit`` (the floor
    cell of the storey above that the climb ends on).
    """
    out = []
    for s in range(plan.n - 1):
        east = s % 2 == 0
        row = 1 if east else 2
        xs = [2, 3, 4, 5] if east else [4, 3, 2, 1]
        last = s + 1 == plan.n - 1
        out.append(
            {
                "storey": s,
                "row": row,
                "facing": "east" if east else "west",
                "steps": [(x, plan.stand(s) + k) for k, x in enumerate(xs)],
                "bottom": (1, row) if east else (5, row),
                "top": (xs[-1], row),
                # an east flight ends at (5, 1): on to (5, 2), where the next
                # flight starts; a west one at (1, 2): on to (1, 1) for the
                # next flight, or (1, 3) into the top storey's room
                "exit": (5, 2) if east else ((1, 3) if last else (1, 1)),
            }
        )
    return out


def _stairs(c: Canvas, plan: _Plan, info: dict) -> None:
    """the stair core (or a ladder): steps, the floor openings over them,
    rails round the openings, storage under the steps; records the cells to
    keep clear on each storey (info["keys"], info["core"]) and the steps and
    their headroom"""
    info["keys"] = {i: [] for i in range(plan.n)}
    info["core"] = {i: set() for i in range(plan.n)}
    info["steps"], info["headroom"] = [], []
    if plan.n == 1:
        return
    if not plan.stairs:
        # a ladder up the back wall at x 1, through every floor
        top = plan.beam(plan.n - 1)
        for y in range(0, top + 1):
            c.set(1, y, 1, "minecraft:ladder[facing=south]")
            info["steps"].append((1, y, 1))
        info["headroom"] += [(1, top + 1, 1), (1, top + 2, 1)]
        for i in range(plan.n):
            info["keys"][i].append((2, 1))
            info["core"][i] |= {(1, 1), (2, 1), (1, 2)}
        return
    fl = flights(plan)
    for f in fl:
        s, row = f["storey"], f["row"]
        for k, (x, y) in enumerate(f["steps"]):
            c.set(x, y, row, f"{STAIRS}[facing={f['facing']},half=bottom]")
            info["steps"].append((x, y, row))
            # feet and head over the step, and the block above that while
            # stepping up to the next one
            for dy in range(1, 4 if k < 3 else 3):
                c.set(x, y + dy, row, AIR)
                info["headroom"].append((x, y + dy, row))
            # storage under the steps against the back wall, a stringer of
            # planks under the others
            for y2 in range(plan.stand(s), y):
                c.set(
                    x,
                    y2,
                    row,
                    "minecraft:barrel[facing=south]" if row == 1 else FLOOR,
                )
        bx, bz = f["bottom"]
        ex, ez = f["exit"]
        info["headroom"] += [(bx, plan.stand(s) + dy, bz) for dy in range(3)]
        info["headroom"] += [(ex, plan.stand(s + 1) + dy, ez) for dy in range(2)]
        info["keys"][s].append(f["bottom"])
        info["keys"][s + 1].append(f["exit"])
    for i in range(plan.n):
        info["core"][i] |= {(x, z) for x in range(1, 6) for z in (1, 2)}
    info["core"][0].add((1, 2))  # the way onto the first step
    # rails round each floor opening, on the storey above
    for f in fl:
        t = f["storey"] + 1
        y = plan.stand(t)
        row = f["row"]
        hole = {(x, row) for x, _y in f["steps"][:3]}
        nxt = fl[t]["steps"] if t < len(fl) else []
        skip = hole | {f["top"], f["exit"]} | {(x, fl[t]["row"]) for x, _ in nxt}
        x1, z1, x2, z2 = plan.inner(t)
        for hx, hz in hole:
            for dx, dz in STEP.values():
                x, z = hx + dx, hz + dz
                if (x, z) in skip or not (x1 <= x <= x2 and z1 <= z <= z2):
                    continue
                if c.get(x, y, z) == AIR and c.get(x, y + 1, z) == AIR:
                    c.set(x, y, z, RAIL)
                    info["core"][t].add((x, z))


# ---------------------------------------------------------------- the hearth


def hearth_cells(plan: _Plan) -> dict:
    """where the fireplace goes: on the back wall right of the stairs in a
    wide house, else on the right wall. ``breast`` (its three cells),
    ``fire`` (the middle one), ``front`` (the floor before it), ``wall``
    (the side it stands against), ``stack`` (the cell the chimney rises in)"""
    w, d = plan.w, plan.d
    if w >= 10:
        xc = w - 3
        breast = [(xc - 1, 1), (xc, 1), (xc + 1, 1)]
        front = [(x, 2) for x, _ in breast]
        return {
            "breast": breast,
            "fire": (xc, 1),
            "front": front,
            "wall": "north",
            "stack": (xc, 1),
        }
    if plan.stairs:
        zc = min(max(3, (d - 1) // 2), d - 3)
    else:
        # a narrow house's door is near the right wall: keep off the front row
        zc = max(2, min((d - 1) // 2, d - 4))
    x = w - 2
    breast = [(x, zc - 1), (x, zc), (x, zc + 1)]
    return {
        "breast": breast,
        "fire": (x, zc),
        "front": [(x - 1, z) for _, z in breast],
        "wall": "east",
        # clear of the top landing at (5, 2..3) in a narrow house
        "stack": (x, zc + 1) if w == 7 else (x, zc),
    }


def _fireplace(c: Canvas, plan: _Plan, info: dict) -> None:
    """a fireplace three bricks wide on the ground floor: a campfire between
    brick cheeks under a brick hood with a mantel shelf of upside-down
    stairs, a hearthstone before it, and the chimney stack above"""
    hc = hearth_cells(plan)
    facing = hc["wall"]  # the mantel's stairs face the wall they stand on
    for x, z in hc["breast"]:
        fire = (x, z) == hc["fire"]
        c.set(x, -1, z, BRICK)
        c.set(x, 0, z, CAMPFIRE if fire else BRICK)
        c.set(x, 1, z, AIR if fire else BRICK)
        c.set(x, 2, z, BRICK)
    for x, z in hc["front"]:
        c.set(x, 2, z, f"minecraft:brick_stairs[facing={facing},half=top]")
    fx, fz = hc["front"][1]
    c.set(fx, -1, fz, BRICK)  # the hearthstone
    # the stack, up through every floor to the roof plate
    sx, sz = hc["stack"]
    c.box(sx, 3, sz, sx, plan.beam(plan.n), sz, BRICK)
    info["stands"]["hearth"] = (fx, 0, fz)
    info["core"][0] |= set(hc["breast"]) | set(hc["front"])
    for i in range(1, plan.n):
        info["core"][i].add(hc["stack"])


def _chimney_top(c: Canvas, plan: _Plan) -> None:
    """carry the stack up through the roof, with a campfire on top for smoke"""
    x, z = hearth_cells(plan)["stack"]
    y = plan.beam(plan.n) + 1
    x1, z1, x2, z2 = plan.rect(plan.n - 1)
    ridge = plan.beam(plan.n) + (z2 - z1) // 2 + 2  # one above the ridge
    while y < ridge or c.get(x, y, z) != AIR or c.get(x, y + 1, z) != AIR:
        c.set(x, y, z, BRICK)
        y += 1
    c.set(x, y, z, BRICK)
    c.set(x, y + 1, z, CAMPFIRE)


# ---------------------------------------------------------------- the roof


def _roof(c: Canvas, plan: _Plan, roof: str, stairs: str) -> None:
    x1, z1, x2, z2 = plan.rect(plan.n - 1)
    y = plan.beam(plan.n)
    a, b = Vec3(x1, y, z1), Vec3(x2, y, z2)
    if roof == "hip":
        c.draw(lambda: hip_roof(a, b, stairs, overhang=1))
    else:
        c.draw(lambda: gable_roof(a, b, stairs, gable=INFILL, axis="x", overhang=1))
        _king_posts(c, x1, x2, z1, z2, y)
    if roof == "gable_cross":
        # a gable to the street over the middle of the front, half the depth
        half = max(1, (x2 - x1) // 4)
        mid = (x1 + x2) // 2
        a2, b2 = Vec3(mid - half, y, (z1 + z2) // 2), Vec3(mid + half, y, z2)
        c.draw(lambda: gable_roof(a2, b2, stairs, gable=INFILL, axis="z", overhang=1))
        # its gable: a small window over a beam
        for h in range(1, half + 1):
            if c.get(mid, y + h, z2) == INFILL:
                c.set(mid, y + h, z2, PANE if h == 1 else _log("y"))
    # the attic is a dark room under the roof: light it
    c.set((x1 + x2) // 2, y + 1, (z1 + z2) // 2, f"{LANTERN}[hanging=false]")


def _king_posts(c: Canvas, x1: int, x2: int, z1: int, z2: int, y: int) -> None:
    """a king post up the middle of each white gable end"""
    mid = (z1 + z2) // 2
    for x in (x1, x2):
        for h in range(1, (z2 - z1) // 2 + 1):
            if c.get(x, y + h, mid) == INFILL:
                c.set(x, y + h, mid, _log("y"))


# ---------------------------------------------------------------- the house


def house_blocks(
    corner: Vec3,
    width: int,
    depth: int,
    floors: int = 2,
    facing: Vec3 | str = "south",
    jetty: int = 1,
    jetty_sides: str = "front",
    ground: str = "stone",
    frame: str = "square_panel",
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
    if frame not in FRAMES:
        raise ValueError(f"frame is one of {FRAMES}, not {frame}")
    if roof not in ("gable", "gable_cross", "hip"):
        raise ValueError(f"roof is gable, gable_cross or hip, not {roof}")
    if windows not in ("leaded", "shuttered", "shop"):
        raise ValueError(f"windows are leaded, shuttered or shop, not {windows}")
    if contents not in KEEPERS:
        raise ValueError(f"contents is one of {list(KEEPERS)}, not {contents}")
    plan = _Plan(width, depth, floors, jetty, jetty_sides)
    rng = random.Random(seed if seed is not None else hash((width, depth, floors)))
    c = Canvas()
    info: dict = {"stands": {}, "seats": [], "frames": [], "clue": None}
    door_x = _door_x(plan, contents, windows)
    shop = windows == "shop" or KEEPERS[contents] not in (None, "nitwit")
    _shell(c, plan, ground, frame, rng)
    _windows(c, plan, windows, window_boxes, door_x, shop, frame, ground, rng)
    _door(c, plan, door_x)
    _floors(c, plan)
    _stairs(c, plan, info)
    if chimney:
        _fireplace(c, plan, info)
    _roof(c, plan, roof, str(roof_block))
    if chimney:
        _chimney_top(c, plan)
    from house_contents import furnish  # the presets (a separate module)

    furnish(c, plan, contents, door_x, info, rng)
    if info.get("sign"):
        _hanging_sign(c, plan, door_x, SIGN_TEXT[info["sign"]])
    return _to_world(
        c, plan, corner, _facing_name(facing), door_x, contents, ground, info
    )


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
    if windows == "shop" or KEEPERS[contents] not in (None, "nitwit"):
        return max(plan.w - 3, plan.w // 2 + 1)
    return plan.w // 2


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
    ground: str,
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

    def turn(name: str) -> str:
        return COMPASS[(COMPASS.index(name) + steps) % 4]

    blocks = {}
    for (x, y, z), state in c.blocks.items():
        p = world(x, y, z)
        s = BlockState.parse(state)
        blocks[(int(p.x), int(p.y), int(p.z))] = str(s.rotate(steps) if steps else s)
    xs = [k[0] for k in blocks]
    ys = [k[1] for k in blocks]
    zs = [k[2] for k in blocks]
    volume = Volume.from_corners(
        Vec3(min(xs), min(ys), min(zs)), Vec3(max(xs), max(ys), max(zs))
    )
    front = plan.rect(0)[3]
    dx, dz = _turn(steps, 0, 1)
    frames = []
    for (x, y, z), side, item in info["frames"]:
        f = turn(side)
        frames.append(
            (world(x, y, z), {"north": 2, "south": 3, "west": 4, "east": 5}[f], item)
        )
    clue = info.get("clue")
    return House(
        volume=volume,
        door=world(door_x, 0, front),
        outside=world(door_x, 0, front) + Vec3(dx, 0, dz),
        floors=[oy + plan.stand(i) for i in range(plan.n)],
        stands={k: world(*v) for k, v in info["stands"].items()},
        seats=[(world(*p), turn(looks)) for p, looks in info["seats"]],
        keeper=KEEPERS[contents],
        contents=contents,
        facing=facing,
        ground=ground,
        footprint={(k[0], k[2]) for k in blocks},
        blocks=blocks,
        frames=frames,
        clue_spot=None if clue is None else world(clue[0], 0, clue[1]),
        steps=[world(*p) for p in info["steps"]],
        headroom=[world(*p) for p in info["headroom"]],
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
                # doors and beds: the lower half (the foot) first
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
    frame: str = "square_panel",
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
    Build a timber-framed house: white panels in a frame of black beams, a
    beam along each jetty, each upper storey jettied out over the street on
    upside-down stair joists, a steep roof, a brick fireplace with a mantel
    and its chimney (a campfire on top for smoke), plank floors, stairs
    with headroom (or a ladder in a narrow house), lanterns, and the
    furniture of ``contents`` on every floor.

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
    :param frame: "square_panel" (posts every 4), "close_studding" (every 3)
        or "braced" (square panels, a brace in each end panel)
    :param roof: "gable" (the ridge along the street), "gable_cross" (with a
        gable to the street) or "hip"
    :param roof_block: the roof's stairs
    :param chimney: a brick fireplace and chimney
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


# ---------------------------------------------------------------- checks

UP = Vec3(0, 1, 0)
FURNITURE = (
    "_bed",
    "chest",
    "barrel",
    "_slab",
    "_shelf",
    "bookshelf",
    "carpet",
    "loom",
    "smoker",
    "furnace",
    "cauldron",
    "composter",
    "brewing_stand",
    "fletching_table",
    "cartography_table",
    "crafting_table",
    "stonecutter",
    "grindstone",
    "lectern",
    "beehive",
    "hay_block",
    "_wool",
    "candle",
    "flower_pot",
    "potted_",
    "anvil",
    "target",
    "smithing_table",
    "_stairs",
    "cake",
    "decorated_pot",
    "_log",
    "_door",
)


def walk(h: House, extra: dict | None = None) -> set[tuple[int, int, int]]:
    """
    Every cell (feet) a player can stand in, walking from the street in
    front of the door: they need their feet and head free, something to
    stand on (or a ladder), climb at most one block per step and only up a
    stair or slab (no jumping), and need the block over their head free
    while stepping up or down (a step up raises the head 1.8 above the half
    step, into the third block). Ladders are climbed with 2 blocks free
    above. ``extra`` overrides blocks (e.g. a lectern on the clue spot).
    """
    b, v = h.blocks, h.volume
    base = h.floors[0]
    over = extra or {}

    def at(x: int, y: int, z: int) -> str:
        k = (x, y, z)
        if k in over:
            return over[k]
        if k in b:
            return b[k]
        return "minecraft:dirt" if y < base else AIR

    def free(x: int, y: int, z: int) -> bool:
        return passable(at(x, y, z))

    def ladder(x: int, y: int, z: int) -> bool:
        return "ladder" in at(x, y, z)

    def support(x: int, y: int, z: int) -> bool:
        s = at(x, y - 1, z)
        return not passable(s) and not any(
            k in s for k in ("fence", "_wall", "pane", "campfire")
        )

    def stand(x: int, y: int, z: int) -> bool:
        return (
            free(x, y, z)
            and free(x, y + 1, z)
            and (support(x, y, z) or ladder(x, y, z) or ladder(x, y - 1, z))
        )

    def step_up(x: int, y: int, z: int) -> bool:
        """is the block at (x, y, z) one a player walks up onto?"""
        s = at(x, y, z)
        return ("_stairs" in s and "half=top" not in s) or (
            "_slab" in s and "type=bottom" in s
        )

    start = (int(h.outside.x), int(h.outside.y), int(h.outside.z))
    seen, todo = {start}, [start]
    lo, hi = v.start, v.end
    while todo:
        x, y, z = todo.pop()
        moves = []
        for dx, dz in STEP.values():
            nx, nz = x + dx, z + dz
            if stand(nx, y, nz):
                moves.append((nx, y, nz))
            if (
                stand(nx, y + 1, nz)
                and free(x, y + 2, z)
                and (step_up(nx, y, nz) or ladder(x, y, z))
            ):
                moves.append((nx, y + 1, nz))
            for drop in (1, 2, 3):
                # down a step or a drop: free from head height at the
                # start down to the feet at the end
                if not all(free(nx, y + 1 - k, nz) for k in range(drop + 2)):
                    break
                if stand(nx, y - drop, nz):
                    moves.append((nx, y - drop, nz))
                    break
        if ladder(x, y, z) or ladder(x, y - 1, z):
            if ladder(x, y, z) and free(x, y + 1, z) and free(x, y + 2, z):
                moves.append((x, y + 1, z))
            if ladder(x, y - 1, z):
                moves.append((x, y - 1, z))
        for q in moves:
            if q in seen or not (
                lo.x - 1 <= q[0] <= hi.x + 1
                and lo.z - 1 <= q[2] <= hi.z + 1
                and lo.y <= q[1] <= hi.y
            ):
                continue
            seen.add(q)
            todo.append(q)
    return seen


def _cell(p: Vec3) -> tuple[int, int, int]:
    return (int(p.x), int(p.y), int(p.z))


def wall_share(h: House) -> float | None:
    """the white share of the timber walls: calcite / (calcite + beams),
    over the timber storeys (above a stone ground storey) and the gables;
    None for a cottage of stone"""
    if h.ground == "stone" and len(h.floors) == 1:
        return None
    lowest = h.floors[1] - 1 if h.ground == "stone" else h.floors[0]
    white = dark = 0
    for (_x, y, _z), s in h.blocks.items():
        if y < lowest:
            continue
        name = _name(s)
        if name == INFILL:
            white += 1
        elif name == BEAM:
            dark += 1
    return white / max(1, white + dark)


def furnished(h: House) -> list[int]:
    """the number of furniture blocks on each storey (inside, from its floor
    up to its ceiling)"""
    out = []
    x1, x2 = h.volume.start.x, h.volume.end.x
    z1, z2 = h.volume.start.z, h.volume.end.z
    steps = {_cell(p) for p in h.steps}
    for y in h.floors:
        n = 0
        for (x, by, z), s in h.blocks.items():
            if not (y <= by <= y + 2 and x1 < x < x2 and z1 < z < z2):
                continue
            if (x, by, z) in steps or s.startswith(DOOR) or s.startswith(BEAM):
                continue
            if any(k in _name(s) for k in FURNITURE) and not _outer(h, x, by, z):
                n += 1
        out.append(n)
    return out


def _outer(h: House, x: int, y: int, z: int) -> bool:
    """is (x, y, z) in or on the outside of the house's walls? (window boxes,
    shutters, the shop counter)"""
    for dx, dz in STEP.values():
        k = 1
        while k < 20:
            s = h.blocks.get((x + dx * k, y, z + dz * k))
            if s is None:
                return True
            if _name(s) in (
                INFILL,
                BEAM,
                STONE,
                QUOIN,
                PANE,
                "minecraft:mossy_cobblestone",
            ):
                break
            k += 1
    return False


def house_problems(h: House) -> list[str]:
    """what is wrong with a house: see the module's docstring"""
    b, out = h.blocks, []
    v = h.volume
    outside = [k for k in b if not v.inside(Vec3(*k))]
    if outside:
        out.append(f"{len(outside)} blocks outside the volume, e.g. {outside[0]}")
    step = h.outside - h.door
    inside = h.door - step

    def free_at(p: Vec3) -> bool:
        return passable(b.get(_cell(p), AIR))

    for name, p in (("outside", h.outside), ("inside", inside)):
        if not (free_at(p) and free_at(p + UP)):
            out.append(f"the door's {name} cell {p} is not free")
    if "door" not in b.get(_cell(h.door), ""):
        out.append(f"no door at {h.door}")
    reach = walk(h)
    for k, y in enumerate(h.floors):
        if not any(p[1] == y for p in reach):
            out.append(f"storey {k} (y {y}) cannot be reached by a walker")
    for name, p in h.stands.items():
        if _cell(p) not in reach:
            out.append(f"stand {name} at {p} cannot be reached")
        below = b.get(_cell(p - UP), AIR)
        if not (free_at(p) and free_at(p + UP)) or passable(below):
            out.append(f"stand {name} at {p} is not free floor ({b.get(_cell(p))})")
    for hp in h.headroom:
        s = b.get(_cell(hp), AIR)
        if not passable(s):
            out.append(f"headroom {hp} over the stairs is {s}")
    for p, looks in h.seats:
        s = b.get(_cell(p), "")
        back = OPP[looks]
        if f"facing={back}" not in s:
            out.append(f"seat at {p} looking {looks} is {s}")
        dx, dz = STEP[looks]
        if "slab[type=top]" in b.get((int(p.x) - dx, int(p.y), int(p.z) - dz), ""):
            out.append(f"seat at {p} looking {looks} has its back to a table")
        if "slab[type=top]" not in b.get((int(p.x) + dx, int(p.y), int(p.z) + dz), ""):
            out.append(f"seat at {p} looking {looks} has no table in front")
        if not any(
            (int(p.x) + ex, int(p.y), int(p.z) + ez) in reach
            for ex, ez in STEP.values()
        ):
            out.append(f"seat at {p} cannot be reached")
    if h.clue_spot is not None:
        c = _cell(h.clue_spot)
        if not (free_at(h.clue_spot) and free_at(h.clue_spot + UP)):
            out.append(f"the clue spot {h.clue_spot} is not free")
        with_lectern = walk(h, {c: "minecraft:lectern"})
        for k, y in enumerate(h.floors):
            if not any(p[1] == y for p in with_lectern):
                out.append(f"a lectern on the clue spot cuts off storey {k}")
        for name, p in h.stands.items():
            if _cell(p) not in with_lectern:
                out.append(f"a lectern on the clue spot cuts off stand {name}")
        if not any(
            (c[0] + ex, c[1], c[2] + ez) in with_lectern for ex, ez in STEP.values()
        ):
            out.append("the clue spot cannot be reached")
    else:
        out.append("no clue spot")
    share = wall_share(h)
    if share is not None and share < 0.6:
        out.append(f"the walls are only {share:.0%} white (want 60%+)")
    for k, n in enumerate(furnished(h)):
        if n < 5:
            out.append(f"storey {k} has only {n} pieces of furniture")
    return out
