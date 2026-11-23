import datetime as dt
from typing import Annotated

from fastapi import UploadFile
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)

from src.account.schemas.user_schema import PhoneStr
from src.application.schemas.application_schema import ActorDTO
from src.product.enums import Language
from src.product.schemas.product_schema import check_languages

TitleStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)]
TextStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50000)]
FullNameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]
DescriptionStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)
]

TRANSLATIONS_NOTE = (
    "Ровно три перевода — `ru`, `uz`, `en`, каждый язык один раз. При изменении передаются все три."
)
QUEUE_NOTE = (
    "Место в списке: 1 — первый. Остальные сдвигаются, номера идут без пропусков. "
    "Не указано — в конец списка."
)
PHONE_NOTE = "Телефон в формате +998XXXXXXXXX."


# ---------- общие переводы ----------


class TitleTextDTO(BaseModel):
    language: Language = Field(examples=["ru"])
    title: TitleStr = Field(description="Заголовок, до 500 символов.")
    text: TextStr = Field(description="Текст, до 50 000 символов.")


TitleTextTranslations = Annotated[
    list[TitleTextDTO], Field(min_length=3, max_length=3), AfterValidator(check_languages)
]


class TitleTextOutDTO(BaseModel):
    language: Language
    title: str
    text: str


EVENT_TRANSLATIONS_EXAMPLE = [
    {
        "language": "ru",
        "title": "День открытых дверей",
        "text": "Приглашаем молодёжь в офис Фонда.",
    },
    {
        "language": "uz",
        "title": "Ochiq eshiklar kuni",
        "text": "Yoshlarni Jamgʻarma ofisiga taklif qilamiz.",
    },
    {"language": "en", "title": "Open day", "text": "We invite young people to the Fund office."},
]
ABOUT_TRANSLATIONS_EXAMPLE = [
    {
        "language": "ru",
        "title": "Наша миссия",
        "text": "Поддержка молодёжного предпринимательства.",
    },
    {
        "language": "uz",
        "title": "Bizning vazifamiz",
        "text": "Yoshlar tadbirkorligini qoʻllab-quvvatlash.",
    },
    {"language": "en", "title": "Our mission", "text": "Supporting youth entrepreneurship."},
]
PERSON_TRANSLATIONS_EXAMPLE = [
    {"language": "ru", "full_name": "Валиев Али Каримович", "description": "Председатель Совета"},
    {"language": "uz", "full_name": "Valiyev Ali Karimovich", "description": "Kengash raisi"},
    {"language": "en", "full_name": "Ali Valiyev", "description": "Chairman of the Council"},
]


class AuditDTO(BaseModel):
    created_by: ActorDTO | None = None
    updated_by: ActorDTO | None = None
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------- события ----------


class PhotoDTO(BaseModel):
    url: str
    name: str | None = None
    content_type: str
    size: int


class EventCreateForm(BaseModel):
    """Поля формы (multipart/form-data, фото — полем `photo`)."""

    title_ru: TitleStr = Field(description="Заголовок (ru).")
    title_uz: TitleStr = Field(description="Заголовок (uz).")
    title_en: TitleStr = Field(description="Заголовок (en).")
    text_ru: TextStr = Field(description="Текст (ru).")
    text_uz: TextStr = Field(description="Текст (uz).")
    text_en: TextStr = Field(description="Текст (en).")
    date: dt.date = Field(description="Дата события.", examples=["2026-12-05"])
    is_active: bool = Field(
        default=True, description="Неактивное событие не показывается на сайте."
    )
    photo: UploadFile | None = Field(
        default=None, description="Фото JPEG / PNG / WEBP, необязательно."
    )

    def translations(self) -> list[TitleTextDTO]:
        return [
            TitleTextDTO(
                language=lang,
                title=getattr(self, f"title_{lang.value}"),
                text=getattr(self, f"text_{lang.value}"),
            )
            for lang in (Language.RU, Language.UZ, Language.EN)
        ]


class EventUpdateDTO(BaseModel):
    """Фото меняется отдельно: `PUT` / `DELETE /{id}/photo`."""

    model_config = ConfigDict(extra="forbid")

    translations: TitleTextTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[EVENT_TRANSLATIONS_EXAMPLE]
    )
    date: dt.date | None = None
    is_active: bool | None = None


class EventFilterDTO(BaseModel):
    date: dt.date | None = Field(
        default=None, description="События одного дня — для выбранного дня в календаре."
    )
    date_from: dt.date | None = Field(default=None, description="События с этой даты.")
    date_to: dt.date | None = Field(default=None, description="События по эту дату.")


class EventCalendarDayDTO(BaseModel):
    date: dt.date
    count: int = Field(description="Сколько событий в этот день.")


class EventPublicDTO(BaseModel):
    id: int
    translations: list[TitleTextOutDTO]
    date: dt.date
    photo: PhotoDTO | None = None


class EventDTO(AuditDTO, EventPublicDTO):
    is_active: bool


# ---------- «О нас» ----------


class AboutCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    translations: TitleTextTranslations = Field(
        description=TRANSLATIONS_NOTE, examples=[ABOUT_TRANSLATIONS_EXAMPLE]
    )
    sort_order: int = Field(default=0, ge=0, description="Порядок на странице: меньше — выше.")
    is_active: bool = Field(default=True, description="Неактивный раздел не показывается на сайте.")


class AboutUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    translations: TitleTextTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[ABOUT_TRANSLATIONS_EXAMPLE]
    )
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class AboutPublicDTO(BaseModel):
    id: int
    translations: list[TitleTextOutDTO]
    sort_order: int


class AboutDTO(AuditDTO, AboutPublicDTO):
    is_active: bool


# ---------- члены Совета и руководство ----------


class PersonTranslationDTO(BaseModel):
    language: Language = Field(examples=["ru"])
    full_name: FullNameStr = Field(description="Ф.И.О.")
    description: DescriptionStr = Field(description="Описание: должность, биография.")


PersonTranslations = Annotated[
    list[PersonTranslationDTO], Field(min_length=3, max_length=3), AfterValidator(check_languages)
]


class PersonCreateForm(BaseModel):
    """Поля формы (multipart/form-data, фото — полем `photo`)."""

    full_name_ru: FullNameStr = Field(description="Ф.И.О. (ru).")
    full_name_uz: FullNameStr = Field(description="Ф.И.О. (uz).")
    full_name_en: FullNameStr = Field(description="Ф.И.О. (en).")
    description_ru: DescriptionStr = Field(description="Описание (ru).")
    description_uz: DescriptionStr = Field(description="Описание (uz).")
    description_en: DescriptionStr = Field(description="Описание (en).")
    phone_number: PhoneStr | None = Field(default=None, description=PHONE_NOTE)
    email: EmailStr | None = None
    queue_number: int | None = Field(default=None, ge=1, description=QUEUE_NOTE)
    is_active: bool = Field(
        default=True, description="Неактивная карточка не показывается на сайте."
    )
    photo: UploadFile | None = Field(
        default=None, description="Фото JPEG / PNG / WEBP, необязательно."
    )

    def translations(self) -> list[PersonTranslationDTO]:
        return [
            PersonTranslationDTO(
                language=lang,
                full_name=getattr(self, f"full_name_{lang.value}"),
                description=getattr(self, f"description_{lang.value}"),
            )
            for lang in (Language.RU, Language.UZ, Language.EN)
        ]


class PersonUpdateDTO(BaseModel):
    """Фото меняется отдельно: `PUT` / `DELETE /{id}/photo`. `null` в `phone_number` или
    `email` очищает поле."""

    model_config = ConfigDict(extra="forbid")

    translations: PersonTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[PERSON_TRANSLATIONS_EXAMPLE]
    )
    phone_number: PhoneStr | None = Field(default=None, description=PHONE_NOTE)
    email: EmailStr | None = None
    queue_number: int | None = Field(default=None, ge=1, description=QUEUE_NOTE)
    is_active: bool | None = None


class PersonTranslationOutDTO(BaseModel):
    language: Language
    full_name: str
    description: str


class PersonPublicDTO(BaseModel):
    id: int
    translations: list[PersonTranslationOutDTO]
    phone_number: str | None = None
    email: str | None = None
    queue_number: int
    photo: PhotoDTO | None = None


class PersonDTO(AuditDTO, PersonPublicDTO):
    is_active: bool


# ---------- контакты организации ----------

CONTACT_NOTE = "Нужно хотя бы одно из полей `phone` и `email`; `null` убирает значение."


class SiteContactCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: PhoneStr | None = Field(default=None, description=PHONE_NOTE, examples=["+998712000000"])
    email: EmailStr | None = Field(default=None, examples=["info@yoshlarfondi.uz"])
    sort_order: int = Field(default=0, ge=0, description="Порядок на сайте: меньше — выше.")
    is_active: bool = Field(
        default=True, description="Неактивный контакт не показывается на сайте."
    )

    @model_validator(mode="after")
    def _not_empty(self):
        if not self.phone and not self.email:
            raise ValueError("Нужен телефон или email")
        return self


class SiteContactUpdateDTO(BaseModel):
    """Передаются только изменяемые поля. `null` в `phone` или `email` убирает значение,
    но хотя бы одно должно остаться."""

    model_config = ConfigDict(extra="forbid")

    phone: PhoneStr | None = Field(default=None, description=PHONE_NOTE)
    email: EmailStr | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class SiteContactPublicDTO(BaseModel):
    id: int
    phone: str | None = None
    email: str | None = None
    sort_order: int


class SiteContactDTO(AuditDTO, SiteContactPublicDTO):
    is_active: bool
