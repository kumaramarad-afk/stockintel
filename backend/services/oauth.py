from __future__ import annotations

import logging
import secrets
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from services.auth import create_token, hash_password

logger = logging.getLogger(__name__)


def frontend_callback(token: str, next_path: str = "/research") -> str:
    base = settings.frontend_url.rstrip("/")
    query = urlencode({"token": token, "next": _safe_next(next_path)})
    return f"{base}/auth/callback?{query}"


def _safe_next(next_path: str) -> str:
    path = (next_path or "/research").strip() or "/research"
    if not path.startswith("/") or path.startswith("//"):
        return "/research"
    prefix = path.split("?", 1)[0]
    if prefix in {"/login", "/register", "/auth/callback"} or prefix.startswith("/auth/"):
        return "/research"
    return path


def _issue_user(db: Session, email: str, full_name: str, provider: str, subject: str) -> tuple[User, str]:
    email = email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = db.scalar(select(User).where(User.oauth_provider == provider, User.oauth_subject == subject))
    if user is None:
        user = User(
            email=email or f"{provider}-{subject[:12]}@oauth.local",
            full_name=(full_name or "GetStockReport member").strip()[:255],
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            plan="free",
            oauth_provider=provider,
            oauth_subject=subject,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.oauth_provider = provider
        user.oauth_subject = subject
        if email and user.email.endswith("@oauth.local"):
            user.email = email
        if full_name and user.full_name == "GetStockReport member":
            user.full_name = full_name.strip()[:255]
        db.add(user)
        db.commit()
        db.refresh(user)
    return user, create_token(user.id)


def google_authorize_url(state: str) -> str:
    if not settings.google_client_id:
        raise RuntimeError("Google sign-in is not configured")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{_api_base()}/api/v1/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def apple_authorize_url(state: str) -> str:
    if not settings.apple_client_id:
        raise RuntimeError("Apple sign-in is not configured")
    params = {
        "client_id": settings.apple_client_id,
        "redirect_uri": f"{_api_base()}/api/v1/auth/apple/callback",
        "response_type": "code id_token",
        "response_mode": "form_post",
        "scope": "name email",
        "state": state,
    }
    return "https://appleid.apple.com/auth/authorize?" + urlencode(params)


def _api_base() -> str:
    return settings.api_public_url.rstrip("/")


def exchange_google_code(code: str) -> dict[str, Any]:
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": f"{_api_base()}/api/v1/auth/google/callback",
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        tokens = response.json()
        id_token = tokens.get("id_token")
        if not id_token:
            raise RuntimeError("Google did not return an identity token")
        return verify_google_id_token(id_token)


def verify_google_id_token(token: str) -> dict[str, Any]:
    with httpx.Client(timeout=15.0) as client:
        response = client.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": token})
        if response.status_code >= 400:
            raise RuntimeError("Google identity token was rejected")
        payload = response.json()
    email = str(payload.get("email") or "").lower()
    if settings.google_client_id and str(payload.get("aud") or "") != settings.google_client_id:
        raise RuntimeError("Google identity token audience mismatch")
    if not email:
        raise RuntimeError("Google account email is required")
    return {
        "email": email,
        "full_name": payload.get("name") or email.split("@")[0],
        "subject": str(payload.get("sub") or email),
    }


def verify_apple_id_token(token: str) -> dict[str, Any]:
    jwks_client = jwt.PyJWKClient("https://appleid.apple.com/auth/keys")
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    decode_kwargs: dict[str, Any] = {
        "algorithms": ["RS256"],
        "issuer": "https://appleid.apple.com",
        "options": {"verify_aud": bool(settings.apple_client_id)},
    }
    if settings.apple_client_id:
        decode_kwargs["audience"] = settings.apple_client_id
    payload = jwt.decode(token, signing_key.key, **decode_kwargs)
    email = str(payload.get("email") or "").lower()
    subject = str(payload.get("sub") or "")
    if not subject:
        raise RuntimeError("Apple identity token is missing a subject")
    return {
        "email": email or f"{subject[:18]}@privaterelay.appleid.com",
        "full_name": email.split("@")[0] if email else "Apple member",
        "subject": subject,
    }


def login_from_google_token(db: Session, token: str) -> tuple[User, str]:
    profile = verify_google_id_token(token)
    return _issue_user(db, profile["email"], profile["full_name"], "google", profile["subject"])


def login_from_apple_token(db: Session, token: str, full_name: str | None = None) -> tuple[User, str]:
    profile = verify_apple_id_token(token)
    return _issue_user(db, profile["email"], full_name or profile["full_name"], "apple", profile["subject"])


def login_from_google_code(db: Session, code: str) -> tuple[User, str]:
    profile = exchange_google_code(code)
    return _issue_user(db, profile["email"], profile["full_name"], "google", profile["subject"])


def user_id_from_state_token(state: str) -> str:
    return state
