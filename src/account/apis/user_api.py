from typing import Annotated

from fastapi import APIRouter, Depends

from src.account.schemas.user_schema import (
    CurrentUserDTO,
    UserFilterDTO,
    UserRequestAddDTO,
    UserRequestUpdateDTO,
    UserRoleAssignDTO,
    UserStatusUpdateDTO,
)
from src.account.services.user_service import UserService
from src.common.dependencies import DBDep, PaginationDep, require_user_admin
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, CONFLICT, paginated_example, success_example
from src.rbac.permissions import Action

router = APIRouter(prefix="/users", tags=["Пользователи"])

ReadAdmin = Annotated[CurrentUserDTO, Depends(require_user_admin(Action.READ))]
CreateAdmin = Annotated[CurrentUserDTO, Depends(require_user_admin(Action.CREATE))]
UpdateAdmin = Annotated[CurrentUserDTO, Depends(require_user_admin(Action.UPDATE))]
DeleteAdmin = Annotated[CurrentUserDTO, Depends(require_user_admin(Action.DELETE))]

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
    responses={200: paginated_example(USER_EXAMPLE), **COMMON_ERRORS},
)
async def get_users(db: DBDep, pagination: PaginationDep, filters: FilterDep, actor: ReadAdmin):
    data = await UserService(db).get_all_users(filters, actor, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Users retrieved successfully.")


@router.get(
    "/grantable-permissions",
    summary="Права, которые текущий пользователь может выдать сотруднику роли",
    description=(
        "Для формы создания/редактирования сотрудника. Админ направления получает права "
        "своей роли, которые есть у него самого (`role_id` можно не передавать). "
        "Super Admin передаёт `role_id` и получает все права этой роли."
    ),
    responses={
        200: success_example(
            {
                "role_id": 2,
                "role_code": "FUND_OPERATOR",
                "permissions": ["applications.read", "applications.update"],
            },
            "Grantable permissions retrieved.",
        ),
        **COMMON_ERRORS,
    },
)
async def grantable_permissions(db: DBDep, actor: CreateAdmin, role_id: int | None = None):
    data = await UserService(db).get_grantable_permissions(actor, role_id)
    return ResponseBuilder.success(data=data, message="Grantable permissions retrieved.")


@router.get(
    "/{user_id}",
    summary="Профиль пользователя",
    responses={200: success_example(USER_EXAMPLE, "User found."), **COMMON_ERRORS},
)
async def get_user(user_id: int, db: DBDep, actor: ReadAdmin):
    user = await UserService(db).get_user(user_id, actor)
    return ResponseBuilder.success(data=user, message="User found.")


@router.post(
    "",
    summary="Создание сотрудника (роль + ПИНФЛ для входа через YIA Portal и/или пароль)",
    description=(
        "Сотрудник Фонда, банка или Совета входит через YIA Portal: при входе он "
        "находится по `pinfl` и попадает в кабинет своей роли. `password` нужен только "
        "для входа по логину и паролю; хотя бы одно из полей обязательно. "
        "Смена `pinfl` снимает привязку к учётке портала и закрывает сессии.\n\n"
        "**Админ направления** создаёт сотрудников только своего направления: роль "
        "(и банк) подставляются его собственные, `permissions` — только из его прав. "
        "Без `permissions` выдаются все права, которые создающий может выдать для роли. "
        "`is_direction_admin` назначает только Super Admin."
    ),
    responses={
        201: success_example(USER_EXAMPLE, "User created successfully."),
        409: CONFLICT,
        **COMMON_ERRORS,
    },
)
async def create_user(data: UserRequestAddDTO, db: DBDep, actor: CreateAdmin):
    user = await UserService(db).add_user(data, actor)
    return ResponseBuilder.success(data=user, message="User created successfully.", status_code=201)


@router.patch(
    "/{user_id}",
    summary="Изменение пользователя",
    responses={
        200: success_example(USER_EXAMPLE, "User updated successfully."),
        409: CONFLICT,
        **COMMON_ERRORS,
    },
)
async def update_user(user_id: int, data: UserRequestUpdateDTO, db: DBDep, actor: UpdateAdmin):
    user = await UserService(db).edit_user(user_id, data, actor)
    return ResponseBuilder.success(data=user, message="User updated successfully.")


@router.post(
    "/{user_id}/status",
    summary="Перевод в статус «активен» / «заблокирован»",
    responses={200: success_example(USER_EXAMPLE, "User status updated."), **COMMON_ERRORS},
)
async def set_user_status(user_id: int, data: UserStatusUpdateDTO, db: DBDep, actor: UpdateAdmin):
    user = await UserService(db).set_status(user_id, data, actor)
    return ResponseBuilder.success(data=user, message="User status updated.")


@router.post(
    "/{user_id}/role",
    summary="Назначение / отзыв роли и привязка scope (банк)",
    responses={200: success_example(USER_EXAMPLE, "Role assigned."), **COMMON_ERRORS},
)
async def assign_role(user_id: int, data: UserRoleAssignDTO, db: DBDep, actor: UpdateAdmin):
    user = await UserService(db).assign_role(user_id, data, actor)
    return ResponseBuilder.success(data=user, message="Role assigned.")


@router.delete(
    "/{user_id}",
    summary="Удаление пользователя",
    responses={200: success_example(None, "User deleted successfully."), **COMMON_ERRORS},
)
async def delete_user(user_id: int, db: DBDep, actor: DeleteAdmin):
    await UserService(db).delete_user(user_id, actor)
    return ResponseBuilder.success(message="User deleted successfully.")


@router.get(
    "/{user_id}/sessions",
    summary="Сессии пользователя (refresh-токены, последний вход)",
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
async def get_sessions(user_id: int, db: DBDep, actor: ReadAdmin):
    data = await UserService(db).get_sessions(user_id, actor)
    return ResponseBuilder.success(data=data, message="Sessions retrieved.")


@router.delete(
    "/{user_id}/sessions",
    summary="Завершить все сессии пользователя",
    responses={200: success_example(None, "Sessions revoked."), **COMMON_ERRORS},
)
async def revoke_sessions(user_id: int, db: DBDep, actor: UpdateAdmin):
    await UserService(db).revoke_sessions(user_id, actor)
    return ResponseBuilder.success(message="Sessions revoked.")
