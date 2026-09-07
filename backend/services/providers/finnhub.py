from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from services.cache import cached
from services.keys import finnhub_key
from services.numbers import iso, to_float, to_int

logger = logging.getLogger(__name__)
BASE = "https://finnhub.io/api/v1"


def _get(path: str, params: dict[str, Any]) -> Any | None:
    token = finnhub_key()
    if not token:
        return None

    def _fetch() -> Any | None:
        query = {**params, "token": token}
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(f"{BASE}{path}", params=query)
                if response.status_code >= 400:
                    logger.warning("Finnhub %s status %s", path, response.status_code)
                    return None
                return response.json()
        except Exception:
            logger.exception("Finnhub %s failed", path)
            return None

    cache_key = f"fh:{path}:{sorted(params.items())}"
    return cached(cache_key, _fetch, ttl=180)


def recommendation(ticker: str) -> dict[str, Any] | None:
    rows = _get("/stock/recommendation", {"symbol": ticker})
    if not isinstance(rows, list) or not rows:
        return None
    latest = rows[0]
    buy = (to_int(latest.get("strongBuy")) or 0) + (to_int(latest.get("buy")) or 0)
    hold = to_int(latest.get("hold")) or 0
    sell = (to_int(latest.get("sell")) or 0) + (to_int(latest.get("strongSell")) or 0)
    return {"buy": buy, "hold": hold, "sell": sell, "total": buy + hold + sell, "period": latest.get("period")}


def price_target(ticker: str) -> dict[str, Any] | None:
    payload = _get("/stock/price-target", {"symbol": ticker})
    if not isinstance(payload, dict) or not payload:
        return None
    return {
        "average_target": to_float(payload.get("targetMean") or payload.get("targetMedian")),
        "high_target": to_float(payload.get("targetHigh")),
        "low_target": to_float(payload.get("targetLow")),
    }


def upgrades(ticker: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    rows = _get("/stock/upgrade-downgrade", {"symbol": ticker})
    if not isinstance(rows, list):
        return [], [], None
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    up: list[dict[str, Any]] = []
    down: list[dict[str, Any]] = []
    top = None
    for row in rows[:50]:
        when = None
        ts = row.get("gradeTime")
        if isinstance(ts, (int, float)):
            epoch = ts / 1000 if ts > 1e12 else ts
            when = datetime.fromtimestamp(epoch, tz=timezone.utc)
        action = str(row.get("action") or "").lower()
        item = {
            "firm": row.get("company"),
            "action": row.get("action"),
            "from_grade": row.get("fromGrade"),
            "to_grade": row.get("toGrade"),
            "date": iso(when),
        }
        if top is None and row.get("company"):
            top = {"firm": row.get("company"), "rating": row.get("toGrade") or row.get("action"), "date": iso(when)}
        if when is not None and when >= cutoff:
            if "down" in action:
                down.append(item)
            elif "up" in action or "init" in action:
                up.append(item)
    return up[:8], down[:8], top


def company_news(ticker: str) -> list[dict[str, Any]]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=7)
    rows = _get("/company-news", {"symbol": ticker, "from": start.isoformat(), "to": end.isoformat()})
    if not isinstance(rows, list):
        return []
    items = []
    for row in rows[:12]:
        ts = row.get("datetime")
        published = iso(datetime.fromtimestamp(ts, tz=timezone.utc)) if isinstance(ts, (int, float)) else None
        items.append(
            {
                "source": row.get("source"),
                "headline": row.get("headline"),
                "url": row.get("url"),
                "published_at": published,
                "summary": row.get("summary"),
            }
        )
    return items


def earnings_calendar(ticker: str) -> dict[str, Any] | None:
    today = datetime.now(timezone.utc).date()
    payload = _get(
        "/calendar/earnings",
        {"symbol": ticker, "from": today.isoformat(), "to": (today + timedelta(days=90)).isoformat()},
    )
    rows = payload.get("earningsCalendar") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        return None
    row = rows[0]
    date_value = row.get("date")
    days_away = None
    if date_value:
        try:
            days_away = (datetime.fromisoformat(str(date_value)).date() - today).days
        except Exception:
            days_away = None
    hour = str(row.get("hour") or "").lower()
    if hour in {"bmo", "amc"}:
        time_of_day = "before market" if hour == "bmo" else "after market"
    else:
        time_of_day = row.get("hour")
    return {
        "next_earnings_date": date_value,
        "days_away": days_away,
        "time_of_day": time_of_day,
        "eps_estimate": to_float(row.get("epsEstimate")),
        "revenue_estimate": to_float(row.get("revenueEstimate")),
    }


def earnings_surprises(ticker: str) -> list[dict[str, Any]]:
    rows = _get("/stock/earnings", {"symbol": ticker})
    if not isinstance(rows, list):
        return []
    items = []
    for row in rows[:8]:
        est = to_float(row.get("estimate"))
        actual = to_float(row.get("actual"))
        items.append(
            {
                "quarter": row.get("period"),
                "eps_estimate": est,
                "eps_actual": actual,
                "beat": None if actual is None or est is None else actual >= est,
                "surprise_pct": to_float(row.get("surprisePercent")),
            }
        )
    return items


def peers(ticker: str) -> list[str]:
    rows = _get("/stock/peers", {"symbol": ticker})
    if not isinstance(rows, list):
        return []
    return [str(item) for item in rows if item and str(item).upper() != ticker.upper()][:12]


def metrics(ticker: str) -> dict[str, Any] | None:
    payload = _get("/stock/metric", {"symbol": ticker, "metric": "all"})
    metric = payload.get("metric") if isinstance(payload, dict) else None
    if not isinstance(metric, dict):
        return None
    return {
        "pe_ratio": to_float(metric.get("peNormalizedAnnual") or metric.get("peTTM")),
        "pb": to_float(metric.get("pbAnnual")),
        "ps": to_float(metric.get("psTTM")),
        "roe": to_float(metric.get("roeTTM") or metric.get("roeRfy")),
        "short_interest_pct": to_float(metric.get("shortInterestPercent") or metric.get("shortInterestRatio")),
    }
