import datetime as dt
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from src.account.models.user_model import Gender
from src.application.schemas.application_schema import ActorDTO
from src.product.enums import Language
from src.product.schemas.product_schema import ProductTranslations
from src.registry.dictionaries import BANKS, REGIONS
from src.registry.enums import (
    Decision,
    GroupBy,
    ImportTemplate,
    ProgramKind,
    ProjectStatus,
    RegistrySubjectType,
    Sector,
    Source,
)

ProgramCodeStr = Annotated[
    str, StringConstraints(min_length=2, max_length=50, pattern=r"^[A-Z][A-Z0-9_]*$")
]
Text255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Text500 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
Money = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=2)]
TinStr = Annotated[str, StringConstraints(pattern=r"^\d{9}$|^\d{14}$")]


def _region(value: str | None) -> str | None:
    if value is not None and value not in REGIONS:
        raise ValueError(f"Неизвестный регион; допустимо: {', '.join(REGIONS)}")
    return value


def _bank(value: str | None) -> str | None:
    if value is not None and value not in BANKS:
        raise ValueError(f"Неизвестный банк; допустимо: {', '.join(BANKS)}")
    return value


RegionCode = Annotated[str, AfterValidator(_region)]
BankCode = Annotated[str, AfterValidator(_bank)]

TRANSLATIONS_NOTE = (
    "Ровно три перевода — `ru`, `uz`, `en`; описание — на всех трёх языках или ни на одном."
)
PROGRAM_TRANSLATIONS_EXAMPLE = [
    {"language": "ru", "name": "ПҚ-60: льготные кредиты через банки", "description": None},
    {"language": "uz", "name": "PQ-60: banklar orqali imtiyozli kreditlar", "description": None},
    {"language": "en", "name": "PQ-60: preferential loans via banks", "description": None},
]


class LabelDTO(BaseModel):
    language: Language
    name: str


class CodeLabelDTO(BaseModel):
    code: str
    translations: list[LabelDTO]


# ---------- программы ----------


class ProgramCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ProgramCodeStr = Field(examples=["PQ60"])
    kind: ProgramKind = Field(examples=["CREDIT"])
    import_template: ImportTemplate | None = Field(
        default=None,
        description="Шаблон Excel для `POST /registry/import`; `null` — проекты только через API.",
    )
    translations: ProductTranslations = Field(
        description=TRANSLATIONS_NOTE, examples=[PROGRAM_TRANSLATIONS_EXAMPLE]
    )
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)


class ProgramUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ProgramCodeStr | None = None
    kind: ProgramKind | None = None
    import_template: ImportTemplate | None = None
    translations: ProductTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[PROGRAM_TRANSLATIONS_EXAMPLE]
    )
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class ProgramTranslationOutDTO(BaseModel):
    language: Language
    name: str
    description: str | None = None


class ProgramShortDTO(BaseModel):
    id: int
    code: str
    kind: ProgramKind
    translations: list[ProgramTranslationOutDTO]


class ProgramDTO(ProgramShortDTO):
    import_template: ImportTemplate | None = None
    is_active: bool
    sort_order: int
    projects_count: int = 0
    last_import_file: str | None = None
    last_import_at: dt.datetime | None = None


class PublicProgramDTO(ProgramShortDTO):
    projects_count: int = 0
    last_import_at: dt.datetime | None = Field(
        default=None, description="Когда данные программы обновлены (последний импорт)."
    )


# ---------- проекты ----------


class _ProjectFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization: Text500 | None = Field(
        default=None, description="МЧЖ / ЯТТ или название проекта."
    )
    tin: TinStr | None = Field(default=None, description="СТИР (9 цифр) или ПИНФЛ (14 цифр).")
    subject_type: RegistrySubjectType | None = None
    head_info: LongText | None = Field(
        default=None, description="Руководитель: Ф.И.Ш., паспорт, дата рождения (как в файле)."
    )
    gender: Gender | None = None
    age: int | None = Field(default=None, ge=14, le=100)
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    region: RegionCode | None = Field(
        default=None, description="Код региона из `GET /registry/dictionaries`."
    )
    district: Text255 | None = Field(
        default=None, description="Туман / город, например «Bo'ston tumani»."
    )
    mahalla: Text255 | None = None
    purpose: LongText | None = Field(default=None, description="Цель использования средств.")
    sector: Sector | None = None
    direction: Text255 | None = Field(
        default=None, description="Направление: «Тикувчилик», «Савдо»…"
    )
    jobs: int | None = Field(default=None, ge=0, description="Планируемые рабочие места.")
    project_cost: Money | None = Field(default=None, description="Стоимость проекта, сўм.")
    requested_amount: Money | None = Field(default=None, description="Запрошено у Фонда, сўм.")
    allocated_amount: Money | None = Field(default=None, description="Выделено Фондом, сўм.")
    credit_amount: Money | None = Field(default=None, description="Фактически выдано банком, сўм.")
    term_months: int | None = Field(default=None, ge=1, le=600)
    collateral: Text255 | None = Field(
        default=None, description="Обеспечение: страховка, поручительство…"
    )
    bank: BankCode | None = Field(
        default=None, description="Код банка из `GET /registry/dictionaries`."
    )
    bank_branch: Text255 | None = None
    bank_letter_date: dt.date | None = Field(
        default=None, description="Письмо в коммерческий банк."
    )
    bank_request: Text255 | None = Field(
        default=None, description="Требование банка: дата и номер."
    )
    order_info: Text255 | None = Field(default=None, description="Приказ в финансовый отдел.")
    application_date: dt.date | None = Field(default=None, description="Дата заявки (буюртманома).")
    decision: Decision | None = None
    council_protocol: Text255 | None = Field(
        default=None, description="Протокол Совета: дата и номер."
    )
    council_date: dt.date | None = None
    note: LongText | None = None


class ProjectCreateDTO(_ProjectFields):
    program_id: int
    applicant_name: Text500 = Field(description="Инициатор проекта (Ф.И.Ш. или название).")
    status: ProjectStatus = ProjectStatus.IN_PROGRESS


class ProjectUpdateDTO(_ProjectFields):
    """Передаются только изменяемые поля; `null` очищает поле."""

    program_id: int | None = None
    applicant_name: Text500 | None = None
    status: ProjectStatus | None = None


class ProjectDTO(BaseModel):
    id: int
    program: ProgramShortDTO
    source: Source
    number: int | None = None
    applicant_name: str
    organization: str | None = None
    tin: str | None = None
    subject_type: RegistrySubjectType | None = None
    head_info: str | None = None
    gender: Gender | None = None
    age: int | None = None
    phone: str | None = None
    region: CodeLabelDTO | None = None
    district: str | None = None
    mahalla: str | None = None
    purpose: str | None = None
    sector: Sector | None = None
    direction: str | None = None
    jobs: int | None = None
    project_cost: Decimal | None = None
    requested_amount: Decimal | None = None
    allocated_amount: Decimal | None = None
    credit_amount: Decimal | None = None
    term_months: int | None = None
    collateral: str | None = None
    bank: CodeLabelDTO | None = None
    bank_branch: str | None = None
    bank_letter_date: dt.date | None = None
    bank_request: str | None = None
    order_info: str | None = None
    application_date: dt.date | None = None
    decision: Decision | None = None
    council_protocol: str | None = None
    council_date: dt.date | None = None
    status: ProjectStatus
    note: str | None = None
    extra: dict | None = Field(default=None, description="Колонки файла без своего поля.")
    created_by: ActorDTO | None = None
    updated_by: ActorDTO | None = None
    created_at: dt.datetime
    updated_at: dt.datetime


class PublicAnalyticsFilterDTO(BaseModel):
    """Фильтры аналитики. Дата и год — по дате решения Совета, а если её нет — по дате заявки."""

    program_id: int | None = None
    kind: ProgramKind | None = None
    region: str | None = Field(default=None, description="Код региона.")
    district: str | None = Field(default=None, description="Туман — в любом написании.")
    bank: str | None = Field(default=None, description="Код банка.")
    sector: Sector | None = None
    direction: str | None = None
    gender: Gender | None = None
    subject_type: RegistrySubjectType | None = None
    status: ProjectStatus | None = None
    year: int | None = Field(default=None, ge=2000, le=2100)
    date_from: dt.date | None = None
    date_to: dt.date | None = None


class ProjectFilterDTO(PublicAnalyticsFilterDTO):
    """Фильтры списка проектов и аналитики (кабинет). Дата и год — по дате решения Совета,
    а если её нет — по дате заявки."""

    source: Source | None = None
    search: str | None = Field(
        default=None, description="Поиск по инициатору, организации, СТИР / ПИНФЛ, телефону."
    )


class PublicScopeFilterDTO(ProjectFilterDTO):
    """Внутренний: публичная аналитика — только активные программы."""

    active_programs_only: bool = True


# ---------- импорт ----------


class ImportResultDTO(BaseModel):
    program: ProgramShortDTO
    file_name: str
    sheet: str
    imported: int = Field(description="Загружено строк.")
    replaced: int = Field(description="Удалено проектов прежнего импорта этой программы.")
    skipped: int = Field(description="Строк без инициатора — пропущены.")
    unknown_regions: list[str] = Field(description="Названия регионов, которые не распознаны.")
    unknown_banks: list[str] = Field(description="Названия банков, которые не распознаны.")


# ---------- аналитика ----------


class TotalsDTO(BaseModel):
    projects: int
    requested_amount: Decimal
    allocated_count: int
    allocated_amount: Decimal
    credit_count: int
    credit_amount: Decimal
    returned_count: int
    returned_amount: Decimal = Field(
        description="Запрошенная сумма проектов, по которым ресурс вернулся."
    )
    jobs: int


class SummaryDTO(TotalsDTO):
    average_allocated: Decimal = Field(description="Средняя выделенная сумма на проект, сўм.")
    by_gender: dict[str, int] = Field(description="`NOT_SPECIFIED` — не указано.")
    by_subject_type: dict[str, int]
    by_status: dict[str, int]
    date_min: dt.date | None = None
    date_max: dt.date | None = None


class BreakdownRowDTO(TotalsDTO):
    key: str | None = Field(description="Значение разреза (код, id, год…); `null` — не указано.")
    translations: list[LabelDTO] = Field(description="Подпись на ru / uz / en.")


class BreakdownDTO(BaseModel):
    group_by: GroupBy
    rows: list[BreakdownRowDTO]
    total: TotalsDTO


class DictionariesDTO(BaseModel):
    regions: list[CodeLabelDTO]
    banks: list[CodeLabelDTO]
    kinds: list[CodeLabelDTO]
    statuses: list[CodeLabelDTO]
    decisions: list[CodeLabelDTO]
    subject_types: list[CodeLabelDTO]
    sectors: list[CodeLabelDTO]
    genders: list[CodeLabelDTO]
    import_templates: list[str]
    group_by: list[str]
