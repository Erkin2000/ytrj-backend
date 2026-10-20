from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM
    from src.application.models.application_model import ApplicationORM


class ResourceAllocationORM(Base):
    """Факт выделения ресурсов, зафиксированный сотрудником Фонда.
    Открытие счёта и перечисление денег платформой не автоматизированы."""

    __tablename__ = "resource_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="UZS", nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[str | None] = mapped_column(Text)

    allocated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    application: Mapped["ApplicationORM"] = relationship(back_populates="resource_allocation")
    allocated_by: Mapped["UserORM | None"] = relationship(lazy="selectin")
