"""
The play stage: what makes Castle 2 a game for more than one visitor. It
comes after ``clues`` and before ``protect``, which places its command
blocks. Rebuild it after ``vault``, ``gatehouse``, ``dungeons`` or
``bailey_machines``, which build over what it places.

What it builds:

- **The main vault's lesser hoard.** The clue trail ends in the inner
  vault, and the best of castle's treasure now lies there (the Founder's
  chest, machines_upper.hoard, with his last word: clues.py). The main
  vault, which three easy ways lead into, keeps a respectable rest
  (loot.MAIN_VAULT).
- **The Steward's bell**: a button in the gatehouse's winch room. Pressed,
  it sets the whole castle to rights for the next visitor (`reset_commands`).
- **A notice board** inside the gate, across the street from Hal the Crier
  (people.py), that sends a newcomer to the tavern and to Mercator.
- **The restless dead**: a closed chamber south of the ossuary, behind an
  iron door with a button each side. A button on its pillar wakes three
  rising waves of zombies and skeletons; each wave, once dead, pays
  emeralds on the altar, and the last a sword.
- **Four caches** behind walls of cracked deepslate bricks (loot.WEAK_WALL,
  used nowhere else), the one block the prospector's pick breaks (the
  pick lies in the ossuary's reliquary: loot.RELIQUARY).

And its rows of the command bank (cmdblocks.py; `plan_rows`), all of which
fail, and so stay silent, while there is nothing to do:

- ``notes``: a trail's book missing from its chest's middle slot is copied
  back from the chest's master copy in the bank;
- ``purse``: a player who comes in at the gate for the first time is given
  `PURSE` emeralds, a word from the crier and the tag `PURSE_TAG`;
- ``organ``: a key that does not move the tune on gives a sour low note
  and smoke, a key in its turn a chime and green sparks;
- ``archery``: three lamps on the butt for a hit, a hit in the inner half
  and a near miss; they go out after `LAMP_TICKS`;
- ``lectern``: the bookcase does not move while the Book of Hours is being
  turned, nor for `LECTERN_PATIENCE` ticks after: someone leafing through
  it for the page that works turns past it (the Founder's Testament says
  to wait);
- ``fight``: the waves of the restless dead;
- ``reset``: the Steward's bell.

Timers are area effect clouds in the bank's chunk (cmdblocks.timer): the
game ages them, so no command has to count. The one number kept is the
fight's wave (`cmdblocks.Bank.score`).
"""

from __future__ import annotations

import time

import castle2_layout as C
import castle_lib as L
import clues
import cmdblocks
import loot
import machines_bailey as B
import machines_upper as M
import organ
import people as P
from castle2_layout import VAULT_Y, V
from castle_layout import (
    ARROW_TRAP,
    CELL_DOOR,
    CELL_LEVER,
    CRYPT_DOOR,
    LIBRARY_DOOR,
)

from mciwb.imports import Vec3

UP = Vec3(0, 1, 0)
E, S, Wd = Vec3(1, 0, 0), Vec3(0, 0, 1), Vec3(-1, 0, 0)
BELL_BUTTON = "minecraft:stone_button"
WAKE_BUTTON = "minecraft:polished_blackstone_button"
BARREL = "minecraft:barrel"
# the reset, in ticks after the bell: the site is loaded, then everything is
# put back, then what needs a second step (a dust placed again, the organ's
# reset let go), then the site is let go again
RESET_LOAD, RESET_SET, RESET_BACK, RESET_LET_GO, RESET_END = 2, 100, 104, 116, 120
RESET_TICKS = RESET_END + 10
ORGAN_TICKS = 50  # no second sign of the same kind for this long after one
LAMP_TICKS = 100  # how long the range's lamps show a shot
# what stands in the lectern lock's dust line while the book is turned
PATIENCE_CUT = L.BRICK
# a stand-in for a player in the chamber of the restless dead (verify
# summons an armour stand with it: RCON cannot be a player)
WITNESS_TAG = f"{L.TAG}.witness"
# the waves: how many zombies and skeletons each brings
WAVES = [(2, 1), (3, 2), (4, 3)]


def xyz(p: Vec3) -> str:
    return f"{p.x} {p.y} {p.z}"


def box(a: Vec3, b: Vec3) -> str:
    return L.box_selector(a, b)


# ---------------------------------------------------------------- the cells


def bell_cells(pos=V) -> dict:
    x, y, z = C.STEWARD_BELL
    return {
        "button": pos(x, y, z),
        "button_state": "face=wall,facing=south",
        "wall": pos(x, y, z - 1),
        "signs": [pos(x, y + 1, z), pos(x + 1, y + 1, z)],
    }


def notice_cells(pos=V) -> dict:
    x, y, z = C.NOTICE_BOARD
    return {
        "board": (pos(x, y, z), pos(x + 1, y + 1, z)),
        # top left, top right, bottom left, bottom right, seen from the gate
        "signs": [
            pos(x, y + 1, z + 1),
            pos(x + 1, y + 1, z + 1),
            pos(x, y, z + 1),
            pos(x + 1, y, z + 1),
        ],
        "lantern": pos(x, y + 2, z),
    }


def purse_box(pos=V) -> tuple[Vec3, Vec3]:
    x1, y1, z1, x2, y2, z2 = C.PURSE_BOX
    return pos(x1, y1, z1), pos(x2, y2, z2)


def vault_cells(pos=V) -> dict:
    return {
        "chests": {x: pos(x, VAULT_Y, 17) for x in loot.MAIN_VAULT},
        "chest_block": "minecraft:chest[facing=south]",
        # castle's netherite stands here: it is the inner vault's now
        "ingots": (pos(63, VAULT_Y, 29), pos(65, VAULT_Y, 29)),
        "ingot_block": "minecraft:raw_iron_block",
    }


def charnel_cells(pos=V) -> dict:
    """the chamber of the restless dead, south of the ossuary"""
    x1, y1, z1, x2, y2, z2 = C.CHARNEL
    dx, dy, dz = C.CHARNEL_DOOR
    px, pz = (x1 + x2) // 2, (z1 + z2) // 2  # the pillar
    zombies = [(x1 + 1, z2 - 1), (x2 - 1, z2 - 1), (x1 + 1, z1 + 1), (px + 1, z2 - 1)]
    skeletons = [(x1, pz), (x2, pz + 2), (px + 3, z2 - 1)]
    return {
        "inside": (pos(x1, y1, z1), pos(x2, y2, z2)),
        # the walls, floor and ceiling (and room for a cache in the west wall)
        "shell": (pos(x1 - 3, y1 - 1, z1 - 1), pos(x2 + 1, y2 + 1, z2 + 1)),
        "floor": (pos(x1, y1 - 1, z1), pos(x2, y1 - 1, z2)),
        # where a player counts as in the chamber, and where its dead must
        # stay: the inside, its walls and the way through the ossuary's wall
        "zone": (pos(x1 - 1, y1 - 1, dz - 1), pos(x2 + 1, y2 + 1, z2 + 1)),
        "door": [pos(dx, dy, dz), pos(dx, dy + 1, dz)],
        "door_facing": "south",
        "passage": [pos(dx, dy, dz - 1), pos(dx, dy + 1, dz - 1)],
        # (cell, state, the block it is fixed to): in the way through, on its
        # ceiling beside the door's top half; inside, on the wall beside it
        "buttons": {
            "ossuary": (
                pos(dx, dy + 1, dz - 1),
                "face=ceiling,facing=north",
                pos(dx, dy + 2, dz - 1),
            ),
            "chamber": (
                pos(dx - 1, dy + 1, dz + 1),
                "face=wall,facing=south",
                pos(dx - 1, dy + 1, dz),
            ),
        },
        "pillar": [pos(px, y1 + h, pz) for h in range(3)],
        "wake": pos(px, y1 + 1, pz - 1),
        "wake_state": "face=wall,facing=north",
        "wake_sign": pos(px, y1 + 2, pz - 1),
        "altar": pos(px + 1, y1, pz),
        "reward": pos(px + 1, y1, pz) + Vec3(0.5, 0.8, 0.5),
        "centre": pos(px + 1, y1, pz - 2) + Vec3(0.5, 0, 0.5),
        "zombies": [pos(x, y1, z) + Vec3(0.5, 0, 0.5) for x, z in zombies],
        "skeletons": [pos(x, y1, z) + Vec3(0.5, 0, 0.5) for x, z in skeletons],
        "lanterns": [pos(x, y2, z) for x in (x1 + 2, x2 - 2) for z in (z1 + 2, z2 - 2)],
        "door_sign": pos(dx, dy + 2, dz - 2),
        "sexton": pos(dx + 1, dy, dz - 2),
        "sexton_block": "minecraft:chest[facing=north]",
        "sexton_sign": pos(dx + 1, dy + 1, dz - 2),
    }


def cache_cells(pos=V) -> dict[str, dict]:
    return {
        name: {
            "wall": pos(*wall),
            "barrel": pos(*barrel),
            "barrel_block": f"{BARREL}[facing={facing}]",
        }
        for name, (wall, barrel, facing) in C.CACHES.items()
    }


def lever_doors(pos=V) -> dict[str, dict]:
    """castle's and the mill's doors worked by a lever (castle_lib.hidden_door):
    the lever, its facing, its first dust, the door and what it is made of"""
    mill = B.mill_cells(pos)
    out = {
        "the mill": {
            "lever": mill["lever"],
            "facing": mill["lever_facing"],
            "dust": mill["first_dust"],
            "door": mill["door"],
            "material": B.MILL_STONE,
        }
    }
    for name, base, lever_b, material in (
        ("the cell block", CELL_DOOR, CELL_LEVER, L.BRICK),
        ("the crypt", CRYPT_DOOR, -1, L.DARK_BRICK),
    ):
        d = L.hidden_door_cells(pos(*base), Wd, S, trigger="lever", lever_b=lever_b)
        out[name] = {
            "lever": d["trigger"],
            "facing": d["trigger_facing"],
            "dust": d["first_dust"],
            "door": d["door"],
            "material": material,
        }
    return out


def mill_inside(pos=V) -> dict:
    """the mill's lever in its passage: on the door's input block, which
    must be placed again for a lever set by command to show"""
    x, y, z = C.MILL_DOOR
    base = pos(x, y, z)
    return {
        "lever": B.mill_cells(pos)["inner_lever"],
        "input": base + S * 2 + E * 2 + UP,
        "input_block": L.BRICK,
    }


def library_cells(pos=V) -> dict:
    """castle's library door: its chiseled bookshelf as built (six books,
    none touched yet) and its door"""
    d = L.hidden_door_cells(pos(*LIBRARY_DOOR), E, S)
    slots = ",".join(f"slot_{k}_occupied=true" for k in range(6))
    books = ",".join(f'{{Slot:{k}b,id:"minecraft:book",count:1}}' for k in range(6))
    return {
        "shelf": d["trigger"],
        "shelf_block": f"minecraft:chiseled_bookshelf[facing={d['trigger_facing']},{slots}]"
        f"{{Items:[{books}],last_interacted_slot:-1}}",
        "door": d["door"],
        "material": "minecraft:bookshelf",
    }


def trap_dispensers(pos=V) -> list[Vec3]:
    x1, x2, y, zw, zd = ARROW_TRAP
    o = pos(0, 0, 0)
    return L.arrow_trap_cells(o.x + x1, o.x + x2, o.y + y, o.z + zw, o.z + zd)[
        "dispensers"
    ]


def single(block: str) -> str:
    """a chest that does not join the chest beside it (in the bank's store)"""
    return block.replace("chest[", "chest[type=single,", 1)


def note_chests(pos=V) -> dict[str, tuple[Vec3, str]]:
    """the chests that hold a book of the trail in their middle slot:
    (where, the chest as it is when full, book and all), by the book's key,
    which is also its master's name in the bank's store"""
    reliquary = B.listening_door_cells(pos)
    study = M.lectern_cells(pos)
    cellar = M.astrolabe_cells(pos)
    chamber = organ.organ_cells(pos)
    inner = M.copper_cells(pos)
    full = {
        "founder": (
            reliquary["reliquary"],
            reliquary["reliquary_block"],
            loot.RELIQUARY,
        ),
        "alchemist": (study["chest"], study["chest_block"], loot.STUDY),
        "cantor": (cellar["chest"], cellar["chest_block"], loot.CELLAR),
        "steward": (chamber["chest"], chamber["chest_block"], loot.CHAMBER),
        "last": (inner["hoard"], inner["hoard_block"], loot.INNER_VAULT),
    }
    return {
        key: (p, loot.container(single(block), stacks, clues.book_snbt(key)))
        for key, (p, block, stacks) in full.items()
    }


def stores(pos=V) -> dict[str, tuple[Vec3, str, str]]:
    """every other container the reset fills: (where, its ``Items`` as
    SNBT, an item it must hold when full)"""
    out: dict[str, tuple[Vec3, str, str]] = {}

    def add(name: str, p: Vec3, stacks: list) -> None:
        out[name] = (p, loot.items(stacks), stacks[0][0])

    vault = vault_cells(pos)
    for x, p in vault["chests"].items():
        add(f"the vault's chest at x {x}", p, loot.MAIN_VAULT[x])
    for x, stacks in loot.LOWER_TREASURY.items():
        add(f"the lower treasury's chest at x {x}", pos(x, -15, 106), stacks)
    a = B.archery_cells(pos)
    add("the archery cache", a["cache"], loot.ARCHERY_CACHE)
    add("the range's bows", a["kit"], loot.ARCHERY_KIT)
    add("the range's arrows", a["dropper"], loot.ARCHERY_ARROWS)
    t = M.transmuter_cells(pos)
    add("the transmuter's stars", t["reward_dropper"], t["rewards"])
    add("the sexton's chest", charnel_cells(pos)["sexton"], loot.SEXTON)
    for name, c in cache_cells(pos).items():
        add(f"the cache of {name}", c["barrel"], loot.CACHES[name])
    for k, p in enumerate(trap_dispensers(pos)):
        # (castle loads a dispenser's middle slot)
        out[f"the arrow trap's dispenser {k + 1}"] = (
            p,
            "[" + loot.stack(4, "arrow", 64) + "]",
            "arrow",
        )
    return out


# ---------------------------------------------------------------- the build


def put(p: Vec3, block: str) -> None:
    """a block with data, in place of whatever is there (a container set
    over itself would keep its old stacks)"""
    L.set_block(p, L.AIR)
    L.set_block(p, block)


def main_vault(pos=V) -> None:
    c = vault_cells(pos)
    for x, p in c["chests"].items():
        put(p, loot.container(c["chest_block"], loot.MAIN_VAULT[x]))
    L.fill(c["ingots"][0], c["ingots"][1], c["ingot_block"])


def steward_bell(pos=V) -> None:
    c = bell_cells(pos)
    L.set_block(c["button"], f"{BELL_BUTTON}[{c['button_state']}]")
    a, b = c["signs"]
    L.sign(
        a,
        "dark_oak_wall_sign[facing=south]",
        "The Steward's",
        "bell. Ring it",
        "to set the castle",
        "to rights:",
    )
    L.sign(
        b,
        "dark_oak_wall_sign[facing=south]",
        "every door shut,",
        "every chest",
        "filled, for the",
        "next guest.",
    )


NOTICES = [
    ("Castle " + C.NAME, "Welcome, guest.", "Hal the Crier", "has your purse."),
    ("Nothing here", "can be broken.", "Pull, press,", "ring and read."),
    ("For secrets,", "begin at the", "tavern, west of", "the square."),
    ("Mercator sells", "a chart. The", "shops buy wool,", "eggs, milk, fish."),
]


def notice_board(pos=V) -> None:
    c = notice_cells(pos)
    L.fill(c["board"][0], c["board"][1], L.SPRUCE)
    L.set_block(c["lantern"], L.LANTERN)
    for p, lines in zip(c["signs"], NOTICES, strict=True):
        L.set_block(p, L.AIR)  # (fallen snow)
        L.sign(p, "spruce_wall_sign[facing=south]", *lines)


def charnel(pos=V) -> dict:
    """the chamber, its door through the ossuary's south wall, the sexton's
    chest by it. The ossuary (machines_bailey) must be there"""
    c = charnel_cells(pos)
    L.fill(c["shell"][0], c["shell"][1], L.DARK_BRICK)
    L.fill(c["inside"][0], c["inside"][1], L.AIR)
    L.fill(c["floor"][0], c["floor"][1], "minecraft:soul_soil")
    for p in c["passage"]:
        L.set_block(p, L.AIR)
    lower, upper = c["door"]
    f = c["door_facing"]
    L.set_block(lower, f"minecraft:iron_door[facing={f},half=lower,hinge=left]")
    L.set_block(upper, f"minecraft:iron_door[facing={f},half=upper,hinge=left]")
    for p, state, _on in c["buttons"].values():
        L.set_block(p, f"minecraft:stone_button[{state}]")
    for p in c["pillar"]:
        L.set_block(p, "minecraft:polished_blackstone_bricks")
    L.set_block(c["pillar"][-1] + UP, "minecraft:skeleton_skull[rotation=8]")
    L.set_block(c["wake"], f"{WAKE_BUTTON}[{c['wake_state']}]")
    L.sign(
        c["wake_sign"],
        "dark_oak_wall_sign[facing=north]",
        "Strike here",
        "to wake",
        "the restless",
        "dead.",
    )
    L.set_block(c["altar"], "minecraft:polished_blackstone_brick_slab[type=bottom]")
    for p in c["lanterns"]:
        L.set_block(p, f"{L.SOUL_LANTERN}[hanging=true]")
    a, b = c["inside"]
    for x, z in ((a.x, b.z), (b.x, b.z), (a.x, a.z)):
        L.set_block(Vec3(x, a.y, z), "minecraft:bone_block")
    L.sign(
        c["door_sign"],
        "dark_oak_wall_sign[facing=north]",
        "The restless",
        "dead lie beyond.",
        "Three waves.",
        "Come armed.",
    )
    put(c["sexton"], loot.container(c["sexton_block"], loot.SEXTON))
    L.sign(
        c["sexton_sign"],
        "dark_oak_wall_sign[facing=north]",
        "The sexton's",
        "chest: take",
        "a blade, and",
        "leave it after.",
    )
    return c


def caches(pos=V) -> None:
    for name, c in cache_cells(pos).items():
        put(c["barrel"], loot.container(c["barrel_block"], loot.CACHES[name]))
        L.set_block(c["wall"], loot.WEAK_WALL)


def play() -> str:
    """castle2's play stage"""
    main_vault()
    steward_bell()
    notice_board()
    charnel()
    caches()
    return (
        "the main vault's hoard, the Steward's bell, the notice board, the"
        f" restless dead, {len(C.CACHES)} caches"
    )


# ---------------------------------------------------------------- the commands


def note_commands(b: cmdblocks.Bank, pos=V) -> list[str]:
    """a book gone from its chest's middle slot comes back from the master"""
    out = []
    for key, (p, block) in note_chests(pos).items():
        m = b.store(key, block)
        slot = f"Items[{{Slot:{loot.NOTE_SLOT}b}}]"
        out.append(
            f"execute unless data block {xyz(p)} {slot} run data modify block"
            f" {xyz(p)} Items append from block {xyz(m)} {slot}"
        )
    return out


def purse_selector(pos=V) -> str:
    """the players due a purse: in the gate's box, without the tag"""
    return f"{box(*purse_box(pos))},tag=!{C.PURSE_TAG}"


CRIER_SAYS = (
    f"Welcome to Castle {C.NAME}! Here is a purse of {C.PURSE} emeralds. "
    "Nothing here can be broken: pull, press, ring and read. For secrets, "
    "begin at the tavern west of the market square, and buy Mercator's chart."
)


def purse_commands(pos=V) -> list[str]:
    sel = f"@a[{purse_selector(pos)}]"
    said = (
        f'[{{text:"Hal the Crier: ",color:"gold"}},'
        f'{{text:{L.snbt_string(CRIER_SAYS)},color:"white"}}]'
    )
    return [
        f"tellraw {sel} {said}",
        f"give {sel} minecraft:emerald {C.PURSE}",
        f"tag {sel} add {C.PURSE_TAG}",  # last: it ends what the others match
    ]


def organ_commands(pos=V) -> list[str]:
    """a sour note and smoke for a key that starts the tune again, a chime
    and sparks for one in its turn. The organ's own dusts say which: the
    reset's and the advance's, each 15 while its pulse lasts (which is as
    long after the key as the organ's works take: two or three seconds). A
    timer for each sign keeps the pulse's other ticks, and the key's
    release, from giving it again"""
    c = organ.organ_cells(pos)
    k = c["above_keys"] + Vec3(0.5, 0, 0.5)
    out = []
    for dust, kind, sound, pitch, particle in (
        (c["reset_dust"], "sour", "block.note_block.didgeridoo", 0.5, "large_smoke"),
        (c["advance_dust"], "sweet", "block.note_block.bell", 1.6, "happy_villager"),
    ):
        when = (
            f"execute unless entity {cmdblocks.timer(kind)} if block"
            f" {xyz(dust)} {L.DUST}[power=15] run"
        )
        out += [
            f"{when} playsound minecraft:{sound} record @a {xyz(k)} 3 {pitch}",
            f"{when} particle minecraft:{particle} {xyz(k)} 1.5 0.4 0.2 0.01 30",
            # last: the timer ends what the others match
            f"{when} {cmdblocks.start_timer(kind, ORGAN_TICKS, pos)}",
        ]
    return out


# the lamps' thresholds: the target's power for a hit, the inner half, a near miss
LAMP_POWER = (1, 8, 12)


def archery_commands(pos=V) -> list[str]:
    c = B.archery_cells(pos)
    t = xyz(c["target"])
    hit = f"execute if block {t} minecraft:target"
    out = []
    for lamp, least in zip(c["lamps"], LAMP_POWER, strict=True):
        less = "".join(
            f" unless block {t} minecraft:target[power={p}]" for p in range(least)
        )
        out.append(f"{hit}{less} run setblock {xyz(lamp)} {B.BULB}[lit=true]")
    a, z = c["lamps"][0], c["lamps"][-1]
    out += [
        f"{hit} unless block {t} minecraft:target[power=0] unless entity"
        f" {cmdblocks.timer('shot')} run {cmdblocks.start_timer('shot', LAMP_TICKS, pos)}",
        f"execute if entity {cmdblocks.timer('shot', LAMP_TICKS - 1)} run"
        f" fill {xyz(a)} {xyz(z)} {B.BULB}[lit=false]",
    ]
    return out


def lectern_commands(pos=V) -> list[str]:
    """the lectern is powered for two ticks when its page is turned: a timer
    starts again each time, and the lock's dust is out while it runs"""
    c = M.lectern_cells(pos)
    turned = f"execute if block {xyz(c['trigger'])} minecraft:lectern[powered=true] run"
    cut = xyz(c["patience"])
    restless = cmdblocks.timer("restless")
    return [
        f"{turned} kill {restless}",
        f"{turned} {cmdblocks.start_timer('restless', C.LECTERN_PATIENCE, pos)}",
        f"execute if entity {restless} if block {cut} {L.DUST} run"
        f" setblock {cut} {PATIENCE_CUT}",
        f"execute unless entity {restless} if block {cut} {PATIENCE_CUT} run"
        f" setblock {cut} {L.DUST}",
    ]


def mob(kind: str, p: Vec3, equipment: str = "") -> str:
    """the command that raises one of the dead (not persistent: left alone,
    far from every player, it is gone)"""
    worn = f",equipment:{{{equipment}}}" if equipment else ""
    return f'summon minecraft:{kind} {xyz(p)} {{Tags:["{C.FIGHT_TAG}"]{worn}}}'


BOW = 'mainhand:{id:"minecraft:bow",count:1}'
CAPTAIN = (
    'head:{id:"minecraft:iron_helmet",count:1},'
    'mainhand:{id:"minecraft:stone_sword",count:1}'
)
WAVE_SAYS = [
    "The first of the dead lie still. More are stirring.",
    "The second wave is down. The last and worst is coming.",
    "The dead rest. Gravebane is yours: take it from the altar.",
]


def wave_mobs(k: int, pos=V) -> list[str]:
    """the summons of wave k (from 0)"""
    c = charnel_cells(pos)
    zombies, skeletons = WAVES[k]
    out = [
        mob("zombie", p, CAPTAIN if n == 3 else "")
        for n, p in enumerate(c["zombies"][:zombies])
    ]
    return out + [mob("skeleton", p, BOW) for p in c["skeletons"][:skeletons]]


def fight_commands(b: cmdblocks.Bank, pos=V) -> list[list[str]]:
    """the fight's four rows. The wave's number: 0 idle; 1, 3, 5 a wave to
    raise (for one tick); 2, 4, 6 a wave fighting; 7 won. A row raises a
    wave and moves the number on in the same tick, so no other row sees a
    wave half raised."""
    c = charnel_cells(pos)
    wave = b.score("#wave")
    dead = f"@e[tag={C.FIGHT_TAG}]"
    zone = box(*c["zone"])

    def when(n: int, more: str = "") -> str:
        return f"execute if score {wave} matches {n}{more} run"

    def raise_wave(k: int) -> list[str]:
        n = 2 * k + 1
        return [f"{when(n)} {m}" for m in wave_mobs(k, pos)] + [
            f"{when(n)} scoreboard players set {wave} {n + 1}"
        ]

    start = [
        f"execute if score {wave} matches 0 if block {xyz(c['wake'])}"
        f" {WAKE_BUTTON}[powered=true] run scoreboard players set {wave} 1",
        f"{when(1)} playsound minecraft:block.bell.use block @a {xyz(c['wake'])} 2 0.6",
    ]
    pay = []
    for k, rewards in enumerate(loot.WAVE_REWARDS):
        over = when(2 * k + 2, f" unless entity {dead}")
        for item, count, *components in rewards:
            extra = f",components:{components[0]}" if components else ""
            pay.append(
                f"{over} summon minecraft:item {xyz(c['reward'])} "
                f'{{Item:{{id:"minecraft:{item}",count:{count}{extra}}}}}'
            )
        pay += [
            f'{over} tellraw @a[{zone}] {{text:{L.snbt_string(WAVE_SAYS[k])},color:"gray"}}',
            f"{over} scoreboard players set {wave} {2 * k + 3}",
        ]
    keep = [
        # the dead stay in: one that is out of the chamber is put back
        f"execute as {dead} unless entity @s[{zone}] run tp @s {xyz(c['centre'])}",
        # nobody in the chamber: the fight is over, and its dead go
        f"execute unless score {wave} matches 0 unless entity @a[{zone}]"
        f" unless entity @e[tag={WITNESS_TAG},{zone}] run scoreboard players set {wave} 0",
        f"execute if score {wave} matches 0 run kill {dead}",
    ]
    return [start + raise_wave(0) + raise_wave(1), raise_wave(2), pay, keep]


def bulb(lit: bool) -> str:
    return f"{B.BULB}[lit={str(lit).lower()},powered=false]"


def lever_off(facing: str, face: str = "wall") -> str:
    return f"minecraft:lever[face={face},facing={facing},powered=false]"


def reset_commands(b: cmdblocks.Bank, pos=V) -> list[str]:
    """
    The Steward's bell. Its button starts a timer of RESET_TICKS, and each
    command runs in one tick of it: the site is forceloaded (the bell is
    further from the keep than a player's chunks reach), and at RESET_SET
    every secret door is shut and every machine put back as built, every
    reward restocked (the chests with a book cloned from their masters) and
    the caches walled up; a lever set by command shows only when its dust
    is placed again, at RESET_BACK. At RESET_END the site is let go, and
    the bank's chunk forceloaded again. Nobody is shut in: every secret
    room has a way out from inside (a button, a bell, a lever or an iron
    door: guide2's "No way to be shut in").
    """
    bell = bell_cells(pos)
    running = cmdblocks.timer("reset")

    def at(tick: int, command: str) -> str:
        return f"execute if entity {cmdblocks.timer('reset', tick)} run {command}"

    a, z = C.site_box()
    site = f"{a.x} {a.z} {z.x} {z.z}"
    zone = C.zone_selector()
    out = [
        f"execute if block {xyz(bell['button'])} {BELL_BUTTON}[powered=true]"
        f" unless entity {running} run"
        f" {cmdblocks.start_timer('reset', RESET_TICKS, pos)}",
        at(
            1,
            f"playsound minecraft:block.bell.use block @a {xyz(bell['button'])} 3 0.7",
        ),
        at(
            1,
            f"tellraw @a[{zone}] {{text:\"The Steward's bell rings. In a moment"
            ' the castle will be as it was.",color:"gold"}',
        ),
        at(RESET_LOAD, f"forceload add {site}"),
    ]
    now, back = [], []
    # the copper puzzle, to the pattern the Steward's Reckoning starts from
    for key, p in M.copper_cells(pos)["bulbs"].items():
        now.append(f"setblock {xyz(p)} {bulb(key in C.COPPER_START)}")
    # the astrolabe: its levers off, the dust under each placed again
    astro = M.astrolabe_cells(pos)
    levers = list(astro["levers"].values())
    d1, d2 = astro["dusts"]
    now += [
        f"fill {xyz(levers[0])} {xyz(levers[-1])} {lever_off('north', 'floor')}"
        " replace minecraft:lever",
        f"fill {xyz(d1)} {xyz(d2)} minecraft:tuff replace {L.DUST}",
    ]
    back.append(f"fill {xyz(d1)} {xyz(d2)} {L.DUST} replace minecraft:tuff")
    # the organ: a redstone block beside its reset row, for a moment
    o = organ.organ_cells(pos)
    now.append(f"setblock {xyz(o['reset_block'])} minecraft:redstone_block")
    # the archery lock and its lamps, the listening door, the lectern
    arch = B.archery_cells(pos)
    now += [
        f"setblock {xyz(arch['bulb'])} {bulb(False)}",
        f"fill {xyz(arch['lamps'][0])} {xyz(arch['lamps'][-1])} {B.BULB}[lit=false]",
        f"setblock {xyz(B.listening_door_cells(pos)['bulb'])} {bulb(False)}",
        f"data modify block {xyz(M.lectern_cells(pos)['trigger'])} Page set value 0",
    ]
    # the library's bookshelf, from its master
    lib = library_cells(pos)
    m = xyz(b.store("library shelf", lib["shelf_block"]))
    now.append(f"clone {m} {m} {xyz(lib['shelf'])}")
    # the levers of the mill, the cell block and the crypt
    for d in lever_doors(pos).values():
        now += [
            f"setblock {xyz(d['lever'])} {lever_off(d['facing'])}",
            f"setblock {xyz(d['dust'])} {L.AIR}",
        ]
        back.append(f"setblock {xyz(d['dust'])} {L.DUST}")
    inner = mill_inside(pos)
    now += [
        f"setblock {xyz(inner['lever'])} {lever_off('north', 'floor')}",
        f"setblock {xyz(inner['input'])} minecraft:smooth_stone",
    ]
    back.append(f"setblock {xyz(inner['input'])} {inner['input_block']}")
    # the rewards: the chests with a book from their masters, the rest filled
    for key, (p, block) in note_chests(pos).items():
        m = xyz(b.store(key, block))
        now.append(f"clone {m} {m} {xyz(p)}")
    for p, stacks, _item in stores(pos).values():
        now.append(f"data modify block {xyz(p)} Items set value {stacks}")
    for c in cache_cells(pos).values():
        now.append(f"setblock {xyz(c['wall'])} {loot.WEAK_WALL}")
    # the restless dead: the fight over (its row then removes them)
    now.append(f"scoreboard players set {b.score('#wave')} 0")
    now.append(
        f'tellraw @a[{zone}] {{text:"The castle is set to rights.",color:"gold"}}'
    )
    out += [at(RESET_SET, command) for command in now]
    out += [at(RESET_BACK, command) for command in back]
    bank = cmdblocks.bank_box(pos)[0]
    out += [
        at(RESET_LET_GO, f"setblock {xyz(o['reset_block'])} {M.STONE}"),
        at(RESET_END, f"forceload remove {site}"),
        at(RESET_END, f"forceload add {bank.x} {bank.z}"),
    ]
    return out


def plan_rows(b: cmdblocks.Bank) -> None:
    """play's part of the command bank"""
    b.row("notes", note_commands(b))
    b.row("purse", purse_commands())
    b.row("organ", organ_commands())
    b.row("archery", archery_commands())
    b.row("lectern", lectern_commands())
    for k, commands in enumerate(fight_commands(b), start=1):
        b.row(f"fight {k}", commands)
    b.rows("reset", reset_commands(b))


cmdblocks.PLANNERS.append(plan_rows)


# ---------------------------------------------------------------- the checks


def count(selector: str) -> int:
    return L.count_entities(selector)


def running(name: str) -> bool:
    return count(cmdblocks.timer(name)[3:-1]) > 0


def held(p: Vec3, item: str, n: int | None = None) -> bool:
    """does the container at p hold the item (a stack of n of it)?"""
    stack = f'id:"minecraft:{item}"' + ("" if n is None else f",count:{n}")
    r = L.cmd(f"execute if data block {xyz(p)} Items[{{{stack}}}]")
    return "Test passed" in r


def is_shut(door: list[Vec3], material: str) -> bool:
    return all(L.is_block(p, material) or L.is_block(p, material) for p in door)


def is_open(door: list[Vec3]) -> bool:
    return all(L.is_block(p, L.AIR) for p in door)


def check_built(check, weak_walls: int | None = None) -> None:
    """what the stage builds is in place"""
    bell = bell_cells()
    check(
        "play: the Steward's bell is a button on the winch room's wall",
        L.is_block(
            bell["button"], f"{BELL_BUTTON}[{bell['button_state']},powered=false]"
        )
        and not L.is_block(bell["wall"], L.AIR),
    )
    n = notice_cells()
    missing = [
        tuple(p) for p in n["signs"] if not L.is_block(p, "#minecraft:wall_signs")
    ]
    check(
        f"play: the notice board's {len(n['signs'])} notices face the gate"
        f" (missing {missing})",
        not missing,
    )
    hoard = M.copper_cells()["hoard"]
    best = ("nether_star", "elytra", "trident", "netherite_ingot", "totem_of_undying")
    lacking = [i for i in best if not held(hoard, i)]
    kept = [
        f"{i} at x {x}"
        for x, p in vault_cells()["chests"].items()
        for i in best
        if held(p, i)
    ]
    poor = [
        x
        for x, p in vault_cells()["chests"].items()
        if not held(p, loot.MAIN_VAULT[x][0][0])
    ]
    check(
        "play: the best treasure is in the inner vault's chest (lacking"
        f" {lacking}) and not in the main vault's (still there: {kept}), which"
        f" keeps a lesser hoard (empty: {poor})",
        not lacking and not kept and not poor,
    )
    reliquary = B.listening_door_cells()["reliquary"]
    r = L.cmd(
        f"data get block {xyz(reliquary)} "
        f'Items[{{id:"minecraft:{loot.PICK}"}}].components."minecraft:can_break"'
    )
    check(
        "play: the prospector's pick is in the reliquary, and breaks"
        f" {loot.WEAK_WALL} only (can_break: {r.split('data:')[-1].strip()[:80]})",
        r.count("minecraft:") == 1 and f'blocks: "{loot.WEAK_WALL}"' in r,
    )
    bad = []
    for name, c in cache_cells().items():
        if not L.is_block(c["wall"], loot.WEAK_WALL):
            bad.append(f"{name}: no weak wall at {tuple(c['wall'])}")
        if not L.is_block(c["barrel"], c["barrel_block"]) or not held(
            c["barrel"], loot.CACHES[name][0][0]
        ):
            bad.append(f"{name}: no full barrel at {tuple(c['barrel'])}")
    only = "" if weak_walls is None else f", {weak_walls} such blocks in the build"
    check(
        f"play: {len(C.CACHES)} caches, each a full barrel behind a weak wall"
        f"{only} (not: {bad})",
        not bad and weak_walls in (None, len(C.CACHES)),
    )


def check_charnel(check) -> None:
    """the chamber is closed, lit, and its door opens to a button on each side"""
    c = charnel_cells()
    a, b = c["inside"]
    lower, upper = c["door"]
    opening = {tuple(lower), tuple(upper)}
    walls = (L.DARK_BRICK, loot.WEAK_WALL, "minecraft:soul_soil")
    holes = []
    for x in range(a.x - 1, b.x + 2):
        for y in range(a.y - 1, b.y + 2):
            for z in range(a.z - 1, b.z + 2):
                edge = (
                    x in (a.x - 1, b.x + 1)
                    or y in (a.y - 1, b.y + 1)
                    or z in (a.z - 1, b.z + 1)
                )
                p = Vec3(x, y, z)
                if edge and tuple(p) not in opening:
                    if not any(L.is_block(p, w) for w in walls):
                        holes.append((x, y, z))
    f = c["door_facing"]

    def door(open_: bool) -> bool:
        state = f"facing={f},open={str(open_).lower()}"
        return L.is_block(lower, f"minecraft:iron_door[half=lower,{state}]") and (
            L.is_block(upper, f"minecraft:iron_door[half=upper,{state}]")
        )

    check(
        "restless dead: the chamber is closed all round (holes at"
        f" {holes[:4]}), its iron door shut",
        not holes and door(False),
    )
    for side, (p, state, on) in c["buttons"].items():
        there = L.is_block(p, f"minecraft:stone_button[{state}]") and not L.is_block(
            on, L.AIR
        )

        def nudge(on: Vec3 = on) -> None:
            # a pressed button updates the neighbours of the block it is on
            # (the door, for the chamber's); one set by command only its
            # own: placing its block again does what the press would
            L.set_block(on, "minecraft:smooth_stone")
            L.set_block(on, L.DARK_BRICK)

        try:
            L.set_block(p, f"minecraft:stone_button[{state},powered=true]")
            nudge()
            opened = L.wait_until(lambda: door(True), 10)
        finally:
            L.set_block(p, f"minecraft:stone_button[{state},powered=false]")
            nudge()
        shut = L.wait_until(lambda: door(False), 10)
        check(
            f"restless dead: the button on the {side} side opens the door (button"
            f" {there}, opened {opened}) and it shuts again ({shut})",
            there and opened and shut,
        )


def check_trades(check) -> None:
    """every keeper buys what `people.BUYS` says, for emeralds, and the
    tools a newcomer needs are for sale"""

    def trades(name: str, buy: str, n: int, sell: str) -> int:
        return count(
            f"type=minecraft:villager,tag={L.TAG},name={L.snbt_string(name)},"
            f'nbt={{Offers:{{Recipes:[{{buy:{{id:"minecraft:{buy}",count:{n}}},'
            f'sell:{{id:"minecraft:{sell}"}}}}]}}}}'
        )

    missing = []
    for shop, buys in P.BUYS.items():
        for item, n, _paid in buys:
            if trades(P.KEEPER[shop][1], item, n, "emerald") != 1:
                missing.append(f"{P.KEEPER[shop][1]} buying {n} {item}")
    tools = (
        ("Agnes the Tailor", "shears"),
        ("Godric the Smith", "bucket"),
        ("Robin the Fletcher", "fishing_rod"),
    )
    for name, tool in tools:
        if trades(name, "emerald", 1, tool) != 1:
            missing.append(f"{name} selling a {tool}")
    n = sum(len(b) for b in P.BUYS.values())
    check(
        f"trades: {n} trades pay emeralds (wool, eggs, milk, fish, rotten"
        " flesh, bones, spectral arrows), and shears, a bucket and a fishing"
        f" rod are sold for 1 emerald (missing: {missing})",
        not missing,
    )


def check_purse(check) -> None:
    """the purse's selector, tried on an armour stand (the commands take
    players only): in the gate's box and untagged it matches, tagged it
    does not, and outside the box it does not"""
    a, b = purse_box()
    x, y, z = C.CRIER
    inside = V(x + 2, y, z) + Vec3(0.5, 0, 0.5)
    outside = Vec3(inside.x, inside.y, a.z - 6)
    stand = "type=minecraft:armor_stand,tag=castle_verify_purse"
    sel = f"{stand},{purse_selector()}"
    try:
        L.cmd(
            f"summon minecraft:armor_stand {xyz(inside)} "
            '{Tags:["castle_verify","castle_verify_purse"],Marker:1b,Invisible:1b}'
        )
        first = count(sel)
        L.cmd(f"tag @e[{sel}] add {C.PURSE_TAG}")
        again = count(sel)
        L.cmd(f"tag @e[{stand}] remove {C.PURSE_TAG}")
        L.cmd(f"tp @e[{stand}] {xyz(outside)}")
        away = count(sel)
    finally:
        L.cmd(f"kill @e[{stand}]")
    check(
        f"purse: the selector takes a newcomer at the gate once (untagged in"
        f" the box {first}, tagged {again}, untagged outside it {away}); the"
        f" tag is {C.PURSE_TAG}",
        (first, again, away) == (1, 0, 0),
    )
    print("INFO purse: the gift itself needs a player: not tested")


def check_organ(check) -> None:
    """a wrong key starts the sour timer, a key in its turn the sweet one"""
    c = organ.organ_cells()
    tune = list(C.ORGAN_TUNE)

    def quiet() -> bool:
        return not running("sour") and not running("sweet")

    def strike(note: str) -> tuple[bool, bool]:
        """press a key, as long as a wooden button stays in or until the
        organ answers (its works take a second or three), and say which
        sign it gave; then wait until the key's release has passed too"""
        k = c["keys"][note]
        L.wait_until(quiet, 2 * ORGAN_TICKS)
        L.set_block(k, "minecraft:redstone_block")
        try:
            L.wait_until(lambda: not quiet(), 150)
            L.tick(4)
            signs = running("sour"), running("sweet")
        finally:
            L.set_block(k, "minecraft:quartz_block")
        L.tick(120)
        L.wait_until(quiet, 2 * ORGAN_TICKS)
        return signs

    dusts = all(L.is_block(c[d], L.DUST) for d in ("reset_dust", "advance_dust"))
    try:
        wrong = strike(organ.wrong_key())
        right = strike(tune[0])
        late = strike(tune[2])  # out of turn: the tune starts again
    finally:
        organ.play(c, [organ.wrong_key()])
        L.wait_until(quiet, 3 * ORGAN_TICKS)
    check(
        "organ: a key not in the tune gives the sour sign (sour, sweet:"
        f" {wrong}), the tune's first key the sweet one ({right}), a key out"
        f" of turn the sour one ({late}); the dusts read are there ({dusts})",
        wrong == (True, False)
        and right == (False, True)
        and late == (True, False)
        and dusts,
    )
    print("INFO organ: the note and the smoke need a player to hear and see them")


def check_archery(check) -> None:
    """the lamps on the butt: one for an outer ring, two for the inner
    half, three for a bullseye, and out again after LAMP_TICKS"""
    c = B.archery_cells()

    def lamps() -> list[bool]:
        return [L.is_block(p, f"{B.BULB}[lit=true]") for p in c["lamps"]]

    def arrows_away() -> None:
        t = c["target"]
        L.cmd(
            f"kill @e[type=minecraft:arrow,{box(t - Vec3(4, 2, 3), t + Vec3(2, 2, 3))}]"
        )

    def shoot(dy: float, dz: float) -> list[bool]:
        B.shoot(c, dy, dz)
        L.tick(12)
        seen = lamps()
        arrows_away()
        L.tick(LAMP_TICKS + 30)
        return seen

    was_open = L.is_block(c["bulb"], f"{B.BULB}[lit=true]")
    try:
        start = lamps()
        outer = shoot(0.92, 0.92)
        inner = shoot(0.7, 0.5)
        bull = shoot(0.5, 0.5)
        after = lamps()
    finally:
        if was_open != L.is_block(c["bulb"], f"{B.BULB}[lit=true]"):
            B.shoot(c)  # the bullseye opened the hatch: another shuts it
            L.tick(30)
            arrows_away()
            L.tick(LAMP_TICKS + 30)
    check(
        f"archery: the lamps show how near a shot came: dark at rest ({start}),"
        f" an outer ring {outer}, the inner half {inner}, a bullseye {bull},"
        f" and dark again after {LAMP_TICKS} ticks ({after})",
        not any(start)
        and outer == [True, False, False]
        and inner == [True, True, False]
        and all(bull)
        and not any(after),
    )


def check_lectern(check) -> None:
    """a page turned (the lectern's two powered ticks, set here by command)
    to the right page: the bookcase waits LECTERN_PATIENCE, then opens"""
    c = M.lectern_cells()
    shelf = c["material"]
    here = c["lectern"].replace("Page:0", f"Page:{C.LECTERN_PAGE - 1}")
    turning = here.replace("has_book=true]", "has_book=true,powered=true]")
    cut = c["patience"]
    assert here != c["lectern"] and turning != here
    try:
        L.set_block(c["trigger"], turning)
        L.tick(2)
        L.set_block(c["trigger"], here)
        waiting = running("restless") and L.is_block(cut, PATIENCE_CUT)
        L.tick(C.LECTERN_PATIENCE // 2)
        still_shut = M.door_shut(c, shelf) and running("restless")
        opened = M.wait_for(lambda: M.door_open(c), C.LECTERN_PATIENCE)
        joined = L.is_block(cut, L.DUST) and not running("restless")
    finally:
        put(c["trigger"], c["lectern"])
    shut = M.wait_for(lambda: M.door_shut(c, shelf), 30)
    check(
        "lectern lock: turned to the page, the lock's dust is cut and a timer"
        f" runs ({waiting}); half way through it the bookcase is still shut"
        f" ({still_shut}); then it opens ({opened}, the dust back {joined});"
        f" turned back, it shuts ({shut})",
        waiting and still_shut and opened and joined and shut,
    )
    print(
        "INFO lectern lock: that a page turned by hand powers the lectern"
        " (as the game's code says) needs a player"
    )


def check_fight(check) -> None:
    """the waves, with an armour stand for the player: woken by the button,
    each wave counted, killed, paid for and followed by the next; one of
    the dead taken out of the chamber is put back; with nobody there the
    fight is over and the dead gone"""
    c = charnel_cells()
    zone = box(*c["zone"])
    dead = f"tag={C.FIGHT_TAG}"
    wake, state = c["wake"], c["wake_state"]

    def wave() -> int | None:
        return cmdblocks.score("#wave")

    def strike() -> None:
        L.set_block(wake, f"{WAKE_BUTTON}[{state},powered=true]")
        L.tick(3)
        L.set_block(wake, f"{WAKE_BUTTON}[{state},powered=false]")

    def items(item: str) -> int:
        return count(
            f'type=minecraft:item,{zone},nbt={{Item:{{id:"minecraft:{item}"}}}}'
        )

    def sweep() -> None:
        for kind in ("item", "experience_orb", "arrow"):
            L.cmd(f"kill @e[type=minecraft:{kind},{zone}]")

    there = L.is_block(wake, f"{WAKE_BUTTON}[{state},powered=false]")
    idle = wave() == 0 and count(dead) == 0
    seen, paid, kinds_ok, kept_in = [], [], True, False
    try:
        sweep()
        L.cmd(
            f"summon minecraft:armor_stand {xyz(c['centre'])} "
            f'{{Tags:["castle_verify","{WITNESS_TAG}"],Marker:1b,Invisible:1b}}'
        )
        strike()
        for k, (zombies, skeletons) in enumerate(WAVES):
            L.wait_until(lambda k=k: wave() == 2 * k + 2, 20)
            z = count(f"type=minecraft:zombie,{dead},{zone}")
            s = count(f"type=minecraft:skeleton,{dead},{zone}")
            seen.append((z, s))
            kinds_ok = kinds_ok and count(dead) == z + s == zombies + skeletons
            if k == 0:
                # one of them out in the ossuary: the next tick has it back
                L.cmd(f"tp @e[{dead},limit=1] {xyz(c['door_sign'] - Vec3(0, 2, 3))}")
                L.tick(2)
                kept_in = count(f"{dead},{zone}") == count(dead) == z + s
            L.cmd(f"kill @e[{dead}]")
            L.wait_until(lambda k=k: (wave() or 0) > 2 * k + 2, 30)
            item, n, *_ = loot.WAVE_REWARDS[k][0]
            paid.append(items(item) >= 1)
            sweep()
        won = wave() == 7
        L.cmd(f"kill @e[tag={WITNESS_TAG}]")
        L.tick(3)
        over = wave() == 0
        strike()  # nobody there: the dead rise and are gone at once
        L.tick(5)
        alone = wave() == 0 and count(dead) == 0
    finally:
        L.cmd(f"kill @e[tag={WITNESS_TAG}]")
        L.tick(3)
        L.cmd(f"kill @e[{dead}]")
        sweep()
    check(
        f"restless dead: the button ({there}) wakes them from rest ({idle});"
        f" waves of zombies and skeletons {seen} of {WAVES}, nothing else"
        f" ({kinds_ok}); one taken out is put back ({kept_in}); each wave dead"
        f" pays on the altar {paid}; won ({won}); the chamber left, the fight"
        f" is over ({over}); woken with nobody there, they are gone ({alone})",
        there
        and idle
        and seen == WAVES
        and kinds_ok
        and kept_in
        and all(paid)
        and len(paid) == len(WAVES)
        and won
        and over
        and alone,
    )


def book_in(p: Vec3) -> str:
    return clues.title_at(f"block {xyz(p)} Items[{{Slot:{loot.NOTE_SLOT}b}}]")


def check_notes(check) -> None:
    """a book taken from its chest comes back by itself"""
    bad = []
    for key, (p, _block) in note_chests().items():
        title = clues.BOOKS[key][0]
        there = book_in(p) == title
        L.cmd(f"data remove block {xyz(p)} Items[{{Slot:{loot.NOTE_SLOT}b}}]")
        back = L.wait_until(lambda p=p, title=title: book_in(p) == title, 10)
        if not (there and back):
            bad.append(f"{title}: there {there}, back {back}")
    check(
        f"notes: each of the {len(note_chests())} books in a chest is put back"
        f" when taken (not: {bad})",
        not bad,
    )


def scramble() -> dict[str, bool]:
    """work every machine, empty every container, break every weak wall:
    what a visitor leaves behind. Returns what was seen to open"""
    opened = {}
    copper = M.copper_cells()
    for p in copper["bulbs"].values():
        L.set_block(p, bulb(True))
    astro = M.astrolabe_cells()
    M.astrolabe_set(astro, C.ASTROLABE_LEVERS)
    org = organ.organ_cells()
    organ.play(org, C.ORGAN_TUNE)
    arch = B.archery_cells()
    L.set_block(arch["bulb"], bulb(True))
    for lamp in arch["lamps"]:
        L.set_block(lamp, bulb(True))
    listen = B.listening_door_cells()
    L.set_block(listen["bulb"], bulb(True))
    lect = M.lectern_cells()
    M.set_page(lect["trigger"], C.LECTERN_PAGE)
    lib = library_cells()
    s = lib["shelf"]
    L.cmd(f"item replace block {xyz(s)} container.5 with minecraft:air")
    L.cmd(f"data merge block {xyz(s)} {{last_interacted_slot:5}}")
    doors = lever_doors()
    for d in doors.values():
        L.lever(d["lever"], d["facing"], "wall", powered=True)
        M.poke(d["dust"])
    L.tick(40)
    opened["the inner vault"] = M.door_open(copper)
    opened["the alchemist's cellar"] = M.panel_open(astro)
    opened["the crypt's chamber"] = M.door_open(org)
    opened["the archery cache"] = L.is_block(
        arch["hatch"], "minecraft:iron_trapdoor[open=true]"
    )
    opened["the ossuary"] = is_open(listen["door"])
    opened["the hidden study"] = M.door_open(lect)
    opened["the library's door"] = is_open(lib["door"])
    for name, d in doors.items():
        opened[name] = is_open(d["door"])
    for p, _block in note_chests().values():
        L.cmd(f"data modify block {xyz(p)} Items set value []")
    for p, _stacks, _item in stores().values():
        L.cmd(f"data modify block {xyz(p)} Items set value []")
    for c in cache_cells().values():
        L.set_block(c["wall"], L.AIR)
    return opened


def as_built() -> list[str]:
    """what is not as the build left it (the machines and the doors)"""
    bad = []
    copper = M.copper_cells()
    if M.lit_bulbs(copper) != set(C.COPPER_START):
        bad.append(f"copper bulbs lit: {sorted(M.lit_bulbs(copper))}")
    if not M.door_shut(copper, copper["material"]):
        bad.append("the inner vault is open")
    astro = M.astrolabe_cells()
    on = [
        k
        for k, p in astro["levers"].items()
        if L.is_block(p, "minecraft:lever[powered=true]")
    ]
    if on or not M.panel_shut(astro):
        bad.append(f"astrolabe: levers on {on}, panel shut {M.panel_shut(astro)}")
    org = organ.organ_cells()
    if not M.door_shut(org, org["material"]):
        bad.append("the crypt's chamber is open")
    if not L.is_block(org["reset_block"], M.STONE):
        bad.append("the organ's reset is still held")
    arch = B.archery_cells()
    if not L.is_block(arch["hatch"], "minecraft:iron_trapdoor[open=false]"):
        bad.append("the archery hatch is open")
    if any(L.is_block(p, f"{B.BULB}[lit=true]") for p in arch["lamps"]):
        bad.append("the range's lamps are lit")
    listen = B.listening_door_cells()
    if not is_shut(listen["door"], listen["door_block"]):
        bad.append("the ossuary is open")
    lect = M.lectern_cells()
    page = L.cmd(f"data get block {xyz(lect['trigger'])} Page")
    if "data: 0" not in page or not M.door_shut(lect, lect["material"]):
        bad.append(f"lectern: {page.split('data:')[-1].strip()}, or the study open")
    lib = library_cells()
    s = lib["shelf"]
    last = L.cmd(f"data get block {xyz(s)} last_interacted_slot")
    if (
        "data: -1" not in last
        or M.container_count(s, "book") != 6
        or not is_shut(lib["door"], lib["material"])
    ):
        bad.append(
            f"library: {M.container_count(s, 'book')} books, last slot {last[-4:]}"
        )
    for name, d in lever_doors().items():
        if L.is_block(d["lever"], "minecraft:lever[powered=true]") or not is_shut(
            d["door"], d["material"]
        ):
            bad.append(f"{name}: its lever on or its door open")
    inner = mill_inside()
    if not L.is_block(inner["input"], inner["input_block"]):
        bad.append("the mill's input block is not back")
    return bad


def unstocked() -> list[str]:
    """the containers that are not full, the books and weak walls missing"""
    bad = []
    stock = {
        "founder": loot.RELIQUARY,
        "alchemist": loot.STUDY,
        "cantor": loot.CELLAR,
        "steward": loot.CHAMBER,
        "last": loot.INNER_VAULT,
    }
    for key, (p, _block) in note_chests().items():
        lacking = [i for i, n, *_ in stock[key] if not held(p, i, n)]
        if lacking or book_in(p) != clues.BOOKS[key][0]:
            bad.append(f"{key}'s chest: lacking {lacking}, book {book_in(p)!r}")
    for name, (p, _stacks, item) in stores().items():
        if not held(p, item):
            bad.append(name)
    for name, c in cache_cells().items():
        if not L.is_block(c["wall"], loot.WEAK_WALL):
            bad.append(f"the wall of {name}")
    t = M.transmuter_cells()
    if not M.locked(t["reward_dropper"]):
        bad.append("the transmuter's dropper lost its lock")
    return bad


def check_reset(check, reload) -> None:
    """scramble the castle, ring the Steward's bell and read it all back.
    ``reload`` forceloads the site again (the reset lets it go)."""
    bell = bell_cells()
    button, state = bell["button"], bell["button_state"]
    before = as_built() + unstocked()
    check(
        f"reset: the castle starts as built and stocked (not: {before[:6]})", not before
    )
    try:
        opened = scramble()
        shut = [name for name, ok in opened.items() if not ok]
        left = unstocked()
        check(
            f"reset: scrambled first: {len(opened)} doors opened (not: {shut}),"
            f" {len(left)} containers, books and walls gone",
            not shut and len(left) >= len(note_chests()) + len(stores()),
        )
        L.set_block(button, f"{BELL_BUTTON}[{state},powered=true]")
        rung = L.wait_until(lambda: running("reset"), 5)
        L.set_block(button, f"{BELL_BUTTON}[{state},powered=false]")
        L.tick(RESET_TICKS + 20)
        time.sleep(2)
        done = L.wait_until(lambda: not running("reset"), RESET_TICKS)
        # (verify's own load of the road to spawn is not the reset's to undo)
        a, b = C.site_box()
        loaded = [
            (x, z)
            for x, z in cmdblocks.forceloaded()
            if a.x // 16 <= x <= b.x // 16 and a.z // 16 <= z <= b.z // 16
        ]
    finally:
        reload()
    L.tick(40)
    machines, stock = as_built(), unstocked()
    check(
        f"reset: the bell starts it ({rung}) and it ends ({done}), leaving of"
        f" the site only the bank's chunk forceloaded ({loaded})",
        rung and done and loaded == [cmdblocks.bank_chunk()],
    )
    check(
        "reset: every secret door shut and every machine as built"
        f" (not: {machines[:6]})",
        not machines,
    )
    check(
        f"reset: all {len(note_chests()) + len(stores())} containers full, the"
        f" trail's books in their chests, the caches walled up (not: {stock[:6]})",
        not stock,
    )
    if machines:  # leave the castle as built for the checks that follow
        tidy()


def tidy() -> None:
    """put the machines back by hand (a failed reset must not fail the rest)"""
    M.copper_reset(M.copper_cells())
    M.astrolabe_set(M.astrolabe_cells(), dict.fromkeys(C.ASTROLABE_LEVERS, False))
    org = organ.organ_cells()
    L.set_block(org["reset_block"], M.STONE)
    organ.play(org, [organ.wrong_key()])
    L.set_block(B.archery_cells()["bulb"], bulb(False))
    L.set_block(B.listening_door_cells()["bulb"], bulb(False))
    M.set_page(M.lectern_cells()["trigger"], 1)
    lib = library_cells()
    put(lib["shelf"], lib["shelf_block"])
    for d in lever_doors().values():
        L.lever(d["lever"], d["facing"], "wall", powered=False)
        M.poke(d["dust"])
    L.tick(40)


def checks(check, reload, weak_walls: int | None = None) -> None:
    """verify's play group: what is built, the trades, the purse, each
    feedback, the fight, the notes, and last the reset (``reload``
    forceloads the site again after it). ``weak_walls``: how many blocks
    of loot.WEAK_WALL the whole build places."""
    check_built(check, weak_walls)
    check_charnel(check)
    check_trades(check)
    check_purse(check)
    check_organ(check)
    check_archery(check)
    check_lectern(check)
    check_fight(check)
    check_notes(check)
    check_reset(check, reload)
    print(
        "INFO play: the pick's can_break (does it break the weak walls for a"
        " player in adventure mode, and nothing else?) needs a player: not tested"
    )
