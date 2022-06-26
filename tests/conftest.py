import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from tempfile import gettempdir
from time import sleep
from typing import cast

import docker
import pytest
from docker.models.containers import Container
from mcipc.rcon.enumerations import Item
from mcipc.rcon.je import Client
from mcwb.types import Vec3

from mciwb.iwb import Iwb
from mciwb.player import Player
from mciwb.threads import set_client
from tests.mockclient import MockClient

HOST = "localhost"
SERVER_PORT = 20400
RCON_PORT = 20401
RCON_P = "pass"
ENTITY_NAME = "george"

# the locally mapped temporary folder for minecraft data

data_folder = Path(gettempdir()) / "test_mc_server"
container_name = "mciwb_server"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(pathname)s:%(lineno)d %(funcName)s " "\n\t%(message)s",
)

KEEP_SERVER = "MCIWB_KEEP_SERVER" in os.environ


def wait_server(cont: Container, count=1):
    """
    Wait until the server is ready to accept rcon connections

    Multiple calls to this with container restarts require passing a count.
    This is how many times the wait code looks for the server to come online
    in the logs.

    This is required because the --since argument to the docker logs command
    fails to return any logs at all.
    """

    start_time: datetime = datetime.now()
    timeout = 100

    cont.reload()
    if cont.status != "running":
        logs = "\n".join(str(cont.logs()).split(r"\n"))
        raise RuntimeError(f"minecraft server failed to start\n\n{logs}")

    logging.debug("waiting for mc server to come online")
    counter = 0
    for block in cont.logs(stream=True):
        print(block.decode("utf-8"))
        if b"RCON running" in block:
            counter += 1
            if counter >= count:
                break
        elapsed = datetime.now() - start_time
        if elapsed.total_seconds() > timeout:
            raise RuntimeError("Timeout Starting minecraft")
    logging.debug("mc server is online")


@pytest.fixture(scope="session")
def minecraft_container(request: pytest.FixtureRequest):
    """
    Spin up a test minecraft server and return a container object

    This fixture is run once per session, meaning that it does not need
    to be executed twice for two runs of the tests. This requires
    caution as the world must be reset to a known state.
    """

    def close_minecraft():
        # set env var MCIWB_KEEP_SERVER to keep server alive for faster
        # repeated tests and viewing the world with a minecraft client
        if cont and not KEEP_SERVER:
            logging.info("\nClosing the Minecraft Server ...")
            cont.stop()
            cont.remove()

    request.addfinalizer(close_minecraft)

    # create and launch minecraft container once per session
    docker_client = docker.from_env()

    for container in docker_client.containers.list(all=True):
        cont = cast(Container, container)
        if cont.name == container_name:
            if cont.status == "running":
                logging.info("test minecraft server already running")
                return cont
            else:
                cont.remove()
                break

    env = {
        "EULA": "TRUE",
        # "VERSION": "1.17.1",
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
        "OPS": "TransformerScorn",
        "MODE": "creative",
        "SPAWN_PROTECTION": "FALSE",
    }
    # offline mode disables OPS so dont use it if we are keeping the server
    # for testing. But normally for running CI we want this option.
    if not KEEP_SERVER:
        env["ONLINE_MODE"] = "FALSE"

    if not data_folder.exists():
        data_folder.mkdir()
    else:
        shutil.rmtree(data_folder)
        data_folder.mkdir()

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

    wait_server(cont)
    return cont


def client_connect():
    """
    Make an rcon connection, waiting for the server to come online
    """
    client = Client(HOST, RCON_PORT, passwd=RCON_P)

    for _ in range(10):
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

    # attach the new client to the current thread
    set_client(client)

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
        "armor_stand", Vec3(0, -60, 0), {"CustomName": f'"{ENTITY_NAME}"'}
    )
    logging.info(res)

    for retry in range(10):
        try:
            player = Player(ENTITY_NAME)
        except ValueError:
            sleep(1)
        else:
            break
    else:
        raise ValueError("dummy player creation failed")

    return player


@pytest.fixture()
def mciwb_world(
    request, minecraft_container, minecraft_client: Client, minecraft_player: Player
):
    def stop_thread():
        world.stop()

    request.addfinalizer(stop_thread)

    world = Iwb(HOST, RCON_PORT, passwd=RCON_P)
    world.add_player(ENTITY_NAME)

    return world


@pytest.fixture()
def mock_client():
    client = MockClient("localhost", 20400, "pass")
    set_client(client)  # type: ignore
    return client
