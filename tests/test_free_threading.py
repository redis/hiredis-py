import os
import subprocess
import sys
import sysconfig

import pytest


def run_python(code):
    env = os.environ.copy()
    env["PYTHON_GIL"] = "0"
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.mark.skipif(
    sysconfig.get_config_var("Py_GIL_DISABLED") != 1,
    reason="requires a CPython free-threading build",
)
def test_import_does_not_enable_gil_on_free_threading_build():
    code = (
        "import sys; "
        "import hiredis; "
        "raise SystemExit(0 if not sys._is_gil_enabled() else 1)"
    )
    result = run_python(code)

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(
    sysconfig.get_config_var("Py_GIL_DISABLED") != 1,
    reason="requires a CPython free-threading build",
)
def test_independent_readers_parse_concurrently_on_free_threading_build():
    code = r"""
import sys
import threading
import hiredis

THREADS = 8
COUNT = 5000

def parse_replies():
    reader = hiredis.Reader()
    for _ in range(COUNT):
        reader.feed(b"+OK\r\n")
        reply = reader.gets()
        if reply != b"OK":
            raise AssertionError(reply)

threads = [threading.Thread(target=parse_replies) for _ in range(THREADS)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()

if sys._is_gil_enabled():
    raise AssertionError("GIL was enabled")
"""
    result = run_python(code)

    assert result.returncode == 0, result.stderr
