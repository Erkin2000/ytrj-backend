"""Точка возврата с YIA Portal.

На портале зарегистрирован redirect_uri = <host>/api/v1/redirect/from-backend
(SSO_REDIRECT_URI). Бэкенд ничего здесь не обменивает: он только пересылает
браузер на SSO_FRONTEND_REDIRECT_URL, сохраняя query-параметры портала
(code, state, error), а дальше страница сама вызывает POST /auth/sso/callback.
Адрес назначения берётся только из настроек, поэтому открытого редиректа нет.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from src.config import settings

router = APIRouter(prefix="/redirect", tags=["Auth"])


def build_redirect_url(target: str, params: list[tuple[str, str]]) -> str:
    """Добавляет params к target, сохраняя его собственные query-параметры и fragment."""
    parts = urlsplit(target)
    query = parse_qsl(parts.query, keep_blank_values=True) + params
    return urlunsplit(parts._replace(query=urlencode(query)))


@router.get(
    "/from-backend",
    summary="Возврат с YIA Portal → редирект на фронтенд",
    description=(
        "Адрес, зарегистрированный на портале как `SSO_REDIRECT_URI`. Отвечает `302` на "
        "`SSO_FRONTEND_REDIRECT_URL`, передавая все query-параметры портала "
        "(`code`, `state`, `error`) без изменений. Код обменивает фронтенд через "
        "`POST /auth/sso/callback` (code живёт 60 секунд)."
    ),
    status_code=302,
    response_class=RedirectResponse,
    responses={302: {"description": "Редирект на SSO_FRONTEND_REDIRECT_URL с query портала"}},
)
async def redirect_from_backend(request: Request) -> RedirectResponse:
    params = list(request.query_params.multi_items())
    url = build_redirect_url(settings.SSO_FRONTEND_REDIRECT_URL, params)
    return RedirectResponse(url, status_code=302)
