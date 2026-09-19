"""Upsert official company names for the launch ticker set into the stocks table."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import ensure_user_schema
from services.stock_seed import upsert_company_names


def main() -> int:
    ensure_user_schema()
    result = upsert_company_names()
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
