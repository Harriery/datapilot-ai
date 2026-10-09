from __future__ import annotations

import os
import time
from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class CacheEntry:
    value: object
    size_bytes: int
    expires_at: float


class PracticeSourceMemoryCache:
    """
    Small in-memory TTL + LRU cache for external Practice source content.

    This cache is intentionally disposable:
    - no learner progress lives here
    - no learner notes live here
    - process restart clears it
    - size is bounded
    """

    def __init__(
        self,
        *,
        max_bytes: int,
        ttl_seconds: int,
    ):
        self.max_bytes = max(
            0,
            max_bytes,
        )
        self.ttl_seconds = max(
            0,
            ttl_seconds,
        )
        self._entries: OrderedDict[
            str,
            CacheEntry,
        ] = OrderedDict()
        self._size_bytes = 0

    def _remove(self, key: str) -> None:
        entry = self._entries.pop(
            key,
            None,
        )

        if entry is not None:
            self._size_bytes -= (
                entry.size_bytes
            )

    def _evict_expired(
        self,
        *,
        now: float,
    ) -> None:
        expired_keys = [
            key
            for key, entry in self._entries.items()
            if entry.expires_at <= now
        ]

        for key in expired_keys:
            self._remove(key)

    def get(
        self,
        key: str,
    ) -> object | None:
        now = time.monotonic()
        self._evict_expired(now=now)

        entry = self._entries.get(key)

        if entry is None:
            return None

        self._entries.move_to_end(key)
        return entry.value

    def put(
        self,
        *,
        key: str,
        value: object,
        size_bytes: int,
    ) -> bool:
        if (
            self.max_bytes <= 0
            or self.ttl_seconds <= 0
            or size_bytes <= 0
            or size_bytes > self.max_bytes
        ):
            return False

        now = time.monotonic()
        self._evict_expired(now=now)
        self._remove(key)

        while (
            self._entries
            and self._size_bytes + size_bytes
            > self.max_bytes
        ):
            oldest_key = next(
                iter(self._entries)
            )
            self._remove(oldest_key)

        self._entries[key] = CacheEntry(
            value=value,
            size_bytes=size_bytes,
            expires_at=(
                now + self.ttl_seconds
            ),
        )
        self._size_bytes += size_bytes
        return True

    def clear(self) -> None:
        self._entries.clear()
        self._size_bytes = 0


PRACTICE_SOURCE_CACHE = (
    PracticeSourceMemoryCache(
        max_bytes=int(
            os.getenv(
                "PRACTICE_SOURCE_CACHE_MAX_BYTES",
                "5242880",
            )
        ),
        ttl_seconds=int(
            os.getenv(
                "PRACTICE_SOURCE_CACHE_TTL_SECONDS",
                "21600",
            )
        ),
    )
)
