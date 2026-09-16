from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from services.cache import cached
from services.keys import newsapi_key

logger = logging.getLogger(__name__)
BASE = "https://newsapi.org/v2"
TICKER_WATCH = [
    "GOOGL", "AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "META", "TSLA", "AMD",
    "NFLX", "AVGO", "ORCL", "INTC", "QCOM", "CRM", "JPM", "BAC", "GS",
    "XOM", "UNH", "JNJ", "WMT", "COST", "HD", "PG", "KO", "PEP", "DIS",
    "BA", "GE", "CAT", "NKE", "V", "MA", "SPY", "QQQ", "IWM", "DIA",
]
_TICKER_RE = re.compile(
    r"(?:\$|(?<![A-Za-z]))(" + "|".join(sorted(set(TICKER_WATCH), key=len, reverse=True)) + r")\b"
)


def _two_sentences(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").replace("\u00a0", " ")).strip()
    cleaned = re.sub(r"\[\+\d+ chars\]\s*$", "", cleaned).strip()
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return " ".join(parts[:2])[:420]


def extract_ticker(*texts: str) -> str:
    blob = " ".join(part for part in texts if part)
    match = _TICKER_RE.search(blob)
    return match.group(1).upper() if match else "MARKET"


def _normalize(article: dict[str, Any]) -> dict[str, Any] | None:
    headline = str(article.get("title") or "").strip()
    url = str(article.get("url") or "").strip()
    if not headline or not url.startswith(("http://", "https://")):
        return None
    source = article.get("source")
    if isinstance(source, dict):
        source_name = str(source.get("name") or "NewsAPI").strip() or "NewsAPI"
    else:
        source_name = str(source or article.get("source_name") or "NewsAPI").strip() or "NewsAPI"
    body = str(article.get("description") or article.get("content") or "").strip()
    summary = _two_sentences(body)
    if summary and summary.lower() == _two_sentences(headline).lower():
        summary = ""
    return {
        "ticker": extract_ticker(headline, str(article.get("description") or "")),
        "headline": headline,
        "summary": summary,
        "source": source_name,
        "url": url,
        "published_at": article.get("publishedAt"),
    }


def _fetch(path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    token = newsapi_key()
    if not token:
        return []

    def _load() -> list[dict[str, Any]]:
        query = {**params, "apiKey": token, "language": "en", "pageSize": 20}
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(f"{BASE}{path}", params=query)
            if response.status_code >= 400:
                logger.warning("NewsAPI %s status %s", path, response.status_code)
                return []
            payload = response.json()
        except Exception:
            logger.exception("NewsAPI %s failed", path)
            return []
        rows = payload.get("articles") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return []
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = _normalize(row)
            if item is None or item["url"] in seen:
                continue
            seen.add(item["url"])
            items.append(item)
        return items

    return cached(f"newsapi:{path}:{sorted(params.items())}", _load, ttl=180)


def market_headlines(limit: int = 12) -> list[dict[str, Any]]:
    headlines = _fetch("/top-headlines", {"country": "us", "category": "business"})
    if len(headlines) < limit:
        extra = _fetch(
            "/everything",
            {
                "q": 'stocks OR Nasdaq OR "S&P 500" OR earnings OR Wall Street',
                "sortBy": "publishedAt",
            },
        )
        seen = {item["url"] for item in headlines}
        for item in extra:
            if item["url"] in seen:
                continue
            headlines.append(item)
            seen.add(item["url"])
            if len(headlines) >= max(limit, 12):
                break
    return headlines[: max(limit, 12)]
