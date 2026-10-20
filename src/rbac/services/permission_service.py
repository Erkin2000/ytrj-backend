from src.common.responses.exceptions import PermissionNotFoundException
from src.rbac.permissions import MODULE_NAMES
from src.rbac.schemas.permission_schema import PermissionDTO, PermissionGroupDTO
from src.utils.base_service import BaseService


class PermissionService(BaseService):
    async def get_all_permissions(self) -> list[PermissionDTO]:
        return await self.db.permission.get_all()

    async def get_grouped_permissions(self) -> list[PermissionGroupDTO]:
        """Матрица прав по модулям для UI (Create/Read/Update/Delete/Approve)."""
        permissions = await self.db.permission.get_all()
        groups: dict[str, list[PermissionDTO]] = {}

        for permission in permissions:
            module = permission.code.split(".", 1)[0]
            groups.setdefault(module, []).append(permission)

        return [
            PermissionGroupDTO(
                module=module,
                module_name=MODULE_NAMES.get(module, module),
                permissions=items,
            )
            for module, items in groups.items()
        ]

    async def get_permission_ids(self, codes: list[str]) -> list[int]:
        codes = list(dict.fromkeys(codes))
        if not codes:
            return []

        permissions = await self.db.permission.get_by_codes(codes)

        found = {permission.code for permission in permissions}
        unknown = [code for code in codes if code not in found]

        if unknown:
            raise PermissionNotFoundException(f"Unknown permission code: {', '.join(unknown)}")

        return [permission.id for permission in permissions]

    async def set_role_permissions(self, role_id: int, codes: list[str]) -> None:
        permission_ids = await self.get_permission_ids(codes)
        await self.db.permission.set_role_permissions(
            role_id=role_id,
            permission_ids=permission_ids,
        )
