from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session, require_admin
from app.models import PlanException, User
from services.paywall import normalize_email

router = APIRouter(prefix="/admin/plan-exceptions", tags=["admin"])


class ExceptionCreate(BaseModel):
    email: EmailStr
    note: str | None = Field(default="Complimentary Premium ($12)", max_length=255)


class ExceptionRead(BaseModel):
    email: str
    plan: str
    note: str | None
    created_at: datetime | None = None
    has_account: bool = False


def upsert_exception(db: Session, email: str, note: str | None = None) -> PlanException:
    address = normalize_email(email)
    row = db.scalar(select(PlanException).where(PlanException.email == address))
    if row is None:
        row = PlanException(email=address, plan="premium", note=note)
        db.add(row)
    else:
        row.plan = "premium"
        if note:
            row.note = note
    user = db.scalar(select(User).where(User.email == address))
    if user is not None:
        user.newsletter_subscription_status = "active"
        user.newsletter_email_preference = "daily"
        user.newsletter_subscribed_at = user.newsletter_subscribed_at or datetime.now(timezone.utc)
        db.add(user)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[ExceptionRead])
def list_exceptions(user: User = Depends(require_admin), db: Session = Depends(db_session)) -> list[ExceptionRead]:
    rows = db.scalars(select(PlanException).order_by(PlanException.created_at.desc())).all()
    accounts = {item.email for item in db.scalars(select(User)).all()}
    return [
        ExceptionRead(
            email=row.email,
            plan=row.plan,
            note=row.note,
            created_at=row.created_at,
            has_account=row.email in accounts,
        )
        for row in rows
    ]


@router.post("", response_model=ExceptionRead)
def add_exception(
    payload: ExceptionCreate,
    user: User = Depends(require_admin),
    db: Session = Depends(db_session),
) -> ExceptionRead:
    row = upsert_exception(db, str(payload.email), payload.note)
    account = db.scalar(select(User).where(User.email == row.email))
    return ExceptionRead(
        email=row.email,
        plan=row.plan,
        note=row.note,
        created_at=row.created_at,
        has_account=account is not None,
    )


@router.delete("")
def remove_exception(
    email: str = Query(..., min_length=3, max_length=255),
    user: User = Depends(require_admin),
    db: Session = Depends(db_session),
) -> dict[str, str]:
    address = normalize_email(email)
    row = db.scalar(select(PlanException).where(PlanException.email == address))
    if row is None:
        raise HTTPException(status_code=404, detail="Email is not on the exception list")
    db.delete(row)
    db.commit()
    return {"status": "removed", "email": address}
