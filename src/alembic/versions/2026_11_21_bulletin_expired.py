"""Статус бюллетеня EXPIRED — срок подписания прошёл

Revision ID: a9c1e3f5b7d0
Revises: f8b0d2e4a6c9
Create Date: 2026-11-21

Разосланный бюллетень, у которого прошёл срок подписания, а подписали не все,
переходит в EXPIRED (фоновая задача бюллетеней). Уже просроченные бюллетени
переводятся при первом проходе задачи после деплоя.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a9c1e3f5b7d0"
down_revision: Union[str, Sequence[str], None] = "f8b0d2e4a6c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADD VALUE нельзя выполнять внутри транзакции вместе с использованием значения.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE bulletin_status ADD VALUE IF NOT EXISTS 'EXPIRED' AFTER 'COMPLETED'")


def downgrade() -> None:
    # Значение enum в PostgreSQL не удаляется; просроченные возвращаются в «ждут подписей».
    op.execute(
        "UPDATE bulletins b SET status = CASE WHEN EXISTS ("
        "SELECT 1 FROM bulletin_signatures s WHERE s.bulletin_id = b.id AND s.signed_at IS NOT NULL"
        ") THEN 'PARTIALLY_SIGNED'::bulletin_status ELSE 'PUBLISHED'::bulletin_status END "
        "WHERE b.status = 'EXPIRED'"
    )
