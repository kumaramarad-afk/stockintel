from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from services.cache import cached
from services.numbers import iso

logger = logging.getLogger(__name__)

HOUSE_URL = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
SENATE_URL = "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json"


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).split("T")[0]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _load(url: str, cache_key: str) -> list[dict[str, Any]]:
    def _fetch() -> list[dict[str, Any]]:
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json()
            return payload if isinstance(payload, list) else []
        except Exception:
            logger.exception("Capitol trades fetch failed for %s", url)
            return []

    return cached(cache_key, _fetch, ttl=21600)


def trades_for(ticker: str) -> list[dict[str, Any]]:
    symbol = ticker.upper()
    cutoff = datetime.now(timezone.utc) - timedelta(days=45)
    matches: list[dict[str, Any]] = []
    for url, key, politician_field, ticker_field in (
        (HOUSE_URL, "capitol:house", "representative", "ticker"),
        (SENATE_URL, "capitol:senate", "senator", "ticker"),
    ):
        for row in _load(url, key):
            raw_ticker = str(row.get(ticker_field) or row.get("asset_ticker") or "").upper()
            if symbol not in raw_ticker.replace("$", "").split():
                if raw_ticker != symbol and not raw_ticker.startswith(symbol + ":"):
                    continue
            when = _parse_date(row.get("transaction_date") or row.get("disclosure_date"))
            if when is None or when < cutoff:
                continue
            action = row.get("type") or row.get("transaction_type") or row.get("ptr_transaction_type")
            matches.append(
                {
                    "politician": row.get(politician_field) or row.get("representative") or row.get("senator"),
                    "action": action,
                    "amount": row.get("amount") or row.get("range"),
                    "date": iso(when),
                    "asset": row.get("asset_description") or row.get("ticker"),
                }
            )
    matches.sort(key=lambda item: item.get("date") or "", reverse=True)
    return matches[:12]
