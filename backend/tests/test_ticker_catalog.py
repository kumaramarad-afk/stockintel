from services.ticker_catalog import resolve_query_to_ticker, search_tickers


def test_resolve_company_name_and_ticker():
    assert resolve_query_to_ticker("AAPL") == "AAPL"
    assert resolve_query_to_ticker("apple") == "AAPL"
    assert resolve_query_to_ticker("NVIDIA") == "NVDA"
    assert resolve_query_to_ticker("google") == "GOOGL"
    assert resolve_query_to_ticker("Berkshire Hathaway") == "BRK.B"


def test_search_returns_ranked_hits():
    hits = search_tickers("micro")
    tickers = [row["ticker"] for row in hits]
    assert "MSFT" in tickers or "MSTR" in tickers
    assert hits[0]["name"]
