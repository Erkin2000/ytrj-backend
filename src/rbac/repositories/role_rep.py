from sqlalchemy import func, select

from src.account.models.user_model import UserORM
from src.rbac.mappers import RoleDataMapper
from src.rbac.models.role_model import RoleORM
from src.utils.base_rep.base_rep import BaseRepository


class RoleRepository(BaseRepository):
    model = RoleORM
    mapper = RoleDataMapper

    async def get_all(self, page: int | None = None, per_page: int | None = None) -> dict:
        stmt = select(self.model).order_by(self.model.id)
        return await self.paginate(stmt, page, per_page)

    async def get_by_code(self, code: str) -> RoleORM | None:
        return await self.session.scalar(select(self.model).where(self.model.code == code))

    async def count_users(self, role_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count()).select_from(UserORM).where(UserORM.role_id == role_id)
            )
            or 0
        )
