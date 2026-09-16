"""Shared ticker ↔ company name catalog for search and directory labels."""

from __future__ import annotations

# Display names for the launch / popular set. Aliases (lowercase) resolve to ticker.
TICKER_NAMES: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com Inc.",
    "GOOGL": "Alphabet Inc.",
    "META": "Meta Platforms Inc.",
    "TSLA": "Tesla Inc.",
    "BRK.B": "Berkshire Hathaway Inc.",
    "AVGO": "Broadcom Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "LLY": "Eli Lilly and Company",
    "V": "Visa Inc.",
    "UNH": "UnitedHealth Group Inc.",
    "XOM": "Exxon Mobil Corporation",
    "MA": "Mastercard Inc.",
    "COST": "Costco Wholesale Corporation",
    "HD": "The Home Depot Inc.",
    "PG": "Procter & Gamble Co.",
    "JNJ": "Johnson & Johnson",
    "ABBV": "AbbVie Inc.",
    "NFLX": "Netflix Inc.",
    "CRM": "Salesforce Inc.",
    "BAC": "Bank of America Corp.",
    "AMD": "Advanced Micro Devices Inc.",
    "WMT": "Walmart Inc.",
    "KO": "The Coca-Cola Company",
    "PEP": "PepsiCo Inc.",
    "MRK": "Merck & Co. Inc.",
    "ADBE": "Adobe Inc.",
    "TMO": "Thermo Fisher Scientific Inc.",
    "PLTR": "Palantir Technologies Inc.",
    "COIN": "Coinbase Global Inc.",
    "SOFI": "SoFi Technologies Inc.",
    "RIVN": "Rivian Automotive Inc.",
    "NIO": "NIO Inc.",
    "LCID": "Lucid Group Inc.",
    "HOOD": "Robinhood Markets Inc.",
    "GME": "GameStop Corp.",
    "AMC": "AMC Entertainment Holdings Inc.",
    "MSTR": "MicroStrategy Inc.",
    "SMCI": "Super Micro Computer Inc.",
    "ARM": "Arm Holdings plc",
    "UBER": "Uber Technologies Inc.",
    "DIS": "The Walt Disney Company",
    "BA": "The Boeing Company",
    "INTC": "Intel Corporation",
    "PYPL": "PayPal Holdings Inc.",
    "SQ": "Block Inc.",
    "SHOP": "Shopify Inc.",
    "SNOW": "Snowflake Inc.",
}

# Extra searchable aliases → ticker (lowercase keys).
NAME_ALIASES: dict[str, str] = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "amazon": "AMZN",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "berkshire": "BRK.B",
    "berkshire hathaway": "BRK.B",
    "broadcom": "AVGO",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "chase": "JPM",
    "eli lilly": "LLY",
    "lilly": "LLY",
    "visa": "V",
    "unitedhealth": "UNH",
    "united health": "UNH",
    "exxon": "XOM",
    "exxonmobil": "XOM",
    "mastercard": "MA",
    "master card": "MA",
    "costco": "COST",
    "home depot": "HD",
    "procter": "PG",
    "procter and gamble": "PG",
    "p&g": "PG",
    "johnson": "JNJ",
    "abbvie": "ABBV",
    "netflix": "NFLX",
    "salesforce": "CRM",
    "bank of america": "BAC",
    "bofa": "BAC",
    "amd": "AMD",
    "walmart": "WMT",
    "coca cola": "KO",
    "coca-cola": "KO",
    "coke": "KO",
    "pepsi": "PEP",
    "pepsico": "PEP",
    "merck": "MRK",
    "adobe": "ADBE",
    "thermo fisher": "TMO",
    "palantir": "PLTR",
    "coinbase": "COIN",
    "sofi": "SOFI",
    "rivian": "RIVN",
    "nio": "NIO",
    "lucid": "LCID",
    "robinhood": "HOOD",
    "gamestop": "GME",
    "amc": "AMC",
    "microstrategy": "MSTR",
    "strategy": "MSTR",
    "supermicro": "SMCI",
    "super micro": "SMCI",
    "arm": "ARM",
    "uber": "UBER",
    "disney": "DIS",
    "boeing": "BA",
    "intel": "INTC",
    "paypal": "PYPL",
    "block": "SQ",
    "square": "SQ",
    "shopify": "SHOP",
    "snowflake": "SNOW",
}


def display_name(ticker: str) -> str | None:
    return TICKER_NAMES.get(ticker.strip().upper())


def resolve_query_to_ticker(query: str) -> str | None:
    """Resolve a ticker or company name fragment to a single best ticker."""
    raw = (query or "").strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in TICKER_NAMES:
        return upper
    lower = raw.lower()
    if lower in NAME_ALIASES:
        return NAME_ALIASES[lower]
    # Exact company name (case-insensitive)
    for ticker, name in TICKER_NAMES.items():
        if name.lower() == lower:
            return ticker
    # Substring match on name / ticker / alias — prefer shortest name match
    hits: list[tuple[int, str]] = []
    for ticker, name in TICKER_NAMES.items():
        if upper in ticker or lower in name.lower():
            hits.append((len(name), ticker))
    for alias, ticker in NAME_ALIASES.items():
        if lower in alias or alias in lower:
            hits.append((len(alias), ticker))
    if not hits:
        return None
    hits.sort()
    return hits[0][1]


def search_tickers(query: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Return ranked {ticker, name} matches for autocomplete."""
    raw = (query or "").strip()
    if not raw:
        return [{"ticker": t, "name": n} for t, n in list(TICKER_NAMES.items())[:limit]]
    upper = raw.upper()
    lower = raw.lower()
    scored: list[tuple[int, str, str]] = []
    seen: set[str] = set()

    def add(score: int, ticker: str) -> None:
        if ticker in seen:
            return
        seen.add(ticker)
        scored.append((score, ticker, TICKER_NAMES.get(ticker, ticker)))

    if upper in TICKER_NAMES:
        add(0, upper)
    if lower in NAME_ALIASES:
        add(0, NAME_ALIASES[lower])
    for ticker, name in TICKER_NAMES.items():
        name_l = name.lower()
        if ticker.startswith(upper):
            add(1, ticker)
        elif upper in ticker:
            add(2, ticker)
        elif name_l.startswith(lower):
            add(3, ticker)
        elif lower in name_l:
            add(4, ticker)
    for alias, ticker in NAME_ALIASES.items():
        if alias.startswith(lower) or lower in alias:
            add(3 if alias.startswith(lower) else 5, ticker)
    scored.sort(key=lambda item: (item[0], item[1]))
    return [{"ticker": t, "name": n} for _, t, n in scored[:limit]]
