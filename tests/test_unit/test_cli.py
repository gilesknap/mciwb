import sys
from pathlib import Path
from subprocess import check_output

import pytest
from typer.testing import CliRunner

import mciwb.__main__
from mciwb import __version__
from mciwb.__main__ import cli
from mciwb.imports import Item, Vec3
from tests.mockclient import MockClient

runner = CliRunner()


def test_cli_version():
    cmd = [sys.executable, "-m", "mciwb", "--version"]
    assert check_output(cmd).decode().strip() == __version__


@pytest.fixture()
def mock_iwb(mock_client: MockClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("mciwb.iwb.Client", MockClient)
    return mock_client


def test_run(mock_iwb: MockClient, tmp_path: Path):
    script = tmp_path / "build.py"
    script.write_text(
        "world.set_block(Vec3(1, 2, 3), Item.GOLD_BLOCK)\n"
        "polygon(get_client(), Vec3(0, 0, 0), height=1, diameter=3)\n"
    )
    result = runner.invoke(
        cli, ["run", str(script), "--server", "localhost", "--port", "20400"]
    )

    assert result.exit_code == 0, (result.output, result.exception)
    assert mock_iwb.getblock(Vec3(1, 2, 3)) == Item.GOLD_BLOCK


def test_run_missing_script(tmp_path: Path):
    result = runner.invoke(cli, ["run", str(tmp_path / "missing.py")])
    assert result.exit_code == 1


def test_shell_test_mode(mock_iwb: MockClient):
    args = ["shell", "--test", "--server", "localhost", "--port", "20400"]
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, (result.output, result.exception)
    assert "no players" in result.output

    # a second shell in the same process reuses the IPython instance
    result = runner.invoke(cli, [*args, "--player", "georgeTest"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert "player: georgeTest" in result.output


def test_restore_passes_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    calls = {}
    monkeypatch.setattr(mciwb.__main__, "stop", lambda **kw: calls.update(stop=kw))
    monkeypatch.setattr(mciwb.__main__, "start", lambda **kw: calls.update(start=kw))
    restored = []
    monkeypatch.setattr(mciwb.__main__.Backup, "__init__", lambda self, **kw: None)
    monkeypatch.setattr(
        mciwb.__main__.Backup,
        "restore",
        lambda self, name, backup: restored.append((name, backup)),
    )

    result = runner.invoke(
        cli,
        ["restore", "b1", "--password", "secret", "--minecraft-version", "26.1"],
    )

    assert result.exit_code == 0, (result.output, result.exception)
    assert restored == [("b1", False)]
    assert calls["start"]["password"] == "secret"
    assert calls["start"]["minecraft_version"] == "26.1"
