import logging
import os
from pathlib import Path
from tempfile import gettempdir
from time import sleep

import pytest
from mcwb.types import Vec3

from mciwb.iwb import Iwb
from mciwb.monitor import Monitor
from mciwb.player import Player, PlayerNotInWorldError
from mciwb.server import HOST, MinecraftServer, podman_client
from mciwb.threads import Client, get_client, set_client, thread_local
from tests.mockclient import MockClient

KEEP_SERVER = "MCIWB_KEEP_SERVER" in os.environ

RCON_PORT = 20401
RCON_P = "pass"
ENTITY_NAME = "georgeTest"
ENTITY_POS = Vec3(0, -60, 0)

test_server_name = "mciwb-test-server"
test_backup_name = "mciwb-backup-server"
# podman resolves bind mount paths on its host, so the devcontainer mounts this
# folder at the same path as on its host (see .devcontainer/devcontainer.json)
servers_folder = Path(gettempdir()) / "test-mc-servers"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(funcName)s - %(message)s (%(pathname)s:%(lineno)d)",
)

SYSTEM_TESTS = Path(__file__).parent / "test_system"


def _podman_available() -> bool:
    try:
        podman_client().close()
    except Exception:
        return False
    return True


# tryfirst: the marker must be added before pytest's own -m deselection runs
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]):
    """
    Mark everything under tests/test_system as a 'system' test.

    System tests launch a real Minecraft server in a podman container. When no
    podman service is reachable they are skipped, except under CI where a
    missing podman service must be reported as a failure rather than hidden.

    Run just the unit tests with: pytest -m "not system"
    """
    system_items = [i for i in items if SYSTEM_TESTS in i.path.parents]
    for item in system_items:
        item.add_marker(pytest.mark.system)

    if system_items and "CI" not in os.environ and not _podman_available():
        skip = pytest.mark.skip(reason="no podman service available for system tests")
        for item in system_items:
            item.add_marker(skip)


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
        backup_folder=servers_folder / test_backup_name,
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
def minecraft_client(minecraft_container: MinecraftServer):
    """
    return an rcon connection to the test server
    """
    client = client_connect()

    # attach the new client to the current thread
    set_client(client)

    # put the world spawn at the test entity. Note this does not keep chunks
    # loaded, MinecraftServer._settings forceloads the chunks used in tests
    client.setworldspawn(ENTITY_POS)
    # don't announce every rcon command
    client.gamerule("send_command_feedback", False)

    return client


@pytest.fixture()
def minecraft_player():
    """
    A named armor stand that stands in for a player. Uses the client of the
    current thread: a MockClient in unit tests, the test server in system
    tests (see tests/test_system/conftest.py)
    """
    client = get_client()

    # remove any stand left over from a previous test
    client.kill(f"@e[name={ENTITY_NAME}]")
    # summon a fixed position, named entity as a substitute for a player.
    # CustomName is an SNBT text component, a plain string is a literal name
    res = client.summon("armor_stand", ENTITY_POS, {"CustomName": ENTITY_NAME})
    logging.info(res)

    for _ in range(10):
        try:
            player = Player(ENTITY_NAME)
            player.pos  # noqa: B018 - check that the entity can be found
        except PlayerNotInWorldError:
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
    # the test entity is an armor stand, so skip op and gamemode
    world.add_player(ENTITY_NAME, setup=False)

    return world


@pytest.fixture()
def mock_client():
    """
    Use a MockClient with an empty mock world for the current thread, and
    restore the previous client afterwards
    """
    previous = getattr(thread_local, "client", None)
    MockClient.reset()
    client = MockClient("localhost", 20400, "pass")
    set_client(client)  # type: ignore
    yield client
    MockClient.reset()
    if previous is None:
        del thread_local.client
    else:
        set_client(previous)


@pytest.fixture(autouse=True)
def stop_monitors():
    """Make sure no test leaves Monitor threads running"""
    yield
    Monitor.stop_all()
