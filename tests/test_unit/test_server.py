"""
Unit tests for MinecraftServer with a mocked podman client
"""

import os
import socket
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from podman.domain.containers import Container

import mciwb.server
from mciwb.server import (
    MINECRAFT_VERSION,
    SERVER_IMAGE,
    MinecraftServer,
    PodmanNotAvailableError,
    container_host,
    podman_client,
)


def rootless_info(rootless: bool) -> dict:
    return {"host": {"security": {"rootless": rootless}}}


@pytest.fixture()
def podman(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock()
    client.containers.exists.return_value = False
    client.containers.run.return_value = MagicMock(spec=Container)
    client.info.return_value = rootless_info(True)
    # podman_client() is used as a context manager
    client.__enter__.return_value = client
    monkeypatch.setattr(mciwb.server, "podman_client", lambda: client)
    monkeypatch.setattr(MinecraftServer, "wait_server", lambda self: None)
    monkeypatch.setattr(MinecraftServer, "_settings", lambda self: None)
    return client


@pytest.mark.parametrize("keep", [True, False])
def test_create(podman: MagicMock, tmp_path: Path, keep: bool):
    server = MinecraftServer(
        "test",
        20100,
        "secret",
        tmp_path / "server",
        "flat",
        keep=keep,
    )
    server.create()

    args, kwargs = podman.containers.run.call_args
    assert args == (SERVER_IMAGE,)
    env = kwargs["environment"]
    assert env["VERSION"] == MINECRAFT_VERSION
    assert env["LEVEL_TYPE"] == "flat"
    assert env["RCON_PORT"] == "20100"
    assert env["SERVER_PORT"] == "20101"
    assert env["RCON_PASSWORD"] == "secret"
    assert env["PAUSE_WHEN_EMPTY_SECONDS"] == "0"
    # the podman API only accepts strings
    assert all(isinstance(v, str) for v in env.values())
    assert kwargs["ports"] == {"20100/tcp": 20100, "20101/tcp": 20101}
    assert kwargs["restart_policy"] == {"Name": "always" if keep else "no"}
    assert kwargs["volumes"] == {
        str(tmp_path / "server"): {"bind": "/data", "mode": "rw"}
    }
    # the client is closed
    podman.__exit__.assert_called_once()


def test_create_rootless(podman: MagicMock, tmp_path: Path):
    """Rootless podman maps the current user to the image's user"""
    MinecraftServer("test", 20100, "pass", tmp_path, "normal").create()

    kwargs = podman.containers.run.call_args.kwargs
    assert kwargs["userns_mode"] == {"nsmode": "keep-id", "value": "uid=1000,gid=1000"}
    assert "UID" not in kwargs["environment"]


def test_create_rootful(podman: MagicMock, tmp_path: Path):
    """Rootful podman runs the server as the current user"""
    podman.info.return_value = rootless_info(False)
    MinecraftServer("test", 20100, "pass", tmp_path, "normal").create()

    kwargs = podman.containers.run.call_args.kwargs
    assert "userns_mode" not in kwargs
    assert kwargs["environment"]["UID"] == str(os.getuid())
    assert kwargs["environment"]["GID"] == str(os.getgid())


def test_create_test_server(podman: MagicMock, tmp_path: Path):
    folder = tmp_path / "server"
    (folder / "world").mkdir(parents=True)
    server = MinecraftServer(
        "test", 20100, "pass", folder, "normal", keep=False, test=True
    )
    server.create()

    env = podman.containers.run.call_args.kwargs["environment"]
    assert env["LEVEL_TYPE"] == "flat"
    assert env["ONLINE_MODE"] == "FALSE"
    # test servers start from a fresh world
    assert not (folder / "world").exists()


def existing_container(
    podman: MagicMock, folder: Path, port: int = 20100, password: str = "pass"
) -> MagicMock:
    """Make podman report an existing, stopped server container"""
    container = MagicMock(spec=Container)
    container.name = "test"
    container.status = "exited"
    container.attrs = {
        "Config": {
            "Env": [
                f"RCON_PORT={port}",
                f"RCON_PASSWORD={password}",
                f"VERSION={MINECRAFT_VERSION}",
            ]
        },
        "Mounts": [{"Source": str(folder), "Destination": "/data"}],
    }
    podman.containers.exists.return_value = True
    podman.containers.get.return_value = container
    return container


def test_create_existing(
    podman: MagicMock, tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    container = existing_container(podman, tmp_path)

    server = MinecraftServer("test", 20100, "pass", tmp_path, "normal")
    server.create()

    container.start.assert_called_once()
    podman.containers.run.assert_not_called()
    assert "already exists" not in caplog.text


def test_create_existing_other_settings(
    podman: MagicMock, tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    """An existing container's settings are used, with a warning"""
    existing_container(podman, tmp_path / "old", port=20300, password="hunter2")

    server = MinecraftServer("test", 20100, "new", tmp_path / "new", "normal")
    server.create()

    assert (server.rcon, server.port) == (20300, 20301)
    assert server.password == "hunter2"
    assert server.server_folder == tmp_path / "old"
    assert "already exists, so its settings are reused" in caplog.text
    assert "port 20100 (using 20300)" in caplog.text
    # the password is not logged
    assert "hunter2" not in caplog.text


def test_wait_server_exited(tmp_path: Path):
    server = MinecraftServer("test", 20100, "pass", tmp_path, "normal")
    container = MagicMock(spec=Container)
    container.status = "exited"
    container.logs.return_value = iter([b"something went wrong\n"])
    server.container = container

    with pytest.raises(RuntimeError, match="something went wrong"):
        server.wait_server()


def test_wait_server_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    server = MinecraftServer("test", 1, "pass", tmp_path, "normal")
    server.start_timeout = 0
    container = MagicMock(spec=Container)
    container.status = "running"
    container.logs.return_value = iter([b"still loading\n"])
    server.container = container

    with pytest.raises(RuntimeError, match="Timeout(.|\n)*still loading"):
        server.wait_server()


def test_create_force(podman: MagicMock, tmp_path: Path):
    container = existing_container(podman, tmp_path)
    container.status = "running"

    server = MinecraftServer("test", 20100, "pass", tmp_path, "normal")
    server.create(force=True)

    container.remove.assert_called_once()
    podman.containers.run.assert_called_once()


@pytest.mark.parametrize("exists", [True, False])
def test_stop_named(podman: MagicMock, exists: bool):
    container = MagicMock(spec=Container)
    podman.containers.exists.return_value = exists
    podman.containers.get.return_value = container

    MinecraftServer.stop_named("test")

    assert container.remove.called == exists


@pytest.fixture()
def no_sockets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """An environment with no podman sockets, returns the XDG_RUNTIME_DIR"""
    monkeypatch.delenv("CONTAINER_HOST", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(mciwb.server, "ROOTFUL_SOCKET", tmp_path / "rootful.sock")
    return tmp_path


def make_socket(path: Path) -> socket.socket:
    path.parent.mkdir(parents=True, exist_ok=True)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(path))
    return sock


def test_container_host_env(no_sockets: Path, monkeypatch: pytest.MonkeyPatch):
    make_socket(no_sockets / "podman" / "podman.sock").close()
    monkeypatch.setenv("CONTAINER_HOST", "unix:///somewhere/podman.sock")
    assert container_host() == "unix:///somewhere/podman.sock"


def test_container_host_rootless(no_sockets: Path):
    make_socket(no_sockets / "rootful.sock").close()
    rootless = no_sockets / "podman" / "podman.sock"
    make_socket(rootless).close()
    assert container_host() == f"unix://{rootless}"


def test_container_host_rootful(no_sockets: Path):
    make_socket(no_sockets / "rootful.sock").close()
    assert container_host() == f"unix://{no_sockets / 'rootful.sock'}"


def test_container_host_missing(no_sockets: Path):
    with pytest.raises(PodmanNotAvailableError, match="podman.socket"):
        container_host()


def test_podman_client_not_responding(no_sockets: Path):
    # a socket that nothing is listening on
    make_socket(no_sockets / "rootful.sock").close()
    with pytest.raises(PodmanNotAvailableError, match="not responding"):
        podman_client()
