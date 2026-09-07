from __future__ import annotations

import logging
from typing import Any

import httpx

from services.cache import cached
from services.keys import reddit_user_agent

logger = logging.getLogger(__name__)


def mentions(ticker: str) -> dict[str, Any] | None:
    def _search(window: str) -> int:
        try:
            with httpx.Client(timeout=15.0, headers={"User-Agent": reddit_user_agent()}) as client:
                response = client.get(
                    "https://www.reddit.com/search.json",
                    params={"q": ticker, "sort": "new", "limit": 100, "t": window},
                )
                if response.status_code >= 400:
                    return 0
                payload = response.json()
            children = ((payload.get("data") or {}).get("children") or []) if isinstance(payload, dict) else []
            return len(children)
        except Exception:
            logger.debug("Reddit search failed for %s %s", ticker, window, exc_info=True)
            return 0

    def _fetch() -> dict[str, Any] | None:
        week = _search("week")
        month = _search("month")
        if week == 0 and month == 0:
            return None
        expected = month / 4 if month else 0
        if week > expected * 1.2 and week >= 5:
            trend = "up"
        elif expected and week < expected * 0.8:
            trend = "down"
        else:
            trend = "stable"
        return {"mention_count": week or month, "trend": trend, "week": week, "month": month}

    return cached(f"reddit:{ticker}", _fetch, ttl=600)
