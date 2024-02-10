"""
Define a castle gateway with portcullis
"""

from time import sleep

from mciwb.imports import Direction, FillMode, Item, Switch, Vec3, get_client, get_world


def portcullis(position, close, width=4, height=6):
    """
    Open and close a portcullis
    """
    if close:
        steps = range(height, 0, -1)
        item = Item.ACACIA_FENCE
    else:
        steps = range(1, height)
        item = Item.AIR

    c = get_client()
    for step in steps:
        start = position + Direction.UP * (step - 1)
        stop = start + Direction.EAST * width
        c.fill(start, stop, item, mode=FillMode.REPLACE)
        sleep(0.5)


def make_gate(position=None):
    """
    Create a castle gate with working portcullis
    """
    position = position or Vec3(x=623, y=73, z=-1660)

    def open_close(switch):
        portcullis(position, switch.powered)

    gate_pos = position + Direction.SOUTH + Direction.WEST * 2
    get_world().load("blocks/gate.json", gate_pos)
    Switch(gate_pos, Item.LEVER, open_close, name="portcullis")


def disable_gate():
    Switch.remove_named("portcullis")
