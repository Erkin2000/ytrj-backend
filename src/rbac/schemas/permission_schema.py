from pydantic import BaseModel

from src.product.enums import Language


class PermissionTranslationDTO(BaseModel):
    language: Language
    name: str
    description: str | None = None


class PermissionDTO(BaseModel):
    id: int
    code: str
    translations: list[PermissionTranslationDTO]


class ModuleTranslationDTO(BaseModel):
    language: Language
    name: str


class PermissionGroupDTO(BaseModel):
    """Права, сгруппированные по модулю — для матрицы прав в UI."""

    module: str
    translations: list[ModuleTranslationDTO]
    permissions: list[PermissionDTO]
