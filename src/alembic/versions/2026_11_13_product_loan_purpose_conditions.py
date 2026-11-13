"""Продукт «Строительство, ремонт и оснащение зданий, сырьё и оборудование»: цель займа и условия

Revision ID: b7d9f1a3c5e7
Revises: a6c8e0b2d4f6
Create Date: 2026-11-13

Data-миграция (docx 01_Bino_qurish_tamirlash_xomashyo_uskuna_qarz). Продукт создан через
API, поэтому его id на разных серверах разный: продукт ищется по русскому названию, этапы —
по номеру, поля — по русскому названию.

- Этап 1: поле «Срок займа, месяцев» (NUMBER) и «Цель займа» (CHECKBOX, 6 вариантов).
- Этапы 4–9 показываются только при выбранной цели; их документы становятся обязательными,
  кроме тех, что в docx начинаются с «если».
- Этап 9: вопрос «Оборудование или технологии импортируются?» (RADIO Да / Нет); импортные
  документы обязательны и видны только при «Да»; добавлена ГТД (необязательная — подаётся
  после ввоза товара).

Идемпотентна и осторожна: продукт пропускается, если он уже настроен (на этапе 1 есть
CHECKBOX), если по нему есть заявки (структура заблокирована) или если его этапы не
совпадают с ожидаемыми. Downgrade ничего не делает — данные правятся вручную через API.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d9f1a3c5e7"
down_revision: Union[str, Sequence[str], None] = "a6c8e0b2d4f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRODUCT_NAME = "Строительство, ремонт и оснащение зданий, сырьё и оборудование"
APPLICATION_FIELD_PREFIX = "Заявление в Фонд"
IMPORT_PREFIX = "При импорте:"

LOAN_TERM = ("Срок займа, месяцев", "Qarz muddati, oy", "Loan term, months")
PURPOSE = ("Цель займа", "Qarz maqsadi", "Loan purpose")
# номер этапа → вариант цели займа
PURPOSES = {
    4: ("Строительство", "Qurilish", "Construction"),
    5: ("Ремонт", "Taʼmirlash", "Repair"),
    6: ("Оснащение", "Jihozlash", "Equipping"),
    7: ("Покупка здания или сооружения", "Bino yoki inshoot sotib olish", "Purchase of a building"),
    8: (
        "Покупка сырья для производства",
        "Ishlab chiqarish uchun xomashyo sotib olish",
        "Purchase of raw materials",
    ),
    9: (
        "Покупка технологий и оборудования",
        "Texnologiya va asbob-uskuna sotib olish",
        "Purchase of technology and equipment",
    ),
}
# документы этапов 4–9, которые остаются необязательными («если…» в docx)
OPTIONAL = {
    "Кадастр или договор аренды ремонтируемого объекта (если это не место деятельности)",
    "Разрешение, если работы его требуют",
}
IMPORT_QUESTION = (
    "Оборудование или технологии импортируются?",
    "Uskuna yoki texnologiya import qilinadimi?",
    "Is the equipment or technology imported?",
)
YES = ("Да", "Ha", "Yes")
NO = ("Нет", "Yoʻq", "No")
CUSTOMS_DECLARATION = (
    "При импорте: таможенная грузовая декларация (ГТД) с актом приёма-передачи "
    "(после ввоза товара)",
    "Import qilinganda: bojxona yuk deklaratsiyasi (BYUD) nusxasi, topshirish-qabul qilish "
    "dalolatnomasi bilan (tovar olib kirilgandan soʻng)",
    "If imported: customs cargo declaration with the acceptance certificate "
    "(after the goods arrive)",
)
LANGUAGES = ("ru", "uz", "en")


def _log(message: str) -> None:
    print(f"[product loan purpose] {message}")


def _add_translations(conn, table: str, owner: str, owner_id: int, names: tuple) -> None:
    for language, name in zip(LANGUAGES, names):
        conn.execute(
            sa.text(
                f"INSERT INTO {table} ({owner}, language, name) "
                "VALUES (:owner_id, CAST(:language AS language), :name)"
            ),
            {"owner_id": owner_id, "language": language, "name": name},
        )


def _add_field(
    conn,
    stage_id: int,
    field_type: str,
    names: tuple,
    sort_order: int,
    is_required: bool = True,
    max_files: int = 1,
    condition: tuple[int, list[int]] | None = None,
) -> int:
    field_id = conn.execute(
        sa.text(
            "INSERT INTO product_fields "
            "(stage_id, field_type, is_required, max_files, sort_order, "
            " condition_field_id, condition_option_ids) "
            "VALUES (:stage_id, CAST(:field_type AS product_field_type), :is_required, "
            " :max_files, :sort_order, :condition_field_id, CAST(:option_ids AS integer[])) "
            "RETURNING id"
        ),
        {
            "stage_id": stage_id,
            "field_type": field_type,
            "is_required": is_required,
            "max_files": max_files,
            "sort_order": sort_order,
            "condition_field_id": condition[0] if condition else None,
            "option_ids": condition[1] if condition else None,
        },
    ).scalar_one()
    _add_translations(conn, "product_field_translations", "field_id", field_id, names)
    return field_id


def _add_option(conn, field_id: int, names: tuple, sort_order: int) -> int:
    option_id = conn.execute(
        sa.text(
            "INSERT INTO product_field_options (field_id, sort_order) "
            "VALUES (:field_id, :sort_order) RETURNING id"
        ),
        {"field_id": field_id, "sort_order": sort_order},
    ).scalar_one()
    _add_translations(conn, "product_field_option_translations", "option_id", option_id, names)
    return option_id


def _update_field(conn, field_id: int, **values) -> None:
    sets = []
    params = {"id": field_id}
    for key, value in values.items():
        if key == "condition_option_ids":
            sets.append(f"{key} = CAST(:{key} AS integer[])")
        else:
            sets.append(f"{key} = :{key}")
        params[key] = value
    conn.execute(sa.text(f"UPDATE product_fields SET {', '.join(sets)} WHERE id = :id"), params)


def _stage_fields(conn, stage_id: int) -> list:
    """Поля этапа по порядку: (id, field_type, is_required, ru-название)."""
    return conn.execute(
        sa.text(
            "SELECT f.id, f.field_type::text AS field_type, f.is_required, t.name "
            "FROM product_fields f "
            "JOIN product_field_translations t ON t.field_id = f.id AND t.language = 'ru' "
            "WHERE f.stage_id = :stage_id ORDER BY f.sort_order, f.id"
        ),
        {"stage_id": stage_id},
    ).all()


def _configure(conn, product_id: int) -> None:
    applications = conn.execute(
        sa.text("SELECT count(*) FROM applications WHERE product_id = :p"), {"p": product_id}
    ).scalar_one()
    if applications:
        _log(f"product {product_id}: has {applications} application(s), skipped")
        return
    stages = dict(
        conn.execute(
            sa.text("SELECT number, id FROM product_stages WHERE product_id = :p"),
            {"p": product_id},
        ).all()
    )
    if set(stages) != set(range(1, 10)):
        _log(f"product {product_id}: unexpected stages {sorted(stages)}, skipped")
        return
    stage1 = _stage_fields(conn, stages[1])
    if any(f.field_type == "CHECKBOX" for f in stage1):
        _log(f"product {product_id}: already configured, skipped")
        return

    # ---- этап 1: сумма (0), срок (1), цель займа (2), заявление (3) ----
    for field in stage1:
        if field.name.startswith(APPLICATION_FIELD_PREFIX):
            _update_field(conn, field.id, sort_order=3)
    _add_field(conn, stages[1], "NUMBER", LOAN_TERM, sort_order=1)
    purpose_id = _add_field(conn, stages[1], "CHECKBOX", PURPOSE, sort_order=2)
    option_ids = {
        number: _add_option(conn, purpose_id, names, index)
        for index, (number, names) in enumerate(PURPOSES.items())
    }

    # ---- этапы 4–9: условие показа и обязательность документов ----
    import_fields = []
    for number, option_id in option_ids.items():
        conn.execute(
            sa.text(
                "UPDATE product_stages SET condition_field_id = :field_id, "
                "condition_option_ids = CAST(:option_ids AS integer[]) WHERE id = :id"
            ),
            {"field_id": purpose_id, "option_ids": [option_id], "id": stages[number]},
        )
        for field in _stage_fields(conn, stages[number]):
            if field.name.startswith(IMPORT_PREFIX):
                import_fields.append(field)
                continue
            required = field.name not in OPTIONAL
            if field.is_required != required:
                _update_field(conn, field.id, is_required=required)

    # ---- этап 9: вопрос об импорте и импортные документы по условию ----
    base = [f for f in _stage_fields(conn, stages[9]) if not f.name.startswith(IMPORT_PREFIX)]
    for index, field in enumerate(base):
        _update_field(conn, field.id, sort_order=index)
    question_order = len(base)
    question_id = _add_field(conn, stages[9], "RADIO", IMPORT_QUESTION, sort_order=question_order)
    yes_id = _add_option(conn, question_id, YES, 0)
    _add_option(conn, question_id, NO, 1)
    for index, field in enumerate(import_fields, start=question_order + 1):
        _update_field(
            conn,
            field.id,
            is_required=True,
            sort_order=index,
            condition_field_id=question_id,
            condition_option_ids=[yes_id],
        )
    _add_field(
        conn,
        stages[9],
        "FILE",
        CUSTOMS_DECLARATION,
        sort_order=question_order + 1 + len(import_fields),
        is_required=False,
        max_files=2,
        condition=(question_id, [yes_id]),
    )
    conn.execute(sa.text("UPDATE products SET updated_at = now() WHERE id = :p"), {"p": product_id})
    _log(f"product {product_id}: configured")


def upgrade() -> None:
    conn = op.get_bind()
    product_ids = (
        conn.execute(
            sa.text(
                "SELECT p.id FROM products p "
                "JOIN product_translations t ON t.product_id = p.id AND t.language = 'ru' "
                "WHERE t.name = :name ORDER BY p.id"
            ),
            {"name": PRODUCT_NAME},
        )
        .scalars()
        .all()
    )
    if not product_ids:
        _log("product not found, nothing to do")
    for product_id in product_ids:
        _configure(conn, product_id)


def downgrade() -> None:
    # Данные продукта правятся через API Фонда; откатывать их миграцией небезопасно.
    pass
