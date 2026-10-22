"""Минимальный веб-фронт для входа через YIA Portal.

Нужен, пока нет отдельного фронтенда: страница входа и страница, на которую
портал возвращает пользователя (redirect_uri = <host>/api/auth/one-id/callback).
Страницы работают через публичное API (/api/v1/auth/sso/*) так же, как это
делал бы SPA, поэтому в схему OpenAPI не попадают.
"""

from pathlib import Path

from fastapi import APIRouter, Request
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


@router.get("/callback")
async def sso_callback_page(request: Request):
    # code/state/error читает скрипт страницы из query и отправляет в
    # POST /api/v1/auth/sso/callback — сервер здесь ничего не обменивает.
    return templates.TemplateResponse(request, "sso_callback.html", _context(request))
