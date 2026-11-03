"""Эффективные права пользователя и направления (делегированное администрирование).

Направление — системная роль сотрудника: Фонд, банк (+ конкретный банк), Совет.
Роль задаёт «потолок» прав направления; сотрудник получает только личные права
(user_permissions), выданные Super Admin или админом своего направления, и
только в пределах потолка. Заявитель и роль-суперпользователь работают по
правам роли, как раньше.
"""

from typing import TYPE_CHECKING

from src.rbac.permissions import RoleCode

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM
    from src.rbac.models.role_model import RoleORM

DIRECTION_ROLES: frozenset[str] = frozenset(
    {RoleCode.FUND_OPERATOR, RoleCode.BANK_EMPLOYEE, RoleCode.COUNCIL_MEMBER}
)


def role_ceiling(role: "RoleORM | None") -> set[str]:
    return {p.code for p in role.permissions} if role else set()


def uses_personal_permissions(role: "RoleORM | None") -> bool:
    """Роль, права которой выдаются сотруднику поштучно (не заявитель и не суперпользователь)."""
    return role is not None and not role.is_superuser and role.code != RoleCode.APPLICANT


def effective_permissions(user: "UserORM") -> set[str]:
    role = user.role
    ceiling = role_ceiling(role)
    if not uses_personal_permissions(role):
        return ceiling
    return ceiling & {p.code for p in user.permissions}
