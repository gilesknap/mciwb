import logging
from pathlib import Path
from typing import Optional

import typer
from IPython.terminal.embed import InteractiveShellEmbed

import mciwb
from mciwb import Iwb, __version__
from mciwb.server import MinecraftServer

cli = typer.Typer(add_completion=False)

server_name = "mciwb_server"
default_server_folder = Path.home() / server_name


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
    server: str = typer.Option(..., prompt=True),
    port: int = typer.Option(..., prompt=True),
    passwd: str = typer.Option(..., prompt=True, hide_input=True),
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
    except BaseException:
        mciwb.world.stop()
        raise

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
    password: str = typer.Option(..., prompt=True, hide_input=True),
    port: int = typer.Option(default=20100),
    folder: Path = default_server_folder,
    world_type: str = "normal",
    debug: bool = False,
):
    """
    Start a minecraft server in the background. Default options automatically
    work with `mciwb shell`
    """
    init_logging(debug)

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
