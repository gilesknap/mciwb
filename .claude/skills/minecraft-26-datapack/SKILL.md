---
name: minecraft-26-datapack
description: Pitfalls of Minecraft Java 26.x commands, NBT and datapacks met while building with mciwb - display entities, redstone set by command, stand-ins in boxes, signs, sounds, water, attributes, interaction entities. Use when writing commands, SNBT or datapack functions for a 26.x server, or when something placed or summoned by command doesn't behave as it does by hand.
---

# Minecraft 26.x: what bit us

Each item cost a live failure on a 26.3 server. When in doubt, check the
client or server jar (it is unobfuscated: `javap` on the class, or the
`SoundEvents` / `ParticleTypes` lists) rather than older wikis.

## Displays and NBT

- **`block_state` on a block display** is a bare id string
  (`block_state:"minecraft:gold_block"`) or a map keyed `id` with
  `properties` (`{id:"minecraft:iron_chain",properties:{axis:"y"}}`). The
  old `{Name:"..."}` form is rejected *silently*: the display spawns as
  air. The server log says `Failed to decode value ... from field
  'block_state'`. Use one helper for it and a test that no command contains
  `block_state:{Name:`.
- A live check that a display isn't air: `execute if entity
  @e[type=block_display,nbt={block_state:"minecraft:air"}]` (26.3 stores
  the bare-string form).
- **Text displays on a face** stand 0.02 proud of it, or they flicker and
  hide when something is placed there. `see_through:1b` plus
  `billboard:"center"` makes a label findable across a room; scale it up
  (e.g. 3) rather than giving it a background, which hides things close up.
- `shadow:1b` on a text display helps white text on a busy background.

## Redstone and blocks set by command

- **A lever placed powered by `setblock` does not update its neighbours**:
  a repeater beside the block it hangs on won't fire. A hand on the lever
  does. In a check, nudge the circuit (place and remove a block over the
  repeater) or toggle it the way a player would.
- Read redstone results after it settles (tens of ticks), not in the same
  tick sequence that set the inputs.
- **Water**: a waterlogged block (`barrier[waterlogged=true]`, glass panes,
  stairs) shows water but never flows: good for "water behind glass".
  Real `minecraft:water` sources spread up to 7 blocks and fall; placing a
  block into a source cell replaces it (so plates can seal a breach). Water
  also flows *into* stairs and other waterloggable blocks next to it.

## Entities, stand-ins and selectors

- **Box selectors** (`x,y,z,dx,dy,dz`) test hitbox intersection: a marker
  armour stand standing exactly on a box's floor is *not* in it. Raise
  stand-ins half a block in checks; real players have height.
- `execute as @e[...]` without `at @s` runs at the world spawn: a
  `playsound ... ~ ~ ~` there is heard by nobody. Add `at @s`.
- **Interaction entities** take clicks; `execute on target` from one finds
  the player who clicked. A player's entity reach is
  `entity_interaction_range` (3.0): raise it in one room with
  `attribute @s minecraft:entity_interaction_range modifier add <ns:id> 4
  add_value` and remove it on leaving (`modifier remove <ns:id>`). Adding
  an existing id errors; modifiers survive death and logout. It is also
  melee reach.
- **Attributes on summon**: `attributes:[{id:"minecraft:follow_range",base:8.0d}]`.
  Something that runs later (a "temper" function giving every mob in a
  room a follow range) will overwrite it: check for that.

## Signs, titles, sounds

- **Sign lines** fit about 15 characters (a bold line about 12). A bold
  first line reads as a title, so split sentences so line 1 stands alone
  ("EACH PUMP / Open its sluice, / then pull its / pump lever.").
- The **action bar** may be rewritten every second by a game loop: use a
  title or `tellraw` for one-off messages.
- **Sound volume above 1 only extends range** (16 blocks per unit); it
  isn't louder. Play a machine's sounds `execute at` its moving part so
  players hear where it is, with volume 2-3 for a big room.
- Check every sound and particle id against the jar's `SoundEvents` /
  `ParticleTypes`; a wrong id fails the whole function line.

## Commands and RCON

- An RCON command over about 1446 bytes makes the server drop the
  connection: keep sent commands (and function lines) short, and refuse
  longer ones before sending.
- A `fill ... replace <block>` filter matches every state of that block.
- `tick freeze` pauses the world (players can still move); `tick sprint N`
  runs N ticks fast, handy before reading a settled state.
