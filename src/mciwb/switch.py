from collections.abc import Callable

from mcipc.rcon.enumerations import Item, SetblockMode
from mcwb.types import Vec3

from mciwb.logging import log
from mciwb.monitor import Monitor
from mciwb.threads import get_client

SwitchCallback = Callable[["Switch"], None]


item_types = {
    "BUTTON": "[face=floor, facing=north]",
    "LEVER": "[face=floor, facing=north]",
    "TRIPWIRE_HOOK": "[]",
    "PRESSURE_PLATE": "[]",
}
"""
supported switch types and the properties to set on them
"""


class Switch:
    """
    Defines a class for representing a lever, button or any other activator
    in the world. Implements monitoring of the switch's state with callbacks.

    :param position: the position of the switch in the world
    :param item: the item type of the switch (must be one of `item_types`)
    :param callback: the callback to call when the switch's state changes
    :param name: the name of the switch (defaults to "switch" + id)

    :ivar id: the id of the switch
    :ivar name: the name of the switch
    :ivar pos: the position of the switch in the world
    :ivar powered: the current state of the switch (True if powered)
    :ivar callback: the callback to call when the switch's state changes
    :ivar monitor: the `Monitor` object for the switch
    :ivar switches: the list of all switches in the world
    :ivar next_id: the next id to assign to a switch
    :ivar on: the state to check for a powered switch
    :ivar off: the state to check for an un-powered switch
    :ivar monitor: the `Monitor` object for the switch
    """

    switches: list["Switch"] = []

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
            log.warning(res)
        log.info(f"Created switch {self.name}, id {self.id} at {position}")

        self.monitor = Monitor(self._poll, name=self.name)

    @classmethod
    def remove_named(cls, name: str):
        """
        Remove a switch by name.
        """
        for switch in cls.switches:
            if switch.name == name:
                switch.remove()
        # fail silently if the switch isn't found

    def remove(self):
        """
        Remove the switch from the world. Clean up the monitor.
        """
        if self in self.switches:
            self.switches.remove(self)
        self.monitor.stop()
        get_client().setblock(self.pos, str(Item.AIR), mode=SetblockMode.REPLACE)
        log.info(f"Deleted switch {self.id} at {self.pos}")

    @classmethod
    def stop(cls):
        """
        Stop monitoring the state of all switches.
        """
        # TODO this does nothing currently?
        cls.monitoring = False

    def check_state(self, state: str) -> bool:
        """
        Test the state of one of the switch's properties.

        :param state: the state to test for, should be one of
            *self.on* or *self.off*
        """
        res = get_client().execute.if_.block(self.pos, state).run("seed")
        if "Seed" in res:
            result = True
        else:
            result = False

        return result

    def _poll(self):
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
