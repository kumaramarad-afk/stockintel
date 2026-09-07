from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from services import scoring
from services.language import (
    analyst_action_row,
    display_outlook,
    outlook_from_grade,
    scrub_copy,
    signal_from_score,
)
from services.numbers import clamp, pct_change, to_float
from services.providers import alpha_vantage, capitol, claude, finnhub, reddit, sec_edgar, trends, yahoo
from services.providers import yahoo_http

logger = logging.getLogger(__name__)

POSITIVE = re.compile(
    r"\b(beat|beats|surge|surges|rally|rallies|record|upgrade|upgraded|growth|profit|profits|"
    r"bullish|win|wins|soar|soars|jump|jumps|gain|gains|outperform|raise|raises|strong|"
    r"breakthrough|optimism|buy|bought|higher|rise|rises|positive|optimistic|expand|expands)\b",
    re.I,
)
NEGATIVE = re.compile(
    r"\b(miss|misses|fall|falls|drop|drops|downgrade|downgraded|lawsuit|probe|bearish|cut|cuts|"
    r"warning|slump|plunge|plunges|loss|losses|weak|concern|investigation|sell|sells|decline|"
    r"declines|crash|fear|layoff|layoffs|fraud|negative|recall|delay|delays)\b",
    re.I,
)


class TickerNotFoundError(Exception):
    pass


class MissingApiKeyError(Exception):
    pass


class ResearchGenerationError(Exception):
    pass


def _unavailable(ticker: str, message: str = "Data unavailable") -> dict[str, Any]:
    return {"ticker": ticker, "available": False, "error": message, "data": None}


def _ok(ticker: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"ticker": ticker, "available": True, "error": None, "data": data}


def _label_headline(text: str | None) -> str:
    if not text:
        return "neutral"
    if POSITIVE.search(text) and not NEGATIVE.search(text):
        return "positive"
    if NEGATIVE.search(text) and not POSITIVE.search(text):
        return "negative"
    return "neutral"


def _bundle(ticker: str) -> dict[str, Any]:
    try:
        return yahoo.load_bundle(ticker)
    except Exception as exc:
        raise TickerNotFoundError(str(exc) or f"No market data found for {ticker}.") from exc


def _merge_fundamentals(ticker: str, yahoo_data: dict[str, Any]) -> dict[str, Any]:
    data = dict(yahoo_data)
    overview = alpha_vantage.overview(ticker)
    earnings = alpha_vantage.earnings(ticker)
    income = alpha_vantage.income(ticker)
    metrics = finnhub.metrics(ticker)
    if income and income.get("revenue_quarters"):
        data["revenue_quarters"] = income["revenue_quarters"]
        data["revenue_acceleration"] = income.get("revenue_acceleration")
    if earnings and earnings.get("eps_quarters"):
        data["eps_quarters"] = earnings["eps_quarters"]
        data["beat_streak"] = earnings.get("beat_streak", data.get("beat_streak"))
    if overview:
        for key in (
            "pe_ratio",
            "peg_ratio",
            "price_to_sales",
            "price_to_book",
            "ev_ebitda",
            "operating_margin",
            "return_on_equity",
        ):
            if overview.get(key) is not None:
                data[key] = overview[key]
        if overview.get("profit_margin") is not None:
            data["profit_margin"] = overview["profit_margin"]
    if metrics:
        if metrics.get("pe_ratio") is not None:
            data["pe_ratio"] = data.get("pe_ratio") or metrics["pe_ratio"]
        if metrics.get("roe") is not None:
            data["return_on_equity"] = data.get("return_on_equity") or metrics["roe"]
    return data


def _merge_analysts(ticker: str, yahoo_data: dict[str, Any], price: float | None) -> dict[str, Any]:
    data = dict(yahoo_data)
    rec = finnhub.recommendation(ticker)
    target = finnhub.price_target(ticker)
    up, down, top = finnhub.upgrades(ticker)
    if rec:
        data["buy"] = rec["buy"]
        data["hold"] = rec["hold"]
        data["sell"] = rec["sell"]
        data["bullish"] = rec["buy"]
        data["neutral"] = rec["hold"]
        data["bearish"] = rec["sell"]
        data["total_analysts"] = rec["total"] or data.get("total_analysts")
        if rec["total"]:
            if rec["buy"] / rec["total"] >= 0.6:
                data["consensus"] = "bullish"
            elif rec["sell"] / rec["total"] >= 0.4:
                data["consensus"] = "bearish"
            else:
                data["consensus"] = "mixed"
    if target:
        for key in ("average_target", "high_target", "low_target"):
            if target.get(key) is not None:
                data[key] = target[key]
    details = yahoo_http.quote_details(ticker) or {}
    for key in ("average_target", "high_target", "low_target", "total_analysts", "top_analyst", "recent_actions", "top_analysts"):
        if data.get(key) in (None, 0, [], {}) and details.get(key) not in (None, 0, [], {}):
            data[key] = details[key]
    if not data.get("consensus") and details.get("consensus"):
        data["consensus"] = str(details["consensus"]).replace("_", " ")
    if not data.get("upgrades"):
        data["upgrades"] = up or details.get("upgrades") or []
    if not data.get("downgrades"):
        data["downgrades"] = down or details.get("downgrades") or []
    if not data.get("top_analyst"):
        data["top_analyst"] = top or details.get("top_analyst")
    if not data.get("recent_actions"):
        combined = []
        for row in (data.get("upgrades") or []) + (data.get("downgrades") or []):
            combined.append(
                analyst_action_row(
                    {
                        "name": row.get("name") or "Research desk",
                        "firm": row.get("firm"),
                        "to_grade": row.get("to_grade") or row.get("action"),
                        "previous_target": row.get("previous_target"),
                        "price_target": row.get("price_target"),
                        "action": row.get("action"),
                        "date": row.get("date"),
                    }
                )
            )
        combined.sort(key=lambda row: row.get("date") or "", reverse=True)
        data["recent_actions"] = combined[:10]
    data["bullish"] = data.get("bullish") if data.get("bullish") is not None else data.get("buy")
    data["neutral"] = data.get("neutral") if data.get("neutral") is not None else data.get("hold")
    data["bearish"] = data.get("bearish") if data.get("bearish") is not None else data.get("sell")
    data["upside_pct"] = pct_change(to_float(data.get("average_target")), price)
    if data.get("upgrades") and not data.get("downgrades"):
        data["eps_revisions_trend"] = "up"
    elif data.get("downgrades") and not data.get("upgrades"):
        data["eps_revisions_trend"] = "down"
    elif data.get("upgrades") or data.get("downgrades"):
        data["eps_revisions_trend"] = "mixed"
    return data


def _client_analysts(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    bullish = out.get("bullish") if out.get("bullish") is not None else out.get("buy")
    neutral = out.get("neutral") if out.get("neutral") is not None else out.get("hold")
    bearish = out.get("bearish") if out.get("bearish") is not None else out.get("sell")
    out["bullish"] = bullish
    out["neutral"] = neutral
    out["bearish"] = bearish
    counted = sum(value or 0 for value in (bullish, neutral, bearish) if value is not None)
    if counted and not out.get("total_analysts"):
        out["total_analysts"] = counted
    total = out.get("total_analysts") or counted
    raw = str(out.get("consensus") or "").replace("_", " ").strip()
    mapped = {
        "buy": "bullish",
        "strong buy": "bullish",
        "sell": "bearish",
        "strong sell": "bearish",
        "hold": "neutral",
        "bullish": "bullish",
        "bearish": "bearish",
        "neutral": "neutral",
        "mixed": "mixed",
    }.get(raw.lower())
    out["consensus"] = mapped or outlook_from_grade(raw)
    if total:
        if (bullish or 0) / total >= 0.6:
            out["consensus"] = "bullish"
        elif (bearish or 0) / total >= 0.4:
            out["consensus"] = "bearish"
        else:
            out["consensus"] = "mixed"
    for key in ("buy", "hold", "sell"):
        out.pop(key, None)
    top = out.get("top_analyst")
    if isinstance(top, dict) and top.get("rating"):
        out["top_analyst"] = {**top, "rating": display_outlook(str(top.get("rating")))}
    for group in ("upgrades", "downgrades"):
        cleaned = []
        for row in out.get(group) or []:
            item = dict(row)
            if item.get("to_grade"):
                item["to_grade"] = display_outlook(str(item.get("to_grade")))
            if item.get("from_grade"):
                item["from_grade"] = display_outlook(str(item.get("from_grade")))
            cleaned.append(item)
        out[group] = cleaned
    return out


def _listify(value: Any) -> list[str]:
    if isinstance(value, list):
        items = [scrub_copy(str(item).strip(" -•")) for item in value]
        return [item for item in items if item]
    text = scrub_copy(str(value or ""))
    if not text:
        return []
    if "\n" in text:
        return [re.sub(r"^[-•]\s*", "", line).strip() for line in text.splitlines() if line.strip()]
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if len(part.strip()) > 8]


def _fallback_briefing(
    ticker: str,
    quote: dict[str, Any],
    analysts: dict[str, Any],
    tech: dict[str, Any],
    earnings: dict[str, Any],
    scores: dict[str, Any],
    flags: list[str],
    headlines: list[dict[str, Any]],
) -> dict[str, Any]:
    composite = scores.get("composite")
    public = _client_analysts(analysts)
    bullish = public.get("bullish") or 0
    total = public.get("total_analysts") or 0
    price = quote.get("price")
    target = public.get("average_target")
    upside = public.get("upside_pct")
    rsi = tech.get("rsi")
    rsi_text = f"{rsi:.1f}" if isinstance(rsi, (int, float)) else "unavailable"
    above_200 = "above" if tech.get("above_ma200") else "below"
    price_text = f"{price:.2f}" if isinstance(price, (int, float)) else "unavailable"
    target_text = f"{target:.2f}" if isinstance(target, (int, float)) else "unavailable"
    upside_text = f"{upside:.1f}%" if isinstance(upside, (int, float)) else "unavailable"
    coverage = (
        f"{bullish} out of {total} analysts tracking this stock have a positive outlook"
        if total
        else "Analyst coverage counts were not published on this snapshot"
    )
    what = scrub_copy(
        f"The data indicates {ticker} carries a composite score of {composite if composite is not None else 'n/a'} out of 100. "
        f"{coverage}, with {public.get('neutral') or 0} remaining neutral and {public.get('bearish') or 0} assigning a negative outlook. "
        f"Consensus points to an average price target of {target_text} versus a last print of {price_text}, implying {upside_text} to the mean target. "
        f"Technical readings show RSI at {rsi_text}, MACD {tech.get('macd_signal') or 'unavailable'}, and the shares {above_200} the 200-day average."
    )
    risks = [scrub_copy(flag.replace("WARNING: ", "")) for flag in flags]
    if not risks:
        risks = ["No automated risk flags fired on this snapshot."]
    if earnings.get("days_away") is not None and isinstance(earnings.get("days_away"), int) and 0 <= earnings["days_away"] < 21:
        risks.append(f"Results are {earnings['days_away']} days away, which historically coincides with larger daily ranges.")
    catalysts: list[str] = []
    if earnings.get("next_earnings_date"):
        session = earnings.get("time_of_day") or "session unset"
        extra = f", {earnings['days_away']} days away" if isinstance(earnings.get("days_away"), int) else ""
        catalysts.append(f"Results are on the calendar for {earnings['next_earnings_date']} ({session}{extra}).")
    for item in headlines[:8]:
        headline = item.get("headline") or ""
        if re.search(r"launch|keynote|event|earnings|product|wwdc|developer", headline, re.I):
            catalysts.append(scrub_copy(headline[:180]))
    if not catalysts:
        catalysts.append("No dated catalysts were published on this snapshot beyond the regular market calendar.")
    return {
        "what_the_data_shows": what,
        "why_it_scores": what,
        "key_risks": risks,
        "upcoming_catalysts": catalysts,
        "outlook": " ".join(catalysts),
    }


def score_headlines(headlines: list[dict[str, Any]]) -> dict[str, Any]:
    labeled = []
    pos = neg = 0
    for item in headlines[:12]:
        label = _label_headline(item.get("headline"))
        if label == "positive":
            pos += 1
        elif label == "negative":
            neg += 1
        labeled.append({**item, "sentiment": label})
    total = len(labeled)
    overall = clamp(50 + 50 * (pos - neg) / total) if total else None
    ratio = (pos / (pos + neg)) if (pos + neg) else (0.5 if total else None)
    return {
        "overall_score": overall,
        "headlines": labeled,
        "reddit": None,
        "google_trends": None,
        "positive_ratio": ratio,
        "positive_count": pos,
        "negative_count": neg,
    }


def _headline_sentiment(ticker: str, headlines: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if headlines is None:
        headlines = finnhub.company_news(ticker)
        if not headlines:
            try:
                headlines = yahoo.news_from_yahoo(_bundle(ticker))
            except Exception:
                headlines = []
    return score_headlines(headlines)


def _sentiment_payload(ticker: str) -> dict[str, Any]:
    payload = _headline_sentiment(ticker)
    payload["reddit"] = reddit.mentions(ticker)
    payload["google_trends"] = trends.interest(ticker)
    if payload.get("overall_score") is None:
        payload["overall_score"] = scoring.sentiment_score(payload)
    return payload


def _ownership_payload(ticker: str, bundle: dict[str, Any]) -> dict[str, Any]:
    data = yahoo.ownership_from_yahoo(bundle)
    details = yahoo_http.quote_details(ticker) or {}
    if data.get("short_interest_pct") is None:
        data["short_interest_pct"] = details.get("short_interest_pct")
    if data.get("short_interest_trend") is None:
        data["short_interest_trend"] = details.get("short_interest_trend")
    if data.get("days_to_cover") is None:
        data["days_to_cover"] = details.get("days_to_cover")
    if data.get("institutional_ownership_pct") is None:
        data["institutional_ownership_pct"] = details.get("institutional_ownership_pct")
    if data.get("institutional_ownership_change") is None:
        data["institutional_ownership_change"] = details.get("institutional_ownership_change")
    additions = details.get("new_institutional_additions")
    if additions is None:
        additions = details.get("new_institutional_buyers")
    if data.get("new_institutional_additions") is None:
        data["new_institutional_additions"] = additions
    if data.get("new_institutional_buyers") is None:
        data["new_institutional_buyers"] = additions
    if not data.get("top_holders") and details.get("holders"):
        data["top_holders"] = details["holders"][:8]

    issuer = (bundle.get("info") or {}).get("longName") or (bundle.get("info") or {}).get("shortName")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            insider_future = pool.submit(sec_edgar.insider_transactions, ticker)
            thirteen_future = pool.submit(sec_edgar.thirteen_f_holdings, ticker, issuer)
            sec_insiders = insider_future.result()
            thirteen = thirteen_future.result()
    except Exception:
        logger.exception("SEC ownership fetch failed for %s", ticker)
        sec_insiders = []
        thirteen = {}

    if sec_insiders:
        data["insider_transactions"] = sec_insiders
        net = 0.0
        for row in sec_insiders:
            shares = abs(to_float(row.get("shares")) or 0)
            code = str(row.get("code") or "").upper()
            action = str(row.get("action") or "").lower()
            if code == "P" or action in {"buy", "acquired"}:
                net += shares
            elif code in {"S", "D"} or action in {"sell", "disposed"}:
                net -= shares
        data["net_insider_sentiment"] = "bullish" if net > 0 else "bearish" if net < 0 else "neutral"
        data["insider_selling"] = net < 0

    if thirteen.get("top_holders"):
        data["top_holders"] = thirteen["top_holders"][:8]
        data["latest_13f"] = thirteen.get("latest_13f")
        data["recent_13f_count"] = thirteen.get("holder_count")
        if data.get("new_institutional_additions") is None:
            data["new_institutional_additions"] = thirteen.get("holder_count")
        if data.get("new_institutional_buyers") is None:
            data["new_institutional_buyers"] = thirteen.get("holder_count")
    data["congressional_trades"] = [
        {
            **row,
            "action": (
                "Disposed"
                if "sell" in str(row.get("action") or "").lower() or "sale" in str(row.get("action") or "").lower()
                else "Acquired"
                if "buy" in str(row.get("action") or "").lower() or "purchase" in str(row.get("action") or "").lower()
                else row.get("action")
            ),
        }
        for row in (capitol.trades_for(ticker) or [])
    ]
    return data


def _risk_flags(quote: dict[str, Any], earnings: dict[str, Any], ownership: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    days = earnings.get("days_away")
    if isinstance(days, int) and 0 <= days < 7:
        flags.append("WARNING: Earnings in less than 7 days")
    month_return = to_float(quote.get("month_return"))
    if month_return is not None and month_return >= 30:
        flags.append("WARNING: Stock up 30%+ this month")
    if ownership.get("insider_selling"):
        flags.append("WARNING: Insider dispositions detected")
    return flags


class StockService:
    def section_header(self, ticker: str) -> dict[str, Any]:
        bundle = _bundle(ticker)
        quote = yahoo.quote(bundle)
        tech = yahoo.technicals(bundle)
        fundamentals = _merge_fundamentals(ticker, yahoo.fundamentals_from_info(bundle))
        analysts = _merge_analysts(ticker, yahoo.analyst_from_yahoo(bundle), quote.get("price"))
        ownership = yahoo.ownership_from_yahoo(bundle)
        sentiment = _headline_sentiment(ticker)
        earnings = yahoo.earnings_from_yahoo(bundle)
        calendar = finnhub.earnings_calendar(ticker)
        if calendar:
            earnings = {**earnings, **{k: v for k, v in calendar.items() if v is not None}}
        scores = {
            "fundamental": scoring.fundamental_score(fundamentals),
            "technical": scoring.technical_score(tech),
            "analyst": scoring.analyst_score(analysts),
            "institutional": scoring.institutional_score(ownership),
            "sentiment": scoring.sentiment_score(sentiment),
        }
        composite = scoring.composite(scores)
        signal = signal_from_score(composite)
        public = _client_analysts(analysts)
        return _ok(
            ticker,
            {
                **quote,
                "composite_score": composite,
                "scores": scores,
                "risk_flags": _risk_flags(quote, earnings, ownership),
                "signal_label": signal["label"],
                "signal_emoji": signal["emoji"],
                "signal_tone": signal["tone"],
                "bullish_count": public.get("bullish"),
                "neutral_count": public.get("neutral"),
                "bearish_count": public.get("bearish"),
                "total_analysts": public.get("total_analysts"),
                "average_target": public.get("average_target"),
                "upside_pct": public.get("upside_pct"),
                "recent_actions": public.get("recent_actions") or [],
                "top_analysts": public.get("top_analysts") or [],
            },
        )

    def section_ai(self, ticker: str) -> dict[str, Any]:
        bundle = _bundle(ticker)
        quote = yahoo.quote(bundle)
        tech = yahoo.technicals(bundle)
        fundamentals = _merge_fundamentals(ticker, yahoo.fundamentals_from_info(bundle))
        analysts = _merge_analysts(ticker, yahoo.analyst_from_yahoo(bundle), quote.get("price"))
        ownership = yahoo.ownership_from_yahoo(bundle)
        earnings = yahoo.earnings_from_yahoo(bundle)
        calendar = finnhub.earnings_calendar(ticker)
        if calendar:
            earnings = {**earnings, **{k: v for k, v in calendar.items() if v is not None}}
        sentiment = _headline_sentiment(ticker)
        scores = {
            "fundamental": scoring.fundamental_score(fundamentals),
            "technical": scoring.technical_score(tech),
            "analyst": scoring.analyst_score(analysts),
            "institutional": scoring.institutional_score(ownership),
            "sentiment": scoring.sentiment_score(sentiment),
        }
        public = _client_analysts(analysts)
        flags = _risk_flags(quote, earnings, ownership)
        snapshot = {
            "quote": {"ticker": ticker, "name": quote.get("name"), "price": quote.get("price")},
            "scores": {**scores, "composite": scoring.composite(scores)},
            "risks": flags,
            "analysts": {
                "bullish": public.get("bullish"),
                "neutral": public.get("neutral"),
                "bearish": public.get("bearish"),
                "total": public.get("total_analysts"),
                "average_target": public.get("average_target"),
                "upside_pct": public.get("upside_pct"),
                "consensus": public.get("consensus"),
            },
            "earnings": {
                "next_earnings_date": earnings.get("next_earnings_date"),
                "days_away": earnings.get("days_away"),
                "time_of_day": earnings.get("time_of_day"),
                "implied_move": earnings.get("implied_move"),
                "average_historical_move": earnings.get("average_historical_move"),
            },
            "technicals": {
                "rsi": tech.get("rsi"),
                "macd_signal": tech.get("macd_signal"),
                "cross_alert": tech.get("cross_alert"),
                "above_ma200": tech.get("above_ma200"),
            },
            "headlines": [item.get("headline") for item in (sentiment.get("headlines") or [])[:6]],
        }
        summary = claude.summarize(ticker, snapshot)
        if not summary or not (summary.get("what_the_data_shows") or summary.get("why_it_scores")):
            summary = _fallback_briefing(
                ticker,
                quote,
                analysts,
                tech,
                earnings,
                snapshot["scores"],
                flags,
                sentiment.get("headlines") or [],
            )
        what = scrub_copy(str(summary.get("what_the_data_shows") or summary.get("why_it_scores") or ""))
        risks = _listify(summary.get("key_risks"))
        catalysts = _listify(summary.get("upcoming_catalysts") or summary.get("outlook"))
        if not catalysts:
            fallback = _fallback_briefing(
                ticker,
                quote,
                analysts,
                tech,
                earnings,
                snapshot["scores"],
                flags,
                sentiment.get("headlines") or [],
            )
            catalysts = fallback["upcoming_catalysts"]
            if not risks:
                risks = fallback["key_risks"]
        implied = earnings.get("implied_move")
        historical = earnings.get("average_historical_move")
        opportunity = None
        if implied is not None and historical is not None:
            opportunity = implied < historical
        return _ok(
            ticker,
            {
                "what_the_data_shows": what,
                "why_it_scores": what,
                "key_risks": risks,
                "upcoming_catalysts": catalysts,
                "outlook": " ".join(catalysts),
                "disclaimer": "Data sourced from public analyst reports. Not financial advice.",
                "options_opportunity": opportunity,
                "implied_move": implied,
                "historical_move": historical,
            },
        )

    def section_technicals(self, ticker: str) -> dict[str, Any]:
        return _ok(ticker, yahoo.technicals(_bundle(ticker)))

    def section_fundamentals(self, ticker: str) -> dict[str, Any]:
        return _ok(ticker, _merge_fundamentals(ticker, yahoo.fundamentals_from_info(_bundle(ticker))))

    def section_analysts(self, ticker: str) -> dict[str, Any]:
        bundle = _bundle(ticker)
        price = yahoo.quote(bundle).get("price")
        return _ok(ticker, _client_analysts(_merge_analysts(ticker, yahoo.analyst_from_yahoo(bundle), price)))

    def section_earnings(self, ticker: str) -> dict[str, Any]:
        bundle = _bundle(ticker)
        data = yahoo.earnings_from_yahoo(bundle)
        calendar = finnhub.earnings_calendar(ticker)
        if calendar:
            for key, value in calendar.items():
                if value is not None:
                    data[key] = value
        av = alpha_vantage.earnings(ticker)
        fh = finnhub.earnings_surprises(ticker)
        if av and av.get("eps_quarters") and not data.get("results"):
            data["results"] = [
                {**row, "next_day_move": None} for row in av["eps_quarters"]
            ]
        elif fh and not data.get("results"):
            data["results"] = [{**row, "next_day_move": None} for row in fh]
        if data.get("implied_move") is None:
            data["implied_move"] = yahoo.implied_move(bundle)
        if data.get("implied_move") is not None and data.get("average_historical_move") is not None:
            data["volatility_underpriced"] = data["implied_move"] < data["average_historical_move"]
        return _ok(ticker, data)

    def section_sentiment(self, ticker: str) -> dict[str, Any]:
        payload = _sentiment_payload(ticker)
        if not payload.get("headlines") and not payload.get("reddit") and not payload.get("google_trends"):
            return _unavailable(ticker)
        return _ok(ticker, payload)

    def section_ownership(self, ticker: str) -> dict[str, Any]:
        return _ok(ticker, _ownership_payload(ticker, _bundle(ticker)))

    def section_dividends(self, ticker: str) -> dict[str, Any]:
        data = yahoo.dividends_from_yahoo(_bundle(ticker))
        overview = alpha_vantage.overview(ticker)
        if overview and overview.get("dividend_yield"):
            yield_pct = overview["dividend_yield"]
            if yield_pct is not None and yield_pct <= 1:
                yield_pct *= 100
            data = data or {}
            data["annual_yield"] = yield_pct
            data["payout_ratio"] = data.get("payout_ratio") or overview.get("payout_ratio")
            data["next_dividend_date"] = data.get("next_dividend_date") or overview.get("ex_dividend_date") or overview.get("dividend_date")
        if not data:
            return _unavailable(ticker, "No dividend data")
        return _ok(ticker, data)

    def section_sector(self, ticker: str) -> dict[str, Any]:
        data = yahoo.sector_from_yahoo(_bundle(ticker))
        names = [ticker.upper(), *finnhub.peers(ticker)]
        if len(names) > 1:
            ranked: list[tuple[str, float]] = []
            for symbol in names[:8]:
                try:
                    hist = yahoo.load_bundle(symbol)["history"] if symbol != ticker.upper() else _bundle(ticker)["history"]
                    ret = yahoo.period_return(hist, 63)
                    if ret is not None:
                        ranked.append((symbol, ret))
                except Exception:
                    continue
            ranked.sort(key=lambda item: item[1], reverse=True)
            data["peer_count"] = len(ranked)
            for idx, (symbol, _) in enumerate(ranked, start=1):
                if symbol == ticker.upper():
                    data["sector_rank"] = idx
                    break
        return _ok(ticker, data)

    def generate_research(self, ticker: str) -> dict[str, Any]:
        symbol = ticker.strip().upper()
        header = self.section_header(symbol)
        if not header["available"]:
            raise TickerNotFoundError(header["error"] or f"No market data found for {symbol}.")
        ai = self.section_ai(symbol)
        data = header["data"]
        report = ""
        if ai["available"] and ai["data"]:
            report = "\n\n".join(
                part
                for part in (
                    ai["data"].get("what_the_data_shows") or ai["data"].get("why_it_scores"),
                    "\n".join(f"- {item}" for item in _listify(ai["data"].get("key_risks"))),
                    "\n".join(f"- {item}" for item in _listify(ai["data"].get("upcoming_catalysts"))),
                )
                if part
            )
        return {
            "ticker": symbol,
            "name": data.get("name"),
            "current_price": {
                "price": data.get("price"),
                "change_percent": data.get("change_percent"),
                "currency": data.get("currency") or "USD",
                "previous_close": data.get("previous_close"),
                "day_high": data.get("high"),
                "day_low": data.get("low"),
                "volume": data.get("volume"),
                "as_of": data.get("as_of"),
            },
            "analyst_ratings": {
                "consensus": None,
                "target_mean": None,
                "target_high": None,
                "target_low": None,
                "number_of_analysts": None,
                "distribution": None,
            },
            "financials": {
                "pe_ratio": None,
                "market_cap": None,
                "revenue": None,
                "eps": None,
                "profit_margin": None,
                "source": None,
            },
            "report": report or "Data unavailable",
        }


SECTION_HANDLERS = {
    "header": StockService.section_header,
    "ai": StockService.section_ai,
    "technicals": StockService.section_technicals,
    "fundamentals": StockService.section_fundamentals,
    "analysts": StockService.section_analysts,
    "earnings": StockService.section_earnings,
    "sentiment": StockService.section_sentiment,
    "ownership": StockService.section_ownership,
    "dividends": StockService.section_dividends,
    "sector": StockService.section_sector,
}


def generate_stock_research(ticker: str) -> dict[str, Any]:
    return StockService().generate_research(ticker)


def generate_section(ticker: str, section: str) -> dict[str, Any]:
    handler = SECTION_HANDLERS.get(section)
    if handler is None:
        raise KeyError(section)
    service = StockService()
    try:
        return handler(service, ticker)
    except TickerNotFoundError:
        raise
    except Exception:
        logger.exception("Section %s failed for %s", section, ticker)
        return _unavailable(ticker)
