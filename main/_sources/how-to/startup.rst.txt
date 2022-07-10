.. _startup:

Setup for each Tutorial
=======================

Once you have completed `../tutorials/01-setup` you have everything on
your computer required to run the remaining tutorials.

At the start of each session you would need to prepare as follows:

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

  - connect to the server mciwb_server

- Go Back to VSCode Terminal prompt and type:

  - mciwb shell --player <your player name>
  - (substitute <your player name> with your Minecraft player name)

- Arrange your windows so you can see both VSCode and Minecraft client

You now have everything you need to work through the tutorials.
