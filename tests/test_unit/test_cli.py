import sys
from subprocess import check_output

from typer.testing import CliRunner

from mciwb import __version__

runner = CliRunner()


def test_cli_version():
    cmd = [sys.executable, "-m", "mciwb", "--version"]
    assert check_output(cmd).decode().strip() == __version__
