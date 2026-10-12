"""
The mciwb command line interface
"""

import runpy
import sys
from pathlib import Path
from typing import Annotated

import typer
from IPython.terminal.embed import InteractiveShellEmbed

from mciwb import __version__, imports
from mciwb.backup import Backup

# these are imported only for use in iPython without needing a manual import
# so I allow import * here to avoid repetition of imports.py
from mciwb.imports import *  # noqa: F401, F403
from mciwb.iwb import Iwb
from mciwb.logging import exception_handler, init_logging, log
from mciwb.server import (
    HOST,
    MINECRAFT_VERSION,
    MinecraftServer,
    PodmanNotAvailableError,
    backup_folder_default,
    def_pass,
    def_port,
    def_world_type,
    default_server_folder,
    server_name,
)

cli = typer.Typer(add_completion=False)


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@cli.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Print the version of mciwb and exit",
    ),
):
    """Minecraft Interactive World Builder"""


@cli.command()
def shell(
    server: str = HOST,
    port: int = def_port,
    passwd: str = def_pass,
    player: str = "",
    debug: bool = False,
    test: bool = False,
):
    """
    Start an interactive iPython shell with a predefined world object
    connected to your Minecraft server.
    """
    init_logging(debug)

    sys.path.append(".")

    world = _connect(server, port, passwd, player)

    log.info("######### Starting Interactive Session ##########\n")

    shell = InteractiveShellEmbed.instance()
    # Prepare IPython shell with auto-reload so user code edits work immediately
    shell.run_line_magic("load_ext", "autoreload")
    shell.run_line_magic("autoreload", "2")
    # Also suppress traceback to avoid intimidating novice programmers
    ipython = shell.get_ipython()
    # monkey patch IPython's private traceback hook
    ipython._showtraceback = exception_handler  # type: ignore # noqa: SLF001

    if test:
        # for testing just report the world object state
        print(world)
    else:
        # enter iPython shell until users exits
        shell(colors="neutral")

    # Terminate all threads after interactive session exits
    world.stop()


def _connect(server: str, port: int, passwd: str, player: str) -> Iwb:
    """Connect to the server and optionally add a player, or exit on failure"""
    world = None
    try:
        world = Iwb(server, port, passwd)

        if player:
            world.add_player(player)
    except ConnectionRefusedError:
        log.error(f"Could not connect to server {server}:{port}")
        raise typer.Exit(1) from None
    except Exception:
        if world:
            world.stop()
        log.error("Failed to start world")
        log.debug("", exc_info=True)
        raise typer.Exit(1) from None
    return world


@cli.command()
def run(
    script: Annotated[Path, typer.Argument(help="the Python script to run")],
    server: str = HOST,
    port: int = def_port,
    passwd: str = def_pass,
    player: str = "",
    debug: bool = False,
):
    """
    Run a Python build script against your Minecraft server, then exit.

    The script runs with the same names available as in `mciwb shell`: a
    `world` object connected to the server, plus everything in mciwb.imports
    (Item, Vec3, Direction, polygon ...). Background monitors are stopped
    when the script ends.
    """
    init_logging(debug)

    if not script.is_file():
        log.error(f"{script} not found")
        raise typer.Exit(1)
    # let the script import modules that sit beside it
    sys.path.insert(0, str(script.resolve().parent))

    world = _connect(server, port, passwd, player)
    namespace = {name: getattr(imports, name) for name in imports.__all__}
    namespace["world"] = world
    try:
        runpy.run_path(str(script), init_globals=namespace, run_name="__main__")
    finally:
        world.stop()


@cli.command()
def start(
    password: str = def_pass,
    world_type: str = def_world_type,
    server_name: str = server_name,
    folder: Path = default_server_folder,
    port: int = def_port,
    minecraft_version: str = MINECRAFT_VERSION,
    debug: bool = False,
):
    """
    Start a minecraft server in the background. Default options automatically
    work with `mciwb shell`.

    The server runs the Minecraft Java Edition release given by
    --minecraft-version. Your Minecraft client must use the same release.
    """
    init_logging(debug)

    if folder.exists():
        if not folder.is_dir():
            log.error(f"{folder} is not a directory")
            raise typer.Exit(1)
        else:
            log.info(f"Launching existing Minecraft server in {folder}")
    else:
        log.info(f"Creating new Minecraft server in {folder}")

    server = MinecraftServer(
        server_name,
        port,
        password,
        folder,
        world_type,
        version=minecraft_version,
    )
    try:
        server.create()
    except PodmanNotAvailableError as e:
        log.error(e)
        raise typer.Exit(1) from e


@cli.command()
def stop(
    server_name: str = server_name,
    debug: bool = False,
):
    """
    Stop the minecraft server started by `mciwb start`.
    """
    init_logging(debug)

    try:
        MinecraftServer.stop_named(server_name)
    except PodmanNotAvailableError as e:
        log.error(e)
        raise typer.Exit(1) from e


@cli.command()
def backup(
    folder: Path = default_server_folder,
    backup_name: str = "",
    backup_folder: Path = backup_folder_default,
    debug: bool = False,
):
    """
    Backup the current state of the world.
    """
    init_logging(debug)

    backup = Backup(world_folder=folder / "world", backup_folder=backup_folder)
    backup.backup(running=False, name=backup_name)


@cli.command()
def restore(
    backup_name: str = typer.Argument("", help="defaults to the latest backup"),
    debug: bool = False,
    folder: Path = default_server_folder,
    backup_folder: Path = backup_folder_default,
    server_name: str = server_name,
    port: int = def_port,
    password: str = def_pass,
    world_type: str = def_world_type,
    minecraft_version: str = MINECRAFT_VERSION,
    keep_old: bool = typer.Option(
        False, help="keep the replaced world folder as <folder>/world-old"
    ),
):
    """
    Stop the minecraft server. Restore from backup and restart.

    Use the same options that you gave to `mciwb start`.
    """
    init_logging(debug)

    stop(server_name=server_name, debug=debug)
    backup = Backup(world_folder=folder / "world", backup_folder=backup_folder)
    backup.restore(name=backup_name, backup=keep_old)
    start(
        password=password,
        world_type=world_type,
        server_name=server_name,
        folder=folder,
        port=port,
        minecraft_version=minecraft_version,
        debug=debug,
    )


if __name__ == "__main__":
    cli()
