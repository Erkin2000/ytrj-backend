"""Минимальный веб-фронт для входа через YIA Portal.

Нужен, пока нет отдельного фронтенда: страница входа и страница, на которую
портал возвращает пользователя (redirect_uri = <host>/api/auth/one-id/callback).
Страницы работают через публичное API (/api/v1/auth/sso/*) так же, как это
делал бы SPA, поэтому в схему OpenAPI не попадают.
"""

from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

router = APIRouter(prefix="/api/auth/one-id", include_in_schema=False)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

LOGIN_PATH = f"{router.prefix}/login"
CALLBACK_PATH = f"{router.prefix}/callback"


def _context(request: Request) -> dict:
    return {
        "request": request,
        "app_name": settings.APP_NAME,
        "api_prefix": settings.API_PREFIX,
        "sso_mock": settings.SSO_MOCK,
        "login_url": LOGIN_PATH,
    }


@router.get("/login")
async def sso_login_page(request: Request):
    return templates.TemplateResponse(request, "sso_login.html", _context(request))


# Параметры, которые портал присылает на redirect_uri и которые нужны фронтенду.
_CALLBACK_PARAMS = ("code", "state", "error", "error_description")


def frontend_callback_url(query: dict[str, str]) -> str | None:
    """Адрес страницы входа фронтенда с параметрами возврата портала.
    None, если SSO_FRONTEND_REDIRECT_URL не задан (работает встроенная страница)."""
    base = settings.SSO_FRONTEND_REDIRECT_URL.strip()
    if not base:
        return None

    passthrough = {k: query[k] for k in _CALLBACK_PARAMS if query.get(k)}
    scheme, netloc, path, existing_query, fragment = urlsplit(base)
    merged_query = "&".join(part for part in (existing_query, urlencode(passthrough)) if part)
    return urlunsplit((scheme, netloc, path, merged_query, fragment))


@router.get("/callback")
async def sso_callback_page(request: Request):
    # Сервер здесь ничего не обменивает: code одноразовый и живёт 60 секунд,
    # поэтому сразу передаём code/state/error на страницу входа фронтенда,
    # а тот вызывает POST /api/v1/auth/sso/callback.
    target = frontend_callback_url(dict(request.query_params))
    if target:
        return RedirectResponse(target, status_code=302)

    # Без фронтенда — встроенная страница делает то же самое скриптом.
    return templates.TemplateResponse(request, "sso_callback.html", _context(request))
