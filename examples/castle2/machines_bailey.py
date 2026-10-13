"""
The bailey's machines (castle2, phase 6): plain redstone that works in
survival (and adventure mode: every trigger is used, never broken or
placed) without mciwb.

- **The listening door** (the catacombs): a bell before a carved face in the
  oubliette's west wall. A calibrated sculk sensor behind the face, tuned by
  a comparator reading a barrel of bones (signal 11 = the bell's vibration
  frequency, `BELL_FREQUENCY`), toggles a waxed copper bulb when it hears a
  bell; a comparator reading the bulb opens a sliding door
  (`castle_lib.hidden_door`) onto a hidden ossuary. Other sounds (footsteps,
  arrows, the pit's trapdoors, doors and chests) are other frequencies.
- **The archery lock** (the barracks yard): a target on a post in a straw
  butt. A comparator behind it in compare mode, with a redstone block at its
  side (15), passes only a bullseye (15), toggling a copper bulb that holds
  an iron hatch open over a cache.
- **The clock tower** (the market square's plot `CLOCK_TOWER`): a daylight
  detector on the roof feeds a repeater; an observer under the repeater
  sees it change at dusk and dawn and rings the bell hanging below it.
  Inverted detectors light lamps round the roof and in the belfry's ceiling
  at night. The roof is glass from below, so the belfry shows the works.
- **The water mill** (the village's south-east, `MILL`): a timber-framed mill
  house, a water wheel in a race of still water, its paddles (trapdoors)
  flipped in two phases by a torch-and-repeater clock on a bench inside the
  mill, wired through a stone annex; millstones and sacks. A lever by the
  hearth ("Sluice") opens a sliding door onto a ladder down to a tunnel that
  joins castle's dungeon guard room.

Each machine's parts come from a ``*_cells`` function, used by the build and
the checks alike. Every function takes ``at``, the map from local
coordinates (castle's) to the world: `castle2_layout.V` in the castle, a
shifted map in the rig (rig_bailey.py). The ``check_*`` functions work a
machine over RCON and put it back as found; each yields (what, passed).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator

import castle_lib as L
from castle2_layout import (
    ARCHERY_LINE,
    ARCHERY_TARGET,
    CLOCK_TOWER,
    GARDEN,
    LISTENING_DOOR,
    MILL,
    MILL_DOOR,
    MILL_HOUSE,
    MILL_TUNNEL,
    MILL_WHEEL,
    V,
)

from mciwb.imports import Vec3

At = Callable[[int, int, int], Vec3]
Result = Iterator[tuple[str, bool]]

N, S, E, Wd, UP = (
    Vec3(0, 0, -1),
    Vec3(0, 0, 1),
    Vec3(1, 0, 0),
    Vec3(-1, 0, 0),
    Vec3(0, 1, 0),
)
BELL_FREQUENCY = 11  # a bell's vibration (block_change)
BULB = "minecraft:waxed_copper_bulb"  # waxed: it does not age
MILL_STONE = "minecraft:cobblestone"  # the mill's ground storey (house.STONE)
# the mill's lever, 4 east of its door: castle_lib.hidden_door's lever dust
# turns the corner into the torch's block only for lever_b >= 4 (at 3 its
# last dust points past the block)
MILL_LEVER_B = 4

# the triggers a player in adventure mode may use (never break or place)
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
    # a bell rings when used (right click): allowed in adventure mode, but
    # not in the lead's list: to be confirmed in game
    "minecraft:bell",
)


def items(*stacks: tuple[str, int], name: dict[int, str] | None = None) -> str:
    """a container's Items NBT: (item, count) per slot; ``name`` gives some
    slots a custom name (a plain SNBT string)"""
    out = []
    for slot, (item, count) in enumerate(stacks):
        extra = ""
        if name and slot in name:
            extra = (
                f',components:{{"minecraft:custom_name":{L.snbt_string(name[slot])}}}'
            )
        out.append(f'{{Slot:{slot}b,id:"minecraft:{item}",count:{count}{extra}}}')
    return "{Items:[" + ",".join(out) + "]}"


def stacks_for(signal: int, slots: int = 27) -> int:
    """the fewest full stacks in a container of ``slots`` that a comparator
    reads as ``signal`` (1 + floor(14 * full / slots))"""
    for n in range(slots + 1):
        if n and 1 + (14 * n) // slots == signal:
            return n
    raise ValueError(f"no number of stacks gives {signal}")


def _block_is(p: Vec3, block: str) -> bool:
    """is_block, read again once (a reply can be lost to another client)"""
    return L.is_block(p, block) or L.is_block(p, block)


def poke(p: Vec3) -> None:
    """re-place a dust, so that it takes up a lever's new power"""
    L.cmd(f"setblock {p.x} {p.y} {p.z} minecraft:air")
    L.cmd(f"setblock {p.x} {p.y} {p.z} minecraft:redstone_wire")


def press(p: Vec3, block: str, ticks: int = 4) -> None:
    """stand a redstone block in for a moment at p (a button press, a bell's
    ring), then put ``block`` back"""
    L.cmd(f"setblock {p.x} {p.y} {p.z} minecraft:redstone_block")
    L.tick(ticks)
    L.cmd(f"setblock {p.x} {p.y} {p.z} {block}")


def adventure_ok(kind: str) -> bool:
    return kind in ADVENTURE_OK


# ================================================================ the listening door


def listening_door_cells(at: At = V) -> dict:
    """the listening door's parts (world positions). Its frame: ``a`` west
    from the oubliette's west wall (x 91), ``b`` south from the door, ``h``
    up from the floor"""
    x, y, z = LISTENING_DOOR
    base = at(x, y, z)

    def p(a: int, b: int, h: int) -> Vec3:
        return base + Wd * a + S * b + UP * h

    d = L.hidden_door_cells(base, Wd, S, trigger="lever", lever_b=3)
    return {
        "door": d["door"],
        "pistons": d["pistons"],
        "inside": d["inside"],
        "face": p(0, 5, 1),
        "sensor": p(2, 5, 1),
        "tuner": p(2, 6, 1),  # the comparator that tunes the sensor
        "tuning_barrel": p(2, 7, 1),
        "bulb": p(2, 4, 1),
        "reader": p(2, 3, 1),  # the comparator reading the bulb
        "torch_block": p(2, 2, 1),
        "lever_spot": p(-1, 3, 1),  # hidden_door's lever: taken away
        "lever_dust": p(1, 3, 1),
        "bell": p(-1, 5, 0),
        "bell_floor": p(-1, 5, -1),
        "hint": p(-1, 5, 2),
        "inner_bell": at(86, y, 123),
        "inner_bell_floor": at(86, y - 1, 123),
        "reliquary": at(81, y, 124),
        "ossuary": (at(81, y, 120), at(87, y + 2, 128)),
        "trigger": p(-1, 5, 0),
        "trigger_kind": "minecraft:bell",
        "door_block": L.DARK_BRICK,
        "floor_block": L.MOSSY_COBBLE,
    }


def listening_door(at: At = V) -> dict:
    """
    The door, its circuit and the ossuary. The oubliette (castle's
    catacombs, built by the dungeons stage) must be there: this cuts into
    its west wall, so it is built again after the dungeons stage
    (`after_dungeons`).
    """
    c = listening_door_cells(at)
    x, y, z = LISTENING_DOOR
    # the mechanism's block, solid: the oubliette's west wall, the hidden
    # space behind it and the circuit south of that
    L.fill(at(x - 3, y - 1, z - 1), at(x, y + 3, z + 8), L.DARK_BRICK)
    L.hidden_door(at(x, y, z), Wd, S, trigger="lever", material=L.DARK_BRICK, lever_b=3)
    # its lever goes: the bulb's comparator drives the torch's block instead
    L.set_block(c["lever_spot"], L.AIR)
    L.set_block(c["lever_dust"], L.DARK_BRICK)
    L.set_block(c["reader"], "minecraft:comparator[facing=south]")
    L.set_block(c["bulb"], f"{BULB}[lit=false]")
    # the sensor faces north: it is tuned from its back (south), by a
    # comparator reading a barrel of bones (placed after the comparator, so
    # that the comparator sees it filled). The sensor goes in last: untuned
    # it hears everything (the door's pistons) and would toggle the bulb
    L.set_block(
        c["tuner"],
        "minecraft:comparator[facing=south,powered=true]"
        f"{{OutputSignal:{BELL_FREQUENCY}}}",
    )  # its output set already: a comparator only updates 2 ticks on
    bones = [("bone", 64)] * stacks_for(BELL_FREQUENCY)
    L.set_block(c["tuning_barrel"], "minecraft:barrel[facing=up]" + items(*bones))
    L.set_block(c["sensor"], "minecraft:calibrated_sculk_sensor[facing=north]")
    # the carved face, the bell before it, and the hint over it
    L.set_block(c["face"], "minecraft:chiseled_polished_blackstone")
    L.set_block(c["bell_floor"], c["floor_block"])
    L.set_block(c["bell"], "minecraft:bell[attachment=floor,facing=east]")
    L.sign(
        c["hint"], "dark_oak_wall_sign[facing=east]", "The dead hear", "only the bell"
    )
    ossuary(at, c)
    L.set_block(c["bulb"], f"{BULB}[lit=false]")  # shut, whatever it heard
    return c


def ossuary(at: At, c: dict) -> None:
    """bones, skulls in niches, candles, the founder's reliquary, and a bell
    to ring the door open from inside"""
    _x, y, _z = LISTENING_DOOR
    L.fill(at(80, y - 1, 119), at(87, y + 3, 129), L.DARK_BRICK)
    L.fill(at(81, y, 120), at(87, y + 2, 128), L.AIR)
    L.fill(at(81, y - 1, 120), at(87, y - 1, 128), "minecraft:soul_soil")
    for z in range(120, 129, 2):  # skulls in the west wall's niches
        L.set_block(at(80, y + 1, z), L.AIR)
        L.set_block(at(80, y, z), "minecraft:bone_block")
        L.set_block(at(80, y + 1, z), "minecraft:skeleton_skull[rotation=12]")
    for z in (121, 127):  # bone pillars
        L.fill(at(84, y, z), at(84, y + 2, z), "minecraft:bone_block[axis=y]")
        L.set_block(at(83, y, z), "minecraft:candle[candles=3,lit=true]")
    L.fill(at(81, y, 120), at(83, y, 120), "minecraft:bone_block[axis=x]")
    L.set_block(at(82, y + 1, 120), "minecraft:skeleton_skull[rotation=0]")
    L.set_block(at(81, y, 128), "minecraft:bone_block")
    L.set_block(at(81, y + 1, 128), "minecraft:white_candle[candles=4,lit=true]")
    L.set_block(at(84, y + 2, 124), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_block(at(86, y + 2, 127), f"{L.SOUL_LANTERN}[hanging=true]")
    L.set_block(
        c["reliquary"],
        "minecraft:chest[facing=east]"
        + items(
            ("golden_apple", 2),
            ("echo_shard", 3),
            ("recovery_compass", 1),
            ("paper", 1),
            name={3: "The founder: the miller keeps a way below"},
        ),
    )
    L.set_block(c["inner_bell_floor"], "minecraft:soul_soil")
    L.set_block(c["inner_bell"], "minecraft:bell[attachment=floor,facing=east]")


def check_listening_door(at: At = V) -> Result:
    c = listening_door_cells(at)
    door, bulb = c["door"], c["bulb"]
    L.tick(5)  # (a comparator set just now updates two ticks later)

    def closed() -> bool:
        return all(_block_is(p, c["door_block"]) for p in door)

    def opened() -> bool:
        return all(L.is_block(p, L.AIR) for p in door)

    yield (
        "listening door: the bell is an adventure trigger",
        adventure_ok(c["trigger_kind"]) and _block_is(c["trigger"], c["trigger_kind"]),
    )
    yield (
        "listening door: sensor tuned (comparator on a barrel of bones)",
        _block_is(c["sensor"], "minecraft:calibrated_sculk_sensor")
        and _block_is(c["tuner"], "minecraft:comparator")
        and f"OutputSignal: {BELL_FREQUENCY}"
        in L.cmd(f"data get block {c['tuner'].x} {c['tuner'].y} {c['tuner'].z}"),
    )
    was_open = _block_is(bulb, f"{BULB}[lit=true]")
    try:
        if was_open:  # shut it first: ring once
            press(c["bell_floor"], c["floor_block"])
            L.tick(40)
        yield "listening door: starts shut", closed()
        # a wrong sound: an arrow landing on the floor before the face
        b = c["bell"] + E * 2
        L.cmd(f"summon minecraft:arrow {b.x + 0.5} {b.y + 1.5} {b.z + 0.5}")
        L.tick(40)
        yield "listening door: an arrow's sound does not open it", closed()
        press(c["bell_floor"], c["floor_block"])
        ok = L.wait_until(opened, 60)
        yield "listening door: the bell opens it", ok
        L.tick(40)  # the sensor's cooldown
        press(c["inner_bell_floor"], "minecraft:soul_soil")
        ok = L.wait_until(closed, 60)
        yield "listening door: the ossuary's bell shuts it again", ok
    finally:
        o1, o2 = c["ossuary"]
        L.cmd(
            f"kill @e[type=minecraft:arrow,{L.box_selector(o1 - Vec3(0, 2, 0), c['bell'] + Vec3(4, 3, 4))}]"
        )
        L.tick(30)
        if was_open != _block_is(bulb, f"{BULB}[lit=true]"):
            press(c["bell_floor"], c["floor_block"])
            L.tick(40)


# ================================================================ the archery lock


def archery_cells(at: At = V) -> dict:
    x, y, z = ARCHERY_TARGET
    return {
        "target": at(x, y, z),
        "post": at(x, y - 1, z),
        "comparator": at(x + 1, y, z),  # compare mode, facing the target
        "side": at(x + 1, y, z - 1),  # the redstone block at its side
        "bulb": at(x + 2, y - 1, z),
        "reader": at(x + 3, y - 1, z),
        "hatch": at(x + 4, y - 1, z),
        "cache": at(x + 4, y - 2, z),
        "butt": (at(x + 1, y - 1, z - 2), at(x + 3, y + 1, z + 2)),
        "line": [at(ARCHERY_LINE, -1, zz) for zz in range(z - 3, z + 4)],
        "kit": at(ARCHERY_LINE - 1, 0, z - 2),  # a barrel of bows
        "dropper": at(ARCHERY_LINE - 1, 0, z + 2),  # arrows, one per press
        "button": at(ARCHERY_LINE - 1, 1, z + 2),
        "sign": at(ARCHERY_LINE - 1, 0, z - 3),
        "trigger": at(x, y, z),
        "trigger_kind": "minecraft:target",
    }


def archery(at: At = V) -> dict:
    c = archery_cells(at)
    b1, b2 = c["butt"]
    x, y, z = ARCHERY_TARGET
    # clear the range's end (x 50..55: the grand stair's balustrade is at 56)
    L.fill(at(x - 1, y - 1, z - 3), at(x + 4, y + 3, z + 3), L.AIR)
    L.fill(b1, b2, "minecraft:hay_block")
    L.set_block(c["post"], "minecraft:stripped_oak_log")
    L.set_block(c["target"], "minecraft:target")
    L.set_block(c["side"], "minecraft:redstone_block")
    L.set_block(c["comparator"], "minecraft:comparator[facing=west,mode=compare]")
    L.set_block(c["bulb"], f"{BULB}[lit=false]")
    L.set_block(c["reader"], "minecraft:comparator[facing=west]")
    L.set_block(
        c["cache"],
        "minecraft:barrel[facing=up]"
        + items(
            ("spectral_arrow", 32),
            ("bow", 1),
            ("arrow", 64),
            ("paper", 1),
            name={3: "Stop the wheel? No: the sluice opens the stones"},
        ),
    )
    L.set_block(
        c["hatch"], "minecraft:iron_trapdoor[facing=west,half=bottom,open=false]"
    )
    L.set_block(at(x + 2, y + 2, z), f"{L.LANTERN}[hanging=false]")  # on the butt
    # the shooting line, the kit and the sign
    for p in c["line"]:
        L.set_block(p, "minecraft:smooth_stone")
    L.set_block(
        c["kit"],
        "minecraft:barrel[facing=up]"
        + items(("bow", 1), ("bow", 1), ("bow", 1), ("arrow", 64)),
    )
    L.set_block(
        c["dropper"],
        "minecraft:dropper[facing=east]" + items(*[("arrow", 64)] * 9),
    )
    L.set_block(c["button"], "minecraft:oak_button[face=floor,facing=east]")
    L.sign(
        c["sign"],
        "oak_sign[rotation=4]",
        "Archery range",
        "a true eye",
        "opens the",
        "stores",
    )
    return c


def _shoot(c: dict, dy: float = 0.5, dz: float = 0.5) -> None:
    """an arrow at the target from just in front of it (tried in 26.3: from
    1.3 blocks at 1 block a tick, aimed at the middle, it hits the bullseye;
    an arrow that starts on a block boundary from the face can miss)"""
    t = c["target"]
    L.cmd(
        f"summon minecraft:arrow {t.x - 1.3} {t.y + dy} {t.z + dz} "
        "{Motion:[1.0d,0.0d,0.0d]}"
    )


def check_archery(at: At = V) -> Result:
    c = archery_cells(at)
    hatch = c["hatch"]

    def is_open() -> bool:
        return L.is_block(hatch, "minecraft:iron_trapdoor[open=true]")

    def arrows_away() -> None:
        t = c["target"]
        L.cmd(
            f"kill @e[type=minecraft:arrow,{L.box_selector(t - Vec3(4, 2, 3), t + Vec3(2, 2, 3))}]"
        )

    yield (
        "archery: the target is an adventure trigger, with bows and arrows at the line",
        adventure_ok(c["trigger_kind"])
        and _block_is(c["trigger"], c["trigger_kind"])
        and _block_is(c["kit"], "minecraft:barrel")
        and _block_is(c["dropper"], "minecraft:dropper")
        and _block_is(c["button"], "#minecraft:buttons"),
    )
    was_open = _block_is(c["bulb"], f"{BULB}[lit=true]")
    try:
        if was_open:
            _shoot(c)
            L.tick(30)
            arrows_away()
        yield "archery: the hatch starts shut", not is_open()
        _shoot(c, 0.92, 0.92)  # near the edge
        ok = not L.wait_until(is_open, 25)
        arrows_away()
        yield "archery: an outer ring does not open the hatch", ok
        L.tick(10)
        _shoot(c)
        ok = L.wait_until(is_open, 25)
        yield (
            "archery: a bullseye opens the hatch (and it stays open)",
            ok and (L.tick(30) or is_open()),
        )
        arrows_away()
        _shoot(c)
        ok = L.wait_until(lambda: not is_open(), 25)
        yield "archery: another bullseye shuts it", ok
    finally:
        L.tick(30)
        arrows_away()
        if was_open != _block_is(c["bulb"], f"{BULB}[lit=true]"):
            _shoot(c)
            L.tick(30)
            arrows_away()


# ================================================================ the clock tower


def clock_tower_cells(at: At = V) -> dict:
    cx, cz = CLOCK_TOWER
    return {
        "plot": (at(cx - 2, -1, cz - 2), at(cx + 2, 18, cz + 2)),
        "door": at(cx - 2, 0, cz),
        "sun": at(cx - 1, 16, cz),  # the daylight detector the bell follows
        "repeater": at(cx, 16, cz),
        "observer": at(cx, 15, cz),
        "bell": at(cx, 14, cz),
        "moons": [at(cx + 1, 16, cz), at(cx - 1, 16, cz - 1), at(cx - 1, 16, cz + 1)],
        "lamps": [
            at(cx + 1, 15, cz),
            at(cx - 1, 15, cz - 1),
            at(cx - 1, 15, cz + 1),
            at(cx + 2, 16, cz),
            at(cx + 1, 16, cz - 1),
            at(cx + 1, 16, cz + 1),
            at(cx, 16, cz - 1),
            at(cx, 16, cz + 1),
            at(cx - 2, 16, cz - 1),
            at(cx - 2, 16, cz + 1),
            at(cx - 1, 16, cz - 2),
            at(cx - 1, 16, cz + 2),
        ],
        "faces": [  # the clocks: item frames outside each wall (facing, cell)
            (2, at(cx, 9, cz - 3)),
            (3, at(cx, 9, cz + 3)),
            (4, at(cx - 3, 9, cz)),
            (5, at(cx + 3, 9, cz)),
        ],
    }


def clock_tower(at: At = V) -> dict:
    c = clock_tower_cells(at)
    cx, cz = CLOCK_TOWER
    x1, x2, z1, z2 = cx - 2, cx + 2, cz - 2, cz + 2
    L.fill(at(x1, 0, z1), at(x2, 19, z2), L.AIR)
    L.fill(at(x1, -2, z1), at(x2, -1, z2), L.BRICK)
    # the stone shaft, a timber clock stage, a beam, the belfry
    L.fill(at(x1, 0, z1), at(x2, 7, z2), L.BRICK)
    L.fill(at(x1, 0, z1), at(x2, 1, z2), L.DARK_BRICK)
    L.fill(at(x1, 8, z1), at(x2, 10, z2), "minecraft:calcite")
    for x, z in ((x1, z1), (x1, z2), (x2, z1), (x2, z2)):
        L.fill(at(x, 8, z), at(x, 14, z), "minecraft:stripped_dark_oak_log[axis=y]")
    L.fill(at(x1, 11, z1), at(x2, 11, z1), "minecraft:stripped_dark_oak_log[axis=x]")
    L.fill(at(x1, 11, z2), at(x2, 11, z2), "minecraft:stripped_dark_oak_log[axis=x]")
    L.fill(
        at(x1, 11, z1 + 1),
        at(x1, 11, z2 - 1),
        "minecraft:stripped_dark_oak_log[axis=z]",
    )
    L.fill(
        at(x2, 11, z1 + 1),
        at(x2, 11, z2 - 1),
        "minecraft:stripped_dark_oak_log[axis=z]",
    )
    # inside: hollow, a landing at 7, the belfry floor at 11
    L.fill(at(x1 + 1, 0, z1 + 1), at(x2 - 1, 14, z2 - 1), L.AIR)
    L.fill(at(x1 + 1, -1, z1 + 1), at(x2 - 1, -1, z2 - 1), L.SPRUCE)
    L.fill(at(x1 + 1, 7, z1 + 1), at(x2 - 1, 7, z2 - 1), L.SPRUCE)
    L.fill(at(x1 + 1, 11, z1 + 1), at(x2 - 1, 11, z2 - 1), L.SPRUCE)
    # the dials round the clocks: a ring of quartz on each face
    for f, p in c["faces"]:
        wall = p - {2: N, 3: S, 4: Wd, 5: E}[f]
        side = E if f in (2, 3) else S
        for k in (-1, 1):
            L.set_block(wall + side * k, "minecraft:smooth_quartz")
            L.set_block(wall + UP * k, "minecraft:smooth_quartz")
        L.set_block(wall, "minecraft:chiseled_quartz_block")
    # the belfry: open on every side over a railing
    for x in range(x1 + 1, x2):
        for z in (z1, z2):
            L.set_block(at(x, 12, z), "minecraft:dark_oak_fence")
            L.fill(at(x, 13, z), at(x, 14, z), L.AIR)
    for z in range(z1 + 1, z2):
        for x in (x1, x2):
            L.set_block(at(x, 12, z), "minecraft:dark_oak_fence")
            L.fill(at(x, 13, z), at(x, 14, z), L.AIR)
    # the roof: a stone cornice round glass, the works on top
    L.fill(at(x1, 15, z1), at(x2, 15, z2), L.BRICK)
    L.fill(at(x1 + 1, 15, z1 + 1), at(x2 - 1, 15, z2 - 1), "minecraft:glass")
    L.fill(at(x1, 16, z1), at(x2, 16, z2), L.BRICK)  # the parapet (lamps below)
    L.fill(at(x1 + 1, 16, z1 + 1), at(x2 - 1, 16, z2 - 1), L.AIR)
    for lamp in c["lamps"]:
        L.set_block(lamp, "minecraft:redstone_lamp")
    L.set_block(c["observer"], "minecraft:observer[facing=up]")
    L.set_block(c["sun"], "minecraft:daylight_detector[inverted=false]")
    for m in c["moons"]:
        L.set_block(m, "minecraft:daylight_detector[inverted=true]")
    L.set_block(c["repeater"], "minecraft:repeater[facing=west]")
    L.set_block(c["bell"], "minecraft:bell[attachment=ceiling,facing=south]")
    for x, z in ((x1, z1), (x1, z2), (x2, z1), (x2, z2)):
        L.set_block(at(x, 17, z), L.BRICK_WALL)
    L.set_block(at(x2, 18, z2), "minecraft:lightning_rod")
    # the door (west, onto the square), the ladder up the east wall
    L.fill(at(x1, 0, cz), at(x1, 1, cz), L.AIR)
    L.set_block(
        at(x1, 0, cz), "minecraft:spruce_door[facing=east,half=lower,hinge=left]"
    )
    L.set_block(
        at(x1, 1, cz), "minecraft:spruce_door[facing=east,half=upper,hinge=left]"
    )
    L.fill(
        at(x2 - 1, 0, cz + 1), at(x2 - 1, 11, cz + 1), "minecraft:ladder[facing=west]"
    )
    L.set_block(at(x1 + 1, 0, z1 + 1), f"{L.LANTERN}[hanging=false]")
    L.set_block(at(x1 + 1, 8, z1 + 1), f"{L.LANTERN}[hanging=false]")
    L.set_block(at(x1 + 1, 12, z1 + 1), f"{L.LANTERN}[hanging=false]")
    L.sign(
        at(x1 + 1, 1, z2 - 1),
        "spruce_wall_sign[facing=north]",
        "The town clock",
        "Climb, and look up:",
        "the sun's eye rings",
        "dawn and dusk",
    )
    for f, p in c["faces"]:
        L.summon(
            "item_frame",
            p,
            f'Facing:{f}b,Fixed:1b,Invulnerable:1b,Item:{{id:"minecraft:clock",count:1}}',
        )
    return c


def _day() -> int | None:
    m = re.search(r"(\d+) tick", L.cmd("time query day"))
    return int(m.group(1)) if m else None


def check_clock_tower(at: At = V) -> Result:
    c = clock_tower_cells(at)
    bell, rep = c["bell"], c["repeater"]
    lamps = c["lamps"]

    def rang() -> bool:
        return L.is_block(bell, "minecraft:bell[powered=true]")

    def lit(on: bool) -> bool:
        return all(
            L.is_block(p, f"minecraft:redstone_lamp[lit={str(on).lower()}]")
            for p in lamps
        )

    yield (
        "clock tower: detectors, observer and bell in place",
        _block_is(c["sun"], "minecraft:daylight_detector[inverted=false]")
        and all(
            _block_is(m, "minecraft:daylight_detector[inverted=true]")
            for m in c["moons"]
        )
        and _block_is(c["observer"], "minecraft:observer[facing=up]")
        and _block_is(bell, "minecraft:bell[attachment=ceiling]"),
    )
    was = _day()
    try:
        L.cmd("time set 6000")
        L.tick(45)
        yield (
            "clock tower: by day the repeater is on and the lamps are out",
            _block_is(rep, "minecraft:repeater[powered=true]") and lit(False),
        )
        L.cmd("time set 18000")
        ok = L.wait_until(rang, 50)
        yield "clock tower: the bell rings at dusk", ok
        L.tick(10)
        yield (
            "clock tower: by night the lamps are lit",
            _block_is(rep, "minecraft:repeater[powered=false]") and lit(True),
        )
        L.cmd("time set 23500")
        ok = L.wait_until(rang, 50)
        yield "clock tower: the bell rings at dawn", ok
    finally:
        if was is not None:
            L.cmd(f"time set {was}")
        L.tick(25)


# ================================================================ the water mill


def mill_cells(at: At = V, tunnel_z: int | None = None) -> dict:
    """the mill's parts. The wheel's paddles are at (dy, dz) from its hub:
    phase A the left and top, phase B the right and bottom"""
    hx, hy, hz = MILL_WHEEL
    tz = MILL_TUNNEL[2] if tunnel_z is None else tunnel_z
    a_paddles = [(0, -3), (3, 0)]
    b_paddles = [(0, 3), (-3, 0)]
    x, y, z = MILL_DOOR
    base = at(x, y, z)
    d = L.hidden_door_cells(base, S, E, trigger="lever", lever_b=MILL_LEVER_B)

    def paddle(dy: int, dz: int) -> Vec3:
        return at(hx, hy + dy, hz + dz)

    return {
        "hub": at(hx, hy, hz),
        "a": [paddle(dy, dz) for dy, dz in a_paddles],
        "b": [paddle(dy, dz) for dy, dz in b_paddles],
        "a_cells": a_paddles,
        "b_cells": b_paddles,
        "race": [
            at(hx, yy, zz)
            for yy in (hy - 3, hy - 2)
            for zz in range(MILL[1] + 1, MILL[1] + 12)
        ],
        "door": d["door"],
        "lever": d["trigger"],
        "lever_facing": d["trigger_facing"],
        "first_dust": d["first_dust"],
        "inner_lever": base + S * 2 + E * 2 + UP * 2,
        "shaft": [base + S * 3 + UP * h for h in range(-8, 1)],
        "tunnel": [
            at(MILL_TUNNEL[0], MILL_TUNNEL[1], zz)
            for zz in range(tz, MILL_DOOR[2] + 3, 7)
        ],
        "clock": at(101, 1, 197),  # the clock's torch block
        "torch": at(102, 1, 197),
        "sign": at(100, 1, 200),
        "trigger": d["trigger"],
        "trigger_kind": "minecraft:lever",
    }


def mill_clear(at: At = V) -> None:
    """the plot (and the old allotments' strip west of it) back to grass"""
    x1 = GARDEN[2] + 1
    _px1, z1, x2, z2 = MILL
    L.fill(at(x1, 0, z1), at(x2, 16, z2), L.AIR)
    L.fill(at(x1, -4, z1), at(x2, -2, z2), "minecraft:dirt")
    L.fill(at(x1, -1, z1), at(x2, -1, z2), "minecraft:grass_block")


def mill_house(at: At = V) -> None:
    """a timber-framed house (house.py), its ground floor cleared for the
    mill: a ladder for the stair, millstones, sacks"""
    from house import house_blocks, place

    hx, hy, hz = MILL_HOUSE
    h = house_blocks(
        at(hx, hy, hz),
        11,
        9,
        floors=2,
        facing="north",
        ground="stone",
        frame="square_panel",
        contents="home",
        seed=7,
    )
    o = at(0, 0, 0)
    for key in list(h.blocks):
        x, y, z = key[0] - o.x, key[1] - o.y, key[2] - o.z
        inside = hx + 1 <= x <= hx + 9 and hz + 1 <= z <= hz + 7
        if (
            inside
            and 0 <= y <= 2
            and not any(k in h.blocks[key] for k in ("brick", "campfire"))
        ):
            del h.blocks[key]  # the ground floor's furniture and stair
        elif inside and y == 3 and h.blocks[key] == L.AIR:
            h.blocks[key] = "minecraft:spruce_planks"  # the stair's hole
    place(h, L.summon)
    # a ladder up in the north-west corner
    L.fill(
        at(hx + 1, 0, hz + 1), at(hx + 1, 3, hz + 1), "minecraft:ladder[facing=east]"
    )
    # the millstones under a grain hopper, a stonecutter, sacks of flour
    for x in (96, 97):
        L.set_block(at(x, 0, 197), "minecraft:grindstone[face=floor,facing=north]")
    L.set_block(at(96, 2, 197), "minecraft:hopper[facing=down]")
    L.set_block(at(95, 0, 197), "minecraft:stonecutter[facing=east]")
    flour = items(("wheat", 64), ("sugar", 32), name={1: "Flour"})
    for z in (195, 196):
        L.set_block(at(94, 0, z), "minecraft:barrel[facing=up]" + flour)
    L.set_block(at(94, 1, 195), "minecraft:barrel[facing=up]" + flour)
    L.set_block(at(96, 0, 194), "minecraft:hay_block")
    for p in ((96, 2, 195), (98, 2, 195), (97, 2, 199)):
        L.set_block(at(*p), f"{L.LANTERN}[hanging=true]")


def mill_clock(at: At = V) -> None:
    """the torch-and-repeater clock on a bench by the east wall, its two
    phases out through the wall (A from the torch's block, B from the
    torch's loop): about 0.9 s each"""
    for x in range(99, 103):
        L.fill(at(x, 0, 194), at(x, 0, 200), "minecraft:polished_andesite")
    L.fill(at(99, 1, 194), at(102, 2, 200), L.AIR)
    parts = {
        (101, 197): L.STONE,  # the clock's block, K
        (102, 197): "minecraft:redstone_wall_torch[facing=east]",
        (102, 198): L.DUST,
        (101, 198): "minecraft:repeater[facing=east,delay=4]",
        (100, 198): L.DUST,
        (99, 198): L.DUST,
        (99, 197): L.DUST,
        (100, 197): "minecraft:repeater[facing=west,delay=4]",
        # phase A: from K, north, through the wall at z 194
        (101, 196): "minecraft:repeater[facing=south]",
        (101, 195): L.DUST,
        (101, 194): L.DUST,
        (102, 194): L.DUST,
        (103, 194): "minecraft:repeater[facing=west]",
        # phase B: the torch's loop, south, through the wall at z 200
        (102, 199): L.DUST,
        (102, 200): L.DUST,
        (103, 200): "minecraft:repeater[facing=west]",
    }
    for (x, z), block in parts.items():
        if "torch" not in block:
            L.set_block(at(x, 1, z), block)
    L.set_block(at(102, 1, 197), "minecraft:redstone_wall_torch[facing=east]")


def mill_wheel(at: At = V) -> None:
    """the annex that carries the phases to the paddles, the race, the wheel"""
    hx, hy, hz = MILL_WHEEL
    _x1, z1, _x2, z2 = MILL
    zr1, zr2 = z1 + 1, z1 + 11  # the race's water
    # the race: its bed and banks, then the annex against the house
    L.fill(at(hx - 1, hy - 4, z1), at(hx + 1, hy - 2, zr2 + 1), L.BRICK)
    L.fill(at(hx - 3, hy - 4, z1), at(hx - 1, hy + 4, z1 + 10), L.BRICK)
    L.fill(
        at(hx - 3, hy + 5, z1),
        at(hx - 1, hy + 5, z1 + 10),
        "minecraft:spruce_slab[type=bottom]",
    )
    L.fill(at(hx, hy - 3, zr1), at(hx, hy - 2, zr2), L.WATER)
    L.fill(
        at(hx + 1, hy - 1, z1), at(hx + 1, hy - 1, zr2 + 1), "minecraft:spruce_fence"
    )
    # lanterns on the bank: the site's water freezes at night where the
    # block light is under 10, and these keep every cell of the race at 10+
    for zz in range(zr1, zr2 + 1, 5):
        L.set_block(at(hx + 1, hy, zz), L.LANTERN)
    # the annex's wiring: a dust stair per phase in the plane x = hx - 3,
    # a repeater behind each paddle (x = hx - 2) into the wall (x = hx - 1)
    stairs = {
        "a": [(0, -3), (1, -2), (2, -1), (3, 0)],
        "b": [(0, 3), (-1, 2), (-2, 1), (-3, 0)],
    }
    for cells in stairs.values():
        for k, (dy, dz) in enumerate(cells):
            L.set_block(at(hx - 3, hy + dy, hz + dz), L.DUST)
            if k + 1 < len(cells):  # air over the lower of each step
                ny, nz = cells[k + 1]
                lo_y, lo_z = (dy, dz) if dy < ny else (ny, nz)
                L.set_block(at(hx - 3, hy + lo_y + 1, hz + lo_z), L.AIR)
    for dy, dz in stairs["a"][::3] + stairs["b"][::3]:
        L.set_block(at(hx - 2, hy + dy, hz + dz), "minecraft:repeater[facing=west]")
    # the wheel: hub, spokes, rim, and the paddles (trapdoors that flip
    # between flat and upright)
    L.set_block(at(hx, hy, hz), "minecraft:stripped_spruce_log[axis=x]")
    for k in (1, 2):
        for dy in (k, -k):
            L.set_block(at(hx, hy + dy, hz), "minecraft:stripped_spruce_log[axis=y]")
        for dz in (k, -k):
            L.set_block(at(hx, hy, hz + dz), "minecraft:stripped_spruce_log[axis=z]")
    for dy, dz in (
        (3, -1), (3, 1), (2, -2), (2, 2), (1, -3), (1, 3),
        (-1, -3), (-1, 3), (-2, -2), (-2, 2), (-3, -1), (-3, 1),
    ):  # fmt: skip
        L.set_block(at(hx, hy + dy, hz + dz), "minecraft:stripped_spruce_wood")
    for dy, dz in ((0, -3), (3, 0), (0, 3), (-3, 0)):
        wet = str(hy + dy <= hy - 2).lower()
        L.set_block(
            at(hx, hy + dy, hz + dz),
            f"minecraft:oak_trapdoor[facing=north,half=bottom,open=false,waterlogged={wet}]",
        )


def mill_secret(at: At = V, tunnel_z: int | None = None) -> dict:
    """the store behind the south wall, the sliding door, the ladder down
    and the tunnel to the dungeon's guard room (whose wall is at
    ``tunnel_z``, a shorter stub in the rig)"""
    x, y, z = MILL_DOOR
    tx, ty, tz = MILL_TUNNEL
    tz = tz if tunnel_z is None else tunnel_z
    # the store: a stone lean-to over the hidden space
    L.fill(at(x - 2, y - 1, z + 1), at(x + 5, y + 4, z + 4), MILL_STONE)
    L.fill(
        at(x - 2, y + 5, z + 1),
        at(x + 5, y + 5, z + 4),
        "minecraft:spruce_slab[type=bottom]",
    )
    # the tunnel's lining, then the tunnel and the shaft
    L.fill(at(tx - 1, ty - 2, tz + 1), at(tx + 1, y - 2, z + 4), L.COBBLE)
    L.hidden_door(
        at(x, y, z), S, E, trigger="lever", material=MILL_STONE, lever_b=MILL_LEVER_B
    )
    c = mill_cells(at, tunnel_z)
    L.set_block(at(x, y + 2, z), "minecraft:chiseled_stone_bricks")  # the mason's mark
    L.lever(c["inner_lever"], "north", "floor")
    L.fill(at(tx, ty, tz + 1), at(tx, ty + 2, z + 2), L.AIR)
    L.fill(at(tx, ty, tz), at(tx, ty + 1, tz), L.AIR)  # through the guard room wall
    L.fill(at(x, ty, z + 3), at(x, y, z + 3), "minecraft:ladder[facing=north]")
    for zz in range(tz + 5, z + 3, 7):
        L.set_block(at(tx, ty + 2, zz), f"{L.SOUL_LANTERN}[hanging=true]")
    L.sign(at(tx, ty + 1, z + 2), "spruce_wall_sign[facing=west]", "Up: the mill")
    L.sign(c["sign"], "spruce_wall_sign[facing=north]", "Sluice")
    return c


def guard_room_join(at: At = V) -> None:
    """the doorway from castle's guard room into the tunnel (the dungeons
    stage builds the guard room's walls again)"""
    tx, ty, tz = MILL_TUNNEL
    L.fill(at(tx, ty, tz), at(tx, ty + 1, tz), L.AIR)


def mill(at: At = V, tunnel_z: int | None = None) -> dict:
    mill_clear(at)
    mill_house(at)
    mill_clock(at)
    mill_wheel(at)
    return mill_secret(at, tunnel_z)


def _open(p: Vec3) -> bool:
    return L.is_block(p, "#minecraft:trapdoors[open=true]")


def check_mill(at: At = V, tunnel_z: int | None = None) -> Result:
    c = mill_cells(at, tunnel_z)
    yield (
        "mill: the race is still water (sources, not ice) round the wheel",
        all(
            L.is_block(p, "minecraft:water[level=0]")
            or L.is_block(p, "minecraft:stripped_spruce_wood")
            or L.is_block(p, "#minecraft:logs")
            or L.is_block(p, "#minecraft:trapdoors")
            for p in c["race"]
        ),
    )
    samples = []
    for _ in range(8):
        samples.append(
            (_open(c["a"][0]), _open(c["a"][1]), _open(c["b"][0]), _open(c["b"][1]))
        )
        L.tick(7)
    a_seen = {s[0] for s in samples} | {s[1] for s in samples}
    b_seen = {s[2] for s in samples} | {s[3] for s in samples}
    opposite = sum(s[0] != s[2] for s in samples)
    yield (
        f"mill: the wheel turns (paddles A {a_seen}, B {b_seen}, opposite in {opposite}/8)",
        a_seen == b_seen == {True, False} and opposite >= 5,
    )
    yield (
        "mill: the lever is an adventure trigger",
        adventure_ok(c["trigger_kind"]) and _block_is(c["trigger"], c["trigger_kind"]),
    )
    door = c["door"]
    shut = all(_block_is(p, MILL_STONE) for p in door)
    yield "mill: the secret door starts shut", shut
    try:
        L.lever(c["lever"], c["lever_facing"], "wall", powered=True)
        poke(c["first_dust"])
        L.tick(20)
        yield (
            "mill: the lever opens the stones",
            all(L.is_block(p, L.AIR) for p in door),
        )
        yield (
            "mill: a ladder down and a dry, lit tunnel to the guard room",
            all(_block_is(p, "minecraft:ladder") for p in c["shaft"])
            and all(_block_is(p, L.AIR) for p in c["tunnel"])
            and not any(L.is_block(p, L.WATER) for p in c["tunnel"]),
        )
    finally:
        L.lever(c["lever"], c["lever_facing"], "wall", powered=False)
        poke(c["first_dust"])
        L.tick(20)
    yield "mill: the lever shuts them", all(_block_is(p, MILL_STONE) for p in door)


# ================================================================ the stage


def bailey_machines() -> str:
    """the stage: the clock tower, the archery range, the mill and its
    tunnel, the listening door (built again after the dungeons stage)"""
    clock_tower()
    archery()
    mill()
    # the path from the main street to the door
    L.fill(
        V(63, -1, MILL[1] - 2),
        V(MILL_HOUSE[0] + 5, -1, MILL[1] - 1),
        "minecraft:dirt_path",
    )
    after_dungeons()
    return "the clock tower, the archery lock, the mill, the listening door"


def after_dungeons() -> None:
    """what castle's dungeons stage would wall up: the listening door in the
    oubliette and the tunnel's doorway into the guard room"""
    listening_door()
    guard_room_join()


def checks(at: At = V) -> Result:
    yield from check_clock_tower(at)
    yield from check_archery(at)
    yield from check_mill(at)
    yield from check_listening_door(at)
