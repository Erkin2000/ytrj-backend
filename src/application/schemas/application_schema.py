from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints

from src.application.enums import (
    ApplicationStatus,
    BankDecision,
    CouncilDecision,
    DemandDocumentStatus,
    ScoringResult,
    SubjectType,
)
from src.application.schemas.bank_schema import BankDTO

LegalNameStr = Annotated[str, StringConstraints(min_length=2, max_length=255)]
ReasonStr = Annotated[str, StringConstraints(min_length=3, max_length=2000)]


# ---------- вложенные ----------


class ApplicantSnapshotDTO(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    passport_number: str | None = None
    pinfl: str | None = None
    inn: str | None = None


class LocationDTO(BaseModel):
    lat: Decimal = Field(ge=-90, le=90, examples=[41.311081])
    lng: Decimal = Field(ge=-180, le=180, examples=[69.240562])
    address: str | None = Field(default=None, max_length=500)
    confirmed: bool = Field(
        default=False,
        description="Пользователь подтвердил, что это место деятельности, а не текущее местоположение.",
    )


class LocationResponseDTO(BaseModel):
    lat: Decimal | None = None
    lng: Decimal | None = None
    address: str | None = None
    confirmed: bool = False


class PhotoDTO(BaseModel):
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
    bank_id: int | None = None


class ApplicationUpdateDTO(BaseModel):
    subject_type: SubjectType | None = None
    legal_name: LegalNameStr | None = None
    bank_id: int | None = None


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
    location: LocationResponseDTO
    photos: list[PhotoDTO] = []
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
    location: LocationResponseDTO
    photos_count: int
    max_photos: int


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
    subject_type: SubjectType | None = None
    legal_name: str | None = None
    bank_id: int | None = None


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
