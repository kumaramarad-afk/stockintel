from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import CachedReport
from services.report_data import fetch_all_data_sections
from services.reasoning_report import generate_reasoning_report
from services.stock_service import TickerNotFoundError
from services.ticker_catalog import display_name

logger = logging.getLogger(__name__)

POPULAR_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "AVGO", "JPM",
    "LLY", "V", "UNH", "XOM", "MA", "COST", "HD", "PG", "JNJ", "ABBV",
    "NFLX", "CRM", "BAC", "AMD", "WMT", "KO", "PEP", "MRK", "ADBE", "TMO",
    "PLTR", "COIN", "SOFI", "RIVN", "NIO", "LCID", "HOOD", "GME", "AMC", "MSTR",
    "SMCI", "ARM", "UBER", "DIS", "BA", "INTC", "PYPL", "SQ", "SHOP", "SNOW",
]

CACHE_DAYS = 7
SECTION_HEADERS = [
    ("one_line", re.compile(r"^## The one-line version\s*$", re.I | re.M)),
    ("paying", re.compile(r"^## 1\. What you're paying\s*$", re.I | re.M)),
    ("bulls", re.compile(r"^## 2\. What the bulls are counting on\s*$", re.I | re.M)),
    ("bears", re.compile(r"^## 3\. What the bears see\s*$", re.I | re.M)),
    ("assumptions", re.compile(r"^## 4\. What would have to be true\s*$", re.I | re.M)),
    ("watch", re.compile(r"^## 5\. What to watch next\s*$", re.I | re.M)),
    ("non_verdict", re.compile(r"^## 6\. What this note does not do\s*$", re.I | re.M)),
]


def split_report_sections(markdown: str) -> dict[str, str]:
    text = (markdown or "").replace("\r\n", "\n")
    matches: list[tuple[str, int, int]] = []
    for key, pattern in SECTION_HEADERS:
        match = pattern.search(text)
        if match:
            matches.append((key, match.start(), match.end()))
    matches.sort(key=lambda item: item[1])
    sections: dict[str, str] = {key: "" for key, _ in SECTION_HEADERS}
    title = ""
    if matches:
        title = text[: matches[0][1]].strip()
    for index, (key, _start, end) in enumerate(matches):
        stop = matches[index + 1][1] if index + 1 < len(matches) else len(text)
        body = text[end:stop].strip()
        body = re.sub(r"^---\s*", "", body).strip()
        body = re.sub(r"\s*---\s*$", "", body).strip()
        sections[key] = body
    # Disclaimer is usually the trailing italic paragraph after section 6.
    disclaimer = ""
    if sections.get("non_verdict"):
        parts = re.split(r"\n---\n", sections["non_verdict"], maxsplit=1)
        if len(parts) == 2:
            sections["non_verdict"] = parts[0].strip()
            disclaimer = parts[1].strip()
    if not disclaimer:
        match = re.search(r"\n\*(Educational and informational purposes only[\s\S]*)$", text)
        if match:
            disclaimer = match.group(1).strip()
    sections["title"] = title
    sections["disclaimer"] = disclaimer
    return sections


def report_view_access(user: Any, db: Session | None = None) -> str:
    """full | preview — controls whether sections 2–5 are unlocked."""
    from services.newsletter_service import newsletter_access

    if user is None:
        return "preview"
    access = newsletter_access(user, db)
    if access == "full":
        return "full"
    if access == "preview":
        return "preview"
    # Day 16+ free users still get the public teaser (blur), not a hard block.
    return "preview"


def _row_to_dict(row: CachedReport) -> dict[str, Any]:
    valuation = None
    if row.valuation_json:
        try:
            valuation = json.loads(row.valuation_json)
        except json.JSONDecodeError:
            valuation = None
    return {
        "ticker": row.ticker,
        "name": row.name,
        "price": row.price,
        "as_of": row.as_of,
        "one_line": row.one_line,
        "markdown": row.markdown,
        "valuation": valuation,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "available": True,
        "error": None,
        "cached": True,
    }


def get_cached_report(db: Session, ticker: str) -> CachedReport | None:
    symbol = ticker.strip().upper()
    return db.scalar(select(CachedReport).where(CachedReport.ticker == symbol))


def list_cached_tickers(db: Session) -> list[dict[str, Any]]:
    """Merge the popular launch set with any cached rows so the directory stays complete."""
    rows = db.scalars(select(CachedReport).order_by(CachedReport.ticker.asc())).all()
    by_ticker = {
        row.ticker: {
            "ticker": row.ticker,
            "name": row.name or display_name(row.ticker),
            "one_line": row.one_line,
            "price": row.price,
            "as_of": row.as_of,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        }
        for row in rows
    }
    merged: list[dict[str, Any]] = []
    for symbol in POPULAR_TICKERS:
        if symbol in by_ticker:
            merged.append(by_ticker.pop(symbol))
        else:
            merged.append(
                {
                    "ticker": symbol,
                    "name": display_name(symbol),
                    "one_line": None,
                    "price": None,
                    "as_of": None,
                    "generated_at": None,
                }
            )
    # Any extra cached tickers outside the popular set.
    merged.extend(sorted(by_ticker.values(), key=lambda item: item["ticker"]))
    return merged


def upsert_cached_report(db: Session, payload: dict[str, Any], *, ttl_days: int = CACHE_DAYS) -> CachedReport:
    symbol = str(payload["ticker"]).upper()
    now = datetime.now(timezone.utc)
    row = get_cached_report(db, symbol)
    if row is None:
        row = CachedReport(ticker=symbol)
        db.add(row)
    row.name = payload.get("name")
    row.price = payload.get("price")
    row.as_of = payload.get("as_of")
    row.one_line = payload.get("one_line")
    row.markdown = payload.get("markdown") or ""
    valuation = payload.get("valuation")
    row.valuation_json = json.dumps(valuation) if valuation is not None else None
    row.generated_at = now
    row.refreshed_at = now
    row.expires_at = now + timedelta(days=ttl_days)
    db.flush()
    return row


def generate_and_cache(ticker: str, db: Session | None = None) -> dict[str, Any]:
    owned = db is None
    session = db or SessionLocal()
    try:
        payload = generate_reasoning_report(ticker)
        upsert_cached_report(session, payload)
        session.commit()
        return payload
    finally:
        if owned:
            session.close()


def get_or_generate_report(db: Session, ticker: str, *, force: bool = False) -> dict[str, Any]:
    symbol = ticker.strip().upper()
    row = get_cached_report(db, symbol)
    now = datetime.now(timezone.utc)
    if row is not None and not force:
        expires = row.expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires is None or expires >= now:
            return _row_to_dict(row)
    try:
        return generate_and_cache(symbol, db)
    except TickerNotFoundError:
        raise
    except Exception:
        logger.exception("Failed to generate cached report for %s", symbol)
        if row is not None:
            return _row_to_dict(row)
        raise


def public_report_payload(db: Session, ticker: str, user: Any) -> dict[str, Any]:
    raw = get_or_generate_report(db, ticker)
    sections = split_report_sections(str(raw.get("markdown") or ""))
    if not sections.get("one_line") and raw.get("one_line"):
        sections["one_line"] = str(raw["one_line"])
    access = report_view_access(user, db)
    locked = access != "full"
    visible = {
        "title": sections.get("title") or "",
        "one_line": sections.get("one_line") or raw.get("one_line") or "",
        "paying": sections.get("paying") or "",
        "bulls": "" if locked else sections.get("bulls") or "",
        "bears": "" if locked else sections.get("bears") or "",
        "assumptions": "" if locked else sections.get("assumptions") or "",
        "watch": "" if locked else sections.get("watch") or "",
        "non_verdict": sections.get("non_verdict") or "",
        "disclaimer": sections.get("disclaimer") or "",
    }
    # Keep blurred stubs so the UI can render overlay placeholders with length cues.
    blurred = {
        "bulls": sections.get("bulls") or "",
        "bears": sections.get("bears") or "",
        "assumptions": sections.get("assumptions") or "",
        "watch": sections.get("watch") or "",
    } if locked else None
    valuation = dict(raw.get("valuation") or {})
    if locked:
        for key in ("average_target", "high_target", "low_target"):
            if key in valuation:
                valuation[key] = "$$$.$$"
    data_sections = fetch_all_data_sections(ticker)
    return {
        "ticker": raw["ticker"],
        "name": raw.get("name"),
        "price": raw.get("price"),
        "as_of": raw.get("as_of"),
        "one_line": visible["one_line"],
        "markdown": raw.get("markdown") if not locked else None,
        "sections": visible,
        "blurred_sections": blurred,
        "data_sections": data_sections,
        "valuation": valuation,
        "locked_sections": ["bulls", "bears", "assumptions", "watch"] if locked else [],
        "view_access": access,
        "preview": locked,
        "generated_at": raw.get("generated_at"),
        "available": True,
        "error": None,
        "cached": bool(raw.get("cached")),
    }


def refresh_popular_reports(tickers: list[str] | None = None, max_workers: int = 3) -> dict[str, Any]:
    symbols = [item.strip().upper() for item in (tickers or POPULAR_TICKERS) if item.strip()]
    ok: list[str] = []
    failed: list[dict[str, str]] = []

    def _one(symbol: str) -> tuple[str, str | None]:
        try:
            generate_and_cache(symbol)
            return symbol, None
        except Exception as exc:
            logger.exception("Refresh failed for %s", symbol)
            return symbol, str(exc)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_one, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            symbol, error = future.result()
            if error:
                failed.append({"ticker": symbol, "error": error})
            else:
                ok.append(symbol)
    return {
        "status": "success",
        "generated": len(ok),
        "failed": failed,
        "tickers": sorted(ok),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
