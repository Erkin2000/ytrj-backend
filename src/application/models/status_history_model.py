from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.application.enums import ApplicationStatus
from src.database import Base

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM
    from src.application.models.application_model import ApplicationORM


class StatusHistoryORM(Base):
    """Хронологическая история заявки: кто, когда, какой этап, комментарий.
    Записи только добавляются — редактирование и удаление не предусмотрены."""

    __tablename__ = "application_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[ApplicationStatus | None] = mapped_column(
        Enum(ApplicationStatus, name="application_status", create_type=False),
    )
    to_status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status", create_type=False),
        nullable=False,
    )
    # Код события для фронтенда/уведомлений: created, submitted, scoring_passed, ...
    event: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_role: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    application: Mapped["ApplicationORM"] = relationship(back_populates="status_history")
    actor: Mapped["UserORM | None"] = relationship(lazy="selectin")
