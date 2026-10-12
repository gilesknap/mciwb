[![CI](https://github.com/gilesknap/mciwb/actions/workflows/ci.yml/badge.svg)](https://github.com/gilesknap/mciwb/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/gilesknap/mciwb/branch/main/graph/badge.svg)](https://codecov.io/gh/gilesknap/mciwb)
[![PyPI](https://img.shields.io/pypi/v/mciwb.svg)](https://pypi.org/project/mciwb)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# mciwb

Minecraft Interactive World Builder.

This project is intended as a fun way to learn the Python Programming Language.

Experienced Python programmers can also use this library to create
Minecraft worlds with interactive Python features.

What            | Where
:---:           | :---:
Source          | <https://github.com/gilesknap/mciwb>
Install         | `pip install git+https://github.com/gilesknap/mciwb.git`
Docker          | `docker run --rm -it --network host ghcr.io/gilesknap/mciwb:latest shell`
Documentation   | <https://gilesknap.github.io/mciwb>
Releases        | <https://github.com/gilesknap/mciwb/releases>


## Quick Start

To get started learning Python, see
[Introduction](https://gilesknap.github.io/mciwb/main/tutorials/00-prereq.html)

For existing Python developers, see
[API documentation](https://gilesknap.github.io/mciwb/main/_api/mciwb.html)

In short: start a local Minecraft server and build in it from a script:

```bash
mciwb start            # a Minecraft 26.3 server in docker, on localhost
mciwb run build.py     # run a build script, or `mciwb shell` for IPython
```

where `build.py` uses the `world` object and the names from `mciwb.imports`:

```python
pos = Vec3(632, 73, -1658)
world.set_block(pos, Item.GOLD_BLOCK)
polygon(get_client(), pos + Direction.EAST * 10, height=5, diameter=7)
```

## Example Build

The pagoda and castle with working portcullis were all created programmatically
with Python and the current version of MCIWB.

https://github.com/gilesknap/mciwb/assets/964827/026b3551-f514-403a-bebe-8d168c7170b0

An earlier video shows the castle being built; the source code for the village
is in [src/mciwb/demo/village.py](https://github.com/gilesknap/mciwb/blob/main/src/mciwb/demo/village.py).

https://user-images.githubusercontent.com/964827/225131152-677da86e-a6b5-44c2-baf1-8da2eb4e221b.mov

## Goals

Minecraft Interactive World Builder's goals are:

 - Use Python to create anything inside of Minecraft worlds.
 - Call Python code when events occur inside the world.
 - Use an iPython prompt to interact with the world by typing Python commands
 - Have your player inside the world execute Python code by placing command
   signs or activating switches/levers with Python actions.

All instructions on how to set up a Minecraft Server and the Python developer
environment are included. There are step by step tutorials to
introduce Python Programming and the features of Minecraft Interactive World
Builder.

**Note:** this is a work in progress. There are now enough tutorials to learn
the fundamentals of Python and enough functionality to have some fun
interacting with Minecraft from Python code.

## Credits

This project would not be possible without [mcipc](https://github.com/conqp/mcipc/),
which provides the client library for Minecraft RCON.

<!-- README only content. Anything below this line won't be included in index.md -->

See https://gilesknap.github.io/mciwb for more detailed documentation.
