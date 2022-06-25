"""
Functions to manage threads.

Each thread maintains its own Client object for parallel execution of Minecraft
Server functions. The 1st Client object is created on the main thread and then
passed to new_thread.
"""

import threading

from mciwb import Client

thread_local = threading.local()


def new_thread(client: Client, target) -> threading.Thread:
    """
    Create a thread with its own RCON Client connection stored in thread local storage
    """

    def _enter_thread(client, target):
        # make new client connection for this thread
        new_client = Client(client.host, client.port, passwd=client.passwd)
        new_client.connect(True)

        # save our new client in the thread local storage
        set_client(client)

        target()

    # Start a new thread and use _enter_thread to set it up with a RCON client
    new_thread = threading.Thread(target=_enter_thread, args=(client, target))
    new_thread.start()

    return new_thread


def set_client(client: Client) -> None:
    # save our new client in the thread local storage
    thread_local.client = client


def get_client() -> Client:
    # retrieve the client for this thread
    return thread_local.client
