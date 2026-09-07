import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(32))
    sector: Mapped[str | None] = mapped_column(String(128))
    industry: Mapped[str | None] = mapped_column(String(128))
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    prices = relationship("PriceSnapshot", back_populates="stock", cascade="all, delete-orphan")
    research_notes = relationship("ResearchNote", back_populates="stock")
    watchlist_items = relationship("WatchlistItem", back_populates="stock")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    change_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    market_cap: Mapped[int | None] = mapped_column(BigInteger)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    stock = relationship("Stock", back_populates="prices")
