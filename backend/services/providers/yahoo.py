from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from services.cache import cached
from services.numbers import iso, lookup, pct_change, to_float, to_int, yahoo_symbol
from services.providers.yahoo_http import http_bundle, quote_details

logger = logging.getLogger(__name__)

SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Financial": "XLF",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
    "Industrials": "XLI",
    "Communication Services": "XLC",
}


def load_bundle(ticker: str) -> dict[str, Any]:
    symbol = yahoo_symbol(ticker)

    def _load() -> dict[str, Any]:
        stock = yf.Ticker(symbol)
        source = "yfinance"
        try:
            history = stock.history(period="2y", auto_adjust=True)
        except Exception:
            logger.warning("yfinance history failed for %s; using Yahoo HTTP fallback", symbol)
            history = pd.DataFrame()
        try:
            info = stock.info or {}
        except Exception:
            info = {}
        if history is None or history.empty:
            http_history, http_info = http_bundle(symbol)
            history = http_history
            info = {**http_info, **(info or {})}
            source = "http"
        if history is None or history.empty:
            raise ValueError(f"No market data found for {ticker}.")
        return {"ticker": ticker.upper(), "symbol": symbol, "stock": stock, "history": history, "info": info, "source": source}

    return cached(f"yahoo:{symbol}", _load, ttl=180)


def quote(bundle: dict[str, Any]) -> dict[str, Any]:
    history: pd.DataFrame = bundle["history"]
    info = bundle["info"] or {}
    last = history.iloc[-1]
    prev = history.iloc[-2] if len(history) > 1 else last
    price = to_float(last.get("Close")) or to_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    previous_close = to_float(prev.get("Close")) or to_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
    change_amount = (price - previous_close) if price is not None and previous_close is not None else None
    change_percent = pct_change(price, previous_close)
    month_ago = history.iloc[-21] if len(history) > 21 else history.iloc[0]
    month_return = pct_change(price, to_float(month_ago.get("Close")))
    return {
        "name": info.get("shortName") or info.get("longName") or info.get("displayName"),
        "ticker": bundle["ticker"],
        "price": price,
        "open": to_float(last.get("Open")) or to_float(info.get("open") or info.get("regularMarketOpen")),
        "high": to_float(last.get("High")) or to_float(info.get("dayHigh")),
        "low": to_float(last.get("Low")) or to_float(info.get("dayLow")),
        "previous_close": previous_close,
        "change_amount": change_amount,
        "change_percent": change_percent,
        "volume": to_int(last.get("Volume")) or to_int(info.get("volume")),
        "currency": info.get("currency") or "USD",
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "month_return": month_return,
        "as_of": iso(history.index[-1]),
    }


def period_return(history: pd.DataFrame, days: int) -> float | None:
    if history is None or history.empty or len(history) < 2:
        return None
    current = to_float(history["Close"].iloc[-1])
    idx = max(0, len(history) - days - 1)
    previous = to_float(history["Close"].iloc[idx])
    return pct_change(current, previous)


def technicals(bundle: dict[str, Any]) -> dict[str, Any]:
    history: pd.DataFrame = bundle["history"]
    close = history["Close"].astype(float)
    high = history["High"].astype(float)
    low = history["Low"].astype(float)
    volume = history["Volume"].astype(float)
    price = to_float(close.iloc[-1])
    ma50 = to_float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    ma200 = to_float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    vol_today = to_float(volume.iloc[-1])
    vol_avg = to_float(volume.tail(30).mean())
    high_52 = to_float(high.tail(252).max()) if len(high) else None
    low_52 = to_float(low.tail(252).min()) if len(low) else None

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = to_float((100 - (100 / (1 + rs))).iloc[-1])
    if rsi is None:
        rsi_label = None
    elif rsi < 30:
        rsi_label = "oversold"
    elif rsi > 70:
        rsi_label = "overbought"
    else:
        rsi_label = "healthy"

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal
    macd_value = to_float(macd_line.iloc[-1])
    macd_hist = to_float(hist.iloc[-1])
    macd_signal = "bullish" if macd_hist is not None and macd_hist > 0 else "bearish" if macd_hist is not None else None

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    bandwidth = (upper - lower) / mid.replace(0, np.nan)
    squeeze = False
    if len(bandwidth.dropna()) >= 40:
        current_bw = to_float(bandwidth.iloc[-1])
        cutoff = to_float(bandwidth.tail(120).quantile(0.2))
        squeeze = bool(current_bw is not None and cutoff is not None and current_bw <= cutoff)

    cross = None
    if len(close) >= 210:
        ma50_series = close.rolling(50).mean()
        ma200_series = close.rolling(200).mean()
        prev_diff = to_float(ma50_series.iloc[-6] - ma200_series.iloc[-6])
        last_diff = to_float(ma50_series.iloc[-1] - ma200_series.iloc[-1])
        if prev_diff is not None and last_diff is not None:
            if prev_diff <= 0 < last_diff:
                cross = "golden_cross"
            elif prev_diff >= 0 > last_diff:
                cross = "death_cross"

    support = to_float(low.tail(20).min())
    resistance = to_float(high.tail(20).max())
    recent = close.tail(20)
    pattern = None
    if len(recent) >= 20:
        higher_highs = to_float(recent.max()) is not None and recent.iloc[-1] >= recent.max() * 0.98
        uptrend = bool(recent.iloc[-1] > recent.iloc[0] and recent.iloc[-5] > recent.iloc[0])
        if higher_highs and uptrend:
            pattern = "Breakout / uptrend"
        elif recent.iloc[-1] < recent.iloc[0] and recent.iloc[-1] <= recent.min() * 1.02:
            pattern = "Downtrend / new low"
        else:
            troughs = recent.nsmallest(2)
            if len(troughs) == 2 and abs(troughs.iloc[0] - troughs.iloc[1]) / max(troughs.iloc[0], 1e-9) < 0.03:
                pattern = "Possible double bottom"

    return {
        "price": price,
        "open": to_float(history["Open"].iloc[-1]),
        "high": to_float(history["High"].iloc[-1]),
        "low": to_float(history["Low"].iloc[-1]),
        "week_52_high": high_52,
        "week_52_low": low_52,
        "pct_from_52w_high": pct_change(price, high_52),
        "pct_from_52w_low": pct_change(price, low_52),
        "volume": to_int(vol_today),
        "volume_avg_30d": to_int(vol_avg),
        "volume_vs_avg_pct": pct_change(vol_today, vol_avg),
        "ma50": ma50,
        "ma200": ma200,
        "above_ma50": None if price is None or ma50 is None else price >= ma50,
        "above_ma200": None if price is None or ma200 is None else price >= ma200,
        "cross_alert": cross,
        "rsi": rsi,
        "rsi_label": rsi_label,
        "macd": macd_value,
        "macd_histogram": macd_hist,
        "macd_signal": macd_signal,
        "bollinger_squeeze": squeeze,
        "support": support,
        "resistance": resistance,
        "pattern": pattern,
    }


def fundamentals_from_info(bundle: dict[str, Any]) -> dict[str, Any]:
    info = bundle["info"]
    stock = bundle["stock"]
    revenue_quarters: list[dict[str, Any]] = []
    eps_quarters: list[dict[str, Any]] = []
    try:
        income = stock.quarterly_income_stmt if bundle.get("source") != "http" else None
        if income is not None and not income.empty:
            row = None
            for candidate in ("Total Revenue", "TotalRevenue", "Operating Revenue"):
                if candidate in income.index:
                    row = income.loc[candidate]
                    break
            if row is not None:
                values = [to_float(v) for v in list(row)[:4]]
                for idx, value in enumerate(values):
                    prev = values[idx + 1] if idx + 1 < len(values) else None
                    revenue_quarters.append(
                        {
                            "period": iso(row.index[idx]) if idx < len(row.index) else None,
                            "revenue": value,
                            "growth_pct": pct_change(value, prev),
                        }
                    )
    except Exception:
        logger.debug("quarterly income unavailable", exc_info=True)

    try:
        dates = stock.earnings_dates if bundle.get("source") != "http" else None
        if dates is not None and not dates.empty:
            past = dates.dropna(subset=["Reported EPS"], how="all").head(8)
            if past.empty:
                past = dates.head(8)
            for idx, row in past.iterrows():
                est = to_float(row.get("EPS Estimate"))
                actual = to_float(row.get("Reported EPS"))
                surprise = to_float(row.get("Surprise(%)"))
                beat = None if actual is None or est is None else actual >= est
                eps_quarters.append(
                    {
                        "quarter": iso(idx),
                        "eps_estimate": est,
                        "eps_actual": actual,
                        "beat": beat,
                        "surprise_pct": surprise,
                    }
                )
    except Exception:
        logger.debug("earnings dates unavailable", exc_info=True)

    growths = [q["growth_pct"] for q in revenue_quarters if q.get("growth_pct") is not None]
    accelerating = bool(len(growths) >= 2 and growths[0] is not None and growths[-1] is not None and growths[0] > growths[-1])
    streak = 0
    for row in eps_quarters:
        if row.get("beat") is True:
            streak += 1
        elif row.get("beat") is False:
            break

    gross = to_float(info.get("grossMargins"))
    operating = to_float(info.get("operatingMargins"))
    return {
        "revenue_quarters": revenue_quarters,
        "revenue_acceleration": accelerating if growths else None,
        "eps_quarters": eps_quarters,
        "beat_streak": streak,
        "gross_margin": gross,
        "gross_margin_trend": "up" if gross is not None and gross > 0.4 else "down" if gross is not None and gross < 0.2 else "stable" if gross is not None else None,
        "operating_margin": operating,
        "free_cash_flow": to_float(info.get("freeCashflow")),
        "free_cash_flow_positive": None if info.get("freeCashflow") is None else to_float(info.get("freeCashflow")) is not None and to_float(info.get("freeCashflow")) > 0,
        "debt_to_equity": to_float(info.get("debtToEquity")),
        "return_on_equity": to_float(info.get("returnOnEquity")),
        "pe_ratio": to_float(info.get("trailingPE") or info.get("forwardPE")),
        "peg_ratio": to_float(info.get("pegRatio")),
        "price_to_sales": to_float(info.get("priceToSalesTrailing12Months")),
        "price_to_book": to_float(info.get("priceToBook")),
        "ev_ebitda": to_float(info.get("enterpriseToEbitda")),
        "sector_pe": None,
    }


def analyst_from_yahoo(bundle: dict[str, Any]) -> dict[str, Any]:
    info = bundle.get("info") or {}
    stock = bundle.get("stock")
    price = to_float(bundle["history"]["Close"].iloc[-1])
    buy = hold = sell = 0
    upgrades: list[dict[str, Any]] = []
    downgrades: list[dict[str, Any]] = []
    top_analyst = None
    if bundle.get("source") != "http" and stock is not None:
        try:
            summary = stock.recommendations_summary
            if summary is not None and not summary.empty:
                latest = summary.iloc[0]
                buy = (to_int(latest.get("strongBuy")) or 0) + (to_int(latest.get("buy")) or 0)
                hold = to_int(latest.get("hold")) or 0
                sell = (to_int(latest.get("sell")) or 0) + (to_int(latest.get("strongSell")) or 0)
        except Exception:
            logger.debug("recommendations summary unavailable", exc_info=True)
        try:
            targets = stock.analyst_price_targets
            if isinstance(targets, dict):
                info = {
                    **info,
                    "targetMeanPrice": info.get("targetMeanPrice") or to_float(targets.get("mean")),
                    "targetHighPrice": info.get("targetHighPrice") or to_float(targets.get("high")),
                    "targetLowPrice": info.get("targetLowPrice") or to_float(targets.get("low")),
                }
        except Exception:
            pass
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        try:
            ud = stock.upgrades_downgrades
            if ud is not None and not ud.empty:
                for idx, row in ud.head(40).iterrows():
                    action = str(row.get("Action") or row.get("ToGrade") or "").lower()
                    when = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else None
                    if when is not None and when.tzinfo is None:
                        when = when.replace(tzinfo=timezone.utc)
                    item = {
                        "firm": row.get("Firm"),
                        "action": row.get("Action") or row.get("ToGrade"),
                        "from_grade": row.get("FromGrade"),
                        "to_grade": row.get("ToGrade"),
                        "date": iso(when or idx),
                    }
                    if when is not None and when >= cutoff:
                        if "down" in action:
                            downgrades.append(item)
                        elif "up" in action or "init" in action or "buy" in action:
                            upgrades.append(item)
                    if top_analyst is None and row.get("Firm"):
                        top_analyst = {
                            "firm": row.get("Firm"),
                            "rating": row.get("ToGrade") or row.get("Action"),
                            "date": iso(when or idx),
                        }
        except Exception:
            logger.debug("upgrades/downgrades unavailable", exc_info=True)

    details = quote_details(bundle.get("symbol") or bundle["ticker"]) or {}
    target = to_float(info.get("targetMeanPrice")) or to_float(details.get("average_target"))
    high = to_float(info.get("targetHighPrice")) or to_float(details.get("high_target"))
    low = to_float(info.get("targetLowPrice")) or to_float(details.get("low_target"))
    consensus = info.get("recommendationKey") or info.get("averageAnalystRating") or details.get("consensus")
    if isinstance(consensus, str):
        consensus = consensus.replace("_", " ")
    upgrades = upgrades or details.get("upgrades") or []
    downgrades = downgrades or details.get("downgrades") or []
    top_analyst = top_analyst or details.get("top_analyst")
    trend = None
    if upgrades and not downgrades:
        trend = "up"
    elif downgrades and not upgrades:
        trend = "down"
    elif upgrades or downgrades:
        trend = "mixed"
    return {
        "consensus": consensus,
        "total_analysts": (buy + hold + sell) or to_int(info.get("numberOfAnalystOpinions")) or details.get("total_analysts"),
        "buy": buy,
        "hold": hold,
        "sell": sell,
        "average_target": target,
        "upside_pct": pct_change(target, price),
        "high_target": high,
        "low_target": low,
        "upgrades": upgrades[:8],
        "downgrades": downgrades[:8],
        "recent_actions": details.get("recent_actions") or [],
        "top_analysts": details.get("top_analysts") or [],
        "eps_revisions_trend": trend,
        "top_analyst": top_analyst,
    }


def earnings_from_yahoo(bundle: dict[str, Any]) -> dict[str, Any]:
    stock = bundle["stock"]
    history: pd.DataFrame = bundle["history"]
    info = bundle["info"] or {}
    next_date = iso(info.get("earningsTimestamp") or info.get("earningsDate"))
    session = None
    results: list[dict[str, Any]] = []
    moves: list[float] = []
    if bundle.get("source") != "http":
        try:
            calendar = stock.calendar
            if isinstance(calendar, dict):
                raw = calendar.get("Earnings Date") or calendar.get("earningsDate")
                if isinstance(raw, list) and raw:
                    next_date = iso(raw[0])
                else:
                    next_date = iso(raw) or next_date
            elif calendar is not None and not getattr(calendar, "empty", True):
                next_date = iso(calendar.index[0]) if hasattr(calendar, "index") else iso(calendar)
        except Exception:
            pass
        try:
            dates = stock.earnings_dates
            if dates is not None and not dates.empty:
                close = history["Close"]
                for idx, row in dates.head(12).iterrows():
                    actual = to_float(row.get("Reported EPS"))
                    if actual is None:
                        continue
                    est = to_float(row.get("EPS Estimate"))
                    day_move = None
                    try:
                        loc = close.index.get_indexer([idx], method="nearest")[0]
                        if 0 <= loc < len(close) - 1:
                            day_move = pct_change(to_float(close.iloc[loc + 1]), to_float(close.iloc[loc]))
                            if day_move is not None:
                                moves.append(abs(day_move))
                    except Exception:
                        day_move = None
                    results.append(
                        {
                            "quarter": iso(idx),
                            "eps_estimate": est,
                            "eps_actual": actual,
                            "beat": None if est is None else actual >= est,
                            "next_day_move": day_move,
                        }
                    )
                    if len(results) >= 8:
                        break
        except Exception:
            logger.debug("earnings history unavailable", exc_info=True)

    days_away = None
    if next_date:
        try:
            parsed = datetime.fromisoformat(str(next_date).replace("Z", "+00:00"))
            days_away = (parsed.date() - datetime.now(timezone.utc).date()).days
        except Exception:
            days_away = None

    implied = implied_move(bundle)
    historical = sum(moves) / len(moves) if moves else None
    underpriced = None
    if implied is not None and historical is not None:
        underpriced = implied < historical
    return {
        "next_earnings_date": next_date,
        "days_away": days_away,
        "time_of_day": info.get("earningsCallTime") or session,
        "eps_estimate": to_float(info.get("forwardEps") or info.get("epsForward")),
        "eps_whisper": None,
        "revenue_estimate": to_float(info.get("revenueEstimate") or info.get("targetMeanSales")),
        "results": results,
        "average_historical_move": historical,
        "implied_move": implied,
        "volatility_underpriced": underpriced,
    }


def implied_move(bundle: dict[str, Any]) -> float | None:
    if bundle.get("source") == "http":
        return None
    stock = bundle["stock"]
    price = to_float(bundle["history"]["Close"].iloc[-1])
    if price in (None, 0):
        return None
    try:
        expirations = stock.options
        if not expirations:
            return None
        chain = stock.option_chain(expirations[0])
        calls, puts = chain.calls, chain.puts
        if calls is None or puts is None or calls.empty or puts.empty:
            return None
        calls = calls.copy()
        puts = puts.copy()
        calls["dist"] = (calls["strike"] - price).abs()
        puts["dist"] = (puts["strike"] - price).abs()
        call = calls.sort_values("dist").iloc[0]
        put = puts.sort_values("dist").iloc[0]
        call_mid = _option_mid(call)
        put_mid = _option_mid(put)
        if call_mid is None or put_mid is None:
            return None
        return ((call_mid + put_mid) / price) * 100
    except Exception:
        logger.debug("implied move unavailable", exc_info=True)
        return None


def _option_mid(row: pd.Series) -> float | None:
    bid = to_float(row.get("bid"))
    ask = to_float(row.get("ask"))
    last = to_float(row.get("lastPrice"))
    if bid is not None and ask is not None and ask > 0:
        return (bid + ask) / 2
    return last


def news_from_yahoo(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        raw = [] if bundle.get("source") == "http" else (bundle["stock"].news or [])
        for article in raw[:8]:
            content = article.get("content") if isinstance(article.get("content"), dict) else article
            title = content.get("title") or article.get("title")
            provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
            source = provider.get("displayName") or article.get("publisher") or content.get("provider")
            published = content.get("pubDate") or article.get("providerPublishTime")
            items.append(
                {
                    "source": source,
                    "headline": title,
                    "url": (content.get("canonicalUrl") or {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else article.get("link"),
                    "published_at": iso(datetime.fromtimestamp(published, tz=timezone.utc)) if isinstance(published, (int, float)) else iso(published),
                }
            )
    except Exception:
        logger.debug("yahoo news unavailable", exc_info=True)
    return items


def ownership_from_yahoo(bundle: dict[str, Any]) -> dict[str, Any]:
    info = bundle["info"]
    stock = bundle["stock"]
    insiders: list[dict[str, Any]] = []
    net_shares = 0.0
    try:
        table = stock.insider_transactions if bundle.get("source") != "http" else None
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        if table is not None and not table.empty:
            for _, row in table.head(40).iterrows():
                when = row.get("Start Date")
                parsed = None
                if hasattr(when, "to_pydatetime"):
                    parsed = when.to_pydatetime()
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed is not None and parsed < cutoff:
                    continue
                text = str(row.get("Text") or row.get("Transaction") or "")
                shares = to_float(row.get("Shares") or row.get("Value"))
                action = "Disposed" if "sale" in text.lower() or "sell" in text.lower() else "Acquired" if "buy" in text.lower() or "purchase" in text.lower() else text
                if "sale" in text.lower() or "sell" in text.lower():
                    net_shares -= abs(shares or 0)
                elif "buy" in text.lower() or "purchase" in text.lower():
                    net_shares += abs(shares or 0)
                insiders.append(
                    {
                        "name": row.get("Insider") or row.get("Name"),
                        "title": row.get("Position") or row.get("Relationship"),
                        "action": action,
                        "shares": to_float(row.get("Shares")),
                        "value": to_float(row.get("Value")),
                        "date": iso(parsed or when),
                    }
                )
    except Exception:
        logger.debug("insider transactions unavailable", exc_info=True)

    holders: list[dict[str, Any]] = []
    try:
        inst = stock.institutional_holders if bundle.get("source") != "http" else None
        if inst is not None and not inst.empty:
            for _, row in inst.head(3).iterrows():
                holders.append(
                    {
                        "holder": row.get("Holder"),
                        "shares": to_float(row.get("Shares")),
                        "value": to_float(row.get("Value")),
                        "pct": to_float(row.get("% Out")),
                        "change": to_float(row.get("pctChange") or row.get("Change")),
                    }
                )
    except Exception:
        logger.debug("institutional holders unavailable", exc_info=True)

    details = quote_details(bundle.get("symbol") or bundle["ticker"]) or {}
    short_pct = to_float(info.get("shortPercentOfFloat"))
    if short_pct is not None and short_pct <= 1:
        short_pct *= 100
    short_pct = short_pct if short_pct is not None else to_float(details.get("short_interest_pct"))
    shares_short = to_float(info.get("sharesShort")) or to_float((details.get("info") or {}).get("sharesShort"))
    avg_vol = to_float(info.get("averageVolume") or info.get("averageDailyVolume10Day")) or to_float((details.get("info") or {}).get("averageVolume"))
    days_to_cover = (shares_short / avg_vol) if shares_short and avg_vol else to_float(info.get("shortRatio")) or to_float(details.get("days_to_cover"))
    inst_pct = to_float(info.get("heldPercentInstitutions"))
    if inst_pct is not None and inst_pct <= 1.5:
        inst_pct *= 100
    inst_pct = inst_pct if inst_pct is not None else to_float(details.get("institutional_ownership_pct"))
    holders = holders or details.get("holders") or []
    return {
        "insider_transactions": insiders[:12],
        "net_insider_sentiment": "bullish" if net_shares > 0 else "bearish" if net_shares < 0 else "neutral" if insiders else None,
        "insider_selling": net_shares < 0,
        "institutional_ownership_pct": inst_pct,
        "institutional_ownership_change": details.get("institutional_ownership_change"),
        "new_institutional_additions": details.get("new_institutional_additions") or details.get("new_institutional_buyers"),
        "new_institutional_buyers": details.get("new_institutional_buyers") or details.get("new_institutional_additions"),
        "top_holders": holders[:8],
        "short_interest_pct": short_pct,
        "short_interest_trend": details.get("short_interest_trend"),
        "days_to_cover": days_to_cover,
    }


def dividends_from_yahoo(bundle: dict[str, Any]) -> dict[str, Any] | None:
    info = bundle["info"]
    yield_pct = to_float(info.get("dividendYield"))
    if yield_pct is not None and yield_pct <= 1:
        yield_pct *= 100
    rate = to_float(info.get("dividendRate"))
    if not yield_pct and not rate:
        return None
    payout = to_float(info.get("payoutRatio"))
    if payout is not None and payout <= 2:
        payout *= 100
    return {
        "annual_yield": yield_pct,
        "payout_ratio": payout,
        "growth_rate_5y": to_float(info.get("fiveYearAvgDividendYield")),
        "next_dividend_date": iso(info.get("exDividendDate")),
        "annual_rate": rate,
    }


def sector_from_yahoo(bundle: dict[str, Any]) -> dict[str, Any]:
    info = bundle["info"]
    history: pd.DataFrame = bundle["history"]
    sector = info.get("sector")
    etf = SECTOR_ETFS.get(sector or "", "SPY")
    stock_perf = {
        "1m": period_return(history, 21),
        "3m": period_return(history, 63),
        "1y": period_return(history, 252),
    }
    etf_perf = {"1m": None, "3m": None, "1y": None}
    try:
        etf_hist = yf.Ticker(etf).history(period="1y", auto_adjust=True)
        etf_perf = {
            "1m": period_return(etf_hist, 21),
            "3m": period_return(etf_hist, 63),
            "1y": period_return(etf_hist, 252),
        }
    except Exception:
        logger.debug("sector ETF history unavailable", exc_info=True)
    momentum = None
    if etf_perf["1m"] is not None:
        momentum = "in" if etf_perf["1m"] > 0 else "out"
    return {
        "sector": sector,
        "sector_etf": etf,
        "stock": stock_perf,
        "sector_etf_perf": etf_perf,
        "relative": {
            "1m": None if stock_perf["1m"] is None or etf_perf["1m"] is None else stock_perf["1m"] - etf_perf["1m"],
            "3m": None if stock_perf["3m"] is None or etf_perf["3m"] is None else stock_perf["3m"] - etf_perf["3m"],
            "1y": None if stock_perf["1y"] is None or etf_perf["1y"] is None else stock_perf["1y"] - etf_perf["1y"],
        },
        "sector_momentum": momentum,
        "sector_rank": None,
        "peer_count": None,
    }
