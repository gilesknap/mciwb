import sys
from pathlib import Path
from typing import Optional

import typer
from IPython.terminal.embed import InteractiveShellEmbed

from mciwb import __version__
from mciwb.backup import Backup

# these are imported only for use in iPython without needing a manual import
# so I allow import * here to avoid repetition of imports.py
from mciwb.imports import *  # noqa: F401, F403
from mciwb.iwb import Iwb
from mciwb.logging import exception_handler, init_logging, log
from mciwb.server import (
    HOST,
    MinecraftServer,
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
    # this should be 'bool | None' but I'm getting
    # RuntimeError: Type not yet supported: bool | None
    # despited Python 3.10 - TODO investigate
    version: Optional[bool] = typer.Option(  # noqa: UP007
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Print the version of ibek and exit",
    ),
    debug: bool = False,
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

    world = None

    try:
        world = Iwb(server, port, passwd)

        if player:
            world.add_player(player)
    except ConnectionRefusedError:
        log.error("Could not connect to server")
        exit(1)
    except Exception:
        if world:
            world.stop()
        log.error("Failed to start world")
        log.debug("", exc_info=True)
        exit(1)

    log.info("######### Starting Interactive Session ##########\n")

    shell = InteractiveShellEmbed.instance()
    # Prepare IPython shell with auto-reload so user code edits work immediately
    shell.run_line_magic("load_ext", "autoreload")
    shell.run_line_magic("autoreload", "2")
    # Also suppress traceback to avoid intimidating novice programmers
    ipython = shell.get_ipython()
    ipython._showtraceback = exception_handler  # type: ignore

    if test:
        # for testing just report the world object state
        print(world)
    else:
        # enter iPython shell until users exits
        shell(colors="neutral")

    # Terminate all threads after interactive session exits
    world.stop()


@cli.command()
def start(
    password: str = def_pass,
    world_type: str = def_world_type,
    server_name: str = server_name,
    folder: Path = default_server_folder,
    backup_folder: Path = backup_folder_default,
    port: int = def_port,
    debug: bool = False,
):
    """
    Start a minecraft server in the background. Default options automatically
    work with `mciwb shell`
    """
    init_logging(debug)

    if folder.exists():
        if not folder.is_dir():
            log.error(f"{folder} is not a directory")
            exit(1)
        else:
            log.info(f"Launching existing Minecraft server in {folder}")
    else:
        log.info(f"Creating new Minecraft server in {folder}")

    server = MinecraftServer(
        server_name, port, password, folder, world_type, backup_folder=backup_folder
    )
    server.create()


@cli.command()
def stop(
    server_name: str = server_name,
    debug: bool = False,
):
    """
    Start a minecraft server in the background. Default options automatically
    work with `mciwb shell`
    """
    init_logging(debug)

    MinecraftServer.stop_named(server_name)


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
    backup_name: str = typer.Argument(""),
    debug: bool = False,
    folder: Path = default_server_folder,
    backup_folder: Path = backup_folder_default,
    server_name: str = server_name,
    port: int = def_port,
):
    """
    Stop the minecraft server. Restore from backup and restart.
    """
    init_logging(debug)

    stop(server_name=server_name)
    backup = Backup(world_folder=folder / "world", backup_folder=backup_folder)
    backup.restore(name=backup_name)
    start(
        folder=folder, port=port, server_name=server_name, backup_folder=backup_folder
    )


if __name__ == "__main__":
    cli()
