import logging

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from src.account.apis import user_api
from src.admin.admin import setup_admin
from src.application.apis import (
    application_api,
    bank_api,
    bank_stage_api,
    council_api,
    fund_api,
)
from src.auth.apis import auth_api
from src.common.logging_config import configure_logging
from src.common.responses.handlers import register_exception_handlers
from src.common.responses.validation_handler import validation_exception_handler
from src.config import settings
from src.rbac.apis import permission_api, role_api

DESCRIPTION = """
Backend платформы финансирования **Jamg'arma** (YTRJ-EP).

Модульный монолит на FastAPI. Текущие модули:

- **auth** — вход через OneID и по паролю, JWT access/refresh с ротацией, сессии;
- **rbac** — роли и права по модулям (Create / Read / Update / Delete / Approve), серверная проверка;
- **account** — пользователи, статусы, scope (банк), последний вход и сессии;
- **application** — заявки: черновик → скоринг KATM → банк → Совет → документ-требование → выделение ресурсов.

Все ответы имеют единый формат `{"success": bool, "message": str, "data": ...}`.
Авторизация: заголовок `Authorization: Bearer <access_token>`.
"""

TAGS_METADATA = [
    {
        "name": "Авторизация и аутентификация",
        "description": "OneID, логин/пароль, refresh, профиль.",
    },
    {
        "name": "Пользователи",
        "description": "Super Admin: профили, роли, scope, блокировка, сессии.",
    },
    {"name": "RBAC: роли", "description": "Каталог ролей и матрица разрешений."},
    {"name": "RBAC: права", "description": "Каталог прав платформы."},
    {"name": "Каталог банков", "description": "Банки-партнёры и правила выбора по типу субъекта."},
    {
        "name": "Заявки: кабинет заявителя",
        "description": "Создание, заполнение, отправка и отслеживание заявки.",
    },
    {
        "name": "Заявки: рабочее окно Фонда",
        "description": "Поиск, скоринг, направление в Совет, финансирование.",
    },
    {
        "name": "Заявки: рабочее окно банка",
        "description": "Приём и результат по заявкам своего банка.",
    },
    {"name": "Заявки: рабочее окно Совета", "description": "Решение по направленным заявкам."},
]

app = FastAPI(
    title=settings.APP_NAME,
    description=DESCRIPTION,
    version=settings.APP_VERSION,
    openapi_tags=TAGS_METADATA,
    docs_url=None,
    redoc_url=None,
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


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=settings.APP_NAME,
        dark_mode=True,
        hide_client_button=True,
    )


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


API_PREFIX = settings.API_PREFIX

app.include_router(auth_api.router, prefix=API_PREFIX)
app.include_router(user_api.router, prefix=API_PREFIX)
app.include_router(role_api.router, prefix=API_PREFIX)
app.include_router(permission_api.router, prefix=API_PREFIX)
app.include_router(bank_api.router, prefix=API_PREFIX)
app.include_router(application_api.router, prefix=API_PREFIX)
app.include_router(fund_api.router, prefix=API_PREFIX)
app.include_router(bank_stage_api.router, prefix=API_PREFIX)
app.include_router(council_api.router, prefix=API_PREFIX)

setup_admin(app)


if __name__ == "__main__":
    configure_logging(level=logging.INFO)
    logging.info("Starting server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
