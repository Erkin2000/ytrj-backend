"""Контент сайта, который ведёт отдел маркетинга (роль MARKETING):
события, разделы «О нас», карточки членов Совета и руководства.

Тексты — в таблицах переводов, по строке на язык (ru / uz / en).
Карточки людей — это страница сайта, а не учётные записи пользователей:
член Совета на сайте и пользователь с ролью COUNCIL_MEMBER не связаны.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base, TimestampMixin
from src.product.enums import Language
from src.product.models.product_model import LanguageType
from src.website.enums import PersonKind

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM


def _ru(translations, attr: str, fallback: str) -> str:
    for t in translations:
        if t.language == Language.RU:
            return getattr(t, attr)
    return getattr(translations[0], attr) if translations else fallback


class AuthorMixin:
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


# ---------- события ----------


class EventORM(AuthorMixin, TimestampMixin, Base):
    __tablename__ = "site_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    translations: Mapped[list["EventTranslationORM"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventTranslationORM.language",
        lazy="selectin",
    )
    created_by: Mapped["UserORM | None"] = relationship(
        foreign_keys="EventORM.created_by_id", lazy="selectin"
    )
    updated_by: Mapped["UserORM | None"] = relationship(
        foreign_keys="EventORM.updated_by_id", lazy="selectin"
    )

    def __str__(self) -> str:
        return _ru(self.translations, "title", f"Event #{self.id}")


class EventTranslationORM(Base):
    __tablename__ = "site_event_translations"
    __table_args__ = (UniqueConstraint("event_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("site_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    event: Mapped["EventORM"] = relationship(back_populates="translations")


# ---------- «О нас» ----------


class AboutSectionORM(AuthorMixin, TimestampMixin, Base):
    __tablename__ = "site_about_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    translations: Mapped[list["AboutTranslationORM"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="AboutTranslationORM.language",
        lazy="selectin",
    )
    created_by: Mapped["UserORM | None"] = relationship(
        foreign_keys="AboutSectionORM.created_by_id", lazy="selectin"
    )
    updated_by: Mapped["UserORM | None"] = relationship(
        foreign_keys="AboutSectionORM.updated_by_id", lazy="selectin"
    )

    def __str__(self) -> str:
        return _ru(self.translations, "title", f"About #{self.id}")


class AboutTranslationORM(Base):
    __tablename__ = "site_about_translations"
    __table_args__ = (UniqueConstraint("section_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("site_about_sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    section: Mapped["AboutSectionORM"] = relationship(back_populates="translations")


# ---------- члены Совета и руководство ----------

PersonKindType = Enum(
    PersonKind, name="site_person_kind", values_callable=lambda e: [m.value for m in e]
)


class PersonORM(AuthorMixin, TimestampMixin, Base):
    """Карточка человека на сайте: член Совета или руководство (`kind`)."""

    __tablename__ = "site_people"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[PersonKind] = mapped_column(PersonKindType, nullable=False, index=True)
    # Место в списке своего раздела: 1, 2, 3… без пропусков.
    queue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    photo_path: Mapped[str | None] = mapped_column(String(500))
    photo_name: Mapped[str | None] = mapped_column(String(255))
    photo_content_type: Mapped[str | None] = mapped_column(String(100))
    photo_size: Mapped[int | None] = mapped_column(Integer)

    translations: Mapped[list["PersonTranslationORM"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by="PersonTranslationORM.language",
        lazy="selectin",
    )
    created_by: Mapped["UserORM | None"] = relationship(
        foreign_keys="PersonORM.created_by_id", lazy="selectin"
    )
    updated_by: Mapped["UserORM | None"] = relationship(
        foreign_keys="PersonORM.updated_by_id", lazy="selectin"
    )

    def __str__(self) -> str:
        return _ru(self.translations, "full_name", f"Person #{self.id}")


class PersonTranslationORM(Base):
    __tablename__ = "site_person_translations"
    __table_args__ = (UniqueConstraint("person_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("site_people.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[Language] = mapped_column(LanguageType, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    person: Mapped["PersonORM"] = relationship(back_populates="translations")
