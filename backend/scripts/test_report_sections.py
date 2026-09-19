"""Smoke-test the five report data sections for a few tickers.

Usage (from backend/):
  set PYTHONPATH=.
  py -3 scripts/test_report_sections.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.report_data import (  # noqa: E402
    fetch_all_data_sections,
    get_analyst_ratings,
    get_earnings_this_week,
    get_important_news,
    get_insider_activity,
    get_institutional_holdings,
)

TICKERS = ["AAPL", "TSLA", "NVDA", "COIN"]
SECTIONS = [
    ("analyst_ratings", get_analyst_ratings),
    ("news", get_important_news),
    ("insider", get_insider_activity),
    ("institutions", get_institutional_holdings),
    ("earnings", get_earnings_this_week),
]


def main() -> int:
    failures: list[str] = []
    ok = 0
    total = len(TICKERS) * len(SECTIONS)
    for ticker in TICKERS:
        print(f"\n=== {ticker} ===")
        for name, fn in SECTIONS:
            started = time.perf_counter()
            try:
                rows = fn(ticker)
                ms = int((time.perf_counter() - started) * 1000)
                count = len(rows) if isinstance(rows, list) else 0
                print(f"  {name}: {count} items in {ms}ms")
                ok += 1
            except Exception as exc:
                failures.append(f"{ticker}/{name}: {exc}")
                print(f"  {name}: ERROR {exc}")
        combined = fetch_all_data_sections(ticker)
        for key in ("analyst_ratings", "news", "insider", "institutions", "earnings"):
            if key not in combined:
                failures.append(f"{ticker}/combined missing {key}")
    print(f"\n{ok}/{total} sections working")
    if failures:
        print("FAILURES:")
        for item in failures:
            print(" -", item)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
