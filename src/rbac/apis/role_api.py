from fastapi import APIRouter, Depends

from src.common.dependencies import (
    DBDep,
    PaginationDep,
    require_any_permission,
    require_permission,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, CONFLICT, paginated_example, success_example
from src.rbac.permissions import Action, Module
from src.rbac.schemas.role_schema import RoleRequestAddDTO, RoleRequestUpdateDTO
from src.rbac.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["RBAC: роли"])

# Список ролей нужен и форме пользователя: roles.read или users.create / users.update.
ROLES_READ = Depends(require_any_permission("roles.read", "users.create", "users.update"))

ROLE_EXAMPLE = {
    "id": 2,
    "code": "FUND_OPERATOR",
    "translations": [
        {
            "language": "ru",
            "name": "Оператор Фонда",
            "description": "Повседневные бизнес-процессы Фонда: заявки, Совет, финансирование",
        },
        {
            "language": "uz",
            "name": "Jamgʻarma operatori",
            "description": "Jamgʻarmaning kundalik jarayonlari: arizalar, Kengash, moliyalashtirish",
        },
        {
            "language": "en",
            "name": "Fund operator",
            "description": "Day-to-day Fund processes: applications, Council, financing",
        },
    ],
    "is_superuser": False,
    "is_system": True,
    "permissions": ["applications.read", "applications.approve"],
}


@router.get(
    "",
    summary="Каталог ролей",
    dependencies=[ROLES_READ],
    responses={200: paginated_example(ROLE_EXAMPLE), **COMMON_ERRORS},
)
async def get_roles(db: DBDep, pagination: PaginationDep):
    data = await RoleService(db).get_all_roles(pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="Roles retrieved successfully.")


@router.get(
    "/options",
    summary="Роли для выбора в форме пользователя (id, код, название)",
    description=(
        "Лёгкий список без прав и пагинации: все роли, кроме заявителя (её нельзя назначить "
        "вручную). Доступно с `roles.read`, `users.create` или `users.update`."
    ),
    dependencies=[ROLES_READ],
    responses={
        200: success_example(
            [
                {
                    "id": 2,
                    "code": "FUND_OPERATOR",
                    "translations": [
                        {"language": "ru", "name": "Оператор Фонда"},
                        {"language": "uz", "name": "Jamgʻarma operatori"},
                        {"language": "en", "name": "Fund operator"},
                    ],
                    "is_superuser": False,
                }
            ],
            "Role options retrieved.",
        ),
        **COMMON_ERRORS,
    },
)
async def get_role_options(db: DBDep):
    data = await RoleService(db).get_options()
    return ResponseBuilder.success(data=data, message="Role options retrieved.")


@router.get(
    "/{role_id}",
    summary="Роль по ID с матрицей прав",
    dependencies=[ROLES_READ],
    responses={200: success_example(ROLE_EXAMPLE, "Role found."), **COMMON_ERRORS},
)
async def get_role(role_id: int, db: DBDep):
    role = await RoleService(db).get_role_by_id(role_id)
    return ResponseBuilder.success(data=role, message="Role found.")


@router.post(
    "",
    status_code=201,
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
