import time
from main import Timer


def test_timer_init():
    t = Timer(100)

    assert t.seconds == 100
    assert not t.running
    assert not t.timeout
    assert t.start_time == 0
    assert t.check()


def test_timer():
    t = Timer(100)

    t.start()

    assert t.running
    assert not t.timeout
    assert t.start_time < time.time()
    assert t.check()

    t.stop()
    assert not t.running


def test_timeout():
    seconds = 1
    t = Timer(seconds)
    t.start()
    start_mark = time.time()

    while time.time() - start_mark < seconds:
        pass

    assert not t.check()
    assert t.running

    t.stop()
    assert not t.running


def test_reset():
    t = Timer(1)
    t.start()

    while t.check():
        pass

    t.reset()
    assert t.check()
