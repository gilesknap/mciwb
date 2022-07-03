import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from zipfile import ZIP_DEFLATED, ZipFile

from mciwb.threads import get_client


class Backup:
    def __init__(
        self,
        world_name: str,
        world_folder: str,
        backup_folder: str,
    ):
        self.name = world_name
        self.world_folder = Path(world_folder)
        self.backup_folder = Path(backup_folder)

        self.backup_folder.mkdir(parents=True, exist_ok=True)
        if not (self.world_folder / "level.dat"):
            raise ValueError(f"{world_folder} does not look like a minecraft world")

    def backup(self, running=True):
        client = get_client()

        if self.name == "" or client is None:
            logging.error("No backup details available.")
            return

        fname = datetime.strftime(datetime.now(), f"%y-%m-%d.%H.%M.%S-{self.name}.zip")

        client.say(f"Preparing to backup to {fname}")
        result = client.save_off()
        logging.debug("save_off: " + result)

        result = client.save_all()
        logging.debug("save_all: " + result)
        client.say("Backing up ...")

        file = self.backup_folder / fname
        world_files = self.world_folder.glob("**/*")
        world_files = [f for f in world_files if not f.suffix == ".lock"]
        with ZipFile(file, "w", compression=ZIP_DEFLATED) as zip_file:
            for wf in world_files:

                zip_file.write(wf, arcname=wf.relative_to(self.world_folder))
        logging.debug("ZipFile complete")

        result = client.save_on()
        logging.debug("save_on: " + result)
        client.say("Backup Complete.")

    def get_latest_zip(self) -> Path:
        backups = self.backup_folder.glob("*.zip")
        ordered = sorted(backups, key=os.path.getctime, reverse=True)
        return ordered[0]

    def restore(self, fname: Optional[Path] = None, backup=False):

        """
        restore world from backup. This must be called with the server stopped.
        """

        if not fname:
            fname = self.get_latest_zip()
        if not fname.exists():
            raise ValueError("{file} not found")

        # backup for recovery from accidental recovery ! Note that on some filesystems
        # it is OK to do this while the server is running. On other filesystems the
        # server will need to be stopped before calling this function
        if backup:
            old_world = Path(str(self.world_folder) + "-old")
            if old_world.exists():
                shutil.rmtree(old_world)
            shutil.move(str(self.world_folder), str(old_world))

        # restore zipped up backup to world folder
        with ZipFile(fname, "r") as zip_file:
            zip_file.extractall(path=self.world_folder)

        # remove lockfile if it exists
        for file in self.world_folder.glob("*.lock"):
            logging.debug(f"removing {file}")
            file.unlink()

        logging.info(f"Restored {self.world_folder} from {fname}")
