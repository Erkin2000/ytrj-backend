"""login_tickets: one-time tickets that hand a session over to a role's cabinet

Revision ID: c9e1f3a5b7d9
Revises: b8d0e2f4a6c8
Create Date: 2026-11-03 12:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e1f3a5b7d9"
down_revision: Union[str, Sequence[str], None] = "b8d0e2f4a6c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_hash"),
    )
    op.create_index("ix_login_tickets_user_id", "login_tickets", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_login_tickets_user_id", table_name="login_tickets")
    op.drop_table("login_tickets")
