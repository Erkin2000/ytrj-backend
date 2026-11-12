from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.account.models.user_model import UserORM

SSO_MANAGED_FIELDS: tuple[str, ...] = ("full_name", "pinfl")

SELF_EDITABLE_FIELDS: tuple[str, ...] = (
    "phone",
    "passport_number",
    "inn",
    "email",
    "gender",
    "date_of_birth",
)

REQUIRED_APPLICANT_FIELDS: tuple[str, ...] = SSO_MANAGED_FIELDS + SELF_EDITABLE_FIELDS


def missing_profile_fields(user: UserORM) -> list[str]:
    return [field for field in REQUIRED_APPLICANT_FIELDS if not getattr(user, field, None)]
