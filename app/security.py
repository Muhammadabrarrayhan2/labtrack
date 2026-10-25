from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# Used when the email does not exist, so login time does not reveal which emails are registered
DUMMY_HASH = hash_password("timing-attack-mitigation")


def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# Tokens are issued and checked by different Cloud Run instances whose clocks can differ
# slightly; without leeway PyJWT rejects a fresh token whose iat is a moment "in the future".
CLOCK_SKEW_LEEWAY = timedelta(seconds=30)


def decode_token(token: str) -> dict:
    return jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], leeway=CLOCK_SKEW_LEEWAY
    )
