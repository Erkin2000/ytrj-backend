from fastapi import APIRouter, Depends

from src.common.dependencies import DBDep, PaginationDep, require_permission
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, CONFLICT, paginated_example, success_example
from src.rbac.permissions import Action, Module
from src.rbac.schemas.role_schema import RoleRequestAddDTO, RoleRequestUpdateDTO
from src.rbac.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["RBAC: роли"])

ROLE_EXAMPLE = {
    "id": 2,
    "name": "Оператор Фонда",
    "code": "FUND_OPERATOR",
    "description": "Повседневные бизнес-процессы Фонда",
    "is_superuser": False,
    "is_system": True,
    "permissions": ["applications.read", "applications.approve"],
}


@router.get(
    "",
    summary="Каталог ролей",
    dependencies=[Depends(require_permission(Module.ROLES, Action.READ))],
    responses={200: paginated_example(ROLE_EXAMPLE), **COMMON_ERRORS},
)
async def get_roles(db: DBDep, pagination: PaginationDep):
    data = await RoleService(db).get_all_roles(pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Roles retrieved successfully.")


@router.get(
    "/{role_id}",
    summary="Роль по ID с матрицей прав",
    dependencies=[Depends(require_permission(Module.ROLES, Action.READ))],
    responses={200: success_example(ROLE_EXAMPLE, "Role found."), **COMMON_ERRORS},
)
async def get_role(role_id: int, db: DBDep):
    role = await RoleService(db).get_role_by_id(role_id)
    return ResponseBuilder.success(data=role, message="Role found.")


@router.post(
    "",
    summary="Создание роли",
    dependencies=[Depends(require_permission(Module.ROLES, Action.CREATE))],
    responses={
        201: success_example(ROLE_EXAMPLE, "Role created successfully."),
        409: CONFLICT,
        **COMMON_ERRORS,
    },
)
async def create_role(data: RoleRequestAddDTO, db: DBDep):
    role = await RoleService(db).add_role(data)
    return ResponseBuilder.success(data=role, message="Role created successfully.", status_code=201)


@router.patch(
    "/{role_id}",
    summary="Изменение роли и её разрешений по модулям",
    dependencies=[Depends(require_permission(Module.ROLES, Action.UPDATE))],
    responses={
        200: success_example(ROLE_EXAMPLE, "Role updated successfully."),
        409: CONFLICT,
        **COMMON_ERRORS,
    },
)
async def update_role(role_id: int, data: RoleRequestUpdateDTO, db: DBDep):
    role = await RoleService(db).update_role(role_id, data)
    return ResponseBuilder.success(data=role, message="Role updated successfully.")


@router.delete(
    "/{role_id}",
    summary="Удаление роли (не системной и без пользователей)",
    dependencies=[Depends(require_permission(Module.ROLES, Action.DELETE))],
    responses={
        200: success_example(None, "Role deleted successfully."),
        409: CONFLICT,
        **COMMON_ERRORS,
    },
)
async def delete_role(role_id: int, db: DBDep):
    await RoleService(db).delete_role(role_id)
    return ResponseBuilder.success(message="Role deleted successfully.")
