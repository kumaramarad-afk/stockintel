from __future__ import annotations

import logging
from typing import Any

import httpx

from services.cache import cached
from services.keys import alpha_vantage_key
from services.numbers import pct_change, to_float

logger = logging.getLogger(__name__)
BASE = "https://www.alphavantage.co/query"


def _get(function: str, ticker: str) -> dict[str, Any] | None:
    key = alpha_vantage_key()
    if not key:
        return None

    def _fetch() -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(BASE, params={"function": function, "symbol": ticker, "apikey": key})
                response.raise_for_status()
                payload = response.json()
            if not isinstance(payload, dict) or "Note" in payload or "Information" in payload or "Error Message" in payload:
                logger.warning("Alpha Vantage %s unavailable for %s", function, ticker)
                return None
            return payload
        except Exception:
            logger.exception("Alpha Vantage %s failed for %s", function, ticker)
            return None

    return cached(f"av:{function}:{ticker}", _fetch, ttl=300)


def overview(ticker: str) -> dict[str, Any] | None:
    payload = _get("OVERVIEW", ticker)
    if not payload or not payload.get("Symbol"):
        return None
    return {
        "pe_ratio": to_float(payload.get("PERatio") or payload.get("TrailingPE")),
        "peg_ratio": to_float(payload.get("PEGRatio")),
        "price_to_sales": to_float(payload.get("PriceToSalesRatioTTM")),
        "price_to_book": to_float(payload.get("PriceToBookRatio")),
        "ev_ebitda": to_float(payload.get("EVToEBITDA")),
        "profit_margin": to_float(payload.get("ProfitMargin")),
        "operating_margin": to_float(payload.get("OperatingMarginTTM")),
        "gross_margin": to_float(payload.get("GrossProfitTTM")),
        "return_on_equity": to_float(payload.get("ReturnOnEquityTTM")),
        "eps": to_float(payload.get("EPS")),
        "revenue_ttm": to_float(payload.get("RevenueTTM")),
        "market_cap": to_float(payload.get("MarketCapitalization")),
        "sector": payload.get("Sector"),
        "dividend_yield": to_float(payload.get("DividendYield")),
        "payout_ratio": to_float(payload.get("PayoutRatio")),
        "dividend_date": payload.get("DividendDate"),
        "ex_dividend_date": payload.get("ExDividendDate"),
        "analyst_target": to_float(payload.get("AnalystTargetPrice")),
        "beta": to_float(payload.get("Beta")),
    }


def earnings(ticker: str) -> dict[str, Any] | None:
    payload = _get("EARNINGS", ticker)
    if not payload:
        return None
    quarterly = payload.get("quarterlyEarnings") or []
    rows = []
    streak = 0
    counting = True
    for item in quarterly[:8]:
        est = to_float(item.get("estimatedEPS"))
        actual = to_float(item.get("reportedEPS"))
        beat = None if actual is None or est is None else actual >= est
        if counting:
            if beat is True:
                streak += 1
            else:
                counting = False
        rows.append(
            {
                "quarter": item.get("fiscalDateEnding") or item.get("reportedDate"),
                "eps_estimate": est,
                "eps_actual": actual,
                "beat": beat,
                "surprise_pct": to_float(item.get("surprisePercentage")),
            }
        )
    return {"eps_quarters": rows, "beat_streak": streak}


def income(ticker: str) -> dict[str, Any] | None:
    payload = _get("INCOME_STATEMENT", ticker)
    if not payload:
        return None
    reports = payload.get("quarterlyReports") or []
    quarters = []
    values: list[float | None] = []
    for item in reports[:4]:
        revenue = to_float(item.get("totalRevenue"))
        values.append(revenue)
        quarters.append({"period": item.get("fiscalDateEnding"), "revenue": revenue, "growth_pct": None})
    for idx, row in enumerate(quarters):
        nxt = values[idx + 1] if idx + 1 < len(values) else None
        row["growth_pct"] = pct_change(row["revenue"], nxt)
    growths = [q["growth_pct"] for q in quarters if q.get("growth_pct") is not None]
    accelerating = bool(len(growths) >= 2 and growths[0] is not None and growths[-1] is not None and growths[0] > growths[-1])
    latest = reports[0] if reports else {}
    return {
        "revenue_quarters": quarters,
        "revenue_acceleration": accelerating if growths else None,
        "gross_profit": to_float(latest.get("grossProfit")),
        "operating_income": to_float(latest.get("operatingIncome")),
    }
