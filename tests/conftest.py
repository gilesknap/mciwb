import os
import shutil
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import cast

import docker
import pytest
from docker.models.containers import Container
from mcipc.rcon.enumerations import Item
from mcipc.rcon.je import Client
from mcwb.types import Vec3

from mciwb.copyblock import Copy
from mciwb.player import Player

SERVER_PORT = 20400
RCON_PORT = 20401
RCON_P = "pass"
ENTITY_NAME = "george"

# the locally mapped temporary folder for minecraft data
data_folder = Path("/tmp/test-mc")
container_name = "mciwb_server"


def wait_server(cont: Container, start_time: datetime = datetime.now()):
    """
    Wait until the server is ready to accept rcon connections
    """

    timeout = 100
    while b"RCON running" not in cont.logs(since=start_time):
        cont.reload()
        if cont.status != "running":
            logs = "\n".join(str(cont.logs()).split(r"\n"))
            raise RuntimeError(f"minecraft server failed to start\n\n{logs}")
        sleep(1)
        if timeout := timeout - 1 == 0:
            raise RuntimeError("Timeout Starting minecraft")


@pytest.fixture(scope="session")
def minecraft_container(request: pytest.FixtureRequest):
    """
    Spin up a test minecraft server and return a container object
    """

    def close_minecraft():
        # set env var MCIWB_KEEP_SERVER to keep server alive for faster
        # repeated tests and viewing the world with a minecraft client
        if cont and ("MCIWB_KEEP_SERVER" not in os.environ):
            print("\nClosing the Minecraft Server ...")
            cont.stop()
            cont.remove()

    request.addfinalizer(close_minecraft)

    docker_client = docker.from_env()

    for container in docker_client.containers.list(all):
        cont = cast(Container, container)
        if cont.name == container_name:
            if cont.status == "running":
                print("test minecraft server already running")
                return cont
            else:
                cont.remove()
                break

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

    if not data_folder.exists():
        data_folder.mkdir()
    else:
        shutil.rmtree(data_folder)
        data_folder.mkdir()

    start_time = datetime.now()
    cont = cast(
        Container,
        docker_client.containers.run(
            "itzg/minecraft-server",
            detach=True,
            environment=env,
            network_mode="host",
            restart_policy={"Name": "always"},
            volumes={str(data_folder): {"bind": "/data", "mode": "rw"}},
            name=container_name,
            user=os.getuid(),
        ),
    )

    wait_server(cont, start_time)

    return cont


def client_connect():
    """
    Make an rcon connection, waiting for the server to come online
    """
    client = Client("localhost", RCON_PORT, passwd=RCON_P)

    for _ in range(40):
        try:
            client.connect(True)
        except ConnectionRefusedError:
            sleep(1)
        else:
            break
    else:
        raise TimeoutError("cannot connect to Minecraft Server")
    return client


@pytest.fixture()
def minecraft_client(minecraft_container: Container):
    """
    return an rcon connection to the test server
    """
    client = client_connect()

    # ensure that the chunks near 0,0,0 are loaded
    client.setworldspawn(Vec3(1, 4, 0))
    # don't announce every rcon command
    client.gamerule("sendCommandFeedback", False)

    # make sure that the grab function entities that are created as a side
    # effect will drop into the void
    # TODO this needs to go in mcwb since this is where grab function is
    client.setblock((0, 0, 0), Item.AIR.value)

    return client


@pytest.fixture()
def minecraft_player(minecraft_client):

    # summon a fixed position, named entity as a substitute for a player
    res = minecraft_client.summon(
        "armor_stand", Vec3(0, 4, 0), {"CustomName": f'"{ENTITY_NAME}"'}
    )
    print(res)

    for retry in range(10):
        try:
            player = Player(minecraft_client, ENTITY_NAME)
        except ValueError:
            sleep(1)
        else:
            break
    else:
        raise ValueError("dummy player creation failed")

    return player


@pytest.fixture()
def minecraft_copy(request, minecraft_client: Client, minecraft_player: Player):
    def stop_thread():
        copy.polling = False
        copy.poll_thread.join()

    request.addfinalizer(stop_thread)

    copy = Copy(minecraft_client, minecraft_player.name)
    return copy
