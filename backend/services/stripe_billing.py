from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import stripe

from app.config import settings

logger = logging.getLogger(__name__)

PRO_PRODUCT_NAME = "GetStockReport Pro"
NEWSLETTER_PRODUCT_NAME = "GetStockReport Newsletter Pro"
PAID_PLANS = frozenset({"pro", "newsletter_pro"})


def _configure() -> None:
    if not settings.stripe_secret_key:
        raise RuntimeError("Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key


def normalize_plan(plan: str | None) -> str:
    value = (plan or "pro").strip().lower()
    return value if value in PAID_PLANS else "pro"


def create_checkout_session(
    user_id: UUID,
    email: str,
    success_url: str,
    cancel_url: str,
    plan: str = "pro",
) -> str:
    _configure()
    selected = normalize_plan(plan)
    line_item: dict[str, Any]
    if selected == "newsletter_pro":
        if settings.stripe_newsletter_price_id:
            line_item = {"price": settings.stripe_newsletter_price_id, "quantity": 1}
        else:
            line_item = {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": settings.newsletter_price_cents,
                    "recurring": {"interval": "month"},
                    "product_data": {
                        "name": NEWSLETTER_PRODUCT_NAME,
                        "description": "Daily market briefing plus unlimited research reports",
                    },
                },
                "quantity": 1,
            }
    elif settings.stripe_price_id:
        line_item = {"price": settings.stripe_price_id, "quantity": 1}
    else:
        line_item = {
            "price_data": {
                "currency": "usd",
                "unit_amount": settings.pro_price_cents,
                "recurring": {"interval": "month"},
                "product_data": {"name": PRO_PRODUCT_NAME, "description": "Full analyst briefings and real-time alerts"},
            },
            "quantity": 1,
        }
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        client_reference_id=str(user_id),
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user_id), "plan": selected},
        subscription_data={"metadata": {"user_id": str(user_id), "plan": selected}},
        line_items=[line_item],
        allow_promotion_codes=True,
    )
    if not session.url:
        raise RuntimeError("Stripe did not return a checkout URL")
    return session.url


def create_portal_session(customer_id: str, return_url: str) -> str:
    _configure()
    if not customer_id:
        raise RuntimeError("This account has no Stripe customer")
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    if not session.url:
        raise RuntimeError("Stripe did not return a billing portal URL")
    return session.url


def stripe_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, dict):
        return stripe_id(value.get("id"))
    return stripe_id(getattr(value, "id", None))


def checkout_plan(session: dict[str, Any]) -> str:
    metadata = session.get("metadata") or {}
    raw = str(metadata.get("plan") or "").strip().lower()
    if raw in PAID_PLANS:
        return raw
    subscription = session.get("subscription")
    if isinstance(subscription, dict):
        sub_plan = str((subscription.get("metadata") or {}).get("plan") or "").strip().lower()
        if sub_plan in PAID_PLANS:
            return sub_plan
    return "pro"


def checkout_user_id(session: dict[str, Any]) -> str | None:
    metadata = session.get("metadata") or {}
    return stripe_id(metadata.get("user_id")) or stripe_id(session.get("client_reference_id"))


def checkout_is_paid(session: dict[str, Any]) -> bool:
    status = str(session.get("status") or "").lower()
    payment = str(session.get("payment_status") or "").lower()
    if payment == "unpaid" or status in {"expired", "open"}:
        return False
    if payment in {"paid", "no_payment_required"} or status == "complete":
        return True
    return not payment and not status


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    to_dict = getattr(value, "to_dict_recursive", None) or getattr(value, "to_dict", None)
    if callable(to_dict):
        payload = to_dict()
        if isinstance(payload, dict):
            return payload
    try:
        return dict(value)
    except Exception:
        return {}


def retrieve_checkout_session(session_id: str) -> dict[str, Any]:
    _configure()
    session = stripe.checkout.Session.retrieve(session_id, expand=["subscription", "customer"])
    return as_dict(session)


def find_paid_checkout_session(user_id: str, email: str, session_id: str | None = None) -> dict[str, Any]:
    _configure()
    if session_id:
        session = retrieve_checkout_session(session_id)
        if not checkout_is_paid(session):
            raise RuntimeError("Checkout is not paid yet")
        if not session_belongs_to_user(session, user_id, email):
            raise RuntimeError("Checkout session does not belong to this account")
        return session
    customers = stripe.Customer.list(email=email, limit=10)
    for customer in customers.data:
        listed = stripe.checkout.Session.list(customer=stripe_id(customer), limit=10)
        for session in listed.data:
            payload = as_dict(session)
            if checkout_is_paid(payload) and session_belongs_to_user(payload, user_id, email):
                return payload
    raise RuntimeError("No paid checkout session found yet")


def session_belongs_to_user(session: dict[str, Any], user_id: str, email: str) -> bool:
    owner = checkout_user_id(session)
    if owner and owner == str(user_id):
        return True
    details = session.get("customer_details") or {}
    session_email = str(details.get("email") or session.get("customer_email") or "").strip().lower()
    return bool(session_email) and session_email == email.strip().lower()


def parse_webhook(payload: bytes, signature: str | None) -> dict[str, Any]:
    if settings.stripe_webhook_secret:
        if not signature:
            raise RuntimeError("Missing Stripe signature")
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
        return dict(event)
    import json

    return json.loads(payload.decode("utf-8"))
