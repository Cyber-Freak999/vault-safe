import threading
import time
from collections import defaultdict


class LockoutStore:
    def __init__(self, max_failures: int = 5, lockout_seconds: int = 300) -> None:
        self._max = max_failures
        self._window = lockout_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        for key, stamps in list(self._failures.items()):
            keep = [t for t in stamps if now - t < self._window]
            if keep:
                self._failures[key] = keep
            else:
                del self._failures[key]

    def is_locked(self, *keys: str) -> bool:
        with self._lock:
            now = time.monotonic()
            self._prune(now)
            return any(len(self._failures.get(key, [])) >= self._max for key in keys)

    def record_failure(self, *keys: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            for key in keys:
                self._failures[key].append(now)

    def reset(self, *keys: str) -> None:
        with self._lock:
            for key in keys:
                self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


lockout_store = LockoutStore()
