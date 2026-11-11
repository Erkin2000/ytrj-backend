from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, model_validator

from src.application.enums import SubjectType
from src.application.schemas.bank_schema import BankDTO
from src.product.enums import FILE_FIELD_TYPES, LANGUAGES, FieldType, Language, ProductStatus

NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]
DescriptionStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
MAX_FILES_LIMIT = 10


# ---------- переводы ----------


class NameTranslationDTO(BaseModel):
    language: Language = Field(examples=["ru"])
    name: NameStr = Field(examples=["Сведения о проекте"])


class ProductTranslationDTO(NameTranslationDTO):
    description: DescriptionStr | None = Field(
        default=None, examples=["Льготный кредит для молодых предпринимателей."]
    )


def check_languages[T: NameTranslationDTO](items: list[T]) -> list[T]:
    """Ровно по одному переводу на каждый язык: ru, uz, en. Возвращает их в этом порядке."""
    seen: dict[Language, T] = {}
    duplicates: list[str] = []
    for item in items:
        if item.language in seen:
            duplicates.append(item.language.value)
        seen[item.language] = item
    if duplicates:
        raise ValueError(f"Язык указан дважды: {', '.join(sorted(set(duplicates)))}")
    missing = [lang.value for lang in LANGUAGES if lang not in seen]
    if missing:
        raise ValueError(f"Нужен перевод на все языки (ru, uz, en); нет: {', '.join(missing)}")
    return [seen[lang] for lang in LANGUAGES]


def check_product_translations(
    items: list[ProductTranslationDTO],
) -> list[ProductTranslationDTO]:
    items = check_languages(items)
    described = [t.language.value for t in items if t.description]
    if described and len(described) != len(items):
        missing = [t.language.value for t in items if not t.description]
        raise ValueError(
            f"Описание задаётся на всех языках или ни на одном; нет: {', '.join(missing)}"
        )
    return items


NameTranslations = Annotated[
    list[NameTranslationDTO], Field(min_length=3, max_length=3), AfterValidator(check_languages)
]
ProductTranslations = Annotated[
    list[ProductTranslationDTO],
    Field(min_length=3, max_length=3),
    AfterValidator(check_product_translations),
]

PRODUCT_TRANSLATIONS_EXAMPLE = [
    {
        "language": "ru",
        "name": "Молодёжный бизнес",
        "description": "Льготный кредит для молодых предпринимателей.",
    },
    {
        "language": "uz",
        "name": "Yoshlar biznesi",
        "description": "Yosh tadbirkorlar uchun imtiyozli kredit.",
    },
    {
        "language": "en",
        "name": "Youth business",
        "description": "Preferential loan for young entrepreneurs.",
    },
]
STAGE_TRANSLATIONS_EXAMPLE = [
    {"language": "ru", "name": "Сведения о проекте"},
    {"language": "uz", "name": "Loyiha haqida maʼlumot"},
    {"language": "en", "name": "Project details"},
]
FIELD_TRANSLATIONS_EXAMPLE = [
    {"language": "ru", "name": "Запрашиваемая сумма"},
    {"language": "uz", "name": "Soʻralayotgan summa"},
    {"language": "en", "name": "Requested amount"},
]
TRANSLATIONS_NOTE = (
    "Ровно три перевода — `ru`, `uz`, `en`, каждый язык один раз. При изменении передаются все три."
)


CATEGORY_TRANSLATIONS_EXAMPLE = [
    {"language": "ru", "name": "Кредиты для бизнеса", "description": None},
    {"language": "uz", "name": "Biznes uchun kreditlar", "description": None},
    {"language": "en", "name": "Business loans", "description": None},
]


# ---------- запросы ----------


class CategoryCreateDTO(BaseModel):
    translations: ProductTranslations = Field(
        description=TRANSLATIONS_NOTE + " Описание — на всех трёх языках или ни на одном.",
        examples=[CATEGORY_TRANSLATIONS_EXAMPLE],
    )
    is_active: bool = Field(
        default=True,
        description="Неактивную категорию нельзя выбрать для продукта; её продукты не видны заявителям.",
    )
    sort_order: int = Field(default=0, ge=0, description="Порядок в списке категорий.")


class CategoryUpdateDTO(BaseModel):
    translations: ProductTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[CATEGORY_TRANSLATIONS_EXAMPLE]
    )
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class ProductCreateDTO(BaseModel):
    category_id: int = Field(
        description="Категория из `GET /fund/product-categories` (активная).", examples=[1]
    )
    translations: ProductTranslations = Field(
        description=TRANSLATIONS_NOTE + " Описание — на всех трёх языках или ни на одном.",
        examples=[PRODUCT_TRANSLATIONS_EXAMPLE],
    )
    allowed_subject_types: list[SubjectType] = Field(
        default_factory=lambda: list(SubjectType),
        min_length=1,
        description="Для каких типов субъекта доступен продукт.",
    )
    accept_from: date | None = Field(
        default=None, description="Начало приёма заявок (включительно).", examples=["2026-11-10"]
    )
    accept_to: date | None = Field(
        default=None, description="Конец приёма заявок (включительно).", examples=["2026-12-31"]
    )
    bank_ids: list[int] = Field(
        default_factory=list,
        description="Банки, через которые работает продукт (из каталога банков).",
        examples=[[1, 2]],
    )

    @model_validator(mode="after")
    def _dates_in_order(self):
        if self.accept_from and self.accept_to and self.accept_from > self.accept_to:
            raise ValueError("accept_from не может быть позже accept_to")
        return self


class ProductUpdateDTO(BaseModel):
    category_id: int | None = Field(
        default=None, description="Перенос в другую активную категорию."
    )
    translations: ProductTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[PRODUCT_TRANSLATIONS_EXAMPLE]
    )
    allowed_subject_types: list[SubjectType] | None = Field(default=None, min_length=1)
    accept_from: date | None = None
    accept_to: date | None = None
    bank_ids: list[int] | None = Field(
        default=None, description="Полный список банков продукта (заменяет текущий)."
    )


class StageCreateDTO(BaseModel):
    number: int = Field(ge=1, le=100, description="Номер этапа (порядок).", examples=[1])
    translations: NameTranslations = Field(
        description=TRANSLATIONS_NOTE, examples=[STAGE_TRANSLATIONS_EXAMPLE]
    )


class StageUpdateDTO(BaseModel):
    number: int | None = Field(default=None, ge=1, le=100)
    translations: NameTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[STAGE_TRANSLATIONS_EXAMPLE]
    )


class FieldCreateDTO(BaseModel):
    field_type: FieldType = Field(examples=["NUMBER"])
    translations: NameTranslations = Field(
        description=TRANSLATIONS_NOTE, examples=[FIELD_TRANSLATIONS_EXAMPLE]
    )
    is_required: bool = True
    max_files: int = Field(
        default=1,
        ge=1,
        le=MAX_FILES_LIMIT,
        description="Только для PHOTO и FILE: сколько файлов можно загрузить.",
    )
    sort_order: int = Field(default=0, ge=0, description="Порядок поля внутри этапа.")

    @model_validator(mode="after")
    def _max_files_only_for_files(self):
        if self.field_type not in FILE_FIELD_TYPES:
            self.max_files = 1
        return self


class FieldUpdateDTO(BaseModel):
    field_type: FieldType | None = None
    translations: NameTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[FIELD_TRANSLATIONS_EXAMPLE]
    )
    is_required: bool | None = None
    max_files: int | None = Field(default=None, ge=1, le=MAX_FILES_LIMIT)
    sort_order: int | None = Field(default=None, ge=0)


class ProductFilterDTO(BaseModel):
    status: ProductStatus | None = None
    category_id: int | None = None
    search: str | None = Field(default=None, description="Поиск по названию на любом языке.")


# ---------- ответы ----------


class TranslationOutDTO(BaseModel):
    language: Language
    name: str


class ProductTranslationOutDTO(TranslationOutDTO):
    description: str | None = None


class ProductBriefDTO(BaseModel):
    id: int
    translations: list[TranslationOutDTO]


class CategoryBriefDTO(BaseModel):
    id: int
    translations: list[TranslationOutDTO]


class CategoryDTO(BaseModel):
    id: int
    translations: list[ProductTranslationOutDTO]
    is_active: bool
    sort_order: int
    products_count: int = Field(
        default=0,
        description="Фонду — все продукты категории; заявителю — доступные сейчас.",
    )
    created_at: datetime
    updated_at: datetime


class ProductFieldDTO(BaseModel):
    id: int
    field_type: FieldType
    translations: list[TranslationOutDTO]
    is_required: bool
    max_files: int
    sort_order: int


class ProductStageDTO(BaseModel):
    id: int
    number: int
    translations: list[TranslationOutDTO]
    fields: list[ProductFieldDTO] = []


class ProductListItemDTO(BaseModel):
    id: int
    category: CategoryBriefDTO
    translations: list[ProductTranslationOutDTO]
    status: ProductStatus
    allowed_subject_types: list[SubjectType]
    accept_from: date | None = None
    accept_to: date | None = None
    banks: list[BankDTO] = []
    created_at: datetime
    updated_at: datetime


class ProductDetailDTO(ProductListItemDTO):
    stages: list[ProductStageDTO] = []
    copied_from_id: int | None = None
    applications_count: int = Field(
        default=0, description="Сколько заявок подано по продукту (включая черновики)."
    )
    is_locked: bool = Field(
        default=False,
        description="Есть заявки: этапы и поля менять нельзя, только скопировать продукт.",
    )


class FieldTypeInfoDTO(BaseModel):
    """Тип поля анкеты и правила его заполнения."""

    type: FieldType
    translations: list[TranslationOutDTO]
    is_file: bool = Field(
        description="true — PHOTO / FILE: файлы загружаются отдельно, значение не передаётся."
    )
    format: str | None = Field(default=None, description="Формат значения для подсказки.")
    example: str | None = None
    pattern: str | None = Field(default=None, description="Регулярное выражение значения.")
    max_length: int | None = Field(default=None, description="Максимальная длина текста.")
    max_digits: int | None = Field(default=None, description="Максимум цифр в числе.")
    max_files_limit: int | None = Field(
        default=None, description="Предел `max_files`, который можно задать полю."
    )
    allowed_content_types: list[str] | None = None
    max_size_mb: int | None = Field(default=None, description="Максимальный размер файла, МБ.")
