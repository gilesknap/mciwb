"""
System tests for the Copy class
"""

from conftest import RCON_PASSWORD, RCON_PORT

from mcipc.rcon.je import Client
from mciwb.backup import Backup

from mciwb.copy import Copy


def test_copy_block(minecraft_server):
    backup = Backup(
        "science",
        "/data/world",
        "/data/backupfolder",
        minecraft_server,
    )
    copy = Copy(minecraft_server, "henry", backup)
