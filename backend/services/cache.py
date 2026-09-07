from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock
from typing import TypeVar

T = TypeVar("T")

_lock = Lock()
_store: dict[str, tuple[float, object]] = {}


def cached(key: str, factory: Callable[[], T], ttl: float = 180.0) -> T:
    now = time.time()
    with _lock:
        hit = _store.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]  # type: ignore[return-value]
    value = factory()
    with _lock:
        _store[key] = (now, value)
    return value
