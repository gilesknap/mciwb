"""
Draw the Pump House from its plan (dome_start.py), with no server::

    python render_start.py [OUT.png]

Three pictures side by side: the room from above and the south west with
the dome's glass left out (each block a little cube), the map wall as a
player facing it sees it, and the room from straight above. It draws what
``dome_start.blocks`` and ``floor_blocks`` say, as they are after a reset:
no text, no entities, no light. A quick look at the shape of the room, to
catch what a list of blocks does not show.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import dome_start as S  # noqa: E402
import domes  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

#: a colour for each block, by the first of these found in its name
COLOURS = (
    ("gold_block", (232, 190, 60)),
    ("gilded", (70, 55, 40)),
    ("oxidized", (80, 160, 140)),
    ("copper_grate", (190, 120, 90)),
    ("copper_bars", (150, 95, 70)),
    ("copper_bulb[lit=true]", (255, 210, 120)),
    ("copper_bulb", (140, 80, 55)),
    ("lantern", (255, 230, 150)),
    ("lightning_rod", (215, 135, 95)),
    ("chiseled_copper", (200, 120, 85)),
    ("copper", (205, 115, 80)),
    ("dark_prismarine", (45, 95, 85)),
    ("prismarine", (80, 150, 140)),
    ("sea_lantern", (210, 235, 230)),
    ("blackstone", (45, 42, 50)),
    ("deepslate", (75, 75, 80)),
    ("dark_oak", (70, 45, 25)),
    ("oak_planks", (170, 135, 80)),
    ("sandstone", (220, 205, 150)),
    ("moss", (95, 125, 50)),
    ("ochre", (245, 200, 90)),
    ("verdant", (150, 220, 130)),
    ("pearlescent", (240, 200, 235)),
    ("redstone_lamp", (110, 65, 35)),
    ("redstone", (190, 30, 20)),
    ("repeater", (170, 160, 160)),
    ("piston", (120, 150, 90)),
    ("iron", (200, 200, 200)),
    ("glass", (200, 225, 240)),
    ("lectern", (150, 110, 60)),
    ("button", (30, 30, 30)),
    ("door", (190, 110, 80)),
    ("lever", (120, 120, 120)),
)


def colour(block: str) -> tuple[int, int, int]:
    for word, rgb in COLOURS:
        if word in block:
            return rgb
    return (255, 0, 255)


def shade(rgb, by: float) -> tuple[int, int, int]:
    return (int(rgb[0] * by), int(rgb[1] * by), int(rgb[2] * by))


def plan() -> dict[S.Cell, str]:
    """every block of the room: the dome's floor, the floor relaid, and
    what stands on it"""
    cells = domes.dome_cells(S.DOME)
    lights = domes.light_cells(S.DOME)[0]
    out = {c: (domes.LIGHT if c in lights else domes.FLOOR) for c in cells.floor}
    solid, fit = S.blocks()
    out.update(S.floor_blocks())
    out.update(solid)
    out.update(fit)
    return out


def local(cell: S.Cell) -> tuple[int, int, int]:
    """a cell as steps east, north and up from the middle of the floor"""
    x, y, z = S.DOME.floor_centre
    dx, dz = cell[0] - x, cell[2] - z
    return (
        dx * S.EAST[0] + dz * S.EAST[1],
        dx * S.NORTH[0] + dz * S.NORTH[1],
        cell[1] - y,
    )


def oblique(blocks: dict[S.Cell, str], size: int = 9) -> Image.Image:
    """the room seen from above the south west corner"""
    r = S.DOME.radius
    w, h = size * 4 * r + 60, size * 3 * r + 60
    image = Image.new("RGB", (w, h), (18, 24, 34))
    draw = ImageDraw.Draw(image)
    half = size // 2
    for cell in sorted(blocks, key=lambda c: (local(c)[1] * -1 + local(c)[0], c[1])):
        e, n, up = local(cell)
        sx = w // 2 + (e + n) * size
        sy = h - 40 - r * half + (e - n) * half - up * size
        rgb = colour(blocks[cell])
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


def map_wall(blocks: dict[S.Cell, str], size: int = 22) -> Image.Image:
    """the map wall from in front: what stands out, over what is behind"""
    wall = S.MAP
    image = Image.new("RGB", (wall.width * size, wall.height * size), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    for k in range(wall.width):
        for h in range(1, wall.height + 1):
            front = blocks.get(wall.front(k, h))
            block = front or blocks.get(wall.cell(k, h), "?")
            x, y = k * size, (wall.height - h) * size
            draw.rectangle([x, y, x + size - 1, y + size - 1], fill=colour(block))
            if front:  # what stands out has an edge
                draw.rectangle([x, y, x + size - 1, y + size - 1], outline=(0, 0, 0))
    return image


def from_above(blocks: dict[S.Cell, str], size: int = 8) -> Image.Image:
    """the highest block of every column, darker the lower it is"""
    r = S.DOME.radius
    image = Image.new("RGB", ((2 * r + 1) * size, (2 * r + 1) * size), (18, 24, 34))
    draw = ImageDraw.Draw(image)
    tops: dict[tuple[int, int], tuple[int, str]] = {}
    for cell, block in blocks.items():
        e, n, up = local(cell)
        if up >= tops.get((e, n), (-1, ""))[0]:
            tops[e, n] = (up, block)
    for (e, n), (up, block) in tops.items():
        x, y = (e + r) * size, (r - n) * size
        fill = shade(colour(block), 0.55 + 0.45 * min(up, 13) / 13)
        draw.rectangle([x, y, x + size - 1, y + size - 1], fill=fill)
    return image


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("start_room.png")
    blocks = plan()
    pictures = [oblique(blocks), map_wall(blocks), from_above(blocks)]
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
