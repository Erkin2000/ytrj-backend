from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base, TimestampMixin

if TYPE_CHECKING:
    from src.application.models.bank_model import BankORM
    from src.rbac.models.role_model import RoleORM


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class UserORM(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Логин для входа по паролю (внутренние пользователи). Для пользователей,
    # созданных через OneID, равен ПИНФЛ.
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Идентификатор субъекта OneID (sub). Заполняется при первом входе.
    oneid_sub: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

    # Данные из OneID / госисточника. Заявитель не может их менять произвольно.
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    passport_number: Mapped[str | None] = mapped_column(String(20))
    pinfl: Mapped[str | None] = mapped_column(String(14), unique=True)
    inn: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        default=UserStatus.ACTIVE,
        nullable=False,
    )

    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"))

    # Scope: сотрудник банка видит только заявки своего банка.
    bank_id: Mapped[int | None] = mapped_column(ForeignKey("banks.id", ondelete="SET NULL"))

    # Scope: организация / регион (справочники появятся позже).
    organization: Mapped[str | None] = mapped_column(String(255))
    region: Mapped[str | None] = mapped_column(String(255))

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped["RoleORM | None"] = relationship(back_populates="users", lazy="selectin")
    bank: Mapped["BankORM | None"] = relationship(lazy="selectin")

    def __str__(self) -> str:
        return self.full_name or self.username
