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
| 2 | Gearworks and the Flooded Dome | the shells, tunnels 2 and 3 are built; the Flooded Dome and the Gearworks built and checked live (see "The Flooded Dome (dome 3): findings" and "The Gearworks (dome 2): findings"), not yet played; the Gearworks' pipe and wrench hand-tested at the test bench (26 Nov 2026) |
| 3 | Foundry and the Signal Room | shells, tunnels 4 and 5; the Signal Room and the Foundry built and checked live (see "The Signal Room (dome 5): findings" and "The Foundry (dome 4): findings"), not yet played |
| 4 | Clockwork Maze, the boss dome, the return tunnel, the win, the Wall of Fame | shells, tunnels 6 and 7; the Engine (dome 7) built and checked live with its phase 2 (the Master) switched off, see "The Engine (dome 7): findings"; the Clockwork Maze built and checked live (see "The Clockwork Maze (dome 6): findings"), not yet played; the win is the core's and is checked, the trophy sign is given at the win, nobody has written one |
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
| before 2 | **The test bench** (a deck beyond the dock's far landing, the side away from the shore; ten minutes; see "Rig, second round"): the Gearworks' pipes and wrench in an adventure-mode hand; a stone button read and let go by the pack, and four lamps behind coloured glass; dying, the 5 s of grace, a zombie that cannot see you set on you; the stepped lift, the hatch, the floor that goes with slow falling; the ravager and its rider seen through glass |  no |
| 1 | Finding the jetty from the world spawn: the signpost, the lamps through the trees (the straight line crosses an inlet and a pond: is the way round plain?) |  no |
| 1 | The boats: getting into one from the jetty, a new one at the mooring a moment after one is rowed away, one each for two players; that a boat cannot be broken |  no |
| 1 | The row out: the beacon's amber beam seen from the jetty by day and by night (it needs the player's own render distance to reach 12 chunks), about 190 blocks |  no |
| 1 | The dock: coming alongside a landing, stepping out of the boat and climbing out of the water onto it, the stairs, the boats there for the row back |  no |
| 1 | The slow lift (second round) with one player and with two: the buttons by hand; the ride down and up seated in the cage, about 11 s (is it smooth? how do you sit in it? does the cage of displays look like the cage?); the chain paying out, the drum turning, the counterweight passing, the lamps; the gates and the bell |  no |
| 1 | The lift's corner cases with real players: one standing in the doorway is taken along; one who sneaks off the seat in mid ride is put back on it; one who logs off in mid ride and comes back is put into the cage, and is not pulled onto a seat when the other player next rides; the cage called away with someone standing in it |  no |
| 1 | Titles and sounds on entering and on solving a dome | no |
| 1 | The pump event through the door's window: is the flooded tunnel visible by the dim lamps, can the water level be seen falling (3 s a layer), do the lamps and the opening doors read well; the same from the far dome's window | no |
| 1 | The engine while it pumps: the strokes, the flashing lamp, the steam and puffs, the klaxon every 4 s (too loud? too often?) | no |
| 1 | The sea seen through the windows of the doors that stay shut (the Pump House's north door, the Gearworks' far door) | no |
| 1 | Two real players and the forms: one in the Boiler Room with the other on the shore or in the Pump House keeps the levers; the second walking in brings the plates at once; one stepping out for under 3 s changes nothing | no |
| 1 | Dying: respawn at the last dome's entrance, with the kit | no |
| 4 | The sloping tunnels walked both ways: the stairs under foot, headroom at each step, the falling water seen through the door from the Maze (looking down the slope) and from the Engine (looking up) | no |
| 3, 4 | The later kits: a shield in the off hand and spectral arrows on first entering the Foundry; the brass helm, cuirass and sabre on first entering the Engine (do they replace what was worn as intended?) | no |
| 3, 4 | Automatons with a player: they attack, do not fight each other, drop nothing, are gone when everyone leaves their dome, and are cleared from round the entrance when you respawn there | no |
| 1 | Nothing broken leaves an item (`block_drops` off): a pipe broken with the wrench, a lamp | no |
| 1 | The reset buttons with two real players, and a late joiner | no |
| 2 | The Gearworks' pipe in a real hand: places only on the track, the tool breaks only the pipe | yes, at the test bench (26 Nov 2026): it works |
| 3, 4 | Whether the fights are fair for a younger player on Easy | no |
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
| 1 | The log on the lectern: it opens, the pages fit, it reads well for a younger player; a reset puts a new one back if it was taken |  no |
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
| 3 | The Signal Room alone: are the plaque and the board's words enough to find both switches (the AERIAL SWITCH is up the mast, on the loft); 3, 4 and 5 signals at 0.8 s with 8 s a key at level 5: fair for a younger player and for an adult, or ground through by trial |  no |
| 3 | The Signal Room's keys by hand: a press read once and popping back; a click held down, or two quick clicks, taken as one key, not WRONG; a hand's press flips no bulb or lamp anywhere; the dull click of a dead key; the switches by hand |  no |
| 3 | The Signal Board read: the four lamps told apart from the console, each wing and the entrance (place, coloured frame, glass), lit against unlit; the four bells told apart by ear, and the last round by bells alone at levels 8 to 10; the board's words the right way round and readable |  no |
| 3 | The mast in front of the board: from the entrance and down the aisle's middle it hides the middle of the words and the LINE lamps (seen from the desks). Leave it, or a see-through lower mast, or the words moved? |  no |
| 3 | The Signal Room with two: a wing desk each, "the desks change over when this round is done" understood, a partner arriving mid-answer; at levels 9 and 10 the walk between wings in the 6 s a key |  no |
| 3 | The Signal Room as a place: the climb (stairs, bridges, catwalk, loft; a fall from the loft is 10 blocks), headroom, light under the wings and behind the houses; the racks, sweep and recorder busy and plainly not to be worked, the racks' bulbs clicking under a puzzle played by ear; "NO ANSWER: PRESS CALL" after walking away understood; a level voted in mid-room keeps the rounds won; the keys as an instrument once solved |  no |
| 3 | The Foundry alone, Easy, level 5: is 160 s of charge plus three trips fair and fun for a younger player, or too long? Do the plaque and the log say enough to find the MAIN SWITCH and then each breaker (A is by the north-west glass, far from everything)? |  no |
| 3 | Automatons in the Foundry with a real player: do Stokers and Slag Husks come out of the moulds at a player they cannot see, cross the floor, climb the open stairs, walk the grating; do Riveters shoot from the loft or walk onto the gallery; can anything climb the ladders to the gantry; do they burn at noon under the glass? If they stand in the moulds the fight is only a timer |  no |
| 3 | The Foundry's breakers by hand: a lamp following its lever within half a second; a trip throwing the lever back in front of you; the red "OUT" label seen through gratings and the mast from every level; with two players, one title naming both breakers of a pair ("BREAKERS A AND B TRIPPED") |  no |
| 3 | Leaving the Foundry mid-fight: back within 3 s nothing changes; after that the charge falls to the last quarter, a breaker left out is still out, "the charge is where you left it" and 5 s to the fight; a level voted in the Pump House meanwhile takes force when it goes on |  no |
| 3 | The Foundry as a place: the stairs now climb straight onto the gallery (no step up at the top); the stamp battery's cage now has a grating lid (hop the rail onto it and walk back: is that fine, or should the rail be higher?); light under the gallery and in the moulds; the ladle as a ladle, its pour; the mast read as a progress bar from the floor, gallery and top deck; sounds (bell, thunder) too loud or too often; the log's fourth page fits ("O.F." may be cut) |  no |
| 3 | Dying in the Foundry: a cell lost (never below the quarter), no automaton on the respawn spot, the shield against Riveters |  no |
| 4 | The Engine alone, Easy, level 5: is it plain from the plaque, the log and the signs what to do (throw a lever, stand on its copper deck till five lamps light)? Main A is on the floor under the gallery to the right, B on the gallery to the left, C up the one-wide stair behind the Engine. Is 3 to 5 automatons at once fair for a younger player; levels 1 and 10 |  no |
| 4 | The Engine's automatons with a real player: do they come out of the hatch notches in the plinth, find a player round the Engine, up the ramps and the one-wide stair (each is set on the nearest player as it comes: does that work, or do they stand at the far hatches)? Do Riveters shoot into the pavilion while someone respawns or reads the log there (review 4: the dial would be no Riveter while someone is out of the arena)? |  no |
| 4 | The Engine's win: the Engine stopping, the way out lighting, tunnel 7 pumping, the trophy sign in your hand (named with the level and the time), placed on the Wall of Fame in the Pump House and written on |  no |
| 4 | The Engine with two: A and B only together (the amber lamp blinking at the side that is ready, the chat hint), a partner in the pavilion not counting, one dying or leaving; the form's chat line at each change (too chatty?) |  no |
| 4 | The Engine as a place: gauges, amber lamps and the drum's telltales read from each deck and the arch (through two decks of grating); headroom under main A's pipe and the gallery; the governor turning; the cylinders seen through their cages and stopping at the win; the heartbeat (too often?); the log's four pages fit; leaving for 3 s throws open levers back (the cheapest way to clear the automatons: does a child find it?) |  no |
| 4 | Phase 2 (switched off): the Master on his ravager at the test bench first; then, switched on, the breach, the fight, the columns as cover, the steam on the high level |  no |
| 2 | The Flooded Dome alone, Easy, level 5: the first sight through the dam (the standpipe's gauge readable at 17 blocks through glass and water; the cabins and the stairs going down into the water seen); finding pump A without the hint; the sluice line read as a countdown; the lever throwing itself back in front of you; are 22 / 32 / 28 s fair; at level 10 is "throw it twice" understood |  no |
| 2 | The Flooded Dome's swims: stage B down the well, through the culvert, up the hatch with the gate open and shut, air left, the ladder out of the well; stage C the dive from the lower deck to the bars at the cabin's foot and up the hatch ladder, finding the gate; getting out of the water at every level (the two long ladders, each flight, a deck level with the surface); being in the water as a layer goes (any push, damage or suffocation); nothing spawns in the basin (fish, squid, drowned) |  no |
| 2 | The Flooded Dome's gates with real bodies: never shutting on you, in its own cells or beyond it; standing against shut bars from outside does not open them; hands on the levers and a player's weight on each plate; the pump lever put back if moved |  no |
| 2 | The Flooded Dome with two: holder and partner in sight at A, B and C (from plate B only a sliver of gate B shows: review 12); "Hold here. Swap next time." understood; one logging off mid-swim; the second arriving mid-clock (the plate comes only when the spring has run out); is holding three times dull |  no |
| 2 | The Flooded Dome as a place: the crown (about 10 walkable cells: cramped for two?); the one-block bar rails, which can be hopped (into the tide clock's open cage from the dam's crest, onto the beam engine past the fence's ends: a repeater clicked there can stop a clock for good, review 4); falls from the high walk and the crown once dry (up to 16 blocks); lag when a stage ends or a player enters (about 1000 fills in one tick); titles, the bell, the gate and pump sounds, the bubbles, the drowned lamps under water, the tide clock's noise in the hall; the log's four pages fit; plaque and signs the right way round; labels readable under water; time, about 8 minutes for a first-time pair |  no |
| 2 | The Gearworks alone, Easy, level 5: is "steam reaches 67 lengths" understood from the plaque, the steam board and the lit pipe; the steam stopping at the Great Gear's edge read as "find the clutch" (the sign on the back bridge, then the hint); laying 38 lengths while walking: pleasure or chore; about 7 minutes for a first run; the way round falling short read from the red board |  no |
| 2 | The Gearworks' kit in the room itself: 64 pipe and a wrench lent within a second of entering, given back after being thrown away, taken on leaving and on solving; the pipe placing on rough brass and rough copper and nothing else; the wrench breaking laid pipe (under a second?) and not the built-in pipe, the tunnel's lamps or the pump engine's lamp; a broken pipe never dropping an item |  no |
| 2 | The Gearworks' clutch by hand: the lever on the catwalk, the bell and lamps, the gear turning for 1.5 s under you (stand on it through the grating), the lever refusing to go back; pipe laid on the gear before the turn thrown off |  no |
| 2 | The Gearworks with two: each player's pipe sticking to one metal (brass or copper), the bands changing every 5 or 6 lengths, a bay plate at the pipe store changing your kind (stand on it, about a second); one partner idle making the other walk down to the bays at each band (review 1.2: a second pair of bays on the gallery?); one leaving, the one left getting both |  no |
| 2 | The Gearworks as a place: the climb (both floor stairs, the catwalk stair, the ladder at the right side, the squeeze past the fallen cog); stepping over laid pipe on the ring to reach a bridge; the six-block fall from the gear's rim and from the catwalk; light under the gallery; the steam board readable from the gallery and catwalk; the steam chest found from the entrance (the pipe store's rack hides it: review 5); the running lights and pinions (busy for good after the solve: review 7), the tappets, the tick, the hiss, the bells; the log's pages 3 and 4 fit (review 11); anything decorative taken for an input (the bay plates in solo, the built-in pipe) |  no |
| 4 | The Clockwork Maze alone, Easy, level 5: is 6 s an hour enough to see a gate open and get through (and at levels 1 and 10)? The three hour colours (oxidised copper, iron, yellow) and the numerals in the tower's light; the Great Dial from the entrance, the atrium's hour lamps on each deck; the bell's three pitches heard over some 25 pistons at a strike (review 6.4: too loud, lost?); about 2 minutes for a clean run |  no |
| 4 | The Maze's lifts (on) with a real player: riding A, B and C up at the strike of Green (smooth, or a jolt every 3 ticks?), being carried down from a lift's top at the strike of Gold (annoying?), the shutter of trapdoors underfoot, the Ram taking you down from the crown 3 s after the Regulator; and the ladders beside every lift: found, climbed, stepped off sideways (now only into the shaft: a short fall, a slow drift in the Ram's) |  no |
| 4 | The Maze's timed floors: the thud and sparks over a floor in its last quarter (enough warning, at levels 7 to 10 too?), the drift down a deck read as "caught", not hurt; the wave w1 to w5 alone and as a pair |  no |
| 4 | The Maze with two: the tower door's and F to K's plates (gold only while there), the signs changing, the Regulator's lever turning into two keys as the second arrives up top and back; stepping into a doorway as a gate shuts (it waits) |  no |
| 4 | The Maze as a place: the closed bands over the wall tops and the lids on the machine cells (do the cells still read as machinery behind bars?), light under deck 2, the Tally Engine (does it count; its new lid), the pendulum's swing, the Walk (found, used, gives too much away?), the falls from the Walk's stairs (4 to 5 blocks, unrailed); the descent after solving and the pump event on the way; the lever, the recall button and the log by hand |  no |

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

Putting the station somewhere else: the steps are in the README's
[Putting the station somewhere else](README.md#putting-the-station-somewhere-else).

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

### Rig, second round

`rig_domes.py`: the mechanics the designs of domes 2 to 7 rest on, each
worked on the 26.3 server with nobody online, in the air over the rig's
ocean (far from the station), through a pack of its own (`station_rig2`)
that is removed again. The last whole run: 47 checks passed, 3 failed
(3d, 3h and 7e below: each is a finding, not a fault of the rig). Numbered
as in the rig. "By the pack" means read by a function in the same tick.

2. **The Flooded Dome's basin: it holds.** A stone box 35 x 47 x 12 of
   sources (19,451 open cells) with a deck, a stair of 12, a ladder, a
   wall with a 2 x 2 of iron bars, and two levers.
   - A layer dry: its fittings set `waterlogged=false`, then
     `fill <layer> minecraft:air replace minecraft:water`. A layer wet:
     `fill <layer> minecraft:water replace minecraft:water`, `... replace
     minecraft:air`, then its fittings `waterlogged=true`. Stepped down 12
     layers writing only the top one each time: every cell below a source,
     every cell above air, nothing flowing, read 200 ticks on for the
     first four layers and 40 for the rest. Drawn whole from the level
     alone, 16 jumps visiting every level and ending full: right each time.
   - **A fitting left to the game waterlogs itself**: a stair, a ladder and
     bars set `waterlogged=false` among sources were all waterlogged 200
     ticks on. Every waterloggable cell in a wet layer must be written by
     `draw`.
   - A lever over the surface stood through all of it and no item dropped.
     A lever left standing while its own layer is made wet is washed off
     and drops an item: `draw` takes levers out first
     (`fill <cell> minecraft:air replace minecraft:lever`).
   - Bars as a gate: filled to water (air when dry) and back to
     `minecraft:iron_bars[waterlogged=true]` (`false` when dry) they join
     up (`north=true,south=true` in a wall) and nothing flows.
   - Light: one sea lantern in the floor gives 8 or more at head height
     out to 5 blocks sideways, wet and dry alike (in a dark box).
3. **The Clockwork Maze's gate: piston gates work, on two rules.** Two
   sticky pistons, two `waxed_chiseled_copper` leaves, the slot filled
   with `redstone_block` by a function; four gates, the slot behind the
   pistons on two and beside them on two.
   - 1000 strokes 80 ticks apart, each read shut and read open by the
     pack: never a cell out of place. A lit bulb on the lintel and one
     diagonal to the slot stayed lit; one face to face with the slot
     flips.
   - **A short pulse leaves the leaves in the doorway** (check 3d fails):
     the slot cleared 2 or 3 ticks after it was filled; 1 tick and 4 or
     more are clean. A shut gate opened and shut again 1 to 8 ticks later
     ends shut.
   - **Writing the pistons destroys the leaves** (check 3h fails): the
     whole gate set open by `setblock` (slot, pistons `extended=false`,
     leaves, doorway) while it is shut or in mid stroke left all four leaf
     and doorway cells air in 5 cases of 9, a shut gate at rest among
     them. No item drops.
   - **Rule 1: never write a piston.** Open is the slot cleared, shut is
     the slot filled. **Rule 2: a mend every tick** that reads the pistons
     and writes only leaves and doorway: where a piston is
     `sticky_piston[extended=false]`, its leaf cell is the leaf and its
     doorway air; where it is `extended=true` with its `piston_head` out,
     its doorway is the leaf. With it every short pulse ended right, and
     everything the rewrites had wrecked was whole within 5 ticks. A reset
     is: clear the slots.
   - Not judged: the noise of some 25 gates at once.
4. **The Engine's pair.** `summon minecraft:ravager x y z
   {PersistenceRequired:1b,Passengers:[{id:"minecraft:vindicator",PersistenceRequired:1b,equipment:{mainhand:{id:"minecraft:iron_axe",count:1}}}]}`,
   `mob_griefing` false, Easy, prey an iron golem that cannot move
   (`NoAI:1b`, 1000 health), 11 blocks off, 600 ticks.
   - The ravager goes for the prey and bites by itself (the rider's
     `attack_damage` set to 0: the prey lost 320), passing under a deck 5
     over the floor. The rider strikes from its back (the ravager's set to
     0: the prey lost 364). Both still there, persistent, the rider up; a
     zombie of their team beside them unhurt.
   - **With a husk on its back the ravager only carries**: it is taken to
     the prey, and a husk whose blow is 0 leaves the prey unhurt (an
     ordinary husk's own blows took 84). The vindicator is the right
     rider.
   - Stairs between stone walls, prey 4 up: climbed at 3 wide and **at 2
     wide**; not at 1 wide. A two-wide stair does not keep it down.
   - Prey on the pair's own team is left alone (the first run had the
     golem on it: nothing moved). Not proved: any of it against a player.
5. **Daylight.** In the same sun in which a bare zombie under the open sky
   and one under a single layer of glass burnt, nobody burnt under one
   layer of glass with one block of water over it: zombie and skeleton,
   bare and in a copper helmet, 180 ticks. A zombie in an unbreakable
   copper helmet under the open sky did not burn either.
6. **The Signal Room's contact.**
   - `setblock` of a `redstone_block` among four redstone lamps: all four
     `lit=true` by the pack in the function that set it. Beside a note
     block on gold with air over it: `powered=true` at once, and it sounds
     (a sculk sensor 8 blocks off woke for it, and not for the lamps'
     contact alone).
   - Swapped back for copper the lamps hold for 4 ticks and are dark at
     the 5th (the design said within 4).
   - A stone button `[face=floor]` set `powered=true` by command five
     times, read each tick and set back in the tick it is read: five
     presses counted, the button up.
   - **A real press flips a bulb that touches the button's block** (an
     arrow on a wooden button: the bulb beside the block lit). A button
     set by command does not show this (bulb and lamp stayed dark), so a
     check with commands cannot find the fault: no bulb or lamp may touch
     a desk.
   - `execute store result score <name> <objective> run random value 1..4`,
     400 times in a function: 90, 109, 100 and 101 of each, nothing else.
7. **Fights.**
   - `execute store result score <name> <objective> run difficulty` gives
     1 on Easy. Peaceful (0) was not tried: the world's difficulty was not
     the rig's to change.
   - A zombie crossed 10 blocks of `waxed_copper_grate` deck with nothing
     under it, climbed a stair two wide, and passed a ladder hole in its
     straight way without going down it, each to its prey.
   - **A ladder does not keep a zombie down** (check 7e fails): below a
     ladder up the face of a ledge 5 high, its prey in sight at the head,
     it stayed down in one run of 600 ticks and stood at the top in the
     next. In a shaft a block square it stayed down both times.
   - `damage` takes one target (two are refused): from a function,
     `execute as <each> run damage @s 2 minecraft:generic` took 2 from
     each of two husks.
   - `damage <mob> 0.01 minecraft:mob_attack by <other>` sets the mob on
     the other: a zombie left another alone for 100 ticks, then killed it.
8. **Displays.** A block display with `teleport_duration:1` turned by
   `execute as <it> at @s run tp @s ~ ~ ~ ~9 ~`: 90 degrees after ten, and
   on by 9 a tick from a tick function (the yaw is not wrapped: it read
   369). One posed by `data merge entity <it>
   {start_interpolation:0,interpolation_duration:20,transformation:{left_rotation:{axis:[0f,1f,0f],angle:1.5708f},translation:[0f,1f,0f],scale:[1f,2f,1f],right_rotation:[0f,0f,0f,1f]}}`
   reads back so. Not seen: whether either looks smooth.
9. **The Maze's lift step.** A 3 x 3 platform stepped up 6 blocks at 3
   ticks a block: each step, `execute as <everyone in the shaft over the
   platform> at @s run tp @s ~ ~1 ~`, the new layer filled, the old
   cleared; the shutter of `iron_trapdoor`s filled to air when the
   platform is 3 below. An armour stand on the platform ended standing on
   it level with the upper deck, and one standing on the shutter when it
   opened ended on the platform too. Everyone in the shaft is moved, not
   only those on the platform, so that the platform never rises into
   someone falling. Not proved: the ride as a player feels it.
10. **The Gearworks' small things.**
    - The rule is `block_drops` (also `entity_drops`, `mob_drops`;
      `doTileDrops` is refused). On, a bulb broken by `setblock ... air
      destroy` drops one item; off, none (the rig turned it off for the
      one test and put it back: it is `true` now).
    - A bulb set `lit=true` stays lit and a bulb set beside it dark; a
      `redstone_block` two blocks off changes nothing.
    - `fill ... minecraft:air replace minecraft:waxed_exposed_copper_bulb`
      takes the bulb in each of its four states.
    - `execute as <item entity> store result score ... if items entity @s
      contents <item>` gives the stack's count (3), as does `contents
      *[minecraft:custom_data~{st_gear:1b}]`; 0 for another item. `clear
      <players> *[minecraft:custom_data~{st_gear:1b}]` parses.
    - The gear's 97 cells swapped for another full block every tick for 60
      ticks, nothing under them: two armour stands on it did not fall.
11. **Machinery.** The torch clock (a torch on a block, dust, two
    repeaters of 4) set by `setblock` starts by itself: a turn is 35.8
    ticks (1.79 s). Three plain pistons tapped off it, each on a block fed
    by a repeater of 4 with a lamp beside it, rise in turn 8 ticks apart,
    once a turn, and are down 60 ticks after the torch is taken out. Six
    `waxed_copper_bulb`s with a `comparator` out of each into the next
    count in binary (changes in 2401 ticks: 67, 34, 17, 9, 5, 3).

**The test bench** is `rig_domes.py` too (`BENCH=build`, `check`,
`remove`): a deck joined to the far landing of the dock, the side away
from the shore, with a bay for each thing only a player can try, and it
stays. It is in the station's box (so its chunks are loaded) but is none
of the station's: a pack of its own (`station_bench`, with its own
namespace, objectives `bench` and `bench.died`, tags and loot table), no
call into the station's functions, no block of the dock changed. Buttons
are stone buttons on gold posts, read each tick and set back. A player is
"at the bench" inside its box: on leaving, what it gave is cleared (by
`custom_data`), and with nobody there its mobs are killed and the bays
put right. `DIE` sets the player's respawn point at the bench; leaving
sets it to the world spawn.
- Checked with nobody there: the pack enabled beside the station's, the
  2238 blocks and 22 notices in place, each of the 14 buttons read and
  let go, the lift and the grate run empty, the lamps, the count, the
  mobs summoned and removed. **Nothing at the bench has been tried by a
  player**: that is what it is for.
- To take it away: `BENCH=remove` (entities, blocks, the sea put back
  under the gangway, the pack).

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

### Core, fifth round: before the six domes

- **The check cell.** The core's checks that build or summon (fittings,
  automatons, fights, restricted items) no longer use dome 6 (the
  Clockwork Maze will fill it): they build a sealed glass cell, 11 by 7
  by 5 inside, in open water in the middle of the ring
  (`fittings.check_cell`, from the layout; its floor 8 above the base
  floor), and put the sea back after. It goes by the number 8, no dome's.
  The unit test checks it is in the station's box and clear of every
  dome, tunnel, the dock, the lift and the bench. Because the cell is no
  dome, two things the fights check saw live are now seen only in the
  unit test: that the core removes a dome's automatons when it empties,
  and clears round its entrance on a respawn (the check runs the same
  clearing line round a spot in the cell, and the core putting
  `st.died` back is still seen live).
- **`game_checks.no_run`**: every live check's first line; refuses while
  `#run` is 1 unless `FORCE=1` (tried live: set `#run` 1, the verify
  refused). Checks that change the level put back `#run.level` too
  (`save_level`, `restore_level`).
- **`block_drops` false** in the rules stage: nothing broken leaves an
  item. The whole verify passed with it.
- **The shore**: the lift's `st.lift.on` is taken off everyone while the
  lift is idle (a rider who logged off mid-ride kept it); no boat is made
  while 12 are about (`BOAT_CAP`). Neither case was made to happen live.

### The Foundry (dome 4): findings

`dome_foundry.py` (its docstring has the fight and the functions), built
live with `dome_4_inside` over the shell already there; the BYPASS stub
is gone. A casting floor with a dais and the mast (twelve cells of four
lamps, the MAIN SWITCH on brass at its foot), a horseshoe gallery 6 up
reached by two stairs, a gantry 12 up reached by two ladders, two moulds
the automatons are cast in, the cupola with the rivet loft, chimneys,
the stamp battery (the shared torch clock, caged and lidded) and a ladle
on a crane rail. Throw the switch; the mast charges while breakers A
(floor), B (gallery) and C (top deck) are all closed; a breaker trips at
each quarter (solo one at a time, duo a pair on two levels); waves from
the moulds and the loft every 20 s at level 5; the twelfth cell solves
it. 160 s of charge at level 5 (133 s at 1, 214 s at 10).

**What the live check (`CHECKS=foundry`) proves**, with stand-ins and
levers set by command: every block as built and again after a reset from
a scrambled duo fight; the room's 9 entities and the logbook; the stamp
battery's lamps and pistons seen both ways; the ladle parked with nobody
in and travelling with someone in; Peaceful refused (the difficulty put
back as found); the switch starting the fight and held over; the moulds'
lamps before a wave and dark after; the first wave's kinds, dressed, in
both moulds, follow range 48; the charge climbing, standing with a
breaker opened by hand and going on when closed; A tripping at the first
quarter, its label red and `see_through`; eight waves with nothing killed
filling each kind to its cap and no more; Slag Husks in a third-quarter
wave; the leash; a death costing a cell and never going below the
quarter; duo (B and C trip together) and one leaving (the relief relay);
the checkpoint (out for a second changes nothing; after 3 s the charge at
the quarter, a breaker left out still out, no automatons, the bar hidden;
back in, a level voted meanwhile taken, the charge standing until the
breaker is closed, then a wave); the end (mast and bus bar lit, tunnel 4
drained, dome 5 opened, the shell intact); a second entry casting
nothing; an idle room left put back; the values at levels 1 and 10.
Live: `PASS foundry` on the first run after the review fixes; then the
whole verify (see below).

**Changed from the review**:

- F1 (would break a game): the battery's cage on the north mould's roof
  was a pit: a player who hopped the gallery's one-block rail could drop
  in and not get out, and nothing in an idle room kills or recalls. Now a
  lid of copper grating level with the die bar (`MOULD_ROOF + 3`), and
  `walk_problems` searches for pits (`pits`: falls of any height, ladders
  both ways, rail tops to stand on; every cell reached must lead back to
  the entrance). Without the lid it finds the review's 11 cells; the unit
  test checks it does.
- F2: in the duo form the second breaker's title replaced the first's.
  Now `trip_stage` sends one title naming the stage's breakers.
- F3: leaving no longer closes the breakers. Before, stepping out for 3 s
  answered every trip and cleared the room, so the fight could be won from
  the doorway. The charge still falls only to the last quarter, so leaving
  costs no more than the stage in progress (the core's rule); a returning
  player closes what is out (the relief relay still closes the second of
  a pair when one of two is left).
- F4: the stairs had five treads, a full block's step below the gallery
  deck. Now six (`TREADS = DECK_H`), the foot one nearer the mast.
- F5: a level voted while the Foundry was left changed the automatons
  (the core's `mob/count`) but not the room's charge rate, wave gap or
  death cost. Now `resume` (a safe point) takes the level's values.
- F6 (debt, one line): a solved room puts its logbook back.
- Nits: no "closed" sound on the first draw after a reset; the duo chat
  line reworded; the stand-in tags are `st.fd1`, `st.fd2`.
- Contract: the check's first line is `game_checks.no_run`; the level is
  saved and put back with `save_level`/`restore_level` whatever happens;
  nothing uses the old check site.
- **Not done** (debt, more than a line each): F7 (the relief relay closes
  a fixed breaker and says so even if it was closed); the death message
  when nothing is lost; `#fdy.live` read only by the check; the three
  `waves` calls used for `cast` only (15 unused functions); the check not
  refusing when `#d4` is 2 (the verify resets the game first).

### The Signal Room (dome 5): findings

`dome_signal.py` (its docstring has the puzzle and the functions), built
live with `dome_5_inside` over the shell already there; the BYPASS stub
is gone. An exchange on four levels: floor (plaque, logbook, recall post,
battery and recorder houses, two caged relay racks either side of the
aisle), the operator's deck (4 up: the main console, the mast's foot),
two wings (6 up: the port and starboard desks), a catwalk (8) and the
loft round the mast (10: the AERIAL SWITCH). The Signal Board over the
way out: four lamps (a cross of redstone lamps round a contact, a frame
of coloured concrete, a bell behind each), three LINE lamps, the words
on a text display. Close the BATTERY and AERIAL SWITCHes, press CALL,
answer the Engine's lamps and bells key for key; three rounds, each a
signal longer, solve it. Solo at the main console; two players at the
wing desks, a pair of keys each.

| At level | Rounds (signals) | Between signals / lamp on | Time a key (duo: +2 s) | Last round |
| --- | --- | --- | --- | --- |
| 1 | 1, 2, 3 | 19 / 11 ticks | 11.2 s | lamps and bells |
| 5 | 3, 4, 5 | 16 / 8 | 8 s | lamps and bells |
| 10 | 6, 7, 8 | 12 / 4 | 4 s | bells alone (levels 8 to 10) |

**What the live check (`CHECKS=signal_room`) proves**, with stand-ins
and blocks set by command: every one of the 1073 blocks as built and
again after a reset from a scrambled room; the racks' eight bulbs
chasing; the recorder still with nobody in and moving with someone in;
dead keys with no line; each switch, the cables and pilots ramping, the
sweep turning; free play of each key (its four lamps lit and its note
block powered, then dark); three rounds answered at level 5 with every
round's sent signals matching the room's own record and some contact
seen closed (a round that lights nothing fails); the solve, tunnel 5's
pump event and dome 6 opened; the switches held once solved; every
failure path (wrong key, clock out mid-answer, no answer, CALL during an
answer, a switch opened, everyone leaving, three wrong answers); the duo
desks, a form change waiting for the round, a key out of turn, one
leaving mid-answer; a change of level keeping the rounds won; the last
round by bells alone at level 10; fifty sequences keeping their rules;
the recall click taken up; tunnel 5 left shut and flooded, the
neighbours' scores untouched. Live: `PASS signal_room` on the first run after the review fixes (its counters confirm the work: 108 signals shown, the 8 of the round by ear rung on the second contacts); then the whole verify, 43/43 passed (5 TODO: the domes not built yet).

**Changed from the review** (none of its findings "will break a game"):

- 1.1 A key held, or clicked twice, was read as a second key, always
  WRONG (the button is let go in the tick it is read, and a held click
  repeats every 4 ticks). Now the same key twice running is ignored while
  answering (`#sig.last`): safe, as a sequence never has a key twice
  running. Tested offline; a real held click is for the play-test.
- 1.2 "NO ANSWER: PRESS CALL" now has a sound (the beacon's deactivate)
  and is red, not READY's gold.
- 1.3 A level voted while in the room used to arm it anew for the next
  first player in: switches opened, LINE lamps out. Now (`rearm`) the
  new level's values and a new sequence for the rounds still to win; the
  switches and the LINE lamps kept.
- 1.4 Duo at levels 9 and 10 left 4 s a key for a 16 block walk between
  wings: while the desks are split each key gets 40 ticks more (`WALK`).
- Debt: the check's `listen` now fails a round in which no contact was
  seen closed (below level 8).
- Contract: the check's first line is `game_checks.no_run`; the level is
  saved and put back with `save_level`/`restore_level`. The core test
  `test_station_shared_room_helpers` builds its own stub of dome 5 now,
  instead of reading the Signal Room's tick as a stub's.
- **Declined, for the owner**: 1.5, the mast hides the middle of the
  board's words from the entrance and the LINE lamps from the whole of
  the aisle's middle column (offline sight lines: the words are clear
  from the aisle's side columns past f -8, and from every desk). Fixing
  it means a see-through lower mast and moving its cable bulbs, or
  moving the words: a matter of taste, so it is on the play-test list.
  Not done either: the review's nits (blank key signs on the unused
  desks, the racks' bulbs clicking, the docstring's list of check-only
  scores).

### The Engine (dome 7): findings

`dome_boss.py` (its docstring has the fight and the functions), built
live with `dome_7_inside` over the shell already there; the BYPASS stub
is gone. A pavilion round the entrance (plaque, logbook, recall post);
the Engine in the middle, its face towards you, two caged torch-clock
cylinders either side of the avenue; a gallery ring 6 up on nine columns
with three ramps; a high level 12 up (crown deck, catwalks, main C's
platform up a one-wide railed stair, three ladders). Three steam mains:
throw a main's lever and stand on its deck (cut copper) until its five
lamps light; step off and it runs down. Automatons come one at a time
from four hatches in the Engine's plinth once a lever is thrown, 3 to 5
alive at level 5 alone. Two players in the arena wind A and B only
together. **The third main shut is the win**: the Engine stops, the way
out lights, tunnel 7 pumps dry, and the core's `run/win` runs (best
time, then this module's `trophy`: a trophy sign for the Wall of Fame).

**Phase 2** (the breach and the Master on his ravager) is written and
kept out of the pack by `PHASE_2 = False` at the top of `dome_boss.py`,
until the owner has seen the pair at the test bench. The list at the
switch says what is still unproved; switching on needs `datapack` and
`dome_7_inside`, and the check then works the breach and the Master too
(offline only so far).

**What the live check (`CHECKS=boss`) proves**, with stand-ins and levers
set by command, switch off: every block as built and again after a reset
from a scrambled room; the build's 8 entities and the log; both
cylinders seen moving; nothing before a lever; a lever with nobody on
the deck wakes the Engine and winds nothing; on the deck the gauge, its
lamps and the telltale climb; off the deck, or the lever back, it runs
down; held to five it shuts (lever gone, telltales out, sign SHUT);
automatons to the cap and no further, on the team, of the core's kinds,
follow range 48; one put in the pavilion is put out, one killed is
replaced; B and C; **the win**: phase 5, `#d7` 2 and `#run` 2 (the core's
`solved` and `run/win`), no automatons, the 17 lamps of the way out,
the eyes out, the governor run down, the trophy hook run (its name made
in storage), the cylinders' clocks out and their pistons at rest;
tunnel 7 pumped dry and open; a second entry leaves the solved room
alone; leaving in phase 1 costs the main being wound and no more; two
players (a partner in the pavilion, the form change waiting for a safe
point, A ready alone with the amber lamp, both in step, the cap, C for
one, one leaving); `died`; the recall click; levels 1 and 10; tunnel 7
left shut and flooded, the scores as found, no stand-in. Live: `PASS
boss` on the second run (the first found the deck fault below); then the
whole verify, 45/45 passed (3 TODO: the domes not built yet).

**Changed from the review** (none of its findings "will break a game"):

- 1 (`minecraft:follow_range` unproved, in the function that casts every
  automaton): **declined as moot**. The Foundry's live check has since
  read follow range 48 back from its automatons, so the name is proved;
  this dome's check now reads it back too.
- 2: main A's deck was plain floor and B's and C's plain grating, so
  the lever could be thrown from 30-odd cells off the deck and nothing
  wound. Every deck is cut copper now; the offline walk and sight checks
  still pass.
- 3: automatons cast at a hatch behind the Engine stood there. Each is
  now set on the nearest player in the arena as it comes (`damage ...
  0.01 minecraft:mob_attack by <player>`, as the rig proved). A
  stand-in is not `@a`, so only a player can show it works.
- 4 (Riveters shooting into the pavilion): **declined for the play-test**,
  as the review itself advised: no fix in blocks, and the dial (no
  Riveter cast while someone in the dome is out of the arena) is a
  balance call. It is on the play-test list.
- Debt, small: the cylinders now stop at the win (the clocks' torches
  taken out, put back by `reset`; review 7); the shared test no longer
  asserts dome 7 is a stub (6); the switch's list rewritten to what the
  rig has not proved (10); the check refuses during a run
  (`game_checks.no_run`), and puts back the run's scores and the level
  (`save_level`/`restore_level`) and kills its stand-ins whatever
  happens (9).
- Found live: a stand-in (a marker, no height) put at a deck's floor is
  not in the deck's box, whose bottom face it sits on; the check now
  hangs it half a block up. A player's body is always in the box. And a
  piston caught in mid stroke reads as `moving_piston`: accepted for a
  cylinder's cells, and for the stamp battery's in the Foundry's check,
  which failed on it twice running in the whole verify. The whole verify
  also found the brow left lit by an earlier check: `reset` now darkens
  it.
- **Not done**: the review's other debt and nits (Slag Husks never cast
  in the check; the log still names the Master with phase 2 off; "The
  Engine watches" at every entry; `form/set`'s chat at every change).

### The Flooded Dome (dome 3): findings

`dome_flooded.py` (its docstring has the puzzle and the functions), built
live with `dome_3_inside` over the shell already there; the BYPASS stub
is gone. A glass dam a few steps in holds a basin 11 layers deep; the
entry hall behind it stays dry. A copper standpipe with a gauge of lamps
rises out of the flood; a stair beside the dam climbs to a high walk,
bridges, a balcony round the pipe, the crown (a caged beam engine) and an
east platform. Under the water: a machine deck, a lower deck, three pump
houses, a culvert and the floor, with tunnel 3's airlock at the bottom.
Three stages, one rule: a pump moves water only while its sluice is open,
and the sluice's control is never by the pump. Solo the control is a
lever on a spring (22 / 32 / 28 s at level 5, counted down by eight
lamps); duo a plate one player holds while the other goes through. A
layer falls every 1.5 s at level 5. Stage A is in the dry, B is a swim
through the culvert, C a dive to the foot of a cabin. The two rig rules
are kept: every waterloggable cell of the basin is written by its
layer's function (`basin_problems` refuses any other), and `draw` takes
levers, plates and signs out before any layer is made wet.

**What the live check (`CHECKS=flooded_dome`) proves**, with stand-ins
and levers set by command: every block of the plan and the basin by
count (13,101 sources, nothing flowing, no air under water, every fitting
wet), again 200 ticks on; the shell; labels, recall entity, log; light at
five places flooded and four more once dry; the tide clock's lamps and
pistons seen both ways; the beam engine still with nobody in and seen
working while water falls; solo straight through (the spring's clock run
out and the lever back, layers falling one at a time with the gauge,
each stage uncovered whole, the water at rest part way for 200 ticks);
the solve, tunnel 3's pump event, dome 4 opened, the dam door open, the
room dry; a second entry changing nothing; nobody shut in at any of the
three gates (beyond it, in its own cells, out again); solved from outside
with nobody in: dry within 4 ticks, the tunnel's doors still shut; duo
(an item on the plate does nothing, a stand-in on it opens the gate and
drains, let go the water rests); the form changing both ways mid-stage;
leaving part drained (kept) and coming back at levels 1 and 10; a reset
from a scrambled duo room, the other domes' and tunnels' scores
untouched. Live: `PASS flooded_dome` on the second run (the first found
the fault below); then the whole verify, 46/46 passed (2 TODO: the Gearworks and the Maze).

**Changed from the review** (none of its findings "will break a game"):

- 1: a tunnel check (`CHECKS=tunnel_3`) opened the tunnel, the guard
  dried the room, the check then shut the tunnel, and the next player in
  found a dry room that solved itself. `tick` now solves a dry room only
  while tunnel 3 is pumping or open, and otherwise floods it again
  (`reset`). Tested offline in the simulation, both ways.
- 2: the beam engine's clock strokes for 8 to 10 ticks after its torch
  goes; the check now waits 30 ticks before reading the engine or the
  room after a stage, and watches it for 40 ticks while pumping.
- 6 (debt, done for the soft lock it guards): the check now stands a
  stand-in beyond gates B and C and in their own cells, not only A's.
- Found live: a tide-clock piston caught in mid stroke reads as
  `moving_piston` (as in the Engine and the Foundry); now accepted for a
  moving cell.
- Nits, a line each: stand-in tags `st.fl1`, `st.fl2` (8: the Foundry's
  are `st.fd*` now anyway); the unused `RECALL_TAG` gone (16); the log's
  last page loses its signature (13).
- Contract: the check's first line is `game_checks.no_run`; the level is
  saved and put back with `save_level`/`restore_level`, and the stand-ins
  killed, whatever happens. Nothing uses the old check site in dome 6.
- **Not done** (debt, more than a line each): 3, the whole build runs
  `dome_3_inside` before `tunnel_3`, which rebuilds the pump engine dry
  inside the standing flood (put right by the first `arm` or
  `reset/all`); 4, the one-block bar rails round the tide clock's open
  cage and the crown's engine (on the play-test list); 5, hint times run
  longer at low levels (the core's `fittings.hint`); 7, the check leaves
  `#t3` 0 whatever it was (the docstring says so now); 9, the stage calls
  `dome/3/reset` whatever pack is installed (run `datapack` first, as the
  README says); 11, 12, 14, 15 (the east platform's unreachable side
  aisles, gate B a sliver from its plate, the entry message, the chase
  beside sluice line A); the `# noqa: E731` lines in the test (as
  `test_station_example.py` has).

### The Clockwork Maze (dome 6): findings

`dome_maze.py` (its docstring has the puzzle and the functions), built
live with `dome_6_inside` over the shell already there; the BYPASS stub
is gone. A tower of three decks and a crown on a lattice of 3 x 3 cells:
38 two-block piston gates (a sticky piston pair in a post, shut by
filling a valve slot with redstone, opened by clearing it to grating,
never writing a piston, mended every tick), 7 arches, 6 timed floors of
grating, 4 lifts each with a ladder always there, the Regulator (a lever,
or two keys while two are up top) on the crown. A clock of three hours
(Green, Iron, Gold; 6 s an hour at level 5) opens each gate in the hour
of its colour. To look at: the Great Dial and its pendulum, the atrium's
hour lamps, the Tally Engine, tanks, the Walk round the wall. The lifts
are on (`LIFTS = True`): A, B and C up at the strike of Green and down
at Gold, the Ram down from the crown once solved.

**What the live check (`CHECKS=clockwork_maze`) proves**, with stand-ins
and the lever set by command: every block as built, after emptying, and
after a reset from a scrambled duo room (keys up, a lift moved, floors
dropped, the log taken); the 80 text displays, the pendulum, the recall
entity, the log; the Tally Engine showing 3 or more patterns; the level's
values; two full turns of the clock with all 38 gates read at every hour
(slot, pistons and doorway shut, or leaves parked and doorway clear),
the dial and the atrium's lamps; a gate not shutting on a stand-in in its
doorway; the solo run walked by teleport along the search's route, each
doorway read open before it is passed; the lever: solved, tunnel 6
pumping, every gate open, every floor out; **the mend**: a wrecked gate
and a gate given a short pulse each whole again; the Ram carrying a
stand-in from the crown to its foot and its shutter closing; the lever
held over; a second entry changing nothing; a stand-in on T2 at the strike
of Green found a deck down; duo: the door shut with both outside, opened
by its plate and not by an item, open with one inside; F to K held, opened
by its plate, back on the clock with one beyond; the lever with one up
top, two keys with two, one key not solving, both solving; one leaving:
solo, the plates gone, the room not set up anew; levels 1 and 10; lift A
carrying a stand-in up at the strike of Green; tunnel 6 left shut and
flooded, the other domes' and tunnels' scores untouched, no stand-in.
Live: `PASS clockwork_maze` on the second run (the first found the fault
below); then the whole verify, 47/47 passed (1 TODO: the Gearworks).

**Changed from the reviews** (`review_maze`, W1 and A1 to A5; the second
review's 1.1 and 3.1):

- W1 / 1.1 (would break a game): stepping off a ladder onto a wall top
  (lift C's, on the way to the crown, and the Ram's), or drifting there
  as a timed floor went (T2, w5), a player could walk the wall tops and
  drop into a machine cell with no way out. Now the band between every
  wall top and the floor over it is closed at foot height with bars
  (which covers the block beside each ladder at each deck that the
  second review asked for) and each machine cell has a lid of bars. A new
  search, `trap_problems` (in `room_problems`, so the build refuses
  without it), climbs every rung and steps off it sideways, falls from
  anywhere drifting a block sideways for each block fallen, lands on
  rails, lets a timed floor go from under a player, with the lifts up and
  down: no machine cell is reachable and every place reached leads back
  to the entrance. Without the block beside lift C's ladder and the lid
  of deck 3's machine cell it finds the review's trap; the unit test
  checks it does. With the bands closed, the only cells off a deck it
  reaches are ladder rungs.
- A1: lift C's ladder and backing ran a block above the crown and
  replaced the collar's rail, so a climber holding forward stepped out
  over a 19-block drop (it also led onto the wall tops). Every ladder and
  backing now ends level with the deck it serves. A step off the Ram's
  ladder (18 high) is now a slow drift (slow falling in its shaft).
  **Declined**: rails on the Walk's stairs. A fall of 4 to 5 blocks
  costs 1 to 2 points of 20 (fall damage is the height less 3); on the
  play-test list.
- A2: a timed floor in its last quarter out now thuds under those on it
  and sparks, every half second (at levels 7 to 10 it goes before the
  bell's ticks).
- A3: the check's scramble ran `keys/on` with nobody up top, so the next
  tick undid it and the check would always fail; now two stand-ins go up.
- A4: the Tally Engine's cage has a lid of bars.
- A5: `enter` armed the room on `#first` alone, so a second player
  walking in after the first had logged back in inside reset the room
  under them; now not while it is live.
- 3.1: the Gold hour's block was gold, the station's mark of an input,
  on 12 lintels, the atrium lamps, the dial and the key. Now yellow
  concrete. The gold under the four plates is there only while its plate
  is (`plate_bases`), the floor round it otherwise.
- Debt, done: the mend is now exercised live (4.1); the lifts are on, as
  the rig's experiment 9 allows, with the ladders kept as the fallback.
  The check's walk comment no longer claims ladders.
- Contract: the check's first line is `game_checks.no_run`; the level is
  saved and put back with `save_level`/`restore_level`, and the stand-ins
  killed, whatever happens. Nothing uses the old check site in dome 6.
- Found live: with the lifts on, a stand-in teleported to a lift's top in
  the first ticks of Gold fell through the hole the platform had just
  left (the shutter comes only once it is more than 3 below); a player
  arriving then drops 1 to 3 blocks onto the platform. The check now
  waits for the platform to come to rest.
- **Not done** (debt or nits): the noise of the gates (6.4) and the
  `fill` fallback; the Regulator's swap waiting for no safe point and its
  chat line repeating (D2); `mend` run every tick (D4, about 370 cheap
  lines a tick); the lint suppressions (D7); `reset` killing items by
  position, as the Boiler Room does (D8); the nits N1 to N7. A player
  standing on a lift's top at the strike of Gold is carried down a deck
  (they climb back up the ladder); the pair search does not model it.

### The Gearworks (dome 2): findings

`dome_gearworks.py` (its docstring has the puzzle and the functions),
built live with `dome_2_inside` over the shell already there; the BYPASS
stub is gone. Built only after the owner's hand test at the test bench
(26 Nov 2026): pipe laid with `can_place_on`, broken with the
`can_break` wrench, in an adventure-mode hand. Three levels: the engine
floor (the steam chest, the pipe store with its two bays, risers, the
tappets, tanks), a ring gallery with four bridges and the Great Gear in
the middle, and a catwalk with the clutch. Steam main of 166 lengths of
track (rough brass and rough copper); the short way is 63, of which a
player lays 38 (the risers, the hub and the door feed are built in). The
rule is the gentle one: a length is lit if it is within N lengths of the
chest along laid pipe (67 at level 5, 81 to 63 from level 1 to 10), so
the way round the gallery falls short at level 3 and up and the clutch
(which turns the gear's track into line, and latches) is the way. Solo,
64 pipe and a wrench are lent; duo, each player's pipe sticks to one
metal, and a bay plate changes your kind.

**What the live check (`CHECKS=gearworks`) proves**, with stand-ins and
the pipe and lever set by command: every block of the room as built,
after leaving and after a reset from a scrambled duo room; the three
entities and the log; the tappets seen out and in, the decoration still
with nobody in and stepping with someone in; arming with the level's N
and the board's text; the feed lighting riser 1; steam stopping at the
gear's edge and the hint counting; pipe on the gear thrown off by the
turn, the track swapped, the clutch lamps, the lever held over; the
short way solving, the intake lamps, tunnel 2's pump event to both doors
open, dome 3 opened, the dome dry; a solved room entered again; the way
round: exactly N lit, the board red, then the short way beside it
solving; a lit length cut and put back; out for a moment (nothing
changes), out for good (pipe kept, dark) and back (it fills again); duo:
one of each kind, both bays, three players, one leaving, the fall-back,
the one left finishing a line laid in the duo form; the recall's click;
N at levels 1 and 10 and the plaque rewritten; the other domes' and
tunnels' scores untouched. Not proved by it: anything in a real hand (the
kit given and taken, each duo kind on its metal, the wrench), a real
weight on a plate, a hand on the lever, standing on the turning gear,
what a player sees or hears, the recall's teleport. Live: `PASS
gearworks` on the first run of the fixed check (an earlier run found the
fault below, the next passed by luck of timing); then the whole verify,
48/48 passed, no TODO.

**Changed from the reviews** (`review_gearworks`, `review_gearworks_opus`;
none "will break a game"), before the live build, in the module's second
commit:

- The check's first line is `game_checks.no_run`; the level is saved and
  put back (`save_level`, `restore_level`); `#t2` is left to the
  tunnel's reset (Opus 4.1).
- The kit is no longer lent again in the tick that solves the room
  (review 1).
- The bays are read every tick, not once a second (Opus 1.1).
- A sign at the back bridge's gear end names the clutch ("GREAT GEAR /
  out of line. / CLUTCH: / catwalk above.") (review 2).
- The drop sweep is gone now that `block_drops` is off; `reset` still
  kills kit thrown down and left lying.
- The logbook is put back after the solve too (review 6).
- Found live: a tappet piston caught in mid stroke reads as
  `moving_piston` (as in the Engine, the Foundry and the Flooded Dome);
  now accepted for a moving cell.
- **Not done** (debt or nits): the hint assertions in the check pass on a
  dead hint (review 3); `restored` takes the kit from `@e` and misses a
  player on the death screen or offline at the solve (review 4, Opus's
  first "not worth fixing"); the pipe store's rack hides the steam chest
  from the entrance (review 5); the solved room's decoration busy for good
  (review 7, play-test); the module's own lending line and items beside
  `fittings` (review 8, Opus 5.2: give `restricted` a tooltip flag); the
  tick cost, about 1,650 commands every 2 ticks while occupied and
  unsolved (Opus 5.2); a second pair of bays on the gallery (Opus 1.2,
  play-test); the nits (the enter message, the plaque's sign after a reset
  at another level, the log's page length, `#gear.live` and the
  built-in lengths' dead writes, the `# noqa: E731` lambdas in the test).
  The test bench row's other items (the button, dying, the lift, the
  ravager) were not part of the hand test.

## Known problems / notes

- The station's box stays forceloaded by design (see "Forceload").
- A dome's shell stage wipes the inside of the dome, the pump engine of
  its outgoing tunnel too, and shuts its doors whatever the tunnels'
  state: after it run the dome's `_inside` stage and `tunnels`, and
  `function station:reset/all`.
- The live checks reset the game (`station:reset/all`) before and after,
  so they refuse to run while a run is in progress (`game_checks.no_run`;
  `FORCE=1` overrides).
- A player who is offline when a reset happens keeps their respawn point
  in a dome; their kit is replaced when they next enter a dome.
- A level changed by vote is recorded against the run as the lowest
  level in force during it (`#run.level`), so the best time of a harder
  level cannot be had by turning the level up at the end.
