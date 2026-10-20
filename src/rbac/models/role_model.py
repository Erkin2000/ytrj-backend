from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base, TimestampMixin
from src.rbac.models.permission_model import PermissionORM
from src.rbac.models.role_permission_model import RolePermissionORM

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM


class RoleORM(TimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None]

    # Суперпользователь: все права без явного назначения.
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Системные роли (SUPER_ADMIN, FUND_OPERATOR, ...) нельзя удалить
    # и переименовать код — на них завязана бизнес-логика scope.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions: Mapped[list[PermissionORM]] = relationship(
        secondary=RolePermissionORM.__table__,
        back_populates="roles",
        lazy="selectin",
    )

    users: Mapped[list["UserORM"]] = relationship(back_populates="role")

    def __str__(self) -> str:
        return self.name
