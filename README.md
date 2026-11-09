# Jamg'arma Platform API (YTRJ-EP)

Backend платформы финансирования: модульный монолит на **FastAPI + SQLAlchemy 2 (async) + PostgreSQL 17**.
Документация API — Scalar (`/docs`), админ-панель — SQLAdmin (`/admin`).

## Модули (первая очередь)

| Модуль        | Что делает |
|---------------|-----------|
| `auth`        | Вход всех ролей через SSO YIA Portal (e-yoshlar.uz, OneID на стороне портала; пока mock), вход по паролю для внутренних пользователей, JWT access/refresh с ротацией, `/auth/me`, смена пароля, сессии |
| `rbac`        | Каталог прав `<модуль>.<create\|read\|update\|delete\|approve>`, роли, матрица прав, системные роли |
| `account`     | Пользователи: поиск/фильтры, назначение роли и scope (банк), блокировка, последний вход, сессии, CLI суперпользователя |
| `product`     | Продукты Фонда: названия и описания в таблицах переводов (ru/uz/en), банки, типы субъекта, сроки приёма, этапы и поля анкеты, публикация |
| `application` | Заявки по продуктам: черновик → ответы на поля этапов → отправка → скоринг KATM → Фонд → Совет → банк → завершение. История статусов, индикатор прогресса, каталог банков |

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
  Интерфейс на русском, узбекском и английском (переключатель в верхней панели, `?lang=uz` / `?lang=en`, выбор сохраняется в cookie).
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
- **Продукты** (раздел «Продукты»): список со статусом, типами субъектов, сроками приёма, банками и числом этапов; карточка продукта — названия и описания на ru/uz/en, условия, этапы и поля анкеты, число заявок и отметка о блокировке. В форме правятся только типы субъектов, сроки приёма и банки; этапы, поля и публикация — через API Фонда (там проверяются три языка, блокировка и готовность к публикации). «Переводы продуктов» — исправление названия и описания на одном языке (язык не меняется, переводы не создаются и не удаляются). В карточке заявки по продукту — блок «Анкета продукта» с ответами по этапам и файлами (`/admin/application-field-file/{id}`); блоки старой анкеты показываются только у заявок без продукта.
- **Фото заявок** отдаются под cookie-сессией админки: `/admin/application-photo/{id}` (в меню не показывается).
- **Локализация ru/uz/en**: системные строки SQLAdmin и все наши подписи переводятся через Babel. Каталоги — `src/admin/translations/{uz,en}/LC_MESSAGES/admin.po` (компилируются при старте, `.mo` не хранится); английский содержит только наши строки, системные берутся из каталога SQLAdmin. Русские строки в коде являются msgid: добавляя подпись, добавьте её перевод в оба `.po`. Подписи колонок переводятся на лету (`LocalizedLabelsMixin`), имена моделей и фильтров — через `_l()`.
- Время показывается в часовом поясе Ташкента (UTC+5), суммы — с разделителями разрядов.
- **Оформление**: собственный сайдбар (группы разделов, перенос длинных названий, футер с текущим пользователем и версией), верхняя панель с окружением, переключателями темы (светлая/тёмная, запоминается в браузере) и языка, заголовки страниц с хлебными крошками, favicon.

## Формат ошибок

```json
{"success": false, "message": "Bank 'Asakabank' does not work with subject type SELF_EMPLOYED; allowed: YATT, MCHJ",
 "code": "bank_subject_type_mismatch", "errors": [{"field": "bank_id", "message": "…"}]}
```

- `code` — машиночитаемый код (snake_case от имени исключения: `application_not_editable`, `product_not_available`,
  `field_value_invalid`, `applicant_profile_incomplete`, `application_validation`, `validation_error` для 422 …).
- `errors` — список `{field, message}`: для незаполненных полей заявки/профиля (ключи как в `submission-check`),
  для ошибок, привязанных к полю (`bank_id`, `product_id`, `values.<id поля>`, `file`), и для 422 от pydantic. Иначе `null`.
- В Scalar у каждой ручки кабинета заявителя перечислены возможные 400/403/404 с примерами по каждому `code`.

## Роли и scope

| Роль (`code`)     | Scope |
|-------------------|-------|
| `SUPER_ADMIN`     | всё (is_superuser), управление пользователями/RBAC/справочниками, админ-панель |
| `FUND_OPERATOR`   | продукты (создание, этапы и поля, публикация), все заявки, скоринг, отказ или направление в Совет |
| `BANK_EMPLOYEE`   | только заявки своего банка (`users.bank_id`), начиная со статуса SENT_TO_BANK |
| `COUNCIL_MEMBER`  | только заявки, направленные ему |
| `APPLICANT`       | только свой профиль и свои заявки |

Права по умолчанию для ролей — `src/rbac/permissions.py` (`ROLE_PRESETS`); новые права добавляются туда и в миграцию.

### Права сотрудника и админы направлений

- **Направление** — роль сотрудника: Фонд (`FUND_OPERATOR`), банк (`BANK_EMPLOYEE` + конкретный банк), Совет (`COUNCIL_MEMBER`).
- **Права сотрудника** = его личные права (`user_permissions`) ∩ права роли. Роль — «потолок» направления: если Super Admin уберёт право у роли, оно пропадёт у всех её сотрудников. Заявитель и роль-суперпользователь работают по правам роли. Расчёт — `src/rbac/access.py`.
- **Админ направления** (`users.is_direction_admin`) назначается только Super Admin и только с ролью направления. Через `/users` он создаёт, изменяет, блокирует и удаляет **рядовых сотрудников своего направления** (у банка — только своего банка): роль и банк подставляются его собственные, а выдать можно только права, которые есть у него самого (`GET /users/grantable-permissions` — список для формы). Других админов, себя, сотрудников чужого направления и смену роли он не трогает (403 `user_out_of_scope` / `admin_management` / `permissions_not_grantable`).
- Без `permissions` при создании выдаются все права, которые создающий может выдать для роли; при смене роли Super Admin права пересчитываются так же.
- Права пересчитываются на каждый запрос — изменения действуют сразу, без перевыпуска токена.
- В Совет заявка направляется только членам Совета с правом `council_review.approve`.
- При миграции `d1f3a5b7c9e1` всем существующим сотрудникам выданы все права их роли.

## Политика входа

- **Заявители** входят только через SSO YIA Portal (`sso_integration.md`). Профиль создаётся автоматически с ролью `APPLICANT`; пароль у заявителя отсутствует, `/auth/login` и смена пароля для него закрыты.
- **Внутренние роли** (Super Admin, Фонд, банк, Совет) входят через SSO YIA Portal и/или по логину и паролю (`/auth/login`). Их создаёт Super Admin через `/users` или админ-панель: для входа через портал обязательно указать ПИНФЛ (по нему сотрудник находится при первом входе, затем привязывается `sso_sub`), пароль — по желанию; нужно хотя бы одно из двух. ПИНФЛ уникален; его смена снимает привязку `sso_sub` и закрывает сессии.
- Если портал не передал ПИНФЛ, сотрудника найти нельзя — будет создан новый заявитель. ПИНФЛ у портала обязательно запросить.
- Роль `APPLICANT` нельзя назначить вручную через API.

### Профиль заявителя

Портал гарантирует только `full_name` и `pinfl` — они обновляются при каждом входе и пользователем не редактируются.
Телефон, паспорт, ИНН, email, пол и дату рождения заявитель дополняет сам: `PATCH /api/v1/auth/me`
(любое подмножество полей, `null` очищает; `full_name` / `pinfl` в теле запроса → 422).
`GET /auth/me` отдаёт `profile_complete` и `missing_fields`. Пока профиль не заполнен, `POST /applications`
отвечает 400 со списком полей в `errors`; при отправке черновика недостающие поля профиля попадают в сводку
как `applicant.<field>`. Снимок данных заявителя в заявке обновляется из профиля в момент отправки.
Список обязательных полей — `src/account/profile.py`.

### Продукты

Анкету заявки задаёт Фонд через продукты (права `products.*`; у Оператора Фонда — все, у Заявителя — `products.read`).

Названия и описания хранятся в таблицах переводов (`product_translations`, `product_stage_translations`,
`product_field_translations`) с enum `language` = `ru` | `uz` | `en`; пара «объект + язык» уникальна в БД.
В API это список `translations: [{"language": "ru", "name": "..."}, ...]`: ровно три перевода, каждый язык
один раз, иначе 422 (не хватает языка, язык указан дважды, пустое название). У продукта есть ещё `description` —
на всех трёх языках или ни на одном. При изменении передаются все три перевода. В ответах переводы идут в порядке ru, uz, en.

1. `POST /fund/products` — черновик (`DRAFT`): `translations` (название и описание), `allowed_subject_types`
   (по умолчанию все), `accept_from` / `accept_to` (сроки приёма включительно, пусто — без ограничения), `bank_ids`
   (банки из каталога). `PATCH /fund/products/{id}` меняет эти поля, `bank_ids` заменяет список целиком.
2. `POST /fund/products/{id}/stages` — этап: `number` (уникален в продукте) и `translations`.
3. `POST /fund/products/{id}/stages/{stage_id}/fields` — поле: `field_type`, `translations`, `is_required`,
   `sort_order`, для PHOTO / FILE — `max_files` (1–10). Типы: `STRING`, `NUMBER`, `DATE` (ГГГГ-ММ-ДД),
   `PHONE` (+998XXXXXXXXX), `EMAIL`, `PHOTO` (JPG/PNG/WEBP, `PHOTO_MAX_SIZE_MB`), `FILE` (PDF/DOCX, `DOCUMENT_MAX_SIZE_MB`).
4. `POST /fund/products/{id}/publish` → `PUBLISHED`: нужны активный банк, этап и хотя бы одно поле в каждом этапе
   (иначе 400 `product_not_ready` со списком `bank_ids`, `stages`, `stages.<номер>.fields`).
   `POST .../archive` → `ARCHIVED`: новые заявки не принимаются, черновики не отправляются; повторный `publish` возвращает продукт.

Когда по продукту есть хотя бы одна заявка (включая черновики), этапы и поля менять нельзя (409 `product_locked`),
продукт нельзя удалить (409 `product_in_use`). Названия, описания, банки, типы субъекта и сроки менять можно.
Чтобы изменить анкету — `POST /fund/products/{id}/copy`: новый черновик с теми же банками, этапами и полями
(`copied_from_id`). В ответе `GET /fund/products/{id}` — `applications_count` и `is_locked`.

Справочник типов полей — `GET /products/field-types` (Фонд и заявитель): для каждого типа названия на ru/uz/en, `is_file`, формат и пример значения, `pattern` / `max_length` / `max_digits`, для PHOTO и FILE — допустимые форматы, размер файла и предел `max_files`.

Заявитель видит `GET /products?subject_type=...` — только опубликованные продукты в сроках приёма; в `banks` — только активные банки.

### Заявка по продукту

1. `POST /applications` с `product_id`, `subject_type` и, по желанию, `bank_id` (из `banks` продукта; позже — `PUT /applications/{id}/bank`).
   Продукт должен быть доступен для этого типа субъекта, иначе 400 `product_not_available`.
2. `PUT /applications/{id}/stages/{stage_id}` с `{"values": {"<id поля>": "значение"}}` — меняются только переданные поля,
   `null` или пустая строка очищает. Значения проверяются по типу и хранятся нормализованными (число `1 500,50` → `1500.5`,
   телефон без пробелов, email в нижнем регистре); ошибки — 400 `field_value_invalid` с `errors[].field = values.<id>`.
3. Файлы полей PHOTO / FILE: `POST /applications/{id}/fields/{field_id}/files` (не больше `max_files`),
   `DELETE .../files/{file_id}` — в черновике, `GET .../files/{file_id}` — всем, кто видит заявку.
   Файлы лежат в `MEDIA_PATH/applications/{id}/fields/`.
4. `PATCH /applications/{id}` меняет продукт или тип субъекта; смена продукта очищает ответы, файлы и банк.
5. `GET /applications/{id}/submission-check` и `POST .../submit`: недостающее — `product_id`, `subject_type`, `bank_id`,
   `fields.<id поля>` (обязательные поля без значения или файла), `applicant.<поле профиля>`.

Карточка заявки (`GET /applications/{id}`, Фонд, банк, Совет) содержит `product` и `form` — этапы продукта с ответами
и файлами, у каждого этапа `is_complete`. Банк выбирается из банков продукта; после утверждения Советом заявка
автоматически уходит в него, Фонд вручную в банк не отправляет.

Прежняя фиксированная анкета (тип предприятия, учредители, проект, место деятельности, фото, документы) больше не
заполняется: её ручки удалены, колонки и таблицы старых заявок оставлены для истории и видны в админ-панели.

### Вход через YIA Portal (SSO)

1. Фронтенд вызывает `GET /api/v1/auth/sso/authorize`, сохраняет `state` (например, в sessionStorage) и перенаправляет браузер на `authorize_url`. Пользователь проходит OneID на стороне портала.
2. Портал возвращает браузер на `SSO_REDIRECT_URI` (в точности как зарегистрировано на портале: `https://yoshlarfondi.uz/api/v1/redirect/from-backend`) с `?code=...&state=...` либо `?error=access_denied&state=...`. Эндпоинт `GET /api/v1/redirect/from-backend` отвечает `302` на `SSO_FRONTEND_REDIRECT_URL` (абсолютный URL фронтенда или путь; по умолчанию встроенная страница `/api/auth/one-id/callback`), передавая все query-параметры портала без изменений (ответ с `Cache-Control: no-store` и `Referrer-Policy: no-referrer`).
3. Страница на адресе `SSO_FRONTEND_REDIRECT_URL` сразу (code живёт 60 секунд) сверяет `state` с сохранённым, отправляет `POST /api/v1/auth/sso/callback` с `{code, state, error}` и получает `access_token`, `refresh_token` и `expires_in`.

**Два сайта входа.** У `GET /api/v1/auth/sso/authorize` есть параметр `site`:

| `site` | Клиент портала | `redirect_uri` | Куда `/redirect/from-backend` вернёт браузер |
|---|---|---|---|
| `yoshlarfondi` (по умолчанию) | `SSO_CLIENT_ID` / `SSO_CLIENT_SECRET` | `SSO_REDIRECT_URI` | `SSO_FRONTEND_REDIRECT_URL` |
| `admin` | `SSO_CLIENT_ID_ADMIN` / `SSO_CLIENT_SECRET_ADMIN` (пусто — основной клиент) | `SSO_REDIRECT_URI_ADMIN` | `SSO_FRONTEND_REDIRECT_URL_ADMIN` |

Сайт подписывается внутри `state`, поэтому `POST /auth/sso/callback` меняет `code` тем же клиентом портала, что выдал ссылку входа, а `/redirect/from-backend` по `state` выбирает фронт. У `/redirect/from-backend` тоже есть параметр `site` (`yoshlarfondi` | `admin`): если он передан, фронт выбирается по нему (например, `SSO_REDIRECT_URI_ADMIN=.../redirect/from-backend?site=admin`), а на фронт он не пересылается. Без `SSO_REDIRECT_URI_ADMIN` вход с `site=admin` отклоняется (401 `sso_failed`).

Встроенные страницы (вне OpenAPI, `src/auth/apis/sso_web_api.py`): `GET /api/auth/one-id/login` — кнопка входа через портал и, при `SSO_MOCK=true`, форма тестового входа; `GET /api/auth/one-id/callback` — точка возврата с портала: встроенная страница сама вызывает `POST /auth/sso/callback` и кладёт токены в `localStorage`. Сторонний адрес редиректа задаётся только настройкой `SSO_FRONTEND_REDIRECT_URL`, из запроса он не берётся.

Бэкенд проверяет подпись и срок `state` (`SSO_STATE_TTL_SECONDS`), меняет `code` на профиль через `POST {SSO_BASE_URL}/api/v1/users/auth/sso/token/` с `client_secret` (только backend) и находит пользователя по `sub` портала (`users.sso_sub`), затем по ПИНФЛ; если не найден — создаёт заявителя (`username` = ПИНФЛ, при его отсутствии `sso_<sub>`). ПИНФЛ запрашивается у портала как опциональное поле при онбординге; `region/city/makhalla/role` приходят только у ётакчи и сейчас сохраняется только название региона.

Ошибки: неверный/просроченный `state` → 400; `access_denied` → 403; `invalid_grant` (code просрочен или использован), `invalid_client` (неверные креды или IP бэкенда не в allow-list портала), сетевые ошибки → 401, вход можно повторить.

## Режимы, пока нет интеграций

- `SSO_MOCK=true` — вместо YIA Portal доступен `POST /api/v1/auth/sso/mock-login` (ПИНФЛ + ФИО, опционально `sub`).
- `SCORING_MODE` — `auto_pass` | `auto_fail` | `technical_error`. Техническая ошибка не отклоняет заявку: ставится флаг `scoring_retry_required`, Фонд делает `POST /fund/applications/{id}/scoring/retry`. Ручного ввода результата скоринга нет.

## Статусы заявки

Порядок (решение заказчика от 2026-11-05; в ТЗ от 30.09.2026 банк шёл до Совета): **скоринг → Фонд → Совет → банк**, банк — последний этап.

`DRAFT → SUBMITTED → SCORING_IN_PROGRESS → (SCORING_FAILED | ELIGIBILITY_FAILED | FUND_REVIEW) → (FUND_REJECTED | COUNCIL_REVIEW) → (COUNCIL_REJECTED | COUNCIL_APPROVED) → SENT_TO_BANK → BANK_REVIEW → (BANK_REJECTED | BANK_APPROVED → COMPLETED)`

| Этап | Кто | Действие |
|---|---|---|
| `FUND_REVIEW` | Фонд | `POST /fund/applications/{id}/send-to-council` или `POST /fund/applications/{id}/reject` (причина обязательна) |
| `COUNCIL_REVIEW` | Совет | решение каждого назначенного члена; все «Согласен» → `COUNCIL_APPROVED` и автоматически `SENT_TO_BANK` |
| `SENT_TO_BANK` → `BANK_REVIEW` | банк | приём и решение; одобрение → `BANK_APPROVED` → сразу `COMPLETED` |

Банк видит заявку только после утверждения Советом. Документ «Требование подтверждено» и выделение ресурсов больше не входят в процесс: таблицы `demand_documents` / `resource_allocations` и старые записи доступны в админке только для чтения. Статусы `READY_FOR_BANK`, `DEMAND_DOCUMENT_CREATED`, `RESOURCE_ALLOCATION` — устаревшие: новые заявки их не получают, значения оставлены ради истории. Миграция `f3b5d7e9a1c3` перевела незавершённые заявки в новый порядок (каждый перенос — событие `workflow_migrated` в истории).

Допустимые переходы — `src/application/workflow.py`. Каждый переход пишется в `application_status_history` (кто, когда, событие, комментарий).

## Принятые допущения (уточнить с заказчиком)

- Итог Совета: «Отклоняю» любого назначенного члена → `COUNCIL_REJECTED`; «Согласен» всех назначенных → `COUNCIL_APPROVED` (кворум/большинство не согласованы).
- Требования Фонда (eligibility) помимо KATM не заданы — пока все проходят (`EligibilityChecker`).
- Список из 9 банков содержит 3 обязательных (Microcreditbank, Xalq banki, Agrobank) и 6 предположительных — заменить на официальный список.
- YIA Portal гарантирует только `sub` и `full_name`; телефон, паспорт, ИНН, email, пол и дату рождения заявитель вводит сам в профиле (`PATCH /auth/me`) — без них заявка не создаётся. Если портал начнёт передавать эти поля, их нужно перенести в `SSO_MANAGED_FIELDS`.
- Реквизиты предприятия (СТИР + руководитель) и учредители (хотя бы один) обязательны только для ООО. Формат СТИР — 9 цифр.
- Банк выбирает только заявитель (`PUT /applications/{id}/bank`); сменить банк после отправки заявки нельзя.
- Срок кредита 12–36 месяцев и правило «сумма ≤ стоимость проекта» — предположение; границы вынесены в настройки.
- Фото и документы хранятся на диске (`MEDIA_PATH`); переход на закрытый S3 — в модуле `documents`.

## Тесты

```bash
uv run pytest            # или .venv/Scripts/pytest
```

- `tests/test_urls.py` — юнит-тесты адресов редиректа, БД не нужна.
- Остальные — интеграционные, через настоящее API на локальной БД из `.env`: вход через SSO (`test_auth_sso.py`), админы направлений (`test_direction_admin.py`), полный путь заявки до `COMPLETED` (`test_application_workflow.py`), админ-панель (`test_admin_panel.py`).
- Нужны применённые миграции, `SSO_MOCK=true`, `SCORING_MODE=auto_pass` (для пути заявки) и суперпользователь `admin` (пароль — `TEST_ADMIN_PASSWORD`, по умолчанию `admin12345`). Иначе тесты пропускаются с причиной.
- Тесты создают только синтетических пользователей (ПИНФЛ `99999…`, логин `test_…`) и после каждого теста удаляют созданное по id вместе с файлами заявок; dev-данные не трогаются.

## Разработка

```bash
uv run ruff check src && uv run ruff format src
uv run alembic revision --autogenerate -m "..."
```
