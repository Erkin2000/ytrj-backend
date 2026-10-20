from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.account.schemas.user_schema import CurrentUserDTO
from src.auth.services.token_service import TokenService
from src.common.responses.exceptions import (
    NotAuthenticatedException,
    PermissionDeniedException,
    UserBlockedException,
)
from src.database import async_session_maker
from src.rbac.permissions import Action, Module, permission_code
from src.utils.db_manager import DBManager


class PaginationParams(BaseModel):
    page: Annotated[int, Query(1, ge=1)]
    per_page: Annotated[int | None, Query(None, ge=1, le=100)]


PaginationDep = Annotated[PaginationParams, Depends()]


async def get_db():
    async with DBManager(session_factory=async_session_maker) as db:
        yield db


DBDep = Annotated[DBManager, Depends(get_db)]


security = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DBDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUserDTO:
    """Проверяет access-токен и возвращает пользователя с ролью, правами
    и scope (банк). Заблокированный пользователь не допускается."""
    if credentials is None:
        raise NotAuthenticatedException()

    payload = TokenService().decode_access_token(credentials.credentials)

    user = await db.user.get_access(int(payload["sub"]))

    if user is None:
        raise NotAuthenticatedException()

    if not user.is_active:
        raise UserBlockedException()

    return user


CurrentUserDep = Annotated[CurrentUserDTO, Depends(get_current_user)]


def require_permission(module: Module, action: Action):
    """Зависимость для роутера/эндпоинта: пускает суперпользователя
    или роль с правом "<module>.<action>"."""

    code = permission_code(module, action)

    async def check_permission(user: CurrentUserDep) -> CurrentUserDTO:
        if not user.has_permission(code):
            raise PermissionDeniedException()
        return user

    return check_permission


def require_any_permission(*codes: str):
    """Пускает, если у пользователя есть хотя бы одно из перечисленных прав."""

    async def check_permission(user: CurrentUserDep) -> CurrentUserDTO:
        if not any(user.has_permission(code) for code in codes):
            raise PermissionDeniedException()
        return user

    return check_permission
