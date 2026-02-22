from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id_int = int(user_id)
    except Exception as exc:  # noqa: BLE001 - normalize all token errors to 401
        raise credentials_exception from exc

    user = db.get(User, user_id_int)
    if user is None or not user.verified:
        raise credentials_exception

    return user


def require_role(role: UserRole):
    def _require_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user

    return _require_role


def get_current_candidate(current_user: User = Depends(require_role(UserRole.candidate))) -> User:
    return current_user


def get_current_hr(current_user: User = Depends(require_role(UserRole.hr))) -> User:
    return current_user