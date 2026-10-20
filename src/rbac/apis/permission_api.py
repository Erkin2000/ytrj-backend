from fastapi import APIRouter, Depends

from src.common.dependencies import DBDep, require_permission
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import COMMON_ERRORS, success_example
from src.rbac.permissions import Action, Module
from src.rbac.services.permission_service import PermissionService

router = APIRouter(
    prefix="/permissions",
    tags=["RBAC: права"],
    dependencies=[Depends(require_permission(Module.ROLES, Action.READ))],
)


@router.get(
    "",
    summary="Каталог прав (плоский список)",
    responses={
        200: success_example(
            [
                {
                    "id": 1,
                    "code": "users.read",
                    "name": "Просмотр пользователей",
                    "description": "...",
                }
            ],
            "Permissions retrieved successfully.",
        ),
        **COMMON_ERRORS,
    },
)
async def get_permissions(db: DBDep):
    data = await PermissionService(db).get_all_permissions()
    return ResponseBuilder.success(data=data, message="Permissions retrieved successfully.")


@router.get(
    "/matrix",
    summary="Матрица прав по модулям (Create / Read / Update / Delete / Approve)",
    responses={
        200: success_example(
            [
                {
                    "module": "applications",
                    "module_name": "Заявки",
                    "permissions": [
                        {"id": 10, "code": "applications.read", "name": "Просмотр заявок"}
                    ],
                }
            ],
            "Permission matrix retrieved successfully.",
        ),
        **COMMON_ERRORS,
    },
)
async def get_permission_matrix(db: DBDep):
    data = await PermissionService(db).get_grouped_permissions()
    return ResponseBuilder.success(data=data, message="Permission matrix retrieved successfully.")
