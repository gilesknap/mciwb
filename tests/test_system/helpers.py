from collections.abc import Callable
from time import monotonic, sleep

from mcwb import Item, Vec3

from mciwb.threads import get_client


def wait_until(predicate: Callable[[], bool], timeout: float = 10.0) -> bool:
    """Poll predicate until it is True, return False on timeout"""
    deadline = monotonic() + timeout
    while not predicate():
        if monotonic() > deadline:
            return False
        sleep(0.1)
    return True


def is_block(pos: Vec3, block: Item | str) -> bool:
    """Test the block at pos with 'execute if block'"""
    return "Seed" in get_client().execute.if_.block(pos, str(block)).run("seed")
