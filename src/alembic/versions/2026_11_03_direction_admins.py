"""direction admins: users.is_direction_admin + per-user permissions

Revision ID: d1f3a5b7c9e1
Revises: c9e1f3a5b7d9
Create Date: 2026-11-03 15:00:00

Existing staff (any role except APPLICANT and superuser roles) receive all
permissions of their role, so nobody loses access after the switch to
per-user permissions.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1f3a5b7c9e1"
down_revision: Union[str, Sequence[str], None] = "c9e1f3a5b7d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_direction_admin", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.create_table(
        "user_permissions",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "permission_id"),
    )
    op.execute(
        """
        INSERT INTO user_permissions (user_id, permission_id)
        SELECT u.id, rp.permission_id
        FROM users u
        JOIN roles r ON r.id = u.role_id
        JOIN role_permissions rp ON rp.role_id = r.id
        WHERE r.code <> 'APPLICANT' AND NOT r.is_superuser
        """
    )


def downgrade() -> None:
    op.drop_table("user_permissions")
    op.drop_column("users", "is_direction_admin")
