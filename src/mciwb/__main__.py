import logging
from pathlib import Path
from typing import Optional

import typer
from IPython.terminal.embed import InteractiveShellEmbed

import mciwb
from mciwb import Iwb, __version__
from mciwb.server import HOST, MinecraftServer

cli = typer.Typer(add_completion=False)

server_name = "mciwb_server"
default_server_folder = Path.home() / server_name
def_pass = "default_pass"
def_port = 20100
def_world_type = "normal"


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

    try:
        mciwb.world = Iwb(server, port, passwd)

        if player:
            mciwb.world.add_player(player)
    except ConnectionRefusedError:
        logging.error("Could not connect to server")
        exit(1)
    finally:
        if mciwb.world is not None:
            mciwb.world.stop()

    # for quick access in the shell without qualifying the namespace
    world = mciwb.world

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
        print(mciwb.world)
    else:
        # enter iPython shell until users exits
        shell(colors="neutral")

    # Terminate all threads after interactive session exits
    world.stop()


@cli.command()
def start(
    password: str = def_pass,
    port: int = def_port,
    folder: Path = default_server_folder,
    world_type: str = def_world_type,
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
            if port != def_port or world_type != def_world_type:
                logging.error(
                    f"server in {folder} already exists. "
                    "Cannot change settings on an existing server."
                )
                exit(1)
            else:
                logging.info(f"Launching existing Minecraft server in {folder}")
    else:
        logging.info(f"Creating new Minecraft server in {folder}")

    server = MinecraftServer(server_name, port, password, folder, world_type)
    server.create()


@cli.command()
def stop(
    debug: bool = False,
):
    """
    Start a minecraft server in the background. Default options automatically
    work with `mciwb shell`
    """
    init_logging(debug)

    MinecraftServer.stop_named(server_name)


if __name__ == "__main__":
    cli()
