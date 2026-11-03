"""Вход через YIA Portal целиком на бэкенде (переходы браузера, не XHR).

1. Кнопка «Войти» ведёт браузер на GET /auth/sso/login: бэкенд ставит HttpOnly
   cookie с nonce, подписывает его в state и отправляет браузер на портал.
2. Портал возвращает браузер на SSO_REDIRECT_URI = GET /redirect/from-backend
   с code/state (или error). Бэкенд сверяет state с cookie этого же браузера,
   меняет code на профиль, по sub/ПИНФЛ определяет пользователя и отвечает 302
   на кабинет его роли (ROLE_HOME_URLS) с одноразовым ?ticket=...
3. Любая ошибка — 302 на SSO_FRONTEND_REDIRECT_URL?error=<code>.

Оба адреса должны быть на одном хосте (cookie ставится на путь /redirect).
Адреса назначения берутся только из настроек — открытого редиректа нет.
"""

import logging
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from src.auth.services.auth_service import AuthService
from src.common.dependencies import DBDep
from src.common.responses.exceptions import ApiException
from src.common.urls import append_query
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Авторизация и аутентификация"])

NONCE_COOKIE = "yia_sso_nonce"
# В URL code/ticket: не кэшируем ответ и не отдаём адрес в Referer.
NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


def _cookie_path() -> str:
    return f"{settings.API_PREFIX}/redirect"


def _cookie_secure() -> bool:
    # Cookie должна вернуться на SSO_REDIRECT_URI: по https — только Secure.
    return settings.SSO_REDIRECT_URI.lower().startswith("https://")


@router.get(
    "/auth/sso/login",
    summary="YIA SSO: начать вход (переход браузера на портал)",
    description=(
        "Открывается **переходом браузера** (`location.href`), не через fetch. Ставит "
        "HttpOnly cookie, привязывающую `state` к этому браузеру, и отвечает `302` на "
        "страницу входа портала. После входа портал вернёт браузер на "
        "`GET /redirect/from-backend`, а тот — в кабинет роли пользователя с `?ticket=`."
    ),
    status_code=302,
    response_class=RedirectResponse,
    responses={302: {"description": "Редирект на страницу входа YIA Portal"}},
)
async def sso_login(db: DBDep) -> RedirectResponse:
    nonce = secrets.token_urlsafe(24)
    authorize_url = AuthService(db).sso_authorize_url(nonce)
    response = RedirectResponse(authorize_url, status_code=302, headers=NO_STORE)
    response.set_cookie(
        NONCE_COOKIE,
        nonce,
        max_age=settings.SSO_STATE_TTL_SECONDS,
        path=_cookie_path(),
        httponly=True,
        secure=_cookie_secure(),
        # Lax: cookie уходит при возврате браузера с портала (top-level GET).
        samesite="lax",
    )
    return response


@router.get(
    "/redirect/from-backend",
    summary="Возврат с YIA Portal: обмен code на бэкенде → кабинет роли",
    description=(
        "Адрес, зарегистрированный на портале как `SSO_REDIRECT_URI`. Сверяет `state` с "
        "cookie браузера, меняет `code` (живёт 60 секунд) на профиль, находит "
        "пользователя по `sub`/ПИНФЛ (заявитель создаётся при первом входе) и отвечает "
        "`302` на `ROLE_HOME_URLS[роль]?ticket=...`. Кабинет меняет билет на токены через "
        "`POST /auth/ticket/exchange`. При ошибке — `302` на "
        "`SSO_FRONTEND_REDIRECT_URL?error=<code>` (`sso_invalid_state`, "
        "`sso_access_denied`, `sso_failed`, `user_blocked`, `server_error`)."
    ),
    status_code=302,
    response_class=RedirectResponse,
    responses={302: {"description": "Кабинет роли с ?ticket=... или страница входа с ?error=..."}},
)
async def redirect_from_backend(request: Request, db: DBDep) -> RedirectResponse:
    query = request.query_params
    try:
        url = await AuthService(db).sso_browser_callback(
            code=query.get("code"),
            state=query.get("state"),
            error=query.get("error"),
            nonce=request.cookies.get(NONCE_COOKIE),
        )
    except ApiException as exc:
        url = append_query(settings.SSO_FRONTEND_REDIRECT_URL, [("error", exc.code)])
    except Exception:
        logger.exception("YIA SSO browser callback failed")
        url = append_query(settings.SSO_FRONTEND_REDIRECT_URL, [("error", "server_error")])

    response = RedirectResponse(url, status_code=302, headers=NO_STORE)
    # nonce одноразовый: после возврата с портала он больше не нужен.
    response.delete_cookie(
        NONCE_COOKIE,
        path=_cookie_path(),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )
    return response
