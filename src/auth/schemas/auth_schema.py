from datetime import datetime
from enum import StrEnum

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


class LoginTokensDTO(BaseModel):
    """Вход, когда кабинет роли на том же сайте, что и страница входа: только токены."""

    access_token: str
    refresh_token: str
    expires_in: int


class LoginRedirectDTO(BaseModel):
    """Вход, когда кабинет роли на другом поддомене: токенов нет, redirect_url содержит
    одноразовый ?ticket=..., который кабинет меняет через POST /auth/ticket/exchange."""

    role: str | None = None
    redirect_url: str


LoginResultDTO = LoginTokensDTO | LoginRedirectDTO


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


class SSOSite(StrEnum):
    """Сайт, с которого начат вход через YIA Portal: у каждого свой клиент портала
    и свой redirect_uri."""

    MAIN = "yoshlarfondi"
    ADMIN = "admin"


class SSOAuthorizeDTO(BaseModel):
    authorize_url: str
    state: str


class SSOCallbackDTO(BaseModel):
    """Параметры, с которыми YIA Portal вернул пользователя на redirect_uri."""

    code: str | None = Field(default=None, examples=["ONE_TIME_CODE"])
    state: str = Field(examples=["eyJ...signed-state"])
    error: str | None = Field(default=None, examples=[None])


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
