"""
Print a visitor's guide to the castle, with world coordinates, for the
castle given by the environment (no server needed)::

    ORIGIN=-80,82,-230 SPAWN=32,74,-64 NAME=Fable python guide.py > GUIDE-Fable.md
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle_lib as L  # noqa: E402
from build_outer import bridge_foot, compass, road_points, signpost_position  # noqa: E402
from castle_layout import (  # noqa: E402
    ARROW_TRAP,
    BANNER,
    BRIDGE_END,
    CELL_DOOR,
    CELL_LEVER,
    CHAPEL,
    CRYPT_DOOR,
    ENGINE,
    GATE_X1,
    GATE_X2,
    GATE_Z,
    GATEHOUSE,
    KEEP,
    KEEP_FLOORS,
    KEEP_ROOF,
    LIBRARY_DOOR,
    LIBRARY_LADDER,
    MAIN_GATE,
    MID_Z,
    MIDDLE_GATE,
    NAME,
    ORIGIN,
    PIT_TRAP,
    SMITHY,
    SMITHY_HATCH,
    SPAWN,
    TELEPORTS,
    UD,
    VAULT,
    VAULT_Y,
    WELL,
    XG,
    YU,
    ZS,
    V,
    built_box,
    centre,
)
from mcwb import Vec3

E, S, Wd = Vec3(1, 0, 0), Vec3(0, 0, 1), Vec3(-1, 0, 0)


def p(v: Vec3) -> str:
    return f"({v.x}, {v.y}, {v.z})"


def xyz(x: int, y: int, z: int) -> str:
    return p(V(x, y, z))


def local_gate(gate: tuple[int, int, int, int, int]) -> dict:
    x1, x2, z, y0, lever_dz = gate
    return L.portcullis_cells(
        ORIGIN.x + x1, ORIGIN.x + x2, ORIGIN.z + z, ORIGIN.y + y0, lever_dz
    )


def main() -> None:
    lo, hi = built_box()
    main_gate = local_gate(MAIN_GATE)
    middle_gate = local_gate(MIDDLE_GATE)
    lib = L.hidden_door_cells(V(*LIBRARY_DOOR), E, S)
    cell = L.hidden_door_cells(
        V(*CELL_DOOR), Wd, S, trigger="lever", lever_b=CELL_LEVER
    )
    crypt = L.hidden_door_cells(V(*CRYPT_DOOR), Wd, S, trigger="lever", lever_b=-1)
    px, py, pz, depth = PIT_TRAP
    pit = L.pit_trap_cells(*V(px, py, pz), depth)
    ax1, ax2, ay, zw, zd = ARROW_TRAP
    arrow = L.arrow_trap_cells(
        ORIGIN.x + ax1, ORIGIN.x + ax2, ORIGIN.y + ay, ORIGIN.z + zw, ORIGIN.z + zd
    )
    lx, lz = LIBRARY_LADDER
    gx1, gz1, gx2, gz2 = GATEHOUSE
    kx1, kz1, kx2, kz2 = KEEP
    cx1, cz1, cx2, cz2 = CHAPEL
    vx1, vz1, vx2, vz2 = VAULT
    ex, ez, ey = ENGINE
    wx, wz = WELL
    gate = bridge_foot()
    route = road_points(gate)
    middle = centre()
    width = 45
    rows = [
        "(T)  Alchemist's".ljust(width - 3) + "(T)",
        "      tower   +------KEEP------+  CHAPEL",
        "  garden      |  turret  turret|  +------+",
        "  & pond      |   great hall   |  | nave |",
        "              |  turret  turret|  | bell |",
        "              +-------door-----+  +------+",
        "(T)  stair down   MIDDLE GATE (portcullis)".ljust(width - 3) + "(T)",
        "================[grand stair]".ljust(width, "="),
        "(J)                      |||".ljust(width - 3) + "(J)",
        "  barracks            [stair]",
        "  stables    well o   path     smithy x",
        "(T)                   dungeon hut".ljust(width - 3) + "(T)",
        "            market    [gatehouse]",
    ]
    notes = {
        2: f"UPPER WARD  (y {ORIGIN.y + YU})",
        6: f"z {ORIGIN.z + UD - 1}",
        7: f"<- {YU}-block cliff",
        10: f"LOWER BAILEY (y {ORIGIN.y})",
    }
    box = "\n".join(
        f"   |{r:<{width}}|   {notes.get(i, '')}".rstrip() for i, r in enumerate(rows)
    )
    edge = "+" + "-" * width + "+"
    bearing = compass(middle.x - SPAWN.x, middle.z - SPAWN.z)
    legs = " then ".join(
        f"{compass(b.x - a.x, b.z - a.z)} to x {b.x}, z {b.z}"
        for a, b in zip(route, route[1:], strict=False)
    )
    sign, _ = signpost_position(route)
    door = lib["door"]
    tps = "\n".join(
        f"| {where[0].upper()}{where[1:]} | `/tp @s {V(*pos).x} {V(*pos).y} {V(*pos).z}` |"
        for where, pos in TELEPORTS.items()
    )
    print(f"""# Castle {NAME}: visitor's guide

Built with mciwb from `examples/castle/` in the mciwb repo; rebuildable with
`ORIGIN={ORIGIN.x},{ORIGIN.y},{ORIGIN.z} SPAWN={SPAWN.x},{SPAWN.y},{SPAWN.z} NAME={NAME} BANNER={BANNER} mciwb run build_castle.py`.

## Getting there

World spawn is {p(SPAWN)}. The castle is to the {bearing}: follow the
cobble-edged dirt road from the signpost at ({sign.x}, {sign.z}) beside spawn
(a few blocks further from spawn if another castle's sign was there first),
which leads to the stair at the foot of the bridge at ({gate.x}, {gate.z})
(from there the road runs {legs}). Or teleport:

| Where | Command |
| --- | --- |
{tps}

Castle extents: x {lo.x}..{hi.x}, z {lo.z}..{hi.z} (plus the road to spawn),
y {lo.y}..{hi.y} (the catacombs' floor to the keep's lightning rod). The
outer wall's north-west corner at bailey level is {p(ORIGIN)}; "local"
coordinates in the scripts are offsets from it (x east, z south, y up).

## Map

```
            N
   {edge}   z {ORIGIN.z}  (dry ditch all round)
{box}
   {edge}   z {ORIGIN.z + ZS}  (water moat)
                            |
                        road to spawn {p(SPAWN)}
```

| Place | World position (entrance) |
| --- | --- |
| Main gate and portcullis | passage x {V(GATE_X1, 0, 0).x}..{V(GATE_X2, 0, 0).x}, z {V(0, 0, gz1).z}..{V(0, 0, gz2).z}; portcullis line z {V(0, 0, GATE_Z).z} |
| Main portcullis lever | in the gate passage at {p(main_gate["lever"])}, on its east wall beside the bars |
| Gatehouse winch room | over the passage: stair up from the west guard room (door from the passage at {xyz(GATE_X1 - 1, 0, gz1 + 3)}) |
| Grand stair and middle gate | x {V(XG - 3, 0, 0).x}..{V(XG + 3, 0, 0).x}, z {V(0, 0, UD + YU).z}..{V(0, 0, UD).z}, up to y {ORIGIN.y + YU}; second portcullis at z {V(0, 0, UD - 2).z}, lever at {p(middle_gate["lever"])} in the passage beside it; its winch room is over the gate: enter the west gate tower from the ward at {xyz(XG - 7, YU, UD - 6)}, up the stair, then east |
| Keep great door | {xyz(XG, YU, kz2)}, facing south |
| Great hall / kitchen | ground floor (y {ORIGIN.y + KEEP_FLOORS[0]}); stair hall in the east wing |
| Library (secret bookshelf) | 2nd floor (y {ORIGIN.y + KEEP_FLOORS[1]}), west half; the chiseled bookshelf at {p(lib["trigger"])} |
| Armoury, gallery | 2nd floor, east |
| Lord's chamber, map room, guest rooms | 3rd floor (y {ORIGIN.y + KEEP_FLOORS[2]}) |
| Roof terrace and turrets | y {ORIGIN.y + KEEP_ROOF}, up the stair hall; lantern tower in the middle; the four turrets have doors onto the terrace and the ward, and ladders between their floors |
| Chapel | {xyz(XG + 38, YU, cz2)} door on the south end; altar at the north end; bell tower at the SW corner |
| Alchemist's tower | centre {xyz(ex, YU, ez)}, door on the south; the Engine is on the top floor (y {ORIGIN.y + ey}) |
| Stables, barracks | west side of the bailey |
| Smithy | {xyz(SMITHY[0], 0, MID_Z)} door on its west side |
| Well | {xyz(wx, 0, wz)} |
| Dungeon entrance | hut at {xyz(95, 0, 108)}, door on its north side |

## Mechanisms and how to trigger them

1. **Main portcullis.** In the gate passage, on the east wall one block on
   the bailey's side of the bars, the lever at {p(main_gate["lever"])} drops
   iron bars from the ceiling *and* raises them from the floor in front of
   you, sealing the passage. Flip it back to open. Its signal climbs inside
   the wall to the winch room over the passage (the door in the passage's
   west wall leads to the guard room and the stair up), where you can watch
   the winch: the redstone over the pistons. The grille in the winch-room
   floor is the murder hole over the passage.
2. **Middle gate portcullis.** The same at the top of the grand stair: the
   lever at {p(middle_gate["lever"])} is in the passage through the gate's
   facade, on the stair's side of the bars. Its winch room is over the gate:
   enter the west gate tower from the upper ward at {xyz(XG - 7, YU, UD - 6)},
   climb the stair and go east.
3. **The library's secret door.** On the keep's second floor, the east wall
   of the library is bookcases. One block is a *chiseled* bookshelf
   (at {p(lib["trigger"])}, head height, full of books). Take out the **last
   (6th, bottom-right) book**: the two bookshelf blocks at
   ({door[0].x}, {door[0].y}..{door[1].y}, {door[0].z}), beside the pilaster,
   slide into the wall. Behind: a lit mechanism room and a ladder at
   ({V(lx, 0, lz).x}, *, {V(lx, 0, lz).z}) straight down into the vault.
   Put any *other* book in or out to close the door again.
4. **The well.** Jump in: the bubble column takes you down to y {ORIGIN.y - 8}.
   A dark oak door at the bottom (east side) opens into a dry tunnel. East
   then south leads to the dungeon's hidden chamber; north the tunnel climbs
   under the cliff to an iron door (buttons either side) into the vault.
   Swim back up the column to leave.
5. **The dungeon's escape door.** Down the dungeon stair, through the guard
   room and along the cell block. Each cell's iron door has a stone button
   on its frame on both sides, so nobody gets shut in: no cell is a trap. In the **last cell on the north side** (x {V(70, 0, 0).x}..{V(72, 0, 0).x},
   z {V(0, 0, 132).z}..{V(0, 0, 134).z}) a lever on its west wall at
   {p(cell["trigger"])} opens the corridor's end wall (two stone bricks at
   ({cell["door"][0].x}, {cell["door"][0].y}..{cell["door"][1].y}, {cell["door"][0].z})):
   the prisoners' tunnel to the well and the vault.
6. **The crypt's hidden door.** Behind the chapel's altar a trapdoor and
   ladder lead down to the crypt. A low passage runs west to a small chamber
   with a skull, a sign and a lever on the west wall at {p(crypt["trigger"])}.
   The lever opens the chamber's west wall into the vault.
7. **The smithy's trapdoor.** By the rug inside the smithy, at
   {xyz(SMITHY_HATCH[0], -1, SMITHY_HATCH[1])}, a spruce trapdoor covers a ladder 15 blocks down into
   the lower treasury behind the arrow trap.
8. **The Engine** (alchemist's tower, top floor): eight hoppers pass
   amethyst shards round a ring; the comparators around it chase the lamps,
   pump the copper piston and strike note blocks while you watch. It stops
   when nobody is near (the server pauses).

## Traps

- **Pit trap**, dungeon approach: the one-wide corridor south of the
  entrance stair has a tripwire at {p(pit["wire"])} with its hooks in two
  alcoves. Step on it and the floor under it (three iron trapdoors, under
  the wire and either side) swings open: you fall {depth} blocks into the
  oubliette, and the floor shuts over you. Jump over the wire, or break the
  string.
- **Arrow trap**, catacombs: from the oubliette the only way out is the
  three-wide corridor north. The tripwire at {p(arrow["wire"])} sets off
  three dispensers in the corridor's end wall (z {arrow["dispensers"][0].z}),
  firing arrows back down it. Keep to the sides or sprint. A doorway on the
  east, just before the end, opens into the lower treasury.
- The **murder hole** in the gatehouse winch-room floor is only a grille,
  not a trap, but it is where to pour things from.

## Admin: where the treasure is

- **The Vault**, under the keep: x {V(vx1, 0, 0).x}..{V(vx2, 0, 0).x},
  y {ORIGIN.y + VAULT_Y}..{ORIGIN.y + VAULT_Y + 3}, z {V(0, 0, vz1).z}..{V(0, 0, vz2).z}
  (`/tp @s {V(*TELEPORTS["the vault"]).x} {V(*TELEPORTS["the vault"]).y} {V(*TELEPORTS["the vault"]).z}`).
  Six chests along the north wall with diamonds, emeralds, gold, netherite
  ingots, enchanted golden apples, elytra, a trident, a nether star, discs
  and more; gold-block corners, a diamond block on a pedestal under an end
  rod, emerald/lapis/netherite/raw-gold blocks, golden and netherite armour
  on stands, an enchanting table. Ways in: the library ladder (secret 3),
  the well tunnel's iron door in the south wall (secret 4/5, buttons on
  both sides), the crypt's lever door in the east wall (secret 6).
- **The lower treasury**, in the catacombs: x {V(101, 0, 0).x}..{V(109, 0, 0).x},
  y {ORIGIN.y - 15}..{ORIGIN.y - 13}, z {V(0, 0, 105).z}..{V(0, 0, 113).z}
  (`/tp @s {V(*TELEPORTS["the lower treasury"]).x} {V(*TELEPORTS["the lower treasury"]).y} {V(*TELEPORTS["the lower treasury"]).z}`):
  chests of gold, emeralds, diamonds, a bow and arrows; gold and raw-gold
  blocks. Reached past the arrow trap, or by the smithy's ladder (secret 7).
- Smaller hoards: the lord's chest in his chamber (keep 3rd floor, west
  wall), the armoury chest, the guard room chest in the dungeon.

## Verification

`verify_castle.py` drives all of the above over RCON (advancing ticks with
`tick sprint`, since the server pauses with no players online): both
portcullises close and reopen, the three secret doors open and close, the
pit opens under whoever steps on the wire and drops them into the
oubliette, the dispensers fire (and are reloaded),
the engine's shards circulate and its lamp blinks, the chests hold their
items, every teleport above lands on a floor with head room, and the
castle's entities are exactly the ones it summoned, every tower door opens
onto a floor on both sides, and a visitor can walk from the gate to every
room.

## Forceloaded chunks

None are left forceloaded: the build and the checks forceload the site
while they run and unload it when they finish. All the redstone is ordinary
and works whenever a player is nearby. The bridge is at z {V(0, 0, ZS + 1).z}..{V(0, 0, BRIDGE_END).z}.
""")


if __name__ == "__main__":
    main()
