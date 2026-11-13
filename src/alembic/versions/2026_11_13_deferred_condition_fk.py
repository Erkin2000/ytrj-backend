"""Условия показа: отложенная проверка внешнего ключа condition_field_id

Revision ID: a6c8e0b2d4f6
Revises: f4b6d8e0a2c4
Create Date: 2026-11-13

С ON DELETE RESTRICT удаление продукта или этапа, внутри которого одно поле
управляет показом другого, падало: ORM удаляет поля по одному, и управляющее
поле могло уйти раньше зависимого. Теперь ключ DEFERRABLE INITIALLY DEFERRED
(NO ACTION) — проверяется при коммите, когда зависимые строки уже удалены.
Удалить управляющее поле, от которого что-то остаётся зависеть, по-прежнему
нельзя: это проверяет сервис, а при коммите — сама БД.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a6c8e0b2d4f6"
down_revision: Union[str, Sequence[str], None] = "f4b6d8e0a2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("product_stages", "product_fields")


def _recreate(table: str, **options) -> None:
    name = f"fk_{table}_condition_field_id_product_fields"
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(name, table, "product_fields", ["condition_field_id"], ["id"], **options)


def upgrade() -> None:
    for table in TABLES:
        _recreate(table, deferrable=True, initially="DEFERRED")


def downgrade() -> None:
    for table in TABLES:
        _recreate(table, ondelete="RESTRICT")
