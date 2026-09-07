import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StockCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=255)
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str = "USD"
    description: str | None = None


class PriceSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    price: Decimal
    change_percent: Decimal | None
    volume: int | None
    market_cap: int | None
    as_of: datetime


class StockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticker: str
    name: str
    exchange: str | None
    sector: str | None
    industry: str | None
    currency: str
    description: str | None
    latest_price: PriceSnapshotRead | None = None
