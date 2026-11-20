"""Новости сайта (маркетинг)

Revision ID: f2b4d6e8a0c3
Revises: e1a3c5d7f9b2
Create Date: 2026-11-20

- таблицы news и news_translations (заголовок и текст на ru / uz / en), тип news_status;
- права news.create/read/update/delete — роли «Маркетинг» и её сотрудникам
  (у сотрудников права выдаются поштучно).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2b4d6e8a0c3"
down_revision: Union[str, Sequence[str], None] = "e1a3c5d7f9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = {
    "news.create": ("Создание новостей", "Новая новость: сразу, в выбранное время или черновик"),
    "news.read": ("Просмотр новостей", "Все новости, включая черновики и отложенные"),
    "news.update": ("Изменение новостей", "Текст, дата, фото и публикация"),
    "news.delete": ("Удаление новостей", "Удаление новости вместе с фото"),
}

news_status = postgresql.ENUM("DRAFT", "PUBLISHED", name="news_status")
language = postgresql.ENUM("ru", "uz", "en", name="language", create_type=False)


def upgrade() -> None:
    news_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "status", postgresql.ENUM(name="news_status", create_type=False), nullable=False
        ),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("news_date", sa.Date(), nullable=False),
        sa.Column("photo_path", sa.String(length=500), nullable=True),
        sa.Column("photo_name", sa.String(length=255), nullable=True),
        sa.Column("photo_content_type", sa.String(length=100), nullable=True),
        sa.Column("photo_size", sa.Integer(), nullable=True),
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
    op.create_index(op.f("ix_news_status"), "news", ["status"], unique=False)
    op.create_index(op.f("ix_news_publish_at"), "news", ["publish_at"], unique=False)
    op.create_table(
        "news_translations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("news_id", sa.Integer(), nullable=False),
        sa.Column("language", language, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["news_id"], ["news.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("news_id", "language"),
    )
    op.create_index(
        op.f("ix_news_translations_news_id"), "news_translations", ["news_id"], unique=False
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
            "UPDATE roles SET description = 'Контент сайта: новости и вопросы-ответы (FAQ)' "
            "WHERE code = 'MARKETING'"
        )
    )
    codes = sa.bindparam("codes", value=list(PERMISSIONS), type_=postgresql.ARRAY(sa.String))
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes)
            WHERE r.code = 'MARKETING'
            ON CONFLICT DO NOTHING
            """
        ).bindparams(codes)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT u.id, p.id FROM users u
            JOIN roles r ON r.id = u.role_id
            JOIN permissions p ON p.code = ANY(:codes)
            WHERE r.code = 'MARKETING'
            ON CONFLICT DO NOTHING
            """
        ).bindparams(codes)
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'news.%'"))
    op.execute(
        sa.text(
            "UPDATE roles SET description = 'Контент сайта: вопросы и ответы (FAQ)' "
            "WHERE code = 'MARKETING'"
        )
    )
    op.drop_index(op.f("ix_news_translations_news_id"), table_name="news_translations")
    op.drop_table("news_translations")
    op.drop_index(op.f("ix_news_publish_at"), table_name="news")
    op.drop_index(op.f("ix_news_status"), table_name="news")
    op.drop_table("news")
    news_status.drop(op.get_bind(), checkfirst=True)
