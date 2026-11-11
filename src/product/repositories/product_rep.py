from datetime import date

from sqlalchemy import Select, any_, func, or_, select
from sqlalchemy.orm import selectinload

from src.application.models.application_model import ApplicationORM
from src.product.enums import ProductStatus
from src.product.mappers import ProductDataMapper
from src.product.models.product_model import (
    ProductCategoryORM,
    ProductFieldORM,
    ProductORM,
    ProductStageORM,
    ProductTranslationORM,
)
from src.product.schemas.product_schema import ProductFilterDTO
from src.utils.base_rep.base_rep import BaseRepository


class ProductRepository(BaseRepository):
    model = ProductORM
    mapper = ProductDataMapper

    async def get_orm(self, product_id: int) -> ProductORM | None:
        """Продукт с банками, этапами и полями; populate_existing перечитывает
        связи после изменений в этой же сессии."""
        stmt = (
            select(ProductORM)
            .where(ProductORM.id == product_id)
            .options(
                selectinload(ProductORM.translations),
                selectinload(ProductORM.category).selectinload(ProductCategoryORM.translations),
                selectinload(ProductORM.banks),
                selectinload(ProductORM.stages).selectinload(ProductStageORM.translations),
                selectinload(ProductORM.stages)
                .selectinload(ProductStageORM.fields)
                .selectinload(ProductFieldORM.translations),
            )
            .execution_options(populate_existing=True)
        )
        return await self.session.scalar(stmt)

    async def applications_count(self, product_id: int) -> int:
        stmt = select(func.count()).where(ApplicationORM.product_id == product_id)
        return await self.session.scalar(stmt) or 0

    async def get_page(
        self, filters: ProductFilterDTO, page: int | None, per_page: int | None
    ) -> dict:
        stmt = select(self.model).order_by(self.model.id.desc())
        if filters.status is not None:
            stmt = stmt.where(self.model.status == filters.status)
        if filters.category_id is not None:
            stmt = stmt.where(self.model.category_id == filters.category_id)
        if filters.search:
            pattern = f"%{filters.search}%"
            stmt = stmt.where(
                self.model.translations.any(ProductTranslationORM.name.ilike(pattern))
            )
        return await self.paginate(stmt, page, per_page)

    @staticmethod
    def _available_stmt(today: date) -> Select:
        return (
            select(ProductORM)
            .join(ProductCategoryORM)
            .where(
                ProductCategoryORM.is_active.is_(True),
                ProductORM.status == ProductStatus.PUBLISHED,
                or_(ProductORM.accept_from.is_(None), ProductORM.accept_from <= today),
                or_(ProductORM.accept_to.is_(None), ProductORM.accept_to >= today),
            )
        )

    async def get_available(
        self, today: date, subject_type: str | None, category_id: int | None = None
    ) -> list[ProductORM]:
        stmt = self._available_stmt(today).order_by(ProductORM.id.desc())
        if category_id is not None:
            stmt = stmt.where(ProductORM.category_id == category_id)
        if subject_type:
            stmt = stmt.where(subject_type == any_(ProductORM.allowed_subject_types))
        return list((await self.session.scalars(stmt)).all())

    async def get_stage(self, product_id: int, stage_id: int) -> ProductStageORM | None:
        stmt = select(ProductStageORM).where(
            ProductStageORM.id == stage_id, ProductStageORM.product_id == product_id
        )
        return await self.session.scalar(stmt)

    async def get_field(self, product_id: int, field_id: int) -> ProductFieldORM | None:
        stmt = (
            select(ProductFieldORM)
            .join(ProductStageORM, ProductStageORM.id == ProductFieldORM.stage_id)
            .where(ProductFieldORM.id == field_id, ProductStageORM.product_id == product_id)
        )
        return await self.session.scalar(stmt)

    async def stage_number_taken(
        self, product_id: int, number: int, exclude_stage_id: int | None = None
    ) -> bool:
        stmt = select(func.count()).where(
            ProductStageORM.product_id == product_id, ProductStageORM.number == number
        )
        if exclude_stage_id is not None:
            stmt = stmt.where(ProductStageORM.id != exclude_stage_id)
        return bool(await self.session.scalar(stmt))

    # ---------- категории ----------

    async def get_category(self, category_id: int) -> ProductCategoryORM | None:
        stmt = (
            select(ProductCategoryORM)
            .where(ProductCategoryORM.id == category_id)
            .options(selectinload(ProductCategoryORM.translations))
            .execution_options(populate_existing=True)
        )
        return await self.session.scalar(stmt)

    async def get_categories(self, only_active: bool = False) -> list[ProductCategoryORM]:
        stmt = select(ProductCategoryORM).order_by(
            ProductCategoryORM.sort_order, ProductCategoryORM.id
        )
        if only_active:
            stmt = stmt.where(ProductCategoryORM.is_active.is_(True))
        return list((await self.session.scalars(stmt)).all())

    async def products_per_category(self) -> dict[int, int]:
        stmt = select(ProductORM.category_id, func.count()).group_by(ProductORM.category_id)
        return dict((await self.session.execute(stmt)).all())

    async def available_per_category(self, today: date, subject_type: str | None) -> dict[int, int]:
        stmt = (
            self._available_stmt(today)
            .with_only_columns(ProductORM.category_id, func.count())
            .group_by(ProductORM.category_id)
        )
        if subject_type:
            stmt = stmt.where(subject_type == any_(ProductORM.allowed_subject_types))
        return dict((await self.session.execute(stmt)).all())
