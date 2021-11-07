import os
from time import sleep
from typing import cast

import docker
import pytest
from docker.models.containers import Container
from mcipc.rcon.enumerations import Item
from mcipc.rcon.je import Client
from mcwb.types import Vec3

from mciwb.copy import Copy
from mciwb.player import Player

SERVER_PORT = 20400
RCON_PORT = 20401
RCON_P = "pass"
ENTITY_NAME = "george"


@pytest.fixture(scope="session")
def minecraft_server(request):
    """
    Spin up a test minecraft server and return a client object for its
    RCON interface
    """

    def close_minecraft():
        # set env var MCIWB_KEEP_SERVER to keep server alive for faster
        # repeated tests and viewing the world with a minecraft client
        if cont and ("MCIWB_KEEP_SERVER" not in os.environ):
            print("\nClosing the Minecraft Server ...")
            cont.stop()

    request.addfinalizer(close_minecraft)

    client = Client("localhost", RCON_PORT, passwd=RCON_P)
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
        "RCON_PASSWORD": RCON_P,
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

    # this ensures that the chunks near 0,0,0 are loaded
    client.setworldspawn(Vec3(1, 4, 0))

    # don't announce every rcon command
    client.gamerule("sendCommandFeedback", False)

    # make sure that the grab function entities that are created as a side
    # effect will drop into the void
    # TODO this needs to go in mcwb since this is where grab function is
    client.setblock((0, 0, 0), Item.AIR.value)

    return client


@pytest.fixture(scope="session")
def minecraft_player(minecraft_server):

    # summon a fixed position, named entity as a substitute for a player
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


@pytest.fixture(scope="session")
def minecraft_copy(request, minecraft_server: Client, minecraft_player: Player):
    def stop_thread():
        copy.polling = False
        copy.poll_thread.join()

    request.addfinalizer(stop_thread)

    copy = Copy(minecraft_server, minecraft_player.name)
    return copy
