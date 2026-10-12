# Contribute to the project

Contributions and issues are most welcome! All issues and pull requests are
handled through [GitHub](https://github.com/gilesknap/mciwb/issues). Also, please check for any existing issues before
filing a new one. If you have a great idea but it involves big changes, please
file a ticket before making a pull request! We want to make sure you don't spend
your time coding something that might not fit the scope of the project.

## Issue or Discussion?

Github also offers [discussions](https://github.com/gilesknap/mciwb/discussions) as a place to ask questions and share ideas. If
your issue is open ended and it is not obvious when it can be "closed", please
raise it as a discussion instead.

## Code Coverage

While 100% code coverage does not make a library bug-free, it significantly
reduces the number of easily caught bugs! Please make sure coverage remains the
same or is improved by a pull request!

## Developer Information

It is recommended that developers use a [vscode devcontainer](https://code.visualstudio.com/docs/devcontainers/containers). This repository contains configuration to set up a containerized development environment that suits its own needs.

This project was created using the [Diamond Light Source Copier Template](https://github.com/DiamondLightSource/python-copier-template) for Python projects.

For more information on common tasks like setting up a developer environment, running the tests, and setting a pre-commit hook, see the template's [How-to guides](https://diamondlightsource.github.io/python-copier-template/5.4.0/how-to.html).

## Running the tests

This project uses [uv](https://docs.astral.sh/uv/). Set up the development
environment and run the checks with:

```bash
uv sync                          # create .venv with all dev dependencies
uv run ruff check src tests      # lint (or: uv run tox -e pre-commit)
uv run pyright src tests         # type check
uv run pytest -m "not system"    # unit tests, no docker needed
uv run pytest                    # unit and system tests, needs docker
uv run tox -e docs               # build the docs into build/html
```

The tests come in two sets:

- `tests/test_unit` use a `MockClient` (tests/mockclient.py) that mimics
  the responses of a Minecraft server. They run anywhere.
- `tests/test_system` start a real Minecraft server in a docker container
  (RCON port 20401, plus 20200 for the CLI backup test). They are skipped
  when no docker daemon is available, except under CI (`CI` set) where a
  missing docker daemon is an error. The first run downloads the server
  image and Minecraft, so allow a few minutes.

Set `MCIWB_KEEP_SERVER=1` to keep the test server running between test runs,
which makes repeated system test runs much faster, and lets you join the
test world with a Minecraft client on port 20402.

## Upgrading Minecraft

The Minecraft release is set in three places that must agree:

1. `mcwb.MINECRAFT_VERSION`: the release that `mcwb.Item` was generated
   from (in the mcwb library).
2. `MINECRAFT_VERSION` in `src/mciwb/server.py`: the release that
   `mciwb start` and the system tests run.
3. `SERVER_IMAGE` in `src/mciwb/server.py`: an itzg/minecraft-server image
   tag with a Java version that supports that release.

`tests/test_unit/test_signs.py::test_minecraft_version` checks 1 and 2.
After upgrading, run the system tests, and check the server responses that
`tests/mockclient.py` mimics (sign and entity data formats change between
releases).
