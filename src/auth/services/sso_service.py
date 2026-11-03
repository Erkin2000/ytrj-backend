"""Адаптер SSO YIA Portal (e-yoshlar.uz).

Единственное место обращения к YIA Portal. Пользователь проходит OneID на
стороне портала, платформа получает одноразовый code и обменивает его на
профиль backend-to-backend (см. sso_integration.md).

При SSO_MOCK=True внешние вызовы не выполняются.
"""

import logging
import secrets
from urllib.parse import urlencode

import httpx
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.auth.schemas.auth_schema import SSOAuthorizeDTO, SSOProfileDTO, SSOSite
from src.common.responses.exceptions import (
    SSOAccessDeniedException,
    SSOException,
    SSOInvalidStateException,
)
from src.config import settings

logger = logging.getLogger(__name__)

AUTHORIZE_PATH = "/api/v1/users/auth/sso/authorize/"
TOKEN_PATH = "/api/v1/users/auth/sso/token/"


class YiaSSOService:
    # state подписывается секретом сервера: в callback принимаем только
    # state, выданный нами и не старше SSO_STATE_TTL_SECONDS.
    _state_serializer = URLSafeTimedSerializer(settings.JWT_SECRET_KEY, salt="yia-sso-state")

    # ---------- шаг 1: ссылка на страницу входа ----------

    @staticmethod
    def client(site: SSOSite) -> tuple[str, str, str]:
        """(client_id, client_secret, redirect_uri) клиента портала для сайта входа."""
        if site == SSOSite.ADMIN:
            return (
                settings.SSO_CLIENT_ID_ADMIN or settings.SSO_CLIENT_ID,
                settings.SSO_CLIENT_SECRET_ADMIN or settings.SSO_CLIENT_SECRET,
                settings.SSO_REDIRECT_URI_ADMIN,
            )
        return settings.SSO_CLIENT_ID, settings.SSO_CLIENT_SECRET, settings.SSO_REDIRECT_URI

    def build_authorize_url(self, site: SSOSite = SSOSite.MAIN) -> SSOAuthorizeDTO:
        client_id, _, redirect_uri = self.client(site)
        if not redirect_uri:
            raise SSOException(f"YIA SSO is not configured for site '{site}'")
        # Сайт подписан в state: callback меняет code тем же клиентом портала,
        # а /redirect/from-backend возвращает браузер на фронт этого сайта.
        state = self._state_serializer.dumps({"n": secrets.token_urlsafe(16), "site": site.value})
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return SSOAuthorizeDTO(
            authorize_url=f"{settings.SSO_BASE_URL}{AUTHORIZE_PATH}?{urlencode(params)}",
            state=state,
        )

    # ---------- шаг 2: проверка ответа портала ----------

    def verify_state(self, state: str | None) -> SSOSite:
        """Проверяет подпись и срок state; возвращает сайт, с которого начат вход."""
        if not state:
            raise SSOInvalidStateException()
        try:
            payload = self._state_serializer.loads(state, max_age=settings.SSO_STATE_TTL_SECONDS)
        except SignatureExpired:
            raise SSOInvalidStateException("SSO state expired, start sign-in again") from None
        except BadSignature:
            raise SSOInvalidStateException() from None
        try:
            return SSOSite(payload["site"])
        except (TypeError, KeyError, ValueError):
            raise SSOInvalidStateException() from None

    def site_of(self, state: str | None) -> SSOSite:
        """Сайт из state без исключений: для выбора фронта в /redirect/from-backend.
        Неверный или просроченный state — основной сайт (ошибку покажет callback)."""
        try:
            return self.verify_state(state)
        except SSOInvalidStateException:
            return SSOSite.MAIN

    @staticmethod
    def check_callback_error(error: str | None) -> None:
        if not error:
            return
        if error == "access_denied":
            raise SSOAccessDeniedException()
        logger.warning("YIA SSO callback returned error=%s", error)
        raise SSOException(f"YIA Portal returned error: {error}")

    # ---------- шаг 3: обмен code на профиль ----------

    async def exchange_code(self, code: str, site: SSOSite = SSOSite.MAIN) -> SSOProfileDTO:
        """POST /sso/token/ → {sub, full_name, pinfl?, region?, city?, makhalla?, role?}.
        code меняется тем же клиентом портала, что выдал ссылку входа (site из state).
        Любая ошибка портала → SSOException (вход прекращается, можно повторить)."""
        client_id, client_secret, _ = self.client(site)
        if not client_id or not client_secret:
            raise SSOException("YIA SSO is not configured")

        try:
            async with httpx.AsyncClient(timeout=settings.SSO_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{settings.SSO_BASE_URL}{TOKEN_PATH}",
                    json={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": code,
                    },
                )
        except httpx.HTTPError as exc:
            logger.warning("YIA SSO token request failed: %s", exc)
            raise SSOException() from exc

        if response.status_code == 400:
            # invalid_grant: code неверный, просрочен (60 c) или уже использован.
            raise SSOException("SSO code is invalid or expired, start sign-in again")
        if response.status_code == 401:
            # invalid_client: неверные client_id/secret или IP сервера не в allow-list.
            logger.error("YIA SSO rejected client credentials: %s", response.text[:300])
            raise SSOException("YIA SSO client is not authorized")
        if response.status_code != 200:
            logger.warning(
                "YIA SSO unexpected status %s: %s", response.status_code, response.text[:300]
            )
            raise SSOException()

        try:
            info = response.json()
        except ValueError:
            raise SSOException("YIA Portal returned malformed response") from None

        return self._map_profile(info)

    @staticmethod
    def _map_profile(info: dict) -> SSOProfileDTO:
        sub = info.get("sub")
        full_name = (info.get("full_name") or "").strip()
        if not sub or not full_name:
            raise SSOException("YIA Portal did not return required profile data")

        def _name(obj: object) -> str | None:
            return obj.get("name") if isinstance(obj, dict) else None

        try:
            return SSOProfileDTO(
                sub=str(sub),
                full_name=full_name,
                pinfl=info.get("pinfl") or None,
                region=_name(info.get("region")),
                city=_name(info.get("city")),
                makhalla=_name(info.get("makhalla")),
                yia_role=_name(info.get("role")),
            )
        except ValueError:
            raise SSOException("YIA Portal returned malformed profile data") from None
