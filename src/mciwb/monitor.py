"""
Thread functions for monitoring state of the world
"""

import logging
from time import sleep
from typing import Callable, List

from mcwb import Vec3
from rcon.exceptions import SessionTimeout

from mciwb.threads import get_client, get_thread_name, new_thread

CallbackFunction = Callable[[], None]
CallbackPosFunction = Callable[[Vec3], None]


class Monitor:
    """ "
    A class to provide threads for monitoring. Each thread maintains a
    list of functions to call and its own Client object for parallel
    execution of Minecraft server functions.
    """

    monitor_num = 0
    monitors: List["Monitor"] = []

    def __init__(self, name=None, poll_rate=0.2) -> None:
        # Each tick on the monitor will call each of the functions in this
        # pollers list. The poller function should take a client object and
        # use that for any MC Server calls. The function can be bound to an
        # object and this is how to maintain state for a given poller.
        self.pollers: List[CallbackFunction] = []

        if name is None:
            name = f"Monitor{Monitor.monitor_num}"
            Monitor.monitor_num += 1

        self._polling = True
        self.poll_rate = poll_rate
        self.poll_thread = new_thread(get_client(), self._poller, name)
        self.monitors.append(self)

    def _poller(self):
        """
        the polling function will run until the monitor is stopped
        """

        while self._polling:
            try:
                for func in self.pollers:
                    func()
                sleep(self.poll_rate)
            except BrokenPipeError:
                logging.error(
                    f"Connection to Minecraft Server lost, "
                    f"polling terminated in {get_thread_name()}"
                )
                self._polling = False
            except SessionTimeout:
                logging.warning(f"Connection timeout in {get_thread_name()}")
            except BaseException:
                logging.error(f"Error in {get_thread_name()}", exc_info=True)

        if self in self.monitors:
            self.monitors.remove(self)

    def add_poller_func(self, func: CallbackFunction):
        self.pollers.append(func)

    def remove_poller_func(self, func: CallbackFunction):
        idx = self.pollers.index(func)
        if idx < 0:
            logging.error("removing unknown poller function")
        else:
            self.pollers.remove(func)

    @classmethod
    def stop_all(cls):
        for monitor in cls.monitors:
            monitor.stop()
        cls.monitors.clear()
        logging.info("Stopped all monitoring threads")

    def stop(self):
        self._polling = False

    def __del__(self):
        self.stop()
