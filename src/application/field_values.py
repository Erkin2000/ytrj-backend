"""Проверка и нормализация значений полей анкеты продукта по их типу."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import EmailStr, TypeAdapter, ValidationError

from src.product.enums import CHOICE_FIELD_TYPES, MULTI_CHOICE_FIELD_TYPES, FieldType
from src.product.models.product_model import ProductFieldORM

MAX_STRING_LENGTH = 2000
MAX_NUMBER_DIGITS = 18
PHONE_RE = re.compile(r"^\+998\d{9}$")
_email = TypeAdapter(EmailStr)

RawValue = str | int | list[int] | list[str]


def chosen_option_ids(field: ProductFieldORM, value: str | None) -> set[int]:
    """Выбранные варианты по сохранённому значению: SELECT / RADIO — один id,
    CHECKBOX — id через запятую. Для остальных типов — пусто."""
    if not value or field.field_type not in CHOICE_FIELD_TYPES:
        return set()
    ids = set()
    for part in value.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def _option_ids(field: ProductFieldORM, raw: RawValue) -> list[int]:
    """Список id вариантов из сырого значения: число, строка с id через запятую или список."""
    parts: list[str | int]
    if isinstance(raw, list):
        parts = list(raw)
    elif isinstance(raw, int):
        parts = [raw]
    else:
        parts = [p for p in raw.split(",") if p.strip()]
    ids: list[int] = []
    for part in parts:
        text = str(part).strip()
        if not text.isdigit():
            raise ValueError("Expected option id(s) of this field")
        ids.append(int(text))
    known = {option.id for option in field.options}
    unknown = sorted(set(ids) - known)
    if unknown:
        raise ValueError(f"Option does not belong to this field: {', '.join(map(str, unknown))}")
    return sorted(dict.fromkeys(ids))


def normalize_value(field: ProductFieldORM, raw: RawValue) -> str | None:
    """Возвращает значение в каноническом виде, `None` для пустого значения
    или бросает ValueError с пояснением."""
    field_type = field.field_type

    if field_type in CHOICE_FIELD_TYPES:
        ids = _option_ids(field, raw)
        if not ids:
            return None
        if field_type not in MULTI_CHOICE_FIELD_TYPES and len(ids) > 1:
            raise ValueError("Only one option can be selected in this field")
        return ",".join(map(str, ids))

    if isinstance(raw, list):
        raise ValueError("Expected a single value, not a list")
    value = str(raw).strip()
    if not value:
        return None

    if field_type == FieldType.STRING:
        if len(value) > MAX_STRING_LENGTH:
            raise ValueError(f"Text is longer than {MAX_STRING_LENGTH} characters")
        return value

    if field_type == FieldType.NUMBER:
        try:
            number = Decimal(value.replace(" ", "").replace(",", "."))
        except InvalidOperation:
            raise ValueError("Expected a number, e.g. 150000000 or 12.5") from None
        if not number.is_finite():
            raise ValueError("Expected a finite number")
        text = format(number.normalize(), "f")
        if len(text.lstrip("-").replace(".", "")) > MAX_NUMBER_DIGITS:
            raise ValueError(f"Number has more than {MAX_NUMBER_DIGITS} digits")
        return text

    if field_type == FieldType.DATE:
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            raise ValueError("Expected a date in YYYY-MM-DD format") from None

    if field_type == FieldType.PHONE:
        phone = re.sub(r"[\s\-()]", "", value)
        if not PHONE_RE.match(phone):
            raise ValueError("Expected a phone in +998XXXXXXXXX format")
        return phone

    if field_type == FieldType.EMAIL:
        try:
            return _email.validate_python(value).lower()
        except ValidationError:
            raise ValueError("Expected a valid email address") from None

    raise ValueError("Files are uploaded to this field, not values")
