import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistCreate(BaseModel):
    user_id: uuid.UUID
    name: str = Field(min_length=1, max_length=128)


class WatchlistItemCreate(BaseModel):
    stock_id: uuid.UUID
    notes: str | None = None


class WatchlistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_id: uuid.UUID
    notes: str | None
    added_at: datetime
    ticker: str | None = None
    name: str | None = None


class WatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    created_at: datetime
    items: list[WatchlistItemRead] = []
