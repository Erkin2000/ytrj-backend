"""Точка возврата с YIA Portal.

На портале зарегистрирован redirect_uri = <host>/api/v1/redirect/from-backend
(SSO_REDIRECT_URI, для админки — SSO_REDIRECT_URI_ADMIN). Бэкенд ничего здесь не
обменивает: он только пересылает браузер на SSO_FRONTEND_REDIRECT_URL (или
SSO_FRONTEND_REDIRECT_URL_ADMIN для админки), сохраняя query-параметры портала
(code, state, error), а дальше страница сама вызывает POST /auth/sso/callback.
Сайт задаётся параметром ?site=, без него — берётся из подписанного state.
Адрес назначения берётся только из настроек, поэтому открытого редиректа нет.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from src.auth.schemas.auth_schema import SSOSite
from src.auth.services.sso_service import YiaSSOService
from src.common.urls import append_query
from src.config import settings

router = APIRouter(prefix="/redirect", tags=["Auth"])

SITE_PARAM_DESCRIPTION = (
    "Фронт, на который вернуть браузер: `yoshlarfondi` — `SSO_FRONTEND_REDIRECT_URL`, "
    "`admin` — `SSO_FRONTEND_REDIRECT_URL_ADMIN`. Без параметра сайт берётся из "
    "подписанного `state` (тот, что передан в `GET /auth/sso/authorize?site=`). "
    "Сам `site` на фронт не пересылается."
)


@router.get(
    "/from-backend",
    summary="Возврат с YIA Portal → редирект на фронтенд",
    description=(
        "Адрес, зарегистрированный на портале как `SSO_REDIRECT_URI` (и "
        "`SSO_REDIRECT_URI_ADMIN` для админки). Отвечает `302` на "
        "`SSO_FRONTEND_REDIRECT_URL` — или на `SSO_FRONTEND_REDIRECT_URL_ADMIN`, если вход "
        "начат с `site=admin` (сайт берётся из подписанного `state`), — передавая все "
        "query-параметры портала (`code`, `state`, `error`) без изменений. Код обменивает "
        "фронтенд через `POST /auth/sso/callback` (code живёт 60 секунд)."
    ),
    status_code=302,
    response_class=RedirectResponse,
    responses={302: {"description": "Редирект на SSO_FRONTEND_REDIRECT_URL с query портала"}},
)
async def redirect_from_backend(
    request: Request,
    site: Annotated[SSOSite | None, Query(description=SITE_PARAM_DESCRIPTION)] = None,
) -> RedirectResponse:
    # На фронт — только параметры портала (code, state, error), без нашего site.
    params = [(k, v) for k, v in request.query_params.multi_items() if k != "site"]
    site = site or YiaSSOService().site_of(request.query_params.get("state"))
    target = (
        settings.SSO_FRONTEND_REDIRECT_URL_ADMIN
        if site == SSOSite.ADMIN
        else settings.SSO_FRONTEND_REDIRECT_URL
    )
    url = append_query(target, params)
    # В URL одноразовый code: не кэшируем ответ и не отдаём его в Referer.
    return RedirectResponse(
        url,
        status_code=302,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
