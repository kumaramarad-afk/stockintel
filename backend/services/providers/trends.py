from __future__ import annotations

import logging
from typing import Any

from services.cache import cached
from services.numbers import to_float

logger = logging.getLogger(__name__)


def interest(ticker: str) -> dict[str, Any] | None:
    def _fetch() -> dict[str, Any] | None:
        try:
            from pytrends.request import TrendReq
        except Exception:
            logger.warning("pytrends is not installed")
            return None
        try:
            pytrends = TrendReq(hl="en-US", tz=360, retries=2, backoff_factor=0.4)
            pytrends.build_payload([ticker], timeframe="today 3-m")
            frame = pytrends.interest_over_time()
            if frame is None or frame.empty or ticker not in frame.columns:
                return None
            series = frame[ticker].astype(float)
            latest = to_float(series.iloc[-1])
            previous = to_float(series.iloc[-5]) if len(series) > 5 else to_float(series.iloc[0])
            if latest is None:
                return None
            if previous is None:
                direction = "stable"
            elif latest > previous * 1.15:
                direction = "up"
            elif latest < previous * 0.85:
                direction = "down"
            else:
                direction = "stable"
            return {"score": latest, "direction": direction}
        except Exception:
            logger.debug("Google Trends failed for %s", ticker, exc_info=True)
            return None

    return cached(f"trends:{ticker}", _fetch, ttl=3600)
