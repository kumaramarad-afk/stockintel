"""Exercise ticker + company-name search for the launch set.

Usage (from backend/):
  set PYTHONPATH=.
  py -3 scripts/test_search.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ticker_catalog import TICKER_NAMES, search_tickers


def _tickers(q: str, limit: int = 10) -> list[str]:
    return [row["ticker"] for row in search_tickers(q, limit=limit)]


def main() -> int:
    failures: list[str] = []
    for ticker, name in TICKER_NAMES.items():
        company_word = name.split()[0]
        checks = [
            (ticker, ticker),
            (ticker.lower(), ticker),
            (company_word, ticker),
            (ticker[:2], ticker),
            (name[:4].lower() if len(name) >= 4 else name.lower(), ticker),
        ]
        for query, expected in checks:
            hits = _tickers(query, limit=15)
            if expected not in hits:
                failures.append(f"q={query!r} expected {expected} in {hits}")

    # Edge cases
    if len(search_tickers("", limit=100)) < len(TICKER_NAMES):
        failures.append("empty query should return full catalog")
    if "AAPL" not in _tickers("a", limit=50):
        failures.append("q='a' should include AAPL")
    the_hits = _tickers("the", limit=20)
    if not any(t in the_hits for t in ("DIS", "BA", "HD", "KO")):
        failures.append(f"q='the' should hit Disney/Boeing/etc, got {the_hits}")
    if _tickers("nonexistentzzzz"):
        failures.append("q='nonexistentzzzz' should return no results")
    if "GME" not in _tickers("gm"):
        failures.append("q='gm' should return GME")
    micro = _tickers("micro", limit=15)
    if "MSTR" not in micro or "SMCI" not in micro:
        failures.append(f"q='micro' should include MSTR and SMCI, got {micro}")

    total = len(TICKER_NAMES)
    if failures:
        print(f"{total - len({f.split()[0] for f in failures})}/{total} tickers working")
        print("FAILURES:")
        for item in failures[:40]:
            print(" -", item)
        if len(failures) > 40:
            print(f" - …and {len(failures) - 40} more")
        return 1

    print(f"{total}/{total} tickers working")
    print("Edge cases OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
