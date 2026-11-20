"""Роль «Маркетинг» и FAQ сайта

Revision ID: e1a3c5d7f9b2
Revises: d9f1b3c5e7a9
Create Date: 2026-11-20

- таблицы faqs и faq_translations (вопрос и ответ на ru / uz / en);
- права faq.create/read/update/delete;
- системная роль MARKETING с этими правами. Сотрудник маркетинга входит через
  YIA Portal (One ID): Super Admin заводит его с ролью «Маркетинг» и ПИНФЛ.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1a3c5d7f9b2"
down_revision: Union[str, Sequence[str], None] = "d9f1b3c5e7a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = {
    "faq.create": ("Создание вопросов FAQ", "Новый вопрос и ответ для сайта"),
    "faq.read": ("Просмотр вопросов FAQ", "Все вопросы, включая скрытые с сайта"),
    "faq.update": ("Изменение вопросов FAQ", "Текст, порядок и показ на сайте"),
    "faq.delete": ("Удаление вопросов FAQ", "Удаление вопроса"),
}

language = postgresql.ENUM("ru", "uz", "en", name="language", create_type=False)


def upgrade() -> None:
    op.create_table(
        "faqs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "faq_translations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("faq_id", sa.Integer(), nullable=False),
        sa.Column("language", language, nullable=False),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["faq_id"], ["faqs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("faq_id", "language"),
    )
    op.create_index(
        op.f("ix_faq_translations_faq_id"), "faq_translations", ["faq_id"], unique=False
    )

    for code, (name, description) in PERMISSIONS.items():
        op.execute(
            sa.text(
                "INSERT INTO permissions (code, name, description) VALUES (:c, :n, :d) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(c=code, n=name, d=description)
        )
    op.execute(
        sa.text(
            "INSERT INTO roles (code, name, description, is_superuser, is_system) "
            "VALUES ('MARKETING', 'Маркетинг', 'Контент сайта: вопросы и ответы (FAQ)', "
            "false, true) ON CONFLICT DO NOTHING"
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes)
            WHERE r.code = 'MARKETING'
            ON CONFLICT DO NOTHING
            """
        ).bindparams(
            sa.bindparam("codes", value=list(PERMISSIONS), type_=postgresql.ARRAY(sa.String))
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'faq.%'"))
    # users.role_id — ON DELETE SET NULL: сотрудники маркетинга останутся без роли.
    op.execute(sa.text("DELETE FROM roles WHERE code = 'MARKETING'"))
    op.drop_index(op.f("ix_faq_translations_faq_id"), table_name="faq_translations")
    op.drop_table("faq_translations")
    op.drop_table("faqs")
