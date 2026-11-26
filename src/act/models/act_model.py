"""Договоры исполнителей и акты выполненных работ (dalolatnoma).

Договор (`contracts`) заводит Фонд: исполнитель (пользователь с ролью «Ijrochi»),
номер и дата, предмет, срок и руководитель, который принимает работы и подписывает
акты (`approver`). Исполнитель по договору составляет акты за периоды: строки
выполненных работ (`act_items`) и скриншоты приложения (`act_attachments`).

Подписи (`act_signatures`) — по одной на роль: исполнитель («Topshiruvchi») при
отправке и руководитель («Qabul qiluvchi») при утверждении, ключом E-IMZO, с
реквизитами сертификата и SHA-256 подписанного содержимого. История —
`act_events`. Ф.И.О. копируются в строки, чтобы документ пережил удаление учётки.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.act.enums import ActEventType, ActSignerRole, ActStatus, ContractStatus
from src.database import Base, TimestampMixin

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM


class ContractORM(TimestampMixin, Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    signed_on: Mapped[date] = mapped_column(Date, nullable=False)

    contractor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Как исполнитель назван в акте: «Ahmadjonov Ziyodbek».
    contractor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str | None] = mapped_column(String(255))
    # Предмет договора — вводная часть акта («... bo‘yicha quyidagi xizmatlarni bajardi»).
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))

    approver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Как руководитель назван в акте: «Quldoshov Mirzobek» и его должность.
    approver_name: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_title: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="contract_status"),
        nullable=False,
        default=ContractStatus.ACTIVE,
        index=True,
    )
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    contractor: Mapped["UserORM | None"] = relationship(
        foreign_keys=[contractor_id], lazy="selectin"
    )
    approver: Mapped["UserORM | None"] = relationship(foreign_keys=[approver_id], lazy="selectin")


class ActORM(TimestampMixin, Base):
    __tablename__ = "acts"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Официальный номер DAL-<год>-<id>, присваивается сразу после создания.
    number: Mapped[str | None] = mapped_column(String(32), unique=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    contract_id: Mapped[int] = mapped_column(
        ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    period_from: Mapped[date] = mapped_column(Date, nullable=False)
    period_to: Mapped[date] = mapped_column(Date, nullable=False)
    act_date: Mapped[date] = mapped_column(Date, nullable=False)
    intro: Mapped[str] = mapped_column(Text, nullable=False)
    appendix_title: Mapped[str] = mapped_column(String(500), nullable=False)

    status: Mapped[ActStatus] = mapped_column(
        Enum(ActStatus, name="act_status"), nullable=False, index=True
    )
    # SHA-256 содержимого на момент отправки (договор, период, строки, файлы приложения).
    content_hash: Mapped[str | None] = mapped_column(String(64))

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    return_comment: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)

    # Итоговый PDF подписанного акта: формируется один раз и больше не меняется.
    final_pdf_path: Mapped[str | None] = mapped_column(String(512))
    final_pdf_sha256: Mapped[str | None] = mapped_column(String(64))

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    contract: Mapped["ContractORM"] = relationship(lazy="selectin")
    items: Mapped[list["ActItemORM"]] = relationship(
        back_populates="act",
        cascade="all, delete-orphan",
        order_by="(ActItemORM.position, ActItemORM.id)",
        lazy="selectin",
    )
    attachments: Mapped[list["ActAttachmentORM"]] = relationship(
        back_populates="act",
        cascade="all, delete-orphan",
        order_by="(ActAttachmentORM.position, ActAttachmentORM.id)",
        lazy="selectin",
    )
    signatures: Mapped[list["ActSignatureORM"]] = relationship(
        back_populates="act",
        cascade="all, delete-orphan",
        order_by="ActSignatureORM.id",
        lazy="selectin",
    )
    events: Mapped[list["ActEventORM"]] = relationship(
        back_populates="act",
        cascade="all, delete-orphan",
        order_by="ActEventORM.id",
        lazy="selectin",
    )


class ActItemORM(Base):
    """Строка таблицы выполненных работ."""

    __tablename__ = "act_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    act_id: Mapped[int] = mapped_column(
        ForeignKey("acts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    period_text: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))

    act: Mapped["ActORM"] = relationship(back_populates="items")


class ActAttachmentORM(Base):
    """Скриншот приложения к акту: картинка, подпись и (необязательно) адрес страницы."""

    __tablename__ = "act_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    act_id: Mapped[int] = mapped_column(
        ForeignKey("acts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    caption: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))

    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    act: Mapped["ActORM"] = relationship(back_populates="attachments")


class ActSignatureORM(Base):
    """Подпись акта ключом E-IMZO: одна на роль."""

    __tablename__ = "act_signatures"
    __table_args__ = (UniqueConstraint("act_id", "role", name="uq_act_signature_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    act_id: Mapped[int] = mapped_column(
        ForeignKey("acts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[ActSignerRole] = mapped_column(
        Enum(ActSignerRole, name="act_signer_role"), nullable=False
    )
    signer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    signer_full_name: Mapped[str | None] = mapped_column(String(255))
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    cert_pinfl: Mapped[str | None] = mapped_column(String(14))
    cert_full_name: Mapped[str | None] = mapped_column(String(255))
    cert_serial_number: Mapped[str | None] = mapped_column(String(128))
    cert_valid_from: Mapped[str | None] = mapped_column(String(32))
    cert_valid_to: Mapped[str | None] = mapped_column(String(32))
    cert_tin: Mapped[str | None] = mapped_column(String(16))
    eimzo_request_id: Mapped[str | None] = mapped_column(String(128))
    # SHA-256 того, что подписано: хэш содержимого акта, роль, подписант, время
    # (у руководителя — ещё и хэш подписи исполнителя).
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    act: Mapped["ActORM"] = relationship(back_populates="signatures")


class ActEventORM(Base):
    """История акта: кто, когда и что сделал."""

    __tablename__ = "act_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    act_id: Mapped[int] = mapped_column(
        ForeignKey("acts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event: Mapped[ActEventType] = mapped_column(
        Enum(ActEventType, name="act_event_type"), nullable=False
    )
    from_status: Mapped[ActStatus | None] = mapped_column(
        Enum(ActStatus, name="act_status", create_type=False)
    )
    to_status: Mapped[ActStatus] = mapped_column(
        Enum(ActStatus, name="act_status", create_type=False), nullable=False
    )
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_name: Mapped[str | None] = mapped_column(String(255))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    act: Mapped["ActORM"] = relationship(back_populates="events")
