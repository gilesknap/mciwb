import logging
from pathlib import Path

import pytest
from docker.models.containers import Container
from mcipc.rcon.item import Item
from mcwb.itemlists import grab
from mcwb.types import Vec3
from mcwb.volume import Volume

from mciwb import Client
from mciwb.backup import Backup
from mciwb.threads import set_client
from tests.conftest import (
    HOST,
    KEEP_SERVER,
    RCON_P,
    RCON_PORT,
    data_folder,
    wait_server,
)


@pytest.mark.skipif(KEEP_SERVER, reason="KEEP_SERVER incompatible with backup")
def test_backup_restore(minecraft_container: Container, tmp_path: Path):
    """
    Test the backup and restore functionality.

    Backup a server, make a change to the world, restore the backup, and
    verify that the world has been restored.

    Requires use of client contexts so that we can restart clients.

    (TODO: need to look at why client.close does not work, as contexts were
    the only way to get this working)
    """

    backup_folder = Path(tmp_path) / "backup"
    data = Path(data_folder) / "world"
    backup_folder.mkdir()

    test_block = Vec3(10, 10, 10)
    backup = Backup("test_world", str(data), str(backup_folder))

    # make a change to the world which is to be backed up
    with Client(HOST, RCON_PORT, passwd=RCON_P) as client:
        set_client(client)
        result = client.setblock(test_block, Item.RED_CONCRETE.value)
        logging.debug("setblock %s", result)
        client.stop()

    # restart the server flush the data
    minecraft_container.wait()
    minecraft_container.start()
    wait_server(minecraft_container, count=2)

    with Client(HOST, RCON_PORT, passwd=RCON_P) as client:
        set_client(client)
        # backup the world
        backup.backup()
        # overwrite the backed up change in the world
        result = client.setblock(test_block, Item.YELLOW_CONCRETE.value)
        logging.debug("setblock %s", result)
        client.stop()

    minecraft_container.wait()
    logging.debug("wait returned, restoring ...")
    backup.restore(backup=True)

    logging.debug("restore done, starting ...")
    minecraft_container.start()

    logging.debug("waiting for start ...")
    wait_server(minecraft_container, count=3)

    logging.debug("started, getting block ...")
    with Client(HOST, RCON_PORT, passwd=RCON_P) as client:
        set_client(client)
        # TODO mcwb should break out a getblock function from grab
        grab_volume = Volume.from_corners(test_block, test_block)
        restored_blocks = grab(client, grab_volume)

    assert restored_blocks[0][0][0] == Item.RED_CONCRETE
