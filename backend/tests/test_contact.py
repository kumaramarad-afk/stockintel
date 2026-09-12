from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

PAYLOAD = {
    "full_name": "Jayanth Kumar",
    "email": "kumar.amarad@gmail.com",
    "topic": "billing",
    "message": "I have a question about the Premium subscription and the daily briefing archive.",
}


def test_contact_sends_to_support() -> None:
    with patch("app.routers.contact._send_html_email", return_value=True) as mocked:
        response = client.post("/api/v1/contact", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json()["status"] == "received"
    assert mocked.call_args.args[0] == "support@getstockreport.com"
    assert "Billing" in mocked.call_args.args[1]
    assert mocked.call_args.kwargs["reply_to"] == "kumar.amarad@gmail.com"


def test_contact_honeypot_is_silent() -> None:
    with patch("app.routers.contact._send_html_email", return_value=True) as mocked:
        response = client.post("/api/v1/contact", json={**PAYLOAD, "company": "spam-bot"})
    assert response.status_code == 200
    mocked.assert_not_called()


def test_contact_rejects_short_message() -> None:
    response = client.post("/api/v1/contact", json={**PAYLOAD, "message": "Hi"})
    assert response.status_code == 422
