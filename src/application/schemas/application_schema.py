from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints

from src.account.models.user_model import Gender
from src.application.enums import (
    ApplicationStatus,
    BankDecision,
    CouncilDecision,
    DemandDocumentStatus,
    ScoringResult,
    SubjectType,
)
from src.application.schemas.bank_schema import BankDTO
from src.product.schemas.product_schema import (
    ProductBriefDTO,
    ProductFieldDTO,
    ProductFieldOptionDTO,
    TranslationOutDTO,
    VisibleWhenDTO,
)

ReasonStr = Annotated[str, StringConstraints(min_length=3, max_length=2000)]


# ---------- вложенные ----------


class ApplicantSnapshotDTO(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    passport_number: str | None = None
    pinfl: str | None = None
    inn: str | None = None
    email: str | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None


class ActorDTO(BaseModel):
    id: int
    full_name: str | None = None
    username: str


class StatusHistoryDTO(BaseModel):
    id: int
    from_status: ApplicationStatus | None = None
    to_status: ApplicationStatus
    event: str
    comment: str | None = None
    actor: ActorDTO | None = None
    actor_role: str | None = None
    created_at: datetime


class ScoringAttemptDTO(BaseModel):
    id: int
    provider: str
    result: ScoringResult
    eligibility_passed: bool | None = None
    details: dict[str, Any] | None = None
    error_message: str | None = None
    recorded_by: ActorDTO | None = None
    created_at: datetime


class CouncilAssignmentDTO(BaseModel):
    id: int
    council_member: ActorDTO
    assigned_at: datetime
    decision: CouncilDecision | None = None
    reason: str | None = None
    decided_at: datetime | None = None


class DemandDocumentDTO(BaseModel):
    id: int
    number: str
    status: DemandDocumentStatus
    file_path: str | None = None
    issued_at: datetime


class ResourceAllocationDTO(BaseModel):
    id: int
    amount: Decimal | None = None
    currency: str
    reference_number: str | None = None
    details: str | None = None
    allocated_by: ActorDTO | None = None
    allocated_at: datetime


class BankStageDTO(BaseModel):
    sent_to_bank_at: datetime | None = None
    accepted_by: ActorDTO | None = None
    accepted_at: datetime | None = None
    decision: BankDecision | None = None
    decision_reason: str | None = None
    decided_by: ActorDTO | None = None
    decided_at: datetime | None = None


# ---------- запросы ----------


class ApplicationCreateDTO(BaseModel):
    product_id: int = Field(description="Продукт из `GET /products`.", examples=[3])
    subject_type: SubjectType = Field(examples=["YATT"])
    bank_id: int | None = Field(
        default=None,
        description="Банк из `banks` продукта; можно выбрать позже (`PUT /applications/{id}/bank`).",
        examples=[1],
    )


class ApplicationUpdateDTO(BaseModel):
    product_id: int | None = Field(
        default=None,
        description="Смена продукта очищает ответы анкеты и выбранный банк.",
    )
    subject_type: SubjectType | None = None


class StageValuesDTO(BaseModel):
    """Значения полей этапа: ключ — id поля, значение — строка; `null` или "" очищает поле.
    SELECT / RADIO — id варианта, CHECKBOX — список id вариантов. Меняются только
    переданные поля. Файлы (PHOTO / FILE) загружаются отдельно."""

    values: dict[int, str | int | list[int] | None] = Field(
        examples=[{"11": "150000000", "10": "21", "15": [31, 32], "14": "+998901234567"}]
    )


class ApplicationFilterDTO(BaseModel):
    status: ApplicationStatus | None = None
    product_id: int | None = None
    statuses: list[ApplicationStatus] | None = None
    bank_id: int | None = None
    subject_type: SubjectType | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = None
    scoring_retry_required: bool | None = None


class BankDecisionDTO(BaseModel):
    decision: BankDecision
    reason: ReasonStr | None = Field(default=None, description="Обязательна при отказе.")


class ApplicationBankDTO(BaseModel):
    """Выбор банка заявителем (отдельный шаг черновика)."""

    bank_id: int = Field(examples=[1])


class FundRejectDTO(BaseModel):
    reason: ReasonStr = Field(description="Причина отказа Фонда (видна заявителю).")


# ---------- ответы ----------


class FieldFileDTO(BaseModel):
    id: int
    file_name: str
    content_type: str
    size: int
    url: str
    created_at: datetime


class FormFieldDTO(ProductFieldDTO):
    value: str | None = Field(
        default=None,
        description=(
            "Значение (NUMBER — строкой, DATE — ГГГГ-ММ-ДД, SELECT / RADIO — id варианта, "
            "CHECKBOX — id вариантов через запятую). Для PHOTO / FILE — null."
        ),
    )
    selected_options: list[ProductFieldOptionDTO] = Field(
        default=[], description="Выбранные варианты SELECT / RADIO / CHECKBOX с названиями."
    )
    files: list[FieldFileDTO] = []


class FormStageDTO(BaseModel):
    id: int
    number: int
    translations: list[TranslationOutDTO]
    visible_when: VisibleWhenDTO | None = None
    is_complete: bool = Field(description="Все обязательные поля этапа заполнены.")
    fields: list[FormFieldDTO] = []


class FormProgressDTO(BaseModel):
    """Насколько заполнена анкета продукта."""

    stages_total: int = Field(description="Сколько этапов в продукте.")
    stages_complete: int = Field(
        description="Сколько этапов заполнено (все обязательные поля этапа заполнены)."
    )
    is_complete: bool = Field(description="Заполнены все этапы.")


class ApplicationListItemDTO(BaseModel):
    id: int
    number: str
    status: ApplicationStatus
    product: ProductBriefDTO | None = None
    subject_type: SubjectType | None = None
    bank: BankDTO | None = None
    applicant_full_name: str | None = None
    form_progress: FormProgressDTO
    scoring_retry_required: bool = False
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationDetailDTO(ApplicationListItemDTO):
    applicant_id: int
    applicant: ApplicantSnapshotDTO
    form: list[FormStageDTO] = Field(
        default=[],
        description="Этапы продукта с ответами заявителя — только видимые при текущих ответах.",
    )
    bank_stage: BankStageDTO
    fund_decided_at: datetime | None = None
    fund_reject_reason: str | None = None
    council_assignments: list[CouncilAssignmentDTO] = []
    council_decided_at: datetime | None = None
    council_reject_reason: str | None = None
    demand_document: DemandDocumentDTO | None = None
    resource_allocation: ResourceAllocationDTO | None = None
    completed_at: datetime | None = None
    rejection_reason: str | None = None


class SubmissionCheckDTO(BaseModel):
    """Сводка перед отправкой: что выбрано и чего не хватает."""

    is_ready: bool
    missing: list[str]
    product: ProductBriefDTO | None = None
    product_available: bool = Field(
        description="Продукт опубликован, в сроках приёма и подходит по типу субъекта."
    )
    subject_type: SubjectType | None = None
    bank: BankDTO | None = None
    stages: list[FormStageDTO] = []


class ProgressStepDTO(BaseModel):
    key: str
    title: str
    state: str = Field(description="done | active | pending | rejected")
    description: str
    action_required: str | None = None


class ApplicationProgressDTO(BaseModel):
    application_id: int
    number: str
    status: ApplicationStatus
    is_rejected: bool
    rejection_message: str | None = None
    steps: list[ProgressStepDTO]


class WorkspaceCountersDTO(BaseModel):
    """Счётчики для рабочих окон."""

    counters: dict[str, int]


# ---------- внутренние DTO для репозитория ----------


class ApplicationAddDTO(BaseModel):
    number: str
    applicant_id: int
    applicant_full_name: str | None = None
    applicant_phone: str | None = None
    applicant_passport: str | None = None
    applicant_pinfl: str | None = None
    applicant_inn: str | None = None
    applicant_email: str | None = None
    applicant_gender: Gender | None = None
    applicant_date_of_birth: date | None = None
    product_id: int
    subject_type: SubjectType
    bank_id: int | None = None


class StatusHistoryAddDTO(BaseModel):
    application_id: int
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    event: str
    comment: str | None = None
    actor_id: int | None = None
    actor_role: str | None = None


class ScoringAttemptAddDTO(BaseModel):
    application_id: int
    provider: str = "KATM"
    result: ScoringResult
    eligibility_passed: bool | None = None
    details: dict[str, Any] | None = None
    error_message: str | None = None
    recorded_by_id: int | None = None


class CouncilAssignmentAddDTO(BaseModel):
    application_id: int
    council_member_id: int
    assigned_by_id: int | None = None


class CouncilAssignmentUpdateDTO(BaseModel):
    decision: CouncilDecision | None = None
    reason: str | None = None
    decided_at: datetime | None = None


class DemandDocumentAddDTO(BaseModel):
    application_id: int
    number: str
    status: DemandDocumentStatus = DemandDocumentStatus.CREATED


class ResourceAllocationAddDTO(BaseModel):
    application_id: int
    amount: Decimal | None = None
    currency: str = "UZS"
    reference_number: str | None = None
    details: str | None = None
    allocated_by_id: int | None = None
