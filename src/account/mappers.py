from src.account.models.user_model import UserORM
from src.account.schemas.user_schema import (
    BankShortDTO,
    CurrentUserDTO,
    UserDetailDTO,
    UserDTO,
    UserProfileDTO,
)
from src.rbac.mappers import RoleDataMapper
from src.utils.base_rep.mappers.base import DataMapper


def _bank_short(model: UserORM) -> BankShortDTO | None:
    if model.bank is None:
        return None
    return BankShortDTO(id=model.bank.id, code=model.bank.code, name=model.bank.name)


def _base_fields(model: UserORM) -> dict:
    return {
        "id": model.id,
        "username": model.username,
        "full_name": model.full_name,
        "phone": model.phone,
        "email": model.email,
        "status": model.status,
        "role": RoleDataMapper.map_to_short(model.role),
        "bank": _bank_short(model),
        "organization": model.organization,
        "region": model.region,
        "has_password": model.hashed_password is not None,
        "sso_linked": model.sso_sub is not None,
        "last_login_at": model.last_login_at,
        "created_at": model.created_at,
    }


class UserDataMapper(DataMapper):
    db_model = UserORM
    schema = UserDTO

    @staticmethod
    def map_to_domain_entity(model: UserORM) -> UserDTO:
        return UserDTO(**_base_fields(model))

    @staticmethod
    def map_to_detail(model: UserORM) -> UserDetailDTO:
        return UserDetailDTO(
            **_base_fields(model),
            passport_number=model.passport_number,
            pinfl=model.pinfl,
            inn=model.inn,
            updated_at=model.updated_at,
        )

    @staticmethod
    def map_to_current_user(model: UserORM) -> CurrentUserDTO:
        role = model.role
        return CurrentUserDTO(
            id=model.id,
            username=model.username,
            full_name=model.full_name,
            status=model.status,
            is_superuser=bool(role and role.is_superuser),
            permissions={p.code for p in role.permissions} if role else set(),
            role=RoleDataMapper.map_to_short(role),
            bank_id=model.bank_id,
        )

    @staticmethod
    def map_to_profile(model: UserORM, permissions: list[str]) -> UserProfileDTO:
        role = model.role
        return UserProfileDTO(
            id=model.id,
            username=model.username,
            full_name=model.full_name,
            phone=model.phone,
            passport_number=model.passport_number,
            pinfl=model.pinfl,
            inn=model.inn,
            email=model.email,
            status=model.status,
            role=RoleDataMapper.map_to_short(role),
            bank=_bank_short(model),
            is_superuser=bool(role and role.is_superuser),
            permissions=permissions,
            last_login_at=model.last_login_at,
        )
