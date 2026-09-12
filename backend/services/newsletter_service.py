from __future__ import annotations

import logging
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Newsletter, NewsletterIssue, NewsletterPick, NewsletterSend, User
from services.paywall import is_newsletter_plan
from services.providers import finnhub, yahoo_http

logger = logging.getLogger(__name__)

MOVER_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD"]
SENTIMENT_LABELS = {
    "bullish": "Bullish Consensus",
    "bearish": "Bearish Consensus",
    "mixed": "Mixed Signals",
}


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def research_path(ticker: str) -> str:
    return f"/research?ticker={ticker.upper()}"


def research_url(ticker: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}{research_path(ticker)}"


def sentiment_label(value: str | None) -> str:
    key = (value or "mixed").strip().lower()
    return SENTIMENT_LABELS.get(key, "Mixed Signals")


def ensure_daily_newsletter(db: Session) -> Newsletter:
    row = db.scalar(select(Newsletter).where(Newsletter.slug == "daily"))
    if row is not None:
        return row
    row = Newsletter(
        name="GetStockReport Daily",
        slug="daily",
        description="Market open briefing plus one deep-dive institutional research desk.",
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def get_pick(db: Session, pick_date: date | None = None) -> NewsletterPick | None:
    day = pick_date or utc_today()
    return db.scalar(select(NewsletterPick).where(NewsletterPick.pick_date == day))


def market_movers(limit: int = 3) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in MOVER_SYMBOLS:
        try:
            quote = yahoo_http.spark_quote(symbol)
        except Exception:
            logger.exception("Mover quote failed for %s", symbol)
            continue
        change = quote.get("change_percent")
        if change is None:
            continue
        rows.append(
            {
                "ticker": quote.get("symbol") or symbol,
                "name": quote.get("name") or symbol,
                "price": quote.get("price"),
                "change_percent": change,
                "headline": f"{symbol} session move versus the prior close",
                "source": "Market tape",
                "source_url": research_url(symbol),
            }
        )
    rows.sort(key=lambda item: abs(float(item.get("change_percent") or 0)), reverse=True)
    return rows[:limit]


def earnings_this_week() -> list[dict[str, Any]]:
    try:
        return finnhub.earnings_week(7)
    except Exception:
        logger.exception("Earnings calendar lookup failed")
        return []


def macro_watch() -> dict[str, Any]:
    payload: dict[str, Any] = {"fed_event": "No scheduled Fed event on file"}
    mapping = {"oil": "CL=F", "vix": "^VIX", "yield_10y": "^TNX"}
    for key, symbol in mapping.items():
        try:
            quote = yahoo_http.spark_quote(symbol)
        except Exception:
            quote = {}
        change = quote.get("change_percent")
        price = quote.get("price")
        payload[key] = None if price is None else price
        payload[f"{key}_change"] = None if change is None else change
    payload["oil_price"] = payload.get("oil")
    payload["oil_change"] = payload.get("oil_change")
    return payload


def compile_email_html(
    pick: NewsletterPick,
    movers: list[dict[str, Any]],
    earnings: list[dict[str, Any]],
    macro: dict[str, Any],
) -> str:
    day = pick.pick_date.strftime("%A, %B %d, %Y")
    parts = [
        '<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#0f172a;">',
        "<h2>Market Open Briefing</h2>",
        f'<p style="color:#64748b;">{day}</p>',
        "<h3>Tape movers</h3>",
    ]
    for index, mover in enumerate(movers, 1):
        change = float(mover.get("change_percent") or 0)
        color = "#059669" if change >= 0 else "#e11d48"
        direction = "up" if change >= 0 else "down"
        parts.append(
            "<p>"
            f"<strong>{index}. {mover.get('ticker')}</strong> "
            f'<span style="color:{color};">{direction} {abs(change):.1f}%</span><br>'
            f"{mover.get('headline') or ''}<br>"
            f'<a href="{research_url(str(mover.get("ticker")))}">Open research</a>'
            "</p>"
        )
    parts.append("<h3>Earnings this week</h3>")
    if not earnings:
        parts.append("<p>No earnings dates were available for this window.</p>")
    for row in earnings[:5]:
        estimate = row.get("eps_estimate")
        actual = row.get("eps_actual")
        parts.append(
            "<p>"
            f"<strong>{row.get('date')}: {row.get('ticker')}</strong><br>"
            f"Estimate: {estimate if estimate is not None else 'n/a'} | "
            f"Prior print: {actual if actual is not None else 'n/a'}"
            "</p>"
        )
    oil = macro.get("oil_price")
    oil_change = macro.get("oil_change")
    parts.extend(
        [
            "<h3>Macro watch</h3>",
            "<p>"
            f"Fed calendar: {macro.get('fed_event', 'n/a')}<br>"
            f"Oil: {oil if oil is not None else 'n/a'}"
            f"{'' if oil_change is None else f' ({oil_change:.1f}%)'}<br>"
            f"VIX: {macro.get('vix', 'n/a')}<br>"
            f"10Y yield: {macro.get('yield_10y', 'n/a')}"
            "</p>",
            f"<h3>Deep dive: {pick.ticker}</h3>",
            f"<p><strong>{pick.reason}</strong></p>",
            "<ul>"
            f"<li>Coverage upgrades in the tape: {pick.analyst_upgrades}</li>"
            f"<li>Institutional flow (USD millions): {pick.institutional_buying}</li>"
            f"<li>Desk reading: {sentiment_label(pick.sentiment)}</li>"
            "</ul>",
            f'<p><a href="{research_url(pick.ticker)}" style="background:#10b981;color:#042f2e;padding:10px 16px;text-decoration:none;border-radius:8px;display:inline-block;">Open full institutional report</a></p>',
            '<p style="font-size:12px;color:#94a3b8;">For educational and informational purposes only. Not financial advice. GetStockReport does not issue buy, sell, or hold recommendations.<br>'
            f'<a href="{settings.frontend_url.rstrip("/")}/newsletter">Manage subscription</a> | '
            f'<a href="{settings.frontend_url.rstrip("/")}/privacy">Privacy Policy</a></p>',
            "</body></html>",
        ]
    )
    return "".join(parts)


def _send_html_email(to_addr: str, subject: str, html: str) -> bool:
    if not to_addr:
        return False
    if not settings.smtp_host:
        logger.info("Newsletter skipped (SMTP unset): %s -> %s", to_addr, subject)
        return False
    message = EmailMessage()
    sender = settings.smtp_from or f"{settings.newsletter_from_name} <{settings.newsletter_from_email}>"
    message["From"] = sender
    message["To"] = to_addr
    message["Subject"] = subject
    message.set_content("Open GetStockReport for today's market briefing and deep-dive research.")
    message.add_alternative(html, subtype="html")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
    return True


def upsert_issue(db: Session, pick: NewsletterPick, html: str) -> NewsletterIssue:
    desk = ensure_daily_newsletter(db)
    slug = f"daily-{pick.pick_date.isoformat()}"
    issue = db.scalar(
        select(NewsletterIssue).where(NewsletterIssue.newsletter_id == desk.id, NewsletterIssue.slug == slug)
    )
    excerpt = pick.reason[:180]
    title = f"Market brief: {pick.ticker} — {pick.pick_date.strftime('%b %d')}"
    published = datetime.combine(pick.pick_date, datetime.min.time(), tzinfo=timezone.utc)
    if issue is None:
        issue = NewsletterIssue(
            newsletter_id=desk.id,
            title=title,
            slug=slug,
            excerpt=excerpt,
            body=html,
            published_at=published,
            ticker=pick.ticker,
        )
        db.add(issue)
        db.flush()
    else:
        issue.title = title
        issue.excerpt = excerpt
        issue.body = html
        issue.published_at = published
        issue.ticker = pick.ticker
    pick.issue_id = issue.id
    return issue


def subscriber_query(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User).where(
                User.is_active.is_(True),
                User.plan == "newsletter_pro",
                User.newsletter_email_preference == "daily",
            )
        ).all()
    )


def generate_daily_newsletter(db: Session | None = None, send_email: bool = True) -> dict[str, Any]:
    owned = db is None
    session = db or SessionLocal()
    try:
        pick = get_pick(session)
        if pick is None:
            return {"status": "no_pick", "emails_sent": 0}
        movers = market_movers()
        earnings = earnings_this_week()
        macro = macro_watch()
        html = compile_email_html(pick, movers, earnings, macro)
        upsert_issue(session, pick, html)
        sent = 0
        if send_email:
            subject = f"Market Brief: {pick.ticker} — {pick.pick_date.strftime('%b %d')}"
            for user in subscriber_query(session):
                try:
                    delivered = _send_html_email(user.email, subject, html)
                except Exception:
                    logger.exception("Newsletter email failed for %s", user.email)
                    continue
                if not delivered:
                    continue
                session.add(NewsletterSend(pick_id=pick.id, user_id=user.id))
                sent += 1
        session.commit()
        return {
            "status": "success",
            "emails_sent": sent,
            "pick": pick.ticker,
            "date": pick.pick_date.isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        if owned:
            session.close()


def archive_items(db: Session, page: int = 1, limit: int = 30) -> list[dict[str, Any]]:
    cutoff = utc_today() - timedelta(days=90)
    offset = max(page - 1, 0) * limit
    rows = db.scalars(
        select(NewsletterPick)
        .where(NewsletterPick.pick_date >= cutoff)
        .order_by(NewsletterPick.pick_date.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "date": row.pick_date.isoformat(),
            "ticker": row.ticker,
            "reason": row.reason,
            "sentiment": sentiment_label(row.sentiment),
            "issue_id": row.issue_id,
            "research_path": research_path(row.ticker),
        }
        for row in rows
    ]


def emails_received(db: Session, user_id: Any) -> int:
    value = db.scalar(select(func.count()).select_from(NewsletterSend).where(NewsletterSend.user_id == user_id))
    return int(value or 0)


def today_payload(db: Session, full_access: bool) -> dict[str, Any]:
    pick = get_pick(db)
    if pick is None:
        return {"date": None, "ticker": None, "reason": None, "full_access": full_access}
    payload: dict[str, Any] = {
        "date": pick.pick_date.isoformat(),
        "ticker": pick.ticker,
        "reason": pick.reason,
        "sentiment": sentiment_label(pick.sentiment),
        "research_path": research_path(pick.ticker),
        "issue_id": pick.issue_id,
        "full_access": full_access,
        "movers": [],
        "earnings": [],
        "macro": {},
        "html": None,
    }
    if not full_access:
        return payload
    movers = market_movers()
    earnings = earnings_this_week()
    macro = macro_watch()
    payload["movers"] = movers
    payload["earnings"] = earnings
    payload["macro"] = macro
    payload["html"] = compile_email_html(pick, movers, earnings, macro)
    return payload
