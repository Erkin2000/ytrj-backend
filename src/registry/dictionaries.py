"""Справочники реестра: регионы, банки, подписи перечислений на ru / uz / en и
нормализация названий из Excel (кириллица и латиница, разные написания)."""

import re

from src.account.models.user_model import Gender
from src.product.enums import Language
from src.registry.enums import (
    Decision,
    ProgramKind,
    ProjectStatus,
    RegistrySubjectType,
    Sector,
)

# ---------- транслитерация узбекской кириллицы ----------

_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ы": "i", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}  # fmt: skip
_APOSTROPHES = "ʻʼ‘’`´ʹ"


def to_latin(text: str) -> str:
    """Узбекская кириллица → латиница; апострофы приводятся к «'»."""
    # «ў» иногда записана двумя символами: «у» + комбинируемая бреве.
    text = text.replace("ў", "ў").replace("Ў", "Ў")
    out = []
    for ch in text:
        low = ch.lower()
        if low in _CYR:
            lat = _CYR[low]
            out.append(lat.capitalize() if ch != low and lat else lat)
        elif ch in _APOSTROPHES:
            out.append("'")
        else:
            out.append(ch)
    return "".join(out)


def key_of(text: str | None) -> str:
    """Ключ для сравнения: латиница, нижний регистр, только буквы и цифры."""
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", to_latin(text).lower())


def clean_text(value) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip().strip('"').strip()
    return text or None


# ---------- регионы ----------

# code -> (ru, uz, en, ключи для распознавания)
REGIONS: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "KARAKALPAKSTAN": (
        "Республика Каракалпакстан",
        "Qoraqalpogʻiston Respublikasi",
        "Republic of Karakalpakstan",
        ("qoraqalpog", "karakalpak"),
    ),
    "ANDIJAN": (
        "Андижанская область",
        "Andijon viloyati",
        "Andijan region",
        ("andijon", "andijan"),
    ),
    "BUKHARA": ("Бухарская область", "Buxoro viloyati", "Bukhara region", ("buxoro", "bukhar")),
    "JIZZAKH": ("Джизакская область", "Jizzax viloyati", "Jizzakh region", ("jizzax", "djizak")),
    "KASHKADARYA": (
        "Кашкадарьинская область",
        "Qashqadaryo viloyati",
        "Kashkadarya region",
        ("qashqadaryo", "kashkadar"),
    ),
    "NAVOI": ("Навоийская область", "Navoiy viloyati", "Navoi region", ("navoiy", "navoi")),
    "NAMANGAN": ("Наманганская область", "Namangan viloyati", "Namangan region", ("namangan",)),
    "SAMARKAND": (
        "Самаркандская область",
        "Samarqand viloyati",
        "Samarkand region",
        ("samarqand", "samarkand"),
    ),
    "SURKHANDARYA": (
        "Сурхандарьинская область",
        "Surxondaryo viloyati",
        "Surkhandarya region",
        ("surxondaryo", "surxondare", "surkhandar"),
    ),
    "SYRDARYA": (
        "Сырдарьинская область",
        "Sirdaryo viloyati",
        "Syrdarya region",
        ("sirdaryo", "sirdare", "syrdar"),
    ),
    "TASHKENT_REGION": (
        "Ташкентская область",
        "Toshkent viloyati",
        "Tashkent region",
        ("toshkentviloyat", "tashkentregion", "tashkentskaya"),
    ),
    "TASHKENT_CITY": (
        "город Ташкент",
        "Toshkent shahri",
        "Tashkent city",
        ("toshkentshah", "tashkentcity", "gorodtashkent"),
    ),
    "FERGANA": ("Ферганская область", "Fargʻona viloyati", "Fergana region", ("fargona", "fergan")),
    "KHOREZM": (
        "Хорезмская область",
        "Xorazm viloyati",
        "Khorezm region",
        ("xorazm", "xorezm", "khorezm"),
    ),
}


def region_code(value) -> str | None:
    """Код региона по названию в любом написании; None — не распознан."""
    key = key_of(clean_text(value))
    if not key:
        return None
    if key in REGIONS or key.upper() in REGIONS:
        return key.upper()
    for code, (*_, keys) in REGIONS.items():
        if any(key.startswith(k) or k in key for k in keys):
            return code
    if key.startswith("toshkent") or key.startswith("tashkent"):
        return "TASHKENT_REGION"
    return None


# ---------- банки ----------

# code -> (ru, uz, en, ключи)
BANKS: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "NBU": (
        "Национальный банк",
        "Milliy bank",
        "National Bank (NBU)",
        ("milliy", "nbu", "natsional", "uzmilliy"),
    ),
    "MICROCREDITBANK": (
        "Микрокредитбанк",
        "Mikrokreditbank",
        "Microcreditbank",
        ("mikrokredit", "microcredit"),
    ),
    "BRB": (
        "Банк развития бизнеса",
        "Biznesni rivojlantirish banki",
        "Business Development Bank",
        ("biznesnirivoj", "brb", "biznesrivoj"),
    ),
    "ASAKABANK": ("Асакабанк", "Asakabank", "Asakabank", ("asaka",)),
    "AGROBANK": ("Агробанк", "Agrobank", "Agrobank", ("agrobank", "agro")),
    "XALQ_BANKI": ("Халк банк", "Xalq banki", "Xalq Bank", ("xalq", "halq", "xalk")),
    "SQB": (
        "Узпромстройбанк (SQB)",
        "Oʻzsanoatqurilishbank (SQB)",
        "Uzpromstroybank (SQB)",
        ("sanoatqurilish", "sqb", "promstroy"),
    ),
    "ALOQABANK": ("Алокабанк", "Aloqabank", "Aloqabank", ("aloqa", "aloka")),
    "TURONBANK": ("Туронбанк", "Turonbank", "Turonbank", ("turon",)),
    "IPOTEKA_BANK": ("Ипотека-банк", "Ipoteka-bank", "Ipoteka Bank", ("ipoteka",)),
    "QQB": (
        "Кишлок курилиш банк",
        "Qishloq qurilish bank",
        "Qishloq Qurilish Bank",
        ("qishloqqurilish",),
    ),
    "HAMKORBANK": ("Хамкорбанк", "Hamkorbank", "Hamkorbank", ("hamkor",)),
}


def bank_code(value) -> str | None:
    key = key_of(clean_text(value))
    if not key:
        return None
    if key.upper() in BANKS:
        return key.upper()
    for code, (*_, keys) in BANKS.items():
        if any(k in key for k in keys):
            return code
    return None


# ---------- туманы ----------

_DISTRICT_SUFFIX = [
    (re.compile(r"\b(tumani|tuman|tuaman|tum\.?|t\.)$", re.I), "tumani"),
    (re.compile(r"\b(shahri|shahar|shaxar|shaxri|sh\.)$", re.I), "shahri"),
]


def district_name(value) -> str | None:
    """Туман в латинице с единым окончанием: «Bo'ston tumani», «Urganch shahri»."""
    text = clean_text(value)
    if not text:
        return None
    text = to_latin(text).strip(" .,")
    text = re.sub(r"\s+", " ", text)
    for pattern, suffix in _DISTRICT_SUFFIX:
        if pattern.search(text):
            text = pattern.sub(suffix, text)
            break
    else:
        text = f"{text} tumani"
    first, *rest = text.split(" ")
    first = first[:1].upper() + first[1:].lower()
    return " ".join([first, *[w.lower() for w in rest]])


def district_key(name: str | None) -> str | None:
    return key_of(name) or None


# ---------- подписи перечислений ----------

LABELS: dict[type, dict[str, tuple[str, str, str]]] = {
    ProgramKind: {
        ProgramKind.CREDIT: ("Кредит", "Kredit", "Credit"),
        ProgramKind.LOAN: ("Заём (ссуда)", "Qarz (ssuda)", "Loan"),
        ProgramKind.COMPENSATION: ("Возмещение затрат", "Qoplab berish", "Cost compensation"),
        ProgramKind.INVESTMENT: ("Инвестиции", "Investitsiya", "Investment"),
    },
    ProjectStatus: {
        ProjectStatus.IN_PROGRESS: ("Оформляется", "Rasmiylashtirilmoqda", "In progress"),
        ProjectStatus.AWAITING_BANK_REQUEST: (
            "Ожидается требование банка",
            "Bank talabnomasi kutilmoqda",
            "Awaiting bank request",
        ),
        ProjectStatus.CLIENT_REFUSED: ("Клиент отказался", "Mijoz rad etdi", "Client refused"),
        ProjectStatus.ALLOCATED: ("Ресурс выделен", "Resurs ajratildi", "Resource allocated"),
        ProjectStatus.CREDIT_ISSUED: ("Кредит выдан", "Kredit berildi", "Credit issued"),
        ProjectStatus.RETURNED: ("Ресурс возвращён", "Resurs qaytarildi", "Resource returned"),
    },
    Decision: {
        Decision.APPROVED: ("Одобрено", "Maʼqullandi", "Approved"),
        Decision.REJECTED: ("Не одобрено", "Maʼqullanmadi", "Rejected"),
    },
    RegistrySubjectType: {
        RegistrySubjectType.LEGAL_ENTITY: ("Юридическое лицо", "Yuridik shaxs", "Legal entity"),
        RegistrySubjectType.SOLE_PROPRIETOR: ("ИП (ЯТТ)", "YaTT", "Sole proprietor"),
        RegistrySubjectType.INDIVIDUAL: ("Физическое лицо", "Jismoniy shaxs", "Individual"),
    },
    Sector: {
        Sector.SERVICES: ("Услуги", "Xizmat koʻrsatish", "Services"),
        Sector.PRODUCTION: ("Производство", "Ishlab chiqarish", "Production"),
        Sector.AGRICULTURE: ("Сельское хозяйство", "Qishloq xoʻjaligi", "Agriculture"),
    },
    Gender: {
        Gender.MALE: ("Мужчина", "Erkak", "Male"),
        Gender.FEMALE: ("Женщина", "Ayol", "Female"),
    },
}

LANGS = (Language.RU, Language.UZ, Language.EN)


def labels(names: tuple[str, str, str]) -> list[dict]:
    return [{"language": lang, "name": name} for lang, name in zip(LANGS, names, strict=True)]


def enum_labels(enum_cls: type, value) -> list[dict]:
    names = LABELS[enum_cls].get(value)
    return labels(names) if names else []


def region_labels(code: str) -> list[dict]:
    ru, uz, en, _ = REGIONS[code]
    return labels((ru, uz, en))


def bank_labels(code: str) -> list[dict]:
    ru, uz, en, _ = BANKS[code]
    return labels((ru, uz, en))


def sector_of(value) -> Sector | None:
    key = key_of(clean_text(value))
    if key.startswith("xizmat"):
        return Sector.SERVICES
    if key.startswith("ishlab"):
        return Sector.PRODUCTION
    if key.startswith("qishloq"):
        return Sector.AGRICULTURE
    return None


def subject_type_of_name(value) -> RegistrySubjectType | None:
    """По названию субъекта: «… MCHJ», «ЯТТ …»."""
    text = clean_text(value)
    if not text:
        return None
    words = set(re.findall(r"[a-z']+", to_latin(text).lower().replace("'", "")))
    if words & {"yatt", "yat", "yakka"}:
        return RegistrySubjectType.SOLE_PROPRIETOR
    if words & {"mchj", "mchzh", "ooo", "llc", "xk", "aj", "qk", "atb"}:
        return RegistrySubjectType.LEGAL_ENTITY
    return None
