from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from services.numbers import to_float

_BANNED = re.compile(
    r"\b(strong\s+)?(buy|sell|hold)s?\b|\bwe recommend\b|\byou should\b|\binvest(?:ment|ing|or|s)?\b",
    re.I,
)

_BULLISH = (
    "outperform",
    "overweight",
    "positive",
    "accumulate",
    "long-term",
    "sector outperform",
    "market outperform",
    "strong buy",
    "buy",
)
_BEARISH = (
    "underperform",
    "underweight",
    "negative",
    "reduce",
    "avoid",
    "strong sell",
    "sell",
)
_NEUTRAL = (
    "neutral",
    "hold",
    "equal-weight",
    "equal weight",
    "market perform",
    "sector perform",
    "peer perform",
    "in-line",
    "mixed",
    "sector weight",
)


def outlook_from_grade(grade: str | None) -> str:
    text = (grade or "").lower().replace("_", " ").strip()
    if not text:
        return "neutral"
    if any(token in text for token in _BEARISH):
        return "bearish"
    if any(token in text for token in _BULLISH):
        return "bullish"
    if any(token in text for token in _NEUTRAL):
        return "neutral"
    return "neutral"


def display_outlook(grade: str | None) -> str:
    outlook = outlook_from_grade(grade)
    return {"bullish": "Bullish", "neutral": "Neutral", "bearish": "Bearish"}[outlook]


def stars_from_grade(grade: str | None) -> int:
    outlook = outlook_from_grade(grade)
    text = (grade or "").lower()
    if outlook == "bullish":
        return 5 if "strong" in text or "outperform" in text else 4
    if outlook == "bearish":
        return 1 if "strong" in text else 2
    return 3


def signal_from_score(score: float | None) -> dict[str, str]:
    if score is None:
        return {"label": "MIXED SIGNALS", "emoji": "🟡", "tone": "amber"}
    if score >= 75:
        return {"label": "BULLISH CONSENSUS", "emoji": "🟢", "tone": "green"}
    if score >= 50:
        return {"label": "MIXED SIGNALS", "emoji": "🟡", "tone": "amber"}
    return {"label": "BEARISH CONSENSUS", "emoji": "🔴", "tone": "red"}


def days_since(iso_date: str | None, now: datetime | None = None) -> int | None:
    if not iso_date:
        return None
    stamp = now or datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0, int((stamp - parsed).total_seconds() // 86400))


def direction_from_targets(previous: float | None, current: float | None, action: str | None) -> str:
    if previous is not None and current is not None:
        if current > previous * 1.005:
            return "raised"
        if current < previous * 0.995:
            return "lowered"
    text = (action or "").lower()
    if "down" in text:
        return "lowered"
    if "up" in text or "init" in text:
        return "raised"
    return "unchanged"


def scrub_copy(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text
    replacements = [
        (r"\bwe recommend\b", "the data indicates"),
        (r"\byou should\b", "the data shows"),
        (r"\bstrong buy\b", "strongly bullish outlook"),
        (r"\bstrong sell\b", "strongly bearish outlook"),
        (r"\bbuy rating\b", "bullish outlook"),
        (r"\bsell rating\b", "bearish outlook"),
        (r"\bhold rating\b", "neutral outlook"),
        (r"\brated buy\b", "assigned a bullish outlook"),
        (r"\brated sell\b", "assigned a bearish outlook"),
        (r"\brated hold\b", "assigned a neutral outlook"),
        (r"\bto buy\b", "to transact in"),
        (r"\bto sell\b", "to transact in"),
        (r"\binvestment advice\b", "financial advice"),
        (r"\binvestment decisions\b", "securities decisions"),
        (r"\binvestments\b", "securities"),
        (r"\binvestment\b", "securities research"),
        (r"\binvestors\b", "market participants"),
        (r"\binvestor\b", "market participant"),
        (r"\binvesting\b", "participating"),
        (r"\binvest\b", "participate"),
        (r"\bbuys\b", "bullish notes"),
        (r"\bsells\b", "bearish notes"),
        (r"\bholds\b", "neutral notes"),
        (r"\bbuy\b", "bullish"),
        (r"\bsell\b", "bearish"),
        (r"\bhold\b", "neutral"),
    ]
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.I)
    return cleaned.strip()


def contains_banned(text: str | None) -> bool:
    return bool(_BANNED.search(text or ""))


def analyst_action_row(row: dict[str, Any]) -> dict[str, Any]:
    grade = row.get("to_grade") or row.get("rating")
    previous = to_float(row.get("previous_target"))
    current = to_float(row.get("price_target") or row.get("current_target"))
    return {
        "name": row.get("name") or row.get("analyst") or "Research desk",
        "firm": row.get("firm"),
        "stars": stars_from_grade(grade),
        "previous_target": previous,
        "new_target": current,
        "direction": direction_from_targets(previous, current, row.get("action")),
        "days_ago": days_since(row.get("date")),
        "outlook": outlook_from_grade(grade),
        "outlook_label": display_outlook(grade),
        "date": row.get("date"),
    }
