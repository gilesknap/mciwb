"""
Render a region of a Minecraft world to an image, so that you (or an AI agent)
can see what a build looks like without joining the game.

First read the blocks with `scan`, then draw them with `render`::

    from mciwb.render import scan, render

    grid = scan(Volume.from_corners(a, b), world_folder, client)
    render(grid, views=["top", "iso", "south"]).save("build.png")

The views are:

- ``top``: a plan, north up, showing the highest block of each column.
  Higher blocks are lighter, and a block higher than its northern
  neighbour has a light edge (a lower one a dark edge).
- ``north``, ``south``, ``east``, ``west``: elevations, the region seen
  from that side, e.g. ``south`` looks north at the south face. Nearer
  blocks are lighter.
- ``iso``: a 3D isometric view from the south east, with shaded faces.
  ``iso_ne``, ``iso_nw`` and ``iso_sw`` look from the other corners.

Translucent blocks (glass, water, ice) and small ones (torches, flowers,
fences) let the blocks behind them show through. Each view has axis labels
with world coordinates, unless you ask for none.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np
from mcwb import Volume
from PIL import Image, ImageDraw, ImageFont

from mciwb.anvil import read_world_blocks
from mciwb.blockgrid import BlockGrid, grab_blocks
from mciwb.logging import log
from mciwb.palette import Palette, default_palette
from mciwb.threads import Client

# the background of each view: a pale sky blue, unlike any common block
BACKGROUND = (214, 230, 245)
CANVAS = (255, 255, 255)
INK = (0, 0, 0)
GRID = (60, 60, 60)
# the largest region that `scan` reads over RCON, one block at a time
MAX_RCON_BLOCKS = 32768
# the auto scale aims for views about this many pixels across
TARGET_PIXELS = 512
MAX_SCALE = 16
# the auto scale shrinks views to keep the whole image within this width:
# models see a scaled down copy of wider images
MAX_IMAGE_PIXELS = 1500
FONT_SIZE = 12
PAD = 6
# how much darker the furthest blocks of a top view or elevation are
DEPTH_SHADE = 0.3
# how much lighter (or darker) a block higher (lower) than its northern
# neighbour is in a top view
EDGE_SHADE = 0.15


@dataclass(frozen=True)
class _Ortho:
    """
    How an orthographic view maps the region's [x][y][z] array to
    [row][column][depth], where depth 0 is nearest the viewer
    """

    title: str
    axes: tuple[int, int, int]
    flips: tuple[bool, bool, bool]
    # True to light the edges of blocks that are higher than their neighbours
    hillshade: bool = False


_ORTHO_VIEWS = {
    "top": _Ortho("top, north up", (2, 0, 1), (False, False, True), True),
    "south": _Ortho("south side, looking north", (1, 0, 2), (True, False, True)),
    "north": _Ortho("north side, looking south", (1, 0, 2), (True, True, False)),
    "east": _Ortho("east side, looking west", (1, 2, 0), (True, True, True)),
    "west": _Ortho("west side, looking east", (1, 2, 0), (True, False, False)),
}

# the number of quarter turns about y that brings each iso viewpoint to the
# south east, the viewpoint that the iso renderer draws
_ISO_VIEWS = {"iso": 0, "iso_se": 0, "iso_ne": 1, "iso_nw": 2, "iso_sw": 3}

#: the names of the views that `render` can draw
VIEWS = (*_ORTHO_VIEWS, *_ISO_VIEWS)
_AXIS_NAMES = "xyz"

# how much light each visible face of an iso block gets
_TOP, _SOUTH, _EAST = 1.0, 0.8, 0.62


# how to read the world files rather than ask over RCON
_WORLD_FOLDER_HINT = (
    "to read the world files, set world.world_folder in a script, or give "
    "mciwb render the --folder of mciwb start (without --rcon)"
)


def scan(
    vol: Volume,
    world_folder: Path | None = None,
    client: Client | None = None,
    dimension: str = "overworld",
    max_rcon_blocks: int = MAX_RCON_BLOCKS,
) -> BlockGrid:
    """
    Read the blocks in a region of the world, by the fastest means available.

    If *world_folder* is a world, its region files are read directly, after
    asking the server (if *client* is given) to save its changes to disk.
    Otherwise the blocks are read over RCON with *client*, one at a time.

    :param vol: the region to read
    :param world_folder: the server's world folder, e.g.
        ``~/mciwb-server/world`` for the server of ``mciwb start``
    :param client: an RCON client for the running server
    :param dimension: overworld, the_nether or the_end (world files only)
    :param max_rcon_blocks: refuse to read larger regions over RCON

    :raises ValueError: if neither source can read the region
    """
    if world_folder is not None and (Path(world_folder) / "level.dat").exists():
        if client is not None:
            # write the server's changes to the region files
            log.debug("save_all: " + client.save_all(flush=True))
        return read_world_blocks(Path(world_folder), vol, dimension)

    if client is None:
        where = (
            "no world folder" if world_folder is None else f"no world in {world_folder}"
        )
        raise ValueError(f"cannot read blocks: {where} and no server to ask over RCON")
    blocks = vol.size.volume
    if blocks > max_rcon_blocks:
        raise ValueError(
            f"{vol.size.i_tuple} is {blocks} blocks: too many to read over RCON "
            f"(max {max_rcon_blocks}). Pick a smaller region, or {_WORLD_FOLDER_HINT}"
        )
    if world_folder is not None:
        log.info(f"{world_folder} is not a world, so reading blocks over RCON")
    else:
        log.info(
            f"reading {blocks} blocks over RCON one at a time, which is slow: "
            f"{_WORLD_FOLDER_HINT}"
        )
    return grab_blocks(client, vol)


def render(
    grid: BlockGrid,
    views: Sequence[str] = ("top", "iso"),
    scale: int | None = None,
    labels: bool = True,
    palette: Palette | None = None,
) -> Image.Image:
    """
    Draw one or more views of a region side by side in one image.

    :param grid: the blocks, from `scan`
    :param views: the views to draw, see the module documentation
    :param scale: pixels per block for every view. By default each view gets
        its own scale, chosen to make it about 512 pixels across, or smaller
        if needed to keep the image under 1500 pixels wide
    :param labels: add a title, axis labels and grid lines with world
        coordinates
    :param palette: block colours, defaults to ``mciwb.palette.default_palette``

    :returns: a Pillow image: call its ``save("file.png")`` method to save it
    """
    if not views:
        raise ValueError("no views requested")
    if scale is not None:
        panels = [render_view(grid, v, scale, labels, palette) for v in views]
        return _layout(grid, panels, labels)

    # each view at its own automatic scale, smaller if the image is too wide
    scales = [auto_scale(grid, v) for v in views]
    panels = [
        render_view(grid, v, s, labels, palette)
        for v, s in zip(views, scales, strict=True)
    ]
    image = _layout(grid, panels, labels)
    columns = _columns(len(panels))
    while image.width > MAX_IMAGE_PIXELS:
        # the widest row: its labels and padding stay the same size as the
        # scale changes, so shrink the blocks to fit in the space left
        row = max(
            (
                range(i, min(i + columns, len(panels)))
                for i in range(0, len(panels), columns)
            ),
            key=lambda r: sum(panels[i].width for i in r),
        )
        blocks = sum(_view_size(grid, views[i])[0] * scales[i] for i in row)
        fixed = image.width - blocks
        factor = max(MAX_IMAGE_PIXELS - fixed, 0) / blocks
        smaller = [max(1, min(s - 1, int(s * factor))) for s in scales]
        if smaller == scales:
            break
        panels = [
            p if s == old else render_view(grid, v, s, labels, palette)
            for v, p, s, old in zip(views, panels, smaller, scales, strict=True)
        ]
        scales = smaller
        image = _layout(grid, panels, labels)
    return image


def _columns(panels: int) -> int:
    """the number of panels in each row of the image"""
    return panels if panels <= 3 else 2 if panels == 4 else 3


def _layout(grid: BlockGrid, panels: list[Image.Image], labels: bool) -> Image.Image:
    """Arrange the panels in rows of up to three under a header"""
    if len(panels) == 1 and not labels:
        return panels[0]

    columns = _columns(len(panels))
    rows = [panels[i : i + columns] for i in range(0, len(panels), columns)]
    widths = [sum(p.width for p in row) + PAD * (len(row) + 1) for row in rows]
    heights = [max(p.height for p in row) for row in rows]

    header = ""
    if labels:
        lo, hi = grid.origin, grid.end
        header = (
            f"x {lo.x}..{hi.x}  y {lo.y}..{hi.y}  z {lo.z}..{hi.z}  "
            f"({grid.size.x} x {grid.size.y} x {grid.size.z} blocks)"
        )
    top = _text_height() + 2 * PAD if header else PAD
    # a small region's panels can be narrower than the header
    width = max(*widths, _text_width(header) + 2 * PAD if header else 0)
    image = Image.new("RGB", (width, top + sum(heights) + PAD * len(rows)), CANVAS)
    draw = ImageDraw.Draw(image)
    if header:
        draw.text((PAD, PAD), header, fill=INK, font=_font())
    y = top
    for row, height in zip(rows, heights, strict=True):
        x = PAD
        for panel in row:
            image.paste(panel, (x, y))
            x += panel.width + PAD
        y += height + PAD
    return image


def render_view(
    grid: BlockGrid,
    view: str,
    scale: int | None = None,
    labels: bool = True,
    palette: Palette | None = None,
) -> Image.Image:
    """
    Draw one view of a region, see `render` for the parameters

    :raises ValueError: if the view is not one of `VIEWS`
    """
    palette = palette or default_palette
    if scale is None:
        scale = auto_scale(grid, view)
    if scale < 1:
        raise ValueError(f"scale must be at least 1, not {scale}")
    colours = np.array([palette.colour(n) for n in grid.names], dtype=np.float32)
    colours /= 255
    if view in _ORTHO_VIEWS:
        return _ortho(grid, _ORTHO_VIEWS[view], colours, scale, labels)
    if view in _ISO_VIEWS:
        return _iso(grid, view, _ISO_VIEWS[view], colours, scale, labels)
    raise ValueError(f"unknown view {view}, use one of {', '.join(VIEWS)}")


def auto_scale(grid: BlockGrid, view: str | None = None) -> int:
    """
    The pixels per block that make *view* about 512 pixels across and no more
    than 512 pixels high, or that do so for every view if *view* is None
    """
    if view is None:
        blocks = max(max(_view_size(grid, v)) for v in ("top", "south", "iso"))
    else:
        blocks = max(_view_size(grid, view))
    return max(1, min(MAX_SCALE, TARGET_PIXELS // blocks))


def _view_size(grid: BlockGrid, view: str) -> tuple[int, int]:
    """The width and height of a view in blocks, without its labels"""
    sx, sy, sz = grid.ids.shape
    if view in _ORTHO_VIEWS:
        rows, cols, _ = _ORTHO_VIEWS[view].axes
        return grid.ids.shape[cols], grid.ids.shape[rows]
    if view in _ISO_VIEWS:
        # turning about y keeps x + z the same
        return sx + sz, (sx + sz + 1) // 2 + sy
    raise ValueError(f"unknown view {view}, use one of {', '.join(VIEWS)}")


# ----------------------------------------------------------------------------
# orthographic views


def _ortho(
    grid: BlockGrid, spec: _Ortho, colours: np.ndarray, scale: int, labels: bool
) -> Image.Image:
    ids = grid.ids.transpose(spec.axes)
    ids = ids[tuple(slice(None, None, -1 if f else None) for f in spec.flips)]
    rows, cols, depth = ids.shape

    background = np.array(BACKGROUND, dtype=np.float32) / 255
    total = np.zeros((rows, cols, 3), dtype=np.float32)
    # the light that gets through the blocks in front
    passed = np.ones((rows, cols), dtype=np.float32)
    # the depth of the first mostly opaque block in each pixel
    hit = np.full((rows, cols), depth, dtype=np.int32)

    # shade from the nearest to the furthest layer that has any blocks
    occupied = np.nonzero((colours[:, 3][ids] > 0).any(axis=(0, 1)))[0]
    near, far = (occupied[0], occupied[-1]) if occupied.size else (0, 0)

    for d in range(depth):
        rgba = colours[ids[:, :, d]]
        alpha = rgba[:, :, 3]
        # nearer blocks are lighter
        shade = 1.0 - DEPTH_SHADE * (d - near) / max(far - near, 1)
        total += (passed * alpha * shade)[:, :, np.newaxis] * rgba[:, :, :3]
        hit[(hit == depth) & (alpha >= 0.5)] = d
        passed *= 1 - alpha
        if passed.max() < 0.004:
            break
    total += passed[:, :, np.newaxis] * background

    if spec.hillshade:
        # compare each column with its northern neighbour: higher is lighter
        step = np.zeros((rows, cols), dtype=np.float32)
        step[1:] = np.clip(hit[:-1] - hit[1:], -1, 1)
        # no edge against empty columns
        step[hit == depth] = 0
        step[1:][hit[:-1] == depth] = 0
        total *= (1 + EDGE_SHADE * step)[:, :, np.newaxis]

    pixels = (np.clip(total, 0, 1) * 255).round().astype(np.uint8)
    pixels = pixels.repeat(scale, axis=0).repeat(scale, axis=1)
    image = Image.fromarray(pixels, "RGB")
    if not labels:
        return image

    def coords(axis: int) -> np.ndarray:
        world_axis = spec.axes[axis]
        values = np.arange(grid.size[world_axis]) + grid.origin[world_axis]
        return values[::-1] if spec.flips[axis] else values

    row_name, col_name = (_AXIS_NAMES[a] for a in spec.axes[:2])
    title = f"{spec.title} (rows {row_name}, columns {col_name})"
    return _frame(image, title, coords(0), coords(1), row_name, col_name, scale)


def _frame(
    image: Image.Image,
    title: str,
    row_coords: np.ndarray,
    col_coords: np.ndarray,
    row_name: str,
    col_name: str,
    scale: int,
) -> Image.Image:
    """
    Add a title, grid lines and coordinate labels to a view. Each label is
    centred on the row or column of blocks at that coordinate, with a grid
    line along its leading edge
    """
    font = _font()
    text_h = _text_height()
    widest = max(_text_width(str(c)) for c in (*row_coords, *col_coords))
    left = widest + _text_width(row_name) + 3 * PAD
    top = 2 * text_h + 3 * PAD
    width = max(left + image.width + PAD, _text_width(title) + 2 * PAD)
    framed = Image.new("RGB", (width, top + image.height + PAD), CANVAS)
    framed.paste(image, (left, top))
    draw = ImageDraw.Draw(framed, "RGBA")
    draw.text((PAD, PAD), title, fill=INK, font=font)
    draw.text((PAD, top - text_h - PAD), f"{row_name}\\{col_name}", fill=INK, font=font)

    if scale >= 8:
        # a faint line between every block
        for i in range(1, len(col_coords)):
            x = left + i * scale
            draw.line([(x, top), (x, top + image.height - 1)], fill=(*GRID, 30))
        for i in range(1, len(row_coords)):
            y = top + i * scale
            draw.line([(left, y), (left + image.width - 1, y)], fill=(*GRID, 30))

    label_y = top - text_h - PAD
    for i in _labelled(col_coords, scale, widest + PAD):
        x = left + i * scale
        text = str(col_coords[i])
        draw.line([(x, top - 3), (x, top + image.height - 1)], fill=(*GRID, 110))
        centre = x + scale / 2 - _text_width(text) / 2
        draw.text((centre, label_y), text, fill=INK, font=font)
    for i in _labelled(row_coords, scale, text_h + 2):
        y = top + i * scale
        text = str(row_coords[i])
        draw.line([(left - 3, y), (left + image.width - 1, y)], fill=(*GRID, 110))
        x = left - PAD - _text_width(text)
        draw.text((x, y + scale / 2 - text_h / 2), text, fill=INK, font=font)
    return framed


_STEPS = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)


def _labelled(coords: np.ndarray, scale: int, space: int) -> list[int]:
    """
    The indices of the coordinates to label: multiples of a round step,
    spaced far enough apart for labels *space* pixels long
    """
    step = next((s for s in _STEPS if s * scale >= space), _STEPS[-1])
    indices = [i for i, c in enumerate(coords) if c % step == 0]
    return indices or [0]


@cache
def _font() -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=FONT_SIZE)


def _text_width(text: str) -> int:
    return round(_font().getlength(text))


@cache
def _text_height() -> int:
    left, top, right, bottom = _font().getbbox("-0123456789xyz")
    return round(bottom)


# ----------------------------------------------------------------------------
# isometric views


def _iso(
    grid: BlockGrid,
    view: str,
    turns: int,
    colours: np.ndarray,
    scale: int,
    labels: bool,
) -> Image.Image:
    """
    Draw the region from above its south east corner with the painter's
    algorithm: the faces of nearer blocks are drawn over those behind
    """
    # the world x and z of each column, turned along with the blocks
    world_x, world_z = np.meshgrid(
        np.arange(grid.size.x) + grid.origin.x,
        np.arange(grid.size.z) + grid.origin.z,
        indexing="ij",
    )
    ids = _turn(grid.ids, turns)
    world_x = _turn(world_x[:, np.newaxis, :], turns)[:, 0, :]
    world_z = _turn(world_z[:, np.newaxis, :], turns)[:, 0, :]
    sx, sy, sz = ids.shape

    alpha = colours[:, 3][ids]
    # blocks that hide whatever is behind them
    solid = alpha >= 1.0

    def exposed(axis: int) -> np.ndarray:
        """blocks whose face on the + side of axis can be seen"""
        neighbour_solid = np.zeros_like(solid)
        same = np.zeros_like(solid)
        inner = [slice(None)] * 3
        outer = [slice(None)] * 3
        inner[axis] = slice(0, -1)
        outer[axis] = slice(1, None)
        neighbour_solid[tuple(inner)] = solid[tuple(outer)]
        # no faces between two blocks of the same glass, water ...
        same[tuple(inner)] = ids[tuple(inner)] == ids[tuple(outer)]
        return (alpha > 0) & ~neighbour_solid & ~same

    faces = {"top": exposed(1), "south": exposed(2), "east": exposed(0)}
    visible = faces["top"] | faces["south"] | faces["east"]
    xs, ys, zs = np.nonzero(visible)
    order = np.argsort(xs + ys + zs, kind="stable")

    half = scale / 2
    width = (sx + sz) * scale
    height = round((sx + sz) * half) + sy * scale

    def point(x: float, y: float, z: float) -> tuple[float, float]:
        return ((x - z + sz) * scale, (x + z) * half + (sy - y) * scale)

    # drawing RGBA on an RGB image blends translucent faces with those behind
    image = Image.new("RGB", (width + 1, height + 1), BACKGROUND)
    draw = ImageDraw.Draw(image, "RGBA")
    face_colours = _face_colours(colours)
    outline = scale >= 6
    for i in order:
        x, y, z = int(xs[i]), int(ys[i]), int(zs[i])
        block = ids[x, y, z]
        polygons = []
        if faces["top"][x, y, z]:
            corners = ((x, y + 1, z), (x + 1, y + 1, z), (x + 1, y + 1, z + 1))
            polygons.append((0, (*corners, (x, y + 1, z + 1))))
        if faces["south"][x, y, z]:
            corners = ((x, y, z + 1), (x + 1, y, z + 1), (x + 1, y + 1, z + 1))
            polygons.append((1, (*corners, (x, y + 1, z + 1))))
        if faces["east"][x, y, z]:
            corners = ((x + 1, y, z), (x + 1, y, z + 1), (x + 1, y + 1, z + 1))
            polygons.append((2, (*corners, (x + 1, y + 1, z))))
        for face, corners in polygons:
            fill, edge = face_colours[block][face]
            draw.polygon(
                [point(*c) for c in corners],
                fill=fill,
                outline=edge if outline else None,
            )
    if not labels:
        return image

    # label the three footprint corners that are in view with world x, z
    margin_w = max(
        _text_width(_xz(world_x[i, j], world_z[i, j])) for i in (0, -1) for j in (0, -1)
    )
    text_h = _text_height()
    top = text_h + 2 * PAD
    framed = Image.new(
        "RGB",
        (image.width + 2 * (margin_w + PAD), top + image.height + text_h + 2 * PAD),
        CANVAS,
    )
    left = margin_w + PAD
    framed.paste(image, (left, top))
    draw = ImageDraw.Draw(framed)
    font = _font()
    title = f"{view}: from the {_corner_name(turns)}, up is up"
    draw.text((PAD, PAD), title, fill=INK, font=font)

    for (i, j), anchor in (((0, -1), "rm"), ((-1, -1), "mt"), ((-1, 0), "lm")):
        corner_x = sx if i == -1 else 0
        corner_z = sz if j == -1 else 0
        px, py = point(corner_x, 0, corner_z)
        text = _xz(world_x[i, j], world_z[i, j])
        nudge = {"rm": (-3, 0), "mt": (0, 3), "lm": (3, 0)}[anchor]
        draw.text(
            (left + px + nudge[0], top + py + nudge[1]),
            text,
            fill=INK,
            font=font,
            anchor=anchor if isinstance(font, ImageFont.FreeTypeFont) else None,
        )
    return framed


def _turn(array: np.ndarray, turns: int) -> np.ndarray:
    """
    Turn an [x][y][z] array a quarter turn about y *turns* times, so that the
    north east, north west or south west corner becomes the south east one
    """
    for _ in range(turns):
        # x' = -z, z' = x takes the north east corner to the south east
        array = array.transpose(2, 1, 0)[::-1, :, :]
    return array


def _corner_name(turns: int) -> str:
    return ("south east", "north east", "north west", "south west")[turns]


def _xz(x: int, z: int) -> str:
    return f"x={x} z={z}"


def _face_colours(
    colours: np.ndarray,
) -> list[list[tuple[tuple[int, ...], tuple[int, ...]]]]:
    """the fill and outline colour of each face of each block"""
    result = []
    for rgba in colours:
        faces = []
        for light in (_TOP, _SOUTH, _EAST):
            rgb = rgba[:3] * light
            alpha = int(round(rgba[3] * 255))
            fill = (*(int(round(c * 255)) for c in rgb), alpha)
            edge = (*(int(round(c * 255 * 0.8)) for c in rgb), alpha)
            faces.append((fill, edge))
        result.append(faces)
    return result
