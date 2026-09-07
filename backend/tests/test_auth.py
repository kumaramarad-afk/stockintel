from uuid import uuid4

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_register_login_and_subscribe() -> None:
    email = f"jayanth-{uuid4().hex[:10]}@example.com"
    register = client.post(
        "/api/v1/users/register",
        json={"email": email, "full_name": "Jayanth", "password": "securepass"},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["plan"] == "free"
    assert me.json()["reports_limit"] == 5
    upgraded = client.post("/api/v1/users/subscribe", json={"plan": "pro"}, headers=headers)
    assert upgraded.status_code == 200
    assert upgraded.json()["plan"] == "pro"


def test_me_requires_auth() -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
