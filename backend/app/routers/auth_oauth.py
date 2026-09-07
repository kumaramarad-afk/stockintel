from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import db_session
from app.schemas.user import TokenResponse, UserRead
from services import oauth
from services.paywall import MONTHLY_LIMIT, count_views

router = APIRouter(prefix="/auth", tags=["auth"])


class OAuthTokenRequest(BaseModel):
    provider: str
    id_token: str
    full_name: str | None = None
    next: str = "/"


def _token_response(user, token, db) -> TokenResponse:
    read = UserRead.model_validate(user)
    read.reports_used = count_views(db, user.id)
    read.reports_limit = MONTHLY_LIMIT
    return TokenResponse(access_token=token, user=read)


@router.get("/google/start")
def google_start(next: str = Query("/", alias="next")) -> RedirectResponse:
    try:
        url = oauth.google_authorize_url(next)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RedirectResponse(url)


@router.get("/google/callback")
def google_callback(db: Session = Depends(db_session), code: str | None = None, state: str = "/", error: str | None = None):
    if error or not code:
        raise HTTPException(status_code=400, detail=error or "Google sign-in was cancelled")
    try:
        user, token = oauth.login_from_google_code(db, code)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Google sign-in failed") from exc
    return RedirectResponse(oauth.frontend_callback(token, state or "/"))


@router.get("/apple/start")
def apple_start(next: str = Query("/", alias="next")) -> RedirectResponse:
    try:
        url = oauth.apple_authorize_url(next)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RedirectResponse(url)


@router.post("/apple/callback")
def apple_callback(
    db: Session = Depends(db_session),
    id_token: str | None = Form(default=None),
    state: str = Form(default="/"),
    user: str | None = Form(default=None),
    error: str | None = Form(default=None),
):
    if error or not id_token:
        raise HTTPException(status_code=400, detail=error or "Apple sign-in was cancelled")
    full_name = None
    if user:
        import json

        try:
            payload = json.loads(user)
            name = payload.get("name") or {}
            full_name = " ".join(part for part in (name.get("firstName"), name.get("lastName")) if part)
        except json.JSONDecodeError:
            full_name = None
    try:
        account, token = oauth.login_from_apple_token(db, id_token, full_name)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Apple sign-in failed") from exc
    return RedirectResponse(oauth.frontend_callback(token, state or "/"), status_code=303)


@router.post("/oauth", response_model=TokenResponse)
def oauth_id_token(payload: OAuthTokenRequest, db: Session = Depends(db_session)) -> TokenResponse:
    provider = payload.provider.lower().strip()
    try:
        if provider == "google":
            user, token = oauth.login_from_google_token(db, payload.id_token)
        elif provider == "apple":
            user, token = oauth.login_from_apple_token(db, payload.id_token, payload.full_name)
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Social sign-in failed") from exc
    return _token_response(user, token, db)


@router.get("/providers")
def auth_providers() -> dict[str, bool]:
    return {
        "google": bool(settings.google_client_id),
        "apple": bool(settings.apple_client_id),
    }
