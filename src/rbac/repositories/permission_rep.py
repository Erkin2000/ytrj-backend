from sqlalchemy import delete, insert, select

from src.rbac.mappers import PermissionDataMapper
from src.rbac.models.permission_model import PermissionORM
from src.rbac.models.role_permission_model import RolePermissionORM
from src.rbac.schemas.permission_schema import PermissionDTO
from src.utils.base_rep.base_rep import BaseRepository


class PermissionRepository(BaseRepository):
    model = PermissionORM
    mapper = PermissionDataMapper

    async def get_all(self) -> list[PermissionDTO]:
        result = await self.session.scalars(select(self.model).order_by(self.model.id))
        return [self.mapper.map_to_domain_entity(m) for m in result.all()]

    async def get_by_codes(self, codes: list[str]) -> list[PermissionDTO]:
        result = await self.session.scalars(select(self.model).where(self.model.code.in_(codes)))
        return [self.mapper.map_to_domain_entity(m) for m in result.all()]

    async def set_role_permissions(self, role_id: int, permission_ids: list[int]) -> None:
        await self.session.execute(
            delete(RolePermissionORM).where(RolePermissionORM.role_id == role_id)
        )
        if permission_ids:
            await self.session.execute(
                insert(RolePermissionORM),
                [{"role_id": role_id, "permission_id": pid} for pid in permission_ids],
            )
