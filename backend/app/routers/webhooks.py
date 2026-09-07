from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import User
from services import stripe_billing

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


def _set_plan(user: User, plan: str, customer: str | None = None, subscription: str | None = None) -> None:
    user.plan = plan
    if plan == "pro":
        user.subscribed_at = datetime.now(timezone.utc)
        if customer:
            user.stripe_customer_id = customer
        if subscription:
            user.stripe_subscription_id = subscription
    else:
        user.subscribed_at = None
        user.stripe_subscription_id = None


@router.post("/api/webhooks/stripe")
@router.post("/api/v1/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(db_session)) -> dict[str, bool]:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        event = stripe_billing.parse_webhook(payload, signature)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook") from exc
    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}
    user: User | None = None
    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id") or obj.get("client_reference_id")
    if user_id:
        try:
            user = db.get(User, UUID(str(user_id)))
        except ValueError:
            user = None
    customer_id = obj.get("customer")
    subscription_id = obj.get("subscription") or (obj.get("id") if event_type and str(event_type).startswith("customer.subscription") else None)
    if user is None and customer_id:
        user = db.scalar(select(User).where(User.stripe_customer_id == str(customer_id)))
    if user is None and subscription_id:
        user = db.scalar(select(User).where(User.stripe_subscription_id == str(subscription_id)))
    if event_type == "checkout.session.completed":
        if user is not None:
            _set_plan(user, "pro", str(customer_id or ""), str(subscription_id or ""))
            db.add(user)
            db.commit()
    elif event_type in {"customer.subscription.deleted", "customer.subscription.paused"}:
        if user is not None:
            _set_plan(user, "free")
            db.add(user)
            db.commit()
    elif event_type == "customer.subscription.updated":
        status = str(obj.get("status") or "")
        if user is not None:
            if status in {"canceled", "unpaid", "incomplete_expired", "paused"}:
                _set_plan(user, "free")
            elif status in {"active", "trialing"}:
                _set_plan(user, "pro", str(customer_id or ""), str(obj.get("id") or subscription_id or ""))
            db.add(user)
            db.commit()
    else:
        logger.info("Ignored Stripe event %s", event_type)
    return {"ok": True}
