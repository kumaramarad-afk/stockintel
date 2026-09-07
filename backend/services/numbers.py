from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd


def to_float(value: Any) -> float | None:
    if value is None or value == "" or value == "None" or value == "-":
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def to_int(value: Any) -> int | None:
    number = to_float(value)
    if number is None:
        return None
    return int(number)


def clamp(value: float, low: float = 0, high: float = 100) -> int:
    return int(max(low, min(high, round(value))))


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return ((current - previous) / abs(previous)) * 100


def lookup(mapping: Any, *keys: str) -> Any:
    if mapping is None:
        return None
    getter = getattr(mapping, "get", None)
    for key in keys:
        value = getter(key) if callable(getter) else getattr(mapping, key, None)
        if value is not None:
            return value
    return None


def iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, pd.Timestamp):
        try:
            return value.to_pydatetime().isoformat()
        except Exception:
            return str(value)
    text = str(value).strip()
    return text or None


def yahoo_symbol(ticker: str) -> str:
    return ticker.strip().upper().replace(".", "-")
