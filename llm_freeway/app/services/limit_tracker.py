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

    def get_usage_snapshot(self) -> dict:
        all_keys = set(self._minute_counts.keys()) | set(self._day_counts.keys())
        by_provider: dict[str, dict] = {}
        by_model: list[dict] = []

        for key in sorted(all_keys):
            provider, model = key.split(":", 1)
            self._prune(key, 60, self._minute_counts)
            self._prune(key, 86400, self._day_counts)

            calls_this_minute = len(self._minute_counts[key])
            calls_today = len(self._day_counts[key])

            provider_entry = by_provider.setdefault(
                provider,
                {
                    "provider": provider,
                    "calls_this_minute": 0,
                    "calls_today": 0,
                    "models": [],
                },
            )
            provider_entry["calls_this_minute"] += calls_this_minute
            provider_entry["calls_today"] += calls_today
            provider_entry["models"].append(
                {
                    "model": model,
                    "calls_this_minute": calls_this_minute,
                    "calls_today": calls_today,
                }
            )
            by_model.append(
                {
                    "provider": provider,
                    "model": model,
                    "calls_this_minute": calls_this_minute,
                    "calls_today": calls_today,
                }
            )

        provider_list = sorted(
            by_provider.values(),
            key=lambda item: (-item["calls_today"], item["provider"]),
        )
        for provider_entry in provider_list:
            provider_entry["models"] = sorted(
                provider_entry["models"],
                key=lambda item: (-item["calls_today"], item["model"]),
            )

        return {
            "providers": provider_list,
            "models": sorted(
                by_model,
                key=lambda item: (-item["calls_today"], item["provider"], item["model"]),
            ),
        }


limit_tracker = LimitTracker()
