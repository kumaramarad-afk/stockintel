from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import stripe

from app.config import settings

logger = logging.getLogger(__name__)

PRO_PRODUCT_NAME = "GetStockReport Pro"


def _configure() -> None:
    if not settings.stripe_secret_key:
        raise RuntimeError("Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key


def create_checkout_session(user_id: UUID, email: str, success_url: str, cancel_url: str) -> str:
    _configure()
    line_item: dict[str, Any]
    if settings.stripe_price_id:
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
        metadata={"user_id": str(user_id)},
        subscription_data={"metadata": {"user_id": str(user_id)}},
        line_items=[line_item],
        allow_promotion_codes=True,
    )
    if not session.url:
        raise RuntimeError("Stripe did not return a checkout URL")
    return session.url


def parse_webhook(payload: bytes, signature: str | None) -> dict[str, Any]:
    if settings.stripe_webhook_secret:
        if not signature:
            raise RuntimeError("Missing Stripe signature")
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
        return dict(event)
    import json

    return json.loads(payload.decode("utf-8"))
