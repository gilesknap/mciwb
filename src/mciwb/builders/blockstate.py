"""
Block states: a block id plus properties, e.g.
``minecraft:oak_stairs[facing=east,half=bottom,shape=straight]``.

`BlockState` parses and formats these strings, and rotates and mirrors them
about the Y axis (used to rotate schematics). `stair_shapes` works out the
``shape`` that Minecraft gives a layer of stairs, so that the builders can
emit the states that the server would settle on anyway.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mcwb import Direction, Item, Vec3

__all__ = [
    "Block",
    "BlockState",
    "facing_name",
    "full_block_of",
    "slab_of",
    "stair_shapes",
]

# the four horizontal directions in clockwise order, viewed from above
_CLOCKWISE = ["north", "east", "south", "west"]
_VECTORS = {
    "north": Direction.NORTH,
    "east": Direction.EAST,
    "south": Direction.SOUTH,
    "west": Direction.WEST,
    "up": Direction.UP,
    "down": Direction.DOWN,
}
_MIRRORS = {
    "x": {"east": "west", "west": "east"},
    "z": {"north": "south", "south": "north"},
}
# canonical order of the direction words in a rail shape e.g. south_east
_RAIL_ORDER = ["north", "south", "east", "west"]
_RAIL_WORDS = {*_RAIL_ORDER, "ascending"}
_HANDED = {"left": "right", "right": "left"}


def facing_name(direction: Vec3) -> str:
    """
    The block state name of a ``Direction``, e.g. ``"east"`` for
    ``Direction.EAST``

    :raises ValueError: if *direction* is not one of the six Directions
    """
    for name, vector in _VECTORS.items():
        if tuple(vector) == tuple(direction):
            return name
    raise ValueError(f"{direction} is not a Direction")


#: a property value for `BlockState.of` and `BlockState.with_props`
PropValue = str | bool | int | Vec3


def _prop_value(value: PropValue) -> str:
    """The block state text of a property value"""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    return facing_name(value)


def _block_id(name: str) -> str:
    name = name.strip()
    return name if ":" in name else f"minecraft:{name}"


@dataclass(frozen=True)
class BlockState:
    """
    A block id and its block state properties.

    ``str(state)`` gives the form that ``setblock`` and ``fill`` accept, and
    that Sponge schematic palettes use::

        >>> state = BlockState.of(Item.OAK_STAIRS, facing="east", half="bottom")
        >>> str(state)
        'minecraft:oak_stairs[facing=east,half=bottom]'
        >>> str(state.rotate(1))
        'minecraft:oak_stairs[facing=south,half=bottom]'
        >>> BlockState.parse("stone").name
        'minecraft:stone'

    :ivar name: the namespaced block id, e.g. ``minecraft:oak_stairs``
    :ivar props: the block state properties, e.g. ``{"facing": "east"}``.
        Properties that are not given take the block's default value.
    """

    name: str
    props: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def parse(cls, block: Block) -> BlockState:
        """
        Make a BlockState from an ``Item``, a block state string or a BlockState.
        Block entity data (``{...}``) at the end of a string is not supported.
        """
        if isinstance(block, BlockState):
            return block
        if isinstance(block, Item):
            return cls(block.value)
        name, _, rest = str(block).partition("[")
        props: dict[str, str] = {}
        if rest:
            if not rest.endswith("]"):
                raise ValueError(f"invalid block state '{block}'")
            for pair in rest[:-1].split(","):
                if pair.strip():
                    key, sep, value = pair.partition("=")
                    if not sep:
                        raise ValueError(f"invalid block state '{block}'")
                    props[key.strip()] = value.strip()
        return cls(_block_id(name), props)

    @classmethod
    def of(cls, block: Block, **props: PropValue) -> BlockState:
        """
        Make a BlockState from a block and extra properties, e.g.
        ``BlockState.of(Item.OAK_STAIRS, facing=Direction.EAST)``. A Direction
        is converted to its name, a bool to ``true``/``false`` and an int to
        its digits, e.g. ``BlockState.of(Item.SNOW, layers=3)``. The new
        properties replace any that the block already has.
        """
        return cls.parse(block).with_props(**props)

    def with_props(self, **props: PropValue) -> BlockState:
        """
        A copy of this state with some properties added or replaced, e.g.
        ``.with_props(half="top", waterlogged=True, rotation=4)``
        """
        new = dict(self.props)
        for key, value in props.items():
            new[key] = _prop_value(value)
        return BlockState(self.name, new)

    def __hash__(self) -> int:
        return hash((self.name, tuple(sorted(self.props.items()))))

    @property
    def item(self) -> Item:
        """
        The ``Item`` for this block, without its properties

        :raises ValueError: if the block is not in ``Item`` e.g. a modded block
        """
        return Item(self.name)

    @property
    def is_air(self) -> bool:
        return self.name in (
            "minecraft:air",
            "minecraft:cave_air",
            "minecraft:void_air",
        )

    def __str__(self) -> str:
        if not self.props:
            return self.name
        props = ",".join(f"{key}={value}" for key, value in sorted(self.props.items()))
        return f"{self.name}[{props}]"

    def _map_directions(self, turn: dict[str, str], handed: bool) -> BlockState:
        """
        Apply a mapping of horizontal direction names to the properties that
        hold directions: facing, rotation-like names, axis, connection
        properties named after directions (fences, walls, redstone ...) and
        rail shapes. If *handed* the mapping is a reflection, so left and
        right swap too.
        """
        props: dict[str, str] = {}
        for key, value in self.props.items():
            new_key = turn.get(key, key)
            if key in ("facing", "horizontal_facing", "orientation"):
                parts = value.split("_")
                value = "_".join(turn.get(part, part) for part in parts)
            elif key == "shape" and value.split("_")[0] in ("inner", "outer"):
                if handed:
                    kind, side = value.split("_")
                    value = f"{kind}_{_HANDED[side]}"
            elif key == "shape" and set(value.split("_")) <= _RAIL_WORDS:
                # rail shapes e.g. north_south, ascending_east, south_west
                parts = [turn.get(part, part) for part in value.split("_")]
                if "ascending" not in parts:
                    parts.sort(key=_RAIL_ORDER.index)
                value = "_".join(parts)
            elif key in ("hinge", "type") and value in _HANDED and handed:
                value = _HANDED[value]
            props[new_key] = value
        return BlockState(self.name, props)

    def rotate(self, steps: int = 1) -> BlockState:
        """
        Rotate the block about the Y axis by *steps* quarter turns clockwise,
        viewed from above (north becomes east). Updates ``facing``, ``axis``,
        ``rotation`` (signs, banners, heads), direction named connections
        (fences, walls, panes, redstone) and rail ``shape``.
        """
        steps %= 4
        if steps == 0:
            return self
        turn = {name: _CLOCKWISE[(i + steps) % 4] for i, name in enumerate(_CLOCKWISE)}
        state = self._map_directions(turn, handed=False)
        props = dict(state.props)
        if steps % 2 and props.get("axis") in ("x", "z"):
            props["axis"] = "z" if props["axis"] == "x" else "x"
        if "rotation" in props:
            props["rotation"] = str((int(props["rotation"]) + 4 * steps) % 16)
        return BlockState(self.name, props)

    def mirror(self, axis: str) -> BlockState:
        """
        Mirror the block along the ``"x"`` axis (east and west swap) or the
        ``"z"`` axis (north and south swap). Also swaps left and right, e.g.
        the stairs shape ``outer_left`` becomes ``outer_right``.
        """
        if axis not in _MIRRORS:
            raise ValueError("axis must be 'x' or 'z'")
        state = self._map_directions(_MIRRORS[axis], handed=True)
        props = dict(state.props)
        if "rotation" in props:
            # rotation 0 is south, counting sixteenths of a turn clockwise
            centre = 16 if axis == "x" else 8
            props["rotation"] = str((centre - int(props["rotation"])) % 16)
        return BlockState(self.name, props)


Block = Item | str | BlockState
"""A block: an ``Item``, a block state string such as ``"minecraft:stone"``
or ``"oak_stairs[facing=east]"``, or a `BlockState`"""


def _turn(name: str, quarter_turns: int) -> str:
    return _CLOCKWISE[(_CLOCKWISE.index(name) + quarter_turns) % 4]


def stair_shapes(stairs: Mapping[tuple[int, int], str]) -> dict[tuple[int, int], str]:
    """
    Work out the ``shape`` of each stairs block in one horizontal layer of
    stairs of the same ``half``, as Minecraft does when the blocks are placed.

    :param stairs: the ``facing`` of each stairs block, keyed by ``(x, z)``
    :returns: the ``shape`` of each stairs block, keyed by ``(x, z)``

    A stairs block's ``facing`` is the side of its full height step, so
    people walking up it travel in that direction. A corner forms when the
    stairs in front of (or behind) it face across it: ``outer_left`` has its
    high corner on the ``facing`` side and the side counterclockwise from
    it, ``outer_right`` on the clockwise side. This follows
    ``StairBlock.getStairsShape`` in Minecraft.
    """

    def neighbour(pos: tuple[int, int], name: str) -> str | None:
        vector = _VECTORS[name]
        return stairs.get((pos[0] + int(vector.x), pos[1] + int(vector.z)))

    def can_take_shape(pos: tuple[int, int], facing: str, side: str) -> bool:
        return neighbour(pos, side) != facing

    shapes = {}
    for pos, facing in stairs.items():
        shape = "straight"
        front = neighbour(pos, facing)
        back = neighbour(pos, _turn(facing, 2))
        if (
            front is not None
            and front not in (facing, _turn(facing, 2))
            and can_take_shape(pos, facing, _turn(front, 2))
        ):
            side = "left" if front == _turn(facing, -1) else "right"
            shape = f"outer_{side}"
        elif (
            back is not None
            and back not in (facing, _turn(facing, 2))
            and can_take_shape(pos, facing, back)
        ):
            side = "left" if back == _turn(facing, -1) else "right"
            shape = f"inner_{side}"
        shapes[pos] = shape
    return shapes


def _stairs_base(stairs: Block) -> str:
    name = BlockState.parse(stairs).name
    if not name.endswith("_stairs"):
        raise ValueError(f"{name} is not a stairs block")
    return name.removeprefix("minecraft:").removesuffix("_stairs")


def slab_of(stairs: Block) -> Item:
    """
    The slab made of the same material as a stairs block, e.g.
    ``Item.OAK_SLAB`` for ``Item.OAK_STAIRS``

    :raises ValueError: if there is no matching slab
    """
    base = _stairs_base(stairs)
    try:
        return Item(f"{base}_slab")
    except ValueError:
        raise ValueError(f"no slab matches {stairs}, give one explicitly") from None


def full_block_of(stairs: Block) -> Item:
    """
    The full block made of the same material as a stairs block, e.g.
    ``Item.OAK_PLANKS`` for ``Item.OAK_STAIRS``, ``Item.STONE_BRICKS`` for
    ``Item.STONE_BRICK_STAIRS``

    :raises ValueError: if there is no matching block
    """
    base = _stairs_base(stairs)
    for name in (f"{base}_planks", f"{base}s", f"{base}_block", base):
        try:
            return Item(name)
        except ValueError:
            continue
    raise ValueError(f"no full block matches {stairs}, give one explicitly")
