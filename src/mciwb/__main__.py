import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from IPython.terminal.embed import InteractiveShellEmbed

from mciwb import (
    Blocks,
    Client,
    CopyPaste,
    Corner,
    Cuboid,
    Direction,
    Item,
    Iwb,
    Monitor,
    Planes3d,
    Player,
    Vec3,
    __version__,
    get_client,
    world,
)
from mciwb.backup import Backup
from mciwb.server import (
    HOST,
    MinecraftServer,
    backup_folder,
    def_pass,
    def_port,
    def_world_type,
    default_server_folder,
    server_name,
)

cli = typer.Typer(add_completion=False)

# these are imported for use in iPython without needing a manual import
useful = [
    Blocks,
    Client,
    CopyPaste,
    Corner,
    Cuboid,
    Direction,
    Item,
    Iwb,
    Monitor,
    Planes3d,
    Player,
    Vec3,
    __version__,
    get_client,
    world,
]


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@cli.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Print the version of ibek and exit",
    ),
    debug: bool = False,
):
    """Minecraft Interactive World Builder"""


def exception_handler(exception_type, exception, traceback):
    if logging.root.level > logging.DEBUG:
        logging.error("%s: %s", exception_type.__name__, exception)
    logging.debug("", exc_info=True)


def init_logging(debug: bool):
    if debug:
        logging.basicConfig(
            format="%(levelname)s: %(pathname)s:%(lineno)d %(funcName)s "
            "\n\t%(message)s",
            level=logging.DEBUG,
        )
    else:
        logging.basicConfig(
            format="%(levelname)s:\t%(message)s",
            level=logging.INFO,
        )


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
        logging.error("Could not connect to server")
        exit(1)
    except Exception:
        if world:
            world.stop()
        logging.error("Failed to start world")
        logging.debug("", exc_info=True)
        exit(1)

    # for quick access in the shell without qualifying the namespace
    world = world

    logging.info("######### Starting Interactive Session ##########\n")

    # Prepare IPython shell with auto-reload so user code edits work immediately
    shell = InteractiveShellEmbed()
    shell.magic(r"%load_ext autoreload")
    shell.magic(r"%autoreload 2")
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
            logging.error(f"{folder} is not a directory")
            exit(1)
        else:
            logging.info(f"Launching existing Minecraft server in {folder}")
    else:
        logging.info(f"Creating new Minecraft server in {folder}")

    server = MinecraftServer(server_name, port, password, folder, world_type)
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
    backup_folder: Path = backup_folder,
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
    backup_folder: Path = backup_folder,
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
    start(folder=folder, port=port, server_name=server_name)


if __name__ == "__main__":
    cli()
