import logging
import os
import shutil

import pytest
from typer.testing import CliRunner

from mciwb.__main__ import cli
from mciwb.threads import Client
from tests.conftest import HOST, RCON_P, RCON_PORT, servers_folder

runner = CliRunner()


def run_cli(*args):
    result = runner.invoke(cli, [str(x) for x in args])
    if result.exception and not isinstance(result.exception, SystemExit):
        raise result.exception
    assert result.exit_code == 0, result.output
    return result


def test_repr(minecraft_player):
    """launch the cli in test mode and connect to the test server"""
    args = ["shell", "--test", "--server", HOST, "--port", RCON_PORT]
    result = run_cli(*args, "--passwd", RCON_P)

    assert "no players" in result.stdout

    result = run_cli(*args, "--passwd", RCON_P, "--player", "georgeTest")

    assert "player: georgeTest" in result.stdout


def test_backup(caplog: pytest.LogCaptureFixture):
    """start a server, back it up, change it, restore it and stop it"""
    server_name = "mciwb-test-backup"
    port = 20200
    # podman resolves bind mounts on its host, so use servers_folder which is
    # at the same path in the devcontainer and on its host
    test_folder = servers_folder / server_name
    shutil.rmtree(test_folder, ignore_errors=True)
    server_folder = test_folder / "server"
    backup_folder = test_folder / "backups"
    world = server_folder / "world"
    common = ["--server-name", server_name, "--port", port]
    folders = ["--folder", server_folder, "--backup-folder", backup_folder]

    try:
        run_cli("start", *common, "--folder", server_folder, "--world-type", "flat")
        assert (world / "level.dat").exists()
        # the server's files belong to the current user, not a podman subuid
        assert (world / "level.dat").stat().st_uid == os.getuid()

        marker = world / "mciwb-marker.txt"
        marker.write_text("before backup")
        run_cli("backup", *folders, "--backup-name", "test")
        assert (backup_folder / "test.zip").exists()

        marker.write_text("after backup")
        extra = world / "mciwb-extra.txt"
        extra.write_text("created after backup")

        run_cli("restore", "test", *common, *folders, "--world-type", "flat")

        assert (world / "level.dat").exists()
        assert marker.read_text() == "before backup"
        assert not extra.exists()
        # the restarted server responds over RCON
        with Client(HOST, port, passwd="default_pass") as client:
            assert isinstance(client.seed, int)
    finally:
        run_cli("stop", "--server-name", server_name)

    problems = [
        r
        for r in caplog.records
        if r.name.startswith("mciwb") and r.levelno >= logging.WARNING
    ]
    assert problems == []
