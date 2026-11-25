"""Импорт Excel отдела в реестр с диска сервера (без HTTP):

    uv run python -m src.registry.cli import PQ60 "ЛОЙИҲАЛАР_19_ноябр_NEW_60_сохалар.xlsx"
    uv run python -m src.registry.cli import KOMAK "Кўмак chiqarish yuklash 16.11.2026.xlsx"

Первый аргумент — код программы (`GET /registry/programs`). Как и `POST /registry/import`,
заменяет все ранее импортированные проекты программы.

    uv run python -m src.registry.cli seed

Заполняет сидом без персональных данных программы, в которых ещё нет проектов (идемпотентно;
запускается `docker/entrypoint.sh` при каждом старте).
"""

import argparse
import asyncio
import sys
from pathlib import Path

import src.models  # noqa: F401  (регистрирует все ORM-модели)
from src.common.responses.exceptions import ApiException
from src.database import async_session_maker_null_pool
from src.registry.seed import seed_empty_programs
from src.registry.services.registry_service import RegistryImportService
from src.utils.db_manager import DBManager


async def import_file(program_code: str, path: Path) -> None:
    async with DBManager(session_factory=async_session_maker_null_pool) as db:
        program = await db.registry.get_program_by_code(program_code)
        if program is None:
            sys.exit(f"Программа {program_code} не найдена")
        if program.import_template is None:
            sys.exit(f"У программы {program_code} нет шаблона импорта")
        try:
            result = await RegistryImportService(db).import_bytes(
                None, program, path.read_bytes(), path.name
            )
        except ApiException as exc:
            sys.exit(f"Ошибка: {exc.message}")
    print(
        f"{program_code}: лист «{result.sheet}», загружено {result.imported}, "
        f"заменено {result.replaced}, пропущено {result.skipped}"
    )
    if result.unknown_regions:
        print("  не распознаны регионы:", ", ".join(result.unknown_regions))
    if result.unknown_banks:
        print("  не распознаны банки:", ", ".join(result.unknown_banks))


async def seed() -> None:
    async with async_session_maker_null_pool() as session:
        seeded = await seed_empty_programs(session)
        await session.commit()
    if seeded:
        for code, count in seeded.items():
            print(f"{code}: добавлено из сида {count}")
    else:
        print("Реестр не пуст — сид не нужен")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m src.registry.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("import", help="загрузить Excel программы в реестр")
    cmd.add_argument("program", help="код программы: PQ60, PQ400, KOMAK, INCUBATION")
    cmd.add_argument("file", type=Path)
    sub.add_parser("seed", help="заполнить пустые программы сидом без персональных данных")
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(seed())
        return
    if not args.file.is_file():
        sys.exit(f"Файл не найден: {args.file}")
    asyncio.run(import_file(args.program, args.file))


if __name__ == "__main__":
    main()
