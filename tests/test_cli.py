import sys
from pathlib import Path
from subprocess import check_output

from docker.models.containers import Container
from typer.testing import CliRunner

from mciwb import Player, __version__
from mciwb.__main__ import cli
from tests.conftest import HOST, RCON_P, RCON_PORT

runner = CliRunner()


def run_cli(*args):
    result = runner.invoke(cli, [str(x) for x in args])
    if result.exception:
        raise result.exception
    assert result.exit_code == 0, result
    return result


def test_cli_version():
    cmd = [sys.executable, "-m", "mciwb", "--version"]
    assert check_output(cmd).decode().strip() == __version__


def test_repr(tmp_path: Path, minecraft_container: Container, minecraft_player: Player):
    """launch the cli in test mode and connect to the test server"""
    result = run_cli(
        "--test", "--server", HOST, "--port", RCON_PORT, "--passwd", RCON_P
    )

    assert "no player selected" in result.stdout

    result = run_cli(
        "--test",
        "--server",
        HOST,
        "--port",
        RCON_PORT,
        "--passwd",
        RCON_P,
        "--player",
        "george",
    )

    assert "player: george" in result.stdout
