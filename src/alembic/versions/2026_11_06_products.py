"""Продукты Фонда: переводы ru/uz/en, этапы и поля анкеты, ответы заявителя, права products.*

Revision ID: b5d7f9a1c3e5
Revises: a4c6e8f0b2d4
Create Date: 2026-11-06

- enum language (ru, uz, en) и таблицы переводов product_translations,
  product_stage_translations, product_field_translations (уникально: объект + язык);
- products, product_banks, product_stages, product_fields;
- applications.product_id, application_field_values, application_field_files;
- права products.create/read/update/delete/approve: Оператору Фонда (роль и его
  сотрудники) — все, Заявителю — products.read.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b5d7f9a1c3e5"
down_revision: Union[str, Sequence[str], None] = "a4c6e8f0b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LANGUAGE = postgresql.ENUM("ru", "uz", "en", name="language")
PRODUCT_STATUS = postgresql.ENUM("DRAFT", "PUBLISHED", "ARCHIVED", name="product_status")
FIELD_TYPE = postgresql.ENUM(
    "STRING", "NUMBER", "DATE", "PHONE", "EMAIL", "PHOTO", "FILE", name="product_field_type"
)

PERMISSIONS = {
    "products.create": ("Создание продуктов", "Новый продукт и копия существующего"),
    "products.read": ("Просмотр продуктов", "Каталог продуктов; заявитель видит опубликованные"),
    "products.update": ("Изменение продуктов", "Названия, банки, сроки, этапы и поля анкеты"),
    "products.delete": ("Удаление продуктов", "Удаление продукта без заявок"),
    "products.approve": ("Публикация продуктов", "Публикация и снятие с публикации"),
}
FUND_OPERATOR = list(PERMISSIONS)
APPLICANT = ["products.read"]


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    LANGUAGE.create(bind, checkfirst=True)
    PRODUCT_STATUS.create(bind, checkfirst=True)
    FIELD_TYPE.create(bind, checkfirst=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="product_status", create_type=False),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("allowed_subject_types", postgresql.ARRAY(sa.String(20)), nullable=False),
        sa.Column("accept_from", sa.Date()),
        sa.Column("accept_to", sa.Date()),
        sa.Column(
            "copied_from_id",
            sa.Integer(),
            sa.ForeignKey(
                "products.id", ondelete="SET NULL", name="fk_products_copied_from_id_products"
            ),
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_products_created_by_id_users"),
        ),
        *_timestamps(),
    )
    op.create_index("ix_products_status", "products", ["status"])

    op.create_table(
        "product_banks",
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey(
                "products.id", ondelete="CASCADE", name="fk_product_banks_product_id_products"
            ),
            primary_key=True,
        ),
        sa.Column(
            "bank_id",
            sa.Integer(),
            sa.ForeignKey("banks.id", ondelete="RESTRICT", name="fk_product_banks_bank_id_banks"),
            primary_key=True,
        ),
    )

    op.create_table(
        "product_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey(
                "products.id", ondelete="CASCADE", name="fk_product_stages_product_id_products"
            ),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("product_id", "number", name="uq_product_stages_product_id"),
    )
    op.create_index("ix_product_stages_product_id", "product_stages", ["product_id"])

    op.create_table(
        "product_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "stage_id",
            sa.Integer(),
            sa.ForeignKey(
                "product_stages.id",
                ondelete="CASCADE",
                name="fk_product_fields_stage_id_product_stages",
            ),
            nullable=False,
        ),
        sa.Column(
            "field_type",
            postgresql.ENUM(name="product_field_type", create_type=False),
            nullable=False,
        ),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_files", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_product_fields_stage_id", "product_fields", ["stage_id"])

    for table, owner, owner_table, with_description in (
        ("product_translations", "product_id", "products", True),
        ("product_stage_translations", "stage_id", "product_stages", False),
        ("product_field_translations", "field_id", "product_fields", False),
    ):
        columns = [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                owner,
                sa.Integer(),
                sa.ForeignKey(
                    f"{owner_table}.id",
                    ondelete="CASCADE",
                    name=f"fk_{table}_{owner}_{owner_table}",
                ),
                nullable=False,
            ),
            sa.Column(
                "language", postgresql.ENUM(name="language", create_type=False), nullable=False
            ),
            sa.Column("name", sa.String(255), nullable=False),
        ]
        if with_description:
            columns.append(sa.Column("description", sa.Text()))
        op.create_table(
            table, *columns, sa.UniqueConstraint(owner, "language", name=f"uq_{table}_{owner}")
        )
        op.create_index(f"ix_{table}_{owner}", table, [owner])

    op.add_column("applications", sa.Column("product_id", sa.Integer()))
    op.create_foreign_key(
        "fk_applications_product_id_products",
        "applications",
        "products",
        ["product_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_applications_product_id", "applications", ["product_id"])

    op.create_table(
        "application_field_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey(
                "applications.id",
                ondelete="CASCADE",
                name="fk_application_field_values_application_id_applications",
            ),
            nullable=False,
        ),
        sa.Column(
            "field_id",
            sa.Integer(),
            sa.ForeignKey(
                "product_fields.id",
                ondelete="RESTRICT",
                name="fk_application_field_values_field_id_product_fields",
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "application_id", "field_id", name="uq_application_field_values_application_id"
        ),
    )
    op.create_index(
        "ix_application_field_values_application_id",
        "application_field_values",
        ["application_id"],
    )
    op.create_index(
        "ix_application_field_values_field_id", "application_field_values", ["field_id"]
    )

    op.create_table(
        "application_field_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey(
                "applications.id",
                ondelete="CASCADE",
                name="fk_application_field_files_application_id_applications",
            ),
            nullable=False,
        ),
        sa.Column(
            "field_id",
            sa.Integer(),
            sa.ForeignKey(
                "product_fields.id",
                ondelete="RESTRICT",
                name="fk_application_field_files_field_id_product_fields",
            ),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_application_field_files_application_id", "application_field_files", ["application_id"]
    )
    op.create_index(
        "ix_application_field_files_field_id", "application_field_files", ["field_id"]
    )

    # Права: на свежей БД seed-миграция уже вставила их из каталога — ON CONFLICT.
    for code, (name, description) in PERMISSIONS.items():
        op.execute(
            sa.text(
                "INSERT INTO permissions (code, name, description) VALUES (:c, :n, :d) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(c=code, n=name, d=description)
        )
    for role, codes in (("FUND_OPERATOR", FUND_OPERATOR), ("APPLICANT", APPLICANT)):
        op.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes)
                WHERE r.code = :role
                ON CONFLICT DO NOTHING
                """
            ).bindparams(role=role, codes=codes)
        )
    # Эффективные права сотрудника = его права ∩ права роли: выдаём новые права
    # уже заведённым операторам Фонда.
    op.execute(
        sa.text(
            """
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT u.id, p.id FROM users u
            JOIN roles r ON r.id = u.role_id
            JOIN permissions p ON p.code = ANY(:codes)
            WHERE r.code = 'FUND_OPERATOR'
            ON CONFLICT DO NOTHING
            """
        ).bindparams(codes=FUND_OPERATOR)
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'products.%'"))
    op.drop_table("application_field_files")
    op.drop_table("application_field_values")
    op.drop_index("ix_applications_product_id", table_name="applications")
    op.drop_constraint("fk_applications_product_id_products", "applications", type_="foreignkey")
    op.drop_column("applications", "product_id")
    op.drop_table("product_field_translations")
    op.drop_table("product_stage_translations")
    op.drop_table("product_translations")
    op.drop_table("product_fields")
    op.drop_table("product_stages")
    op.drop_table("product_banks")
    op.drop_table("products")
    FIELD_TYPE.drop(op.get_bind(), checkfirst=True)
    PRODUCT_STATUS.drop(op.get_bind(), checkfirst=True)
    LANGUAGE.drop(op.get_bind(), checkfirst=True)
