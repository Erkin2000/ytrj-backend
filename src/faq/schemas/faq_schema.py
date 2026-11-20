from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from src.application.schemas.application_schema import ActorDTO
from src.product.enums import Language
from src.product.schemas.product_schema import check_languages

QuestionStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)]
AnswerStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]

TRANSLATIONS_NOTE = (
    "Ровно три перевода — `ru`, `uz`, `en`, каждый язык один раз. При изменении передаются все три."
)

FAQ_TRANSLATIONS_EXAMPLE = [
    {
        "language": "ru",
        "question": "Кто может подать заявку?",
        "answer": "Молодёжь от 18 до 30 лет, зарегистрированная в Узбекистане.",
    },
    {
        "language": "uz",
        "question": "Kim ariza topshirishi mumkin?",
        "answer": "Oʻzbekistonda roʻyxatdan oʻtgan 18 yoshdan 30 yoshgacha boʻlgan yoshlar.",
    },
    {
        "language": "en",
        "question": "Who can apply?",
        "answer": "Young people aged 18 to 30 registered in Uzbekistan.",
    },
]


class FaqTranslationDTO(BaseModel):
    language: Language = Field(examples=["ru"])
    question: QuestionStr = Field(description="Вопрос, до 500 символов.")
    answer: AnswerStr = Field(description="Ответ, до 10 000 символов.")


FaqTranslations = Annotated[
    list[FaqTranslationDTO],
    Field(min_length=3, max_length=3),
    AfterValidator(check_languages),
]


class FaqCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    translations: FaqTranslations = Field(
        description=TRANSLATIONS_NOTE, examples=[FAQ_TRANSLATIONS_EXAMPLE]
    )
    is_active: bool = Field(default=True, description="Неактивный вопрос не показывается на сайте.")
    sort_order: int = Field(default=0, ge=0, description="Порядок на сайте: меньше — выше.")


class FaqUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    translations: FaqTranslations | None = Field(
        default=None, description=TRANSLATIONS_NOTE, examples=[FAQ_TRANSLATIONS_EXAMPLE]
    )
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class FaqTranslationOutDTO(BaseModel):
    language: Language
    question: str
    answer: str


class FaqPublicDTO(BaseModel):
    id: int
    translations: list[FaqTranslationOutDTO]
    sort_order: int


class FaqDTO(FaqPublicDTO):
    is_active: bool
    created_by: ActorDTO | None = None
    updated_by: ActorDTO | None = None
    created_at: datetime
    updated_at: datetime
