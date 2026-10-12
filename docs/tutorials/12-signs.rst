Action Signs
============

In `signs_try` you used the ``select`` and ``paste`` action signs. You can
add your own action signs that call a Python function when your player
places them in the world.

When you place an action sign in front of your player, MCIWB reads the text
on it and calls the function for that text. The function is passed the
position that the sign points at:

- a standing sign points at the block below it
- a sign on a wall points at the block behind it

The sign is then removed from the world.

Make a Pagoda Sign
------------------

This adds a "pagoda" sign that builds a pagoda wherever you place it:

.. code-block:: python

    from mciwb.demo.pagoda import build_pagoda

    def pagoda_sign(pos):
        build_pagoda(pos, width=10)

    world.signs.add_sign("pagoda", pagoda_sign)
    world.signs.give_signs()

``give_signs`` puts one of each action sign that you don't already have into
your inventory. Place the "pagoda" sign on the ground in front of you, within
3 blocks.

To stop responding to a sign:

.. code-block:: python

    world.signs.remove_sign("pagoda")

You can also place an action sign from code, which is useful for testing:

.. code-block:: python

    get_client().setblock(world.player.pos + world.player.facing, Signs.sign_block("pagoda"))

Building Walls with Signs
-------------------------

`WallMaker` uses two action signs to build walls. Place a "start_wall" sign
where the wall begins, then an "end_wall" sign for each corner:

.. code-block:: python

    maker = WallMaker(Wall(height=4, item=Item.STONE_BRICKS))

Use ``maker.remove()`` to remove the signs again. See `Wall` for how to make
walls with a fancy profile, such as battlements.
