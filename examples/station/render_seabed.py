"""
Draw the dressed sea floor (seabed.py) from above, with no server::

    python render_seabed.py [OUT.png]

Two pictures, one over the other. The first is the plan: the surveyed sea
floor (lighter the higher), the domes and tunnels in outline, and the top
block of every dressed column in its own colour. The second is the light
the plan gives the water just over the floor, 0 to 15, counted level from
each lantern and each cluster of sea pickles (heights are left out, and so
are the domes' own lanterns): where it is black a player sees nothing.
The default file is ``seabed_plan.png`` beside this one.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import seabed as S  # noqa: E402
import station_layout as layout  # noqa: E402
import tunnels  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

SCALE = 4  # pixels a block
COLOURS = {
    "tube": (60, 100, 230),
    "brain": (235, 110, 180),
    "bubble": (180, 50, 200),
    "fire": (225, 50, 50),
    "horn": (235, 215, 70),
    "sea_lantern": (225, 250, 245),
    "sea_pickle": (150, 230, 60),
    "seagrass": (40, 130, 60),
    "dead": (120, 120, 120),
}


def colour(block: str) -> tuple[int, int, int]:
    for word, rgb in COLOURS.items():
        if word in block:
            return rgb
    return (255, 0, 255)


def light(where: S.Site, blocks: dict[S.Cell, str]) -> np.ndarray:
    """the block light over each column, as the plan's sources give it"""
    nx, nz = where.floor.shape
    out = np.zeros((nx, nz), int)
    for (x, _, z), block in blocks.items():
        if block == S.LANTERN:
            level = 15
        elif S.PICKLE in block:
            level = 3 + 3 * int(block.partition("pickles=")[2][0])
        else:
            continue
        i, j = x - where.x0, z - where.z0
        for di in range(-level, level + 1):
            for dj in range(-level + abs(di), level - abs(di) + 1):
                if 0 <= i + di < nx and 0 <= j + dj < nz:
                    here = level - abs(di) - abs(dj)
                    out[i + di, j + dj] = max(out[i + di, j + dj], here)
    return out


def outline(draw: ImageDraw.ImageDraw, where: S.Site, fill) -> None:
    """the domes and the tunnels"""

    def px(x: float, z: float) -> tuple[float, float]:
        return ((x - where.x0) * SCALE, (z - where.z0) * SCALE)

    for d in layout.DOMES:
        (cx, cz), r = d.centre, d.radius + 0.5
        draw.ellipse([px(cx - r, cz - r), px(cx + r + 1, cz + r + 1)], outline=fill)
    half = tunnels.DOOR_HALF_WIDTH + 1
    for t in layout.TUNNELS:
        ax, az = abs(t.step[1]) * half, abs(t.step[0]) * half
        lo = px(min(t.a[0], t.b[0]) - ax, min(t.a[2], t.b[2]) - az)
        hi = px(max(t.a[0], t.b[0]) + ax + 1, max(t.a[2], t.b[2]) + az + 1)
        draw.rectangle([lo, hi], outline=fill)


def pictures() -> tuple[Image.Image, Image.Image]:
    where, blocks = S.site(), S.plan()
    nx, nz = where.floor.shape
    # the floor: darker the deeper, between the dressed heights
    depth = np.clip((where.floor - S.FLOOR_LOW) / (S.FLOOR_HIGH - S.FLOOR_LOW), 0, 1)
    ground = np.stack(
        [30 + 60 * depth, 55 + 75 * depth, 75 + 70 * depth], axis=-1
    ).astype(np.uint8)
    tops: dict[tuple[int, int], tuple[int, str]] = {}
    for (x, y, z), block in blocks.items():
        if y >= tops.get((x, z), (-999, ""))[0]:
            tops[x, z] = (y, block)
    for (x, z), (_, block) in tops.items():
        ground[x - where.x0, z - where.z0] = colour(block)
    lit = light(where, blocks)
    glow = np.stack([lit * 9, lit * 15, lit * 17], axis=-1).astype(np.uint8)
    out = []
    for array, line in ((ground, (255, 255, 255)), (glow, (255, 140, 60))):
        image = Image.fromarray(array.transpose(1, 0, 2), "RGB")
        image = image.resize((nx * SCALE, nz * SCALE), Image.Resampling.NEAREST)
        outline(ImageDraw.Draw(image), where, line)
        out.append(image)
    return out[0], out[1]


def main() -> None:
    out = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).with_name("seabed_plan.png")
    )
    plan, glow = pictures()
    sheet = Image.new("RGB", (plan.width, plan.height + glow.height + 8), (255,) * 3)
    sheet.paste(plan, (0, 0))
    sheet.paste(glow, (0, plan.height + 8))
    sheet.save(out)
    where, lit = S.site(), light(S.site(), S.plan())
    dark = float((lit[where.free] < 4).mean())
    print(
        f"wrote {out}: {len(S.plan())} blocks; {dark:.0%} of the free floor under light 4"
    )


if __name__ == "__main__":
    main()
