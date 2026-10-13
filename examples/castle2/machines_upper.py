"""
castle2's machines (phase 6): plain redstone that works in survival and
adventure mode without mciwb. Each machine has a ``*_cells`` function giving
the positions of its parts (local coordinates mapped to the world by ``pos``,
castle2_layout.V by default, a rig's translation in machines_rig.py), used by
the build and by verify_castle2 alike, and each opens a secret
(castle2_layout.SECRETS).

- the lectern lock (library): a 15-page book on a lectern in the bookcase
  wall; turned to page LECTERN_PAGE, a bookcase slides aside onto a hidden
  study. Exact match: a subtract comparator takes LECTERN_PAGE - 1 from the
  page, and two repeaters tapping the next two dusts pass only a 1.
- the astrolabe (alchemist's tower, ground floor): six floor levers round a
  gnomon; set to the pattern of the star chart on the wall, a floor panel by
  the door slides open onto a ladder down to the alchemist's cellar.
- the engine (alchemist's tower, top floor, castle's): a copper pipe of
  torches carries the astrolabe's state up the tower; while the astrolabe is
  set, the engine's east chase ends in a lamp and a bell that ring with it.
- the transmuter (alchemist's tower, third floor): drop an amethyst shard
  into its hopper and it comes back in the tray with a nether star; anything
  else goes to the reject tray. An item sorter (a filter hopper with 18 keys
  and four barriers, a subtract comparator and a torch lock) and a dropper.
- the copper puzzle (vault, west wall): two rows of waxed copper bulbs and
  buttons on a checkerboard; each button toggles the bulbs beside it (above,
  below, left, right). With every bulb lit the inner vault's door slides open.
- the organ (chapel): see organ.py.
"""

from __future__ import annotations

import castle_lib as L
from castle2_layout import (
    ASTROLABE_CHART,
    ASTROLABE_LEVERS,
    ASTROLABE_PANEL,
    COPPER_GRID,
    COPPER_START,
    INNER_VAULT_DOOR,
    LECTERN_LOCK,
    LECTERN_PAGE,
    TRANSMUTER,
    TRANSMUTER_KEY,
    TRANSMUTER_REWARD,
    YU,
    V,
)
from castle_layout import ENGINE

from mciwb.imports import Vec3

# the interactions an adventure-mode player has (no breaking or placing):
# verify checks every machine's trigger is one of these
ADVENTURE_OK = (
    "minecraft:lever",
    "#minecraft:buttons",
    "minecraft:lectern",
    "#minecraft:pressure_plates",
    "minecraft:hopper",
    "minecraft:target",
    "minecraft:tripwire",
    "#minecraft:doors",
    "#minecraft:trapdoors",
    "#minecraft:fence_gates",
    "minecraft:chest",
    "minecraft:barrel",
    "minecraft:note_block",
)

UP = Vec3(0, 1, 0)
COMPASS = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}
STONE = "minecraft:stone"
AIR = L.AIR
DUST = L.DUST
# a lone dust powers its four sides only as a cross (a placed dot powers none)
CROSS = "minecraft:redstone_wire[north=side,south=side,east=side,west=side]"


def compass(d: Vec3) -> str:
    return COMPASS[(int(d.x), int(d.z))]


class Frame:
    """local cells ``base + u*a + v*b + up*h`` (u, v horizontal), mapped to
    the world by pos"""

    def __init__(self, base: tuple[int, int, int], u: Vec3, v: Vec3, pos=V):
        self.base, self.u, self.v, self.pos = base, u, v, pos

    def __call__(self, a: int, b: int, h: int = 0) -> Vec3:
        x, y, z = self.base
        p = Vec3(x, y, z) + self.u * a + self.v * b + UP * h
        return self.pos(p.x, p.y, p.z)

    def face(self, d: str) -> str:
        """the compass name of "u", "-u", "v" or "-v" """
        vec = {"u": self.u, "-u": self.u * -1, "v": self.v, "-v": self.v * -1}[d]
        return compass(vec)


def set_at(p: Vec3, block: str) -> None:
    L.set_block(p, block)


def fill(a: Vec3, b: Vec3, block: str) -> None:
    L.fill(a, b, block)


def diode(kind: str, toward_input: str, extra: str = "") -> str:
    """a repeater or comparator facing its input (castle's convention:
    ``facing`` is the side the input comes from)"""
    more = f",{extra}" if extra else ""
    return f"minecraft:{kind}[facing={toward_input}{more}]"


def wall_torch(facing: str, lit: bool = True) -> str:
    return f"minecraft:redstone_wall_torch[facing={facing},lit={str(lit).lower()}]"


# ---------------------------------------------------------------- the sliding door


def door_cells(f: Frame, mode: str) -> dict:
    """the parts of a `slide_door`"""
    cells = {
        "door": [f(0, 0, 0), f(0, 0, 1)],
        "slot": [f(0, 1, 0), f(0, 1, 1)],
        "pistons": [f(0, 2, 0), f(0, 2, 1)],
        "inside": f(1, 0, 0),
    }
    if mode == "torch":
        cells["torch"] = f(1, 2, 1)
        cells["input"] = f(2, 2, 1)  # the block whose power opens the door
    else:
        cells["repeater"] = f(1, 2, 1)
        cells["input"] = f(2, 2, 1)  # the cell whose power (dust) closes it
    return cells


def slide_door(f: Frame, material: str, mode: str, pilaster: str = "") -> dict:
    """
    A two-high door of ``material`` in a wall plane (a = 0), opening into the
    space behind (a > 0) as castle_lib.hidden_door's: sticky pistons at b = 2
    (extended into b = 1) hold the door at b = 0 and pull it to b = 1.
    ``mode="torch"``: a redstone torch at (1, 2, 1) on the block (2, 2, 1)
    powers the pistons, so the door is shut until that block is powered.
    ``mode="direct"``: a repeater at (1, 2, 1) fed from (2, 2, 1) powers them,
    so the door is shut while (2, 2, 1) is powered. The caller builds the
    wall round it and wires the input. ``pilaster``: blocks at a = -1,
    b = 1..2 that hide the piston faces from the room.
    """
    c = door_cells(f, mode)
    for h in (0, 1):
        set_at(f(0, 2, h), f"minecraft:sticky_piston[facing={f.face('-v')}]")
        set_at(f(0, 1, h), AIR)
        set_at(f(0, 0, h), material)
    if pilaster:
        for b in (1, 2):
            fill(f(-1, b, 0), f(-1, b, 1), pilaster)
    if mode == "torch":
        set_at(f(2, 2, 1), STONE)
        set_at(f(1, 2, 1), wall_torch(f.face("-u")))
    else:
        set_at(f(1, 2, 0), STONE)
        set_at(f(1, 2, 1), diode("repeater", f.face("u")))
    return c


def door_shut(c: dict, material: str) -> bool:
    return all(L.is_block(p, material) for p in c["door"])


def door_open(c: dict) -> bool:
    return all(L.is_block(p, AIR) for p in c["door"])


# ---------------------------------------------------------------- the lectern lock


def lectern_frame(pos=V) -> Frame:
    # the bookcase wall x 58 of the library, the hidden study behind it (east)
    return Frame(LECTERN_LOCK, Vec3(1, 0, 0), Vec3(0, 0, 1), pos)


LECTERN_BOOK_TITLE = "The Book of Hours"
LECTERN_TEXT = [
    "Prime. The bell for the first hour, and the library opens.",
    "Terce. The scribes at their desks.",
    "Sext. Bread and small beer.",
    "None. The long afternoon of copying.",
    "Vespers. Candles are lit along the shelves.",
    "Compline. The doors are barred.",
    "Matins. Only the librarian is awake.",
    "Lauds. The first light on the east wall.",
    "The eighth leaf is blank but for a blot.",
    "Of the keeping of books: every book has its hour.",
    "Of the keeping of keys: no key is kept in the library.",
    "Of the keeping of secrets: a secret kept by twelve is no secret.",
    "The thirteenth hour, which no bell rings, opens what the other twelve keep shut.",
    "Of the alchemist: his tower has a cellar, and his stars a pattern.",
    "Here ends the Book of Hours.",
]


def book_nbt(title: str, author: str, pages: list[str]) -> str:
    text = ",".join(L.snbt_string(p) for p in pages)
    return (
        f'{{id:"minecraft:written_book",count:1,components:{{"minecraft:written_book_content":'
        f"{{title:{L.snbt_string(title)},author:{L.snbt_string(author)},pages:[{text}]}}}}}}"
    )


def lectern_cells(pos=V) -> dict:
    """the lectern lock's parts: the lectern (trigger), the comparators, the
    door, the study"""
    f = lectern_frame(pos)
    c = door_cells(f, "torch")
    c.update(
        {
            "trigger": f(0, 7, 0),
            "trigger_kind": "minecraft:lectern",
            "reader": f(1, 7, 0),  # subtract: page - (LECTERN_PAGE - 1)
            "constant": [f(1, b, 0) for b in range(8, 12)],
            "source": f(1, 12, 0),
            "taps": [f(2, 6, 0), f(3, 6, 0)],
            "gate": f(2, 5, 0),
            "study": f(2, 8, 2),
            "chest": f(1, 11, 2),
            "material": "minecraft:bookshelf",
        }
    )
    return c


def lectern_lock(pos=V) -> dict:
    """
    The lectern lock in the library's east bookcase wall (frame: a east into
    the partition, b south along the wall, h up from the library floor).
    The lectern (0, 7, 0) stands in a niche of the bookcase wall; behind it,
    inside the partition at the floor's level:

    - the reader (1, 7, 0), a comparator in subtract mode, takes the page
      number (a 15-page book gives page = signal) and subtracts LECTERN_PAGE
      - 1, given by four dusts from a redstone block (1, 12, 0): 15 - 3;
    - its output runs along two dusts (2, 7, 0) and (3, 7, 0); repeaters
      beside them (2, 6, 0) and (3, 6, 0) pass "at least 1" and "at least 2";
    - the gate (2, 5, 0), a subtract comparator, gives 15 only for "at least
      1 and not at least 2", that is page == LECTERN_PAGE, up a dust step to
      the door's torch block: the bookcase door at b = 0 opens.

    Behind the door, a vestibule and two steps up to the study, which sits
    on the wiring (its floor is at h = 1), with a chest of treasure.
    """
    f = lectern_frame(pos)
    c = lectern_cells(pos)
    shelf = c["material"]
    brick = L.BRICK
    # the partition behind the wall, solid, then carve
    fill(f(1, -1, 0), f(3, 12, 6), brick)
    # the bookcase wall face, the door and its pistons
    fill(f(0, -1, 0), f(0, 11, 2), shelf)
    slide_door(f, shelf, "torch", pilaster=shelf)
    for b in (1, 2):
        set_at(f(-1, b, 2), f"{L.BRICK_SLAB}[type=bottom]")
    # the vestibule behind the door, and the stairwell up to the study
    fill(f(1, 0, 0), f(3, 1, 3), AIR)
    fill(f(1, 2, 2), f(3, 4, 4), AIR)
    set_at(f(3, 2, 0), f"minecraft:stone_brick_stairs[facing={f.face('v')}]")
    set_at(f(3, 2, 1), AIR)
    set_at(f(3, 3, 1), f"minecraft:stone_brick_stairs[facing={f.face('v')}]")
    set_at(f(2, 3, 1), DUST)  # the step of dust up to the torch block
    set_at(f(2, 4, 1), "minecraft:smooth_stone_slab[type=bottom]")  # lets it climb
    set_at(f(1, 2, 0), brick)
    # the wiring, at the library's floor level
    set_at(f(0, 7, 0), AIR)
    book = book_nbt(LECTERN_BOOK_TITLE, "Brother Bede", LECTERN_TEXT)
    set_at(
        f(0, 7, 0),
        f"minecraft:lectern[facing={f.face('-u')},has_book=true]{{Book:{book},Page:0}}",
    )
    set_at(f(1, 7, 0), diode("comparator", f.face("-u"), "mode=subtract"))
    for p in c["constant"]:
        set_at(p, DUST)
    set_at(c["source"], "minecraft:redstone_block")
    set_at(f(2, 7, 0), DUST)
    set_at(f(3, 7, 0), DUST)
    set_at(f(2, 6, 0), diode("repeater", f.face("v")))
    set_at(f(3, 6, 0), diode("repeater", f.face("v")))
    set_at(f(2, 5, 0), diode("comparator", f.face("v"), "mode=subtract"))
    set_at(f(3, 5, 0), DUST)
    set_at(f(2, 4, 0), DUST)
    # the study: floor over the wiring, walls, ceiling, furniture
    fill(f(1, 4, 1), f(3, 11, 1), "minecraft:spruce_planks")
    set_at(f(2, 4, 1), "minecraft:smooth_stone_slab[type=bottom]")
    fill(f(1, 5, 2), f(3, 11, 4), AIR)
    fill(f(1, 4, 5), f(3, 11, 5), "minecraft:spruce_planks")
    set_at(f(2, 0, 3), f"{L.SOUL_LANTERN}[hanging=true]")
    set_at(f(2, 8, 4), f"{L.LANTERN}[hanging=true]")
    set_at(f(3, 10, 2), "minecraft:spruce_slab[type=top]")
    set_at(f(3, 9, 2), "minecraft:spruce_slab[type=top]")
    set_at(f(3, 10, 3), "minecraft:white_candle[candles=3,lit=true]")
    set_at(f(1, 6, 2), "minecraft:bookshelf")
    set_at(f(1, 7, 2), "minecraft:bookshelf")
    chest = c["chest"]
    items = [
        ("amethyst_shard", 4),  # the transmuter's ingredient
        ("diamond", 6),
        ("gold_ingot", 12),
        ("map", 1),
        ("spyglass", 1),
    ]
    data = ",".join(
        f'{{Slot:{k}b,id:"minecraft:{i}",count:{n}}}' for k, (i, n) in enumerate(items)
    )
    set_at(chest, f"minecraft:chest[facing={f.face('u')}]{{Items:[{data}]}}")
    return c


# ---------------------------------------------------------------- the copper puzzle


def copper_frame(pos=V) -> Frame:
    # the vault's west wall x 49; a west (back), b south, h up
    return Frame(COPPER_GRID, Vec3(-1, 0, 0), Vec3(0, 0, 1), pos)


def inner_door_frame(pos=V) -> Frame:
    return Frame(INNER_VAULT_DOOR, Vec3(-1, 0, 0), Vec3(0, 0, 1), pos)


COPPER_COLUMNS = 6


def bulb_at(b: int, h: int) -> bool:
    """a checkerboard: row 0's bulbs in the even columns, row 1's in the odd"""
    return (b + h) % 2 == 0


def copper_toggles(b: int, h: int) -> list[tuple[int, int]]:
    """the bulbs the button at (b, h) toggles: those beside it"""
    return [
        (bb, hh)
        for bb, hh in ((b - 1, h), (b + 1, h), (b, h - 1), (b, h + 1))
        if 0 <= bb < COPPER_COLUMNS and hh in (0, 1)
    ]


def copper_cells(pos=V) -> dict:
    f = copper_frame(pos)
    bulbs = {
        (b, h): f(0, b, h)
        for b in range(COPPER_COLUMNS)
        for h in (0, 1)
        if bulb_at(b, h)
    }
    buttons = {
        (b, h): f(0, b, h)
        for b in range(COPPER_COLUMNS)
        for h in (0, 1)
        if not bulb_at(b, h)
    }
    g = inner_door_frame(pos)
    c = door_cells(g, "direct")
    c.update(
        {
            "bulbs": bulbs,
            "buttons": buttons,
            "button_facing": f.face("-u"),
            "trigger": list(buttons.values())[0],
            "trigger_kind": "#minecraft:buttons",
            "material": "minecraft:polished_blackstone_bricks",
            "inner": g(4, 0, 0),
        }
    )
    return c


def copper_puzzle(pos=V) -> dict:
    """
    The copper puzzle in the vault's west wall (a west into the wall, b
    south, h up from row 0). Bulbs and buttons alternate in two rows; a
    pressed button powers the bulbs beside it in the wall (a button powers
    its neighbours as well as the block it is on), which toggle. Behind each
    bulb a comparator reads it (row 1's straight behind, standing on row 0's
    button blocks; row 0's through a block, one further back), its output
    block carries a torch (lit while the bulb is dark), and the torches feed
    two dust lines: row 0's at a = 4, row 1's (through the blocks over its
    torches) at a = 3, h = 3. Either line, while any bulb is dark, powers the
    inner vault's door shut (a "direct" slide_door north of the grid).
    """
    f = copper_frame(pos)
    c = copper_cells(pos)
    shell = c["material"]
    # the machine block behind the wall and the inner vault, solid first
    fill(f(1, -9, -2), f(9, COPPER_COLUMNS + 4, 5), STONE)
    for (b, h), p in c["bulbs"].items():
        lit = (b, h) in COPPER_START
        set_at(p, f"minecraft:waxed_copper_bulb[lit={str(lit).lower()}]")
        if h == 1:
            set_at(f(1, b, 1), diode("comparator", f.face("-u")))  # reads the bulb
            set_at(f(2, b, 1), STONE)  # its output block
            set_at(f(3, b, 1), wall_torch(f.face("u"), not lit))
            set_at(f(3, b, 2), STONE)  # powered by the torch: the dust on it
        else:
            set_at(f(1, b, 0), STONE)  # read through
            set_at(f(2, b, 0), diode("comparator", f.face("-u")))
            set_at(f(3, b, 0), STONE)
            set_at(f(4, b, 0), wall_torch(f.face("u"), not lit))
            set_at(f(4, b, 1), AIR)
    for (b, h), p in c["buttons"].items():
        set_at(f(1, b, h), STONE)
        set_at(
            p,
            f"minecraft:polished_blackstone_button[face=wall,facing={c['button_facing']}]",
        )
    # the two lines: row 0's at a = 5 (beside its torches), row 1's at h = 3
    # (on the blocks over its torches)
    for b in range(COPPER_COLUMNS):
        set_at(f(5, b, 0), DUST)
        set_at(f(3, b, 2), STONE)
        set_at(f(3, b, 3), DUST)
    # north of the grid they meet at (5, -2, 1): row 1's steps down from
    # (3, -1, 3), row 0's climbs from (5, -1, 0); then down to (5, -3, 0) and
    # west along b = -3 to the door's input (2, -3, 0)
    set_at(f(3, -1, 3), DUST)
    set_at(f(3, -2, 3), DUST)
    set_at(f(4, -2, 3), AIR)
    set_at(f(4, -2, 2), DUST)
    set_at(f(5, -2, 2), AIR)
    set_at(f(5, -2, 1), DUST)
    set_at(f(5, -1, 0), DUST)
    set_at(f(5, -1, 1), AIR)
    set_at(f(5, -3, 1), AIR)
    for a in (5, 4, 3, 2):
        set_at(f(a, -3, 0), DUST)
    g = inner_door_frame(pos)
    # the inner vault behind the door
    fill(g(1, -6, -1), g(7, 1, 3), shell)
    fill(g(1, -5, 0), g(6, 1, 2), AIR)
    fill(g(1, -5, -1), g(6, 1, -1), "minecraft:polished_blackstone")
    slide_door(g, shell, "direct", pilaster=shell)
    set_at(g(-1, 1, 2), "minecraft:polished_blackstone_brick_slab[type=bottom]")
    set_at(g(-1, 2, 2), "minecraft:polished_blackstone_brick_slab[type=bottom]")
    return c


# ---------------------------------------------------------------- the astrolabe


def astrolabe_cells(pos=V) -> dict:
    levers = {
        (x, z): pos(x, YU, z)
        for (x, z) in ASTROLABE_LEVERS  # lever on the floor
    }
    px, pz = ASTROLABE_PANEL
    return {
        "levers": levers,
        "trigger": next(iter(levers.values())),
        "trigger_kind": "minecraft:lever",
        "piston": pos(px + 2, YU - 1, pz),
        "panel": pos(px, YU - 1, pz),
        "hole": pos(px, YU - 1, pz),
        "panel_block": "minecraft:dark_oak_planks",
        "cellar": pos(18, 11, 22),
        "column": [pos(22, y, 24) for y in range(13, 42)],
        "top": pos(22, YU + 24, 24),  # the dust beside the engine's gate
    }


def astrolabe(pos=V, cellar: bool = True) -> dict:
    """
    The astrolabe: six levers on the laboratory floor (x 16 and 20, z 20,
    22, 24) round a gnomon. Each lever powers the plank under it, and the
    dust under that plank (y 16); below, at y 15, a station per lever: a
    lever that must be ON has a torch on the block under its dust (lit while
    the lever is off), one that must be OFF lets its dust step down. The
    stations feed two buses (x 14 and x 18, y 15) joined along z 26: while
    any lever is wrong the bus powers the sticky piston at (21, 17, 25),
    which holds the floor panel at (19, 17, 25) shut; all right, it pulls the
    panel aside and the ladder below leads down to the cellar. The bus also
    feeds a copper pipe of torches up the tower's east wall to the engine.
    """
    c = astrolabe_cells(pos)
    # solid under the laboratory: y 12..16, then carve
    fill(pos(14, 15, 18), pos(22, 16, 28), STONE)
    fill(pos(14, 12, 18), pos(22, 14, 28), STONE)
    for (x, z), want in ASTROLABE_LEVERS.items():
        set_at(pos(x, YU - 1, z), "minecraft:dark_oak_planks")
        set_at(pos(x, YU, z), "minecraft:lever[face=floor,facing=north,powered=false]")
        set_at(pos(x, 16, z), DUST)
        set_at(pos(x - 1, 16, z), AIR)
        if want:  # must be on: a torch, lit while the lever is off
            set_at(pos(x - 1, 15, z), wall_torch("west"))
        else:  # must be off: its dust steps down to the bus
            set_at(pos(x - 1, 15, z), DUST)
    for z in range(20, 27):
        set_at(pos(14, 15, z), DUST)
        set_at(pos(18, 15, z), DUST)
    for x in range(14, 19):
        set_at(pos(x, 15, 26), DUST)
    # the bus's end: a repeater south, a line east, to the piston and the pipe
    set_at(pos(18, 15, 27), diode("repeater", "north"))
    for x in range(18, 23):
        set_at(pos(x, 15, 28), DUST)
    set_at(pos(21, 16, 28), AIR)
    set_at(pos(21, 16, 27), DUST)
    set_at(pos(21, 16, 26), diode("repeater", "south"))
    set_at(pos(21, 16, 25), STONE)  # under the piston
    set_at(pos(22, 15, 27), AIR)
    set_at(pos(22, 14, 27), DUST)
    set_at(pos(22, 14, 26), AIR)
    set_at(pos(22, 13, 26), DUST)
    set_at(pos(22, 13, 25), diode("repeater", "south"))
    # the panel: piston (21, 17, 25) facing west, head, panel (19, 17, 25)
    px, pz = ASTROLABE_PANEL
    set_at(pos(px + 2, YU - 1, pz), "minecraft:sticky_piston[facing=west]")
    set_at(pos(px + 1, YU - 1, pz), AIR)
    set_at(pos(px, YU - 1, pz), c["panel_block"])
    # the shaft and the cellar
    for y in range(12, 17):
        set_at(pos(px, y, pz), AIR)
    for y in range(14, 17):
        set_at(pos(px, y, pz), "minecraft:ladder[facing=west]")
    fill(pos(15, 11, 19), pos(21, 13, 25), AIR)
    if cellar:  # (a rig leaves out the cellar's floor)
        fill(pos(15, 10, 19), pos(21, 10, 25), "minecraft:polished_deepslate")
    set_at(pos(18, 13, 22), f"{L.SOUL_LANTERN}[hanging=true]")
    set_at(pos(15, 11, 19), "minecraft:brewing_stand")
    set_at(pos(16, 11, 19), "minecraft:cauldron")
    items = [
        ("amethyst_shard", 4),
        ("blaze_rod", 3),
        ("experience_bottle", 16),
        ("golden_apple", 2),
        ("ender_pearl", 4),
    ]
    data = ",".join(
        f'{{Slot:{k}b,id:"minecraft:{i}",count:{n}}}' for k, (i, n) in enumerate(items)
    )
    set_at(pos(20, 11, 21), f"minecraft:chest[facing=west]{{Items:[{data}]}}")
    # the gnomon in the middle of the levers
    set_at(pos(18, YU, 22), "minecraft:gold_block")
    set_at(pos(18, YU + 1, 22), "minecraft:lightning_rod")
    # the star chart on the west wall: a lit star for each lever that must be on
    for (x, z), want in ASTROLABE_LEVERS.items():
        cx, cy, cz = ASTROLABE_CHART[(x, z)]
        block = "minecraft:sea_lantern" if want else "minecraft:black_concrete"
        set_at(pos(cx, cy, cz), block)
    L.sign(
        pos(14, YU + 4, 22),
        "dark_oak_wall_sign[facing=east]",
        "As above,",
        "so below.",
        "The near stars high,",
        "the far stars low.",
    )
    # the copper pipe up the east wall: torches and blocks to the engine
    pipe(pos)
    return c


def pipe(pos=V) -> None:
    """a column at (22, y, 24): the base block (y 13) is powered while the
    astrolabe is wrong; torches at even y, blocks at odd y (floors at y 25,
    33 and 41 included), so the torch at y 40 is lit while it is wrong and
    powers the floor block over it and the dust on that"""
    for y in range(13, 42):
        p = pos(22, y, 24)
        if y % 2:
            floor = y in (25, 33, 41)
            set_at(
                p,
                "minecraft:dark_oak_planks" if floor else "minecraft:waxed_cut_copper",
            )
        else:
            # lit while wrong when (y - 14) / 2 is odd
            set_at(
                p,
                f"minecraft:redstone_torch[lit={str(((y - 14) // 2) % 2 == 1).lower()}]",
            )
    set_at(pos(22, YU + 24, 24), DUST)


# ---------------------------------------------------------------- the engine


def engine_cells(pos=V) -> dict:
    cx, cz, ey = ENGINE
    return {
        "gate": pos(cx + 4, ey, cz + 1),
        "lamp": pos(cx + 5, ey, cz + 1),
        "bell": pos(cx + 5, ey + 1, cz + 1),
        "chase": pos(cx + 3, ey, cz + 1),  # castle's lamp, now dust to the gate
        "set_line": pos(cx + 4, ey, cz + 2),
    }


def engine_purpose(pos=V) -> dict:
    """the end of the engine's east chase: castle's lamp at (21, 42, 23) is
    dust into a subtract comparator, gated by the astrolabe's pipe (15 while
    it is wrong); while it is set, each shard passing the comparator lights a
    lamp in the wall and rings a bell above it"""
    c = engine_cells(pos)
    set_at(c["chase"], DUST)
    set_at(c["gate"], diode("comparator", "west", "mode=subtract"))
    set_at(c["lamp"], "minecraft:redstone_lamp")
    set_at(c["bell"], "minecraft:bell[attachment=single_wall,facing=west]")
    return c


# ---------------------------------------------------------------- the transmuter


def transmuter_cells(pos=V) -> dict:
    x, y, z = TRANSMUTER  # the filter hopper
    return {
        "input": pos(x - 1, y + 1, z - 1),  # drop the ingredient on this hopper
        "trigger": pos(x - 1, y + 1, z - 1),
        "trigger_kind": "minecraft:hopper",
        "filter": pos(x, y, z),
        "lower": pos(x, y - 1, z),  # locked; pulls one key when unlocked
        "collector": pos(x, y - 2, z),
        "tray": pos(x - 1, y - 2, z),  # the key and the reward come back here
        "reject": pos(x - 1, y, z + 1),  # anything else comes back here
        "reward_dropper": pos(x - 1, y - 2, z + 1),
        "reader": pos(x + 1, y, z),
        "lock": pos(x, y - 1, z - 1),
        "lamp": pos(x, y - 1, z + 2),
        "note": pos(x, y - 2, z + 3),
    }


def item_list(items: list[tuple[str, int]]) -> str:
    return ",".join(
        f'{{Slot:{k}b,id:"minecraft:{i}",count:{n}}}' for k, (i, n) in enumerate(items)
    )


FILTER_ITEMS = [(TRANSMUTER_KEY, 18)] + [("barrier", 1)] * 4


def transmuter(pos=V) -> dict:
    """
    The transmuter against the third floor's east wall (filter hopper at
    TRANSMUTER = (20, 36, 22)), a classic item sorter. An item dropped on
    the input hopper (19, 37, 21) runs along the stream hoppers over the
    filter hopper, which holds 18 keys and four barriers (so it takes only a
    key) and faces into the casing (so it never pushes). Its comparator
    (east) reads 2 with the extra key: two dusts on, a repeater turns the
    lock comparator (15 from a redstone block, less the repeater) off, and
    the locked hopper under the filter pulls one key; the collector hopper
    under that takes it (a hopper pulls from a locked one) and passes it
    west into the tray chest. The collector's comparator fires the reward
    dropper into the tray, lights a lamp and plays a note block. Any other
    item runs on to the reject chest. Casing of waxed copper and gold.
    """
    c = transmuter_cells(pos)
    x, y, z = TRANSMUTER
    copper, cut, gold = (
        "minecraft:waxed_copper_block",
        "minecraft:waxed_cut_copper",
        "minecraft:gold_block",
    )
    # the casing x 19..22, z 19..23, y 34..39 (the pipe is at (22, y, 24))
    fill(pos(x - 1, y - 2, z - 3), pos(x + 2, y + 3, z + 1), cut)
    fill(pos(x - 1, y + 3, z - 3), pos(x + 2, y + 3, z + 1), copper)
    fill(pos(x - 1, y - 2, z - 3), pos(x - 1, y - 2, z + 1), gold)
    # the stream: input -> (20,37,21) -> (20,37,22) -> (20,37,23) -> (19,37,23) -> reject
    set_at(pos(x - 1, y + 1, z - 1), "minecraft:hopper[facing=east]")
    set_at(pos(x - 1, y + 2, z - 1), AIR)  # room over the input to drop things in
    set_at(pos(x, y + 1, z - 1), "minecraft:hopper[facing=south]")
    set_at(pos(x, y + 1, z), "minecraft:hopper[facing=south]")
    set_at(pos(x, y + 1, z + 1), "minecraft:hopper[facing=west]")
    set_at(pos(x - 1, y + 1, z + 1), "minecraft:hopper[facing=down]")
    set_at(pos(x - 1, y, z + 1), "minecraft:chest[facing=west]")
    # the filter (facing into the casing), its reader and threshold
    set_at(
        pos(x, y, z),
        f"minecraft:hopper[facing=west]{{Items:[{item_list(FILTER_ITEMS)}]}}",
    )
    set_at(pos(x + 1, y, z), diode("comparator", "west"))
    set_at(pos(x + 2, y, z), DUST)  # 2 with the extra key, 1 without
    set_at(pos(x + 2, y, z - 1), AIR)
    set_at(pos(x + 2, y - 1, z - 1), DUST)  # 1 with the key, 0 without
    set_at(pos(x + 1, y - 1, z - 1), diode("repeater", "east"))
    # the lock: 15 from the redstone block, less the repeater, into the lower hopper
    set_at(pos(x, y - 1, z - 2), "minecraft:redstone_block")
    # (built giving its 15 already, so that the hopper is locked from the start)
    set_at(
        pos(x, y - 1, z - 1),
        diode("comparator", "north", "mode=subtract,powered=true")
        + "{OutputSignal:15}",
    )
    set_at(pos(x, y - 1, z), "minecraft:hopper[facing=down,enabled=false]")
    set_at(pos(x, y - 2, z), "minecraft:hopper[facing=west]")
    set_at(pos(x - 1, y - 2, z), "minecraft:chest[facing=west]")
    set_at(pos(x - 1, y - 1, z), "minecraft:waxed_copper_grate")  # the tray opens
    # the reward: the collector's comparator, its block, the dropper
    rewards = [(TRANSMUTER_REWARD, 16)]
    set_at(
        pos(x - 1, y - 2, z + 1),
        f"minecraft:dropper[facing=north]{{Items:[{item_list(rewards)}]}}",
    )
    set_at(pos(x, y - 2, z + 1), diode("comparator", "north"))
    set_at(pos(x, y - 2, z + 2), cut)
    set_at(pos(x - 1, y - 2, z + 2), CROSS)  # beside the block, into the dropper
    set_at(pos(x, y - 1, z + 2), "minecraft:redstone_lamp")
    set_at(pos(x, y - 2, z + 3), "minecraft:note_block[instrument=chime,note=18]")
    set_at(pos(x, y - 1, z + 3), AIR)
    return c


# ---------------------------------------------------------------- working them
# Each ``work_*`` works a machine over RCON in place and puts it back as
# built, reporting through ``check(name, ok)`` (verify_castle.check, or the
# rig's). ``pos`` maps local to world coordinates.


def poke(p: Vec3) -> None:
    """re-place a dust so that it sees a lever set by command"""
    L.cmd(f"setblock {p.x} {p.y} {p.z} minecraft:air")
    L.cmd(f"setblock {p.x} {p.y} {p.z} minecraft:redstone_wire")


def wait_for(cond, ticks: int = 40) -> bool:
    return L.wait_until(cond, ticks)


def trigger_ok(c: dict) -> bool:
    """is the machine's trigger an interaction an adventure player has?"""
    return L.is_block(c["trigger"], c["trigger_kind"])


def set_page(p: Vec3, page: int) -> None:
    """turn a lectern's book to a page (1..)"""
    L.cmd(f"data modify block {p.x} {p.y} {p.z} Page set value {page - 1}")


def work_lectern(check, pos=V) -> None:
    c = lectern_cells(pos)
    shelf = c["material"]
    check("lectern lock: the lectern holds the Book of Hours", trigger_ok(c))
    check("lectern lock: the bookcase door starts shut", door_shut(c, shelf))
    try:
        for page in (LECTERN_PAGE - 1, LECTERN_PAGE + 1):
            set_page(c["trigger"], page)
            L.tick(10)
            check(f"lectern lock: page {page} leaves it shut", door_shut(c, shelf))
        set_page(c["trigger"], LECTERN_PAGE)
        check(
            f"lectern lock: page {LECTERN_PAGE} opens the door",
            wait_for(lambda: door_open(c), 20),
        )
        set_page(c["trigger"], 1)
        check(
            "lectern lock: another page shuts it",
            wait_for(lambda: door_shut(c, shelf), 20),
        )
    finally:
        set_page(c["trigger"], 1)
        L.tick(10)


def set_lever(p: Vec3, on: bool) -> None:
    L.set_block(
        p, f"minecraft:lever[face=floor,facing=north,powered={str(on).lower()}]"
    )


def astrolabe_set(c: dict, pattern: dict, pos=V) -> None:
    for (x, z), on in pattern.items():
        set_lever(c["levers"][(x, z)], on)
        poke(pos(x, 16, z))


def panel_open(c: dict) -> bool:
    return L.is_block(c["hole"], AIR)


def panel_shut(c: dict) -> bool:
    return L.is_block(c["panel"], c["panel_block"])


def work_astrolabe(check, pos=V) -> None:
    c = astrolabe_cells(pos)
    check("astrolabe: its levers are levers", trigger_ok(c))
    check("astrolabe: the floor panel starts shut", panel_shut(c))
    try:
        astrolabe_set(c, ASTROLABE_LEVERS, pos)
        check(
            "astrolabe: the star chart's setting opens the floor panel",
            wait_for(lambda: panel_open(c), 30),
        )
        top = c["top"]
        check(
            "astrolabe: the pipe tells the engine it is set",
            wait_for(lambda: L.is_block(top, "minecraft:redstone_wire[power=0]"), 60),
        )
        wrong = dict(ASTROLABE_LEVERS)
        first = next(iter(wrong))
        wrong[first] = not wrong[first]
        astrolabe_set(c, {first: wrong[first]}, pos)
        check(
            "astrolabe: one lever wrong shuts it",
            wait_for(lambda: panel_shut(c), 30),
        )
    finally:
        astrolabe_set(c, dict.fromkeys(ASTROLABE_LEVERS, False), pos)
        L.tick(40)


def work_engine(check, pos=V) -> None:
    """the engine's end lamp blinks with the chase while the astrolabe is
    set, and stays dark while it is not"""
    e = engine_cells(pos)
    a = astrolabe_cells(pos)

    def lamp_seen(samples: int) -> bool:
        for _ in range(samples):
            L.tick(3)
            if L.is_block(e["lamp"], "minecraft:redstone_lamp[lit=true]"):
                return True
        return False

    check("engine: dark while the astrolabe is not set", not lamp_seen(15))
    try:
        astrolabe_set(a, ASTROLABE_LEVERS, pos)
        L.tick(60)
        check("engine: its end lamp lights while the astrolabe is set", lamp_seen(40))
    finally:
        astrolabe_set(a, dict.fromkeys(ASTROLABE_LEVERS, False), pos)
        L.tick(60)


def container_count(p: Vec3, item: str) -> int:
    import re

    r = L.cmd(f"data get block {p.x} {p.y} {p.z} Items")
    n = 0
    for m in re.finditer(r'\{[^{}]*id: "minecraft:(\w+)"[^{}]*\}', r):
        if m.group(1) == item:
            c = re.search(r"count: (\d+)", m.group(0))
            n += int(c.group(1)) if c else 1
    return n


def transmuter_reset(c: dict) -> None:
    """the trays emptied, the filter and the reward dropper as built"""
    for key in ("tray", "reject", "lower", "collector", "input"):
        p = c[key]
        L.cmd(f"data modify block {p.x} {p.y} {p.z} Items set value []")
    p = c["filter"]
    L.cmd(
        f"data modify block {p.x} {p.y} {p.z} Items set value [{item_list(FILTER_ITEMS)}]"
    )
    p = c["reward_dropper"]
    reward = item_list([(TRANSMUTER_REWARD, 16)])
    L.cmd(f"data modify block {p.x} {p.y} {p.z} Items set value [{reward}]")


def work_transmuter(check, pos=V) -> None:
    c = transmuter_cells(pos)
    check("transmuter: its input is a hopper", trigger_ok(c))
    p = c["input"]
    try:
        L.cmd(
            f"item replace block {p.x} {p.y} {p.z} container.0 with minecraft:{TRANSMUTER_KEY} 1"
        )
        ok = wait_for(
            lambda: (
                container_count(c["tray"], TRANSMUTER_REWARD) == 1
                and container_count(c["tray"], TRANSMUTER_KEY) == 1
            ),
            120,
        )
        check(
            f"transmuter: an {TRANSMUTER_KEY} comes back with a {TRANSMUTER_REWARD}",
            ok,
        )
        check(
            "transmuter: the filter keeps its 18 keys",
            container_count(c["filter"], TRANSMUTER_KEY) == 18,
        )
        L.cmd(
            f"item replace block {p.x} {p.y} {p.z} container.0 with minecraft:stick 1"
        )
        check(
            "transmuter: anything else goes to the reject tray",
            wait_for(lambda: container_count(c["reject"], "stick") == 1, 120)
            and container_count(c["tray"], TRANSMUTER_REWARD) == 1,
        )
    finally:
        transmuter_reset(c)


def press(p: Vec3, facing: str, block: str = "polished_blackstone_button") -> None:
    """a button pressed and let go, by command: its neighbours see it"""
    L.set_block(p, f"minecraft:{block}[face=wall,facing={facing},powered=true]")
    L.tick(4)
    L.set_block(p, f"minecraft:{block}[face=wall,facing={facing},powered=false]")
    L.tick(4)


def copper_reset(c: dict) -> None:
    for key, p in c["bulbs"].items():
        lit = str(key in COPPER_START).lower()
        L.set_block(p, f"minecraft:waxed_copper_bulb[lit={lit},powered=false]")


def lit_bulbs(c: dict) -> set:
    return {
        key
        for key, p in c["bulbs"].items()
        if L.is_block(p, "minecraft:waxed_copper_bulb[lit=true]")
    }


def work_copper(check, pos=V) -> None:
    from castle2_layout import COPPER_SOLUTION

    c = copper_cells(pos)
    material = c["material"]
    check("copper puzzle: its keys are buttons", trigger_ok(c))
    check(
        f"copper puzzle: starts with {sorted(COPPER_START)} lit",
        lit_bulbs(c) == set(COPPER_START),
    )
    check("copper puzzle: the inner vault's door starts shut", door_shut(c, material))
    try:
        for k, key in enumerate(COPPER_SOLUTION):
            press(c["buttons"][key], c["button_facing"])
            if k < len(COPPER_SOLUTION) - 1:
                L.tick(10)
                check(
                    f"copper puzzle: after {key}, the door is still shut",
                    door_shut(c, material),
                )
        check(
            "copper puzzle: the solution lights every bulb",
            lit_bulbs(c) == set(c["bulbs"]),
        )
        check(
            "copper puzzle: every bulb lit opens the inner vault",
            wait_for(lambda: door_open(c), 30),
        )
    finally:
        copper_reset(c)
        L.tick(20)
    check(
        "copper puzzle: reset, the door shuts again",
        wait_for(lambda: door_shut(c, material), 30),
    )


# ---------------------------------------------------------------- the stage


def machines() -> str:
    """castle2's machines stage"""
    lectern_lock()
    copper_puzzle()
    astrolabe()
    engine_purpose()
    transmuter()
    try:
        import organ

        organ.organ()
    except ImportError:
        pass
    return "the lectern lock, the copper puzzle, the astrolabe, the engine, the transmuter, the organ"
