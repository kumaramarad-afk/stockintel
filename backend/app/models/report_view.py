from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database import Base


class ReportView(Base):
    __tablename__ = "report_views"
    __table_args__ = (UniqueConstraint("user_id", "ticker", "period", name="uq_report_views_user_ticker_period"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="report_views")


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_alert_events_user_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
