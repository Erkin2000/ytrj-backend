from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class UserPermissionORM(Base):

    __tablename__ = "user_permissions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )
