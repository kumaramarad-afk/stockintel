from html import escape
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.config import settings
from services.newsletter_service import _send_html_email

router = APIRouter(prefix="/contact", tags=["contact"])

TOPICS = {
    "billing": "Billing & subscriptions",
    "research": "Research desk",
    "newsletter": "Daily briefing",
    "account": "Account access",
    "other": "General inquiry",
}


class ContactRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    topic: Literal["billing", "research", "newsletter", "account", "other"] = "other"
    message: str = Field(min_length=20, max_length=4000)
    company: str = Field(default="", max_length=120)


class ContactResponse(BaseModel):
    status: str
    message: str


def _compose(payload: ContactRequest) -> tuple[str, str, str]:
    topic = TOPICS.get(payload.topic, TOPICS["other"])
    subject = f"[Contact] {topic} — {payload.full_name.strip()}"
    body = payload.message.strip()
    text = (
        f"Name: {payload.full_name.strip()}\n"
        f"Email: {payload.email}\n"
        f"Topic: {topic}\n\n"
        f"{body}\n"
    )
    html = (
        "<html><body style='font-family:Arial,sans-serif;color:#0f172a'>"
        "<h2>New GetStockReport inquiry</h2>"
        f"<p><strong>Name:</strong> {escape(payload.full_name.strip())}<br>"
        f"<strong>Email:</strong> {escape(str(payload.email))}<br>"
        f"<strong>Topic:</strong> {escape(topic)}</p>"
        f"<p>{escape(body).replace(chr(10), '<br>')}</p>"
        "<p style='font-size:12px;color:#64748b'>Reply directly to this email to reach the sender.</p>"
        "</body></html>"
    )
    return subject, html, text


@router.post("", response_model=ContactResponse)
def submit_contact(payload: ContactRequest) -> ContactResponse:
    if payload.company.strip():
        return ContactResponse(status="received", message="Thanks. We received your message.")
    dest = settings.contact_to_email or "support@getstockreport.com"
    subject, html, text = _compose(payload)
    delivered = _send_html_email(
        dest,
        subject,
        html,
        text=text,
        reply_to=str(payload.email),
        reply_name=payload.full_name.strip(),
    )
    if not delivered:
        raise HTTPException(
            status_code=503,
            detail="Could not send your message right now. Email support@getstockreport.com directly.",
        )
    return ContactResponse(
        status="received",
        message="Thanks. We received your message and will reply from support@getstockreport.com.",
    )
