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
    """Ответ на вход (пароль или YIA SSO)."""

    access_token: str
    refresh_token: str
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


# ---------- E-IMZO (ЭЦП) ----------


class EimzoLoginDTO(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=512,
        description=(
            "Одноразовый code из сообщения `eimzo:result` страницы-моста E-IMZO "
            "(живёт 60 секунд). При `EIMZO_MOCK=true` — `mock-<ПИНФЛ>`."
        ),
        examples=["q8ZtR0b1Yc3X"],
    )


class EimzoConfigDTO(BaseModel):
    """Что нужно фронтенду, чтобы открыть страницу-мост E-IMZO во всплывающем окне."""

    bridge_url: str
    bridge_origin: str
    client_id: str
    mock: bool


class EimzoCertificateDTO(BaseModel):
    """Данные сертификата, проверенные YIA Portal (POST /api/v1/eimzo/result)."""

    pinfl: str
    full_name: str | None = None
    individual_tin: str | None = None
    legal_entity_tin: str | None = None
    organisation_name: str | None = None
    position: str | None = None
    serial_number: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    request_id: str | None = None
