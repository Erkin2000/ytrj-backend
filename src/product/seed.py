"""Заводит категории продуктов и их продукты из перечней документов (папка products/):
«Займы и ссуды» (01–07, src/product/seed_data.py) и «Возмещение расходов»
(08–12, 15, src/product/seed_data_reimbursement.py).

    python -m src.product.seed

Продукты создаются черновиками без банков: Фонд добавляет банки и публикует их
(PATCH /fund/products/{id}, POST /fund/products/{id}/publish). Повторный запуск
ничего не дублирует: категория и продукты ищутся по русскому названию.
"""

import asyncio

from sqlalchemy import select

import src.models  # noqa: F401  (регистрирует все ORM-модели)
from src.application.enums import SubjectType
from src.database import async_session_maker_null_pool
from src.product.enums import LANGUAGES, FieldType, ProductStatus
from src.product.models.product_model import (
    ProductCategoryORM,
    ProductCategoryTranslationORM,
    ProductFieldORM,
    ProductFieldTranslationORM,
    ProductORM,
    ProductStageORM,
    ProductStageTranslationORM,
    ProductTranslationORM,
)
from src.product.seed_data import CATEGORY, DOCS, PRODUCTS
from src.product.seed_data_reimbursement import REIMBURSEMENT_CATEGORY, REIMBURSEMENT_PRODUCTS

# Категории и их продукты в порядке заведения.
CATEGORIES: list[tuple[dict, list[dict]]] = [
    (CATEGORY, PRODUCTS),
    (REIMBURSEMENT_CATEGORY, REIMBURSEMENT_PRODUCTS),
]


def _names(values, orm_class, descriptions=None) -> list:
    rows = []
    for index, language in enumerate(LANGUAGES):
        name = values[index]
        assert 2 <= len(name) <= 255, name
        extra = {"description": descriptions[index]} if descriptions else {}
        rows.append(orm_class(language=language, name=name, **extra))
    return rows


def _field(spec, sort_order: int) -> ProductFieldORM:
    label, field_type, required, max_files = spec
    names = DOCS[label] if isinstance(label, str) else label
    field_type = FieldType(field_type)
    return ProductFieldORM(
        field_type=field_type,
        is_required=required,
        max_files=max_files if field_type in (FieldType.PHOTO, FieldType.FILE) else 1,
        sort_order=sort_order,
        translations=_names(names, ProductFieldTranslationORM),
    )


def _product(data: dict, category_id: int) -> ProductORM:
    names, descriptions = data["translations"]
    for value in data["subject_types"]:
        SubjectType(value)
    return ProductORM(
        category_id=category_id,
        status=ProductStatus.DRAFT,
        uses_bank=data.get("uses_bank", True),
        allowed_subject_types=list(data["subject_types"]),
        translations=_names(names, ProductTranslationORM, descriptions),
        banks=[],
        stages=[
            ProductStageORM(
                number=number,
                translations=_names(stage_names, ProductStageTranslationORM),
                fields=[_field(spec, order) for order, spec in enumerate(fields)],
            )
            for number, (stage_names, fields) in enumerate(data["stages"], start=1)
        ],
    )


async def _find_category(session, data: dict) -> ProductCategoryORM | None:
    ru_name = data["translations"][0][0]
    stmt = (
        select(ProductCategoryORM)
        .join(ProductCategoryTranslationORM)
        .where(
            ProductCategoryTranslationORM.language == "ru",
            ProductCategoryTranslationORM.name == ru_name,
        )
    )
    return await session.scalar(stmt)


async def _product_exists(session, category_id: int, ru_name: str) -> ProductORM | None:
    stmt = (
        select(ProductORM)
        .join(ProductTranslationORM)
        .where(
            ProductORM.category_id == category_id,
            ProductTranslationORM.language == "ru",
            ProductTranslationORM.name == ru_name,
        )
    )
    return await session.scalar(stmt)


async def _seed_category(session, category_data: dict, products: list[dict]) -> None:
    category = await _find_category(session, category_data)
    names, descriptions = category_data["translations"]
    if category is None:
        category = ProductCategoryORM(
            is_active=True,
            sort_order=category_data["sort_order"],
            translations=_names(names, ProductCategoryTranslationORM, descriptions),
        )
        session.add(category)
        await session.flush()
        print(f"Категория создана: #{category.id} {names[0]}")
    else:
        print(f"Категория уже есть: #{category.id} {names[0]}")

    for data in products:
        ru_name = data["translations"][0][0]
        existing = await _product_exists(session, category.id, ru_name)
        if existing is not None:
            uses_bank = data.get("uses_bank", True)
            if existing.uses_bank != uses_bank:
                existing.uses_bank = uses_bank
                if not uses_bank:
                    existing.banks = []
                print(f"  обновлён #{existing.id} (uses_bank={uses_bank}): {ru_name}")
            else:
                print(f"  пропущен (уже есть): {ru_name}")
            continue
        product = _product(data, category.id)
        session.add(product)
        await session.flush()
        fields = sum(len(stage.fields) for stage in product.stages)
        print(f"  создан #{product.id}: {ru_name} — этапов {len(product.stages)}, полей {fields}")


async def seed() -> None:
    async with async_session_maker_null_pool() as session:
        for category_data, products in CATEGORIES:
            await _seed_category(session, category_data, products)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
