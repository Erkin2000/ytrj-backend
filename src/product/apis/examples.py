"""Примеры продуктов для Swagger."""

from src.product.schemas.product_schema import (
    FIELD_TRANSLATIONS_EXAMPLE,
    PRODUCT_TRANSLATIONS_EXAMPLE,
    STAGE_TRANSLATIONS_EXAMPLE,
)

BANK_EXAMPLE = {
    "id": 1,
    "code": "microcreditbank",
    "name": "Microcreditbank",
    "official_name": "АКБ «Микрокредитбанк»",
    "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
    "is_active": True,
    "sort_order": 1,
}

PRODUCT_BRIEF_EXAMPLE = {
    "id": 3,
    "translations": [
        {"language": t["language"], "name": t["name"]} for t in PRODUCT_TRANSLATIONS_EXAMPLE
    ],
}

FIELD_EXAMPLES = [
    {
        "id": 11,
        "field_type": "NUMBER",
        "translations": FIELD_TRANSLATIONS_EXAMPLE,
        "is_required": True,
        "max_files": 1,
        "sort_order": 0,
    },
    {
        "id": 12,
        "field_type": "PHOTO",
        "translations": [
            {"language": "ru", "name": "Фото места деятельности"},
            {"language": "uz", "name": "Faoliyat joyi surati"},
            {"language": "en", "name": "Business location photo"},
        ],
        "is_required": True,
        "max_files": 4,
        "sort_order": 1,
    },
]

STAGE_EXAMPLE = {
    "id": 5,
    "number": 1,
    "translations": STAGE_TRANSLATIONS_EXAMPLE,
    "fields": FIELD_EXAMPLES,
}

PRODUCT_EXAMPLE = {
    "id": 3,
    "translations": PRODUCT_TRANSLATIONS_EXAMPLE,
    "status": "PUBLISHED",
    "allowed_subject_types": ["YATT", "MCHJ", "SELF_EMPLOYED"],
    "accept_from": "2026-11-10",
    "accept_to": "2026-12-31",
    "banks": [BANK_EXAMPLE],
    "created_at": "2026-11-06T09:00:00Z",
    "updated_at": "2026-11-06T09:30:00Z",
}

PRODUCT_DETAIL_EXAMPLE = {
    **PRODUCT_EXAMPLE,
    "stages": [STAGE_EXAMPLE],
    "copied_from_id": None,
    "applications_count": 0,
    "is_locked": False,
}

FIELD_TYPES_EXAMPLE = [
    {
        "type": "PHONE",
        "translations": [
            {"language": "ru", "name": "Телефон"},
            {"language": "uz", "name": "Telefon"},
            {"language": "en", "name": "Phone"},
        ],
        "is_file": False,
        "format": "+998XXXXXXXXX",
        "example": "+998901234567",
        "pattern": r"^\+998\d{9}$",
        "max_length": None,
        "max_digits": None,
        "max_files_limit": None,
        "allowed_content_types": None,
        "max_size_mb": None,
    },
    {
        "type": "PHOTO",
        "translations": [
            {"language": "ru", "name": "Фото"},
            {"language": "uz", "name": "Surat"},
            {"language": "en", "name": "Photo"},
        ],
        "is_file": True,
        "format": None,
        "example": None,
        "pattern": None,
        "max_length": None,
        "max_digits": None,
        "max_files_limit": 10,
        "allowed_content_types": ["image/jpeg", "image/png", "image/webp"],
        "max_size_mb": 5,
    },
]
