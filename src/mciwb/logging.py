import logging

log = logging.getLogger("mciwb")
handler = logging.StreamHandler()


def exception_handler(exception_type, exception, traceback):
    if log.root.level > logging.DEBUG:
        log.error("%s: %s", exception_type.__name__, exception)
    log.debug("", exc_info=True)


def init_logging(debug: bool):
    if debug:
        log.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(levelname)s: %(pathname)s:%(lineno)d %(funcName)s " "\n\t%(message)s"
        )
    else:
        log.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s:\t%(message)s")

    handler.setFormatter(formatter)
    log.addHandler(handler)

    log.debug("Debugging logging initialized")
