#!/bin/sh
# Entrypoint контейнера приложения:
#   1) ждём PostgreSQL;
#   2) alembic upgrade head (схема + сид: права, роли, банки);
#   3) реестр проектов: пустые программы заполняются сидом (идемпотентно);
#   4) создаём суперпользователя SUPERUSER с паролем ADMIN_PASSWORD (идемпотентно);
#   5) запускаем команду из CMD (uvicorn).
set -eu

: "${DB_HOST:=db}"
: "${DB_PORT:=5432}"
: "${SUPERUSER:=admin}"
: "${ADMIN_PASSWORD:=admin12345}"
: "${RUN_MIGRATIONS:=true}"
: "${CREATE_SUPERUSER:=true}"
: "${SEED_REGISTRY:=true}"
export DB_HOST DB_PORT SUPERUSER ADMIN_PASSWORD

echo "[entrypoint] waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} ..."
attempt=0
until python - <<'PY'
import os, socket, sys
s = socket.socket()
s.settimeout(2)
try:
    s.connect((os.environ["DB_HOST"], int(os.environ["DB_PORT"])))
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        echo "[entrypoint] PostgreSQL is not reachable, giving up." >&2
        exit 1
    fi
    sleep 2
done

if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "[entrypoint] alembic upgrade head"
    alembic upgrade head
fi

if [ "$SEED_REGISTRY" = "true" ]; then
    echo "[entrypoint] registry seed (only programs without projects)"
    python -m src.registry.cli seed
fi

if [ "$CREATE_SUPERUSER" = "true" ]; then
    echo "[entrypoint] ensure superuser '${SUPERUSER}'"
    python -m src.account.cli create-superuser --if-missing
fi

echo "[entrypoint] starting: $*"
exec "$@"
