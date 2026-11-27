"""
Draw Hull Breach from its plan (dome_hullbreach.py), with no server::

    python render_hullbreach.py [OUT.png]

Three pictures side by side: the chamber from above the entry hall with
the dome's glass left out (each block a little cube; the near half cut
away below the walk so the floor shows), the room from straight above,
and a section across the middle with the water at the flood line. It
draws what ``dome_hullbreach.room_blocks`` says, every breach sound and
the room dry (the section: at the line, three breaches open): no text, no
entities, no light. A quick look at the shape of the room.

On a branch whose ring has no ``hullbreach`` yet the room is drawn at the
Clockwork Maze's site (the same size, entered from the east, its exit
straight ahead).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import station_layout as L  # noqa: E402

if "hullbreach" not in [d.key for d in L.DOMES]:
    _SITE, _REAL = L.index_of("maze"), L.index_of
    L.index_of = lambda key: _SITE if key == "hullbreach" else _REAL(key)

import dome_hullbreach as H  # noqa: E402
import domes  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

#: a colour for each block, by the first of these found in its name
COLOURS = (
    ("gold_block", (232, 190, 60)),
    ("raw_iron", (190, 160, 140)),
    ("iron_block", (215, 215, 220)),
    ("exposed_chiseled", (190, 140, 110)),
    ("red_concrete", (170, 30, 30)),
    ("oxidized", (80, 160, 140)),
    ("weathered", (110, 150, 115)),
    ("copper_grate", (190, 120, 90)),
    ("copper_bulb[lit=true]", (255, 210, 120)),
    ("copper_bulb", (140, 80, 55)),
    ("sea_lantern", (210, 235, 230)),
    ("lantern", (255, 200, 110)),
    ("exposed", (180, 125, 100)),
    ("chiseled_copper", (200, 120, 85)),
    ("copper", (205, 115, 80)),
    ("deepslate_tiles", (55, 55, 62)),
    ("deepslate", (75, 75, 80)),
    ("anvil", (60, 60, 65)),
    ("redstone", (190, 30, 20)),
    ("blast_furnace", (90, 90, 95)),
    ("lightning_rod", (215, 135, 95)),
    ("repeater", (170, 160, 160)),
    ("piston", (120, 150, 90)),
    ("iron_bars", (150, 150, 155)),
    ("iron_chain", (110, 110, 115)),
    ("ladder", (160, 120, 70)),
    ("glass", (200, 225, 240)),
    ("lectern", (150, 110, 60)),
    ("water", (40, 90, 200)),
    ("button", (30, 30, 30)),
    ("lever", (120, 120, 120)),
    ("sign", (180, 150, 90)),
)
DOME = L.DOMES[H.INDEX]
FR = H.frame(DOME)


def colour(block: str) -> tuple[int, int, int]:
    for word, rgb in COLOURS:
        if word in block:
            return rgb
    return (255, 0, 255)


def shade(rgb, by: float) -> tuple[int, int, int]:
    return (int(rgb[0] * by), int(rgb[1] * by), int(rgb[2] * by))


def plan() -> dict[H.Cell, str]:
    """every block of the room as built: the dome's floor, the floor
    relaid, what stands on it, and the outgoing pump engine"""
    cells = domes.dome_cells(DOME)
    lights = domes.light_cells(DOME)[0]
    out = {c: (domes.LIGHT if c in lights else domes.FLOOR) for c in cells.floor}
    out.update(H.fixed_blocks(DOME, H.START))
    out.update({c: b for c, b in H.engine_blocks(DOME).items() if b != H.AIR})
    return {c: b for c, b in out.items() if b != H.AIR}


def oblique(blocks: dict[H.Cell, str], size: int = 10) -> Image.Image:
    """the room seen from above its back left (behind the entry hall, to
    the left), the near quarter cut away below the gantry so the floor,
    the column and the breaches show"""
    r = DOME.radius
    w, h = size * 4 * r + 80, size * 3 * r + 160
    image = Image.new("RGB", (w, h), (18, 24, 34))
    draw = ImageDraw.Draw(image)
    half = size // 2
    shown = {}
    for cell, block in blocks.items():
        f, rr, up = H.fr_of(FR, cell)
        if f < 0 and rr < 0 and 0 < up < H.GANTRY_H:
            continue  # the cut-away
        shown[cell] = (rr, f, up, block)
    # far first: the viewer is at -f, -r, above
    for cell in sorted(
        shown, key=lambda c: (-(shown[c][0] + shown[c][1]), shown[c][2])
    ):
        e, n, up, block = shown[cell]
        sx = w // 2 + (e - n) * size
        sy = h - 40 - r * size - (e + n) * half - up * size
        rgb = colour(block)
        top = [
            (sx, sy),
            (sx + size, sy - half),
            (sx + 2 * size, sy),
            (sx + size, sy + half),
        ]
        left = [
            (sx, sy),
            (sx + size, sy + half),
            (sx + size, sy + half + size),
            (sx, sy + size),
        ]
        right = [
            (sx + size, sy + half),
            (sx + 2 * size, sy),
            (sx + 2 * size, sy + size),
            (sx + size, sy + half + size),
        ]
        draw.polygon(left, fill=shade(rgb, 0.6))
        draw.polygon(right, fill=shade(rgb, 0.8))
        draw.polygon(top, fill=rgb)
    return image


def from_above(blocks: dict[H.Cell, str], size: int = 9) -> Image.Image:
    """the highest block of every column, darker the lower it is"""
    r = DOME.radius
    image = Image.new("RGB", ((2 * r + 1) * size, (2 * r + 1) * size), (18, 24, 34))
    draw = ImageDraw.Draw(image)
    tops: dict[tuple[int, int], tuple[int, str]] = {}
    for cell, block in blocks.items():
        f, rr, up = H.fr_of(FR, cell)
        if up >= tops.get((f, rr), (-1, ""))[0]:
            tops[f, rr] = (up, block)
    for (f, rr), (up, block) in tops.items():
        x, y = (rr + r) * size, (r - f) * size
        fill = shade(colour(block), 0.45 + 0.55 * min(up, 20) / 20)
        draw.rectangle([x, y, x + size - 1, y + size - 1], fill=fill)
    return image


def section(size: int = 12) -> Image.Image:
    """a slice across the chamber (along r, a little forward of the
    column), the water at the line and three breaches open"""
    r = DOME.radius
    state = H.State(w=H.MAX, open=frozenset({2, 5, 9}))
    blocks = plan() | H.fixed_blocks(DOME, state) | H.fluid_blocks(DOME, state)
    image = Image.new("RGB", ((2 * r + 1) * size, (r + 2) * size), (18, 24, 34))
    draw = ImageDraw.Draw(image)
    for depth in range(8, 1, -1):  # what is behind the slice, dimmer
        for cell, block in blocks.items():
            f, rr, up = H.fr_of(FR, cell)
            if f != depth or block == H.AIR:
                continue
            x, y = (rr + r) * size, (r - up) * size
            dim = 0.35 + 0.65 * (8 - depth) / 6
            draw.rectangle(
                [x, y, x + size - 1, y + size - 1], fill=shade(colour(block), dim)
            )
    return image


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("hullbreach_room.png")
    blocks = plan()
    pictures = [oblique(blocks), from_above(blocks), section()]
    width = sum(p.width for p in pictures) + 20 * (len(pictures) - 1)
    sheet = Image.new("RGB", (width, max(p.height for p in pictures)), (255, 255, 255))
    x = 0
    for picture in pictures:
        sheet.paste(picture, (x, 0))
        x += picture.width + 20
    sheet.save(out)
    print(f"wrote {out}: {len(blocks)} blocks")


if __name__ == "__main__":
    main()
