from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import ALGO

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    username: str
    role_id: Optional[int]
    userable_id: Optional[str]
    userable_type: Optional[str]


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CurrentUser:
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak ditemukan",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[ALGO])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kadaluarsa",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        user_id=int(user_id),
        username=payload.get("username", ""),
        role_id=payload.get("role_id"),
        userable_id=payload.get("userable_id"),
        userable_type=payload.get("userable_type"),
    )
