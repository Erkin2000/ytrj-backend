"""Управление сотрудниками.

Два уровня доступа:
- глобальный — право users.<action> (Super Admin): любые пользователи;
- админ направления (users.is_direction_admin) — только рядовые сотрудники
  своего направления (та же роль; для банка — тот же банк). Выдаёт только те
  права, которые есть у него самого, и только в пределах прав роли.

Администраторов (суперпользователей и админов направлений) назначает и
меняет только Super Admin.
"""

import asyncio

from src.account.mappers import UserDataMapper
from src.account.models.user_model import UserORM, UserStatus
from src.account.schemas.user_schema import (
    CurrentUserDTO,
    GrantablePermissionsDTO,
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
    AdminManagementException,
    ApplicantRoleNotAssignableException,
    BankNotFoundException,
    BankScopeRequiredException,
    DirectionAdminRoleException,
    PermissionDeniedException,
    PermissionsNotGrantableException,
    PinflAlreadyExistsException,
    RoleNotFoundException,
    RoleRequiredException,
    SelfBlockException,
    UsernameAlreadyExistsException,
    UserNotFoundException,
    UserOutOfScopeException,
)
from src.rbac.access import DIRECTION_ROLES, role_ceiling, uses_personal_permissions
from src.rbac.models.role_model import RoleORM
from src.rbac.permissions import Action, Module, RoleCode, permission_code
from src.rbac.services.permission_service import PermissionService
from src.utils.base_service import BaseService


class UserService(BaseService):
    # ---------- кто кем управляет ----------

    @staticmethod
    def _is_global(actor: CurrentUserDTO, action: Action) -> bool:
        return actor.has_permission(permission_code(Module.USERS, action))

    @staticmethod
    def _direction(actor: CurrentUserDTO) -> tuple[int, int | None]:
        """(role_id, bank_id) направления админа; bank_id только у банка."""
        if not actor.is_direction_admin or actor.role is None:
            raise PermissionDeniedException()
        if actor.role.code not in DIRECTION_ROLES:
            raise PermissionDeniedException()
        bank_id = actor.bank_id if actor.role.code == RoleCode.BANK_EMPLOYEE else None
        return actor.role.id, bank_id

    def _in_direction(self, actor: CurrentUserDTO, target: UserORM) -> bool:
        role_id, bank_id = self._direction(actor)
        return target.role_id == role_id and (bank_id is None or target.bank_id == bank_id)

    @staticmethod
    def _is_admin(user: UserORM) -> bool:
        return user.is_direction_admin or bool(user.role and user.role.is_superuser)

    async def _get_orm(self, user_id: int) -> UserORM:
        user = await self.db.user.get_orm_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        return user

    async def _get_visible(self, user_id: int, actor: CurrentUserDTO) -> UserORM:
        target = await self._get_orm(user_id)
        if self._is_global(actor, Action.READ) or self._in_direction(actor, target):
            return target
        # Чужое направление: не раскрываем, что пользователь существует.
        raise UserNotFoundException()

    async def _get_manageable(self, user_id: int, actor: CurrentUserDTO, action: Action) -> UserORM:
        target = await self._get_orm(user_id)
        if self._is_global(actor, action):
            if not actor.is_superuser and self._is_admin(target):
                raise AdminManagementException()
            return target

        if not self._in_direction(actor, target):
            raise UserOutOfScopeException()
        if target.id == actor.id or self._is_admin(target):
            raise UserOutOfScopeException()
        return target

    # ---------- роли и права ----------

    async def _get_role(self, role_id: int) -> RoleORM:
        role = await self.db.role.get_orm_one_or_none(id=role_id)
        if role is None:
            raise RoleNotFoundException()
        return role

    async def _validate_role_and_scope(self, role: RoleORM | None, bank_id: int | None) -> None:
        if bank_id is not None and not await self.db.bank.exists(id=bank_id):
            raise BankNotFoundException()
        if role is None:
            return
        # Сотрудник банка без привязки к банку не увидит ни одной заявки.
        if role.code == RoleCode.BANK_EMPLOYEE and bank_id is None:
            raise BankScopeRequiredException()
        # Заявители появляются только через YIA SSO; вручную эту роль не выдаём.
        if role.code == RoleCode.APPLICANT:
            raise ApplicantRoleNotAssignableException()

    @staticmethod
    def _check_admin_assignment(
        actor: CurrentUserDTO, role: RoleORM | None, is_direction_admin: bool
    ) -> None:
        if role is not None and role.is_superuser and not actor.is_superuser:
            raise AdminManagementException()
        if is_direction_admin:
            if not actor.is_superuser:
                raise AdminManagementException()
            if role is None or role.code not in DIRECTION_ROLES:
                raise DirectionAdminRoleException()

    @staticmethod
    def _grantable(actor: CurrentUserDTO, role: RoleORM) -> set[str]:
        ceiling = role_ceiling(role)
        return ceiling if actor.is_superuser else ceiling & actor.permissions

    async def _set_permissions(
        self,
        user_id: int,
        actor: CurrentUserDTO,
        role: RoleORM | None,
        requested: list[str] | None,
    ) -> None:
        """Записывает личные права. None — всё, что создающий может выдать для роли."""
        if role is None or not uses_personal_permissions(role):
            await self.db.permission.set_user_permissions(user_id, [])
            return

        grantable = self._grantable(actor, role)
        codes = grantable if requested is None else set(requested)
        permission_ids = await PermissionService(self.db).get_permission_ids(sorted(codes))

        extra = codes - grantable
        if extra:
            raise PermissionsNotGrantableException(
                "Permissions are outside your rights or the role: " + ", ".join(sorted(extra))
            )
        await self.db.permission.set_user_permissions(user_id, permission_ids)

    async def _ensure_pinfl_free(self, pinfl: str | None, user_id: int | None = None) -> None:
        # По ПИНФЛ YIA SSO находит сотрудника, поэтому он должен быть уникален.
        if pinfl is None:
            return
        owner = await self.db.user.get_orm_by_pinfl(pinfl)
        if owner is not None and owner.id != user_id:
            raise PinflAlreadyExistsException()

    async def _detail(self, user_id: int) -> UserDetailDTO:
        user = await self.db.user.get_orm_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        # expire_on_commit=False: после UPDATE/INSERT прав объект в сессии устарел.
        await self.db.session.refresh(user)
        return UserDataMapper.map_to_detail(user)

    # ---------- чтение ----------

    async def get_all_users(
        self,
        filters: UserFilterDTO,
        actor: CurrentUserDTO,
        page: int | None,
        per_page: int | None,
    ) -> dict:
        if not self._is_global(actor, Action.READ):
            role_id, bank_id = self._direction(actor)
            scope = {"role_id": role_id}
            if bank_id is not None:
                scope["bank_id"] = bank_id
            filters = filters.model_copy(update=scope)
        return await self.db.user.get_all(filters, page=page, per_page=per_page)

    async def get_user(self, user_id: int, actor: CurrentUserDTO) -> UserDetailDTO:
        await self._get_visible(user_id, actor)
        return await self._detail(user_id)

    async def get_grantable_permissions(
        self, actor: CurrentUserDTO, role_id: int | None
    ) -> GrantablePermissionsDTO:
        """Какие права текущий пользователь может выдать сотруднику роли role_id."""
        if not self._is_global(actor, Action.CREATE):
            own_role_id, _ = self._direction(actor)
            if role_id not in (None, own_role_id):
                raise UserOutOfScopeException()
            role_id = own_role_id
        if role_id is None:
            raise RoleRequiredException()

        role = await self._get_role(role_id)
        permissions = self._grantable(actor, role) if uses_personal_permissions(role) else set()
        return GrantablePermissionsDTO(
            role_id=role.id, role_code=role.code, permissions=sorted(permissions)
        )

    # ---------- изменение ----------

    async def add_user(self, data: UserRequestAddDTO, actor: CurrentUserDTO) -> UserDetailDTO:
        role_id, bank_id = data.role_id, data.bank_id

        if not self._is_global(actor, Action.CREATE):
            own_role_id, own_bank_id = self._direction(actor)
            if role_id not in (None, own_role_id):
                raise UserOutOfScopeException()
            if own_bank_id is not None and bank_id not in (None, own_bank_id):
                raise UserOutOfScopeException()
            role_id = own_role_id
            bank_id = own_bank_id if own_bank_id is not None else bank_id

        if role_id is None:
            raise RoleRequiredException()

        if await self.db.user.get_orm_by_username(data.username):
            raise UsernameAlreadyExistsException()
        await self._ensure_pinfl_free(data.pinfl)

        role = await self._get_role(role_id)
        await self._validate_role_and_scope(role, bank_id)
        self._check_admin_assignment(actor, role, data.is_direction_admin)

        hashed_password = (
            await asyncio.to_thread(hash_password, data.password) if data.password else None
        )

        user = await self.db.user.add(
            UserAddDTO(
                **data.model_dump(exclude={"password", "permissions", "role_id", "bank_id"}),
                role_id=role_id,
                bank_id=bank_id,
                hashed_password=hashed_password,
            )
        )
        await self._set_permissions(user.id, actor, role, data.permissions)
        await self.db.commit()
        return await self._detail(user.id)

    async def edit_user(
        self, user_id: int, data: UserRequestUpdateDTO, actor: CurrentUserDTO
    ) -> UserDetailDTO:
        target = await self._get_manageable(user_id, actor, Action.UPDATE)
        is_global = self._is_global(actor, Action.UPDATE)

        update_data = data.model_dump(exclude_unset=True, exclude={"password", "permissions"})

        if not is_global:
            if "role_id" in update_data and update_data["role_id"] != target.role_id:
                raise UserOutOfScopeException()
            if "bank_id" in update_data and update_data["bank_id"] != target.bank_id:
                raise UserOutOfScopeException()

        if "username" in update_data and update_data["username"] != target.username:
            if await self.db.user.get_orm_by_username(update_data["username"]):
                raise UsernameAlreadyExistsException()

        pinfl_changed = "pinfl" in update_data and update_data["pinfl"] != target.pinfl
        if pinfl_changed:
            await self._ensure_pinfl_free(update_data["pinfl"], user_id)
            # Новый ПИНФЛ — другой человек на портале: снимаем старую привязку SSO.
            update_data["sso_sub"] = None

        role_id = update_data.get("role_id", target.role_id)
        bank_id = update_data.get("bank_id", target.bank_id)
        is_admin = update_data.get("is_direction_admin", target.is_direction_admin)
        role = await self._get_role(role_id) if role_id is not None else None

        await self._validate_role_and_scope(role, bank_id)
        if is_admin != target.is_direction_admin or role_id != target.role_id:
            self._check_admin_assignment(actor, role, bool(is_admin))

        role_changed = role_id != target.role_id
        update_dto = UserUpdateDTO(**update_data)
        if data.password:
            update_dto.hashed_password = await asyncio.to_thread(hash_password, data.password)

        await self.db.user.edit(update_dto, exclude_unset=True, id=user_id)

        if data.permissions is not None or role_changed:
            # Новая роль — новый потолок: без явного списка выдаём всё доступное.
            await self._set_permissions(user_id, actor, role, data.permissions)

        if data.password or pinfl_changed:
            # Смена пароля или ПИНФЛ завершает все активные сессии пользователя.
            await self.db.refresh_token.delete(user_id=user_id)

        await self.db.commit()
        return await self._detail(user_id)

    async def set_status(
        self,
        user_id: int,
        data: UserStatusUpdateDTO,
        actor: CurrentUserDTO,
    ) -> UserDetailDTO:
        if user_id == actor.id and data.status == UserStatus.BLOCKED:
            raise SelfBlockException()
        await self._get_manageable(user_id, actor, Action.UPDATE)

        await self.db.user.edit(UserUpdateDTO(status=data.status), exclude_unset=True, id=user_id)

        if data.status == UserStatus.BLOCKED:
            # Блокировка завершает все сессии.
            await self.db.refresh_token.delete(user_id=user_id)

        await self.db.commit()
        return await self._detail(user_id)

    async def assign_role(
        self, user_id: int, data: UserRoleAssignDTO, actor: CurrentUserDTO
    ) -> UserDetailDTO:
        target = await self._get_manageable(user_id, actor, Action.UPDATE)
        # Админ направления роль не меняет: у его сотрудников роль одна.
        if not self._is_global(actor, Action.UPDATE):
            raise UserOutOfScopeException()

        bank_id = data.bank_id if "bank_id" in data.model_fields_set else target.bank_id
        role = await self._get_role(data.role_id) if data.role_id is not None else None
        await self._validate_role_and_scope(role, bank_id)

        # Без роли направления админом направления быть нельзя.
        keep_admin = target.is_direction_admin and role is not None
        if role is None or role.code not in DIRECTION_ROLES:
            keep_admin = False
        self._check_admin_assignment(actor, role, keep_admin)

        await self.db.user.edit(
            UserUpdateDTO(role_id=data.role_id, bank_id=bank_id, is_direction_admin=keep_admin),
            exclude_unset=True,
            id=user_id,
        )
        if data.role_id != target.role_id:
            await self._set_permissions(user_id, actor, role, None)

        await self.db.commit()
        return await self._detail(user_id)

    async def delete_user(self, user_id: int, actor: CurrentUserDTO) -> None:
        await self._get_manageable(user_id, actor, Action.DELETE)
        await self.db.user.delete(id=user_id)
        await self.db.commit()

    async def get_sessions(self, user_id: int, actor: CurrentUserDTO) -> list[UserSessionDTO]:
        await self._get_visible(user_id, actor)
        tokens = await self.db.refresh_token.get_user_sessions(user_id)
        return [UserSessionDTO(**t.model_dump()) for t in tokens]

    async def revoke_sessions(self, user_id: int, actor: CurrentUserDTO) -> None:
        await self._get_manageable(user_id, actor, Action.UPDATE)
        await self.db.refresh_token.delete(user_id=user_id)
        await self.db.commit()
