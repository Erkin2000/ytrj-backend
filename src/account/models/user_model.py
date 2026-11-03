from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.account.models.user_permission_model import UserPermissionORM
from src.database import Base, TimestampMixin

if TYPE_CHECKING:
    from src.application.models.bank_model import BankORM
    from src.rbac.models.permission_model import PermissionORM
    from src.rbac.models.role_model import RoleORM


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class UserORM(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sso_sub: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

    full_name: Mapped[str | None] = mapped_column(String(255))
    pinfl: Mapped[str | None] = mapped_column(String(14), unique=True)

    phone: Mapped[str | None] = mapped_column(String(20))
    passport_number: Mapped[str | None] = mapped_column(String(20))
    inn: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender, name="gender"))
    date_of_birth: Mapped[date | None] = mapped_column(Date)

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        default=UserStatus.ACTIVE,
        nullable=False,
    )

    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"))

    bank_id: Mapped[int | None] = mapped_column(ForeignKey("banks.id", ondelete="SET NULL"))

    organization: Mapped[str | None] = mapped_column(String(255))
    region: Mapped[str | None] = mapped_column(String(255))

    is_direction_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped["RoleORM | None"] = relationship(back_populates="users", lazy="selectin")
    bank: Mapped["BankORM | None"] = relationship(lazy="selectin")

    permissions: Mapped[list["PermissionORM"]] = relationship(
        secondary=UserPermissionORM.__table__, lazy="selectin"
    )

    def __str__(self) -> str:
        return self.full_name or self.username
