"""
Defines a class for representing a lever, button or any other activator
in the world. Implements monitoring of the switch's state with callbacks.
"""

import logging
from typing import Callable, List

from mcipc.rcon.enumerations import Item, SetblockMode
from mcwb.types import Vec3

from mciwb.monitor import Monitor
from mciwb.threads import get_client

SwitchCallback = Callable[["Switch"], None]

# supported switch types and the properties to set on them
item_types = {
    "BUTTON": "[face=floor, facing=north, powered=off]",
    "LEVER": "[face=floor, facing=north, powered=off]",
    "TRIPWIRE_HOOK": "[]",
    "PRESSURE_PLATE": "[]",
}


class Switch:
    switches: List["Switch"] = []

    next_id: int = 0

    def __init__(
        self,
        position: Vec3,
        item: Item,
        callback: SwitchCallback,
        name: str = "",
    ) -> None:
        self.pos = position
        self.callback = callback
        Switch.next_id += 1
        self.id = Switch.next_id
        self.name = name if name else f"switch{self.id}"
        Switch.switches.append(self)
        self.powered = False

        for key, val in item_types.items():
            if key in str(item).upper():
                properties = val
                break
        else:
            raise ValueError(f"{item} is not a supported type of switch")

        self.on = str(item) + "[powered=true]"
        self.off = str(item) + "[powered=false]"

        # TODO pass properties for orientation to the constructor
        full_item = str(item) + properties
        res = get_client().setblock(position, full_item, mode=SetblockMode.REPLACE)
        if "Changed the block" not in res:
            logging.warning(res)
        logging.info(f"Created switch {self.name}, id {self.id} at {position}")

        self.monitor = Monitor(self.poll, name=self.name)

    def __del__(self):
        self.remove()

    def remove(self):
        if self in self.switches:
            self.switches.remove(self)
        self.monitor.stop()
        get_client().setblock(self.pos, str(Item.AIR), mode=SetblockMode.REPLACE)
        logging.info(f"Deleted switch {self.id} at {self.pos}")

    @classmethod
    def stop(cls):
        cls.monitoring = False

    def check_state(self, state: str) -> bool:
        res = get_client().execute.if_.block(self.pos, state).run("seed")
        if "Seed" in res:
            result = True
        else:
            result = False

        return result

    def poll(self):
        if self.powered:
            if self.check_state(self.off):
                self.powered = False
                if self.callback:
                    self.callback(self)
        else:
            if self.check_state(self.on):
                self.powered = True
                if self.callback:
                    self.callback(self)
