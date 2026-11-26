from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.act.enums import (
    ActEventType,
    ActSignerRole,
    ActStatus,
    ContractStatus,
    FundActTab,
)
from src.application.schemas.application_schema import ReasonStr
from src.config import settings

NumberStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]
TextStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=4000)]
ShortStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
NoteStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
CaptionStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
UrlStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
TitleStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
CodeStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]

DEFAULT_APPROVER_TITLE = "ijrochi direktori"
DEFAULT_APPENDIX_TITLE = "Ilova: bajarilgan ishlarni tasdiqlovchi skrinshotlar"


# ---------- договоры: запросы ----------


class ContractCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: NumberStr = Field(description="Номер договора (уникален).")
    signed_on: date = Field(description="Дата договора.")
    contractor_id: int = Field(
        description="Исполнитель: активный пользователь с ролью CONTRACTOR и ПИНФЛ."
    )
    contractor_name: NameStr | None = Field(
        default=None,
        description="Как исполнитель назван в акте («Ahmadjonov Ziyodbek»); по умолчанию — из Ф.И.О.",
    )
    position: NameStr | None = Field(default=None, description="Роль в проекте (PM, Frontend…).")
    subject: TextStr = Field(
        description="Предмет договора: вводная часть акта («… bo‘yicha quyidagi xizmatlarni bajardi»)."
    )
    start_date: date = Field(description="Начало срока договора.")
    end_date: date = Field(description="Конец срока договора (включительно).")
    amount: Decimal | None = Field(default=None, ge=0, description="Сумма договора, сўм.")
    approver_id: int = Field(
        description="Руководитель, который подписывает акты: право act_signing.approve и ПИНФЛ."
    )
    approver_name: NameStr | None = Field(
        default=None,
        description="Как руководитель назван в акте («Quldoshov Mirzobek»); по умолчанию — из Ф.И.О.",
    )
    approver_title: NameStr = Field(
        default=DEFAULT_APPROVER_TITLE, description="Должность руководителя в акте."
    )


class ContractUpdateDTO(BaseModel):
    """Номер, дата, исполнитель, сроки и руководитель меняются, пока по договору нет
    подписанных актов; статус и сумма — всегда."""

    model_config = ConfigDict(extra="forbid")

    number: NumberStr | None = None
    signed_on: date | None = None
    contractor_id: int | None = None
    contractor_name: NameStr | None = None
    position: NameStr | None = None
    subject: TextStr | None = None
    start_date: date | None = None
    end_date: date | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    approver_id: int | None = None
    approver_name: NameStr | None = None
    approver_title: NameStr | None = None
    status: ContractStatus | None = Field(
        default=None, description="CLOSED — новых актов по договору нет."
    )


class ContractFilterDTO(BaseModel):
    status: ContractStatus | None = None
    contractor_id: int | None = None
    search: str | None = Field(default=None, description="Номер договора или исполнитель.")


# ---------- акты: запросы ----------


class ActCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: int = Field(description="Свой активный договор.")
    period_from: date = Field(description="Начало периода работ.")
    period_to: date = Field(description="Конец периода работ (включительно).")
    act_date: date | None = Field(
        default=None, description="Дата акта; по умолчанию — конец периода."
    )
    copy_from_id: int | None = Field(
        default=None,
        description="Свой акт по тому же договору: скопировать вводную часть, строки и заголовок "
        "приложения (без файлов).",
    )


class ActUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_from: date | None = None
    period_to: date | None = None
    act_date: date | None = None
    intro: TextStr | None = Field(default=None, description="Вводная часть (предмет работ).")
    appendix_title: TitleStr | None = None


class ActItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: TextStr = Field(description="Содержание выполненной работы.")
    period_text: ShortStr = Field(description="Срок выполнения («3-noyabr – 13-noyabr»).")
    note: NoteStr | None = Field(default=None, description="Примечание (колонка «Izoh»).")


class ActItemsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ActItemIn] = Field(
        max_length=settings.ACT_MAX_ITEMS,
        description="Все строки таблицы по порядку: список заменяется целиком.",
    )


class ActAttachmentForm(BaseModel):
    caption: CaptionStr = Field(description="Подпись под скриншотом.")
    url: UrlStr | None = Field(default=None, description="Адрес страницы на скриншоте.")
    file: UploadFile = Field(description="JPEG или PNG, до 5 МБ.")


class ActAttachmentUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caption: CaptionStr | None = None
    url: UrlStr | None = None


class ActAttachmentOrderDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[int] = Field(description="id всех файлов приложения в новом порядке.")


class ActSignDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: CodeStr = Field(description="Одноразовый код моста E-IMZO (живёт 60 секунд).")


class ActReturnDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: ReasonStr = Field(description="Что исправить: увидит исполнитель.")


class ActCancelDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: ReasonStr = Field(description="Причина аннулирования.")


class MyActFilterDTO(BaseModel):
    status: ActStatus | None = None
    contract_id: int | None = None


class FundActFilterDTO(BaseModel):
    tab: FundActTab = Field(default=FundActTab.ALL, description="Вкладка рабочего окна.")
    status: ActStatus | None = None
    contract_id: int | None = None
    contractor_id: int | None = None
    mine: bool = Field(
        default=False, description="Только акты по договорам, где я — подписывающий руководитель."
    )
    search: str | None = Field(default=None, description="Номер акта, договора или исполнитель.")


# ---------- ответы ----------


class PersonDTO(BaseModel):
    id: int
    full_name: str | None = None


class ContractShortDTO(BaseModel):
    id: int
    number: str
    signed_on: date
    contractor_name: str
    position: str | None = None
    approver_name: str


class ContractDTO(BaseModel):
    id: int
    number: str
    signed_on: date
    contractor: PersonDTO | None = None
    contractor_name: str
    position: str | None = None
    subject: str
    start_date: date
    end_date: date
    amount: Decimal | None = None
    approver: PersonDTO | None = None
    approver_name: str
    approver_title: str
    status: ContractStatus
    acts_count: int = 0
    created_at: datetime


class ActItemDTO(BaseModel):
    id: int
    position: int
    content: str
    period_text: str
    note: str | None = None


class ActAttachmentDTO(BaseModel):
    id: int
    position: int
    caption: str
    url: str | None = None
    file_name: str | None = None
    content_type: str
    size: int
    sha256: str


class ActSignatureDTO(BaseModel):
    role: ActSignerRole
    signer: PersonDTO | None = None
    signer_full_name: str | None = None
    signed_at: datetime
    cert_full_name: str | None = None
    cert_serial_number: str | None = None
    cert_valid_to: str | None = None
    document_hash: str


class ActEventDTO(BaseModel):
    event: ActEventType
    from_status: ActStatus | None = None
    to_status: ActStatus
    actor: PersonDTO | None = None
    actor_name: str | None = None
    comment: str | None = None
    created_at: datetime


class ActActionsDTO(BaseModel):
    """Что текущий пользователь может сделать с актом сейчас."""

    edit: bool = False
    delete: bool = False
    submit: bool = False
    withdraw: bool = False
    accept: bool = False
    send_back: bool = Field(default=False, description="Вернуть исполнителю с замечанием.")
    sign: bool = False
    cancel: bool = False


class ActListItemDTO(BaseModel):
    id: int
    number: str | None = None
    status: ActStatus
    contract: ContractShortDTO
    period_from: date
    period_to: date
    act_date: date
    items_count: int
    attachments_count: int
    submitted_at: datetime | None = None
    accepted_at: datetime | None = None
    signed_at: datetime | None = None
    returned_at: datetime | None = None
    updated_at: datetime


class ActDetailDTO(ActListItemDTO):
    intro: str
    appendix_title: str
    return_comment: str | None = None
    cancel_reason: str | None = None
    cancelled_at: datetime | None = None
    content_hash: str | None = None
    final_pdf_sha256: str | None = None
    items: list[ActItemDTO]
    attachments: list[ActAttachmentDTO]
    signatures: list[ActSignatureDTO]
    events: list[ActEventDTO]
    verify_url: str
    actions: ActActionsDTO


class ActSubmissionCheckDTO(BaseModel):
    ready: bool
    missing: list[str]


class ActVerifySignatureDTO(BaseModel):
    role: ActSignerRole
    name: str | None = None
    signed_at: datetime
    cert_serial_number: str | None = None


class ActVerifyDTO(BaseModel):
    number: str | None = None
    status: ActStatus
    validity: str = Field(
        description="`VALID` — подписан и не менялся; `NOT_SIGNED` — ещё не подписан "
        "руководителем; `CANCELLED` — аннулирован; `MODIFIED` — содержимое не совпадает с подписанным."
    )
    contract_number: str
    contract_signed_on: date
    contractor_name: str
    approver_name: str
    period_from: date
    period_to: date
    act_date: date
    signatures: list[ActVerifySignatureDTO]
    content_unchanged: bool
    pdf_sha256: str | None = None
