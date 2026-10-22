import asyncio

from src.account.models.user_model import UserStatus
from src.account.schemas.user_schema import (
    CurrentUserDTO,
    UserAddDTO,
    UserDetailDTO,
    UserFilterDTO,
    UserRequestAddDTO,
    UserRequestUpdateDTO,
    UserRoleAssignDTO,
    UserSessionDTO,
    UserStatusUpdateDTO,
    UserUpdateDTO,
)
from src.auth.services.password_service import hash_password
from src.common.responses.exceptions import (
    ApplicantRoleNotAssignableException,
    BankNotFoundException,
    BankScopeRequiredException,
    RoleNotFoundException,
    SelfBlockException,
    UsernameAlreadyExistsException,
    UserNotFoundException,
)
from src.rbac.permissions import RoleCode
from src.utils.base_service import BaseService


class UserService(BaseService):
    async def get_all_users(
        self,
        filters: UserFilterDTO,
        page: int | None,
        per_page: int | None,
    ) -> dict:
        return await self.db.user.get_all(filters, page=page, per_page=per_page)

    async def get_user(self, user_id: int) -> UserDetailDTO:
        user = await self.db.user.get_detail(user_id)
        if user is None:
            raise UserNotFoundException()
        return user

    async def _validate_role_and_scope(self, role_id: int | None, bank_id: int | None) -> None:
        role = None
        if role_id is not None:
            role = await self.db.role.get_one_or_none(id=role_id)
            if role is None:
                raise RoleNotFoundException()

        if bank_id is not None and not await self.db.bank.exists(id=bank_id):
            raise BankNotFoundException()

        # Сотрудник банка без привязки к банку не увидит ни одной заявки.
        if role is not None and role.code == RoleCode.BANK_EMPLOYEE and bank_id is None:
            raise BankScopeRequiredException()

        # Заявители появляются только через YIA SSO; вручную эту роль не выдаём.
        if role is not None and role.code == RoleCode.APPLICANT:
            raise ApplicantRoleNotAssignableException()

    async def add_user(self, data: UserRequestAddDTO) -> UserDetailDTO:
        if await self.db.user.get_orm_by_username(data.username):
            raise UsernameAlreadyExistsException()

        await self._validate_role_and_scope(data.role_id, data.bank_id)

        hashed_password = await asyncio.to_thread(hash_password, data.password)

        user = await self.db.user.add(
            UserAddDTO(
                **data.model_dump(exclude={"password"}),
                hashed_password=hashed_password,
            )
        )
        await self.db.commit()
        return await self.get_user(user.id)

    async def edit_user(self, user_id: int, data: UserRequestUpdateDTO) -> UserDetailDTO:
        user = await self.get_user(user_id)

        update_data = data.model_dump(exclude_unset=True, exclude={"password"})

        if "username" in update_data and update_data["username"] != user.username:
            if await self.db.user.get_orm_by_username(update_data["username"]):
                raise UsernameAlreadyExistsException()

        role_id = update_data.get("role_id", user.role.id if user.role else None)
        bank_id = update_data.get("bank_id", user.bank.id if user.bank else None)
        await self._validate_role_and_scope(role_id, bank_id)

        update_dto = UserUpdateDTO(**update_data)

        if data.password:
            update_dto.hashed_password = await asyncio.to_thread(hash_password, data.password)

        await self.db.user.edit(update_dto, exclude_unset=True, id=user_id)

        if data.password:
            # Смена пароля завершает все активные сессии пользователя.
            await self.db.refresh_token.delete(user_id=user_id)

        await self.db.commit()
        return await self.get_user(user_id)

    async def set_status(
        self,
        user_id: int,
        data: UserStatusUpdateDTO,
        current: CurrentUserDTO,
    ) -> UserDetailDTO:
        await self.get_user(user_id)

        if user_id == current.id and data.status == UserStatus.BLOCKED:
            raise SelfBlockException()

        await self.db.user.edit(UserUpdateDTO(status=data.status), exclude_unset=True, id=user_id)

        if data.status == UserStatus.BLOCKED:
            # Блокировка завершает все сессии.
            await self.db.refresh_token.delete(user_id=user_id)

        await self.db.commit()
        return await self.get_user(user_id)

    async def assign_role(self, user_id: int, data: UserRoleAssignDTO) -> UserDetailDTO:
        user = await self.get_user(user_id)

        bank_id = (
            data.bank_id
            if "bank_id" in data.model_fields_set
            else (user.bank.id if user.bank else None)
        )
        await self._validate_role_and_scope(data.role_id, bank_id)

        await self.db.user.edit(
            UserUpdateDTO(role_id=data.role_id, bank_id=bank_id),
            exclude_unset=True,
            id=user_id,
        )
        await self.db.commit()
        return await self.get_user(user_id)

    async def delete_user(self, user_id: int) -> None:
        await self.get_user(user_id)
        await self.db.user.delete(id=user_id)
        await self.db.commit()

    async def get_sessions(self, user_id: int) -> list[UserSessionDTO]:
        await self.get_user(user_id)
        tokens = await self.db.refresh_token.get_user_sessions(user_id)
        return [UserSessionDTO(**t.model_dump()) for t in tokens]

    async def revoke_sessions(self, user_id: int) -> None:
        await self.get_user(user_id)
        await self.db.refresh_token.delete(user_id=user_id)
        await self.db.commit()
