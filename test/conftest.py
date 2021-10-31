from time import sleep
from typing import cast

import docker
import pytest
from docker.models.containers import Container
from mcipc.rcon.je import Client

SERVER_PORT = 20400
RCON_PORT = 20401
RCON_PASSWORD = "pass"


@pytest.fixture(scope="session")
def minecraft_server(request):
    def close_minecraft():
        print("\nClosing the Minecraft Server ...")
        cont.stop()

    request.addfinalizer(close_minecraft)

    client = docker.from_env()

    env = {
        "EULA": "TRUE",
        "SERVER_PORT": SERVER_PORT,
        "RCON_PORT": RCON_PORT,
        "ENABLE_RCON": "true",
        "RCON_PASSWORD": RCON_PASSWORD,
        "GENERATE_STRUCTURES": "false",
        "SPAWN_ANIMALS": "false",
        "SPAWN_MONSTERS": "false",
        "SPAWN_NPCS": "false",
        "VIEW_DISTANCE": " 5",
        "SEED": 0,
        "LEVEL_TYPE": "FLAT",
        "ONLINE_MODE": "FALSE",
    }
    cont = cast(
        Container,
        client.containers.run(
            "itzg/minecraft-server", detach=True, environment=env, network_mode="host"
        ),
    )

    while b"RCON running" not in cont.logs():
        cont.reload()
        if cont.status != "running":
            logs = "\n".join(str(cont.logs()).split(r"\n"))
            raise RuntimeError(f"minecraft server failed to start\n\n{logs}")
        sleep(1)

    client = Client("localhost", RCON_PORT, passwd=RCON_PASSWORD)

    return client
