import logging
import os
from pathlib import Path

import pytest
from mcipc.rcon.item import Item
from mcwb.itemlists import grab
from mcwb.types import Vec3
from mcwb.volume import Volume

from mciwb import Client
from mciwb.backup import Backup
from mciwb.threads import set_client
from tests.conftest import HOST, RCON_P
from tests.server import MinecraftServer

GITHUB_ACTIONS = "GITHUB_ACTIONS" in os.environ


@pytest.mark.skipif(
    GITHUB_ACTIONS, reason="file permissions problems on github - skipping"
)
def test_backup_restore(tmp_path: Path):
    """
    Test the backup and restore functionality.

    Backup a server, make a change to the world, restore the backup, and
    verify that the world has been restored.

    Requires use of client contexts so that we can restart clients.

    (TODO: need to look at why client.close does not work, as contexts were
    the only way to get this working)
    """

    BACKUP_RCON = 20600
    backup_folder = Path(tmp_path) / "backup"
    backup_folder.mkdir()

    test_block = Vec3(100, 100, 100)

    # create a new world to backup from
    mc_backup = MinecraftServer(name="mciwb_backup", rcon=BACKUP_RCON)
    backup = Backup("backup_world", str(mc_backup.world), str(backup_folder))
    mc_backup.minecraft_create()

    # make a change to the world which is to be backed up
    with Client(HOST, BACKUP_RCON, passwd=RCON_P) as client:
        set_client(client)
        result = client.setblock(test_block, Item.RED_CONCRETE.value)
        logging.info("setblock %s", result)
        # backup the world
        backup.backup()

    RESTORE_RCON = 20500
    # create a new world to restore into
    mc_restore = MinecraftServer(name="mciwb_restore", rcon=RESTORE_RCON)
    mc_restore.minecraft_create()
    mc_restore.stop()
    restore = Backup("restore_world", str(mc_restore.world), str(backup_folder))
    # restore the world and the start the server
    restore.restore()
    mc_restore.start()

    with Client(HOST, RESTORE_RCON, passwd=RCON_P) as client:
        set_client(client)
        # TODO mcwb should break out a getblock function from grab
        grab_volume = Volume.from_corners(test_block, test_block)
        restored_blocks = grab(client, grab_volume)

    # shut down the servers
    mc_restore.minecraft_remove()
    mc_backup.minecraft_remove()

    assert restored_blocks[0][0][0] == Item.RED_CONCRETE