"""Новости из Telegram-канала: источник новости и пост канала

Revision ID: b4d6f8a0c2e5
Revises: a3c5e7f9b1d4
Create Date: 2026-11-20

- news.source (MARKETING / TELEGRAM, по умолчанию MARKETING — для уже созданных новостей);
- news.telegram_chat_id / telegram_message_id (уникальны вместе — один пост = одна новость),
  telegram_media_group_id (альбом), telegram_url (ссылка на пост).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4d6f8a0c2e5"
down_revision: Union[str, Sequence[str], None] = "a3c5e7f9b1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

news_source = postgresql.ENUM("MARKETING", "TELEGRAM", name="news_source")


def upgrade() -> None:
    news_source.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "news",
        sa.Column(
            "source",
            postgresql.ENUM(name="news_source", create_type=False),
            server_default="MARKETING",
            nullable=False,
        ),
    )
    op.add_column("news", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
    op.add_column("news", sa.Column("telegram_message_id", sa.BigInteger(), nullable=True))
    op.add_column("news", sa.Column("telegram_media_group_id", sa.String(length=64), nullable=True))
    op.add_column("news", sa.Column("telegram_url", sa.String(length=255), nullable=True))
    op.create_unique_constraint(
        op.f("uq_news_telegram_chat_id"), "news", ["telegram_chat_id", "telegram_message_id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_news_telegram_chat_id"), "news", type_="unique")
    op.drop_column("news", "telegram_url")
    op.drop_column("news", "telegram_media_group_id")
    op.drop_column("news", "telegram_message_id")
    op.drop_column("news", "telegram_chat_id")
    op.drop_column("news", "source")
    news_source.drop(op.get_bind(), checkfirst=True)
