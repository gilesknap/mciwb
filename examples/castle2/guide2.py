"""
Print a visitor's guide to Castle 2, with world coordinates (no server
needed): castle's guide for castle2's layout, then the village, the
market, the pens and the people::

    python guide2.py > GUIDE.md
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle2_layout as C  # noqa: E402, I001  (first: it sets up castle's layout)
import guide  # noqa: E402  (castle's)
import people as P  # noqa: E402
from castle2_layout import BAILEY_DEPTH_NOTE, V  # noqa: E402


def xyz(x: int, y: int, z: int) -> str:
    p = V(x, y, z)
    return f"({p.x}, {p.y}, {p.z})"


def main() -> None:
    out = io.StringIO()
    with redirect_stdout(out):
        guide.main()
    text = out.getvalue()
    o, s = C.ORIGIN, C.SPAWN
    text = text.replace(
        "Built with mciwb from `examples/castle/` in the mciwb repo; rebuildable with\n"
        f"`ORIGIN={o.x},{o.y},{o.z} SPAWN={s.x},{s.y},{s.z} NAME={C.NAME} BANNER={C.BANNER} mciwb run build_castle.py`.",
        "Built with mciwb from `examples/castle2/` (on `examples/castle/`) in the mciwb\n"
        "repo; rebuildable with `mciwb run build_castle2.py`. " + BAILEY_DEPTH_NOTE,
    )
    print(text.rstrip())
    houses = C.village_houses()
    shops = []
    homes = 0
    for name, h in houses.items():
        if h.contents == "home":
            homes += 1
            continue
        keeper = P.KEEPER.get(h.contents, ("", ""))[1]
        door = h.door
        shops.append(
            f"| {name.capitalize()} | ({door.x}, {door.y}, {door.z}) | {keeper} |"
        )
    sx1, sz1, sx2, sz2 = C.SQUARE
    cx, cz = C.MARKET_CROSS
    pens = "\n".join(
        f"| {name.capitalize()} | {xyz(x1, 0, z1)} to {xyz(x2, 0, z2)} | "
        + ", ".join(f"{n} {what}" for what, n in animals.items())
        + " |"
        for name, ((x1, z1, x2, z2), animals) in C.PENS.items()
    )
    gx1, gz1, gx2, gz2 = C.GARDEN
    print(f"""

## The village

The lower bailey of Castle {C.NAME} is twice as deep as Castle Fable's.
Its middle is a village of {len(houses)} timber-framed houses round a
market square: from {xyz(sx1, 0, sz1)} to {xyz(sx2, 0, sz2)}, with a
stone market cross at {xyz(cx, 0, cz)} and a bell, where the villagers
gather. A ring of lanes runs round the square. {homes} of the houses are
homes; the rest are shops, each with a counter window, shelves of goods
and a sign hanging over the door, and a shopkeeper who trades:

| Shop | Door | Keeper |
| --- | --- | --- |
{chr(10).join(shops)}

The tavern has tables with drinkers at them. The houses' upper storeys
overhang the street on carved joists; climb the stairs (a ladder in the
narrow ones) to the bedrooms.

## The pens and the allotments

South of the village, between it and the gate, the animals are penned
along the walls (they are not fed, so they stay as they are):

| Pen | Where | Animals |
| --- | --- | --- |
{pens}

The allotments, {xyz(gx1, 0, gz1)} to {xyz(gx2, 0, gz2)}, grow wheat,
carrots, beetroot and potatoes round a scarecrow. Bee hives stand by the
upper ward's garden.

## The people

The king and queen sit on their thrones in the great hall, with musicians
in the gallery and hounds by the fire; the cook works in the kitchen, the
librarian at his lectern, the monk at the altar, the alchemist among his
brewing stands, the smith at his anvil and the jailer in the guard room,
with two prisoners in the cells. Guards with spears watch from the walls;
the captain is on the keep's roof and the gate sergeant on the gatehouse.
""")


if __name__ == "__main__":
    main()
