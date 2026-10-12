"""
Unit tests for Player and Signs using a MockClient that returns the same
responses as a Minecraft 26.3 server.
"""

import mcwb
import pytest

from mciwb.imports import Direction, Item, Vec3
from mciwb.player import Player
from mciwb.server import MINECRAFT_VERSION
from mciwb.signs import Signs
from tests.conftest import ENTITY_NAME
from tests.mockclient import MockClient


def test_minecraft_version():
    # the server must run the release that mcwb.Item was generated from
    assert MINECRAFT_VERSION == mcwb.MINECRAFT_VERSION


def test_player_pos(mock_client: MockClient):
    player = Player(ENTITY_NAME)
    assert player.pos_f == Vec3(0.5, -60.0, 0.5)
    assert player.pos == Vec3(0, -60, 0)


@pytest.mark.parametrize(
    "yaw, facing",
    [
        (0.0, Direction.SOUTH),
        (44.9, Direction.SOUTH),
        (90.0, Direction.WEST),
        (180.0, Direction.NORTH),
        (-180.0, Direction.NORTH),
        (-90.0, Direction.EAST),
        (270.0, Direction.EAST),
    ],
)
def test_player_facing(mock_client: MockClient, yaw: float, facing: Vec3):
    mock_client.rotation = (yaw, 12.5)
    player = Player(ENTITY_NAME)
    assert player.facing == facing
    assert player.rotation == (yaw, 12.5)


def test_sign_strings():
    assert Signs.sign_block("select") == (
        'minecraft:oak_sign{front_text:{messages:["select","","",""]}}'
    )
    assert Signs.sign_item("paste") == (
        "minecraft:oak_sign[block_entity_data={"
        'id:"minecraft:sign",front_text:{messages:["paste","","",""]}},'
        'minecraft:item_name="paste"]'
    )


@pytest.mark.parametrize(
    "response, text",
    [
        ('0, -60, 3 has the following block data: "select"', "select"),
        ('0, -60, 3 has the following block data: {text: "expand"}', "expand"),
        ("The target block is not a block entity", None),
        ("Found no elements matching front_text", None),
    ],
)
def test_sign_text_regex(response: str, text: str | None):
    match = Signs._re_sign_text.search(response)  # noqa: SLF001
    assert (match.group(1) if match else None) == text


@pytest.fixture()
def signs(mock_client: MockClient):
    """A Signs object whose sign commands record their target position"""
    targets: dict[str, Vec3] = {}
    signs = Signs(Player(ENTITY_NAME))
    signs.add_sign("test", lambda pos: targets.update(test=pos))
    signs.targets = targets  # type: ignore
    return signs


def test_poll_standing_sign(mock_client: MockClient, signs: Signs):
    # the player faces south, place a standing sign 2 blocks in front
    sign_pos = Vec3(0, -60, 2)
    mock_client.place_sign(sign_pos, "test")

    signs.poll()

    # a standing sign targets the block below it and is then removed
    assert signs.targets == {"test": Vec3(0, -61, 2)}  # type: ignore
    assert str(mock_client.getblock(sign_pos)) == str(Item.AIR)


def test_poll_wall_sign(mock_client: MockClient, signs: Signs):
    sign_pos = Vec3(0, -59, 3)
    mock_client.place_sign(sign_pos, "test", Item.OAK_WALL_SIGN)

    signs.poll()

    # a wall sign targets the block behind it
    assert signs.targets == {"test": Vec3(0, -59, 4)}  # type: ignore


def test_poll_ignores_other_signs(mock_client: MockClient, signs: Signs):
    sign_pos = Vec3(0, -60, 1)
    mock_client.place_sign(sign_pos, "hello")

    signs.poll()

    assert signs.targets == {}  # type: ignore
    assert mock_client.getblock(sign_pos) == Item.OAK_SIGN


def test_give_signs(mock_client: MockClient, signs: Signs):
    signs.give_signs()

    assert mock_client.given == [
        (ENTITY_NAME, Signs.sign_item(command)) for command in signs.signs
    ]


def test_give_signs_skips_held_signs(
    mock_client: MockClient, signs: Signs, monkeypatch: pytest.MonkeyPatch
):
    # how a select sign shows up in a 26.3 player's Inventory data
    inventory = (
        'georgeTest has the following entity data: [{Slot: 0b, components: {"'
        'minecraft:item_name": "select", "minecraft:block_entity_data": '
        '{id: "minecraft:sign", front_text: {messages: ["select", "", "", ""]}}}, '
        'count: 1, id: "minecraft:oak_sign"}]'
    )
    monkeypatch.setattr(Player, "inventory", property(lambda self: inventory))

    signs.give_signs()

    given = [item for _, item in mock_client.given]
    assert Signs.sign_item("select") not in given
    assert Signs.sign_item("paste") in given
