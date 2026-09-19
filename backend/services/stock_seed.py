"""Seed / refresh company names on the stocks table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Stock
from services.ticker_catalog import TICKER_NAMES, TICKER_SECTORS


def upsert_company_names(db: Session | None = None) -> dict[str, int]:
    owned = db is None
    session = db
    if session is None:
        from app.database import SessionLocal

        session = SessionLocal()
    created = 0
    updated = 0
    try:
        for ticker, name in TICKER_NAMES.items():
            row = session.scalar(select(Stock).where(Stock.ticker == ticker))
            sector = TICKER_SECTORS.get(ticker)
            if row is None:
                session.add(Stock(ticker=ticker, name=name, sector=sector, currency="USD"))
                created += 1
            else:
                changed = False
                if row.name != name:
                    row.name = name
                    changed = True
                if sector and row.sector != sector:
                    row.sector = sector
                    changed = True
                if changed:
                    updated += 1
        session.commit()
    finally:
        if owned:
            session.close()
    return {"created": created, "updated": updated, "total": len(TICKER_NAMES)}
