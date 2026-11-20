"""Новости сайта. Ведёт отдел маркетинга (роль MARKETING).

Заголовок и текст — в таблице переводов, по строке на язык (ru / uz / en).
Новость видна на сайте, когда status=PUBLISHED и наступило `publish_at`.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base, TimestampMixin
from src.news.enums import NewsStatus
from src.product.enums import Language
from src.product.models.product_model import LanguageType

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM


NewsStatusType = Enum(
    NewsStatus, name="news_status", values_callable=lambda e: [m.value for m in e]
)


class NewsORM(TimestampMixin, Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[NewsStatus] = mapped_column(
        NewsStatusType, default=NewsStatus.DRAFT, nullable=False, index=True
    )
    # Дата и время публикации; для черновика — NULL.
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    # Дата новости, которую показывает сайт.
    news_date: Mapped[date] = mapped_column(Date, nullable=False)

    photo_path: Mapped[str | None] = mapped_column(String(500))
    photo_name: Mapped[str | None] = mapped_column(String(255))
    photo_content_type: Mapped[str | None] = mapped_column(String(100))
    photo_size: Mapped[int | None] = mapped_column(Integer)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    translations: Mapped[list["NewsTranslationORM"]] = relationship(
        back_populates="news",
        cascade="all, delete-orphan",
        order_by="NewsTranslationORM.language",
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
                return t.title
        return self.translations[0].title if self.translations else f"News #{self.id}"


class NewsTranslationORM(Base):
    __tablename__ = "news_translations"
    __table_args__ = (UniqueConstraint("news_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    news_id: Mapped[int] = mapped_column(
        ForeignKey("news.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    news: Mapped["NewsORM"] = relationship(back_populates="translations")
