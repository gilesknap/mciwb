"""
Functions to manage threads.

Each thread maintains its own Client object for parallel execution of Minecraft
Server functions. The 1st Client object is created on the main thread and then
passed to new_thread.
"""

import re
import threading
from collections.abc import Callable

from mcipc.rcon.client import Client as _RawClient
from mcipc.rcon.functions import str_until_none
from mcipc.rcon.je.client import Client as _McipcClient

from mciwb.logging import log

thread_local = threading.local()

# The Minecraft server collects the output of every RCON connection in one
# shared buffer (DedicatedServer.rconConsoleSource), which it clears before
# each command and reads after it. Two connections running commands at the
# same time therefore receive each other's output, or none at all.
#
# This lock lets only one command of this process run at a time. It can not
# stop other processes (another script, a dashboard polling ``list``) from
# interleaving with us, so replies are also checked, and the commands that
# are safe to send twice are retried, see retry_command.
_rcon_lock = threading.RLock()

#: how many times to send an idempotent command whose reply is lost or
#: garbled by another RCON client, before giving up and returning the reply
RCON_ATTEMPTS = 5

#: a check of a command's reply: returns the command's own output, without
#: any other client's output around it, or None if it is not in the reply
ReplyCheck = Callable[[str], str | None]


def reply_matches(pattern: str | re.Pattern[str]) -> ReplyCheck:
    """
    A `ReplyCheck` that accepts a reply containing *pattern*, and returns the
    text that matched it
    """
    regex = re.compile(pattern)

    def check(reply: str) -> str | None:
        match = regex.search(reply)
        return match.group(0) if match else None

    return check


def retry_command(
    send: Callable[[], str],
    check: ReplyCheck,
    description: str,
    attempts: int = RCON_ATTEMPTS,
) -> str:
    """
    Send a command until its reply passes *check*, for when another RCON
    client may have emptied or added to the reply (see ``_rcon_lock``).

    Only use this for commands that do the same thing when sent twice, e.g.
    ``setblock`` or ``tp`` to a fixed place, but not ``give`` or ``summon``:
    a garbled reply does not mean that the command failed.

    A non-empty reply that fails *check* twice in a row is the server's real
    reply (e.g. an error such as "That position is not loaded"): garbled
    replies are random, so it is returned at once rather than retried.

    :param send: sends the command and returns the reply
    :param check: returns the command's own output from a reply, or None
    :param description: the command, for log messages
    :param attempts: the most times to send the command
    :returns: the command's own output, as returned by *check*, or the last
        reply if no reply passed the check
    """
    previous = None
    reply = ""
    for attempt in range(1, attempts + 1):
        reply = send()
        output = check(reply)
        if output is not None:
            if attempt > 1:
                log.info(
                    f"RCON reply recovered after {attempt} attempts: {description}"
                )
            return output
        if reply and reply == previous:
            break
        previous = reply
        if attempt < attempts:
            log.warning(
                f"RCON reply to '{description}' looks lost or garbled by "
                f"another client, retrying: {reply!r}"
            )
    return reply


# checks for the replies of the commands that the client retries itself:
# commands that mciwb and mcwb use a lot, that do the same thing when sent
# twice, and always reply with a message that says they ran. The patterns are
# the Minecraft 26.3 messages (commands.<name>.* in its en_us.json).
_REPLIES: dict[str, ReplyCheck] = {
    "setblock": reply_matches(
        r"Changed the block at -?\d+, -?\d+, -?\d+|Could not set the block"
    ),
    "fill": reply_matches(r"Successfully filled \d+ block\(s\)|No blocks were filled"),
    "clone": reply_matches(r"Successfully cloned \d+ block\(s\)|No blocks were cloned"),
    # mcwb.get_block reads blocks with 'loot spawn <dump> mine <pos>', which
    # drops the block's loot into the void
    "loot": reply_matches(
        r"Dropped [^\n]*? from loot table minecraft:[\w/.-]+"
        r"|Block [^\n]+? has no loot table"
    ),
}

_setblock_at = re.compile(r"setblock (-?\d+) (-?\d+) (-?\d+) ")
_changed_at = re.compile(r"Changed the block at (-?\d+), (-?\d+), (-?\d+)")
_could_not_set = "Could not set the block"


def _reply_check(command: str) -> ReplyCheck | None:
    """the check for the reply to *command*, or None to send it just once"""
    check = _REPLIES.get(command.partition(" ")[0])
    if check is None or not (at := _setblock_at.match(command)):
        return check

    # a setblock reply names the block, so a reply to another client's
    # setblock can be told apart from ours
    def setblock_check(reply: str) -> str | None:
        for changed in _changed_at.finditer(reply):
            if changed.groups() == at.groups():
                return changed.group(0)
        if _could_not_set in reply:
            return _could_not_set
        return None

    return setblock_check


class Client(_McipcClient):
    """
    An RCON client for Minecraft Java Edition that copes with the other RCON
    clients of the server.

    Each command waits for any command running on another connection of this
    process to complete, so that the server returns the output of this
    command only.

    Other processes can still run commands at the same moment, which can
    empty our reply or add theirs to it (about 1 in 10000 commands while
    another client polls the server). So the replies of ``setblock``,
    ``fill``, ``clone`` and ``loot`` (as used by ``mcwb.get_block``) are
    checked, the command is sent again if the reply is lost, and only the
    command's own output is returned. Other commands are sent once: use
    ``retry_command``, or ``Iwb.cmd(..., expect=...)``, for those that are
    safe to send again.
    """

    def run(self, command: str, *arguments: str) -> str:
        """
        Run a command, raising mcipc's exceptions (e.g. ``InvalidArgument``)
        for the errors that mcipc recognises
        """
        return self._run(command, arguments, raw=False)

    def run_raw(self, command: str, *arguments: str) -> str:
        """
        Run a command and return the server's reply as it is, including any
        error message, rather than raising mcipc's exceptions
        """
        return self._run(command, arguments, raw=True)

    def _run(self, command: str, arguments: tuple[str, ...], raw: bool) -> str:
        text = " ".join(str_until_none(command, *arguments))

        def send() -> str:
            with _rcon_lock:
                if raw:
                    return _RawClient.run(self, text)
                return super(Client, self).run(text)

        check = _reply_check(text)
        if check is None:
            return send()
        return retry_command(send, check, text)


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
