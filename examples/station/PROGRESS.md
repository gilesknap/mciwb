# The Drowned Station: progress

The state of the work on the station (plan in [PLAN.md](PLAN.md)), for
whoever picks it up next. Branch `examples/station`.

Nothing here is claimed to work unless a check exercised it or the owner
played it: each entry says which.

## Stages

| Stage | What | State |
| --- | --- | --- |
| 0 | Ground work: survey, layout, mechanisms proved in a rig, datapack delivery, the skeleton | done |
| 1 | The playable slice: shore, boat, dock, lift, start dome, Boiler Room, its tunnel, reset, recall, kit | built and played once: the way in, the Pump House, the Boiler Room, tunnels 0 and 1, the Gearworks' empty shell. The owner's first play-test (25 Nov 2026) asked for changes: see "The first play-test" |
| 2 | Gearworks and the Flooded Dome | the shells, tunnels 2 and 3 and a stub (a BYPASS lever) in each dome are built; the rooms are designed, not built |
| 3 | Foundry and the Signal Room | as stage 2: shells, tunnels 4 and 5, stubs |
| 4 | Clockwork Maze, the boss dome, the return tunnel, the win, the Wall of Fame | as stage 2: shells, tunnels 6 and 7, stubs; the win is the core's and is checked; the Wall of Fame's sign is not written |
| 5 | Polish from the play-tests, the guide, the docs image, the PR | not started |

Stages 1 to 5 each end with a play-test by the owner; the next does not
start until the owner has played the last and said what to change.

## Done

- **The shared core of stage 1**, built in the world and worked there by
  `verify_station.py`'s live checks (named in brackets), nobody online:
  - (This entry is the first round's: all eight shells and tunnels are
    built now, see "The ring's structure".) The empty, lit shells of the
    Pump House, the Boiler Room and the Gearworks (`domes.py`), each on a foundation, its two tunnel mouths
    plugged with brass doors. Read back: nothing inside or in a mouth
    wet, no hole in shell or floor, nothing but solid ground under the
    floor, the sea over the top, light of 8 or more at nine places at
    head height, no dropped items or falling blocks (`shell_0`,
    `shell_1`, `shell_2`). The wet check was seen to fail with one block
    of water put in the Gearworks, and to pass again once it had dried.
  - Tunnels 0 and 1 (`tunnels.py`), flooded, dark and shut behind brass
    doors with glass windows, each with a pump engine in its upstream
    dome. Worked: reset, the pump event (one piston out and one in, and
    the engine's lamp on and off, seen while it ran), every state read
    whole as the water fell a layer at a time from the top (the layers
    above all air, those below all sources, no flowing water, no air
    under water, every lamp glowing dimly, the doors still shut), then
    the lamps read coming on fully in order, both doors open, the engine
    still, the tunnel and both domes dry 150 ticks on; then, behind shut
    doors, a half-drained state set after the dry one and after the
    flooded one and left 100 ticks each; then reset and all sources
    again, the event's whole length on (`tunnels`).
  - The game core (`game.py`): the count of players and which dome each
    is in; each dome's own form: solo with one in it whoever else is in
    the game (one in the Boiler Room and one on the dock: solo), duo at
    once with two in it, solo again 3 s after one leaves it (read as solo
    within 4.2 s and
    not within the first 0.6 s) (`player_count`); the vote proposed, counted, shown on its bossbar,
    running out after 60 s, passing with every player's press, a player
    leaving mid-vote, one player one press, both kinds (`vote`); the
    level taking force on the next dome entered and the scaled values
    at levels 1, 5 and 10, the level kept through a reset
    (`difficulty`); the run started once, the clock, a dome solved once,
    the win and the best time kept per level (`progress`); the reset
    from a run with one tunnel open, one part drained, a vote open and
    progress made (`reset`). All of these with stand-ins for players:
    see "Stand-ins" below for what that leaves unproved.
  - The game rules of the plan set and read back, the difficulty Easy,
    both mineshaft spawners gone (`rules`); the station's box
    forceloaded (`forceloaded`).
- **The inside of the Pump House** (`dome_start.py`, stage
  `start_dome_inside`), built in the world and worked there by the live
  check `start_dome`, nobody online, players stood in for (see "The Pump
  House: findings" for what that leaves unproved):
  - Every block where the room's plan has it (1014 read back), its 52
    text displays and 2 interaction entities, the log on the lectern.
  - The master lever, set over by command with a stand-in in the dome:
    the run started, its lamps lit; put back and set over again during
    the run, it is held over and the clock runs on.
  - The map wall: the eight lamps and eight lines following the scores
    through locked, open and solved, tunnel 0's line lighting when the
    lever's pump event ends, and all of it back after a reset.
  - The clock board: the run's time, the best time ("--:--" when there
    is none), the level, read from the text displays.
  - The dial: the two real buttons (set by command) moving the proposal
    one step a press, not again while held in, stopping at 1 and 10, and
    held still while its vote is open; the lamps and the pointer.
  - The votes, by the functions the two voting buttons end in, run as
    two stand-ins: a level proposed, the proposer's second press not
    counted, the reset button during it ignored, confirmed by the other;
    a reset refused behind the shut door, proposed, the dial's confirm
    during it ignored, confirmed by the other, and the reset putting
    back the lever, its lamps, the door, the buttons, the log and the
    dial. The level is put back afterwards.
  - The dome still dry and whole, no dropped item in it.
  - Second round (after the first play-test), the same check, nobody
    online: the new map wall and the room's upper level and machinery,
    2387 blocks read back (bars and what the machinery lights by name
    alone); the governor's two pistons and its lamp seen both ways in
    ten seconds, the chase overhead in three or more states, a tank's
    level moving and the map's pin blinking, with a stand-in in the
    dome and again after a reset; the datapack's part standing still
    with nobody in the dome; and, on the plan alone (`walk_problems`,
    which the unit test runs too), a clear way at foot and head height
    from the arrival point and every side of the lift's shaft to both
    mouths, every input, the Wall of Fame, the look-out and the gallery.
- **The Boiler Room** (`dome_boiler.py`, stage `dome_1_inside`), built in
  the world and worked there by the live check `boiler_room`, nobody
  online, players stood in for (see "The Boiler Room: findings" for the
  puzzle and for what that leaves unproved):
  - Every block as built (599 read back: the puzzle's and the boiler
    house's; a block of a clock that runs by itself is read by its name
    only), the log on the lectern, coal
    in the bunker's dropper, the recall button's interaction entity.
  - Solo, solved: a stand-in comes in and the room is set up with the
    level's values; the bunker's button (set pressed) drops one coal; the
    coal, put over boiler A's chute, is drawn in by the hopper and lights
    the fire, as does coal put in B's; the feed pump's two pistons are
    each seen out and in; with one lever over the pressure stays at 0,
    with both it climbs; held in the band by working one lever it charges
    the main and solves the dome without the safety valve blowing; tunnel
    1's pump event runs to both doors open, dome 2 is open, the dome dry
    and whole; the gauge is left at 8 lamps and the main at 5.
  - A second entry into the solved room changes nothing; into an
    unsolved one sets it up anew.
  - Failing and getting back: both levers left over, the safety valve
    blows (pressure dumped, charge lost, levers shut, dome unsolved);
    fires left to burn out, the furnaces go dark, the pump's torch goes
    and the pressure falls; coal again and the main charges again; put
    under the band, the charge is gone in 2 s.
  - Duo: with two stand-ins the plates are down and the levers gone; one
    plate stood on for 3 s raises nothing and solves nothing; a coal
    dropped on the other plate does not hold it; both stood on, working
    one, it solves.
  - Duo, one leaving half way: the plates go, the levers come back shut,
    the pressure is kept, and the one left solves it with the levers.
  - The recall button's click taken up by the tick; the values and the
    gauge's green lamps at levels 1 and 10 on a new entry; `reset` from a
    scrambled room (duo form, a stand-in on a plate, coal and arrows in
    the chutes, pressure, charge and fire set, the pump running); a log
    taken from the lectern put back; the room, tunnel 1 and the dome
    left as built, shut and dry, no stand-in behind.
  - The boiler house's machinery (second round): the lamp chaser's four
    lamps each seen lit and unlit over 6 s with nobody in the dome, and
    again at the end; the governor still with nobody in and with fires
    lit but no pressure, making 10 strokes or more through the solo run
    with both pistons seen out and in, more strokes in 4 s at 8 lamps
    than at 2 (the pressure set), a slow beat in the solved room with a
    stand-in there and none once it had left; the bell's power block and
    the bell itself read powered and unpowered through the solo run, 4
    rings or more counted; the governor mid-stroke and the bell's power
    on put back by `reset`.
- **The way in** (`shore.py`: the stages `shore`, `dock` and `lift`),
  built in the world and worked there by its three live checks, nobody
  online (see "The way in: findings" for what that leaves unproved):
  - The shore (`shore`): a dark oak jetty from the landing out towards
    the dock, a sign at its end, two boats beside it; from the world
    spawn a signpost and three lamp posts towards the landing (each
    on the first open ground among five places across the line). Read back: the deck,
    its lamp posts and sign, the place the reset puts players clear,
    each marker of the way with its post.
  - The boats (`shore` and `dock`, two moorings each): one boat at each
    mooring after a reset and still one 150 ticks on; one moved 12
    blocks off, a new one at its mooring; that one killed, another; a
    reset, and the stray is gone and each mooring has one again; no
    item dropped.
  - The dock (`dock`): its 267 blocks and 12 piles read back, the beacon
    lit (`Levels: 1`).
  - The lift (`lift`): its 499 fixed blocks read back; at rest the cage
    at the top, the top gate open and the bottom one shut; the 700
    cells of its column dry. Ridden by an armour stand: sent down by the
    button in the cage (half way the cage is 18 displays and a seat,
    the rider and the counterweight between their ends; the pack counts
    27 blocks; the trip takes 226 ticks, give or take the check's own
    looking; the rider's feet go from y 65 to y 38, the gates and the
    buttons change ends, the travelling parts are gone), sent up
    again, called down empty and called up with a rider; a button where
    the cage stands does nothing; sent off, called back and sent off
    again in one tick, it goes down once; reset from the bottom and
    from on its way. After each
    the column is dry, and at the end the dome is dry and whole but for
    the 9 cells of the shaft.
- **The skeleton** (stage 0):
  - `build_station.py`: the stage list (`STAGES`, in the order of work),
    a stage being a function of a `Context` (the world, the layout, the
    datapack under construction, and the commands a build or a check
    needs). The build asks who is online and refuses if anyone is
    (`FORCE=1` overrides), and forceloads the station's box in commands
    of at most 256 chunks.
  - `fake_client.py`: a fake RCON client (`Recorder`) over a simulated
    box of blocks (`World`). `python build_station.py OUT` records a whole
    build as `OUT.commands` and `OUT.blocks`, to diff one build against
    another.
  - `verify_station.py`: the offline checks (`offline_checks()`), which
    `tests/test_station_example.py` runs, and the live checks.

## The first play-test

25 Nov 2026: the owner, alone, from the shore to a solved Boiler Room.
Everything worked as intended. Asked for:

| Request | State |
| --- | --- |
| The airlock is solid, so the tunnel being pumped out cannot be seen: give it a window | done: every door has a 3 by 3 window of glass (`domes.door_blocks`); not yet seen by a player |
| Can the water be seen going down? | done: the level falls a layer every 3 s from the top over the whole tube, by dim lamplight, then the lamps come on fully towards the next dome, then the doors open (`tunnels.py`); not yet seen by a player |
| More of a show from the pump engine | done in part: a faster stroke, a lamp that flashes with it, a chimney, a puff from each rising head, the klaxon every 4 s. Still 3 by 1 by 4 blocks: a bigger machine needs more of the dome reserved |
| A dome's two-player form must follow who is in that dome, not who is in the game | done (`#form<n>`), checked with stand-ins |
| Rooms busy, not bare: levels, walkways, pipework, machinery that ticks by itself | the Boiler Room: done (see "The Boiler Room: findings", "The boiler house"), not yet seen by a player; the rules for it are in `domes.py` ("Dressing a dome") |
| The lift slow enough to savour, about ten seconds | not started |
| The map wall | not started |

## Not done in stage 1 yet

- The owner's requests above that are not started.
- Nothing of the second round (the window, the falling water, the engine)
  has been seen by a player: see the play-test list.
- The insides of domes 2 to 7: their shells and all the tunnels are
  built (see "The ring's structure"), their rooms are not.

## For the owner's play-test

What RCON cannot stand in for. Each stage adds to the list as it builds.

| Stage | To try | Tried |
| --- | --- | --- |
| 1 | Finding the jetty from the world spawn: the signpost, the lamps through the trees (the straight line crosses an inlet and a pond: is the way round plain?) |  no |
| 1 | The boats: getting into one from the jetty, a new one at the mooring a moment after one is rowed away, one each for two players; that a boat cannot be broken |  no |
| 1 | The row out: the beacon's amber beam seen from the jetty by day and by night (it needs the player's own render distance to reach 12 chunks), about 190 blocks |  no |
| 1 | The dock: coming alongside a landing, stepping out of the boat and climbing out of the water onto it, the stairs, the boats there for the row back |  no |
| 1 | The slow lift (second round) with one player and with two: the buttons by hand; the ride down and up seated in the cage, about 11 s (is it smooth? how do you sit in it? does the cage of displays look like the cage?); the chain paying out, the drum turning, the counterweight passing, the lamps; the gates and the bell |  no |
| 1 | The lift's corner cases with real players: one standing in the doorway is taken along; one who sneaks off the seat in mid ride is put back on it; one who logs off in mid ride and comes back is put into the cage; the cage called away with someone standing in it |  no |
| 1 | Titles and sounds on entering and on solving a dome | no |
| 1 | The pump event through the door's window: is the flooded tunnel visible by the dim lamps, can the water level be seen falling (3 s a layer), do the lamps and the opening doors read well; the same from the far dome's window | no |
| 1 | The engine while it pumps: the strokes, the flashing lamp, the steam and puffs, the klaxon every 4 s (too loud? too often?) | no |
| 1 | The sea seen through the windows of the doors that stay shut (the Pump House's north door, the Gearworks' far door) | no |
| 1 | Two real players and the forms: one in the Boiler Room with the other on the shore or in the Pump House keeps the levers; the second walking in brings the plates at once; one stepping out for under 3 s changes nothing | no |
| 1 | Dying: respawn at the last dome's entrance, with the kit | no |
| 4 | The sloping tunnels walked both ways: the stairs under foot, headroom at each step, the falling water seen through the door from the Maze (looking down the slope) and from the Engine (looking up) | no |
| 3, 4 | The later kits: a shield in the off hand and spectral arrows on first entering the Foundry; the brass helm, cuirass and sabre on first entering the Engine (do they replace what was worn as intended?) | no |
| 3, 4 | Automatons with a player: they attack, do not fight each other, drop nothing, and are gone when everyone leaves their dome | no |
| 1 | The reset buttons with two real players, and a late joiner | no |
| 2 | The Gearworks' pipe in a real hand: places only on the track, the tool breaks only the pipe | no |
| 3, 4 | Whether the fights are fair for a child on Easy | no |
| 4 | Writing a line on the trophy sign for the Wall of Fame | no |
| 1 | The timers' text displays and the bossbar as a player sees them (the rig only read their data back) | no |
| 1 | A bossbar shown to the players in the game and to nobody else (`bossbar set ... players` did nothing with nobody online) | no |
| 1 | What the commands aimed at players do: spawn point, teleport, titles, the on-screen line, sounds, kit, effects (the rig proved only that they parse) | no |
| 1 | Functions changing blocks (a tunnel draining) while the players are far from it | no |
| 2, 4 | Restricted items in adventure mode: the sign places only on its block, the tool breaks only its blocks, and how the tooltip reads | no |
| 1 | Being found by the game: an adventure-mode player on the shore, in a boat on the row out, on the dock and in the station is "in the game" (sees the on-screen line once the run starts); a survival player arriving is put in adventure mode; a creative or spectator player is left alone and not counted in a vote |  no |
| 1 | Two real players: the two-player form appears when the second arrives, and the solo form about 3 s after one logs off or leaves the station |  no |
| 1 | The pump event seen and heard from inside a dome: the klaxon, the pistons, the steam, the lamps coming on down the tunnel, the doors sliding open; and how a flooded, dark tunnel reads through the glass |  no |
| 1 | The kit on first entering a dome (iron armour, sword, bow, 64 arrows, 8 steaks), given once; steak and arrows topped up when the last is used; a late joiner kitted on arrival; a reset taking the kit away |  no |
| 1 | The vote's bossbar as the players see it, counting down, and the "ran out" message |  no |
| 1 | The reset putting every player on the shore, and the recall putting one at the start dome's entrance |  no |
| 1 | Walking the tunnels: the step in and out of each door, headroom, whether 5 wide is right for two |  no |
| 1 | Fire lit beside wood with a player standing by (`fire_spread_radius_around_player 0` was tried only with nobody online) |  no |
| 1 | The master lever pulled by hand: the run starts, its four lamps light by the lever's own redstone, and it will not stay back during a run |  no |
| 1 | The CONFIRM button of the dial and the reset button clicked by hand (an `interaction` entity over each): the click counts for the player who clicked and for nobody else, with two players at the same button; the button is seen to press |  no |
| 1 | The reset cabinet: its button cannot be clicked through the shut door, and can once the door is opened |  no |
| 1 | The dial's LOWER and RAISE buttons by hand: one step a press, the lamps following |  no |
| 1 | Every text display in the Pump House the right way round and readable from where a player stands: the domes' names on the map's frame, the clock board, the dial, the plaques, the arrival point (they were turned to face out from their walls by yaw; only their data was read) |  no |
| 1 | The map wall read by a player: which lamp is which dome, whether "ahead is up" reads naturally, the three states of a lamp told apart, a tunnel's line seen to light |  no |
| 1 | The log on the lectern: it opens, the pages fit, it reads well for a 14 year old; a reset puts a new one back if it was taken |  no |
| 1 | The Pump House as a room: the walk from the lift to the east airlock, whether the arrival pad reads as where the recall brings you, the sealed north door, the light in the map's bay |  no |
| 1 | The new map wall at a glance: does it read as a map (sea, domes as discs of their sizes, pipes, the shore's corner and the row out, "STATION MAP", the blinking "you are here" pin over the Pump House); are the names, the legend and "south is up, east is left" readable from the bay; does glass over copper read as a dome |  no |
| 1 | The Pump House's upper level: the stairs climbed, the gallery and the bridge walked, the view from the look-out by the lift's shaft, the rails (one block high: can be jumped), headroom under the deck and the pipes |  no |
| 1 | Sight lines from the lift's door to the map, the dial, the clock and the master lever with the gallery, tanks and pipes in place; whether the room is light enough under the deck and whether it is now busy enough |  no |
| 1 | The machinery seen and heard: the governor in its cage (pistons about every 4 s; can it be heard from the lectern or the map's bay, and does it annoy), nothing of it clickable through the bars or from the gallery, the bulbs chasing along the pipes, the tanks' sight glasses, the bell every minute and a half (too loud, too often?), copper bulbs' clicks |  no |
| 1 | The Boiler Room played through alone: is it clear from the plaque and the signs what to do, how long does it take, does holding the gauge in the green with one lever feel fair at level 5 (and at 1 and 10) |  no |
| 1 | The Boiler Room with two: the plates appear, each holds a valve only while stood on, both gauges can be seen from both plates, and with three players two are enough |  no |
| 1 | The second player leaving (or logging off) half way through the Boiler Room: the levers come back within a few seconds and the one left can finish. And the other way: a second player joining the game anywhere (the shore too) turns a lone player's levers into plates, since the mode is counted over the whole game: is that wanted? |  no |
| 1 | Coal by hand in adventure mode: the bunker's button drops a coal, it can be picked up, and it goes into a boiler's chute both by throwing it on the hopper and by opening the hopper; the furnaces and the dropper say they are locked |  no |
| 1 | The gauge read by a player: the ten lamps from the door, the bunker, the boilers and both valves; whether the green (oxidised) lamps stand out as the band, lit and unlit; the five lamps of the main in the floor |  no |
| 1 | The safety valve as a player meets it: the title, the bang and the steam, the levers thrown back, and that it reads as "start the main again", not as a lost game |  no |
| 1 | The Boiler Room's sounds, messages and smoke: a fire lighting, the hiss when both valves open, the bell at each lamp of the main, the two hints in chat, smoke from a burning boiler |  no |
| 1 | The feed pump seen working (a torch clock, two repeaters, two pistons) beside boiler B while a fire burns, and stopping when the fires go out |  no |
| 1 | The boiler house as a room: does it read as one (tall boilers, flues and header, the gantry, the bunker, the tanks, the pipe run in the floor), is it busy enough, is anything in the way or ugly from where a player stands |  no |
| 1 | The stoker's gantry: the stairs at its north end found and climbed, the rails, the view down on the gauge and both valves; falling off it costs about a heart |  no |
| 1 | The gauge read through the gantry's grating and rails from the entrance and the bunker (the offline sight check counts grating, bars and pipes as clear) |  no |
| 1 | The machinery seen and heard: the lamp chaser blinking under the gantry's south end, the governor's two pistons quickening as the pressure rises and standing still when it is nil, the bell swinging as each lamp of the main comes on, steam from the header, the stack and the receivers. Is any of it too loud or too busy; is any of it taken for something to press |  no |
| 1 | The recall button at the Boiler Room's door clicked by hand: it takes the player who clicked to the Pump House and nobody else; the click lands on the button from where a player stands |  no |
| 1 | The Boiler Room's plaque, signs and log: readable, the right way round, the log's three pages fit; a log taken from the lectern is replaced within a second |  no |
| 1 | Leaving the Boiler Room unsolved and coming back: it has put itself right (fires out, gauge dark, coal gone from the chutes). Is losing the fire by stepping back into the tunnel too harsh? |  no |

## Decisions and findings

### Layout

The site is the deep ocean basin north east of the world spawn
(-32, 63, 81). Sea level is 63: the top layer of water is y 62. The
positions are in `station_layout.py`; the plan is `layout_plan.png`.

The eight domes (the start, six, the boss) stand on a rectangular ring,
four by two, so every tunnel runs straight along x or z. A dome is a half
sphere: its top is at floor y + radius.

| # | Dome | Centre x, z | Diameter | Floor y | Top y | Water over the top | Sea floor under it (median y) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | The Pump House (start) | 63, -109 | 48 | 37 | 61 | 1 | 41 |
| 1 | Boiler Room | 129, -109 | 32 | 37 | 53 | 9 | 38 |
| 2 | Gearworks | 199, -109 | 48 | 37 | 61 | 1 | 37 |
| 3 | Flooded Dome | 271, -109 | 48 | 37 | 61 | 1 | 39 |
| 4 | Foundry | 271, -189 | 48 | 37 | 61 | 1 | 37 |
| 5 | Signal Room | 207, -189 | 32 | 37 | 53 | 9 | 37 |
| 6 | Clockwork Maze | 143, -189 | 48 | 37 | 61 | 1 | 36 |
| 7 | The Engine (boss) | 63, -189 | 64 | 29 | 61 | 1 | 42 |

| Tunnel | From, to | Length (shell to shell) | Floor |
| --- | --- | --- | --- |
| 0 | start to Boiler Room | 26 | level, y 37 |
| 1 | Boiler Room to Gearworks | 30 | level |
| 2 | Gearworks to Flooded Dome | 24 | level |
| 3 | Flooded Dome to Foundry | 32 | level |
| 4 | Foundry to Signal Room | 24 | level |
| 5 | Signal Room to Clockwork Maze | 24 | level |
| 6 | Clockwork Maze to boss | 24 | falls 8, y 37 to 29 |
| 7 | boss to start | 24 | rises 8, y 29 to 37 |

- Shore landing: (-18, 63, 66), a grass block at the tip of the headland
  21 blocks north east of the spawn, the sea just north and east of it.
- Dock: (63, 64, -109), directly above the start dome. The row from the
  shore is 193 blocks, 99% of it over water, never shallower than 7.
- Lift: straight down at x 63, z -109, from y 64 to the start dome's floor
  at y 37.
- The station's box (`BOUNDS`): (23, 21, -229) to (303, 72, -77).

Awkward points of the site:

- The basin is shallow for a "deep" ocean: its floor is at y 36 to 42,
  20 to 26 blocks of water, and only 9% of the surveyed area is 25 deep
  or more. So the 48 and 64 domes have their tops one block under the
  surface, and none breaks it. The boss dome's floor is dug 13 below the
  sea floor there to manage that.
- Ravines cross the basin. About 9% of the Foundry's footprint is ravine
  (down to y 14), the boss dome has one deep hole under it, the Clockwork
  Maze and the Gearworks have small ones, and tunnels 3 and 5 cross
  ravines (sea floor y 30 and y 18 under them). All need foundations or
  filling.
- The west end is the rim of the basin: the sea floor under the start
  dome is y 38 to 52 and under the boss y 38 to 49, so both sit in the
  sea floor rather than on it (the start dome by 4).
- An abandoned mineshaft runs under much of the site, its timbers at y 8
  to 34, three or more below the floors at y 37; none is under the boss
  dome. It has two spawners, at (188, 23, -102) and (197, 22, -137)
  (`MINESHAFT_SPAWNERS`). The first is within a spawner's 16 block reach
  of the Gearworks floor: the build should remove both.
- No monument, wreck or ruin is in the station's box. The nearest: an
  ocean ruin at about (0, -192), its bricks at x -16 to -1, some 30 blocks
  west of the boss dome's shell; a shipwreck at (64, -368); a monument at
  (176, -880).
- Bubble columns (they sink boats) reach the surface in 12 columns of the
  survey, none on the row to the dock. One, at (191, -177), is inside the
  box but under no dome.
- The plan says "all nine domes" in stage 0; its list has eight (0 to 7),
  and eight are laid out.

To redo it:

- `STATION_WORLD=<the server's world folder> mciwb run survey_site.py
  --server HOST --port PORT` reads every column of the area from the
  world's files (seconds) and writes `site_survey.npz`. Without
  `STATION_WORLD` it samples one column in four each way over RCON, and
  finds no structures or bubble columns. `STATION_SURVEY="X1 Z1 X2 Z2"`
  sets the area (default: 576 x 576 round the basin; the saved survey is
  x -256 to 447, z -320 to 255). It forceloads 256 chunks at a time,
  releases them in a `finally`, leaves chunks that were forceloaded
  before, and refuses to run with a player online.
- `python render_layout.py` draws `layout_plan.png` from the layout and
  the saved survey, and prints what the survey says about the sea floor
  under each dome and tunnel. It needs no server.
- `python station_layout.py` prints the layout and runs `check_layout()`.

Verified: `check_layout()` finds no problems (tunnels 20 to 40, along x
or z, ending on the shells, no domes overlapping, the ring closed). The
figures above come from the full survey. The RCON survey was run on a
patch of 2 x 2 chunks and matched the survey from the files exactly. The
shore landing's column was read from the world's files (grass at y 63,
air above). `check_site()` finds no problems for this site; with the
anchor moved it reports land under domes, tops above the surface, or a
box outside the survey, as it should.

Not verified:

- Nothing is built, and nobody has walked or rowed the route.
- That the survey's own `tick sprint` wakes an empty, paused server: it
  did by hand, but the server was already awake for the runs made after
  that was added.
- Land heights under trees: leaves and logs count as ground on land. The
  sea is not affected.
- The structure search is a search for tell-tale block names (planks,
  fences, prismarine, stone bricks, chests, spawners) from y 0 to 127,
  at most 2000 blocks of a kind per batch of chunks: a structure made of
  other blocks would be missed.

Putting the station somewhere else (another world, or another part of
this sea). Every position is an offset from one anchor, so the layout
moves as a whole:

1. Survey the sea there with `survey_site.py` (above); it writes
   `site_survey.npz`.
2. Set the site block at the top of `station_layout.py`, and nothing
   else: `ANCHOR` (the x, z of the middle of the start dome),
   `BASE_FLOOR_Y` (the y of its floor), `SEA_LEVEL`, `SPAWN`,
   `SHORE_LANDING` and the site's hazards (`MINESHAFT_SPAWNERS`, empty if
   there are none). The shape block (`RING`: each dome's offset from the
   anchor, its size, how far its floor is sunk) stays as it is.
3. Run `python station_layout.py`: it prints the layout, runs
   `check_layout()` and then `check_site()` against the survey. The site
   check fails if a dome's footprint has land in it, a dome's top is above
   the surface or its floor more than 3 above the sea floor, a tunnel
   crosses land, the shore landing is not the top of the ground, or the
   row to the dock crosses land or a bubble column. Its notes say how far
   each dome's top is below the surface, how much of each dome and tunnel
   is over a ravine, and what structure blocks lie under the box. The
   same check is `site` in `verify_station.py`'s offline checks (skipped
   if there is no survey file).
4. Run `python render_layout.py` and read the picture.

What that does not do: choose the anchor for you (the search that chose
this one was done by hand and is not in the example), or change the
shape to fit a sea of another size; and the site check knows only what
the survey holds.

### Datapack: format and delivery

Proved by `rig_mechanisms.py` check 1 on the 26.3 server, unless marked
"by hand" (a one-off probe over RCON, not in the rig).

- **Format.** `pack.mcmeta` is
  `{"pack":{"description":...,"min_format":121,"max_format":121}}`. 121 is
  `pack_version.data_major` in the server jar's `version.json`. By hand:
  with `pack_format` alone the pack still loads but each scan of the
  folder logs a warning and a stack trace; a wrong number (999) loaded too.
- **Folders.** `data/<namespace>/function/` and
  `data/minecraft/tags/function/{load,tick}.json`, singular. By hand: the
  plural `functions` is ignored, silently.
- **Delivery.** The build writes the pack's folder straight into the
  world's `datapacks` folder (`STATION_DATAPACKS_DIR`), then `reload`. So
  the build must run where the world's files can be written. A new folder
  is found and enabled by `reload` alone (1a). By hand: one disabled with
  `datapack disable` stays disabled, and `datapack.install` enables it.
- **Replacing.** `Pack.write` removes `<datapacks>/<pack name>` and writes
  it again, touching nothing else; it refuses a folder with no
  `pack.mcmeta`, and a link. A rebuilt pack takes over on `reload` and its
  load function runs again (1j).
- **Seeing that it loaded.** The pack's own `_load` function writes a
  stamp to the storage `<namespace>:pack`; `install` waits for this
  build's stamp.
- **A bad line is silent.** The game loads the rest of the pack and says
  nothing over RCON: the function is left out, and the whole
  `minecraft:tick` tag with it if the tag names it. Only the server's log
  tells (`Failed to load function`, `Couldn't load tag`). `install` reads
  `logs/latest.log` beside the world and raises `PackError` (1k); where it
  cannot find the log it cannot tell.
- **Limits.** `fill` refuses over 32768 blocks (the game rule
  `max_block_modifications`); a function runs at most 65536 commands (the
  game rule `max_command_sequence_length`); `datapack.py` refuses both. The
  rig's pack of 24 functions and 83,549 lines loaded and ran.

What the skeleton does with it: the `datapack` stage writes the pack to
the folder named by `STATION_DATAPACKS_DIR` and reloads; with no folder
named it installs nothing and says so in capitals. The pack is made in
full by `build_station.new_pack` whichever stages run, so a stage run
alone never installs half a pack: a dome's functions are to be added
there (from the layout), not by the dome's build stage.

### Forceload

- **Decision.** From stage 1 the built game keeps the station's box
  forceloaded for good: the one deliberate forceload. A function's block
  change fails in an unloaded chunk (rig check 1i: `setblock` from a
  function, success 0 in an unloaded chunk, 1 in a loaded one), and the
  box is about 18 x 10 chunks, longer than the server's simulation
  distance of 10 chunks. The build adds it once something is built; the
  rig and the survey still release theirs. Whether it is really needed
  with players present is not proved: nothing has been tried with a
  player.
- **Waiting for a forceloaded chunk** (a probe by hand on the 26.3
  server, one fresh chunk each time, nobody online):
  - On a paused server (game time frozen) `execute if block x 0 z
    minecraft:air` answered for the chunk in the first poll after
    `forceload add`, with no tick ("That position is not loaded" before).
    `execute if loaded x 0 z` stayed "Test failed" for the whole 15 s
    watched, and passed within 0.25 s of one `tick sprint 1`.
  - On a running server `if block` answered at once and `if loaded`
    passed within 0.5 s.
  - So `if block` is the form that works whether or not the game ticks,
    and says the blocks are there. `if loaded` is reliable only if the
    game is made to tick first (`tick sprint`), and a wait on it with no
    sprint never ends on a paused server. Blocks can be read and set in a
    forceloaded chunk of a paused server with no sprint; what `if loaded`
    reports (the chunk ticking) needs the tick. Not tried: an area of many
    chunks, where loading may take longer than one poll.

**From stage 1 the box is forceloaded for good.** The build adds it and
no longer releases it; the live checks add it if it is missing and leave
it; `verify_station.py`'s `forceloaded` check reports it as expected (198
chunks) and lists any other forceloaded chunk (one, at chunk -2, 5, which
was there before the station). A paused server (nobody online) ticks
nothing in it. The paragraph below is how stage 0 did it, kept as
history.

What the skeleton did: the build, and the live checks when there are
any, forceload the station's whole box (`station_layout.BOUNDS`: the
dock, the domes and the tunnels, not the shore, so the `shore` stage will
have to load its own ground) for as long as they run and
release it afterwards, leaving forceloaded the chunks that were so
before. If the decision is to keep an area loaded for the game, a stage
will add it and the build's release will leave it alone only on the
next run (it reads what is forceloaded at its start): the release must
then be taught to keep that area on the run that adds it too.

### Mechanisms

From the rig, `rig_mechanisms.py` (45 checks passed on the 26.3 server,
nobody online; numbered as there). It builds in a deep cold ocean far from
the game, copies the sea aside first and puts it back.

1. **Functions.** The load function runs once per `reload`; the tick
   function once per game tick (score +41 for 41 ticks). `function ns:name`
   works. Macros work: a `$` line with `$(value)`, called with
   `function ns:f {value:7}` or `function ns:f with storage ns:store path`.
   `schedule function ns:f 60t` runs later, not at once. Box selectors
   `@e[...,x=,y=,z=,dx=,dy=,dz=]` count what is inside
   (`datapack.box_selector`); `@a[gamemode=adventure,...]` parses.
   - **Ticking with nobody online.** The server stops ticking about 60 s
     after the last activity (game time freezes; reading over RCON does
     not wake it). A `tick sprint` wakes it, and it then runs at 20 ticks
     a second for about a minute: a check must not assume the game stands
     still between its commands, nor that it moves. `tick sprint N` returns
     at once (200 ticks take under 0.1 s) and a second one sent too soon
     interrupts the first: wait on `time query gametime`.
2. **Tunnel.** A glass tube, 5 x 5 inside and 24 long, in the sea. One
   function per state ("the first d sections are dry"), each writing the
   whole tube in one tick, so any state can follow any other and state 0
   is the reset: `fill <wet> water replace water` (flowing back to
   sources), `... replace air`, `... replace barrier`;
   `fill <dry> air replace water`, `... replace barrier`; then a bulkhead
   of `barrier` on the first slice of the flooded part. Drain and refill
   are chains of `schedule function`, 10 ticks apart. Read back: part
   drained 300 air, 275 sources, 25 barrier, no flowing water; drained 600
   air, the same 150 ticks on with the sea beyond its end; refilled 600
   sources. With no bulkhead a drained section held 40 flowing water 60
   ticks on. The `replace` filters leave waterlogged blocks alone: put
   nothing waterlogged in a tunnel.
3. **Dome.** 32 across, on the sea bed, its top under water. Placing the
   floor and shell and then clearing the inside to air row by row leaks if
   the game ticks meanwhile (3472 of 7660 cells wet 40 ticks later, with 10
   ticks let pass half way): the water left runs into the rows already
   cleared. What works whatever the game does: fill the whole dome solid
   glass, then hollow it. Then all 7660 cells are air, none wet, and the
   same 200 ticks on.
   - To find water or a waterlogged block at a place:
     `execute positioned x y z if predicate {type:"minecraft:location_check",predicate:{fluid:{fluids:"#minecraft:water"}}}`
     (the key is `type`, not `condition`). A waterlogged slab inside
     wetted 74 cells in 40 ticks; they dried within 100 ticks of its removal.
   - Kelp cut by the shell drops items (1 to 12 a run): kill them. The
     site had no seagrass, sand or gravel, and the dome had a laid floor:
     falling sand and gravel were not exercised.
4. **Timer.** `summon minecraft:text_display x y z {Tags:[...],text:"--:--",billboard:"center"}`,
   rewritten each second (a tick function counting to 20) by a macro
   line: `$data modify entity @e[type=minecraft:text_display,tag=...,limit=1] text set value "$(m):$(t)$(o)"`
   (`datapack.mmss_lines` does the sums). `data get ... text` read
   "12:35", "12:36", "12:37", and "1:00" after 59 + 1. Minutes are not
   padded.
5. **Bossbars.** `bossbar add ns:id "Reset"`,
   `bossbar set ns:id name {text:"Reset: 1 of 2",color:"gold"}`, `max 60`,
   `value 45`, `color yellow`, `style notched_6`, `visible false`, read
   back with `bossbar get` and `bossbar list`, removed with
   `bossbar remove`. From a function:
   `execute store result bossbar ns:id value run scoreboard players get ...`.
   `set ... players` could not be tried (nobody online: "Nothing changed").
6. **Restricted items** (stored and read back; no hand to hold them).
   `minecraft:oak_sign[minecraft:can_place_on={blocks:"minecraft:gold_block"}]`
   and
   `minecraft:iron_pickaxe[minecraft:can_break={blocks:["minecraft:cut_copper","minecraft:waxed_cut_copper"]},minecraft:tooltip_display={hidden_components:["minecraft:can_break"]}]`.
   `blocks` also takes a `#tag` (by hand). The old `{predicates:[...]}` is
   refused. As NBT on a summoned item:
   `Item:{id:...,count:1,components:{"minecraft:can_place_on":{blocks:...}}}`.
   `give @a[...] <item>` parses.
7. **Boat.** `minecraft:boat` is gone: `minecraft:oak_boat` is a type of
   its own, and the tag `#minecraft:boat` holds the boats and the bamboo
   raft (not chest boats). Kept at a marker by
   `execute at @e[type=minecraft:marker,tag=...] unless entity @e[type=#minecraft:boat,distance=..4] run summon minecraft:oak_boat ~ ~ ~ {Tags:[...]}`:
   one boat, still one 150 ticks on; moved 30 blocks away or killed, a new
   one. Boats taken pile up: the reset must kill them by tag.
8. **Names in 26.3.**
   - Game rules are snake_case and the old names are refused:
     `keep_inventory`, `mob_griefing`, `spawn_monsters` (monsters only;
     `spawn_mobs` is all mobs), `fire_spread_radius_around_player` (a
     number, 128 now; the value for "off" not tried, as the rig changes no
     rule), `advance_time`, `advance_weather`, `immediate_respawn`.
   - The 28 block names of the plan's look exist. `minecraft:chain` does
     not: `iron_chain`, `copper_chain`.
   - Mobs: armour is `equipment:{head:{id:...,count:1},mainhand:{...}}`
     with `drop_chances:{head:0f,...}`; `CustomName:"Automaton"`; a ravager
     with `Passengers:[{id:"minecraft:vindicator",...}]`. `copper_helmet`
     exists.
   - These parse with a box selector, and did nothing with nobody online:
     `spawnpoint`, `tp`, `gamemode`, `title` (title, and actionbar with a
     score), `playsound`, `clear`, `tag`, `effect give`,
     `item replace entity`, `particle`, and
     `execute as ... run attribute @s minecraft:max_health base set 20`
     (`attribute` takes one entity).

### Stage 1 core: findings

Each was met on the 26.3 server while building or checking the core.

- **Fire spread.** `fire_spread_radius_around_player 0` turns it off.
  Tried with real fire (a block of netherrack alight under 17 blocks of
  wool, in the forceloaded box, nobody online, 2400 ticks each): at 0 all
  17 left, twice; at -1 none left; at 128 (the default) all 17 left, there
  being no player within 128. -1 is the least value the rule takes, and
  means everywhere. Not tried with a player standing by the fire.
- **Building.** A dome is filled solid and hollowed with boxes
  (`domes.boxes`), about 440 commands for a 48 dome where rows take 970.
  A whole build of three shells and two tunnels is some 4000 commands and
  takes 2 s over a local RCON connection.
- **The site.** Tunnels 0 and 1 run half in the sea floor (it is at y 39
  to 42 along them, their floors at y 37): the tubes are whole, but their
  lower walls are buried, and their piers found ground at once. The start
  dome stands in sea floor up to y 52 on its west side. Making the dome
  solid glass first replaces all of that, and nothing fell in: no falling
  block or item was in a shell afterwards. The Gearworks' build killed 2
  dropped items (cut kelp).
- **Names and syntax, each loaded in the pack or sent over RCON.**
  - `fill ... replace #minecraft:replaceable` takes the block tag: water,
    air, lava and small plants, but not kelp (`kelp`, `kelp_plant`).
  - Light at a place: `execute positioned x y z if predicate
    {type:"minecraft:location_check",predicate:{light:{light:{min:8}}}}`.
  - `spawnpoint <targets> x y z <yaw> <pitch>`: the angle is two numbers
    (one alone is refused).
  - `execute ... run return 0` stops a function; `execute as @a[...]
    unless items entity @s container.* <item or #tag>` tests an inventory;
    `bossbar set <id> players` with no selector empties the bar.
  - `bossbar get <id> visible` answers "is currently visible" or "is
    currently hidden"; `... value`, "has a value of N"; the bar's name is
    in square brackets in every reply.
  - A waxed copper bulb set with `[lit=true]` stays lit (read 150 ticks
    on), as does a sticky piston's load through the engine's strokes.
  - A macro function can pass its arguments on:
    `$... run function station:vote/open {kind:2,value:$(level),label:"Difficulty $(level)"}`.
- **`retry_command` gives back the part of the reply that matched**, not
  the whole reply. `Context.cmd(command, expect)` therefore wraps the
  pattern to match everything; before that, counts and bossbar replies
  read wrong.
- **A check function that does not run reads as "nothing wrong"** (the
  score stays 0). Each of the domes' check functions adds one to `#ran`
  as its last line and the check counts them, so a function that is
  missing, or cut short by the limit of 65536 commands, is a failure.

### Core, fourth round: stubs, shared helpers, and the stage 1 review

Built for the six rooms to come, each proved by the check named (run in
the whole verify, alone on the server, nobody online):

- **Stub domes** (`ring`). Domes 2 to 7 each have a BYPASS lever on a
  brass post by the exit. One stand-in walked the ring from the master
  lever to the win: through each tunnel (in no dome on the way), into
  each dome, the Boiler Room's `solved` called and each stub's lever set
  as a hand would leave it, every tunnel's pump event waited out, the
  Pump House's far door open at the end; then the reset, every lever
  back. Not proved: that a player can walk it, or pull a lever.
- **Fights** (`fights`): the difficulty read into `#difficulty` (Easy is
  1; `execute store result score ... run difficulty` works; that
  Peaceful reads 0 is taken from the game's numbering, not tried, since
  the difficulty stays Easy); waves cast only at a spawn point with a
  player by it, 3 Stokers and 1 Riveter of the 2 asked (its kind's cap)
  to a cap of 4, the gap scaled by the level, refilled after a kill,
  none cast with nobody by a point; an automaton moved into a tunnel
  back on the leash, and all back inside a fence; a death (a stand-in's
  `st.died` set by hand) answered within 3 ticks: the automaton by the
  entrance gone, the one across the dome left, the score back to 0; an
  arrow and an orb swept; a dome's bossbar hidden, shown at a value,
  hidden.
- **Fittings** (`fittings`): the torch clock built and left to run 120
  ticks: each of its four lamps seen lit and dark and both plain pistons
  seen out and in; a gauge of three lamps right at five values; a lever
  put back, left alone when not held and thrown back when held; a
  button answered once for a press read twice, and let go; a blackstone
  plate that reads "held" with a stand-in on it and not with another
  armour stand on it or nothing; a post's label; a display rewritten and
  turned; a lent item told from the same item not lent; a hint not said
  at 30 ticks, put off by progress, said once at its time.
- **Offline** (the unit test): the room checks find a wall across a
  walk, stone but not glass in a sight line, an unlisted input, one not
  on gold, one with no sign, a piston touching an input's block, a
  block that means something in another dome, a screen before the
  outgoing door's window (and pass it once the dome has said so).

From the review of stage 1 (each finding checked in the code first):

- **A player offline when the game was reset** came back sealed in a
  shut dome with a stale kit, and then counted in every vote. Now the
  scan sends anyone whose kit is from an earlier run to the shore with
  nothing (`players/stale`). Aimed at `@a`: loaded, not exercised.
- **The recall skipped a dome's `leave` hook** (the start dome is first
  in the scan, so the player was "in" it before the dome they left was
  looked at). Every dome's leavers are now found before any dome's
  comers-in; a player going out of the game from a dome, and the reset,
  call `leave` too.
- **A dome emptied half a second after its last player stepped out**, and
  its room was put back. It is now empty 3 s after (`EMPTY_AFTER`), as a
  form falls back; the checks wait that long (`game_checks.EMPTY`).
- **The live checks reset a parked run.** They now refuse while `#run`
  is 1 unless `FORCE=1`.
- **The pack was 15 MB, nearly all of it the checks' functions** (a line
  or five for every cell). They are now a line a row, calling shared row
  functions: 2.4 MB, 32,000 lines where there were 330,000. The checks
  read the same counts.
- The `datapack` stage now says whether the server's log was read (it
  is, on this server): only the log says that a line did not parse.
- A click on any recall post is answered by the core; a module places
  the post and nothing more.

### The ring's structure (core, third round)

Built in the world and checked there, nobody online, each check run by
itself while other work went on in domes 0 to 2. The whole verify has
since been run alone on the server, from a rebuild of every stage, and
again after the fourth round (below):

- **The shells of domes 3 to 7** (`shell_3` ... `shell_7`, all passed):
  nothing wet inside, no hole, nothing but ground under any floor cell,
  the sea over the top, light of 8 or more at head height, no item and
  no falling block. The Engine's dome is 65 across with 64,911 cells
  inside, its floor 8 below the others'; its build is 1 s. The Clockwork
  Maze's build killed 3 dropped items. The foundations filled what the
  survey found under the Foundry, the Maze and the Engine: the check
  reads the cell under every floor cell.
- **Tunnels 2 to 7** (`tunnel_2` ... `tunnel_7`, all passed), each read
  whole at every state of its drain, as tunnels 0 and 1 were. The level
  ones: 4 layers. The two that slope (6, the Maze down to the Engine; 7,
  the Engine up to the Pump House's north door): 11 layers each, by y,
  read (0, 0), (1, 0) ... (11, 0) then the lamps (11, 1) ... (11, 6):
  at every one all sources below the surface, all air above, no flowing
  water, no air under water. A layer goes every 21 ticks there, so the
  whole event is about as long as a level tunnel's.
- **What a player walks on in a sloping tunnel**: 3 blocks of polished
  deepslate floor, then a row of polished deepslate stairs 5 wide, eight
  times over (the floor climbs 8 in 24). The stairs stand where the
  lowest water of their slice would be, never waterlogged; all 40 of each
  tunnel read back as stairs after the drain and the refill. Nobody has
  walked them.
- **Piers.** Read back by hand: under tunnel 3, 2 to 9 blocks of pier a
  column; under tunnel 5, 9 to 18; under tunnel 6, 8 to 17; none ran the
  whole 25 blocks to an empty cell, so every pier stands on ground.
  Tunnels 2 and 4 lie in the sea floor and needed none.
- **The win.** `dome/7/solved` opens tunnel 7 (the Pump House's north
  door with it) and calls `run/win`. Checked by `progress` in the second
  round with tunnel 7 a stub; not run again with the built tunnel, since
  that check resets the game.
- **Automatons** (`automatons`, passed): a zombie summoned by
  `automatons.summon` and dressed at 150% health and 50% damage read
  max health 30, health 30, attack damage 1.5, reinforcements 0, not a
  baby, picks nothing up, persistent, on the team, in its copper helmet,
  named; killed, it dropped nothing (the pack's own empty loot table);
  the count 2 solo, 3 duo, 6 for three players at 160%; three skeletons
  gone a scan after the dome emptied. Not proved: that automatons leave
  each other alone and attack a player.
- **Restricted items** (`restricted_items`, passed): the three items read
  back from a barrel with their rules. Not in a hand.
- The kits for the Foundry and the Engine loaded without error; nobody
  has been given one.

### Core, second round: findings

- **`f"{x}.5"` is a block off where x is negative**: "-109.5" is the
  middle of cell -110, not of cell -109. The core had it in four places,
  all of them positions of entities or effects, none of blocks:
  `domes.sphere` (the middle of every dome's "who is in it" sphere was a
  block north of the floor's middle), the stand-ins of `game_checks`
  (put a block north of the entrance spot and of the tunnel's middle),
  and the engine's steam. All now come from `domes.middle(cell)`.
  **The glass was never affected**: every block of a shell, a floor, a
  door and a tunnel is placed by whole-number cells worked out from the
  layout, and the offline build's blocks before and after the correction
  differ only by the doors' windows and the engine's two new blocks. The
  correction moves each dome's sphere one block south (z + 1), so a
  player standing in the last block of a tunnel at a north or south
  mouth is counted in or out a block differently; nothing was rebuilt
  for it. `shore.py` has the same form in five places (the boat's
  marker, the boats' selectors, the lift's riders): left for its owner.
- **A top-down drain needs no bulkhead.** Sources with air over them stay
  put; water flows only into an empty cell beside or under it, and a
  whole layer of sources bounded by glass, brass and more sources has
  none. Read in the world at every layer state of both tunnels: every
  cell of the layers below a source (`water` = `source`), every cell
  above air, none wet above, no air under water, and the same 100 ticks
  on for a half-drained tube set straight after the dry state and after
  the flooded one. The fills are `water replace water` (which makes any
  flowing water a source again) and `water replace air` for the wet
  layers, `air replace water` for the dry: three a box, and a layer of a
  level tunnel is one or two boxes. The window (glass) holds as the
  brass does: both domes read dry with the tunnel flooded behind it.
  For a sloping tunnel the layers must go by y, not by height above the
  floor, or water would stand beside air at each step and run downhill:
  checked offline only.
- **Light for the event.** A lit waxed weathered copper bulb gives light
  8 (oxidized 4, exposed 12, plain 15) and stays lit when set with
  `[lit=true]`; the tunnel's lamps are that while the water falls, and
  plain bulbs after. Whether 8 is enough to see the water by through the
  window is for the play-test.
- **A whole build in the list's order used to wipe the lift**: `lift` came
  before `start_dome`, whose shell stage clears the dome, the shaft's
  lower part with it (385 of the lift's 499 blocks, by its own check).
  `lift` now comes between `start_dome` and `start_dome_inside`.
- **A sound's name can trip the names check**: `item.bucket.fill` in a
  `playsound` line reads as a `fill` command to the check's pattern.
  Another sound is used.

### The Pump House: findings

Each met on the 26.3 server while building or checking `dome_start.py`.

- **Who pressed a button.** A vote is counted by player, so the two
  voting buttons (the dial's CONFIRM, the reset) must run their function
  as the player who used them. A real button tells a function only that
  it is pressed, and "the nearest player" is the wrong one as soon as two
  stand at the same button to confirm. So over each is an `interaction`
  entity filling the button's cell
  (`summon minecraft:interaction x y z {width:1f,height:1f,response:1b}`),
  which records the last player to right-click it in its `interaction`
  data; the dome's tick finds one that has it, runs
  `execute on target run function ...` (as that player), and removes the
  data. The button under it is set pressed for show and let go half a
  second later. The lever and the dial's LOWER and RAISE buttons are
  real blocks that the tick reads: what they do does not depend on who
  used them.
  - Proved: the summon; a click written into the entity by command is
    taken up by the tick and cleared, and casts no vote when its player
    is nobody; the vote functions run as each of two stand-ins.
  - Not proved: `on target` reaching a real player. It gives nothing for
    an entity that is not a player (an armour stand's UUID written into
    `interaction.player`: the command ran as nobody), so a stand-in
    cannot show it. Nor that a click meant for the button always lands on
    the entity. Both are in the play-test list.
- **A lever or button set by command tells nothing round it.**
  `setblock ... lever[powered=true]` over a lever that is off leaves the
  redstone lamps beside its block dark until something else updates
  them (then they light: the power is real). Taking the lever out
  (`setblock ... air`) while it is on does tell them, and they go out.
  So the reset takes the lever out and puts it back, and the functions
  that set it over set the lamps too. A button set pressed by command is
  set back by command (whether it would let itself go was not tried). A
  hand on the lever or a button does all of this by itself: not seen
  yet.
- **A book on a lectern.**
  `setblock x y z minecraft:lectern[facing=south,has_book=true]{Book:{id:"minecraft:written_book",count:1,components:{"minecraft:written_book_content":{title:"...",author:"...",pages:["...","..."]}}}}`:
  the pages are plain strings (or text components), `\n` a new line;
  read back, each is `{raw:"..."}` and the title `{raw:"..."}`. A page
  can be added with
  `data modify block x y z Book.components."minecraft:written_book_content".pages append value "..."`,
  which keeps each command of the build inside RCON's length. Putting a
  lectern over a lectern is done as air first, then the lectern: no book
  was dropped by either (no item in the dome after a reset).
- **Text displays** on a wall:
  `{Rotation:[<yaw>f,0f],billboard:"fixed",background:0,brightness:{sky:15,block:15},text:{text:"...",color:"gold"},transformation:{translation:[0f,0f,0f],scale:[2f,2f,2f],left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]}}`
  summons and reads back; `text` takes a list of components too. The yaw
  is that of the way the wall faces (0 south, 90 west, 180 north, -90
  east): taken from how entities face, not seen.
- **Names** used here and accepted by `setblock`: the three froglights,
  `gilded_blackstone`, `waxed_copper_door`, `waxed_lightning_rod`,
  `polished_blackstone_button`, `redstone_lamp`, `lectern`, `lever`.
- **Two live checks at once spoil each other**: one check's stand-ins are
  players in the other's votes, and both reset the game. Run one at a
  time.
- **Second round: the map.** The shore is 190 blocks from the dock and
  the ring is 208 by 80: at one scale with the shore the domes would be
  a block or two each. So the ring is drawn to scale (12.75 blocks to a
  block of the wall here; `map_cells` finds the largest scale that
  fits with every tunnel at least a block long) and the shore is a
  corner of land in the direction it lies in, marked "a long row". The
  dock is over the Pump House, so one pin is the dock, the lift and
  "you are here". The wall moved two blocks into the room to be 13
  high: the dome's curve allows no more at 25 wide.
- **Second round: machinery.** The governor is a ring of ten repeaters
  (delay 4) and one redstone torch on a block, placed by `setblock`,
  torch last: it started by itself and ran through two resets (about
  8 s a turn). A repeater's `facing` is the side its signal comes in
  by. A sticky piston beside the block under a redstone wire, and one
  beside the block the last repeater powers, both follow the clock.
  Copper bars set with their `north`/`south`/... states keep them
  until a neighbour changes, then join themselves to it (a piston's
  block, the lift's door): the check reads bars by name. A bell cannot
  be rung by command: the block hangs out of reach and a `playsound`
  rings. The pistons are 20 blocks or more from the lectern and the
  map's bay, beyond a piston's 16 blocks of sound: not heard by anyone
  yet.
- **`render_start.py`** draws the room's plan with no server (blocks
  only: no text, light or glass), enough to see the shape of it; that
  picture and the block read-back are all that has been seen of the
  second round.
- **The sea over the dome's top.** `domes.check_shell` wants water over
  the top of a dome, and the lift's shaft is there now: the Pump House's
  check leaves that one finding out when the top cell is a registered
  opening.

### The Boiler Room: findings

The puzzle (`dome_boiler.py`'s docstring has the functions). Coal from
the bunker (a button and a dropper) goes into the chute (a hopper) on
each of two boilers and lights its fire; with both steam valves open the
pressure climbs a gauge of ten lamps in the middle of the dome, and
otherwise leaks away; held in the green lamps it charges the main, five
lamps in the floor towards the next tunnel, and the fifth solves the
dome. At the tenth lamp of the gauge the safety valve blows: the
pressure is dumped, the charge lost, the levers thrown back. Solo each
valve has a lever; duo each has a plate that must be stood on.

| At level | Band (lamps) | Leak a second | Hold | A coal burns |
| --- | --- | --- | --- | --- |
| 1 | 6 to 8 | 72 | 7.75 s | 42 s |
| 5 | 7 to 8 | 120 | 15 s | 30 s |
| 10 | 8 | 180 | 24 s | 15 s |

A lamp is 1000 of pressure; two fires raise 320 a second, one 160. The
values are read from the core's `#diff.*` when an unsolved room is first
entered (`dome_boiler.scaled` is the same sum in Python).

Each of these was met on the 26.3 server while building or checking it.

- **A sign's text**:
  `minecraft:bamboo_wall_sign[facing=west]{is_waxed:1b,front_text:{messages:["",{text:"BOILER ROOM",bold:true},"",""]}}`;
  rewritten in place with
  `data merge block x y z {front_text:{messages:[...]}}` (a `setblock`
  of the same block and state changes nothing, its NBT included).
- **A block nobody can open**: `{lock:{items:"minecraft:barrier"}}` on a
  furnace or a dropper (the lock is an item to be held). A hopper still
  feeds a locked block, so the chutes point at a plain block. Stored and
  read back; what a player sees on clicking one is not seen.
- **One item out of a slot**:
  `item modify block x y z container.0 {type:"minecraft:set_count",count:-1,add:true}`.
  The modifier's key is `type`; `function` is refused. Guard it with
  `execute if items block x y z container.0 minecraft:coal`, or it takes
  one of whatever is there.
- **A furnace set `lit=true` by `setblock` stays lit** with nothing
  burning in it: both read lit on the second entry into the solved room,
  15 s of game time and more after the function last set them.
- **The recall button** uses the Pump House's method: an `interaction`
  entity over a real button, the recall run `on target`. Here it is 0.6
  across and set back against the button's block, not the whole cell.
  Proved and not proved as there: the click written by command is taken
  up and cleared; `on target` reaching a real player is not.
- **A button set pressed by command does not work a dropper** beside the
  button's block: only the button's own neighbours are told. The power
  is real: once the dropper is told (the check sets and clears a block
  above it) it drops one coal. A hand on the button tells both: not seen.
- **A dropper throws its item about three blocks**, so the coal lands on
  the floor in front of the bunker, not at its foot.
- **An armour stand presses a stone-kind pressure plate only if it has
  gravity** (and is not a marker): one summoned with `NoGravity:1b`
  stood on the plate and the plate stayed up. With gravity the plate
  went down within 15 ticks and came up within 40 of the stand going.
  An item on a `polished_blackstone_pressure_plate` does not press it
  (a coal lay on one for 30 ticks), which is why the valves' plates are
  that kind and not the brass-coloured weighted one.
- **A sticky piston drops its block** when the feed pump's clock is
  stopped and started within a stroke (a brass head was left a block up
  after the first run of the check). The pump's pistons are plain and
  carry nothing.
- **The feed pump** is a redstone torch on a block, its light led by
  dust through two repeaters (4 ticks each) back into that block: placed
  by `setblock` it starts by itself, and it stops when the torch is
  taken out. Both pistons were seen out and in over 6 s.
- **`{x}.5` is not the middle of a cell with a negative coordinate**:
  for z = -116 it writes -116.5, the middle of cell -117. The first
  check put its coal a block north of the chute. `dome_boiler.middle`
  adds a half instead. The core writes positions the first way
  (`domes.sphere`, `game_checks.stand_in`, the tunnels' sounds and
  steam), so here, where z is negative, each is a block to the north:
  nothing has gone wrong by it yet.
- **A solved dome put back to "open" by score solves itself again** if
  the room's own state is left as it was: the check resets the room
  (`dome/1/reset`) with the score.

**The boiler house** (second round, after the first play-test: "less
bare"). Round the puzzle, which plays as it did: the boilers are 3 by 3
and 7 high with domed tops, their flues rising to a header 12 up that
crosses the dome over the gauge, a stack on it; a stoker's gantry of
copper grating 5 up over the firing aisle, railed, stairs at its north
end, a feed pipe slung under it with a riser from the feed pump and a
branch into each boiler; the bunker a timbered bin; the main a strip of
copper set in the floor from the gauge to the pump engine with the five
lamps in it; a feed tank and two receivers. The east half is left open
above head height: anything there would hide the gauge from a valve.
Machinery that works by itself: the lamp chaser (real redstone, always
running), the governor (two pistons worked by a function, a stroke each
time a count reaches 16, a lamp of pressure adding one a step: still at
nil, a stroke a second at 8 lamps, one every 2 s in the solved room
while someone is there), the bell under the header (a redstone block
put over it for half a second as each lamp of the main lights), and
steam at seven places, more of them the higher the pressure. The pump
engine by the door joins in at the solve by the tunnel's own event.

- **Copper bulbs under a clock's dust blink with it**: dust powers the
  block it lies on, and a bulb turns over at each rising edge, so a
  bulb under the dust just after the torch and one under the dust after
  the first repeater turn over 8 ticks apart. All four read lit and
  unlit within 6 s.
- **A bell hung under a block rings when that block is made a redstone
  block**: the bell read `powered=true` while it was. That it swings and
  sounds is for the play-test.
- **The governor's pistons are plain too**: the first check left a
  sticky one's head a block up after `reset` cut a stroke short.
- **The walks and the sight lines are checked with no server**
  (`walk_problems`: feet and head free and something underfoot, a step
  level or one up or down, to the bunker, both chutes, both valves in
  both forms, the gauge, the log, the gantry and the way out;
  `sight_problems`: every lamp of the gauge from both valves and both
  chutes, the band's lamps from the entrance and the bunker). The build
  refuses a room that fails either. Both were seen to fail with a wall
  put across the dome.
- Not proved: anything about how it looks or sounds; particles; that a
  player cannot reach or be confused by any of it. A picture of the
  blocks was rendered from the plan (not kept in the example) and
  looked at: it shows shapes and places, not the game's look.

What the stand-ins leave unproved (all in the play-test list): a hand on
a lever, a button, a hopper or the lectern, and coal picked up and
carried; a player's own weight on a plate; the click on the recall
button and where it takes the player; everything aimed at players
(titles, chat hints, sounds, particles); adventure mode's limits (the
locks, nothing breakable); whether the gauge and the signs can be read,
and whether the puzzle is clear and fair at any level.

### The way in: findings

`shore.py`, on the 26.3 server.

- **The lift's mechanism** (second round: slow, about 11 s a trip,
  after the owner's first ride on the quick one). Standing at an end the
  cage is blocks: a floor and a roof of copper grate in a shaft of iron
  bars. When it leaves, the blocks are taken away and a block display
  put where each was, and everyone in the cage is sat on an item
  display of their own (`ride @s mount`). Then every tick the pack
  moves the displays and the seats an eighth of a block
  (`tp @s ~ ~-0.125 ~`, `teleport_duration:1`): 27 blocks in 216 ticks
  after half a second's wait. A rider is a passenger, carried by the
  client's own drawing of vehicles between ticks, not teleported: that
  is why it should be smooth, and a passenger does not collide, so
  nothing can catch or drop them. At the far end the blocks are put
  back, the riders dismounted and stood where they sat, the displays
  killed. One who gets off their seat on the way is put back on it the
  next tick. To watch: real chain blocks paid out above the cage a
  block at a time (taken in going up), the winch's drum (an item
  display of a log) turning a quarter for each block, a counterweight
  (a block display) sliding the other way up a corner chain of the
  shaft, four lit copper bulbs in the shaft wall to pass, a bell at
  each end. The first version stepped the blocks and teleported the
  riders a block every 2 ticks: checkable, but at ten seconds a trip it
  would have been a jolt every 8 ticks. The inputs are real buttons
  that `lift/tick` reads
  (`if block ... polished_blackstone_button[powered=true]`): a call
  button outside each end, and one in the cage that the cage brings
  with it. Each end's gate is shut whenever the cage is not there, so
  there is never an open shaft to fall down.
  - Proved in the world with an armour stand: `ride` onto an item
    display, the stand's position following the display's teleports (it
    reads 0.1 below the seat), `ride @s dismount`, and
    `execute as <seat> at @s positioned ~ <y> ~ on passengers run ...`.
    `data merge entity ... {start_interpolation:0,interpolation_duration:8,transformation:{left_rotation:{axis:[1f,0f,0f],angle:1.5708f},...}}`
    is taken and reads back as a quaternion.
  - Not proved: any of it as a player sees it. Whether the ride is
    smooth, how a seated player sits in the cage (the seat is 0.1 above
    the floor), whether the displays read as the cage, the drum's turn
    and the counterweight seen, and that a player who sneaks off the
    seat is put back.
- **The middle of a cell** is `domes.middle(cell)`, not `f"{x}.5"`
  (a block off for a negative coordinate). Correcting it moved the two
  jetty boats a block east (one had been half under the jetty's edge),
  the two dock boats a block south, and the spot riders are stood at in
  the cage a block south, to the true middle of the shaft.
- **Sealed.** The shaft meets the sea only between the dome's top and
  the deck: there it is a 5 x 5 collar of copper filled solid and then
  hollowed (the rig's rule). The 25 cells of the shell it replaces are
  registered with `domes.add_opening`. **`domes.check_shell` still
  wants the sea over the dome's top**, where the shaft now stands: the
  core's `shell_0` check reports "no sea over its top" until that test
  leaves a registered opening out; the lift's own check leaves that one
  finding out.
- **The shore is outside the station's box**, so nothing keeps it
  loaded: the `shore` stage and check forceload its chunks while they
  run and release only those they added (the world's own forceloaded
  chunk is among them and is left). The boat function runs there only
  when a player is near, which is when it is wanted.
- **The world spawn is left where it is.** New players appear within 10
  blocks of it (`respawn_radius`), some 20 blocks from the landing, with
  the signpost in sight. To put them on the landing itself, set the
  layout's `SPAWN` to it and `setworldspawn` there with `respawn_radius
  0`: not done, as the spawn is the layout's site data.
- **Spawn protection.** A server's spawn protection (16 blocks by
  default) stops players who are not operators using blocks near the
  world spawn, and the landing is inside it. Nothing at the shore is a
  block to use (a boat is an entity), so it does not matter here: keep
  it so.
- **Syntax, each sent over RCON or loaded in the pack.**
  - A sign: `dark_oak_sign[rotation=2]{front_text:{messages:["a","b","c","d"],has_glowing_text:1b,color:"yellow"},is_waxed:1b}`:
    the lines are plain strings.
  - On the ground, whatever its height:
    `execute positioned x 0 z positioned over motion_blocking_no_leaves run summon minecraft:marker ~ ~ ~`
    puts the marker in the first free cell over the ground (under a
    tree's leaves, on top of water or a log: test `~ ~-1 ~`).
  - `positioned 63 50 -109` is the middle of that block in x and z, so a
    selector's box from there starts half a block off: step back with
    `positioned ~-1.5 ~1 ~-1.5` before `@e[dx=2,dy=2,dz=2]`.
  - `fill` joins iron bars to their neighbours (`[east=true,west=true]`
    read back); a button set `[powered=true]` by command stays so until
    set back.
  - `summon minecraft:dark_oak_boat ~ ~ ~ {Tags:[...],Invulnerable:1b,Rotation:[25f,0f]}`;
    `kill` on a boat drops no item. `unless score @s obj = @s obj` is
    true of an entity with no score yet.
  - A beacon on 3 x 3 gold reads `Levels: 1` once lit: up to 105 ticks
    after it is placed (25 to look up its beam, then the next multiple
    of 80).
  - A lantern whose fence post is removed from under it drops as an
    item: remove the lantern first.
- **Replies from a shared server.** With other RCON clients busy, a
  read can come back as another client's reply (a score of 0, a "Test
  passed") and still look like an answer. The way in's checks read
  again whatever is not as expected before calling it a fault, and
  count the lift's steps in the pack rather than watch them, since
  another client's `tick sprint` runs the ride through.
- **Not proved** (armour stands and block reads cannot): anything a
  player does or sees. The ride as a player feels it; the buttons
  pressed by hand; a player in the doorway taken along and one found in
  the shaft put in the cage (those lines aim at `@a`, and loaded
  without error); getting into and out of a boat, the row, whether the
  beacon shows from the jetty; whether the signpost and lamps are
  enough to find the jetty. All in the play-test list.

### Stand-ins

The live checks of the core run with nobody online. A player is stood in
for by an armour stand tagged `st.standin`, which `players/scan` counts
as in the game wherever it is, and functions are run as one with
`execute as`. That exercises the counting, the mode, which dome, the
vote's tally, and every function's logic and its scores.

It does not prove: that a real adventure-mode player is found by
position (the `@a[gamemode=adventure,...]` lines), or a survival player
put in adventure mode; anything aimed at `@a`: titles, the on-screen
line, sounds, particles seen, the bossbar shown, teleports, respawn
points, the kit, its topping up, inventories cleared. Those lines loaded
without error and no more. They are in the play-test list.

### Patterns taken from castle2

- The stage list in one dict, in order, and `STAGES=a,b` to run some
  (`mciwb run` passes a script no arguments, so the environment it is).
- The fake client and the recorded build. castle2's `record_build.py`
  showed that a refactor left every block as it was; the station's is
  part of `build_station.py`. Unlike castle2's, the station's fake
  refuses a block command outside the forceloaded chunks, and knows the
  256 chunk limit.
- The unit test runs the example in a Python of its own, in the
  example's folder: the example changes `sys.path` and has short module
  names.
- The limits castle2 met, built in from the start: a command over 1446
  bytes breaks the RCON connection (`build_station.cmd` refuses it before
  sending); another RCON client can empty or add to a reply (`list` and
  `forceload query` are sent until their replies read as such, and a
  `list` that cannot be read stops the build, it is not taken as "nobody
  online"); a server with nobody online does not tick (`Context.tick`
  sprints, or waits when a player is on); a forceloaded chunk is not
  there at once (the build waits for blocks at nine points of the box,
  by `execute if block`, as castle does).
- Still to copy when there is something to use it on: a `*_cells`
  function per mechanism, shared by its build and its check; checks that
  work a mechanism in place and put it back; entities tagged by stage so
  that a stage removes its own before it runs; what each stage summons
  learnt from the fake client and counted in the world.
- Left behind: castle2's stages built on another example's (the station
  imports no example); settings by a dozen environment variables (the
  site is in the layout); the sloping fake ground (the station's site is
  sea, and the fake world is empty).

## Known problems / notes

- The station's box stays forceloaded by design (see "Forceload").
- A dome's shell stage wipes the inside of the dome, the pump engine of
  its outgoing tunnel too, and shuts its doors whatever the tunnels'
  state: after it run the dome's `_inside` stage and `tunnels`, and
  `function station:reset/all`.
- The live checks reset the game (`station:reset/all`) before and after:
  do not run them over a game someone means to carry on.
- A player who is offline when a reset happens keeps their respawn point
  in a dome; their kit is replaced when they next enter a dome.
- A level changed by vote is recorded against the run as the lowest
  level in force during it (`#run.level`), so the best time of a harder
  level cannot be had by turning the level up at the end.
