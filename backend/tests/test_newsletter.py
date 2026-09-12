from copy import deepcopy
from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from sqlalchemy import select

from app.database import SessionLocal
from app.models import NewsletterPick, User
from main import app
from services.paywall import PLACEHOLDER

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
    assert rows[0]["research_path"] == "/research?ticker=NVDA"


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
