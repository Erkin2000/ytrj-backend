"""Инвестиционные продукты — в категорию «Возмещение расходов»

Revision ID: 8c0e2a4b6d9f
Revises: 3dd16afff293
Create Date: 2026-11-24

Yoshlar ventures (до 5 млрд сум) и чемпионат «Ёш тадбиркорлар» (до 1 млрд сум) переносятся из
«Инвестиции» в «Возмещение расходов» — как в списке продуктов Фонда (Qoplab berish) и как
Положение (глава 4). Продукты ищутся по русскому названию; если продукт уже в нужной категории
(перенесён вручную) — ничего не меняется. Категория «Инвестиции» остаётся: без продуктов она не
видна заявителям, удалить её можно через API Фонда.

Downgrade возвращает продукты в «Инвестиции», если эта категория есть.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c0e2a4b6d9f"
down_revision: str | Sequence[str] | None = "3dd16afff293"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRODUCTS = (
    "Yoshlar ventures: инвестиции до 5 млрд сум для выхода на внешний рынок",
    "Чемпионат «Ёш тадбиркорлар»: инвестиции до 1 млрд сум",
)
TARGET = "Возмещение расходов"
SOURCE = "Инвестиции"


def _move(to_category: str) -> None:
    conn = op.get_bind()
    category_id = conn.execute(
        sa.text(
            "SELECT category_id FROM product_category_translations "
            "WHERE language = 'ru' AND name = :n ORDER BY category_id LIMIT 1"
        ),
        {"n": to_category},
    ).scalar()
    if category_id is None:
        print(f"[investments] category «{to_category}» not found, skipped")
        return
    for name in PRODUCTS:
        moved = conn.execute(
            sa.text(
                "UPDATE products p SET category_id = :c FROM product_translations t "
                "WHERE t.product_id = p.id AND t.language = 'ru' AND t.name = :n "
                "AND p.category_id <> :c"
            ),
            {"c": category_id, "n": name},
        ).rowcount
        print(f"[investments] «{name}» -> «{to_category}»: {moved}")


def upgrade() -> None:
    _move(TARGET)


def downgrade() -> None:
    _move(SOURCE)
