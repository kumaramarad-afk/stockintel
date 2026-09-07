from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import Newsletter, NewsletterIssue, NewsletterSubscription, Subscriber
from app.schemas.newsletter import (
    NewsletterIssueRead,
    NewsletterRead,
    SubscribeRequest,
    SubscribeResponse,
)

router = APIRouter(prefix="/newsletters", tags=["newsletters"])


@router.get("", response_model=list[NewsletterRead])
def list_newsletters(db: Session = Depends(db_session)) -> list[Newsletter]:
    return list(db.scalars(select(Newsletter).order_by(Newsletter.name)).all())


@router.get("/{slug}", response_model=NewsletterRead)
def get_newsletter(slug: str, db: Session = Depends(db_session)) -> Newsletter:
    newsletter = db.scalar(select(Newsletter).where(Newsletter.slug == slug))
    if newsletter is None:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    return newsletter


@router.get("/{slug}/issues", response_model=list[NewsletterIssueRead])
def list_issues(slug: str, db: Session = Depends(db_session)) -> list[NewsletterIssue]:
    newsletter = db.scalar(select(Newsletter).where(Newsletter.slug == slug))
    if newsletter is None:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    return list(
        db.scalars(
            select(NewsletterIssue)
            .where(NewsletterIssue.newsletter_id == newsletter.id)
            .order_by(NewsletterIssue.published_at.desc().nulls_last())
        ).all()
    )


@router.get("/issues/{issue_id}", response_model=NewsletterIssueRead)
def get_issue(issue_id: str, db: Session = Depends(db_session)) -> NewsletterIssue:
    issue = db.get(NewsletterIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe(payload: SubscribeRequest, db: Session = Depends(db_session)) -> SubscribeResponse:
    newsletter = db.scalar(select(Newsletter).where(Newsletter.slug == payload.newsletter_slug))
    if newsletter is None:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    subscriber = db.scalar(select(Subscriber).where(Subscriber.email == payload.email))
    if subscriber is None:
        subscriber = Subscriber(email=payload.email, full_name=payload.full_name)
        db.add(subscriber)
        db.flush()

    existing = db.scalar(
        select(NewsletterSubscription).where(
            NewsletterSubscription.newsletter_id == newsletter.id,
            NewsletterSubscription.subscriber_id == subscriber.id,
        )
    )
    if existing is None:
        db.add(NewsletterSubscription(newsletter_id=newsletter.id, subscriber_id=subscriber.id))

    db.commit()
    return SubscribeResponse(
        subscriber_id=subscriber.id,
        newsletter_id=newsletter.id,
        email=subscriber.email,
        message="Subscribed",
    )
