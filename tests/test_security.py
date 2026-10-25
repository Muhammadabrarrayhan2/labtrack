"""JWT handling across Cloud Run instances with slightly different clocks."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import get_settings
from app.security import decode_token

settings = get_settings()


def _token(iat_offset_s: int, exp_offset_s: int = 3600) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "role": "admin",
        "iat": now + timedelta(seconds=iat_offset_s),
        "exp": now + timedelta(seconds=exp_offset_s),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_token_issued_by_instance_with_clock_slightly_ahead_is_accepted():
    # Issued by an instance whose clock runs 5 s ahead of the one verifying it
    assert decode_token(_token(iat_offset_s=5))["sub"] == "1"


def test_token_issued_far_in_the_future_is_rejected():
    with pytest.raises(jwt.ImmatureSignatureError):
        decode_token(_token(iat_offset_s=600))


def test_expired_token_is_still_rejected():
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(_token(iat_offset_s=-7200, exp_offset_s=-60))
