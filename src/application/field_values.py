"""Проверка и нормализация значений полей анкеты продукта по их типу."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import EmailStr, TypeAdapter, ValidationError

from src.product.enums import FieldType

MAX_STRING_LENGTH = 2000
MAX_NUMBER_DIGITS = 18
PHONE_RE = re.compile(r"^\+998\d{9}$")
_email = TypeAdapter(EmailStr)


def normalize_value(field_type: FieldType, raw: str) -> str:
    """Возвращает значение в каноническом виде или бросает ValueError с пояснением."""
    value = raw.strip()

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
