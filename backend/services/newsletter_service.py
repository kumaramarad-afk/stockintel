from __future__ import annotations

import logging
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Newsletter, NewsletterIssue, NewsletterPick, NewsletterSend, PlanException, User
from services.paywall import normalize_email, user_has_premium
from services.providers import finnhub, sec_edgar, yahoo_http

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


def insider_activity(ticker: str, limit: int = 3) -> list[dict[str, Any]]:
    try:
        rows = sec_edgar.insider_transactions(ticker) or []
    except Exception:
        logger.exception("Insider lookup failed for %s", ticker)
        return []
    items = []
    for row in rows[:limit]:
        items.append(
            {
                "ticker": ticker.upper(),
                "executive_name": row.get("name") or "Form 4 filer",
                "title": row.get("title") or "Officer",
                "transaction_type": row.get("action") or "Form 4",
                "amount": row.get("value"),
                "date": row.get("date"),
            }
        )
    return items


def institutional_flows(ticker: str, pick: NewsletterPick | None = None, limit: int = 5) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if pick is not None and pick.institutional_buying:
        items.append(
            {
                "ticker": ticker.upper(),
                "fund_name": "Desk-noted institutional flow",
                "value": float(pick.institutional_buying) * 1_000_000,
                "shares": None,
                "report_date": "this week",
            }
        )
    return items[:limit]


def weekly_scorecard(db: Session, current: NewsletterPick, limit: int = 5) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(NewsletterPick)
        .where(NewsletterPick.pick_date < current.pick_date)
        .order_by(NewsletterPick.pick_date.desc())
        .limit(limit)
    ).all()
    return [
        {
            "date": row.pick_date.isoformat(),
            "ticker": row.ticker,
            "reason": row.reason,
            "sentiment": sentiment_label(row.sentiment),
        }
        for row in rows
    ]


def compile_email_html(
    pick: NewsletterPick,
    movers: list[dict[str, Any]],
    earnings: list[dict[str, Any]],
    macro: dict[str, Any],
    insider_rows: list[dict[str, Any]] | None = None,
    institution_rows: list[dict[str, Any]] | None = None,
    scorecard: list[dict[str, Any]] | None = None,
) -> str:
    day = pick.pick_date.strftime("%A, %B %d, %Y")
    site = settings.frontend_url.rstrip("/")
    parts = [
        "<html><head><style>",
        "body{font-family:Arial,sans-serif;max-width:700px;margin:0 auto;color:#0f172a;background:#ffffff;}",
        ".header{background:#042f2e;color:#ecfdf5;padding:20px;text-align:center;}",
        ".section{border:1px solid #d1d5db;margin:16px 0;padding:18px;border-radius:8px;}",
        ".section h3{color:#065f46;margin-top:0;}",
        ".note{background:#fff7ed;border:1px solid #fdba74;padding:12px;font-size:12px;margin:16px 0;}",
        ".item{background:#f8fafc;padding:12px;margin:10px 0;border-radius:6px;}",
        "</style></head><body>",
        '<div class="header"><h2>Market Intelligence Brief</h2>',
        f"<p>{day}</p></div>",
        '<div class="note"><strong>Disclaimer:</strong> Educational and informational purposes only. Not financial advice. ',
        "GetStockReport does not issue buy, sell, or hold recommendations. Consult a licensed advisor. Past performance is not future results.</div>",
        '<div class="section"><h3>1. Tape alerts</h3>',
    ]
    if not movers:
        parts.append("<p>No large-cap tape movers were available for this window.</p>")
    for mover in movers:
        change = float(mover.get("change_percent") or 0)
        direction = "higher" if change >= 0 else "lower"
        parts.append(
            '<div class="item">'
            f"<strong>{mover.get('ticker')}</strong> printed {abs(change):.1f}% {direction} versus the prior close.<br>"
            f"{mover.get('headline') or ''}<br>"
            f'<a href="{research_url(str(mover.get("ticker")))}">Open the research report</a>'
            "</div>"
        )
    parts.append("</div>")
    parts.append('<div class="section"><h3>2. Insider Form 4 activity</h3><p><em>Historical SEC filings only. Not a recommendation.</em></p>')
    if not insider_rows:
        parts.append("<p>No recent Form 4 prints were available for the featured name.</p>")
    for row in insider_rows or []:
        amount = row.get("amount")
        money = f"${amount:,.0f}" if isinstance(amount, (int, float)) else "an unspecified amount"
        parts.append(
            '<div class="item">'
            f"<strong>{row.get('executive_name')}</strong> ({row.get('title')}) reported a {row.get('transaction_type')} "
            f"in {row.get('ticker')} totaling {money}."
            "</div>"
        )
    parts.append("</div>")
    parts.append('<div class="section"><h3>3. Institutional 13F holdings</h3><p><em>Lagging 13F snapshots. Informational only.</em></p>')
    if not institution_rows:
        parts.append("<p>No 13F holder snapshot was available for the featured name.</p>")
    for row in institution_rows or []:
        value = row.get("value")
        money = f"${value:,.0f}" if isinstance(value, (int, float)) else "n/a"
        parts.append(
            '<div class="item">'
            f"<strong>{row.get('fund_name')}</strong> reported a {row.get('ticker')} holding of {money} "
            f"(as of {row.get('report_date') or 'the latest 13F'})."
            "</div>"
        )
    parts.append("</div>")
    parts.append('<div class="section"><h3>4. Earnings this week</h3>')
    if not earnings:
        parts.append("<p>No earnings dates were available for this window.</p>")
    for row in earnings[:5]:
        estimate = row.get("eps_estimate")
        parts.append(
            '<div class="item">'
            f"<strong>{row.get('date')}: {row.get('ticker')}</strong><br>"
            f"Consensus EPS estimate: {estimate if estimate is not None else 'n/a'}. "
            "Use this as a calendar marker for possible volatility, not as a directional view."
            "</div>"
        )
    parts.append("</div>")
    oil = macro.get("oil_price")
    oil_change = macro.get("oil_change")
    parts.append('<div class="section"><h3>5. Macro watch</h3><p>')
    parts.append(f"Fed calendar: {macro.get('fed_event', 'n/a')}<br>")
    parts.append(f"Oil: {oil if oil is not None else 'n/a'}")
    if oil_change is not None:
        parts.append(f" ({oil_change:.1f}%)")
    parts.append(f"<br>VIX: {macro.get('vix', 'n/a')}<br>10Y yield: {macro.get('yield_10y', 'n/a')}</p></div>")
    parts.append(
        '<div class="section"><h3>6. Featured research desk</h3>'
        f"<p><strong>{pick.ticker}</strong> — {pick.reason}</p>"
        f"<p>Coverage upgrades in the tape: {pick.analyst_upgrades} | Institutional flow (USD millions): {pick.institutional_buying}</p>"
        f"<p>Desk reading: {sentiment_label(pick.sentiment)}</p>"
        '<p class="note">Not a recommendation. Do your own research. '
        f'<a href="{research_url(pick.ticker)}">Read the full institutional report</a></p></div>'
    )
    parts.append('<div class="section"><h3>7. Recent featured names</h3><p><em>Transparency archive. Not performance advertising.</em></p>')
    if not scorecard:
        parts.append("<p>No prior featured names are on file yet.</p>")
    for row in scorecard or []:
        parts.append(
            '<div class="item">'
            f"{row.get('date')}: <strong>{row.get('ticker')}</strong> — {row.get('sentiment')}<br>{row.get('reason')}"
            "</div>"
        )
    parts.append("</div>")
    parts.append(
        '<div class="note"><strong>Full disclaimer:</strong> Not financial advice. Not a recommendation to transact. '
        "Consult a licensed financial advisor. Verify independently before investing. "
        f'<a href="{site}/legal/newsletter-disclaimer">Read the newsletter disclaimer</a> | '
        f'<a href="{site}/newsletter">Manage subscription</a> | '
        f'<a href="{site}/privacy">Privacy Policy</a></div>'
        "</body></html>"
    )
    return "".join(parts)


def _from_identity() -> tuple[str, str]:
    email = settings.newsletter_from_email or "newsletter@getstockreport.com"
    name = settings.newsletter_from_name or "GetStockReport"
    return name, email


def _send_via_sendgrid(
    to_addr: str,
    subject: str,
    html: str,
    *,
    text: str | None = None,
    reply_to: str | None = None,
    reply_name: str | None = None,
) -> bool:
    name, email = _from_identity()
    payload: dict[str, Any] = {
        "personalizations": [{"to": [{"email": to_addr}]}],
        "from": {"email": email, "name": name},
        "subject": subject,
        "content": [
            {
                "type": "text/plain",
                "value": text or "Open GetStockReport for today's market briefing and deep-dive research.",
            },
            {"type": "text/html", "value": html},
        ],
    }
    if reply_to:
        payload["reply_to"] = {"email": reply_to, "name": reply_name or reply_to}
    headers = {
        "Authorization": f"Bearer {settings.sendgrid_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers)
    if response.status_code >= 400:
        logger.warning("SendGrid rejected newsletter to %s (%s) %s", to_addr, response.status_code, response.text[:300])
        return False
    return True


def _send_html_email(
    to_addr: str,
    subject: str,
    html: str,
    *,
    text: str | None = None,
    reply_to: str | None = None,
    reply_name: str | None = None,
) -> bool:
    if not to_addr:
        return False
    if settings.sendgrid_api_key:
        return _send_via_sendgrid(
            to_addr,
            subject,
            html,
            text=text,
            reply_to=reply_to,
            reply_name=reply_name,
        )
    if not settings.smtp_host:
        logger.info("Newsletter skipped (email unset): %s -> %s", to_addr, subject)
        return False
    name, email = _from_identity()
    message = EmailMessage()
    message["From"] = f"{name} <{email}>"
    message["To"] = to_addr
    message["Subject"] = subject
    if reply_to:
        message["Reply-To"] = f"{reply_name} <{reply_to}>" if reply_name else reply_to
    message.set_content(text or "Open GetStockReport for today's market briefing and deep-dive research.")
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
    users = []
    for user in db.scalars(select(User).where(User.is_active.is_(True))).all():
        if user_has_premium(user, db) and (user.newsletter_email_preference or "daily") == "daily":
            users.append(user)
    return users


def recipient_emails(db: Session, extra_emails: list[str] | None = None) -> list[tuple[str, User | None]]:
    mapped: dict[str, User | None] = {}
    for user in subscriber_query(db):
        mapped[normalize_email(user.email)] = user
    for row in db.scalars(select(PlanException)).all():
        mapped.setdefault(normalize_email(row.email), None)
    for raw in extra_emails or []:
        address = normalize_email(raw)
        if address:
            mapped.setdefault(address, None)
    users_by_email = {normalize_email(user.email): user for user in db.scalars(select(User)).all()}
    out: list[tuple[str, User | None]] = []
    for email, user in mapped.items():
        out.append((email, user or users_by_email.get(email)))
    return out


def generate_daily_newsletter(
    db: Session | None = None,
    send_email: bool = True,
    extra_emails: list[str] | None = None,
) -> dict[str, Any]:
    owned = db is None
    session = db or SessionLocal()
    try:
        pick = get_pick(session)
        if pick is None:
            return {"status": "no_pick", "emails_sent": 0}
        movers = market_movers()
        earnings = earnings_this_week()
        macro = macro_watch()
        insiders = insider_activity(pick.ticker)
        institutions = institutional_flows(pick.ticker, pick)
        scorecard = weekly_scorecard(session, pick)
        html = compile_email_html(pick, movers, earnings, macro, insiders, institutions, scorecard)
        upsert_issue(session, pick, html)
        sent = 0
        failed: list[str] = []
        if send_email:
            subject = f"Market Brief: {pick.ticker} — {pick.pick_date.strftime('%b %d')}"
            for email, user in recipient_emails(session, extra_emails):
                try:
                    delivered = _send_html_email(email, subject, html)
                except Exception:
                    logger.exception("Newsletter email failed for %s", email)
                    failed.append(email)
                    continue
                if not delivered:
                    failed.append(email)
                    continue
                if user is not None:
                    session.add(NewsletterSend(pick_id=pick.id, user_id=user.id))
                sent += 1
        session.commit()
        return {
            "status": "success",
            "emails_sent": sent,
            "failed": failed,
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
