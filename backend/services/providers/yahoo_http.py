from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import pandas as pd

from services.cache import cached
from services.language import analyst_action_row, days_since, display_outlook, stars_from_grade
from services.numbers import iso, to_float, to_int

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}


def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    try:
        with httpx.Client(timeout=20.0, headers=HEADERS, follow_redirects=True) as client:
            response = client.get(url, params=params)
            if response.status_code >= 400:
                logger.warning("Yahoo HTTP %s -> %s", url, response.status_code)
                return None
            payload = response.json()
        return payload if isinstance(payload, dict) else None
    except Exception:
        logger.exception("Yahoo HTTP request failed: %s", url)
        return None


def fetch_chart(symbol: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    payload = _get_json(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        {"range": "2y", "interval": "1d", "events": "div,splits"},
    )
    if not payload:
        payload = _get_json(
            f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
            {"range": "2y", "interval": "1d"},
        )
    result = ((payload or {}).get("chart") or {}).get("result") or []
    if not result:
        return pd.DataFrame(), {}
    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
    adj = ((item.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")
    frame = pd.DataFrame(
        {
            "Open": quote.get("open") or [],
            "High": quote.get("high") or [],
            "Low": quote.get("low") or [],
            "Close": adj or quote.get("close") or [],
            "Volume": quote.get("volume") or [],
        },
        index=pd.to_datetime(timestamps, unit="s", utc=True),
    )
    frame = frame.dropna(subset=["Close"])
    meta = item.get("meta") or {}
    info = {
        "shortName": meta.get("shortName") or meta.get("longName") or meta.get("symbol"),
        "longName": meta.get("longName"),
        "currency": meta.get("currency") or "USD",
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        "currentPrice": to_float(meta.get("regularMarketPrice")),
        "regularMarketPrice": to_float(meta.get("regularMarketPrice")),
        "previousClose": to_float(meta.get("chartPreviousClose") or meta.get("previousClose")),
        "regularMarketPreviousClose": to_float(meta.get("chartPreviousClose")),
    }
    return frame, info


def spark_quote(symbol: str) -> dict[str, Any]:
    payload = _get_json(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        {"range": "1d", "interval": "5m"},
    )
    if not payload:
        payload = _get_json(
            f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
            {"range": "1d", "interval": "5m"},
        )
    result = ((payload or {}).get("chart") or {}).get("result") or []
    meta = (result[0].get("meta") if result else {}) or {}
    price = to_float(meta.get("regularMarketPrice") or meta.get("currentPrice"))
    previous = to_float(meta.get("chartPreviousClose") or meta.get("previousClose") or meta.get("regularMarketPreviousClose"))
    change_percent = None
    if price is not None and previous not in (None, 0):
        change_percent = ((price - previous) / previous) * 100
    return {
        "symbol": symbol,
        "name": meta.get("shortName") or meta.get("longName") or symbol,
        "price": price,
        "previous_close": previous,
        "change_percent": change_percent,
    }


def fetch_quote_summary(symbol: str) -> dict[str, Any]:
    modules = ",".join(
        [
            "price",
            "summaryDetail",
            "defaultKeyStatistics",
            "financialData",
            "calendarEvents",
            "assetProfile",
        ]
    )
    payload = _get_json(
        f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
        {"modules": modules},
    )
    result = ((payload or {}).get("quoteSummary") or {}).get("result") or []
    if not result:
        payload = _authed_json(
            f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
            {"modules": modules},
        )
        result = ((payload or {}).get("quoteSummary") or {}).get("result") or []
    if not result:
        return {}
    block = result[0]
    info: dict[str, Any] = {}

    def _raw(node: Any, *keys: str) -> Any:
        current = node
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        if isinstance(current, dict) and "raw" in current:
            return current.get("raw")
        return current

    price = block.get("price") or {}
    summary = block.get("summaryDetail") or {}
    stats = block.get("defaultKeyStatistics") or {}
    financials = block.get("financialData") or {}
    profile = block.get("assetProfile") or {}
    calendar = block.get("calendarEvents") or {}
    info.update(
        {
            "shortName": price.get("shortName") or price.get("longName"),
            "longName": price.get("longName"),
            "currency": price.get("currency") or "USD",
            "exchange": price.get("exchangeName"),
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "currentPrice": _raw(price, "regularMarketPrice"),
            "regularMarketPrice": _raw(price, "regularMarketPrice"),
            "previousClose": _raw(summary, "previousClose"),
            "open": _raw(summary, "open"),
            "dayHigh": _raw(summary, "dayHigh"),
            "dayLow": _raw(summary, "dayLow"),
            "volume": _raw(summary, "volume"),
            "averageVolume": _raw(summary, "averageVolume"),
            "marketCap": _raw(summary, "marketCap"),
            "trailingPE": _raw(summary, "trailingPE"),
            "forwardPE": _raw(summary, "forwardPE"),
            "dividendYield": _raw(summary, "dividendYield"),
            "dividendRate": _raw(summary, "dividendRate"),
            "payoutRatio": _raw(summary, "payoutRatio"),
            "exDividendDate": _raw(summary, "exDividendDate"),
            "fiftyTwoWeekHigh": _raw(summary, "fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": _raw(summary, "fiftyTwoWeekLow"),
            "shortPercentOfFloat": _raw(stats, "shortPercentOfFloat"),
            "sharesShort": _raw(stats, "sharesShort"),
            "shortRatio": _raw(stats, "shortRatio"),
            "heldPercentInstitutions": _raw(stats, "heldPercentInstitutions"),
            "pegRatio": _raw(stats, "pegRatio"),
            "priceToBook": _raw(stats, "priceToBook"),
            "enterpriseToEbitda": _raw(stats, "enterpriseToEbitda"),
            "targetMeanPrice": _raw(financials, "targetMeanPrice"),
            "targetHighPrice": _raw(financials, "targetHighPrice"),
            "targetLowPrice": _raw(financials, "targetLowPrice"),
            "recommendationKey": financials.get("recommendationKey"),
            "numberOfAnalystOpinions": _raw(financials, "numberOfAnalystOpinions"),
            "grossMargins": _raw(financials, "grossMargins"),
            "operatingMargins": _raw(financials, "operatingMargins"),
            "profitMargins": _raw(financials, "profitMargins"),
            "returnOnEquity": _raw(financials, "returnOnEquity"),
            "freeCashflow": _raw(financials, "freeCashflow"),
            "totalRevenue": _raw(financials, "totalRevenue"),
            "debtToEquity": _raw(financials, "debtToEquity"),
            "trailingEps": _raw(stats, "trailingEps"),
            "forwardEps": _raw(stats, "forwardEps"),
            "earningsTimestamp": _raw(calendar, "earnings", "earningsDate")
            if isinstance(calendar.get("earnings"), dict)
            else None,
        }
    )
    earnings_dates = ((calendar.get("earnings") or {}).get("earningsDate") or []) if isinstance(calendar.get("earnings"), dict) else []
    if earnings_dates:
        first = earnings_dates[0]
        info["earningsTimestamp"] = first.get("raw") if isinstance(first, dict) else first
    return {key: value for key, value in info.items() if value is not None}


def http_bundle(symbol: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    history, meta_info = fetch_chart(symbol)
    quote_info = fetch_quote_summary(symbol)
    authed = quote_details(symbol)
    return history, {**meta_info, **quote_info, **(authed.get("info") or {})}


def _raw(node: Any, *keys: str) -> Any:
    current = node
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    if isinstance(current, dict) and "raw" in current:
        return current.get("raw")
    return current


def quote_details(symbol: str) -> dict[str, Any]:
    def _fetch() -> dict[str, Any]:
        payload = _authed_json(
            f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
            {
                "modules": ",".join(
                    [
                        "financialData",
                        "defaultKeyStatistics",
                        "upgradeDowngradeHistory",
                        "institutionOwnership",
                        "majorHoldersBreakdown",
                    ]
                )
            },
        )
        result = ((payload or {}).get("quoteSummary") or {}).get("result") or []
        if not result:
            return {}
        block = result[0]
        stats = block.get("defaultKeyStatistics") or {}
        financials = block.get("financialData") or {}
        majors = block.get("majorHoldersBreakdown") or {}
        info = {
            "targetMeanPrice": _raw(financials, "targetMeanPrice"),
            "targetHighPrice": _raw(financials, "targetHighPrice"),
            "targetLowPrice": _raw(financials, "targetLowPrice"),
            "recommendationKey": financials.get("recommendationKey"),
            "numberOfAnalystOpinions": _raw(financials, "numberOfAnalystOpinions"),
            "shortPercentOfFloat": _raw(stats, "shortPercentOfFloat"),
            "sharesShort": _raw(stats, "sharesShort"),
            "sharesShortPriorMonth": _raw(stats, "sharesShortPriorMonth"),
            "shortRatio": _raw(stats, "shortRatio"),
            "heldPercentInstitutions": _raw(majors, "institutionsPercentHeld") or _raw(stats, "heldPercentInstitutions"),
            "heldPercentInsiders": _raw(majors, "insidersPercentHeld"),
            "institutionsCount": _raw(majors, "institutionsCount"),
            "averageVolume": _raw(stats, "averageVolume") or _raw(stats, "averageDailyVolume10Day"),
        }
        holders = []
        for row in (block.get("institutionOwnership") or {}).get("ownershipList") or []:
            holders.append(
                {
                    "holder": row.get("organization"),
                    "shares": _raw(row, "position"),
                    "value": _raw(row, "value"),
                    "pct": (_raw(row, "pctHeld") or 0) * 100 if _raw(row, "pctHeld") is not None else None,
                    "change": (_raw(row, "pctChange") or 0) * 100 if _raw(row, "pctChange") is not None else None,
                    "report_date": (row.get("reportDate") or {}).get("fmt"),
                }
            )
        history_rows = (block.get("upgradeDowngradeHistory") or {}).get("history") or []
        recent_actions, top_analysts, upgrades, downgrades, top = _analyst_feed(history_rows)
        short_pct = to_float(info.get("shortPercentOfFloat"))
        if short_pct is not None and short_pct <= 1:
            short_pct *= 100
        prior = to_float(info.get("sharesShortPriorMonth"))
        current_short = to_float(info.get("sharesShort"))
        trend = None
        if current_short is not None and prior not in (None, 0):
            trend = "up" if current_short > prior * 1.03 else "down" if current_short < prior * 0.97 else "stable"
        inst_pct = to_float(info.get("heldPercentInstitutions"))
        if inst_pct is not None and inst_pct <= 1.5:
            inst_pct *= 100
        avg_vol = to_float(info.get("averageVolume"))
        days = (current_short / avg_vol) if current_short and avg_vol else to_float(info.get("shortRatio"))
        return {
            "info": {key: value for key, value in info.items() if value is not None},
            "average_target": to_float(info.get("targetMeanPrice")),
            "high_target": to_float(info.get("targetHighPrice")),
            "low_target": to_float(info.get("targetLowPrice")),
            "consensus": info.get("recommendationKey"),
            "total_analysts": to_int(info.get("numberOfAnalystOpinions")),
            "upgrades": upgrades[:8],
            "downgrades": downgrades[:8],
            "recent_actions": recent_actions,
            "top_analysts": top_analysts,
            "top_analyst": top,
            "holders": holders,
            "short_interest_pct": short_pct,
            "short_interest_trend": trend,
            "days_to_cover": days,
            "institutional_ownership_pct": inst_pct,
            "institutional_ownership_change": _avg([h.get("change") for h in holders]),
            "new_institutional_additions": sum(1 for h in holders if (h.get("change") or 0) > 0),
            "new_institutional_buyers": sum(1 for h in holders if (h.get("change") or 0) > 0),
        }

    return cached(f"yahoo:details:v3:{symbol}", _fetch, ttl=180)


def _analyst_feed(history: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    parsed: list[dict[str, Any]] = []
    for row in history:
        epoch = to_float(_raw(row, "epochGradeDate")) or to_float(row.get("epochGradeDate"))
        if epoch and epoch > 1e12:
            epoch = epoch / 1000
        target = to_float(_raw(row, "currentPriceTarget")) or to_float(row.get("currentPriceTarget"))
        previous = to_float(_raw(row, "previousPriceTarget")) or to_float(row.get("previousPriceTarget"))
        parsed.append(
            {
                "epoch": epoch or 0,
                "firm": row.get("firm"),
                "name": row.get("analyst") or row.get("analystName") or "Research desk",
                "from_grade": row.get("fromGrade"),
                "to_grade": row.get("toGrade"),
                "action": row.get("action") or row.get("priceTargetAction"),
                "price_target": target,
                "previous_target": previous,
                "date": iso(datetime.fromtimestamp(epoch, tz=timezone.utc)) if epoch else None,
            }
        )
    parsed.sort(key=lambda item: item["epoch"])
    last_target: dict[str, float] = {}
    for row in parsed:
        key = str(row.get("firm") or row.get("name") or "")
        if row.get("previous_target") is None and key:
            row["previous_target"] = last_target.get(key)
        if key and row.get("price_target") is not None:
            last_target[key] = row["price_target"]

    newest = list(reversed(parsed))
    actions: list[dict[str, Any]] = []
    for row in newest:
        if not row.get("firm") and not row.get("to_grade"):
            continue
        actions.append(
            analyst_action_row(
                {
                    "name": row.get("name"),
                    "firm": row.get("firm"),
                    "to_grade": row.get("to_grade"),
                    "previous_target": row.get("previous_target"),
                    "price_target": row.get("price_target"),
                    "action": row.get("action"),
                    "date": row.get("date"),
                }
            )
        )
        if len(actions) >= 10:
            break

    latest_by_firm: dict[str, dict[str, Any]] = {}
    target_by_firm: dict[str, float] = {}
    for row in newest:
        firm = row.get("firm")
        if not firm:
            continue
        if firm not in latest_by_firm:
            latest_by_firm[firm] = row
        if firm not in target_by_firm and row.get("price_target") is not None:
            target_by_firm[firm] = row["price_target"]

    ranked = sorted(
        latest_by_firm.values(),
        key=lambda item: (stars_from_grade(item.get("to_grade")), item.get("epoch") or 0),
        reverse=True,
    )
    top_analysts: list[dict[str, Any]] = []
    for row in ranked[:3]:
        firm = row.get("firm")
        grade = row.get("to_grade")
        top_analysts.append(
            {
                "name": row.get("name") or "Research desk",
                "firm": firm,
                "stars": stars_from_grade(grade),
                "accuracy_pct": None,
                "current_target": target_by_firm.get(firm) if firm else row.get("price_target"),
                "sentiment": display_outlook(grade),
                "days_ago": days_since(row.get("date")),
            }
        )

    upgrades: list[dict[str, Any]] = []
    downgrades: list[dict[str, Any]] = []
    top = None
    cutoff = time.time() - 30 * 86400
    for row in newest:
        if top is None and row.get("firm"):
            top = {
                "firm": row.get("firm"),
                "rating": display_outlook(row.get("to_grade")),
                "date": row.get("date"),
            }
        action = str(row.get("action") or "").lower()
        item = {
            "firm": row.get("firm"),
            "action": row.get("action"),
            "from_grade": row.get("from_grade"),
            "to_grade": display_outlook(row.get("to_grade")),
            "date": row.get("date"),
            "price_target": row.get("price_target"),
        }
        if row.get("epoch") and row["epoch"] >= cutoff:
            if action in {"down", "downgrade"} or "down" in action:
                downgrades.append(item)
            elif action in {"up", "upgrade", "init"} or "up" in action or "init" in action:
                upgrades.append(item)
    return actions, top_analysts, upgrades, downgrades, top


def _avg(values: list[Any]) -> float | None:
    present = [to_float(value) for value in values]
    present = [value for value in present if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _authed_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    try:
        with httpx.Client(timeout=20.0, headers=HEADERS, follow_redirects=True) as client:
            client.get("https://fc.yahoo.com")
            crumb = client.get("https://query1.finance.yahoo.com/v1/test/getcrumb").text.strip()
            if not crumb or "<" in crumb:
                logger.warning("Yahoo crumb missing")
                return None
            query = {**(params or {}), "crumb": crumb}
            response = client.get(url, params=query)
            if response.status_code >= 400:
                logger.warning("Yahoo authed %s -> %s", url, response.status_code)
                return None
            payload = response.json()
        return payload if isinstance(payload, dict) else None
    except Exception:
        logger.exception("Yahoo authed request failed: %s", url)
        return None
