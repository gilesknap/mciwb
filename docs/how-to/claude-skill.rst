.. _claude_skill:

Build with Claude Code
======================

mciwb comes with a `Claude Code <https://claude.com/claude-code>`_ skill,
``minecraft-build``, that teaches Claude how to build in your Minecraft world
with mciwb. Ask Claude for a build, e.g. *"build a stone watchtower 20
blocks north of me, my player is called steve"*, and it follows this loop:

1. make sure the server is running (``mciwb start``)
2. back up the world (``mciwb backup``)
3. survey the site: where the players are, the ground height and what the
   ground is made of, and an image of the area
4. write a Python build script, starting from the skill's template and
   using the builders (see :doc:`builders`) for roofs, arches, stairways,
   roads and foundations that follow the terrain
5. run it with ``mciwb run``
6. render the build to an image (see `render_howto`) and look at it
7. fix the script and run it again until the build is right, or restore the
   backup (``mciwb restore``) if it went badly wrong

The skill is in the mciwb repository, in
`.claude/skills/minecraft-build
<https://github.com/gilesknap/mciwb/tree/main/.claude/skills/minecraft-build>`_:

``SKILL.md``
    The workflow and the rules (coordinates, ground levels, block names,
    performance, safety). Claude reads it when you ask for a build.
``reference.md``
    The build API and the builders, schematics, render options, performance
    numbers and troubleshooting, which Claude reads when it needs them.
``scripts/survey.py``
    Surveys a site. Run it yourself with
    ``SURVEY="X Z RADIUS" mciwb run survey.py`` or
    ``mciwb run survey.py --player NAME``. Without the world files (a
    server on another machine) it finds the ground with Minecraft's
    heightmaps and reads only the blocks near it over RCON.
``scripts/build_template.py``
    A template build script: it clears the site, refuses to build over a
    player, builds a small hut on a foundation with a gable roof, renders it
    to a PNG beside the script and checks the blocks, reading the roof's
    stairs back with ``Schematic.from_world`` because the images draw stairs
    as full blocks.

Install the skill
-----------------

First install mciwb so that the ``mciwb`` command is on your path (see
:doc:`../tutorials/installation`), and set up Podman as in `podman`. Then either:

Use it in this repository
    Open Claude Code in a clone of mciwb. Claude Code finds project skills
    in ``.claude/skills`` by itself.

Use it in every project
    Copy or link the skill into your personal skills folder,
    ``~/.claude/skills``::

        git clone https://github.com/gilesknap/mciwb.git
        mkdir -p ~/.claude/skills
        ln -s "$PWD/mciwb/.claude/skills/minecraft-build" ~/.claude/skills/

    A link keeps the skill up to date when you ``git pull`` mciwb. Copy the
    folder instead (``cp -r``) to keep a version that you can change.

Use it in one other project
    Copy the folder into that project's ``.claude/skills``, and commit it
    so everyone working on the project has it.

Claude decides to use the skill when you ask it to build something in
Minecraft. You can also start it yourself by typing ``/minecraft-build``
followed by what you want built.

Claude runs ``mciwb`` commands with its Bash tool, so it asks before each
one unless you allow them, e.g. with ``"Bash(mciwb *)"`` in the
``permissions.allow`` list of ``.claude/settings.json``. That also allows
``mciwb restore``, which replaces the world with a backup, so leave it out if
you prefer to approve those yourself.

Tips
----

- Start the server with ``mciwb start --world-type flat`` for a flat world
  to experiment in: its ground is at y = -61, so builds start at y = -60.
- Tell Claude your player name, so it can survey around you and keep its
  builds away from where you stand.
- Ask Claude to show you the rendered images: they are ordinary PNG files.
- Ask Claude to save a piece you like as a ``.schem`` file, to place copies
  of it elsewhere, turned or mirrored, or to open it in WorldEdit.
- Backups are in ``~/mciwb-backups``. ``mciwb restore NAME`` brings one back.
