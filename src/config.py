from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "Jamg'arma Platform API"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"

    # Временная отладка: если True, необработанные ошибки (500)
    # возвращаются клиенту с типом, текстом и трейсом.
    DEBUG_ERRORS: bool = False

    CORS_ORIGINS: list[str] = ["*"]

    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    @property
    def DB_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Логин суперпользователя, который создаёт `python -m src.account.cli create-superuser`
    SUPERUSER: str = "admin"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Секрет cookie-сессии админ-панели (SQLAdmin)
    ADMIN_SESSION_SECRET: str

    MEDIA_PATH: str = "media"
    MAX_APPLICATION_PHOTOS: int = 4
    PHOTO_MAX_SIZE_MB: int = 5
    PHOTO_ALLOWED_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # SSO YIA Portal (e-yoshlar.uz): пользователь проходит OneID на стороне
    # портала, платформа получает code и меняет его на профиль (sso_integration.md).
    # Пока доступ не выдан — SSO_MOCK=True включает тестовый вход /auth/sso/mock-login.
    SSO_MOCK: bool = True
    # Prod: https://api.e-yoshlar.uz, dev-стенд портала: https://dev-api.yiaportal.uz
    SSO_BASE_URL: str = "https://api.e-yoshlar.uz"
    SSO_CLIENT_ID: str = ""
    SSO_CLIENT_SECRET: str = ""
    # Должен в точности совпадать с redirect_uri, зарегистрированным на портале.
    SSO_REDIRECT_URI: str = "http://localhost:8000/api/auth/one-id/callback"
    SSO_TIMEOUT_SECONDS: float = 10.0
    # Сколько живёт подписанный state между authorize и callback.
    SSO_STATE_TTL_SECONDS: int = 600

    # Режим скоринга KATM, пока нет реальной интеграции:
    #   auto_pass       — каждая отправленная заявка проходит скоринг;
    #   auto_fail       — каждая заявка не проходит;
    #   technical_error — имитация сбоя KATM (заявка ждёт повтора);
    #   manual          — результат вносит сотрудник Фонда / Super Admin вручную.
    SCORING_MODE: Literal["auto_pass", "auto_fail", "technical_error", "manual"] = "auto_pass"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def media_dir(self) -> Path:
        path = Path(self.MEDIA_PATH)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path


settings = Settings()
