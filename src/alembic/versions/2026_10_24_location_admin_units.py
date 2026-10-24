"""location: region, district, makhalla in applications

Revision ID: a7c9d1e3f5b7
Revises: f6b8c0d2e4a6
Create Date: 2026-10-24 18:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c9d1e3f5b7"
down_revision: Union[str, Sequence[str], None] = "f6b8c0d2e4a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "applications", sa.Column("location_region", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "applications", sa.Column("location_district", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "applications", sa.Column("location_makhalla", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("applications", "location_makhalla")
    op.drop_column("applications", "location_district")
    op.drop_column("applications", "location_region")
