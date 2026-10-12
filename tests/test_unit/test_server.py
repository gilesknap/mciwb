"""
Unit tests for MinecraftServer with a mocked docker client
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from docker.models.containers import Container

import mciwb.server
from mciwb.server import MINECRAFT_VERSION, SERVER_IMAGE, MinecraftServer


@pytest.fixture()
def docker(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock()
    client.containers.list.return_value = []
    client.containers.run.return_value = MagicMock(spec=Container)
    monkeypatch.setattr(mciwb.server, "from_env", lambda: client)
    monkeypatch.setattr(MinecraftServer, "wait_server", lambda self: None)
    monkeypatch.setattr(MinecraftServer, "_settings", lambda self: None)
    return client


@pytest.mark.parametrize("keep", [True, False])
def test_create(docker: MagicMock, tmp_path: Path, keep: bool):
    server = MinecraftServer(
        "test",
        20100,
        "secret",
        tmp_path / "server",
        "flat",
        backup_folder=tmp_path / "backups",
        keep=keep,
    )
    server.create()

    args, kwargs = docker.containers.run.call_args
    assert args == (SERVER_IMAGE,)
    env = kwargs["environment"]
    assert env["VERSION"] == MINECRAFT_VERSION
    assert env["LEVEL_TYPE"] == "flat"
    assert env["RCON_PORT"] == 20100
    assert env["SERVER_PORT"] == 20101
    assert env["RCON_PASSWORD"] == "secret"
    assert env["PAUSE_WHEN_EMPTY_SECONDS"] == 0
    assert env["UID"] == os.getuid()
    assert env["GID"] == os.getgid()
    assert kwargs["ports"] == {"20100/tcp": 20100, "20101": 20101}
    assert kwargs["restart_policy"] == {"Name": "unless-stopped" if keep else "no"}
    assert str(tmp_path / "server") in kwargs["volumes"]
    assert (tmp_path / "backups").is_dir()


def test_create_test_server(docker: MagicMock, tmp_path: Path):
    folder = tmp_path / "server"
    (folder / "world").mkdir(parents=True)
    server = MinecraftServer(
        "test", 20100, "pass", folder, "normal", keep=False, test=True
    )
    server.create()

    env = docker.containers.run.call_args.kwargs["environment"]
    assert env["LEVEL_TYPE"] == "flat"
    assert env["ONLINE_MODE"] == "FALSE"
    # test servers start from a fresh world
    assert not (folder / "world").exists()


def test_create_existing(docker: MagicMock, tmp_path: Path):
    container = MagicMock(spec=Container)
    container.name = "test"
    container.status = "exited"
    docker.containers.list.return_value = [container]

    server = MinecraftServer("test", 20100, "pass", tmp_path, "normal")
    server.create()

    container.start.assert_called_once()
    docker.containers.run.assert_not_called()


def test_wait_server_exited(tmp_path: Path):
    server = MinecraftServer("test", 20100, "pass", tmp_path, "normal")
    container = MagicMock(spec=Container)
    container.status = "exited"
    container.logs.return_value = b"something went wrong"
    server.container = container

    with pytest.raises(RuntimeError, match="something went wrong"):
        server.wait_server()


def test_wait_server_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    server = MinecraftServer("test", 1, "pass", tmp_path, "normal")
    server.start_timeout = 0
    container = MagicMock(spec=Container)
    container.status = "running"
    container.logs.return_value = b"still loading"
    server.container = container

    with pytest.raises(RuntimeError, match="Timeout(.|\n)*still loading"):
        server.wait_server()
