"""
Thread functions for monitoring state of the world
"""

import logging
from time import sleep
from typing import Any, Callable, List, Tuple, Union

from rcon.exceptions import SessionTimeout

from mciwb.player import PlayerNotInWorld
from mciwb.threads import get_client, get_thread_name, new_thread

# supports any function arguments
CallbackFunction = Callable


class Monitor:
    """ "
    A class to provide threads for monitoring. Each thread maintains a
    list of functions to call and its own Client object for parallel
    execution of Minecraft server functions.
    """

    monitor_num = 0
    monitors: List["Monitor"] = []

    def __init__(
        self,
        func: Union[None, CallbackFunction] = None,
        params: Tuple[Any, ...] = (),
        once=False,
        name=None,
        poll_rate=0.2,
        start=True,
    ) -> None:

        if name is None:
            name = f"Monitor{Monitor.monitor_num}"
            Monitor.monitor_num += 1

        # pollers is a list of functions, param tuples. It may be initialized
        # with a single function passed in func, params
        self.pollers: List[Tuple[CallbackFunction, Tuple[Any, ...]]] = (
            [] if func is None else [(func, params)]
        )

        self.name = name
        self.once = once
        self.poll_rate = poll_rate
        self.poll_thread = None
        self._polling = False

        if start:
            self.start_poller()

    def start_poller(self):
        if self.poll_thread is None:
            logging.debug(f"starting polling thread {self.name}")
            self.poll_thread = new_thread(get_client(), self._poller, self.name)
            self.monitors.append(self)
            self._polling = True

    def _poller(self):
        """
        the polling function will run until the monitor is stopped
        """

        while self._polling:
            try:
                for func, params in self.pollers:
                    func(*params)
                sleep(self.poll_rate)
            except BrokenPipeError:
                logging.error(
                    f"Connection to Minecraft Server lost, "
                    f"polling terminated in {get_thread_name()}"
                )
                self._polling = False
            except SessionTimeout:
                logging.warning(f"Connection timeout in {get_thread_name()}")
            except PlayerNotInWorld as e:
                logging.warning(e)
                self._polling = False
            except BaseException:
                # report any other exception and continue polling
                logging.error(f"Error in {get_thread_name()}", exc_info=True)

            if self.once:
                self._polling = False

        if self in self.monitors:
            self.monitors.remove(self)
        self.poll_thread = None
        self.pollers = []
        if not self.once:
            logging.info(f"Monitor {self.name} stopped")

    def add_poller_func(self, func: CallbackFunction, params: Tuple[Any, ...] = ()):
        self.pollers.append((func, params))

    # TODO: consider using a dict or indexing pollers in some fashion
    # currently this does not support 2 calls to same function
    def remove_poller_func(self, func: CallbackFunction):
        for i, t in enumerate(self.pollers):
            f, params = t
            if f == func:
                self.pollers.remove(t)
                break
        else:
            logging.error("removing unknown poller function")

    @classmethod
    def stop_all(cls):
        if cls.monitors is not None:
            for monitor in cls.monitors:
                monitor.stop()
            cls.monitors.clear()
            logging.info("Stopped all monitoring threads")

    def stop(self):
        self._polling = False

    def __del__(self):
        self.stop()

    def __repr__(self):
        # TODO work out how to show the class of the bound method
        func_list = [f.__name__ for f, p in self.pollers]
        return f"{self.name} polling {func_list} at {self.poll_rate})"
