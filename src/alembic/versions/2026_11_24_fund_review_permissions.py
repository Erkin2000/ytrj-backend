"""Права для админ-панели по permissions: отдельное окно Фонда, лишнее у Фонда снято

Revision ID: f5b7d9e1a3c4
Revises: e4a6c8d0f2b3
Create Date: 2026-11-24

- новые права fund_review.read (список, счётчики и карточка `/fund/applications`) и
  fund_review.approve (отказ Фонда) с переводами — роли «Оператор Фонда» и её сотрудникам;
  раньше эти ручки открывал applications.read, который есть и у банка, и у Совета;
- у роли «Оператор Фонда» и её сотрудников сняты users.read, roles.read и
  council_review.read: из-за них сотруднику Фонда открывались «Пользователи», «Роли» и
  «Мои бюллетени» члена Совета. Админ направления Фонда по-прежнему управляет своими
  сотрудниками через флаг is_direction_admin.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f5b7d9e1a3c4"
down_revision: str | Sequence[str] | None = "e4a6c8d0f2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADDED = ["fund_review.read", "fund_review.approve"]
REMOVED = ["users.read", "roles.read", "council_review.read"]


def _codes(codes: list[str]):
    return sa.bindparam("codes", value=codes, type_=postgresql.ARRAY(sa.String))


def _grant(codes: list[str]) -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes)
            WHERE r.code = 'FUND_OPERATOR'
            ON CONFLICT DO NOTHING
            """
        ).bindparams(_codes(codes))
    )
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
        ).bindparams(_codes(codes))
    )


def _revoke(codes: list[str]) -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions rp USING roles r, permissions p
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
              AND r.code = 'FUND_OPERATOR' AND p.code = ANY(:codes)
            """
        ).bindparams(_codes(codes))
    )
    op.execute(
        sa.text(
            """
            DELETE FROM user_permissions up USING users u, roles r, permissions p
            WHERE up.user_id = u.id AND u.role_id = r.id AND up.permission_id = p.id
              AND r.code = 'FUND_OPERATOR' AND p.code = ANY(:codes)
            """
        ).bindparams(_codes(codes))
    )


def upgrade() -> None:
    from src.rbac.i18n import permission_translations
    from src.rbac.permissions import PERMISSIONS

    bind = op.get_bind()
    for code in ADDED:
        name, description = PERMISSIONS[code]
        permission_id = bind.execute(
            sa.text(
                "INSERT INTO permissions (code, name, description) VALUES (:c, :n, :d) "
                "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id"
            ),
            {"c": code, "n": name, "d": description},
        ).scalar_one()
        for language, (t_name, t_description) in permission_translations(
            code, name, description
        ).items():
            bind.execute(
                sa.text(
                    "INSERT INTO permission_translations (permission_id, language, name, "
                    "description) VALUES (:id, CAST(:lang AS language), :n, :d) "
                    "ON CONFLICT (permission_id, language) DO NOTHING"
                ),
                {"id": permission_id, "lang": str(language), "n": t_name, "d": t_description},
            )
    _grant(ADDED)
    _revoke(REMOVED)


def downgrade() -> None:
    _grant(REMOVED)
    op.execute(
        sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(_codes(ADDED))
    )
