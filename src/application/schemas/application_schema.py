from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints, ValidationInfo, field_validator

from src.account.models.user_model import Gender
from src.account.schemas.user_schema import InnStr, PassportStr, PhoneStr
from src.application.enums import (
    ApplicationStatus,
    BankDecision,
    CouncilDecision,
    DemandDocumentStatus,
    ScoringResult,
    SubjectType,
)
from src.application.schemas.bank_schema import BankDTO
from src.config import settings

LegalNameStr = Annotated[str, StringConstraints(min_length=2, max_length=255)]
ReasonStr = Annotated[str, StringConstraints(min_length=3, max_length=2000)]
FullNameStr = Annotated[str, StringConstraints(min_length=3, max_length=255)]


def _normalize_passport(value):
    if isinstance(value, str):
        return value.replace(" ", "").upper()
    return value


def _date_in_past(value: date | None) -> date | None:
    if value is not None and value >= date.today():
        raise ValueError("Дата рождения должна быть в прошлом")
    return value


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


class CompanyDTO(BaseModel):
    """Реквизиты ООО и его руководителя. Руководитель может не совпадать с заявителем."""

    inn: InnStr | None = Field(
        default=None, description="СТИР (ИНН) предприятия.", examples=["305123456"]
    )
    director_full_name: FullNameStr | None = Field(
        default=None, examples=["Каримов Бахтиёр Рустамович"]
    )
    director_passport: PassportStr | None = Field(default=None, examples=["AB7654321"])
    director_phone: PhoneStr | None = Field(default=None, examples=["+998971234567"])
    director_date_of_birth: date | None = Field(default=None, examples=["1985-11-02"])

    _passport = field_validator("director_passport", mode="before")(_normalize_passport)
    _dob = field_validator("director_date_of_birth")(_date_in_past)


class FounderCreateDTO(BaseModel):
    full_name: FullNameStr = Field(examples=["Усманов Жасур Абдуллаевич"])
    passport_number: PassportStr = Field(examples=["AC1122334"])
    date_of_birth: date = Field(examples=["1990-07-14"])

    _passport = field_validator("passport_number", mode="before")(_normalize_passport)
    _dob = field_validator("date_of_birth")(_date_in_past)


class FounderUpdateDTO(BaseModel):
    full_name: FullNameStr | None = None
    passport_number: PassportStr | None = None
    date_of_birth: date | None = None

    _passport = field_validator("passport_number", mode="before")(_normalize_passport)
    _dob = field_validator("date_of_birth")(_date_in_past)


class FounderDTO(BaseModel):
    id: int
    full_name: str
    passport_number: str
    date_of_birth: date
    created_at: datetime


class LocationDTO(BaseModel):
    lat: Decimal = Field(ge=-90, le=90, examples=[41.311081])
    lng: Decimal = Field(ge=-180, le=180, examples=[69.240562])
    region: str = Field(min_length=2, max_length=255, description="Область.", examples=["Ташкент"])
    district: str = Field(
        min_length=2, max_length=255, description="Район.", examples=["Яккасарайский район"]
    )
    makhalla: str = Field(
        min_length=2, max_length=255, description="Махалля.", examples=["Махалля Кушбеги"]
    )
    address: str | None = Field(
        default=None,
        max_length=500,
        description="Улица, дом (уточнение).",
        examples=["ул. Бабура, 12"],
    )
    confirmed: bool = Field(
        default=False,
        description="Пользователь подтвердил, что это место деятельности, а не текущее местоположение.",
    )


class ProjectDTO(BaseModel):
    """Проект, на который запрашивается финансирование."""

    requested_amount: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
        description="Запрашиваемая сумма, UZS.",
        examples=[150000000],
    )
    loan_term_months: int = Field(
        ge=settings.LOAN_TERM_MIN_MONTHS,
        le=settings.LOAN_TERM_MAX_MONTHS,
        description=(
            f"Срок кредита в месяцах: от {settings.LOAN_TERM_MIN_MONTHS} "
            f"до {settings.LOAN_TERM_MAX_MONTHS}."
        ),
        examples=[24],
    )
    total_cost: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
        description="Общая стоимость проекта, UZS (не меньше запрашиваемой суммы).",
        examples=[200000000],
    )
    jobs_count: int = Field(
        ge=0, le=10000, description="Сколько рабочих мест будет создано.", examples=[5]
    )
    description: str = Field(
        min_length=20,
        max_length=4000,
        description="Описание проекта: на что пойдут средства.",
        examples=["Открытие швейного цеха: закупка 10 машин и аренда помещения на 12 месяцев."],
    )

    @field_validator("total_cost")
    @classmethod
    def _amount_within_cost(cls, value: Decimal, info: ValidationInfo) -> Decimal:
        requested = info.data.get("requested_amount")
        if requested is not None and requested > value:
            raise ValueError("Запрашиваемая сумма не может превышать общую стоимость проекта")
        return value


class ProjectResponseDTO(BaseModel):
    requested_amount: Decimal | None = None
    loan_term_months: int | None = None
    total_cost: Decimal | None = None
    jobs_count: int | None = None
    description: str | None = None


class LocationResponseDTO(BaseModel):
    lat: Decimal | None = None
    lng: Decimal | None = None
    region: str | None = None
    district: str | None = None
    makhalla: str | None = None
    address: str | None = None
    confirmed: bool = False


class PhotoDTO(BaseModel):
    id: int
    file_name: str
    content_type: str
    size: int
    url: str
    created_at: datetime


class DocumentDTO(BaseModel):
    id: int
    file_name: str
    content_type: str
    size: int
    url: str
    created_at: datetime


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
    subject_type: SubjectType | None = None
    legal_name: LegalNameStr | None = None
    company: CompanyDTO | None = Field(
        default=None,
        description="Реквизиты предприятия и руководителя (только для ООО).",
    )
    founders: list[FounderCreateDTO] | None = Field(
        default=None,
        description="Учредители (только для ООО, хотя бы один).",
    )


class ApplicationUpdateDTO(BaseModel):
    subject_type: SubjectType | None = None
    legal_name: LegalNameStr | None = None
    company: CompanyDTO | None = Field(
        default=None,
        description="Передаются только изменяемые поля; `null` очищает поле.",
    )


class ApplicationFilterDTO(BaseModel):
    status: ApplicationStatus | None = None
    statuses: list[ApplicationStatus] | None = None
    bank_id: int | None = None
    subject_type: SubjectType | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = None
    scoring_retry_required: bool | None = None


class ScoringResultRecordDTO(BaseModel):
    """Ручное внесение результата KATM (режим manual или после техошибки)."""

    result: ScoringResult
    eligibility_passed: bool | None = Field(
        default=None,
        description="Результат проверки требований Фонда. Нужен только при result=PASSED.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        examples=[{"check": "credit_history", "reason": "Просроченная задолженность > 90 дней"}],
    )
    error_message: str | None = None


class BankDecisionDTO(BaseModel):
    decision: BankDecision
    reason: ReasonStr | None = Field(default=None, description="Обязательна при отказе.")


class ApplicationBankDTO(BaseModel):
    """Выбор банка заявителем (отдельный шаг черновика)."""

    bank_id: int = Field(examples=[1])


class SendToBankDTO(BaseModel):
    """Фонд направляет заявку в банк после успешного скоринга."""

    bank_id: int = Field(examples=[1])
    comment: str | None = None


class SendToCouncilDTO(BaseModel):
    council_member_ids: list[int] | None = Field(
        default=None,
        description="Кому направить. Пусто — всем активным членам Совета.",
    )
    comment: str | None = None


class CouncilDecisionDTO(BaseModel):
    decision: CouncilDecision
    reason: ReasonStr | None = Field(default=None, description="Обязательна при «Отклоняю».")


class ResourceAllocationCreateDTO(BaseModel):
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    reference_number: str | None = Field(default=None, max_length=100)
    details: str | None = None


class CompleteApplicationDTO(BaseModel):
    comment: str | None = None


# ---------- ответы ----------


class ApplicationListItemDTO(BaseModel):
    id: int
    number: str
    status: ApplicationStatus
    subject_type: SubjectType | None = None
    legal_name: str | None = None
    bank: BankDTO | None = None
    applicant_full_name: str | None = None
    scoring_retry_required: bool = False
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationDetailDTO(ApplicationListItemDTO):
    applicant_id: int
    applicant: ApplicantSnapshotDTO
    company: CompanyDTO
    founders: list[FounderDTO] = []
    project: ProjectResponseDTO
    location: LocationResponseDTO
    photos: list[PhotoDTO] = []
    documents: list[DocumentDTO] = []
    bank_stage: BankStageDTO
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
    subject_type: SubjectType | None = None
    legal_name: str | None = None
    bank: BankDTO | None = None
    company: CompanyDTO
    founders_count: int
    project: ProjectResponseDTO
    location: LocationResponseDTO
    photos_count: int
    max_photos: int
    documents_count: int
    max_documents: int


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
    subject_type: SubjectType | None = None
    legal_name: str | None = None
    bank_id: int | None = None
    company_inn: str | None = None
    director_full_name: str | None = None
    director_passport: str | None = None
    director_phone: str | None = None
    director_date_of_birth: date | None = None


class FounderAddDTO(BaseModel):
    application_id: int
    full_name: str
    passport_number: str
    date_of_birth: date


class ApplicationPatchDTO(BaseModel):
    """Частичное обновление — только заданные поля."""

    status: ApplicationStatus | None = None
    subject_type: SubjectType | None = None
    legal_name: str | None = None
    bank_id: int | None = None
    location_lat: Decimal | None = None
    location_lng: Decimal | None = None
    location_address: str | None = None
    location_confirmed: bool | None = None
    submitted_at: datetime | None = None
    scoring_retry_required: bool | None = None
    scoring_error_message: str | None = None
    sent_to_bank_at: datetime | None = None
    bank_accepted_by_id: int | None = None
    bank_accepted_at: datetime | None = None
    bank_decision: BankDecision | None = None
    bank_decision_reason: str | None = None
    bank_decided_by_id: int | None = None
    bank_decided_at: datetime | None = None
    sent_to_council_at: datetime | None = None
    sent_to_council_by_id: int | None = None
    council_decided_at: datetime | None = None
    council_reject_reason: str | None = None
    completed_at: datetime | None = None


class PhotoAddDTO(BaseModel):
    application_id: int
    file_name: str
    storage_path: str
    content_type: str
    size: int


class DocumentAddDTO(PhotoAddDTO):
    pass


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
