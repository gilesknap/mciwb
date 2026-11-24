# Castle 2: progress

The state of the work on castle2 (gilesknap/mciwb#173, plan in
[PLAN.md](PLAN.md)), for whoever picks it up next. Branch
`examples/castle2`.

## Done

- **Phase 0** (castle resizable, unchanged at its default size):
  `BAILEY_DEPTH` (default 81) in `castle_layout`; mid-wall towers are a
  list (`MID_ZS`, one pair per 81 of depth) with their wall stairs; the
  market follows the gate. The stages that mix structure and furniture are
  split: `keep_interiors` = `interiors_shell` + `interiors_furnishing` +
  `interiors_lights`, `chapel` = `chapel_shell` + `chapel_furnishing`,
  `bailey_buildings` = `bailey_shell` + `bailey_furnishing`, `details` =
  `details_fixtures` + `details_people`. Every seat goes through
  `castle_lib.seat(pos, faces)` (faces = the way the sitter looks) and is
  recorded in `castle_lib.PLACED_SEATS` (castle's own `castle_layout.SEATS`
  from #174 lists castle's seats for its verify). The branch was rebuilt on
  694358f (#174, which reworked castle: tower doors, levers by the gates,
  pit trap, seats): the refactor was redone on top of it, dropping our own
  seat fix (#174 has it). Proof at the time: `record_build.py` records a
  full castle build against a fake client, and the sorted commands and the
  final blocks were identical to 694358f's. They no longer are, and that
  is intended: castle has since changed on this branch. Against main's
  castle the recording differs in 608 block lines (every tower's stair or
  ladder now comes out on its top floor, the well's rim has a gate so the
  bubble column has a way out, and sign text is plain SNBT strings, as
  26.x wants it: the quotes showed on every sign), and 44 summons gain
  `Invulnerable` (fittings, people and pets). To see what a change to
  castle does, run `python record_build.py ../castle /tmp/after` and diff
  it against a recording of `git archive origin/main examples/castle`.
  Decision taken: the underground complex (dungeons, catacombs, lower
  treasury) does NOT move with the gate: it hangs off the smithy's hatch and
  the well's tunnel, so it is counted from the junction. (PLAN.md put the
  dungeon hut in the south: deviation.)
- **Phase 1** (doubled bailey): `castle2_layout` (defaults ORIGIN
  560,68,-190, BAILEY_DEPTH 162, NAME "Fable II", BANNER cyan; Fable is
  red, the castle at 148,-262 purple, the one at -300,-40 yellow),
  `build_castle2` (castle's build plus castle2's stages and layout check),
  `verify_castle2` (castle's checks + castle2's).
- **Phase 2** (`medieval_house`): `house.py`, `house_contents.py`,
  `house_rig.py`. All 13 rig variants pass offline and in the world (the
  rig was built over the site at y 150+ and cleared).
- **Village layout**: `castle2_layout.HOUSES` (32 houses), `LANES`,
  `SQUARE`, `MARKET_CROSS`, `CLOCK_TOWER` plot (empty, for phase 6);
  `village_problems()` checks houses against towers, castle's buildings,
  paths, stairs, signs, lanes, the square and each other.
- **Phase 3** (pens): `pens.py`; `PENS`, `GARDEN`, `BEEHIVES` in the layout.
- **Phase 4** (people): `people.py`.
- **Phase 5** (rooms in full detail): `rooms.py` replaces castle's
  furniture in the `interiors`, `chapel` and `bailey_buildings` stages
  (castle's shells kept; see `build_castle2`), and a new `furnish` stage
  (after `dungeons`) adds detail where castle furnishes as it builds
  (alchemist's tower, dungeon prisoners, vault treasure, winch-room guard).
  All seats go through `castle_lib.seat`. What each castle2 stage summons
  is counted by running it against a fake client
  (`record_build.summon_counts`), so `SUMMONED` stays right.
- **Phase 6** (machines and the clue trail): all ten machines, each with
  its `*_cells` and a check that works it in place: `machines_upper.py`
  (lectern lock, copper puzzle, astrolabe, engine bell, transmuter),
  `organ.py`, `machines_bailey.py` (clock tower, archery lock, mill,
  listening door); `SECRETS` in the layout. `clues.py` (stage `clues`,
  after `people`) lays the trail: books on lecterns (tavern, fletcher, the
  prisoner's cell) and in the secrets' reward chests (slot 13), a plaque in
  the smithy, and Mercator's chart (his last trade). `clues.TRAIL` orders
  it and adds each book to its secrets' `clues`; every secret has 2+.
  `guide2.py` prints Rumours, then the whole trail as Spoilers.
- **Protection** (branch `examples/castle2-play`; so that visitors can
  play in the castle without taking it apart):
  - `cmdblocks.py`: the command bank, the reusable helper for hidden
    command blocks. `Bank.row(name, commands)` plans a row (a repeating
    block and chain blocks, always active; `first="impulse"` for a row
    worked by redstone), `Bank.store(name, block)` a master copy of a block
    to clone from; `Bank.place()` builds it and `Bank.problems()` reads it
    back, and `last_run`, `parses`, `forceloaded` help the checks. The bank
    is `castle2_layout.COMMAND_BANK` (local 33,0,47 to 46,12,60: one
    chunk, in the ground under the upper ward that no stage touches), with
    room for 35 rows of 12 commands (`ROWS`: 18 taken) and 12 masters
    (`STORE`: 10 taken). `Bank.rows` splits a long list over rows
    `name 1`, `name 2` ...; `Bank.score` keeps a number (a fake player in
    the scoreboard objective named after the castle's tag, made by
    `place`); `start_timer` and `timer` are timers (an area effect cloud
    in the bank's chunk, which the game ages and removes: a command tests
    `nbt={Age:n}` for one tick of it, so nothing has to count). A new feature adds a name to `ROWS` (and `STORE`),
    and a function that plans its rows to `cmdblocks.PLANNERS` (as
    `protect.plan_rows`; import its module in build_castle2): the protect
    stage places the whole plan and verify reads it all back.
  - `protect.py`, stage `protect` (last): the adventure zone
    (`zone_commands`: six commands a tick, tag `castle_560_-190.zone`, box
    `castle2_layout.zone_box()` = the site + ZONE_MARGIN 8, any height),
    the books that come back (a master lectern cloned over one that has
    lost its book), the Engine's hoppers locked, the bank's chunk
    forceloaded. `build_castle2.forceload` wraps castle's so that a build
    or a verify leaves that chunk loaded.
  - Ways out: `machines_upper.slide_door` (study, crypt chamber, inner
    vault) has a wooden button inside on the door's input block; the inner
    vault's door was a "direct" door (shut while powered) and is now a
    torch door behind an inverter (`copper_cells`: dark, dark_block,
    inverter, lit_dust, guard); the astrolabe's panel piston is fed
    through a subtract comparator that a button in a niche at the top of
    the cellar's ladder cuts. `main_gate.postern`: an iron door round the
    portcullis, a stone button each side.
  - Entities: `castle_lib.protected` (in castle, so castle's summons
    change too: 44 of its commands, no block): `Invulnerable` for armour
    stands, item frames, paintings, villagers, cats, wolves, the parrot,
    horses and golems; `Fixed` frames; `DisabledSlots:4144959` on stands
    that wear something; the copper golem waxed (`next_weather_age:-2L`:
    unwaxed it ages into a statue). Pen animals and loose chickens are
    left as they are.
  - Drift: a barrier lid over the goat pen and the frog pond (`pens.py`);
    waxed lightning rods (the kitchens' spits in `rooms.py`, the
    astrolabe's gnomon, the clock tower's rod) and a waxed copper chest at
    the market. Left to age on purpose: castle's own rods (tower roofs,
    the keep's lantern, the Engine's: castle's verify accepts any stage)
    and the Engine's copper block on its piston; the alchemist's roof is
    built oxidised. The copper bulbs, the transmuter's casing and the pipe
    were waxed already.
- **Play** (branch `examples/castle2-play`; so that a visitor in
  adventure mode has a game, and the next one too). `play.py` (stage
  `play`, after `clues`), `loot.py` (what every restocked container
  holds, used by the stage that builds it, the reset and verify):
  - The end of the trail: the Founder's chest in the inner vault
    (`machines_upper.hoard`, `loot.INNER_VAULT`: castle's nether star,
    elytra, trident, netherite, enchanted apples, totem, heart of the
    sea, diamond blocks), a plaque, and a ninth book, The Founder's Last
    Word (`clues.BOOKS["last"]`). The main vault keeps `loot.MAIN_VAULT`;
    its netherite blocks are raw iron now (two netherite blocks stand by
    the Founder's chest). The Engine's bell was left as it was: no cheap
    point for it was found.
  - The Steward's bell (`play.reset_commands`, rows `reset 1..6`): a
    stone button in the winch room starts a timer of 130 ticks. Tick 2:
    `forceload add` the site (the bell is 14 chunks from the keep, a
    player's chunks reach 10). Tick 100: the copper bulbs to their start
    pattern, the astrolabe's levers off, a redstone block beside the
    organ's reset row, the archery and listening bulbs dark, the lectern
    at page 1, the library's bookshelf cloned from its master, the levers
    of the mill (both), the cell block and the crypt off; five chests
    cloned from masters (those with a book), 20 containers filled by
    `data modify ... Items set value`, four weak walls set, the fight's
    wave set to 0. Tick 104: the dusts of the levers set by command
    placed again. Tick 116: the organ's redstone block out. Tick 120:
    `forceload remove` the site, `forceload add` the bank's chunk.
  - Books back in chests (row `notes`): a book of the trail missing from
    slot 13 of its chest is copied from the chest's master.
  - Emeralds: `people.BUYS` (nine buying trades) and three tools sold
    for 1 emerald; the purse (row `purse`: tellraw, give, tag, for
    players in `PURSE_BOX` without `PURSE_TAG`).
  - Feedback (rows `organ`, `archery`, `lectern`). The commands read
    the redstone and do not drive it: the organ's reset dust and advance
    dust at 15 (a timer for each sign keeps the rest of the pulse, and
    the key's release, from giving it again); the target's power for the
    three lamps (copper bulbs, out again after 100 ticks). The lectern
    lock is the one place a command reaches into a machine: a lectern is
    `powered` for two ticks when its page is turned, which starts an
    80-tick timer again, and while one runs the dust between the lock's
    gate and the door's input (`lectern_cells()["patience"]`) is a stone
    brick. So the door opens 4 seconds after the last page turn, and
    someone clicking through the 15 pages sees nothing move. The
    Founder's Testament says to wait.
  - The restless dead (rows `fight 1..4`, the number `#wave`): the
    chamber `CHARNEL` south of the ossuary, cut into what was natural
    cave. 0 idle; the pillar's button sets 1; 1, 3, 5 summon a wave
    (zombies, skeletons with bows, tag `castle_560_-190.fight` only) and
    go to 2, 4, 6; with none alive the wave pays (items summoned on the
    altar) and goes on; 7 is won. One command puts any of them that is
    outside the chamber's box back in its middle; one sets the wave to 0
    when no player is in the box; one kills them while the wave is 0.
    The ossuary had no east wall north of the listening door's passage
    (raw rock, with a cave's mouth in it): it has one now.
  - The prospector's pick (`loot.PICK_COMPONENTS`: `can_break` for
    `loot.WEAK_WALL`, cracked deepslate bricks, of which the world's
    site had none) in the reliquary; `castle2_layout.CACHES`.
  - A start: Hal the Crier (`people.CASTLE_PEOPLE`) and a notice board
    (`play.notice_board`) inside the gate.
  - RCON drops a command over 1446 bytes (the connection breaks, and a
    build that dies then leaves the site forceloaded: run any stage
    again to unload it). Mercator's summon, with the whole chart in his
    trades, is 1370: the chart's pages must stay short.
- **Docs**: README.md; `guide2.py` (castle's guide for castle2, plus the
  village, shops and keepers, pens and people); castle2's teleports are
  added to castle's `TELEPORTS` (checked by castle's verify, listed in the
  guide).

## In the world (a test world, Minecraft 26.3)

Castle Fable II is built at ORIGIN 560,68,-190: site x 550..690,
z -200..47, entities tagged `castle_560_-190`; its road runs south from
the bridge, west along z ~52 / x 545, then along z -64 to spawn
(32,74,-64), sharing the last leg with the castle at 148,-262. Rebuilt
2026-10-17 in full from this branch (machines and clues included) on
mciwb 694358f.

Rebuilt in full again 2026-11-24 from `examples/castle2-play` (66 s), with
the protect stage: chunk (37, -9) is forceloaded from then on.

The play pass (2026-11-24): stages `bailey_machines`, `machines`,
`people`, `clues`, `play` and `protect` rebuilt in place (the command
bank now reaches down to local y 0). The world also holds the scoreboard
objective `castle_560_-190` (one number, `#wave`).

Last full verify (2026-11-24, all checks, nobody online, from the
server's own host): **300/300 passed** (about 8 minutes: a sprint
keeps the empty server awake for another minute, and the roam and the
reset each wait for it). The full run before it gave 299/300: "roam:
after 6000 ticks all 32 villagers still inside the walls (found 30 of
32)". Asked straight after, and at four samples over the next 12000
ticks, all 32 were inside, so two had been out of the check's box and
come back. Not explained: the box is x 0..120, and the wall towers'
floors reach to x -3 and 123 through their ground doors, which would do
it, but no villager was caught there. The
clock tower's dawn check was flaky (2 of 4 runs) at time 23500, on the
edge of sunrise: it now rings at 1000, and still failed once in four
full runs on 2026-11-24, in rain (not looked into). Its "lamps out
by day" check failed in rain (the inverted detectors give 3 at noon in
rain, measured): in rain it now reads only the repeater. The site is in
a snowy_plains biome: when it snows, a layer of snow lies on the walks
and the bailey, and castle's checks that wanted air at a visitor's feet
(the wall stairs' walks, a teleport) failed; they and castle2's `free`
now take snow at the feet (`verify_castle.feet_free`).

### What adventure mode allows: not yet tried by a player

Nobody was online, and RCON cannot act as a player, so **none of these
is confirmed**. A person in adventure mode in the castle must try each.
The third column is only what the 26.3 server's classes suggest (the jar
is not obfuscated; I listed which methods read `Player.mayBuild`, the
flag adventure mode clears): a guide to what to expect, not a result.

| Action | Tried | What the server's code suggests |
| --- | --- | --- |
| Turn a lectern's page | no | `LecternMenu.clickMenuButton` reads `mayBuild` for some button: probably only "take book", so probably allowed. The lectern lock and three clues need it |
| Take a book from a lectern | no | probably refused in adventure (same method). The books row puts it back in any case (worked over RCON) |
| Ring a bell | no | `BellBlock` reads no game mode: probably allowed. The listening door needs it |
| Take or put a chiseled bookshelf book | no | `ChiseledBookShelfBlock` reads no game mode: probably allowed. castle's library door needs it, and nothing stops a visitor keeping the books |
| Drop an item in a hopper | no | nothing found against it. The transmuter needs it |
| Punch an item out of a frame | no | `ItemFrame.hurtServer` and `interact` read `fixed` and invulnerability, not `mayBuild`: a plain frame would lose its item, so all 108 are `Fixed` and `Invulnerable` (read back) |
| Take armour off a stand | no | `ArmorStand.interact` reads only `isDisabled` (DisabledSlots), `hurtServer` reads `mayBuild`: armour could be taken, the stand not broken; so the 31 stands with equipment have every slot disabled (read back) |
| Shear a sheep | no | `Sheep` and `ShearsItem` read no game mode: probably allowed (the sheep are not protected) |

The play stage adds these, none tried by a player either:

| Action | Tried | What is known |
| --- | --- | --- |
| Break a weak wall with the prospector's pick, in adventure mode | no | the pick's `can_break` names cracked deepslate bricks and nothing else (read back from the reliquary); the four walls are that block (read back). Also try it on another block: it must not break |
| Get the purse at the gate | no | the selector was tried on an armour stand (in the box and untagged: taken; tagged: not; outside: not). `give` and `tellraw` take players only |
| Turn the Book of Hours to page 13 and wait | no | verify sets the lectern `powered` by command, as the game does for two ticks on a page turn (`LecternBlock.signalPageChange`), and the door then waits 4 seconds and opens. That a hand-turned page powers it was not seen |
| Hear the organ's sour note and chime, see the smoke and sparks | no | their timers start for the right keys (read back); `playsound` and `particle` do nothing without a player |
| Sell wool, eggs, milk, fish to the keepers | no | the trades are in the villagers' offers (read back). That a static (`NoAI`) villager trades was not tried here |
| Fight the three waves | no | with an armour stand for the player each wave rose, was counted, was killed by command and paid; whether the fight is fair for a visitor with a stone sword on Easy is for a person to say |
| Pick the reward up from the altar | no | the items are there (counted); the altar is a slab one block from the pillar |
| Ring the Steward's bell by hand | no | verify sets the button `powered`, and the reset runs. With a player online it also sends two lines of chat to everyone in the zone |
| Be in a secret room when the bell is rung | no | the doors shut; each room has a way out from inside: a wooden button (study, alchemist's cellar, crypt's second chamber, inner vault), the ossuary's inner bell, the miller's way's inner lever, the fight chamber's stone button, the main vault's iron door to the well tunnel (worked by verify's machines checks) |

Also untested, for the same reason: the zone's change of game mode
(survival to adventure on entering, back on leaving, dying or changing
dimension). What was tested: in a rig the same box and "no longer in the
box" selectors, run by a repeating and chain command block, tagged and
untagged an armour stand as it was moved in and out; in the castle the
six commands are accepted by the server and their row runs every tick.
The `unless dimension` commands were accepted but never had anything to
act on. And that a locked hopper or dropper refuses a player (the locks
are read back, and the Engine and the transmuter work with them on).

## How to run

- Run the scripts on any host that can reach the server's RCON port, the
  nearer the better (a build is about 63 s on the server's own host, at
  about 0.05 ms a command; over a network allow a round trip per command).
  Give `mciwb run` the server with `--server` and `--port`, and the
  password in `MCIWB_PASSWORD`:
  - Build: `cd examples/castle2 && mciwb run build_castle2.py --server
    HOST --port PORT`.
  - Verify: the same with `verify_castle2.py` (about 100 s with nobody
    online, more with the roam and the reset checks; 20+ minutes with a
    player on, the ticks are real time). `CHECKS=clues,signs` for a
    subset; FORCE=1 if a player is near.
  - Run long jobs in the background with their output in a log file: a
    remote shell that is quiet for a minute may time out and kill its
    command.
- The world's files, if the host can read them, make the renders fast
  (`mciwb render --folder`, and `WORLD_FOLDER` for castle's `reach.py`).
  Without them use the RCON tools below; the chunks are not loaded outside
  a build or verify, so RCON block tests fail there.
- With Python 3.13 where `.python-version` says 3.11: use
  `uv run --python 3.13 ...` for ruff, pyright and `record_build.py`.
- See: `top_render.py` (plan of a large area, ~10 s), `render_rcon.py`
  (a small region), or offline `RECORD_PNG=x.png python record_build.py .
  /tmp/c2 build_castle2`.

## Known problems / notes

- Goats and frogs leap any fence: their pens have an invisible barrier
  ring (5 high) over a 3-high fence, and since 2026-11-24 a barrier lid
  at the ring's top. With the ring alone four goats and a frog got out
  over some weeks of play: one frog was found standing on top of the ring
  (y 76). How they get up there was not found out; the lid leaves no top
  to land on. verify counts every pen again after the roam's 6000 ticks.
  Animals step over a fence from any block beside it, so nothing in a pen
  stands next to its fence.
- Two of castle's gate guards (armour stands) had been pushed some blocks
  from their posts, probably by the loose goats. Nothing was changed for
  it: the rebuild put them back and the goats are penned. An invulnerable
  stand can still be pushed.
- A command block's command that succeeds is logged on the server's
  console (`command_block_output` is true, and no game rule was changed):
  the bank's commands fail while idle, so the log hears from them only
  when a visitor's game mode changes or a book is put back.
- A button set by command updates only its own neighbours; a pressed one
  also its block's. The checks of the buttons inside the secrets place
  the door's input block again to make up for it (`work_release`).
- Anything dropped on the Engine's hoppers joins the ring: the lock only
  stops a visitor opening them.
- A visitor who takes a lectern's book keeps it: the lectern gets a new
  one from its master, so copies can be collected.
- RCON replies get mixed with the dashboard's (`list`) now and then
  (#166 item 2): mciwb now retries setblock/fill/loot/ground reads (#170);
  castle2's checks read a failing block again.
- Wild animals wander into the site (it reaches 10 blocks outside the
  walls): `people.kill_strays` (run by the people stage and before the
  checks) removes untagged animals of the kinds castle2 keeps, and stray
  cats and iron golems.
- castle's verify leaves out marker armour stands from its "no armour
  stand in a block" check (castle2's seated people ride markers in their
  seats); castle's own seat check is given castle2's seats by
  verify_castle2.
- Hostile mobs still spawn somewhere in the site at night (cleanup kills
  ~10): probably natural caves under the platform, as castle notes. Not
  investigated.
- The main gate is closed to villagers by a row of fence gates outside
  castle's portcullis (main_gate.py; villagers cannot open them). verify's
  `roam` check sprints ROAM_TICKS (6000) and counts the villagers inside
  again: all 31 (9 of them mobile, which do move: ~20 blocks in 1200
  ticks) stayed in over 6000 and over 24000 ticks.
- The castle's own great hall carpet covers the dais step and cuts the
  benches (castle quirk, kept in castle; castle2's phase 5 should redo it).

## Next steps

0. Done: the second pass on play (see "Play" above). Have a person try
   both tables under "What adventure mode allows". Left out of it: a
   point for the Engine's bell; a once-only final reward for the fight
   (the sword is paid every time it is won); the smaller chests the reset
   does not fill (castle's guard room, barracks and keep chests, the
   transmuter's trays); a cost for a wrong lectern page (the wait was
   chosen instead).

1. Done (the notes kept for reference): phase 6, the ten machines and
   the clue trail. Build each in a rig first (as castle's
   test_modules.py: a stone block in the air over the site, toggled
   over RCON and read back), with a `*_cells` function used by the build
   and verify alike, then place it. `SECRETS` in the layout
   lists each secret, its machine and its clues; verify checks the clues
   (book on lectern, sign text, map in a trade) and works each machine.
   Formats tested in 26.3 (all work through Placer, NBT included):
   written books on lecterns
   (`lectern[...]{Book:{id:"minecraft:written_book",count:1,components:
   {"minecraft:written_book_content":{title:"T",author:"A",pages:["p1","p2"]}}}}`),
   patterned banners (`{patterns:[{color:"yellow",pattern:"minecraft:border"}]}`),
   chiseled bookshelves with Items, shelves with Items, hanging signs with
   front_text/back_text, villagers with VillagerData and Offers, a
   villager riding a marker armour stand. Paintings' `facing` is 0 south,
   1 west, 2 north, 3 east (item frames' 3D: 2 north, 3 south, 4 west,
   5 east). Ideas for the hard ones:
   - lectern lock: a comparator reads the page (a 15-page book gives
     page = signal); exact match with two subtract-mode comparators
     against constant signals (dust from a redstone block, 16 - c long)
     ANDed, or "≥ P" by dust length with "≥ P+1" cutting it via a torch;
     the result drives a castle_lib.hidden_door (its lever-variant dust).
   - astrolabe: an item frame's comparator output is its rotation + 1;
     three frames each through an exact-match, ANDed, open a floor panel.
   - organ: buttons as keys beside the note blocks (a hit note block gives
     no signal); a sequence lock from copper bulbs (they toggle on each
     pulse and a comparator reads them), a wrong key resetting them.
   - copper puzzle (lights-out): copper bulbs toggled by buttons wired to
     their neighbours; all lit, ANDed by comparators, opens the inner door.
   - archery lock: a target's output is 15 only for a bullseye: a dust
     line 15 long passes only that to a hatch.
   - clock tower (the plot at `CLOCK_TOWER`, 5x5 in the square):
     daylight detector and its inverse, observers pulsing a bell at dawn
     and dusk, lamps at night. The mill: an observer chain moving pistons.
   - verify over RCON: lectern page by `data modify block ... Page`, frame
     rotation by `data modify entity ... ItemRotation`, arrows summoned at
     the target, redstone blocks in place of button presses.
2. Done: the gate (fence gates, main_gate.py) and the `roam` check that
   the villagers stay in.
3. Done: the docs image (docs/images/castle2.png: `mciwb render 545 48 -205
   695 161 52 --view iso_sw --no-labels --scale 4 --folder <the world's folder>`,
   cropped), shown in docs/how-to/claude-skill.rst and the README.
