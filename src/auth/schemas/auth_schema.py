from datetime import datetime

from pydantic import BaseModel, Field

from src.account.schemas.user_schema import PasswordStr, PinflStr


class LoginDTO(BaseModel):
    username: str = Field(examples=["admin"])
    password: str = Field(examples=["admin12345"])


class TokenPairDTO(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResultDTO(TokenPairDTO):
    """Ответ на вход (пароль или YIA SSO): токены + куда отправить браузер.

    redirect_url — кабинет роли (ROLE_HOME_URLS) с одноразовым ?ticket=...;
    кабинет на своём поддомене меняет билет на токены через POST /auth/ticket/exchange.
    """

    role: str | None = None
    redirect_url: str


class TicketExchangeDTO(BaseModel):
    ticket: str = Field(min_length=16, max_length=128, examples=["k3J9x...one-time-ticket"])


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


# ---------- YIA SSO ----------


class SSOProfileDTO(BaseModel):
    """Данные, которые платформа получает от YIA Portal после входа.
    Гарантированы sub и full_name; pinfl — по договорённости с порталом;
    region/city/makhalla/role заполняются только у ётакчи."""

    sub: str
    full_name: str
    pinfl: PinflStr | None = None
    region: str | None = None
    city: str | None = None
    makhalla: str | None = None
    yia_role: str | None = None


class SSOMockLoginDTO(BaseModel):
    """Тестовый вход вместо YIA Portal (только при SSO_MOCK=True)."""

    pinfl: PinflStr = Field(examples=["30101900000011"])
    full_name: str = Field(examples=["Алиев Али Алиевич"])
    sub: str | None = Field(
        default=None,
        description="Стабильный идентификатор пользователя портала; по умолчанию mock-<pinfl>",
    )
