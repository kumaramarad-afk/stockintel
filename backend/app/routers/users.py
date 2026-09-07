from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import current_user, db_session
from app.models import User
from app.schemas.user import SubscribePlanRequest, TokenResponse, UserCreate, UserLogin, UserRead
from services.auth import create_token, hash_password, verify_password
from services.paywall import MONTHLY_LIMIT, count_views

router = APIRouter(prefix="/users", tags=["users"])


def _to_read(user: User, db: Session) -> UserRead:
    payload = UserRead.model_validate(user)
    payload.reports_used = count_views(db, user.id)
    payload.reports_limit = MONTHLY_LIMIT
    return payload


def _issue(user: User, db: Session) -> TokenResponse:
    return TokenResponse(access_token=create_token(user.id), user=_to_read(user, db))


@router.post("", response_model=TokenResponse, status_code=201)
@router.post("/register", response_model=TokenResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(db_session)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        plan="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue(user, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(db_session)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return _issue(user, db)


@router.get("/me", response_model=UserRead)
def read_me(user: User = Depends(current_user), db: Session = Depends(db_session)) -> UserRead:
    return _to_read(user, db)


@router.post("/subscribe", response_model=UserRead)
def subscribe_plan(
    payload: SubscribePlanRequest,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> UserRead:
    user.plan = payload.plan
    user.subscribed_at = datetime.now(timezone.utc) if payload.plan == "pro" else None
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_read(user, db)
