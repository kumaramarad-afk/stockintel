from services.ticker_catalog import TICKER_NAMES, resolve_query_to_ticker, search_tickers


def test_resolve_company_name_and_ticker():
    assert resolve_query_to_ticker("AAPL") == "AAPL"
    assert resolve_query_to_ticker("apple") == "AAPL"
    assert resolve_query_to_ticker("NVIDIA") == "NVDA"
    assert resolve_query_to_ticker("google") == "GOOGL"
    assert resolve_query_to_ticker("Berkshire Hathaway") == "BRK.B"


def test_search_ranking_and_empty():
    assert search_tickers("AAPL")[0]["ticker"] == "AAPL"
    assert search_tickers("aapl")[0]["ticker"] == "AAPL"
    assert search_tickers("apple")[0]["ticker"] == "AAPL"
    assert search_tickers("tesla")[0]["ticker"] == "TSLA"
    assert "GME" in [row["ticker"] for row in search_tickers("gm")]
    micro = [row["ticker"] for row in search_tickers("micro", limit=15)]
    assert "MSTR" in micro and "SMCI" in micro
    empty = search_tickers("")
    assert len(empty) == len(TICKER_NAMES)
    assert empty[0]["ticker"] < empty[-1]["ticker"]
    assert search_tickers("nonexistentzzzz") == []


def test_search_returns_company_name_field():
    hits = search_tickers("apple")
    assert hits[0]["company_name"] == "Apple Inc."
    assert hits[0]["name"] == "Apple Inc."
