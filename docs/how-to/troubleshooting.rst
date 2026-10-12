.. _troubleshooting:

Troubleshooting
===============

Minecraft Server wont start
---------------------------

If you see this error::

    ERROR:  No Podman socket found (looked for CONTAINER_HOST, then /run/user/1000/podman/podman.sock, /run/podman/podman.sock).
    Start the Podman service with:
        systemctl --user enable --now podman.socket

or this one::

    ERROR:  Podman service at unix:///run/user/1000/podman/podman.sock is not responding

This implies that the Podman service is not running. On Linux and Windows
(WSL2), start it with the command in the message and retry. On MacOS, start
the Podman machine from Podman Desktop (or with ``podman machine start``) and
check that ``CONTAINER_HOST`` is set as described in `podman`.

Problems with Player Connection
-------------------------------

If you see a message like this::

    ERROR:        failed to give signs to player, player <player> left

This means MCIWB could not find your player. It is worth checking that you 
have your player name correct. 

TODO good way to look for your name.

Minecraft Server Logs
---------------------

You can also get the logs from the attempted start of the server with this 
command on the Terminal::

    podman logs mciwb-server
