# Jamg'arma Platform API (YTRJ-EP)

Backend платформы финансирования: модульный монолит на **FastAPI + SQLAlchemy 2 (async) + PostgreSQL 17**.
Документация API — Scalar (`/docs`), админ-панель — SQLAdmin (`/admin`).

## Модули (первая очередь)

| Модуль        | Что делает |
|---------------|-----------|
| `auth`        | Вход заявителей через SSO YIA Portal (e-yoshlar.uz, OneID на стороне портала; пока mock), вход по паролю для внутренних пользователей, JWT access/refresh с ротацией, `/auth/me`, смена пароля, сессии |
| `rbac`        | Каталог прав `<модуль>.<create\|read\|update\|delete\|approve>`, роли, матрица прав, системные роли |
| `account`     | Пользователи: поиск/фильтры, назначение роли и scope (банк), блокировка, последний вход, сессии, CLI суперпользователя |
| `application` | Заявки: черновик → отправка → скоринг KATM → требования Фонда → банк → Фонд → Совет → документ-требование → выделение ресурсов → завершение. История статусов, индикатор прогресса, фото (≤4), место деятельности, каталог банков |

Следующие очереди (по архитектуре): `bulletins`, `council` (ЭЦП/QR), `notifications`, `audit`, `documents` (PDF), `integrations` (KATM/E-IMZO), фоновые задачи (outbox → Celery).

## Структура

```
src/
  main.py                 # FastAPI app, Scalar docs, роутеры, админка
  config.py               # pydantic-settings (.env)
  database.py             # engine, session maker, Base, TimestampMixin
  models.py               # единая точка импорта всех ORM-моделей
  common/                 # dependencies (DBDep, CurrentUserDep, require_permission), ответы, исключения, swagger-примеры
  utils/                  # BaseRepository, DataMapper, BaseService, DBManager (unit of work)
  <module>/
    apis/                 # роутеры
    models/               # ORM
    repositories/         # доступ к данным
    schemas/              # Pydantic DTO
    services/             # бизнес-логика
    mappers.py            # ORM -> DTO
  application/workflow.py # state machine статусов + шаги индикатора прогресса
  admin/                  # SQLAdmin: дашборд, ModelView-ы, шаблоны
  alembic/                # миграции (async env)
```

Правила слоёв: API → Service → Repository. Сервис получает `DBManager` (одна сессия на запрос), сам делает `commit()`.
Проверка прав и принадлежности объекта (scope) выполняется **только на backend**: `require_permission(...)` на роутере + проверка scope в сервисе (`ApplicationBaseService.assert_can_view`).

## Запуск

```bash
uv sync                                   # зависимости (Python 3.13+)
cp .env.example .env                      # и заполнить DB_*, JWT_SECRET_KEY, ADMIN_SESSION_SECRET
createdb ytrj_db                          # или через pgAdmin
uv run alembic upgrade head               # схема + сид: права, 5 системных ролей, 9 банков
ADMIN_PASSWORD=admin12345 uv run python -m src.account.cli create-superuser
uv run uvicorn src.main:app --reload
```

- Scalar docs: http://127.0.0.1:8000/docs
  Документация двуязычная: переключатель «Русский / Oʻzbek» в шапке сайдбара, прямая ссылка на узбекскую версию — `/docs/uz`, схема — `/openapi-uz.json`. Русские строки в коде (summary, description, теги, описания полей) — источник; узбекские переводы в `src/common/swagger/i18n.py` (`UZ`). Добавили ручку — добавьте перевод; непереведённые строки покажет `untranslated(openapi_uz())`.
- Админ-панель: http://127.0.0.1:8000/admin (логин/пароль суперпользователя)
  Интерфейс на русском и узбекском (переключатель в верхней панели, `?lang=uz`, выбор сохраняется в cookie).
- Health: http://127.0.0.1:8000/health

## Запуск в Docker

```bash
docker compose up -d --build
```

Поднимаются два контейнера: `ytrj_db` (PostgreSQL 17) и `ytrj_api`. При старте `api` entrypoint
(`docker/entrypoint.sh`) ждёт БД, выполняет `alembic upgrade head` и создаёт суперпользователя
**`admin` / `admin12345`** (переменные `SUPERUSER` / `ADMIN_PASSWORD`, шаг идемпотентный — существующий
пользователь не трогается). Затем стартует uvicorn.

- API / Scalar docs: http://localhost:8888/docs
- Админ-панель: http://localhost:8888/admin — `admin` / `admin12345`
- PostgreSQL с хоста: `localhost:5555` (`DB_PORT_HOST`), чтобы не конфликтовать с локальным Postgres

Значения берутся из `.env` в корне (если есть), иначе из дефолтов в `docker-compose.yml`.
`DB_HOST` внутри compose всегда `db`. Медиа-файлы — в volume `media_data`, данные БД — в `pg_data`.

```bash
docker compose logs -f api        # логи
docker compose down               # остановить (данные сохраняются)
docker compose down -v            # остановить и удалить volumes
```

Для продакшена обязательно задать в `.env`: `ADMIN_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_SESSION_SECRET`, `DB_PASS`,
`DEBUG_ERRORS=false`, `SSO_MOCK=false`, `SSO_CLIENT_ID` / `SSO_CLIENT_SECRET` / `SSO_REDIRECT_URI` (выдаёт YIA Portal).

## Админ-панель

SQLAdmin на Tabler UI, вход только для роли с `is_superuser`. Что есть сверх стандартного CRUD:

- **Дашборд** (`/admin`): заявки всего и новые за сегодня / 7 дней, в работе, завершено / отклонено, активные пользователи; воронка по статусам (каждый статус — ссылка на отфильтрованный список); «требуют внимания»; последние входы и изменения заявок.
- **Карточка заявки**: шапка со статусом и индикатором прогресса (те же шаги, что в API), таймлайн истории статусов, попытки скоринга, галерея фотографий, место деятельности (ссылка на карту), решения Совета, документ-требование и выделение ресурсов; полная таблица полей свёрнута в «Все поля».
- **Фото заявок** отдаются под cookie-сессией админки: `/admin/application-photo/{id}` (в меню не показывается).
- **Локализация ru/uz**: системные строки SQLAdmin и все наши подписи переводятся через Babel. Узбекский каталог — `src/admin/translations/uz/LC_MESSAGES/admin.po` (компилируется при старте, `.mo` не хранится). Русские строки в коде являются msgid: добавляя подпись, добавьте её перевод в `.po`. Подписи колонок переводятся на лету (`LocalizedLabelsMixin`), имена моделей и фильтров — через `_l()`.
- Время показывается в часовом поясе Ташкента (UTC+5), суммы — с разделителями разрядов.
- **Оформление**: собственный сайдбар (группы разделов, перенос длинных названий, футер с текущим пользователем и версией), верхняя панель с окружением, переключателями темы (светлая/тёмная, запоминается в браузере) и языка, заголовки страниц с хлебными крошками, favicon.

## Роли и scope

| Роль (`code`)     | Scope |
|-------------------|-------|
| `SUPER_ADMIN`     | всё (is_superuser), управление пользователями/RBAC/справочниками, админ-панель |
| `FUND_OPERATOR`   | все заявки, скоринг, направление в Совет, выделение ресурсов |
| `BANK_EMPLOYEE`   | только заявки своего банка (`users.bank_id`), начиная со статуса SENT_TO_BANK |
| `COUNCIL_MEMBER`  | только заявки, направленные ему |
| `APPLICANT`       | только свой профиль и свои заявки |

Права по умолчанию для ролей — `src/rbac/permissions.py` (`ROLE_PRESETS`); новые права добавляются туда и в миграцию.

## Политика входа

- **Заявители** входят только через SSO YIA Portal (`sso_integration.md`). Профиль создаётся автоматически с ролью `APPLICANT`; пароль у заявителя отсутствует, `/auth/login` и смена пароля для него закрыты.
- **Внутренние роли** (Super Admin, Фонд, банк, Совет) входят по логину и паролю (`/auth/login`). Их создаёт Super Admin через `/users` или админ-панель; вход через SSO для них запрещён, даже если ПИНФЛ совпадает.
- Роль `APPLICANT` нельзя назначить вручную через API.

### Профиль заявителя

Портал гарантирует только `full_name` и `pinfl` — они обновляются при каждом входе и пользователем не редактируются.
Телефон, паспорт, ИНН, email, пол и дату рождения заявитель дополняет сам: `PATCH /api/v1/auth/me`
(любое подмножество полей, `null` очищает; `full_name` / `pinfl` в теле запроса → 422).
`GET /auth/me` отдаёт `profile_complete` и `missing_fields`. Пока профиль не заполнен, `POST /applications`
отвечает 400 со списком полей в `errors`; при отправке черновика недостающие поля профиля попадают в сводку
как `applicant.<field>`. Снимок данных заявителя в заявке обновляется из профиля в момент отправки.
Список обязательных полей — `src/account/profile.py`.

### Вход через YIA Portal (SSO)

1. Фронтенд вызывает `GET /api/v1/auth/sso/authorize`, сохраняет `state` (например, в sessionStorage) и перенаправляет браузер на `authorize_url`. Пользователь проходит OneID на стороне портала.
2. Портал возвращает браузер на `SSO_REDIRECT_URI` (в точности как зарегистрировано на портале, например `https://yoshlarfondi.uz/api/auth/one-id/callback`) с `?code=...&state=...` либо `?error=access_denied&state=...`.
3. Бэкенд на этом адресе ничего не обменивает, а сразу отвечает `302` на страницу входа фронтенда `SSO_FRONTEND_REDIRECT_URL` (по умолчанию `http://localhost:5173/login`), пробрасывая `code`, `state`, `error`, `error_description` в query.
4. Фронтенд сразу (code живёт 60 секунд) сверяет `state` с сохранённым, отправляет `POST /api/v1/auth/sso/callback` с `{code, state, error}` и получает пару JWT.

Встроенные страницы (вне OpenAPI, `src/auth/apis/sso_web_api.py`): `GET /api/auth/one-id/login` — кнопка входа через портал и, при `SSO_MOCK=true`, форма тестового входа; `GET /api/auth/one-id/callback` — точка возврата с портала. Если `SSO_FRONTEND_REDIRECT_URL` пуст, вместо редиректа она показывает встроенную страницу, которая сама вызывает `POST /auth/sso/callback` и кладёт токены в `localStorage`.

Бэкенд проверяет подпись и срок `state` (`SSO_STATE_TTL_SECONDS`), меняет `code` на профиль через `POST {SSO_BASE_URL}/api/v1/users/auth/sso/token/` с `client_secret` (только backend) и находит пользователя по `sub` портала (`users.sso_sub`), затем по ПИНФЛ; если не найден — создаёт заявителя (`username` = ПИНФЛ, при его отсутствии `sso_<sub>`). ПИНФЛ запрашивается у портала как опциональное поле при онбординге; `region/city/makhalla/role` приходят только у ётакчи и сейчас сохраняется только название региона.

Ошибки: неверный/просроченный `state` → 400; `access_denied` → 403; `invalid_grant` (code просрочен или использован), `invalid_client` (неверные креды или IP бэкенда не в allow-list портала), сетевые ошибки → 401, вход можно повторить.

## Режимы, пока нет интеграций

- `SSO_MOCK=true` — вместо YIA Portal доступен `POST /api/v1/auth/sso/mock-login` (ПИНФЛ + ФИО, опционально `sub`).
- `SCORING_MODE` — `auto_pass` | `auto_fail` | `technical_error` | `manual`. Техническая ошибка не отклоняет заявку: ставится флаг `scoring_retry_required`, Фонд делает `POST /fund/applications/{id}/scoring/retry`. В режиме `manual` результат вносится `POST /fund/applications/{id}/scoring/result`.

## Статусы заявки

`DRAFT → SUBMITTED → SCORING_IN_PROGRESS → (SCORING_FAILED | ELIGIBILITY_FAILED | READY_FOR_BANK) → SENT_TO_BANK → BANK_REVIEW → (BANK_APPROVED | BANK_REJECTED) → COUNCIL_REVIEW → (COUNCIL_APPROVED | COUNCIL_REJECTED) → DEMAND_DOCUMENT_CREATED → RESOURCE_ALLOCATION → COMPLETED`

Допустимые переходы — `src/application/workflow.py`. Каждый переход пишется в `application_status_history` (кто, когда, событие, комментарий).

## Принятые допущения (уточнить с заказчиком)

- Итог Совета: «Отклоняю» любого назначенного члена → `COUNCIL_REJECTED`; «Согласен» всех назначенных → `COUNCIL_APPROVED` (кворум/большинство не согласованы).
- Требования Фонда (eligibility) помимо KATM не заданы — пока все проходят (`EligibilityChecker`).
- Список из 9 банков содержит 3 обязательных (Microcreditbank, Xalq banki, Agrobank) и 6 предположительных — заменить на официальный список.
- YIA Portal гарантирует только `sub` и `full_name`; телефон, паспорт, ИНН, email, пол и дату рождения заявитель вводит сам в профиле (`PATCH /auth/me`) — без них заявка не создаётся. Если портал начнёт передавать эти поля, их нужно перенести в `SSO_MANAGED_FIELDS`.
- Файл документа «Требование подтверждено» формирует будущий модуль `documents`; сейчас создаётся запись с номером `TD-ГГГГ-NNNNNN`.
- Фото хранятся на диске (`MEDIA_PATH`); переход на закрытый S3 — в модуле `documents`.

## Разработка

```bash
uv run ruff check src && uv run ruff format src
uv run alembic revision --autogenerate -m "..."
```
