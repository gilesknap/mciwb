import IPython
import typer

from mciwb import iwb


def main(
    server: str = typer.Option(..., prompt=True),
    port: int = typer.Option(..., prompt=True),
    passwd: str = typer.Option(..., prompt=True, hide_input=True),
    player: str = "",
):
    global cmd
    cmd = iwb.Iwb(server, port, passwd)
    if player:
        cmd.add_player(player)
    print("\n-- Starting Interactive Session --\n")

    IPython.embed(colors="neutral")

    # Terminate all threads
    cmd.stop()


def cli():
    typer.run(main)


if __name__ == "__main__":
    typer.run(main)
