Discovering the Coordinates of a Block
======================================

When you are creating objects in the world you need to know the 
X, Y, Z coordinate of the place in the world where you want to start your 
creation.

There are 3 easy ways to do this as follows.

Player Position
---------------

You can always use your player's position to build from. e.g. assuming you
have defined the `pagoda`. You could build a pagoda around your player like 
this:

.. code-block:: python

   pagoda(player.world.position)

It might also be good to use a variable to store your player's position. Then
you can walk away from it and turn around the see pagoda build.

.. code-block:: python

    pos = player.world.pos
    # now walk away and turn around
    pagoda(pos)

Minecraft Diagnostic Info
-------------------------

You can turn on Minecraft Diagnostic information in the game by pressing
F3. This will show you the X, Y, Z coordinates of the block you are looking at.
Look at the block you want and it will highlight with a black outline. 
Then read off the coordinates from ``Targeted Block`` near the top right of 
the screen. Hit F3 again to turn off the diagnostic information.

Once you know the coordinates you can create a variable to hold them as 
follows:

.. code-block:: python

    # assumes you read X=200 Y=-10 Z=54
    pos = Vec3(200,-10,54)
    pagoda(pos)

The Selection Sign
------------------

When you place the ``Select`` sign in the world it will update the copy buffer
coordinates. The copy buffer start is always the coordinates at which you 
last dropped a sign. You can ask the world what its current status including 
copy buffer start and end is by tying ``world`` e.g.::

    In [10]: world
    Out[10]: 
    Minecraft Interactive World Builder status:
    copy buffer start: Vec3(x=620, y=71, z=-1623)
    copy buffer stop: Vec3(x=621, y=71, z=-1626)
    copy buffer size: Vec3(x=1, y=0, z=-3)
    paste point: Vec3(x=620, y=71, z=-1623)
    player: TransformerScorn
    player position: Vec3(x=620, y=72, z=-1625)
    player facing: Vec3(x=0, y=0, z=-1)

    In [11]: 

You can then copy and paste the start value and assign it to a variable like 
this:

.. code-block:: python

    pos = Vec3(x=620, y=71, z=-1623)
    pagoda(pos)

This is the easiest and most versatile way to discover a block's coordinates.
