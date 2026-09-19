"""Public ticker / company-name search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import Stock
from services.ticker_catalog import TICKER_NAMES, search_tickers

router = APIRouter(prefix="/search", tags=["search"])


class SearchResult(BaseModel):
    ticker: str
    company_name: str


@router.get("", response_model=list[SearchResult])
def search(
    q: str = Query("", max_length=64),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(db_session),
) -> list[SearchResult]:
    """Search by ticker or company name (exact → prefix → substring), case-insensitive."""
    needle = (q or "").strip()
    fetch_limit = max(limit, len(TICKER_NAMES)) if not needle else limit

    ranked = search_tickers(needle, limit=100 if not needle else limit)
    db_names: dict[str, str] = {}
    try:
        rows = db.scalars(select(Stock).order_by(Stock.ticker.asc())).all()
        db_names = {row.ticker.upper(): row.name for row in rows}
    except Exception:
        db_names = {}

    results: list[SearchResult] = []
    seen: set[str] = set()
    for hit in ranked:
        ticker = hit["ticker"]
        if ticker in seen:
            continue
        seen.add(ticker)
        results.append(
            SearchResult(
                ticker=ticker,
                company_name=db_names.get(ticker) or hit.get("company_name") or hit.get("name") or ticker,
            )
        )
        if needle and len(results) >= limit:
            break

    if needle and db_names and len(results) < limit:
        upper = needle.upper()
        extras = db.scalars(
            select(Stock)
            .where(
                or_(
                    Stock.ticker.ilike(f"{upper}%"),
                    Stock.name.ilike(needle),
                    Stock.name.ilike(f"%{needle}%"),
                )
            )
            .order_by(Stock.ticker.asc())
            .limit(limit)
        ).all()
        for row in extras:
            ticker = row.ticker.upper()
            if ticker in seen:
                continue
            seen.add(ticker)
            results.append(SearchResult(ticker=ticker, company_name=row.name))
            if len(results) >= limit:
                break

    return results[:fetch_limit]
