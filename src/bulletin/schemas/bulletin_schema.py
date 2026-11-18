from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from src.application.enums import ApplicationStatus
from src.application.schemas.application_schema import ActorDTO, ReasonStr
from src.bulletin.enums import (
    TASHKENT_TZ,
    BulletinDecision,
    BulletinStatus,
    CalendarEventType,
    MemberBulletinStatus,
)

NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=255)]
DescriptionStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)
]
CommentStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]

DATETIME_HINT = "Дата и время ISO 8601; без часового пояса — по Ташкенту (UTC+5)."


def as_aware(value: datetime | None) -> datetime | None:
    """Время без часового пояса считается ташкентским."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=TASHKENT_TZ)
    return value


# ---------- запросы ----------


class BulletinCreateForm(BaseModel):
    """Поля формы создания бюллетеня (multipart/form-data, файл — полем `file`)."""

    name: NameStr = Field(description="Название бюллетеня.")
    description: DescriptionStr = Field(description="Описание / текст бюллетеня.")
    status: Literal[BulletinStatus.PENDING, BulletinStatus.PUBLISHED] = Field(
        default=BulletinStatus.PUBLISHED,
        description=(
            "`PUBLISHED` — отправить членам Совета сразу; `PENDING` — отправить автоматически "
            "в `send_at`."
        ),
    )
    send_at: datetime | None = Field(
        default=None,
        description=f"Дата отправки членам Совета; обязательна для `PENDING`. {DATETIME_HINT}",
    )
    deadline_at: datetime = Field(description=f"Срок подписания. {DATETIME_HINT}")
    application_id: int | None = Field(
        default=None,
        description=(
            "Заявка на рассмотрении Фонда (FUND_REVIEW), если бюллетень относится к ней. "
            "Заявка сразу переходит в COUNCIL_REVIEW, решения по бюллетеню решают заявку."
        ),
    )

    file: UploadFile | None = Field(default=None, description="PDF или DOCX, до 10 МБ.")

    _aware = field_validator("send_at", "deadline_at")(as_aware)


class BulletinUpdateDTO(BaseModel):
    """До отправки (PENDING) меняется всё; после отправки — только срок подписания."""

    model_config = ConfigDict(extra="forbid")

    name: NameStr | None = None
    description: DescriptionStr | None = None
    send_at: datetime | None = Field(default=None, description=DATETIME_HINT)
    deadline_at: datetime | None = Field(default=None, description=DATETIME_HINT)

    _aware = field_validator("send_at", "deadline_at")(as_aware)


class BulletinCancelDTO(BaseModel):
    reason: ReasonStr = Field(description="Причина аннулирования.")


class BulletinSignDTO(BaseModel):
    decision: BulletinDecision = Field(description="`AGREE` — «Согласен», `AGAINST` — «Против».")
    comment: CommentStr | None = Field(default=None, description="Комментарий к решению.")
    code: str = Field(
        min_length=1,
        max_length=512,
        description=(
            "Одноразовый code страницы-моста E-IMZO, полученный при подписании (60 секунд). "
            "ПИНФЛ сертификата должен совпадать с ПИНФЛ члена Совета. "
            "При `EIMZO_MOCK=true` — `mock-<ПИНФЛ>`."
        ),
    )


class BulletinFilterDTO(BaseModel):
    status: BulletinStatus | None = None
    application_id: int | None = None
    search: str | None = Field(default=None, description="Номер или название.")


# ---------- ответы ----------


class BulletinFileDTO(BaseModel):
    name: str
    content_type: str
    size: int
    sha256: str
    url: str | None = None


class BulletinApplicationDTO(BaseModel):
    id: int
    number: str | None = None
    status: ApplicationStatus
    applicant_full_name: str | None = None
    url: str


class SignaturesSummaryDTO(BaseModel):
    total: int
    signed: int
    pending: int
    agree: int
    against: int


class CertificateDTO(BaseModel):
    pinfl: str | None = None
    full_name: str | None = None
    serial_number: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None


class BulletinSignatureDTO(BaseModel):
    """Строка подписи для Фонда: кто подписал, а кто нет."""

    id: int
    member: ActorDTO | None = None
    member_full_name: str | None = None
    status: MemberBulletinStatus
    viewed_at: datetime | None = None
    file_viewed_at: datetime | None = None
    decision: BulletinDecision | None = None
    comment: str | None = None
    signed_at: datetime | None = None
    certificate: CertificateDTO | None = None
    document_hash: str | None = None


class BulletinListItemDTO(BaseModel):
    id: int
    number: str | None = None
    name: str
    status: BulletinStatus
    send_at: datetime
    published_at: datetime | None = None
    deadline_at: datetime
    is_overdue: bool
    has_file: bool
    application: BulletinApplicationDTO | None = None
    signatures: SignaturesSummaryDTO
    created_at: datetime


class BulletinDetailDTO(BulletinListItemDTO):
    public_id: str
    description: str
    file: BulletinFileDTO | None = None
    signature_list: list[BulletinSignatureDTO]
    created_by: ActorDTO | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancelled_by: ActorDTO | None = None
    cancel_reason: str | None = None
    verify_url: str
    qr_url: str


class MySignatureDTO(BaseModel):
    """Личный статус члена Совета (чужие подписи ему не показываются)."""

    status: MemberBulletinStatus
    viewed_at: datetime | None = None
    file_viewed_at: datetime | None = None
    decision: BulletinDecision | None = None
    comment: str | None = None
    signed_at: datetime | None = None
    certificate: CertificateDTO | None = None
    can_sign: bool
    sign_blockers: list[str] = Field(
        description=(
            "Почему подписать пока нельзя: `bulletin_not_viewed`, `bulletin_file_not_viewed`, "
            "`already_signed`, `deadline_passed`, `not_open_for_signing`."
        )
    )


class CouncilBulletinItemDTO(BaseModel):
    id: int
    number: str | None = None
    name: str
    status: BulletinStatus
    published_at: datetime | None = None
    deadline_at: datetime
    has_file: bool
    application: BulletinApplicationDTO | None = None
    my_status: MemberBulletinStatus
    my_decision: BulletinDecision | None = None
    signed_at: datetime | None = None


class CouncilBulletinDetailDTO(CouncilBulletinItemDTO):
    description: str
    file: BulletinFileDTO | None = None
    created_at: datetime
    my: MySignatureDTO
    verify_url: str


class CalendarEventDTO(BaseModel):
    type: CalendarEventType
    at: datetime
    bulletin_id: int
    number: str | None = None
    name: str
    status: BulletinStatus
    my_status: MemberBulletinStatus | None = None


class CalendarDayDTO(BaseModel):
    date: date
    events: list[CalendarEventDTO]


# ---------- публичная проверка по QR ----------


class VerifySignerDTO(BaseModel):
    full_name: str | None = None
    signed: bool


class BulletinVerifyDTO(BaseModel):
    document_type: str = "Бюллетень члена Совета"
    number: str | None = None
    name: str
    description: str
    bulletin_date: date = Field(description="Дата создания бюллетеня (по Ташкенту).")
    status: BulletinStatus
    validity: Literal["VALID", "CANCELLED"]
    file: BulletinFileDTO | None = None
    signers: list[VerifySignerDTO]
    signed_count: int
    total_count: int
