from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.account.models.user_model import Gender
from src.application.enums import ApplicationStatus, BankDecision, SubjectType
from src.database import Base, TimestampMixin

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM
    from src.application.models.bank_model import BankORM
    from src.application.models.council_assignment_model import CouncilAssignmentORM
    from src.application.models.demand_document_model import DemandDocumentORM
    from src.application.models.document_model import ApplicationDocumentORM
    from src.application.models.founder_model import ApplicationFounderORM
    from src.application.models.photo_model import ApplicationPhotoORM
    from src.application.models.resource_allocation_model import ResourceAllocationORM
    from src.application.models.scoring_model import ScoringAttemptORM
    from src.application.models.status_history_model import StatusHistoryORM


class ApplicationORM(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    applicant_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # --- Снимок данных заявителя на момент создания / отправки (ТЗ, п. 5-6) ---
    # Ф.И.О. и ПИНФЛ — из YIA SSO; остальное заявитель дополняет в профиле.
    applicant_full_name: Mapped[str | None] = mapped_column(String(255))
    applicant_phone: Mapped[str | None] = mapped_column(String(20))
    applicant_passport: Mapped[str | None] = mapped_column(String(20))
    applicant_pinfl: Mapped[str | None] = mapped_column(String(14))
    applicant_inn: Mapped[str | None] = mapped_column(String(20))
    applicant_email: Mapped[str | None] = mapped_column(String(255))
    applicant_gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, name="gender", create_type=False)
    )
    applicant_date_of_birth: Mapped[date | None] = mapped_column(Date)

    # --- Форма заявки ---
    subject_type: Mapped[SubjectType | None] = mapped_column(
        Enum(SubjectType, name="subject_type"),
    )
    legal_name: Mapped[str | None] = mapped_column(String(255))

    # --- Предприятие и его руководитель (ИП / ООО). Руководитель может не совпадать
    # с заявителем, поэтому данные вводятся отдельно от снимка профиля. ---
    company_inn: Mapped[str | None] = mapped_column(String(20))
    director_full_name: Mapped[str | None] = mapped_column(String(255))
    director_passport: Mapped[str | None] = mapped_column(String(20))
    director_phone: Mapped[str | None] = mapped_column(String(20))
    director_date_of_birth: Mapped[date | None] = mapped_column(Date)

    bank_id: Mapped[int | None] = mapped_column(
        ForeignKey("banks.id", ondelete="RESTRICT"),
        index=True,
    )

    # --- Проект: на что запрашивается финансирование ---
    project_requested_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    project_loan_term_months: Mapped[int | None] = mapped_column(Integer)
    project_total_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    project_jobs_count: Mapped[int | None] = mapped_column(Integer)
    project_description: Mapped[str | None] = mapped_column(Text)

    # Место осуществления деятельности (не текущее местоположение!)
    location_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    location_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    # Административная привязка (справочники появятся позже — пока текст).
    location_region: Mapped[str | None] = mapped_column(String(255))
    location_district: Mapped[str | None] = mapped_column(String(255))
    location_makhalla: Mapped[str | None] = mapped_column(String(255))
    location_address: Mapped[str | None] = mapped_column(String(500))
    location_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Этапы ---
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Техническая ошибка KATM: заявка не отклонена, ждёт повтора.
    scoring_retry_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scoring_error_message: Mapped[str | None] = mapped_column(Text)

    sent_to_bank_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bank_accepted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    bank_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bank_decision: Mapped[BankDecision | None] = mapped_column(
        Enum(BankDecision, name="bank_decision")
    )
    bank_decision_reason: Mapped[str | None] = mapped_column(Text)
    bank_decided_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    bank_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sent_to_council_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_to_council_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    council_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    council_reject_reason: Mapped[str | None] = mapped_column(Text)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Связи ---
    applicant: Mapped["UserORM"] = relationship(foreign_keys=[applicant_id], lazy="selectin")
    bank: Mapped["BankORM | None"] = relationship(lazy="selectin")
    bank_accepted_by: Mapped["UserORM | None"] = relationship(foreign_keys=[bank_accepted_by_id])
    bank_decided_by: Mapped["UserORM | None"] = relationship(foreign_keys=[bank_decided_by_id])
    sent_to_council_by: Mapped["UserORM | None"] = relationship(
        foreign_keys=[sent_to_council_by_id]
    )

    photos: Mapped[list["ApplicationPhotoORM"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationPhotoORM.id",
    )
    documents: Mapped[list["ApplicationDocumentORM"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationDocumentORM.id",
    )
    founders: Mapped[list["ApplicationFounderORM"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationFounderORM.id",
    )
    status_history: Mapped[list["StatusHistoryORM"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="StatusHistoryORM.id",
    )
    scoring_attempts: Mapped[list["ScoringAttemptORM"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ScoringAttemptORM.id",
    )
    council_assignments: Mapped[list["CouncilAssignmentORM"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="CouncilAssignmentORM.id",
    )
    demand_document: Mapped["DemandDocumentORM | None"] = relationship(
        back_populates="application",
        uselist=False,
    )
    resource_allocation: Mapped["ResourceAllocationORM | None"] = relationship(
        back_populates="application",
        uselist=False,
    )

    def __str__(self) -> str:
        return self.number
