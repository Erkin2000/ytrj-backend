from src.common.responses.exceptions import (
    RoleCodeAlreadyExistsException,
    RoleInUseException,
    RoleNameAlreadyExistsException,
    RoleNotFoundException,
    SystemRoleException,
)
from src.product.enums import Language
from src.product.services.product_service import apply_translations
from src.rbac.mappers import RoleDataMapper
from src.rbac.models.role_model import RoleORM, RoleTranslationORM
from src.rbac.permissions import RoleCode
from src.rbac.schemas.role_schema import (
    RoleDTO,
    RoleRequestAddDTO,
    RoleRequestUpdateDTO,
    RoleShortDTO,
    RoleTranslationDTO,
)
from src.rbac.services.permission_service import PermissionService
from src.utils.base_service import BaseService


def ru_of(translations: list[RoleTranslationDTO]) -> RoleTranslationDTO:
    return next(t for t in translations if t.language == Language.RU)


class RoleService(BaseService):
    @property
    def permission_service(self) -> PermissionService:
        return PermissionService(self.db)

    async def get_all_roles(self, page: int | None, per_page: int | None) -> dict:
        return await self.db.role.get_all(page=page, per_page=per_page)

    async def get_options(self) -> list[RoleShortDTO]:
        roles = await self.db.role.get_orm_list()
        return [RoleDataMapper.map_to_short(r) for r in roles if r.code != RoleCode.APPLICANT]

    async def get_role_by_id(self, role_id: int) -> RoleDTO:
        role = await self.db.role.get_one_or_none(id=role_id)
        if role is None:
            raise RoleNotFoundException()
        return role

    async def add_role(self, data: RoleRequestAddDTO) -> RoleDTO:
        if await self.db.role.get_by_code(data.code):
            raise RoleCodeAlreadyExistsException()
        ru = ru_of(data.translations)
        await self._check_name(ru.name)

        # Коды прав проверяются до вставки роли, чтобы не создавать
        # роль, которой не удастся назначить права.
        permission_ids = await self.permission_service.get_permission_ids(data.permissions)

        role = RoleORM(
            code=data.code,
            name=ru.name,
            description=ru.description,
            is_superuser=data.is_superuser,
            is_system=False,
        )
        apply_translations(role.translations, data.translations, RoleTranslationORM)
        self.db.session.add(role)
        await self.db.session.flush()

        await self.db.permission.set_role_permissions(
            role_id=role.id,
            permission_ids=permission_ids,
        )
        await self.db.commit()

        return await self.get_role_by_id(role.id)

    async def update_role(self, role_id: int, data: RoleRequestUpdateDTO) -> RoleDTO:
        role = await self.db.role.get_orm(role_id)
        if role is None:
            raise RoleNotFoundException()

        if role.is_system:
            # У системной роли нельзя менять код и флаг суперпользователя.
            if data.code is not None and data.code != role.code:
                raise SystemRoleException()
            if data.is_superuser is not None and data.is_superuser != role.is_superuser:
                raise SystemRoleException()

        if data.code is not None and data.code != role.code:
            if await self.db.role.get_by_code(data.code):
                raise RoleCodeAlreadyExistsException()
            role.code = data.code

        if data.translations is not None:
            ru = ru_of(data.translations)
            if ru.name != role.name:
                await self._check_name(ru.name)
            role.name = ru.name
            role.description = ru.description
            apply_translations(role.translations, data.translations, RoleTranslationORM)

        if data.is_superuser is not None:
            role.is_superuser = data.is_superuser

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

    async def _check_name(self, name: str) -> None:
        if await self.db.role.get_by_name(name):
            raise RoleNameAlreadyExistsException()
