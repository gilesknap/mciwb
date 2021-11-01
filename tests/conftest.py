import os
from time import sleep
from typing import cast

import docker
import pytest
from docker.models.containers import Container
from mcipc.rcon.je import Client
from mcwb.types import Vec3

from mciwb.player import Player

SERVER_PORT = 20400
RCON_PORT = 20401
RCON_PASSWORD = "pass"
ENTITY_NAME = "george"


@pytest.fixture(scope="session")
def minecraft_server(request):
    """
    Spin up a test minecraft server and return a client object for its
    RCON interface
    """
    def close_minecraft():
        if cont and ("MCIWB_KEEP_SERVER" not in os.environ):
            print("\nClosing the Minecraft Server ...")
            cont.stop()

    request.addfinalizer(close_minecraft)

    client = Client("localhost", RCON_PORT, passwd=RCON_PASSWORD)
    try:
        # don't start if already running
        client.connect(True)
    except ConnectionRefusedError:
        print("test minecraft server already running")
    else:
        cont = None
        return client

    docker_client = docker.from_env()

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
        "OPS": "TransformerScorn",
        "MODE": "creative",
    }
    cont = cast(
        Container,
        docker_client.containers.run(
            "itzg/minecraft-server", detach=True, environment=env, network_mode="host"
        ),
    )

    timeout = 100
    while b"RCON running" not in cont.logs():
        cont.reload()
        if cont.status != "running":
            logs = "\n".join(str(cont.logs()).split(r"\n"))
            raise RuntimeError(f"minecraft server failed to start\n\n{logs}")
        sleep(1)
        if timeout := timeout - 1 == 0:
            raise RuntimeError("Timeout Starting minecraft")

    client.connect(True)

    return client


@pytest.fixture(scope="session")
def minecraft_player(minecraft_server):

    # summon a fixed position, named entity as a substitute for a player
    minecraft_server.setworldspawn(Vec3(1, 4, 0))
    res = minecraft_server.summon(
        "armor_stand", Vec3(0, 4, 0), {"CustomName": f'"{ENTITY_NAME}"'}
    )
    print(res)

    for retry in range(10):
        try:
            player = Player(minecraft_server, ENTITY_NAME)
        except ValueError:
            sleep(1)
        else:
            break
    else:
        raise ValueError("dummy player creation failed")

    return player
