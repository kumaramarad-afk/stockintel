from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ReportView, User

PLACEHOLDER = "$$$.$$"
MONTHLY_LIMIT = settings.monthly_report_limit
PAID_PLANS = frozenset({"pro", "newsletter_pro"})

PUBLIC_LOCKED = ["targets", "direction", "summary", "risks", "catalysts", "analyst_case", "insider_amounts"]
BASIC_LOCKED = ["targets", "direction", "risks", "catalysts", "analyst_case", "insider_amounts"]


def is_paid_plan(plan: str | None) -> bool:
    return (plan or "") in PAID_PLANS


def is_newsletter_plan(plan: str | None) -> bool:
    return (plan or "") == "newsletter_pro"


def current_period(now: datetime | None = None) -> str:
    stamp = now or datetime.now(timezone.utc)
    return stamp.strftime("%Y-%m")


def count_views(db: Session, user_id: UUID, period: str | None = None) -> int:
    month = period or current_period()
    value = db.scalar(
        select(func.count()).select_from(ReportView).where(ReportView.user_id == user_id, ReportView.period == month)
    )
    return int(value or 0)


def has_viewed(db: Session, user_id: UUID, ticker: str, period: str | None = None) -> bool:
    month = period or current_period()
    row = db.scalar(
        select(ReportView.id).where(
            ReportView.user_id == user_id,
            ReportView.ticker == ticker.upper(),
            ReportView.period == month,
        )
    )
    return row is not None


def reports_generated_of(user: User) -> int:
    return int(getattr(user, "reports_generated", 0) or 0)


def quota_fields(user: User | None, db: Session | None = None) -> dict[str, int]:
    if user is None:
        return {
            "reports_generated": 0,
            "reports_used": 0,
            "reports_limit": MONTHLY_LIMIT,
            "reports_remaining": MONTHLY_LIMIT,
        }
    used = count_views(db, user.id) if db is not None else reports_generated_of(user)
    remaining = MONTHLY_LIMIT if is_paid_plan(user.plan) else max(0, MONTHLY_LIMIT - used)
    return {
        "reports_generated": used,
        "reports_used": used,
        "reports_limit": MONTHLY_LIMIT,
        "reports_remaining": remaining,
    }


def record_view(db: Session, user: User, ticker: str) -> None:
    if is_paid_plan(user.plan):
        return
    month = current_period()
    symbol = ticker.upper()
    locked = db.scalar(select(User).where(User.id == user.id).with_for_update())
    if locked is None:
        return
    if has_viewed(db, locked.id, symbol, month):
        return
    if count_views(db, locked.id, month) >= MONTHLY_LIMIT:
        return
    locked.reports_generated = count_views(db, locked.id, month) + 1
    db.add(ReportView(user_id=locked.id, ticker=symbol, period=month))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    else:
        db.refresh(user)


def resolve_access(user: User | None, ticker: str, db: Session | None, consume: bool = False) -> dict[str, Any]:
    if user is None:
        return {
            "tier": "guest",
            "entitlement": "public",
            "pro": False,
            "locked_fields": list(PUBLIC_LOCKED),
            **quota_fields(user, db),
        }
    if is_paid_plan(user.plan):
        return {
            "tier": user.plan,
            "entitlement": "full",
            "pro": True,
            "locked_fields": [],
            **quota_fields(user, db),
        }
    if consume and db is not None:
        record_view(db, user, ticker)
    viewed = has_viewed(db, user.id, ticker) if db is not None else False
    quota = quota_fields(user, db)
    if viewed:
        return {
            "tier": "free",
            "entitlement": "full",
            "pro": False,
            "locked_fields": [],
            **quota,
        }
    return {
        "tier": "free",
        "entitlement": "public",
        "pro": False,
        "locked_fields": list(PUBLIC_LOCKED),
        **quota,
    }


def _preview(text: str | None, sentences: int = 2) -> str:
    blob = (text or "").strip()
    if not blob:
        return ""
    parts: list[str] = []
    buffer = ""
    for char in blob:
        buffer += char
        if char in ".!?" and len(buffer.strip()) > 12:
            parts.append(buffer.strip())
            buffer = ""
            if len(parts) >= sentences:
                break
    if not parts:
        return blob[:180]
    return " ".join(parts)


def _mask_money(value: Any) -> str:
    return PLACEHOLDER


def apply_paywall(section: str, data: dict[str, Any] | None, entitlement: str) -> dict[str, Any] | None:
    if data is None or entitlement == "full":
        return data
    payload = copy.deepcopy(data)
    guest = entitlement in {"public", "locked"}
    if guest:
        _redact_guest(section, payload)
    else:
        _redact_basic(section, payload)
    return payload


def _redact_targets(payload: dict[str, Any]) -> None:
    for key in ("average_target", "high_target", "low_target", "upside_pct", "current_target"):
        if key in payload:
            payload[key] = PLACEHOLDER


def _redact_grade_rows(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    cleaned = []
    for row in rows or []:
        item = dict(row)
        item["price_target"] = PLACEHOLDER
        cleaned.append(item)
    return cleaned


def _redact_actions(actions: list[dict[str, Any]] | None, hide_identity: bool) -> list[dict[str, Any]]:
    cleaned = []
    for row in actions or []:
        item = dict(row)
        item["previous_target"] = PLACEHOLDER
        item["new_target"] = PLACEHOLDER
        item["direction"] = None
        if hide_identity:
            item["name"] = item.get("name") or "Research desk"
        cleaned.append(item)
    return cleaned


def _redact_top(rows: list[dict[str, Any]] | None, hide_case: bool) -> list[dict[str, Any]]:
    cleaned = []
    for row in rows or []:
        item = dict(row)
        if hide_case:
            item["current_target"] = PLACEHOLDER
            item["sentiment"] = None
            item["accuracy_pct"] = None
        cleaned.append(item)
    return cleaned


def _redact_guest(section: str, payload: dict[str, Any]) -> None:
    _redact_targets(payload)
    if "recent_actions" in payload:
        payload["recent_actions"] = _redact_actions(payload.get("recent_actions"), hide_identity=False)
    if "top_analysts" in payload:
        payload["top_analysts"] = _redact_top(payload.get("top_analysts"), hide_case=True)
    if "upgrades" in payload:
        payload["upgrades"] = _redact_grade_rows(payload.get("upgrades"))
    if "downgrades" in payload:
        payload["downgrades"] = _redact_grade_rows(payload.get("downgrades"))
    if section == "ai":
        payload["what_the_data_shows"] = ""
        payload["why_it_scores"] = ""
        payload["key_risks"] = [PLACEHOLDER, PLACEHOLDER]
        payload["upcoming_catalysts"] = [PLACEHOLDER]
        payload["outlook"] = ""
        payload["summary_preview"] = ""
    if section == "analysts":
        payload["high_target"] = PLACEHOLDER
        payload["low_target"] = PLACEHOLDER
        payload["average_target"] = PLACEHOLDER
        payload["upside_pct"] = PLACEHOLDER
    if section == "ownership":
        _redact_ownership(payload, guest=True)
    if section == "header":
        payload["risk_flags"] = []


def _redact_basic(section: str, payload: dict[str, Any]) -> None:
    _redact_targets(payload)
    if "recent_actions" in payload:
        payload["recent_actions"] = _redact_actions(payload.get("recent_actions"), hide_identity=False)
    if "top_analysts" in payload:
        payload["top_analysts"] = _redact_top(payload.get("top_analysts"), hide_case=True)
    if "upgrades" in payload:
        payload["upgrades"] = _redact_grade_rows(payload.get("upgrades"))
    if "downgrades" in payload:
        payload["downgrades"] = _redact_grade_rows(payload.get("downgrades"))
    if section == "ai":
        full = str(payload.get("what_the_data_shows") or payload.get("why_it_scores") or "")
        preview = _preview(full)
        payload["summary_preview"] = preview
        payload["what_the_data_shows"] = preview
        payload["why_it_scores"] = preview
        payload["key_risks"] = [PLACEHOLDER, PLACEHOLDER]
        payload["upcoming_catalysts"] = [PLACEHOLDER]
        payload["outlook"] = ""
    if section == "analysts":
        payload["high_target"] = PLACEHOLDER
        payload["low_target"] = PLACEHOLDER
        payload["average_target"] = PLACEHOLDER
        payload["upside_pct"] = PLACEHOLDER
    if section == "ownership":
        _redact_ownership(payload, guest=False)
    if section == "header":
        payload["risk_flags"] = []


def _redact_ownership(payload: dict[str, Any], guest: bool) -> None:
    rows = []
    for row in payload.get("insider_transactions") or []:
        item = dict(row)
        item["shares"] = PLACEHOLDER
        item["value"] = PLACEHOLDER
        if guest:
            item["title"] = None
        rows.append(item)
    payload["insider_transactions"] = [] if guest else rows
    holders = []
    for row in payload.get("top_holders") or []:
        item = dict(row)
        item["shares"] = PLACEHOLDER
        item["value"] = PLACEHOLDER
        item["pct"] = PLACEHOLDER
        item["change"] = PLACEHOLDER
        holders.append(item)
    payload["top_holders"] = [] if guest else holders
    trades = []
    for row in payload.get("congressional_trades") or []:
        item = dict(row)
        item["amount"] = PLACEHOLDER
        trades.append(item)
    payload["congressional_trades"] = [] if guest else trades
    for key in ("institutional_ownership_pct", "institutional_ownership_change", "short_interest_pct", "days_to_cover"):
        if key in payload and payload[key] is not None:
            payload[key] = PLACEHOLDER
