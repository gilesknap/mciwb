import threading
from time import monotonic, sleep

import pytest

from mciwb.imports import Monitor
from mciwb.player import PlayerNotInWorldError
from mciwb.threads import get_thread_name


def wait_until(predicate, timeout: float = 5.0) -> bool:
    deadline = monotonic() + timeout
    while not predicate():
        if monotonic() > deadline:
            return False
        sleep(0.01)
    return True


def test_single_use(mock_client):
    count = 0

    def test_func():
        nonlocal count
        count += 1

    mon = Monitor(test_func, once=True)

    assert wait_until(lambda: not mon._polling), "once monitor did not stop"
    assert count == 1
    assert wait_until(lambda: mon not in Monitor.monitors)


def test_multiple_use(mock_client):
    count = 0

    def test_func():
        nonlocal count
        count += 1

    mon = Monitor(test_func, poll_rate=0.0001)
    assert wait_until(lambda: count >= 100), "monitor did not poll repeatedly"

    mon.remove_poller_func(test_func)
    Monitor.stop_all()

    assert not mon._polling
    assert Monitor.monitors == []


def test_starts_polling_immediately(mock_client):
    # the thread must see _polling set even if it starts before the
    # constructor returns
    for _ in range(20):
        calls = []
        mon = Monitor(lambda calls=calls: calls.append(1), poll_rate=0.001)
        assert wait_until(lambda calls=calls: len(calls) > 0)
        assert mon in Monitor.monitors
        Monitor.stop_all()


def test_thread_name(mock_client):
    names = []
    Monitor(lambda: names.append(get_thread_name()), once=True, name="named")

    assert wait_until(lambda: names == ["named"])
    assert get_thread_name() == threading.current_thread().name


@pytest.mark.parametrize("error", [ValueError("oops"), PlayerNotInWorldError("x")])
def test_keeps_polling_after_errors(
    mock_client, monkeypatch: pytest.MonkeyPatch, error: Exception
):
    monkeypatch.setattr(Monitor, "player_missing_backoff", 0.01)
    count = 0

    def failing():
        nonlocal count
        count += 1
        if count < 3:
            raise error

    mon = Monitor(failing, poll_rate=0.001)

    assert wait_until(lambda: count >= 5), "monitor stopped after an error"
    assert mon._polling


def test_stop_all_stops_everything(mock_client):
    monitors = [Monitor(lambda: None, poll_rate=0.001) for _ in range(10)]
    threads = [m.poll_thread for m in monitors]

    Monitor.stop_all()

    assert Monitor.monitors == []
    assert all(t is not None and not t.is_alive() for t in threads)


def test_stop_named(mock_client):
    keep = Monitor(lambda: None, name="keep", poll_rate=0.001)
    stop = Monitor(lambda: None, name="stop", poll_rate=0.001)

    Monitor.stop_named("stop")
    Monitor.stop_named("unknown")

    assert Monitor.monitors == [keep]
    assert not stop._polling
    assert keep._polling
