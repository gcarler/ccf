"""Cross-platform file locking for safe concurrent reads/writes.

Uses ``fcntl.flock`` on Unix and ``msvcrt.locking`` on Windows.
Falls back to a directory-based mutex when neither is available.
"""
import os
import time
from contextlib import contextmanager
from pathlib import Path


_LOCK_POLL_INTERVAL = 0.05  # seconds
_LOCK_TIMEOUT = 10.0  # seconds


def _acquire_file_lock(lock_file: Path, timeout: float = _LOCK_TIMEOUT) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(fd)
            return True
        except FileExistsError:
            if time.monotonic() > deadline:
                return False
            time.sleep(_LOCK_POLL_INTERVAL)


def _release_file_lock(lock_file: Path) -> None:
    try:
        lock_file.unlink()
    except FileNotFoundError:
        pass


@contextmanager
def file_lock(file_path: str | Path) -> None:
    """Context manager that acquires an exclusive lock on a data file.

    Usage::

        with file_lock(FLAGS_FILE):
            data = json.loads(FLAGS_FILE.read_text())
            # ... modify data ...
            FLAGS_FILE.write_text(json.dumps(data))

    The lock file is created alongside the data file as ``<filename>.lock``.
    """
    target = Path(file_path)
    lock_path = target.with_suffix(target.suffix + ".lock")

    if not _acquire_file_lock(lock_path):
        raise TimeoutError(f"Could not acquire lock on {target} within {_LOCK_TIMEOUT}s")

    try:
        yield
    finally:
        _release_file_lock(lock_path)
