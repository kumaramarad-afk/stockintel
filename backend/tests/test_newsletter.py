from copy import deepcopy
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from sqlalchemy import select

from app.database import SessionLocal
from app.models import NewsletterPick, User
from main import app
from services.newsletter_service import (
    business_days_elapsed,
    compile_email_html,
    newsletter_access,
    recipient_emails,
    _distinct_summary,
)
from services.paywall import PLACEHOLDER, normalize_email
from services.providers.newsapi import extract_ticker, _two_sentences

client = TestClient(app)

AI = {
    "ticker": "NVDA",
    "available": True,
    "error": None,
    "data": {
        "what_the_data_shows": "Coverage remains constructive on the franchise. Cash generation continues to fund the buyback. Valuation still depends on services growth holding up.",
        "why_it_scores": "Coverage remains constructive on the franchise.",
        "key_risks": ["Export controls", "Customer concentration"],
        "upcoming_catalysts": ["Earnings"],
        "outlook": "Constructive",
    },
}


def _register(email: str | None = None) -> tuple[str, dict]:
    address = email or f"user-{uuid4().hex[:10]}@example.com"
    response = client.post(
        "/api/v1/users/register",
        json={"email": address, "full_name": "Jayanth", "password": "securepass"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["access_token"], body["user"]


def _insert_pick(ticker: str = "NVDA", pick_date: date | None = None) -> NewsletterPick:
    day = pick_date or datetime.now(timezone.utc).date()
    db = SessionLocal()
    try:
        existing = db.scalar(select(NewsletterPick).where(NewsletterPick.pick_date == day))
        if existing is not None:
            existing.ticker = ticker
            existing.reason = "Institutional flow and coverage revisions clustered around this name."
            db.commit()
            db.refresh(existing)
            return existing
        pick = NewsletterPick(
            pick_date=day,
            ticker=ticker,
            reason="Institutional flow and coverage revisions clustered around this name.",
            analyst_upgrades=4,
            institutional_buying=120.5,
            sentiment="bullish",
        )
        db.add(pick)
        db.commit()
        db.refresh(pick)
        return pick
    finally:
        db.close()


def test_compile_email_html_leads_with_news_and_ratings() -> None:
    pick = SimpleNamespace(
        pick_date=date(2026, 9, 13),
        ticker="NVDA",
        reason="Institutional flow and coverage revisions clustered around this name.",
        analyst_upgrades=4,
        institutional_buying=120.5,
        sentiment="bullish",
    )
    html = compile_email_html(
        pick,
        [],
        [],
        {"fed_event": "No scheduled Fed event on file"},
        news_items=[
            {
                "ticker": "AAPL",
                "headline": "Apple supplier news hits the tape",
                "summary": "A supplier update moved large-cap tech. Traders watched the follow-through.",
                "source": "Reuters",
                "url": "https://example.com/aapl-news",
            }
        ],
        analyst_changes=[
            {
                "ticker": "MSFT",
                "firm": "Goldman Sachs",
                "old_rating": "Neutral",
                "new_rating": "Buy",
                "old_target": 400,
                "new_target": 450,
                "date": "2026-09-01T00:00:00+00:00",
            }
        ],
    )
    assert html.index("1. NEWS") < html.index("2. ANALYST RATINGS") < html.index("3. Tape alerts")
    assert html.index("3. Tape alerts") < html.index("9. Recent featured names")
    assert "AAPL" in html
    assert "Reuters" in html
    assert "https://example.com/aapl-news" in html
    assert "Neutral" in html and "Buy" in html
    assert "$400.00" in html and "$450.00" in html


def test_newsapi_ticker_and_summary_helpers() -> None:
    assert extract_ticker("NVIDIA ($NVDA) climbs after data-center update") == "NVDA"
    assert extract_ticker("Broad market futures are mixed before the open") == "MARKET"
    summary = _two_sentences("First sentence. Second sentence. Third should drop.")
    assert summary == "First sentence. Second sentence."


def test_news_summary_does_not_repeat_headline() -> None:
    headline = "Oil prices jump more than 2% after new strikes on Saudi, Strait of Hormuz - Reuters"
    duplicate = "Oil prices jump more than 2% after new strikes on Saudi, Strait of Hormuz Reuters"
    assert _distinct_summary(headline, duplicate, "Reuters") == ""
    extra = _distinct_summary(
        headline,
        f"{duplicate}. Traders watched energy shares into the close.",
        "Reuters",
    )
    assert extra == "Traders watched energy shares into the close."
    pick = SimpleNamespace(
        pick_date=date(2026, 9, 13),
        ticker="NVDA",
        reason="Desk note.",
        analyst_upgrades=0,
        institutional_buying=0,
        sentiment="mixed",
    )
    html = compile_email_html(
        pick,
        [],
        [],
        {"fed_event": "n/a"},
        news_items=[
            {
                "ticker": "MARKET",
                "headline": headline,
                "summary": duplicate,
                "source": "Reuters",
                "url": "https://example.com/oil",
            }
        ],
    )
    assert html.count("Oil prices jump more than 2%") == 1
    assert "Strait of Hormuz - Reuters" not in html
    assert "Reuters · " in html


def test_business_days_count_weekdays_only() -> None:
    monday = date(2026, 9, 7)
    assert business_days_elapsed(monday, monday) == 1
    assert business_days_elapsed(monday, date(2026, 9, 11)) == 5
    assert business_days_elapsed(monday, date(2026, 9, 13)) == 5
    assert business_days_elapsed(monday, date(2026, 9, 14)) == 6
    assert business_days_elapsed(date(2026, 9, 12), date(2026, 9, 14)) == 1


def test_newsletter_access_follows_trial_windows() -> None:
    created = datetime(2026, 9, 7, tzinfo=timezone.utc)
    free = SimpleNamespace(
        is_active=True,
        plan="free",
        email="trial@example.com",
        newsletter_email_preference="daily",
        created_at=created,
    )
    premium = SimpleNamespace(**{**free.__dict__, "plan": "premium"})
    unsubscribed = SimpleNamespace(**{**free.__dict__, "newsletter_email_preference": "off"})
    assert newsletter_access(free, None, date(2026, 9, 11)) == "full"
    assert newsletter_access(free, None, date(2026, 9, 14)) == "preview"
    assert newsletter_access(free, None, date(2026, 9, 25)) == "preview"
    assert newsletter_access(free, None, date(2026, 9, 28)) == "skip"
    assert newsletter_access(premium, None, date(2026, 9, 28)) == "full"
    assert newsletter_access(unsubscribed, None, date(2026, 9, 8)) == "skip"


def test_recipient_emails_stop_after_trial_unless_premium() -> None:
    _, user = _register()
    db = SessionLocal()
    try:
        account = db.scalar(select(User).where(User.email == user["email"]))
        assert account is not None
        account.created_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
        db.add(account)
        db.commit()
        with patch("services.newsletter_service.utc_today", return_value=date(2026, 9, 14)):
            skipped = {row[0]: row[2] for row in recipient_emails(db)}
        assert normalize_email(user["email"]) not in skipped
        account.created_at = datetime(2026, 9, 7, tzinfo=timezone.utc)
        db.add(account)
        db.commit()
        with patch("services.newsletter_service.utc_today", return_value=date(2026, 9, 14)):
            preview = {row[0]: row[2] for row in recipient_emails(db)}
        assert preview[normalize_email(user["email"])] == "preview"
        account.plan = "premium"
        db.add(account)
        db.commit()
        with patch("services.newsletter_service.utc_today", return_value=date(2026, 9, 14)):
            paid = {row[0]: row[2] for row in recipient_emails(db)}
        assert paid[normalize_email(user["email"])] == "full"
    finally:
        db.close()


def test_preview_html_shows_first_item_and_upgrade_gate() -> None:
    pick = SimpleNamespace(
        pick_date=date(2026, 9, 14),
        ticker="NVDA",
        reason="Desk note.",
        analyst_upgrades=1,
        institutional_buying=10,
        sentiment="mixed",
    )
    html = compile_email_html(
        pick,
        [],
        [],
        {"fed_event": "n/a"},
        news_items=[
            {
                "ticker": "AAPL",
                "headline": "Visible headline",
                "summary": "First unique summary sentence.",
                "source": "Reuters",
                "url": "https://example.com/one",
            },
            {
                "ticker": "MSFT",
                "headline": "Locked headline",
                "summary": "Second unique summary sentence.",
                "source": "Bloomberg",
                "url": "https://example.com/two",
            },
        ],
        preview=True,
    )
    news_at = html.index("1. NEWS")
    locked_at = html.index('class="locked-wrap"')
    visible_at = html.index("Visible headline")
    hidden_at = html.index("Locked headline")
    assert visible_at > news_at
    assert locked_at > visible_at
    assert hidden_at > locked_at
    assert "Upgrade to Premium" in html
    assert "Limited preview" in html


def test_premium_gets_full_unlimited_research() -> None:
    token, _ = _register()
    headers = {"Authorization": f"Bearer {token}"}
    upgraded = client.post("/api/v1/users/subscribe", json={"plan": "premium"}, headers=headers)
    assert upgraded.status_code == 200
    assert upgraded.json()["plan"] == "premium"
    with patch("app.routers.research.generate_section", return_value=deepcopy(AI)):
        response = client.get("/api/v1/research/report/NVDA/ai", headers=headers)
    body = response.json()
    assert body["access"]["entitlement"] == "full"
    assert body["access"]["pro"] is True
    assert body["access"]["reports_remaining"] == 5
    assert "Valuation still depends" in body["data"]["what_the_data_shows"]


def test_archive_requires_premium() -> None:
    token, _ = _register()
    headers = {"Authorization": f"Bearer {token}"}
    denied = client.get("/api/v1/newsletter/archive", headers=headers)
    assert denied.status_code == 403
    client.post("/api/v1/users/subscribe", json={"plan": "premium"}, headers=headers)
    allowed = client.get("/api/v1/newsletter/archive", headers=headers)
    assert allowed.status_code == 200


def test_newsletter_archive_links_to_research() -> None:
    token, _ = _register()
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/users/subscribe", json={"plan": "premium"}, headers=headers)
    _insert_pick("NVDA", date.today())
    response = client.get("/api/v1/newsletter/archive", headers=headers)
    assert response.status_code == 200, response.text
    rows = response.json()
    assert rows[0]["ticker"] == "NVDA"
    assert rows[0]["research_path"] == "/research/NVDA"


def test_unsubscribe_keeps_research_access() -> None:
    token, _ = _register()
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/users/subscribe", json={"plan": "premium"}, headers=headers)
    stopped = client.post("/api/v1/newsletter/unsubscribe", headers=headers)
    assert stopped.status_code == 200
    status = client.get("/api/v1/newsletter/status", headers=headers).json()
    assert status["tier"] == "premium"
    assert status["newsletter_enabled"] is False
    with patch("app.routers.research.generate_section", return_value=deepcopy(AI)):
        report = client.get("/api/v1/research/report/NVDA/ai", headers=headers)
    assert report.json()["access"]["entitlement"] == "full"


def test_today_teaser_is_public() -> None:
    _insert_pick("AAPL")
    response = client.get("/api/v1/newsletter/today")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] in {"AAPL", "NVDA"}
    assert body["full_access"] is False
    assert body["html"] is None


def test_checkout_newsletter_plan_is_forwarded() -> None:
    token, _ = _register()
    with patch(
        "services.stripe_billing.create_checkout_session",
        return_value="https://checkout.stripe.com/c/newsletter",
    ) as mocked:
        response = client.post("/api/checkout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert mocked.call_args.args[4] == "premium"


def test_webhook_activates_newsletter_pro() -> None:
    token, user = _register()
    headers = {"Authorization": f"Bearer {token}"}
    completed = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": user["id"], "plan": "newsletter_pro"},
                "customer": "cus_news",
                "subscription": "sub_news",
                "status": "complete",
                "payment_status": "paid",
            }
        },
    }
    with (
        patch("app.routers.webhooks.stripe_billing.parse_webhook", return_value=completed),
        patch("app.routers.webhooks.stripe_billing.retrieve_checkout_session", return_value=completed["data"]["object"]),
    ):
        assert client.post("/api/webhooks/stripe", json=completed).status_code == 200
    me = client.get("/api/v1/users/me", headers=headers).json()
    assert me["plan"] == "premium"
    assert me["newsletter_subscription_status"] == "active"


def test_generate_without_key_is_unavailable() -> None:
    response = client.post("/api/v1/newsletter/admin/generate")
    assert response.status_code in {401, 503}


def test_guest_report_still_redacts() -> None:
    analysts = {
        "ticker": "AAPL",
        "available": True,
        "error": None,
        "data": {"average_target": 250.0, "high_target": 280.0, "low_target": 190.0},
    }
    with patch("app.routers.research.generate_section", return_value=deepcopy(analysts)):
        body = client.get("/api/v1/research/report/AAPL/analysts").json()
    assert body["data"]["average_target"] == PLACEHOLDER


def test_plan_exception_grants_premium_without_stripe() -> None:
    token, user = _register()
    headers = {"Authorization": f"Bearer {token}"}
    admin_token, admin = _register()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    db = SessionLocal()
    try:
        account = db.scalar(select(User).where(User.email == admin["email"]))
        account.is_admin = True
        db.add(account)
        db.commit()
    finally:
        db.close()
    added = client.post(
        "/api/v1/admin/plan-exceptions",
        json={"email": user["email"], "note": "Complimentary Premium ($12)"},
        headers=admin_headers,
    )
    assert added.status_code == 200, added.text
    me = client.get("/api/v1/users/me", headers=headers).json()
    assert me["plan"] == "premium"
    assert me["complimentary"] is True
    with patch("app.routers.research.generate_section", return_value=deepcopy(AI)):
        report = client.get("/api/v1/research/report/AAPL/ai", headers=headers)
    assert report.json()["access"]["entitlement"] == "full"
    assert client.get("/api/v1/newsletter/archive", headers=headers).status_code == 200
