import logging
from pathlib import Path

from docker.models.containers import Container
from mcipc.rcon.item import Item
from mcwb.itemlists import grab
from mcwb.types import Vec3
from mcwb.volume import Volume

from mciwb import Client
from mciwb.backup import Backup
from mciwb.threads import set_client
from tests.conftest import HOST, RCON_P, RCON_PORT, data_folder, wait_server


def test_backup_restore(
    minecraft_container: Container, minecraft_client: Client, tmp_path: Path
):
    """
    Test the backup and restore functionality.

    Backup a server, make a change to the world, restore the backup, and
    verify that the world has been restored.

    Requires use of client contexts so that we can restart clients.

    (TODO: need to look at why client.close does not work, as contexts were
    the only way to get this working)
    TODO tidy up the need for set_client all the time?
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

    # ensure world file changes get written out
    minecraft_client.close()
    minecraft_container.restart()
    wait_server(minecraft_container, count=2)

    with Client(HOST, RCON_PORT, passwd=RCON_P) as client:
        set_client(client)
        # backup the world
        backup.backup()
        # overwrite the backed up change in the world
        result = client.setblock(test_block, Item.YELLOW_CONCRETE.value)
        logging.debug("setblock %s", result)

    with Client(HOST, RCON_PORT, passwd=RCON_P) as client:
        set_client(client)
        # restore the backed up change
        backup.restore(yes=True)

    minecraft_container.restart()
    wait_server(minecraft_container, count=3)

    with Client(HOST, RCON_PORT, passwd=RCON_P) as client:
        set_client(client)
        # TODO mcwb should break out a getblock function from grab
        grab_volume = Volume.from_corners(test_block, test_block)
        restored_blocks = grab(client, grab_volume)

    assert restored_blocks[0][0][0] == Item.RED_CONCRETE
