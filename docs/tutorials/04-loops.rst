Loops
=====

Introduction
------------

For this tutorial we are going to write code that will create a Nether
Portal. If you don't know about Nether Portals, you can read about them
here: https://minecraft.fandom.com/wiki/Nether_portal.

A Nether Portal requiresa minimum of 14 blocks. Now we could use a similar
approach as that for the iron golem in the previous tutorial. But that would
be a lot of typing. So instead we'll take a look at Python ``for loops``.

Backups
-------

Before we proceed I recommend that you learn about making backups of the
world. That way we can experiment as much as we like and restore our 
world back to a good state. Go and read `backups` and then come back to
this tutorial.

For Loops
---------

For loop provide the mechanism to repeat a block of code a number of times.
Try the following code in your Python Terminal, note that the second line
is indented by 4 spaces, you can use the tab key to do this indent.

.. code-block:: python

    for i in range(10):
        print("hello")
        print(i)

The ``range`` function creates a list of numbers from 0 to 9 (i.e. it starts
at 0 and does 10 numbers). Then the ``for`` loops through those numbers for 
each of them it sets the variable i equal to the current number in the list and
then executes its code block.

An important concept in Python a block of code is declared by indenting it 
by 4 spaces. So the two print functions are inside of the block controlled
by the for loop. This is why both of those print functions get called 10
times each.

.. note::

    In the above code we used a ``string`` of characters which was the word 
    "hello". Python variables with this type of data are called ``str`` and
    you can make strings by enclosing your text in quotes as we did above
    for "hello".

Nested Loops
------------

You can have loops inside of loops which is called a nested loop. Try the
following:


.. code-block:: python

    for i in range(3):
        print("i is ", i)
        for j in range(3):
            print("    j is ", j)
            print("    j times i is ", j * i)

This is two loops inside of each other, each loops 3 times and so the total
number of times the code block is executed is 3 time 3 = 9. See if you can
work out why the output looks like it does.

.. note::
    
    We used a new operator here. The ``*`` operator is used to multiply two
    numbers together. It is just the same as multiplication in basic 
    arithmetic. Most computer languages use the star symbol to signify
    multiplication. This is because there is no multiply symbol on 
    computer keyboards since they evolved from typewriter keyboards!

    Similarly the symbol ``/`` is used to represent divide by.

Nether Portal
-------------

We have enough knowledge now to make loops to build a nether portal.
Try the following code in your Python Terminal:



.. code-block:: python

    pos = world.player.pos

    for x in range(4):
        # bottom row
        world.set_block(pos + Direction.EAST * x, Item.OBSIDIAN)
        # top row
        world.set_block(pos + Direction.EAST * x + Direction.UP * 4 , Item.OBSIDIAN)

    for y in range(4):
        # left side 
        world.set_block(pos + Direction.UP * y, Item.OBSIDIAN)
        # top row
        world.set_block(pos + Direction.UP * y + Direction.EAST * 3 , Item.OBSIDIAN)

    c = get_client()
    c.give("TransformerScorn", Item.FLINT_AND_STEEL)

.. image:: ../images/portal.png
    :alt: nether portal
    :width: 500px

The most important thing to note here is that I used multiplication on the 
Direction values to add them multiple times to a starting position. This means
that:

.. code-block:: python

    # bottom row
    world.set_block(pos + Direction.EAST * x, Item.OBSIDIAN)

places an obsidian block at the position offset from pos in an Easterly 
direction. How much it is offset is determined by the value of x. We know 
that the for loop is looping over values of x from 0 to 3. So we have::

    Loop 1 with x = 0
        set block at pos
    Loop 2 with x = 1
        set block at 1 step EAST from pos
    Loop 3 with x = 2
        set block at 2 steps EAST from pos
    Loop 4 with x = 3
        set block at 3 steps EAST from pos

For the top row we do the same thing but also add 4 steps upwards. The 
loop over y does a similar thing for the two sides of the portal.

See if you can experiment with creating different sizes of nether portals.
Maybe you can create other shapes? If you used a nested loop you could make 
steps for example?


Flint and Steel
---------------

Did you notice the ``c.give()`` at the end of the code snippet? This handed
a Flint and Steel to the player. You can equip this in your hand and ignite
your portal by left clicking in the interior of the portal. It should then
look like my picture above and you can jump through to see the Nether.

MCIPC Client object
-------------------

.. note::

    This is an advanced feature and if you are new to Python then don't
    worry about it for the moment. You can come back to this at a later
    date.

The function ``get_client()`` gets hold of an mcipc client object. mcipc is 
the underlying Python project that we use to communicate with the Minecraft.

Minecraft provides a remote control mechanism called RCON that gives you
exactly the same set of admin commands that you may be familiar with if you 
have player a lot of Minecraft. Those commands are documented here
https://minecraft.fandom.com/wiki/Commands and let you do pretty much
anything in the world.

Note that due to tab completion in Interactive Python it is quite easy to
use the client object to discover what commands you can call.

For MCIWB I have deliberately provided a simplified interface to make 
learning Python easier. But with ``mcipc`` you can do anything that RCON
allows.

The documentation for the underlying mcipc library is here
https://mcipc.readthedocs.io/en/latest/

