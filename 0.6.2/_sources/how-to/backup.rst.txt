Backup and Restore
==================

The default MCIWB Minecraft server provides a backup and restore facility
described below.

If you are running your own server it is useful to add backup and restore 
capability and MCIWB supports this with a little configuration. Jump to
`my_server_backups` to see how to do this.

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
can also specify a name if you want. Let's do that now::
    
    world.backup('my-first-backup')

It is better not to use spaces in backup names so I used dash to separate
the words.

Now lets do a restore. You can first have your player dig a hole in our
flat area then exit the Python Prompt using 'Ctrl+D'. Now we are back
at the terminal prompt and we can look in the backups folder to see our
list of backups e.g::

    
    (.venv) [giles@ws1 mciwb]$ ls $HOME/mciwb-backups
    22-07-13.06.26.01.zip  22-07-13.06.34.06.zip  flat-area-backup.zip

    (.venv) [giles@ws1 mciwb]$ mciwb restore flat-area-backup
    INFO:   Stopping Minecraft Server mciwb-server ...
    INFO:   Restored /home/giles/mciwb-server/world from /home/giles/mciwb-backups/flat-area-backup.zip
    INFO:   Launching existing Minecraft server in /home/giles/mciwb-server
    INFO:   Launching Minecraft Server 'mciwb-server' on port 20101 ...
    INFO:   waiting for server to come online ...
    INFO:   Server mciwb-server is online on port 20101

    (.venv) [giles@ws1 mciwb]$ 
    
You backups are stored in a folder called $HOME/mciwb-backups and ``ls`` is
a terminal command that lists the contents of that folder. The ``mciwb restore``
command can be given the name of the backup to restore or if you specify no
name it will restore the most recent backup.

When the server restarts you can reconnect your client. You should see that
the hole you dug has disappeared.

Note that the bash terminal has a history of commands. So to reconnect to
your client you just need to hit up arrow a couple of times until you see the
command that you typed earlier::

    mciwb shell --player <player_name>

and then hit enter. This saves some typing. You'll find that most command line
tools have recall and editing of previous commands, including the iPython.

