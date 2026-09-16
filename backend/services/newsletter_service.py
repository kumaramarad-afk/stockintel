from __future__ import annotations

import html as html_lib
import logging
import re
import smtplib
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.message import EmailMessage
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Newsletter, NewsletterIssue, NewsletterPick, NewsletterSend, PlanException, User
from services.numbers import to_float
from services.paywall import normalize_email, user_has_premium
from services.providers import finnhub, newsapi, sec_edgar, yahoo_http

logger = logging.getLogger(__name__)

MOVER_SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD"]
SENTIMENT_LABELS = {
    "bullish": "Bullish Consensus",
    "bearish": "Bearish Consensus",
    "mixed": "Mixed Signals",
}
FREE_FULL_BUSINESS_DAYS = 5
FREE_PREVIEW_BUSINESS_DAYS = 15
NEWSLETTER_ACCESS_FULL = "full"
NEWSLETTER_ACCESS_PREVIEW = "preview"
NEWSLETTER_ACCESS_SKIP = "skip"


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def registration_date(user: Any) -> date | None:
    raw = getattr(user, "created_at", None) if user is not None else None
    if raw is None:
        return None
    if isinstance(raw, datetime):
        stamp = raw if raw.tzinfo is not None else raw.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc).date()
    if isinstance(raw, date):
        return raw
    return None


def business_days_elapsed(start: date, today: date | None = None) -> int:
    end = today or utc_today()
    if end < start:
        return 0
    days = 0
    cursor = start
    step = timedelta(days=1)
    while cursor <= end:
        if cursor.weekday() < 5:
            days += 1
        cursor += step
    return days


def trial_business_day(user: Any, today: date | None = None) -> int:
    started = registration_date(user)
    if started is None:
        return 0
    return business_days_elapsed(started, today or utc_today())


def newsletter_access(user: Any, db: Session | None = None, today: date | None = None) -> str:
    if user is None:
        return NEWSLETTER_ACCESS_SKIP
    if not bool(getattr(user, "is_active", True)):
        return NEWSLETTER_ACCESS_SKIP
    if (getattr(user, "newsletter_email_preference", None) or "daily") != "daily":
        return NEWSLETTER_ACCESS_SKIP
    if user_has_premium(user, db):
        return NEWSLETTER_ACCESS_FULL
    day = trial_business_day(user, today)
    if 1 <= day <= FREE_FULL_BUSINESS_DAYS:
        return NEWSLETTER_ACCESS_FULL
    if FREE_FULL_BUSINESS_DAYS < day <= FREE_PREVIEW_BUSINESS_DAYS:
        return NEWSLETTER_ACCESS_PREVIEW
    return NEWSLETTER_ACCESS_SKIP


def upgrade_url() -> str:
    return f"{settings.frontend_url.rstrip('/')}/subscribe"


def research_path(ticker: str) -> str:
    return f"/research/{ticker.upper()}"


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


def _esc(value: Any) -> str:
    return html_lib.escape(str(value or ""), quote=True)


def _href(url: Any) -> str:
    text = str(url or "").strip()
    if not text.startswith(("http://", "https://")):
        return "#"
    return _esc(text)


def _two_sentences(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").replace("\u00a0", " ")).strip()
    cleaned = re.sub(r"\[\+\d+ chars\]\s*$", "", cleaned).strip()
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return " ".join(parts[:2])[:420]


def _plain_news(text: Any, source: Any = "") -> str:
    value = re.sub(r"\s+", " ", str(text or "").replace("\u00a0", " ")).strip()
    value = re.sub(r"\[\+\d+ chars\]\s*$", "", value).strip()
    src = str(source or "").strip()
    if src:
        value = re.sub(rf"[\s\-|:/–—]*{re.escape(src)}\s*$", "", value, flags=re.I).strip()
    return re.sub(r"[\s\-|:/–—]+$", "", value).strip()


def _news_fingerprint(text: Any, source: Any = "") -> str:
    value = _plain_news(text, source).lower()
    value = re.sub(r"[^a-z0-9\s]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _is_repeat_sentence(headline: str, sentence: str, source: str = "") -> bool:
    head = _news_fingerprint(headline, source)
    other = _news_fingerprint(sentence, source)
    if not head or not other:
        return False
    if head == other:
        return True
    shorter, longer = (head, other) if len(head) <= len(other) else (other, head)
    if shorter in longer:
        extra = longer.replace(shorter, "", 1).strip()
        if len(extra) < 28:
            return True
    return SequenceMatcher(None, head, other).ratio() >= 0.84


def _clean_headline(headline: Any, source: Any = "") -> str:
    return _plain_news(headline, source) or str(headline or "").strip()


def _distinct_summary(headline: str, summary: Any, source: Any = "") -> str:
    cleaned = _two_sentences(_plain_news(summary, source))
    if not cleaned:
        return ""
    kept: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", cleaned):
        text = _plain_news(sentence, source)
        if not text or _is_repeat_sentence(headline, text, source):
            continue
        kept.append(text)
    return " ".join(kept[:2]).strip()


def _locked_overlay(subscribe_url: str) -> str:
    return (
        '<div class="locked-overlay">'
        "<p><strong>Upgrade to Premium</strong></p>"
        "<p>Subscribe to see the rest of this section.</p>"
        f'<a class="upgrade-btn" href="{_esc(subscribe_url)}">Upgrade to Premium</a>'
        "</div>"
    )


def _emit_items(items: list[str], preview: bool, subscribe_url: str) -> list[str]:
    if not items:
        return []
    if not preview or len(items) == 1:
        return list(items)
    return [
        items[0],
        '<div class="locked-wrap">',
        '<div class="locked-content">',
        *items[1:],
        "</div>",
        _locked_overlay(subscribe_url),
        "</div>",
    ]


def _fmt_money(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return "n/a"
    return f"${number:,.2f}"


def _fmt_day(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "n/a"
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return stamp.strftime("%b %d")
    except Exception:
        return text[:10]


def market_news(limit: int = 12) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        for row in newsapi.market_headlines(limit):
            url = str(row.get("url") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            items.append(row)
    except Exception:
        logger.exception("NewsAPI market headlines failed")
    if len(items) < 10:
        try:
            for row in finnhub.general_news(max(limit, 12)):
                url = str(row.get("url") or "")
                if not url or url in seen:
                    continue
                seen.add(url)
                items.append(row)
                if len(items) >= max(limit, 12):
                    break
        except Exception:
            logger.exception("Finnhub general news fallback failed")
    out: list[dict[str, Any]] = []
    for row in items[: max(limit, 12)]:
        source = str(row.get("source") or "Wire").strip() or "Wire"
        headline = _clean_headline(row.get("headline"), source)
        if not headline:
            continue
        out.append(
            {
                "ticker": str(row.get("ticker") or "MARKET").upper(),
                "headline": headline,
                "summary": _distinct_summary(headline, row.get("summary"), source),
                "source": source,
                "url": row.get("url"),
            }
        )
    return out


def analyst_rating_changes(days: int = 30, limit: int = 15, extra_symbols: list[str] | None = None) -> list[dict[str, Any]]:
    symbols = []
    for symbol in [*(extra_symbols or []), *MOVER_SYMBOLS]:
        ticker = str(symbol or "").upper().strip()
        if ticker and ticker not in symbols:
            symbols.append(ticker)
    items: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    def _absorb(rows: list[dict[str, Any]]) -> None:
        for row in rows:
            ticker = str(row.get("ticker") or "").upper().strip()
            if not ticker:
                continue
            payload = {
                "ticker": ticker,
                "firm": row.get("firm") or "Analyst desk",
                "old_rating": row.get("old_rating") or "n/a",
                "new_rating": row.get("new_rating") or "n/a",
                "old_target": row.get("old_target"),
                "new_target": row.get("new_target"),
                "date": row.get("date"),
            }
            key = (payload["ticker"], payload["firm"], payload["old_rating"], payload["new_rating"], str(payload["date"] or ""))
            if key in seen:
                continue
            seen.add(key)
            items.append(payload)

    try:
        _absorb(finnhub.rating_target_changes(days=days, symbols=symbols, limit=limit))
    except Exception:
        logger.exception("Finnhub rating and target lookup failed")
    if len(items) < 5:
        for symbol in symbols:
            try:
                _absorb(yahoo_http.rating_target_changes(symbol, days=days, limit=6))
            except Exception:
                logger.exception("Yahoo rating history failed for %s", symbol)
            if len(items) >= limit:
                break
    if len(items) < 5:
        try:
            _absorb(finnhub.recommendation_shifts(symbols, limit=limit))
        except Exception:
            logger.exception("Finnhub consensus shift lookup failed")
    return items[:limit]


def compile_email_html(
    pick: NewsletterPick,
    movers: list[dict[str, Any]],
    earnings: list[dict[str, Any]],
    macro: dict[str, Any],
    insider_rows: list[dict[str, Any]] | None = None,
    institution_rows: list[dict[str, Any]] | None = None,
    scorecard: list[dict[str, Any]] | None = None,
    news_items: list[dict[str, Any]] | None = None,
    analyst_changes: list[dict[str, Any]] | None = None,
    preview: bool = False,
) -> str:
    day = pick.pick_date.strftime("%A, %B %d, %Y")
    site = settings.frontend_url.rstrip("/")
    subscribe = upgrade_url()
    parts = [
        "<html><head><style>",
        "body{font-family:Arial,sans-serif;max-width:700px;margin:0 auto;color:#0f172a;background:#ffffff;}",
        ".header{background:#042f2e;color:#ecfdf5;padding:20px;text-align:center;}",
        ".section{border:1px solid #d1d5db;margin:16px 0;padding:18px;border-radius:8px;}",
        ".section h3{color:#065f46;margin-top:0;}",
        ".note{background:#fff7ed;border:1px solid #fdba74;padding:12px;font-size:12px;margin:16px 0;}",
        ".item{background:#f8fafc;padding:12px;margin:10px 0;border-radius:6px;}",
        ".meta{font-size:12px;color:#64748b;margin-top:6px;}",
        ".locked-wrap{position:relative;overflow:hidden;border-radius:8px;margin-top:8px;}",
        ".locked-content{filter:blur(7px);opacity:.4;user-select:none;pointer-events:none;}",
        ".locked-overlay{position:absolute;left:0;right:0;top:0;bottom:0;background:rgba(255,255,255,.82);"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:18px;}",
        ".upgrade-btn{background:#065f46;color:#ffffff;text-decoration:none;padding:10px 16px;border-radius:6px;"
        "font-weight:bold;display:inline-block;margin-top:8px;}",
        "</style></head><body>",
        '<div class="header"><h2>Market Intelligence Brief</h2>',
        f"<p>{_esc(day)}</p></div>",
        '<div class="note"><strong>Disclaimer:</strong> Educational and informational purposes only. Not financial advice. ',
        "GetStockReport does not issue buy, sell, or hold recommendations. Consult a licensed advisor. Past performance is not future results.</div>",
    ]
    if preview:
        parts.append(
            '<div class="note"><strong>Limited preview:</strong> Business days 6–15 after signup. '
            f'<a href="{_esc(subscribe)}">Upgrade to Premium</a> for the full daily briefing.</div>'
        )
    news_blocks: list[str] = []
    for item in news_items or []:
        source = str(item.get("source") or "Wire")
        headline = _clean_headline(item.get("headline"), source)
        summary = _distinct_summary(headline, item.get("summary"), source)
        block = f"<strong>{_esc(item.get('ticker'))}</strong> — {_esc(headline)}"
        if summary:
            block += f"<br>{_esc(summary)}"
        news_blocks.append(
            '<div class="item">'
            f"{block}"
            f'<div class="meta">{_esc(source)} · '
            f'<a href="{_href(item.get("url"))}">Read the source</a></div>'
            "</div>"
        )
    parts.append('<div class="section"><h3>1. NEWS &amp; ALERTS</h3>')
    if not news_blocks:
        parts.append("<p>No market headlines were available for this window.</p>")
    else:
        parts.extend(_emit_items(news_blocks, preview, subscribe))
    parts.append("</div>")
    rating_blocks: list[str] = []
    for row in analyst_changes or []:
        rating_blocks.append(
            '<div class="item">'
            f"<strong>{_esc(row.get('ticker'))}</strong> — {_esc(row.get('firm'))} ({_esc(_fmt_day(row.get('date')))})<br>"
            f"Rating: {_esc(row.get('old_rating'))} → {_esc(row.get('new_rating'))}<br>"
            f"Target: {_esc(_fmt_money(row.get('old_target')))} → {_esc(_fmt_money(row.get('new_target')))}"
            "</div>"
        )
    parts.append('<div class="section"><h3>2. ANALYST RATINGS &amp; TARGETS</h3>')
    parts.append("<p><em>Third-party rating and target changes from the last 30 days. Not our recommendations.</em></p>")
    if not rating_blocks:
        parts.append("<p>No analyst rating or price-target changes were available for this window.</p>")
    else:
        parts.extend(_emit_items(rating_blocks, preview, subscribe))
    parts.append("</div>")
    mover_blocks: list[str] = []
    for mover in movers:
        change = float(mover.get("change_percent") or 0)
        direction = "higher" if change >= 0 else "lower"
        mover_blocks.append(
            '<div class="item">'
            f"<strong>{mover.get('ticker')}</strong> printed {abs(change):.1f}% {direction} versus the prior close.<br>"
            f"{mover.get('headline') or ''}<br>"
            f'<a href="{research_url(str(mover.get("ticker")))}">Open the research report</a>'
            "</div>"
        )
    parts.append('<div class="section"><h3>3. Tape alerts</h3>')
    if not mover_blocks:
        parts.append("<p>No large-cap tape movers were available for this window.</p>")
    else:
        parts.extend(_emit_items(mover_blocks, preview, subscribe))
    parts.append("</div>")
    insider_blocks: list[str] = []
    for row in insider_rows or []:
        amount = row.get("amount")
        money = f"${amount:,.0f}" if isinstance(amount, (int, float)) else "an unspecified amount"
        insider_blocks.append(
            '<div class="item">'
            f"<strong>{row.get('executive_name')}</strong> ({row.get('title')}) reported a {row.get('transaction_type')} "
            f"in {row.get('ticker')} totaling {money}."
            "</div>"
        )
    parts.append('<div class="section"><h3>4. Insider Form 4 activity</h3><p><em>Historical SEC filings only. Not a recommendation.</em></p>')
    if not insider_blocks:
        parts.append("<p>No recent Form 4 prints were available for the featured name.</p>")
    else:
        parts.extend(_emit_items(insider_blocks, preview, subscribe))
    parts.append("</div>")
    institution_blocks: list[str] = []
    for row in institution_rows or []:
        value = row.get("value")
        money = f"${value:,.0f}" if isinstance(value, (int, float)) else "n/a"
        institution_blocks.append(
            '<div class="item">'
            f"<strong>{row.get('fund_name')}</strong> reported a {row.get('ticker')} holding of {money} "
            f"(as of {row.get('report_date') or 'the latest 13F'})."
            "</div>"
        )
    parts.append('<div class="section"><h3>5. Institutional 13F holdings</h3><p><em>Lagging 13F snapshots. Informational only.</em></p>')
    if not institution_blocks:
        parts.append("<p>No 13F holder snapshot was available for the featured name.</p>")
    else:
        parts.extend(_emit_items(institution_blocks, preview, subscribe))
    parts.append("</div>")
    earnings_blocks: list[str] = []
    for row in earnings[:5]:
        estimate = row.get("eps_estimate")
        earnings_blocks.append(
            '<div class="item">'
            f"<strong>{row.get('date')}: {row.get('ticker')}</strong><br>"
            f"Consensus EPS estimate: {estimate if estimate is not None else 'n/a'}. "
            "Use this as a calendar marker for possible volatility, not as a directional view."
            "</div>"
        )
    parts.append('<div class="section"><h3>6. Earnings this week</h3>')
    if not earnings_blocks:
        parts.append("<p>No earnings dates were available for this window.</p>")
    else:
        parts.extend(_emit_items(earnings_blocks, preview, subscribe))
    parts.append("</div>")
    oil = macro.get("oil_price")
    oil_change = macro.get("oil_change")
    macro_block = (
        "<p>"
        f"Fed calendar: {macro.get('fed_event', 'n/a')}<br>"
        f"Oil: {oil if oil is not None else 'n/a'}"
        f"{f' ({oil_change:.1f}%)' if oil_change is not None else ''}"
        f"<br>VIX: {macro.get('vix', 'n/a')}<br>10Y yield: {macro.get('yield_10y', 'n/a')}</p>"
    )
    parts.append('<div class="section"><h3>7. Macro watch</h3>')
    parts.extend(_emit_items([macro_block], preview, subscribe))
    parts.append("</div>")
    featured_block = (
        f"<p><strong>{_esc(pick.ticker)}</strong> — {_esc(pick.reason)}</p>"
        f"<p>Coverage upgrades in the tape: {pick.analyst_upgrades} | Institutional flow (USD millions): {pick.institutional_buying}</p>"
        f"<p>Desk reading: {sentiment_label(pick.sentiment)}</p>"
        '<p class="note">Not a recommendation. Do your own research. '
        f'<a href="{research_url(pick.ticker)}">Read the full institutional report</a></p>'
    )
    parts.append('<div class="section"><h3>8. Featured research desk</h3>')
    parts.extend(_emit_items([featured_block], preview, subscribe))
    parts.append("</div>")
    score_blocks: list[str] = []
    for row in scorecard or []:
        score_blocks.append(
            '<div class="item">'
            f"{row.get('date')}: <strong>{row.get('ticker')}</strong> — {row.get('sentiment')}<br>{row.get('reason')}"
            "</div>"
        )
    parts.append('<div class="section"><h3>9. Recent featured names</h3><p><em>Transparency archive. Not performance advertising.</em></p>')
    if not score_blocks:
        parts.append("<p>No prior featured names are on file yet.</p>")
    else:
        parts.extend(_emit_items(score_blocks, preview, subscribe))
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
        email = normalize_email(user.email)
        if email.endswith("@example.com") or email.endswith("@test.com"):
            continue
        if (user.newsletter_email_preference or "daily") != "daily":
            continue
        if newsletter_access(user, db) == NEWSLETTER_ACCESS_SKIP:
            continue
        users.append(user)
    return users


def recipient_emails(db: Session, extra_emails: list[str] | None = None) -> list[tuple[str, User | None, str]]:
    mapped: dict[str, User | None] = {}
    forced: set[str] = set()
    for user in subscriber_query(db):
        mapped[normalize_email(user.email)] = user
    for row in db.scalars(select(PlanException)).all():
        address = normalize_email(row.email)
        if address.endswith("@example.com") or address.endswith("@test.com"):
            continue
        mapped.setdefault(address, None)
    for raw in extra_emails or []:
        address = normalize_email(raw)
        if not address:
            continue
        forced.add(address)
        mapped.setdefault(address, None)
    users_by_email = {
        normalize_email(user.email): user
        for user in db.scalars(select(User)).all()
        if not normalize_email(user.email).endswith(("@example.com", "@test.com"))
    }
    out: list[tuple[str, User | None, str]] = []
    for email, user in mapped.items():
        account = user or users_by_email.get(email)
        access = newsletter_access(account, db) if account is not None else NEWSLETTER_ACCESS_FULL
        if email in forced and access == NEWSLETTER_ACCESS_SKIP:
            access = NEWSLETTER_ACCESS_FULL
        if access == NEWSLETTER_ACCESS_SKIP:
            continue
        out.append((email, account, access))
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
        news_items = market_news()
        analyst_changes = analyst_rating_changes(extra_symbols=[pick.ticker])
        insiders = insider_activity(pick.ticker)
        institutions = institutional_flows(pick.ticker, pick)
        scorecard = weekly_scorecard(session, pick)
        html = compile_email_html(
            pick,
            movers,
            earnings,
            macro,
            insiders,
            institutions,
            scorecard,
            news_items=news_items,
            analyst_changes=analyst_changes,
        )
        preview_html: str | None = None
        upsert_issue(session, pick, html)
        sent = 0
        failed: list[str] = []
        full_sent = 0
        preview_sent = 0
        if send_email:
            subject = f"Market Brief: {pick.ticker} — {pick.pick_date.strftime('%b %d')}"
            recipients = recipient_emails(session, extra_emails)
            if any(access == NEWSLETTER_ACCESS_PREVIEW for _, _, access in recipients):
                preview_html = compile_email_html(
                    pick,
                    movers,
                    earnings,
                    macro,
                    insiders,
                    institutions,
                    scorecard,
                    news_items=news_items,
                    analyst_changes=analyst_changes,
                    preview=True,
                )
            for email, user, access in recipients:
                body = preview_html if access == NEWSLETTER_ACCESS_PREVIEW and preview_html is not None else html
                try:
                    delivered = _send_html_email(email, subject, body)
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
                if access == NEWSLETTER_ACCESS_PREVIEW:
                    preview_sent += 1
                else:
                    full_sent += 1
        session.commit()
        return {
            "status": "success",
            "emails_sent": sent,
            "full_sent": full_sent,
            "preview_sent": preview_sent,
            "failed": failed,
            "pick": pick.ticker,
            "date": pick.pick_date.isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        if owned:
            session.close()


def send_test_newsletter(to_email: str, db: Session | None = None) -> dict[str, Any]:
    address = normalize_email(to_email)
    if not address:
        return {"status": "invalid_email", "emails_sent": 0}
    owned = db is None
    session = db or SessionLocal()
    try:
        try:
            pick = get_pick(session)
        except Exception:
            logger.exception("Could not load today's newsletter pick")
            pick = None
        persist = pick is not None
        if pick is None:
            from types import SimpleNamespace

            pick = SimpleNamespace(
                pick_date=utc_today(),
                ticker="NVDA",
                reason="Test briefing used while no featured pick was on file for today.",
                analyst_upgrades=0,
                institutional_buying=0,
                sentiment="mixed",
            )
        movers = market_movers()
        earnings = earnings_this_week()
        macro = macro_watch()
        news_items = market_news()
        analyst_changes = analyst_rating_changes(extra_symbols=[pick.ticker])
        insiders = insider_activity(pick.ticker)
        institutions = institutional_flows(pick.ticker, pick if persist else None)
        scorecard = weekly_scorecard(session, pick) if persist else []
        html = compile_email_html(
            pick,
            movers,
            earnings,
            macro,
            insiders,
            institutions,
            scorecard,
            news_items=news_items,
            analyst_changes=analyst_changes,
        )
        if persist:
            upsert_issue(session, pick, html)
            session.commit()
        subject = f"[TEST] Market Brief: {pick.ticker} — {pick.pick_date.strftime('%b %d')}"
        delivered = _send_html_email(address, subject, html)
        return {
            "status": "success" if delivered else "send_failed",
            "emails_sent": 1 if delivered else 0,
            "to": address,
            "pick": pick.ticker,
            "date": pick.pick_date.isoformat(),
            "news_count": len(news_items),
            "analyst_count": len(analyst_changes),
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


def today_payload(db: Session, full_access: bool, user: User | None = None) -> dict[str, Any]:
    access = newsletter_access(user, db) if user is not None else NEWSLETTER_ACCESS_SKIP
    if full_access:
        access = NEWSLETTER_ACCESS_FULL
    show_briefing = access in {NEWSLETTER_ACCESS_FULL, NEWSLETTER_ACCESS_PREVIEW}
    pick = get_pick(db)
    if pick is None:
        return {
            "date": None,
            "ticker": None,
            "reason": None,
            "full_access": access == NEWSLETTER_ACCESS_FULL,
            "newsletter_access": access if show_briefing else "none",
        }
    payload: dict[str, Any] = {
        "date": pick.pick_date.isoformat(),
        "ticker": pick.ticker,
        "reason": pick.reason,
        "sentiment": sentiment_label(pick.sentiment),
        "research_path": research_path(pick.ticker),
        "issue_id": pick.issue_id,
        "full_access": access == NEWSLETTER_ACCESS_FULL,
        "newsletter_access": access if show_briefing else "none",
        "movers": [],
        "earnings": [],
        "macro": {},
        "news": [],
        "analyst_changes": [],
        "html": None,
    }
    if not show_briefing:
        return payload
    movers = market_movers()
    earnings = earnings_this_week()
    macro = macro_watch()
    news_items = market_news()
    analyst_changes = analyst_rating_changes(extra_symbols=[pick.ticker])
    preview = access == NEWSLETTER_ACCESS_PREVIEW
    payload["movers"] = movers[:1] if preview else movers
    payload["earnings"] = earnings[:1] if preview else earnings
    payload["macro"] = macro
    payload["news"] = news_items[:1] if preview else news_items
    payload["analyst_changes"] = analyst_changes[:1] if preview else analyst_changes
    payload["html"] = compile_email_html(
        pick,
        movers,
        earnings,
        macro,
        news_items=news_items,
        analyst_changes=analyst_changes,
        preview=preview,
    )
    return payload
