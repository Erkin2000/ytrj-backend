"""Продукты без банка: products.uses_bank

Revision ID: d1f3a5c7e9b1
Revises: c7e9a1b3d5f7
Create Date: 2026-11-12

uses_bank = true — заявка идёт Фонд → Совет → банк (как раньше, по умолчанию для всех
существующих продуктов); false — заявку одобряет или отклоняет только Фонд.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1f3a5c7e9b1"
down_revision: Union[str, Sequence[str], None] = "c7e9a1b3d5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("uses_bank", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("products", "uses_bank")
