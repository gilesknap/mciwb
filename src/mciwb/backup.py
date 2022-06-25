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

        if not self.backup_folder.exists():
            raise ValueError("backup folder must exist")
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
        with ZipFile(file, "w", compression=ZIP_DEFLATED) as zip_file:
            for wf in world_files:
                zip_file.write(wf, arcname=wf.relative_to(self.world_folder))
        logging.debug("ZipFile complete")

        result = client.save_on()
        logging.debug("save_on: " + result)
        client.say("Backup Complete.")

    def restore(self, fname: Optional[Path] = None, yes=False, restart=True):

        """
        restore world from backup. Note this function may be called in an instance
        of Backup that has client = None. That is so it can be run while the
        server is down.
        """
        client = get_client()

        if not fname:
            backups = self.backup_folder.glob("*.zip")
            ordered = sorted(backups, key=os.path.getctime, reverse=True)
            fname = ordered[0]
        if not fname.exists():
            raise ValueError("{file} not found")

        if not yes:
            if client is not None:
                client.say("SERVER GOING DOWN FOR RESTORE FROM BACKUP")
            if input(f"Overwrite world with with {fname} (y/n)? : ") != "y":
                if client is not None:
                    client.say("Restore Cancelled.")
                return

        # stop the server - it will pick up the restore on restart
        if restart:
            if client is not None:
                result = client.stop()
                logging.debug("stop: " + result)

        old_world = Path(str(self.world_folder) + "-old")
        if old_world.exists():
            shutil.rmtree(old_world)

        # backup for recovery from accidental recovery ! Note that on some filesystems
        # it is OK to do this while the server is running. On other filesystems the
        # server will need to be stopped before calling this function
        shutil.move(str(self.world_folder), str(old_world))

        # restore zipped up backup to world folder
        with ZipFile(fname, "r") as zip_file:
            zip_file.extractall(path=self.world_folder)

        logging.info(f"Restored from {fname}")
