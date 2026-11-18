"""Адаптер E-IMZO через мост YIA Portal (eimzo_api.md).

Ключи E-IMZO работают только на домене портала, поэтому человек подписывает на
странице-мосте `https://e-yoshlar.uz/eimzo-bridge` (её открывает фронтенд во
всплывающем окне), а backend получает одноразовый code (60 секунд) и меняет его
на проверенные порталом данные сертификата:

1. ``POST {API}/api/v1/auth/token`` (client_credentials) — токен на 1 час, кэшируется;
2. ``POST {API}/api/v1/eimzo/result {code}`` — ПИНФЛ, Ф.И.О., серийный номер и срок
   сертификата.

Используется и для входа члена Совета, и для подписания бюллетеня: каждое
подписание — отдельный проход через мост, после которого сверяется ПИНФЛ.

При ``EIMZO_MOCK=True`` внешние вызовы не выполняются: code вида ``mock-<ПИНФЛ>``
даёт сертификат с этим ПИНФЛ.
"""

import asyncio
import logging
import re
import time

import httpx

from src.auth.schemas.auth_schema import EimzoCertificateDTO, EimzoConfigDTO
from src.common.responses.exceptions import EimzoException, EimzoInvalidCodeException
from src.config import settings

logger = logging.getLogger(__name__)

TOKEN_PATH = "/api/v1/auth/token"
RESULT_PATH = "/api/v1/eimzo/result"
MOCK_CODE = re.compile(r"^mock-(\d{14})(?:-.*)?$")
# Токен обновляется заранее, чтобы не истечь посреди запроса.
TOKEN_REFRESH_MARGIN_SECONDS = 60


class EimzoService:
    _token: str | None = None
    _token_expires_at: float = 0.0
    _token_lock: asyncio.Lock | None = None

    @staticmethod
    def config() -> EimzoConfigDTO:
        return EimzoConfigDTO(
            bridge_url=settings.EIMZO_BRIDGE_URL,
            bridge_origin=settings.EIMZO_BRIDGE_ORIGIN,
            client_id=settings.EIMZO_CLIENT_ID,
            mock=settings.EIMZO_MOCK,
        )

    async def verify_code(self, code: str) -> EimzoCertificateDTO:
        """Меняет code моста на данные сертификата. Ошибка → вход/подпись прекращаются."""
        if settings.EIMZO_MOCK:
            return self._mock_certificate(code)

        if not settings.EIMZO_API_URL or not settings.EIMZO_CLIENT_ID:
            raise EimzoException("E-IMZO is not configured")

        response = await self._post_result(code, await self._get_token())
        if response.status_code == 401:
            # Токен отозван или истёк раньше срока — один повтор с новым токеном.
            type(self)._token = None
            response = await self._post_result(code, await self._get_token())
        return self._parse_result(response)

    # ---------- mock ----------

    @staticmethod
    def _mock_certificate(code: str) -> EimzoCertificateDTO:
        match = MOCK_CODE.match(code.strip())
        if match is None:
            raise EimzoInvalidCodeException("Mock E-IMZO code must look like mock-<PINFL>")
        pinfl = match.group(1)
        return EimzoCertificateDTO(
            pinfl=pinfl,
            full_name="MOCK E-IMZO",
            serial_number=f"mock{pinfl[-8:]}",
            valid_from="2026.01.01 00:00:00",
            valid_to="2028.01.01 23:59:59",
            request_id="mock",
        )

    # ---------- токен ----------

    async def _get_token(self) -> str:
        cls = type(self)
        if cls._token_lock is None:
            cls._token_lock = asyncio.Lock()
        async with cls._token_lock:
            if cls._token and time.monotonic() < cls._token_expires_at:
                return cls._token

            try:
                async with httpx.AsyncClient(timeout=settings.EIMZO_TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        f"{settings.EIMZO_API_URL}{TOKEN_PATH}",
                        json={
                            "grant_type": "client_credentials",
                            "client_id": settings.EIMZO_CLIENT_ID,
                            "client_secret": settings.EIMZO_CLIENT_SECRET,
                        },
                    )
            except httpx.HTTPError as exc:
                logger.warning("E-IMZO token request failed: %s", exc)
                raise EimzoException() from exc

            if response.status_code != 200:
                logger.error(
                    "E-IMZO token request rejected (%s): %s",
                    response.status_code,
                    response.text[:300],
                )
                raise EimzoException("E-IMZO client is not authorized")

            try:
                payload = response.json()
                token = payload["access_token"]
                expires_in = int(payload.get("expires_in") or 3600)
            except (ValueError, KeyError, TypeError):
                raise EimzoException("E-IMZO returned malformed token response") from None

            cls._token = token
            cls._token_expires_at = time.monotonic() + max(
                expires_in - TOKEN_REFRESH_MARGIN_SECONDS, 1
            )
            return token

    # ---------- результат подписи ----------

    @staticmethod
    async def _post_result(code: str, token: str) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=settings.EIMZO_TIMEOUT_SECONDS) as client:
                return await client.post(
                    f"{settings.EIMZO_API_URL}{RESULT_PATH}",
                    json={"code": code},
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            logger.warning("E-IMZO result request failed: %s", exc)
            raise EimzoException() from exc

    @staticmethod
    def _parse_result(response: httpx.Response) -> EimzoCertificateDTO:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        request_id = response.headers.get("X-Request-ID") or payload.get("request_id")

        if response.status_code != 200 or not payload.get("success"):
            error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
            error_code = error.get("code")
            if error_code in ("invalid_code", "invalid_request"):
                raise EimzoInvalidCodeException()
            logger.warning(
                "E-IMZO result failed: status=%s code=%s request_id=%s",
                response.status_code,
                error_code,
                request_id,
            )
            raise EimzoException()

        data = payload.get("data") or {}
        if not isinstance(data, dict) or not data.get("pinfl"):
            raise EimzoException("E-IMZO certificate has no PINFL")
        fields = {
            key: str(data[key]) if data.get(key) is not None else None
            for key in EimzoCertificateDTO.model_fields
            if key != "request_id"
        }
        try:
            return EimzoCertificateDTO(**fields, request_id=request_id)
        except ValueError:
            raise EimzoException("E-IMZO returned malformed certificate data") from None
