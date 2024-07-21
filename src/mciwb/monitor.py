"""
Thread functions for running any background tasks. Primarily used for
monitoring the state of objects in Minecraft.
"""

from collections.abc import Callable
from time import sleep
from typing import Any

from rcon.exceptions import SessionTimeout

from mciwb.logging import log
from mciwb.player import PlayerNotInWorld
from mciwb.threads import get_client, get_thread_name, new_thread

# supports any function arguments
CallbackFunction = Callable


class Monitor:
    """ "
    A class to provide threads for monitoring. Each thread maintains a
    list of functions to call repeatedly.

    Each thread has its own Client object for parallel
    execution of Minecraft server functions.

    :param name: name of the thread
    :param func: a function to call in the Monitor thread
    :param params: parameters to pass to the above function. Note that
        *func* and *params* can be None, () in which case you must use
        `add_poller_func` to add functions to be called.
    :param poll_rate: rate at which to poll the functions
    :param once: if True, stop polling after first poll - use for a single
                background operation
    :param start: if True, start the thread immediately
    """

    monitor_num = 0
    monitors: list["Monitor"] = []

    def __init__(
        self,
        # maybe this type is a bit loose, pyright not happy, lets just roll with it.
        func: None | CallbackFunction = None,  # type: ignore
        params: tuple[Any, ...] = (),
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
        self.pollers: list[tuple[CallbackFunction, tuple[Any, ...]]] = (  # type: ignore
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
        """
        Begin polling the functions in the pollers list
        """
        if self.poll_thread is None:
            log.debug(f"starting polling thread {self.name}")
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
                log.error(
                    f"Connection to Minecraft Server lost, "
                    f"polling terminated in {get_thread_name()}"
                )
                self._polling = False
            except SessionTimeout:
                log.warning(f"Connection timeout in {get_thread_name()}")
            except PlayerNotInWorld as e:
                log.warning(e)
                self._polling = False
            except BaseException:
                # report any other exception and continue polling
                log.error(f"Error in {get_thread_name()}", exc_info=True)

            if self.once:
                self._polling = False

        if self in self.monitors:
            self.monitors.remove(self)
        self.poll_thread = None
        self.pollers = []
        if not self.once:
            log.info(f"Monitor {self.name} stopped")

    def add_poller_func(self, func: CallbackFunction, params: tuple[Any, ...] = ()):  # type: ignore
        """
        Add a function to the pollers list

        :param func: function to add
        :param params: parameters to pass to the function
        """
        self.pollers.append((func, params))

    # TODO: consider using a dict or indexing pollers in some fashion
    # currently this does not support 2 calls to same function
    def remove_poller_func(self, func: CallbackFunction):  # type: ignore
        """
        Remove a function from the pollers list

        :param func: function to remove
        """
        for _i, t in enumerate(self.pollers):
            f, params = t
            if f == func:
                self.pollers.remove(t)
                break
        else:
            log.error("removing unknown poller function")

    @classmethod
    def stop_all(cls):
        """
        Stop all instances of Monitor and tidy up. Call this before exiting
        the program otherwise Python will wait on the background threads
        indefinitely.
        """
        if cls.monitors is not None:
            for monitor in cls.monitors:
                monitor.stop()
            cls.monitors.clear()
            log.info("Stopped all monitoring threads")

    def stop(self):
        """
        Stop this instance of Monitor
        """
        self._polling = False

    @classmethod
    def stop_named(cls, name: str):
        """
        Stop a named instance of Monitor
        """
        for monitor in cls.monitors:
            if monitor.name == name:
                monitor.stop()
                cls.monitors.remove(monitor)
                break

    def __del__(self):
        self.stop()

    def __repr__(self):
        # TODO work out how to show the class of the bound method
        func_list = [f.__name__ for f, p in self.pollers]
        return f"{self.name} polling {func_list} at {self.poll_rate})"
