from pathlib import Path
from time import sleep

from docker.models.containers import Container
from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb.itemlists import grab
from mcwb.types import Vec3
from mcwb.volume import Volume

from mciwb.backup import Backup
from tests.conftest import client_connect, data_folder


def test_backup_restore(
    minecraft_container: Container, minecraft_client: Client, tmp_path
):

    backup_folder = Path(tmp_path) / "backup"
    data = Path(data_folder) / "world"
    backup_folder.mkdir()

    test_block = Vec3(10, 10, 10)
    backup = Backup("testworld", str(data), str(backup_folder), minecraft_client)

    minecraft_client.setblock(test_block, Item.RED_CONCRETE.value)
    backup.backup()
    minecraft_client.setblock(test_block, Item.YELLOW_CONCRETE.value)

    minecraft_container.stop()
    backup.client = None
    backup.restore(yes=True)
    minecraft_container.start()

    client = client_connect()
    sleep(5)

    # TODO mcwb should break out a getblock function from grab
    grab_volume = Volume.from_corners(test_block, test_block)
    restored_blocks = grab(client, grab_volume)

    assert restored_blocks[0][0][0] == Item.RED_CONCRETE
