import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

sys.path.append(str(Path(__file__).resolve().parents[2]))

# Модели должны быть импортированы, чтобы попасть в Base.metadata (autogenerate).
from src.account.models.user_model import UserORM  # noqa: E402, F401
from src.application.models.application_model import ApplicationORM  # noqa: E402, F401
from src.application.models.bank_model import BankORM  # noqa: E402, F401
from src.application.models.council_assignment_model import CouncilAssignmentORM  # noqa: E402, F401
from src.application.models.demand_document_model import DemandDocumentORM  # noqa: E402, F401
from src.application.models.document_model import ApplicationDocumentORM  # noqa: E402, F401
from src.application.models.founder_model import ApplicationFounderORM  # noqa: E402, F401
from src.application.models.photo_model import ApplicationPhotoORM  # noqa: E402, F401
from src.application.models.resource_allocation_model import ResourceAllocationORM  # noqa: E402, F401
from src.application.models.scoring_model import ScoringAttemptORM  # noqa: E402, F401
from src.application.models.status_history_model import StatusHistoryORM  # noqa: E402, F401
from src.auth.models.refresh_token_model import RefreshTokenORM  # noqa: E402, F401
from src.config import settings  # noqa: E402
from src.database import Base  # noqa: E402
from src.rbac.models.permission_model import PermissionORM  # noqa: E402, F401
from src.rbac.models.role_model import RoleORM  # noqa: E402, F401
from src.rbac.models.role_permission_model import RolePermissionORM  # noqa: E402, F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DB_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
