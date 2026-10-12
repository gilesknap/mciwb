from pathlib import Path
from zipfile import ZipFile

import pytest

from mciwb.backup import Backup
from tests.mockclient import MockClient


@pytest.fixture()
def world_folder(tmp_path: Path) -> Path:
    world = tmp_path / "server" / "world"
    (world / "region").mkdir(parents=True)
    (world / "level.dat").write_text("level")
    (world / "region" / "r.0.0.mca").write_text("region")
    (world / "session.lock").write_text("lock")
    return world


def test_not_a_world(tmp_path: Path):
    with pytest.raises(ValueError):
        Backup(tmp_path, tmp_path / "backups")


def test_backup_restore(world_folder: Path, tmp_path: Path):
    backups = tmp_path / "backups"
    backup = Backup(world_folder, backups)

    file = backup.backup(name="my backup", running=False)

    assert file == backups / "my_backup.zip"
    with ZipFile(file) as zip_file:
        assert sorted(zip_file.namelist()) == [
            "level.dat",
            "region/",
            "region/r.0.0.mca",
        ]

    # change the world after the backup
    (world_folder / "level.dat").write_text("changed")
    (world_folder / "region" / "r.1.0.mca").write_text("new region")

    backup.restore()

    assert (world_folder / "level.dat").read_text() == "level"
    # files created after the backup do not survive the restore
    assert not (world_folder / "region" / "r.1.0.mca").exists()
    assert not (world_folder / "session.lock").exists()


def test_restore_keeps_old_world(world_folder: Path, tmp_path: Path):
    backup = Backup(world_folder, tmp_path / "backups")
    backup.backup(name="first", running=False)
    (world_folder / "level.dat").write_text("changed")

    backup.restore("first", backup=True)

    old_world = world_folder.parent / "world-old"
    assert (old_world / "level.dat").read_text() == "changed"
    assert (world_folder / "level.dat").read_text() == "level"


def test_restore_missing(world_folder: Path, tmp_path: Path):
    backup = Backup(world_folder, tmp_path / "backups")
    with pytest.raises(ValueError, match="no backups"):
        backup.restore()
    with pytest.raises(ValueError, match="not found"):
        backup.restore("missing")


def test_backup_running(mock_client: MockClient, world_folder: Path, tmp_path: Path):
    backup = Backup(world_folder, tmp_path / "backups")

    backup.backup(name="running")

    saves = [c for c in mock_client.commands if not c.startswith("say")]
    assert saves == ["save-off", "save-all flush", "save-on"]
