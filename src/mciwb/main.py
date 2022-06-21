import logging
from typing import Optional

import typer
from IPython.terminal.embed import InteractiveShellEmbed

import mciwb
from mciwb import Iwb, __version__


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def exception_handler(exception_type, exception, traceback):
    if logging.root.level > logging.DEBUG:
        logging.error("%s: %s", exception_type.__name__, exception)
    logging.debug("", exc_info=True)


def main(
    server: str = typer.Option(..., prompt=True),
    port: int = typer.Option(..., prompt=True),
    passwd: str = typer.Option(..., prompt=True, hide_input=True),
    player: str = "",
    debug: bool = False,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Print the version of ibek and exit",
    ),
):
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

    # enter iPython shell until users exits
    shell(colors="neutral")
    # Terminate all threads after interactive session exits
    world.stop()


def cli():
    typer.run(main)


if __name__ == "__main__":
    typer.run(main)
