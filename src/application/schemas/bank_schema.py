from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from src.application.enums import SubjectType


class BankDTO(BaseModel):
    id: int
    code: str
    name: str
    official_name: str | None = None
    allowed_subject_types: list[SubjectType]
    is_active: bool
    sort_order: int


class BankRequestAddDTO(BaseModel):
    code: Annotated[str, StringConstraints(min_length=2, max_length=50, pattern=r"^[a-z0-9_]+$")]
    name: Annotated[str, StringConstraints(min_length=2, max_length=255)]
    official_name: str | None = None
    allowed_subject_types: list[SubjectType] = Field(
        default_factory=lambda: list(SubjectType),
    )
    is_active: bool = True
    sort_order: int = 0


class BankRequestUpdateDTO(BaseModel):
    name: Annotated[str, StringConstraints(min_length=2, max_length=255)] | None = None
    official_name: str | None = None
    allowed_subject_types: list[SubjectType] | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class BankAddDTO(BaseModel):
    code: str
    name: str
    official_name: str | None = None
    allowed_subject_types: list[str]
    is_active: bool = True
    sort_order: int = 0


class BankUpdateDTO(BaseModel):
    name: str | None = None
    official_name: str | None = None
    allowed_subject_types: list[str] | None = None
    is_active: bool | None = None
    sort_order: int | None = None
