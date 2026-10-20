from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

RoleCodeStr = Annotated[
    str,
    StringConstraints(min_length=2, max_length=50, pattern=r"^[A-Z][A-Z0-9_]*$"),
]


class RoleShortDTO(BaseModel):
    id: int
    code: str
    name: str
    is_superuser: bool = False


class RoleDTO(BaseModel):
    id: int
    name: str
    code: str
    description: str | None = None
    is_superuser: bool
    is_system: bool
    permissions: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoleRequestAddDTO(BaseModel):
    name: Annotated[str, StringConstraints(min_length=2, max_length=100)]
    code: RoleCodeStr
    description: str | None = None
    is_superuser: bool = False
    permissions: list[str] = Field(default_factory=list, examples=[["applications.read"]])


class RoleRequestUpdateDTO(BaseModel):
    name: Annotated[str, StringConstraints(min_length=2, max_length=100)] | None = None
    code: RoleCodeStr | None = None
    description: str | None = None
    is_superuser: bool | None = None
    permissions: list[str] | None = None


class RoleAddDTO(BaseModel):
    name: str
    code: str
    description: str | None = None
    is_superuser: bool = False
    is_system: bool = False


class RoleUpdateDTO(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    is_superuser: bool | None = None
