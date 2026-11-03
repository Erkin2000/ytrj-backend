"""drop login_tickets: login tickets / role cabinets removed

Revision ID: e2a4c6e8f0b2
Revises: d1f3a5b7c9e1
Create Date: 2026-11-03 18:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2a4c6e8f0b2"
down_revision: Union[str, Sequence[str], None] = "d1f3a5b7c9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_login_tickets_user_id", table_name="login_tickets")
    op.drop_table("login_tickets")


def downgrade() -> None:
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
