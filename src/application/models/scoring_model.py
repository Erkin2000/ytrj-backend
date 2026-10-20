from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.application.enums import ScoringResult
from src.database import Base

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM
    from src.application.models.application_model import ApplicationORM


class ScoringAttemptORM(Base):
    """Попытка скоринга KATM + проверка требований Фонда (eligibility).

    details хранит полную внутреннюю причину (по какой проверке и почему):
    её видят только Фонд и Super Admin. Заявителю уходит общее сообщение.
    """

    __tablename__ = "application_scoring_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="KATM")
    result: Mapped[ScoringResult] = mapped_column(
        Enum(ScoringResult, name="scoring_result"),
        nullable=False,
    )
    eligibility_passed: Mapped[bool | None]
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Кто внёс результат вручную (None — автоматический режим)
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    application: Mapped["ApplicationORM"] = relationship(back_populates="scoring_attempts")
    recorded_by: Mapped["UserORM | None"] = relationship(lazy="selectin")
