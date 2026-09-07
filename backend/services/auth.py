from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any

from app.config import settings


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(password), hashed)


def create_token(user_id: uuid.UUID | str, hours: int = 720) -> str:
    payload = json.dumps({"sub": str(user_id), "exp": int(time.time()) + hours * 3600}, separators=(",", ":"))
    raw = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    signature = hmac.new(settings.secret_key.encode("utf-8"), raw.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{raw}.{signature}"


def parse_token(token: str) -> dict[str, Any] | None:
    try:
        raw, signature = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(settings.secret_key.encode("utf-8"), raw.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(raw.encode("ascii")))
    except Exception:
        return None
    if int(payload.get("exp") or 0) < int(time.time()):
        return None
    return payload
