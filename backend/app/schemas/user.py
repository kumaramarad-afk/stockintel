import uuid
from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_admin: bool
    plan: str = "free"
    complimentary: bool = False
    subscribed_at: datetime | None
    created_at: datetime
    reports_generated: int = 0
    reports_used: int = 0
    reports_limit: int = 5
    reports_remaining: int = 5
    oauth_provider: str | None = None
    newsletter_subscription_status: str = "none"
    newsletter_email_preference: str = "daily"
    newsletter_subscribed_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class SubscribePlanRequest(BaseModel):
    plan: Literal["pro", "free", "newsletter_pro", "premium"] = "premium"
