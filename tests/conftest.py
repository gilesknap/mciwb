import logging
import os
from pathlib import Path
from tempfile import gettempdir
from time import sleep

import pytest
from docker.models.containers import Container
from mcipc.rcon.enumerations import Item
from mcipc.rcon.je import Client
from mcwb.types import Vec3

from mciwb.iwb import Iwb
from mciwb.player import Player
from mciwb.server import HOST, MinecraftServer
from mciwb.threads import get_client, set_client
from tests.mockclient import MockClient

KEEP_SERVER = "MCIWB_KEEP_SERVER" in os.environ

RCON_PORT = 20401
RCON_P = "pass"
ENTITY_NAME = "george"
ENTITY_POS = Vec3(0, -60, 0)

test_server_name = "mciwb-test-server"
servers_folder = Path(gettempdir()) / "test-mc-servers"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(funcName)s - %(message)s (%(pathname)s:%(lineno)d)",
)


@pytest.fixture(scope="session")
def minecraft_container(request: pytest.FixtureRequest):
    """
    Spin up a test minecraft server and return a container object

    This fixture is run once per session, meaning that it does not need
    to be executed twice for two runs of the tests. This requires
    caution as the world must be reset to a known state.
    """
    mc = MinecraftServer(
        name=test_server_name,
        rcon=RCON_PORT,
        password=RCON_P,
        keep=KEEP_SERVER,
        world_type="flat",
        server_folder=servers_folder / test_server_name,
        test=True,
    )
    mc.create()

    request.addfinalizer(mc.remove)
    return mc


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


@pytest.fixture(scope="session")
def minecraft_client(minecraft_container: Container):
    """
    return an rcon connection to the test server
    """
    client = client_connect()

    # attach the new client to the current thread
    set_client(client)

    # ensure that the chunks near 0,0,0 are loaded
    client.setworldspawn(ENTITY_POS)
    # don't announce every rcon command
    client.gamerule("sendCommandFeedback", False)

    # make sure that the grab function entities that are created as a side
    # effect will drop into the void
    # TODO in 1.19 the bottom of the world is at -64 so need a fix for that!
    client.setblock((0, 0, 0), Item.AIR.value)

    return client


@pytest.fixture()
def minecraft_player():
    client = get_client()

    # summon a fixed position, named entity as a substitute for a player
    res = client.summon("armor_stand", ENTITY_POS, {"CustomName": f'"{ENTITY_NAME}"'})
    logging.info(res)

    for _ in range(10):
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
