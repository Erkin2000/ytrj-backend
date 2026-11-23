from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.product.enums import Language

if TYPE_CHECKING:
    from src.rbac.models.role_model import RoleORM

# Тот же PG-тип `language`, что у переводов продуктов и контента сайта.
LanguageType = Enum(Language, name="language", values_callable=lambda e: [m.value for m in e])


class PermissionORM(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Русское название — копия перевода `ru` (поиск и списки в админ-панели).
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None]

    translations: Mapped[list["PermissionTranslationORM"]] = relationship(
        back_populates="permission",
        cascade="all, delete-orphan",
        order_by="PermissionTranslationORM.language",
        lazy="selectin",
    )
    roles: Mapped[list["RoleORM"]] = relationship(
        secondary="role_permissions",
        back_populates="permissions",
    )

    def __str__(self) -> str:
        return self.code


class PermissionTranslationORM(Base):
    __tablename__ = "permission_translations"
    __table_args__ = (UniqueConstraint("permission_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    permission: Mapped["PermissionORM"] = relationship(back_populates="translations")
