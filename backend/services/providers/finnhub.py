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
        query = {key: value for key, value in {**params, "token": token}.items() if value not in (None, "")}
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
        "last_updated": payload.get("lastUpdated"),
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


def _grade_when(row: dict[str, Any]) -> datetime | None:
    ts = row.get("gradeTime")
    if isinstance(ts, (int, float)):
        epoch = ts / 1000 if ts > 1e12 else ts
        return datetime.fromtimestamp(epoch, tz=timezone.utc)
    return None


def _row_target(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = to_float(row.get(key))
        if value is not None:
            return value
    return None


def rating_target_changes(days: int = 30, symbols: list[str] | None = None, limit: int = 20) -> list[dict[str, Any]]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = _get("/stock/upgrade-downgrade", {"from": start.isoformat(), "to": end.isoformat()})
    if not isinstance(rows, list):
        rows = []
    elif not rows:
        for symbol in symbols or []:
            payload = _get("/stock/upgrade-downgrade", {"symbol": symbol})
            if isinstance(payload, list):
                rows.extend(payload)
    items: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        when = _grade_when(row)
        if when is not None and when < cutoff:
            continue
        ticker = str(row.get("symbol") or "").upper().strip()
        if not ticker:
            continue
        old_rating = str(row.get("fromGrade") or "").strip() or "n/a"
        new_rating = str(row.get("toGrade") or row.get("action") or "").strip() or "n/a"
        old_target = _row_target(row, "fromPriceTarget", "priceTargetFrom", "fromPT", "oldPriceTarget")
        new_target = _row_target(row, "toPriceTarget", "priceTargetTo", "toPT", "priceTarget", "newPriceTarget")
        key = (ticker, row.get("company"), old_rating, new_rating, iso(when))
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "ticker": ticker,
                "firm": row.get("company") or "Analyst desk",
                "action": row.get("action"),
                "old_rating": old_rating,
                "new_rating": new_rating,
                "old_target": old_target,
                "new_target": new_target,
                "date": iso(when) or start.isoformat(),
            }
        )
    items.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    missing = []
    for item in items:
        if item.get("new_target") is None and item["ticker"] not in missing:
            missing.append(item["ticker"])
    for ticker in missing[:10]:
        target = price_target(ticker)
        if not target or target.get("average_target") is None:
            continue
        last_updated = str(target.get("last_updated") or "")
        recent = True
        if last_updated:
            try:
                stamp = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                recent = stamp >= cutoff
            except Exception:
                recent = True
        if not recent:
            continue
        for item in items:
            if item["ticker"] == ticker and item.get("new_target") is None:
                item["new_target"] = target["average_target"]
    return items[:limit]


def _consensus_label(row: dict[str, Any]) -> str:
    buy = (to_int(row.get("strongBuy")) or 0) + (to_int(row.get("buy")) or 0)
    hold = to_int(row.get("hold")) or 0
    sell = (to_int(row.get("sell")) or 0) + (to_int(row.get("strongSell")) or 0)
    total = buy + hold + sell
    if not total:
        return "n/a"
    if buy / total >= 0.6:
        return "Buy"
    if sell / total >= 0.4:
        return "Sell"
    return "Hold"


def recommendation_shifts(symbols: list[str], limit: int = 12) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for symbol in symbols:
        rows = _get("/stock/recommendation", {"symbol": symbol})
        if not isinstance(rows, list) or len(rows) < 2:
            continue
        latest, prior = rows[0], rows[1]
        old_rating = _consensus_label(prior)
        new_rating = _consensus_label(latest)
        if old_rating == new_rating:
            continue
        items.append(
            {
                "ticker": symbol.upper(),
                "firm": "Finnhub consensus",
                "action": "revise",
                "old_rating": old_rating,
                "new_rating": new_rating,
                "old_target": None,
                "new_target": None,
                "date": str(latest.get("period") or ""),
            }
        )
        if len(items) >= limit:
            break
    return items


def general_news(limit: int = 15) -> list[dict[str, Any]]:
    rows = _get("/news", {"category": "general"})
    if not isinstance(rows, list):
        return []
    items: list[dict[str, Any]] = []
    for row in rows[: max(limit, 12)]:
        if not isinstance(row, dict):
            continue
        ts = row.get("datetime")
        published = iso(datetime.fromtimestamp(ts, tz=timezone.utc)) if isinstance(ts, (int, float)) else None
        related = [part.strip().upper() for part in str(row.get("related") or "").split(",") if part.strip()]
        summary = str(row.get("summary") or "").strip()
        items.append(
            {
                "ticker": related[0] if related else "MARKET",
                "headline": row.get("headline"),
                "summary": summary,
                "source": row.get("source") or "Finnhub",
                "url": row.get("url"),
                "published_at": published,
            }
        )
    return items


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


def earnings_week(days: int = 7) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    payload = _get(
        "/calendar/earnings",
        {"from": today.isoformat(), "to": (today + timedelta(days=days)).isoformat()},
    )
    rows = payload.get("earningsCalendar") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    items: list[dict[str, Any]] = []
    for row in rows[:12]:
        items.append(
            {
                "date": row.get("date"),
                "ticker": row.get("symbol"),
                "eps_estimate": to_float(row.get("epsEstimate")),
                "eps_actual": to_float(row.get("epsActual")),
                "hour": row.get("hour"),
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


def symbol_search(query: str, *, limit: int = 10) -> list[dict[str, str]]:
    """Finnhub symbol lookup — US common stock / ETF when available."""
    needle = (query or "").strip()
    if len(needle) < 1:
        return []
    payload = _get("/search", {"q": needle})
    if not isinstance(payload, dict):
        return []
    rows = payload.get("result")
    if not isinstance(rows, list):
        return []
    hits: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "").upper().strip()
        if not symbol or symbol in seen or "." in symbol and not symbol.replace(".", "").isalnum():
            continue
        # Finnhub includes many international symbols with exchange suffixes like AAPL.US
        if symbol.endswith(".US"):
            symbol = symbol[:-3]
        if "." in symbol and len(symbol.split(".")[-1]) > 1:
            continue
        kind = str(row.get("type") or "").lower()
        if kind and kind not in {"common stock", "etp", "etf", "adr", "equity"}:
            continue
        name = str(row.get("description") or symbol)
        seen.add(symbol)
        hits.append({"ticker": symbol, "company_name": name, "name": name})
        if len(hits) >= limit:
            break
    return hits


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
