from pydantic import BaseModel


class PermissionDTO(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None


class PermissionGroupDTO(BaseModel):
    """Права, сгруппированные по модулю — для матрицы прав в UI."""

    module: str
    module_name: str
    permissions: list[PermissionDTO]
