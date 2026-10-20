from typing import Annotated

from fastapi import APIRouter, Depends

from src.account.schemas.user_schema import (
    UserFilterDTO,
    UserRequestAddDTO,
    UserRequestUpdateDTO,
    UserRoleAssignDTO,
    UserStatusUpdateDTO,
)
from src.account.services.user_service import UserService
from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, CONFLICT, paginated_example, success_example
from src.rbac.permissions import Action, Module

router = APIRouter(prefix="/users", tags=["Пользователи"])

USER_EXAMPLE = {
    "id": 5,
    "username": "fund_operator",
    "full_name": "Каримова Нигора",
    "phone": "+998901234567",
    "status": "ACTIVE",
    "role": {"id": 2, "code": "FUND_OPERATOR", "name": "Оператор Фонда", "is_superuser": False},
    "bank": None,
    "last_login_at": "2026-10-19T09:30:00Z",
}

FilterDep = Annotated[UserFilterDTO, Depends()]


@router.get(
    "",
    summary="Просмотр, поиск и фильтрация пользователей",
    dependencies=[Depends(require_permission(Module.USERS, Action.READ))],
    responses={200: paginated_example(USER_EXAMPLE), **COMMON_ERRORS},
)
async def get_users(db: DBDep, pagination: PaginationDep, filters: FilterDep):
    data = await UserService(db).get_all_users(filters, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Users retrieved successfully.")


@router.get(
    "/{user_id}",
    summary="Профиль пользователя",
    dependencies=[Depends(require_permission(Module.USERS, Action.READ))],
    responses={200: success_example(USER_EXAMPLE, "User found."), **COMMON_ERRORS},
)
async def get_user(user_id: int, db: DBDep):
    user = await UserService(db).get_user(user_id)
    return ResponseBuilder.success(data=user, message="User found.")


@router.post(
    "",
    summary="Создание внутреннего пользователя (логин + пароль + роль)",
    dependencies=[Depends(require_permission(Module.USERS, Action.CREATE))],
    responses={
        201: success_example(USER_EXAMPLE, "User created successfully."),
        409: CONFLICT,
        **COMMON_ERRORS,
    },
)
async def create_user(data: UserRequestAddDTO, db: DBDep):
    user = await UserService(db).add_user(data)
    return ResponseBuilder.success(data=user, message="User created successfully.", status_code=201)


@router.patch(
    "/{user_id}",
    summary="Изменение пользователя",
    dependencies=[Depends(require_permission(Module.USERS, Action.UPDATE))],
    responses={
        200: success_example(USER_EXAMPLE, "User updated successfully."),
        409: CONFLICT,
        **COMMON_ERRORS,
    },
)
async def update_user(user_id: int, data: UserRequestUpdateDTO, db: DBDep):
    user = await UserService(db).edit_user(user_id, data)
    return ResponseBuilder.success(data=user, message="User updated successfully.")


@router.post(
    "/{user_id}/status",
    summary="Перевод в статус «активен» / «заблокирован»",
    dependencies=[Depends(require_permission(Module.USERS, Action.UPDATE))],
    responses={200: success_example(USER_EXAMPLE, "User status updated."), **COMMON_ERRORS},
)
async def set_user_status(
    user_id: int, data: UserStatusUpdateDTO, db: DBDep, current: CurrentUserDep
):
    user = await UserService(db).set_status(user_id, data, current)
    return ResponseBuilder.success(data=user, message="User status updated.")


@router.post(
    "/{user_id}/role",
    summary="Назначение / отзыв роли и привязка scope (банк)",
    dependencies=[Depends(require_permission(Module.USERS, Action.UPDATE))],
    responses={200: success_example(USER_EXAMPLE, "Role assigned."), **COMMON_ERRORS},
)
async def assign_role(user_id: int, data: UserRoleAssignDTO, db: DBDep):
    user = await UserService(db).assign_role(user_id, data)
    return ResponseBuilder.success(data=user, message="Role assigned.")


@router.delete(
    "/{user_id}",
    summary="Удаление пользователя",
    dependencies=[Depends(require_permission(Module.USERS, Action.DELETE))],
    responses={200: success_example(None, "User deleted successfully."), **COMMON_ERRORS},
)
async def delete_user(user_id: int, db: DBDep):
    await UserService(db).delete_user(user_id)
    return ResponseBuilder.success(message="User deleted successfully.")


@router.get(
    "/{user_id}/sessions",
    summary="Сессии пользователя (refresh-токены, последний вход)",
    dependencies=[Depends(require_permission(Module.USERS, Action.READ))],
    responses={
        200: success_example(
            [
                {
                    "id": 1,
                    "created_at": "2026-10-19T09:30:00Z",
                    "expires_at": "2026-10-26T09:30:00Z",
                    "is_revoked": False,
                    "user_agent": "Mozilla/5.0",
                    "ip_address": "127.0.0.1",
                }
            ],
            "Sessions retrieved.",
        ),
        **COMMON_ERRORS,
    },
)
async def get_sessions(user_id: int, db: DBDep):
    data = await UserService(db).get_sessions(user_id)
    return ResponseBuilder.success(data=data, message="Sessions retrieved.")


@router.delete(
    "/{user_id}/sessions",
    summary="Завершить все сессии пользователя",
    dependencies=[Depends(require_permission(Module.USERS, Action.UPDATE))],
    responses={200: success_example(None, "Sessions revoked."), **COMMON_ERRORS},
)
async def revoke_sessions(user_id: int, db: DBDep):
    await UserService(db).revoke_sessions(user_id)
    return ResponseBuilder.success(message="Sessions revoked.")
