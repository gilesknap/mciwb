"""
Thread functions for monitoring state of the world
"""

import logging
from threading import Thread
from time import sleep
from typing import Callable, List

from mcipc.rcon.je import Client
from mcwb import Vec3

CallbackFunction = Callable[[Client], None]
CallbackPosFunction = Callable[[Vec3, Client], None]


class Monitor:
    """ "
    A class to provide threads for monitoring. Each thread maintains a
    list of functions to call and its own Client object for parallel
    execution of Minecraft server functions.
    """

    monitors: List["Monitor"] = []

    def __init__(self, client: Client, poll_rate=0.5) -> None:
        # Each tick on the monitor will call each of the functions in this
        # pollers list. The poller function should take a client object and
        # use that for any MC Server calls. The function can be bound to an
        # object and this is how to maintain state for a given poller.
        self.pollers: List[CallbackFunction] = []

        # create our own client for the new thread
        self._polling = True
        self.poll_rate = poll_rate
        self.poll_client = Client(client.host, client.port, passwd=client.passwd)
        self.poll_client.connect(True)
        self.poll_thread = Thread(target=self._poller)
        self.poll_thread.start()

        global monitors
        self.monitors.append(self)

    def _poller(self):
        """
        the polling function will run until
        """
        try:
            while self._polling:
                for func in self.pollers:
                    func(self.poll_client)
                sleep(self.poll_rate)
        except BrokenPipeError:
            logging.error("Connection to Minecraft Server lost, polling terminated")
            self._polling = False

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

    def stop(self):
        self._polling = False

    @classmethod
    def stop_all(cls):
        for monitor in cls.monitors:
            monitor.stop()
        cls.monitors.clear()
        logging.info("Stopped all monitoring threads")

    def __del__(self):
        self.stop()
