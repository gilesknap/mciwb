Minecraft Server Config
=======================

If you have experience of Minecraft Servers and want to make changes to
the defaults used by MCIWB then read on.

Configuration of the default server
-----------------------------------

Your server installation is created in ``$HOME/mciwb-server`` if you want to 
change the world settings then you can go into that folder and alter the
``server.properties``.

Perform the following to pick up the changes::

    mciwb stop
    mciwb start

.. _minecraft_version:

Minecraft version
-----------------

``mciwb start`` runs the Minecraft Java Edition release that this version of
MCIWB was tested with, currently **26.3**. This is the release that the
``Item`` enum of block and item names comes from (``mcwb.MINECRAFT_VERSION``).
The server runs in the ``itzg/minecraft-server`` container image, see
``MINECRAFT_VERSION`` and ``SERVER_IMAGE`` in ``mciwb/server.py``.

Your Minecraft client must run the same release as the server. If the
Minecraft Launcher's "Latest release" is newer, add an installation for
release 26.3 in the Launcher's "Installations" tab and play with that.

To run a different release, pass it to ``mciwb start``. ``mciwb stop``
removes the server container, so the new release is used the next time the
server starts::

    mciwb stop
    mciwb start --minecraft-version 26.3

Your world is kept in ``$HOME/mciwb-server`` and is upgraded when a newer
release opens it. Worlds cannot be downgraded, so take a backup first
(see `backups`).

Running your own Server
-----------------------

TODO


.. _my_server_backups:

Backups of your own custom server
---------------------------------

TODO
