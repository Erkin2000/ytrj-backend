from src.rbac.models.permission_model import PermissionORM
from src.rbac.models.role_model import RoleORM
from src.rbac.schemas.permission_schema import PermissionDTO, PermissionTranslationDTO
from src.rbac.schemas.role_schema import (
    RoleDTO,
    RoleNameOutDTO,
    RoleShortDTO,
    RoleTranslationOutDTO,
)
from src.utils.base_rep.mappers.base import DataMapper


class PermissionDataMapper(DataMapper):
    db_model = PermissionORM
    schema = PermissionDTO

    @staticmethod
    def map_to_domain_entity(model: PermissionORM) -> PermissionDTO:
        return PermissionDTO(
            id=model.id,
            code=model.code,
            translations=[
                PermissionTranslationDTO(
                    language=t.language, name=t.name, description=t.description
                )
                for t in model.translations
            ],
        )


class RoleDataMapper(DataMapper):
    db_model = RoleORM
    schema = RoleDTO

    @staticmethod
    def map_to_domain_entity(model: RoleORM) -> RoleDTO:
        return RoleDTO(
            id=model.id,
            code=model.code,
            translations=[
                RoleTranslationOutDTO(language=t.language, name=t.name, description=t.description)
                for t in model.translations
            ],
            is_superuser=model.is_superuser,
            is_system=model.is_system,
            permissions=sorted(permission.code for permission in model.permissions),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def map_to_short(model: RoleORM | None) -> RoleShortDTO | None:
        if model is None:
            return None
        return RoleShortDTO(
            id=model.id,
            code=model.code,
            translations=[
                RoleNameOutDTO(language=t.language, name=t.name) for t in model.translations
            ],
            is_superuser=model.is_superuser,
        )
