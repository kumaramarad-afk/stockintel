from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import NewsletterIssue, ResearchNote, Stock, Subscriber

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "stockintel-api"}


@router.get("/stats")
def stats(db: Session = Depends(db_session)) -> dict[str, int]:
    stock_count = db.scalar(select(func.count()).select_from(Stock)) or 0
    research_count = db.scalar(select(func.count()).select_from(ResearchNote)) or 0
    issue_count = db.scalar(select(func.count()).select_from(NewsletterIssue)) or 0
    subscriber_count = db.scalar(select(func.count()).select_from(Subscriber)) or 0
    return {
        "stocks": stock_count,
        "research_notes": research_count,
        "newsletter_issues": issue_count,
        "subscribers": subscriber_count,
    }
