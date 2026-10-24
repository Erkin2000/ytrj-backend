"""project info in applications: amount, loan term, total cost, jobs, description

Revision ID: f6b8c0d2e4a6
Revises: e5a7b9c1d3f5
Create Date: 2026-10-24 17:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6b8c0d2e4a6"
down_revision: Union[str, Sequence[str], None] = "e5a7b9c1d3f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("project_requested_amount", sa.Numeric(precision=18, scale=2), nullable=True),
    )
    op.add_column(
        "applications", sa.Column("project_loan_term_months", sa.Integer(), nullable=True)
    )
    op.add_column(
        "applications",
        sa.Column("project_total_cost", sa.Numeric(precision=18, scale=2), nullable=True),
    )
    op.add_column("applications", sa.Column("project_jobs_count", sa.Integer(), nullable=True))
    op.add_column("applications", sa.Column("project_description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "project_description")
    op.drop_column("applications", "project_jobs_count")
    op.drop_column("applications", "project_total_cost")
    op.drop_column("applications", "project_loan_term_months")
    op.drop_column("applications", "project_requested_amount")
