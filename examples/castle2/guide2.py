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
    text = text.replace(*forceloaded_chunks())
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
    print(playing())
    print(rumours_and_spoilers())
    print(more_play())


def forceloaded_chunks() -> tuple[str, str]:
    """castle's "Forceloaded chunks" paragraph, and castle2's in its place"""
    import cmdblocks

    cx, cz = cmdblocks.bank_chunk()
    a, b = cmdblocks.bank_box()
    return (
        "None are left forceloaded: the build and the checks forceload the site\n"
        "while they run and unload it when they finish.",
        f"One chunk is left forceloaded: chunk ({cx}, {cz}) (x {cx * 16}..{cx * 16 + 15},"
        f" z {cz * 16}..{cz * 16 + 15}), which holds the\n"
        f"command bank ({a.x}, {a.y}, {a.z}) to ({b.x}, {b.y}, {b.z}), buried under the"
        " upper ward: the command\nblocks that keep visitors in adventure mode and put"
        " the lecterns' books back\nmust run wherever the players are. The build and the"
        " checks forceload the\nrest of the site while they run and unload it when they"
        " finish (`forceload\nquery` should list that one chunk).",
    )


def playing() -> str:
    """what the protect stage does for (and to) visitors"""
    import main_gate

    x1, z1, x2, z2 = C.zone_box()
    c = main_gate.postern_cells()
    door = c["door"][0]
    return f"""
## Playing in the castle

This is how the castle is set up for visitors. The checks work all of it
over RCON except what only a player can do: the change of game mode,
what adventure mode lets a visitor do, the purse's gift and the pick's
use have not yet been tried by a player (PROGRESS.md lists what to try).

- **Adventure mode.** A visitor in survival mode is put in adventure mode
  on coming within x {x1}..{x2}, z {z1}..{z2} (at any height), where
  nothing can be broken or placed; the machines are built to be worked
  with levers, buttons, lecterns, bells and hoppers. On leaving (on foot,
  by dying and coming back at the world's spawn, or to another dimension)
  they are in survival again. Players in creative or spectator mode are
  left alone. The players the zone holds carry the tag `{C.ZONE_TAG}`.
- **The fittings.** The armour stands, the item frames, the paintings,
  the people, the cats, the horses, the hounds and the golems are
  invulnerable; the stands' slots are disabled and the frames fixed, to
  keep the armour on its stands and the items in their frames. The farm
  animals in the pens are ordinary animals.
- **The books come back.** When the book is gone from the library's Book
  of Hours lectern, or from the lecterns in the tavern, the fletcher's and
  the prisoners' cell, a new copy is put on it at once; and so is a book
  of the trail taken from its chest.
- **No way to be shut in.** The hidden study, the alchemist's cellar, the
  crypt's second chamber and the inner vault have a wooden button inside,
  by the door (the cellar's: in a niche at the top of its ladder), that
  opens it for a moment. The ossuary is left by its inner bell, the
  miller's way by its inner lever, the fight chamber by a stone button,
  and the main vault by the iron door to the well tunnel (a button each
  side). The main gate has a postern: an
  iron door at ({door.x}, {door.y}, {door.z}) in the west wall of the
  gate passage, between the fence gates and the portcullis, with a stone
  button on each side (on the ceiling in the passage), through the guard
  room to the bailey. Whoever shuts the portcullis shuts nobody out.
- **The machines keep their stock.** The Engine's hoppers and the
  transmuter's store of stars are locked: they work, but do not open.
- **A purse at the gate.** Hal the Crier stands just inside the gate at
  {xyz(*C.CRIER)}, his notice board across the street. The first time you
  come through the gate he gives you {C.PURSE} emeralds (once for each
  player: the tag `{C.PURSE_TAG}`).
- **Earning emeralds.** Nothing can be harvested or mined here, but the
  keepers buy what you can come by:

{buying()}

  Shears are 1 emerald at the tailor's, a bucket 1 at the smithy, a
  fishing rod 1 at the fletcher's. Fish in the moat; the dead under the
  dungeon drop the flesh and the bones.
- **The Steward's bell.** A button on the north wall of the gatehouse's
  winch room at {xyz(*C.STEWARD_BELL)} (up the stair from the guard room
  west of the gate passage). Ring it when you leave: six seconds later
  every secret door is shut, every machine as it was built, every chest
  and cache full again and walled up, for the next visitor. Nobody is
  shut in by it: every secret room has its way out from inside.
"""


def buying() -> str:
    """the keepers' buying trades (people.BUYS), as a table"""
    rows = [
        f"  | {P.KEEPER[shop][1]} | {n} {item.replace('_', ' ')} | {paid} |"
        for shop, buys in P.BUYS.items()
        for item, n, paid in buys
    ]
    head = "  | Keeper | Buys | Emeralds |\n  | --- | --- | --- |\n"
    return head + "\n".join(rows)


def more_play() -> str:
    """play.py's spoilers: the fight, the pick and its caches"""
    import loot
    import play

    c = play.charnel_cells()
    door = c["door"][0]
    waves = ", then ".join(
        f"{z} zombies and {s} skeleton{'s' if s > 1 else ''}" for z, s in play.WAVES
    )
    pay = "; ".join(
        " and ".join(
            (
                "Gravebane (a diamond sword, Smite III)"
                if i == "diamond_sword"
                else f"{n} {i}s"
            )
            for i, n, *_ in rewards
        )
        for rewards in loot.WAVE_REWARDS
    )
    caches = "\n".join(
        f"- {name.capitalize()}: the wall at {xyz(*wall)}, with "
        + ", ".join(f"{n} {i.replace('_', ' ')}" for i, n, *_ in loot.CACHES[name])
        + "."
        for name, (wall, _barrel, _facing) in C.CACHES.items()
    )
    return f"""
## Spoilers: the restless dead

South of the ossuary (the listening door's secret), behind an iron door
at ({door.x}, {door.y}, {door.z}) with a stone button on each side (on
the ossuary's side it is on the ceiling of the way through). The sexton's
chest beside the door has stone swords, shields and bread. In the
chamber, the button on the pillar wakes the dead: three waves ({waves}),
the next as soon as the last of a wave is dead. Each wave pays on the
altar beside the pillar: {pay}. They cannot follow you out, and if
everyone leaves the chamber the fight is over and they are gone: go back
in and start again. The Steward's bell ends it too.

## Spoilers: the prospector's pick

The pick in the ossuary's reliquary is made to break one block only,
in adventure mode too (its `can_break`; not yet tried by a player):
cracked deepslate bricks. Four walls in the castle are one such block,
each with a barrel behind it:

{caches}

Ringing the Steward's bell walls them up and fills them again.
"""


def rumours_and_spoilers() -> str:
    """the clue trail (clues.py): vague rumours, then every step in full"""
    import clues

    rumours = "\n".join(f"- {r}" for r in clues.RUMOURS)
    steps = []
    for k, (key, where, secrets) in enumerate(clues.TRAIL, start=1):
        title, author, pages = clues.BOOKS[key]
        p = clues.found_at(key)
        at = "" if p is None else f" at ({p.x}, {p.y}, {p.z})"
        lines = [f"{k}. **{title}** by {author}, {where}{at}: “{' '.join(pages)}”"]
        for name in secrets if key != "chart" else []:
            s = C.SECRETS[name]
            lines.append(
                f"   - **{name.capitalize()}** ({s['machine']}, worked at "
                f"{xyz(*s['where'])}): {s['solution'].rstrip('.')}. Then: {s['opens']}."
            )
        steps.append("\n".join(lines))
    return f"""
## Rumours

Castle {C.NAME} keeps more secrets than Castle Fable. Its people talk:

{rumours}

## Spoilers: the clue trail

Each clue leads to a secret, and each secret holds the clue to the next,
from the village down to the inner vault, where the Founder's chest and
his last word end it. The books are on lecterns or in the secrets' chests
(in the middle slot); one taken from its chest comes back.

{chr(10).join(steps)}
"""


if __name__ == "__main__":
    main()
