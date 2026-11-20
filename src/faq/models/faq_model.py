"""Вопросы и ответы (FAQ) для сайта. Ведёт отдел маркетинга (роль MARKETING).

Вопрос и ответ хранятся в таблице переводов — по строке на язык (ru / uz / en).
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base, TimestampMixin
from src.product.enums import Language
from src.product.models.product_model import LanguageType

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM


class FaqORM(TimestampMixin, Base):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Неактивный вопрос не показывается на сайте.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    translations: Mapped[list["FaqTranslationORM"]] = relationship(
        back_populates="faq",
        cascade="all, delete-orphan",
        order_by="FaqTranslationORM.language",
        lazy="selectin",
    )
    created_by: Mapped["UserORM | None"] = relationship(
        foreign_keys=[created_by_id], lazy="selectin"
    )
    updated_by: Mapped["UserORM | None"] = relationship(
        foreign_keys=[updated_by_id], lazy="selectin"
    )

    def __str__(self) -> str:
        for t in self.translations:
            if t.language == Language.RU:
                return t.question
        return self.translations[0].question if self.translations else f"FAQ #{self.id}"


class FaqTranslationORM(Base):
    __tablename__ = "faq_translations"
    __table_args__ = (UniqueConstraint("faq_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    faq_id: Mapped[int] = mapped_column(
        ForeignKey("faqs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    faq: Mapped["FaqORM"] = relationship(back_populates="translations")
