"""Правила заполнения профиля заявителя.

YIA Portal (SSO) передаёт только Ф.И.О. и ПИНФЛ — эти поля ведутся из источника
и пользователем не редактируются. Остальные персональные данные заявитель
дополняет сам через ``PATCH /auth/me``; пока они не заполнены, заявку создать
нельзя. Список полей — единая точка для API, сервиса заявок и проверок.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM

# Приходят из YIA SSO, редактированию не подлежат.
SSO_MANAGED_FIELDS: tuple[str, ...] = ("full_name", "pinfl")

# Заполняются пользователем в личном кабинете.
SELF_EDITABLE_FIELDS: tuple[str, ...] = (
    "phone",
    "passport_number",
    "inn",
    "email",
    "gender",
    "date_of_birth",
)

# Обязательны для создания заявки.
REQUIRED_APPLICANT_FIELDS: tuple[str, ...] = SSO_MANAGED_FIELDS + SELF_EDITABLE_FIELDS


def missing_profile_fields(user: UserORM) -> list[str]:
    """Незаполненные поля профиля, без которых нельзя подать заявку."""
    return [field for field in REQUIRED_APPLICANT_FIELDS if not getattr(user, field, None)]
