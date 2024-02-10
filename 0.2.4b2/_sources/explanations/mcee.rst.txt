.. _mcee:

Comparison with Minecraft Education Edition
===========================================

Introduction
------------

Minecraft Education Edition (MC EE) is a separate
version of Minecraft that is designed
for use in schools. It provides an in game editor for making python,
javascript or scratch code to create in and interact with Minecraft worlds.

When I started working on MCIWB, I took a brief look at MC EE. But dismissed it
as out of date and not well supported. That was a mistake. The Hacker News
discussion `here <https://news.ycombinator.com/item?id=35166874#35195105>`_
encouraged me to take another look.

This page details my findings on investigating MC EE in more depth and
discusses the differences between MC EE and MCIWB.

Minecraft Education Edition
---------------------------

The main reason for dismissing MC EE was that it was a paid subscription only
available to schools. However I found that I was able to quite easily get a
"commercial" license for around £10 per year. This is good value for money
given the amount of content that is available. See the ``DIRECT PURCHASE`` option
at https://education.minecraft.net/en-us/licensing.

Once you have the license there is a whole raft of education content
available, not just coding. The lessons run inside of the Minecraft worlds
in which you can explore and interact with the content. Here is a link
to the lessons available
https://education.minecraft.net/en-us/resources/explore-lessons.

I spent some time inside ``HOUR OF CODE 2021 (TIMECRAFT)`` and it does
introduce Python concepts in a pretty engaging mini game. I was disappointed
that the world did not use the latest vscode based editor and did encounter
a significant bug in the 2nd lesson that made it not work. I'm under the
impression that there is some work to do to update the lessons to work with
Microsoft's latest changes to the game engine.

My impression is that Microsoft are interested in the product and putting
effort into supporting it, so I thinks the issues above will get resolved.
I base this on:

- There are frequent
  `recent releases <https://educommunity.minecraft.net/hc/en-us/articles/360047556451-Minecraft-Education-Change-Log>`_
  of the product
- The in game editor has been updated to use Microsoft's popular developer tool
  vscode

Minecraft Interactive World Builder
-----------------------------------

MCIWB is a Free Open Source project that uses Minecraft's RCON interface too
send admin commands to a Minecraft Server. It therefore works with the most
recent version of Minecraft and is automatically compatible with new
releases of Minecraft. The Admin commands are pretty powerful and allow a
similar level of control to MC EE.

It is a single developer project at present but I'm open to contributions and
would like to get a bit of a community going around it.

Is there a place for MCIWB when the MC EE is available? I'd argue yes, See
my summary of advantages of each below.

MC EE Advantages
----------------

- It is a complete product with a lot of content and lessons available with
  support from a major software vendor.
- It is very low barrier to entry, install and run one app. Hit C and you
  are writing Python code.
- There are lots of pre created examples and tutorials here
  https://minecraft.makecode.com/
- For some children it will be what they are learning at school already.

MCIWB Advantages
----------------

- It is >500 times faster to execute code inside the game than MC EE.
- It is Free and Open Source.
- It is cross platform, runs on Linux and Mac and Windows. MC EE is Windows only.
- You get to use and learn standard developer tools such as vscode
- It uses the latest version of Python and can access all the standard libraries
  and PyPi packages. MC EE uses an in game Python engine that does not appear
  to have the standard libraries available.
- It works against any Minecraft Server, not just the MC EE server. This means
  you can combine it with server mods for unlimited options (currently Java only
  but Bedrock support could be added easily).
- You can create complex projects with multiple modules when you get advanced.
  MC EE is limited to a single file per project.
- You get an Interactive Python prompt to do immediate commands in as well as
  the ability to write modules and import them. This has ipython command
  line completion to help learn the commands.

Performance Results
-------------------

A headline difference is code execution speed. Microsoft could perhaps
fix this in the future.

For the performance test I made a tower in both MCIWB and MC EE. The code
places individual blocks and is not the most efficient way to do it in either
system, but demonstrates how fast loops and world updates run.

MC EE Tower Build code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def tower(start, size, height, item):
    for y in range(height):
        for x in range(size):
            for z in range(size):
                blocks.place(item, start.add(pos(0,y,z)))
                blocks.place(item, start.add(pos(size,y,z)))
                blocks.place(item, start.add(pos(x,y,0)))
                blocks.place(item, start.add(pos(x,y,size)))
        blocks.place(item, start.add(pos(x,y,z)))

    tower(world(0, 4, 0), 9, 10, COBBLESTONE)

To build a 9 by 9 block tower 10 blocks high in MC EE took over 80 seconds.
I could not do an accurate timing because the standard libraries for time
are not available.


.. raw:: html

    <iframe width="780" height="558" src="https://www.youtube.com/embed/DaizMyMxnhg" title="Minecraft Education Edition Tower Build" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>


MCIWB Tower Build code
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import logging
    from datetime import datetime

    from mciwb.imports import Direction, Item, Vec3, get_world

    def tower(start: Vec3, size: int, height: int, item=Item.COBBLESTONE):
        world = get_world()

        start_time = datetime.now()

        for y in range(height):
            for x in range(size):
                for z in range(size):
                    world.set_block(start + Vec3(0, y, z), item)
                    world.set_block(start + Vec3(size, y, z), item)
                    world.set_block(start + Vec3(x, y, 0), item)
                    world.set_block(start + Vec3(x, y, size), item)
            world.set_block(start + Vec3(x, y, z), item)

        diff_time = datetime.now() - start_time

        logging.warning(f"tower took {diff_time.total_seconds()} seconds")

    tower(Vec3(632, 73, -1724), 9, 10, Item.COBBLESTONE)

To build a 9 by 9 block tower 10 blocks high in MCIWB took 0.14 seconds.
That is more than 550 times faster than MC EE.

.. raw:: html

    <iframe width="780" height="680" src="https://www.youtube.com/embed/Pbmkct4KNqU" title="MCIWB Tower Build" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

Another Alternative
-------------------

If you prefer the MC EE python API and don't want to pay for a license then
there is https://github.com/zhuowei/RaspberryJuice. This uses the Java server
mod Bukkit to create a similar API to EE.

This would also have the advantage that you get to use a real version of
Python and your choice of developer tools.

I've not tried this so if anyone knows more details then please let me know
about it in an Issue or Pull Request.