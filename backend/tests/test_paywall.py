from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from services.paywall import PLACEHOLDER

client = TestClient(app)

ANALYSTS = {
    "ticker": "AAPL",
    "available": True,
    "error": None,
    "data": {
        "consensus": "bullish",
        "total_analysts": 36,
        "average_target": 250.0,
        "high_target": 280.0,
        "low_target": 190.0,
        "upside_pct": 12.4,
        "recent_actions": [
            {
                "name": "Katy Huberty",
                "firm": "Morgan Stanley",
                "stars": 5,
                "previous_target": 220.0,
                "new_target": 245.0,
                "direction": "raised",
                "outlook_label": "Positive",
                "days_ago": 1,
            }
        ],
        "top_analysts": [
            {
                "name": "Katy Huberty",
                "firm": "Morgan Stanley",
                "stars": 5,
                "accuracy_pct": 78,
                "current_target": 245.0,
                "sentiment": "Constructive on services mix",
            }
        ],
    },
}

AI = {
    "ticker": "AAPL",
    "available": True,
    "error": None,
    "data": {
        "what_the_data_shows": "Coverage remains constructive on the franchise. Cash generation continues to fund the buyback. Valuation still depends on services growth holding up.",
        "why_it_scores": "Coverage remains constructive on the franchise. Cash generation continues to fund the buyback.",
        "key_risks": ["China demand slows", "Regulatory pressure on the App Store"],
        "upcoming_catalysts": ["September product event", "October earnings"],
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


def test_guest_report_redacts_targets_on_backend() -> None:
    with patch("app.routers.research.generate_section", return_value=deepcopy(ANALYSTS)):
        response = client.get("/api/v1/research/report/AAPL/analysts")
    assert response.status_code == 200
    body = response.json()
    assert body["access"]["entitlement"] == "public"
    assert body["data"]["consensus"] == "bullish"
    assert body["data"]["average_target"] == PLACEHOLDER
    assert body["data"]["high_target"] == PLACEHOLDER
    assert body["data"]["recent_actions"][0]["new_target"] == PLACEHOLDER
    assert body["data"]["recent_actions"][0]["direction"] is None
    assert body["data"]["top_analysts"][0]["name"] == "Katy Huberty"
    assert body["data"]["top_analysts"][0]["current_target"] == PLACEHOLDER


def test_free_user_gets_basic_preview_and_redacted_pro_fields() -> None:
    token, _ = _register()
    headers = {"Authorization": f"Bearer {token}"}
    with patch("app.routers.research.generate_section", return_value=deepcopy(AI)):
        response = client.get("/api/v1/research/report/AAPL/ai", headers=headers)
    body = response.json()
    assert body["access"]["entitlement"] == "basic"
    assert body["access"]["reports_used"] == 1
    assert body["access"]["reports_generated"] == 1
    assert body["access"]["reports_remaining"] == 4
    preview = body["data"]["what_the_data_shows"]
    assert "Coverage remains constructive" in preview
    assert "Valuation still depends" not in preview
    assert body["data"]["key_risks"] == [PLACEHOLDER, PLACEHOLDER]


def test_free_quota_locks_sixth_unique_ticker() -> None:
    token, user = _register()
    headers = {"Authorization": f"Bearer {token}"}
    assert user["reports_generated"] == 0
    assert user["reports_remaining"] == 5
    tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META"]
    statuses = []
    for symbol in tickers:
        payload = deepcopy(ANALYSTS)
        payload["ticker"] = symbol
        with patch("app.routers.research.generate_section", return_value=payload):
            response = client.get(f"/api/v1/research/report/{symbol}/analysts", headers=headers)
        statuses.append((response.status_code, response.json()))
    assert [item[0] for item in statuses[:5]] == [200] * 5
    assert statuses[5][0] == 403
    assert statuses[5][1]["detail"] == "Free report limit reached (5/5). Please upgrade to continue."
    me = client.get("/api/v1/users/me", headers=headers).json()
    assert me["reports_generated"] == 5
    assert me["reports_used"] == 5
    assert me["reports_remaining"] == 0
    with patch("app.routers.research.generate_section", return_value=deepcopy(ANALYSTS)):
        again = client.get("/api/v1/research/report/AAPL/analysts", headers=headers)
    assert again.status_code == 200
    assert again.json()["access"]["entitlement"] == "basic"


def test_pro_user_sees_unredacted_targets() -> None:
    token, _ = _register()
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/users/subscribe", json={"plan": "pro"}, headers=headers)
    with patch("app.routers.research.generate_section", return_value=deepcopy(ANALYSTS)):
        response = client.get("/api/v1/research/report/AAPL/analysts", headers=headers)
    body = response.json()
    assert body["access"]["entitlement"] == "full"
    assert body["data"]["average_target"] == 250.0
    assert body["data"]["recent_actions"][0]["direction"] == "raised"


def test_checkout_requires_auth() -> None:
    response = client.post("/api/checkout")
    assert response.status_code == 401


def test_checkout_without_stripe_is_unavailable() -> None:
    token, _ = _register()
    with patch("services.stripe_billing.create_checkout_session", side_effect=RuntimeError("Stripe is not configured")):
        response = client.post("/api/checkout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503


def test_checkout_returns_session_url() -> None:
    token, _ = _register()
    with patch("services.stripe_billing.create_checkout_session", return_value="https://checkout.stripe.com/c/test"):
        response = client.post("/api/checkout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["url"] == "https://checkout.stripe.com/c/test"


def test_stripe_webhook_upgrades_and_cancels() -> None:
    token, user = _register()
    headers = {"Authorization": f"Bearer {token}"}
    completed = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": user["id"]},
                "customer": "cus_test",
                "subscription": "sub_test",
            }
        },
    }
    with patch("app.routers.webhooks.stripe_billing.parse_webhook", return_value=completed):
        assert client.post("/api/webhooks/stripe", json=completed).status_code == 200
    assert client.get("/api/v1/users/me", headers=headers).json()["plan"] == "pro"
    deleted = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test",
                "customer": "cus_test",
                "metadata": {"user_id": user["id"]},
            }
        },
    }
    with patch("app.routers.webhooks.stripe_billing.parse_webhook", return_value=deleted):
        assert client.post("/api/webhooks/stripe", json=deleted).status_code == 200
    assert client.get("/api/v1/users/me", headers=headers).json()["plan"] == "free"


def test_google_oauth_creates_free_account() -> None:
    profile = {
        "email": f"google-{uuid4().hex[:8]}@example.com",
        "full_name": "Google User",
        "subject": f"sub-{uuid4().hex}",
    }
    with patch("services.oauth.verify_google_id_token", return_value=profile):
        response = client.post("/api/v1/auth/oauth", json={"provider": "google", "id_token": "fake-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == profile["email"]
    assert body["user"]["plan"] == "free"
    assert body["user"]["reports_limit"] == 5
    assert body["user"]["oauth_provider"] == "google"


def test_billing_portal_requires_auth() -> None:
    response = client.post("/api/billing/portal")
    assert response.status_code == 401


def test_billing_portal_requires_stripe_customer() -> None:
    token, _ = _register()
    response = client.post("/api/billing/portal", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400


def test_checkout_success_url_includes_session_id() -> None:
    token, _ = _register()
    with patch("services.stripe_billing.create_checkout_session", return_value="https://checkout.stripe.com/c/test") as mocked:
        response = client.post("/api/checkout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    success_url = mocked.call_args.args[2]
    assert "upgraded=1" in success_url
    assert "{CHECKOUT_SESSION_ID}" in success_url


def test_stripe_webhook_upgrades_nested_customer_object() -> None:
    token, user = _register()
    headers = {"Authorization": f"Bearer {token}"}
    session = {
        "id": "cs_nested",
        "status": "complete",
        "payment_status": "paid",
        "metadata": {"user_id": user["id"]},
        "customer": {"id": "cus_nested"},
        "subscription": {"id": "sub_nested"},
    }
    completed = {"type": "checkout.session.completed", "data": {"object": session}}
    with (
        patch("app.routers.webhooks.stripe_billing.parse_webhook", return_value=completed),
        patch("app.routers.webhooks.stripe_billing.retrieve_checkout_session", return_value=session),
    ):
        assert client.post("/api/webhooks/stripe", json=completed).status_code == 200
    me = client.get("/api/v1/users/me", headers=headers).json()
    assert me["plan"] == "pro"


def test_verify_session_requires_auth() -> None:
    response = client.post("/api/v1/payments/verify-session", json={"session_id": "cs_test"})
    assert response.status_code == 401


def test_verify_session_upgrades_plan_when_webhook_is_late() -> None:
    token, user = _register()
    headers = {"Authorization": f"Bearer {token}"}
    paid = {
        "id": "cs_verify",
        "status": "complete",
        "payment_status": "paid",
        "metadata": {"user_id": user["id"]},
        "client_reference_id": user["id"],
        "customer": "cus_verify",
        "subscription": "sub_verify",
        "customer_email": user["email"],
    }
    with patch("app.routers.checkout.stripe_billing.find_paid_checkout_session", return_value=paid):
        response = client.post(
            "/api/v1/payments/verify-session",
            json={"session_id": "cs_verify"},
            headers=headers,
        )
    assert response.status_code == 200, response.text
    assert response.json()["plan"] == "pro"
    assert client.get("/api/v1/auth/me", headers=headers).json()["plan"] == "pro"


def test_billing_portal_returns_session_url() -> None:
    token, user = _register()
    headers = {"Authorization": f"Bearer {token}"}
    completed = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": user["id"]},
                "customer": "cus_portal",
                "subscription": "sub_portal",
            }
        },
    }
    with patch("app.routers.webhooks.stripe_billing.parse_webhook", return_value=completed):
        assert client.post("/api/webhooks/stripe", json=completed).status_code == 200
    with patch(
        "services.stripe_billing.create_portal_session",
        return_value="https://billing.stripe.com/p/session/test",
    ) as portal:
        response = client.post("/api/billing/portal", headers=headers)
    assert response.status_code == 200
    assert response.json()["url"] == "https://billing.stripe.com/p/session/test"
    portal.assert_called_once()
    assert portal.call_args.args[0] == "cus_portal"
    assert portal.call_args.args[1].endswith("/account")
