Backup and Restore
==================

The default MCIWB Minecraft server provides a backup and restore facility
described below.

If you are an advanced Minecraft user running your own server instead of the
default provided by MCIWB then you will need some extra config to make backups
work. Jump to `my_server_backups` to see how to do this.

.. _backups:

Backups of mciwb-server
-----------------------

Backups provide a way to save our world to a file when we are happy with it.
Then we are protected from loosing our work if we make a programming error.
When things go wrong we can just restore back to a previous version of the
world.

To backup the world type this at the Python Prompt::

    world.backup()

This will create a backup with a name that is the current date and time. You
can also specify a name if you want. Let's do that now, naming the backup
after the flat area that we made in `signs_try`::

    world.backup('flat-area-backup')

It is better not to use spaces in backup names so I used dash to separate
the words.

You can also make a backup from the ``bash`` prompt, without the Python
Prompt::

    mciwb backup --backup-name my-second-backup

Leave out ``--backup-name`` to name the backup with the current date and time.
If the server is running, ``mciwb backup`` connects to it over RCON, tells it
to save the whole world to disk (``save-all flush``) and pauses saving until
the backup is complete, so the backup is consistent. If the server is not
running, the world folder is simply copied.

``mciwb backup`` looks for the server on port 20100 with the password
``default_pass``, the defaults of ``mciwb start``. If you started your
server with a different ``--port`` or ``--password``, give the same options
to ``mciwb backup``::

    mciwb backup --port 20101 --password my_password

If the password is wrong, ``mciwb backup`` warns you and copies the world
without asking the server to save it first. Use ``--folder`` and
``--backup-folder`` if your server or backups are not in the default folders.

Now lets do a restore. You can first have your player dig a hole in our
flat area, this is to make a change that we don't want to keep.
Then exit the Python Prompt using 'Ctrl+D'. Now we are back
at the ``bash`` prompt and we can look in the backups folder to see our
list of backups e.g

This command::

    ls $HOME/mciwb-backups

Shows my backup files like this::

    22-07-13.06.26.01.zip  flat-area-backup.zip  my-second-backup.zip

Your backups are stored in a folder called $HOME/mciwb-backups and ``ls`` is
a terminal command that lists the contents of that folder.

Note
that the backup files all end in ``.zip``. One of them is dated but you also
see the ``flat-area-backup.zip`` and ``my-second-backup.zip`` files that we
named explicitly.

Now you can restore from backup with the following command::

    mciwb restore flat-area-backup

The output should look something like this::

    INFO:   Stopping Minecraft Server mciwb-server ...
    INFO:   Restored /home/giles/mciwb-server/world from /home/giles/mciwb-backups/flat-area-backup.zip
    INFO:   Launching existing Minecraft server in /home/giles/mciwb-server
    INFO:   Launching Minecraft Server 'mciwb-server' on port 20101 ...
    INFO:   waiting for server to come online ...
    INFO:   Server mciwb-server is online on port 20101


The ``mciwb restore``
command can be given the name of the backup to restore or if you specify no
name it will restore the most recent backup.

When the server restarts you can reconnect your client. You should see that
the hole you dug has disappeared.

Note that the bash terminal has a history of commands. So to reconnect to
your client you just need to hit up arrow a couple of times until you see the
command that you typed earlier::

    mciwb shell --player <player_name>

and then hit enter. This saves some typing. You'll find that most command line
tools have recall and editing of previous commands, including **iPython**.
This is one of the reasons that a command line interface is a good thing!
