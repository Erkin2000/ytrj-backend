from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base, TimestampMixin
from src.product.enums import Language
from src.rbac.models.permission_model import LanguageType, PermissionORM
from src.rbac.models.role_permission_model import RolePermissionORM

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM


class RoleORM(TimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Русское название — копия перевода `ru` (уникально; поиск и списки в админ-панели).
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

    translations: Mapped[list["RoleTranslationORM"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
        order_by="RoleTranslationORM.language",
        lazy="selectin",
    )
    users: Mapped[list["UserORM"]] = relationship(back_populates="role")

    def __str__(self) -> str:
        return self.name


class RoleTranslationORM(Base):
    __tablename__ = "role_translations"
    __table_args__ = (UniqueConstraint("role_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    role: Mapped["RoleORM"] = relationship(back_populates="translations")
