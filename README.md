# mciwb
Minecraft Interactive world builder

Additional functions on top of the mcwb world builder library to allow 
interactive world building using ipython and a minecraft client in tandem.

## Intro
The interaction is achieved by dropping command signs into the world.
You can also switch back to the iPython console and execute commands.

To initiate an interacive session create a Copy object and
pass the player's name. See demo.py for example usage.

The player will be given one of each of the command signs
currently available. The player can then invoke these
commands and indicate a block location by placing one of
these signs in game.

See the following video for a quick sample of the capabilities:

https://user-images.githubusercontent.com/964827/139144276-8c14ddc4-350f-4e7f-b393-2ec4187c5870.mp4

## Interactive Commands
So far we have the following signs to drop. See demo.py for example usage.

When you drop a sign you must be facing it. It will disappear when
the sign has been detected by the poller and the function has executed.

Note that the sign's coordinates of action are the block **behind** it or the block it is attached to (which is also
the block behind it)

- **start**: set the start point for the copy buffer (and anchor point for paste)
- **stop**: set the opposite corner of the copy buffer
- **paste**: clone the contents of copy buffer to the current
indicated location (anchored at the start point)
- **pastefloor** - shift the copy buffer down by 1 and paste it at the location
  indicated but down by one (good for copying sections of floor)
- **clear**: clear the contents of the paste buffer

## Todo Interactive Commands

- **backup** create a zipped and dated backup of the world
 (requires some preconfiguration)
- **expand**: expand the closest face of the copy buffer to the indicated point (can do all 6 dimensions)
- **shift**: shift the copy buffer until the closest face is at the indicated point

## Useful iPython Commands

Using iPython you can also interact with the same Copy object
your player is using in the game.

The following useful commands are available on the Copy class:

- **shift**: shift the copy buffer in any dimension
- **expand**: expand the copy buffer by moving one of its faces
outwards
- **paste**: paste at the paste location with offset. Can
be used in a loop to make repeating structures.
- Additional support in mcwb required (profile generators)

  - **rectangle**: make a rectangle described by copy buffer
  corners (expects one of the copy dimensions to be size 1)
  - **elipse**: make a elipse described by copy buffer
  corners (expects one of the copy dimensions to be size 1)

## Todo iPython Commands

- **save**: save the copy buffer to a named file
- **load**: load a file into the world at the copy buffer start point. Set the copy buffer to enclose the loaded structure
- **rotate**: perform transforms on the copy buffer
- **restore**: restore the world to a previous backup
