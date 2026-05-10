import time
from collections import defaultdict
from typing import Optional


class LimitTracker:
    def __init__(self):
        self._minute_counts: dict[str, list[float]] = defaultdict(list)
        self._day_counts: dict[str, list[float]] = defaultdict(list)

    def _key(self, provider: str, model: str) -> str:
        return f"{provider}:{model}"

    def _prune(self, key: str, window: int, store: dict[str, list[float]]):
        now = time.time()
        store[key] = [t for t in store[key] if now - t < window]

    def check(self, provider: str, model: str) -> tuple[bool, Optional[str]]:
        key = self._key(provider, model)

        self._prune(key, 60, self._minute_counts)
        self._prune(key, 86400, self._day_counts)

        minute_count = len(self._minute_counts[key])
        day_count = len(self._day_counts[key])

        if minute_count >= 100:
            return False, "Minute rate limit exceeded (100 req/min)"
        if day_count >= 5000:
            return False, "Daily rate limit exceeded (5000 req/day)"

        return True, None

    def increment(self, provider: str, model: str):
        key = self._key(provider, model)
        now = time.time()
        self._minute_counts[key].append(now)
        self._day_counts[key].append(now)

    def get_remaining(
        self, provider: str, model: str
    ) -> dict[str, int]:
        key = self._key(provider, model)
        self._prune(key, 60, self._minute_counts)
        self._prune(key, 86400, self._day_counts)

        return {
            "requests_remaining_this_minute": max(0, 100 - len(self._minute_counts[key])),
            "requests_remaining_today": max(0, 5000 - len(self._day_counts[key])),
        }


limit_tracker = LimitTracker()
