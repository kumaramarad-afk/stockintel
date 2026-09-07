from services.language import analyst_action_row, days_since, display_outlook, outlook_from_grade, scrub_copy, signal_from_score, stars_from_grade


def test_signal_from_score_bands() -> None:
    assert signal_from_score(75)["label"] == "BULLISH CONSENSUS"
    assert signal_from_score(100)["emoji"] == "🟢"
    assert signal_from_score(50)["label"] == "MIXED SIGNALS"
    assert signal_from_score(74)["tone"] == "amber"
    assert signal_from_score(49)["label"] == "BEARISH CONSENSUS"
    assert signal_from_score(0)["emoji"] == "🔴"


def test_outlook_and_stars() -> None:
    assert outlook_from_grade("Overweight") == "bullish"
    assert outlook_from_grade("Equal Weight") == "neutral"
    assert outlook_from_grade("Underperform") == "bearish"
    assert display_outlook("Buy") == "Bullish"
    assert display_outlook("Hold") == "Neutral"
    assert stars_from_grade("Outperform") == 5
    assert stars_from_grade("Neutral") == 3
    assert stars_from_grade("Strong Sell") == 1


def test_scrub_copy_removes_banned_words() -> None:
    cleaned = scrub_copy("We recommend a buy rating. You should not sell or hold or invest.")
    lowered = cleaned.lower()
    for word in ("buy", "sell", "hold", "invest", "recommend", "you should"):
        assert word not in lowered


def test_analyst_action_row_direction() -> None:
    row = analyst_action_row(
        {
            "name": "Jane Doe",
            "firm": "Example Capital",
            "to_grade": "Overweight",
            "previous_target": 180,
            "price_target": 210,
            "action": "up",
            "date": "2026-09-01T00:00:00+00:00",
        }
    )
    assert row["direction"] == "raised"
    assert row["outlook_label"] == "Bullish"
    assert row["stars"] == 4
    assert days_since("2026-09-01T00:00:00+00:00") is not None
