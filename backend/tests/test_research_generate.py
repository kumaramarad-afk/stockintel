from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.scoring import composite
from services.stock_service import score_headlines

client = TestClient(app)


def test_generate_research_validates_ticker() -> None:
    response = client.post("/api/v1/research/generate", json={"ticker": "???"})
    assert response.status_code == 422


def test_report_section_rejects_bad_ticker() -> None:
    response = client.get("/api/v1/research/report/AAPL_X/header")
    assert response.status_code == 422


def test_report_section_unknown() -> None:
    response = client.get("/api/v1/research/report/AAPL/not-a-section")
    assert response.status_code == 404


def test_report_header_section() -> None:
    payload = {
        "ticker": "AAPL",
        "available": True,
        "error": None,
        "data": {
            "name": "Apple Inc.",
            "ticker": "AAPL",
            "price": 229.15,
            "change_amount": 2.81,
            "change_percent": 1.24,
            "composite_score": 74,
            "scores": {"fundamental": 80, "technical": 70, "analyst": 75, "institutional": 72, "sentiment": 73},
            "risk_flags": [],
        },
    }
    with patch("app.routers.research.generate_section", return_value=payload):
        response = client.get("/api/v1/research/report/aapl/header")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["data"]["composite_score"] == 74


def test_report_section_unavailable() -> None:
    payload = {"ticker": "AAPL", "available": False, "error": "Data unavailable", "data": None}
    with patch("app.routers.research.generate_section", return_value=payload):
        response = client.get("/api/v1/research/report/AAPL/sentiment")
    assert response.status_code == 200
    assert response.json()["available"] is False


def test_generate_research_returns_structured_report() -> None:
    payload = {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "current_price": {
            "price": 229.15,
            "change_percent": 1.24,
            "currency": "USD",
            "previous_close": 226.34,
            "day_high": 230.0,
            "day_low": 225.5,
            "volume": 48_000_000,
            "as_of": "2026-09-06T20:00:00+00:00",
        },
        "analyst_ratings": {
            "consensus": "buy",
            "target_mean": 250.0,
            "target_high": 280.0,
            "target_low": 190.0,
            "number_of_analysts": 36,
            "distribution": {"buy": 24, "hold": 10, "sell": 2},
        },
        "financials": {
            "pe_ratio": 32.1,
            "market_cap": 3_500_000_000_000,
            "revenue": 394_000_000_000,
            "eps": 7.09,
            "profit_margin": 0.24,
            "source": "alpha_vantage",
        },
        "report": "## Investment Thesis\nApple remains a high-quality compounder.",
    }
    with patch("app.routers.research.generate_stock_research", return_value=payload):
        response = client.post("/api/v1/research/generate", json={"ticker": "aapl"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert "Investment Thesis" in body["report"]


def test_generate_research_unknown_ticker() -> None:
    from services.stock_service import TickerNotFoundError

    with patch(
        "app.routers.research.generate_stock_research",
        side_effect=TickerNotFoundError("No market data found for ZZZX."),
    ):
        response = client.post("/api/v1/research/generate", json={"ticker": "ZZZX"})

    assert response.status_code == 404
    assert "ZZZX" in response.json()["detail"]


def test_headline_sentiment_score_is_0_to_100() -> None:
    payload = score_headlines(
        [
            {"headline": "Apple beats estimates as iPhone sales surge"},
            {"headline": "Shares drop after lawsuit warning"},
            {"headline": "Company announces quarterly results"},
        ]
    )
    assert payload["overall_score"] is not None
    assert 0 <= payload["overall_score"] <= 100
    assert payload["positive_count"] == 1
    assert payload["negative_count"] == 1
    all_neutral = score_headlines([{"headline": "Apple files 10-K with the SEC"}])
    assert all_neutral["overall_score"] == 50


def test_composite_score_color_bands() -> None:
    high = composite({"a": 80, "b": 90, "c": 85})
    mid = composite({"a": 60, "b": 65})
    low = composite({"a": 20, "b": 30})
    assert high is not None and high > 70
    assert mid is not None and 51 <= mid <= 70
    assert low is not None and low <= 50
