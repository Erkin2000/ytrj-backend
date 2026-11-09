"""Справочник типов полей анкеты: названия на ru/uz/en и правила заполнения.
Единый источник для фронтенда (конструктор Фонда и форма заявителя)."""

from src.application.field_values import MAX_NUMBER_DIGITS, MAX_STRING_LENGTH, PHONE_RE
from src.config import settings
from src.product.enums import FILE_FIELD_TYPES, FieldType
from src.product.schemas.product_schema import MAX_FILES_LIMIT, FieldTypeInfoDTO

# тип → (ru, uz, en, формат, пример)
_CATALOG: dict[FieldType, tuple[str, str, str, str | None, str | None]] = {
    FieldType.STRING: ("Текст", "Matn", "Text", None, "Швейный цех"),
    FieldType.NUMBER: ("Число", "Son", "Number", "123456.78", "150000000"),
    FieldType.DATE: ("Дата", "Sana", "Date", "YYYY-MM-DD", "2026-12-01"),
    FieldType.PHONE: ("Телефон", "Telefon", "Phone", "+998XXXXXXXXX", "+998901234567"),
    FieldType.EMAIL: ("Email", "Email", "Email", "name@example.com", "user@example.com"),
    FieldType.PHOTO: ("Фото", "Surat", "Photo", None, None),
    FieldType.FILE: ("Файл", "Fayl", "File", None, None),
}


def field_types() -> list[FieldTypeInfoDTO]:
    items = []
    for field_type, (ru, uz, en, value_format, example) in _CATALOG.items():
        is_file = field_type in FILE_FIELD_TYPES
        info = {
            "type": field_type,
            "translations": [
                {"language": "ru", "name": ru},
                {"language": "uz", "name": uz},
                {"language": "en", "name": en},
            ],
            "is_file": is_file,
            "format": value_format,
            "example": example,
            "max_files_limit": MAX_FILES_LIMIT if is_file else None,
        }
        if field_type == FieldType.STRING:
            info["max_length"] = MAX_STRING_LENGTH
        if field_type == FieldType.NUMBER:
            info["max_digits"] = MAX_NUMBER_DIGITS
        if field_type == FieldType.PHONE:
            info["pattern"] = PHONE_RE.pattern
        if field_type == FieldType.PHOTO:
            info["allowed_content_types"] = list(settings.PHOTO_ALLOWED_TYPES)
            info["max_size_mb"] = settings.PHOTO_MAX_SIZE_MB
        if field_type == FieldType.FILE:
            info["allowed_content_types"] = list(settings.DOCUMENT_ALLOWED_TYPES)
            info["max_size_mb"] = settings.DOCUMENT_MAX_SIZE_MB
        items.append(FieldTypeInfoDTO(**info))
    return items
