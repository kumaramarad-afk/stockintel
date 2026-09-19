"""Structured data sections appended to public research reports."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

from services.cache import cached
from services.providers import finnhub, newsapi, sec_edgar
from services.ticker_catalog import display_name, market_symbol

logger = logging.getLogger(__name__)

DISCLAIMERS = {
    "analyst_ratings": "Analyst opinions change frequently. Past upgrades do not predict future returns.",
    "news": "News headlines are reported as-is. Verify important claims with original sources.",
    "insider": "Form 4 filings are routine transactions. Scheduled sales (10b5-1 plans) are normal and not signals.",
    "institutions": "These are 45-day lagged filings (SEC requirement). Position changes happened in the past.",
    "earnings": "Earnings dates are estimates and may shift. EPS estimates are consensus, not predictions.",
}


def _safe(factory, fallback: Any):
    try:
        return factory()
    except Exception:
        logger.exception("report_data fetch failed")
        return fallback


def get_analyst_ratings(ticker: str) -> list[dict[str, Any]]:
    symbol = market_symbol(ticker)

    def _fetch() -> list[dict[str, Any]]:
        up, down, _top = finnhub.upgrades(symbol)
        rows: list[dict[str, Any]] = []
        for row in up[:8]:
            rows.append(
                {
                    "analyst_name": row.get("firm") or "Analyst",
                    "action": row.get("action") or "upgrade",
                    "old_rating": row.get("from_grade"),
                    "new_rating": row.get("to_grade"),
                    "target_price": row.get("new_target") or row.get("target"),
                    "old_target": row.get("old_target"),
                    "date": row.get("date") or row.get("when"),
                    "direction": "up",
                }
            )
        for row in down[:8]:
            rows.append(
                {
                    "analyst_name": row.get("firm") or "Analyst",
                    "action": row.get("action") or "downgrade",
                    "old_rating": row.get("from_grade"),
                    "new_rating": row.get("to_grade"),
                    "target_price": row.get("new_target") or row.get("target"),
                    "old_target": row.get("old_target"),
                    "date": row.get("date") or row.get("when"),
                    "direction": "down",
                }
            )
        rows.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
        return rows[:10]

    return cached(f"report:analyst:{symbol}", lambda: _safe(_fetch, []), ttl=86400)


def get_important_news(ticker: str) -> list[dict[str, Any]]:
    symbol = market_symbol(ticker)
    name = display_name(ticker) or ticker

    def _fetch() -> list[dict[str, Any]]:
        rows = finnhub.company_news(symbol) or []
        if len(rows) < 3:
            extra = newsapi.company_headlines(f'{symbol} OR "{name}"', limit=8)
            seen = {str(item.get("url") or "") for item in rows}
            for item in extra:
                url = str(item.get("url") or "")
                if url and url not in seen:
                    rows.append(item)
                    seen.add(url)
        items: list[dict[str, Any]] = []
        for row in rows:
            headline = str(row.get("headline") or row.get("title") or "").strip()
            if not headline:
                continue
            if re.search(r"\bearnings\b|\bEPS\b|\bquarterly results\b", headline, re.I):
                continue
            items.append(
                {
                    "headline": headline,
                    "source": row.get("source") or "News",
                    "url": row.get("url"),
                    "date": row.get("published_at") or row.get("datetime") or row.get("date"),
                    "summary": row.get("summary") or row.get("description") or "",
                    "sentiment": row.get("sentiment"),
                }
            )
            if len(items) >= 5:
                break
        return items

    return cached(f"report:news:{symbol}", lambda: _safe(_fetch, []), ttl=43200)


def get_insider_activity(ticker: str) -> list[dict[str, Any]]:
    symbol = market_symbol(ticker)

    def _fetch() -> list[dict[str, Any]]:
        rows = sec_edgar.insider_transactions(symbol) or []
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        items: list[dict[str, Any]] = []
        for row in rows:
            when = str(row.get("date") or "")
            try:
                stamp = datetime.fromisoformat(when.replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                if stamp < cutoff:
                    continue
            except Exception:
                pass
            code = str(row.get("code") or "").upper()
            action = str(row.get("action") or "").lower()
            side = "buy" if code == "P" or "acquir" in action or action == "buy" else "sell"
            items.append(
                {
                    "executive_name": row.get("name") or "Insider",
                    "title": row.get("title"),
                    "transaction_type": side,
                    "shares_quantity": row.get("shares"),
                    "transaction_value": row.get("value"),
                    "date": row.get("date"),
                    "code": code,
                }
            )
            if len(items) >= 8:
                break
        return items

    return cached(f"report:insider:{symbol}", lambda: _safe(_fetch, []), ttl=86400)


def get_institutional_holdings(ticker: str) -> list[dict[str, Any]]:
    symbol = market_symbol(ticker)
    issuer = display_name(ticker)

    def _fetch() -> list[dict[str, Any]]:
        payload = sec_edgar.thirteen_f_holdings(symbol, issuer) or {}
        holders = payload.get("top_holders") or []
        items: list[dict[str, Any]] = []
        for row in holders[:5]:
            items.append(
                {
                    "fund_name": row.get("holder") or row.get("fund_name") or row.get("name") or "Institution",
                    "shares_held": row.get("shares") or row.get("shares_held"),
                    "position_value": row.get("value") or row.get("position_value"),
                    "change_vs_previous_quarter": row.get("change") or row.get("change_shares"),
                    "change_percentage": row.get("change_pct") or row.get("pct_change"),
                    "report_date": payload.get("latest_13f") or row.get("report_date"),
                }
            )
        return items

    return cached(f"report:inst:{symbol}", lambda: _safe(_fetch, []), ttl=604800)


def get_earnings_this_week(ticker: str) -> list[dict[str, Any]]:
    symbol = market_symbol(ticker)

    def _fetch() -> list[dict[str, Any]]:
        calendar = finnhub.earnings_calendar(symbol) or {}
        surprises = finnhub.earnings_surprises(symbol) or []
        date_value = calendar.get("next_earnings_date")
        days_away = calendar.get("days_away")
        items: list[dict[str, Any]] = []
        if date_value is not None and isinstance(days_away, int) and 0 <= days_away <= 14:
            prev = surprises[0] if surprises else {}
            items.append(
                {
                    "earnings_date": date_value,
                    "days_away": days_away,
                    "eps_estimate": calendar.get("eps_estimate"),
                    "previous_eps": prev.get("eps_actual"),
                    "revenue_estimate": calendar.get("revenue_estimate"),
                    "surprise_percentage": prev.get("surprise_pct"),
                    "time_of_day": calendar.get("time_of_day"),
                }
            )
        return items

    return cached(f"report:earn:{symbol}", lambda: _safe(_fetch, []), ttl=86400)


def fetch_all_data_sections(ticker: str) -> dict[str, Any]:
    """Fetch all five data sections in parallel with per-section TTLs."""
    with ThreadPoolExecutor(max_workers=5) as pool:
        fut_analyst = pool.submit(get_analyst_ratings, ticker)
        fut_news = pool.submit(get_important_news, ticker)
        fut_insider = pool.submit(get_insider_activity, ticker)
        fut_inst = pool.submit(get_institutional_holdings, ticker)
        fut_earn = pool.submit(get_earnings_this_week, ticker)
        analyst = fut_analyst.result()
        news = fut_news.result()
        insider = fut_insider.result()
        institutions = fut_inst.result()
        earnings = fut_earn.result()
    return {
        "analyst_ratings": analyst,
        "news": news,
        "insider": insider,
        "institutions": institutions,
        "earnings": earnings,
        "disclaimers": DISCLAIMERS,
        "empty_labels": {
            "analyst_ratings": "No recent activity" if not analyst else None,
            "news": "No recent activity" if not news else None,
            "insider": "No recent activity" if not insider else None,
            "institutions": "No recent activity" if not institutions else None,
            "earnings": "No recent activity" if not earnings else None,
        },
    }
