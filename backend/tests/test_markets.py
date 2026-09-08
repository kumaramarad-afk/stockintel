from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_market_quotes_returns_named_indices() -> None:
    sample = {
        "symbol": "^GSPC",
        "name": "S&P 500",
        "price": 5601.25,
        "previous_close": 5550.1,
        "change_percent": 0.92,
    }
    with patch("app.routers.markets.yahoo_http.spark_quote", return_value=sample):
        response = client.get("/api/v1/markets/quotes?symbols=%5EGSPC")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["name"] == "S&P 500"
    assert body[0]["price"] == 5601.25
    assert body[0]["change_percent"] == 0.92
