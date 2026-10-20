# syntax=docker/dockerfile:1.7
# Jamg'arma Platform API — образ приложения (FastAPI + uv).
#
# Сборка:   docker compose build
# Запуск:   docker compose up -d
# При старте контейнера entrypoint выполняет миграции Alembic и создаёт
# суперпользователя (SUPERUSER / ADMIN_PASSWORD, по умолчанию admin / admin12345).

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# ---------- зависимости ----------
FROM base AS deps

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /bin/

# Сначала только манифесты: слой с зависимостями кешируется отдельно от кода.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------- финальный образ ----------
FROM base AS runtime

RUN groupadd --system app && useradd --system --gid app --home /app app

COPY --from=deps /app/.venv /app/.venv
COPY alembic.ini ./
COPY src ./src
COPY docker/entrypoint.sh /app/entrypoint.sh

# Нормализуем CRLF (проект разрабатывается на Windows) и даём права на запуск.
RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh \
    && mkdir -p /app/media \
    && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
