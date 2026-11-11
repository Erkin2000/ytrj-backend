"""Продукт Фонда: переводы (ru / uz / en), банки, этапы и поля анкеты.

Названия и описания хранятся в таблицах переводов — по строке на язык
(уникально в пределах объекта). Заявитель выбирает опубликованный продукт и
заполняет поля его этапов. Когда по продукту есть заявки, этапы и поля менять
нельзя — только копировать продукт.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base, TimestampMixin
from src.product.enums import FieldType, Language, ProductStatus

if TYPE_CHECKING:
    from src.application.models.bank_model import BankORM


LanguageType = Enum(Language, name="language", values_callable=lambda e: [m.value for m in e])

product_banks = Table(
    "product_banks",
    Base.metadata,
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("bank_id", ForeignKey("banks.id", ondelete="RESTRICT"), primary_key=True),
)


def ru_name(translations) -> str:
    """Название на русском (для истории, админки и логов)."""
    for t in translations:
        if t.language == Language.RU:
            return t.name
    return translations[0].name if translations else ""


class ProductCategoryORM(TimestampMixin, Base):
    """Категория продуктов. Создаёт оператор Фонда; каждый продукт относится к одной категории."""

    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Неактивную категорию нельзя выбрать для продукта, её продукты не видны заявителям.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    translations: Mapped[list["ProductCategoryTranslationORM"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="ProductCategoryTranslationORM.language",
        lazy="selectin",
    )

    def __str__(self) -> str:
        return ru_name(self.translations)


class ProductCategoryTranslationORM(Base):
    __tablename__ = "product_category_translations"
    __table_args__ = (UniqueConstraint("category_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("product_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    category: Mapped["ProductCategoryORM"] = relationship(back_populates="translations")


class ProductORM(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("product_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"),
        default=ProductStatus.DRAFT,
        nullable=False,
        index=True,
    )
    # Для каких типов субъекта доступен продукт.
    allowed_subject_types: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)), nullable=False, default=list
    )
    # Сроки приёма заявок (включительно); пусто — без ограничения.
    accept_from: Mapped[date | None] = mapped_column(Date)
    accept_to: Mapped[date | None] = mapped_column(Date)

    copied_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    category: Mapped["ProductCategoryORM"] = relationship(lazy="selectin")
    translations: Mapped[list["ProductTranslationORM"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductTranslationORM.language",
        lazy="selectin",
    )
    banks: Mapped[list["BankORM"]] = relationship(
        secondary=product_banks, lazy="selectin", order_by="BankORM.sort_order"
    )
    stages: Mapped[list["ProductStageORM"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductStageORM.number",
        lazy="selectin",
    )

    def __str__(self) -> str:
        return ru_name(self.translations)


class ProductTranslationORM(Base):
    __tablename__ = "product_translations"
    __table_args__ = (UniqueConstraint("product_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    product: Mapped["ProductORM"] = relationship(back_populates="translations")


class ProductStageORM(Base):
    __tablename__ = "product_stages"
    __table_args__ = (UniqueConstraint("product_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["ProductORM"] = relationship(back_populates="stages")
    translations: Mapped[list["ProductStageTranslationORM"]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="ProductStageTranslationORM.language",
        lazy="selectin",
    )
    fields: Mapped[list["ProductFieldORM"]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="[ProductFieldORM.sort_order, ProductFieldORM.id]",
        lazy="selectin",
    )

    def __str__(self) -> str:
        return f"{self.number}. {ru_name(self.translations)}"


class ProductStageTranslationORM(Base):
    __tablename__ = "product_stage_translations"
    __table_args__ = (UniqueConstraint("stage_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("product_stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    stage: Mapped["ProductStageORM"] = relationship(back_populates="translations")


class ProductFieldORM(Base):
    __tablename__ = "product_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("product_stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_type: Mapped[FieldType] = mapped_column(
        Enum(FieldType, name="product_field_type"), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Для PHOTO / FILE: сколько файлов можно загрузить в поле.
    max_files: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    stage: Mapped["ProductStageORM"] = relationship(back_populates="fields")
    translations: Mapped[list["ProductFieldTranslationORM"]] = relationship(
        back_populates="field",
        cascade="all, delete-orphan",
        order_by="ProductFieldTranslationORM.language",
        lazy="selectin",
    )

    def __str__(self) -> str:
        return ru_name(self.translations)


class ProductFieldTranslationORM(Base):
    __tablename__ = "product_field_translations"
    __table_args__ = (UniqueConstraint("field_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    field_id: Mapped[int] = mapped_column(
        ForeignKey("product_fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    field: Mapped["ProductFieldORM"] = relationship(back_populates="translations")
