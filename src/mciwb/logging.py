"""
Logging for mciwb, with a simple format for novice users
"""

import logging
import sys

log = logging.getLogger("mciwb")


class _StderrHandler(logging.StreamHandler):
    """
    A StreamHandler that writes to whatever sys.stderr is at the time of
    logging, so that redirection (e.g. by pytest or typer's CliRunner)
    captures mciwb's log output
    """

    @property
    def stream(self):  # type: ignore[override]
        return sys.stderr

    @stream.setter
    def stream(self, _value):
        pass


handler = _StderrHandler()


def exception_handler(exception_type, exception, traceback):
    """
    An IPython traceback hook that reports exceptions in one line, unless
    debug logging is enabled
    """
    if log.level > logging.DEBUG:
        log.error("%s: %s", exception_type.__name__, exception)
    log.debug("", exc_info=True)


def init_logging(debug: bool):
    """
    Set up the mciwb log. Can be called again to change the level.

    :param debug: True for debug messages with source locations
    """
    if debug:
        log.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(levelname)s: %(pathname)s:%(lineno)d %(funcName)s \n\t%(message)s"
        )
    else:
        log.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s:\t%(message)s")

    handler.setFormatter(formatter)
    if handler not in log.handlers:
        log.addHandler(handler)

    log.debug("Debugging logging initialized")
