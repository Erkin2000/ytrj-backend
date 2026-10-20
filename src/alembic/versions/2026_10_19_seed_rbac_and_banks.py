"""seed rbac and banks

Начальные данные: каталог прав, системные роли с пресетами разрешений,
9 банков-партнёров, последовательности номеров заявок и документов.

Revision ID: a1c3e5f7b9d1
Revises: 531b34d0736b
Create Date: 2026-10-19 14:10:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from src.rbac.permissions import PERMISSIONS, ROLE_PRESETS

revision: str = "a1c3e5f7b9d1"
down_revision: Union[str, Sequence[str], None] = "531b34d0736b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Официальные названия 9 банков уточняются заказчиком (ТЗ, п. 18.1).
# Самозанятым доступны только Microcreditbank, Xalq banki и Agrobank (ТЗ, п. 26).
ALL = ["YATT", "MCHJ", "SELF_EMPLOYED"]
IP_LLC = ["YATT", "MCHJ"]

BANKS = [
    ("microcreditbank", "Microcreditbank", "АКБ «Микрокредитбанк»", ALL, 1),
    ("xalq_banki", "Xalq banki", "АКБ «Халк банки»", ALL, 2),
    ("agrobank", "Agrobank", "АКБ «Агробанк»", ALL, 3),
    ("asakabank", "Asakabank", "АКБ «Асакабанк»", IP_LLC, 4),
    ("ipoteka_bank", "Ipoteka-bank", "АКИБ «Ипотека-банк»", IP_LLC, 5),
    ("turonbank", "Turonbank", "АКБ «Туронбанк»", IP_LLC, 6),
    ("aloqabank", "Aloqabank", "АКБ «Алокабанк»", IP_LLC, 7),
    ("qishloq_qurilish_bank", "Qishloq Qurilish Bank", "АКБ «Кишлок курилиш банк»", IP_LLC, 8),
    ("hamkorbank", "Hamkorbank", "АКБ «Хамкорбанк»", IP_LLC, 9),
]


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS application_number_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS demand_document_number_seq START 1")

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
    )
    roles = sa.table(
        "roles",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("code", sa.String),
        sa.column("description", sa.String),
        sa.column("is_superuser", sa.Boolean),
        sa.column("is_system", sa.Boolean),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )
    banks = sa.table(
        "banks",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("official_name", sa.String),
        sa.column("allowed_subject_types", sa.ARRAY(sa.String)),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )

    op.bulk_insert(
        permissions,
        [
            {"code": code, "name": name, "description": description}
            for code, (name, description) in PERMISSIONS.items()
        ],
    )

    op.bulk_insert(
        roles,
        [
            {
                "code": code,
                "name": name,
                "description": description,
                "is_superuser": is_superuser,
                "is_system": True,
            }
            for code, (name, description, is_superuser, _) in ROLE_PRESETS.items()
        ],
    )

    connection = op.get_bind()
    permission_ids = dict(connection.execute(sa.select(permissions.c.code, permissions.c.id)).all())
    role_ids = dict(connection.execute(sa.select(roles.c.code, roles.c.id)).all())

    rows = [
        {"role_id": role_ids[code], "permission_id": permission_ids[permission]}
        for code, (_, _, _, preset) in ROLE_PRESETS.items()
        for permission in preset
    ]
    if rows:
        op.bulk_insert(role_permissions, rows)

    op.bulk_insert(
        banks,
        [
            {
                "code": code,
                "name": name,
                "official_name": official,
                "allowed_subject_types": types,
                "is_active": True,
                "sort_order": order,
            }
            for code, name, official, types, order in BANKS
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM roles WHERE is_system = true")
    op.execute("DELETE FROM permissions")
    op.execute("DELETE FROM banks")
    op.execute("DROP SEQUENCE IF EXISTS application_number_seq")
    op.execute("DROP SEQUENCE IF EXISTS demand_document_number_seq")
