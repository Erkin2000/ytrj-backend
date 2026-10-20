from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.application.enums import DemandDocumentStatus
from src.database import Base

if TYPE_CHECKING:
    from src.application.models.application_model import ApplicationORM


class DemandDocumentORM(Base):
    """Документ «Требование подтверждено». Создаётся после решения Совета
    «Согласен». Формирование файла (PDF, ЭЦП, QR) — модуль documents."""

    __tablename__ = "demand_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    status: Mapped[DemandDocumentStatus] = mapped_column(
        Enum(DemandDocumentStatus, name="demand_document_status"),
        default=DemandDocumentStatus.CREATED,
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(String(500))
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    application: Mapped["ApplicationORM"] = relationship(back_populates="demand_document")

    def __str__(self) -> str:
        return self.number
