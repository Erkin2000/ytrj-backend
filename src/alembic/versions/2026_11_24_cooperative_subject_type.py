"""Тип субъекта «Кооператив» (COOPERATIVE)

Revision ID: c8e0a2b4d6f9
Revises: b7d9f1a3c5e6
Create Date: 2026-11-24

- значение COOPERATIVE в PG-типе `subject_type` (тип субъекта заявки);
- кооперативы добавлены в `allowed_subject_types` всех банков: кредит кооперативам идёт через
  банк, а банк принимает заявку только своего типа субъекта. Фонд может убрать тип у банка
  (`PATCH /banks/{id}`).

Downgrade убирает COOPERATIVE у банков и продуктов; значение PG-типа остаётся (PostgreSQL не
удаляет значения enum), заявок с ним быть не должно.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8e0a2b4d6f9"
down_revision: str | Sequence[str] | None = "b7d9f1a3c5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE subject_type ADD VALUE IF NOT EXISTS 'COOPERATIVE'")
    op.execute(
        sa.text(
            "UPDATE banks SET allowed_subject_types = "
            "array_append(allowed_subject_types, 'COOPERATIVE') "
            "WHERE NOT ('COOPERATIVE' = ANY(allowed_subject_types))"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE banks SET allowed_subject_types = "
            "array_remove(allowed_subject_types, 'COOPERATIVE')"
        )
    )
    op.execute(
        sa.text(
            "UPDATE products SET allowed_subject_types = "
            "array_remove(allowed_subject_types, 'COOPERATIVE')"
        )
    )
