"""
The mciwb command line interface
"""

import runpy
import sys
from pathlib import Path
from typing import Annotated

import typer
from IPython.terminal.embed import InteractiveShellEmbed
from mcwb import Vec3, Volume
from rcon.exceptions import WrongPassword

from mciwb import __version__, imports
from mciwb.backup import Backup

# these are imported only for use in iPython without needing a manual import
# so I allow import * here to avoid repetition of imports.py
from mciwb.imports import *  # noqa: F401, F403
from mciwb.iwb import Iwb
from mciwb.logging import exception_handler, init_logging, log
from mciwb.render import VIEWS, render, scan
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
from mciwb.threads import Client, set_client

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
    except WrongPassword:
        log.error(f"Wrong RCON password for server {server}:{port}")
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

    If the server's container already exists, it is started with the
    settings that it was created with. Run `mciwb stop` first to change them.
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
    except WrongPassword:
        log.error(
            f"Minecraft Server '{server_name}' rejected the RCON password. "
            f"Check rcon.password in {server.server_folder}/server.properties."
        )
        raise typer.Exit(1) from None


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
    port: int = def_port,
    password: str = def_pass,
    debug: bool = False,
):
    """
    Backup the current state of the world.

    If the server is running, it saves the world to disk and pauses saving
    while the backup is made. Use the --port and --password that you gave to
    `mciwb start`.
    """
    init_logging(debug)

    backup = Backup(world_folder=folder / "world", backup_folder=backup_folder)
    client, wrong_password = _rcon_client(port, password)
    if wrong_password:
        log.warning(
            f"wrong RCON password for {HOST}:{port}: copying the world files "
            "without asking the server to save them first"
        )
    try:
        if client:
            set_client(client)
        backup.backup(running=client is not None, name=backup_name)
    except ValueError as e:
        log.error(e)
        raise typer.Exit(1) from None
    finally:
        if client:
            client.close()


def _rcon_client(port: int, password: str) -> tuple[Client | None, bool]:
    """
    Connect to a running server. Return the client, or None if there is no
    server or the password is wrong, and whether the password was wrong (for
    the caller to report: there is a server, but it was not asked to save)
    """
    client = Client(HOST, port, passwd=password, timeout=10)
    try:
        client.connect(True)
    except WrongPassword:
        client.close()
        return None, True
    except Exception as e:
        log.debug(f"no server on {HOST}:{port}: {e!r}")
    else:
        # the timeout is only for the probe: save-all flush on a large world
        # can take longer, so wait for commands as long as they need (rcon
        # types the timeout as float, but the socket accepts None)
        client.timeout = None  # pyright: ignore[reportAttributeAccessIssue]
        return client, False
    client.close()
    return None, False


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

    backup = Backup(world_folder=folder / "world", backup_folder=backup_folder)
    # check the backup exists before taking the server down
    try:
        rfile = backup.find(backup_name)
    except ValueError as e:
        log.error(e)
        raise typer.Exit(1) from None

    stop(server_name=server_name, debug=debug)
    backup.restore(name=rfile.name, backup=keep_old)
    start(
        password=password,
        world_type=world_type,
        server_name=server_name,
        folder=folder,
        port=port,
        minecraft_version=minecraft_version,
        debug=debug,
    )


@cli.command(
    "render",
    # let corners have negative coordinates, e.g. 632 73 -1658
    context_settings={"ignore_unknown_options": True},
)
def render_cmd(
    corners: Annotated[
        list[int] | None,
        typer.Argument(
            help="two opposite corners of the region: X1 Y1 Z1 X2 Y2 Z2",
            show_default=False,
        ),
    ] = None,
    centre: Annotated[
        tuple[int, int, int] | None,
        typer.Option(help="the centre of the region, with --size", show_default=False),
    ] = None,
    size: Annotated[
        tuple[int, int, int] | None,
        typer.Option(help="the size of the region in blocks, with --centre"),
    ] = None,
    view: Annotated[
        list[str] | None,
        typer.Option(help=f"repeat for several views: {', '.join(VIEWS)}"),
    ] = None,
    output: Annotated[Path, typer.Option(help="the PNG file to write")] = Path(
        "render.png"
    ),
    scale: Annotated[
        int | None, typer.Option(help="pixels per block (default: automatic)")
    ] = None,
    labels: Annotated[
        bool, typer.Option(help="add titles and world coordinate labels")
    ] = True,
    folder: Annotated[
        Path, typer.Option(help="the server folder, as for mciwb start")
    ] = default_server_folder,
    rcon: Annotated[
        bool, typer.Option(help="read blocks over RCON, not from the world files")
    ] = False,
    port: int = def_port,
    password: str = def_pass,
    debug: bool = False,
):
    """
    Render a region of the world to a PNG image, to see what you built.

    Give the region as two corners, or as --centre and --size. Blocks are
    read from the world files in --folder (after asking a running server to
    save), or over RCON one block at a time (with --rcon, or when --folder
    has no world): use the --port and --password that you gave to
    `mciwb start`.
    """
    init_logging(debug)

    try:
        vol = _region(corners, centre, size)
        views = view or ["top", "iso"]
        unknown = [v for v in views if v not in VIEWS]
        if unknown:
            raise ValueError(f"unknown view {unknown[0]}, use {', '.join(VIEWS)}")
    except ValueError as e:
        log.error(e)
        raise typer.Exit(1) from None

    client, wrong_password = _rcon_client(port, password)
    world_folder = None if rcon else folder / "world"
    if client is None and world_folder and (world_folder / "level.dat").exists():
        # unlike backup, render expects a running server: without one the
        # world files may be minutes behind what was just built
        if wrong_password:
            problem, options = "wrong RCON password for", "--password"
        else:
            problem, options = "no server on", "--port/--password"
        log.warning(
            f"{problem} {HOST}:{port}: reading the world files without "
            "asking the server to save, so recent changes may be missing; "
            f"pass the {options} of mciwb start"
        )
    elif wrong_password:
        log.warning(f"wrong RCON password for {HOST}:{port}")
    try:
        grid = scan(vol, world_folder, client)
    except ValueError as e:
        log.error(e)
        raise typer.Exit(1) from None
    finally:
        if client:
            client.close()

    render(grid, views, scale, labels).save(output)
    log.info(f"rendered {', '.join(views)} of {vol.start} to {vol.end} to {output}")


def _region(
    corners: list[int] | None,
    centre: tuple[int, int, int] | None,
    size: tuple[int, int, int] | None,
) -> Volume:
    """the region given to mciwb render, as corners or centre and size"""
    if corners:
        if len(corners) != 6 or centre or size:
            raise ValueError(
                "give two corners X1 Y1 Z1 X2 Y2 Z2, or --centre and --size"
            )
        return Volume.from_corners(Vec3(*corners[:3]), Vec3(*corners[3:]))
    if centre is None or size is None:
        raise ValueError("give two corners X1 Y1 Z1 X2 Y2 Z2, or --centre and --size")
    if min(size) < 1:
        raise ValueError(f"--size must be at least 1 in each direction, not {size}")
    start = Vec3(*centre) - Vec3(*size) // 2
    return Volume.from_corners(start, start + Vec3(*size) - 1)


if __name__ == "__main__":
    cli()
