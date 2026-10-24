"""company details (inn, director) in applications + application_founders table

Руководитель предприятия может не совпадать с заявителем, поэтому его данные
вводятся отдельно от снимка профиля. Учредители — отдельная таблица (ООО).

Revision ID: e5a7b9c1d3f5
Revises: d4f6a8b0c2e4
Create Date: 2026-10-24 15:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5a7b9c1d3f5"
down_revision: Union[str, Sequence[str], None] = "d4f6a8b0c2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("company_inn", sa.String(length=20), nullable=True))
    op.add_column(
        "applications", sa.Column("director_full_name", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "applications", sa.Column("director_passport", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "applications", sa.Column("director_phone", sa.String(length=20), nullable=True)
    )
    op.add_column("applications", sa.Column("director_date_of_birth", sa.Date(), nullable=True))

    op.create_table(
        "application_founders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("passport_number", sa.String(length=20), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_founders_application_id"),
        "application_founders",
        ["application_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_application_founders_application_id"), table_name="application_founders"
    )
    op.drop_table("application_founders")
    op.drop_column("applications", "director_date_of_birth")
    op.drop_column("applications", "director_phone")
    op.drop_column("applications", "director_passport")
    op.drop_column("applications", "director_full_name")
    op.drop_column("applications", "company_inn")
