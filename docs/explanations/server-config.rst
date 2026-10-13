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

The options of ``mciwb start`` (``--port``, ``--password``, ``--folder`` and
``--minecraft-version``) only take effect when it creates the server
container. ``mciwb stop`` removes the container, so while it exists
``mciwb start`` starts it with the settings it was created with, and warns
about any options that differ. Run ``mciwb stop`` first to change them.

.. _rcon_password:

The RCON password
-----------------

mciwb talks to the server over RCON, which needs a password. ``mciwb start``
sets the server's password, and the other commands (``shell``, ``run``,
``backup``, ``restore`` and ``render``) must use the same one. Every one of
these commands takes the password from the first of these that is given:

1. ``--password PASSWORD`` (or ``--passwd``) on the command line;
2. ``--password-file FILE`` (or ``--passwd-file``): the first line of FILE;
3. the ``MCIWB_PASSWORD`` environment variable;
4. ``default_pass``.

The default is fine for a server that only you can reach. To choose your
own password, put it in a file that only you can read, or set
``MCIWB_PASSWORD`` in your shell::

    echo 'my_password' > ~/.mciwb-password
    chmod 600 ~/.mciwb-password
    mciwb start --password-file ~/.mciwb-password
    mciwb run build.py --password-file ~/.mciwb-password

    export MCIWB_PASSWORD='my_password'
    mciwb start
    mciwb run build.py

.. warning::

    Avoid ``--password``: any user on the same computer can read a command
    line, for example with ``ps``. It still works, for compatibility.

mciwb never prints or logs the password, even with ``--debug``.

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
