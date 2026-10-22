from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, StringConstraints

from src.account.models.user_model import UserStatus
from src.rbac.schemas.role_schema import RoleShortDTO

PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=128)]
UsernameStr = Annotated[
    str,
    StringConstraints(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.@-]+$"),
]
PhoneStr = Annotated[str, StringConstraints(pattern=r"^\+998\d{9}$")]
PinflStr = Annotated[str, StringConstraints(pattern=r"^\d{14}$")]


class BankShortDTO(BaseModel):
    id: int
    code: str
    name: str


class UserDTO(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: UserStatus
    role: RoleShortDTO | None = None
    bank: BankShortDTO | None = None
    organization: str | None = None
    region: str | None = None
    has_password: bool = False
    sso_linked: bool = False
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class UserDetailDTO(UserDTO):
    passport_number: str | None = None
    pinfl: str | None = None
    inn: str | None = None
    updated_at: datetime | None = None


class UserProfileDTO(BaseModel):
    """Собственный профиль (для /auth/me)."""

    id: int
    username: str
    full_name: str | None = None
    phone: str | None = None
    passport_number: str | None = None
    pinfl: str | None = None
    inn: str | None = None
    email: str | None = None
    status: UserStatus
    role: RoleShortDTO | None = None
    bank: BankShortDTO | None = None
    is_superuser: bool
    permissions: list[str]
    last_login_at: datetime | None = None


class CurrentUserDTO(BaseModel):
    """Пользователь из access-токена: роль, права, scope."""

    id: int
    username: str
    full_name: str | None = None
    status: UserStatus
    is_superuser: bool
    permissions: set[str]
    role: RoleShortDTO | None = None
    bank_id: int | None = None

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @property
    def role_code(self) -> str | None:
        return self.role.code if self.role else None

    def has_permission(self, code: str) -> bool:
        return self.is_superuser or code in self.permissions


class UserRequestAddDTO(BaseModel):
    username: UsernameStr
    password: PasswordStr
    role_id: int
    full_name: str | None = None
    phone: PhoneStr | None = None
    email: EmailStr | None = None
    bank_id: int | None = None
    organization: str | None = None
    region: str | None = None


class UserRequestUpdateDTO(BaseModel):
    username: UsernameStr | None = None
    password: PasswordStr | None = None
    role_id: int | None = None
    full_name: str | None = None
    phone: PhoneStr | None = None
    email: EmailStr | None = None
    bank_id: int | None = None
    organization: str | None = None
    region: str | None = None


class UserStatusUpdateDTO(BaseModel):
    status: UserStatus
    reason: str | None = None


class UserRoleAssignDTO(BaseModel):
    role_id: int | None = None  # None — отзыв роли
    bank_id: int | None = None


class UserAddDTO(BaseModel):
    username: str
    hashed_password: str | None = None
    role_id: int | None = None
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    bank_id: int | None = None
    organization: str | None = None
    region: str | None = None
    sso_sub: str | None = None
    passport_number: str | None = None
    pinfl: str | None = None
    inn: str | None = None


class UserUpdateDTO(BaseModel):
    username: str | None = None
    hashed_password: str | None = None
    role_id: int | None = None
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    bank_id: int | None = None
    organization: str | None = None
    region: str | None = None
    status: UserStatus | None = None
    sso_sub: str | None = None
    passport_number: str | None = None
    pinfl: str | None = None
    inn: str | None = None
    last_login_at: datetime | None = None


class UserSessionDTO(BaseModel):
    id: int
    created_at: datetime
    expires_at: datetime
    is_revoked: bool
    user_agent: str | None = None
    ip_address: str | None = None


class UserFilterDTO(BaseModel):
    search: str | None = None
    role_id: int | None = None
    role_code: str | None = None
    status: UserStatus | None = None
    bank_id: int | None = None
