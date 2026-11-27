"""
Draw the Cargo Hold from an offline build (the fake client), with no
server::

    python cargo_render.py [OUT.png]

Four pictures: the room from above her port quarter and from above her
starboard bow, the dome's glass left out; the room from straight above;
the hold as seen forward from her stern, as the driver looks; and her
section along A2 and F2, the port side cut away. The hold is laid with a manifest (levels 5 and 6,
No. 1) and the crane drawn over A2 carrying a barrel, its displays as the
cells they fill. No text, no light: a look at the shape of the room.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_station as B  # noqa: E402
import dome_cargo as D  # noqa: E402
import domes  # noqa: E402
import station_layout as L  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

COLOURS = (
    ("gold_block", (232, 190, 60)),
    ("copper_bulb[lit=true]", (255, 214, 120)),
    ("copper_bulb", (120, 70, 50)),
    ("oxidized", (80, 160, 140)),
    ("weathered", (110, 150, 120)),
    ("copper_grate", (190, 120, 90)),
    ("chiseled_copper", (200, 120, 85)),
    ("lightning_rod", (215, 135, 95)),
    ("cut_copper_stairs", (190, 110, 75)),
    ("cut_copper_slab", (195, 112, 78)),
    ("copper", (205, 115, 80)),
    ("sea_lantern", (210, 235, 230)),
    ("lantern", (255, 220, 140)),
    ("blackstone", (45, 42, 50)),
    ("deepslate", (75, 75, 80)),
    ("andesite", (140, 140, 138)),
    ("dark_oak", (70, 45, 25)),
    ("spruce_log", (150, 115, 75)),
    ("spruce", (115, 85, 50)),
    ("lime", (120, 200, 40)),
    ("red_concrete", (160, 40, 35)),
    ("yellow", (230, 190, 40)),
    ("green_concrete", (80, 110, 30)),
    ("blue", (50, 70, 160)),
    ("iron_block", (220, 220, 220)),
    ("barrel", (140, 100, 55)),
    ("white_wool", (245, 245, 245)),
    ("hay", (200, 170, 50)),
    ("coal", (25, 25, 25)),
    ("chain", (60, 65, 75)),
    ("iron_bars", (160, 160, 165)),
    ("redstone", (190, 30, 20)),
    ("repeater", (170, 160, 160)),
    ("piston", (120, 150, 90)),
    ("bell", (240, 200, 80)),
    ("lectern", (150, 110, 60)),
    ("button", (30, 30, 30)),
    ("lever", (120, 120, 120)),
    ("torch", (220, 40, 30)),
    ("red_nether", (90, 20, 20)),
    ("fence", (70, 45, 25)),
    ("grindstone", (140, 140, 140)),
    ("anvil", (60, 60, 64)),
    ("furnace", (90, 90, 95)),
    ("sign", (200, 180, 120)),
    ("glass", (200, 225, 240)),
)


def colour(block: str) -> tuple[int, int, int]:
    for word, rgb in COLOURS:
        if word in block:
            return rgb
    return (255, 0, 255)


def shade(rgb, by: float) -> tuple[int, int, int]:
    return (int(rgb[0] * by), int(rgb[1] * by), int(rgb[2] * by))


def scene() -> tuple[D.fittings.Frame, dict[tuple[int, int, int], str]]:
    """the room as built (offline), laid with a manifest, the crane over
    A2 with a barrel on its hook: frame cell (f, r, h) -> block"""
    dome = L.DOMES[D.INDEX]
    fr = D.frame(dome)
    stages = ["site", B.dome_stage_name(D.INDEX), "tunnels", f"dome_{D.INDEX}_inside"]
    rec = B.offline_build(stages=stages, force=False)
    cells = domes.dome_cells(dome)
    ox, oy, oz = fr.origin
    out = {}
    for cell in cells.interior | cells.floor:
        block = rec.world.at(cell)
        if block and "air" not in block:
            x, y, z = cell
            f = (x - ox) * fr.forward[0] + (z - oz) * fr.forward[1]
            r = (x - ox) * fr.right[0] + (z - oz) * fr.right[1]
            out[f, r, y - oy] = block
    start = D.parse(D.BANDS[2].manifests[0][0])
    plan = D.parse(D.BANDS[2].manifests[0][1])
    for i, stack in enumerate(start):
        for t, k in enumerate(stack):
            for p in D.bay_cells(i, t):
                out[p] = D.CRATE[k]
            out[D.table_cell(D.HOLD_TABLE, i, t)] = D.CRATE[k]
    for i, stack in enumerate(plan):
        for t, k in enumerate(stack):
            for table in (D.PLAN_TABLE, D.BOW_TABLE):
                out[D.table_cell(table, i, t)] = D.CRATE[k]
    # the crane over A2, a barrel up: each display as the cells it fills
    c, vc = D.home()
    dv = D.bay_mid(1)[1] - vc
    for block, (u0, u1, v0, v1, h0, h1), tags in D.crane_boxes():
        w = dv if D.T_TAG in tags else 0
        for f in range(int(u0 // 1), int(-(-u1 // 1))):
            for r in range(int((v0 + w) // 1), int(-(-(v1 + w) // 1))):
                for h in range(int(h0 // 1), int(-(-h1 // 1))):
                    out.setdefault((f, r, h), block)
    for h in range(D.UP + 1, D.RAIL_H + 2):
        out[(-8, -2, h)] = D.CHAIN
    for f, r, _ in D.bay_cells(1, 0):
        for h in (D.UP - 2, D.UP - 1):
            out[f, r, h] = D.CRATE[D.BARREL]
    return fr, out


def oblique(blocks, sign: int = -1, size: int = 10) -> Image.Image:
    """the room from above one quarter (``sign`` -1: her port quarter,
    astern; 1: her starboard bow), each block a little cube, cropped"""
    w, h = size * 110, size * 90
    image = Image.new("RGB", (w, h), (18, 24, 34))
    draw = ImageDraw.Draw(image)
    half = size // 2
    box = [w, h, 0, 0]

    def depth(p):
        f, r, up = p
        return (sign * f + sign * r, up)

    for p in sorted(blocks, key=depth):
        f, r, up = p
        x, z = sign * f, sign * r
        sx = w // 2 + (x - z) * size - size
        sy = h // 2 + (x + z) * half - up * size
        rgb = colour(blocks[p])
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
        box = [min(box[0], sx), min(box[1], sy - half), max(box[2], sx + 2 * size),
               max(box[3], sy + half + size)]  # fmt: skip
    return image.crop((box[0] - 10, box[1] - 10, box[2] + 10, box[3] + 10))


def from_above(blocks, size: int = 9, radius: int = 24) -> Image.Image:
    """the highest block of every column, darker the lower it is; forward
    to the right, port at the top"""
    image = Image.new(
        "RGB", ((2 * radius + 1) * size, (2 * radius + 1) * size), (18, 24, 34)
    )
    draw = ImageDraw.Draw(image)
    tops: dict[tuple[int, int], tuple[int, str]] = {}
    for (f, r, up), block in blocks.items():
        if up >= tops.get((f, r), (-1, ""))[0]:
            tops[f, r] = (up, block)
    for (f, r), (up, block) in tops.items():
        x, y = (f + radius) * size, (r + radius) * size
        fill = shade(colour(block), 0.5 + 0.5 * min(up, 16) / 16)
        draw.rectangle([x, y, x + size - 1, y + size - 1], fill=fill)
    return image


def pulpit_view(blocks, size: int = 14) -> Image.Image:
    """the room seen from behind the driver, looking forward: for each
    (r, h) the nearest block from the pulpit's back rail onward"""
    width, height = 41, 18
    image = Image.new("RGB", (width * size, height * size), (18, 24, 34))
    draw = ImageDraw.Draw(image)
    for r in range(-20, 21):
        for h in range(0, height):
            for f in range(-10, 24):
                block = blocks.get((f, r, h))
                if block:
                    depth = max(0.35, 1 - (f + 10) / 40)
                    x, y = (r + 20) * size, (height - 1 - h) * size
                    draw.rectangle(
                        [x, y, x + size - 1, y + size - 1],
                        fill=shade(colour(block), depth),
                    )
                    break
    return image


def section(blocks, size: int = 12) -> Image.Image:
    """her section along A2 and F2, the port side cut away: for each (f, h)
    the nearest block from r -2 to starboard, darker the further"""
    width, height = 49, 18
    image = Image.new("RGB", (width * size, height * size), (18, 24, 34))
    draw = ImageDraw.Draw(image)
    for f in range(-24, 25):
        for h in range(0, height):
            for r in range(-2, 25):
                block = blocks.get((f, r, h))
                if block:
                    depth = max(0.3, 1 - (r + 2) / 20)
                    x, y = (f + 24) * size, (height - 1 - h) * size
                    fill = shade(colour(block), depth)
                    draw.rectangle([x, y, x + size - 1, y + size - 1], fill=fill)
                    break
    return image


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cargo_room.png")
    _, blocks = scene()
    top = [oblique(blocks, -1), oblique(blocks, 1)]
    low = [from_above(blocks), pulpit_view(blocks)]
    rows = [top, low, [section(blocks)]]
    width = max(sum(p.width for p in row) + 20 * (len(row) - 1) for row in rows)
    height = sum(max(p.height for p in row) for row in rows) + 20 * (len(rows) - 1)
    sheet = Image.new("RGB", (width, height), (255, 255, 255))
    y = 0
    for row in rows:
        x = 0
        for picture in row:
            sheet.paste(picture, (x, y))
            x += picture.width + 20
        y += max(p.height for p in row) + 20
    sheet.save(out)
    print(f"wrote {out}: {len(blocks)} blocks")


if __name__ == "__main__":
    main()
