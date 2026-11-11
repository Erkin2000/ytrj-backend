"""Категории продуктов: product_categories + переводы, products.category_id (обязателен)

Revision ID: c7e9a1b3d5f7
Revises: b5d7f9a1c3e5
Create Date: 2026-11-11

Если продукты уже есть, создаётся категория «Без категории» / «Kategoriyasiz» /
«Uncategorized», и все продукты попадают в неё. Фонд потом переносит их в нужные.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7e9a1b3d5f7"
down_revision: Union[str, Sequence[str], None] = "b5d7f9a1c3e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_NAMES = {"ru": "Без категории", "uz": "Kategoriyasiz", "en": "Uncategorized"}


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "product_category_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey(
                "product_categories.id",
                ondelete="CASCADE",
                name="fk_product_category_translations_category_id_product_categories",
            ),
            nullable=False,
        ),
        sa.Column("language", postgresql.ENUM(name="language", create_type=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.UniqueConstraint(
            "category_id", "language", name="uq_product_category_translations_category_id"
        ),
    )
    op.create_index(
        "ix_product_category_translations_category_id",
        "product_category_translations",
        ["category_id"],
    )

    op.add_column("products", sa.Column("category_id", sa.Integer()))
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM products")):
        category_id = bind.scalar(
            sa.text("INSERT INTO product_categories (is_active) VALUES (true) RETURNING id")
        )
        for language, name in DEFAULT_NAMES.items():
            bind.execute(
                sa.text(
                    "INSERT INTO product_category_translations (category_id, language, name) "
                    "VALUES (:c, CAST(:l AS language), :n)"
                ),
                {"c": category_id, "l": language, "n": name},
            )
        bind.execute(sa.text("UPDATE products SET category_id = :c"), {"c": category_id})
    op.alter_column("products", "category_id", nullable=False)
    op.create_foreign_key(
        "fk_products_category_id_product_categories",
        "products",
        "product_categories",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_constraint("fk_products_category_id_product_categories", "products", type_="foreignkey")
    op.drop_column("products", "category_id")
    op.drop_table("product_category_translations")
    op.drop_table("product_categories")
