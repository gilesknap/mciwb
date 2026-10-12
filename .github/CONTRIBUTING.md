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
uv run pytest -m "not system"    # unit tests, no podman needed
uv run pytest                    # unit and system tests, needs podman
uv run tox -e docs               # build the docs into build/html
```

The tests come in two sets:

- `tests/test_unit` use a `MockClient` (tests/mockclient.py) that mimics
  the responses of a Minecraft server. They run anywhere.
- `tests/test_system` start a real Minecraft server in a podman container
  (RCON port 20401, plus 20200 for the CLI backup test). They are skipped
  when no podman service is reachable, except under CI (`CI` set) where a
  missing podman service is an error. The first run downloads the server
  image and Minecraft, so allow a few minutes.

mciwb talks to the Podman service socket: `CONTAINER_HOST` if set, else the
rootless `$XDG_RUNTIME_DIR/podman/podman.sock`, else the rootful
`/run/podman/podman.sock`. Enable the rootless socket on your host with:

```bash
systemctl --user enable --now podman.socket
```

The devcontainer mounts that socket as `/run/podman/podman.sock` and sets
`CONTAINER_HOST`, so the system tests also run from inside it. Podman
resolves bind mount paths on the host, not in the devcontainer, so the
servers' folders must be at the same path in both: the devcontainer mounts
`/tmp/test-mc-servers` for the system tests. To run `mciwb start` from
inside the devcontainer, put `--folder` and `--backup-folder` under
`/tmp/test-mc-servers` too.

Under rootless podman the server runs as the image's uid 1000, which mciwb
maps to your host user (`--userns=keep-id:uid=1000,gid=1000`), so the files
in the server folder stay yours.

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

## The mcwb dependency

mciwb builds on [mcwb](https://github.com/gilesknap/mcwb). Until an mcwb
release contains `mcwb.Item` and the `get_block` fix for blocks without a loot
table, `pyproject.toml` pins mcwb as a git dependency on a commit SHA (see
[ADR 0003](https://github.com/gilesknap/mciwb/blob/main/docs/explanations/decisions/0003-keep-mcipc-use-mcwb-item.md)).
PyPI rejects direct URL dependencies, so before the next mciwb release:

1. Release mcwb (from mcipc-tools/mcwb, which publishes to PyPI).
2. Replace the git dependency with `mcwb>=<new version>` and run `uv lock`.

To try local mcwb changes, run `uv pip install -e ../mcwb` in the mciwb venv
(and `uv sync` afterwards to return to the pinned commit).
