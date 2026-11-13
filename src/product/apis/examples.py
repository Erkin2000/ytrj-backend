"""Примеры продуктов для Swagger."""

from src.common.swagger.responses import keep_nulls
from src.product.schemas.product_schema import (
    CATEGORY_TRANSLATIONS_EXAMPLE,
    FIELD_TRANSLATIONS_EXAMPLE,
    OPTION_TRANSLATIONS_EXAMPLE,
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

CATEGORY_EXAMPLE = {
    "id": 1,
    "translations": CATEGORY_TRANSLATIONS_EXAMPLE,
    "is_active": True,
    "sort_order": 0,
    "products_count": 3,
    "created_at": "2026-11-11T09:00:00Z",
    "updated_at": "2026-11-11T09:00:00Z",
}

CATEGORY_BRIEF_EXAMPLE = {
    "id": 1,
    "translations": [
        {"language": t["language"], "name": t["name"]} for t in CATEGORY_TRANSLATIONS_EXAMPLE
    ],
}

PRODUCT_BRIEF_EXAMPLE = {
    "id": 3,
    "translations": [
        {"language": t["language"], "name": t["name"]} for t in PRODUCT_TRANSLATIONS_EXAMPLE
    ],
}

OPTION_EXAMPLES = [
    {"id": 21, "translations": OPTION_TRANSLATIONS_EXAMPLE, "sort_order": 0},
    {
        "id": 22,
        "translations": [
            {"language": "ru", "name": "Услуги"},
            {"language": "uz", "name": "Xizmatlar"},
            {"language": "en", "name": "Services"},
        ],
        "sort_order": 1,
    },
]

FIELD_EXAMPLES = [
    {
        "id": 11,
        "field_type": "NUMBER",
        "translations": FIELD_TRANSLATIONS_EXAMPLE,
        "is_required": True,
        "max_files": 1,
        "sort_order": 0,
        "options": [],
        "visible_when": None,
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
        "options": [],
        "visible_when": None,
    },
    {
        "id": 10,
        "field_type": "SELECT",
        "translations": [
            {"language": "ru", "name": "Направление деятельности"},
            {"language": "uz", "name": "Faoliyat yoʻnalishi"},
            {"language": "en", "name": "Business area"},
        ],
        "is_required": True,
        "max_files": 1,
        "sort_order": 2,
        "options": OPTION_EXAMPLES,
        "visible_when": None,
    },
    {
        "id": 13,
        "field_type": "STRING",
        "translations": [
            {"language": "ru", "name": "Выпускаемая продукция"},
            {"language": "uz", "name": "Ishlab chiqariladigan mahsulot"},
            {"language": "en", "name": "Products manufactured"},
        ],
        "is_required": True,
        "max_files": 1,
        "sort_order": 3,
        "options": [],
        "visible_when": {"field_id": 10, "option_ids": [21]},
    },
]

STAGE_EXAMPLE = {
    "id": 5,
    "number": 1,
    "translations": STAGE_TRANSLATIONS_EXAMPLE,
    "visible_when": None,
    "fields": FIELD_EXAMPLES,
}

PRODUCT_EXAMPLE = {
    "id": 3,
    "category": CATEGORY_BRIEF_EXAMPLE,
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
        "has_options": False,
        "multiple": False,
        "min_options": None,
        "max_options": None,
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
        "has_options": False,
        "multiple": False,
        "min_options": None,
        "max_options": None,
        "format": None,
        "example": None,
        "pattern": None,
        "max_length": None,
        "max_digits": None,
        "max_files_limit": 10,
        "allowed_content_types": ["image/jpeg", "image/png", "image/webp"],
        "max_size_mb": 5,
    },
    {
        "type": "CHECKBOX",
        "translations": [
            {"language": "ru", "name": "Несколько вариантов"},
            {"language": "uz", "name": "Bir nechta variant"},
            {"language": "en", "name": "Checkboxes"},
        ],
        "is_file": False,
        "has_options": True,
        "multiple": True,
        "min_options": 2,
        "max_options": 50,
        "format": "[<id варианта>, ...]",
        "example": "[21, 22]",
        "pattern": None,
        "max_length": None,
        "max_digits": None,
        "max_files_limit": None,
        "allowed_content_types": None,
        "max_size_mb": None,
    },
]


# ---------- примеры тел запросов (openapi_examples) ----------


def _names(ru: str, uz: str, en: str) -> list[dict]:
    return [
        {"language": "ru", "name": ru},
        {"language": "uz", "name": uz},
        {"language": "en", "name": en},
    ]


def _option(ru: str, uz: str, en: str, sort_order: int) -> dict:
    return {"translations": _names(ru, uz, en), "sort_order": sort_order}


STAGE_CREATE_EXAMPLES = {
    "basic": {
        "summary": "Этап без условия",
        "value": {"number": 1, "translations": STAGE_TRANSLATIONS_EXAMPLE},
    },
    "conditional": {
        "summary": "Этап с условием показа",
        "description": "Этап виден, только если в поле 10 выбран вариант 21.",
        "value": {
            "number": 2,
            "translations": _names(
                "Сведения о производстве", "Ishlab chiqarish haqida maʼlumot", "Production details"
            ),
            "visible_when": {"field_id": 10, "option_ids": [21]},
        },
    },
}

FIELD_CREATE_EXAMPLES = {
    "string": {
        "summary": "STRING — текст",
        "value": {
            "field_type": "STRING",
            "translations": _names(
                "Выпускаемая продукция", "Ishlab chiqariladigan mahsulot", "Products manufactured"
            ),
            "is_required": True,
            "sort_order": 0,
        },
    },
    "number": {
        "summary": "NUMBER — число",
        "value": {
            "field_type": "NUMBER",
            "translations": FIELD_TRANSLATIONS_EXAMPLE,
            "is_required": True,
            "sort_order": 1,
        },
    },
    "file": {
        "summary": "FILE / PHOTO — файлы с лимитом",
        "description": "`max_files` (1–10) учитывается только для PHOTO и FILE.",
        "value": {
            "field_type": "FILE",
            "translations": _names("Бизнес-план", "Biznes-reja", "Business plan"),
            "is_required": False,
            "max_files": 3,
            "sort_order": 2,
        },
    },
    "select": {
        "summary": "SELECT — выпадающий список",
        "description": "Один вариант из списка. `options` — от 2 до 50 вариантов.",
        "value": {
            "field_type": "SELECT",
            "translations": _names(
                "Направление деятельности", "Faoliyat yoʻnalishi", "Business area"
            ),
            "is_required": True,
            "sort_order": 3,
            "options": [
                _option("Производство", "Ishlab chiqarish", "Manufacturing", 0),
                _option("Услуги", "Xizmatlar", "Services", 1),
                _option("Торговля", "Savdo", "Trade", 2),
            ],
        },
    },
    "radio": {
        "summary": "RADIO — один вариант (радиокнопки)",
        "description": "Как SELECT, но фронт показывает все варианты сразу; удобно для 2–5 вариантов.",
        "value": {
            "field_type": "RADIO",
            "translations": _names(
                "Есть ли у вас опыт в бизнесе?",
                "Biznes tajribangiz bormi?",
                "Do you have business experience?",
            ),
            "is_required": True,
            "sort_order": 4,
            "options": [
                _option("Да", "Ha", "Yes", 0),
                _option("Нет", "Yoʻq", "No", 1),
            ],
        },
    },
    "checkbox": {
        "summary": "CHECKBOX — несколько вариантов",
        "description": "Заявитель может отметить несколько вариантов.",
        "value": {
            "field_type": "CHECKBOX",
            "translations": _names("Каналы продаж", "Sotuv kanallari", "Sales channels"),
            "is_required": False,
            "sort_order": 5,
            "options": [
                _option("Офлайн-магазин", "Oflayn doʻkon", "Offline store", 0),
                _option("Интернет-магазин", "Internet-doʻkon", "Online store", 1),
                _option("Маркетплейсы", "Marketpleyslar", "Marketplaces", 2),
            ],
        },
    },
    "conditional": {
        "summary": "Поле с условием показа",
        "description": (
            "Поле видно, только если в поле 10 (SELECT / RADIO / CHECKBOX выше в анкете) "
            "выбран вариант 21."
        ),
        "value": {
            "field_type": "STRING",
            "translations": _names(
                "Выпускаемая продукция", "Ishlab chiqariladigan mahsulot", "Products manufactured"
            ),
            "is_required": True,
            "sort_order": 6,
            "visible_when": {"field_id": 10, "option_ids": [21]},
        },
    },
}

FIELD_UPDATE_EXAMPLES = {
    "required": {
        "summary": "Сделать поле необязательным",
        "value": {"is_required": False},
    },
    "rename": {
        "summary": "Переименовать поле",
        "description": "Передаются все три перевода.",
        "value": {"translations": FIELD_TRANSLATIONS_EXAMPLE},
    },
    "to_radio": {
        "summary": "Сменить SELECT на RADIO",
        "description": "Между SELECT / RADIO / CHECKBOX варианты сохраняются.",
        "value": {"field_type": "RADIO"},
    },
    "set_condition": {
        "summary": "Задать условие показа",
        "value": {"visible_when": {"field_id": 10, "option_ids": [21, 22]}},
    },
    "clear_condition": {
        "summary": "Снять условие показа",
        "description": "`null` — показывать всегда.",
        "value": keep_nulls({"visible_when": None}),
    },
}

OPTION_CREATE_EXAMPLES = {
    "option": {
        "summary": "Новый вариант ответа",
        "value": _option("Сельское хозяйство", "Qishloq xoʻjaligi", "Agriculture", 3),
    },
}
