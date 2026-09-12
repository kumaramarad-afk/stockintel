from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import AlertEvent, User, Watchlist, WatchlistItem
from services.paywall import is_paid_plan

logger = logging.getLogger(__name__)


def _send_email(to_addr: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not to_addr:
        logger.info("Alert skipped (SMTP unset): %s -> %s", to_addr, subject)
        return
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_addr
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def _watchers(db: Session, ticker: str) -> list[User]:
    symbol = ticker.upper()
    watchlists = db.scalars(
        select(Watchlist).options(
            selectinload(Watchlist.items).selectinload(WatchlistItem.stock),
            selectinload(Watchlist.user),
        )
    ).all()
    users: list[User] = []
    seen: set = set()
    for board in watchlists:
        user = board.user
        if user is None or not is_paid_plan(user.plan) or not user.is_active or user.id in seen:
            continue
        for item in board.items or []:
            stock = getattr(item, "stock", None)
            if stock is not None and str(getattr(stock, "ticker", "")).upper() == symbol:
                users.append(user)
                seen.add(user.id)
                break
    if users:
        return users
    return []


def _record(db: Session, user: User, ticker: str, event_type: str, dedupe_key: str) -> bool:
    db.add(
        AlertEvent(
            user_id=user.id,
            ticker=ticker.upper(),
            event_type=event_type,
            dedupe_key=dedupe_key[:255],
        )
    )
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def notify_from_report(db: Session, ticker: str, section: str, data: dict[str, Any] | None) -> None:
    if not data:
        return
    events: list[tuple[str, str, str]] = []
    if section == "header":
        for row in data.get("recent_actions") or []:
            direction = str(row.get("direction") or "")
            if direction not in {"raised", "lowered"}:
                continue
            days = row.get("days_ago")
            if isinstance(days, int) and days > 2:
                continue
            firm = row.get("firm") or "a coverage desk"
            key = f"{ticker}:{row.get('date')}:{firm}:{direction}"
            verb = "raised a target" if direction == "raised" else "cut a target"
            events.append(
                (
                    "target_change",
                    key,
                    f"{firm} {verb} on {ticker}. Open GetStockReport for the full briefing.",
                )
            )
    if section == "ownership":
        for row in data.get("insider_transactions") or []:
            key = f"{ticker}:insider:{row.get('date')}:{row.get('name')}"
            events.append(
                (
                    "insider",
                    key,
                    f"Insider activity printed on {ticker} ({row.get('name') or 'an insider'}). Open GetStockReport for the filing detail.",
                )
            )
    if not events:
        return
    for user in _watchers(db, ticker):
        for event_type, key, body in events[:8]:
            if _record(db, user, ticker, event_type, f"{user.id}:{key}"):
                try:
                    _send_email(user.email, f"GetStockReport alert: {ticker}", body)
                except Exception:
                    logger.exception("Alert email failed for %s", user.email)
