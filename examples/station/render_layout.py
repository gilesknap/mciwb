"""
Draw the plan of the Drowned Station (`station_layout.py`) over the survey of
the sea floor (``site_survey.npz``, written by `survey_site.py`), and report
what the survey says about each dome and tunnel. Needs no server::

    python render_layout.py [SURVEY.npz [PLAN.png]]

The picture is a top view with north up: the sea shaded by depth, the land in
green, the coast outlined, depth contours, the domes, the tunnels, the dock,
the shore landing and the world spawn. It needs numpy and Pillow only.
"""

import sys
from pathlib import Path
from typing import NamedTuple

import numpy as np
import station_layout as layout
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
SCALE = 3  # pixels per block
EDGE = 40  # blocks of surroundings drawn round the station and the shore
BORDER = 46  # pixels of margin for the coordinates
CONTOURS = ((10, (120, 160, 215)), (20, (250, 235, 150)))  # depth, colour
BRASS, INK, PAPER = (255, 196, 64), (20, 24, 40), (255, 255, 255)


class Structure(NamedTuple):
    """a cell of 16 x 16 columns that holds blocks of a structure"""

    x: int  #: the cell's corner of least x and z
    z: int
    low: int  #: the y of the lowest and the highest such block
    high: int
    blocks: int  #: how many of them
    name: str  #: the block


class Survey:
    """the survey file: the sea floor and the water of a rectangle of columns"""

    def __init__(self, path: Path):
        data = np.load(path)
        self.floor = data["floor"].astype(int)
        self.wet = data["wet"] > 0
        self.bubbles = data["wet"] == 2
        self.x0, self.z0 = (int(v) for v in data["origin"])
        # cells of 16 x 16 columns holding blocks of a structure:
        # (x, z, lowest y, highest y, count, name), magma left out
        names = [str(n) for n in data["suspect_names"]] if "suspects" in data else []
        self.structures = []
        for row in data["suspects"] if names else []:
            x, z, low, high, blocks, kind = (int(v) for v in row)
            if "magma" not in names[kind]:
                self.structures.append(Structure(x, z, low, high, blocks, names[kind]))
        # layers of water over each column's floor (0 on land)
        self.depth = np.where(self.wet, layout.SEA_LEVEL - 1 - self.floor, 0)

    def window(self, x: int, z: int, radius: int) -> tuple[np.ndarray, np.ndarray]:
        """the floor and wet values of the columns of a disc"""
        xs = np.arange(x - radius, x + radius + 1)
        zs = np.arange(z - radius, z + radius + 1)
        inside = (xs[:, None] - x) ** 2 + (zs[None, :] - z) ** 2 <= radius**2
        cut = np.s_[
            x - radius - self.x0 : x + radius + 1 - self.x0,
            z - radius - self.z0 : z + radius + 1 - self.z0,
        ]
        return self.floor[cut][inside], self.wet[cut][inside]


def site_report(survey: Survey) -> list[str]:
    """what the survey says about the sea floor under each dome and tunnel"""
    lines = []
    for d in layout.DOMES:
        floor, wet = survey.window(*d.centre, d.radius)
        low, mid, high = (int(v) for v in np.percentile(floor, [5, 50, 95]))
        lines.append(
            f"dome {d.index} {d.key:9} centre {d.centre}, diameter {d.diameter}: "
            f"sea floor y {floor.min()}..{floor.max()} (5% {low}, median {mid}, "
            f"95% {high}), {wet.mean():.0%} water; floor y {d.floor_y} is "
            f"{mid - d.floor_y} below the median; top y {d.top_y}, "
            f"water above {d.water_above}"
        )
    for t in layout.TUNNELS:
        (dx, dz), n = t.step, t.length
        xs = t.a[0] + dx * np.arange(n + 1) - survey.x0
        zs = t.a[2] + dz * np.arange(n + 1) - survey.z0
        floor = survey.floor[xs, zs]
        lines.append(
            f"tunnel {t.index} {layout.DOMES[t.start].key} to "
            f"{layout.DOMES[t.end].key}: length {n}, floor y {t.a[1]} to "
            f"{t.b[1]}, sea floor under it y {floor.min()}..{floor.max()}, "
            f"{survey.wet[xs, zs].mean():.0%} water"
        )
    (bx1, by1, bz1), (bx2, _, bz2) = layout.BOUNDS
    under = [
        s
        for s in survey.structures
        if bx1 - 15 <= s.x <= bx2 and bz1 - 15 <= s.z <= bz2 and s.high >= by1 - 8
    ]
    if under:
        kinds = sorted({s.name.removeprefix("minecraft:") for s in under})
        cells = sorted({(s.x, s.z) for s in under})
        lines.append(
            f"structure blocks ({', '.join(kinds)}) at y "
            f"{min(s.low for s in under)}..{max(s.high for s in under)} in "
            f"{len(cells)} cells of 16 under the station's box: {cells}"
        )
    else:
        lines.append("no structure blocks near the floors of the station's box")
    sx, _, sz = layout.SHORE_LANDING
    dock = layout.DOCK
    row = ((dock[0] - sx) ** 2 + (dock[2] - sz) ** 2) ** 0.5
    steps = int(row) + 1
    xs = np.linspace(sx, dock[0], steps).round().astype(int) - survey.x0
    zs = np.linspace(sz, dock[2], steps).round().astype(int) - survey.z0
    lines.append(
        f"shore landing {layout.SHORE_LANDING}: ground y "
        f"{survey.floor[sx - survey.x0, sz - survey.z0]}; the row to the dock "
        f"{dock} is {row:.0f} blocks, {survey.wet[xs, zs].mean():.0%} of it "
        f"over water, least depth {survey.depth[xs, zs][survey.wet[xs, zs]].min()}"
    )
    spawn = layout.SPAWN
    walk = ((spawn[0] - sx) ** 2 + (spawn[2] - sz) ** 2) ** 0.5
    lines.append(f"world spawn {spawn} to the shore landing: {walk:.0f} blocks")
    return lines


def colours(survey: Survey) -> np.ndarray:
    """an RGB image of the survey, one pixel per column, indexed [z][x]"""
    floor, wet, depth = survey.floor, survey.wet, survey.depth
    rgb = np.zeros((*floor.shape, 3), dtype=float)
    # the sea: pale in the shallows, dark in the deep
    t = np.clip(depth / 34, 0, 1)[..., None]
    rgb[:] = (1 - t) * np.array([176, 214, 240]) + t * np.array([16, 44, 110])
    # the land: darker green with height
    h = np.clip((floor - layout.SEA_LEVEL) / 30, 0, 1)[..., None]
    land = (1 - h) * np.array([150, 196, 120]) + h * np.array([70, 120, 70])
    rgb = np.where(wet[..., None], rgb, land)

    def outline(mask: np.ndarray) -> np.ndarray:
        inner = mask.copy()
        inner[1:, :] &= mask[:-1, :]
        inner[:-1, :] &= mask[1:, :]
        inner[:, 1:] &= mask[:, :-1]
        inner[:, :-1] &= mask[:, 1:]
        return mask & ~inner

    for level, colour in CONTOURS:
        rgb[outline(wet & (depth >= level))] = colour
    rgb[outline(~wet)] = (60, 70, 40)  # the coast
    rgb[survey.bubbles] = (255, 60, 200)
    return rgb.astype(np.uint8).transpose(1, 0, 2)


def render(survey: Survey, out: Path) -> None:
    low, high = layout.BOUNDS
    points = [layout.SPAWN, layout.SHORE_LANDING]
    x1 = max(survey.x0, min(low[0], *(p[0] for p in points)) - EDGE)
    z1 = max(survey.z0, min(low[2], *(p[2] for p in points)) - EDGE)
    x2 = min(
        survey.x0 + survey.floor.shape[0], max(high[0], *(p[0] for p in points)) + EDGE
    )
    z2 = min(
        survey.z0 + survey.floor.shape[1], max(high[2], *(p[2] for p in points)) + EDGE
    )
    whole = colours(survey)[
        z1 - survey.z0 : z2 - survey.z0, x1 - survey.x0 : x2 - survey.x0
    ]
    sea = Image.fromarray(whole).resize(
        ((x2 - x1) * SCALE, (z2 - z1) * SCALE), Image.Resampling.NEAREST
    )
    image = Image.new("RGB", (sea.width + 2 * BORDER, sea.height + 2 * BORDER), PAPER)
    image.paste(sea, (BORDER, BORDER))
    draw = ImageDraw.Draw(image, "RGBA")
    small, font, big = (ImageFont.load_default(size=s) for s in (13, 16, 22))

    def px(x: float, z: float) -> tuple[float, float]:
        """the pixel of the middle of a block"""
        return (
            BORDER + (x - x1 + 0.5) * SCALE,
            BORDER + (z - z1 + 0.5) * SCALE,
        )

    def label(xy, text, face=font, anchor="mm", fill=PAPER, back=(*INK, 200)):
        box = draw.textbbox(xy, text, font=face, anchor=anchor)
        draw.rectangle((box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2), fill=back)
        draw.text(xy, text, font=face, anchor=anchor, fill=fill)

    # coordinates round the edge, every 50 blocks
    for x in range(-(-x1 // 50) * 50, x2, 50):
        u = px(x, z1)[0]
        draw.line((u, BORDER - 6, u, BORDER), fill=INK)
        draw.line((u, BORDER, u, BORDER + sea.height), fill=(0, 0, 0, 28))
        draw.text((u, BORDER - 8), f"x {x}", font=small, anchor="mb", fill=INK)
    for z in range(-(-z1 // 50) * 50, z2, 50):
        v = px(x1, z)[1]
        draw.line((BORDER - 6, v, BORDER, v), fill=INK)
        draw.line((BORDER, v, BORDER + sea.width, v), fill=(0, 0, 0, 28))
        draw.text((BORDER - 8, v), f"z {z}", font=small, anchor="rm", fill=INK)

    # cells with blocks of a structure under them (mineshafts, ruins)
    for x, z in sorted({(s.x, s.z) for s in survey.structures}):
        if x1 <= x < x2 - 15 and z1 <= z < z2 - 15:
            u, v = px(x + 7.5, z + 7.5)
            draw.line((u - 5, v - 5, u + 5, v + 5), fill=(120, 60, 30, 170), width=2)
            draw.line((u - 5, v + 5, u + 5, v - 5), fill=(120, 60, 30, 170), width=2)

    # the station's box
    (bx1, _, bz1), (bx2, _, bz2) = low, high
    draw.rectangle((*px(bx1, bz1), *px(bx2, bz2)), outline=(255, 255, 255, 150))

    # the row from the shore to the dock
    shore, dock = layout.SHORE_LANDING, layout.DOCK
    a, b = px(shore[0], shore[2]), px(dock[0], dock[2])
    for i in range(0, 40, 2):
        p = [a[k] + (b[k] - a[k]) * i / 40 for k in (0, 1)]
        q = [a[k] + (b[k] - a[k]) * (i + 1) / 40 for k in (0, 1)]
        draw.line((*p, *q), fill=PAPER, width=2)

    # tunnels, with their lengths
    for t in layout.TUNNELS:
        a, b = px(t.a[0], t.a[2]), px(t.b[0], t.b[2])
        draw.line((*a, *b), fill=INK, width=4 * SCALE)
        draw.line((*a, *b), fill=BRASS, width=2 * SCALE)
    # domes
    for d in layout.DOMES:
        (u1, v1), (u2, v2) = (
            px(d.centre[0] - d.radius, d.centre[1] - d.radius),
            px(d.centre[0] + d.radius, d.centre[1] + d.radius),
        )
        tint = (255, 120, 90, 110) if d is layout.BOSS else (150, 240, 230, 110)
        draw.ellipse((u1, v1, u2, v2), fill=tint, outline=INK, width=3)
        draw.ellipse((u1 + 3, v1 + 3, u2 - 3, v2 - 3), outline=BRASS, width=2)
    for t in layout.TUNNELS:
        a, b = px(t.a[0], t.a[2]), px(t.b[0], t.b[2])
        label(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), str(t.length), small)
    for d in layout.DOMES:
        u, v = px(*d.centre)
        draw.text((u, v - 24), str(d.index), font=big, anchor="mm", fill=INK)
        label((u, v), d.name, small)
        label(
            (u, v + 19),
            f"{d.diameter} wide  floor y {d.floor_y}",
            small,
            fill=INK,
            back=(255, 255, 255, 190),
        )

    # dock, shore landing and spawn
    u, v = px(dock[0] - 12, dock[2] - 12)
    draw.rectangle((u - 8, v - 5, u + 8, v + 5), fill=(120, 80, 40), outline=INK)
    edge = px(dock[0] - layout.START.radius, dock[2] - 14)
    label((edge[0] - 6, edge[1]), "dock + lift, above", small, anchor="rm")
    u, v = px(shore[0], shore[2])
    draw.polygon((u, v - 9, u + 9, v, u, v + 9, u - 9, v), fill=BRASS, outline=INK)
    label((u + 14, v), "shore landing", small, anchor="lm")
    u, v = px(layout.SPAWN[0], layout.SPAWN[2])
    draw.line((u - 7, v - 7, u + 7, v + 7), fill=(200, 0, 0), width=3)
    draw.line((u - 7, v + 7, u + 7, v - 7), fill=(200, 0, 0), width=3)
    label((u + 12, v + 14), "world spawn", small, anchor="lm")

    # title, north arrow, scale bar and key
    draw.text(
        (BORDER, image.height - 6),
        "The Drowned Station: plan.  Sea shaded by depth; contours at "
        + " and ".join(str(c[0]) for c in CONTOURS)
        + " blocks deep; brown crosses: mineshaft or ruin below; pink: bubble"
        " columns; tunnel lengths in blocks.",
        font=small,
        anchor="lb",
        fill=INK,
    )
    u, v = BORDER + sea.width - 40, BORDER + 50
    draw.polygon((u, v - 32, u + 10, v, u, v - 8, u - 10, v), fill=PAPER, outline=INK)
    draw.text((u, v + 4), "N", font=font, anchor="mt", fill=PAPER)
    u, v = BORDER + 20, BORDER + sea.height - 22
    draw.rectangle((u, v, u + 50 * SCALE, v + 6), fill=PAPER, outline=INK)
    draw.text(
        (u + 50 * SCALE + 8, v + 3), "50 blocks", font=small, anchor="lm", fill=PAPER
    )
    image.save(out)


if __name__ == "__main__":
    survey_file = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "site_survey.npz"
    plan_file = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "layout_plan.png"
    the_survey = Survey(survey_file)
    print(layout.describe())
    print("\n".join(site_report(the_survey)))
    problems = layout.check_layout()
    print("\n".join(problems) if problems else "layout OK")
    render(the_survey, plan_file)
    print(f"wrote {plan_file}")
