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
                    "translations": [
                        {
                            "language": "ru",
                            "name": "Просмотр пользователей",
                            "description": "Просмотр, поиск и фильтрация профилей",
                        },
                        {
                            "language": "uz",
                            "name": "Foydalanuvchilarni koʻrish",
                            "description": "Profillarni koʻrish, qidirish va saralash",
                        },
                        {
                            "language": "en",
                            "name": "View users",
                            "description": "View, search and filter profiles",
                        },
                    ],
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
                    "translations": [
                        {"language": "ru", "name": "Заявки"},
                        {"language": "uz", "name": "Arizalar"},
                        {"language": "en", "name": "Applications"},
                    ],
                    "permissions": [
                        {
                            "id": 10,
                            "code": "applications.read",
                            "translations": [
                                {
                                    "language": "ru",
                                    "name": "Просмотр заявок",
                                    "description": "Просмотр заявок в рамках scope",
                                },
                                {
                                    "language": "uz",
                                    "name": "Arizalarni koʻrish",
                                    "description": "Scope doirasidagi arizalarni koʻrish",
                                },
                                {
                                    "language": "en",
                                    "name": "View applications",
                                    "description": "View applications within scope",
                                },
                            ],
                        }
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
