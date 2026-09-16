from __future__ import annotations

import json
import logging
import re
import statistics
from datetime import date, datetime, timezone
from typing import Any

from services.language import scrub_copy
from services.numbers import to_float
from services.providers import alpha_vantage, claude, finnhub, newsapi, sec_edgar, yahoo
from services.providers import yahoo_http
from services.stock_service import TickerNotFoundError, _bundle, _merge_analysts, _merge_fundamentals

logger = logging.getLogger(__name__)

NON_VERDICT = """## 6. What this note does not do

It doesn't tell you to buy or sell. It won't, ever.

You have the valuation in context, the strongest version of both cases, and the specific assumptions the current price depends on. What you do with that depends on your time horizon, your existing exposure, your risk tolerance, and what else you could do with the money — none of which we know.

If you want someone to tell you what to do, you want a licensed financial adviser, and that is a genuinely reasonable thing to want."""


def _disclaimer(as_of: str) -> str:
    return (
        "*Educational and informational purposes only. Not investment advice and not "
        "a recommendation to buy or sell any security. GetStockReport is not a "
        "registered investment adviser. Figures are as of "
        f"{as_of} and go stale quickly — verify against primary sources before acting. "
        "All investments carry risk including loss of principal. Past performance does not "
        "guarantee future results.*"
    )


def _fmt(value: Any, digits: int = 1) -> str:
    number = to_float(value)
    if number is None:
        return "n/a"
    return f"{number:.{digits}f}"


def _money(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return "n/a"
    return f"${number:,.2f}"


def _pct(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return "n/a"
    return f"{number:+.0f}%" if abs(number) >= 1 else f"{number * 100:+.0f}%"


def _median_pe_from_history(history: Any, trailing_eps: float | None, years: int = 10) -> tuple[float | None, str]:
    if trailing_eps in (None, 0) or history is None or getattr(history, "empty", True):
        return None, "unavailable"
    try:
        closes = history["Close"].dropna()
        if closes.empty:
            return None, "unavailable"
        annual = closes.resample("YE").last().dropna().tail(years)
        if len(annual) < 3:
            try:
                annual = closes.resample("Y").last().dropna().tail(years)
            except Exception:
                annual = closes.resample("YE").last().dropna().tail(5)
        ratios = [float(price) / trailing_eps for price in annual if to_float(price)]
        ratios = [ratio for ratio in ratios if 1 < ratio < 200]
        if len(ratios) < 3:
            return None, "unavailable"
        window = f"{len(ratios)}-year" if len(ratios) >= 8 else "5-year"
        return float(statistics.median(ratios)), window
    except Exception:
        logger.exception("Historical median P/E failed")
        return None, "unavailable"


def _headlines(ticker: str, limit: int = 6) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        for row in finnhub.company_news(ticker)[:limit]:
            headline = str(row.get("headline") or "").strip()
            if headline:
                items.append({"headline": headline, "source": row.get("source"), "summary": row.get("summary")})
    except Exception:
        logger.exception("Finnhub company news failed for %s", ticker)
    if len(items) < 3:
        try:
            for row in newsapi.market_headlines(limit):
                headline = str(row.get("headline") or "").strip()
                if not headline:
                    continue
                items.append(
                    {
                        "headline": headline,
                        "source": row.get("source"),
                        "summary": row.get("summary"),
                        "ticker": row.get("ticker"),
                    }
                )
                if len(items) >= limit:
                    break
        except Exception:
            logger.exception("NewsAPI headlines failed for %s", ticker)
    return items[:limit]


def build_reasoning_snapshot(ticker: str) -> dict[str, Any]:
    symbol = ticker.strip().upper()
    bundle = _bundle(symbol)
    quote = yahoo.quote(bundle)
    if not quote.get("price"):
        raise TickerNotFoundError(f"No market data found for {symbol}.")
    fundamentals = _merge_fundamentals(symbol, yahoo.fundamentals_from_info(bundle))
    analysts = _merge_analysts(symbol, yahoo.analyst_from_yahoo(bundle), quote.get("price"))
    details = {}
    try:
        details = yahoo_http.quote_details(symbol) or {}
    except Exception:
        logger.exception("Yahoo quote details failed for %s", symbol)
    overview = {}
    try:
        overview = alpha_vantage.overview(symbol) or {}
    except Exception:
        logger.exception("Alpha Vantage overview failed for %s", symbol)

    price = to_float(quote.get("price"))
    info = bundle.get("info") or {}
    detail_info = details.get("info") if isinstance(details.get("info"), dict) else {}
    trailing_pe = to_float(fundamentals.get("pe_ratio") or overview.get("pe_ratio") or info.get("trailingPE"))
    forward_pe = to_float(info.get("forwardPE") or detail_info.get("forwardPE"))
    trailing_eps = to_float(overview.get("eps") or info.get("trailingEps") or detail_info.get("trailingEps"))
    if trailing_eps is None and price and trailing_pe:
        trailing_eps = price / trailing_pe
    gross_margin = to_float(fundamentals.get("gross_margin") or overview.get("gross_margin"))
    if gross_margin is not None and abs(gross_margin) <= 1.5:
        gross_margin *= 100
    sector = fundamentals.get("sector") or overview.get("sector") or info.get("sector")

    median_pe, pe_window = _median_pe_from_history(bundle.get("history"), trailing_eps, years=10)
    pe_gap_pct = None
    if trailing_pe is not None and median_pe not in (None, 0):
        pe_gap_pct = ((trailing_pe - median_pe) / median_pe) * 100

    avg_target = to_float(analysts.get("average_target") or details.get("average_target"))
    high_target = to_float(analysts.get("high_target") or details.get("high_target"))
    low_target = to_float(analysts.get("low_target") or details.get("low_target"))
    analyst_count = analysts.get("total_analysts") or details.get("total_analysts")

    fair_models: list[dict[str, Any]] = []
    if median_pe and trailing_eps:
        fair_models.append(
            {
                "name": f"{pe_window} median P/E multiple",
                "value": median_pe * trailing_eps,
                "note": f"Applies the {pe_window} median multiple ({_fmt(median_pe)}x) to trailing EPS.",
            }
        )
    if avg_target:
        fair_models.append({"name": "Street mean target", "value": avg_target, "note": "Average published analyst target."})
    if low_target and high_target and low_target != high_target:
        fair_models.append(
            {
                "name": "Street target midpoint",
                "value": (low_target + high_target) / 2,
                "note": f"Midpoint of {_money(low_target)}–{_money(high_target)} published range.",
            }
        )

    insiders: list[dict[str, Any]] = []
    try:
        for row in (sec_edgar.insider_transactions(symbol) or [])[:3]:
            insiders.append(
                {
                    "name": row.get("name"),
                    "title": row.get("title"),
                    "action": row.get("action"),
                    "value": row.get("value"),
                    "date": row.get("date"),
                }
            )
    except Exception:
        logger.exception("Insider fetch failed for %s", symbol)

    earnings = yahoo.earnings_from_yahoo(bundle)
    try:
        calendar = finnhub.earnings_calendar(symbol)
        if calendar:
            earnings = {**earnings, **{k: v for k, v in calendar.items() if v is not None}}
    except Exception:
        pass

    return {
        "ticker": symbol,
        "name": quote.get("name") or symbol,
        "as_of": date.today().isoformat(),
        "price": price,
        "change_percent": quote.get("change_percent"),
        "trailing_pe": trailing_pe,
        "forward_pe": forward_pe,
        "median_pe": median_pe,
        "pe_window": pe_window,
        "pe_gap_pct": pe_gap_pct,
        "trailing_eps": trailing_eps,
        "gross_margin": gross_margin,
        "sector": sector,
        "average_target": avg_target,
        "high_target": high_target,
        "low_target": low_target,
        "target_spread": None if high_target is None or low_target is None else high_target - low_target,
        "analyst_count": analyst_count,
        "bullish": analysts.get("bullish") or analysts.get("buy"),
        "neutral": analysts.get("neutral") or analysts.get("hold"),
        "bearish": analysts.get("bearish") or analysts.get("sell"),
        "fair_value_models": fair_models,
        "headlines": _headlines(symbol),
        "insiders": insiders,
        "earnings": {
            "next_earnings_date": earnings.get("next_earnings_date"),
            "days_away": earnings.get("days_away"),
            "eps_estimate": earnings.get("eps_estimate"),
        },
        "recent_actions": (analysts.get("recent_actions") or details.get("recent_actions") or [])[:6],
        "data_notes": []
        if median_pe is not None
        else ["Historical median P/E unavailable from clean history — valuation gap uses available current multiples only."],
    }


def _fallback_markdown(snapshot: dict[str, Any]) -> str:
    ticker = snapshot["ticker"]
    name = snapshot.get("name") or ticker
    price = _money(snapshot.get("price"))
    trailing = _fmt(snapshot.get("trailing_pe"))
    median = _fmt(snapshot.get("median_pe"))
    gap = _pct(snapshot.get("pe_gap_pct")) if snapshot.get("pe_gap_pct") is not None else "n/a"
    window = snapshot.get("pe_window") or "historical"
    one_liner = (
        f"{name} trades near {_money(snapshot.get('price'))} on a trailing multiple of about {trailing}x"
        f"{f' versus its own {window} median near {median}x' if snapshot.get('median_pe') else ''}"
        f"{', against contested Street targets and the usual concentration and execution risks' if snapshot.get('high_target') else ''}."
    )
    models = snapshot.get("fair_value_models") or []
    model_lines = "\n".join(
        f"- **{row['name']}**: {_money(row['value'])} — {row.get('note') or ''}" for row in models
    ) or "- Independent fair-value models were sparse for this name."
    headlines = snapshot.get("headlines") or []
    bull_bits = [f"- {row.get('headline')}" for row in headlines[:3] if row.get("headline")]
    if not bull_bits:
        bull_bits = ["- Street coverage and recent filings supply the constructive case; pull the latest 10-Q for segment detail."]
    bear_bits = [f"- {row.get('headline')}" for row in headlines[3:6] if row.get("headline")]
    if len(bear_bits) < 2:
        bear_bits.extend(
            [
                "- Multiple risk: paying above the company's own history embeds growth that still has to show up in the numbers.",
                "- Concentration and execution: watch customer, geography, and product-cycle dependency in the next filings.",
            ]
        )
    high = _money(snapshot.get("high_target"))
    low = _money(snapshot.get("low_target"))
    as_of = snapshot.get("as_of") or date.today().isoformat()
    body = f"""# {name} ({ticker})
### What you're actually looking at near {price}

*Research note — {as_of}. Educational analysis, not financial advice.*

---

## The one-line version

{one_liner}

That's the tension. Everything below is the detail.

---

## 1. What you're paying

| | Now | Its own {window} median | Gap |
|---|---|---|---|
| P/E (trailing) | ~{trailing} | ~{median} | **{gap}** |
| P/E (forward) | ~{_fmt(snapshot.get('forward_pe'))} | — | — |
| EPS (TTM) | {_fmt(snapshot.get('trailing_eps'), 2)} | — | — |
| Gross margin | {_fmt(snapshot.get('gross_margin'))}% | — | — |

**What that means in plain terms:** the gap versus the company's own history is the growth or durability the market is already pricing. It is not automatically wrong — it is the bet.

Fair-value anchors on file:
{model_lines}

Street targets run from {low} to {high}. A wide spread means the name is contested, not consensus.

---

## 2. What the bulls are counting on

{chr(10).join(bull_bits)}

---

## 3. What the bears see

{chr(10).join(bear_bits)}

---

## 4. What would have to be true

For the stock to justify ~{trailing}x rather than its {window} ~{median}x, roughly all of the following need to hold:

1. **Growth or margin durability** shows up in the next several reports, not just in narrative.
2. **Key revenue concentrations** survive competitive and regulatory pressure.
3. **Execution** on the current product or services cycle stays on schedule.
4. **The Street target range** compresses as results clarify the contested assumptions.

**Ask yourself honestly: how many of those would you bet on individually?** Multiply your answers together.

---

## 5. What to watch next

- Next earnings date: {snapshot.get('earnings', {}).get('next_earnings_date') or 'check the company calendar'}
- Trailing and forward multiples versus the company's own history
- Segment growth rates in the next 10-Q / earnings release
- Material Form 4 and 13F changes
- Whether the Street high-to-low target spread narrows or widens

---

{NON_VERDICT}

---

{_disclaimer(as_of)}
"""
    # Scrub only the generated narrative blocks, not the fixed legal footer.
    body = scrub_copy(body.replace(NON_VERDICT, "<<<NON_VERDICT>>>").replace(_disclaimer(as_of), "<<<DISCLAIMER>>>"))
    return body.replace("<<<NON_VERDICT>>>", NON_VERDICT).replace("<<<DISCLAIMER>>>", _disclaimer(as_of))


def _assemble_from_sections(snapshot: dict[str, Any], sections: dict[str, Any]) -> str:
    ticker = snapshot["ticker"]
    name = snapshot.get("name") or ticker
    price = _money(snapshot.get("price"))
    as_of = snapshot.get("as_of") or date.today().isoformat()
    one = scrub_copy(str(sections.get("one_line") or "").strip())
    paying = scrub_copy(str(sections.get("what_youre_paying") or "").strip())
    bulls = scrub_copy(str(sections.get("bulls") or "").strip())
    bears = scrub_copy(str(sections.get("bears") or "").strip())
    assumptions = scrub_copy(str(sections.get("assumptions") or "").strip())
    watch = scrub_copy(str(sections.get("watch") or "").strip())
    if not one or not paying:
        return _fallback_markdown(snapshot)
    return "\n".join(
        [
            f"# {name} ({ticker})",
            f"### What you're actually looking at near {price}",
            "",
            f"*Research note — {as_of}. Educational analysis, not financial advice.*",
            "",
            "---",
            "",
            "## The one-line version",
            "",
            one,
            "",
            "That's the tension. Everything below is the detail.",
            "",
            "---",
            "",
            "## 1. What you're paying",
            "",
            paying,
            "",
            "---",
            "",
            "## 2. What the bulls are counting on",
            "",
            bulls,
            "",
            "---",
            "",
            "## 3. What the bears see",
            "",
            bears,
            "",
            "---",
            "",
            "## 4. What would have to be true",
            "",
            assumptions,
            "",
            "---",
            "",
            "## 5. What to watch next",
            "",
            watch,
            "",
            "---",
            "",
            NON_VERDICT,
            "",
            "---",
            "",
            _disclaimer(as_of),
            "",
        ]
    )


def generate_reasoning_report(ticker: str) -> dict[str, Any]:
    snapshot = build_reasoning_snapshot(ticker)
    sections = claude.reasoning_sections(snapshot["ticker"], snapshot)
    markdown = _assemble_from_sections(snapshot, sections) if sections else _fallback_markdown(snapshot)
    return {
        "ticker": snapshot["ticker"],
        "name": snapshot.get("name"),
        "price": snapshot.get("price"),
        "as_of": snapshot.get("as_of"),
        "one_line": _extract_one_line(markdown),
        "markdown": markdown,
        "valuation": {
            "trailing_pe": snapshot.get("trailing_pe"),
            "forward_pe": snapshot.get("forward_pe"),
            "median_pe": snapshot.get("median_pe"),
            "pe_window": snapshot.get("pe_window"),
            "pe_gap_pct": snapshot.get("pe_gap_pct"),
            "trailing_eps": snapshot.get("trailing_eps"),
            "gross_margin": snapshot.get("gross_margin"),
            "average_target": snapshot.get("average_target"),
            "high_target": snapshot.get("high_target"),
            "low_target": snapshot.get("low_target"),
            "fair_value_models": snapshot.get("fair_value_models") or [],
            "data_notes": snapshot.get("data_notes") or [],
        },
        "available": True,
        "error": None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _extract_one_line(markdown: str) -> str:
    match = re.search(r"## The one-line version\s*\n+(.+)", markdown)
    if not match:
        return ""
    return match.group(1).strip()


def apply_reasoning_paywall(payload: dict[str, Any], entitlement: str) -> dict[str, Any]:
    if entitlement == "full":
        return payload
    data = dict(payload)
    markdown = str(data.get("markdown") or "")
    one = data.get("one_line") or _extract_one_line(markdown)
    teaser_pay = ""
    match = re.search(r"## 1\. What you're paying\s*\n+([\s\S]*?)(?:\n---|\n## 2\.)", markdown)
    if match:
        teaser_pay = match.group(1).strip()
        # Keep table + first paragraph only for preview
        parts = re.split(r"\n\s*\n", teaser_pay)
        teaser_pay = "\n\n".join(parts[:2])
    preview = "\n".join(
        [
            f"# {data.get('name') or data.get('ticker')} ({data.get('ticker')})",
            "",
            f"*Research note — {data.get('as_of')}. Educational analysis, not financial advice.*",
            "",
            "---",
            "",
            "## The one-line version",
            "",
            one or "Sign in or upgrade to read the full research note.",
            "",
            "---",
            "",
            "## 1. What you're paying",
            "",
            teaser_pay or "Valuation detail is available in the full research note.",
            "",
            "---",
            "",
            "## Preview locked",
            "",
            "Bull case, bear case, assumption testing, and what to watch next are available with a free monthly report allowance or Premium.",
            "",
            "---",
            "",
            NON_VERDICT,
            "",
            "---",
            "",
            _disclaimer(str(data.get("as_of") or date.today().isoformat())),
            "",
        ]
    )
    valuation = dict(data.get("valuation") or {})
    for key in ("average_target", "high_target", "low_target"):
        if key in valuation:
            valuation[key] = "$$$.$$"
    data["markdown"] = preview
    data["one_line"] = one
    data["valuation"] = valuation
    data["preview"] = True
    return data
