import os
import shutil
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from mcipc.rcon.je import Client


class Backup:
    def __init__(
        self, world_name: str, world_folder: str, backup_folder: str, client: Client
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

    def restore(self, fname: Path = None):
        if not fname:
            backups = self.backup_folder.glob("*.zip")
            ordered = sorted(backups, key=os.path.getctime)
            fname = ordered[0]
        if not fname.exists():
            raise ValueError("{file} not found")

        self.client.say(f"Preparing to restore from {fname}. WORLD GOING DOWN NOW.")

        if input("This will overwrite recent changes. Are you sure? (y/n)") != "y":
            self.client.say(f"Restore Cancelled.")
            return

        self.client.save_off()

        old_world = Path(str(self.world_folder) + "-old")
        if old_world.exists():
            shutil.rmtree(old_world)

        shutil.move(self.world_folder, old_world)

        with ZipFile(fname, "r") as zip:
            zip.extractall(path=self.world_folder)

        # this assumes that there is an auto restart like docker. Manual
        # start will be required otherwise
        self.client.stop()
