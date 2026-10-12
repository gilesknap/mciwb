Levers and Switches
===================

A `Switch` is a lever, button, pressure plate or tripwire hook that calls a
Python function whenever it is switched on or off. It uses a `Monitor` (see
the previous tutorial) to watch the state of the switch.

Make a Light Switch
-------------------

This makes a lever that turns a block of glowstone on and off:

.. code-block:: python

    lamp = world.player.pos + Direction.NORTH * 3 + Direction.UP * 2

    def light(switch):
        if switch.powered:
            world.set_block(lamp, Item.GLOWSTONE)
        else:
            world.set_block(lamp, Item.GLASS)

    Switch(world.player.pos + Direction.NORTH * 2, Item.LEVER, light, name="light")

Walk up to the lever and flick it. Your function is passed the Switch object
and ``switch.powered`` tells you whether it is now on.

The supported switch types are levers, buttons (e.g. ``Item.STONE_BUTTON``),
pressure plates (e.g. ``Item.OAK_PRESSURE_PLATE``) and ``Item.TRIPWIRE_HOOK``.

To remove the switch from the world type:

.. code-block:: python

    Switch.remove_named("light")

The castle gate in `mciwb.demo.gate` uses a lever to open and close a
portcullis.
