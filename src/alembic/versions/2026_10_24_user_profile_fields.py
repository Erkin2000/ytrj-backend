"""profile fields: users.gender, users.date_of_birth + snapshot in applications

YIA SSO передаёт только Ф.И.О. и ПИНФЛ. Телефон, паспорт, ИНН, email, пол и дату
рождения заявитель дополняет сам (PATCH /auth/me); они нужны для создания заявки
и фиксируются в снимке данных заявителя.

Revision ID: d4f6a8b0c2e4
Revises: c3e5a7b9d1f3
Create Date: 2026-10-24 12:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4f6a8b0c2e4"
down_revision: Union[str, Sequence[str], None] = "c3e5a7b9d1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

gender_enum = sa.Enum("MALE", "FEMALE", name="gender")


def _gender_column(name: str) -> sa.Column:
    return sa.Column(name, sa.Enum("MALE", "FEMALE", name="gender", create_type=False))


def upgrade() -> None:
    gender_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("users", _gender_column("gender"))
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))

    op.add_column(
        "applications", sa.Column("applicant_email", sa.String(length=255), nullable=True)
    )
    op.add_column("applications", _gender_column("applicant_gender"))
    op.add_column("applications", sa.Column("applicant_date_of_birth", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "applicant_date_of_birth")
    op.drop_column("applications", "applicant_gender")
    op.drop_column("applications", "applicant_email")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "gender")
    gender_enum.drop(op.get_bind(), checkfirst=True)
