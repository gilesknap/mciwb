import os
import tempfile
from pathlib import Path
from shutil import copytree

import pytest
from typer.testing import CliRunner

from mciwb.__main__ import cli
from tests.conftest import HOST, RCON_P, RCON_PORT

runner = CliRunner()


def run_cli(*args):
    result = runner.invoke(cli, [str(x) for x in args])
    if result.exception:
        raise result.exception
    assert result.exit_code == 0, result
    return result


def test_repr(tmp_path: Path, minecraft_container, minecraft_client, minecraft_player):
    """launch the cli in test mode and connect to the test server"""
    result = run_cli(
        "shell", "--test", "--server", HOST, "--port", RCON_PORT, "--passwd", RCON_P
    )

    assert "no players" in result.stdout

    result = run_cli(
        "shell",
        "--test",
        "--server",
        HOST,
        "--port",
        RCON_PORT,
        "--passwd",
        RCON_P,
        "--player",
        "georgeTest",
    )

    assert "player: georgeTest" in result.stdout


@pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") == "true", reason="Permissions error in GH Actions"
)
def test_backup(tmp_path):
    checks = ["ERROR", "WARNING"]

    server_folder = Path(tempfile.gettempdir()) / "test-backup-server"
    server_folder2 = Path(tempfile.gettempdir()) / "test-backup-server2"
    backup_folder = Path(tempfile.gettempdir()) / "test-backup-backup"
    backup_folder_tmp = Path(tempfile.gettempdir()) / "test-backup-backup"

    result = run_cli(
        "start",
        "--folder",
        server_folder,
        "--server-name",
        "test",
        "--port",
        "20200",
        "--backup-folder",
        backup_folder_tmp,
    )
    assert not any(err in result.stdout for err in checks)

    result = run_cli(
        "backup",
        "--folder",
        server_folder,
        "--backup-folder",
        backup_folder,
    )
    assert not any(err in result.stdout for err in checks)

    copytree(server_folder, server_folder2, dirs_exist_ok=True)
    result = run_cli(
        "restore",
        "--folder",
        server_folder2,
        "--server-name",
        "test",
        "--port",
        "20200",
        "--backup-folder",
        backup_folder,
    )
    assert not any(err in result.stdout for err in checks)

    result = run_cli("stop", "--server-name", "test")
    assert not any(err in result.stdout for err in checks)
