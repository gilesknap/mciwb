from typing import Optional

import typer
from IPython.terminal.embed import InteractiveShellEmbed
from mcipc.rcon.je import Client

import mciwb as mc
from mciwb import __version__, iwb

interactive_imports = [mc]

cmd: iwb.Iwb
c: Client


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


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

    # Terminate all threads after interactive session exits
    cmd.stop()


def cli():
    typer.run(main)


if __name__ == "__main__":
    typer.run(main)
