from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

from src.product.enums import Language
from src.product.schemas.product_schema import NameTranslationDTO, check_product_translations

RoleCodeStr = Annotated[
    str,
    StringConstraints(min_length=2, max_length=50, pattern=r"^[A-Z][A-Z0-9_]*$"),
]
RoleNameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
RoleDescriptionStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]

ROLE_TRANSLATIONS_NOTE = (
    "Ровно три перевода — `ru`, `uz`, `en`, каждый язык один раз. Описание — на всех трёх "
    "языках или ни на одном. При изменении передаются все три."
)
ROLE_TRANSLATIONS_EXAMPLE = [
    {"language": "ru", "name": "Аналитик Фонда", "description": "Отчёты по заявкам"},
    {
        "language": "uz",
        "name": "Jamgʻarma tahlilchisi",
        "description": "Arizalar boʻyicha hisobotlar",
    },
    {"language": "en", "name": "Fund analyst", "description": "Application reports"},
]


class RoleTranslationDTO(NameTranslationDTO):
    name: RoleNameStr = Field(examples=["Аналитик Фонда"])
    description: RoleDescriptionStr | None = Field(default=None, examples=["Отчёты по заявкам"])


RoleTranslations = Annotated[
    list[RoleTranslationDTO],
    Field(min_length=3, max_length=3),
    AfterValidator(check_product_translations),
]


class RoleTranslationOutDTO(BaseModel):
    language: Language
    name: str
    description: str | None = None


class RoleNameOutDTO(BaseModel):
    language: Language
    name: str


class RoleShortDTO(BaseModel):
    id: int
    code: str
    translations: list[RoleNameOutDTO]
    is_superuser: bool = False


class RoleDTO(BaseModel):
    id: int
    code: str
    translations: list[RoleTranslationOutDTO]
    is_superuser: bool
    is_system: bool
    permissions: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoleRequestAddDTO(BaseModel):
    code: RoleCodeStr
    translations: RoleTranslations = Field(
        description=ROLE_TRANSLATIONS_NOTE, examples=[ROLE_TRANSLATIONS_EXAMPLE]
    )
    is_superuser: bool = False
    permissions: list[str] = Field(default_factory=list, examples=[["applications.read"]])


class RoleRequestUpdateDTO(BaseModel):
    code: RoleCodeStr | None = None
    translations: RoleTranslations | None = Field(
        default=None, description=ROLE_TRANSLATIONS_NOTE, examples=[ROLE_TRANSLATIONS_EXAMPLE]
    )
    is_superuser: bool | None = None
    permissions: list[str] | None = None
