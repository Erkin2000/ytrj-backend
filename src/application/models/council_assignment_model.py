from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.application.enums import CouncilDecision
from src.database import Base

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM
    from src.application.models.application_model import ApplicationORM


class CouncilAssignmentORM(Base):
    """Заявка, направленная конкретному члену Совета, и его решение."""

    __tablename__ = "application_council_assignments"
    __table_args__ = (
        UniqueConstraint("application_id", "council_member_id", name="uq_council_assignment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    council_member_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    decision: Mapped[CouncilDecision | None] = mapped_column(
        Enum(CouncilDecision, name="council_decision"),
    )
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    application: Mapped["ApplicationORM"] = relationship(back_populates="council_assignments")
    council_member: Mapped["UserORM"] = relationship(
        foreign_keys=[council_member_id], lazy="selectin"
    )
    assigned_by: Mapped["UserORM | None"] = relationship(foreign_keys=[assigned_by_id])
