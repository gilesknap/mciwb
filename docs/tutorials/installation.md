# Installation

## Check your version of python

You will need python 3.11 or later. You can check your version of python by
typing into a terminal:

```
$ python3 --version
```

If you do not have a suitable Python, [uv](https://docs.astral.sh/uv/) can
install one for you (`uv venv --python 3.13` below does so automatically).

## Create a virtual environment

It is recommended that you install into a “virtual environment” so this
installation will not interfere with any existing Python software:

```
$ uv venv --python 3.13 /path/to/venv
$ source /path/to/venv/bin/activate
```

or without uv:

```
$ python3 -m venv /path/to/venv
$ source /path/to/venv/bin/activate
```

## Installing the library

Install the library and its dependencies from GitHub:

```
$ uv pip install git+https://github.com/gilesknap/mciwb.git
```

(or `python3 -m pip install git+https://github.com/gilesknap/mciwb.git`
without uv).

:::{note}
The releases on PyPI (`pip install mciwb`) predate support for Minecraft 26.x.
Until a new release is published, install from GitHub as above.
:::

The library should now be installed and the commandline interface on your path.
You can check the version that has been installed by typing:

```
$ mciwb --version
```
