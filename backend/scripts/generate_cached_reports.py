"""Batch-generate cached research reports for the launch ticker set.

Usage (from backend/):
  set PYTHONPATH=.
  py -3 scripts/generate_cached_reports.py
  py -3 scripts/generate_cached_reports.py --limit 5
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.database import ensure_user_schema  # noqa: E402
from services.report_cache import POPULAR_TICKERS, refresh_popular_reports  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate cached research reports")
    parser.add_argument("--limit", type=int, default=None, help="Only first N tickers")
    parser.add_argument("--workers", type=int, default=2, help="Parallel workers")
    args = parser.parse_args()
    ensure_user_schema()
    symbols = POPULAR_TICKERS[: args.limit] if args.limit else POPULAR_TICKERS
    print(f"Generating {len(symbols)} reports with {args.workers} workers…")
    result = refresh_popular_reports(symbols, max_workers=args.workers)
    print(result)
    return 0 if not result.get("failed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
