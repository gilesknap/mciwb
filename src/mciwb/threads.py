"""
Functions to manage threads.

Each thread maintains its own Client object for parallel execution of Minecraft
Server functions. The 1st Client object is created on the main thread and then
passed to new_thread.
"""

import threading

from mcipc.rcon.je.client import Client

thread_local = threading.local()


def _enter_thread(client, target, name):
    # make new client connection for this thread
    # Note use of type(client). When testing the type may be MockClient
    # TODO would prefer to use a context for client here as the cleanup
    # works - but it gets an error running under PyTest (huh?)
    new_client = type(client)(client.host, client.port, passwd=client.passwd)
    new_client.connect(True)
    set_client(new_client)

    target()


def new_thread(client: Client, target, name: str) -> threading.Thread:
    """
    Create a thread with its own RCON Client connection stored in thread local storage
    """

    # Start a new thread and use _enter_thread to set it up with a new RCON client
    new_thread = threading.Thread(target=_enter_thread, args=(client, target, name))
    new_thread.start()

    return new_thread


def set_client(client: Client) -> None:
    """
    Set the client for this thread. Use this when the client object has been
    created outside of `new_thread`.
    """
    # save our new client in the thread local storage
    thread_local.client = client


def get_client() -> Client:
    """
    retrieve the client for the current thread
    """
    return thread_local.client


def get_thread_name() -> str:
    """
    retrieve the name of the current thread. This is the name that was passed
    to `new_thread`.
    """
    return thread_local.name
