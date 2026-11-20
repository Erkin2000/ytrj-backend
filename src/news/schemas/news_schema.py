import datetime as dt
from datetime import datetime
from typing import Annotated, Literal

from fastapi import UploadFile
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from src.application.schemas.application_schema import ActorDTO
from src.bulletin.schemas.bulletin_schema import DATETIME_HINT, as_aware
from src.news.enums import NewsSource, NewsState
from src.product.enums import Language
from src.product.schemas.product_schema import check_languages

TitleStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)]
TextStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50000)]

TRANSLATIONS_NOTE = (
    "Ровно три перевода — `ru`, `uz`, `en`, каждый язык один раз. При изменении передаются все три."
)
STATUS_NOTE = (
    "`PUBLISHED` — опубликовать сразу; `SCHEDULED` — опубликовать в `publish_at` "
    "(обязательна, в будущем); `DRAFT` — черновик, на сайте не виден."
)
DATE_NOTE = "Дата новости для сайта. Не указана — дата публикации (по Ташкенту)."

NEWS_TRANSLATIONS_EXAMPLE = [
    {
        "language": "ru",
        "title": "Фонд открыл приём заявок",
        "text": "С 1 декабря молодёжь может подать заявку на льготный кредит.",
    },
    {
        "language": "uz",
        "title": "Jamgʻarma arizalar qabulini boshladi",
        "text": "1-dekabrdan yoshlar imtiyozli kreditga ariza topshirishi mumkin.",
    },
    {
        "language": "en",
        "title": "The Fund opened applications",
        "text": "From December 1, young people can apply for a soft loan.",
    },
]

PublishStatus = Literal[NewsState.PUBLISHED, NewsState.SCHEDULED, NewsState.DRAFT]


class NewsTranslationDTO(BaseModel):
    language: Language = Field(examples=["ru"])
    title: TitleStr = Field(description="Заголовок, до 500 символов.")
    text: TextStr = Field(description="Текст новости, до 50 000 символов.")


NewsTranslations = Annotated[
    list[NewsTranslationDTO],
    Field(min_length=3, max_length=3),
    AfterValidator(check_languages),
]


class NewsCreateForm(BaseModel):
    """Поля формы создания новости (multipart/form-data, фото — полем `photo`)."""

    title_ru: TitleStr = Field(description="Заголовок (ru).")
    title_uz: TitleStr = Field(description="Заголовок (uz).")
    title_en: TitleStr = Field(description="Заголовок (en).")
    text_ru: TextStr = Field(description="Текст (ru).")
    text_uz: TextStr = Field(description="Текст (uz).")
    text_en: TextStr = Field(description="Текст (en).")
    date: dt.date | None = Field(default=None, description=DATE_NOTE)
    status: PublishStatus = Field(default=NewsState.PUBLISHED, description=STATUS_NOTE)
    publish_at: datetime | None = Field(
        default=None, description=f"Дата и время публикации для `SCHEDULED`. {DATETIME_HINT}"
    )
    photo: UploadFile | None = Field(
        default=None, description="Фото JPEG / PNG / WEBP, необязательно."
    )

    _aware = field_validator("publish_at")(as_aware)

    def translations(self) -> list[NewsTranslationDTO]:
        return [
            NewsTranslationDTO(
                language=lang,
                title=getattr(self, f"title_{lang.value}"),
                text=getattr(self, f"text_{lang.value}"),
            )
            for lang in (Language.RU, Language.UZ, Language.EN)
        ]


class NewsUpdateDTO(BaseModel):
    """Фото меняется отдельно: `PUT` / `DELETE /marketing/news/{id}/photo`."""

    model_config = ConfigDict(extra="forbid")

    translations: NewsTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[NEWS_TRANSLATIONS_EXAMPLE]
    )
    date: dt.date | None = Field(default=None, description="Дата новости для сайта.")
    status: PublishStatus | None = Field(default=None, description=STATUS_NOTE)
    publish_at: datetime | None = Field(
        default=None,
        description=(
            "Новое время публикации: вместе со `status=SCHEDULED` или для новости, "
            f"которая ещё ждёт публикации. {DATETIME_HINT}"
        ),
    )

    _aware = field_validator("publish_at")(as_aware)


class NewsFilterDTO(BaseModel):
    state: NewsState | None = Field(default=None, description="Черновики, отложенные или на сайте.")
    search: str | None = Field(default=None, max_length=100, description="Поиск по заголовку.")
    source: NewsSource | None = Field(
        default=None, description="`MARKETING` — созданы в админке, `TELEGRAM` — из канала."
    )


class NewsTranslationOutDTO(BaseModel):
    language: Language
    title: str
    text: str


class NewsPhotoDTO(BaseModel):
    url: str
    name: str | None = None
    content_type: str
    size: int


class NewsPublicDTO(BaseModel):
    id: int
    translations: list[NewsTranslationOutDTO]
    date: dt.date
    published_at: datetime
    photo: NewsPhotoDTO | None = None


class NewsDTO(BaseModel):
    id: int
    translations: list[NewsTranslationOutDTO]
    date: dt.date
    state: NewsState = Field(
        description="`DRAFT`, `SCHEDULED` (ждёт `publish_at`) или `PUBLISHED`."
    )
    publish_at: datetime | None = None
    photo: NewsPhotoDTO | None = None
    source: NewsSource = Field(
        default=NewsSource.MARKETING,
        description="`MARKETING` — создана в админке, `TELEGRAM` — пост канала (сохранил бот).",
    )
    telegram_url: str | None = Field(
        default=None, description="Ссылка на пост канала (для публичного канала)."
    )
    created_by: ActorDTO | None = None
    updated_by: ActorDTO | None = None
    created_at: datetime
    updated_at: datetime
