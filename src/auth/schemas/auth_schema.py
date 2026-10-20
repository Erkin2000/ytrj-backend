from datetime import datetime

from pydantic import BaseModel, Field

from src.account.schemas.user_schema import PasswordStr, PhoneStr, PinflStr


class LoginDTO(BaseModel):
    username: str = Field(examples=["admin"])
    password: str = Field(examples=["admin12345"])


class TokenPairDTO(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequestDTO(BaseModel):
    refresh_token: str


class ChangePasswordDTO(BaseModel):
    current_password: str
    new_password: PasswordStr


class RefreshTokenDTO(BaseModel):
    id: int
    refresh_token: str
    user_id: int
    expires_at: datetime
    is_revoked: bool
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime


class RefreshTokenCreateDTO(BaseModel):
    user_id: int
    refresh_token: str
    expires_at: datetime
    user_agent: str | None = None
    ip_address: str | None = None


# ---------- OneID ----------


class OneIDAuthorizeDTO(BaseModel):
    authorize_url: str
    state: str


class OneIDCallbackDTO(BaseModel):
    code: str
    state: str | None = None


class OneIDProfileDTO(BaseModel):
    """Данные, которые платформа получает из OneID после входа."""

    sub: str
    pinfl: PinflStr
    full_name: str
    phone: PhoneStr | None = None
    passport_number: str | None = None
    inn: str | None = None
    email: str | None = None


class OneIDMockLoginDTO(BaseModel):
    """Тестовый вход вместо OneID (только при ONEID_MOCK=True)."""

    pinfl: PinflStr = Field(examples=["30101900000011"])
    full_name: str = Field(examples=["Алиев Али Алиевич"])
    phone: PhoneStr | None = Field(default=None, examples=["+998901234567"])
    passport_number: str | None = Field(default=None, examples=["AA1234567"])
    inn: str | None = Field(default=None, examples=["123456789"])
    email: str | None = None
