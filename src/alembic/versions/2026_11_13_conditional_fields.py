"""Условные поля анкеты: типы SELECT / RADIO / CHECKBOX, варианты ответа, условия показа

Revision ID: f4b6d8e0a2c4
Revises: e3a5c7e9b1d3
Create Date: 2026-11-13

- значения SELECT, RADIO, CHECKBOX в enum product_field_type (необратимо: PostgreSQL
  не удаляет значения из enum);
- product_field_options и product_field_option_translations — варианты ответа
  полей с выбором (ru / uz / en, уникально: вариант + язык);
- product_stages.condition_field_id / condition_option_ids и
  product_fields.condition_field_id / condition_option_ids — условие показа:
  этап или поле видны, если в управляющем поле выбран один из вариантов.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f4b6d8e0a2c4"
down_revision: Union[str, Sequence[str], None] = "e3a5c7e9b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONDITION_TABLES = ("product_stages", "product_fields")


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for value in ("SELECT", "RADIO", "CHECKBOX"):
            op.execute(f"ALTER TYPE product_field_type ADD VALUE IF NOT EXISTS '{value}'")

    op.create_table(
        "product_field_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "field_id",
            sa.Integer(),
            sa.ForeignKey(
                "product_fields.id",
                ondelete="CASCADE",
                name="fk_product_field_options_field_id_product_fields",
            ),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_product_field_options_field_id", "product_field_options", ["field_id"])

    op.create_table(
        "product_field_option_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "option_id",
            sa.Integer(),
            sa.ForeignKey(
                "product_field_options.id",
                ondelete="CASCADE",
                name="fk_product_field_option_translations_option_id",
            ),
            nullable=False,
        ),
        sa.Column("language", postgresql.ENUM(name="language", create_type=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.UniqueConstraint(
            "option_id", "language", name="uq_product_field_option_translations_option_id"
        ),
    )
    op.create_index(
        "ix_product_field_option_translations_option_id",
        "product_field_option_translations",
        ["option_id"],
    )

    for table in CONDITION_TABLES:
        op.add_column(table, sa.Column("condition_field_id", sa.Integer()))
        op.add_column(table, sa.Column("condition_option_ids", postgresql.ARRAY(sa.Integer())))
        op.create_foreign_key(
            f"fk_{table}_condition_field_id_product_fields",
            table,
            "product_fields",
            ["condition_field_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table}_condition_field_id", table, ["condition_field_id"])


def downgrade() -> None:
    for table in CONDITION_TABLES:
        op.drop_index(f"ix_{table}_condition_field_id", table_name=table)
        op.drop_constraint(
            f"fk_{table}_condition_field_id_product_fields", table, type_="foreignkey"
        )
        op.drop_column(table, "condition_option_ids")
        op.drop_column(table, "condition_field_id")

    op.drop_index(
        "ix_product_field_option_translations_option_id",
        table_name="product_field_option_translations",
    )
    op.drop_table("product_field_option_translations")
    op.drop_index("ix_product_field_options_field_id", table_name="product_field_options")
    op.drop_table("product_field_options")
    # Значения SELECT / RADIO / CHECKBOX остаются в enum product_field_type.
