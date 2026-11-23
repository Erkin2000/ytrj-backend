"""Контакты организации на сайте (маркетинг)

Revision ID: b1d3f5a7c9e2
Revises: a9c1e3f5b7d0
Create Date: 2026-11-23

- таблица site_contacts: несколько контактов, у каждого телефон и/или email,
  порядок и показ на сайте;
- права contacts.* — роли «Маркетинг» и её сотрудникам.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

CODES = [f"contacts.{action}" for action in ("create", "read", "update", "delete")]
OLD_ROLE_DESCRIPTION = "Контент сайта: новости, события, FAQ, «О нас», члены Совета и руководство"
NEW_ROLE_DESCRIPTION = (
    "Контент сайта: новости, события, FAQ, «О нас», члены Совета, руководство и контакты"
)

# revision identifiers, used by Alembic.
revision: str = "b1d3f5a7c9e2"
down_revision: Union[str, Sequence[str], None] = "a9c1e3f5b7d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "site_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_site_contacts_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_site_contacts_updated_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site_contacts")),
    )
    _seed_permissions()


def _seed_permissions() -> None:
    from src.rbac.permissions import PERMISSIONS

    for code in CODES:
        name, description = PERMISSIONS.get(code, (code, ""))
        op.execute(
            sa.text(
                "INSERT INTO permissions (code, name, description) VALUES (:c, :n, :d) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(c=code, n=name, d=description)
        )
    op.execute(
        sa.text("UPDATE roles SET description = :d WHERE code = 'MARKETING'").bindparams(
            d=NEW_ROLE_DESCRIPTION
        )
    )
    bind = sa.bindparam("codes", value=CODES, type_=postgresql.ARRAY(sa.String))
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes)
            WHERE r.code = 'MARKETING'
            ON CONFLICT DO NOTHING
            """
        ).bindparams(bind)
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
        ).bindparams(bind)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'contacts.%'"))
    op.execute(
        sa.text("UPDATE roles SET description = :d WHERE code = 'MARKETING'").bindparams(
            d=OLD_ROLE_DESCRIPTION
        )
    )
    op.drop_table("site_contacts")
