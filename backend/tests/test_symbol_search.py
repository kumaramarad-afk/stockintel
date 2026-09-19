from services.symbol_search import search_us_symbols


def test_search_us_includes_micron_and_sandisk():
    micron = [row["ticker"] for row in search_us_symbols("micron", limit=10)]
    assert "MU" in micron
    sandisk = [row["ticker"] for row in search_us_symbols("sandisk", limit=10)]
    assert "SNDK" in sandisk


def test_search_us_still_ranks_catalog_first():
    apple = search_us_symbols("apple", limit=5)
    assert apple[0]["ticker"] == "AAPL"
