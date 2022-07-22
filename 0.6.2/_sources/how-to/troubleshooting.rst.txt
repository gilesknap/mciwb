.. _troubleshooting:

Troubleshooting
===============

Minecraft Server wont start
---------------------------

If you see this error::

    docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))

This implies that the docker engine is not running. Use the start
menu to launch Docker Desktop and retry once it is running.

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

    docker logs mciwb-server