"""Сид реестра проектов из Excel отдела на 20.11.2026 — без персональных данных

Revision ID: a6c8e0f2b4d5
Revises: f5b7d9e1a3c4
Create Date: 2026-11-24

Данные — `src/alembic/seed_data/registry_2026_11_20.json.gz`, собраны из файлов ПҚ-60, ПҚ-400,
«Кўмак» и «Oʻquv kurs inkubatsiya» (3 168 проектов). Чтобы файл можно было хранить в git,
оставлены только поля для аналитики: суммы, регион, туман, банк, отрасль, направление, пол,
возраст, тип субъекта, даты, решение, статус, вид обеспечения. Имени нет (`applicant_name` —
«<код программы> №N»), нет ПИНФЛ / СТИР, телефонов, паспортов, махалли, названий организаций
и свободного текста.

- Программа заполняется, только если в ней ещё нет проектов: на базе, куда уже загружен Excel
  (с полными данными), миграция ничего не меняет.
- Строки сида — `source = IMPORT`: следующий импорт Excel программы
  (`POST /registry/import` или `python -m src.registry.cli import`) заменит их полными данными.
- `extra.seed` помечает строки сида; downgrade удаляет только их.
"""

import gzip
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a6c8e0f2b4d5"
down_revision: str | Sequence[str] | None = "f5b7d9e1a3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED = "2026-11-20"
DATA_FILE = Path(__file__).resolve().parent.parent / "seed_data" / "registry_2026_11_20.json.gz"
DATE_COLUMNS = {"bank_letter_date", "application_date", "council_date"}


def _enum(name: str):
    return postgresql.ENUM(name=name, create_type=False)


projects = sa.table(
    "registry_projects",
    sa.column("program_id", sa.Integer),
    sa.column("source", _enum("registry_source")),
    sa.column("number", sa.Integer),
    sa.column("applicant_name", sa.String),
    sa.column("subject_type", _enum("registry_subject_type")),
    sa.column("gender", _enum("registry_gender")),
    sa.column("age", sa.Integer),
    sa.column("region", sa.String),
    sa.column("district", sa.String),
    sa.column("district_key", sa.String),
    sa.column("sector", _enum("registry_sector")),
    sa.column("direction", sa.String),
    sa.column("jobs", sa.Integer),
    sa.column("project_cost", sa.Numeric),
    sa.column("requested_amount", sa.Numeric),
    sa.column("allocated_amount", sa.Numeric),
    sa.column("credit_amount", sa.Numeric),
    sa.column("term_months", sa.Integer),
    sa.column("collateral", sa.String),
    sa.column("bank", sa.String),
    sa.column("bank_letter_date", sa.Date),
    sa.column("application_date", sa.Date),
    sa.column("decision", _enum("registry_decision")),
    sa.column("council_date", sa.Date),
    sa.column("status", _enum("registry_project_status")),
    sa.column("extra", postgresql.JSONB),
)


def upgrade() -> None:
    with gzip.open(DATA_FILE, "rt", encoding="utf-8") as f:
        data = json.load(f)
    columns = data["columns"]
    bind = op.get_bind()

    for code, rows in data["programs"].items():
        program_id = bind.execute(
            sa.text("SELECT id FROM registry_programs WHERE code = :code"), {"code": code}
        ).scalar()
        if program_id is None:
            continue
        has_projects = bind.execute(
            sa.text("SELECT 1 FROM registry_projects WHERE program_id = :id LIMIT 1"),
            {"id": program_id},
        ).scalar()
        if has_projects:
            continue

        items = []
        for values in rows:
            row = dict(zip(columns, values, strict=True))
            for name in DATE_COLUMNS:
                if row.get(name):
                    row[name] = date.fromisoformat(row[name])
            items.append(
                {
                    **row,
                    "program_id": program_id,
                    "source": "IMPORT",
                    "applicant_name": f"{code} №{row['number']}",
                    "extra": {"seed": SEED},
                }
            )
        op.bulk_insert(projects, items)
        bind.execute(
            sa.text(
                "UPDATE registry_programs SET last_import_file = :file, last_import_at = :at "
                "WHERE id = :id"
            ),
            {
                "file": f"seed {SEED} (без персональных данных)",
                "at": datetime(2026, 11, 20, tzinfo=UTC),
                "id": program_id,
            },
        )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM registry_projects WHERE extra ->> 'seed' = :seed").bindparams(
            seed=SEED
        )
    )
