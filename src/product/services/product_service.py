"""Продукты Фонда: ведение (оператор Фонда) и каталог для заявителя."""

from datetime import date

from sqlalchemy import select

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import SubjectType
from src.application.models.bank_model import BankORM
from src.application.services.base import ApplicationBaseService
from src.common.responses.exceptions import (
    BankNotFoundException,
    FieldInUseByConditionException,
    FieldOptionsException,
    ProductCategoryInactiveException,
    ProductCategoryInUseException,
    ProductCategoryNotFoundException,
    ProductFieldNotFoundException,
    ProductFieldOptionNotFoundException,
    ProductInUseException,
    ProductLockedException,
    ProductNotFoundException,
    ProductNotReadyException,
    ProductStageNotFoundException,
    ProductStatusException,
    StageNumberTakenException,
)
from src.product.conditions import (
    dependents,
    option_dependents,
    precheck_condition,
    validate_conditions,
)
from src.product.enums import CHOICE_FIELD_TYPES, FILE_FIELD_TYPES, ProductStatus
from src.product.mappers import ProductDataMapper, category_dto
from src.product.models.product_model import (
    ProductCategoryORM,
    ProductCategoryTranslationORM,
    ProductFieldOptionORM,
    ProductFieldOptionTranslationORM,
    ProductFieldORM,
    ProductFieldTranslationORM,
    ProductORM,
    ProductStageORM,
    ProductStageTranslationORM,
    ProductTranslationORM,
)
from src.product.schemas.product_schema import (
    MIN_OPTIONS,
    CategoryCreateDTO,
    CategoryDTO,
    CategoryUpdateDTO,
    FieldCreateDTO,
    FieldUpdateDTO,
    OptionCreateDTO,
    OptionUpdateDTO,
    ProductCreateDTO,
    ProductDetailDTO,
    ProductFilterDTO,
    ProductListItemDTO,
    ProductUpdateDTO,
    StageCreateDTO,
    StageUpdateDTO,
    VisibleWhenDTO,
)
from src.utils.base_service import BaseService


def is_available(product: ProductORM, subject_type: SubjectType | None = None) -> bool:
    """Продукт принимает заявки: опубликован, его категория активна, сегодня в
    сроках приёма и, если указан тип субъекта, рассчитан на него."""
    today = date.today()
    if product.status != ProductStatus.PUBLISHED or not product.category.is_active:
        return False
    if product.accept_from is not None and today < product.accept_from:
        return False
    if product.accept_to is not None and today > product.accept_to:
        return False
    return subject_type is None or subject_type in product.allowed_subject_types


def apply_translations(current: list, items: list, orm_class: type) -> None:
    """Обновляет переводы по языку на месте: схема уже проверила, что переданы
    ровно ru, uz, en. Строки не пересоздаются — уникальность (объект, язык) не нарушается."""
    by_language = {t.language: t for t in current}
    for item in items:
        values = item.model_dump(exclude={"language"})
        existing = by_language.get(item.language)
        if existing is None:
            current.append(orm_class(language=item.language, **values))
        else:
            for key, value in values.items():
                setattr(existing, key, value)


class ProductService(BaseService):
    # ---------- каталог для заявителя ----------

    async def get_available(
        self, subject_type: SubjectType | None, category_id: int | None = None
    ) -> list[ProductListItemDTO]:
        products = await self.db.product.get_available(date.today(), subject_type, category_id)
        return [ProductDataMapper.map_to_applicant(p) for p in products]

    async def get_available_categories(self, subject_type: SubjectType | None) -> list[CategoryDTO]:
        """Активные категории, в которых сейчас есть продукты для подачи заявки."""
        counts = await self.db.product.available_per_category(date.today(), subject_type)
        categories = await self.db.product.get_categories(only_active=True)
        return [category_dto(c, counts[c.id]) for c in categories if counts.get(c.id)]

    # ---------- категории (Фонд) ----------

    async def get_categories(self) -> list[CategoryDTO]:
        """Публичный справочник: все категории, включая неактивные."""
        counts = await self.db.product.products_per_category()
        categories = await self.db.product.get_categories()
        return [category_dto(c, counts.get(c.id, 0)) for c in categories]

    async def get_category(self, category_id: int) -> CategoryDTO:
        return await self._category_detail(category_id)

    async def create_category(self, user: CurrentUserDTO, data: CategoryCreateDTO) -> CategoryDTO:
        ApplicationBaseService.assert_global_scope(user)
        category = ProductCategoryORM(is_active=data.is_active, sort_order=data.sort_order)
        apply_translations(category.translations, data.translations, ProductCategoryTranslationORM)
        self.db.session.add(category)
        await self.db.commit()
        return await self._category_detail(category.id)

    async def update_category(
        self, user: CurrentUserDTO, category_id: int, data: CategoryUpdateDTO
    ) -> CategoryDTO:
        ApplicationBaseService.assert_global_scope(user)
        category = await self._category(category_id)
        if data.translations is not None:
            apply_translations(
                category.translations, data.translations, ProductCategoryTranslationORM
            )
        if data.is_active is not None:
            category.is_active = data.is_active
        if data.sort_order is not None:
            category.sort_order = data.sort_order
        await self.db.commit()
        return await self._category_detail(category_id)

    async def delete_category(self, user: CurrentUserDTO, category_id: int) -> None:
        ApplicationBaseService.assert_global_scope(user)
        category = await self._category(category_id)
        if (await self.db.product.products_per_category()).get(category_id):
            raise ProductCategoryInUseException()
        await self.db.session.delete(category)
        await self.db.commit()

    async def get_available_detail(self, product_id: int) -> ProductDetailDTO:
        product = await self.db.product.get_orm(product_id)
        if product is None or not is_available(product):
            raise ProductNotFoundException()
        return ProductDataMapper.map_to_detail(product, for_applicant=True)

    # ---------- ведение (Фонд) ----------

    async def get_page(
        self, filters: ProductFilterDTO, page: int | None, per_page: int | None
    ) -> dict:
        """Публичный список всех продуктов (включая черновики и снятые с публикации)."""
        return await self.db.product.get_page(filters, page, per_page)

    async def get_detail(self, product_id: int) -> ProductDetailDTO:
        """Публичная карточка любого продукта (в том числе черновика)."""
        return await self._detail(product_id)

    async def create(self, user: CurrentUserDTO, data: ProductCreateDTO) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        await self._active_category(data.category_id)
        product = ProductORM(
            category_id=data.category_id,
            allowed_subject_types=[s.value for s in data.allowed_subject_types],
            accept_from=data.accept_from,
            accept_to=data.accept_to,
            status=ProductStatus.DRAFT,
            created_by_id=user.id,
        )
        apply_translations(product.translations, data.translations, ProductTranslationORM)
        product.banks = await self._banks(data.bank_ids)
        self.db.session.add(product)
        await self.db.commit()
        return await self._detail(product.id)

    async def update(
        self, user: CurrentUserDTO, product_id: int, data: ProductUpdateDTO
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get(product_id)
        changes = data.model_dump(exclude_unset=True)

        category_id = changes.pop("category_id", None)
        if category_id is not None and category_id != product.category_id:
            await self._active_category(category_id)
            product.category_id = category_id
        bank_ids = changes.pop("bank_ids", None)
        if bank_ids is not None:
            product.banks = await self._banks(bank_ids)
        if changes.pop("translations", None) is not None:
            apply_translations(product.translations, data.translations, ProductTranslationORM)
        if changes.get("allowed_subject_types") is not None:
            changes["allowed_subject_types"] = [s.value for s in data.allowed_subject_types]
        elif "allowed_subject_types" in changes:
            changes.pop("allowed_subject_types")
        for key, value in changes.items():
            setattr(product, key, value)

        if product.accept_from and product.accept_to and product.accept_from > product.accept_to:
            raise ProductStatusException("accept_from cannot be later than accept_to")

        await self.db.commit()
        return await self._detail(product_id)

    async def delete(self, user: CurrentUserDTO, product_id: int) -> None:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get(product_id)
        if await self.db.product.applications_count(product_id):
            raise ProductInUseException()
        await self.db.session.delete(product)
        await self.db.commit()

    async def publish(self, user: CurrentUserDTO, product_id: int) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get(product_id)
        if product.status == ProductStatus.PUBLISHED:
            raise ProductStatusException("Product is already published")

        missing: list[str] = []
        # Банки не обязательны: продукт без банков завершается решением Совета.
        # Но если банки указаны, хотя бы один должен быть активным.
        if product.banks and not any(bank.is_active for bank in product.banks):
            missing.append("bank_ids")
        if not product.stages:
            missing.append("stages")
        missing.extend(f"stages.{s.number}.fields" for s in product.stages if not s.fields)
        missing.extend(
            f"stages.{s.number}.fields.{f.id}.options"
            for s in product.stages
            for f in s.fields
            if f.field_type in CHOICE_FIELD_TYPES and len(f.options) < MIN_OPTIONS
        )
        if missing:
            raise ProductNotReadyException(missing=missing)

        product.status = ProductStatus.PUBLISHED
        await self.db.commit()
        return await self._detail(product_id)

    async def archive(self, user: CurrentUserDTO, product_id: int) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get(product_id)
        if product.status != ProductStatus.PUBLISHED:
            raise ProductStatusException("Only a published product can be archived")
        product.status = ProductStatus.ARCHIVED
        await self.db.commit()
        return await self._detail(product_id)

    async def copy(self, user: CurrentUserDTO, product_id: int) -> ProductDetailDTO:
        """Новый черновик с теми же названиями, банками, этапами и полями."""
        ApplicationBaseService.assert_global_scope(user)
        source = await self._get(product_id)
        product = ProductORM(
            translations=[
                ProductTranslationORM(language=t.language, name=t.name, description=t.description)
                for t in source.translations
            ],
            category_id=source.category_id,
            allowed_subject_types=list(source.allowed_subject_types),
            accept_from=source.accept_from,
            accept_to=source.accept_to,
            status=ProductStatus.DRAFT,
            copied_from_id=source.id,
            created_by_id=user.id,
        )
        product.banks = list(source.banks)
        # Копии этапов, полей и вариантов; условия переносятся после flush,
        # когда у новых полей и вариантов появятся id.
        stage_copies: list[tuple[ProductStageORM, ProductStageORM]] = []
        field_copies: list[tuple[ProductFieldORM, ProductFieldORM]] = []
        option_ids: dict[int, ProductFieldOptionORM] = {}
        for stage in source.stages:
            new_stage = ProductStageORM(
                number=stage.number,
                translations=[
                    ProductStageTranslationORM(language=t.language, name=t.name)
                    for t in stage.translations
                ],
            )
            for field in stage.fields:
                new_field = ProductFieldORM(
                    field_type=field.field_type,
                    translations=[
                        ProductFieldTranslationORM(language=t.language, name=t.name)
                        for t in field.translations
                    ],
                    is_required=field.is_required,
                    max_files=field.max_files,
                    sort_order=field.sort_order,
                )
                for option in field.options:
                    new_option = ProductFieldOptionORM(
                        sort_order=option.sort_order,
                        translations=[
                            ProductFieldOptionTranslationORM(language=t.language, name=t.name)
                            for t in option.translations
                        ],
                    )
                    new_field.options.append(new_option)
                    option_ids[option.id] = new_option
                new_stage.fields.append(new_field)
                field_copies.append((field, new_field))
            product.stages.append(new_stage)
            stage_copies.append((stage, new_stage))
        self.db.session.add(product)
        await self.db.flush()

        field_ids = {old.id: new.id for old, new in field_copies}
        targets = [*stage_copies, *field_copies]
        for old, new in targets:
            if old.condition_field_id is None or not old.condition_option_ids:
                continue
            new.condition_field_id = field_ids[old.condition_field_id]
            new.condition_option_ids = [option_ids[o].id for o in old.condition_option_ids]
        await self.db.commit()
        return await self._detail(product.id)

    # ---------- этапы ----------

    async def add_stage(
        self, user: CurrentUserDTO, product_id: int, data: StageCreateDTO
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get_unlocked(product_id)
        if await self.db.product.stage_number_taken(product_id, data.number):
            raise StageNumberTakenException()
        precheck_condition(product, data.visible_when, f"stages.{data.number}.visible_when")
        stage = ProductStageORM(product_id=product_id, number=data.number)
        apply_translations(stage.translations, data.translations, ProductStageTranslationORM)
        self._set_condition(stage, data.visible_when)
        self.db.session.add(stage)
        return await self._commit_structure(product_id)

    async def update_stage(
        self, user: CurrentUserDTO, product_id: int, stage_id: int, data: StageUpdateDTO
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get_unlocked(product_id)
        stage = await self._stage(product_id, stage_id)
        if "visible_when" in data.model_fields_set:
            precheck_condition(product, data.visible_when, f"stages.{stage.number}.visible_when")
        if data.number is not None:
            if await self.db.product.stage_number_taken(
                product_id, data.number, exclude_stage_id=stage_id
            ):
                raise StageNumberTakenException()
            stage.number = data.number
        if data.translations is not None:
            apply_translations(stage.translations, data.translations, ProductStageTranslationORM)
        if "visible_when" in data.model_fields_set:
            self._set_condition(stage, data.visible_when)
        return await self._commit_structure(product_id)

    async def delete_stage(
        self, user: CurrentUserDTO, product_id: int, stage_id: int
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get_unlocked(product_id)
        stage = await self._stage(product_id, stage_id)
        # Поля этапа могут управлять показом других этапов и полей вне этого этапа.
        own = {f"fields.{field.id}" for field in stage.fields}
        used = [
            key for field in stage.fields for key in dependents(product, field.id) if key not in own
        ]
        if used:
            raise FieldInUseByConditionException(
                f"Fields of this stage control visibility of: {', '.join(used)}"
            )
        await self.db.session.delete(stage)
        return await self._commit_structure(product_id)

    # ---------- поля ----------

    async def add_field(
        self, user: CurrentUserDTO, product_id: int, stage_id: int, data: FieldCreateDTO
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get_unlocked(product_id)
        await self._stage(product_id, stage_id)
        precheck_condition(product, data.visible_when, "fields.new.visible_when")
        field = ProductFieldORM(
            stage_id=stage_id,
            **data.model_dump(exclude={"translations", "options", "visible_when"}),
        )
        apply_translations(field.translations, data.translations, ProductFieldTranslationORM)
        for item in data.options or []:
            field.options.append(self._new_option(item))
        self._set_condition(field, data.visible_when)
        self.db.session.add(field)
        return await self._commit_structure(product_id)

    async def update_field(
        self, user: CurrentUserDTO, product_id: int, field_id: int, data: FieldUpdateDTO
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get_unlocked(product_id)
        field = await self._field(product_id, field_id)
        if "visible_when" in data.model_fields_set:
            precheck_condition(product, data.visible_when, f"fields.{field.id}.visible_when")
        changes = data.model_dump(
            exclude_unset=True, exclude_none=True, exclude={"translations", "visible_when"}
        )
        new_type = changes.get("field_type")
        if (
            new_type is not None
            and new_type not in CHOICE_FIELD_TYPES
            and field.field_type in CHOICE_FIELD_TYPES
        ):
            # Поле перестаёт быть полем с вариантами: варианты удаляются,
            # а зависящие от него условия должны быть сняты заранее.
            used = dependents(product, field.id)
            if used:
                raise FieldInUseByConditionException(
                    f"Field controls visibility of: {', '.join(used)}"
                )
            field.options.clear()
        for key, value in changes.items():
            setattr(field, key, value)
        if data.translations is not None:
            apply_translations(field.translations, data.translations, ProductFieldTranslationORM)
        if "visible_when" in data.model_fields_set:
            self._set_condition(field, data.visible_when)
        if field.field_type not in FILE_FIELD_TYPES:
            field.max_files = 1
        return await self._commit_structure(product_id)

    async def delete_field(
        self, user: CurrentUserDTO, product_id: int, field_id: int
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get_unlocked(product_id)
        field = await self._field(product_id, field_id)
        used = dependents(product, field.id)
        if used:
            raise FieldInUseByConditionException(f"Field controls visibility of: {', '.join(used)}")
        await self.db.session.delete(field)
        return await self._commit_structure(product_id)

    # ---------- варианты ответа ----------

    async def add_option(
        self, user: CurrentUserDTO, product_id: int, field_id: int, data: OptionCreateDTO
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        await self._get_unlocked(product_id)
        field = await self._field(product_id, field_id)
        if field.field_type not in CHOICE_FIELD_TYPES:
            raise FieldOptionsException()
        field.options.append(self._new_option(data))
        return await self._commit_structure(product_id)

    async def update_option(
        self, user: CurrentUserDTO, product_id: int, option_id: int, data: OptionUpdateDTO
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        await self._get_unlocked(product_id)
        option = await self._option(product_id, option_id)
        if data.translations is not None:
            apply_translations(
                option.translations, data.translations, ProductFieldOptionTranslationORM
            )
        if data.sort_order is not None:
            option.sort_order = data.sort_order
        return await self._commit_structure(product_id)

    async def delete_option(
        self, user: CurrentUserDTO, product_id: int, option_id: int
    ) -> ProductDetailDTO:
        ApplicationBaseService.assert_global_scope(user)
        product = await self._get_unlocked(product_id)
        option = await self._option(product_id, option_id)
        used = option_dependents(product, option.id)
        if used:
            raise FieldInUseByConditionException(
                f"Option controls visibility of: {', '.join(used)}"
            )
        await self.db.session.delete(option)
        return await self._commit_structure(product_id)

    # ---------- вспомогательное ----------

    async def _get(self, product_id: int) -> ProductORM:
        product = await self.db.product.get_orm(product_id)
        if product is None:
            raise ProductNotFoundException()
        return product

    async def _category(self, category_id: int) -> ProductCategoryORM:
        category = await self.db.product.get_category(category_id)
        if category is None:
            raise ProductCategoryNotFoundException()
        return category

    async def _active_category(self, category_id: int) -> ProductCategoryORM:
        category = await self._category(category_id)
        if not category.is_active:
            raise ProductCategoryInactiveException()
        return category

    async def _category_detail(self, category_id: int) -> CategoryDTO:
        category = await self._category(category_id)
        counts = await self.db.product.products_per_category()
        return category_dto(category, counts.get(category_id, 0))

    async def _get_unlocked(self, product_id: int) -> ProductORM:
        product = await self._get(product_id)
        if await self.db.product.applications_count(product_id):
            raise ProductLockedException()
        return product

    async def _stage(self, product_id: int, stage_id: int) -> ProductStageORM:
        stage = await self.db.product.get_stage(product_id, stage_id)
        if stage is None:
            raise ProductStageNotFoundException()
        return stage

    async def _field(self, product_id: int, field_id: int) -> ProductFieldORM:
        field = await self.db.product.get_field(product_id, field_id)
        if field is None:
            raise ProductFieldNotFoundException()
        return field

    async def _option(self, product_id: int, option_id: int) -> ProductFieldOptionORM:
        option = await self.db.product.get_option(product_id, option_id)
        if option is None:
            raise ProductFieldOptionNotFoundException()
        return option

    @staticmethod
    def _new_option(data: OptionCreateDTO) -> ProductFieldOptionORM:
        option = ProductFieldOptionORM(sort_order=data.sort_order)
        apply_translations(option.translations, data.translations, ProductFieldOptionTranslationORM)
        return option

    @staticmethod
    def _set_condition(
        target: ProductStageORM | ProductFieldORM, visible_when: VisibleWhenDTO | None
    ) -> None:
        if visible_when is None:
            target.condition_field_id = None
            target.condition_option_ids = None
        else:
            target.condition_field_id = visible_when.field_id
            target.condition_option_ids = list(visible_when.option_ids)

    async def _commit_structure(self, product_id: int) -> ProductDetailDTO:
        """Завершение изменения этапов / полей / вариантов: перечитать продукт,
        проверить условия показа целиком, сохранить."""
        await self.db.flush()
        product = await self._get(product_id)
        validate_conditions(product)
        await self.db.commit()
        return await self._detail(product_id)

    async def _banks(self, bank_ids: list[int]) -> list[BankORM]:
        ids = list(dict.fromkeys(bank_ids))
        if not ids:
            return []
        banks = (await self.db.session.scalars(select(BankORM).where(BankORM.id.in_(ids)))).all()
        missing = sorted(set(ids) - {bank.id for bank in banks})
        if missing:
            raise BankNotFoundException(
                f"Banks not found: {', '.join(map(str, missing))}", field="bank_ids"
            )
        order = {bank_id: index for index, bank_id in enumerate(ids)}
        return sorted(banks, key=lambda bank: order[bank.id])

    async def _detail(self, product_id: int) -> ProductDetailDTO:
        product = await self._get(product_id)
        count = await self.db.product.applications_count(product_id)
        return ProductDataMapper.map_to_detail(product, applications_count=count)
