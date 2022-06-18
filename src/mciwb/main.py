import sys
from typing import Optional

import typer
from IPython.terminal.embed import InteractiveShellEmbed
from mcipc.rcon.je import Client

from mciwb import __version__, iwb

cmd: iwb.Iwb
c: Client


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def exception_handler(exception_type, exception, traceback):
    print("%s: %s" % (exception_type.__name__, exception), file=sys.stderr)


def main(
    server: str = typer.Option(..., prompt=True),
    port: int = typer.Option(..., prompt=True),
    passwd: str = typer.Option(..., prompt=True, hide_input=True),
    player: str = "",
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Print the version of ibek and exit",
    ),
):
    global cmd, c
    cmd = iwb.Iwb(server, port, passwd)
    c = cmd._client
    if player:
        cmd.add_player(player)
    print("\n-- Starting Interactive Session --\n")

    # Prepare IPython shell with auto-reload so user code edits work immediately
    shell = InteractiveShellEmbed()
    shell.magic(r"%load_ext autoreload")
    shell.magic(r"%autoreload 2")
    shell(colors="neutral")
    # Also suppress traceback to avoid intimidating novice programmers
    ipython = shell.get_ipython()
    ipython._showtraceback = exception_handler

    # Terminate all threads after interactive session exits
    cmd.stop()


def cli():
    typer.run(main)


if __name__ == "__main__":
    typer.run(main)
