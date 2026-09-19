"""Shared ticker ↔ company name catalog for search and directory labels."""

from __future__ import annotations

# Official display names for the launch / popular set.
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
    "UNH": "UnitedHealth Group Incorporated",
    "XOM": "Exxon Mobil Corporation",
    "MA": "Mastercard Incorporated",
    "COST": "Costco Wholesale Corporation",
    "HD": "The Home Depot Inc.",
    "PG": "Procter & Gamble Company",
    "JNJ": "Johnson & Johnson",
    "ABBV": "AbbVie Inc.",
    "NFLX": "Netflix Inc.",
    "CRM": "Salesforce Inc.",
    "BAC": "Bank of America Corporation",
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

TICKER_SECTORS: dict[str, str] = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "NVDA": "Technology",
    "AMZN": "Consumer Cyclical",
    "GOOGL": "Communication Services",
    "META": "Communication Services",
    "TSLA": "Consumer Cyclical",
    "BRK.B": "Financial Services",
    "AVGO": "Technology",
    "JPM": "Financial Services",
    "LLY": "Healthcare",
    "V": "Financial Services",
    "UNH": "Healthcare",
    "XOM": "Energy",
    "MA": "Financial Services",
    "COST": "Consumer Defensive",
    "HD": "Consumer Cyclical",
    "PG": "Consumer Defensive",
    "JNJ": "Healthcare",
    "ABBV": "Healthcare",
    "NFLX": "Communication Services",
    "CRM": "Technology",
    "BAC": "Financial Services",
    "AMD": "Technology",
    "WMT": "Consumer Defensive",
    "KO": "Consumer Defensive",
    "PEP": "Consumer Defensive",
    "MRK": "Healthcare",
    "ADBE": "Technology",
    "TMO": "Healthcare",
    "PLTR": "Technology",
    "COIN": "Financial Services",
    "SOFI": "Financial Services",
    "RIVN": "Consumer Cyclical",
    "NIO": "Consumer Cyclical",
    "LCID": "Consumer Cyclical",
    "HOOD": "Financial Services",
    "GME": "Consumer Cyclical",
    "AMC": "Communication Services",
    "MSTR": "Technology",
    "SMCI": "Technology",
    "ARM": "Technology",
    "UBER": "Technology",
    "DIS": "Communication Services",
    "BA": "Industrials",
    "INTC": "Technology",
    "PYPL": "Financial Services",
    "SQ": "Technology",
    "SHOP": "Technology",
    "SNOW": "Technology",
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
    "procter & gamble": "PG",
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
    "micron": "MU",
    "sandisk": "SNDK",
    "san disk": "SNDK",
}


# Yahoo / market data symbols when the public ticker differs (e.g. Block).
MARKET_SYMBOL_ALIASES: dict[str, str] = {
    "SQ": "XYZ",
}


def market_symbol(ticker: str) -> str:
    symbol = ticker.strip().upper()
    return MARKET_SYMBOL_ALIASES.get(symbol, symbol)


def display_name(ticker: str) -> str | None:
    return TICKER_NAMES.get(ticker.strip().upper())


def catalog_entries() -> list[dict[str, str]]:
    return [
        {"ticker": ticker, "company_name": name, "name": name, "sector": TICKER_SECTORS.get(ticker, "")}
        for ticker, name in sorted(TICKER_NAMES.items())
    ]


def resolve_query_to_ticker(query: str) -> str | None:
    """Resolve a ticker or company name fragment to a single best ticker."""
    hits = search_tickers(query, limit=1)
    return hits[0]["ticker"] if hits else None


def search_tickers(query: str, *, limit: int = 10) -> list[dict[str, str]]:
    """Ranked search: exact ticker, exact company, partial ticker, partial company.

    Empty query returns the full catalog alphabetically (up to limit, or all if limit is large).
    Each hit includes ticker + company_name (+ name alias for older callers).
    """
    raw = (query or "").strip()
    if not raw:
        return [
            {"ticker": row["ticker"], "company_name": row["company_name"], "name": row["company_name"]}
            for row in catalog_entries()
        ]

    upper = raw.upper()
    lower = raw.lower()
    # score buckets: 0 exact ticker, 1 exact company/alias, 2 ticker prefix, 3 company prefix, 4 company/alias substring
    scored: list[tuple[int, str, str]] = []
    seen: set[str] = set()

    def add(score: int, ticker: str) -> None:
        if ticker not in TICKER_NAMES or ticker in seen:
            return
        seen.add(ticker)
        name = TICKER_NAMES[ticker]
        scored.append((score, ticker, name))

    if upper in TICKER_NAMES:
        add(0, upper)

    for ticker, name in TICKER_NAMES.items():
        if name.lower() == lower:
            add(1, ticker)
    if lower in NAME_ALIASES:
        add(1, NAME_ALIASES[lower])

    for ticker in TICKER_NAMES:
        if ticker.startswith(upper):
            add(2, ticker)

    for ticker, name in TICKER_NAMES.items():
        name_l = name.lower()
        if name_l.startswith(lower):
            add(3, ticker)
        elif lower in name_l:
            add(4, ticker)

    for alias, ticker in NAME_ALIASES.items():
        if alias == lower:
            add(1, ticker)
        elif alias.startswith(lower):
            add(3, ticker)
        elif lower in alias:
            add(4, ticker)

    scored.sort(key=lambda item: (item[0], item[1]))
    return [
        {"ticker": ticker, "company_name": name, "name": name}
        for _, ticker, name in scored[:limit]
    ]
