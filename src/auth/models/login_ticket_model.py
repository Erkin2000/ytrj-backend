from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class LoginTicketORM(Base):
    """Одноразовый билет входа: переносит сессию с общей страницы входа
    на поддомен кабинета роли. Хранится только SHA-256 билета."""

    __tablename__ = "login_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
