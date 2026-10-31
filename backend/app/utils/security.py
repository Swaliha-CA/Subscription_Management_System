"""Password hashing, JWT token creation/verification, and password validation."""
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.config import config

PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;\']).{9,}$'
)


def hash_password(plain: str) -> str:
    # bcrypt has a 72-byte limit; we use SHA-256 pre-hash to safely support longer passwords
    import hashlib, base64
    digest = hashlib.sha256(plain.encode("utf-8")).digest()
    secret = base64.b64encode(digest)
    return bcrypt.hashpw(secret, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    import hashlib, base64
    digest = hashlib.sha256(plain.encode("utf-8")).digest()
    secret = base64.b64encode(digest)
    try:
        return bcrypt.checkpw(secret, hashed.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if len(password) <= 8:
        return False, "Password must be more than 8 characters."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;\']', password):
        return False, "Password must contain at least one special character."
    return True, ""


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def generate_reset_token() -> str:
    return secrets.token_urlsafe(48)
