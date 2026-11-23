"""Переводы ролей и прав на ru / uz / en

Revision ID: d3f5b7c9e1a2
Revises: c2e4a6b8d0f1
Create Date: 2026-11-23

- таблицы permission_translations и role_translations (язык + название + описание);
- права: переводы из каталога `src/rbac/i18n.py`, русская колонка `permissions.name`
  синхронизируется с каталогом;
- роли: русское название — текущее из БД, uz / en — из каталога для системных ролей,
  у своих ролей (созданных Super Admin) — копия русского, пока их не переведут через API.

Новая миграция, которая добавляет права, должна вызвать `fill_permission_translations()`
отсюда (или повторить её), иначе у новых прав не будет переводов.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d3f5b7c9e1a2"
down_revision: str | Sequence[str] | None = "c2e4a6b8d0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LANGUAGE = postgresql.ENUM("ru", "uz", "en", name="language", create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "permission_translations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name=op.f("fk_permission_translations_permission_id_permissions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permission_translations")),
        sa.UniqueConstraint(
            "permission_id", "language", name=op.f("uq_permission_translations_permission_id")
        ),
    )
    op.create_index(
        op.f("ix_permission_translations_permission_id"),
        "permission_translations",
        ["permission_id"],
        unique=False,
    )
    op.create_table(
        "role_translations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("language", LANGUAGE, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_role_translations_role_id_roles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_translations")),
        sa.UniqueConstraint("role_id", "language", name=op.f("uq_role_translations_role_id")),
    )
    op.create_index(
        op.f("ix_role_translations_role_id"), "role_translations", ["role_id"], unique=False
    )
    fill_permission_translations()
    _fill_role_translations()


def fill_permission_translations() -> None:
    """Переводы для всех прав без переводов (повторный вызов ничего не дублирует)."""
    from src.rbac.i18n import permission_translations

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT p.id, p.code, p.name, p.description FROM permissions p "
            "WHERE NOT EXISTS (SELECT 1 FROM permission_translations t "
            "WHERE t.permission_id = p.id)"
        )
    ).all()
    for permission_id, code, name, description in rows:
        texts = permission_translations(code, name, description)
        ru_name, ru_description = texts["ru"]
        bind.execute(
            sa.text("UPDATE permissions SET name = :n, description = :d WHERE id = :id"),
            {"n": ru_name, "d": ru_description, "id": permission_id},
        )
        for language, (t_name, t_description) in texts.items():
            bind.execute(
                sa.text(
                    "INSERT INTO permission_translations (permission_id, language, name, "
                    "description) VALUES (:id, CAST(:lang AS language), :n, :d)"
                ),
                {"id": permission_id, "lang": str(language), "n": t_name, "d": t_description},
            )


def _fill_role_translations() -> None:
    from src.rbac.i18n import ROLE_I18N

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, code, name, description FROM roles")).all()
    for role_id, code, name, description in rows:
        i18n = ROLE_I18N.get(code, {})
        texts = {
            "ru": (name, description),
            "uz": i18n.get("uz", (name, description)),
            "en": i18n.get("en", (name, description)),
        }
        for language, (t_name, t_description) in texts.items():
            bind.execute(
                sa.text(
                    "INSERT INTO role_translations (role_id, language, name, description) "
                    "VALUES (:id, CAST(:lang AS language), :n, :d)"
                ),
                {"id": role_id, "lang": language, "n": t_name, "d": t_description},
            )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_role_translations_role_id"), table_name="role_translations")
    op.drop_table("role_translations")
    op.drop_index(
        op.f("ix_permission_translations_permission_id"), table_name="permission_translations"
    )
    op.drop_table("permission_translations")
