from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.rbac.models.role_model import RoleORM


class PermissionORM(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None]

    roles: Mapped[list["RoleORM"]] = relationship(
        secondary="role_permissions",
        back_populates="permissions",
    )

    def __str__(self) -> str:
        return self.code
