.. _mcipc:

MCIPC Client object
===================

.. note::

    Advanced topic!

get_client
----------

The function ``get_client()`` gets hold of an mcipc client object. mcipc is 
the underlying Python project that we use to communicate with the Minecraft.

Minecraft provides a remote control mechanism called RCON that gives you
exactly the same set of admin commands that you may be familiar with if you 
have player a lot of Minecraft. Those commands are documented here
https://minecraft.wiki/w/Commands and let you do pretty much
anything in the world.

Note that due to tab completion in Interactive Python it is quite easy to
use the client object to discover what commands you can call.

For Interactive World Builder I have deliberately provided a simplified 
interface to make 
learning Python easier. But with ``mcipc`` you can do anything that RCON
allows.

The documentation for the underlying mcipc library is here
https://mcipc.readthedocs.io/en/latest/

Thread Safe
-----------

Interactive World Builder often performs background tasks. For example,
it is always monitoring the world for action signs even while the user 
is executing other code from the Python console. To make a single program
execute more than one thing at once we need to use threads. 

You can get help from Interactive World Builder in using threads by using 
the Monitor class. TODO reference.

The important thing about ``get_client()`` is it will always deliver you a
separate client object per thread of execution. If it did not do so then
the communication to RCON would get tangled up between threads and fail to
work.

Other RCON clients
------------------

The Minecraft server keeps one output buffer for all of its RCON
connections. It empties the buffer before running a command and returns
what is in it afterwards, so when two connections run commands at the same
moment, a reply can come back empty, or with the other connection's output
in it. mciwb's threads take turns, so this only happens when another
program uses RCON at the same time, e.g. a server dashboard that polls
``list``: about one command in 10000.

This can not be fixed on the client side, so mciwb's ``Client`` checks the
replies of the commands it uses most, which are safe to send twice:
``setblock``, ``fill``, ``clone`` and ``loot`` (which reads blocks). If the
reply does not say that the command ran, the command is sent again (up to
5 times, with a warning in the log), and only the command's own output is
returned. `mciwb.builders.ground_heights` and ``foundation`` check each
column in the same way.

Other commands are sent once, because some are not safe to send twice: a
garbled reply to ``summon`` or ``give`` does not mean that it failed. For a
command that is safe to repeat, pass the reply you expect to ``world.cmd``::

    world.cmd("gamerule advance_time", expect=r"Game rule \S+ is currently set to \S+")

``world.cmd`` returns the server's reply as text, errors included. Since
Minecraft 1.21.11 game rules have snake case names (``advance_time``, not
``doDaylightCycle``), and since 26.1 ``time query`` takes a timeline:
``time query day`` gives the ticks into the current day (it was
``time query daytime``) and ``time query day repetition`` the number of days.
