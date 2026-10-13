# Castle 2 plan (draft for iteration)

Castle 2 is Castle Fable with a lower bailey twice the size, filled with a
timber-framed village, farm animals in pens, people, and richly furnished
rooms. It reuses `examples/castle` (it does not fork it): castle2 imports
castle's modules, sets a bigger layout, and swaps or adds stages.

## Phase 0: make castle's layout resizable (castle builds exactly as now)

- `castle_layout.py` takes the bailey's depth from the environment
  (`BAILEY_DEPTH`, default 81). Today ~70 bailey coordinates in
  `build_inner.py` are literal z values (dungeons z 131..143, catacombs,
  market, cells...). Make each relative to the gate (`ZS - n`) or to the
  junction (`UD + n`), so the gate end (gatehouse, market, dungeons) moves
  with the south wall and the north end (barracks, stair) stays.
- Mid-wall towers become a list spaced along the curtain (one pair at 81,
  two pairs at 162), and the wall stairs and lantern grid follow.
- Split the stages that mix structure and furniture (`keep_interiors`,
  `chapel`, `bailey_buildings`, `details`) into a shell part and a
  furnishing part, so castle2 can swap only the furnishing.
- Check: build castle at default size and diff a `world.scan` of the site
  against one taken before the refactor: identical blocks.

## Phase 1: the doubled bailey

- `BAILEY_DEPTH=162`: the bailey becomes 121 x 162 (x 0..120, z 65..226).
  The site grows to about 150 x 270, so castle2 needs a new `ORIGIN`: the
  default one would put spawn inside the site. Survey with
  `scripts/survey.py` for a site whose ground is within ~30 blocks of both
  ward levels, and propose two or three candidates.
- Layout of the new bailey (north to south):
  - north third (z 65..120): barracks, stables, smithy, well and the cross
    paths as now;
  - middle (z 120..190): the village: a market square round a second well
    or a market cross, houses along two or three lanes;
  - south (z 190..226): pens and paddocks along the walls, market stalls by
    the gate, the dungeon hut.
- `castle2_layout.py` holds `HOUSES` (footprint incl. jetties, facing,
  options), `PENS`, `LANES` and `PEOPLE`; `layout_problems()` is extended to
  check houses and pens against towers, paths, each other and the lanes.

## Phase 2: `medieval_house()`, one function with options

```python
medieval_house(
    corner: Vec3,            # NW corner of the ground floor, at standing level
    width: int, depth: int,  # ground floor, 5..11 x 5..13
    floors: int = 2,         # 1..4 storeys
    facing: Direction = SOUTH,       # the street side (door, jetties, shop front)
    jetty: int = 1,          # each upper floor overhangs the street by this (0 = none)
    jetty_sides: str = "front",      # "front", "front+sides", "all"
    ground: str = "stone",   # "stone" plinth storey, or "timber"
    frame: str = "close_studding",   # "close_studding", "square_panel", "braced"
    roof: str = "gable",     # "gable", "gable_cross" (dormer gable to the street), "hip"
    roof_block = Item.SPRUCE_STAIRS, # or DEEPSLATE_TILE_STAIRS, ...
    chimney: bool = True,
    windows: str = "leaded", # "leaded" (panes), "shuttered", "shop" (open counter)
    window_boxes: bool = False,
    contents: str = "home",  # see below
    seed: int | None = None, # varies the small things repeatably
) -> Volume
```

- Look: white infill (calcite or white terracotta: pick by render), black
  beams (stripped dark oak logs, axis-aware; see question 4), sill and
  floor beams at every storey, joist ends under each jetty (upside-down
  dark oak stairs), brick chimney with a campfire on top for smoke, steep
  roof via `gable_roof`/`hip_roof` with an overhang.
- Inside: plank floors on beams, a ladder (small houses) or a stair (width
  7+), lanterns, a fireplace on the chimney wall.
- `contents` presets, each furnishing the floors and naming the shopkeeper
  it wants: `home`, `baker`, `butcher`, `tailor` (looms, wool), `tavern`
  (barrels, tables, seated drinkers), `apothecary`, `candlemaker`,
  `carpenter`, `fletcher`, `cartographer`, `cobbler`, `weaver`. Shops get a
  ground-floor counter with open shutters, a hanging sign over the door and
  goods on shelves (`*_shelf` blocks show items) and in item frames.
- Returns the bounding `Volume` and the positions people should stand at
  (counter, bed, hearth), which Phase 4 uses.
- Lives in `examples/castle2/house.py` first; once it settles it could
  move to `mciwb.builders` (question 2).
- Tested on its own: a rig script builds every combination of options in a
  row in the air, renders it, and checks doors are walkable, every floor
  is reachable, nothing pokes outside the returned volume, and jetties have
  their joists.

## Phase 3: farm animals in pens

- Pens of fence with a gate, a water trough (cauldron), hay bales, a
  shelter roof, and a lantern so nothing hostile spawns inside:
  cows, pigs (a mud wallow), sheep of several colours, goats on a rocky
  mound, a chicken coop with nesting barrels, a rabbit hutch, bee hives by
  the upper ward garden, a duck-less pond with frogs.
- Some young animals kept young (`Age:-24000, AgeLocked:1b`).
- A kitchen garden and allotments: farmland with wheat, carrots, cabbage
  (beetroot), a scarecrow (armour stand with a carved pumpkin).
- Animals are not fed, so they do not breed; verify checks each pen still
  holds what was put in it.

## Phase 4: people

All tagged as now (castle tag + stage tag), `PersistenceRequired`.

- **Static** (`NoAI:1b`, `Invulnerable:1b`, facing set): shopkeepers at
  their counters with real trades (`Offers`) that match the shop, e.g. the
  baker sells bread for emeralds; the king and queen on the thrones; the
  cook in the kitchen; the librarian at a lectern; a monk at the altar;
  the alchemist (a witch with NoAI?) at the brewing stands; the
  blacksmith at the anvil; a jailer in the guard room; drinkers seated in
  the tavern (a villager riding an invisible, small armour stand sits).
- **Mobile**: villagers wandering the village (nitwits or masons, which
  do not take crops and have no food, so no breeding), children playing
  (baby villagers, AgeLocked), cats and a tame dog, chickens loose in the
  square, a copper golem tending the market chests, the iron golem.
- **Guards**: posed armour stands with spears on the wall walks and gate
  (static), with names on the captain and the gate sergeant.
- Risks to handle: villagers with beds and workstations can spawn extra
  iron golems and claim other jobs; verify counts only tagged entities and
  the cleanup removes untagged golems in the site. Mobile villagers must
  stay inside: doors in the gate are portcullised; check after ticks that
  every mobile one is still in the bailey.

## Phase 5: rooms in full detail

A furnishing function per room, each checked by render (top + iso of the
room alone) before moving on. Renders draw stairs as full blocks, so they
cannot show which way a seat faces (castle's thrones, benches, chairs and
pews were all backwards). Seats are placed by a `seat(pos, faces)` helper
that takes the direction the sitter looks, and verify reads every seat's
state back and checks that it faces its table, altar or hall:

- **Great hall**: tapestries (patterned banners), high table with plates
  (decorated pots, cake, candles), minstrels' gallery, fireplace with a
  spit, rushes (carpets), hounds by the fire, servants.
- **Kitchen**: hearth with smokers and cauldrons, hanging chains with
  lanterns, pantry of barrels and shelves, a bread oven, the cook.
- **Library**: chiseled bookshelves, lecterns with written books (castle
  history, a hint at the secret door), reading desks, a map wall.
- **Armoury**: weapon racks (item frames, shelves), armour stands in each
  material, grindstone, practice dummies.
- **Chambers**: four-poster beds (fence posts, carpet canopy), wardrobes,
  dressing tables, paintings, rugs; a nursery; a privy.
- **Chapel / crypt**: pews, altar with candles, stained glass, an organ
  (note blocks), tombs with effigies, skulls in niches.
- **Alchemist's tower**: brewing stands, coloured cauldrons, specimen jars,
  a parrot, a star chart.
- **Barracks, smithy, stables, dungeons, vault, gatehouse winch room**:
  bunks and kit, forge tools, tack and feed, prisoners and chains, treasure
  piles, a guard at the winch.

## Phase 6: mysterious machines and a trail of clues

Like castle's mechanisms: plain redstone that works without mciwb, each
with a `*_cells` function giving the positions of its parts, so that both
the build and verify use them. Most of them open something, so the
machines and the secrets become one puzzle trail rather than decoration.

Machines (all of them):

- **The lectern lock** (library): a book on a lectern; turning it to the
  right page sends that page's comparator signal to a hidden door. The
  page number is a clue found elsewhere.
- **The astrolabe** (alchemist's tower): item frames on a wall, each
  turned to a position (an item frame's comparator output is its
  rotation); set all of them right and a floor panel slides open. The
  star chart in the room shows the setting.
- **The organ** (chapel): note-block keys played in the right order (a
  sequence lock: wrong key resets it) open the crypt's second chamber.
  The tune is carved on a tomb.
- **The listening door** (catacombs): a calibrated sculk sensor behind a
  carved face; make the right kind of sound in front of it (drop an
  item, open a trapdoor) and the wall opens.
- **The transmuter** (alchemist): a hopper and crafter in a brass-and-
  copper casing; feed it the right ingredients and it hands back
  something rare, with lamps and note blocks running as it works.
- **The clock tower** (market square): a daylight-sensor clock that rings
  a bell at dawn and dusk and lights the square at night.
- **The archery lock** (barracks yard): hit the bullseye of a target
  block to open a hatch for a moment.
- **The copper puzzle** (vault antechamber): a lights-out grid of copper
  bulbs and buttons; light them all to open the vault's inner door.
- **The water wheel and mill** (village): a mill house with an observer
  chain driving moving parts, which also hides a way into the tunnels.
- **The engine** (exists): give it a purpose, e.g. its chase completes
  only when the astrolabe is set.

Clues, at least two per secret (one plain, one subtle), new and old
secrets alike (the library bookshelf, the smithy hatch, the well's
bubble column, the crypt and cell levers, the hidden chambers):

- written books: a drunk's ramblings on a tavern table, the castle's
  history on a library lectern, the alchemist's notebook, a prisoner's
  diary scratched in a cell;
- signs and carvings: riddles on tomb lids, a mason's mark on the one
  wall block that moves, an engraved plaque in the smithy;
- things people can notice: a worn path of coarse dirt leading to a
  wall, a draft (a tiny bubble column / particle-less airflow cue), a
  painting hiding a sign behind it, a banner pattern that matches a
  door, an item frame pointing at a bookshelf;
- shopkeepers' trades: the cartographer sells a map of the castle with
  marks on it (a filled map with banner markers);
- the guide gets a "Rumours" section with vague hints, and its full
  solutions move to a separate spoilers section.

`castle2_layout.SECRETS` lists each secret with its machine, what opens
it and where its clues are; verify checks every clue is in place
(book on its lectern, sign text, map in the trade) and works every
machine over RCON, as castle does now (lectern page by `data modify`,
frame rotation by `data modify entity`, arrows summoned at the target,
redstone blocks standing in for button presses).

## Checks and docs

- `verify_castle2.py`: runs castle's checks, plus houses (doors, stairs,
  floors reachable), pens closed (flood fill from inside stays inside),
  every static person at their spot, mobile ones inside the walls, entity
  counts by stage.
- README for castle2 and a guide with teleports to the village, market
  and pens; a new image for the docs.

## Order of work

0 (refactor, castle unchanged) -> 1 (bigger bailey, site survey) -> 2
(house function and its rig) -> village layout -> 3 -> 4 -> 5 -> 6, rendering
after each step. Each phase is its own PR.

## Decisions (2026-10-13)

1. The bailey doubles southwards: depth 81 -> 162.
2. `medieval_house` starts in the example; once castle2's village has
   settled its options it moves to `mciwb.builders` in its own PR (tests,
   docs), leaving the `contents` presets in the example.
3. Mobile villagers roam freely in the bailey.
4. Beams are stripped dark oak.
5. Clues form a trail, one leading to the next: not too hard, but enough
   to keep it interesting. All ten machines are built.
