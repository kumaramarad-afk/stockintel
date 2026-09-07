import uuid
from datetime import datetime

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


class SubscribeRequest(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    newsletter_slug: str = Field(min_length=1, max_length=128)


class SubscribeResponse(BaseModel):
    subscriber_id: uuid.UUID
    newsletter_id: uuid.UUID
    email: EmailStr
    message: str
