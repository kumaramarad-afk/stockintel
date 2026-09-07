from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.deps import current_user
from app.models import User
from services import stripe_billing

router = APIRouter(tags=["billing"])


class CheckoutResponse(BaseModel):
    url: str


@router.post("/api/checkout", response_model=CheckoutResponse)
@router.post("/api/v1/checkout", response_model=CheckoutResponse)
def create_checkout(user: User = Depends(current_user)) -> CheckoutResponse:
    if user.plan == "pro":
        raise HTTPException(status_code=400, detail="This account is already on Pro")
    success = f"{settings.frontend_url.rstrip('/')}/account?upgraded=1"
    cancel = f"{settings.frontend_url.rstrip('/')}/subscribe"
    try:
        url = stripe_billing.create_checkout_session(user.id, user.email, success, cancel)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not start checkout") from exc
    return CheckoutResponse(url=url)
