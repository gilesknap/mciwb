import subprocess
import sys

from mciwb import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "mciwb", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
