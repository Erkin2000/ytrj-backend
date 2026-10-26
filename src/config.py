from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "Jamg'arma Platform API"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"

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

    SUPERUSER: str = "admin"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Секрет cookie-сессии админ-панели (SQLAdmin)
    ADMIN_SESSION_SECRET: str

    MEDIA_PATH: str = "media"
    MAX_APPLICATION_PHOTOS: int = 4
    MAX_APPLICATION_FOUNDERS: int = 20

    # Срок кредита в заявке, месяцев (границы уточнить с заказчиком).
    LOAN_TERM_MIN_MONTHS: int = 12
    LOAN_TERM_MAX_MONTHS: int = 36
    PHOTO_MAX_SIZE_MB: int = 5
    PHOTO_ALLOWED_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

    MAX_APPLICATION_DOCUMENTS: int = 4
    DOCUMENT_MAX_SIZE_MB: int = 10
    DOCUMENT_ALLOWED_TYPES: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    SSO_MOCK: bool = True

    SSO_BASE_URL: str
    SSO_CLIENT_ID: str
    SSO_CLIENT_SECRET: str

    SSO_REDIRECT_URI: str
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
