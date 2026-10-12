from time import monotonic, sleep

import pytest

from mciwb.imports import Item, Switch, Vec3
from tests.mockclient import MockClient


@pytest.fixture(autouse=True)
def no_switches(mock_client: MockClient):
    yield
    for switch in list(Switch.switches):
        switch.remove()


def test_switch(mock_client: MockClient):
    pos = Vec3(1, 0, 1)
    changes = []
    switch = Switch(pos, Item.LEVER, lambda s: changes.append(s.powered))

    assert mock_client.getblock(pos) == Item.LEVER
    assert not switch.check_state(switch.on)
    assert switch.check_state(switch.off)

    # flick the lever and wait for the monitor thread to notice
    mock_client.setblock(pos, "minecraft:lever[face=floor,powered=true]")
    deadline = monotonic() + 5
    while not changes and monotonic() < deadline:
        sleep(0.01)
    assert changes == [True]

    Switch.remove_named(switch.name)
    assert switch not in Switch.switches
    assert mock_client.getblock(pos) == Item.AIR


def test_unsupported_switch(mock_client: MockClient):
    with pytest.raises(ValueError):
        Switch(Vec3(0, 0, 0), Item.STONE, lambda s: None)


def test_stop(mock_client: MockClient):
    switch = Switch(Vec3(0, 0, 0), Item.STONE_BUTTON, lambda s: None)
    Switch.stop()
    assert not switch.monitor._polling
