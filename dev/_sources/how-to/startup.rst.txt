.. _startup:

Setup for each Tutorial
=======================

Quick Start
-----------

Once you have completed `../tutorials/01-setup` you have everything on
your computer required to run the remaining tutorials.

Each time you come back to your computer you need to set up your environment
again. The short description of what you need to do is:

- Start VSCode
- Start Minecraft client and connect to mciwb-server
- in the VSCode Terminal

  - ``source .venv/bin/activate``
  - ``mciwb shell --player <your player name>`` 


Full Startup Description
------------------------

The short version assumes that Minecraft Server and Docker Desktop have 
automatically started and that VSCode reopens the previous session.

Here is the long version in case any of the above are not true:

- turn on your computer and log in
- start Docker Desktop from the start menu

  - (this can be configured to start automatically at login)

- start VSCode from the start menu

  - normally VSCode will open in your my_world folder ready to go
  - if it doesn't then go to the menu bar and choose

    - File -> Open Recent -> ~/my_world
    - Terminal -> New Terminal

- On the terminal prompt in VSCode type:

  - cd $HOME/my_world
  - source .venv/bin/activate
  - mciwb start

- Open Minecraft Java client from the start menu

  - connect to the server mciwb-server

- Go Back to VSCode Terminal prompt and type:

  - mciwb shell --player <your player name>
  - (substitute <your player name> with your Minecraft player name)

- Arrange your windows so you can see both VSCode and Minecraft client

You now have everything you need to work through the tutorials.
