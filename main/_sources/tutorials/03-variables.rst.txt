Python Variables
================

Introduction
------------

We now have everything ready to start learning some Python!

.. note:: 
    There are many other
    excellent Python beginner's tutorials available for free on the internet,
    such as:

        https://python.land/python-tutorial

    My tutorials are going to focus on quickly getting into interacting with the
    world of Minecraft. We won't be going into programming theory 
    to any great degree. Therefore, a tutorial like python.land will 
    be needed to fill in the background if you want to get serious with Python.

Follow along with these tutorials by having both you Minecraft client and 
your VSCode windows visible on your screen. You should try out the Python
commands shown here and feel free to experiment.

Each time you come back to work on these tutorials you can get yourself
ready to go by following `startup`.

Variables, Types and Operators
------------------------------

Variables provide a place to hold some bit of data for use inside of a
computer program. They have the following properties:

- Name: a name that is used to identify the variable.
- Value: the data that the variable holds.
- Type: the type of data that the variable holds.

Operators are used to make changes to variables. For example the ``=`` operator
assigns a value to a variable. In Python we can quickly create a variable
using assignment. Try out the commands below:

.. list-table:: Create some variables
   :widths: 50 25 20 60
   :header-rows: 1    
   
   * - Command
     - Name
     - Value
     - Type
   * - birth_year = 1964
     - birth_year
     - 1964
     - int (a whole number)
   * - my_height = 1.94
     - my_height
     - 1.94
     - float (a decimal number)            
   * - my_name = "giles"
     - my_name
     - "giles"
     - str (a string of characters)

Now you can use the ``print`` function to see the value of the variables::

    In [1]: birth_year = 1964

    In [2]: my_height = 1.94

    In [3]: my_name = "giles"

    In [4]: print(birth_year, my_height, my_name)
    1964 1.94 giles

Let's try another operator ``-`` or minus. This operator subtracts the value of
one variable from another. It behaves just like ``-`` in basic arithmetic.
Try out the commands below::

    In [6]: age = 2022 - birth_year

    In [7]: age
    Out[7]: 58

This makes a calculation from the value 2022 and the value of the variable
``birth_year`` and assigned it to variable ``age``. Note that I did not
use ``print`` to see the value, I simply typed the variable name ``age``,
Interactive Python will always print the value returned by the last
input command.

Variables in Minecraft
----------------------

MCIWB provides some built in variables that you can use. The most important
is called ``world`` and it is your entry point into most of the functions
provided by the library.

World is a special variable called an ``object`` which can have many values
stored in its ``properties``. Objects can also have ``methods`` which 
execute code.

One property of ``world`` is ``player`` and a property of ``player`` is ``pos``
which holds the player's current position.

Thus you can access the player's location like this::
    
    In [10]: world.player.pos
    Out[10]: Vec3(x=633, y=73, z=-1665)

Try moving your player around and see how the position changes. 

.. note::

    You will notice that the position is reported as a type of variable 
    called Vec3. This holds the Minecraft coordinates that you may be 
    familiar with if you have used e.g. the teleport command.

    For lots of detail on what this all means see `coordinates`.

    However, for the moment you may prefer to just work through the first 
    few tutorials and come back to that level of detail later on.

An example of a ``method`` on ``world`` is ``set_block`` which will place
a block in a particular position. Make sure your player is standing
on the flat area of sand and try this::
    
    world.set_block(pos, Item.IRON_BLOCK)

Your player should have been bumped out of their position and if you turn
around you will see an iron block.

(I'm no longer showing the In[] prompt in the examples so you can use
copy and paste to easily try these examples)

OK, let's make an iron golem! Copy and paste these commands into the 
Python terminal::

    world.set_block(pos, Item.IRON_BLOCK)
    arms = pos + Direction.UP
    world.set_block(arms, Item.IRON_BLOCK)
    world.set_block(arms + Direction.EAST, Item.IRON_BLOCK)
    world.set_block(arms + Direction.WEST, Item.IRON_BLOCK)
    world.set_block(arms + Direction.UP, Item.CARVED_PUMPKIN)

Yay! You can paste again to create another one.

.. image:: ../images/golem.png
    :alt: Server Address
    :width: 500px

(See "Creation" in this article https://minecraft.fandom.com/wiki/Iron_Golem
if you don't know about making iron golems)

How does this work? We use ``set_block`` to place all the necessary blocks
in the world. We use the variables ``pos`` (which we set earlier) and ``arms``
to control where those blocks are placed.

``Direction`` provides values that will move a position by one block in a 
particular direction when added/subtracted to/from that position. 

So, first we place the golem's feet at ``pos``.
Then we move Up one block from the position ``pos`` to the arm level of 
the golem and save  that position in ``arms``. Now we can move east
and west from ``arms`` to make the arms and Up to make the head.

