from src.common.responses.exceptions import (
    RoleCodeAlreadyExistsException,
    RoleInUseException,
    RoleNotFoundException,
    SystemRoleException,
)
from src.rbac.schemas.role_schema import (
    RoleAddDTO,
    RoleDTO,
    RoleRequestAddDTO,
    RoleRequestUpdateDTO,
    RoleUpdateDTO,
)
from src.rbac.services.permission_service import PermissionService
from src.utils.base_service import BaseService


class RoleService(BaseService):
    @property
    def permission_service(self) -> PermissionService:
        return PermissionService(self.db)

    async def get_all_roles(self, page: int | None, per_page: int | None) -> dict:
        return await self.db.role.get_all(page=page, per_page=per_page)

    async def get_role_by_id(self, role_id: int) -> RoleDTO:
        role = await self.db.role.get_one_or_none(id=role_id)
        if role is None:
            raise RoleNotFoundException()
        return role

    async def add_role(self, data: RoleRequestAddDTO) -> RoleDTO:
        if await self.db.role.get_by_code(data.code):
            raise RoleCodeAlreadyExistsException()

        # Коды прав проверяются до вставки роли, чтобы не создавать
        # роль, которой не удастся назначить права.
        permission_ids = await self.permission_service.get_permission_ids(data.permissions)

        role = await self.db.role.add(RoleAddDTO(**data.model_dump(exclude={"permissions"})))

        await self.db.permission.set_role_permissions(
            role_id=role.id,
            permission_ids=permission_ids,
        )
        await self.db.commit()

        return await self.get_role_by_id(role.id)

    async def update_role(self, role_id: int, data: RoleRequestUpdateDTO) -> RoleDTO:
        role = await self.get_role_by_id(role_id)

        update_data = data.model_dump(exclude_unset=True, exclude={"permissions"})

        if role.is_system:
            # У системной роли нельзя менять код и флаг суперпользователя.
            if "code" in update_data and update_data["code"] != role.code:
                raise SystemRoleException()
            if "is_superuser" in update_data and update_data["is_superuser"] != role.is_superuser:
                raise SystemRoleException()

        if "code" in update_data and update_data["code"] != role.code:
            if await self.db.role.get_by_code(update_data["code"]):
                raise RoleCodeAlreadyExistsException()

        if update_data:
            await self.db.role.edit(
                data=RoleUpdateDTO(**update_data),
                exclude_unset=True,
                id=role_id,
            )

        if data.permissions is not None:
            await self.permission_service.set_role_permissions(
                role_id=role_id,
                codes=data.permissions,
            )

        await self.db.commit()
        return await self.get_role_by_id(role_id)

    async def delete_role(self, role_id: int) -> None:
        role = await self.get_role_by_id(role_id)

        if role.is_system:
            raise SystemRoleException()
        if await self.db.role.count_users(role_id):
            raise RoleInUseException()

        await self.db.role.delete(id=role_id)
        await self.db.commit()
