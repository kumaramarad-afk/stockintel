from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import current_user, db_session
from app.models import User
from app.routers.users import user_to_read
from app.routers.webhooks import apply_paid_checkout
from app.schemas.user import UserRead
from services import stripe_billing

router = APIRouter(tags=["billing"])


class CheckoutResponse(BaseModel):
    url: str


class VerifySessionRequest(BaseModel):
    session_id: str | None = None


@router.post("/api/checkout", response_model=CheckoutResponse)
@router.post("/api/v1/checkout", response_model=CheckoutResponse)
def create_checkout(user: User = Depends(current_user)) -> CheckoutResponse:
    if user.plan == "pro":
        raise HTTPException(status_code=400, detail="This account is already on Pro")
    success = (
        f"{settings.frontend_url.rstrip('/')}/account"
        "?upgraded=1&session_id={CHECKOUT_SESSION_ID}"
    )
    cancel = f"{settings.frontend_url.rstrip('/')}/subscribe"
    try:
        url = stripe_billing.create_checkout_session(user.id, user.email, success, cancel)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not start checkout") from exc
    return CheckoutResponse(url=url)


@router.post("/api/billing/portal", response_model=CheckoutResponse)
@router.post("/api/v1/billing/portal", response_model=CheckoutResponse)
def create_billing_portal(user: User = Depends(current_user)) -> CheckoutResponse:
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe billing account is linked yet. Subscribe first, then manage or cancel from here.",
        )
    return_url = f"{settings.frontend_url.rstrip('/')}/account"
    try:
        url = stripe_billing.create_portal_session(user.stripe_customer_id, return_url)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not open billing portal") from exc
    return CheckoutResponse(url=url)


@router.post("/api/payments/verify-session", response_model=UserRead)
@router.post("/api/v1/payments/verify-session", response_model=UserRead)
def verify_checkout_session(
    payload: VerifySessionRequest,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> UserRead:
    session_id = (payload.session_id or "").strip() or None
    try:
        session = stripe_billing.find_paid_checkout_session(str(user.id), user.email, session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not verify checkout session") from exc
    upgraded = apply_paid_checkout(db, session, user)
    if upgraded is None:
        raise HTTPException(status_code=400, detail="Checkout is not paid yet")
    return user_to_read(upgraded, db)
