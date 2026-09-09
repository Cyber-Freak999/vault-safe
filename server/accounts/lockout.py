import threading
from collections import defaultdict


class LockoutStore:
    def __init__(self, max_failures: int = 5, lockout_seconds: int = 300) -> None:
        self._max = max_failures
        self._window = lockout_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


lockout_store = LockoutStore()
