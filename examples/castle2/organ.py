"""
The organ (castle2's chapel, phase 6): a sequence lock. Six keys (birch
buttons on quartz keys, C D E F G A from the west, named on two signs over
them) on the chapel's north wall west of the altar; each key sounds a note
block behind it. Played in the order of ORGAN_TUNE, they open the crypt's
second chamber, behind its south wall; the tune is carved on Brother
Cantor's tomb in the crypt. A key that does not move the tune on (one not
in the tune, or one played out of turn) starts it again; the chamber stays
open until then.

How it works, all plain redstone under the chapel's floor and the ward:

- a sounding note block changes state: a column of observers under it
  carries a pulse down (the press and the release each give one), and a run
  of observers takes it to its stage's unit in the logic plane (y 13, z
  4..12; each run at its own level, so runs cross without touching, and all
  about the same length, so pulses keep the order they were played in);
- one unit per note of the tune, west to east in the tune's order: a
  repeater lengthens the pulse, and a subtract comparator G passes it only
  while the previous unit is set (its side reads the previous latch's "not
  set") into the block A of an RS latch of two torches, which then holds;
- each run's pulse, at its end (or at the top, for the keys not in the
  tune), also runs along the "any key" line (y 15), and G's pulse, from the
  block A it powers, along the "advance" line (y 11); at the west end a
  subtract comparator fires a reset when a key's pulse comes without an
  advance (both lines have repeaters at the same places, and the key's
  pulse is held back to fall inside the advance's); the reset runs along
  the plane's north row into every latch's other block B;
- the last latch's torch powers the block above it, and that line runs
  east, south over the crypt and down to the torch of a sliding door in the
  crypt's south wall.
"""

from __future__ import annotations

import castle_lib as L
from castle2_layout import ORGAN_KEYS, ORGAN_TUNE, V
from machines_upper import (
    AIR,
    DUST,
    STONE,
    Frame,
    diode,
    door_cells,
    door_open,
    door_shut,
    item_list,
    slide_door,
    wall_torch,
)

from mciwb.imports import Vec3

NOTES = "CDEFGA"
NOTE_PITCH = {"C": 6, "D": 8, "E": 10, "F": 11, "G": 13, "A": 15}
KEY_Y, KEY_Z = 19, 16  # keys on z 16, buttons on z 17, note blocks on z 15
PLANE_Y, UX, UZ, UNIT_DX = 13, 84, 8, 6  # unit j: a, b -> UX + 6 j + a, UZ + b
# the level of each stage's run, chosen so that the runs are the same length
LANE_LEVELS = [9, 7, 8, 12]
ANY_Y, ANY_Z = 15, 12  # the any-key line, along z 12
ADV_Y, ADV_Z = 11, 8  # the advance line, along z 8
R_Z = UZ - 4  # the reset row (y 13)
R2 = (79, 11, 9)  # the reset comparator
LINE_REPEATERS = (93, 82)  # x of the repeaters on both lines
CHAMBER_DOOR = (98, 8, 30)  # in the crypt's south wall; frame: a south, b east
CHAMBER_MATERIAL = L.DARK_BRICK
WOOD = "minecraft:dark_oak_planks"
TOMB = [(96, 8, 28), (97, 8, 28)]  # Brother Cantor's tomb, the tune on its signs
FACING = {
    (1, 0, 0): "east",
    (-1, 0, 0): "west",
    (0, 0, 1): "south",
    (0, 0, -1): "north",
    (0, 1, 0): "up",
    (0, -1, 0): "down",
}


def key_x(note: str) -> int:
    return ORGAN_KEYS[0] + NOTES.index(note)


def unit_x(j: int) -> int:
    return UX + UNIT_DX * j


def chamber_frame(pos=V) -> Frame:
    return Frame(CHAMBER_DOOR, Vec3(0, 0, 1), Vec3(1, 0, 0), pos)


def organ_cells(pos=V) -> dict:
    f = chamber_frame(pos)
    c = door_cells(f, "torch")
    c.update(
        {
            "keys": {n: pos(key_x(n), KEY_Y, KEY_Z) for n in NOTES},
            "buttons": {n: pos(key_x(n), KEY_Y, KEY_Z + 1) for n in NOTES},
            "notes": {n: pos(key_x(n), KEY_Y, KEY_Z - 1) for n in NOTES},
            "trigger": pos(key_x("C"), KEY_Y, KEY_Z + 1),
            "trigger_kind": "#minecraft:buttons",
            "material": CHAMBER_MATERIAL,
            "set": [
                pos(unit_x(j) + 2, PLANE_Y, UZ - 2) for j in range(len(ORGAN_TUNE))
            ],
            "tomb_signs": [pos(x, y, z - 1) for x, y, z in TOMB],
            "chamber": f(3, -2, 0),
            "chest": f(4, -3, 0),
        }
    )
    return c


def put(pos, x: int, y: int, z: int, block: str) -> None:
    L.set_block(pos(x, y, z), block)


def dust_path(pos, points: list[tuple[int, int, int]]) -> None:
    """dust along points (each a step along x or z, up or down at most 1),
    solid under each and air over the lower end of every step"""
    for x, y, z in points:
        put(pos, x, y - 1, z, STONE)
    for k, (x, y, z) in enumerate(points):
        put(pos, x, y, z, DUST)
        if k:
            px, py, pz = points[k - 1]
            if py > y:
                put(pos, x, y + 1, z, AIR)
            elif py < y:
                put(pos, px, py + 1, pz, AIR)


def observer_run(pos, points: list[tuple[int, int, int]]) -> None:
    """a line of observers carrying a pulse: each watches the one before it
    (the first point is what the first observer watches)"""
    for k in range(1, len(points)):
        x, y, z = points[k]
        px, py, pz = points[k - 1]
        facing = FACING[(px - x, py - y, pz - z)]
        put(pos, x, y, z, f"minecraft:observer[facing={facing}]")


def lane_points(j: int) -> list[tuple[int, int, int]]:
    """stage j's run: from its key's note block down the column (z 15), north
    one, along z 14 at its level to its unit's x, north one, up (z 13) to the
    plane and into the unit's (0, 4)"""
    x0, ux, y = key_x(ORGAN_TUNE[j]), unit_x(j), LANE_LEVELS[j]
    pts = [(x0, KEY_Y, KEY_Z - 1)]
    pts += [(x0, yy, KEY_Z - 1) for yy in range(KEY_Y - 1, y - 1, -1)]
    pts.append((x0, y, KEY_Z - 2))
    if ux != x0:
        step = 1 if ux > x0 else -1
        pts += [(x, y, KEY_Z - 2) for x in range(x0 + step, ux + step, step)]
    pts.append((ux, y, KEY_Z - 3))
    pts += [(ux, yy, KEY_Z - 3) for yy in range(y + 1, PLANE_Y + 1)]
    pts.append((ux, PLANE_Y, UZ + 4))
    return pts


def build_unit(pos, j: int) -> None:
    """stage j's unit: (a, b) cells round its latch, A at (0, 1), B at (2, -1)"""
    ux, y, last = unit_x(j), PLANE_Y, len(ORGAN_TUNE) - 1

    def at(a: int, b: int, block: str, h: int = 0) -> None:
        put(pos, ux + a, y + h, UZ + b, block)

    at(0, 3, diode("repeater", "south", "delay=4"))  # lengthens the run's pulse
    at(0, 2, diode("comparator", "south", "mode=subtract"))  # G
    at(0, 1, STONE)  # A
    at(1, 1, wall_torch("east"))  # Ta, lit while not set
    at(2, 1, DUST)
    at(2, 0, DUST)
    at(2, -1, STONE)  # B
    at(2, -2, wall_torch("north", lit=False))  # Tb, lit while set
    at(2, -2, STONE, 1)  # powered by Tb while set
    for a, b in ((1, -2), (0, -2), (0, -1), (0, 0)):
        at(a, b, DUST)  # Tb's dust into A: the latch holds
    # the reset into B from the reset row
    at(3, -1, diode("repeater", "east"))
    for b in (-1, -2, -3, -4):
        at(4, b, DUST)
    if j < last:  # "not set" on to the next unit's G
        at(3, 1, diode("repeater", "west"))
        at(4, 1, DUST)
        at(4, 2, DUST)
        at(5, 2, diode("repeater", "west"))
    # the advance: dust under A (powered only by G's pulse, not by the
    # latch's dust), down to the advance line
    at(0, 1, DUST, -1)
    at(-1, 1, DUST, -1)
    at(-1, 0, AIR, -1)
    at(-1, 0, DUST, -2)
    # the any-key tap: an observer over the run's end, the line's dust on it
    put(pos, ux, ANY_Y - 1, ANY_Z, "minecraft:observer[facing=down]")


def organ(pos=V) -> dict:
    """the keyboard, the runs, the units, the reset, the chamber and the tomb"""
    c = organ_cells(pos)
    # the machine's block, solid: under the ward north of the chapel and under
    # the organ, and the line's way over the crypt to the chamber
    L.fill(pos(70, 5, 3), pos(108, 16, 15), STONE)
    L.fill(pos(104, 13, 3), pos(108, 16, 33), STONE)
    L.fill(pos(92, 6, 30), pos(108, 15, 37), CHAMBER_MATERIAL)
    keyboard(pos)
    for j in range(len(ORGAN_TUNE)):
        build_unit(pos, j)
        observer_run(pos, lane_points(j))
    # the keys not in the tune: their column's pulse into the any-key line
    for note in NOTES:
        if note not in ORGAN_TUNE:
            x = key_x(note)
            put(pos, x, 16, KEY_Z - 2, "minecraft:observer[facing=south]")
            put(pos, x, 16, KEY_Z - 3, DUST)
            put(pos, x, 16, ANY_Z, AIR)
    # the any-key and advance lines, west to the reset comparator
    east = unit_x(len(ORGAN_TUNE) - 1)
    for x in range(R2[0] + 2, east + 1):
        put(pos, x, ANY_Y, ANY_Z, DUST)
        put(pos, x, ADV_Y, ADV_Z, DUST)
    for x in LINE_REPEATERS:
        put(pos, x, ANY_Y, ANY_Z, diode("repeater", "east"))
        put(pos, x, ADV_Y, ADV_Z, diode("repeater", "east"))
    reset_cluster(pos)
    chamber(pos, c)
    return c


def keyboard(pos) -> None:
    pipes = [3, 4, 5, 5, 4, 3]
    for k, note in enumerate(NOTES):
        x = key_x(note)
        put(pos, x, KEY_Y - 1, KEY_Z, WOOD)
        put(pos, x, KEY_Y, KEY_Z, "minecraft:quartz_block")
        put(pos, x, KEY_Y + 1, KEY_Z, WOOD)
        put(pos, x, KEY_Y, KEY_Z + 1, "minecraft:birch_button[face=wall,facing=south]")
        put(pos, x, KEY_Y, KEY_Z - 1, f"minecraft:note_block[note={NOTE_PITCH[note]}]")
        put(pos, x, KEY_Y + 1, KEY_Z - 1, AIR)  # a note block sounds only so
        for h in range(pipes[k]):
            put(pos, x, KEY_Y + 2 + h, KEY_Z - 1, "minecraft:iron_bars")
        for yy in range(KEY_Y - 1, 15, -1):
            put(pos, x, yy, KEY_Z - 1, "minecraft:observer[facing=up]")
    L.sign(
        pos(key_x("D"), KEY_Y + 1, KEY_Z + 1),
        "dark_oak_wall_sign[facing=south]",
        "C   D   E",
    )
    L.sign(
        pos(key_x("G"), KEY_Y + 1, KEY_Z + 1),
        "dark_oak_wall_sign[facing=south]",
        "F   G   A",
    )


def reset_cluster(pos) -> None:
    """R2 (subtract): rear the any-key pulse, held back by six repeaters;
    side the advance; out north, lengthened, up to the reset row"""
    rx, ry, rz = R2
    put(pos, rx, ry, rz, diode("comparator", "south", "mode=subtract"))
    # the advance into R2's east side
    put(pos, rx + 2, ADV_Y, ADV_Z, DUST)
    put(pos, rx + 2, ADV_Y, ADV_Z + 1, DUST)
    put(pos, rx + 1, ADV_Y, ADV_Z, STONE)
    put(pos, rx + 1, ry, rz, diode("repeater", "east"))
    # the any-key pulse: three repeaters on y 15, down a stair, one more,
    # and the last (lengthening it) into R2's rear (south)
    for x in range(rx - 1, rx + 2):
        put(pos, x, ANY_Y, ANY_Z, diode("repeater", "east"))
    put(pos, rx - 2, ANY_Y, ANY_Z, DUST)
    dust_path(
        pos,
        [(rx - 3, 15, 12), (rx - 4, 14, 12), (rx - 5, 13, 12), (rx - 6, 12, 12)],
    )
    dust_path(pos, [(rx - 6, 12, 12), (rx - 7, 11, 12), (rx - 7, 11, 11)])
    put(pos, rx - 6, 11, 11, diode("repeater", "west"))
    dust_path(pos, [(x, 11, 11) for x in range(rx - 5, rx + 1)])
    # (two ticks long: a comparator misses a pulse of one)
    put(pos, rx, ry, rz + 1, diode("repeater", "south", "delay=2"))
    # out: lengthened, up to the reset row and east along it
    put(pos, rx, ry, rz - 1, diode("repeater", "south", "delay=4"))
    dust_path(pos, [(rx, 11, rz - 2), (rx, 12, rz - 3), (rx, 13, rz - 4)])
    row = [(x, PLANE_Y, R_Z) for x in range(rx, unit_x(len(ORGAN_TUNE) - 1) + 5)]
    dust_path(pos, [(rx, 13, rz - 4), *row])
    for x in (unit_x(0) + 1, unit_x(2) + 1):
        put(pos, x, PLANE_Y, R_Z, diode("repeater", "west"))


def chamber(pos, c: dict) -> None:
    """the line from the last latch to the chamber's door, the chamber, its
    tomb and chest, and Brother Cantor's tomb in the crypt with the tune"""
    last = len(ORGAN_TUNE) - 1
    tx = unit_x(last) + 2  # over the last Tb: (tx, 14, UZ - 2) powered while set
    line = [(tx, 15, UZ - 2)]
    line += [(x, 15, UZ - 2) for x in range(tx + 1, 108)]
    line += [(107, 15, z) for z in range(UZ - 1, 33)]
    line += [(107 - k, 15 - k, 32) for k in range(1, 7)]  # down to (101, 9, 32)
    dust_path(pos, line)
    for z in (UZ + 2, 20, 30):
        put(pos, 107, 15, z, diode("repeater", "north"))
    f = chamber_frame(pos)
    # the chamber behind the crypt's south wall (a south, b east)
    for a in range(1, 6):
        for b in range(-4, 2):
            for h in range(0, 3):
                L.set_block(f(a, b, h), AIR)
    slide_door(f, CHAMBER_MATERIAL, "torch", pilaster=CHAMBER_MATERIAL)
    for b in (1, 2):
        L.set_block(f(-1, b, 2), "minecraft:deepslate_brick_slab[type=bottom]")
    # the organist's tomb in the chamber, a chest at its foot, candles
    for b in (-3, -2):
        L.set_block(f(3, b, 0), "minecraft:polished_deepslate")
    L.set_block(f(3, -3, 1), "minecraft:skeleton_skull[rotation=4]")
    L.set_block(f(3, -2, 1), "minecraft:white_candle[candles=3,lit=true]")
    treasure = [
        ("music_disc_otherside", 1),
        ("enchanted_golden_apple", 1),
        ("diamond", 8),
        ("emerald", 16),
        ("golden_helmet", 1),
    ]
    L.set_block(
        c["chest"], f"minecraft:chest[facing=north]{{Items:[{item_list(treasure)}]}}"
    )
    L.set_block(f(2, -4, 2), f"{L.SOUL_LANTERN}[hanging=true]")
    # Brother Cantor's tomb in the crypt, by the door, with the tune
    for x, y, z in TOMB:
        put(pos, x, y, z, "minecraft:polished_deepslate")
        put(pos, x, y + 1, z, "minecraft:polished_deepslate_slab[type=bottom]")
    a_sign, b_sign = c["tomb_signs"]
    L.sign(
        a_sign,
        "dark_oak_wall_sign[facing=north]",
        "Brother Cantor",
        "organist",
        "of this chapel",
    )
    L.sign(
        b_sign,
        "dark_oak_wall_sign[facing=north]",
        "Play me home:",
        "  ".join(ORGAN_TUNE),
        "and I will",
        "let you in.",
    )


# ---------------------------------------------------------------- working it


def press(c: dict, note: str) -> None:
    """a key pressed and let go, by command: a redstone block in place of
    the key block powers the note block as the button would"""
    k = c["keys"][note]
    L.set_block(k, "minecraft:redstone_block")
    L.tick(30)  # as long as a wooden button stays in
    L.set_block(k, "minecraft:quartz_block")
    L.tick(30)


def play(c: dict, notes) -> None:
    for note in notes:
        press(c, note)
    L.tick(40)


def wrong_key() -> str:
    return next(n for n in NOTES if n not in ORGAN_TUNE)


def work_organ(check, pos=V) -> None:
    c = organ_cells(pos)
    m = c["material"]
    check("organ: its keys are buttons", L.is_block(c["trigger"], c["trigger_kind"]))
    tune = list(ORGAN_TUNE)
    try:
        play(c, [wrong_key()])
        check("organ: the chamber's door starts shut", door_shut(c, m))
        play(c, tune)
        check(
            f"organ: playing {' '.join(tune)} opens the crypt's chamber", door_open(c)
        )
        play(c, [wrong_key()])
        check("organ: a key not in the tune shuts it again", door_shut(c, m))
        play(c, [tune[0], tune[2]] + tune[1:])
        check("organ: a note out of turn starts the tune again", door_shut(c, m))
        play(c, tune)
        check("organ: the tune opens it again", door_open(c))
    finally:
        play(c, [wrong_key()])
    check("organ: put back, the door shut", door_shut(c, m))
