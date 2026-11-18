"""Бюллетень Совета: документ Фонда, который подписывают ЭЦП все активные члены Совета.

Бюллетень может ссылаться на заявку (тогда решения членов Совета по нему решают
заявку: любое «Против» → COUNCIL_REJECTED, «Согласен» всех → COUNCIL_APPROVED и
отправка в банк), а может быть самостоятельным. К нему прикрепляется один файл
PDF или DOCX. `public_id` — неугадываемый идентификатор страницы проверки по QR.

Получатели фиксируются при отправке строками `bulletin_signatures` (по одной на
члена Совета): просмотр, решение, подпись и реквизиты сертификата E-IMZO.
Ф.И.О. члена копируется в строку, чтобы история подписи пережила удаление учётки.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.bulletin.enums import BulletinDecision, BulletinStatus
from src.database import Base, TimestampMixin

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM
    from src.application.models.application_model import ApplicationORM


class BulletinORM(TimestampMixin, Base):
    __tablename__ = "bulletins"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Официальный номер BYU-<год>-<id>, присваивается сразу после создания.
    number: Mapped[str | None] = mapped_column(String(32), unique=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )

    status: Mapped[BulletinStatus] = mapped_column(
        Enum(BulletinStatus, name="bulletin_status"),
        nullable=False,
        index=True,
    )
    # Плановая (PENDING) или фактическая дата отправки членам Совета.
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Срок подписания.
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    file_path: Mapped[str | None] = mapped_column(String(512))
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_content_type: Mapped[str | None] = mapped_column(String(128))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    file_sha256: Mapped[str | None] = mapped_column(String(64))

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    published_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    cancel_reason: Mapped[str | None] = mapped_column(Text)

    application: Mapped["ApplicationORM | None"] = relationship(lazy="selectin")
    created_by: Mapped["UserORM | None"] = relationship(
        foreign_keys=[created_by_id], lazy="selectin"
    )
    cancelled_by: Mapped["UserORM | None"] = relationship(
        foreign_keys=[cancelled_by_id], lazy="selectin"
    )
    signatures: Mapped[list["BulletinSignatureORM"]] = relationship(
        back_populates="bulletin",
        cascade="all, delete-orphan",
        order_by="BulletinSignatureORM.id",
        lazy="selectin",
    )


class BulletinSignatureORM(Base):
    """Получатель бюллетеня (член Совета) и его подпись."""

    __tablename__ = "bulletin_signatures"
    __table_args__ = (
        UniqueConstraint("bulletin_id", "council_member_id", name="uq_bulletin_signature_member"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bulletin_id: Mapped[int] = mapped_column(
        ForeignKey("bulletins.id", ondelete="CASCADE"), nullable=False, index=True
    )
    council_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    member_full_name: Mapped[str | None] = mapped_column(String(255))
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    file_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    decision: Mapped[BulletinDecision | None] = mapped_column(
        Enum(BulletinDecision, name="bulletin_decision")
    )
    comment: Mapped[str | None] = mapped_column(Text)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Реквизиты сертификата E-IMZO, которым подписано решение.
    cert_pinfl: Mapped[str | None] = mapped_column(String(14))
    cert_full_name: Mapped[str | None] = mapped_column(String(255))
    cert_serial_number: Mapped[str | None] = mapped_column(String(128))
    cert_valid_from: Mapped[str | None] = mapped_column(String(32))
    cert_valid_to: Mapped[str | None] = mapped_column(String(32))
    cert_tin: Mapped[str | None] = mapped_column(String(16))
    eimzo_request_id: Mapped[str | None] = mapped_column(String(128))
    # SHA-256 подписанного содержимого: реквизиты бюллетеня, хэш файла, решение.
    document_hash: Mapped[str | None] = mapped_column(String(64))

    bulletin: Mapped["BulletinORM"] = relationship(back_populates="signatures")
    council_member: Mapped["UserORM | None"] = relationship(lazy="selectin")
