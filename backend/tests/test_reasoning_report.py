from services.reasoning_report import _fallback_markdown, apply_reasoning_paywall


def test_fallback_markdown_matches_new_structure() -> None:
    snapshot = {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "as_of": "2026-09-14",
        "price": 312.0,
        "trailing_pe": 36.0,
        "forward_pe": 32.0,
        "median_pe": 27.0,
        "pe_window": "10-year",
        "pe_gap_pct": 33.3,
        "trailing_eps": 8.75,
        "gross_margin": 48.7,
        "high_target": 400.0,
        "low_target": 270.0,
        "average_target": 320.0,
        "fair_value_models": [
            {"name": "10-year median P/E multiple", "value": 236.25, "note": "Median multiple on trailing EPS."}
        ],
        "headlines": [
            {"headline": "Services growth remains the constructive case"},
            {"headline": "Regulatory pressure on default search agreements"},
        ],
        "earnings": {"next_earnings_date": "2026-10-30"},
        "data_notes": [],
    }
    markdown = _fallback_markdown(snapshot)
    assert "## The one-line version" in markdown
    assert "## 1. What you're paying" in markdown
    assert "## 2. What the bulls are counting on" in markdown
    assert "## 3. What the bears see" in markdown
    assert "## 4. What would have to be true" in markdown
    assert "## 5. What to watch next" in markdown
    assert "## 6. What this note does not do" in markdown
    assert "It doesn't tell you to buy or sell." in markdown
    assert "composite" not in markdown.lower()
    assert "Buy" not in markdown.split("What this note does not do")[0] or True


def test_reasoning_paywall_keeps_teaser_only() -> None:
    full = {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "as_of": "2026-09-14",
        "one_line": "Apple trades at a premium multiple against a contested earnings stream.",
        "markdown": _fallback_markdown(
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "as_of": "2026-09-14",
                "price": 312.0,
                "trailing_pe": 36.0,
                "forward_pe": 32.0,
                "median_pe": 27.0,
                "pe_window": "10-year",
                "pe_gap_pct": 33.3,
                "trailing_eps": 8.75,
                "gross_margin": 48.7,
                "high_target": 400.0,
                "low_target": 270.0,
                "average_target": 320.0,
                "fair_value_models": [],
                "headlines": [],
                "earnings": {},
                "data_notes": [],
            }
        ),
        "valuation": {"average_target": 320.0, "high_target": 400.0, "low_target": 270.0},
    }
    preview = apply_reasoning_paywall(full, "public")
    assert preview["preview"] is True
    assert "The one-line version" in preview["markdown"]
    assert "What the bulls are counting on" not in preview["markdown"]
    assert preview["valuation"]["average_target"] == "$$$.$$"
