import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import OpenAPISource, get_scalar_api_reference

from src.account.apis import user_api
from src.admin.admin import setup_admin
from src.application.apis import (
    admin_application_api,
    application_api,
    bank_api,
    bank_stage_api,
    council_api,
    fund_api,
)
from src.auth.apis import auth_api, redirect_api, sso_web_api
from src.bulletin.apis import council_bulletin_api, fund_bulletin_api, verify_api
from src.bulletin.services.scheduler import bulletin_scheduler
from src.common.logging_config import configure_logging
from src.common.responses.handlers import register_exception_handlers
from src.common.responses.validation_handler import validation_exception_handler
from src.common.swagger.i18n import DESCRIPTION_UZ, translate_openapi
from src.common.swagger.openapi import restore_nulls
from src.config import settings
from src.product.apis import fund_category_api, fund_product_api, product_api
from src.rbac.apis import permission_api, role_api

DESCRIPTION = """
Backend платформы финансирования **Jamg'arma** (YTRJ-EP).

Модульный монолит на FastAPI. Текущие модули:

- **auth** — вход через YIA Portal (SSO), по паролю и ключом E-IMZO (члены Совета), JWT access/refresh с ротацией, сессии;
- **rbac** — роли и права по модулям (Create / Read / Update / Delete / Approve), серверная проверка;
- **account** — пользователи, статусы, scope (банк), последний вход и сессии;
- **product** — продукты Фонда: названия, банки, сроки приёма, этапы и поля анкеты;
- **application** — заявки по продуктам: черновик → скоринг KATM → Фонд → Совет → банк → завершение;
- **bulletin** — бюллетени Совета: отправка членам Совета, подпись ЭЦП (E-IMZO), проверка по QR.

Все ответы имеют единый формат `{"success": bool, "message": str, "data": ...}`.
Авторизация: заголовок `Authorization: Bearer <access_token>`.

Язык документации переключается в выпадающем списке слева вверху (Русский / Oʻzbek).
"""

TAGS_METADATA = [
    {
        "name": "Авторизация и аутентификация",
        "description": "YIA Portal SSO, E-IMZO (члены Совета), логин/пароль, refresh, профиль.",
    },
    {
        "name": "Пользователи",
        "description": "Super Admin: профили, роли, scope, блокировка, сессии.",
    },
    {"name": "RBAC: роли", "description": "Каталог ролей и матрица разрешений."},
    {"name": "RBAC: права", "description": "Каталог прав платформы."},
    {"name": "Каталог банков", "description": "Банки-партнёры и правила выбора по типу субъекта."},
    {
        "name": "Продукты: категории (Фонд)",
        "description": "Категории продуктов; продукт относится к одной категории.",
    },
    {
        "name": "Продукты: управление (Фонд)",
        "description": "Продукты, их банки, сроки приёма, этапы и поля анкеты; публикация.",
    },
    {
        "name": "Продукты: каталог заявителя",
        "description": "Опубликованные продукты, по которым сейчас принимаются заявки.",
    },
    {
        "name": "Заявки: кабинет заявителя",
        "description": "Заявка по продукту: ответы на поля этапов, файлы, отправка, отслеживание.",
    },
    {
        "name": "Заявки: рабочее окно Фонда",
        "description": "Поиск, скоринг, отказ или направление в Совет.",
    },
    {
        "name": "Заявки: рабочее окно Совета",
        "description": "Просмотр направленных заявок; решение — подписью бюллетеня.",
    },
    {
        "name": "Заявки: рабочее окно банка",
        "description": "Приём и результат по утверждённым Советом заявкам своего банка.",
    },
    {
        "name": "Заявки: Super Admin",
        "description": "Полное удаление заявки со всеми данными и файлами.",
    },
    {
        "name": "Бюллетени: рабочее окно Фонда",
        "description": "Создание, отправка членам Совета, статус подписания, QR-код, аннулирование.",
    },
    {
        "name": "Бюллетени: рабочее окно Совета",
        "description": "Мои бюллетени, календарь, просмотр и подпись ключом E-IMZO.",
    },
    {
        "name": "Бюллетени: проверка по QR",
        "description": "Публичная проверка документа по QR-коду.",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Фоновая отправка отложенных бюллетеней в дату отправки.
    async with bulletin_scheduler():
        yield


app = FastAPI(
    title=settings.APP_NAME,
    description=DESCRIPTION,
    version=settings.APP_VERSION,
    openapi_tags=TAGS_METADATA,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

register_exception_handlers(app)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


_generate_openapi = app.openapi


def openapi_with_nulls() -> dict:
    """app.openapi(): null-поля в примерах ответов не теряются (см. NULL_MARKER)."""
    if app.openapi_schema is None:
        restore_nulls(_generate_openapi())
    return app.openapi_schema


app.openapi = openapi_with_nulls

_openapi_uz_cache: dict | None = None


def openapi_uz() -> dict:
    """OpenAPI-схема на узбекском: русские строки заменяются по словарю
    src/common/swagger/i18n.py. Считается один раз, как и app.openapi()."""
    global _openapi_uz_cache
    if _openapi_uz_cache is None:
        _openapi_uz_cache = translate_openapi(app.openapi(), description=DESCRIPTION_UZ)
    return _openapi_uz_cache


@app.get("/openapi-uz.json", include_in_schema=False)
async def openapi_uz_json():
    return JSONResponse(openapi_uz())


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    # Два документа в одном Scalar: переключатель языка — в шапке сайдбара.
    return get_scalar_api_reference(
        title=settings.APP_NAME,
        sources=[
            OpenAPISource(title="Русский", slug="ru", url=app.openapi_url, default=True),
            OpenAPISource(title="Oʻzbek", slug="uz", url="/openapi-uz.json"),
        ],
        dark_mode=True,
        hide_client_button=True,
    )


@app.get("/docs/uz", include_in_schema=False)
async def scalar_html_uz():
    """Прямая ссылка на узбекскую версию документации."""
    return get_scalar_api_reference(
        title=settings.APP_NAME,
        sources=[
            OpenAPISource(title="Oʻzbek", slug="uz", url="/openapi-uz.json", default=True),
            OpenAPISource(title="Русский", slug="ru", url=app.openapi_url),
        ],
        dark_mode=True,
        hide_client_button=True,
    )


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


API_PREFIX = settings.API_PREFIX

app.include_router(auth_api.router, prefix=API_PREFIX)
app.include_router(redirect_api.router, prefix=API_PREFIX)
app.include_router(user_api.router, prefix=API_PREFIX)
app.include_router(role_api.router, prefix=API_PREFIX)
app.include_router(permission_api.router, prefix=API_PREFIX)
app.include_router(bank_api.router, prefix=API_PREFIX)
app.include_router(fund_category_api.router, prefix=API_PREFIX)
app.include_router(fund_product_api.router, prefix=API_PREFIX)
app.include_router(product_api.router, prefix=API_PREFIX)
app.include_router(application_api.router, prefix=API_PREFIX)
app.include_router(fund_api.router, prefix=API_PREFIX)
app.include_router(council_api.router, prefix=API_PREFIX)
app.include_router(admin_application_api.router, prefix=API_PREFIX)
app.include_router(bank_stage_api.router, prefix=API_PREFIX)
app.include_router(fund_bulletin_api.router, prefix=API_PREFIX)
app.include_router(council_bulletin_api.router, prefix=API_PREFIX)
app.include_router(verify_api.api_router, prefix=API_PREFIX)

# Веб-страницы входа через YIA Portal (вне /api/v1, без OpenAPI)
app.include_router(sso_web_api.router)
# Страница проверки бюллетеня по QR (вне /api/v1, без OpenAPI)
app.include_router(verify_api.web_router)

setup_admin(app)


if __name__ == "__main__":
    configure_logging(level=logging.INFO)
    logging.info("Starting server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
