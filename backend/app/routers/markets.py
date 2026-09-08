from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from services.cache import cached
from services.providers import yahoo_http

router = APIRouter(prefix="/markets", tags=["markets"])

INDEX_NAMES = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones",
}

DEFAULT_SYMBOLS = ["^GSPC", "^IXIC", "^DJI", "AAPL", "NVDA", "MSFT"]


class MarketQuote(BaseModel):
    symbol: str
    name: str
    price: float | None = None
    previous_close: float | None = None
    change_percent: float | None = None


@router.get("/quotes", response_model=list[MarketQuote])
def market_quotes(symbols: str | None = Query(default=None)) -> list[MarketQuote]:
    requested = [item.strip() for item in (symbols or ",".join(DEFAULT_SYMBOLS)).split(",") if item.strip()]
    quotes: list[MarketQuote] = []
    for symbol in requested[:12]:
        payload = cached(f"market-quote:{symbol}", lambda ticker=symbol: yahoo_http.spark_quote(ticker), ttl=45.0)
        quotes.append(
            MarketQuote(
                symbol=payload.get("symbol") or symbol,
                name=INDEX_NAMES.get(symbol) or INDEX_NAMES.get(symbol.upper()) or payload.get("name") or symbol,
                price=payload.get("price"),
                previous_close=payload.get("previous_close"),
                change_percent=payload.get("change_percent"),
            )
        )
    return quotes
