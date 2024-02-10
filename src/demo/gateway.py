"""
Define a castle gateway with portcullis and drawbridge
"""

from time import sleep

from mciwb.imports import Direction, FillMode, Item, Monitor, Switch, Vec3, get_client


def portcullis(position, open, width, height):
    c = get_client()
    if open:
        steps = range(1, height)
        item = Item.AIR
    else:
        steps = range(height, 0, -1)
        item = Item.ACACIA_FENCE

    for step in steps:
        start = position + Direction.UP * step
        stop = start + Direction.EAST * width
        c.fill(start, stop, item, mode=FillMode.REPLACE)
        sleep(0.5)


def drawbridge(position, open, width, length):
    c = get_client()
    if open:
        steps = range(1, length)
        item = Item.ACACIA_LOG
    else:
        item = Item.AIR
        steps = range(length - 1, 0, -1)

    for step in steps:
        start = position + Direction.NORTH * step
        stop = start + Direction.EAST * width
        c.fill(start, stop, item, mode=FillMode.REPLACE)
        sleep(0.2)


def gateway(position, width, height):
    c = get_client()
    w_front = position + Direction.WEST + Direction.NORTH + Direction.UP
    e_back_top = (
        w_front
        + Direction.SOUTH * 2
        + Direction.UP * (height + 1)
        + Direction.EAST * (width + 2)
    )

    c.fill(w_front, e_back_top, Item.STONE)

    w_front += Direction.EAST
    e_back_top += Direction.WEST + Direction.DOWN * 2

    c.fill(w_front, e_back_top, Item.AIR)


def make_gate(position=None, width=4, height=6, length=25):
    position = position or Vec3(x=621, y=72, z=-1662)

    def open_close(switch):
        o = switch.powered
        Monitor(func=portcullis, params=(position, o, width, height), once=True)
        Monitor(func=drawbridge, params=(position, o, width, length), once=True)

    gateway(position, width, height)

    switch_pos = position + Direction.SOUTH * 2 + Direction.WEST + Direction.UP
    Switch(switch_pos, Item.LEVER, open_close)
    portcullis(position, False, width, height)
