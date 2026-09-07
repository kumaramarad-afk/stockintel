import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Newsletter(Base):
    __tablename__ = "newsletters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    issues = relationship("NewsletterIssue", back_populates="newsletter", cascade="all, delete-orphan")
    subscriptions = relationship("NewsletterSubscription", back_populates="newsletter")


class NewsletterIssue(Base):
    __tablename__ = "newsletter_issues"
    __table_args__ = (UniqueConstraint("newsletter_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    newsletter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("newsletters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    newsletter = relationship("Newsletter", back_populates="issues")


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscriptions = relationship("NewsletterSubscription", back_populates="subscriber")


class NewsletterSubscription(Base):
    __tablename__ = "newsletter_subscriptions"
    __table_args__ = (UniqueConstraint("newsletter_id", "subscriber_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    newsletter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("newsletters.id", ondelete="CASCADE"), nullable=False
    )
    subscriber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscribers.id", ondelete="CASCADE"), nullable=False
    )
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    newsletter = relationship("Newsletter", back_populates="subscriptions")
    subscriber = relationship("Subscriber", back_populates="subscriptions")
