from datetime import datetime, timedelta, timezone
import hashlib

import bcrypt
from jose import jwt

from app.core.config import settings

ALGO = "HS256"
BCRYPT_ROUNDS = 12
_PREFIX = "bsha256$"


def _sha256_bytes(s: str) -> bytes:
    return hashlib.sha256(s.encode("utf-8")).digest()


def _bcrypt_hash(b: bytes) -> str:
    return bcrypt.hashpw(b, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def create_bsha256(raw: str) -> str:
    return _PREFIX + _bcrypt_hash(_sha256_bytes(raw))


def verify_password(raw: str, stored: str) -> bool:
    if not stored.startswith(_PREFIX):
        return False
    hashed = stored[len(_PREFIX):].encode("utf-8")
    return bcrypt.checkpw(_sha256_bytes(raw), hashed)


def create_access_token(sub: str, extra: dict | None = None) -> str:
    data: dict = {
        "sub": sub,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        data.update(extra)
    return jwt.encode(data, settings.SECRET_KEY, algorithm=ALGO)
