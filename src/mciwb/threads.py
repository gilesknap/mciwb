"""
Functions to manage threads.

Each thread maintains its own Client object for parallel execution of Minecraft
Server functions. The 1st Client object is created on the main thread and then
passed to new_thread.
"""

import threading
from collections.abc import Callable

from mcipc.rcon.je.client import Client

thread_local = threading.local()


def _enter_thread(client: Client, target: Callable[[], None], name: str) -> None:
    thread_local.name = name
    # make new client connection for this thread
    # Note use of type(client). When testing the type may be MockClient
    new_client = type(client)(client.host, client.port, passwd=client.passwd)
    new_client.connect(True)
    set_client(new_client)

    target()


def new_thread(
    client: Client, target: Callable[[], None], name: str
) -> threading.Thread:
    """
    Create a thread with its own RCON Client connection stored in thread local
    storage.

    The thread is a daemon thread so that it can never keep the Python
    interpreter alive on exit. Use `Monitor.stop_all` to stop threads cleanly.

    :param client: the client whose connection details the new thread copies
    :param target: the function to run in the new thread
    :param name: the name of the new thread
    """
    # Start a new thread and use _enter_thread to set it up with a new RCON client
    thread = threading.Thread(
        target=_enter_thread, args=(client, target, name), name=name, daemon=True
    )
    thread.start()

    return thread


def set_client(client: Client) -> None:
    """
    Set the client for this thread. Use this when the client object has been
    created outside of `new_thread`.
    """
    # save our new client in the thread local storage
    thread_local.client = client


def get_client() -> Client:
    """
    Retrieve the client for the current thread.

    Every thread needs its own RCON connection. Threads created with
    `new_thread` (e.g. by `Monitor`) get one automatically.
    """
    return thread_local.client


def get_thread_name() -> str:
    """
    Retrieve the name of the current thread. This is the name that was passed
    to `new_thread`, or the Python thread name for other threads.
    """
    return getattr(thread_local, "name", threading.current_thread().name)
