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

PRO_PLAN = "premium"
NEWSLETTER_PLAN = "premium"
FREE_PLAN = "free"
PAID_PLANS = frozenset({"pro", "newsletter_pro", "premium"})


def activate_plan(user: User, plan: str, customer: str | None = None, subscription: str | None = None) -> None:
    selected = "premium" if plan in PAID_PLANS else PRO_PLAN
    user.plan = selected
    user.subscribed_at = datetime.now(timezone.utc)
    if customer:
        user.stripe_customer_id = customer
    if subscription:
        user.stripe_subscription_id = subscription
    user.newsletter_subscription_status = "active"
    if (user.newsletter_email_preference or "off") == "off":
        user.newsletter_email_preference = "daily"
    if user.newsletter_subscribed_at is None:
        user.newsletter_subscribed_at = datetime.now(timezone.utc)


def activate_pro(user: User, customer: str | None = None, subscription: str | None = None) -> None:
    activate_plan(user, PRO_PLAN, customer, subscription)


def _set_plan(user: User, plan: str, customer: str | None = None, subscription: str | None = None) -> None:
    if plan in PAID_PLANS:
        activate_plan(user, plan, customer, subscription)
        return
    user.plan = FREE_PLAN
    user.subscribed_at = None
    user.stripe_subscription_id = None
    if (user.newsletter_subscription_status or "none") == "active":
        user.newsletter_subscription_status = "cancelled"


def _user_from_session(db: Session, session: dict) -> User | None:
    user_id = stripe_billing.checkout_user_id(session)
    if user_id:
        try:
            user = db.get(User, UUID(str(user_id)))
        except ValueError:
            user = None
        else:
            if user is not None:
                return user
    customer_id = stripe_billing.stripe_id(session.get("customer"))
    if customer_id:
        user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
        if user is not None:
            return user
    subscription_id = stripe_billing.stripe_id(session.get("subscription"))
    if subscription_id:
        return db.scalar(select(User).where(User.stripe_subscription_id == subscription_id))
    return None


def apply_paid_checkout(db: Session, session: dict, user: User | None = None) -> User | None:
    if not stripe_billing.checkout_is_paid(session):
        return None
    account = user or _user_from_session(db, session)
    if account is None:
        return None
    activate_plan(
        account,
        stripe_billing.checkout_plan(session),
        stripe_billing.stripe_id(session.get("customer")),
        stripe_billing.stripe_id(session.get("subscription")),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


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
    obj = dict((event.get("data") or {}).get("object") or {})
    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        session_id = stripe_billing.stripe_id(obj.get("id"))
        if session_id:
            try:
                obj = stripe_billing.retrieve_checkout_session(session_id)
            except Exception:
                logger.exception("Could not retrieve Stripe checkout session %s", session_id)
        if apply_paid_checkout(db, obj) is None:
            logger.warning("Checkout completed but no matching user was found")
        return {"ok": True}

    user: User | None = None
    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id") or obj.get("client_reference_id")
    if user_id:
        try:
            user = db.get(User, UUID(str(user_id)))
        except ValueError:
            user = None
    customer_id = stripe_billing.stripe_id(obj.get("customer"))
    event_name = str(event_type or "")
    subscription_id = stripe_billing.stripe_id(obj.get("subscription"))
    if subscription_id is None and event_name.startswith("customer.subscription"):
        subscription_id = stripe_billing.stripe_id(obj.get("id"))
    if user is None and customer_id:
        user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
    if user is None and subscription_id:
        user = db.scalar(select(User).where(User.stripe_subscription_id == subscription_id))
    if event_type in {"customer.subscription.deleted", "customer.subscription.paused"}:
        if user is not None:
            _set_plan(user, FREE_PLAN)
            db.add(user)
            db.commit()
    elif event_type == "customer.subscription.updated":
        status = str(obj.get("status") or "")
        if user is not None:
            if status in {"canceled", "unpaid", "incomplete_expired", "paused"}:
                _set_plan(user, FREE_PLAN)
            elif status in {"active", "trialing"}:
                paid_plan = str((obj.get("metadata") or {}).get("plan") or PRO_PLAN)
                if paid_plan not in PAID_PLANS:
                    paid_plan = PRO_PLAN
                _set_plan(user, paid_plan, customer_id, stripe_billing.stripe_id(obj.get("id")) or subscription_id)
            db.add(user)
            db.commit()
    else:
        logger.info("Ignored Stripe event %s", event_type)
    return {"ok": True}
