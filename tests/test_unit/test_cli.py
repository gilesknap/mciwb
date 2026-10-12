import sys
from subprocess import check_output

from mciwb import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "mciwb", "--version"]
    assert check_output(cmd).decode().strip() == __version__
