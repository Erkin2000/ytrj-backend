from datetime import UTC, datetime

from sqlalchemy import or_, select, update

from src.account.mappers import UserDataMapper
from src.account.models.user_model import UserORM, UserStatus
from src.account.schemas.user_schema import CurrentUserDTO, UserDetailDTO, UserFilterDTO
from src.rbac.models.role_model import RoleORM
from src.utils.base_rep.base_rep import BaseRepository


class UserRepository(BaseRepository):
    model = UserORM
    mapper = UserDataMapper

    async def get_all(
        self,
        filters: UserFilterDTO,
        page: int | None = None,
        per_page: int | None = None,
    ) -> dict:
        stmt = select(self.model).order_by(self.model.id)

        if filters.search:
            pattern = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    self.model.username.ilike(pattern),
                    self.model.full_name.ilike(pattern),
                    self.model.phone.ilike(pattern),
                    self.model.pinfl.ilike(pattern),
                )
            )
        if filters.role_id is not None:
            stmt = stmt.where(self.model.role_id == filters.role_id)
        if filters.role_code:
            stmt = stmt.join(RoleORM, RoleORM.id == self.model.role_id).where(
                RoleORM.code == filters.role_code
            )
        if filters.status is not None:
            stmt = stmt.where(self.model.status == filters.status)
        if filters.bank_id is not None:
            stmt = stmt.where(self.model.bank_id == filters.bank_id)

        return await self.paginate(stmt, page, per_page)

    async def get_detail(self, user_id: int) -> UserDetailDTO | None:
        user = await self.session.get(self.model, user_id)
        return self.mapper.map_to_detail(user) if user else None

    async def get_orm_by_id(self, user_id: int) -> UserORM | None:
        return await self.session.get(self.model, user_id)

    async def get_orm_by_username(self, username: str) -> UserORM | None:
        return await self.session.scalar(select(self.model).where(self.model.username == username))

    async def get_orm_by_sso_sub(self, sub: str) -> UserORM | None:
        return await self.session.scalar(select(self.model).where(self.model.sso_sub == sub))

    async def get_orm_by_pinfl(self, pinfl: str) -> UserORM | None:
        return await self.session.scalar(select(self.model).where(self.model.pinfl == pinfl))

    async def get_access(self, user_id: int) -> CurrentUserDTO | None:
        user = await self.session.get(self.model, user_id)
        return self.mapper.map_to_current_user(user) if user else None

    async def get_active_by_role_code(self, role_code: str) -> list[UserORM]:
        stmt = (
            select(self.model)
            .join(RoleORM, RoleORM.id == self.model.role_id)
            .where(RoleORM.code == role_code, self.model.status == UserStatus.ACTIVE)
            .order_by(self.model.id)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def touch_last_login(self, user_id: int) -> None:
        await self.session.execute(
            update(self.model)
            .where(self.model.id == user_id)
            .values(last_login_at=datetime.now(UTC))
        )
