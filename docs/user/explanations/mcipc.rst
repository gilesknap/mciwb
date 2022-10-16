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
https://minecraft.fandom.com/wiki/Commands and let you do pretty much
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

