import pytest
from mcipc.rcon.je import Client

from mciwb.threads import get_client, set_client
from tests.mockclient import MockClient


@pytest.fixture(autouse=True)
def system_client(minecraft_client: Client):
    """
    Every system test talks to the real test server: attach its client to the
    test thread, in case a unit test left a MockClient there
    """
    set_client(minecraft_client)
    yield
    assert not isinstance(get_client(), MockClient)
