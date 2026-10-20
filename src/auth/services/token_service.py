import uuid
from datetime import UTC, datetime, timedelta

import jwt

from src.common.responses.exceptions import (
    ExpiredRefreshTokenException,
    ExpiredTokenException,
    InvalidTokenException,
    InvalidTokenTypeException,
)
from src.config import settings


class TokenService:
    @property
    def access_expire(self) -> timedelta:
        return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    @property
    def refresh_expire(self) -> timedelta:
        return timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    def _create_token(self, user_id: int, token_type: str, expires_delta: timedelta) -> str:
        payload = {
            "sub": str(user_id),
            "type": token_type,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + expires_delta,
            # Уникальный id: без него токены, выпущенные в одну секунду, совпадают.
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def _decode_token(self, token: str, token_type: str) -> dict:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != token_type:
            raise InvalidTokenTypeException()
        if not str(payload.get("sub", "")).isdigit():
            raise InvalidTokenException()
        return payload

    def create_access_token(self, user_id: int) -> str:
        return self._create_token(user_id, "access", self.access_expire)

    def create_refresh_token(self, user_id: int) -> str:
        return self._create_token(user_id, "refresh", self.refresh_expire)

    def decode_access_token(self, token: str) -> dict:
        try:
            return self._decode_token(token, "access")
        except jwt.ExpiredSignatureError:
            raise ExpiredTokenException() from None
        except jwt.InvalidTokenError:
            raise InvalidTokenException() from None

    def decode_refresh_token(self, token: str) -> dict:
        try:
            return self._decode_token(token, "refresh")
        except jwt.ExpiredSignatureError:
            raise ExpiredRefreshTokenException() from None
        except jwt.InvalidTokenError:
            raise InvalidTokenException() from None
