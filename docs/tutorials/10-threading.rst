Running Code in the Background
==============================

So far every command you typed ran to completion before you could type the
next one. Sometimes you want code that keeps running in the background while
you carry on playing: a door that opens when you walk up to it, or a pyramid
that turns to face you.

MCIWB provides the `Monitor` class for this. A Monitor runs a function over
and over again, a few times a second, in its own **thread**. A thread is a
separate path of execution that runs at the same time as your iPython prompt.

A Simple Monitor
----------------

Try this in iPython. It puts a gold block under your feet wherever you walk:

.. code-block:: python

    def gold_path():
        pos = world.player.pos
        world.set_block(pos + Direction.DOWN, Item.GOLD_BLOCK)

    Monitor(gold_path, name="gold")

Now walk around in Minecraft. To stop it type:

.. code-block:: python

    Monitor.stop_named("gold")

The parameters of Monitor are:

- the function to call
- ``params``: a tuple of arguments to pass to the function (optional)
- ``name``: a name so that you can stop the monitor later
- ``poll_rate``: how many seconds to wait between calls (default 0.2)
- ``once``: set to True to call the function just once, in the background

A one off background job is useful for slow builds that you don't want to
wait for:

.. code-block:: python

    from mciwb.demo.pagoda import build_pagoda

    Monitor(build_pagoda, params=(world.player.pos,), once=True)

Things to Know About Threads
----------------------------

- Each thread needs its own connection to the Minecraft server. Monitor
  sets this up for you. Always call ``get_client()`` inside your function
  to get the connection for the current thread.
- If your function raises an error, the error is logged and the Monitor
  keeps going.
- ``Monitor.stop_all()`` stops every monitor. Leaving ``mciwb shell`` does
  this for you.

The demo `mciwb.demo.follow` uses a Monitor to make a pyramid of pumpkins
that always faces the player.
