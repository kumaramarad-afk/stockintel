from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import current_user, db_session, optional_user
from app.models import NewsletterIssue, User
from app.schemas.newsletter import (
    EmailPreferenceRequest,
    NewsletterArchiveItem,
    NewsletterStatusRead,
    NewsletterTodayRead,
)
from services.newsletter_service import (
    archive_items,
    emails_received,
    generate_daily_newsletter,
    get_pick,
    today_payload,
)
from services.paywall import is_newsletter_plan

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


def _require_newsletter(user: User) -> None:
    if not is_newsletter_plan(user.plan):
        raise HTTPException(status_code=403, detail="Newsletter Pro required")


@router.get("/status", response_model=NewsletterStatusRead)
def newsletter_status(user: User = Depends(current_user), db: Session = Depends(db_session)) -> NewsletterStatusRead:
    status = user.newsletter_subscription_status or "none"
    if is_newsletter_plan(user.plan) and status == "none":
        status = "active"
    return NewsletterStatusRead(
        tier=user.plan,
        status=status,
        newsletter_enabled=(user.newsletter_email_preference or "daily") == "daily" and is_newsletter_plan(user.plan),
        subscribed_at=user.newsletter_subscribed_at or user.subscribed_at,
        newsletter_emails_received=emails_received(db, user.id),
        email_preference=user.newsletter_email_preference or "daily",
    )


@router.post("/unsubscribe")
def unsubscribe_newsletter(user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict[str, str]:
    user.newsletter_email_preference = "off"
    db.add(user)
    db.commit()
    return {"status": "unsubscribed"}


@router.post("/email-preference")
def set_email_preference(
    payload: EmailPreferenceRequest,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict[str, str]:
    preference = payload.preference.strip().lower()
    if preference not in {"daily", "off"}:
        raise HTTPException(status_code=400, detail="Preference must be daily or off")
    user.newsletter_email_preference = preference
    db.add(user)
    db.commit()
    return {"status": preference}


@router.get("/archive", response_model=list[NewsletterArchiveItem])
def newsletter_archive(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=90),
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> list[NewsletterArchiveItem]:
    _require_newsletter(user)
    return [NewsletterArchiveItem.model_validate(item) for item in archive_items(db, page, limit)]


@router.get("/archive/{pick_date}", response_model=NewsletterTodayRead)
def newsletter_archive_date(
    pick_date: str,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> NewsletterTodayRead:
    _require_newsletter(user)
    try:
        day = datetime.strptime(pick_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Use YYYY-MM-DD") from exc
    pick = get_pick(db, day)
    if pick is None:
        raise HTTPException(status_code=404, detail="No briefing for that date")
    html = None
    if pick.issue_id is not None:
        issue = db.get(NewsletterIssue, pick.issue_id)
        html = issue.body if issue is not None else None
    return NewsletterTodayRead(
        date=pick.pick_date.isoformat(),
        ticker=pick.ticker,
        reason=pick.reason,
        sentiment=pick.sentiment,
        research_path=f"/research?ticker={pick.ticker.upper()}",
        issue_id=pick.issue_id,
        full_access=True,
        html=html,
    )


@router.get("/today", response_model=NewsletterTodayRead)
def newsletter_today(
    db: Session = Depends(db_session),
    user: User | None = Depends(optional_user),
) -> NewsletterTodayRead:
    full = is_newsletter_plan(user.plan) if user is not None else False
    return NewsletterTodayRead.model_validate(today_payload(db, full))


@router.post("/admin/generate")
def generate_newsletter_admin(
    api_key: str | None = Query(default=None),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Session = Depends(db_session),
) -> dict:
    expected = settings.internal_api_key
    if not expected:
        raise HTTPException(status_code=503, detail="Internal API key is not configured")
    provided = api_key or x_internal_key
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return generate_daily_newsletter(db, send_email=True)
