"""Реестр профинансированных проектов — данные для аналитики отдела финансирования.

Программа (ПҚ-60, ПҚ-400, «Кўмак», обучение и инкубация, …) — направление финансирования
с названием на ru / uz / en. Проект — строка реестра: кто, где, сколько запрошено,
выделено и выдано, решение Совета, банк. Проекты загружаются из Excel отдела
(`source = IMPORT`, следующий импорт программы их заменяет) или ведутся через API (`MANUAL`).
Суммы — в сўм.
"""

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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.account.models.user_model import Gender
from src.database import Base, TimestampMixin
from src.product.enums import Language
from src.rbac.models.permission_model import LanguageType
from src.registry.enums import (
    Decision,
    ImportTemplate,
    ProgramKind,
    ProjectStatus,
    RegistrySubjectType,
    Sector,
    Source,
)

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM


def _enum(cls, name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


ProgramKindType = _enum(ProgramKind, "registry_program_kind")
ImportTemplateType = _enum(ImportTemplate, "registry_import_template")
ProjectStatusType = _enum(ProjectStatus, "registry_project_status")
DecisionType = _enum(Decision, "registry_decision")
SubjectTypeType = _enum(RegistrySubjectType, "registry_subject_type")
SectorType = _enum(Sector, "registry_sector")
SourceType = _enum(Source, "registry_source")
GenderType = _enum(Gender, "registry_gender")

MONEY = Numeric(20, 2)


class RegistryProgramORM(TimestampMixin, Base):
    __tablename__ = "registry_programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    kind: Mapped[ProgramKind] = mapped_column(ProgramKindType, nullable=False)
    import_template: Mapped[ImportTemplate | None] = mapped_column(ImportTemplateType)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Последний импорт: файл и время — для подписи «данные на …».
    last_import_file: Mapped[str | None] = mapped_column(String(255))
    last_import_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    translations: Mapped[list["RegistryProgramTranslationORM"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="RegistryProgramTranslationORM.language",
        lazy="selectin",
    )

    def __str__(self) -> str:
        for t in self.translations:
            if t.language == Language.RU:
                return t.name
        return self.code


class RegistryProgramTranslationORM(Base):
    __tablename__ = "registry_program_translations"
    __table_args__ = (UniqueConstraint("program_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("registry_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    program: Mapped["RegistryProgramORM"] = relationship(back_populates="translations")


class RegistryProjectORM(TimestampMixin, Base):
    __tablename__ = "registry_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("registry_programs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source: Mapped[Source] = mapped_column(SourceType, nullable=False, index=True)
    number: Mapped[int | None] = mapped_column(Integer)  # № в файле отдела

    # кто
    applicant_name: Mapped[str] = mapped_column(String(500), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(500))  # МЧЖ / ЯТТ / название проекта
    tin: Mapped[str | None] = mapped_column(String(20), index=True)  # СТИР или ПИНФЛ
    subject_type: Mapped[RegistrySubjectType | None] = mapped_column(SubjectTypeType, index=True)
    head_info: Mapped[str | None] = mapped_column(
        Text
    )  # руководитель: Ф.И.Ш., паспорт, дата рождения
    gender: Mapped[Gender | None] = mapped_column(GenderType, index=True)
    age: Mapped[int | None] = mapped_column(Integer)
    phone: Mapped[str | None] = mapped_column(String(100))

    # где
    region: Mapped[str | None] = mapped_column(String(30), index=True)  # код из справочника
    district: Mapped[str | None] = mapped_column(String(255))
    district_key: Mapped[str | None] = mapped_column(String(255), index=True)
    mahalla: Mapped[str | None] = mapped_column(String(255))

    # что
    purpose: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[Sector | None] = mapped_column(SectorType, index=True)
    direction: Mapped[str | None] = mapped_column(String(255), index=True)  # «Тикувчилик», «Савдо»…
    jobs: Mapped[int | None] = mapped_column(Integer)  # планируемые рабочие места

    # деньги (сўм)
    project_cost: Mapped[Decimal | None] = mapped_column(MONEY)
    requested_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    allocated_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    credit_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    term_months: Mapped[int | None] = mapped_column(Integer)
    collateral: Mapped[str | None] = mapped_column(String(255))

    # банк
    bank: Mapped[str | None] = mapped_column(String(30), index=True)  # код из справочника
    bank_branch: Mapped[str | None] = mapped_column(String(255))
    bank_letter_date: Mapped[date | None] = mapped_column(Date)
    bank_request: Mapped[str | None] = mapped_column(String(255))  # талабнома: дата и номер
    order_info: Mapped[str | None] = mapped_column(String(255))  # приказ в финотдел

    # решение
    application_date: Mapped[date | None] = mapped_column(Date, index=True)
    decision: Mapped[Decision | None] = mapped_column(DecisionType)
    council_protocol: Mapped[str | None] = mapped_column(String(255))
    council_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[ProjectStatus] = mapped_column(ProjectStatusType, nullable=False, index=True)

    note: Mapped[str | None] = mapped_column(Text)
    # Колонки файла, у которых нет своего поля (как есть).
    extra: Mapped[dict | None] = mapped_column(JSONB)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    program: Mapped["RegistryProgramORM"] = relationship(lazy="selectin")
    created_by: Mapped["UserORM | None"] = relationship(
        foreign_keys="RegistryProjectORM.created_by_id", lazy="selectin"
    )
    updated_by: Mapped["UserORM | None"] = relationship(
        foreign_keys="RegistryProjectORM.updated_by_id", lazy="selectin"
    )

    def __str__(self) -> str:
        return self.applicant_name
