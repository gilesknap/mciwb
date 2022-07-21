import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from mciwb.server import backup_folder, default_server_folder
from mciwb.threads import get_client


class Backup:
    re_valid_filename = re.compile(r"[^-a-zA-Z0-9_.]+")

    def __init__(
        self,
        world_folder: Path = default_server_folder / "world",
        backup_folder: Path = backup_folder,
    ):
        self.world_folder = Path(world_folder)
        self.backup_folder = Path(backup_folder)

        self.backup_folder.mkdir(parents=True, exist_ok=True)
        if not (self.world_folder / "level.dat").exists():
            raise ValueError(f"{world_folder} does not look like a minecraft world")

    def backup(self, name=None, running=True):

        fname = name or datetime.strftime(datetime.now(), "%y-%m-%d.%H.%M.%S.zip")
        fname = self.re_valid_filename.sub("_", fname)
        if not fname.endswith(".zip"):
            fname += ".zip"

        if running:
            client = get_client()
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

        if running:
            client = get_client()
            result = client.save_on()
            logging.debug("save_on: " + result)
            client.say("Backup Complete.")

    def _get_latest_zip(self) -> Path:
        backups = self.backup_folder.glob("*.zip")
        ordered = sorted(backups, key=os.path.getctime, reverse=True)
        return ordered[0]

    def restore(self, name=None, backup=False):

        """
        restore world from backup. This must be called with the server stopped.
        """

        if not name:
            rfile = self._get_latest_zip()
        else:
            if not name.endswith(".zip"):
                name += ".zip"
            rfile = backup_folder / self.re_valid_filename.sub("_", name)
        if not rfile.exists():
            raise ValueError(f"{rfile} not found")

        # backup for recovery from accidental recovery ! Note that on some filesystems
        # it is OK to do this while the server is running. On other filesystems the
        # server will need to be stopped before calling this function
        if backup:
            old_world = Path(str(self.world_folder) + "-old")
            if old_world.exists():
                shutil.rmtree(old_world)
            shutil.move(str(self.world_folder), str(old_world))

        # restore zipped up backup to world folder
        with ZipFile(rfile, "r") as zip_file:
            zip_file.extractall(path=self.world_folder)

        # remove lockfile if it exists
        for file in self.world_folder.glob("*.lock"):
            logging.debug(f"removing {file}")
            file.unlink()

        logging.info(f"Restored {self.world_folder} from {rfile}")
