import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchNoteCreate(BaseModel):
    stock_id: uuid.UUID | None = None
    author_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    body: str = Field(min_length=1)
    rating: str | None = Field(default=None, max_length=16)
    target_price: Decimal | None = None


class ResearchNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_id: uuid.UUID | None
    author_id: uuid.UUID
    title: str
    summary: str | None
    body: str
    rating: str | None
    target_price: Decimal | None
    published_at: datetime | None
    created_at: datetime
    ticker: str | None = None


class ResearchGenerateRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,15}", ticker):
            raise ValueError("Enter a valid ticker symbol, such as AAPL or BRK.B")
        return ticker


class CurrentPriceData(BaseModel):
    price: float | None = None
    change_percent: float | None = None
    currency: str = "USD"
    previous_close: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: int | None = None
    as_of: str | None = None


class AnalystRatingsData(BaseModel):
    consensus: str | None = None
    target_mean: float | None = None
    target_high: float | None = None
    target_low: float | None = None
    number_of_analysts: int | None = None
    distribution: dict[str, int] | None = None


class BasicFinancialsData(BaseModel):
    pe_ratio: float | None = None
    market_cap: float | None = None
    revenue: float | None = None
    eps: float | None = None
    profit_margin: float | None = None
    source: str | None = None


class ResearchGenerateResponse(BaseModel):
    ticker: str
    name: str | None = None
    current_price: CurrentPriceData
    analyst_ratings: AnalystRatingsData
    financials: BasicFinancialsData
    report: str


class ResearchSectionResponse(BaseModel):
    ticker: str
    available: bool = True
    error: str | None = None
    data: dict | None = None
    access: dict | None = None
