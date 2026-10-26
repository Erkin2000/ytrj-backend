"""Локализация админ-панели: русский (по умолчанию), узбекский и английский.

SQLAdmin переводит собственные строки интерфейса через Babel и поставляет
каталоги только для en/de/az/ru/tr/ja. Узбекский каталог лежит рядом
(``translations/uz/LC_MESSAGES/admin.po``) и содержит два слоя:

* системные строки SQLAdmin (английские msgid → узбекский);
* строки нашей админки — подписи моделей, колонок, статусов, дашборда
  (русские msgid → узбекский). Для русского перевода не нужно: исходные
  строки уже русские, а системные строки берутся из каталога SQLAdmin.

Английский каталог (``translations/en/LC_MESSAGES/admin.po``) содержит только
второй слой: системные строки SQLAdmin уже английские.

Каталог компилируется из .po при старте, .mo в репозитории не храним.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po
from babel.support import Translations
from sqladmin import i18n as sqladmin_i18n
from sqladmin.i18n import gettext, lazy_gettext

__all__ = ["_", "_l", "ADMIN_LOCALES", "DEFAULT_ADMIN_LOCALE", "register_locales"]

_ = gettext
"""Перевод во время запроса (форматтеры, дашборд)."""

_l = lazy_gettext
"""Отложенный перевод для строк, объявляемых при импорте (name, category, фильтры)."""

TRANSLATIONS_DIR = Path(__file__).resolve().parent / "translations"

DEFAULT_ADMIN_LOCALE = "ru"
ADMIN_LOCALES = ["ru", "uz", "en"]

# Узбекистан — единый пояс UTC+5 без перехода на летнее время, поэтому
# фиксированное смещение надёжнее zoneinfo (на Windows без tzdata его нет).
TASHKENT_TZ = timezone(timedelta(hours=5), name="Asia/Tashkent")


def _load_catalog(locale: str) -> Translations | None:
    po_path = TRANSLATIONS_DIR / locale / "LC_MESSAGES" / "admin.po"
    if not po_path.is_file():
        return None
    with po_path.open("rb") as fh:
        catalog = read_po(fh, locale=locale, domain="admin")
    buffer = BytesIO()
    write_mo(buffer, catalog)
    buffer.seek(0)
    return Translations(fp=buffer, domain="admin")


def register_locales() -> None:
    """Регистрирует наши каталоги в SQLAdmin (идемпотентно).

    Локали без собственного .po (ru) используют каталог SQLAdmin как есть;
    наш .po (uz, en) объединяется поверх пакетного, если такой есть.
    """
    if not sqladmin_i18n.BABEL_INSTALLED:
        return

    for locale in ADMIN_LOCALES:
        own = _load_catalog(locale)
        if own is None:
            continue
        base = sqladmin_i18n.translations.get(locale)
        if isinstance(base, Translations):
            base.merge(own)
        else:
            sqladmin_i18n.translations[locale] = own
        if locale not in sqladmin_i18n.SUPPORTED_LOCALES:
            sqladmin_i18n.SUPPORTED_LOCALES.append(locale)


# ---------- форматирование под локаль ----------


def fmt_dt(value: datetime | None, with_time: bool = True) -> str:
    """Дата/время в тайм-зоне Ташкента: 23.10.2026 14:05."""
    if value is None:
        return "—"
    if value.tzinfo is not None:
        value = value.astimezone(TASHKENT_TZ)
    return value.strftime("%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y")


def fmt_money(amount: Decimal | int | float | None, currency: str | None = "UZS") -> str:
    """1 500 000,00 UZS — разряды пробелом, дробная часть запятой (ru/uz)."""
    if amount is None:
        return "—"
    text = f"{Decimal(amount):,.2f}".replace(",", " ").replace(".", ",")
    return f"{text} {currency}".strip()


def fmt_size(size: int | None) -> str:
    if size is None:
        return "—"
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
