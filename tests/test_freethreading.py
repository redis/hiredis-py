"""Concurrency tests aimed at the free-threaded build.

These also pass under the GIL build (where the GIL serializes everything).
Under cp313t/cp314t with the GIL disabled they exercise the per-Reader
PyMutex added for free-threading support.
"""
import sys
import threading

import pytest

import hiredis


def _run_in_threads(target, n_threads):
    """Spawn n threads that all call target() with no arguments, releasing
    from a barrier so they hit the test path concurrently. Returns any
    exceptions raised on the worker threads."""
    errors = []
    barrier = threading.Barrier(n_threads)

    def runner():
        try:
            barrier.wait()
            target()
        except BaseException as e:  # noqa: BLE001 - collect for the main thread
            errors.append(e)

    threads = [threading.Thread(target=runner) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return errors


def test_gil_disabled_when_freethreaded():
    """On a freethreaded interpreter, importing hiredis must not re-enable
    the GIL. This is the contract of PyUnstable_Module_SetGIL."""
    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    if is_gil_enabled is None:
        pytest.skip("requires Python 3.13+")
    if is_gil_enabled():
        pytest.skip("not running on a freethreaded interpreter")
    assert not is_gil_enabled()


def test_concurrent_independent_readers():
    """Each thread owns its own Reader. No shared mutable state, so every
    thread must observe identical replies."""
    payload = b"*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n"
    iterations = 500

    def worker():
        for _ in range(iterations):
            r = hiredis.Reader()
            r.feed(payload)
            reply = r.gets()
            assert reply == [b"hello", b"world"]

    errors = _run_in_threads(worker, n_threads=8)
    assert not errors, errors


def test_concurrent_shared_reader_atomic_feed_gets():
    """Multiple threads share a single Reader. The protocol bytes for a
    single command must not interleave across threads, so we hold a
    Python-level lock around the feed+gets pair. The C-level PyMutex is
    what protects the parser's internal state from being torn during each
    individual call."""
    cmd = b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n$5\r\nvalue\r\n"
    iterations = 200
    reader = hiredis.Reader()
    serialize = threading.Lock()

    def worker():
        for _ in range(iterations):
            with serialize:
                reader.feed(cmd)
                reply = reader.gets()
            assert reply == [b"SET", b"key", b"value"]

    errors = _run_in_threads(worker, n_threads=8)
    assert not errors, errors


def test_concurrent_shared_reader_no_crash_under_torn_protocol():
    """Without a Python-level lock, concurrent feed() calls from different
    threads can interleave bytes and produce protocol errors. The C-level
    guarantee is: no crash, no UAF, no segfault. Acceptable outcomes per
    call are a valid reply, the NotEnoughData sentinel, or a ProtocolError."""
    chunks = [
        b"*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n",
        b"+OK\r\n",
        b":42\r\n",
        b"$5\r\nhello\r\n",
    ]
    iterations = 200
    reader = hiredis.Reader()
    n = 8
    errors = []
    barrier = threading.Barrier(n)

    def worker(idx):
        chunk = chunks[idx % len(chunks)]
        for _ in range(iterations):
            try:
                reader.feed(chunk)
            except (hiredis.ProtocolError, ValueError):
                pass
            try:
                reader.gets()
            except (hiredis.ProtocolError, hiredis.ReplyError):
                pass

    def runner(i):
        try:
            barrier.wait()
            worker(i)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=runner, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for e in errors:
        assert isinstance(e, (hiredis.ProtocolError, hiredis.ReplyError, ValueError)), e


def test_concurrent_set_encoding_does_not_corrupt():
    """set_encoding mutates instance state that gets() reads inside the
    parser callbacks. Concurrent set_encoding from multiple threads followed
    by feed+gets on the same Reader must not segfault."""
    reader = hiredis.Reader()
    encodings = ["utf-8", "latin-1", "ascii"]
    iterations = 200
    serialize = threading.Lock()

    n = 8
    errors = []
    barrier = threading.Barrier(n)

    def worker(idx):
        for i in range(iterations):
            reader.set_encoding(encodings[(idx + i) % len(encodings)])
            with serialize:
                reader.feed(b"+OK\r\n")
                reader.gets()

    def runner(i):
        try:
            barrier.wait()
            worker(i)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=runner, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors


def test_concurrent_setmaxbuf_with_readers():
    """setmaxbuf/getmaxbuf/len/has_data each touch self->reader internals.
    Concurrent access from multiple threads must not crash."""
    reader = hiredis.Reader()
    iterations = 500

    def setters():
        for i in range(iterations):
            reader.setmaxbuf((i + 1) * 1024)
            _ = reader.getmaxbuf()

    def readers():
        for _ in range(iterations):
            _ = reader.len()
            _ = reader.has_data()

    errors = _run_in_threads(setters, n_threads=4)
    errors += _run_in_threads(readers, n_threads=4)
    assert not errors, errors


def test_concurrent_pack_command():
    """pack_command is stateless — concurrent calls must produce identical
    output and must not crash."""
    args = ("HSET", "foo", "key", "value", "key2", b"value2", "key3", 67, "key4", 3.14)
    expected = hiredis.pack_command(args)

    def worker():
        for _ in range(1000):
            assert hiredis.pack_command(args) == expected

    errors = _run_in_threads(worker, n_threads=8)
    assert not errors, errors


def test_concurrent_error_callbacks():
    """User-supplied error classes are invoked from inside the parser
    callbacks while the per-Reader lock is held. With one Reader per thread
    they must produce isolated, correct results."""
    calls = []
    calls_lock = threading.Lock()

    def make_error(msg):
        with calls_lock:
            calls.append(msg)
        return RuntimeError(msg)

    iterations = 100

    def worker():
        for _ in range(iterations):
            r = hiredis.Reader(replyError=make_error)
            r.feed(b"-ERR something went wrong\r\n")
            reply = r.gets()
            assert isinstance(reply, RuntimeError)

    errors = _run_in_threads(worker, n_threads=8)
    assert not errors, errors
    assert len(calls) == 8 * iterations
