"""
Make a pet bat follow you around floating over your head
"""

from mciwb.imports import Direction, Monitor, get_client, get_world


def enable_bat():
    name = "bat"
    Monitor.stop_named(name)
    Monitor(do_bat, name=name, poll_rate=0.1)


def do_bat():
    c = get_client()

    w = get_world()

    c.teleport(
        targets="@e[limit=1, type=bat]",
        location=w.player.pos_f + Direction.UP * 2.5,
        rotation=w.player.rotation,
    )
