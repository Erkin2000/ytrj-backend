"""Бюллетени Совета: подпись ЭЦП (E-IMZO), проверка по QR

Revision ID: d9f1b3c5e7a9
Revises: c8e0a2b4d6f8
Create Date: 2026-11-18

- таблицы bulletins и bulletin_signatures, типы bulletin_status / bulletin_decision;
- права bulletins.create/read/update/delete/approve — роли «Оператор Фонда» и
  существующим операторам Фонда (у сотрудников права выдаются поштучно).

Решение Совета по заявке теперь принимается только подписью бюллетеня, связанного
с заявкой; данные application_council_assignments не меняются.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d9f1b3c5e7a9"
down_revision: Union[str, Sequence[str], None] = "c8e0a2b4d6f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = {
    "bulletins.create": ("Создание бюллетеней", "Новый бюллетень для членов Совета"),
    "bulletins.read": ("Просмотр бюллетеней", "Все бюллетени и статус подписания"),
    "bulletins.update": ("Изменение бюллетеней", "Данные, файл и срок подписания бюллетеня"),
    "bulletins.delete": ("Удаление бюллетеней", "Удаление неотправленного бюллетеня"),
    "bulletins.approve": ("Отправка бюллетеней", "Отправка членам Совета и аннулирование"),
}

bulletin_status = postgresql.ENUM(
    "PENDING",
    "PUBLISHED",
    "PARTIALLY_SIGNED",
    "COMPLETED",
    "CANCELLED",
    name="bulletin_status",
    create_type=False,
)
bulletin_decision = postgresql.ENUM("AGREE", "AGAINST", name="bulletin_decision", create_type=False)


def upgrade() -> None:
    bulletin_status.create(op.get_bind(), checkfirst=True)
    bulletin_decision.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "bulletins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=32), nullable=True),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("status", bulletin_status, nullable=False),
        sa.Column("send_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_content_type", sa.String(length=128), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("published_by_id", sa.Integer(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_id", sa.Integer(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_bulletins_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_bulletins_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["published_by_id"],
            ["users.id"],
            name=op.f("fk_bulletins_published_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by_id"],
            ["users.id"],
            name=op.f("fk_bulletins_cancelled_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bulletins")),
        sa.UniqueConstraint("number", name=op.f("uq_bulletins_number")),
        sa.UniqueConstraint("public_id", name=op.f("uq_bulletins_public_id")),
    )
    op.create_index(op.f("ix_bulletins_application_id"), "bulletins", ["application_id"])
    op.create_index(op.f("ix_bulletins_status"), "bulletins", ["status"])
    op.create_index(op.f("ix_bulletins_send_at"), "bulletins", ["send_at"])

    op.create_table(
        "bulletin_signatures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bulletin_id", sa.Integer(), nullable=False),
        sa.Column("council_member_id", sa.Integer(), nullable=True),
        sa.Column("member_full_name", sa.String(length=255), nullable=True),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision", bulletin_decision, nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cert_pinfl", sa.String(length=14), nullable=True),
        sa.Column("cert_full_name", sa.String(length=255), nullable=True),
        sa.Column("cert_serial_number", sa.String(length=128), nullable=True),
        sa.Column("cert_valid_from", sa.String(length=32), nullable=True),
        sa.Column("cert_valid_to", sa.String(length=32), nullable=True),
        sa.Column("cert_tin", sa.String(length=16), nullable=True),
        sa.Column("eimzo_request_id", sa.String(length=128), nullable=True),
        sa.Column("document_hash", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["bulletin_id"],
            ["bulletins.id"],
            name=op.f("fk_bulletin_signatures_bulletin_id_bulletins"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["council_member_id"],
            ["users.id"],
            name=op.f("fk_bulletin_signatures_council_member_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bulletin_signatures")),
        sa.UniqueConstraint(
            "bulletin_id", "council_member_id", name="uq_bulletin_signature_member"
        ),
    )
    op.create_index(
        op.f("ix_bulletin_signatures_bulletin_id"), "bulletin_signatures", ["bulletin_id"]
    )
    op.create_index(
        op.f("ix_bulletin_signatures_council_member_id"),
        "bulletin_signatures",
        ["council_member_id"],
    )

    for code, (name, description) in PERMISSIONS.items():
        op.execute(
            sa.text(
                "INSERT INTO permissions (code, name, description) VALUES (:c, :n, :d) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(c=code, n=name, d=description)
        )
    codes = list(PERMISSIONS)
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes)
            WHERE r.code = 'FUND_OPERATOR'
            ON CONFLICT DO NOTHING
            """
        ).bindparams(sa.bindparam("codes", value=codes, type_=postgresql.ARRAY(sa.String)))
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
        ).bindparams(sa.bindparam("codes", value=codes, type_=postgresql.ARRAY(sa.String)))
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'bulletins.%'"))
    op.drop_index(op.f("ix_bulletin_signatures_council_member_id"), table_name="bulletin_signatures")
    op.drop_index(op.f("ix_bulletin_signatures_bulletin_id"), table_name="bulletin_signatures")
    op.drop_table("bulletin_signatures")
    op.drop_index(op.f("ix_bulletins_send_at"), table_name="bulletins")
    op.drop_index(op.f("ix_bulletins_status"), table_name="bulletins")
    op.drop_index(op.f("ix_bulletins_application_id"), table_name="bulletins")
    op.drop_table("bulletins")
    bulletin_decision.drop(op.get_bind(), checkfirst=True)
    bulletin_status.drop(op.get_bind(), checkfirst=True)
