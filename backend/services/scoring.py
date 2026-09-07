from __future__ import annotations

from typing import Any

from services.numbers import clamp, to_float


def _avg(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def technical_score(tech: dict[str, Any]) -> int | None:
    if not tech:
        return None
    rsi = to_float(tech.get("rsi"))
    if rsi is None:
        rsi_pts = None
    elif 40 <= rsi <= 65:
        rsi_pts = 82
    elif 30 <= rsi < 40 or 65 < rsi <= 75:
        rsi_pts = 62
    elif rsi < 30:
        rsi_pts = 55
    else:
        rsi_pts = 38
    ma_pts = 70
    if tech.get("above_ma50") and tech.get("above_ma200"):
        ma_pts = 88
    elif tech.get("above_ma200"):
        ma_pts = 72
    elif tech.get("above_ma50"):
        ma_pts = 60
    else:
        ma_pts = 35
    macd_pts = 80 if tech.get("macd_signal") == "bullish" else 40 if tech.get("macd_signal") == "bearish" else 55
    if tech.get("cross_alert") == "golden_cross":
        ma_pts = min(100, ma_pts + 8)
    elif tech.get("cross_alert") == "death_cross":
        ma_pts = max(0, ma_pts - 12)
    value = _avg([rsi_pts, ma_pts, macd_pts])
    return None if value is None else clamp(value)


def fundamental_score(data: dict[str, Any]) -> int | None:
    if not data:
        return None
    points: list[float] = []
    growths = [to_float(row.get("growth_pct")) for row in data.get("revenue_quarters") or [] if isinstance(row, dict)]
    growths = [g for g in growths if g is not None]
    if growths:
        latest = growths[0]
        points.append(85 if latest > 10 else 70 if latest > 0 else 40)
    if data.get("revenue_acceleration") is True:
        points.append(88)
    elif data.get("revenue_acceleration") is False:
        points.append(52)
    streak = data.get("beat_streak")
    if isinstance(streak, int):
        points.append(min(95, 55 + streak * 8))
    fcf = data.get("free_cash_flow_positive")
    if fcf is True:
        points.append(80)
    elif fcf is False:
        points.append(35)
    roe = to_float(data.get("return_on_equity"))
    if roe is not None:
        roe_pct = roe * 100 if roe <= 1 else roe
        points.append(85 if roe_pct > 15 else 65 if roe_pct > 8 else 45)
    pe = to_float(data.get("pe_ratio"))
    if pe is not None:
        points.append(78 if 8 <= pe <= 28 else 60 if pe < 40 else 42)
    if not points:
        return None
    return clamp(sum(points) / len(points))


def analyst_score(data: dict[str, Any]) -> int | None:
    if not data:
        return None
    total = to_float(data.get("total_analysts")) or 0
    bullish = to_float(data.get("bullish") if data.get("bullish") is not None else data.get("buy")) or 0
    bearish = to_float(data.get("bearish") if data.get("bearish") is not None else data.get("sell")) or 0
    if total <= 0 and not data.get("consensus"):
        return None
    if total > 0:
        bullish_pct = bullish / total
        bearish_pct = bearish / total
        base = 40 + bullish_pct * 60 - bearish_pct * 25
    else:
        consensus = str(data.get("consensus") or "").lower()
        if "bullish" in consensus or "buy" in consensus:
            base = 80
        elif "bearish" in consensus or "sell" in consensus:
            base = 40
        else:
            base = 58
    upside = to_float(data.get("upside_pct"))
    if upside is not None:
        base += 8 if upside > 15 else 3 if upside > 0 else -8
    return clamp(base)


def institutional_score(data: dict[str, Any]) -> int | None:
    if not data:
        return None
    points: list[float] = []
    own = to_float(data.get("institutional_ownership_pct"))
    if own is not None:
        points.append(82 if own > 60 else 68 if own > 40 else 50)
    if data.get("net_insider_sentiment") == "bullish":
        points.append(84)
    elif data.get("net_insider_sentiment") == "bearish":
        points.append(38)
    short_pct = to_float(data.get("short_interest_pct"))
    if short_pct is not None:
        points.append(80 if short_pct < 3 else 60 if short_pct < 8 else 40)
    change = to_float(data.get("institutional_ownership_change"))
    if change is not None:
        points.append(78 if change > 0 else 48)
    if not points:
        return None
    return clamp(sum(points) / len(points))


def sentiment_score(data: dict[str, Any]) -> int | None:
    if not data:
        return None
    overall = data.get("overall_score")
    if overall is not None:
        return clamp(float(overall))
    headlines = data.get("headlines") or []
    if headlines:
        pos = sum(1 for item in headlines if item.get("sentiment") == "positive")
        neg = sum(1 for item in headlines if item.get("sentiment") == "negative")
        return clamp(50 + 50 * (pos - neg) / len(headlines))
    ratio = to_float(data.get("positive_ratio"))
    reddit = data.get("reddit") or {}
    trends = data.get("google_trends") or {}
    points: list[float] = []
    if ratio is not None:
        points.append(ratio * 100)
    trend = reddit.get("trend")
    if trend == "up":
        points.append(78)
    elif trend == "down":
        points.append(45)
    direction = trends.get("direction")
    if direction == "up":
        points.append(76)
    elif direction == "down":
        points.append(48)
    if not points:
        return None
    return clamp(sum(points) / len(points))


def composite(scores: dict[str, int | None]) -> int | None:
    present = [value for value in scores.values() if value is not None]
    if not present:
        return None
    return clamp(sum(present) / len(present))
