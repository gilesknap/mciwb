Modules and Packages
====================

In this tutorial we will start to use vscode to develop a Python package 
for making buildings in the game. We will be starting with 
the pagoda building from the previous tutorial and here we will also 
go into the detail of how the pagoda function works.

Preparing VSCode
----------------

VSCode has some great extensions for working with Python files. Let's make sure 
those are installed now. 

Click on the extensions Icon and type ``pylance``. Click on ``install`` for 
the two Microsoft extensions listed.

.. figure:: ../images/pylance.png
   :alt: pylance
   :align: center
   :width: 600px

   Adding Extensions

Getting a Bash Prompt
---------------------

We are going to use some bash (zsh) commands here so lets open a second terminal
in VSCode so that we can have a bash prompt but also keep our Python shell
prompt open.

Right click in the VSCode terminal area and select ``Split Terminal``

.. figure:: ../images/split_term.png
   :alt: split_terminal
   :align: center
   :width: 600px

   Splitting the Terminal

You can grab the dividing line between the two terminals and drag it to the
right with your mouse. This makes the Python terminal bigger and the 
Bash terminal smaller. Then your terminal area of VSCode should look like 
this:

.. figure:: ../images/terminals.png
   :alt: split_terminal
   :align: center
   :width: 900px

   Python prompt and Bash prompt

Create a Package and a Module
-----------------------------

A python module is simply a file with a ``.py`` extension containing Python
code.

A package is simply a folder (directory) that contains python modules.

We are going to create a package called ``buildings`` with a single module
to start with called ``pagoda``. Type the following commands at the
bash prompt::

    cd $HOME/my_world
    mkdir buildings
    cd buildings
    touch __init__.py
    code pagoda.py

The steps above were:

- Change working directory to ``$HOME/my_world`` which is our VSCode work folder.
- Make a new directory called ``buildings``, this is our new package
- Create an empty file called ``__init__.py`` in the ``buildings`` directory. 
  This is a special file name that tells Python that this directory is a 
  Python package.
- Tell vscode to open a new file called ``pagoda.py`` in the editor window

Now we can paste our pagoda function into the editor window and save it with
Menu -> File -> Save (or Ctrl+S is a shortcut to save the current file).
Use this slightly modified version of the pagoda function:

.. literalinclude :: ../../src/demo/pagoda2.py
   :language: python

To try using this function you can now type the following command in the
iPython prompt:

.. code-block:: python

    from buildings.pagoda import build_pagoda
    build_pagoda(world.player.pos)

That should build a little pagoda around your player. You can break some 
blocks to make a door for you to exit the pagoda.


How it Works
------------

Let's take a look at all of the new things that we used in our ``build_pagoda``
function.

import
~~~~~~

.. code-block:: python
   
   from mcwb.api import polygon

import allows us to access code from other modules. The polygon function is
implemented in a module called ``api`` in a package called ``mcwb``. 
We will frequently use code from two packages called ``mcwb`` (Minecraft world
builder) and ``mcipc`` (Minecraft inter-process communication). These are two
packages that ``mciwb`` is built on top of.

One of the greatest features of Python is its extensive library of built in
packages. For example the maths package contains functions for doing math.
e.g.

.. code-block:: python

    from math import sqrt, cos, sin

The polygon function itself is implemented using some of these math functions.
Luckily, you don't need to know anything about the mathematics of polygon
construction because the polygon function has done all that for you!

.. code-block:: python
   
   from mciwb import Direction, Item, get_client

The 2nd import function is importing things from ``mciwb``. Direction and
Item are already familiar, we need to import them here because we are 
writing a new module called ``pagoda``. When working on the iPython
prompt we are already in the ``mciwb`` so we can see Direction and Item
already.

get_client
~~~~~~~~~~

Whenever we call any functions in the ``mciwb`` or ``mcipc`` packages we need
a client object. This represents a connection to our Minecraft server. 

The get_client function obtains a client object for you to use. Here we 
assign it into the variable ``c`` and pass ``c`` to the polygon function.

Advanced programmers may want to read up on how this is a thread-safe
client object (`mcipc`).

comments
~~~~~~~~

At the beginning of ``build_pagoda`` we have a block comment. It uses the 
triple quotes ``"""`` which allow you to write a block of text that is not
interpreted as Python code.

Good programmers will usually add a comment block at the top of their
functions.

extra parameters to ``range``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
