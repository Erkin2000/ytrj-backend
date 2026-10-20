# Jamg'arma Platform API (YTRJ-EP)

Backend платформы финансирования: модульный монолит на **FastAPI + SQLAlchemy 2 (async) + PostgreSQL 17**.
Документация API — Scalar (`/docs`), админ-панель — SQLAdmin (`/admin`).

## Модули (первая очередь)

| Модуль        | Что делает |
|---------------|-----------|
| `auth`        | Вход через OneID (OAuth2, пока mock), вход по паролю для внутренних пользователей, JWT access/refresh с ротацией, `/auth/me`, смена пароля, сессии |
| `rbac`        | Каталог прав `<модуль>.<create\|read\|update\|delete\|approve>`, роли, матрица прав, системные роли |
| `account`     | Пользователи: поиск/фильтры, назначение роли и scope (банк), блокировка, последний вход, сессии, CLI суперпользователя |
| `application` | Заявки: черновик → отправка → скоринг KATM → требования Фонда → банк → Фонд → Совет → документ-требование → выделение ресурсов → завершение. История статусов, индикатор прогресса, фото (≤4), место деятельности, каталог банков |

Следующие очереди (по архитектуре): `bulletins`, `council` (ЭЦП/QR), `notifications`, `audit`, `documents` (PDF), `integrations` (OneID/KATM/E-IMZO), фоновые задачи (outbox → Celery).

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
- Админ-панель: http://127.0.0.1:8000/admin (логин/пароль суперпользователя)
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
`DEBUG_ERRORS=false`, `ONEID_MOCK=false`.

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

- **Заявители** входят только через OneID (`/auth/oneid/authorize` → `/auth/oneid/callback`). Профиль создаётся автоматически с ролью `APPLICANT`; пароль у заявителя отсутствует, `/auth/login` и смена пароля для него закрыты.
- **Внутренние роли** (Super Admin, Фонд, банк, Совет) входят по логину и паролю (`/auth/login`). Их создаёт Super Admin через `/users` или админ-панель; вход через OneID для них запрещён, даже если ПИНФЛ совпадает.
- Роль `APPLICANT` нельзя назначить вручную через API.

## Режимы, пока нет интеграций

- `ONEID_MOCK=true` — вместо OneID доступен `POST /api/v1/auth/oneid/mock-login` (ПИНФЛ + ФИО).
- `SCORING_MODE` — `auto_pass` | `auto_fail` | `technical_error` | `manual`. Техническая ошибка не отклоняет заявку: ставится флаг `scoring_retry_required`, Фонд делает `POST /fund/applications/{id}/scoring/retry`. В режиме `manual` результат вносится `POST /fund/applications/{id}/scoring/result`.

## Статусы заявки

`DRAFT → SUBMITTED → SCORING_IN_PROGRESS → (SCORING_FAILED | ELIGIBILITY_FAILED | READY_FOR_BANK) → SENT_TO_BANK → BANK_REVIEW → (BANK_APPROVED | BANK_REJECTED) → COUNCIL_REVIEW → (COUNCIL_APPROVED | COUNCIL_REJECTED) → DEMAND_DOCUMENT_CREATED → RESOURCE_ALLOCATION → COMPLETED`

Допустимые переходы — `src/application/workflow.py`. Каждый переход пишется в `application_status_history` (кто, когда, событие, комментарий).

## Принятые допущения (уточнить с заказчиком)

- Итог Совета: «Отклоняю» любого назначенного члена → `COUNCIL_REJECTED`; «Согласен» всех назначенных → `COUNCIL_APPROVED` (кворум/большинство не согласованы).
- Требования Фонда (eligibility) помимо KATM не заданы — пока все проходят (`EligibilityChecker`).
- Список из 9 банков содержит 3 обязательных (Microcreditbank, Xalq banki, Agrobank) и 6 предположительных — заменить на официальный список.
- Файл документа «Требование подтверждено» формирует будущий модуль `documents`; сейчас создаётся запись с номером `TD-ГГГГ-NNNNNN`.
- Фото хранятся на диске (`MEDIA_PATH`); переход на закрытый S3 — в модуле `documents`.

## Разработка

```bash
uv run ruff check src && uv run ruff format src
uv run alembic revision --autogenerate -m "..."
```
