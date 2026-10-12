"""
Thread functions for running any background tasks. Primarily used for
monitoring the state of objects in Minecraft.
"""

import threading
from collections.abc import Callable
from time import sleep
from typing import Any, ClassVar

from rcon.exceptions import SessionTimeout

from mciwb.logging import log
from mciwb.player import PlayerNotInWorldError
from mciwb.threads import get_client, get_thread_name, new_thread

# supports any function arguments
CallbackFunction = Callable[..., Any]


class Monitor:
    """
    A class to provide threads for monitoring. Each thread maintains a
    list of functions to call repeatedly.

    Each thread has its own Client object for parallel
    execution of Minecraft server functions.

    :param func: a function to call in the Monitor thread
    :param params: parameters to pass to the above function. Note that
        *func* and *params* can be None, () in which case you must use
        `add_poller_func` to add functions to be called.
    :param once: if True, stop polling after first poll - use for a single
                background operation
    :param name: name of the thread
    :param poll_rate: rate at which to poll the functions
    :param start: if True, start the thread immediately
    """

    monitor_num = 0
    monitors: ClassVar[list["Monitor"]] = []
    # protects the monitors list, which the monitor threads also modify
    _lock = threading.Lock()

    # seconds to wait before polling again after the player has gone missing
    # (e.g. while they respawn, change dimension or briefly disconnect)
    player_missing_backoff = 5.0

    def __init__(
        self,
        func: CallbackFunction | None = None,
        params: tuple[Any, ...] = (),
        once: bool = False,
        name: str | None = None,
        poll_rate: float = 0.2,
        start: bool = True,
    ) -> None:
        if name is None:
            name = f"Monitor{Monitor.monitor_num}"
            Monitor.monitor_num += 1

        # pollers is a list of functions, param tuples. It may be initialized
        # with a single function passed in func, params
        self.pollers: list[tuple[CallbackFunction, tuple[Any, ...]]] = (
            [] if func is None else [(func, params)]
        )

        self.name = name
        self.once = once
        self.poll_rate = poll_rate
        self.poll_thread: threading.Thread | None = None
        self._polling = False

        if start:
            self.start_poller()

    def start_poller(self):
        """
        Begin polling the functions in the pollers list
        """
        if self.poll_thread is None:
            log.debug(f"starting polling thread {self.name}")
            # set up state before the thread starts, it may run immediately
            self._polling = True
            with self._lock:
                self.monitors.append(self)
            self.poll_thread = new_thread(get_client(), self._poller, self.name)

    def _poller(self):
        """
        the polling function will run until the monitor is stopped
        """

        while self._polling:
            try:
                for func, params in list(self.pollers):
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
            except PlayerNotInWorldError as e:
                # the player may come back, so keep polling but slow down
                log.warning(f"{e}, {get_thread_name()} will retry")
                sleep(self.player_missing_backoff)
            except BaseException:
                # report any other exception and continue polling
                log.error(f"Error in {get_thread_name()}", exc_info=True)

            if self.once:
                self._polling = False

        self._remove()
        self.poll_thread = None
        self.pollers = []
        if not self.once:
            log.info(f"Monitor {self.name} stopped")

    def _remove(self):
        with self._lock:
            if self in self.monitors:
                self.monitors.remove(self)

    def add_poller_func(self, func: CallbackFunction, params: tuple[Any, ...] = ()):
        """
        Add a function to the pollers list

        :param func: function to add
        :param params: parameters to pass to the function
        """
        self.pollers.append((func, params))

    # TODO: consider using a dict or indexing pollers in some fashion
    # currently this does not support 2 calls to same function
    def remove_poller_func(self, func: CallbackFunction):
        """
        Remove a function from the pollers list

        :param func: function to remove
        """
        for t in self.pollers:
            f, _params = t
            if f == func:
                self.pollers.remove(t)
                break
        else:
            log.error("removing unknown poller function")

    @classmethod
    def stop_all(cls, timeout: float = 5.0):
        """
        Stop all instances of Monitor and tidy up. Call this before exiting
        the program so that background work is finished cleanly.

        :param timeout: seconds to wait for each thread to finish
        """
        with cls._lock:
            monitors = list(cls.monitors)
            cls.monitors.clear()
        for monitor in monitors:
            monitor.stop()
        for monitor in monitors:
            thread = monitor.poll_thread
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout)
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
        with cls._lock:
            matches = [m for m in cls.monitors if m.name == name]
        for monitor in matches:
            monitor.stop()
            monitor._remove()  # noqa: SLF001

    def __del__(self):
        self.stop()

    def __repr__(self):
        func_list = [getattr(f, "__qualname__", repr(f)) for f, _ in self.pollers]
        return f"{self.name} polling {func_list} at {self.poll_rate}"
