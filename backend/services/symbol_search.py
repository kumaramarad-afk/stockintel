"""Unified ticker / company search across catalog + live US market sources."""

from __future__ import annotations

import logging
import re
from typing import Any

from services.providers import finnhub, sec_edgar, yahoo_http
from services.ticker_catalog import TICKER_NAMES, search_tickers

logger = logging.getLogger(__name__)
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,15}$")


def _norm(row: dict[str, Any]) -> dict[str, str] | None:
    ticker = str(row.get("ticker") or "").upper().strip()
    if not ticker or not TICKER_RE.fullmatch(ticker):
        return None
    # Keep dotted share classes only when we already know them (e.g. BRK.B).
    # Foreign suffixes like EUCA.F / SNDK.TO must not leak in from secondary sources.
    if "." in ticker and ticker not in TICKER_NAMES:
        return None
    name = str(row.get("company_name") or row.get("name") or TICKER_NAMES.get(ticker) or ticker)
    return {"ticker": ticker, "company_name": name, "name": name}


def search_us_symbols(query: str, *, limit: int = 10) -> list[dict[str, str]]:
    """Ranked search: curated catalog first, then Yahoo, Finnhub, and SEC issuer map."""
    needle = (query or "").strip()
    if not needle:
        return search_tickers("", limit=max(limit, len(TICKER_NAMES)))

    merged: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_rows(rows: list[dict[str, Any]] | list[dict[str, str]]) -> None:
        for row in rows:
            item = _norm(row)
            if not item or item["ticker"] in seen:
                continue
            seen.add(item["ticker"])
            merged.append(item)
            if len(merged) >= limit:
                return

    # 1) Curated popular set + aliases (instant, offline)
    add_rows(search_tickers(needle, limit=limit))
    if len(merged) >= limit:
        return merged[:limit]

    # 2) Live Yahoo US equity/ETF search (covers Micron, SanDisk, etc.)
    try:
        add_rows(yahoo_http.symbol_search(needle, limit=limit))
    except Exception:
        logger.exception("Yahoo symbol search failed for %s", needle)
    if len(merged) >= limit:
        return merged[:limit]

    # 3) Finnhub search
    try:
        add_rows(finnhub.symbol_search(needle, limit=limit))
    except Exception:
        logger.exception("Finnhub symbol search failed for %s", needle)
    if len(merged) >= limit:
        return merged[:limit]

    # 4) SEC company_tickers.json substring match (~10k US issuers)
    try:
        add_rows(sec_edgar.search_company_tickers(needle, limit=limit))
    except Exception:
        logger.exception("SEC ticker search failed for %s", needle)

    return merged[:limit]
