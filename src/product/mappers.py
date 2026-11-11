from src.application.schemas.bank_schema import BankDTO
from src.product.models.product_model import (
    ProductCategoryORM,
    ProductFieldORM,
    ProductORM,
    ProductStageORM,
)
from src.product.schemas.product_schema import (
    CategoryBriefDTO,
    CategoryDTO,
    ProductBriefDTO,
    ProductDetailDTO,
    ProductFieldDTO,
    ProductListItemDTO,
    ProductStageDTO,
    ProductTranslationOutDTO,
    TranslationOutDTO,
)
from src.utils.base_rep.mappers.base import DataMapper


def names(translations) -> list[TranslationOutDTO]:
    return [TranslationOutDTO(language=t.language, name=t.name) for t in translations]


def product_brief(model: ProductORM) -> ProductBriefDTO:
    return ProductBriefDTO(
        id=model.id, translations=names(model.translations), uses_bank=model.uses_bank
    )


def field_dto(model: ProductFieldORM) -> ProductFieldDTO:
    return ProductFieldDTO(
        id=model.id,
        field_type=model.field_type,
        translations=names(model.translations),
        is_required=model.is_required,
        max_files=model.max_files,
        sort_order=model.sort_order,
    )


def stage_dto(model: ProductStageORM) -> ProductStageDTO:
    return ProductStageDTO(
        id=model.id,
        number=model.number,
        translations=names(model.translations),
        fields=[field_dto(f) for f in model.fields],
    )


class ProductDataMapper(DataMapper):
    db_model = ProductORM
    schema = ProductListItemDTO

    @staticmethod
    def _list_fields(model: ProductORM, only_active_banks: bool = False) -> dict:
        banks = [b for b in model.banks if b.is_active] if only_active_banks else model.banks
        return {
            "id": model.id,
            "category": CategoryBriefDTO(
                id=model.category.id, translations=names(model.category.translations)
            ),
            "translations": [
                ProductTranslationOutDTO(
                    language=t.language, name=t.name, description=t.description
                )
                for t in model.translations
            ],
            "status": model.status,
            "uses_bank": model.uses_bank,
            "allowed_subject_types": model.allowed_subject_types,
            "accept_from": model.accept_from,
            "accept_to": model.accept_to,
            "banks": [BankDTO.model_validate(b, from_attributes=True) for b in banks],
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    @staticmethod
    def map_to_domain_entity(model: ProductORM) -> ProductListItemDTO:
        return ProductListItemDTO(**ProductDataMapper._list_fields(model))

    @staticmethod
    def map_to_applicant(model: ProductORM) -> ProductListItemDTO:
        """Каталог заявителя: только активные банки продукта."""
        return ProductListItemDTO(**ProductDataMapper._list_fields(model, only_active_banks=True))

    @staticmethod
    def map_to_detail(
        model: ProductORM, applications_count: int = 0, for_applicant: bool = False
    ) -> ProductDetailDTO:
        return ProductDetailDTO(
            **ProductDataMapper._list_fields(model, only_active_banks=for_applicant),
            stages=[stage_dto(s) for s in model.stages],
            copied_from_id=model.copied_from_id,
            applications_count=applications_count,
            is_locked=applications_count > 0,
        )


def category_dto(model: ProductCategoryORM, products_count: int = 0) -> CategoryDTO:
    return CategoryDTO(
        id=model.id,
        translations=[
            ProductTranslationOutDTO(language=t.language, name=t.name, description=t.description)
            for t in model.translations
        ],
        is_active=model.is_active,
        sort_order=model.sort_order,
        products_count=products_count,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
