"""Тексты акта на узбекском: даты, имена, номера."""

from datetime import date

from src.act.enums import UZ_MONTHS

# Апострофы узбекской латиницы, которые встречаются в Ф.И.О. из OneID.
_APOSTROPHES = str.maketrans({"'": "‘", "`": "‘", "ʻ": "‘", "’": "‘", "ʼ": "‘"})


def uz_day_month(value: date) -> str:
    """«26-noyabr»."""
    return f"{value.day}-{UZ_MONTHS[value.month - 1]}"


def uz_date(value: date) -> str:
    """«26-noyabr 2026 yil»."""
    return f"{uz_day_month(value)} {value.year} yil"


def uz_quoted_date(value: date) -> str:
    """«“26” noyabr 2026 y.» — для блока «TASDIQLAYMAN»."""
    return f"“{value.day}” {UZ_MONTHS[value.month - 1]} {value.year} y."


def uz_period(period_from: date, period_to: date) -> str:
    """«23-oktabrdan 26-noyabrga qadar»."""
    return f"{uz_day_month(period_from)}dan {uz_day_month(period_to)}ga qadar"


def uz_range(period_from: date, period_to: date) -> str:
    """«23-oktabr – 26-noyabr» — срок по умолчанию в строке таблицы."""
    if period_from == period_to:
        return uz_day_month(period_from)
    return f"{uz_day_month(period_from)} – {uz_day_month(period_to)}"


def _word(value: str) -> str:
    value = value.translate(_APOSTROPHES)
    return value[:1].upper() + value[1:].lower()


def display_name(full_name: str | None) -> str:
    """«AHMADJONOV ZIYODBEK MURODJON O‘G‘LI» → «Ahmadjonov Ziyodbek» (фамилия и имя)."""
    words = (full_name or "").split()
    return " ".join(_word(w) for w in words[:2])


def short_name(name: str) -> str:
    """«Ahmadjonov Ziyodbek» → «Z.Ahmadjonov» — для строк подписи."""
    words = name.split()
    if len(words) < 2:
        return name
    return f"{words[1][:1].upper()}.{words[0]}"


def act_number(act_id: int, year: int) -> str:
    return f"DAL-{year}-{act_id:06d}"
