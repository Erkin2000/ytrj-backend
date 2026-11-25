"""Сид реестра без персональных данных: заполняет программы, в которых ещё нет ни одного проекта.

Тот же файл, что и у миграции `2026_11_24_registry_seed` (ПҚ-60, ПҚ-400, «Кўмак», обучение и
инкубация на 20.11.2026 — 3 168 проектов). Миграция выполняется один раз; эта функция —
при каждом старте контейнера (`docker/entrypoint.sh`), поэтому реестр снова заполнится, если на
базе он оказался пустым: миграция прошла до появления программы, проекты удалили и т.п.

Программа, в которой уже есть проекты (полный импорт Excel, сид, ручные), не трогается.
Строки сида — `source = IMPORT` с `extra.seed`: следующий импорт Excel программы заменит их.
"""

import gzip
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import exists, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.models.user_model import Gender
from src.registry.enums import Decision, ProjectStatus, RegistrySubjectType, Sector, Source
from src.registry.models.registry_model import RegistryProgramORM, RegistryProjectORM

SEED = "2026-11-20"
DATA_FILE = (
    Path(__file__).resolve().parent.parent / "alembic" / "seed_data" / "registry_2026_11_20.json.gz"
)
DATE_COLUMNS = {"bank_letter_date", "application_date", "council_date"}
ENUM_COLUMNS = {
    "subject_type": RegistrySubjectType,
    "gender": Gender,
    "sector": Sector,
    "decision": Decision,
    "status": ProjectStatus,
}
# Несколько контейнеров стартуют одновременно: сидит только один, остальные ждут и видят данные.
ADVISORY_LOCK_KEY = 7_340_112_026


def load_seed(path: Path = DATA_FILE) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def _row(code: str, program_id: int, columns: list[str], values: list) -> dict:
    row = dict(zip(columns, values, strict=True))
    for name in DATE_COLUMNS:
        if row.get(name):
            row[name] = date.fromisoformat(row[name])
    for name, enum in ENUM_COLUMNS.items():
        if row.get(name) is not None:
            row[name] = enum(row[name])
    return {
        **row,
        "program_id": program_id,
        "source": Source.IMPORT,
        "applicant_name": f"{code} №{row['number']}",
        "extra": {"seed": SEED},
    }


async def seed_empty_programs(session: AsyncSession, data: dict | None = None) -> dict[str, int]:
    """Заполняет пустые программы из сида; возвращает {код программы: добавлено проектов}.

    Коммит — на вызывающем. Программы, которых нет в базе, пропускаются.
    """
    data = data if data is not None else load_seed()
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADVISORY_LOCK_KEY})

    seeded: dict[str, int] = {}
    for code, rows in data["programs"].items():
        program_id = await session.scalar(
            select(RegistryProgramORM.id).where(RegistryProgramORM.code == code)
        )
        if program_id is None or not rows:
            continue
        has_projects = await session.scalar(
            select(exists().where(RegistryProjectORM.program_id == program_id))
        )
        if has_projects:
            continue

        await session.execute(
            insert(RegistryProjectORM),
            [_row(code, program_id, data["columns"], values) for values in rows],
        )
        await session.execute(
            update(RegistryProgramORM)
            .where(RegistryProgramORM.id == program_id)
            .values(
                last_import_file=f"seed {SEED} (без персональных данных)",
                last_import_at=datetime(2026, 11, 20, tzinfo=UTC),
            )
        )
        seeded[code] = len(rows)
    return seeded
