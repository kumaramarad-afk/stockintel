import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from services.auth import parse_token

bearer = HTTPBearer(auto_error=False)


def db_session(db: Session = Depends(get_db)) -> Session:
    return db


def _user_from_creds(
    creds: HTTPAuthorizationCredentials | None,
    db: Session,
) -> User | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    payload = parse_token(creds.credentials)
    if not payload or not payload.get("sub"):
        return None
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except ValueError:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(db_session),
) -> User | None:
    return _user_from_creds(creds, db)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(db_session),
) -> User:
    user = _user_from_creds(creds, db)
    if user is None:
        if creds is None or creds.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Sign in required")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
