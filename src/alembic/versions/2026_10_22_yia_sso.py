"""yia sso: users.oneid_sub -> users.sso_sub

Вход заявителей переведён с прямой интеграции OneID на SSO YIA Portal.
Идентификатор пользователя теперь — sub портала (общий для всех проектов).

Revision ID: c3e5a7b9d1f3
Revises: a1c3e5f7b9d1
Create Date: 2026-10-22 22:00:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c3e5a7b9d1f3"
down_revision: Union[str, Sequence[str], None] = "a1c3e5f7b9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_users_oneid_sub", "users", type_="unique")
    op.alter_column("users", "oneid_sub", new_column_name="sso_sub")
    op.create_unique_constraint("uq_users_sso_sub", "users", ["sso_sub"])


def downgrade() -> None:
    op.drop_constraint("uq_users_sso_sub", "users", type_="unique")
    op.alter_column("users", "sso_sub", new_column_name="oneid_sub")
    op.create_unique_constraint("uq_users_oneid_sub", "users", ["oneid_sub"])
