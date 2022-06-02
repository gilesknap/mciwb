import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from zipfile import ZIP_DEFLATED, ZipFile

from mcipc.rcon.je import Client


class Backup:
    def __init__(
        self,
        world_name: str,
        world_folder: str,
        backup_folder: str,
        client: Optional[Client] = None,
    ):
        self.name = world_name
        self.world_folder = Path(world_folder)
        self.backup_folder = Path(backup_folder)
        self.client = client

        if not self.backup_folder.exists():
            raise ValueError("backup folder must exist")
        if not (self.world_folder / "level.dat"):
            raise ValueError(f"{world_folder} does not look like a minecraft world")

    def backup(self):
        if self.name == "" or self.client is None:
            print("No backup details available.")
            return

        fname = datetime.strftime(datetime.now(), f"%y-%m-%d.%H.%M.%S-{self.name}.zip")

        self.client.say(f"Preparing to backup to {fname}")
        self.client.save_off()
        self.client.save_all()
        self.client.say("Backing up ...")

        file = self.backup_folder / fname
        world_files = self.world_folder.glob("**/*")
        with ZipFile(file, "w", compression=ZIP_DEFLATED) as zip:
            for wf in world_files:
                zip.write(wf, arcname=wf.relative_to(self.world_folder))

        self.client.save_on()
        self.client.say("Backup Complete.")

    def restore(self, fname: Path = None, yes=False):
        """
        restore world from backup. Note this function may be called in an instance
        of Backup that has client = None. That is so it can be run while the
        server is down.
        """
        if not fname:
            backups = self.backup_folder.glob("*.zip")
            ordered = sorted(backups, key=os.path.getctime, reverse=True)
            fname = ordered[0]
        if not fname.exists():
            raise ValueError("{file} not found")

        if not yes:
            if self.client is not None:
                self.client.say("SERVER GOING DOWN FOR RESTORE FROM BACKUP")
            if input(f"Overwrite world with with {fname} (y/n)? : ") != "y":
                if self.client is not None:
                    self.client.say("Restore Cancelled.")
                return

        old_world = Path(str(self.world_folder) + "-old")
        if old_world.exists():
            shutil.rmtree(old_world)

        # backup for recovery from accidental recovery ! Note that on some filesystems
        # it is OK to do this while the server is running. On other filesystems the
        # server will need to be stopped before calling this function
        shutil.move(str(self.world_folder), str(old_world))

        # restore zipped up backup to world folder
        with ZipFile(fname, "r") as zip:
            zip.extractall(path=self.world_folder)

        # stop the server - it will pick up the restore on restart
        if self.client is not None:
            self.client.stop()

        print(f"\n\nRestored from {fname}")
