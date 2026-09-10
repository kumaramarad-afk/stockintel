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
    assert me.json()["reports_generated"] == 0
    assert me.json()["reports_remaining"] == 5
    upgraded = client.post("/api/v1/users/subscribe", json={"plan": "pro"}, headers=headers)
    assert upgraded.status_code == 200
    assert upgraded.json()["plan"] == "pro"


def test_auth_me_alias_and_requires_auth() -> None:
    email = f"jayanth-{uuid4().hex[:10]}@example.com"
    register = client.post(
        "/api/v1/users/register",
        json={"email": email, "full_name": "Jayanth", "password": "securepass"},
    )
    token = register.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["plan"] == "free"
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/users/me").status_code == 401
