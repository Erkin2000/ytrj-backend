"""Ответы заявителя на поля продукта: значения и загруженные файлы."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.application.models.application_model import ApplicationORM


class ApplicationFieldValueORM(Base):
    """Значение поля STRING / NUMBER / DATE / PHONE / EMAIL в нормализованном виде."""

    __tablename__ = "application_field_values"
    __table_args__ = (UniqueConstraint("application_id", "field_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_id: Mapped[int] = mapped_column(
        ForeignKey("product_fields.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    application: Mapped["ApplicationORM"] = relationship(back_populates="field_values")


class ApplicationFieldFileORM(Base):
    """Файл поля PHOTO / FILE."""

    __tablename__ = "application_field_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_id: Mapped[int] = mapped_column(
        ForeignKey("product_fields.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["ApplicationORM"] = relationship(back_populates="field_files")

    def __str__(self) -> str:
        return self.file_name
