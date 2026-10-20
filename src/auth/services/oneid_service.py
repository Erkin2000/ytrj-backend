"""Адаптер OneID (OAuth2 authorization code).

Единственное место обращения к OneID. Реальные URL/контракты уточняются
по документации OneID; при ONEID_MOCK=True внешние вызовы не выполняются.
"""

import logging
import secrets
from urllib.parse import urlencode

import httpx

from src.auth.schemas.auth_schema import OneIDAuthorizeDTO, OneIDProfileDTO
from src.common.responses.exceptions import OneIDException
from src.config import settings

logger = logging.getLogger(__name__)


class OneIDService:
    def build_authorize_url(self) -> OneIDAuthorizeDTO:
        state = secrets.token_urlsafe(24)
        params = {
            "response_type": "one_code",
            "client_id": settings.ONEID_CLIENT_ID,
            "redirect_uri": settings.ONEID_REDIRECT_URI,
            "scope": settings.ONEID_SCOPE,
            "state": state,
        }
        return OneIDAuthorizeDTO(
            authorize_url=f"{settings.ONEID_AUTHORIZE_URL}?{urlencode(params)}",
            state=state,
        )

    async def exchange_code(self, code: str) -> OneIDProfileDTO:
        """Обменивает code на access_token и получает профиль.
        Любая ошибка OneID → OneIDException (вход прекращается, можно повторить)."""
        if not settings.ONEID_CLIENT_ID:
            raise OneIDException("OneID is not configured")

        try:
            async with httpx.AsyncClient(timeout=settings.ONEID_TIMEOUT_SECONDS) as client:
                token_response = await client.post(
                    settings.ONEID_TOKEN_URL,
                    data={
                        "grant_type": "one_authorization_code",
                        "client_id": settings.ONEID_CLIENT_ID,
                        "client_secret": settings.ONEID_CLIENT_SECRET,
                        "code": code,
                        "redirect_uri": settings.ONEID_REDIRECT_URI,
                    },
                )
                token_response.raise_for_status()
                access_token = token_response.json().get("access_token")

                if not access_token:
                    raise OneIDException()

                info_response = await client.post(
                    settings.ONEID_USERINFO_URL,
                    data={
                        "grant_type": "one_access_token_identify",
                        "client_id": settings.ONEID_CLIENT_ID,
                        "client_secret": settings.ONEID_CLIENT_SECRET,
                        "access_token": access_token,
                        "scope": settings.ONEID_SCOPE,
                    },
                )
                info_response.raise_for_status()
                info = info_response.json()

        except httpx.HTTPError as exc:
            logger.warning("OneID request failed: %s", exc)
            raise OneIDException() from exc

        return self._map_profile(info)

    @staticmethod
    def _map_profile(info: dict) -> OneIDProfileDTO:
        """Поля OneID: pin (ПИНФЛ), full_name / sur_name + first_name + mid_name,
        mob_phone_no, pport_no, tin, email, user_id."""
        full_name = info.get("full_name") or " ".join(
            part
            for part in (info.get("sur_name"), info.get("first_name"), info.get("mid_name"))
            if part
        )
        pinfl = info.get("pin") or info.get("pinfl")

        if not pinfl or not full_name:
            raise OneIDException("OneID did not return required profile data")

        phone = info.get("mob_phone_no")
        if phone and not phone.startswith("+"):
            phone = f"+{phone}"

        try:
            return OneIDProfileDTO(
                sub=str(info.get("user_id") or pinfl),
                pinfl=pinfl,
                full_name=full_name,
                phone=phone,
                passport_number=info.get("pport_no"),
                inn=info.get("tin"),
                email=info.get("email"),
            )
        except ValueError:
            raise OneIDException("OneID returned malformed profile data") from None
