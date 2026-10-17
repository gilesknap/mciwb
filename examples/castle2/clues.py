"""
Castle 2's clue trail (phase 6): the written books, notes and plaques that
lead a visitor from one secret to the next, from the village down to the
inner vault::

    the tavern     a drunk's book: the miller goes down, not out
      -> the miller's way (the mill's Sluice lever; its tunnel comes out
         in the dungeon's guard room)
    the cells      a prisoner's diary: the jailer's lever in the west cell,
                   and the oubliette's dead who hear only a bell
      -> the ossuary (the listening door)
    its reliquary  the founder's testament: the thirteenth hour of his
                   Book of Hours
      -> the hidden study (the lectern lock)
    its chest      the alchemist's notebook: as above, so below; a star
                   for a shard of amethyst
      -> the alchemist's cellar (the astrolabe), the engine's bell, the
         transmuter
    the cellar     Brother Cantor's letter: play me home, the tune is on
                   my tomb
      -> the crypt's second chamber (the organ)
    its chest      the steward's reckoning: which copper lights to press
      -> the inner vault (the copper puzzle)

and, off the trail, the fletcher's rules of the range (the archery cache),
a plaque in the smithy (its trapdoor) and Mercator's chart of the castle,
sold by the cartographer, with a hint for every secret.

``clues()`` is the build stage (after ``people``: the notes go into the
chests the machine stages fill, so rebuild it after them); ``check()`` reads
every book back. The signs among the clues are read back by verify's signs
check, as every other sign.
"""

from __future__ import annotations

import re

import castle2_layout as C  # noqa: I001  (first: it sets up castle's layout)
import castle_lib as L
from castle2_layout import CELL_ROWS, DUNGEON_Y, V
from castle_layout import SMITHY_HATCH

from mciwb.imports import Vec3

STEP = {
    "north": Vec3(0, 0, -1),
    "south": Vec3(0, 0, 1),
    "east": Vec3(1, 0, 0),
    "west": Vec3(-1, 0, 0),
}
NOTE_SLOT = 13  # the middle of a chest: the reward chests fill from slot 0


def _ordinal(k: int) -> str:
    return ("first", "second", "third", "fourth", "fifth", "sixth")[k]


def _copper_hint() -> list[str]:
    rows: dict[int, list[int]] = {}
    for b, h in C.COPPER_SOLUTION:
        rows.setdefault(h, []).append(b)
    said = []
    for h, word in ((0, "In the lower row"), (1, "in the upper row")):
        if h in rows:
            cols = sorted(rows[h])
            names = ["the last" if b == 5 else "the " + _ordinal(b) for b in cols]
            said.append(f"{word} press {' and '.join(names)}")
    return [
        "The inner vault answers to the copper lights "
        "in the west wall of the treasure vault below the keep: it opens when "
        "every one of them is lit.",
        "Count the lights from the north. " + "; ".join(said) + ". Press no "
        "other, or you must put them back as they were.",
    ]


# every book of the trail: (key, title, author, pages)
BOOKS: dict[str, tuple[str, str, list[str]]] = {
    "tavern": (
        "Wat's Ramblings",
        "Wat the Sot",
        [
            "Another ale, Ned. I saw the miller again last night. He pulled "
            "his Sluice lever, and the wheel never stopped turning. Then he "
            "went down. Not out, Ned. Down.",
            "Down by his hearth, under the stone with the mason's mark. And "
            "where does a miller go under the ground? To the dungeon, I say, "
            "to see his brother in the cells.",
        ],
    ),
    "prisoner": (
        "Scratched in the Dark",
        "a prisoner",
        [
            "Day 40. The jailer goes into the west cell on our side and pulls "
            "something on its wall. Then the end of the corridor stands open "
            "and he goes off to the well.",
            "Day 52. The old guard talks of the oubliette under the pit: the "
            "dead there are deaf to all but a bell. Ring it before the carved "
            "face, he says, and the bones let you in.",
        ],
    ),
    "founder": (
        "The Founder's Testament",
        "the Founder",
        [
            "I raised this castle and hid its heart. My Book of Hours stands "
            "on a lectern in the library, by the east bookcases.",
            "Twelve hours keep my doors shut. Turn to the thirteenth and the "
            "shelves will let you into my study.",
        ],
    ),
    "alchemist": (
        "Notebook",
        "the Alchemist",
        [
            "My cellar is under my laboratory, at the top of the alchemist's "
            "tower. As above, so below: set the levers of my floor as the "
            "star chart on the west wall shows them.",
            "A lit star for a lever that is on, a dark one for a lever that "
            "is off. The near row of stars is the row of levers by the wall.",
            "Feed my transmuter a shard of amethyst and it pays you back a "
            "star. The engine on my roof rings its bell only while the "
            "heavens are set.",
        ],
    ),
    "cantor": (
        "A Letter",
        "Brother Cantor",
        [
            "Old friend, when I am gone, play me home. My tune is carved on "
            "my tomb in the crypt, under the chapel's altar.",
            "Play it on my organ, from the west: C D E F G A. Strike a wrong "
            "key and you must begin again. Then my chamber will open to you.",
        ],
    ),
    "steward": ("The Steward's Reckoning", "the Steward", _copper_hint()),
    "fletcher": (
        "Rules of the Range",
        "Robin the Fletcher",
        [
            "Shoot only from the line in the barracks yard. Bows and arrows "
            "are there for all.",
            "A true eye opens the stores: the stores open for a bullseye, and "
            "for nothing less. Another bullseye shuts them.",
        ],
    ),
    "chart": (
        "A Chart of Fable II",
        "Mercator",
        [
            "The mill: the miller keeps a lever he calls the Sluice. "
            "The tavern: ask the drunk.",
            "The dungeon: the cells remember. The oubliette: the dead hear "
            "only the bell.",
            "The library: the History tells of the last book; the Book of "
            "Hours of the thirteenth hour.",
            "The alchemist's tower: as above, so below.",
            "The chapel: the dead monk's tune. The vault: let every lamp be lit.",
            "The barracks: a true eye. The smithy: mind the rug.",
        ],
    ),
}

# the trail, in order: (book, where it is found, the secrets it points to);
# the last two are off the trail (the chart hints at most of the secrets)
TRAIL: list[tuple[str, str, list[str]]] = [
    ("tavern", "on a lectern by the drunk's table in the tavern", ["the miller's way"]),
    (
        "prisoner",
        "on a lectern in the prisoner's cell (the dungeon's north row)",
        ["the ossuary"],
    ),
    ("founder", "in the ossuary's reliquary", ["the hidden study"]),
    (
        "alchemist",
        "in the hidden study's chest",
        ["the alchemist's cellar", "the transmuter", "the engine's bell"],
    ),
    ("cantor", "in the alchemist's cellar's chest", ["the crypt's second chamber"]),
    ("steward", "in the crypt's second chamber's chest", ["the inner vault"]),
    ("fletcher", "on a lectern in the fletcher's shop", ["the archery cache"]),
    (
        "chart",
        "sold by Mercator the cartographer, for 2 emeralds",
        [
            "the miller's way",
            "the ossuary",
            "the hidden study",
            "the alchemist's cellar",
            "the crypt's second chamber",
            "the inner vault",
            "the archery cache",
        ],
    ),
]

# the guide's rumours: vague, one for each step of the trail
RUMOURS = [
    "The tavern's regulars say old Wat knows more than he lets on, and writes "
    "it all down.",
    "The prisoners keep a diary. They have time enough.",
    "Some say the castle's founder lies with the bones under the dungeon, and "
    "left word for whoever finds him.",
    "The alchemist trusted nobody, but he wrote everything in his notebook.",
    "Brother Cantor, the organist, wrote a last letter before he died.",
    "The steward counted the treasure, and how to reach the rest of it.",
    "The fletcher has rules for his range, and a reason for them.",
    "Mercator the cartographer sells a chart with more on it than the roads.",
]


def book_snbt(key: str) -> str:
    """a written book item, as SNBT (without a slot)"""
    title, author, pages = BOOKS[key]
    text = ",".join(L.snbt_string(p) for p in pages)
    return (
        f'{{id:"minecraft:written_book",count:1,components:'
        f'{{"minecraft:written_book_content":{{title:{L.snbt_string(title)},'
        f"author:{L.snbt_string(author)},pages:[{text}]}}}}}}"
    )


def chests() -> dict[str, Vec3]:
    """the reward chests that hold a note: world positions"""
    import machines_bailey
    import machines_upper
    import organ

    return {
        "founder": machines_bailey.listening_door_cells()["reliquary"],
        "alchemist": machines_upper.lectern_cells()["chest"],
        "cantor": V(20, 11, 21),  # the alchemist's cellar (machines_upper.astrolabe)
        "steward": organ.organ_cells()["chest"],
    }


# the diary's lectern in the prisoners' cell (rooms.dungeon: the second
# north cell from the west but one; the prisoner stands in its middle, the
# hay in its north-west corner): its north-east corner, against the east wall
PRISONER_LECTERN = (CELL_ROWS[0][3][2] + 2, DUNGEON_Y, CELL_ROWS[0][0])
# the smithy's plaque: on its east wall, at head height beside the trapdoor
SMITHY_PLAQUE = (SMITHY_HATCH[0] + 1, 1, SMITHY_HATCH[1])


def house_spot(name: str) -> tuple[Vec3, str]:
    """a house's clue spot (world) and the way a lectern on it faces: away
    from the wall it stands against, read from the house's own blocks"""
    from house import _cell, passable

    h = C.village_houses()[name]
    assert h.clue_spot is not None, name
    p = h.clue_spot
    for side, d in STEP.items():
        behind = h.blocks.get(_cell(p - d), L.AIR)
        ahead = h.blocks.get(_cell(p + d), L.AIR)
        if not passable(behind) and passable(ahead):
            return p, side
    raise RuntimeError(f"the {name}'s clue spot {p} is against no wall")


def lecterns() -> dict[str, tuple[Vec3, str]]:
    """where each lectern of the trail stands (world), and its facing"""
    return {
        "tavern": house_spot("tavern"),
        "fletcher": house_spot("fletcher"),
        "prisoner": (V(*PRISONER_LECTERN), "west"),
    }


def found_at(key: str) -> Vec3 | None:
    """where a book of the trail is (world), or None for Mercator's chart"""
    spots = {k: p for k, (p, _facing) in lecterns().items()} | chests()
    return spots.get(key)


def place_lectern(p: Vec3, facing: str, key: str) -> None:
    L.set_block(
        p, f"minecraft:lectern[facing={facing},has_book=true]{{Book:{book_snbt(key)}}}"
    )


def note(chest: Vec3, key: str) -> None:
    """put a book in a chest's middle slot, replacing what was there"""
    x, y, z = int(chest.x), int(chest.y), int(chest.z)
    L.cmd(f"data remove block {x} {y} {z} Items[{{Slot:{NOTE_SLOT}b}}]")
    item = book_snbt(key)[1:]  # the item's fields, to go after its slot
    L.cmd(
        f"data modify block {x} {y} {z} Items append value {{Slot:{NOTE_SLOT}b,{item}"
    )


def clues() -> str:
    """the trail's books, notes and the smithy's plaque (Mercator's chart is
    one of his trades: people.TRADES)"""
    for key, (p, facing) in lecterns().items():
        place_lectern(p, facing, key)
    for key, chest in chests().items():
        note(chest, key)
    L.sign(
        V(*SMITHY_PLAQUE),
        "spruce_wall_sign[facing=west]",
        "Mind the rug:",
        "it goes",
        "a long way",
        "down",
    )
    return f"{len(BOOKS)} books, a plaque"


def _title_at(where: str) -> str:
    """the title of the book a ``data get`` path points at, or ''"""
    r = L.cmd(f'data get {where}.components."minecraft:written_book_content".title')
    # a text component: {raw: "..."} (a plain string reads back that way)
    m = re.search(r'data: (?:\{raw: )?"((?:[^"\\]|\\.)*)"', r)
    return re.sub(r"\\(.)", r"\1", m.group(1)) if m else ""


def check(check_fn) -> None:
    """every book of the trail is in place: on its lectern, in its chest,
    in Mercator's trades"""
    bad = []
    for key, (p, _facing) in lecterns().items():
        found = _title_at(f"block {p.x} {p.y} {p.z} Book")
        if found != BOOKS[key][0]:
            bad.append(f"{key} lectern {tuple(p)}: {found!r}")
    for key, chest in chests().items():
        found = _title_at(
            f"block {chest.x} {chest.y} {chest.z} Items[{{Slot:{NOTE_SLOT}b}}]"
        )
        if found != BOOKS[key][0]:
            bad.append(f"{key} note in {tuple(chest)}: {found!r}")
    sel = f"@e[type=minecraft:villager,tag={C.TAG},name=Mercator,limit=1]"
    found = _title_at(f"entity {sel} Offers.Recipes[-1].sell")
    if found != BOOKS["chart"][0]:
        bad.append(f"Mercator's last trade: {found!r}")
    check_fn(
        f"clues: the trail's {len(BOOKS)} books on their lecterns, in their "
        "chests and in Mercator's trades" + (f" (not {bad[:4]})" if bad else ""),
        not bad,
    )


def _record() -> None:
    """add the trail's books to the secrets they point to (castle2_layout.SECRETS),
    in local coordinates"""
    o = C.ORIGIN
    for key, where, secrets in TRAIL:
        p = found_at(key)
        local = None if p is None else (int(p.x - o.x), int(p.y - o.y), int(p.z - o.z))
        for name in secrets:
            C.SECRETS[name]["clues"].append(
                ("book", local, f"{BOOKS[key][0]}, {where}")
            )


_record()
