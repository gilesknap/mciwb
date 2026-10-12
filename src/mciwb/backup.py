"""
Backup and restore the world folder of a Minecraft server as zip files
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from mciwb.logging import log
from mciwb.server import backup_folder_default, default_server_folder
from mciwb.threads import get_client


class Backup:
    """
    Backup and restore a Minecraft world folder.

    :param world_folder: the world folder of the server (containing level.dat)
    :param backup_folder: the folder to save backup zip files in
    """

    re_valid_filename = re.compile(r"[^-a-zA-Z0-9_.]+")

    def __init__(
        self,
        world_folder: Path = default_server_folder / "world",
        backup_folder: Path = backup_folder_default,
    ):
        self.world_folder = Path(world_folder)
        self.backup_folder = Path(backup_folder)
        self.backup_folder.mkdir(parents=True, exist_ok=True)

    def backup(self, name: str | None = None, running: bool = True) -> Path:
        """
        Backup the world folder to a zip file in the backup folder.

        :param name: the name of the backup file, defaults to the current
            date and time
        :param running: True if the server is running. The server is then
            told to save everything to disk and pause saving during the backup.
            This needs an RCON client for the current thread (see `get_client`)

        :returns: the path of the backup file

        :raises ValueError: if the world folder is not a Minecraft world
        """
        if not (self.world_folder / "level.dat").exists():
            raise ValueError(
                f"{self.world_folder} does not look like a minecraft world"
            )

        fname = name or datetime.strftime(datetime.now(), "%y-%m-%d.%H.%M.%S.zip")
        fname = self.re_valid_filename.sub("_", fname)
        if not fname.endswith(".zip"):
            fname += ".zip"

        file = self.backup_folder / fname
        try:
            if running:
                client = get_client()
                client.say(f"Preparing to backup to {fname}")
                result = client.save_off()
                log.debug("save_off: " + result)

                # flush makes the save synchronous, so the world is complete
                # on disk
                result = client.save_all(flush=True)
                log.debug("save_all: " + result)
                client.say("Backing up ...")

            world_files = self.world_folder.glob("**/*")
            world_files = [f for f in world_files if not f.suffix == ".lock"]
            with ZipFile(file, "w", compression=ZIP_DEFLATED) as zip_file:
                for wf in world_files:
                    zip_file.write(wf, arcname=wf.relative_to(self.world_folder))
            log.debug("ZipFile complete")
        finally:
            if running:
                client = get_client()
                result = client.save_on()
                log.debug("save_on: " + result)
                client.say("Backup Complete.")

        log.info(f"Backed up {self.world_folder} to {file}")
        return file

    def _get_latest_zip(self) -> Path:
        backups = self.backup_folder.glob("*.zip")
        ordered = sorted(backups, key=os.path.getmtime, reverse=True)
        if not ordered:
            raise ValueError(f"no backups found in {self.backup_folder}")
        return ordered[0]

    def restore(self, name: str | None = None, backup: bool = False) -> None:
        """
        Restore the world folder from a backup. The server must be stopped.

        The current world folder is replaced. It is kept as a sibling folder
        with the suffix '-old' if *backup* is True, and deleted otherwise.

        :param name: the name of the backup file, defaults to the latest backup
        :param backup: keep the current world folder as '<world>-old'

        :raises ValueError: if the backup file does not exist
        """

        if not name:
            rfile = self._get_latest_zip()
        else:
            if not name.endswith(".zip"):
                name += ".zip"
            rfile = self.backup_folder / self.re_valid_filename.sub("_", name)
        if not rfile.exists():
            raise ValueError(f"{rfile} not found")

        # clear out the current world so that the restore is faithful: files
        # created after the backup was taken must not survive
        if self.world_folder.exists():
            if backup:
                old_world = Path(str(self.world_folder) + "-old")
                if old_world.exists():
                    shutil.rmtree(old_world)
                shutil.move(str(self.world_folder), str(old_world))
            else:
                shutil.rmtree(self.world_folder)

        # restore zipped up backup to world folder
        with ZipFile(rfile, "r") as zip_file:
            zip_file.extractall(path=self.world_folder)

        # remove lockfile if it exists
        for file in self.world_folder.glob("*.lock"):
            log.debug(f"removing {file}")
            file.unlink()

        log.info(f"Restored {self.world_folder} from {rfile}")
