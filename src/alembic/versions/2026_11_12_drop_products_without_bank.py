"""Отказ от продуктов без банка: удаление products.uses_bank

Revision ID: e3a5c7e9b1d3
Revises: d1f3a5c7e9b1
Create Date: 2026-11-12

Все продукты снова работают только через банк: Фонд → Совет → банк.
Продукты, которые были без банка, становятся обычными: для публикации им нужен банк.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3a5c7e9b1d3"
down_revision: Union[str, Sequence[str], None] = "d1f3a5c7e9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("products", "uses_bank")


def downgrade() -> None:
    op.add_column(
        "products",
        sa.Column("uses_bank", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
