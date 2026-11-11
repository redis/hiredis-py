"""Tests for use of the extension on free-threaded (PEP 703) CPython builds.

The stress tests are only meaningful when the GIL is actually disabled, but
they check invariants that must also hold with the GIL, so they run on every
interpreter.
"""

import os
import subprocess
import sys
import sysconfig
import threading
import time

import pytest

import hiredis

FREE_THREADED = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))

THREADS = 4
ARRAY_LEN = 16
TIMEOUT = 60  # seconds; the tests take well under one when nothing is wrong


def run_in_threads(*targets):
    """Start every target at once, wait for all of them and re-raise the first error."""
    barrier = threading.Barrier(len(targets), timeout=TIMEOUT)
    errors = []

    def runner(target):
        try:
            barrier.wait()
            target()
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=runner, args=(t,), daemon=True) for t in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(TIMEOUT)
    if errors:
        raise errors[0]
    assert not any(thread.is_alive() for thread in threads), "threads did not finish"


def array_reply(value):
    """RESP array of ARRAY_LEN copies of an integer (long enough to overlap)."""
    return b"*%d\r\n" % ARRAY_LEN + (b":%d\r\n" % value) * ARRAY_LEN


def drain(reader, sink, decode=True):
    while True:
        reply = reader.gets(decode)
        if reply is False:
            return
        sink.append(reply)


@pytest.mark.skipif(not FREE_THREADED, reason="requires a free-threaded build")
def test_import_does_not_enable_gil():
    env = dict(os.environ)
    env.pop("PYTHON_GIL", None)
    package_root = os.path.dirname(os.path.dirname(os.path.abspath(hiredis.__file__)))
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [package_root, env.get("PYTHONPATH")])
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::RuntimeWarning",
            "-c",
            "import sys, hiredis; sys.exit(int(sys._is_gil_enabled()))",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr


def test_concurrent_feed_and_gets_on_shared_reader():
    """Replies fed from several threads are each delivered exactly once, intact."""
    producers = 2
    per_producer = 2000
    reader = hiredis.Reader()
    done = threading.Event()
    lock = threading.Lock()
    remaining = [producers]
    sinks = [[] for _ in range(THREADS)]

    def produce(offset):
        def target():
            try:
                for i in range(per_producer):
                    reader.feed(array_reply(offset + i))
            finally:
                # Always signal completion, or a failing producer would leave
                # the consumers spinning forever.
                with lock:
                    remaining[0] -= 1
                    if remaining[0] == 0:
                        done.set()

        return target

    def consume(sink):
        def target():
            while not done.is_set():
                drain(reader, sink)
                time.sleep(0)
            drain(reader, sink)

        return target

    run_in_threads(
        *[produce(p * per_producer) for p in range(producers)],
        *[consume(sink) for sink in sinks],
    )

    replies = [reply for sink in sinks for reply in sink]
    assert len(replies) == producers * per_producer
    for reply in replies:
        assert reply == [reply[0]] * ARRAY_LEN
    assert sorted(reply[0] for reply in replies) == list(
        range(producers * per_producer)
    )


def test_concurrent_gets_with_different_decoding():
    """The decode flag passed to gets() applies to that call only."""
    total = 20000
    reader = hiredis.Reader(encoding="utf-8")
    reader.feed(b"$5\r\nhello\r\n" * total)
    decoded, raw = [], []

    def consume(sink, decode):
        return lambda: drain(reader, sink, decode)

    run_in_threads(
        consume(decoded, True),
        consume(decoded, True),
        consume(raw, False),
        consume(raw, False),
    )

    assert len(decoded) + len(raw) == total
    assert all(reply == "hello" for reply in decoded)
    assert all(reply == b"hello" for reply in raw)


def test_concurrent_set_encoding_while_decoding():
    """Changing the decode settings never affects a decode that is in progress."""
    total = 20000
    reader = hiredis.Reader(encoding="utf-8")
    reader.feed(b"$5\r\nhello\r\n" * total)
    sinks = [[], []]

    def consume(sink):
        return lambda: drain(reader, sink)

    def reconfigure():
        for i in range(100_000):  # bounded, in case the consumers fail
            if not reader.has_data():
                return
            if i % 2:
                reader.set_encoding("latin-1", "replace")
            else:
                reader.__init__(encoding="utf-8")

    run_in_threads(consume(sinks[0]), consume(sinks[1]), reconfigure, reconfigure)

    replies = sinks[0] + sinks[1]
    assert len(replies) == total
    assert all(reply == "hello" for reply in replies)


def test_concurrent_mixed_operations_on_shared_reader():
    """Every public Reader method can be called concurrently without crashing."""
    reader = hiredis.Reader()
    iterations = 2000

    def feeder():
        for i in range(iterations):
            reader.feed(array_reply(i))

    def getter():
        for _ in range(iterations):
            reader.gets()

    def inspector():
        for _ in range(iterations):
            assert reader.len() >= 0
            assert reader.has_data() in (True, False)
            assert reader.getmaxbuf() >= 0

    def configurer():
        for i in range(iterations):
            reader.setmaxbuf(None if i % 2 else 1 << 20)
            reader.set_encoding("utf-8" if i % 2 else None)
            reader.__init__(encoding="utf-8" if i % 2 else None)

    run_in_threads(feeder, feeder, getter, getter, inspector, configurer)


def test_concurrent_pack_command():
    cmd = ("SET", "key", 42, b"value", 1.5, memoryview(b"view"))
    expected = hiredis.pack_command(cmd)

    def target():
        for _ in range(5000):
            assert hiredis.pack_command(cmd) == expected

    run_in_threads(*[target] * THREADS)


def test_callback_cannot_reenter_the_reader():
    """Python code run by gets() cannot feed, read or re-initialize its Reader."""
    refused = {}
    calls = []

    def reply_error(message):
        calls.append(message)
        if len(calls) == 1:  # a gets() that is let in would call this again
            for name, call in (
                ("feed", lambda: reader.feed(b"+OK\r\n")),
                ("gets", reader.gets),
                ("__init__", reader.__init__),
            ):
                try:
                    call()
                except RuntimeError as exc:
                    refused[name] = str(exc)
        return ValueError(message)

    reader = hiredis.Reader(replyError=reply_error)
    reader.feed(b"*2\r\n-ERR first\r\n:2\r\n")
    first, second = reader.gets()

    assert sorted(refused) == ["__init__", "feed", "gets"]
    assert all("is still running" in message for message in refused.values())
    assert calls == ["ERR first"]
    # The refused calls neither took the reply nor added to the stream.
    assert isinstance(first, ValueError) and str(first) == "ERR first"
    assert second == 2
    assert not reader.has_data()
    reader.feed(b"+OK\r\n")
    assert reader.gets() == b"OK"


def test_other_threads_cannot_enter_a_reader_while_a_callback_runs():
    """A thread that calls in while gets() waits in Python code gets an error,
    instead of taking the reply that is being built."""
    entered, release = threading.Event(), threading.Event()

    def reply_error(message):
        entered.set()
        release.wait(TIMEOUT)
        return ValueError(message)

    reader = hiredis.Reader(replyError=reply_error)
    reader.feed(b"*2\r\n-ERR first\r\n:2\r\n")
    result = []

    def getter():
        try:
            result.append(reader.gets())
        except BaseException as exc:
            result.append(exc)

    thread = threading.Thread(target=getter, daemon=True)
    thread.start()
    try:
        assert entered.wait(TIMEOUT)
        for call in (lambda: reader.feed(b"+OK\r\n"), reader.gets, reader.__init__):
            with pytest.raises(RuntimeError, match="is still running"):
                call()
    finally:
        release.set()
        thread.join(TIMEOUT)

    assert not thread.is_alive()
    assert len(result) == 1 and not isinstance(result[0], BaseException), result
    first, second = result[0]
    assert isinstance(first, ValueError) and str(first) == "ERR first"
    assert second == 2
    reader.feed(b"+OK\r\n")
    assert reader.gets() == b"OK"


def test_reader_is_idle_again_after_gets_fails():
    """Whichever way gets() fails, the next call is not refused as re-entrant."""

    def reply_error(message):
        raise KeyError(message)

    reader = hiredis.Reader(replyError=reply_error, encoding="utf-8")
    with pytest.raises(TypeError):
        reader.gets("not a flag")
    reader.feed(b"-ERR\r\n")
    with pytest.raises(KeyError):
        reader.gets()
    reader.feed(b"+\xff\r\n")
    with pytest.raises(UnicodeDecodeError):
        reader.gets()
    reader.feed(b"!\r\n")
    for _ in range(2):  # a protocol error is permanent, but it is still that error
        with pytest.raises(hiredis.ProtocolError):
            reader.gets()
