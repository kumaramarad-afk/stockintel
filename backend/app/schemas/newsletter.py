import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class NewsletterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_active: bool


class NewsletterIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    newsletter_id: uuid.UUID
    title: str
    slug: str
    excerpt: str | None
    body: str
    published_at: datetime | None
    created_at: datetime
    ticker: str | None = None


class SubscribeRequest(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    newsletter_slug: str = Field(min_length=1, max_length=128)


class SubscribeResponse(BaseModel):
    subscriber_id: uuid.UUID
    newsletter_id: uuid.UUID
    email: EmailStr
    message: str


class NewsletterStatusRead(BaseModel):
    tier: str
    status: str
    newsletter_enabled: bool
    subscribed_at: datetime | None = None
    newsletter_emails_received: int = 0
    email_preference: str = "daily"


class EmailPreferenceRequest(BaseModel):
    preference: str = Field(min_length=2, max_length=20)


class NewsletterArchiveItem(BaseModel):
    date: str
    ticker: str
    reason: str
    sentiment: str
    issue_id: uuid.UUID | None = None
    research_path: str


class NewsletterTodayRead(BaseModel):
    date: str | None = None
    ticker: str | None = None
    reason: str | None = None
    sentiment: str | None = None
    research_path: str | None = None
    issue_id: uuid.UUID | None = None
    full_access: bool = False
    movers: list[dict[str, Any]] = Field(default_factory=list)
    earnings: list[dict[str, Any]] = Field(default_factory=list)
    macro: dict[str, Any] = Field(default_factory=dict)
    html: str | None = None
